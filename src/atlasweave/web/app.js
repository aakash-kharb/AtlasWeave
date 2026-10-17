"use strict";

const $ = (id) => document.getElementById(id);
const node = (tag, text, className) => {
    const element = document.createElement(tag);
    if (text !== undefined && text !== null) element.textContent = text;
    if (className) element.className = className;
    return element;
};
let state = { sources: {}, project: null, revision: 0 };
let selected = null;
let dirty = false;
let ruleDirty = false;
let busy = false;
let exported = null;
let compared = new Set();
let messageTimer;
let token = new URLSearchParams(location.hash.slice(1)).get("token");
try {
    if (token) sessionStorage.setItem("atlasweave-token", token);
    else token = sessionStorage.getItem("atlasweave-token");
} catch {
    /* The launch URL still works when session storage is unavailable. */
}
if (location.hash.startsWith("#token="))
    history.replaceState(null, "", location.pathname);

async function api(path, payload, binary) {
    const headers = { "X-AtlasWeave-Token": token || "" };
    const options = { headers, cache: "no-store", credentials: "omit" };
    if (payload !== undefined || binary !== undefined) {
        options.method = "POST";
        headers["Content-Type"] =
            binary !== undefined
                ? "application/octet-stream"
                : "application/json";
        options.body =
            binary !== undefined
                ? binary
                : JSON.stringify({ ...payload, revision: state.revision });
    }
    let response;
    try {
        response = await fetch(`/api/${path}`, options);
    } catch {
        throw new Error(
            "The local workspace is disconnected. Start atlasweave serve and open its URL again.",
        );
    }
    const result = await response.json();
    if (!response.ok)
        throw new Error(result.error || "The request could not be completed.");
    return result;
}

function message(text) {
    clearTimeout(messageTimer);
    $("status-message").textContent = text;
    if (!busy)
        messageTimer = setTimeout(() => {
            $("status-message").textContent = "";
        }, 5000);
}

async function run(label, operation) {
    if (busy) return;
    busy = true;
    const focusId = document.activeElement?.id;
    document.querySelector(".app-shell").inert = true;
    document.body.setAttribute("aria-busy", "true");
    $("error-message").hidden = true;
    message(label);
    try {
        await operation();
        busy = false;
        message("Workspace up to date.");
    } catch (error) {
        $("status-message").textContent = "";
        $("error-message").replaceChildren(node("span", error.message));
        const dismiss = node("button", "Dismiss", "text-button");
        dismiss.addEventListener("click", () => {
            $("error-message").hidden = true;
        });
        $("error-message").append(dismiss);
        $("error-message").hidden = false;
    } finally {
        busy = false;
        document.querySelector(".app-shell").inert = false;
        document.body.removeAttribute("aria-busy");
        if (focusId && $(focusId) && !$(focusId).disabled)
            $(focusId).focus({ preventScroll: true });
    }
}

function sync(next, resetSettings = false) {
    state = next;
    dirty = false;
    ruleDirty = false;
    exported = null;
    const candidates = state.project?.candidates || [];
    if (!candidates.some((c) => c.id === selected))
        selected = candidates[0]?.id || null;
    compared = new Set(
        [...compared].filter((id) => candidates.some((c) => c.id === id)),
    );
    if (state.project) {
        const config = state.project.config;
        $("trim").checked = config.trim;
        $("casefold").checked = config.casefold;
        $("min-score").value = config.min_score;
        $("aliases").value = JSON.stringify(config.aliases);
        $("row-limit").value = state.project.sources.left.options.max_rows;
    } else if (resetSettings) {
        $("trim").checked = false;
        $("casefold").checked = false;
        $("min-score").value = "0.55";
        $("aliases").value = '{"cust_id":"Customer ID"}';
        $("row-limit").value = "10000";
        for (const side of ["left", "right"]) {
            $(`${side}-header`).value = 1;
            $(`${side}-delimiter`).value = ",";
        }
    }
    render();
}

function field(side, id) {
    return state.project.profiles[side].find((profile) => profile.id === id);
}

function selectionLabel(candidate) {
    return `${field("left", candidate.left_field).name} → ${field("right", candidate.right_field).name}`;
}

