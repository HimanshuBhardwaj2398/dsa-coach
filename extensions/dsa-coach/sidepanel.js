"use strict";
const frame = document.getElementById("coach");
const status = document.getElementById("status");
const address = document.getElementById("server");
let serverOrigin = null, ready = false, problem = null, generation = 0, windowId;
let selectionGeneration = 0;
const connection = document.getElementById("connection");
const connectionToggle = document.getElementById("connection-toggle");
function showConnection(open) {
  connection.hidden = !open;
  connection.open = open;
  connectionToggle.setAttribute("aria-expanded", String(open));
}
connectionToggle.onclick = () => showConnection(connection.hidden);

function sendProblem() {
  if (ready) frame.contentWindow.postMessage({type: "dsa-coach:problem", slug: problem}, serverOrigin);
}

async function activeProblem() {
  const current = ++selectionGeneration;
  const [tab] = await chrome.tabs.query({active: true, windowId});
  if (current !== selectionGeneration) return;
  problem = CoachExtension.problemSlug(tab?.url);
  sendProblem();
}

async function connect(value) {
  const current = ++generation;
  ready = false;
  status.hidden = false;
  status.textContent = "Connecting to your coach…";
  try {
    const origin = CoachExtension.serverOrigin(value);
    const response = await fetch(origin + "/companion", {signal: AbortSignal.timeout(5000)});
    if (!response.ok || !(await response.text()).includes('name="dsa-coach-app"')) {
      throw new Error("Restart the updated DSA Coach server, then connect again.");
    }
    if (current !== generation) return;
    serverOrigin = origin;
    address.value = origin;
    document.getElementById("full-app").href = origin + "/#/solve";
    frame.src = origin + "/companion#/solve";
    frame.hidden = false;
    showConnection(false);
    await chrome.storage.local.set({server: origin});
    setTimeout(() => {
      if (current === generation && !ready) {
        status.hidden = false;
        status.textContent = "The coach could not open here. Restart the updated server and reload the extension, then connect again.";
        showConnection(true);
      }
    }, 10000);
  } catch (error) {
    if (current !== generation) return;
    status.textContent = error.name === "TypeError" || error.name === "TimeoutError"
      ? "Coach is offline. Start the local server, then choose Connect."
      : error.message;
    showConnection(true);
  }
}

async function capture(kind) {
  const [tab] = await chrome.tabs.query({active: true, windowId});
  const slug = CoachExtension.problemSlug(tab?.url);
  if (!slug) throw new Error("Open a LeetCode problem in this window first.");
  let text = "", screenshot = null;
  if (kind === "text") {
    const [result] = await chrome.scripting.executeScript({
      target: {tabId: tab.id},
      func: () => (window.getSelection()?.toString() || document.querySelector("main")?.innerText || document.body.innerText).slice(0, 24000),
    });
    text = result?.result || "";
    if (!text.trim()) throw new Error("No page text found. Paste your code or capture a screenshot instead.");
  } else if (kind === "screenshot") {
    try {
      screenshot = await chrome.tabs.captureVisibleTab(windowId, {format: "jpeg", quality: 75});
    } catch {
      throw new Error("Click the DSA Coach toolbar icon while on LeetCode to allow screenshots, then try again. You can also paste an image here.");
    }
  } else throw new Error("Choose page text or screenshot.");
  const [after] = await chrome.tabs.query({active: true, windowId});
  if (after?.id !== tab.id || after?.url !== tab.url) throw new Error("The tab changed during capture. Try again.");
  return {slug, text, screenshot};
}

window.addEventListener("message", async event => {
  if (event.source !== frame.contentWindow || event.origin !== serverOrigin) return;
  if (event.data?.type === "dsa-coach:ready") {
    ready = true;
    status.hidden = true;
    sendProblem();
  } else if (event.data?.type === "dsa-coach:capture" && ready) {
    const origin = serverOrigin;
    const response = {type: "dsa-coach:captured", id: event.data.id};
    try { Object.assign(response, await capture(event.data.kind)); }
    catch (error) { response.error = error.message; }
    frame.contentWindow.postMessage(response, origin);
  }
});

document.getElementById("settings").addEventListener("submit", async event => {
  event.preventDefault();
  // Reconnecting replaces the frame, including its temporary chat and captures.
  if (ready) {
    status.hidden = false;
    status.textContent = "Save your work in the panel before reconnecting.";
    if (!window.confirm("Reconnect the coach? Save stage edits and copy any chat you want to keep first.")) return;
  }
  const button = event.submitter;
  button.disabled = true;
  try { await connect(address.value); } finally { button.disabled = false; }
});

chrome.tabs.onActivated.addListener(info => { if (info.windowId === windowId) activeProblem().catch(console.error); });
chrome.tabs.onUpdated.addListener((_id, info, tab) => {
  if (tab.active && tab.windowId === windowId && (info.url || info.status === "complete")) activeProblem().catch(console.error);
});
chrome.storage.onChanged.addListener((changes, area) => {
  // Never replace a loaded workspace when another app tab uses a different server.
  if (area === "local" && changes.server && !ready && changes.server.newValue !== serverOrigin) {
    connect(changes.server.newValue);
  }
});

(async () => {
  windowId = (await chrome.windows.getCurrent()).id;
  const {server = CoachExtension.defaultServer} = await chrome.storage.local.get("server");
  address.value = server;
  await activeProblem();
  await connect(server);
})().catch(error => { status.textContent = error.message; });
