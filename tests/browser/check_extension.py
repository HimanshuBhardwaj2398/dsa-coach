"""Exercise the unpacked extension with Chromium and a temporary notebook.

    python3 tests/browser/check_extension.py [screenshot directory]

Requires Playwright's Chromium. Does not contact LeetCode or change the real notebook.
"""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import threading

from playwright.sync_api import expect, sync_playwright

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "app"))
import server


def tap(locator):
    """A click in the panel's frame. Playwright first checks that the target is visible, enabled and not covered, then
    the click is dispatched to it: headless Chromium sends a real mouse click to the outer iframe while another tab
    (LeetCode here) is in front, which a real side panel never is."""
    locator.click(trial=True)
    locator.dispatch_event("click")


def main():
    out = Path(sys.argv[1] if len(sys.argv) > 1 else tempfile.mkdtemp(prefix="dsa-extension-shots-"))
    out.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="dsa-extension-check-") as temp:
        root = Path(temp) / "notebook"
        env = {k: v for k, v in os.environ.items() if k != "DSA_NOTEBOOK"}

        def coach(*args):
            return subprocess.run([sys.executable, str(server.COACH), "--root", str(root), *args],
                                  check=True, capture_output=True, text=True, env=env)

        coach("init", "--name", "Tester", "--start-date", "2026-11-01", "--days", "90")
        config = json.loads((root / "config.json").read_text())
        config["claude_bin"] = str(Path(__file__).with_name("fake_coach.py"))
        (root / "config.json").write_text(json.dumps(config))
        theory = root / "concepts/arrays-hashing/theory.html"
        theory.parent.mkdir(parents=True, exist_ok=True)
        theory.write_text("<!doctype html><title>Arrays theory</title><h1>Arrays and hashing, explained</h1>")
        coach("artifact", "add", "--concept", "arrays-hashing", "--title", "Arrays theory", "--file", str(theory))
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
                    viewport={"width": 390, "height": 844})
                editor = ("<script>window.monaco = {editor: {getEditors: () => [{getModel: () => ({getValue: () => "
                          "'class Solution:\\n    def twoSum(self, nums, target): ...'})}]}};</script>")
                context.route("https://leetcode.com/**", lambda route: route.fulfill(
                    content_type="text/html", body=editor + "<h1>LeetCode fixture</h1>"))
                context.route("**/api/problem/fetch", lambda route: route.fulfill(
                    content_type="application/json", body=json.dumps({"text": "# Two Sum\n\nFind the pair."})))
                worker = context.service_workers[0] if context.service_workers else context.wait_for_event("serviceworker")
                assert worker.url.startswith(server.COMPANION_ORIGIN)
                worker.evaluate("server => chrome.storage.local.set({server})", origin)
                # Exercise the actual content-script click -> service worker -> native panel path.
                worker.evaluate("() => { globalThis.panelOpened = false; chrome.sidePanel.onOpened.addListener(() => { globalThis.panelOpened = true; }); }")
                app_page = context.new_page()
                app_page.goto(origin)
                with context.expect_page() as opened:
                    app_page.get_by_role("link", name="Open on LeetCode").click()
                opened.value.wait_for_load_state()
                for _ in range(50):
                    if worker.evaluate("globalThis.panelOpened"):
                        break
                    app_page.wait_for_timeout(100)
                assert worker.evaluate("globalThis.panelOpened"), "app link did not open the native side panel"
                panel = context.new_page()
                panel.on("pageerror", lambda error: errors.append(str(error)))
                panel.goto(server.COMPANION_ORIGIN + "/sidepanel.html")
                workspace = panel.frame_locator("#coach")
                expect(workspace.locator("#companion-chat")).to_be_visible(timeout=20000)
                expect(workspace.locator("#companion-tab-chat")).to_have_attribute("aria-selected", "true")
                expect(workspace.locator("#start")).to_be_hidden()
                expect(panel.locator("#status")).to_be_hidden()
                expect(panel.locator("#connection")).to_be_hidden()
                panel.locator("#connection-toggle").click()
                expect(panel.locator("#connection")).to_be_visible()
                panel.locator("#connection-toggle").click()

                leetcode = context.new_page()
                leetcode.goto("https://leetcode.com/problems/two-sum/description/")
                leetcode.bring_to_front()
                expect(workspace.locator("#slug")).to_have_value("two-sum")
                expect(workspace.locator("#companion-problem")).to_have_text("Two Sum")
                expect(workspace.locator("#companion-question")).to_be_in_viewport()
                tap(workspace.locator("#companion-use"))
                expect(workspace.locator("#start")).to_be_visible()
                workspace.locator("#confidence").select_option("3")
                tap(workspace.locator("#start-btn"))
                expect(workspace.locator("#solve")).to_be_visible()
                expect(workspace.locator("#tab-stage")).to_have_attribute("aria-selected", "true")
                expect(workspace.locator("#work")).to_be_hidden()
                tap(workspace.locator("#companion-tab-chat"))
                expect(workspace.locator("#solve")).to_be_hidden()
                tap(workspace.locator("#companion-attachment summary"))
                tap(workspace.locator("#capture-text"))
                expect(workspace.locator("#captured-text")).to_have_value("LeetCode fixture")
                screenshot = out / "leetcode-fixture.png"
                leetcode.screenshot(path=str(screenshot))
                workspace.locator("#captured-file").set_input_files(str(screenshot))
                expect(workspace.locator("#captured-image")).to_be_visible()
                workspace.locator("#companion-question").fill("What should I check next?")
                tap(workspace.locator("#companion-send"))
                try:
                    expect(workspace.locator("#companion-messages")).to_contain_text("same value appears twice", timeout=20000)
                except AssertionError:
                    print("Chat status:", workspace.locator("#companion-chat-status").inner_text(), "Page errors:", errors)
                    panel.screenshot(path=str(out / "failure.png"))
                    raise
                # The rung the reply gave is on the hint ladder, and the RUNG line itself isn't shown.
                expect(workspace.locator(".message-note")).to_have_text("Hint rung 2 recorded (a nudge for this problem).")
                expect(workspace.locator("#companion-messages")).not_to_contain_text("RUNG:")
                assert json.loads(coach("solve", "show", "--json").stdout)["rung"] == 2
                # The coach asks to look. Without screen access the panel says how to grant it.
                tap(workspace.locator("#companion-attachment summary"))
                tap(workspace.locator("#capture-clear"))
                workspace.locator("#companion-question").fill("Does my layout look right?")
                tap(workspace.locator("#companion-send"))
                expect(workspace.locator("#companion-messages")).to_contain_text("I need to see the page. Choose Allow screenshots", timeout=20000)
                expect(panel.locator("#screen-access")).to_be_visible()
                expect(workspace.locator("#companion-messages")).not_to_contain_text("[[LOOK]]")
                tap(workspace.locator("#companion-tab-stages"))
                note = workspace.locator("#panel textarea").first
                note.fill("Keep this unsaved reasoning")
                tap(workspace.get_by_role("button", name="Stage 3: Count, upcoming", exact=True))
                expect(workspace.locator("#companion-stage-preview")).to_be_visible()
                expect(workspace.locator("#solve")).to_be_hidden()
                assert json.loads(coach("solve", "show", "--json").stdout)["stage"] == 1
                tap(workspace.locator("#companion-stage-prev"))
                expect(workspace.locator("#companion-stage-count")).to_have_text("Stage 2 of 8")
                tap(workspace.locator("#companion-stage-current"))
                expect(note).to_have_value("Keep this unsaved reasoning")
                tap(workspace.locator("#companion-tab-chat"))
                workspace.locator("#companion-question").fill("My unsent follow-up")
                tap(workspace.locator("#companion-tab-learn"))
                expect(workspace.locator(".theory-card")).to_have_count(1)
                with context.expect_page() as theory_tab:
                    tap(workspace.get_by_role("link", name="Open interactive theory", exact=False))
                expect(theory_tab.value.locator("h1")).to_have_text("Arrays and hashing, explained")
                theory_tab.value.close()
                leetcode.bring_to_front()
                # Improve: what should change goes to the coach, which revises the page in place.
                tap(workspace.get_by_role("button", name="Improve this page", exact=True))
                workspace.get_by_label("What should change?").fill("Show the duplicate case first.")
                panel.screenshot(path=str(out / "companion-learn-improve.png"), full_page=True)
                tap(workspace.get_by_role("button", name="Revise it", exact=True))
                expect(workspace.get_by_text("Revised. Open it again to see the changes.")).to_be_visible(timeout=20000)
                with context.expect_page() as theory_tab:
                    tap(workspace.get_by_role("link", name="Open interactive theory", exact=False))
                expect(theory_tab.value.locator("body")).to_contain_text("Revised: Show the duplicate case first.")
                theory_tab.value.close()
                leetcode.bring_to_front()
                tap(workspace.get_by_role("button", name="Explain this to me", exact=True))
                expect(workspace.locator("#companion-tab-chat")).to_have_attribute("aria-selected", "true")
                assert "My unsent follow-up" in workspace.locator("#companion-question").input_value()
                assert "Arrays & Hashing" in workspace.locator("#companion-question").input_value()
                expect(workspace.locator("#companion-attachment-count")).to_contain_text("text")
                tap(workspace.locator("#companion-tab-learn"))
                workspace.locator("#companion-theory-search").fill("binary search")
                expect(workspace.locator(".theory-card")).to_have_count(1)
                expect(workspace.locator(".theory-card a")).to_have_attribute("href", "/#/learn/binary-search")
                # Write: a topic without an explainer gets one, and its card then opens it.
                tap(workspace.get_by_role("button", name="Write the interactive explainer", exact=True))
                expect(workspace.locator(".theory-card a")).to_have_attribute("href", "/explainer/binary-search", timeout=20000)
                expect(workspace.get_by_role("button", name="Improve this page", exact=True)).to_be_visible()
                workspace.locator("#companion-theory-search").fill("no matching topic")
                expect(workspace.locator("#companion-theory-status")).to_contain_text("No matching topics")
                tap(workspace.locator("#companion-tab-stages"))
                expect(note).to_have_value("Keep this unsaved reasoning")

                leetcode.goto("https://leetcode.com/problems/valid-anagram/")
                leetcode.bring_to_front()
                expect(workspace.locator("#companion-mismatch")).to_contain_text("active solve is two-sum")
                expect(note).to_have_value("Keep this unsaved reasoning")
                assert json.loads(coach("solve", "show", "--json").stdout)["problem"] == "two-sum"
                expect(workspace.locator("#captured-image")).to_be_hidden()
                expect(workspace.locator("#captured-text")).to_have_value("")
                expect(workspace.locator("#companion-send")).to_be_disabled()
                leetcode.goto("https://leetcode.com/problems/two-sum/")
                leetcode.bring_to_front()
                expect(workspace.locator("#companion-mismatch")).to_be_hidden()
                for width in (320, 390):
                    panel.set_viewport_size({"width": width, "height": 844})
                    frame = next(frame for frame in panel.frames if "/companion" in frame.url)
                    for name in ("chat", "stages", "learn"):
                        tap(workspace.locator(f"#companion-tab-{name}"))
                        assert frame.evaluate("document.documentElement.scrollWidth <= innerWidth"), f"{name} overflow at {width}px"
                        if name == "chat":
                            expect(workspace.locator("#companion-question")).to_be_in_viewport()
                            expect(workspace.locator("#companion-send")).to_be_in_viewport()
                workspace.locator("#companion-theory-search").fill("")
                for name in ("chat", "stages", "learn"):
                    tap(workspace.locator(f"#companion-tab-{name}"))
                    panel.screenshot(path=str(out / f"companion-{name}-light.png"), full_page=True)
                panel.emulate_media(color_scheme="dark")
                tap(workspace.locator("#companion-tab-chat"))
                panel.screenshot(path=str(out / "companion-chat-dark.png"), full_page=True)
                tap(workspace.locator("#companion-tab-stages"))
                workspace.locator("table.examples .args").first.fill("[2, 7], 9")
                workspace.locator("table.examples .expected").first.fill("[0, 1]")
                tap(workspace.locator("table.examples .edge").first)
                tap(workspace.get_by_role("button", name="Remove this example").nth(1))
                tap(workspace.get_by_role("button", name="Complete and continue", exact=True))
                expect(workspace.locator("#companion-stage-count")).to_have_text("Stage 2 of 8")
                assert json.loads(coach("solve", "show", "--json").stdout)["stage"] == 2
                tap(workspace.get_by_role("button", name="Stage 1: Understand, completed", exact=True))
                expect(note).to_have_value("Keep this unsaved reasoning")
                assert json.loads(coach("solve", "show", "--json").stdout)["stage"] == 2

                # A normal web origin cannot embed the privileged companion route.
                hostile = context.new_page()
                hostile.goto(origin)
                hostile.evaluate("url => {const f=document.createElement('iframe');f.src=url;document.body.append(f);}", origin + "/companion")
                expect(hostile.frame_locator("iframe").locator("#bar")).not_to_be_visible()

                # A fresh panel gives a useful connection failure without discarding the loaded one.
                worker.evaluate("() => chrome.storage.local.set({server: 'http://127.0.0.1:1'})")
                offline = context.new_page()
                offline.goto(server.COMPANION_ORIGIN + "/sidepanel.html")
                expect(offline.locator("#status")).to_contain_text("offline", timeout=15000)
                expect(offline.locator("#connection")).to_have_attribute("open", "")
                context.close()
            assert not errors, errors
            print(f"Extension checks passed; screenshots: {out}")
        finally:
            srv.shutdown()
            srv.server_close()


if __name__ == "__main__":
    main()