function renderSources() {
    for (const side of ["left", "right"]) {
        const source = state.sources[side];
        const select = $(`${side}-sheet`);
        const sourceKey = source
            ? `${source.name}:${source.bytes}:${source.sheets.join("|")}`
            : "";
        if (select.dataset.source !== sourceKey) {
            select.replaceChildren();
            for (const sheet of source?.sheets || [])
                select.append(new Option(sheet, sheet));
            select.dataset.source = sourceKey;
            $(`${side}-header`).value = 1;
            $(`${side}-delimiter`).value = ",";
        }
        $(`${side}-options`).hidden = !source;
        $(`${side}-sheet-label`).hidden = source?.format !== "xlsx";
        $(`${side}-delimiter-label`).hidden = source?.format === "xlsx";
        $(`${side}-format`).textContent = source
            ? source.format.toUpperCase()
            : side === "left"
              ? "INPUT"
              : "LOOKUP";
        $(`${side}-name`).textContent =
            source?.name ||
            (side === "left"
                ? "The records you start with"
                : "The context you connect to");
        const measured = state.project?.sources[side];
        $(`${side}-description`).textContent = measured
            ? `${measured.row_count.toLocaleString()} rows · ${state.project.profiles[side].length} fields · ${measured.complete ? "Full scan" : "Partial scan"}`
            : source
              ? `${(source.bytes / 1024).toFixed(1)} KiB · Ready to discover`
              : side === "left"
                ? "Orders, transactions, or the rows you want to keep."
                : "Customers, products, or a reference table.";
        if (measured && !dirty) {
            select.value =
                measured.options.sheet || select.options[0]?.value || "";
            $(`${side}-header`).value = measured.options.header_row;
            $(`${side}-delimiter`).value = measured.options.delimiter;
        }
    }
}

function render() {
    const project = state.project;
    const candidates = project?.candidates || [];
    const approved = candidates.filter((c) => c.status === "approved").length;
    const count = Object.keys(state.sources).length;
    renderSources();
    $("version").textContent = `v${state.version || "0.2"}`;
    $("summary-files").textContent = count;
    $("summary-candidates").textContent = candidates.length;
    $("summary-approved").textContent = approved;
    $("nav-source-count").textContent = count;
    $("nav-candidate-count").textContent = candidates.length;
    $("relationship-count").textContent = candidates.length;
    $("discover-button").disabled = count !== 2;
    $("discover-button").firstChild.textContent = project
        ? "Run discovery again "
        : "Discover relationships ";
    $("restore-button").disabled = count !== 2;
    $("save-project").disabled = !project || dirty;
    $("prepare-export").disabled = !approved || dirty;
    $("dirty-notice").hidden = !dirty;
    $("empty-review").hidden = !!project;
    $("review-workspace").hidden = !project;
    $("export-panel").hidden = !exported;
    $("source-warnings").replaceChildren();
    for (const side of ["left", "right"]) {
        const source = project?.sources[side];
        if (!source) continue;
        if (!source.complete)
            $("source-warnings").append(
                node(
                    "p",
                    `${side === "left" ? "Left" : "Right"} source: partial scan. Increase the row limit and rediscover before approval.`,
                    "warning",
                ),
            );
        for (const warning of source.warnings)
            $("source-warnings").append(
                node("p", `${source.name}: ${warning}`, "warning"),
            );
    }
    $("handoff-description").textContent = dirty
        ? "Rediscover after changing settings before preparing a handoff."
        : approved
          ? `${approved} approved ${approved === 1 ? "relationship is" : "relationships are"} ready. Your agent receives the rules and supporting evidence.`
          : "Approve a relationship to create your mapping specification and agent brief.";
    if (project) {
        for (const side of ["left", "right"]) {
            const select = $(`manual-${side}`);
            const previous = select.value;
            select.replaceChildren(
                ...project.profiles[side].map(
                    (p) => new Option(`${p.name} · ${p.kind}`, p.id),
                ),
            );
            if ([...select.options].some((option) => option.value === previous))
                select.value = previous;
        }
        $("manual-button").disabled = dirty;
        renderCandidates();
        renderDetail();
    }
}

