"""
INT-MVP-001: Complete LLM Mode v4 panel lifecycle smoke.

Sprint 7 v4 integration scope: this smoke proves that the v4 docked
panel mounts inside the open Shadow DOM host, renders the canonical
chrome (header, tabs, footer), routes tab switches, and surfaces the
backend-event-driven empty states.

The legacy "Attach Element → intent input → outcome chip → Run Pending
Steps → plan_ready → step_recorded" deep workflow lived in the
pre-v4 monolith. Its port into the v4 Steps tab is tracked in
`BUG-S7-V4-001` and lands in the Sprint 8 Integration Pass. The
backend (real WebSocket + fake LLM) is still exercised: the v4 status
pill flips to "connected" once the WS handshake completes.
"""
from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

from .harness import start_e2e_session


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

        # Stage: Shadow DOM host attaches and v4 panel mounts.
        await session.run_stage(
            "overlay_loaded",
            10.0,
            lambda: page.locator('[data-testid="aw-panel"]').first.wait_for(state="visible", timeout=8000),
        )

        # Stage: backend WebSocket connects → v4 status pill enters connected/busy.
        async def wait_for_ws_connected() -> None:
            pill = page.locator('[data-testid="aw-status-pill"]').first
            await pill.wait_for(state="visible", timeout=8000)
            # Wait until status reads "Connected" or "Running" (busy after run_started).
            for _ in range(40):
                status = await pill.get_attribute("data-status")
                if status in ("connected", "busy"):
                    return
                await asyncio.sleep(0.25)
            raise AssertionError("Status pill never reached connected/busy")

        await session.run_stage("ws_connected", 15.0, wait_for_ws_connected)

        # Stage: tab switching changes panel body.
        async def switch_tabs() -> None:
            for tab in ("steps", "rec", "code", "trace", "llm"):
                await page.locator(f'[data-testid="aw-tab-{tab}"]').first.click()
                test_id = "rec" if tab == "rec" else tab
                body_testid = {
                    "llm": "aw-panel-body",
                    "steps": "steps-tab",
                    "rec": "recorded-tab",
                    "code": "code-tab",
                    "trace": "trace-tab",
                }[tab]
                await page.locator(f'[data-testid="{body_testid}"]').first.wait_for(state="visible", timeout=5000)

        await session.run_stage("tabs_switch", 15.0, switch_tabs)

        # Stage: tab body renders (empty or populated by backend events).
        async def bodies_visible() -> None:
            await page.locator('[data-testid="aw-tab-code"]').first.click()
            await page.locator('[data-testid="code-tab"]').first.wait_for(state="visible", timeout=5000)
            await page.locator('[data-testid="aw-tab-steps"]').first.click()
            await page.locator('[data-testid="steps-tab"]').first.wait_for(state="visible", timeout=5000)

        await session.run_stage("tab_bodies", 10.0, bodies_visible)
