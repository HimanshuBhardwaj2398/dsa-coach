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
let problemText = null;  // problems/<slug>/problem.md, or null before it's pasted
let view = null;         // the stage shown in the panel
let lastStage = null;    // the live stage at the previous poll
let editor = null;       // CodeMirror, or null when the CDN didn't load and the textarea is used
let dirty = false;       // the editor has code that isn't in the file
let panelDirty = false;  // the stage's boxes have text that isn't saved (an unsaved statement: statementDraft)
let savePanel = null;    // saves the panel shown: its parts of the attempt file, then its stage note
let focusNext = false;   // after Done: focus the next stage's first box once it's drawn
let barFile = null;      // the solve the bar's problem link and stage buttons were built for
let lastPick = null;     // the start screen's pick when the slug box was last filled from it
let blockBanner = null;  // the block number the "block is over" banner was shown for
let finishSent = null;   // the solve whose stage-8 finish prompt was copied: the coach logs it from the chat
let warnedMtime = null;  // the disk mtime we already warned about
let busy = false;        // a refresh is running
let chain = Promise.resolve();  // the page's state changes (its POSTs and PUTs), one at a time, in click order
let pending = 0;         // state changes waiting or in flight
let finished = 0;        // state changes done: a poll that was out while one finished may predate it

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
  const run = chain.then(fn).catch(fail).finally(() => {
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

function field(parent, label, value, multiline) {
  const input = document.createElement(multiline ? "textarea" : "input");
  if (multiline) input.rows = 3;
  input.setAttribute("autocomplete", "off");
  input.value = value || "";
  return labelled(parent, label, input);
}

async function copyPrompt(text, copied = "Copied. Paste it into the coach chat:") {
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

// The live solve went away: ended from the chat, or replaced by another one. Unsaved code and stage text aren't
// dropped silently.
function solveGone() {
  const fields = attempt && panelDirty ? panelFields() : "";
  if ($("banner").dataset.kind === "solve") $("banner").hidden = true;  // its buttons were for that solve
  if (attempt && (dirty || fields)) rescue(dirty ? getCode() : "", fields);
  else if (attempt && finishSent === attempt.file) banner("The coach logged the solve.");
  attempt = problemText = view = lastStage = blockBanner = warnedMtime = savePanel = finishSent = null;
  panelDirty = focusNext = false;
  // nothing of that solve may stay on screen to act on the next one, or to be typed into while it loads
  $("panel").innerHTML = "";
  setCode("");
  $("file").textContent = "";
  $("results").innerHTML = "";
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

// parts: only what he changed in the panel, so edits made in the editor to the rest survive. The editor's code is
// saved first, since the parts are written into the file on disk.
async function saveParts(parts) {
  if (dirty && !(await save())) {
    const e = new Error("not saved"); e.shown = true; throw e;
  }
  if (!attempt || !Object.keys(parts).length) return;  // the solve ended meanwhile, or nothing changed
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
  $("block-btn").hidden = !live || live.block.open;
  if (!live) {
    barFile = null;
    stages.replaceChildren();
    $("problem").textContent = "DSA Coach";
    $("rung").textContent = $("timer").textContent = "";
    return;
  }
  if (barFile !== live.file) {  // once per solve: built again on every poll, they'd lose clicks and keyboard focus
    barFile = live.file;
    const link = Object.assign(elem("a", live.problem), {href: live.url, target: "_blank", rel: "noopener"});
    $("problem").replaceChildren(link);
    if (live.labeled) $("problem").append(" ", Object.assign(elem("span", live.pattern_name), {className: "muted"}));
    stages.replaceChildren(...STAGES.map(([name], i) => {
      const b = button(String(i + 1), () => goTo(i + 1));
      b.title = name;
      b.setAttribute("aria-label", `Stage ${i + 1}: ${name}`);
      return b;
    }));
  }
  [...stages.children].forEach((b, i) => {
    const n = i + 1;
    b.className = (n === live.stage ? "current" : n < live.stage ? "done" : "") + (n === view ? " viewing" : "");
    if (n === live.stage) b.setAttribute("aria-current", "step"); else b.removeAttribute("aria-current");
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

// Leaving a stage saves what he typed in it first: the panel is drawn again for the stage he goes to.
function goTo(n) {
  const live = state.live;
  if (n <= live.stage) {
    return change(async () => {
      if (panelDirty && savePanel) await savePanel();
      if (!state.live || !attempt) return;  // the solve ended meanwhile, or hasn't loaded yet
      view = n; renderPanel(); renderBar();
    });
  }
  banner(`Which stage are you in? The solve is at stage ${live.stage} (${STAGES[live.stage - 1][0]}).`, [
    [`Move to stage ${n} anyway`, async () => {
      if (panelDirty && savePanel) await savePanel();
      await api("POST", "/api/solve/stage", {n});
      view = n;
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
  if (n === 7) return `Check my attempt in ${attempt.path}.`;
  return `I'm done with stage ${n} of ${live.problem}. Check it: my notes are in \`coach.py solve show --json\` and my attempt file is ${attempt.path}.`;
}

// draft: a statement pasted into the box before the panel was drawn again, and not saved yet
function problemBlock(draft = "") {
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
    ta.value = draft;
    ta.placeholder = "Paste the problem statement from LeetCode. You only do this once per problem.";
    ta.setAttribute("aria-label", "Problem statement");
    box.append(ta, button("Save statement", async () => {
      problemText = (await api("PUT", "/api/problem", {slug, text: ta.value})).text;
      box.replaceWith(problemBlock());  // only this box: what he's typed in the rest of the panel stays
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
    tr.innerHTML = '<td><input class="args" aria-label="inputs, as Python values" autocomplete="off" spellcheck="false"></td>' +
      '<td><input class="expected" aria-label="predicted output" autocomplete="off" spellcheck="false"></td>' +
      '<td><input type="checkbox" class="edge" aria-label="edge case"></td><td></td>';
    tr.querySelector(".args").value = r.args;
    tr.querySelector(".expected").value = r.expected;
    tr.querySelector(".edge").checked = r.edge;
    const remove = button("×", () => { tr.remove(); panelDirty = true; gate(); });
    remove.setAttribute("aria-label", "Remove this example");
    tr.cells[3].append(remove);
    tr.addEventListener("input", gate);
    tr.addEventListener("change", gate);
  };
  (attempt.examples.length ? attempt.examples : [undefined, undefined]).forEach((r) => addRow(r));
  let drawn = JSON.stringify(rows());  // EXAMPLES is written only if the rows changed here: edits in the editor stay
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
    const el = field(panel, f, attempt.plan_card[f] || "", f === "Hand trace");
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
    return field(panel, q, part.startsWith(lookHead(i)) ? part.slice(lookHead(i).length) : part, true);
  });
  // a blank line inside an answer would read back as the start of the next one
  return async () => boxes.map((b, i) => lookHead(i) + b.value.trim().replace(/\n\s*\n/g, "\n")).join("\n\n");
}

function renderPanel() {
  const live = state.live;
  const n = view;
  const panel = $("panel");
  const draft = panel.querySelector(".problem textarea")?.value || "";
  panel.innerHTML = "";
  panelDirty = false;
  const h = document.createElement("h2");
  h.textContent = `${n}. ${STAGES[n - 1][0]}`;
  const q = document.createElement("p");
  q.className = "question";
  q.textContent = STAGES[n - 1][1];
  panel.append(problemBlock(draft), h, q);

  const note = (live.notes || {})[String(n)] || "";
  let collect;  // saves this stage's parts of the attempt file, and returns the stage note (or null)
  const saveNote = async () => {
    panelDirty = false;  // what he types from here on counts as unsaved again
    try {
      const text = await collect();
      if (text !== null) {
        await api("POST", "/api/solve/note", {stage: n, text});
        // as the next poll will have it, so drawing this stage again before that poll shows what he wrote
        if (state.live) state.live.notes = {...state.live.notes, [n]: text};
      }
    } catch (e) {
      panelDirty = true;
      throw e;
    }
    await refresh();
  };
  savePanel = saveNote;
  let finish;  // stage 8: the outcome and lesson boxes
  const done = button(n === 8 ? "Done: ask the coach to log it" : `Done with stage ${n}`, async () => {
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
  const actions = document.createElement("div");
  actions.className = "actions";
  // The prompt sends the coach to the file and to `solve show --json`, so both are saved before it's copied.
  const ask = async () => {
    if (dirty && !(await save())) return;
    await saveNote();
    if (state.live && attempt) await copyPrompt(askPrompt(n));
  };
  actions.append(button("Save", saveNote, true), ...(n === 8 ? [] : [done]), button("Ask the coach", ask, true));
  panel.append(actions);
  if (n === 8) {
    finish = finishBlock(done);
    panel.append(finish.box);
  }
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
  labelled(box, "Outcome", outcome);
  const lesson = field(box, "Lesson (one line)", "", false);
  done.gate = () => { done.disabled = !outcome.value; };
  outcome.addEventListener("change", done.gate);
  done.gate();
  box.append(done);
  return {box, outcome, lesson};
}

async function finishPrompt(outcome, lesson) {
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

// --- start screen ------------------------------------------------------------
function renderStart() {
  const nx = state.next || {};
  const pick = (nx.kind === "new" || nx.kind === "resolve") && nx.problem ? nx.problem : "";
  $("next-pick").replaceChildren(...(pick
    ? ["Next pick: ", elem("b", pick), ` (${nx.kind === "resolve" ? "a re-solve from a blank page" : "a new problem"})`]
    : ["No pick from ", elem("code", "coach.py next"), " right now. Type a slug."]));
  if (pick !== lastPick) {  // a new pick fills the slug box, unless he typed a slug of his own into it
    const slug = $("slug");
    if (!slug.value.trim() || slug.value === lastPick) slug.value = pick;
    lastPick = pick;
  }
  const due = state.due;
  $("due-line").textContent = due ? `Due: ${due.resolves.length} re-solve(s), ${due.cards.length} card(s), ${due.drafts} draft card(s).` : "";
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
const statementDraft = () => ($("panel").querySelector(".problem textarea")?.value || "").trim();

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
    if ($("banner").dataset.kind === "offline") $("banner").hidden = true;  // it's answering again
    const live = state.live;
    if (attempt && (!live || live.file !== attempt.file)) solveGone();
    $("start").hidden = !!live;
    $("solve").hidden = !live;
    if (!live) { renderBar(); renderStart(); return; }
    if (!attempt) {  // both or neither: a failed load leaves attempt null, so the next poll loads it again
      const [a, p] = await Promise.all([api("GET", "/api/attempt"),
        api("GET", "/api/problem?slug=" + encodeURIComponent(live.problem))]);
      if (stale()) return;
      useAttempt(a);
      problemText = p.text;
      view = view || live.stage;
      redraw = true;
    } else if (!pending && state.attempt_mtime !== attempt.mtime && state.attempt_mtime !== warnedMtime) {
      // not while a save of the page's own is in flight: its answer brings the new mtime
      const disk = await api("GET", "/api/attempt");
      if (stale()) return;
      if (dirty) conflict(disk); else { useAttempt(disk); if (redrawForFile()) redraw = true; }
    }
    // the chat moved the stage: follow it, unless he's typing in the panel
    if (lastStage !== null && live.stage !== lastStage && view === lastStage && !panelDirty) { view = live.stage; redraw = true; }
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
  $("slug").oninput = gateStart;
  $("confidence").onchange = gateStart;
  $("block-btn").onclick = () => change(async () => { await api("POST", "/api/solve/block", {}); await refresh(); }, $("block-btn"));
  // the statement box isn't one of the stage's boxes: Save statement saves it, and a redraw carries it over
  $("panel").addEventListener("input", (e) => { if (!e.target.closest(".problem")) panelDirty = true; });
  document.addEventListener("keydown", saveKey);
  window.addEventListener("beforeunload", (e) => {  // closing or reloading the tab would drop unsaved text
    if (dirty || panelDirty || statementDraft()) { e.preventDefault(); e.returnValue = ""; }
  });
  refresh();
  setInterval(refresh, 3000);
});
