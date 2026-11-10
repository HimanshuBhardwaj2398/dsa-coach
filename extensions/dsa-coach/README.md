# DSA Coach browser panel

A Chrome/Edge extension that keeps your DSA Coach progress and theory in a side panel beside LeetCode, or any other page. The panel shows the local learning app:

- **Today:** the live solve (stage, hint rung, focus block), the re-solves due, and what's next
- **Map:** all 22 patterns with their status
- **Learn:** a pattern's cues, invariant, template, resources, problems and saved explainer

The panel is read-only. You code on LeetCode, and you talk to the coach in Claude Code, which can look at your LeetCode tab itself. The extension reads no page and has no access to LeetCode or any other site: its only permissions are the side panel, its own storage, and your local server.

## Install once

1. Start the learning app from the repo and leave it running:

   ```bash
   python3 app/server.py --no-browser
   ```

2. Open `chrome://extensions` (or `edge://extensions`) and turn on **Developer mode**.
3. Choose **Load unpacked** and select this folder, `extensions/dsa-coach`.
4. Pin **DSA Coach** from the browser's Extensions menu, then click it on any page.

The panel connects to `http://127.0.0.1:8765`. If the terminal prints another port, open the ⚙ settings, paste that address and choose **Connect**. Only loopback HTTP addresses are accepted. Chrome 116 or later is required.

Keep the `key` in `manifest.json`: it fixes the extension's ID, which is the only origin the server lets frame its `/panel` page.

## Explainers

**Read the explainer** opens the saved page in a new tab. **Ask the coach to write it** and **Improve it** give you a prompt to paste into your coach chat; the coach writes or revises the page, and **Refresh** shows it.

## Troubleshooting

- **Offline:** start the server, check the printed port, then choose **Connect**.
- **Drafts from the old Solve tab:** if the full page at the address you used before 0.9.0 says unsaved drafts are still in the browser, choose **Download them** to keep a copy.
- After changing extension files, choose **Reload** on its card in the extensions page.

## Checks

From the repo root:

```bash
node --test tests/frontend/*.test.cjs
python3 tests/browser/check_app.py
```

The browser check loads the unpacked extension in Chromium against a temporary notebook. It covers the full page, the panel at 390 px, the explainer prompts, and the offline message.
