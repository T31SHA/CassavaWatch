"""Screenshot both pages at 360/768/1440 px in light and dark mode, plus layout checks.

Needs a running, seeded server and `pip install playwright` + system Chrome.
Usage: python scripts/ui_screenshots.py [base_url]   -> docs/screenshots/ui-*.png
"""
import sys
from pathlib import Path

from playwright.sync_api import expect, sync_playwright

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8000"
ROOT = Path(__file__).resolve().parent.parent
SHOTS = ROOT / "docs" / "screenshots"
SHOTS.mkdir(parents=True, exist_ok=True)
TEST = ROOT / "data" / "icassava" / "test"
CMD_IMGS = [str(p) for p in sorted((TEST / "cmd").glob("*.jpg"))[:3]]
MIXED = [str(sorted((TEST / c).glob("*.jpg"))[0]) for c in ("cbb", "cgm", "healthy")]
WIDTHS = {360: 760, 768: 1024, 1440: 900}
problems = []

SMALL_TARGETS = """[...document.querySelectorAll('button, a, label.tile, select, summary')]
  .filter(e => e.offsetParent && e.getBoundingClientRect().height < 48)
  .map(e => (e.getAttribute('aria-label') || e.textContent.trim() || e.tagName).slice(0, 30))"""


def layout_check(page, name):
    if page.evaluate("document.documentElement.scrollWidth > window.innerWidth"):
        problems.append(f"{name}: horizontal overflow")


with sync_playwright() as p:
    browser = p.chromium.launch(channel="chrome", headless=True)
    for scheme in ("light", "dark"):
        for w, h in WIDTHS.items():
            ctx = browser.new_context(viewport={"width": w, "height": h}, device_scale_factor=2 if w < 800 else 1,
                                      color_scheme=scheme, geolocation={"latitude": 0.46, "longitude": 34.15},
                                      permissions=["geolocation"], is_mobile=w < 800, has_touch=w < 800)
            page = ctx.new_page()
            tag = f"{w}-{scheme}"

            # capture: empty, then 3 photos
            page.goto(BASE + "/")
            expect(page.locator("#loctext")).to_contain_text("Location found")
            page.wait_for_timeout(300)
            layout_check(page, f"capture {tag}")
            small = page.evaluate(SMALL_TARGETS)
            if small:
                problems.append(f"capture {tag}: targets < 48px: {small}")
            page.screenshot(path=SHOTS / f"ui-capture-{tag}.png", full_page=True)
            page.set_input_files("#photo", CMD_IMGS)
            page.wait_for_timeout(300)
            if w == 360:
                page.screenshot(path=SHOTS / f"ui-capture-photos-{tag}.png", full_page=True)

            # result
            page.click("#submit")
            expect(page.locator("#s3")).to_be_visible(timeout=20000)
            page.wait_for_timeout(300)
            layout_check(page, f"result {tag}")
            small = page.evaluate(SMALL_TARGETS)
            if small:
                problems.append(f"result {tag}: targets < 48px: {small}")
            page.screenshot(path=SHOTS / f"ui-result-{tag}.png", full_page=True)

            if w == 360:
                # step 2 skeleton (freeze the request so the skeleton stays up)
                page.click("#again")
                page.set_input_files("#photo", MIXED)
                page.route("**/api/diagnose", lambda route: None)
                page.click("#submit")
                page.wait_for_timeout(400)
                page.screenshot(path=SHOTS / f"ui-analysing-{tag}.png", full_page=True)
                page.unroute("**/api/diagnose")

            # dashboard
            page.goto(BASE + "/dashboard")
            expect(page.locator(".alert-card:not(.skel-card)").first).to_be_visible(timeout=10000)
            page.wait_for_timeout(1500)  # tiles
            layout_check(page, f"dashboard {tag}")
            page.screenshot(path=SHOTS / f"ui-dashboard-{tag}.png", full_page=True)
            if w == 1440:
                page.locator(".alert-place").first.click()
                page.wait_for_timeout(2500)  # tiles at the new zoom
                page.click("#info-btn")
                page.screenshot(path=SHOTS / f"ui-dashboard-alert-{tag}.png")
            ctx.close()
    browser.close()

print("\n".join(problems) if problems else "no layout problems found")
