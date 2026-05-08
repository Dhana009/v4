from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

from .harness import click_autoworkbench_tab
from .harness import start_e2e_session
from .harness import wait_for_agents_page
from .harness import wait_for_overlay_ready
from .harness import wait_for_locator_text
from .harness import wait_for_process_log_markers_async


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

        await session.run_stage("overlay_loaded", 10.0, lambda: wait_for_overlay_ready(page, timeout_ms=8000))

        async def arm_picker() -> None:
            await click_autoworkbench_tab(page, "steps")
            attach_button = page.get_by_role("button", name="Attach Element").first
            await attach_button.wait_for(state="visible", timeout=8000)
            await attach_button.click()
            await page.get_by_role("button", name="Click page element…").first.wait_for(state="visible", timeout=8000)

        await session.run_stage("picker_armed", 10.0, arm_picker)

        async def pick_element() -> None:
            await page.get_by_role("button", name="Get started").click()
            attach_button = page.get_by_role("button", name="Attach Element").first
            await attach_button.wait_for(state="visible", timeout=8000)
            target_summary = page.locator(".ide-step-target-summary").first
            await target_summary.wait_for(state="visible", timeout=8000)

        await session.run_stage("element_picked", 10.0, pick_element)

        async def prepare_pending_step() -> None:
            intent_input = page.locator(".ide-step-input").first
            await intent_input.fill("click this button")
            outcome_chip = page.locator(".ide-step-outcome").get_by_role("button", name="navigation")
            await outcome_chip.click()
            await page.locator(".ide-step-topline .ide-badge.b-ready").first.wait_for(state="visible", timeout=8000)

        await session.run_stage("pending_step_added", 10.0, prepare_pending_step)

        async def click_run() -> None:
            await click_autoworkbench_tab(page, "workbench")
            run_button = page.get_by_role("button", name="Run Pending Steps").first
            await run_button.wait_for(state="visible", timeout=8000)
            await run_button.click()

        await session.run_stage("run_clicked", 10.0, click_run)

        async def wait_for_plan_ready() -> None:
            confirm_plan_button = page.get_by_role("button", name="Confirm Plan").first
            await confirm_plan_button.wait_for(state="visible", timeout=20000)
            await _wait_for_page_mode(page, "plan review", timeout_ms=20000)

        await session.run_stage("plan_ready_seen", 25.0, wait_for_plan_ready)

        async def confirm_plan() -> None:
            confirm_plan_button = page.get_by_role("button", name="Confirm Plan").first
            await confirm_plan_button.click()
            await wait_for_process_log_markers_async(session.backend, ["[CONFIRMED_PLAN]"], timeout_s=10.0)

        await session.run_stage("confirm_clicked", 10.0, confirm_plan)

        async def wait_for_execution_started() -> None:
            await wait_for_agents_page(page, timeout_ms=10000)
            await wait_for_process_log_markers_async(session.backend, ["[EXECUTION_CONTRACT]"], timeout_s=10.0)

        await session.run_stage("execution_started", 15.0, wait_for_execution_started)

        async def wait_for_recorded_step() -> None:
            recorded_step = page.locator(".ide-recorded-step").first
            await recorded_step.wait_for(state="visible", timeout=20000)
            recorded_step_title = recorded_step.locator(".ide-recorded-step-title").first
            await recorded_step_title.wait_for(state="visible", timeout=20000)
            recorded_step_text = (await recorded_step_title.inner_text()).strip().lower()
            assert "click" in recorded_step_text
            recorded_child_desc = (await recorded_step.locator(".ide-plan-child-desc").first.inner_text()).strip()
            assert "Get started" in recorded_child_desc
            recorded_step_count = await page.locator(".ide-stat-num").first.inner_text()
            assert recorded_step_count.strip() == "1"
            await wait_for_process_log_markers_async(session.backend, ["[CONFIRMED_CURSOR]"], timeout_s=15.0)

        await session.run_stage("step_recorded_seen", 25.0, wait_for_recorded_step)

        async def wait_for_code_update() -> None:
            await wait_for_process_log_markers_async(session.backend, ["[CODE_UPDATE]"], timeout_s=15.0)
            backend_logs = session.backend_logs()
            assert 'generated_line": "await page.getByTestId(' in backend_logs
            assert '.click();' in backend_logs

        await session.run_stage("code_update_seen", 25.0, wait_for_code_update)


async def _wait_for_page_mode(page, expected_mode: str, timeout_ms: int) -> None:
    await wait_for_locator_text(page.locator(".ide-hd-state").first, expected_mode, timeout_ms=timeout_ms)
