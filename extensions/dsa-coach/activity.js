"use strict";
// Typing or clicking on a LeetCode problem tells the open side panel he is working, so the focus block's clock
// keeps running. Nothing about the page is sent: only that there was activity, at most once every 30 seconds.
let lastActivity = 0;
function activity() {
  if (Date.now() - lastActivity < 30_000) return;
  lastActivity = Date.now();
  chrome.runtime.sendMessage({type: "dsa-coach:activity"}).catch(() => {});  // no panel open: nobody listens
}
for (const type of ["keydown", "pointerdown", "wheel"]) document.addEventListener(type, activity, {capture: true, passive: true});
