"""Single-user, loopback-only browser workspace. No remote hosting or arbitrary path API."""

import hmac
import json
import secrets
import shutil
import tempfile
import threading
import webbrowser
from copy import deepcopy
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from importlib.resources import files
from pathlib import Path
from urllib.parse import parse_qs, urlsplit
from xml.etree.ElementTree import ParseError
from zipfile import BadZipFile

from defusedxml.common import DefusedXmlException

from atlasweave import __version__
from atlasweave.adapters import MAX_FILE_BYTES, adapter_for
from atlasweave.exporters import agent_brief, export_mapping
from atlasweave.models import AtlasWeaveError, ReadOptions
from atlasweave.project import (
    add_manual_pair,
    decide,
    discover,
    validate_project,
    verify_project,
)
from atlasweave.strategies import StrategyConfig

ASSETS = {
    "/": ("index.html", "text/html; charset=utf-8"),
    "/app.js": ("app.js", "text/javascript; charset=utf-8"),
    "/styles.css": ("styles.css", "text/css; charset=utf-8"),
    "/mark.png": ("mark.png", "image/png"),
}


def upload_name(name):
    if (
        not isinstance(name, str)
        or not name
        or len(name) > 200
        or any(char in name for char in "/\\:")
        or any(ord(char) < 32 or ord(char) == 127 for char in name)
        or name in (".", "..")
    ):
        raise AtlasWeaveError("Choose a CSV/XLSX file with a plain filename.")
    adapter_for(name)
    return name


class Workspace:
    def __init__(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="atlasweave-")
        self.root = Path(self.temporary.name)
        self.sources = {}
        self.project = None
        self.revision = 0
        self.lock = threading.RLock()

    def close(self):
        self.temporary.cleanup()

    def state(self):
        return {
            "sources": self.sources,
            "project": self.project,
            "version": __version__,
            "revision": self.revision,
        }

    def clear(self):
        for side in ("left", "right"):
            shutil.rmtree(self.root / side, ignore_errors=True)
        self.sources = {}
        self.project = None
        self.revision += 1

    def upload(self, side, name, content):
        if side not in ("left", "right"):
            raise AtlasWeaveError("Select the left or right source.")
        name = upload_name(name)
        if not content or len(content) > MAX_FILE_BYTES:
            raise AtlasWeaveError("Choose a nonempty file no larger than 32 MiB.")
        # Validate before replacing the previous source or invalidating its decisions.
        with tempfile.TemporaryDirectory(dir=self.root) as staging:
            path = Path(staging) / name
            path.write_bytes(content)
            adapter = adapter_for(name)
            sheets = adapter.discover(str(path)) if adapter.format == "xlsx" else []
            destination = self.root / side
            shutil.rmtree(destination, ignore_errors=True)
            destination.mkdir()
            shutil.move(str(path), destination / name)
        self.sources[side] = {
            "name": name,
            "format": adapter.format,
            "bytes": len(content),
            "sheets": sheets,
        }
        self.project = None
        self.revision += 1

    def require_project(self):
        if self.project is None:
            raise AtlasWeaveError("Discover relationships before reviewing or exporting.")
        self.check_paths(self.project)
        verify_project(self.project, self.root)

    def check_paths(self, project):
        for side in ("left", "right"):
            if side not in self.sources:
                raise AtlasWeaveError("Choose both original source files first.")
            expected = f"{side}/{self.sources[side]['name']}"
            if project["sources"][side]["path"] != expected:
                raise AtlasWeaveError(
                    "This project does not reference the selected source files. "
                    "Reopen a browser-saved project with its original filenames."
                )

    def action(self, action, payload):
        if not isinstance(payload, dict):
            raise AtlasWeaveError("Expected a JSON object.")
        # Every mutation is bound to the state the tab last observed.
        if type(payload.get("revision")) is not int or payload["revision"] != self.revision:
            raise AtlasWeaveError("Workspace changed in another tab. Refresh before continuing.")
        if action == "clear":
            self.clear()
        elif action == "demo":
            for side, name in (("left", "orders.csv"), ("right", "customers.csv")):
                self.upload(side, name, files("atlasweave").joinpath("web", name).read_bytes())
            self.discover({})
        elif action == "discover":
            self.discover(payload)
        elif action == "restore":
            # Keep JSON number representations intact across JavaScript save/open.
            proposed = (
                json.loads(payload["document"]) if "document" in payload else payload.get("project")
            )
            validate_project(proposed)
            self.check_paths(proposed)
            verify_project(proposed, self.root)
            # A saved project's explicit decisions must still satisfy approval constraints.
            for candidate in proposed["candidates"]:
                if candidate["status"] == "approved":
                    decide(proposed, candidate["id"], "approved", candidate["rules"])
            self.project = proposed
            self.revision += 1
        elif action in ("review", "manual", "export", "save"):
            self.require_project()
            if action == "review":
                proposed = deepcopy(self.project)
                decide(
                    proposed, payload.get("candidate"), payload.get("status"), payload.get("rules")
                )
                self.project = proposed
                self.revision += 1
            elif action == "manual":
                self.project = add_manual_pair(
                    self.project, self.root, payload.get("left_field"), payload.get("right_field")
                )
                self.revision += 1
            elif action == "export":
                mapping = export_mapping(self.project)
                return {"mapping": mapping, "brief": agent_brief(mapping)}
            elif action == "save":
                return {"document": json.dumps(self.project, indent=2, ensure_ascii=True)}
        else:
            raise AtlasWeaveError("Unknown workspace action.")
        return self.state()

    def discover(self, payload):
        if set(self.sources) != {"left", "right"}:
            raise AtlasWeaveError("Choose both source files first.")
        options = {}
        for side in ("left", "right"):
            supplied = payload.get(f"{side}_options", {})
            if not isinstance(supplied, dict):
                raise AtlasWeaveError("Invalid import options.")
            options[side] = ReadOptions(**supplied)
        config = StrategyConfig(**payload.get("config", {}))
        proposed = discover(
            self.root / "left" / self.sources["left"]["name"],
            self.root / "right" / self.sources["right"]["name"],
            self.root,
            options["left"],
            options["right"],
            config,
        )
        self.project = proposed
        self.revision += 1


