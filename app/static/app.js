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
const OFFLINE = "The app's server isn't answering. Is <code>python3 app/server.py</code> still running?";

const $ = (id) => document.getElementById(id);
let state = null;        // the last /api/state
let attempt = null;      // the last /api/attempt: {file, path, text, mtime, plan_card, examples, examples_error}
let problemText = null;  // problems/<slug>/problem.md, or null before it's pasted
let view = null;         // the stage shown in the panel
let lastStage = null;    // the live stage at the previous poll
let editor = null;       // CodeMirror, or null when the CDN didn't load and the textarea is used
let dirty = false;
let blockBanner = null;  // the block number the "block is over" banner was shown for
let warnedMtime = null;  // the disk mtime we already warned about
let busy = false;        // a refresh is running
let chain = Promise.resolve();  // the page's state changes (its POSTs and PUTs), one at a time, in click order
let pending = 0;         // state changes waiting or in flight

// --- plumbing ----------------------------------------------------------------
async function api(method, path, body) {
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
    err.gone = res.status === 404 && err.message.startsWith("no live solve");
    throw err;
  }
  return data;
}

const escapeHtml = (s) => String(s).replace(/[&<>"]/g, (c) => ({"&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;"}[c]));

// kind: "solve" for a banner whose buttons act on the live solve, "offline" while the server isn't answering
function banner(html, actions = [], kind = "") {
  const el = $("banner");
  el.innerHTML = "";
  el.dataset.kind = kind;
  const text = document.createElement("span");
  text.innerHTML = html;
  el.append(text);
  for (const [label, fn] of actions) {
    el.append(button(label, () => { el.hidden = true; return change(fn); }));
  }
  const close = button("×", () => { el.hidden = true; });
  close.className = "close";
  close.setAttribute("aria-label", "Dismiss");
  el.append(close);
  el.hidden = false;
}

function fail(e) {
  if (e.gone) { solveGone(); refresh(); }
  if (!e.shown) banner(e.offline ? OFFLINE : escapeHtml(e.message), [], e.offline ? "offline" : "");
}

// changes: the click sends a POST or PUT, so it goes through change()
function button(label, fn, changes = false) {
  const b = document.createElement("button");
  b.textContent = label;
  b.onclick = changes ? () => change(fn, b) : () => Promise.resolve().then(fn).catch(fail);
  return b;
}

// One state change at a time: a click that changes something waits for the one before it, and its button
// stays disabled until it's done. Polling goes on meanwhile.
function change(fn, btn) {
  pending++;
  if (btn) btn.disabled = true;
  const run = chain.then(fn).catch(fail).finally(() => {
    pending--;
    if (btn) { btn.disabled = false; if (btn.gate) btn.gate(); }
  });
  chain = run;
  return run;
}

function field(parent, label, value, multiline) {
  const l = document.createElement("label");
  l.textContent = label;
  const input = document.createElement(multiline ? "textarea" : "input");
  if (multiline) input.rows = 3;
  input.setAttribute("autocomplete", "off");
  input.value = value || "";
  l.append(input);
  parent.append(l);
  return input;
}

async function copyPrompt(text) {
  try {
    await navigator.clipboard.writeText(text);
    banner("Copied. Paste it into the coach chat: <code>" + escapeHtml(text) + "</code>");
  } catch {
    banner("Copy this into the coach chat: <code>" + escapeHtml(text) + "</code>");
  }
}

// --- editor and the attempt file ---------------------------------------------
function setupEditor() {
  const saveKey = () => change(save, $("save-btn"));
  if (window.CodeMirror) {
    $("editor-host").innerHTML = "";
    editor = CodeMirror($("editor-host"), {
      mode: "python", lineNumbers: true, indentUnit: 4, tabSize: 4, indentWithTabs: false,
      extraKeys: {
        Tab: (cm) => (cm.somethingSelected() ? cm.execCommand("indentMore") : cm.replaceSelection("    ")),
        "Cmd-S": saveKey, "Ctrl-S": saveKey,
      },
    });
    editor.on("change", () => markDirty(true));
  } else {
    const ta = $("editor-fallback");
    ta.addEventListener("input", () => markDirty(true));
    ta.addEventListener("keydown", (e) => {
      if ((e.metaKey || e.ctrlKey) && e.key === "s") { e.preventDefault(); saveKey(); }
    });
  }
  $("save-btn").onclick = saveKey;
}
const getCode = () => (editor ? editor.getValue() : $("editor-fallback").value);
function setCode(text) {
  if (getCode() !== text) {  // the same text: keep the cursor where it is
    if (editor) editor.setValue(text); else $("editor-fallback").value = text;
  }
  markDirty(false);
}
function markDirty(d) {
  dirty = d;
  $("dirty").textContent = d ? "unsaved" : "saved";
}

function useAttempt(a) {
  const another = !attempt || attempt.file !== a.file;
  attempt = a;
  warnedMtime = null;
  setCode(a.text);
  if (another && editor) editor.clearHistory();  // so undo can't bring back another solve's code
  $("file").textContent = a.file;
}

// The live solve went away: ended from the chat, or replaced by another one. Unsaved code isn't dropped silently.
function solveGone() {
  if (attempt && dirty) rescue(getCode());
  if ($("banner").dataset.kind === "solve") $("banner").hidden = true;  // its buttons were for that solve
  attempt = problemText = view = lastStage = blockBanner = warnedMtime = null;
  markDirty(false);
  $("results").innerHTML = "";
}

function rescue(code) {
  const el = $("rescue");
  el.innerHTML = "";
  const text = document.createElement("span");
  text.textContent = "The solve ended (from the chat?). Your unsaved code isn't in any file.";
  const copy = button("Copy my code", async () => {
    try {
      await navigator.clipboard.writeText(code);
      text.textContent = "The solve ended (from the chat?). Your unsaved code isn't in any file; it's on the clipboard now.";
    } catch {
      if (!el.querySelector("textarea")) {
        const ta = document.createElement("textarea");
        ta.readOnly = true;
        ta.rows = 10;
        ta.value = code;
        el.append(ta);
      }
      el.querySelector("textarea").select();
      text.textContent = "The solve ended (from the chat?). The clipboard isn't available: copy your unsaved code from the box below.";
    }
  });
  const close = button("×", () => { el.hidden = true; });
  close.className = "close";
  close.setAttribute("aria-label", "Dismiss");
  el.append(text, copy, close);
  el.hidden = false;
}

const isConflict = (e) => e.status === 409 && typeof e.data.text === "string" && e.data.mtime != null;

function conflict(disk) {
  warnedMtime = disk.mtime;
  banner("The attempt file changed on disk (the coach or another editor saved it) while you had unsaved edits.", [
    ["Load the disk version (drops my edits)", async () => { useAttempt(disk); renderPanel(); }],
    ["Keep mine (overwrite the file)", async () => {
      useAttempt(await api("PUT", "/api/attempt", {text: getCode(), force: true}));
    }],
  ], "solve");
}

async function save() {
  if (!attempt) return true;
  try {
    attempt = await api("PUT", "/api/attempt", {text: getCode(), mtime: attempt.mtime});
    markDirty(getCode() !== attempt.text);  // still unsaved if he typed while it saved
    return true;
  } catch (e) {
    if (isConflict(e)) conflict(e.data); else fail(e);
    return false;
  }
}

async function saveParts(parts) {
  if (dirty && !(await save())) {
    const e = new Error("not saved"); e.shown = true; throw e;
  }
  if (!attempt) return;  // the solve ended meanwhile
  try {
    useAttempt(await api("PUT", "/api/attempt/parts", {...parts, mtime: attempt.mtime}));
  } catch (e) {
    if (isConflict(e)) { conflict(e.data); e.shown = true; }
    throw e;
  }
}

async function runTests() {
  if (dirty && !(await save())) return;
  $("results").innerHTML = "<p class='muted'>Running…</p>";
  try {
    renderResults(await api("POST", "/api/run", {}));
  } catch (e) {
    $("results").innerHTML = "";
    throw e;
  }
}

function renderResults(r) {
  const out = $("results");
  out.innerHTML = "";
  if (r.error) {  // above the table: after a time limit, it names the example that hung
    const pre = document.createElement("pre");
    pre.className = "fail";
    pre.textContent = r.error;
    out.append(pre);
  }
  if (!r.rows.length) return;
  const t = document.createElement("table");
  t.innerHTML = "<tr><th></th><th>input</th><th>expected</th><th>got</th></tr>";
  for (const row of r.rows) {
    const tr = t.insertRow();
    tr.className = row.ok ? "ok" : "fail";
    const got = row.got === null ? "" : row.error ? "error" : row.got;  // null: the example never finished
    for (const v of [row.ok ? "ok" : "FAIL", row.args, row.expected, got]) {
      tr.insertCell().textContent = v;
    }
    if (row.error || row.stdout) {
      const cell = t.insertRow().insertCell();
      cell.colSpan = 4;
      for (const [text, cls] of [[row.stdout, ""], [row.error, "err"]]) {
        if (!text) continue;
        const pre = document.createElement("pre");
        pre.className = cls;
        pre.textContent = text;
        cell.append(pre);
      }
    }
  }
  out.append(t);
}

// --- top bar -----------------------------------------------------------------
function renderBar() {
  const live = state.live;
  const stages = $("stages");
  stages.innerHTML = "";
  $("block-btn").hidden = !live || live.block.open;
  if (!live) {
    $("problem").textContent = "DSA Coach";
    $("rung").textContent = $("timer").textContent = "";
    return;
  }
  $("problem").innerHTML = `<a href="${escapeHtml(live.url)}" target="_blank" rel="noopener">${escapeHtml(live.problem)}</a>` +
    (live.labeled ? ` <span class="muted">${escapeHtml(live.pattern_name)}</span>` : "");
  STAGES.forEach(([name], i) => {
    const n = i + 1;
    const b = button(String(n), () => goTo(n));
    b.title = name;
    b.className = (n === live.stage ? "current" : n < live.stage ? "done" : "") + (n === view ? " viewing" : "");
    stages.append(b);
  });
  $("rung").textContent = `hint rung ${live.rung}/7`;
  const blk = live.block;
  $("timer").textContent = blk.open ? `block ${blk.number}: ${blk.elapsed} of ${blk.length} min`
    : `on a break after block ${blk.number}`;
  if (blk.open && blk.elapsed >= blk.length && blockBanner !== blk.number) {
    blockBanner = blk.number;
    blockOver();
  }
}

function goTo(n) {
  const live = state.live;
  if (n <= live.stage) { view = n; renderPanel(); renderBar(); return; }
  banner(`Which stage are you in? The solve is at stage ${live.stage} (${escapeHtml(STAGES[live.stage - 1][0])}).`, [
    [`Move to stage ${n} anyway`, async () => { await api("POST", "/api/solve/stage", {n}); view = n; await refresh(true); }],
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
  if (n === 7) return `Check my attempt in ${attempt.path}.`;
  return `I'm done with stage ${n} of ${live.problem}. Check it: my notes are in \`coach.py solve show --json\` and my attempt file is ${attempt.path}.`;
}

function problemBlock() {
  const box = document.createElement("details");
  box.className = "problem";
  box.open = !problemText || view === 1;
  const summary = document.createElement("summary");
  summary.textContent = "Problem statement";
  box.append(summary);
  if (problemText) {
    const pre = document.createElement("pre");
    pre.textContent = problemText;
    box.append(pre);
  } else {
    const slug = state.live.problem;
    const ta = document.createElement("textarea");
    ta.rows = 8;
    ta.placeholder = "Paste the problem statement from LeetCode. You only do this once per problem.";
    box.append(ta, button("Save statement", async () => {
      problemText = (await api("PUT", "/api/problem", {slug, text: ta.value})).text;
      renderPanel();
    }, true));
  }
  return box;
}

function textStage(panel, note, done, n) {
  const ta = field(panel, n === 7 ? "Notes (optional): your subgoals, or what you're unsure about" : "Your answer", note, true);
  ta.rows = 6;
  return async () => ta.value.trim();
}

function stageOne(panel, note, done) {
  const restate = field(panel, "The problem in one sentence", note, true);
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
    tr.innerHTML = '<td><input class="args" autocomplete="off" spellcheck="false"></td>' +
      '<td><input class="expected" autocomplete="off" spellcheck="false"></td><td><input type="checkbox" class="edge"></td><td></td>';
    tr.querySelector(".args").value = r.args;
    tr.querySelector(".expected").value = r.expected;
    tr.querySelector(".edge").checked = r.edge;
    tr.cells[3].append(button("×", () => { tr.remove(); gate(); }));
    tr.addEventListener("input", gate);
    tr.addEventListener("change", gate);
  };
  (attempt.examples.length ? attempt.examples : [undefined, undefined]).forEach((r) => addRow(r));
  restate.addEventListener("input", gate);
  panel.append(table, button("Add an example", () => addRow()));
  if (attempt.examples_error) {
    const p = document.createElement("p");
    p.className = "nudge";
    p.textContent = attempt.examples_error;
    panel.append(p);
  }
  const hint = document.createElement("p");
  hint.className = "muted";
  hint.textContent = "Done unlocks once you have a one-sentence restatement and at least one edge case.";
  panel.append(hint);
  setTimeout(gate);
  return async () => { await saveParts({examples: rows()}); return restate.value.trim(); };
}

function stageSix(panel) {
  const inputs = PLAN_FIELDS.map((f) => [f, field(panel, f, attempt.plan_card[f] || "", f === "Hand trace")]);
  return async () => {
    await saveParts({plan_card: Object.fromEntries(inputs.map(([f, el]) => [f, el.value]))});
    return null;  // the plan card lives in the attempt file's docstring, not in a stage note
  };
}

function stageEight(panel, note) {
  const parts = note ? note.split("\n\n") : [];
  const boxes = LOOK_BACK.map((q, i) => field(panel, q, (parts[i] || "").replace(/^[^:]*: /, ""), true));
  return async () => boxes.map((b, i) => `${LOOK_BACK[i].split(":")[0]}: ${b.value.trim()}`).join("\n\n");
}

function renderPanel() {
  const live = state.live;
  const n = view;
  const panel = $("panel");
  panel.innerHTML = "";
  const h = document.createElement("h2");
  h.textContent = `${n}. ${STAGES[n - 1][0]}`;
  const q = document.createElement("p");
  q.className = "question";
  q.textContent = STAGES[n - 1][1];
  panel.append(problemBlock(), h, q);

  const note = (live.notes || {})[String(n)] || "";
  let collect;  // saves this stage's parts of the attempt file, and returns the stage note (or null)
  const saveNote = async () => {
    const text = await collect();
    if (text !== null) await api("POST", "/api/solve/note", {stage: n, text});
    await refresh();
  };
  const done = button(n === 8 ? "Done: end the solve" : `Done with stage ${n}`, async () => {
    await saveNote();
    if (!state.live) return;  // the solve ended meanwhile
    if (n === 8) return endForm(panel);
    if (n >= state.live.stage) await api("POST", "/api/solve/stage", {n: n + 1});
    view = n + 1;
    await refresh(true);
  }, true);
  collect = ({1: stageOne, 6: stageSix, 8: stageEight}[n] || textStage)(panel, note, done, n);

  if (n === 7 && !PLAN_FIELDS.slice(0, 6).some((f) => (attempt.plan_card[f] || "").trim())) {
    const nudge = document.createElement("p");
    nudge.className = "nudge";
    nudge.textContent = "The plan card (stage 6) is empty. Bugs like a missed last candidate show up in the hand trace before they show up in the tests.";
    panel.append(nudge);
  }
  const actions = document.createElement("div");
  actions.className = "actions";
  actions.append(button("Save", saveNote, true), done, button("Ask the coach", () => copyPrompt(askPrompt(n))));
  panel.append(actions);
}

function endForm(panel) {
  if (panel.querySelector(".end-form")) return;  // a second click on Done
  const box = document.createElement("div");
  box.className = "end-form";
  box.innerHTML = "<h3>End the solve</h3>";
  const outcome = document.createElement("select");
  for (const o of ["solved", "partial", "failed"]) outcome.add(new Option(o, o));
  const lesson = field(box, "One-line lesson (goes into the problem's notes)", "", false);
  box.append(outcome, button("Log it", () => endSolve(outcome.value, lesson.value.trim()), true));
  panel.append(box);
}

async function endSolve(outcome, note) {
  if (dirty && !(await save())) return;  // the code goes into the attempt file before the attempt is logged
  const out = await api("POST", "/api/solve/end", {outcome, note});
  solveGone();
  banner(escapeHtml(out.message));
  await refresh();
}

// --- start screen ------------------------------------------------------------
function renderStart() {
  const nx = state.next || {};
  const pick = (nx.kind === "new" || nx.kind === "resolve") && nx.problem ? nx.problem : "";
  $("next-pick").innerHTML = pick
    ? `Next pick: <b>${escapeHtml(pick)}</b> (${nx.kind === "resolve" ? "a re-solve from a blank page" : "a new problem"})`
    : "No pick from <code>coach.py next</code> right now. Type a slug.";
  if (pick && !$("slug").value) $("slug").value = pick;
  const due = state.due;
  $("due-line").textContent = due ? `Due: ${due.resolves.length} re-solve(s), ${due.cards.length} card(s), ${due.drafts} draft card(s).` : "";
  gateStart();
}
const gateStart = () => { $("start-btn").disabled = !($("slug").value.trim() && $("confidence").value); };

async function start() {
  const nx = state.next || {};
  const problem = $("slug").value.trim().toLowerCase();
  const body = {problem, confidence: Number($("confidence").value)};
  if ($("pattern").value.trim()) body.pattern = $("pattern").value.trim();
  if (nx.problem === problem && nx.kind === "new") {
    body.pattern = body.pattern || nx.pattern;
    if (nx.block === false) body.unlabeled = true;
  }
  if (nx.problem === problem && nx.kind === "resolve") body.mode = "review";
  await api("POST", "/api/solve/start", body);
  $("slug").value = $("pattern").value = $("confidence").value = "";
  view = 1;
  await refresh(true);
}

// --- the loop ----------------------------------------------------------------
let queued = null;       // a refresh asked for while one was running: null, or whether it wanted a redraw

async function refresh(redraw = false) {
  if (busy) { queued = Boolean(queued) || redraw; return; }
  busy = true;
  try {
    state = await api("GET", "/api/state");
    if ($("banner").dataset.kind === "offline") $("banner").hidden = true;  // it's answering again
    const live = state.live;
    if (attempt && (!live || live.file !== attempt.file)) solveGone();
    $("start").hidden = !!live;
    $("solve").hidden = !live;
    if (!live) { renderBar(); renderStart(); return; }
    if (!attempt) {
      useAttempt(await api("GET", "/api/attempt"));
      problemText = (await api("GET", "/api/problem?slug=" + encodeURIComponent(live.problem))).text;
      view = view || live.stage;
      redraw = true;
    } else if (!pending && state.attempt_mtime !== attempt.mtime && state.attempt_mtime !== warnedMtime) {
      // not while a save of the page's own is in flight: its answer brings the new mtime
      const disk = await api("GET", "/api/attempt");
      if (dirty) conflict(disk); else { useAttempt(disk); redraw = view === 1 || view === 6; }
    }
    if (lastStage !== null && live.stage !== lastStage && view === lastStage) { view = live.stage; redraw = true; }
    lastStage = live.stage;
    if (redraw) renderPanel();
    renderBar();
  } catch (e) {
    fail(e);
  } finally {
    busy = false;
    if (queued !== null) { const r = queued; queued = null; refresh(r); }
  }
}

document.addEventListener("DOMContentLoaded", () => {
  setupEditor();
  $("run-btn").onclick = () => change(runTests, $("run-btn"));
  $("start-btn").onclick = () => change(start, $("start-btn"));
  $("start-btn").gate = gateStart;
  $("slug").oninput = gateStart;
  $("confidence").onchange = gateStart;
  $("block-btn").onclick = () => change(async () => { await api("POST", "/api/solve/block", {}); await refresh(); }, $("block-btn"));
  refresh();
  setInterval(refresh, 3000);
});
