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

// The explainer: a link when there is one; otherwise the coach writes it, and the page checks on the job.
function explainerBlock(p) {
  const box = withClass(document.createElement("section"), "explainer");
  if (p.explainer) {
    box.append(withClass(link("Read the explainer", `/explainer/${p.key}`, true), "button primary"));
  } else if (!p.format) {
    offerExplainer(p.key, box);
    checkExplainer(p.key, box);  // a job started earlier may still be running
  }
  return box;
}
function offerExplainer(key, box, note = "No explainer yet. The coach writes one from real Python traces, with a prediction to make at each step.") {
  const write = withClass(button("Write the explainer", () => writeExplainer(key, box)), "primary");
  box.replaceChildren(withClass(elem("p", note), "hint"), write);
}
async function writeExplainer(key, box) {
  await api("POST", "/api/explainer", {pattern: key});
  await checkExplainer(key, box);
}
async function checkExplainer(key, box) {
  let s;
  try {
    s = await api("GET", "/api/explainer?pattern=" + encodeURIComponent(key));
  } catch (e) {
    return fail(e);
  }
  if (route(location.hash).key !== key) return;  // he left the page
  if (s.state === "running") {
    box.replaceChildren(withClass(elem("p", "The coach is writing it. This usually takes one to three minutes."), "hint"));
    pollTimer = setTimeout(() => checkExplainer(key, box), POLL_MS);
  } else if (s.state === "error") {
    offerExplainer(key, box, s.error);
  } else if (s.state === "done") {
    mapData = await api("GET", "/api/map");
    if (mapData.patterns.find((x) => x.key === key)?.explainer) renderLearn(key);
    else offerExplainer(key, box, "The coach finished but didn't register an explainer. Try again, or ask it in the chat.");
  }
}

window.addEventListener("hashchange", show);
document.addEventListener("DOMContentLoaded", show);