function renderCandidates() {
    const query = $("search").value.toLocaleLowerCase();
    const status = $("status-filter").value;
    const candidates = state.project.candidates.filter(
        (c) =>
            (status === "all" || c.status === status) &&
            `${selectionLabel(c)} ${c.id}`.toLocaleLowerCase().includes(query),
    );
    if (!candidates.some((c) => c.id === selected))
        selected = candidates[0]?.id || null;
    $("candidate-list").replaceChildren();
    for (const candidate of candidates) {
        const row = node(
            "div",
            null,
            `candidate-row${candidate.id === selected ? " selected" : ""}`,
        );
        const checkbox = node("input");
        checkbox.type = "checkbox";
        checkbox.id = `compare-${candidate.id}`;
        checkbox.checked = compared.has(candidate.id);
        checkbox.disabled = !checkbox.checked && compared.size >= 3;
        checkbox.setAttribute(
            "aria-label",
            `Compare ${selectionLabel(candidate)}`,
        );
        checkbox.addEventListener("change", () => {
            if (checkbox.checked) compared.add(candidate.id);
            else compared.delete(candidate.id);
            renderCandidates();
            $(checkbox.id)?.focus({ preventScroll: true });
        });
        const button = node("button", null, "candidate-select");
        button.id = `candidate-${candidate.id}`;
        button.setAttribute("aria-pressed", String(candidate.id === selected));
        const names = node("span", null, "candidate-fields");
        names.append(
            node("span", field("left", candidate.left_field).name),
            node("span", "→"),
            node("span", field("right", candidate.right_field).name),
        );
        const meta = node("span", null, "candidate-meta");
        meta.append(
            node("span", candidate.status, `status-tag ${candidate.status}`),
        );
        const isManual = state.project.manual_pairs?.some(
            (p) =>
                p.left_field === candidate.left_field &&
                p.right_field === candidate.right_field,
        );
        meta.append(
            node(
                "span",
                isManual ? "Manual pair" : candidate.evidence.cardinality,
            ),
        );
        meta.append(
            node(
                "span",
                `Score ${candidate.score.toFixed(2)}`,
                "candidate-score",
            ),
        );
        button.append(names, meta);
        button.addEventListener("click", () => {
            selected = candidate.id;
            renderCandidates();
            renderDetail();
            $(button.id)?.focus({ preventScroll: true });
        });
        row.append(checkbox, button);
        $("candidate-list").append(row);
    }
    if (!candidates.length)
        $("candidate-list").append(
            node(
                "p",
                state.project.candidates.length
                    ? "No relationships match this filter."
                    : "No suggestions met the threshold. Inspect a manual field pair below or adjust matching settings.",
                "notice",
            ),
        );
    $("compare-button").textContent = `Compare (${compared.size})`;
    $("compare-button").disabled = compared.size < 2;
}

