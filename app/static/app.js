"use strict";

// Stage names and prompts follow references/protocol.md ("Stage prompts for the solve protocol").
const STAGES = [
  ["Unknown, data, condition", "What is the unknown, what is given, and what must hold? Restate it in one sentence. Predict the output for two or three inputs, at least one of them an edge case (empty, one element, duplicates, negatives)."],
  ["Brute force on the grid", "What is every candidate answer? How would you check one?"],
  ["Count", "How many times does the innermost line run? What does one run cost? Is that fast enough for these constraints?"],
  ["Find the repeated work", "What does the brute force recompute? Which candidates can you prove are useless?"],
  ["Classify and choose the state", "Have you seen a problem with the same unknown? Which pattern, what in the problem made you think of it, and which datum does it rely on? What do add, remove and check cost?"],
  ["Plan card", "Fill in the plan card, including what it relies on and when it breaks, then trace one example by hand."],
  ["Pseudocode, then code", "Write the subgoal comments first, then the code under each one. Does each step keep the invariant?"],
  ["Test and look back", "Trace the edge case as if there's a bug, run the tests, then answer the three questions below."],
];
const PLAN_FIELDS = ["State", "Invariant", "Relies on", "Breaks if", "Termination", "Complexity", "Hand trace"];
const LOOK_BACK = ["Why it works, in one sentence",
  "Time and space complexity, and why",
  "One more question: another approach and its trade-off, a changed constraint and what it breaks, or another problem this method solves"];

const $ = (id) => document.getElementById(id);
const elem = (tag, text = "") => Object.assign(document.createElement(tag), {textContent: text});
let state = null;        // the last /api/state
let attempt = null;      // the last /api/attempt: {file, path, text, mtime, plan_card, examples, examples_error}
let problemText = null;  // problems/<slug>/problem.md, or null before it's fetched or pasted
let fetchState = null;   // the statement fetch for this solve: null, "fetching", or {error}
let view = null;         // the stage shown in the panel
let lastStage = null;    // the live stage at the previous poll
let editor = null;       // CodeMirror, or null when the CDN didn't load and the textarea is used
let dirty = false;       // the editor has code that isn't in the file
let panelDirty = false;  // the stage's boxes have text that isn't saved (an unsaved statement: statementDraft)
let savePanel = null;    // saves the panel shown: its parts of the attempt file, then its stage note
let focusNext = false;   // after Done: focus the next stage's first box once it's drawn
let barFile = null;      // the solve the bar's problem link and stage buttons were built for
let lastPick = null;     // the start screen's pick when the slug box was last filled from it
let companionProblem = null; // offered by the browser panel; never starts or replaces a solve
const shownOnce = {};     // once() falls back to this when sessionStorage is blocked
let lastTouch = 0;       // when the page last told the server he was active
let finishSent = null;   // the solve whose stage-8 finish prompt was copied: the coach logs it from the chat
let warnedMtime = null;  // the disk mtime we already warned about
let busy = false;        // a refresh is running
let activeSession = null; // identity captured when the active mutation was enqueued
let editGeneration = 0, panelGeneration = 0, settingCode = false;
let chain = Promise.resolve();  // the page's state changes (its POSTs and PUTs), one at a time, in click order
let pending = 0;         // state changes waiting or in flight
let finished = 0;        // state changes done: a poll that was out while one finished may predate it
let tab = "stage";       // the left pane's tab: "desc", "stage" or "notes"
let consoleTab = "cases"; // the console's tab: "cases" or "results"
let askCoach = null;     // the shown stage's "Ask coach": saves it, then copies the prompt
let lastRun = null;      // the last /api/run result, and the case selected in it
let selectedCase = 0;
let notesDrawn = null;   // what the Notes tab was last drawn from, so a poll doesn't redraw it for nothing
const openedFolds = new Set();  // the folds he opened in this solve: they stay open across saves and polls

// --- plumbing ----------------------------------------------------------------
async function api(method, path, body) {
  const scoped = path.startsWith("/api/attempt") || path === "/api/run" ||
    (path.startsWith("/api/solve/") && path !== "/api/solve/start");
  if (scoped) {
    const identity = activeSession || attempt?.session_id || state?.live?.session_id;
    if (method === "GET") {
      if (!path.includes("session_id=")) path += (path.includes("?") ? "&" : "?") + "session_id=" + encodeURIComponent(identity || "");
    } else body = {...body, session_id: identity};
  }
  let res;
  try {
    res = await fetch(path, {
      method,
      headers: {"X-DSA-Coach": "1", "Content-Type": "application/json"},
      body: body === undefined ? undefined : JSON.stringify(body),
    });
  } catch {
    const err = new Error("the server isn't answering");
    err.offline = true;
    throw err;
  }
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    const err = new Error(data.error || `${res.status} ${res.statusText}`);
    err.status = res.status; err.data = data;
    err.staleSession = !!data.stale_session;
    err.gone = res.status === 404 && err.message.startsWith("no live solve");
    throw err;
  }
  return data;
}

function closeButton(box) {
  const close = button("×", () => { box.hidden = true; });
  close.className = "close";
  close.setAttribute("aria-label", "Dismiss");
  return close;
}

// text is plain text; code, if given, follows it as a snippet to copy.
// kind: "solve" for a banner whose buttons act on the live solve, "offline" while the server isn't answering
function banner(text, actions = [], kind = "", code = "") {
  const el = $("banner");
  const span = elem("span", text);
  if (code) span.append(" ", elem("code", code));
  el.replaceChildren(span, ...actions.map(([label, fn]) => button(label, () => { el.hidden = true; return change(fn); })),
    closeButton(el));
  el.dataset.kind = kind;
  el.hidden = false;
}

function fail(e) {
  if (e.staleSession) {
    persistDraft();
    banner("That solve ended or changed. Your unsaved work is kept for recovery; the action was not replayed.");
    refresh();
    return;
  }
  if (e.gone) { solveGone(); refresh(); }
  if (e.shown) return;
  if (e.offline) banner("The app's server isn't answering. Check that this still runs in a terminal:", [], "offline", "python3 app/server.py");
  else banner(e.message);
}

// changes: the click sends a POST or PUT, so it goes through change()
function button(label, fn, changes = false) {
  const b = elem("button", label);
  b.onclick = changes ? () => change(fn, b) : () => Promise.resolve().then(fn).catch(fail);
  return b;
}

// One state change at a time: a click that changes something waits for the one before it, and its button
// stays disabled until it's done. Polling goes on meanwhile.
function change(fn, btn) {
  pending++;
  if (btn) btn.disabled = true;
  const identity = state?.live?.session_id || null;
  const run = chain.then(async () => {
    if (identity && identity !== state?.live?.session_id) throw staleSessionError();
    activeSession = identity;
    try { return await fn(); } finally { activeSession = null; }
  }).catch(fail).finally(() => {
    pending--;
    finished++;
    if (btn) { btn.disabled = false; if (btn.gate) btn.gate(); }
    gateStart();  // Start waits for every change, not only its own
  });
  chain = run;
  return run;
}

function labelled(parent, label, control) {
  const l = elem("label", label);
  l.append(control);
  parent.append(l);
  return control;
}

function field(parent, label, value, multiline, name) {
  const input = document.createElement(multiline ? "textarea" : "input");
  if (multiline) input.rows = 3;
  input.setAttribute("autocomplete", "off");
  input.value = value || "";
  if (name) input.dataset.draftField = name;
  return labelled(parent, label, input);
}

async function copyPrompt(text, copied = "Copied. Paste it into the coach chat:") {
  if (typeof companionEnabled !== "undefined" && companionEnabled) return companionAsk(text);
  try {
    await navigator.clipboard.writeText(text);
    banner(copied, [], "", text);
  } catch {  // no clipboard, or Safari's, which refuses a copy that comes after the saves
    banner("Copy this into the coach chat:", [], "", text);
  }
}

