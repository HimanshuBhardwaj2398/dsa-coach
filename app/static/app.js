"use strict";
// The learning app's page: Today (the live solve, what's due, what's next), the Map, and a pattern's Learn page.
// Everything shown comes from /api/map; the page writes nothing. Sections: helpers, loading and routing, the three
// views, the explainer handoff, the old drafts, and the wiring at the end.

const $ = (id) => document.getElementById(id);
const elem = (tag, text = "", className = "") => Object.assign(document.createElement(tag), {textContent: text, className});
const plural = (n, word) => `${n} ${word}${n === 1 ? "" : "s"}`;
function button(text, action, className = "") {
  const b = elem("button", text, className);
  b.type = "button";
  b.onclick = () => Promise.resolve().then(action).catch(fail);
  return b;
}
function link(text, href, newTab = false) {
  const a = Object.assign(elem("a", text), {href});
  if (newTab) Object.assign(a, {target: "_blank", rel: "noopener"});
  return a;
}
function fail(error) {
  $("notice").replaceChildren(elem("span", error.message + " "), button("Try again", () => show()));
  $("notice").hidden = false;
}
async function getMap() {
  let response;
  try { response = await fetch("/api/map"); }
  catch { throw new Error("The learning app isn't answering. Start python3 app/server.py, then try again."); }
  const data = await response.json();
  if (!response.ok) throw new Error(data.error || "Couldn't read the notebook.");
  return data;
}

// Before 0.9.0 the Solve tab kept unsaved text in this browser. Offer it as a download; never parse or clear it.
// Remove this section, and #recovery in index.html and app.css, after 2026-12-10.
function legacyDrafts(storage) {
  const drafts = {};
  for (let i = 0; i < storage.length; i++) {
    const key = storage.key(i);
    if (key?.startsWith("dsa-coach:draft:")) drafts[key] = storage.getItem(key);
  }
  return drafts;
}
function downloadDrafts() {
  const blob = new Blob([JSON.stringify(legacyDrafts(localStorage), null, 2)], {type: "application/json"});
  const a = Object.assign(elem("a"), {href: URL.createObjectURL(blob), download: "dsa-coach-earlier-drafts.json"});
  document.body.append(a);
  a.click();
  a.remove();
  setTimeout(() => URL.revokeObjectURL(a.href), 1000);
}
function showRecovery() {
  let count = 0;
  try { count = Object.keys(legacyDrafts(localStorage)).length; } catch { return; }  // storage blocked: nothing to offer
  if (!count) return;
  $("recovery").replaceChildren(
    elem("p", `${plural(count, "unsaved draft")} from the old Solve tab ${count === 1 ? "is" : "are"} still in this browser. `),
    button("Download them", downloadDrafts));
  $("recovery").hidden = false;
}

// The coach writes and revises explainers in the chat: the page hands it a prompt to paste.
function openHandoff(prompt) {
  $("handoff-prompt").value = prompt;
  $("copy-status").textContent = "";
  $("handoff").hidden = false;
  $("handoff").scrollIntoView({block: "nearest"});
  $("copy-prompt").focus();
}
async function copyHandoff() {
  try {
    await navigator.clipboard.writeText($("handoff-prompt").value);
    $("copy-status").textContent = "Copied. Paste it into your coach chat.";
  } catch {
    $("handoff-prompt").select();
    $("copy-status").textContent = "Couldn't reach the clipboard. The prompt is selected: copy it with ⌘C or Ctrl+C.";
  }
}

const STATUS_LABEL = {"not started": "Not started", exploring: "Exploring", learning: "Learning",
  practicing: "Practising", retained: "Retained", ready: "Ready"};
let mapData = null;
let loads = 0;  // each load's number: a slow answer to an older load is dropped, not drawn over a newer one

