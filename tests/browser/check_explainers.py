"""Browser check for the saved explainers. Run by hand: python3 tests/browser/check_explainers.py [--root NOTEBOOK]

Serves the notebook the way the learning app does and opens every registered explainer in Chromium with Playwright.
Each page must be a whole document (a doctype and a title), run without script errors inside the app's sandbox,
and open at its top.
"""
import argparse
import sys
import threading
from pathlib import Path

from playwright.sync_api import sync_playwright

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "app"))
import server  # noqa: E402


def faults(page, url: str) -> list:
    """What is wrong with the explainer at url, in words. Empty when it is fine."""
    found = []
    page.on("pageerror", lambda error: found.append(f"script error: {error}"))
    page.goto(url)
    page.wait_for_timeout(800)  # scripts that run on load have finished
    facts = page.evaluate("({doctype: !!document.doctype, title: document.title.trim(), y: Math.round(scrollY)})")
    if not facts["doctype"] or not facts["title"]:
        found.append("not a whole page: it needs <!doctype html> and a <title>")
    if facts["y"]:
        found.append(f"opens {facts['y']}px down the page: something takes focus or scrolls on load")
    return found


def main() -> None:
    parser = argparse.ArgumentParser(description="open every saved explainer the way the learning app serves it")
    parser.add_argument("--root", type=Path, default=REPO / "notebook", help="notebook folder (default: ./notebook in the repo)")
    root = parser.parse_args().root.resolve()
    keys = [p["key"] for p in server.read_map(root)["patterns"] if p["explainer"]]
    srv = server.make_server(root, port=0)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    bad = 0
    try:
        with sync_playwright() as pw:
            browser = pw.chromium.launch(channel="chromium", headless=True)
            for key in keys:
                page = browser.new_page(viewport={"width": 1280, "height": 860})
                found = faults(page, f"http://127.0.0.1:{srv.server_address[1]}/explainer/{key}")
                page.close()
                bad += bool(found)
                print(f"{key}: " + ("ok" if not found else "; ".join(found)))
            browser.close()
    finally:
        srv.shutdown()
        srv.server_close()
    if bad:
        raise SystemExit(f"{bad} of {len(keys)} explainers need fixing")
    print(f"OK. {len(keys)} explainers open cleanly.")


if __name__ == "__main__":
    main()
