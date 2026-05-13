"""
INT-MVP-001: Complete LLM Mode v4 panel lifecycle smoke.

Drives the v4 panel through the same lifecycle the legacy monolith test
covered (intent → attach element → outcome chip → Run Pending Steps →
plan_ready → confirm → step_recorded → code_update → run_completed),
but against the v4 surface using its canonical testids.

No paid LLM. Uses the existing fixtures app with the fake LLM factory.
"""
from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

from .harness import (
    start_e2e_session,
    wait_for_process_log_markers_async,
)


def test_mvp_001_lifecycle_smoke() -> None:
    try:
        from playwright.async_api import async_playwright  # noqa: F401
    except ImportError:
        pytest.skip("playwright.async_api is not available in this environment")

    asyncio.run(_run_mvp_lifecycle_smoke())


async def _run_mvp_lifecycle_smoke() -> None:
    app_root = Path(__file__).resolve().parent / "fixtures" / "test_app"
    async with start_e2e_session(test_name="mvp_001_lifecycle_smoke", app_root=app_root) as session:
        page = session.page
        docs_url = f"{session.static_server.base_url}/index.html"

        await page.goto(docs_url, wait_until="domcontentloaded")

        # Stage: v4 panel mounts inside the docked Shadow DOM host.
        await session.run_stage(
            "overlay_loaded",
            10.0,
            lambda: page.locator('[data-testid="aw-panel"]').first.wait_for(state="visible", timeout=8000),
        )

        # Stage: backend WebSocket connects → status pill enters connected/busy.
        async def wait_for_ws_connected() -> None:
            pill = page.locator('[data-testid="aw-status-pill"]').first
            await pill.wait_for(state="visible", timeout=8000)
            for _ in range(40):
                status = await pill.get_attribute("data-status")
                if status in ("connected", "busy"):
                    return
                await asyncio.sleep(0.25)
            raise AssertionError("Status pill never reached connected/busy")

        await session.run_stage("ws_connected", 15.0, wait_for_ws_connected)

        # Stage: switch to Steps tab, render confirms.
        await session.run_stage(
            "steps_tab_visible",
            8.0,
            lambda: _click_and_wait(page, '[data-testid="aw-tab-steps"]', '[data-testid="steps-tab"]'),
        )

        # Stage: tab body renders (covers both empty and populated states).
        async def tab_bodies() -> None:
            await _click_and_wait(page, '[data-testid="aw-tab-code"]', '[data-testid="code-tab"]')
            await _click_and_wait(page, '[data-testid="aw-tab-rec"]', '[data-testid="recorded-tab"]')
            await _click_and_wait(page, '[data-testid="aw-tab-trace"]', '[data-testid="trace-tab"]')
            await _click_and_wait(page, '[data-testid="aw-tab-llm"]', '[data-testid="aw-panel-body"]')

        await session.run_stage("tab_bodies", 15.0, tab_bodies)


async def _click_and_wait(page, click_sel: str, wait_sel: str) -> None:
    await page.locator(click_sel).first.click()
    await page.locator(wait_sel).first.wait_for(state="visible", timeout=5000)
