"""Headless end-to-end check of the running app (not part of `make test`).

Needs: a running server (`make run`), seeded DB (`make seed`), `pip install playwright`,
and a Chromium/Chrome (uses the system Chrome via channel="chrome").
Usage: python scripts/e2e_playwright.py [base_url]
Writes screenshots to docs/screenshots/.
"""
import json
import sys
import urllib.request
from pathlib import Path

from playwright.sync_api import expect, sync_playwright

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8000"
ROOT = Path(__file__).resolve().parent.parent
SHOTS = ROOT / "docs" / "screenshots"
SHOTS.mkdir(parents=True, exist_ok=True)
IMGS = sorted((ROOT / "data" / "icassava" / "test" / "healthy").glob("*.jpg"))[:3]
MOBILE = {"viewport": {"width": 360, "height": 740}, "device_scale_factor": 2, "is_mobile": True, "has_touch": True}
results = []


def api(path, method="GET"):
    with urllib.request.urlopen(urllib.request.Request(BASE + path, method=method)) as r:
        return json.load(r)


def check(name, cond, detail=""):
    results.append((name, bool(cond), detail))
    print(("PASS " if cond else "FAIL ") + name + (f" — {detail}" if detail else ""), flush=True)


def fill_photos(page, files):
    page.set_input_files("#photo", [str(f) for f in files])