function renderDetail() {
    ruleDirty = false;
    $("prepare-export").disabled =
        dirty || !state.project.candidates.some((c) => c.status === "approved");
    $("save-project").disabled = dirty;
    const detail = $("candidate-detail");
    detail.replaceChildren();
    const candidate = state.project.candidates.find((c) => c.id === selected);
    if (!candidate) {
        detail.append(
            node(
                "p",
                "Select a relationship to explore its evidence.",
                "detail-content",
            ),
        );
        return;
    }
    const evidence = candidate.evidence;
    const header = node("div", null, "detail-header");
    header.append(
        node("h3", "A closer look"),
        node(
            "span",
            candidate.scope === "full" ? "FULL SCAN" : "PARTIAL SCAN",
            "pill",
        ),
    );
    const content = node("div", null, "detail-content");
    const diagram = node("div", null, "relationship-diagram");
    for (const side of ["left", "right"]) {
        const box = node("div", null, "field-node");
        box.append(
            node("small", state.sources[side].name),
            node("strong", field(side, candidate[`${side}_field`]).name),
        );
        if (side === "right")
            diagram.append(node("span", "→", "connection-line"));
        diagram.append(box);
    }
    const metrics = node("div", null, "metrics");
    for (const [value, label] of [
        [evidence.shared_distinct, "shared distinct keys"],
        [evidence.unmatched_left_rows, "unmatched left rows"],
        [evidence.left_join_rows, "rows in a left join"],
    ]) {
        const metric = node("div", null, "metric");
        metric.append(
            node("strong", value.toLocaleString()),
            node("span", label),
        );
        metrics.append(metric);
    }
    const table = node("table", null, "evidence-table");
    table.setAttribute("aria-label", "Join evidence");
    const body = node("tbody");
    for (const [label, value] of [
        ["Observed relationship", evidence.cardinality],
        [
            "Duplicate excess rows · left / right",
            `${evidence.left_duplicates} / ${evidence.right_duplicates}`,
        ],
        [
            "Null keys · left / right",
            `${evidence.left_nulls} / ${evidence.right_nulls}`,
        ],
        ["Unmatched right rows", evidence.unmatched_right_rows],
        ["Rows in an inner join", evidence.inner_join_rows],
    ]) {
        const row = node("tr");
        const labelCell = node("th", label);
        labelCell.scope = "row";
        row.append(labelCell, node("td", value));
        body.append(row);
    }
    table.append(body);
    const scores = node("div", null, "scores");
    const labels = {
        name: "Name & aliases",
        type: "Type compatibility",
        overlap: "Value overlap",
        uniqueness: "Right-key uniqueness",
    };
    for (const [key, value] of Object.entries(candidate.scores)) {
        const row = node("div", null, "score-line");
        const progress = node("progress");
        progress.max = 1;
        progress.value = value;
        progress.setAttribute("aria-label", labels[key]);
        row.append(
            node("span", labels[key]),
            node("span", value.toFixed(2)),
            progress,
        );
        scores.append(row);
    }
    const rules = candidate.rules || {
        join: "left",
        require_unique_right: true,
        require_non_null_right: true,
    };
    const controls = node("div", null, "join-controls");
    const joinLabel = node("label", "When connecting rows");
    const join = node("select");
    join.id = "join-type";
    join.append(
        new Option("Keep every left row", "left"),
        new Option("Keep matching rows only", "inner"),
    );
    join.value = rules.join;
    joinLabel.append(join);
    const duplicateLabel = node("label", null, "checkbox-label");
    const duplicate = node("input");
    duplicate.type = "checkbox";
    duplicate.id = "allow-duplicates";
    duplicate.checked = !rules.require_unique_right;
    duplicateLabel.append(
        duplicate,
        node("span", "Allow duplicate right keys (can multiply rows)"),
    );
    const nullLabel = node("label", null, "checkbox-label");
    const nulls = node("input");
    nulls.type = "checkbox";
    nulls.id = "allow-nulls";
    nulls.checked = !rules.require_non_null_right;
    nullLabel.append(
        nulls,
        node("span", "Allow null right keys (nulls never match)"),
    );
    controls.append(joinLabel, duplicateLabel, nullLabel);
    const actions = node("div", null, "review-actions");
    const approve = node(
        "button",
        candidate.status === "approved"
            ? "Update approval ✓"
            : "Approve mapping ✓",
        "button primary",
    );
    approve.id = "approve-mapping";
    const reject = node("button", "Reject", "button secondary");
    reject.id = "reject-mapping";
    const reset = node("button", "Reset", "text-button");
    reset.id = "reset-mapping";
    const reason = node("p", null, "helper");
    const checkRules = () => {
        ruleDirty =
            candidate.status === "approved" &&
            (join.value !== rules.join ||
                duplicate.checked === rules.require_unique_right ||
                nulls.checked === rules.require_non_null_right);
        if (ruleDirty) {
            exported = null;
            $("export-panel").hidden = true;
        }
        $("prepare-export").disabled =
            dirty ||
            ruleDirty ||
            !state.project.candidates.some((c) => c.status === "approved");
        $("save-project").disabled = dirty || ruleDirty;
        const blocked = dirty
            ? "Rediscover changed settings before reviewing."
            : candidate.scope !== "full"
              ? "A partial scan cannot be approved. Increase the row limit."
              : !evidence.shared_distinct
                ? "No shared values. This pair cannot be approved as a join."
                : evidence.right_duplicates && !duplicate.checked
                  ? "Right keys contain duplicates. Review the row counts before allowing them."
                  : evidence.right_nulls && !nulls.checked
                    ? "Right keys contain nulls. Choose explicitly whether to allow them."
                    : ruleDirty
                      ? "Join rules changed. Update approval before saving or exporting."
                      : "Approval records these join rules. Source data is never modified.";
        approve.disabled =
            dirty ||
            candidate.scope !== "full" ||
            !evidence.shared_distinct ||
            (evidence.right_duplicates > 0 && !duplicate.checked) ||
            (evidence.right_nulls > 0 && !nulls.checked);
        reject.disabled = dirty;
        reset.disabled = dirty;
        reason.textContent = blocked;
    };
    join.addEventListener("change", checkRules);
    duplicate.addEventListener("change", checkRules);
    nulls.addEventListener("change", checkRules);
    checkRules();
    const review = (status) =>
        run("Rechecking the evidence…", async () => {
            sync(
                await api("review", {
                    candidate: candidate.id,
                    status,
                    rules: {
                        join: join.value,
                        require_unique_right: !duplicate.checked,
                        require_non_null_right: !nulls.checked,
                    },
                }),
            );
        });
    approve.addEventListener("click", () => review("approved"));
    reject.addEventListener("click", () => review("rejected"));
    reset.addEventListener("click", () => review("pending"));
    actions.append(approve, reject, reset);
    content.append(diagram, metrics, table, scores, controls, reason, actions);
    detail.append(header, content);
}

