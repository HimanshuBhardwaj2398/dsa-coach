"""Browser check for the Map and Learn views. Run by hand: python3 tests/browser/check_map.py [screenshot folder]

Copies notebook/ to a temp folder, points claude_bin at fake_claude.py, serves it and drives the page with Playwright.
"""
import json
import os
import shutil
import sys
import tempfile
import threading
from pathlib import Path

from playwright.sync_api import expect, sync_playwright

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "app"))
import server  # noqa: E402

FAKE = Path(__file__).resolve().parent / "fake_claude.py"


def notebook_copy() -> Path:
    root = Path(tempfile.mkdtemp(prefix="dsa-map-check-")).resolve() / "notebook"
    shutil.copytree(REPO / "notebook", root)
    cfg = json.loads((root / "config.json").read_text())
    (root / "config.json").write_text(json.dumps({**cfg, "claude_bin": str(FAKE)}))
    return root


def main() -> None:
    out = Path(sys.argv[1] if len(sys.argv) > 1 else tempfile.mkdtemp(prefix="dsa-map-shots-"))
    out.mkdir(parents=True, exist_ok=True)
    root = notebook_copy()
    env = {k: v for k, v in os.environ.items() if k != "DSA_NOTEBOOK"}
    srv = server.make_server(root, port=0, env=env)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    base = f"http://127.0.0.1:{srv.server_address[1]}/"
    errors = []
    try:
        with sync_playwright() as pw:
            browser = pw.chromium.launch()
            page = browser.new_page(viewport={"width": 1440, "height": 900})
            page.on("pageerror", lambda e: errors.append(str(e)))

            page.goto(base)
            expect(page.locator(".next-strip")).to_be_visible()
            assert page.locator("a.node").count() == 22, page.locator("a.node").count()
            assert page.locator(".node.stub").count() == 3
            assert page.locator("#solve").is_hidden() and page.locator("#start").is_hidden()
            page.screenshot(path=out / "map-light.png")

            page.click('a.node[href="#/learn/binary-search"]')
            expect(page.locator(".learn h1")).to_have_text("Binary Search")
            rows = page.locator("table.problems tr").all()[1:]
            tagged = [r.locator(".tag").count() > 0 for r in rows]
            assert tagged == sorted(tagged, reverse=True) and any(tagged), tagged  # Blind 75 rows first
            hrefs = page.locator("table.problems a").evaluate_all("as => as.map(a => a.href)")
            assert hrefs and all(h.startswith("https://leetcode.com/problems/") for h in hrefs), hrefs
            page.screenshot(path=out / "learn-light.png", full_page=True)

            page.get_by_role("button", name="Write the explainer").click()
            read = page.get_by_role("link", name="Read the explainer")
            expect(read).to_be_visible(timeout=30_000)
            with page.context.expect_page() as tab:
                read.click()
            explainer = tab.value
            explainer.wait_for_load_state()
            assert "binary-search, explained" in explainer.content()
            explainer.close()

            page.goto(base + "#/solve")
            expect(page.locator("#start, #solve").locator("visible=true")).to_have_count(1)
            assert page.locator("#map").is_hidden()
            page.click("#home")
            expect(page.locator(".weeks")).to_be_visible()

            page.emulate_media(color_scheme="dark")
            page.screenshot(path=out / "map-dark.png")
            page.goto(base + "#/learn/binary-search")
            expect(page.locator(".learn h1")).to_be_visible()
            page.screenshot(path=out / "learn-dark.png", full_page=True)

            page.emulate_media(color_scheme="light")
            page.set_viewport_size({"width": 390, "height": 844})
            for name, hash_, shown in (("map", "#/map", ".weeks"), ("learn", "#/learn/binary-search", ".learn")):
                page.goto(base + hash_)
                page.wait_for_selector(shown)
                wide = page.evaluate("document.documentElement.scrollWidth - document.documentElement.clientWidth")
                assert wide <= 0, f"{name} scrolls sideways by {wide}px at 390px"
                page.screenshot(path=out / f"{name}-390.png", full_page=True)
            browser.close()
        assert not errors, errors
        print(f"all checks passed; screenshots in {out}")
    finally:
        srv.shutdown()
        shutil.rmtree(root.parent, ignore_errors=True)


if __name__ == "__main__":
    main()
