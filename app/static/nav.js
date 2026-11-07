"use strict";
// The Map and Learn views. Loaded after app.js; uses its $, elem, button, api, fail, state and editor.

const STATUS_LABEL = {"not started": "Not started", exploring: "Exploring", learning: "Learning",
  practicing: "Practising", retained: "Retained", ready: "Ready"};
const FOUNDATIONS = ["Python for interviews", "Complexity", "How to approach a problem"];  // written for testers
const POLL_MS = 3000;
let mapData = null;
let pollTimer = null;

// --- pure helpers -------------------------------------------------------------
function route(hash) {  // "#/map" (the default), "#/learn/<key>" or "#/solve"
  const [, view = "map", key = ""] = String(hash || "").split("/");
  return ["map", "learn", "solve"].includes(view) ? {view, key} : {view: "map", key: ""};
}
const statusLabel = (s) => STATUS_LABEL[s] || s;
function listsText(lists) {
  return [["Blind 75", lists.blind75], ["NeetCode 150", lists.nc150]]
    .filter(([, l]) => l.total).map(([name, l]) => `${name} ${l.done}/${l.total}`).join(" · ");
}
function byWeek(patterns) {
  const weeks = new Map();
  for (const p of patterns) {
    if (!weeks.has(p.week)) weeks.set(p.week, []);
    weeks.get(p.week).push(p);
  }
  return [...weeks.entries()].sort((a, b) => a[0] - b[0]);
}

// --- small DOM helpers ----------------------------------------------------------
const withClass = (el, className) => Object.assign(el, {className});
function link(text, href, newTab = false) {
  const a = Object.assign(elem("a", text), {href});
  if (newTab) Object.assign(a, {target: "_blank", rel: "noopener"});
  return a;
}
function list(items) {
  const ul = document.createElement("ul");
  for (const item of items) {
    const li = document.createElement("li");
    li.append(item);
    ul.append(li);
  }
  return ul;
}

// --- routing --------------------------------------------------------------------
async function show() {
  const {view, key} = route(location.hash);
  document.body.dataset.view = view;
  clearTimeout(pollTimer);
  if (view === "solve") {
    if (editor) editor.refresh();  // CodeMirror measures wrong while hidden
    return;
  }
  try {
    mapData = await api("GET", "/api/map");
  } catch (e) {
    return fail(e);
  }
  if (view === "map") renderMap(); else renderLearn(key);
}

// --- the map ----------------------------------------------------------------------
function renderMap() {
  const strip = withClass(document.createElement("section"), "next-strip");
  strip.append(withClass(elem("p", "Next up"), "eyebrow"), elem("p", mapData.next_text));
  if (mapData.next_url) strip.append(link("Open on LeetCode", mapData.next_url, true));
  if (state?.live) strip.append(link(`Resume ${state.live.problem}`, "#/solve"));
  const weeks = withClass(document.createElement("div"), "weeks");
  weeks.append(week("Foundations", FOUNDATIONS.map(stub)));
  for (const [n, patterns] of byWeek(mapData.patterns)) weeks.append(week(`Week ${n}`, patterns.map(node)));
  $("map").replaceChildren(strip, weeks);
}
function week(title, nodes) {
  const col = withClass(document.createElement("section"), "week");
  col.append(withClass(elem("h2", title), "eyebrow"), ...nodes);
  return col;
}
function stub(name) {
  const d = withClass(document.createElement("div"), "node stub");
  d.append(elem("b", name), withClass(elem("span", "coming later"), "meta"));
  return d;
}
function node(p) {
  const a = withClass(link("", `#/learn/${p.key}`), `node s-${p.status.replace(" ", "-")}`);
  a.append(elem("b", p.name), withClass(elem("span", statusLabel(p.status)), "status"),
    withClass(elem("span", p.format ? "practised with the coach in chat" : listsText(p.lists)), "meta"));
  if (p.due) a.append(withClass(elem("span", `${p.due} due`), "due"));
  return a;
}

// --- a pattern's Learn page ---------------------------------------------------------
function renderLearn(key) {
  const p = mapData.patterns.find((x) => x.key === key);
  if (!p) { location.hash = "#/map"; return; }
  const page = withClass(document.createElement("article"), "learn");
  page.append(link("← Map", "#/map"), withClass(elem("p", `Week ${p.week} · ${statusLabel(p.status)}`), "eyebrow"),
    elem("h1", p.name), elem("h2", "Cues"), list(p.cues), elem("h2", "Invariant"), elem("p", p.invariant),
    elem("h2", "Template"), elem("pre", p.template), explainerBlock(p));
  if (p.resources.length) page.append(elem("h2", "Read"), list(p.resources.map((r) => link(r.title, r.url, true))));
  if (p.problems.length) page.append(elem("h2", "Problems"), problemTable(p.problems));
  $("learn").replaceChildren(page);
}

function problemTable(problems) {
  const t = withClass(document.createElement("table"), "problems");
  t.innerHTML = "<tr><th>Problem</th><th>Difficulty</th><th>Status</th><th>Next re-solve</th></tr>";
  for (const x of problems) {
    const tr = t.insertRow();
    const name = tr.insertCell();
    name.append(link(x.title, x.url, true));
    if (x.lists.includes("blind75")) name.append(withClass(elem("span", "Blind 75"), "tag"));
    tr.insertCell().textContent = x.difficulty;
    tr.insertCell().textContent = statusLabel(x.status) + (x.last_outcome ? ` (last: ${x.last_outcome})` : "");
    tr.insertCell().textContent = x.due ? "due now" : x.next_due || "";
  }
  return t;
}