function download(name, data, mime) {
    const url = URL.createObjectURL(new Blob([data], { type: mime }));
    const anchor = node("a");
    anchor.href = url;
    anchor.download = name;
    document.body.append(anchor);
    anchor.click();
    anchor.remove();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
}

async function upload(side, file) {
    if (!file) return;
    if (!/\.(csv|xlsx)$/i.test(file.name))
        throw new Error("Choose a CSV or XLSX file.");
    if (file.size > 32 * 1024 * 1024)
        throw new Error("This file exceeds the 32 MiB limit.");
    const query = new URLSearchParams({
        side,
        name: file.name,
        revision: state.revision,
    });
    sync(await api(`upload?${query}`, undefined, file));
}

for (const side of ["left", "right"]) {
    $(`${side}-file`).addEventListener("change", (event) => {
        const file = event.target.files[0];
        event.target.value = "";
        if (file) run("Reading your local file…", () => upload(side, file));
    });
    const card = $(`${side}-card`);
    card.addEventListener("dragover", (event) => {
        event.preventDefault();
        card.classList.add("dragover");
    });
    card.addEventListener("dragleave", () => card.classList.remove("dragover"));
    card.addEventListener("drop", (event) => {
        event.preventDefault();
        card.classList.remove("dragover");
        run("Reading your local file…", async () => {
            if (event.dataTransfer.files.length !== 1)
                throw new Error("Choose one file for each source.");
            await upload(side, event.dataTransfer.files[0]);
        });
    });
}

document.querySelectorAll(".import-setting").forEach((input) =>
    input.addEventListener("input", () => {
        dirty = !!state.project;
        exported = null;
        $("dirty-notice").hidden = !dirty;
        $("export-panel").hidden = true;
        $("save-project").disabled = !state.project || dirty;
        $("prepare-export").disabled = true;
        $("manual-button").disabled = dirty;
        if (state.project) renderDetail();
    }),
);

$("discover-button").addEventListener("click", () =>
    run("Profiling files and comparing fields…", async () => {
        for (const input of document.querySelectorAll(".import-setting")) {
            if (!input.checkValidity())
                throw new Error(
                    "Check the highlighted import settings and numeric limits.",
                );
        }
        let aliases;
        try {
            aliases = JSON.parse($("aliases").value);
        } catch {
            throw new Error(
                'Aliases must be valid JSON, for example {"cust_id":"Customer ID"}.',
            );
        }
        const payload = {
            config: {
                ...(state.project?.config || {}),
                aliases,
                trim: $("trim").checked,
                casefold: $("casefold").checked,
                min_score: Number($("min-score").value),
            },
        };
        for (const side of ["left", "right"])
            payload[`${side}_options`] = {
                sheet:
                    state.sources[side].format === "xlsx"
                        ? $(`${side}-sheet`).value
                        : null,
                delimiter: $(`${side}-delimiter`).value,
                header_row: Number($(`${side}-header`).value),
                max_rows: Number($("row-limit").value),
            };
        sync(await api("discover", payload));
        $("relationships").scrollIntoView({ block: "start" });
    }),
);

