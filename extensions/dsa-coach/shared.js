"use strict";
// Shared by the panel and the Node checks.
const CoachExtension = {
  defaultServer: "http://127.0.0.1:8765",
  // Only the local learning app: loopback over HTTP, no credentials, path, query or fragment.
  serverOrigin(value) {
    const url = new URL(value);
    if (url.protocol !== "http:" || !["127.0.0.1", "localhost"].includes(url.hostname) ||
        url.username || url.password || url.pathname !== "/" || url.search || url.hash) {
      throw new Error("Use the local server address, such as http://127.0.0.1:8765.");
    }
    return url.origin;
  },
};
if (typeof module !== "undefined") module.exports = CoachExtension;
