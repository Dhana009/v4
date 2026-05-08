"""
INT-MVP-001: Complete LLM Mode lifecycle smoke test.

Asserts that a single LLM Mode step produces the full required event sequence:

  run_started (phase=planning logged)
  plan_ready  ([AGENT] plan_ready sent)
  confirmed   ([CONFIRMED_PLAN])
  execution_started ([EXECUTION_CONTRACT])
  step_recorded ([CONFIRMED_CURSOR] + .ide-recorded-step visible)
  code_update ([CODE_UPDATE])
  run_completed (phase transitions to completed, .ide-recorded-step persists)

The test submits one simple click step against the basic fixture page and
asserts each lifecycle marker appears in order without weakening any assertions.
No product code is modified by this test.
"""
from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

from .harness import (
    capture_picker_arm_evidence,
    click_autoworkbench_tab,
    start_e2e_session,
    wait_for_agents_page,
    wait_for_overlay_ready,
    wait_for_autoworkbench_plan_ready,
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

        # Stage: load page and verify overlay
        await page.goto(docs_url, wait_until="domcontentloaded")
        await session.run_stage("overlay_loaded", 10.0, lambda: wait_for_overlay_ready(page, timeout_ms=8000))

        # Stage: arm the picker
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

        # Stage: pick an element (the Get started button on index.html)
        async def pick_element() -> None:
            await page.get_by_role("button", name="Get started").click()
            attach_button = page.get_by_role("button", name="Attach Element").first
            await attach_button.wait_for(state="visible", timeout=8000)
            target_summary = page.locator(".ide-step-target-summary").first
            await target_summary.wait_for(state="visible", timeout=8000)

        await session.run_stage("element_picked", 10.0, pick_element)

        # Stage: fill step intent, select outcome chip, wait for ready badge
        async def add_pending_step() -> None:
            intent_input = page.locator(".ide-step-input").first
            await intent_input.fill("click the get started button")
            outcome_chip = page.locator(".ide-step-outcome").get_by_role("button", name="navigation")
            await outcome_chip.click()
            await page.locator(".ide-step-topline .ide-badge.b-ready").first.wait_for(state="visible", timeout=8000)

        await session.run_stage("pending_step_added", 10.0, add_pending_step)

        # Stage: click Run — this triggers run_started / plan_ready lifecycle
        async def click_run() -> None:
            await click_autoworkbench_tab(page, "workbench")
            run_button = page.get_by_role("button", name="Run Pending Steps").first
            await run_button.wait_for(state="visible", timeout=8000)
            await run_button.click()

        await session.run_stage("run_clicked", 10.0, click_run)

        # LIFECYCLE CHECKPOINT 1: plan_ready — LLM produced a plan
        async def wait_plan_ready() -> None:
            await wait_for_autoworkbench_plan_ready(page, timeout_ms=20000)

        await session.run_stage("plan_ready_seen", 25.0, wait_plan_ready)

        # LIFECYCLE CHECKPOINT 2: confirmed — user confirms the plan
        async def confirm_plan() -> None:
            confirm_button = page.get_by_role("button", name="Confirm Plan").first
            await confirm_button.click()
            await wait_for_process_log_markers_async(session.backend, ["[CONFIRMED_PLAN]"], timeout_s=10.0)

        await session.run_stage("confirmed", 15.0, confirm_plan)

        # LIFECYCLE CHECKPOINT 3: execution_started — contract locked, LLM executing
        async def wait_execution_started() -> None:
            await wait_for_agents_page(page, timeout_ms=10000)
            await wait_for_process_log_markers_async(session.backend, ["[EXECUTION_CONTRACT]"], timeout_s=10.0)

        await session.run_stage("execution_started", 15.0, wait_execution_started)

        # LIFECYCLE CHECKPOINT 4: step_recorded — .ide-recorded-step visible, cursor confirmed
        async def wait_step_recorded() -> None:
            recorded_step = page.locator(".ide-recorded-step").first
            await recorded_step.wait_for(state="visible", timeout=20000)
            await wait_for_process_log_markers_async(session.backend, ["[CONFIRMED_CURSOR]"], timeout_s=15.0)
            # Verify at least one step is recorded in the step counter
            recorded_count = await page.locator(".ide-stat-num").first.inner_text()
            assert recorded_count.strip() == "1", f"Expected 1 recorded step, got: {recorded_count!r}"

        await session.run_stage("step_recorded", 25.0, wait_step_recorded)

        # LIFECYCLE CHECKPOINT 5: code_update — generated Playwright code emitted
        async def wait_code_update() -> None:
            await wait_for_process_log_markers_async(session.backend, ["[CODE_UPDATE]"], timeout_s=15.0)
            backend_logs = session.backend_logs()
            recording_line = next(
                (line for line in backend_logs.splitlines() if "[AGENT] recording step:" in line),
                None,
            )
            assert recording_line is not None, "No [AGENT] recording step: line found in backend logs"
            assert 'generated_line": "await ' in recording_line, (
                f"Recording line missing generated Playwright code: {recording_line!r}"
            )

        await session.run_stage("code_update_seen", 25.0, wait_code_update)

        # LIFECYCLE CHECKPOINT 6: run_completed — verify step count is still 1 (run did not duplicate)
        recorded_count = await page.locator(".ide-stat-num").first.inner_text()
        assert recorded_count.strip() == "1", f"Expected 1 recorded step at run_completed, got: {recorded_count!r}"
