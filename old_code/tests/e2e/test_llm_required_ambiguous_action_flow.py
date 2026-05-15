from __future__ import annotations

import asyncio
import json
import time
from pathlib import Path

import pytest

from .harness import click_autoworkbench_tab
from .harness import start_e2e_session
from .harness import wait_for_overlay_ready


def test_llm_required_ambiguous_action_flow() -> None:
    try:
        from playwright.async_api import async_playwright  # noqa: F401
    except ImportError:
        pytest.skip("playwright.async_api is not available in this environment")

    artifact_dir = asyncio.run(_run_llm_required_ambiguous_action_flow())
    report = json.loads((artifact_dir / "token-report.json").read_text(encoding="utf-8"))

    assert report["call_count"] > 0
    assert report["total_estimated_input_tokens"] > 0
    assert "step_plan_normalizer" in report["purposes"]
    assert "deterministic_fast_path" not in report["purposes"]


async def _run_llm_required_ambiguous_action_flow() -> Path:
    app_root = Path(__file__).resolve().parent / "fixtures" / "test_app"
    async with start_e2e_session(test_name="llm_required_ambiguous_action_flow", app_root=app_root) as session:
        page = session.page
        fixture_url = f"{session.static_server.base_url}/ambiguous-actions.html"

        await page.goto(fixture_url, wait_until="domcontentloaded")
        await session.run_stage("overlay_loaded", 10.0, lambda: wait_for_overlay_ready(page, timeout_ms=8000))

        async def prepare_pending_step() -> None:
            await click_autoworkbench_tab(page, "steps")
            intent_input = page.locator(".ide-step-input").first
            await intent_input.fill("Click Save")
            outcome_chip = page.locator(".ide-step-outcome").get_by_role("button", name="not_sure")
            await outcome_chip.click()
            await page.locator(".ide-step-topline .ide-badge.b-ready").first.wait_for(state="visible", timeout=8000)

        await session.run_stage("pending_step_added", 10.0, prepare_pending_step)

        async def click_run() -> None:
            await click_autoworkbench_tab(page, "workbench")
            run_button = page.get_by_role("button", name="Run Pending Steps").first
            await run_button.wait_for(state="visible", timeout=8000)
            await run_button.click()

        await session.run_stage("run_clicked", 10.0, click_run)

        async def wait_for_llm_response() -> str:
            return await _wait_for_plan_or_clarification(page, timeout_ms=30000)

        response_kind = await session.run_stage("llm_response_seen", 35.0, wait_for_llm_response)

        async def assert_safe_llm_behavior() -> None:
            backend_logs = session.backend_logs()
            assert "[LLM_TELEMETRY]" in backend_logs
            assert "[MODEL_ROUTER]" in backend_logs
            assert "purpose=step_plan_normalizer" in backend_logs
            assert "[EXECUTION_CONTRACT]" not in backend_logs
            assert "[FAST_PATH] qualified" not in backend_logs
            assert "[FAST_PATH] confirmed" not in backend_logs
            assert "via action_click" not in backend_logs
            assert await page.locator(".ide-recorded-step").count() == 0
            assert page.url == fixture_url

            if response_kind == "clarification":
                clarification_question = page.locator(".ide-clarification-question").first
                question_text = (await clarification_question.inner_text()).strip()
                assert question_text
            else:
                confirm_plan_button = page.get_by_role("button", name="Confirm Plan").first
                await confirm_plan_button.wait_for(state="visible", timeout=5000)

        await session.run_stage("safe_llm_behavior_verified", 10.0, assert_safe_llm_behavior)

        return session.artifact_dir


async def _wait_for_plan_or_clarification(page, *, timeout_ms: int) -> str:
    deadline = time.monotonic() + timeout_ms / 1000
    clarification_question = page.locator(".ide-clarification-question").first
    confirm_plan_button = page.get_by_role("button", name="Confirm Plan").first

    while time.monotonic() < deadline:
        try:
            if await clarification_question.is_visible():
                return "clarification"
        except Exception:
            pass
        try:
            if await confirm_plan_button.is_visible():
                return "plan_ready"
        except Exception:
            pass
        await asyncio.sleep(0.25)

    raise TimeoutError("Timed out waiting for plan review or clarification")
