"""Browser check for the learning app and the Chrome side panel. Run by hand: python3 tests/browser/check_app.py [shots folder]

Uses a temporary notebook with a live solve, a due re-solve and a registered explainer, serves it, and drives
Chromium with Playwright: the full page at desktop width, then the unpacked extension's side panel at 390 px.
"""
import os
import subprocess
import sys
import tempfile
import threading
from pathlib import Path

from playwright.sync_api import expect, sync_playwright

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "app"))
import server  # noqa: E402


def main() -> None:
    out = Path(sys.argv[1] if len(sys.argv) > 1 else tempfile.mkdtemp(prefix="dsa-app-shots-"))
    out.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="dsa-app-check-") as temp:
        root = Path(temp) / "notebook"
        env = {k: v for k, v in os.environ.items() if k != "DSA_NOTEBOOK"}

        def coach(*args, today=None):
            subprocess.run([sys.executable, str(server.COACH), "--root", str(root), *args], check=True,
                           capture_output=True, env=dict(env, DSA_TODAY=today) if today else env)

        coach("init", "--name", "Tester", "--days", "90")
        coach("log", "attempt", "--problem", "valid-anagram", "--pattern", "arrays-hashing", "--outcome", "solved",
              "--date", "2026-01-01", today="2026-01-01")
        page_file = Path(temp) / "stack.html"
        page_file.write_text("<!doctype html><title>Stack</title><h1>Stack, explained</h1>")
        coach("artifact", "add", "--concept", "stack", "--title", "Stack, explained", "--file", str(page_file))
        coach("solve", "start", "--problem", "two-sum", "--unlabeled")
        srv = server.make_server(root, port=0, env=env)
        threading.Thread(target=srv.serve_forever, daemon=True).start()
        origin = f"http://127.0.0.1:{srv.server_address[1]}"
        extension = REPO / "extensions/dsa-coach"
        errors = []
        try:
            with sync_playwright() as pw:
                context = pw.chromium.launch_persistent_context(
                    str(Path(temp) / "browser"), channel="chromium", headless=True,
                    args=[f"--disable-extensions-except={extension}", f"--load-extension={extension}"],
                    viewport={"width": 1280, "height": 860})
                context.on("weberror", lambda e: errors.append(str(e.error)))
                page = context.new_page()

                page.goto(origin + "/#/solve")  # an old bookmark lands on Today
                expect(page.locator("h1")).to_have_text("Solving two-sum")
                assert "Arrays" not in page.locator("#content").inner_text()  # unlabeled: no pattern name
                expect(page.locator("a", has_text="valid-anagram")).to_have_attribute(
                    "href", "https://leetcode.com/problems/valid-anagram/")
                page.screenshot(path=out / "today.png")

                page.click("[data-nav=map]")
                expect(page.locator("a.node")).to_have_count(22)
                page.screenshot(path=out / "map.png", full_page=True)

                page.click('a.node[href="#/learn/stack"]')
                expect(page.locator(".learn h1")).to_have_text("Stack")
                expect(page.locator(".explainer a")).to_have_attribute("href", "/explainer/stack")
                page.click("text=Improve it")
                page.fill(".improve textarea", "show two equal heights")
                page.click("text=Make the prompt")
                prompt = page.locator("#handoff-prompt").input_value()
                assert "Revise" in prompt and "show two equal heights" in prompt, prompt
                page.screenshot(path=out / "learn-handoff.png", full_page=True)

                page.goto(origin + "/#/learn/binary-search")
                page.click("text=Ask the coach to write it")
                assert "Write the interactive explainer for Binary Search" in page.locator("#handoff-prompt").input_value()
                page.click("#copy-prompt")  # copied, or selected for copying by hand when the clipboard is blocked
                expect(page.locator("#copy-status")).not_to_be_empty()
                page.click("#close-handoff")
                expect(page.locator("#handoff")).to_be_hidden()

                page.evaluate("localStorage.setItem('dsa-coach:draft:two-sum', 'def f(): pass')")  # left by the old Solve tab
                page.reload()
                expect(page.locator("#recovery")).to_contain_text("1 unsaved draft from the old Solve tab")
                page.evaluate("localStorage.clear()")

                panel = context.new_page()
                panel.set_viewport_size({"width": 390, "height": 844})
                panel.goto(server.PANEL_PARENT + "/sidepanel.html")
                panel.evaluate(f"chrome.storage.local.set({{server: {origin!r}}})")
                panel.reload()
                frame = panel.frame_locator("#coach")
                expect(frame.locator("h1")).to_have_text("Solving two-sum")
                frame.locator("[data-nav=map]").click()
                expect(frame.locator("a.node")).to_have_count(22)
                assert panel.evaluate("document.documentElement.scrollWidth") <= 390
                panel.screenshot(path=out / "panel-map.png")

                srv.shutdown()
                srv.server_close()
                panel.reload()
                expect(panel.locator("#status")).to_contain_text("offline")
                panel.screenshot(path=out / "panel-offline.png")
                context.close()
        finally:
            srv.server_close()
    assert not errors, errors
    print(f"OK. Screenshots in {out}")


if __name__ == "__main__":
    main()