// --- the explainer: the coach writes it, or revises it from what he says should change ----------------------
// The jobs this page started or saw running, by pattern ("write", "revise" or "seen"). Only these are checked when a
// list of cards is drawn, so drawing it doesn't ask about every pattern.
const explainerJobs = new Map();
const explainerNotes = new Map();  // pattern -> a line to show once its job has ended
const explainerFeedback = new Map();  // pattern -> what he last said should change, until a revision succeeds
const statusNote = (text) => Object.assign(withClass(elem("p", text), "hint"), {role: "status"});

// redraw: draws the view again with fresh map data once a job ends. compact: the actions of a card that links to
// the explainer itself, rather than the Learn page's buttons.
function explainerBlock(p, redraw = () => reloadLearn(p.key), compact = false) {
  const box = withClass(document.createElement("section"), compact ? "explainer compact" : "explainer");
  if (p.format) return box;
  idleExplainer(p, box, redraw, compact);
  if (!compact || explainerJobs.has(p.key)) checkExplainer(p, box, redraw, compact);  // a job may still be running
  return box;
}
function idleExplainer(p, box, redraw, compact, said = explainerNotes.get(p.key)) {
  const parts = said ? [statusNote(said)] : [];
  if (p.explainer) {
    if (!compact) parts.push(withClass(link("Read the explainer", `/explainer/${p.key}`, true), "button primary"));
    parts.push(withClass(button(compact ? "Improve this page" : "Improve it", () => improveForm(p, box, redraw, compact)),
      compact ? "text-action" : "ghost"));
  } else {
    if (!said && !compact) parts.push(statusNote("No explainer yet. The coach writes one from real Python traces, with a prediction to make at each step."));
    parts.push(withClass(button(compact ? "Write the interactive explainer" : "Write the explainer",
      () => startExplainer(p, box, redraw, compact, {})), compact ? "text-action" : "primary"));
  }
  box.replaceChildren(...parts);
}
// What he says should change goes to the coach, which revises the page in place. His words come back into the box
// until a revision succeeds, so a failed request or job doesn't lose them.
function improveForm(p, box, redraw, compact) {
  const form = withClass(document.createElement("form"), "improve");
  const text = Object.assign(document.createElement("textarea"), {rows: 3, maxLength: 2000, required: true,
    value: explainerFeedback.get(p.key) || "", placeholder: "For example: the pop step is unclear. Show it with two equal heights."});
  text.oninput = () => explainerFeedback.set(p.key, text.value);
  const label = elem("label", "What should change?");
  label.append(text);
  const revise = withClass(elem("button", "Revise it"), "primary");
  const cancel = withClass(button("Cancel", () => {
    idleExplainer(p, box, redraw, compact);
    box.querySelector("button")?.focus();
  }), "ghost");
  cancel.type = "button";
  const actions = withClass(document.createElement("div"), "actions");
  actions.append(revise, cancel);
  form.append(label, withClass(elem("p", "Attempting one problem first often shows what the page is really missing."), "hint"), actions);
  form.onsubmit = (e) => {
    e.preventDefault();
    revise.disabled = true;
    startExplainer(p, box, redraw, compact, {feedback: text.value}).catch(fail).finally(() => { revise.disabled = false; });
  };
  box.replaceChildren(form);
  text.focus();
}
async function startExplainer(p, box, redraw, compact, extra) {
  await api("POST", "/api/explainer", {pattern: p.key, ...extra});
  explainerJobs.set(p.key, extra.feedback === undefined ? "write" : "revise");
  explainerNotes.delete(p.key);
  await checkExplainer(p, box, redraw, compact);
}
// Only a job this page follows redraws the view when it ends: an old job's "done" would otherwise redraw for ever.
async function checkExplainer(p, box, redraw, compact) {
  let s;
  try {
    s = await api("GET", "/api/explainer?pattern=" + encodeURIComponent(p.key));
  } catch (e) {
    return fail(e);
  }
  if (!box.isConnected) return;  // he left the page, or the view was drawn again
  const kind = explainerJobs.get(p.key);
  if (s.state === "running") {
    explainerJobs.set(p.key, kind || "seen");
    box.replaceChildren(statusNote("The coach is working on it. This usually takes one to three minutes."));
    pollTimer = setTimeout(() => checkExplainer(p, box, redraw, compact), POLL_MS);
    return;
  }
  explainerJobs.delete(p.key);
  if (s.state === "error") {
    idleExplainer(p, box, redraw, compact, s.error);
  } else if (s.state === "done" && kind) {
    if (kind === "revise") {
      explainerNotes.set(p.key, "Revised. Open it again to see the changes.");
      explainerFeedback.delete(p.key);
    }
    await redraw();
  } else if (s.state === "done" && !p.explainer) {
    idleExplainer(p, box, redraw, compact, "The coach finished but didn't register an explainer. Try again, or ask it in the chat.");
  }
}
async function reloadLearn(key) {
  mapData = await api("GET", "/api/map");
  const {view, key: shown} = route(location.hash);
  if (view === "learn" && shown === key) renderLearn(key);
}

window.addEventListener("hashchange", show);
document.addEventListener("DOMContentLoaded", show);
