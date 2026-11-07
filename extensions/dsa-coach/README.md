# DSA Coach browser companion

A Chrome/Edge extension that keeps the coach beside LeetCode. Write and run your code in LeetCode, then ask the coach about your reasoning, selected text, page text or a screenshot. Replies appear inside the panel through your existing Claude CLI sign-in.

## Install once

1. Start or restart the **updated** study app from the repo:

   ```bash
   python3 app/server.py --no-browser
   ```

2. Open `chrome://extensions` (or `edge://extensions`) and turn on **Developer mode**.
3. Choose **Load unpacked**, then select this folder, `extensions/dsa-coach`, containing `manifest.json`.
4. Pin **DSA Coach** from the browser's Extensions menu.
5. Open a LeetCode problem and click the DSA Coach toolbar icon.

The default server is `http://127.0.0.1:8765`. If the terminal prints a different port, expand **Local connection**, paste that address and choose **Connect**. Only loopback HTTP addresses are accepted. The server needs to stay running.

Chrome controls the panel's side. If yours opens on the left, use Chrome Settings → Appearance → Side panel → **Show on right**. The extension cannot override your browser preference. See the [Side Panel API documentation](https://developer.chrome.com/docs/extensions/reference/api/sidePanel).

Chrome 116 or later is required. The same manifest targets Edge's compatible side-panel API; automated browser checks run in Chromium, not Edge.

## Use it

- Clicking an ordinary LeetCode problem link in the study app opens LeetCode normally and also opens the coach panel. Refresh an already-open app tab after installing the extension. Modifier clicks keep their usual behavior; use the toolbar icon if necessary.
- With no active solve, the current problem is offered in the start form. Choose your confidence and **Start solving**, or ask a question before starting. Navigating to another problem never replaces an active solve.
- Expand **Page context** and choose **Read page text**. Selected text takes priority; otherwise it reads the page's main text, up to 24,000 characters. Virtualized editors may expose only visible lines. Paste the relevant code if it is missing.
- Choose **Take screenshot** for the visible LeetCode tab. If Chrome asks for access, click the DSA Coach toolbar icon while on LeetCode and reopen the panel, then retry. Screenshots require a toolbar invocation under Chrome's [activeTab permission](https://developer.chrome.com/docs/extensions/develop/concepts/activeTab). You can also paste an image in the conversation area or attach a PNG/JPEG under 4 MB.
- Review or edit the attached text, type a question, then choose **Ask coach**. Stage-specific **Ask coach** controls save your stage answer before asking. The conversation form uses already-saved stage answers; save a stage answer first if you want it included.
- When changing problems, attachments are cleared. A different active solve is shown explicitly, and coaching is paused until you return to that problem or finish that solve.

## What is sent and saved

Clicking a capture button only attaches context for review. **Ask coach** sends the question, attached context, saved solve stage/answers/plan card/examples and recent conversation to Claude through the CLI. This uses your existing Claude account/provider, and its usual limits or charges apply. No API key is stored in the extension.

Stage answers and start/stage controls use the existing notebook. Chat history and captures are temporary and are not saved in the notebook; reopening/reloading the panel starts a fresh chat. Copy any reply you want to keep. The existing study app's recovery behavior still protects stage notes.

The coach is read-only: its CLI invocation has tools and MCP servers disabled. It cannot edit code, run tests, click Submit, change stages or log attempts. It asks you to run checks in LeetCode. **Review with coach** reviews your final answers; use your main coach chat to record the completed attempt. The full app remains available from the panel header.

This is on-demand browser context capture, not continuous desktop recording or autonomous computer control. Only the active LeetCode problem tab is captured. Page content is treated as evidence, not instructions to the coach.

## Troubleshooting

- **Offline:** start the server and check the printed port, then choose **Connect**.
- **Cannot open here:** restart the updated server and reload the extension. Keep the public `key` in `manifest.json`; it gives the extension the stable ID allowed by the companion route.
- **Claude cannot start:** run `claude` in a terminal and sign in. If needed, set `claude_bin` in `notebook/config.json` to its executable path. The CLI needs the `--input-format stream-json`, `--tools`, `--setting-sources` and `--no-session-persistence` flags; see the [Claude CLI reference](https://code.claude.com/docs/en/cli-reference).
- **Capture permission:** use the toolbar icon on the LeetCode tab, or paste/attach an image instead. The extension does not request access to every website.
- After changing extension files, choose **Reload** on its card in the extensions page and refresh app tabs. Save stage work before reconnecting or reloading.

## Checks

From the repo root:

```bash
python3 -m unittest discover -s tests
node --test tests/frontend/*.test.cjs
python3 tests/browser/check_extension.py
```

The browser check uses a temporary notebook, a loaded unpacked extension, a fake LeetCode page and a fake Claude executable. It covers an app link opening the native side panel, framing restrictions, tab context, starting a solve, text capture, image attachment, a direct reply, preservation of unsaved stage notes, offline handling, and layout at 320/390 pixels. Real Claude text and image transport have also been smoke-tested locally. Native toolbar/screenshot permission behavior still depends on the browser's user-gesture rules.