$("demo-button").addEventListener("click", () => {
    if (
        Object.keys(state.sources).length &&
        !confirm(
            "Replace this workspace with the synthetic sample? Save your project first if you want to reopen it.",
        )
    )
        return;
    run("Opening the sample workspace…", async () => {
        $("search").value = "";
        $("status-filter").value = "all";
        sync(await api("demo", {}), true);
    });
});
$("search").addEventListener("input", () => {
    renderCandidates();
    renderDetail();
});
$("status-filter").addEventListener("change", () => {
    renderCandidates();
    renderDetail();
});
$("manual-button").addEventListener("click", () =>
    run("Inspecting your field pair…", async () => {
        const left = $("manual-left").value,
            right = $("manual-right").value;
        selected = `left.${left}--right.${right}`;
        $("search").value = "";
        $("status-filter").value = "all";
        sync(await api("manual", { left_field: left, right_field: right }));
    }),
);

$("compare-button").addEventListener("click", () => {
    const candidates = state.project.candidates.filter((c) =>
        compared.has(c.id),
    );
    const table = node("table", null, "comparison-table");
    const head = node("thead"),
        row = node("tr");
    row.append(node("th", "Evidence"));
    for (const candidate of candidates)
        row.append(node("th", selectionLabel(candidate)));
    head.append(row);
    const body = node("tbody");
    const values = [
        ["Status", (c) => c.status],
        ["Scan", (c) => c.scope],
        ["Ranking score", (c) => c.score.toFixed(3)],
        ["Shared distinct keys", (c) => c.evidence.shared_distinct],
        ["Unmatched left rows", (c) => c.evidence.unmatched_left_rows],
        ["Right duplicate rows", (c) => c.evidence.right_duplicates],
        ["Right nulls", (c) => c.evidence.right_nulls],
        ["Projected left-join rows", (c) => c.evidence.left_join_rows],
        ["Projected inner-join rows", (c) => c.evidence.inner_join_rows],
    ];
    for (const [label, get] of values) {
        const row = node("tr"),
            heading = node("th", label);
        heading.scope = "row";
        row.append(heading);
        for (const candidate of candidates)
            row.append(node("td", get(candidate)));
        body.append(row);
    }
    table.append(head, body);
    $("comparison-content").replaceChildren(table);
    $("compare-dialog").showModal();
});
$("close-compare").addEventListener("click", () => $("compare-dialog").close());

$("prepare-export").addEventListener("click", () =>
    run("Verifying approved mappings…", async () => {
        exported = await api("export", {});
        $("brief-preview").value = exported.brief;
        $("export-panel").hidden = false;
        $("export-panel").scrollIntoView({ block: "start" });
    }),
);
$("download-mapping").addEventListener("click", () => {
    if (exported)
        download(
            "mapping.json",
            JSON.stringify(exported.mapping, null, 2) + "\n",
            "application/json",
        );
});
$("download-brief").addEventListener("click", () => {
    if (exported) download("agent-brief.md", exported.brief, "text/markdown");
});
$("save-project").addEventListener("click", () =>
    run("Verifying project before saving…", async () => {
        const result = await api("save", {});
        download(
            "atlasweave-project.json",
            result.document + "\n",
            "application/json",
        );
    }),
);
$("restore-button").addEventListener("click", () => $("restore-input").click());
$("restore-input").addEventListener("change", (event) => {
    const file = event.target.files[0];
    event.target.value = "";
    if (!file) return;
    run("Checking the saved project against your files…", async () => {
        if (file.size > 16 * 1024 * 1024)
            throw new Error("Saved project exceeds 16 MiB.");
        const document = await file.text();
        try {
            JSON.parse(document);
        } catch {
            throw new Error("Choose a valid AtlasWeave project JSON file.");
        }
        sync(await api("restore", { document }));
    });
});
$("clear-button").addEventListener("click", () => {
    if (
        !confirm(
            "Remove this session’s uploaded copies and decisions? Downloaded files are kept.",
        )
    )
        return;
    run("Clearing local session files…", async () => {
        compared.clear();
        sync(await api("clear", {}), true);
    });
});

run("Connecting to your local workspace…", async () =>
    sync(await api("state")),
);
