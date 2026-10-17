# Local browser workspace

After installing the package, run `atlasweave serve`. It binds to `127.0.0.1:8765` and opens a browser tab. If that port is busy, use `atlasweave serve --port 8766` or `--port 0` to choose a free one. `--no-browser` prints the URL without launching a browser. Open the printed URL, including its session fragment; opening only the bare port in a new tab will not authenticate.

## From sources to handoff

1. Choose or drop one CSV/XLSX file on each source card. Left is the table whose unmatched rows a left join preserves; right is the lookup table. The sample uses orders and customers.
2. Choose Excel worksheets, header rows, and CSV delimiters. Expand Matching settings for scan limits, minimum score, aliases, and trim/casefold normalization.
3. Run discovery. Search and filter the candidates, select one to inspect evidence, or choose up to three checkboxes and compare them. The field-pair panel can inspect a relationship below the suggestion threshold.
4. Choose left/inner join rules, explicitly allow right duplicates/nulls only when intended, and approve or reject. Reset returns a decision to pending. Partial scans and no-overlap pairs cannot be approved.
5. Prepare a handoff, inspect its preview, and download the JSON specification and Markdown brief. No join is executed. Changing approved join rules requires updating approval before export.

Changing import settings blocks review/export in the tab until rediscovery. Rediscovery clears earlier decisions and manual pairs. Replacing either uploaded source also discards that session's project. Adding a manual pair preserves existing decisions because the source/settings/evidence are reverified first. Raw cell values never appear in the workspace or exports.

## Save and reopen

Save project downloads a metadata-only `atlasweave-project.json`. It does not contain the source files. To reopen it after restarting, select the same original files on the same left/right sides, then choose Open project. File bytes, original filenames, engine version, and evidence must match. Browser projects use `left/filename` and `right/filename` references and cannot request arbitrary filesystem paths.

CLI projects with arbitrary local paths are not accepted by the browser. Rediscover those files in the workspace. Version 0.1 projects require rediscovery under the 0.2 engine. The version 1 JSON format remains supported; `manual_pairs` is an optional additive field for new projects.

## Local session behavior

One server process has one workspace. Uploaded copies live in a private temporary directory, and decisions live in server memory. Clear workspace removes temporary uploads and decisions; it does not remove originals or downloaded files. Ctrl+C also cleans up uploads. A forced kill or machine crash may leave an OS temporary directory behind; there is no secure-erasure guarantee.

Tabs authenticate using a random process token stored in tab session storage. The URL fragment is removed after startup. Treat the launch URL as private. Revisions prevent an older tab from silently overwriting newer state; refresh a stale tab before continuing. Do not expose the server through a public tunnel or reverse proxy; this is a single-user local tool, not a hosted service.