class LocalServer(ThreadingHTTPServer):
    daemon_threads = False
    block_on_close = True

    def __init__(self, port=0):
        if type(port) is not int or not 0 <= port <= 65535:
            raise AtlasWeaveError("Port must be between 0 and 65535.")
        super().__init__(("127.0.0.1", port), Handler)
        self.workspace = Workspace()
        self.token = secrets.token_urlsafe(32)
        self.origin = f"http://127.0.0.1:{self.server_port}"

    def server_close(self):
        super().server_close()
        if hasattr(self, "workspace"):
            self.workspace.close()


class Handler(BaseHTTPRequestHandler):
    server_version = "AtlasWeave"

    def setup(self):
        super().setup()
        self.connection.settimeout(30)

    def log_message(self, _format, *_args):
        pass  # Do not log filenames, project data, or authentication tokens.

    def reply(self, status, body, content_type="application/json; charset=utf-8"):
        if not isinstance(body, bytes):
            body = json.dumps(body, ensure_ascii=True, allow_nan=False).encode()
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header(
            "Content-Security-Policy",
            "default-src 'self'; script-src 'self'; "
            "style-src 'self'; img-src 'self'; connect-src 'self'; "
            "frame-ancestors 'none'; base-uri 'none'; form-action 'none'",
        )
        self.end_headers()
        self.wfile.write(body)

    def authorized(self, api=False):
        if self.headers.get("Host") != urlsplit(self.server.origin).netloc:
            self.reply(403, {"error": "Invalid local host."})
            return False
        if self.headers.get("Origin") not in (None, self.server.origin):
            self.reply(403, {"error": "Cross-origin requests are not permitted."})
            return False
        if api and not hmac.compare_digest(
            self.headers.get("X-AtlasWeave-Token", "").encode("utf-8"),
            self.server.token.encode("ascii"),
        ):
            self.reply(403, {"error": "Open the URL printed by atlasweave serve to connect."})
            return False
        return True

    def do_GET(self):
        path = urlsplit(self.path).path
        if not self.authorized(api=path.startswith("/api/")):
            return
        if path in ASSETS:
            name, mime = ASSETS[path]
            self.reply(200, files("atlasweave").joinpath("web", name).read_bytes(), mime)
        elif path == "/api/state":
            with self.server.workspace.lock:
                self.reply(200, self.server.workspace.state())
        else:
            self.reply(404, {"error": "Not found."})

    def do_OPTIONS(self):
        self.reply(403, {"error": "Cross-origin requests are not permitted."})

    def do_POST(self):
        if not self.authorized(api=True):
            return
        parsed = urlsplit(self.path)
        limit = MAX_FILE_BYTES if parsed.path == "/api/upload" else 16 * 1024 * 1024
        try:
            if self.headers.get("Transfer-Encoding"):
                raise AtlasWeaveError("Chunked uploads are not supported.")
            length = int(self.headers.get("Content-Length", "-1"))
            if not 0 <= length <= limit:
                self.reply(413, {"error": "Request exceeds the allowed size."})
                return
            body = self.rfile.read(length)
            if len(body) != length:
                raise AtlasWeaveError("Incomplete upload. Choose the file again.")
            with self.server.workspace.lock:
                if parsed.path == "/api/upload":
                    if self.headers.get_content_type() != "application/octet-stream":
                        raise AtlasWeaveError("Upload a file as binary content.")
                    params = parse_qs(parsed.query)
                    revision = int(params.get("revision", ["-1"])[0])
                    if revision != self.server.workspace.revision:
                        raise AtlasWeaveError("Workspace changed. Refresh before uploading.")
                    self.server.workspace.upload(
                        params.get("side", [""])[0], params.get("name", [""])[0], body
                    )
                    result = self.server.workspace.state()
                else:
                    if self.headers.get_content_type() != "application/json":
                        raise AtlasWeaveError("Expected application/json.")
                    if not parsed.path.startswith("/api/"):
                        self.reply(404, {"error": "Not found."})
                        return
                    result = self.server.workspace.action(parsed.path[5:], json.loads(body))
                self.reply(200, result)
        except (AtlasWeaveError, DefusedXmlException, ParseError, BadZipFile) as exc:
            self.reply(400, {"error": str(exc)})
        except (ValueError, KeyError, TypeError, OverflowError):
            self.reply(400, {"error": "Invalid file or settings. Check the inputs and try again."})
        except OSError:
            self.reply(400, {"error": "Could not read the local upload. Select the file again."})


def serve(port=8765, *, open_browser=True):
    with LocalServer(port) as server:
        url = f"{server.origin}/#token={server.token}"
        print(f"AtlasWeave local workspace: {url}", flush=True)
        print(
            "Files stay on this computer. Stop with Ctrl+C to remove temporary uploads.", flush=True
        )
        if open_browser:
            webbrowser.open(url)
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            print("\nWorkspace stopped. Temporary uploads removed.", flush=True)
