from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

from .harness import click_autoworkbench_tab
from .harness import start_e2e_session
from .harness import wait_for_overlay_ready
from .harness import wait_for_process_log_markers_async
from .harness import wait_for_locator_text


def test_visible_assertion_flow() -> None:
    try:
        from playwright.async_api import async_playwright  # noqa: F401
    except ImportError:
        pytest.skip("playwright.async_api is not available in this environment")

    asyncio.run(_run_visible_assertion_flow())


async def _run_visible_assertion_flow() -> None:
    app_root = Path(__file__).resolve().parent / "fixtures" / "test_app"
    async with start_e2e_session(test_name="visible_assertion_flow", app_root=app_root) as session:
        page = session.page
        docs_url = f"{session.static_server.base_url}/playwright_docs_like.html"

        await page.goto(docs_url, wait_until="domcontentloaded")
        await session.run_stage("overlay_loaded", 10.0, lambda: wait_for_overlay_ready(page, timeout_ms=8000))

        async def arm_picker() -> None:
            await click_autoworkbench_tab(page, "steps")
            attach_button = page.get_by_role("button", name="Attach Element").first
            await attach_button.wait_for(state="visible", timeout=8000)
            await attach_button.click()
            await page.get_by_role("button", name="Click page element…").first.wait_for(state="visible", timeout=8000)

        await session.run_stage("visible_assertion_picker_armed", 10.0, arm_picker)

        async def pick_heading() -> None:
            await page.get_by_role("heading", name="Playwright Test Agents").click()
            attach_button = page.get_by_role("button", name="Attach Element").first
            await attach_button.wait_for(state="visible", timeout=8000)
            target_summary = page.locator(".ide-step-target-summary").first
            await target_summary.wait_for(state="visible", timeout=8000)

        await session.run_stage("visible_assertion_element_picked", 10.0, pick_heading)

        async def prepare_pending_step() -> None:
            intent_input = page.locator(".ide-step-input").first
            await intent_input.fill("assert this is visible")
            await page.locator(".ide-step-topline .ide-badge.b-ready").first.wait_for(state="visible", timeout=8000)

        await session.run_stage("visible_assertion_pending_step_added", 10.0, prepare_pending_step)

        async def click_run() -> None:
            await click_autoworkbench_tab(page, "workbench")
            run_button = page.get_by_role("button", name="Run Pending Steps").first
            await run_button.wait_for(state="visible", timeout=8000)
            await run_button.click()

        await session.run_stage("visible_assertion_run_clicked", 10.0, click_run)

        async def wait_for_plan_ready() -> None:
            confirm_plan_button = page.get_by_role("button", name="Confirm Plan").first
            await confirm_plan_button.wait_for(state="visible", timeout=20000)
            await _wait_for_page_mode(page, "plan review", timeout_ms=20000)

        await session.run_stage("visible_assertion_plan_ready_seen", 25.0, wait_for_plan_ready)

        async def confirm_plan() -> None:
            confirm_plan_button = page.get_by_role("button", name="Confirm Plan").first
            await confirm_plan_button.click()
            await wait_for_process_log_markers_async(session.backend, ["[CONFIRMED_PLAN]"], timeout_s=10.0)

        await session.run_stage("visible_assertion_confirm_clicked", 10.0, confirm_plan)

        async def wait_for_execution_started() -> None:
            await page.locator(".ide-hd-state").first.wait_for(state="visible", timeout=10000)
            await _wait_for_page_mode(page, "executing", timeout_ms=10000)
            await wait_for_process_log_markers_async(session.backend, ["[EXECUTION_CONTRACT]"], timeout_s=10.0)

        await session.run_stage("visible_assertion_execution_started", 15.0, wait_for_execution_started)

        async def wait_for_recorded_step() -> None:
            recorded_step = page.locator(".ide-recorded-step").first
            await recorded_step.wait_for(state="visible", timeout=20000)
            recorded_step_title = (await recorded_step.locator(".ide-recorded-step-title").first.inner_text()).strip().lower()
            assert "visible" in recorded_step_title
            assert "click" not in recorded_step_title
            recorded_child_desc = (await recorded_step.locator(".ide-plan-child-desc").first.inner_text()).strip().lower()
            assert "playwright test agents" in recorded_child_desc
            recorded_step_count = await page.locator(".ide-stat-num").first.inner_text()
            assert recorded_step_count.strip() == "1"
            await wait_for_process_log_markers_async(session.backend, ["[CONFIRMED_CURSOR]"], timeout_s=15.0)

        await session.run_stage("visible_assertion_step_recorded_seen", 25.0, wait_for_recorded_step)

        async def wait_for_code_update() -> None:
            await wait_for_process_log_markers_async(session.backend, ["[CODE_UPDATE]"], timeout_s=15.0)
            backend_logs = session.backend_logs()
            recording_line = next(
                line for line in backend_logs.splitlines() if "[AGENT] recording step:" in line
            )
            assert 'action": "assert"' in recording_line
            assert 'generated_line": "await expect(' in recording_line
            assert 'toBeVisible();' in recording_line
            assert '.click();' not in recording_line
            assert page.url == docs_url

        await session.run_stage("visible_assertion_code_update_seen", 25.0, wait_for_code_update)


async def _wait_for_page_mode(page, expected_mode: str, timeout_ms: int) -> None:
    await wait_for_locator_text(page.locator(".ide-hd-state").first, expected_mode, timeout_ms=timeout_ms)
