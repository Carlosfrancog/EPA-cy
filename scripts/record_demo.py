"""Record a REAL local Rails UI session with Playwright.

Run only against the local synthetic development app.
No simulated screenshots or invented model metrics.
"""
from __future__ import annotations

import os
import re
import shutil
import time
from pathlib import Path

from playwright.sync_api import sync_playwright

BASE = os.environ.get("EPA_DEMO_BASE_URL", "http://127.0.0.1:3000")
OUTPUT = Path(os.environ.get("EPA_DEMO_OUTPUT", "tmp/demo"))
OUTPUT.mkdir(parents=True, exist_ok=True)

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True, args=["--no-sandbox"])
    context = browser.new_context(
        viewport={"width": 1440, "height": 900},
        device_scale_factor=1,
        locale="pt-BR",
        color_scheme="light",
        record_video_dir=str(OUTPUT),
        record_video_size={"width": 1440, "height": 900},
    )
    page = context.new_page()
    page.set_default_timeout(15000)

    def navigate(section: str, pause_ms: int = 2600):
        page.locator(f'nav a[href="{section}"]').click()
        page.wait_for_load_state("domcontentloaded")
        page.wait_for_timeout(pause_ms)

    try:
        page.goto(BASE, wait_until="domcontentloaded")
        page.locator("h1").wait_for()
        page.wait_for_timeout(3800)

        navigate("/datasets", 3500)
        navigate("/architecture", 3200)
        navigate("/integrity", 3000)
        navigate("/models", 3000)
        navigate("/experiments", 3500)

        page.locator("#model").select_option("random_forest")
        page.locator("#seed").fill("20261029")
        page.wait_for_timeout(1300)
        page.get_by_role("button", name=re.compile("Executar experimento")).click()
        page.wait_for_url(re.compile(r"/experiments/\d+"), timeout=15000)

        # A genuine submitted Rails job must finish and produce a real report.
        deadline = time.monotonic() + 150
        while time.monotonic() < deadline:
            if page.locator(".status-completed").count():
                break
            if page.locator(".status-failed").count():
                raise RuntimeError("Experiment failed in the running application")
            page.wait_for_timeout(2500)
            page.reload(wait_until="domcontentloaded")
        else:
            raise TimeoutError("Experiment did not finish in 150 seconds")

        page.locator("table.runs-table").wait_for()
        page.wait_for_timeout(4000)
        page.mouse.wheel(0, 560)
        page.wait_for_timeout(3500)
        page.screenshot(path=str(OUTPUT / "results-real.png"), full_page=True)
        page.mouse.wheel(0, -620)
        page.wait_for_timeout(1500)
        page.locator('nav a[href="/experiments"]').click()
        page.wait_for_load_state("domcontentloaded")
        page.wait_for_timeout(2600)
        page.screenshot(path=str(OUTPUT / "experiments-real.png"), full_page=True)
    finally:
        video = page.video
        context.close()
        browser.close()

    raw = Path(video.path())
    final = OUTPUT / "raw-navigation.webm"
    shutil.copyfile(raw, final)
    print(f"Recorded actual Rails UI session: {final} ({final.stat().st_size} bytes)")
