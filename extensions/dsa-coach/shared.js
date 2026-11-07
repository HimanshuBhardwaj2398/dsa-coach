"use strict";
// Shared by the panel, worker and Node checks. No page content is read.
const CoachExtension = {
  defaultServer: "http://127.0.0.1:8765",
  serverOrigin(value) {
    const url = new URL(value);
    if (url.protocol !== "http:" || !["127.0.0.1", "localhost"].includes(url.hostname) ||
        url.username || url.password || url.pathname !== "/" || url.search || url.hash) {
      throw new Error("Use the local server address, such as http://127.0.0.1:8765.");
    }
    return url.origin;
  },
  problemSlug(value) {
    try {
      const url = new URL(value);
      if (url.origin !== "https://leetcode.com") return null;
      return url.pathname.match(/^\/problems\/([a-z0-9][a-z0-9-]{0,254})(?:\/|$)/)?.[1] || null;
    } catch { return null; }
  },
};
if (typeof module !== "undefined") module.exports = CoachExtension;
