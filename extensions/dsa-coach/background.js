"use strict";
importScripts("shared.js");

chrome.sidePanel.setPanelBehavior({openPanelOnActionClick: true}).catch(console.error);

chrome.runtime.onMessage.addListener((message, sender, reply) => {
  if (message?.type !== "dsa-coach:open" || !sender.tab || !CoachExtension.problemSlug(message.url)) return;
  let origin;
  try { origin = CoachExtension.serverOrigin(new URL(sender.url).origin); } catch { return; }
  // Open synchronously within the click's user gesture, before storage or other async work.
  chrome.sidePanel.open({windowId: sender.tab.windowId}).then(async () => {
    await chrome.storage.local.set({server: origin});
    reply({ok: true});
  }).catch(error => reply({ok: false, error: error.message}));
  return true;
});