// --- editor and the attempt file ---------------------------------------------
function setupEditor() {
  if (window.CodeMirror) {
    $("editor-host").innerHTML = "";
    editor = CodeMirror($("editor-host"), {
      mode: "python", lineNumbers: true, indentUnit: 4, tabSize: 4, indentWithTabs: false,
      extraKeys: {
        Tab: (cm) => cm.execCommand(cm.somethingSelected() ? "indentMore" : "insertSoftTab"),
        "Shift-Tab": "indentLess",
      },
    });
    editor.on("change", () => markDirty(true));
  } else {
    const ta = $("editor-fallback");
    ta.addEventListener("input", () => markDirty(true));
    ta.addEventListener("keydown", (e) => {  // Tab indents, as in the editor, rather than leaving the box
      if (e.key !== "Tab" || e.shiftKey || e.altKey || e.ctrlKey || e.metaKey) return;
      e.preventDefault();
      if (!document.execCommand("insertText", false, "    ")) {  // insertText keeps undo, and fires input
        ta.setRangeText("    ", ta.selectionStart, ta.selectionEnd, "end");
        markDirty(true);
      }
    });
  }
  $("save-btn").onclick = () => change(save, $("save-btn"));
}

// Cmd-S or Ctrl-S anywhere saves the code, rather than opening the browser's Save dialog. In the stage panel it
// saves what he typed there too.
function saveKey(e) {
  if (!(e.metaKey || e.ctrlKey) || e.altKey || String(e.key).toLowerCase() !== "s") return;
  e.preventDefault();
  if (!attempt) return;
  const inPanel = $("panel").contains(e.target);
  change(async () => {
    if (!inPanel) return save();
    if (dirty && !(await save())) return;
    if (savePanel) await savePanel();
  }, $("save-btn"));
}
const getCode = () => (editor ? editor.getValue() : $("editor-fallback").value);
function setCode(text) {
  settingCode = true;
  if (getCode() !== text) {  // the same text: keep the cursor and the folds where they are
    if (editor) { editor.setValue(text); applyFolds(); } else $("editor-fallback").value = text;
  }
  settingCode = false;
  markDirty(false);
}
function markDirty(d) {
  dirty = d;
  if (d && !settingCode) { editGeneration++; scheduleDraft(); }
  $("dirty").textContent = d ? "Code not saved" : "Code saved";
  $("run-btn").dataset.unsaved = d ? "1" : "";
}

