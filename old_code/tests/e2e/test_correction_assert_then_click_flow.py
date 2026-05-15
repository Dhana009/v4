from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

from .harness import capture_picker_arm_evidence
from .harness import click_autoworkbench_tab
from .harness import start_e2e_session
from .harness import wait_for_overlay_ready
from .harness import wait_for_autoworkbench_execution_progress
from .harness import wait_for_autoworkbench_plan_ready
from .harness import extract_latest_recording_step_payload
from .harness import wait_for_locator_count
from .harness import recording_step_code_lines
from .harness import wait_for_process_log_markers_async


def test_correction_assert_then_click_flow() -> None:
    try:
        from playwright.async_api import async_playwright  # noqa: F401
    except ImportError:
        pytest.skip("playwright.async_api is not available in this environment")

    asyncio.run(_run_correction_assert_then_click_flow())


async def _run_correction_assert_then_click_flow() -> None:
    app_root = Path(__file__).resolve().parent / "fixtures" / "test_app"
    async with start_e2e_session(test_name="correction_assert_then_click_flow", app_root=app_root) as session:
        page = session.page
        start_url = f"{session.static_server.base_url}/index.html"

        await page.goto(start_url, wait_until="domcontentloaded")
        await session.run_stage("overlay_loaded", 10.0, lambda: wait_for_overlay_ready(page, timeout_ms=8000))

        async def arm_picker() -> None:
            session.record_picker_arm_evidence(await capture_picker_arm_evidence(page))
            await click_autoworkbench_tab(page, "steps")
            session.record_picker_arm_evidence(steps_tab_clicked=True)
            attach_button = page.get_by_role("button", name="Attach Element").first
            await attach_button.wait_for(state="visible", timeout=8000)
            session.record_picker_arm_evidence(picker_state_changed=True)
            await attach_button.click()
            await page.get_by_role("button", name="Click page element…").first.wait_for(state="visible", timeout=8000)

        await session.run_stage("picker_armed", 10.0, arm_picker)

        async def pick_get_started() -> None:
            await page.get_by_role("button", name="Get started").click()
            attach_button = page.get_by_role("button", name="Attach Element").first
            await attach_button.wait_for(state="visible", timeout=8000)
            target_summary = page.locator(".ide-step-target-summary").first
            await target_summary.wait_for(state="visible", timeout=8000)

        await session.run_stage("element_picked", 10.0, pick_get_started)

        async def prepare_click_step() -> None:
            intent_input = page.locator(".ide-step-input").first
            await intent_input.fill("click this button")
            outcome_chip = page.locator(".ide-step-outcome").get_by_role("button", name="navigation")
            await outcome_chip.click()
            await page.locator(".ide-step-topline .ide-badge.b-ready").first.wait_for(state="visible", timeout=8000)

        await session.run_stage("pending_step_added", 10.0, prepare_click_step)

        async def run_pending_step() -> None:
            await click_autoworkbench_tab(page, "workbench")
            run_button = page.get_by_role("button", name="Run Pending Steps").first
            await run_button.wait_for(state="visible", timeout=8000)
            await run_button.click()

        await session.run_stage("run_clicked", 10.0, run_pending_step)

        async def wait_for_initial_plan_ready() -> None:
            await wait_for_autoworkbench_plan_ready(page, timeout_ms=20000)
            plan_review_card = _plan_review_card(page)
            initial_children = plan_review_card.locator(".ide-plan-child-desc")
            assert await initial_children.count() == 1
            initial_child_text = (await initial_children.first.inner_text()).strip().lower()
            assert "get started" in initial_child_text

        await session.run_stage("initial_plan_ready_seen", 25.0, wait_for_initial_plan_ready)

        async def send_correction() -> None:
            correction_input = page.get_by_placeholder("Type correction…").first
            await correction_input.fill("assert first then click")
            send_button = page.get_by_role("button", name="Send Correction").first
            await send_button.click()
            await wait_for_autoworkbench_plan_ready(page, timeout_ms=8000)

        await session.run_stage("correction_sent", 10.0, send_correction)

        async def wait_for_corrected_plan_ready() -> None:
            await wait_for_autoworkbench_plan_ready(page, timeout_ms=20000)
            plan_review_card = _plan_review_card(page)
            corrected_children = plan_review_card.locator(".ide-plan-child-desc")
            await wait_for_locator_count(corrected_children, 2, timeout_ms=20000)
            assert await page.locator(".ide-clarification-question").count() == 0

        await session.run_stage("corrected_plan_ready_seen", 25.0, wait_for_corrected_plan_ready)

        async def confirm_corrected_plan() -> None:
            confirm_plan_button = page.get_by_role("button", name="Confirm Plan").first
            await confirm_plan_button.click()
            await wait_for_process_log_markers_async(session.backend, ["[CONFIRMED_PLAN]"], timeout_s=10.0)

        await session.run_stage("corrected_plan_confirmed", 10.0, confirm_corrected_plan)

        async def wait_for_corrected_recording() -> None:
            await wait_for_autoworkbench_execution_progress(page, timeout_ms=10000)
            await wait_for_process_log_markers_async(session.backend, ["[EXECUTION_CONTRACT]"], timeout_s=10.0)

            recorded_step = page.locator(".ide-recorded-step").first
            await recorded_step.wait_for(state="visible", timeout=20000)
            recorded_children = recorded_step.locator(".ide-plan-child-desc")
            assert await recorded_children.count() == 2
            recorded_step_count = await page.locator(".ide-stat-num").first.inner_text()
            assert recorded_step_count.strip() == "1"
            await wait_for_process_log_markers_async(session.backend, ["[CONFIRMED_CURSOR]"], timeout_s=15.0)

        await session.run_stage("corrected_step_recorded_seen", 25.0, wait_for_corrected_recording)

        async def wait_for_corrected_code_update() -> None:
            await wait_for_process_log_markers_async(session.backend, ["[CODE_UPDATE]"], timeout_s=15.0)
            backend_logs = session.backend_logs()
            assert_line = 'await expect(page.getByTestId("get-started")).toBeVisible();'
            click_line = 'await page.getByTestId("get-started").click();'
            recording_payload = extract_latest_recording_step_payload(backend_logs)
            assert recording_payload is not None
            assert [child["type"] for child in recording_payload["children"]] == ["assert", "click"]
            assert recording_step_code_lines(recording_payload) == [assert_line, click_line]
            assert page.url.endswith("/agents.html")

        await session.run_stage("corrected_code_update_seen", 25.0, wait_for_corrected_code_update)
def _plan_review_card(page):
    return page.locator(".ide-card").filter(has_text="// plan review").first
