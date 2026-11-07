"use strict";
// Only the study app opts in. Keep normal link navigation and modifier clicks intact.
document.addEventListener("click", event => {
  if (!event.isTrusted || event.button !== 0 || event.ctrlKey || event.metaKey || event.shiftKey || event.altKey ||
      !document.querySelector('meta[name="dsa-coach-app"]')) return;
  const link = event.target.closest?.("a[href]");
  if (!link) return;
  let url;
  try { url = new URL(link.href); } catch { return; }
  if (url.origin !== "https://leetcode.com" || !url.pathname.startsWith("/problems/")) return;
  chrome.runtime.sendMessage({type: "dsa-coach:open", url: url.href}).catch(() => {
    // Navigation still works if the extension was reloaded. The toolbar can open the panel.
  });
}, true);