// The parts of the attempt file he doesn't need while coding fold away on load: the docstring with the plan card,
// EXAMPLES with the comment above it, and the run block. They stay in the file, one click from opening.
function foldRanges(text) {
  const lines = text.split("\n"), r = {};
  const q = (lines[0] || "").trim().slice(0, 3);
  if ((q === '"""' || q === "'''") && !lines[0].trim().slice(3).includes(q)) {
    const end = lines.findIndex((l, i) => i > 0 && l.includes(q));
    if (end > 0) r.plan = [0, end];
  }
  const ex = lines.findIndex((l) => /^EXAMPLES\s*=/.test(l));
  if (ex >= 0) {
    let s = ex, e = ex;
    while (s > 0 && lines[s - 1].startsWith("#")) s--;
    if (!/\]\s*$/.test(lines[ex])) { e = ex + 1; while (e < lines.length && !/^\]/.test(lines[e])) e++; }
    if (e < lines.length) r.examples = [s, e];
  }
  const run = lines.findIndex((l) => /^if __name__ == ["']__main__["']\s*:/.test(l));
  if (run >= 0) {
    let e = lines.length - 1;
    while (e > run && !lines[e].trim()) e--;
    r.run = [run, e];
  }
  return r;
}
let refolding = false;
function applyFolds() {
  if (!editor) return;
  refolding = true;
  for (const m of editor.getAllMarks()) if (m.foldKind) m.clear();
  refolding = false;
  const n = attempt?.examples && !attempt.examples_error ? ` (${attempt.examples.length})` : "";
  const labels = {plan: "Plan card", examples: `EXAMPLES${n}`, run: "run block"};
  for (const [kind, [s, e]] of Object.entries(foldRanges(editor.getValue()))) {
    if (openedFolds.has(kind)) continue;
    const w = elem("span", `▸ ${labels[kind]}`);
    w.className = "fold";
    w.title = "Click to open";
    const mark = editor.markText({line: s, ch: 0}, {line: e, ch: editor.getLine(e).length},
      {replacedWith: w, clearOnEnter: true, handleMouseEvents: false});
    mark.foldKind = kind;
    mark.on("clear", () => { if (!refolding) openedFolds.add(kind); });
    w.addEventListener("mousedown", (ev) => { ev.preventDefault(); mark.clear(); editor.focus(); });
  }
}

function staleSessionError() {
  const e = new Error("the solve changed; refresh before trying again");
  e.staleSession = true;
  return e;
}
function useAttempt(a) {
  if (a.session_id !== state?.live?.session_id) throw staleSessionError();
  const another = !attempt || attempt.file !== a.file;
  const examplesBefore = attempt && JSON.stringify([attempt.examples, attempt.examples_error]);
  attempt = a;
  warnedMtime = null;
  if (another) openedFolds.clear();
  setCode(a.text);
  if (another && editor) editor.clearHistory();  // so undo can't bring back another solve's code
  $("problem").title = a.path;
  if (another || examplesBefore !== JSON.stringify([a.examples, a.examples_error])) renderCases();
}

// The live solve went away: ended from the chat, or replaced by another one. Unsaved code and stage text aren't
// dropped silently.
function solveGone() {
  persistDraft();
  draftData = null;
  recoveryPending = false;
  const fields = attempt && panelDirty ? panelFields() : "";
  if ($("banner").dataset.kind === "solve") $("banner").hidden = true;  // its buttons were for that solve
  if (attempt && (dirty || fields)) rescue(dirty ? getCode() : "", fields);
  else if (attempt && finishSent === attempt.file) banner("The coach logged the solve.");
  attempt = problemText = fetchState = view = lastStage = warnedMtime = savePanel = finishSent = null;
  askCoach = lastRun = notesDrawn = null;
  panelDirty = focusNext = false;
  tab = "stage";
  // nothing of that solve may stay on screen to act on the next one, or to be typed into while it loads
  for (const id of ["panel", "desc", "notes", "cases", "results"]) $(id).innerHTML = "";
  setCode("");
  $("problem").title = "";
}

// The stage's boxes as text, each under its label, for the rescue: the panel goes, and what's typed there with it
function panelFields() {
  const panel = $("panel"), out = [];
  for (const l of panel.querySelectorAll("label")) {
    const c = l.querySelector("input, textarea, select");
    if (c && c.value.trim()) out.push(`${l.firstChild.textContent.trim()}:\n${c.value.trim()}`);
  }
  const rows = [...panel.querySelectorAll("table.examples tr")].slice(1)
    .map((tr) => [tr.querySelector(".args").value.trim(), tr.querySelector(".expected").value.trim(), tr.querySelector(".edge").checked])
    .filter(([args, expected]) => args || expected)
    .map(([args, expected, edge]) => `${args} -> ${expected}${edge ? "  (edge)" : ""}`);
  if (rows.length) out.push(`Examples:\n${rows.join("\n")}`);
  return out.length ? `Stage ${view}, not saved:\n\n${out.join("\n\n")}` : "";
}

// code: the editor's unsaved code, or ""; fields: the panel's unsaved text (panelFields), or ""
function rescue(code, fields) {
  const el = $("rescue");
  const all = fields ? (code ? code.replace(/\n*$/, "\n\n") : "") + fields : code;
  const what = fields ? "What you hadn't saved" : "Your unsaved code";
  const text = elem("span", `The solve ended (from the chat?). ${what} isn't in any file.`);
  const copy = button(fields ? "Copy what I hadn't saved" : "Copy my code", async () => {
    try {
      await navigator.clipboard.writeText(all);
      text.textContent = `The solve ended (from the chat?). ${what} isn't in any file; it's on the clipboard now.`;
    } catch {
      if (!el.querySelector("textarea")) {
        const ta = document.createElement("textarea");
        ta.readOnly = true;
        ta.rows = 10;
        ta.value = all;
        ta.setAttribute("aria-label", what);
        el.append(ta);
      }
      el.querySelector("textarea").select();
      text.textContent = `The solve ended (from the chat?). The clipboard isn't available: copy ${what.toLowerCase()} from the box below.`;
    }
  });
  el.replaceChildren(text, copy, closeButton(el));
  el.hidden = false;
}

const isConflict = (e) => e.status === 409 && typeof e.data.text === "string" && e.data.mtime != null;

function conflict(disk) {
  warnedMtime = disk.mtime;
  banner("The attempt file changed on disk (the coach or another editor saved it) while you had unsaved edits.", [
    ["Load the disk version (drops my edits)", async () => { useAttempt(disk); if (redrawForFile()) renderPanel(); }],
    ["Keep mine (overwrite the file)", async () => {
      const generation = editGeneration;
      acceptSavedAttempt(await api("PUT", "/api/attempt", {text: getCode(), force: true, revision: attempt.revision}), generation);
    }],
  ], "solve");
}

async function save() {
  if (!attempt) return true;
  try {
    const generation = editGeneration;
    const saved = await api("PUT", "/api/attempt", {text: getCode(), revision: attempt.revision});
    acceptSavedAttempt(saved, generation);
    return true;
  } catch (e) {
    if (isConflict(e)) conflict(e.data); else fail(e);
    return false;
  }
}

// parts: only what he changed in the panel, so edits made in the editor to the rest survive. The editor's code is
// saved first, since the parts are written into the file on disk.
async function saveParts(parts) {
  if (dirty && !(await save())) {
    const e = new Error("not saved"); e.shown = true; throw e;
  }
  if (!attempt || !Object.keys(parts).length) return;  // the solve ended meanwhile, or nothing changed
  try {
    const generation = editGeneration;
    acceptSavedAttempt(await api("PUT", "/api/attempt/parts", {...parts, revision: attempt.revision}), generation);
  } catch (e) {
    if (isConflict(e)) { conflict(e.data); e.shown = true; }
    throw e;
  }
}

function acceptSavedAttempt(saved, generation) {
  if (saved.session_id !== state?.live?.session_id) throw staleSessionError();
  if (generation === editGeneration) useAttempt(saved);
  else { attempt = saved; markDirty(true); }
  if (draftData && !recoveryPending) draftData.base_revision = saved.revision;
  persistDraft();
}

async function runTests() {
  const generation = editGeneration, panelAtStart = panelGeneration;
  if (dirty && !(await save())) return;
  if (panelDirty && savePanel) await savePanel();
  if (generation !== editGeneration || panelAtStart !== panelGeneration) {
    banner("Your inputs changed while saving. Run again to test the latest version.");
    return;
  }
  showConsole("results");
  $("results").replaceChildren(Object.assign(elem("p", "Running…"), {className: "console-empty"}));
  try {
    const result = await api("POST", "/api/run", {});
    if (result.session_id === state?.live?.session_id) renderResults(result);
  } catch (e) {
    $("results").innerHTML = "";
    throw e;
  }
}

// --- the console: Testcases and Result ----------------------------------------
function showConsole(which) {
  consoleTab = which;
  for (const [id, panel] of [["tab-cases", "cases"], ["tab-results", "results"]]) {
    $(id).setAttribute("aria-selected", String(panel === which));
    $(panel).hidden = panel !== which;
  }
  setConsoleOpen(true);
}
function setConsoleOpen(open) {
  $("console").className = open ? "" : "collapsed";
  $("console-toggle").setAttribute("aria-expanded", String(open));
  $("console-toggle").title = open ? "Collapse the console" : "Open the console";
}

function chip(label, selected, onclick, cls = "") {
  const b = button(label, onclick);
  b.className = "chip " + cls;
  b.setAttribute("aria-pressed", String(selected));
  return b;
}
// a definition list of label/value pairs, the ones with a value; err: labels shown as errors
function caseDetail(pairs, err = []) {
  const dl = document.createElement("dl");
  dl.className = "case";
  for (const [label, value] of pairs) {
    if (value === undefined || value === null || value === "") continue;
    const pre = elem("pre", String(value));
    if (err.includes(label)) pre.className = "err";
    const dd = document.createElement("dd");
    dd.append(pre);
    dl.append(elem("dt", label), dd);
  }
  return dl;
}

// The EXAMPLES rows: edited in stage 1's table or in the editor, shown here
function renderCases(selected = 0) {
  const out = $("cases");
  if (!attempt) { out.innerHTML = ""; return; }
  const empty = (text) => {
    const p = Object.assign(elem("p", text), {className: "console-empty"});
    p.append(button("Open stage 1", () => goTo(1)));
    out.replaceChildren(p);
  };
  if (attempt.examples_error) return empty(attempt.examples_error);
  const rows = attempt.examples || [];
  if (!rows.length) return empty("No examples yet. Predict two or three in stage 1, at least one edge case.");
  const chips = document.createElement("div");
  chips.className = "chips";
  rows.forEach((r, i) => {
    const c = chip(`Case ${i + 1}`, i === selected, () => renderCases(i));
    if (r.edge) c.append(Object.assign(elem("span", "edge"), {className: "tag"}));
    chips.append(c);
  });
  const r = rows[Math.min(selected, rows.length - 1)];
  out.replaceChildren(chips, caseDetail([["Input", r.args], ["Expected", r.expected]]));
}

// A traceback names the runner's own frames and long absolute paths: only the attempt file's frames are kept
function trimTraceback(text) {
  if (!text || !text.includes("Traceback (most recent call last):")) return text;
  const out = [];
  let skip = false;
  for (const line of text.split("\n")) {
    if (line.startsWith("Traceback (most recent call last):")) continue;
    const frame = line.match(/^\s*File "([^"]+)", line (\d+), in (.+)$/);
    if (frame) {
      skip = !(attempt && frame[1].endsWith(attempt.file));
      if (!skip) out.push(`line ${frame[2]}, in ${frame[3]}`);
      continue;
    }
    if (skip && /^\s{2,}/.test(line)) continue;  // the code and carets under a skipped frame
    skip = false;
    out.push(line);
  }
  return out.join("\n").trim();
}

function renderResults(r, selected = null) {
  lastRun = r;
  const out = $("results");
  const rows = r.rows || [];
  const passed = rows.filter((x) => x.ok).length;
  const verdict = elem("p", r.error && !rows.length ? "Error" : passed === rows.length && !r.error ? "Accepted" : "Wrong answer");
  verdict.className = "verdict " + (passed === rows.length && !r.error ? "ok" : "fail");
  if (rows.length) verdict.append(Object.assign(elem("span", `${passed} / ${rows.length} cases passed`), {className: "muted"}));
  out.replaceChildren(verdict);
  if (r.error) {  // above the cases: after a time limit, it names the example that hung
    out.append(Object.assign(elem("pre", trimTraceback(r.error)), {className: "run-error"}));
  }
  if (!rows.length) return;
  if (selected === null) selected = Math.max(0, rows.findIndex((x) => !x.ok));
  selectedCase = selected;
  const chips = document.createElement("div");
  chips.className = "chips";
  rows.forEach((row, i) => {
    chips.append(chip(`${row.ok ? "✓" : "✗"} Case ${i + 1}`, i === selected, () => renderResults(r, i), row.ok ? "ok" : "fail"));
  });
  const row = rows[selected];
  // got null: the example never finished
  const got = row.got === null ? "(didn't finish)" : row.error ? "(raised an error)" : row.got;
  // an error is what he needs first when there is one: it goes right under the input
  out.append(chips, caseDetail([["Input", row.args], ["Error", trimTraceback(row.error)], ["Output", got],
    ["Expected", row.expected], ["Stdout", row.stdout]], ["Error"]));
}

