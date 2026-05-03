from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

from .harness import start_e2e_session
from .harness import wait_for_process_log_markers
from .harness import wait_for_agents_page
from .harness import wait_for_overlay_ready


def test_basic_click_flow() -> None:
    try:
        from playwright.async_api import async_playwright  # noqa: F401
    except ImportError:
        pytest.skip("playwright.async_api is not available in this environment")

    asyncio.run(_run_basic_click_flow())


async def _run_basic_click_flow() -> None:
    app_root = Path(__file__).resolve().parent / "fixtures" / "test_app"
    async with start_e2e_session(test_name="basic_click_flow", app_root=app_root) as session:
        page = session.page

        await wait_for_overlay_ready(page)

        attach_button = page.get_by_role("button", name="Attach Element").first
        await attach_button.click()
        await page.get_by_role("button", name="Click page element…").first.wait_for(state="visible", timeout=15000)

        await page.get_by_role("button", name="Get started").click()

        intent_input = page.locator(".ide-step-input").first
        await intent_input.fill("click this button")

        outcome_chip = page.locator(".ide-step-outcome").get_by_role("button", name="navigation")
        await outcome_chip.click()

        run_button = page.get_by_role("button", name="Run Pending Steps").first
        await run_button.click()

        confirm_plan_button = page.get_by_role("button", name="Confirm Plan").first
        await confirm_plan_button.wait_for(state="visible", timeout=120000)
        await confirm_plan_button.click()

        await wait_for_agents_page(page, timeout_ms=120000)

        recorded_step_title = page.locator(".ide-recorded-step-title").filter(has_text="Clicked Get started").first
        await recorded_step_title.wait_for(state="visible", timeout=120000)

        recorded_step_count = await page.locator(".ide-stat-num").first.inner_text()
        assert recorded_step_count.strip() == "1"

        await page.locator(".ide-mini-tabs").get_by_role("button", name="Code").click()
        recorded_code = await page.locator(".ide-recorded-code").inner_text()
        assert "click" in recorded_code.lower()

        await page.locator(".ide-tabs").get_by_role("button", name="Code").click()
        code_preview = await page.locator(".ide-code").inner_text()
        assert "click" in code_preview.lower()

        backend_logs = wait_for_process_log_markers(
            session.backend,
            [
                "[PHASE]",
                "[CONFIRMED_PLAN]",
                "[EXECUTION_CONTRACT]",
                "[RECORDING_TARGET]",
                "[CODE_UPDATE]",
            ],
            timeout_s=120,
        )
        for marker in [
            "[PHASE]",
            "[CONFIRMED_PLAN]",
            "[EXECUTION_CONTRACT]",
            "[RECORDING_TARGET]",
            "[CODE_UPDATE]",
        ]:
            assert marker in backend_logs, f"missing {marker} in backend logs"