// --- pure helpers -------------------------------------------------------------
function route(hash) {  // "#/today" (the default), "#/map" or "#/learn/<key>"; anything else, such as an old "#/solve", is Today
  const [, view = "today", key = ""] = String(hash || "").split("/");
  return ["today", "map", "learn"].includes(view) ? {view, key} : {view: "today", key: ""};
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
function section(...children) {
  const s = elem("section");
  s.append(...children);
  return s;
}
function list(items) {
  const ul = elem("ul");
  for (const item of items) {
    const li = elem("li");
    li.append(item);
    ul.append(li);
  }
  return ul;
}

// --- loading and routing -----------------------------------------------------------
async function show(reload = true) {
  const {view, key} = route(location.hash);
  document.body.dataset.view = view === "learn" ? "map" : view;
  if (reload || !mapData) {
    const mine = ++loads;
    $("content").setAttribute("aria-busy", "true");
    let data;
    try { data = await getMap(); } catch (e) { if (mine === loads) fail(e); return; }
    if (mine !== loads) return;
    mapData = data;
    $("notice").hidden = true;
    $("content").setAttribute("aria-busy", "false");
  }
  const page = view === "map" ? renderMap() : view === "learn" ? renderLearn(key) : renderToday();
  if (page) $("content").replaceChildren(page);
}

// --- Today ---------------------------------------------------------------------------
function renderToday() {
  const page = elem("article", "", "today");
  const plan = mapData.plan;
  page.append(elem("p", `Day ${plan.day} of ${plan.total_days} · week ${plan.week} · ${plan.phase}`, "eyebrow"));
  const live = mapData.live;
  if (live) {
    const title = elem("h1", `Solving ${live.problem}`);
    if (live.labeled) title.append(elem("span", ` · ${live.pattern_name}`, "muted"));  // naming it is hint rung 3
    page.append(section(title, elem("p", live.line), link("Open on LeetCode", live.url, true),
      elem("p", "Ask for checks and hints in your coach chat.", "hint")));
  } else {
    const next = section(elem("h1", "Next up"), elem("p", mapData.next_text));
    if (mapData.next_url) next.append(link("Open on LeetCode", mapData.next_url, true));
    page.append(next);
  }
  const due = mapData.due;
  const counts = [due.cards.length && plural(due.cards.length, "card") + " to quiz",
    due.drafts && plural(due.drafts, "draft card") + " to approve",
    due.inbox.length && plural(due.inbox.length, "session delta") + " to import"].filter(Boolean);
  const dueBox = section(elem("h2", "Due"));
  if (due.resolves.length) {
    dueBox.append(list(due.resolves.map((r) => {
      const item = elem("span");
      item.append(link(r.problem, r.url, true),
        elem("span", r.overdue_days ? ` · ${plural(r.overdue_days, "day")} overdue` : " · due today", "muted"));
      return item;
    })));
  }
  if (counts.length) dueBox.append(elem("p", counts.join(" · ") + ". Ask the coach in chat."));
  if (!due.resolves.length && !counts.length) dueBox.append(elem("p", "Nothing due.", "muted"));
  page.append(dueBox);
  return page;
}

// --- the map ----------------------------------------------------------------------
function renderMap() {
  const page = elem("article", "", "map");
  for (const [n, patterns] of byWeek(mapData.patterns)) {
    page.append(section(elem("h2", `Week ${n}`, "eyebrow"), ...patterns.map(node)));
  }
  return page;
}
function node(p) {
  const a = link("", `#/learn/${p.key}`);
  a.className = `node s-${p.status.replace(" ", "-")}`;
  a.append(elem("b", p.name), elem("span", statusLabel(p.status), "status"),
    elem("span", p.format ? "practised with the coach in chat" : listsText(p.lists), "meta"));
  if (p.due) a.append(elem("span", `${p.due} due`, "due"));
  return a;
}

// --- a pattern's Learn page ---------------------------------------------------------
function renderLearn(key) {
  const p = mapData.patterns.find((x) => x.key === key);
  if (!p) { location.hash = "#/map"; return null; }
  const page = elem("article", "", "learn");
  page.append(link("← Map", "#/map"), elem("p", `Week ${p.week} · ${statusLabel(p.status)}`, "eyebrow"), elem("h1", p.name));
  if (!p.format) page.append(explainerBlock(p));
  page.append(elem("h2", "Cues"), list(p.cues), elem("h2", "Invariant"), elem("p", p.invariant),
    elem("h2", "Template"), elem("pre", p.template));
  if (p.resources.length) page.append(elem("h2", "Read"), list(p.resources.map((r) => link(r.title, r.url, true))));
  if (p.problems.length) page.append(elem("h2", "Problems"), problemTable(p.problems));
  return page;
}
function problemTable(problems) {
  const t = elem("table", "", "problems");
  const head = t.createTHead().insertRow();
  for (const h of ["Problem", "Difficulty", "Status", "Next re-solve"]) head.append(elem("th", h));
  const body = t.createTBody();
  for (const x of problems) {
    const tr = body.insertRow();
    const name = tr.insertCell();
    name.append(link(x.title, x.url, true));
    if (x.lists.includes("blind75")) name.append(elem("span", "Blind 75", "tag"));
    tr.insertCell().textContent = x.difficulty;
    tr.insertCell().textContent = statusLabel(x.status) + (x.last_outcome ? ` (last: ${x.last_outcome})` : "");
    tr.insertCell().textContent = x.due ? "due now" : x.next_due || "";
  }
  return t;
}

// --- the explainer: open it, or hand the coach a prompt to write or revise it ----------------------------------
function explainerPrompt(p, feedback) {
  const file = `notebook/concepts/${p.key}/${p.key}-explainer.html`;
  if (feedback === undefined) {
    return `Use the dsa-coach skill. Write the interactive explainer for ${p.name} (${p.key}), following ` +
      `references/explainers.md. Save it as one self-contained HTML file at ${file} and register it with ` +
      `coach.py artifact add --concept ${p.key} --title "${p.name}, explained" --file ${file}.`;
  }
  return `Use the dsa-coach skill. Revise the interactive explainer for ${p.name} (${p.key}) at ${p.explainer ? "notebook/" + p.explainer : file}, ` +
    `following references/explainers.md. My feedback: ${JSON.stringify(feedback)}. Log it with coach.py log question ` +
    `--concept ${p.key}. Change what the feedback needs, keep what works, and save over the same file.`;
}
function explainerBlock(p) {
  const box = section();
  box.className = "explainer";
  if (p.explainer) {
    const open = link("Read the explainer", `/explainer/${p.key}`, true);
    open.className = "button primary";
    box.append(open, button("Improve it", () => improveForm(p, box), "ghost"));
  } else {
    box.append(elem("p", "No explainer yet. The coach writes one from real Python traces, with a prediction at each step.", "hint"),
      button("Ask the coach to write it", () => openHandoff(explainerPrompt(p)), "primary"));
  }
  return box;
}
function improveForm(p, box) {
  const form = elem("form", "", "improve");
  const text = Object.assign(elem("textarea"), {rows: 3, maxLength: 2000, required: true,
    placeholder: "For example: the pop step is unclear. Show it with two equal heights."});
  const label = elem("label", "What should change?");
  label.append(text);
  const actions = elem("div", "", "actions");
  actions.append(Object.assign(elem("button", "Make the prompt", "primary"), {type: "submit"}),
    button("Cancel", () => box.replaceWith(explainerBlock(p)), "ghost"));
  form.append(label, elem("p", "Attempting one problem first often shows what the page is really missing.", "hint"), actions);
  form.onsubmit = (e) => { e.preventDefault(); openHandoff(explainerPrompt(p, text.value.trim())); };
  box.replaceChildren(form);
  text.focus();
}

window.addEventListener("hashchange", () => show(false));
// The coach updates the notebook from the chat: coming back to this page or tab reads it again.
document.addEventListener("visibilitychange", () => { if (document.visibilityState === "visible" && $("handoff").hidden) show(); });
document.addEventListener("DOMContentLoaded", () => {
  $("refresh").onclick = () => show();
  $("copy-prompt").onclick = copyHandoff;
  $("close-handoff").onclick = () => { $("handoff").hidden = true; };
  showRecovery();
  show();
});