// --- top bar -----------------------------------------------------------------
function renderBar() {
  const live = state.live;
  const stages = $("stages");
  $("block-btn").hidden = !live || live.block.open;
  $("progress").hidden = $("actions").hidden = !live;
  if (!live) {
    barFile = null;
    stages.replaceChildren();
    $("problem").textContent = "DSA Coach";
    $("rung").hidden = true;
    $("timer").textContent = $("timer").dataset.text = "";
    return;
  }
  if (barFile !== live.file) {  // once per solve: built again on every poll, they'd lose clicks and keyboard focus
    barFile = live.file;
    const link = Object.assign(elem("a", live.problem), {href: live.url, target: "_blank", rel: "noopener"});
    $("problem").replaceChildren(link);
    if (live.labeled) $("problem").append(Object.assign(elem("span", live.pattern_name), {className: "pattern"}));
    stages.replaceChildren(...STAGES.map(([name], i) => {
      const b = button("", () => goTo(i + 1));
      b.title = `${i + 1}. ${name}`;
      b.setAttribute("aria-label", `Stage ${i + 1}: ${name}`);
      return b;
    }));
  }
  [...stages.children].forEach((b, i) => {
    const n = i + 1;
    b.className = (n === live.stage ? "current" : n < live.stage ? "done" : "") + (n === view ? " viewing" : "");
    if (n === live.stage) b.setAttribute("aria-current", "step"); else b.removeAttribute("aria-current");
  });
  const name = $("stage-name");
  name.replaceChildren(`Stage ${live.stage} · `, elem("b", STAGES[live.stage - 1][0]));
  if (view && view !== live.stage) name.append(Object.assign(elem("span", `viewing ${view}`), {className: "muted"}));
  $("rung").hidden = !live.rung;  // shown once a hint has been used
  $("rung").textContent = `hint ${live.rung}/7`;
  const blk = live.block;
  const over = blk.open && blk.elapsed >= blk.length;
  const text = !blk.open ? `on a break after block ${blk.number}`
    : over ? `block ${blk.number} over by ${minutes(blk.elapsed - blk.length)}`
      : `block ${blk.number} · ${blk.elapsed} of ${blk.length} min`;
  if ($("timer").dataset.text !== text) {  // only when it changes: a button drawn on every poll would lose focus
    $("timer").dataset.text = text;
    if (over) {  // the end-of-block choices stay one click away after the banner is closed
      const b = button(text, blockOver);
      b.title = "Take a break, start another block, or park it";
      $("timer").replaceChildren(b);
    } else $("timer").textContent = text;
  }
  if (live.resumed && once(`welcome:${live.session_id}`, live.resumed)) welcomeBack(live);
  else if (over && once(`block-over:${live.session_id}`, String(blk.number))) blockOver();
}

// True the first time a key gets this value in this tab, so a banner isn't shown again after a reload.
function once(key, value) {
  try {
    if (sessionStorage.getItem("dsa-coach:" + key) === value) return false;
    sessionStorage.setItem("dsa-coach:" + key, value);
  } catch {
    if (shownOnce[key] === value) return false;
    shownOnce[key] = value;
  }
  return true;
}

// After a long absence coach.py starts a fresh block; this says where he was, so he can pick up at once.
function welcomeBack(live) {
  const notes = live.notes || {};
  const last = notes[live.stage] || notes[Object.keys(notes).map(Number).sort((a, b) => b - a)[0]] || "";
  const note = last.trim().split("\n")[0];
  banner(`Welcome back. You were at stage ${live.stage} · ${STAGES[live.stage - 1][0]}.` +
    (note ? ` Last note: "${note.length > 140 ? note.slice(0, 140) + "…" : note}".` : "") +
    ` Block ${live.block.number} started fresh; the time away isn't counted.`, [], "solve");
}

// Typing, clicking or working on LeetCode (the browser panel relays that) keeps the block's clock running.
// coach.py stops the clock after five quiet minutes. At most one touch a minute, and only from a visible page.
function touchActivity() {
  if (!state?.live || document.visibilityState !== "visible" || Date.now() - lastTouch < 60_000) return;
  lastTouch = Date.now();
  api("POST", "/api/solve/touch", {}).catch(() => {});  // a missed touch costs at most a minute of the clock
}
const minutes = (m) => m < 60 ? `${m} min` : `${Math.floor(m / 60)} h ${m % 60} min`;

// Leaving a stage saves what he typed in it first: the panel is drawn again for the stage he goes to.
function goTo(n) {
  const live = state.live;
  if (n <= live.stage) {
    return change(async () => {
      if (panelDirty && savePanel) await savePanel();
      if (!state.live || !attempt) return;  // the solve ended meanwhile, or hasn't loaded yet
      view = n; renderPanel(); renderBar(); showTab("stage");
    });
  }
  banner(`Which stage are you in? The solve is at stage ${live.stage} (${STAGES[live.stage - 1][0]}).`, [
    [`Move to stage ${n} anyway`, async () => {
      if (panelDirty && savePanel) await savePanel();
      await api("POST", "/api/solve/stage", {n});
      view = n;
      showTab("stage");
      await refresh(true);
    }],
    [`Stay at stage ${live.stage}`, async () => {}],
  ], "solve");
}

function blockOver() {
  const live = state.live;
  banner(`Focus block ${live.block.number} is over. If you're stuck, a five-minute break away from the screen often loosens a first idea that isn't working.`, [
    ["Take a break", async () => { await api("POST", "/api/solve/break", {}); await refresh(); }],
    ["Another block", async () => { await api("POST", "/api/solve/block", {}); await refresh(); }],
    ["Ask for the next rung", () => copyPrompt(`My focus block is over and I'm stuck at stage ${live.stage} of ${live.problem}. Next rung, please.`)],
    ["Park it until tomorrow", () => endSolve("partial", `parked: block ${live.block.number}, stage ${live.stage}`)],
  ], "solve");
}

// --- the stage panel ---------------------------------------------------------
function askPrompt(n) {
  const live = state.live;
  if (typeof companionEnabled !== "undefined" && companionEnabled) {
    const context = n === 7
      ? "Review the attached LeetCode code against my supplied plan card. If code is missing or cut off, ask me to attach the code."
      : "Review my supplied saved stage notes, plan card, examples, and any attached LeetCode context.";
    return `Check my work for stage ${n} of ${live.problem}. ${context}`;
  }
  if (n === 7) return `Check my attempt in ${attempt.path}.`;
  return `I'm done with stage ${n} of ${live.problem}. Check it: my notes are in \`coach.py solve show --json\` and my attempt file is ${attempt.path}.`;
}

// --- the Description tab -------------------------------------------------------
const statementBox = () => $("desc").querySelector(".problem textarea");

