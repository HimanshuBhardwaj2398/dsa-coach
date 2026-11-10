"use strict";
// The panel frames the local learning app's /panel page. It reads no page and sends nothing anywhere else.
const frame = document.getElementById("coach");
const status = document.getElementById("status");
const address = document.getElementById("server");
const connection = document.getElementById("connection");
const connectionToggle = document.getElementById("connection-toggle");
let attempt = 0;  // a newer Connect wins over a slower older one

function showConnection(open) {
  connection.hidden = !open;
  connection.open = open;
  connectionToggle.setAttribute("aria-expanded", String(open));
}
connectionToggle.onclick = () => showConnection(connection.hidden);

async function connect(value) {
  const mine = ++attempt;
  status.hidden = false;
  status.textContent = "Connecting to your coach…";
  try {
    const origin = CoachExtension.serverOrigin(value);
    const response = await fetch(origin + "/panel", {signal: AbortSignal.timeout(5000)});
    if (!response.ok || !(await response.text()).includes('name="dsa-coach-app"')) {
      throw new Error("That address isn't the DSA Coach app. Restart python3 app/server.py, then connect again.");
    }
    if (mine !== attempt) return;
    address.value = origin;
    document.getElementById("full-app").href = origin + "/";
    frame.src = origin + "/panel";
    frame.hidden = false;
    status.hidden = true;
    showConnection(false);
    await chrome.storage.local.set({server: origin});
  } catch (error) {
    if (mine !== attempt) return;
    frame.hidden = true;
    status.textContent = error.name === "TypeError" || error.name === "TimeoutError"
      ? "Coach is offline. Start the local server, then choose Connect."
      : error.message;
    showConnection(true);
  }
}

document.getElementById("settings").addEventListener("submit", async (event) => {
  event.preventDefault();
  event.submitter.disabled = true;
  try { await connect(address.value); } finally { event.submitter.disabled = false; }
});

(async () => {
  const {server = CoachExtension.defaultServer} = await chrome.storage.local.get("server");
  address.value = server;
  await connect(server);
})().catch((error) => { status.textContent = error.message; });
