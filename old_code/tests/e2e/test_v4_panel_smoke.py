"""
tests/e2e/test_v4_panel_smoke.py

V4 panel smoke (Sprint 7 integration pass).

Verifies the v4-driven IDE panel mounts inside the docked Shadow DOM
host against the local fixture app:

- aw-shadow-host attaches and the panel becomes visible
- canonical testids (aw-panel, aw-tabs, aw-tab-*, aw-footer) render
- tab switching changes the panel body
- empty states surface when the backend has not yet sent events

No paid LLM, no live websites. Uses the existing fixtures app served
by `start_e2e_session`.
"""
from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

from .harness import start_e2e_session


def test_v4_panel_smoke() -> None:
    try:
        from playwright.async_api import async_playwright  # noqa: F401
    except ImportError:
        pytest.skip("playwright.async_api is not available in this environment")

    asyncio.run(_run_v4_panel_smoke())


async def _run_v4_panel_smoke() -> None:
    app_root = Path(__file__).resolve().parent / "fixtures" / "test_app"
    async with start_e2e_session(test_name="v4_panel_smoke", app_root=app_root) as session:
        page = session.page
        docs_url = f"{session.static_server.base_url}/index.html"

        await page.goto(docs_url, wait_until="domcontentloaded")

        # Shadow DOM host attaches at #autoworkbench-root/#aw-shadow-host.
        await page.locator("#autoworkbench-root").wait_for(state="attached", timeout=10000)

        # v4 panel mounts inside the open shadow root — Playwright CSS engine
        # pierces shadow boundaries automatically.
        panel = page.locator('[data-testid="aw-panel"]').first
        await panel.wait_for(state="visible", timeout=10000)

        # Tab strip and canonical tabs render
        await page.locator('[data-testid="aw-tabs"]').first.wait_for(state="visible", timeout=5000)
        for tab in ("llm", "steps", "rec", "code", "trace"):
            await page.locator(f'[data-testid="aw-tab-{tab}"]').first.wait_for(state="visible", timeout=5000)

        # Footer renders with phase placeholder
        await page.locator('[data-testid="aw-footer"]').first.wait_for(state="visible", timeout=5000)

        # Switch to Steps tab → steps body renders (empty or populated).
        await page.locator('[data-testid="aw-tab-steps"]').first.click()
        await page.locator('[data-testid="steps-tab"]').first.wait_for(state="visible", timeout=5000)

        # Switch to Recorded tab → recorded body renders.
        await page.locator('[data-testid="aw-tab-rec"]').first.click()
        await page.locator('[data-testid="recorded-tab"]').first.wait_for(state="visible", timeout=5000)

        # Switch to Code tab → code body renders (empty until code_update).
        await page.locator('[data-testid="aw-tab-code"]').first.click()
        await page.locator('[data-testid="code-tab"]').first.wait_for(state="visible", timeout=5000)

        # Switch to Trace tab → empty (or known event types render)
        await page.locator('[data-testid="aw-tab-trace"]').first.click()
        await page.locator('[data-testid="trace-tab"]').first.wait_for(state="visible", timeout=5000)