// problem.md as LeetCode's fetch writes it (a title, the link, paragraphs, "Example N:" blocks, "Constraints:" and
// a list); a pasted statement of any other shape comes out as plain paragraphs.
function renderStatement(text) {
  const root = document.createElement("div");
  root.className = "statement";
  const inline = (parent, s) => {  // `code` spans
    s.split(/(`[^`\n]+`)/).forEach((part) => parent.append(/^`.+`$/.test(part) ? elem("code", part.slice(1, -1)) : part));
    return parent;
  };
  const blocks = text.replace(/\r\n/g, "\n").split(/\n\s*\n/).map((b) => b.replace(/^\n+|\s+$/g, "")).filter(Boolean);
  let inExample = false, pre = null;  // after "Example N:", its Input/Output/Explanation lines go into one <pre>
  for (const b of blocks) {
    const head = b.match(/^(#{1,3})\s+(.*)$/);
    if (head && !b.includes("\n")) { root.append(elem(head[1] === "#" ? "h2" : "h3", head[2])); inExample = false; continue; }
    if (/^https?:\/\/\S+$/.test(b)) continue;  // the LeetCode link: the title in the bar is that link
    if (/^(Example \d+|Constraints|Follow[- ]?up)\b[^\n]{0,20}$/i.test(b)) {
      root.append(elem("h3", b.replace(/:$/, "")));
      inExample = /^Example/i.test(b);
      pre = null;
      continue;
    }
    const ends = pre && pre.textContent.endsWith(":");  // "Explanation:" and its text, in separate blocks
    if (inExample && (ends || /^(Input|Output|Explanation)\b/.test(b))) {
      if (!pre) { pre = elem("pre", b); root.append(pre); } else pre.textContent += (ends ? " " : "\n") + b;
      continue;
    }
    inExample = false;
    if (b.split("\n").every((l) => /^\s*[-*•]\s+/.test(l))) {
      const ul = document.createElement("ul");
      for (const l of b.split("\n")) ul.append(inline(document.createElement("li"), l.replace(/^\s*[-*•]\s+/, "")));
      root.append(ul);
    } else root.append(inline(document.createElement("p"), b));
  }
  return root;
}

// draft: a statement pasted into the box before the tab was drawn again, and not saved yet
function problemBlock(draft = "") {
  const box = document.createElement("div");
  box.className = "problem";
  if (problemText) {
    box.append(renderStatement(problemText));
  } else if (fetchState === "fetching") {
    box.append(Object.assign(elem("p", "Fetching the statement from LeetCode…"), {className: "empty"}));
  } else {
    box.append(elem("h2", state.live.problem));
    if (fetchState && fetchState.error) {
      box.append(Object.assign(elem("p", fetchState.error), {className: "nudge"}));
    }
    const slug = state.live.problem;
    const ta = document.createElement("textarea");
    ta.rows = 12;
    ta.value = draft;
    ta.placeholder = "Paste the problem statement from LeetCode. You only do this once per problem.";
    ta.setAttribute("aria-label", "Problem statement");
    const actions = document.createElement("div");
    actions.className = "actions";
    const saveBtn = button("Save statement", async () => {
      const sent = ta.value, identity = state.live.session_id;
      const saved = await api("PUT", "/api/problem", {slug, text: sent});
      if (identity !== state?.live?.session_id) return;
      problemText = saved.text;
      if (ta.value === sent) {
        if (draftData) delete draftData.statement;
        renderDesc();
      }
      persistDraft();  // only this box: what he's typed in the stage stays
    }, true);
    saveBtn.className = "primary";
    actions.append(saveBtn);
    if (fetchState && fetchState.error) actions.append(button("Try fetching again", async () => { await fetchStatement(); }));
    box.append(ta, actions);
  }
  return box;
}

function renderDesc() {
  if (!state?.live || !attempt) return;
  const draft = statementBox()?.value || "";
  $("desc").replaceChildren(problemBlock(draft));
  applyStatementDraft();
}

// Opening the tab reads problem.md again: a statement the coach wrote meanwhile shows up. Never over a paste.
async function reloadStatement() {
  if (!state?.live || !attempt || statementDraft() || fetchState === "fetching") return;
  const file = attempt.file;
  try {
    const p = await api("GET", "/api/problem?slug=" + encodeURIComponent(state.live.problem));
    if (!attempt || attempt.file !== file || statementDraft()) return;
    if (p.text !== problemText) { problemText = p.text; renderDesc(); }
  } catch (e) { fail(e); }
}

function showTab(which) {
  tab = which;
  for (const [id, panel] of [["tab-desc", "desc"], ["tab-stage", "panel"], ["tab-notes", "notes"]]) {
    const on = $(id).dataset.tab === which;
    $(id).setAttribute("aria-selected", String(on));
    $(id).tabIndex = on ? 0 : -1;
    $(panel).hidden = !on;
  }
  if (which === "notes") renderNotes();
}

// --- the Notes tab: what he saved in earlier stages, read-only --------------------
function renderNotes() {
  if (!state?.live || !attempt) return;
  const notes = state.live.notes || {};
  const plan = PLAN_FIELDS.filter((f) => (attempt.plan_card[f] || "").trim()).map((f) => `${f}: ${attempt.plan_card[f].trim()}`);
  const key = JSON.stringify([notes, plan]);
  if (notesDrawn === key && $("notes").childElementCount) return;
  notesDrawn = key;
  const list = document.createElement("div");
  list.className = "notes-list";
  STAGES.forEach(([name], i) => {
    const n = i + 1;
    const text = n === 6 ? plan.join("\n") : (notes[String(n)] || "").trim();
    if (!text) return;
    const b = button("", () => goTo(n));
    b.className = "note";
    b.title = `Open stage ${n}`;
    b.append(Object.assign(elem("span", String(n)), {className: "n"}), elem("b", name), elem("pre", text));
    list.append(b);
  });
  $("notes").replaceChildren(list.childElementCount ? list
    : Object.assign(elem("p", "Answers you save in each stage collect here, so you can look back without leaving the stage you're in."), {className: "empty"}));
}

// One request to LeetCode, through the server, when a solve opens without a statement; pasting is the fallback.
// Not in the change() queue: it only writes problem.md and may take seconds. Polls never call it.
async function fetchStatement() {
  if (!attempt || !state || !state.live) return;
  const file = attempt.file, slug = state.live.problem;
  const redrawBox = renderDesc;
  fetchState = "fetching";
  redrawBox();
  let next;
  try {
    const r = await api("POST", "/api/problem/fetch", {slug});
    next = {text: r.text};
  } catch (e) {
    if (e.gone || e.offline) { fail(e); next = {error: e.message}; }
    else next = {error: e.message};
  }
  if (!attempt || attempt.file !== file) return;  // that solve ended while the fetch was out
  if (next.text !== undefined) { problemText = next.text; fetchState = null; } else fetchState = next;
  redrawBox();
}

function textStage(panel, note, done, n) {
  const ta = field(panel, n === 7 ? "Notes (optional): your subgoals, or what you're unsure about" : "Your answer", note, true, "answer");
  ta.rows = 6;
  return async () => ta.value.trim();
}

function stageOne(panel, note, done) {
  const restate = field(panel, "The problem in one sentence", note, true, "restate");
  const table = document.createElement("table");
  table.className = "examples";
  table.innerHTML = "<tr><th>inputs, as Python values (e.g. [5], 5)</th><th>your predicted output</th><th>edge?</th><th></th></tr>";
  const rows = () => [...table.rows].slice(1).map((tr) => ({
    args: tr.querySelector(".args").value.trim(),
    expected: tr.querySelector(".expected").value.trim(),
    edge: tr.querySelector(".edge").checked,
  })).filter((r) => r.args || r.expected);
  const gate = () => { done.disabled = !(restate.value.trim() && rows().some((r) => r.edge && r.args && r.expected)); };
  done.gate = gate;
  const addRow = (r = {args: "", expected: "", edge: false}) => {
    const tr = table.insertRow();
    tr.innerHTML = '<td><input class="args" aria-label="inputs, as Python values" autocomplete="off" spellcheck="false"></td>' +
      '<td><input class="expected" aria-label="predicted output" autocomplete="off" spellcheck="false"></td>' +
      '<td><input type="checkbox" class="edge" aria-label="edge case"></td><td></td>';
    tr.querySelector(".args").value = r.args;
    tr.querySelector(".expected").value = r.expected;
    tr.querySelector(".edge").checked = r.edge;
    const remove = button("×", () => { tr.remove(); panelEdited(); gate(); });
    remove.setAttribute("aria-label", "Remove this example");
    tr.cells[3].append(remove);
    tr.addEventListener("input", gate);
    tr.addEventListener("change", gate);
  };
  (attempt.examples.length ? attempt.examples : [undefined, undefined]).forEach((r) => addRow(r));
  let drawn = JSON.stringify(rows());  // EXAMPLES is written only if the rows changed here: edits in the editor stay
  restate.addEventListener("input", gate);
  panel.append(table, button("Add an example", () => { addRow(); panelEdited(); }));
  restoreExamples = (examples) => {
    while (table.rows.length > 1) table.deleteRow(1);
    examples.forEach(addRow);
    gate();
  };
  if (attempt.examples_error) {
    const p = document.createElement("p");
    p.className = "nudge";
    p.textContent = attempt.examples_error;
    panel.append(p);
  }
  const hint = document.createElement("p");
  hint.className = "hint";
  hint.textContent = "Done unlocks once you have a one-sentence restatement and at least one edge case.";
  panel.append(hint);
  setTimeout(gate);
  return async () => {
    const text = restate.value.trim(), now = rows(), json = JSON.stringify(now);
    await saveParts(json === drawn ? {} : {examples: now});
    drawn = json;
    return text;
  };
}

function stageSix(panel) {
  // a field is written only if he changed it here, so what he typed into the docstring in the editor stays.
  // drawn is the value as the box holds it: a one-line box drops the line breaks of a longer value.
  const inputs = PLAN_FIELDS.map((f) => {
    const el = field(panel, f, attempt.plan_card[f] || "", f === "Hand trace", "plan:" + f);
    return {f, el, drawn: el.value};
  });
  return async () => {
    const changed = inputs.filter((x) => x.el.value !== x.drawn).map((x) => [x, x.el.value]);
    await saveParts(changed.length ? {plan_card: Object.fromEntries(changed.map(([x, v]) => [x.f, v]))} : {});
    for (const [x, v] of changed) x.drawn = v;
    return null;  // the plan card lives in the attempt file's docstring, not in a stage note
  };
}

// The note holds the three answers, each after its question's head, with a blank line between them.
const lookHead = (i) => `${LOOK_BACK[i].split(":")[0]}: `;
function stageEight(panel, note) {
  const parts = note ? note.split("\n\n") : [];
  const boxes = LOOK_BACK.map((q, i) => {
    const part = parts[i] || "";
    return field(panel, q, part.startsWith(lookHead(i)) ? part.slice(lookHead(i).length) : part, true, "reflection:" + i);
  });
  // a blank line inside an answer would read back as the start of the next one
  return async () => boxes.map((b, i) => lookHead(i) + b.value.trim().replace(/\n\s*\n/g, "\n")).join("\n\n");
}

function renderPanel() {
  const live = state.live;
  const n = view;
  const panel = $("panel");
  panel.innerHTML = "";
  restoreExamples = null;
  panelDirty = false;
  const head = document.createElement("div");
  head.className = "stage-head";
  const q = elem("p", STAGES[n - 1][1]);
  q.className = "question";
  head.append(Object.assign(elem("p", `Stage ${n} of 8`), {className: "eyebrow"}), elem("h2", STAGES[n - 1][0]), q);
  panel.append(head);

  const note = (live.notes || {})[String(n)] || "";
  let collect;  // saves this stage's parts of the attempt file, and returns the stage note (or null)
  const saveNote = async () => {
    const generation = panelGeneration;
    const identity = state.live.session_id;
    const captured = capturePanel();
    // Keep the panel protected from polling redraws until its acknowledgement arrives.
    try {
      const text = await collect();
      if (text !== null) {
        await api("POST", "/api/solve/note", {stage: n, text});
        // as the next poll will have it, so drawing this stage again before that poll shows what he wrote
        if (identity !== state?.live?.session_id) throw staleSessionError();
        state.live.notes = {...state.live.notes, [n]: text};
      }
    } catch (e) {
      panelDirty = true;
      throw e;
    }
    panelDirty = generation !== panelGeneration;
    if (!panelDirty) acknowledgePanel(n, captured);
    persistDraft();
    await refresh();
  };
  savePanel = saveNote;
  let finish;  // stage 8: the outcome and lesson boxes
  const inCompanion = typeof companionEnabled !== "undefined" && companionEnabled;
  const doneLabel = n === 8 ? (inCompanion ? "Review with coach" : "Done: ask the coach to log it")
    : inCompanion ? (n === live.stage ? "Complete and continue" : `Go to stage ${n + 1}`) : `Done with stage ${n}`;
  const done = button(doneLabel, async () => {
    if (n === 8 && dirty && !(await save())) return;  // the finish prompt sends the coach to the file
    await saveNote();
    if (!state.live || !attempt) return;  // the solve ended meanwhile
    if (n === 8) return finishPrompt(finish.outcome.value, finish.lesson.value.trim());
    if (n >= state.live.stage) await api("POST", "/api/solve/stage", {n: n + 1});
    view = n + 1;
    focusNext = true;
    await refresh(true);
  }, true);
  collect = ({1: stageOne, 6: stageSix, 8: stageEight}[n] || textStage)(panel, note, done, n);

  if (n === 7 && !PLAN_FIELDS.slice(0, 6).some((f) => (attempt.plan_card[f] || "").trim())) {
    const nudge = document.createElement("p");
    nudge.className = "nudge";
    nudge.textContent = "The plan card (stage 6) is empty. Bugs like a missed last candidate show up in the hand trace before they show up in the tests.";
    panel.append(nudge);
  }
  done.className = "primary";
  // Save first so both the panel's supplied context and the main chat's file reads see the latest work.
  askCoach = async () => {
    if (dirty && !(await save())) return;
    await saveNote();
    if (state.live && attempt) await copyPrompt(askPrompt(n));
  };
  if (n === 8) {
    finish = finishBlock(done);
    panel.append(finish.box);
  }
  const actions = document.createElement("div");
  actions.className = "actions";
  const saveBtn = button("Save answer", saveNote, true);
  saveBtn.className = "ghost";
  actions.append(saveBtn, ...(n === 8 ? [] : [done]));
  if (inCompanion) actions.append(button("Discuss with coach", () => askCoach(), true));
  panel.append(actions);
  applyStageDraft(n);
  if (focusNext) {  // drawn by Done: he goes on typing in the next stage
    focusNext = false;
    panel.querySelector("label > textarea, label > input")?.focus();
  }
}

// The coach logs the attempt: the technique, mistake codes and complexity check are its judgment, so stage 8's Done
// hands it his outcome and lesson rather than ending the solve here.
function finishBlock(done) {
  const box = document.createElement("div");
  box.className = "finish";
  box.append(elem("h3", "Finish"));
  const outcome = document.createElement("select");  // no default: he says how it went
  outcome.add(new Option("choose one", ""));
  for (const o of ["solved", "partial", "failed"]) outcome.add(new Option(o, o));
  outcome.dataset.draftField = "finish:outcome";
  labelled(box, "Outcome", outcome);
  const lesson = field(box, "Lesson (one line)", "", false, "finish:lesson");
  done.gate = () => { done.disabled = !outcome.value; };
  outcome.addEventListener("change", done.gate);
  done.gate();
  box.append(done);
  return {box, outcome, lesson};
}

async function finishPrompt(outcome, lesson) {
  if (typeof companionEnabled !== "undefined" && companionEnabled) {
    return companionAsk(`Review my stage 8 answers and the attached LeetCode context. My outcome is ${outcome}; lesson: ${lesson || "not stated yet"}. Ask me for any evidence still missing. I will log the attempt in my main coach chat.`);
  }
  finishSent = attempt.file;
  await copyPrompt(`I'm done with stage 8 of ${state.live.problem}: outcome ${outcome}, `
    + `${lesson ? `lesson "${lesson}"` : "no lesson"}. Check my answers (solve show --json) and my attempt in `
    + `${attempt.path}, then log the attempt.`,
    "Copied. Paste it into the chat: the coach checks it and logs the attempt, and this page goes back to the start screen.");
}

// Parking: the one way a solve ends from the page
async function endSolve(outcome, note) {
  if (dirty && !(await save())) return;  // the code goes into the attempt file before the attempt is logged
  if (panelDirty && savePanel) await savePanel();  // and his stage note into the solve, which copies it to notes.md
  const out = await api("POST", "/api/solve/end", {outcome, note});  // no outcome: "outcome is empty", in the banner
  solveGone();
  banner(out.message);
  await refresh();
}

// --- local recovery (drafts never count as notebook saves) ---------------------
const DRAFT_VERSION = 1, DRAFT_PREFIX = "dsa-coach:draft:";
let draftData = null, recoveryPending = false, recoveryChoice = null;
let draftTimer = null, restoreExamples = null, recoveryShown = null;
const invalidDrafts = new Map();

function draftKey(notebook, session) { return DRAFT_PREFIX + notebook + ":" + session; }
function draftStatus(text) { $("draft-status").textContent = text; }
function storageFailure() {
  draftStatus("Draft recovery is unavailable in this browser. Save your work before closing.");
}
function readDraft(key) {
  const text = localStorage.getItem(key);
  if (!text) return null;
  try {
    const d = JSON.parse(text);
    if (d.version !== DRAFT_VERSION || typeof d.notebook_id !== "string" || typeof d.session_id !== "string" ||
        !d.stages || typeof d.stages !== "object" || Array.isArray(d.stages) ||
        (d.code && (typeof d.code.text !== "string" || typeof d.code.revision !== "string")) ||
        (d.statement !== undefined && typeof d.statement !== "string")) throw new Error("invalid draft");
    for (const [stage, value] of Object.entries(d.stages)) {
      if (!/^[1-8]$/.test(stage) || !value || !value.fields || typeof value.fields !== "object" ||
          Object.values(value.fields).some((v) => typeof v !== "string") ||
          (value.examples && (!Array.isArray(value.examples) || value.examples.some((r) =>
            typeof r.args !== "string" || typeof r.expected !== "string" || typeof r.edge !== "boolean")))) throw new Error("invalid draft");
    }
    if (key.startsWith(DRAFT_PREFIX) && key !== draftKey(d.notebook_id, d.session_id)) throw new Error("wrong draft namespace");
    invalidDrafts.delete(key);
    return d;
  } catch {
    invalidDrafts.set(key, text);
    draftStatus("A saved draft could not be read. It has been kept in browser storage; normal saving still works.");
    return null;
  }
}
function freshDraft() {
  return {version: DRAFT_VERSION, notebook_id: state.notebook_id, session_id: attempt.session_id,
    file: attempt.file, base_revision: attempt.revision, view, stages: {}};
}
function beginDraft() {
  draftData = freshDraft();
  recoveryChoice = null; recoveryPending = false; recoveryShown = null;
  try {
    const key = draftKey(draftData.notebook_id, draftData.session_id);
    const existing = readDraft(key);
    if (existing || invalidDrafts.has(key)) {
      recoveryChoice = {key, data: existing, raw: invalidDrafts.get(key)}; recoveryPending = true;
    }
  } catch { storageFailure(); }
}
function capturePanel() {
  const fields = {};
  for (const control of $("panel").querySelectorAll("[data-draft-field]")) fields[control.dataset.draftField] = control.value;
  const table = $("panel").querySelector("table.examples");
  const result = {fields};
  if (table) result.examples = [...table.rows].slice(1).map((tr) => ({
    args: tr.querySelector(".args").value, expected: tr.querySelector(".expected").value,
    edge: tr.querySelector(".edge").checked,
  }));
  return result;
}
function panelEdited() { panelGeneration++; panelDirty = true; scheduleDraft(); }
function scheduleDraft() {
  clearTimeout(draftTimer);
  draftTimer = setTimeout(persistDraft, 200);
}
function persistDraft() {
  clearTimeout(draftTimer);
  if (!attempt || !draftData) return;
  if (recoveryPending) { draftStatus("Choose whether to restore or discard the saved draft before storing new edits."); return; }
  if (dirty) draftData.code = {text: getCode(), revision: attempt.revision};
  else delete draftData.code;
  if (panelDirty && view) draftData.stages[view] = capturePanel();
  const statement = statementBox();
  if (statement) {
    if (statement.value) draftData.statement = statement.value;
    else delete draftData.statement;
  }
  draftData.view = view;
  draftData.updated = Date.now();
  try {
    const key = draftKey(draftData.notebook_id, draftData.session_id);
    if (draftData.code || Object.keys(draftData.stages).length || draftData.statement) {
      localStorage.setItem(key, JSON.stringify(draftData));
      draftStatus("Draft kept in this browser. Notebook saves are separate.");
    } else {
      localStorage.removeItem(key);
      draftStatus("");
    }
  } catch { storageFailure(); }
}
function acknowledgePanel(stage, captured) {
  if (!draftData || recoveryPending) return;
  // Outcome and lesson are not acknowledged by solve note; keep them until explicit discard.
  const finish = Object.fromEntries(Object.entries(captured.fields).filter(([k, v]) => k.startsWith("finish:") && v));
  if (Object.keys(finish).length) draftData.stages[stage] = {fields: finish};
  else delete draftData.stages[stage];
}
function applyStageDraft(stage) {
  if (!draftData || recoveryPending) return;
  const saved = draftData.stages[stage];
  if (saved) {
    for (const control of $("panel").querySelectorAll("[data-draft-field]")) {
      if (Object.hasOwn(saved.fields, control.dataset.draftField)) control.value = saved.fields[control.dataset.draftField];
    }
    if (saved.examples && restoreExamples) restoreExamples(saved.examples);
    panelDirty = true;
    // Refresh gates after restoring, including the stage-8 outcome selector.
    for (const control of $("panel").querySelectorAll("[data-draft-field]")) control.dispatchEvent(new Event("change"));
  }
}
// the statement half of a draft: into the paste box, or shown beside a statement that's saved meanwhile
function applyStatementDraft() {
  if (!draftData || recoveryPending) return;
  if (draftData.statement !== undefined) {
    const existing = $("desc").querySelector(".problem");
    const ta = existing?.querySelector("textarea");
    if (ta) ta.value = draftData.statement;
    else if (existing) {
      const recovery = field(existing, "Recovered statement draft (copy it before discarding)", draftData.statement, true);
      recovery.readOnly = true;
    }
  }
}
function restoreDraft(choice) {
  if (!choice.data || !attempt || choice.data.notebook_id !== state.notebook_id || choice.data.session_id !== attempt.session_id) return;
  const d = choice.data;
  draftData = d; recoveryPending = false; recoveryChoice = null; recoveryShown = null;
  if (d.code) {
    setCode(d.code.text); markDirty(true);
    attempt.revision = d.code.revision; // retain the original base so Save still detects external changes
  } else if (d.base_revision) attempt.revision = d.base_revision;
  view = Number(d.view) >= 1 && Number(d.view) <= 8 ? Number(d.view) : state.live.stage;
  renderPanel(); renderBar(); renderDesc();
  $("recovery").hidden = true;
  persistDraft();
}
function discardDraft(choice) {
  try { localStorage.removeItem(choice.key); } catch { storageFailure(); return; }
  invalidDrafts.delete(choice.key);
  const current = attempt && choice.key === draftKey(state.notebook_id, attempt.session_id);
  if (current) { recoveryChoice = null; recoveryPending = false; draftData = freshDraft(); }
  recoveryShown = null;
  $("recovery").hidden = true;
  persistDraft();
}
async function copyDraft(choice) {
  const text = choice.raw ?? JSON.stringify(choice.data, null, 2);
  try { await navigator.clipboard.writeText(text); draftStatus("Recovered draft copied."); }
  catch {
    const ta = document.createElement("textarea");
    ta.value = text; ta.readOnly = true; ta.setAttribute("aria-label", "Recovered draft to copy");
    $("recovery").append(ta); ta.select();
  }
}
function offerRecovery() {
  if (!state?.notebook_id) return;
  try {
    let choice = recoveryChoice;
    if (!choice) {
      const prefix = DRAFT_PREFIX + state.notebook_id + ":";
      for (let i = 0; i < localStorage.length; i++) {
        const key = localStorage.key(i);
        if (!key.startsWith(prefix) || key === draftKey(state.notebook_id, attempt?.session_id)) continue;
        const data = readDraft(key);
        if (data || invalidDrafts.has(key)) { choice = {key, data, raw: invalidDrafts.get(key)}; break; }
      }
    }
    if (!choice || recoveryShown === choice.key) return;
    recoveryShown = choice.key;
    const same = attempt && choice.data?.session_id === attempt.session_id;
    const box = $("recovery");
    box.replaceChildren(elem("span", same
      ? "A saved draft is available. Restoring replaces the current local fields; disk changes still require conflict resolution."
      : choice.data ? `Unsaved work from an earlier solve (${choice.data.file}) is available to copy.`
        : "A saved draft could not be read. Copy it for safekeeping or discard it to resume draft storage."),
      ...(same ? [button("Restore draft", () => restoreDraft(choice))] : []),
      button("Copy draft", () => copyDraft(choice)), button("Discard draft", () => discardDraft(choice)));
    box.hidden = false;
  } catch { storageFailure(); }
}

// --- start screen ------------------------------------------------------------
function renderStart() {
  const nx = state.next || {};
  const pick = companionProblem || ((nx.kind === "new" || nx.kind === "resolve") && nx.problem ? nx.problem : "");
  $("pick-kind").textContent = companionProblem ? "Open on LeetCode" : pick ? `Next up · ${nx.kind === "resolve" ? "re-solve from a blank page" : "new problem"}`
    : "Start a solve";
  $("next-pick").textContent = pick;
  if (pick !== lastPick) {  // a new pick fills the slug box, unless he typed a slug of his own into it
    const slug = $("slug");
    if (!slug.value.trim() || slug.value === lastPick) slug.value = pick;
    lastPick = pick;
  }
  const due = state.due;
  $("due-line").textContent = due ? `Due: ${due.resolves.length} re-solve(s), ${due.cards.length} card(s), ${due.drafts} draft card(s).`
    : "";
  gateStart();
}
// pending: not while a start (or anything else) is still on its way
const gateStart = () => { $("start-btn").disabled = pending > 0 || !($("slug").value.trim() && $("confidence").value); };

async function start() {
  const nx = state.next || {};
  const problem = $("slug").value.trim().toLowerCase();
  const body = {problem, confidence: Number($("confidence").value)};
  if ($("pattern").value.trim()) body.pattern = $("pattern").value.trim();
  if ($("difficulty").value) body.difficulty = $("difficulty").value;  // none: an earlier attempt's, or medium
  if (nx.problem === problem && nx.kind === "new") {
    body.pattern = body.pattern || nx.pattern;
    if (nx.block === false) body.unlabeled = true;
  }
  if (nx.problem === problem && nx.kind === "resolve") body.mode = "review";
  await api("POST", "/api/solve/start", body);
  $("slug").value = $("pattern").value = $("confidence").value = $("difficulty").value = "";
  lastPick = null;  // the next start screen offers its pick again
  view = 1;
  await refresh(true);
}

// --- the loop ----------------------------------------------------------------
let queued = null;       // a refresh asked for while one was running: null, or whether it wanted a redraw

// Stages 1 and 6 show parts of the attempt file, so a new version of the file draws them again, unless that would
// drop what he's typed in the panel. Nothing here ever redraws a panel with unsaved text in it.
const redrawForFile = () => !panelDirty && (view === 1 || view === 6);
const statementDraft = () => (statementBox()?.value || "").trim();

async function refresh(redraw = false) {
  if (busy) { queued = Boolean(queued) || redraw; return; }
  busy = true;
  const seen = finished;
  // A state change finished while this refresh was out: what it fetched may be from before that change. It's
  // dropped, and fetched again at once.
  const stale = () => {
    if (seen === finished) return false;
    queued = Boolean(queued) || redraw;
    return true;
  };
  try {
    const next = await api("GET", "/api/state");
    if (stale()) return;
    state = next;
    if (typeof renderCompanion === "function") renderCompanion();
    if ($("banner").dataset.kind === "offline") $("banner").hidden = true;  // it's answering again
    const live = state.live;
    if (attempt && (!live || live.session_id !== attempt.session_id)) solveGone();
    $("start").hidden = !!live;
    $("solve").hidden = !live;
    if (!live) { renderBar(); renderStart(); offerRecovery(); return; }
    if (!attempt) {  // both or neither: a failed load leaves attempt null, so the next poll loads it again
      const [a, p] = await Promise.all([api("GET", "/api/attempt?session_id=" + encodeURIComponent(live.session_id)),
        api("GET", "/api/problem?slug=" + encodeURIComponent(live.problem))]);
      if (stale()) return;
      useAttempt(a);
      problemText = p.text;
      view = view || live.stage;
      beginDraft();
      redraw = true;
      renderDesc();
      showTab(problemText === null && !document.body.classList.contains("companion") ? "desc" : "stage");
      showConsole("cases");
      if (problemText === null && fetchState === null) fetchStatement();  // once per solve; not awaited
    } else if (!pending && state.attempt_mtime !== attempt.mtime && state.attempt_mtime !== warnedMtime) {
      // not while a save of the page's own is in flight: its answer brings the new mtime
      const disk = await api("GET", "/api/attempt?session_id=" + encodeURIComponent(live.session_id));
      if (stale()) return;
      if (dirty) conflict(disk); else { useAttempt(disk); if (redrawForFile()) redraw = true; }
    }
    // the chat moved the stage: follow it, unless he's typing in the panel
    if (lastStage !== null && live.stage !== lastStage && view === lastStage && !panelDirty) { view = live.stage; redraw = true; }
    lastStage = live.stage;
    if (redraw) renderPanel();
    if (tab === "notes") renderNotes();
    renderBar();
    offerRecovery();
  } catch (e) {
    fail(e);
  } finally {
    busy = false;
    if (typeof renderCompanion === "function") renderCompanion();
    if (queued !== null) { const r = queued; queued = null; refresh(r); }
  }
}

document.addEventListener("DOMContentLoaded", () => {
  if (location.pathname !== "/companion") setupEditor();
  $("run-btn").onclick = () => change(runTests, $("run-btn"));
  $("start-btn").onclick = () => change(start, $("start-btn"));
  $("slug").oninput = gateStart;
  $("confidence").onchange = gateStart;
  $("ask-btn").onclick = () => { if (askCoach) change(askCoach, $("ask-btn")); };
  for (const t of document.querySelectorAll("#left [role=tab]")) {
    t.onclick = () => { showTab(t.dataset.tab); if (t.dataset.tab === "desc") reloadStatement(); };
  }
  for (const t of document.querySelectorAll("#console [role=tab]")) t.onclick = () => showConsole(t.dataset.console);
  $("console-toggle").onclick = () => setConsoleOpen($("console").className === "collapsed");
  // arrow keys move between tabs, as in any tab strip
  document.addEventListener("keydown", (e) => {
    const t = e.target.closest?.("[role=tab]");
    if (!t || !["ArrowLeft", "ArrowRight"].includes(e.key)) return;
    const all = [...t.parentElement.querySelectorAll("[role=tab]")];
    const next = all[(all.indexOf(t) + (e.key === "ArrowRight" ? 1 : all.length - 1)) % all.length];
    next.focus(); next.click();
  });
  $("block-btn").onclick = () => change(async () => { await api("POST", "/api/solve/block", {}); await refresh(); }, $("block-btn"));
  // the statement box isn't one of the stage's boxes: Save statement saves it, and a redraw carries it over
  $("panel").addEventListener("input", panelEdited);
  $("desc").addEventListener("input", scheduleDraft);
  $("panel").addEventListener("change", (e) => {
    if (e.target.matches("select, input[type=checkbox]")) panelEdited();
  });
  document.addEventListener("visibilitychange", () => { if (document.hidden) persistDraft(); });
  window.addEventListener("pagehide", persistDraft);
  document.addEventListener("keydown", saveKey);
  for (const type of ["keydown", "input", "pointerdown"]) document.addEventListener(type, touchActivity, true);
  window.addEventListener("beforeunload", (e) => {  // closing or reloading the tab would drop unsaved text
    if (dirty || panelDirty || statementDraft()) { e.preventDefault(); e.returnValue = ""; }
  });
  refresh();
  setInterval(refresh, 3000);
});
