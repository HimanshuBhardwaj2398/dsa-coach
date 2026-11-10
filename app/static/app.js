"use strict";
// Small helpers shared by the views (nav.js), the recovery of drafts from the old Solve tab, and the prompt handoff.

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
document.addEventListener("DOMContentLoaded", () => {
  showRecovery();
  $("copy-prompt").onclick = copyHandoff;
  $("close-handoff").onclick = () => { $("handoff").hidden = true; };
});