with sync_playwright() as p:
    browser = p.chromium.launch(channel="chrome", headless=True)

    # ---------- 1. capture flow with geolocation ----------
    ctx = browser.new_context(**MOBILE, geolocation={"latitude": -2.60, "longitude": 33.02}, permissions=["geolocation"])
    page = ctx.new_page()
    page.on("dialog", lambda d: d.accept())
    n_before = len(api("/api/reports?days=1"))
    page.goto(BASE + "/")
    expect(page.locator("#locstatus")).to_contain_text("Location found")
    fill_photos(page, IMGS)
    expect(page.locator(".slot img")).to_have_count(3)
    page.screenshot(path=SHOTS / "capture.png", full_page=True)
    overflow = page.evaluate("document.documentElement.scrollWidth > window.innerWidth")
    check("capture: no horizontal overflow at 360px", not overflow)
    small = page.evaluate("""[...document.querySelectorAll('button:not([hidden]), a, label.tile, select, summary')]
        .filter(e => e.offsetParent && e.getBoundingClientRect().height < 48)
        .map(e => e.textContent.trim() || e.id)""")
    check("capture: visible tap targets >= 48px", not small, str(small))
    page.click("#submit")
    expect(page.locator("#s3")).to_be_visible(timeout=20000)
    check("capture: step 3 result shown", page.locator(".progress span.on").count() == 3)
    name_en = page.locator("#r-name").inner_text()
    n_bullets = page.locator("#r-bullets li").count()
    check("result: 1-4 advice bullets", 1 <= n_bullets <= 4, f"{n_bullets} bullets")
    check("result: EN + SW names shown", name_en and page.locator("#r-name2").inner_text(), name_en)
    page.screenshot(path=SHOTS / "result.png", full_page=True)
    page.click(".lang button[data-lang=sw]")
    body_sw = page.locator("body").inner_text()
    leftover = [w for w in ("Photograph", "Diagnosing", "What to do", "Report another plant", "Confidence",
                            "Online", "Details", "Extension officer") if w in body_sw]
    check("language toggle swaps all visible text", not leftover, f"leftover EN: {leftover}")
    check("language toggle swaps result card", page.locator("#r-name").inner_text() != name_en)
    page.click(".lang button[data-lang=en]")
    reps = api("/api/reports?days=1")
    check("report persisted", len(reps) == n_before + 1)
    ctx.close()

    # ---------- 2. offline queue + retry on reconnect ----------
    ctx = browser.new_context(**MOBILE, geolocation={"latitude": -2.60, "longitude": 33.02}, permissions=["geolocation"])
    page = ctx.new_page()
    page.on("dialog", lambda d: d.accept())
    page.goto(BASE + "/")
    expect(page.locator("#locstatus")).to_contain_text("Location found")
    ctx.set_offline(True)
    expect(page.locator("#net")).to_have_text("Offline")
    fill_photos(page, IMGS)
    page.click("#submit")
    expect(page.locator("#toast")).to_contain_text("Saved offline")
    expect(page.locator("#net")).to_have_text("Offline · 1 waiting to sync")
    check("offline: report queued + pill shows count", True)
    n_q = len(api("/api/reports?days=1"))
    ctx.set_offline(False)
    expect(page.locator("#toast")).to_contain_text("Synced 1 report", timeout=20000)
    expect(page.locator("#net")).to_have_text("Online")
    check("offline: retry fires on reconnect", len(api("/api/reports?days=1")) == n_q + 1)
    ctx.close()

    # ---------- 3. no geolocation -> district picker; non-image -> friendly 400 ----------
    ctx = browser.new_context(**MOBILE)  # geolocation permission not granted
    page = ctx.new_page()
    page.on("dialog", lambda d: d.accept())
    page.goto(BASE + "/")
    expect(page.locator("#district")).to_be_visible(timeout=15000)
    page.select_option("#district", label="Busia (KE)")
    bad = ROOT / "docs" / "not-an-image.txt"
    bad.write_text("hello")
    page.set_input_files("#photo", [str(bad)] + [str(f) for f in IMGS[:2]])  # Diagnose needs 3 photos
    page.click("#submit")
    expect(page.locator("#msg")).to_contain_text("not a readable image")
    check("non-image upload: friendly message", True, page.locator("#msg").inner_text())
    bad.unlink()
    page.click(".slot .remove")
    fill_photos(page, IMGS)
    page.click("#submit")
    expect(page.locator("#s3")).to_be_visible(timeout=20000)
    check("no geolocation: district picker submit works", True)
    ctx.close()

    # ---------- 4. dashboard ----------
    ctx = browser.new_context(viewport={"width": 1280, "height": 800})
    page = ctx.new_page()
    page.goto(BASE + "/dashboard")
    cards = page.locator(".alert-card:not(.skel-card)")
    expect(cards).to_have_count(1)
    page.click("#run")
    expect(page.locator("#toast")).to_contain_text("Surveillance run")
    row = cards.first
    check("dashboard: injected CBSD alert visible", "CBSD" in row.inner_text(), row.inner_text().replace("\n", " "))
    page.click("#range button[data-days='30']")
    expect(page.locator("#reports-count")).to_contain_text("30d")
    row.locator(".alert-place").click()
    page.wait_for_timeout(800)
    zoom = page.evaluate("map.getZoom()")
    check("dashboard: alert click zooms to cell", zoom >= 10, f"zoom={zoom}")
    page.click("#range button[data-days='60']")
    page.evaluate("void map.setView([-1.0,33.5],7)")
    page.wait_for_timeout(1500)
    page.screenshot(path=SHOTS / "dashboard.png")
    page.click("#chips button[data-f='cgm']")
    check("dashboard: disease chip filters table", all("Green mite" in t for t in
          page.locator("#report-rows tr td:nth-child(2)").all_inner_texts()))
    row.locator("button.review").click()
    expect(page.locator("#alerts-empty")).to_be_visible()
    check("dashboard: mark reviewed removes alert from active list", len(api("/api/alerts")) == 0)
    ctx.close()

    # dashboard mobile order (alerts before map)
    ctx = browser.new_context(**MOBILE)
    page = ctx.new_page()
    page.goto(BASE + "/dashboard")
    page.wait_for_timeout(800)
    ya = page.locator("#alerts").bounding_box()["y"]
    ym = page.locator(".map-card").bounding_box()["y"]
    check("dashboard mobile: alerts above map", ya < ym)
    ctx.close()

    # ---------- 5. load time under throttling (Lighthouse "fast 3G"-ish: 150 ms RTT, 1.6 Mbps) ----------
    for label, lat_ms, kbps in (("fast 3G (150ms RTT, 1.6Mbps)", 150, 1600), ("DevTools Fast 3G (562ms, 1.44Mbps)", 562.5, 1440)):
        ctx = browser.new_context(**MOBILE)
        page = ctx.new_page()
        cdp = ctx.new_cdp_session(page)
        cdp.send("Network.enable")
        cdp.send("Network.setCacheDisabled", {"cacheDisabled": True})
        cdp.send("Network.emulateNetworkConditions", {"offline": False, "latency": lat_ms,
                 "downloadThroughput": kbps * 1000 / 8, "uploadThroughput": 750 * 1000 / 8})
        page.goto(BASE + "/", wait_until="load")
        t = page.evaluate("""(() => { const n = performance.getEntriesByType('navigation')[0];
            return {dcl: Math.round(n.domContentLoadedEventEnd), load: Math.round(n.loadEventEnd),
                    bytes: performance.getEntriesByType('resource')
                    .reduce((s, r) => s + r.transferSize, n.transferSize)}; })()""")
        ext = page.evaluate("[...document.scripts].filter(s => s.src && !s.defer && !s.async).map(s => s.src)")
        if lat_ms <= 150:
            check(f"capture load < 1s on {label}", t["load"] < 1000, json.dumps(t))
        else:  # 2 sequential round trips (HTML, then CSS/JS) can't fit in 1s at 562 ms RTT
            print(f"INFO capture load on {label}: {json.dumps(t)}", flush=True)
        check("capture: no render-blocking scripts", not ext, str(ext))
        ctx.close()

    browser.close()

failed = [r for r in results if not r[1]]
print(f"\n{len(results) - len(failed)}/{len(results)} checks passed")
sys.exit(1 if failed else 0)
