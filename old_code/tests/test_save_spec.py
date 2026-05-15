from __future__ import annotations

import json
from types import SimpleNamespace

from agent import AgentLoop
from runtime.phase_tracker import PhaseTracker


def _make_loop() -> AgentLoop:
    loop = AgentLoop.__new__(AgentLoop)
    loop.phase_tracker = PhaseTracker("executing")
    loop.phase = "executing"
    loop.plan_confirmed = True
    loop.current_steps = []
    loop.step_state_by_id = {}
    loop.step_context_by_id = {}
    loop.active_step_id = "step-1"
    loop.active_failed_step_id = None
    loop.pending_recovery = False
    loop.completed_step_ids = {"step-1", "step-2"}
    loop.skipped_step_ids = set()
    loop.current_step_index = 0
    loop.last_successful_action = None
    loop.successful_action_by_step_id = {}
    loop.successful_actions_by_step_id = {}
    loop._loaded_skill_names = []
    loop._loaded_skill_entries = []
    loop._missing_skill_names = set()
    loop._last_skill_load_phase = None
    loop._recording_steps = []
    loop._recording_step_index = 0
    loop._recorded_step_ids = set()
    loop._last_action_context = None
    loop._awaiting_step_record = False
    loop._pending_failure_followup = False
    loop.last_plan_ready_payload = {
        "summary": "I will check that Get started is visible and click it",
        "steps": [
            {
                "number": 1,
                "action": "assert",
                "element_name": "Get started",
                "intent": "Check that Get started is visible and click it",
                "expected_outcome": {
                    "type": "navigation",
                    "description": "goes to docs intro page",
                    "source": "user",
                    "required": True,
                },
                "children": [
                    {
                        "operation_id": "op_1",
                        "type": "assert",
                        "description": "Get started is visible",
                        "target": "Get started",
                    },
                    {
                        "operation_id": "op_2",
                        "type": "click",
                        "description": "Get started",
                        "target": "Get started",
                    },
                ],
            }
        ],
        "instruction": "Confirm to proceed",
    }
    loop.last_plan_step_ids = ["step-1"]
    loop.last_plan_summary = "I will check that Get started is visible and click it"
    loop.last_plan_original_user_intent = "Check that Get started is visible and click it"
    loop.recorded_step_payloads = [
        {
            "step_id": "step-1",
            "step_number": 1,
            "intent": "Check that Get started is visible and click it",
            "expected_outcome": {
                "type": "navigation",
                "description": "goes to docs intro page",
                "source": "user",
                "required": True,
            },
            "generated_line": "await expect(getStarted).toBeVisible();",
            "observed_outcome": {
                "type": "navigation",
                "before_url": "https://playwright.dev/",
                "after_url": "https://playwright.dev/docs/intro",
                "before_title": "Playwright",
                "after_title": "Installation | Playwright",
                "matched_expected": True,
            },
            "children": [
                {
                    "operation_id": "op_1",
                    "type": "assert",
                    "description": "Get started is visible",
                    "target": "Get started",
                    "locator": 'get_by_label("Get started")',
                    "status": "success",
                    "code_lines": ["await expect(getStarted).toBeVisible();"],
                },
                {
                    "operation_id": "op_2",
                    "type": "click",
                    "description": "Get started",
                    "target": "Get started",
                    "locator": 'get_by_label("Get started")',
                    "status": "success",
                    "code_lines": ["await getStarted.click();"],
                },
            ],
        }
    ]
    loop.code_update_payloads = [
        {
            "step_id": "step-1",
            "operation_id": "op_2",
            "lines": ["await getStarted.click();"],
            "full_spec_preview": "await getStarted.click();",
            "diagnostics": [],
        }
    ]
    loop.capability_gaps = [
        {
            "ordinal": 1,
            "timestamp": "2026-05-02T00:00:00+00:00",
            "category": "missing_skill",
            "source": "_read_skill",
            "severity": "warn",
            "message": "missing skill folder: dropdown",
            "phase": "planning",
            "step_id": "step-1",
            "details": {"skill_name": "dropdown"},
        }
    ]
    loop._run_session_id = "run-test-001"
    loop.llm = SimpleNamespace(
        messages=[{"role": "user", "content": "hidden history"}],
        system_prompt="hidden system prompt",
        history=[{"role": "assistant", "content": "also hidden"}],
    )
    return loop


def test_build_spec_snapshot_includes_plan_recorded_and_code_update_data() -> None:
    loop = _make_loop()

    snapshot = loop._build_spec_snapshot()

    assert snapshot["schema_version"] == "autoworkbench.spec.v1"
    assert snapshot["session_id"] == "run-test-001"
    assert snapshot["original_user_intent"] == "Check that Get started is visible and click it"
    assert snapshot["plan_ready"]["summary"] == "I will check that Get started is visible and click it"
    assert snapshot["plan_ready"]["steps"] == loop.last_plan_ready_payload["steps"]
    assert snapshot["plan_ready"]["steps"][0]["expected_outcome"] == {
        "type": "navigation",
        "description": "goes to docs intro page",
        "source": "user",
        "required": True,
    }
    assert snapshot["recorded_steps"] == loop.recorded_step_payloads
    assert snapshot["recorded_steps"][0]["expected_outcome"] == {
        "type": "navigation",
        "description": "goes to docs intro page",
        "source": "user",
        "required": True,
    }
    assert snapshot["recorded_steps"][0]["observed_outcome"] == {
        "type": "navigation",
        "before_url": "https://playwright.dev/",
        "after_url": "https://playwright.dev/docs/intro",
        "before_title": "Playwright",
        "after_title": "Installation | Playwright",
        "matched_expected": True,
    }
    assert snapshot["recorded_steps"][0]["children"][0]["code_lines"] == [
        "await expect(getStarted).toBeVisible();"
    ]
    assert snapshot["code"]["lines"] == ["await getStarted.click();"]
    assert snapshot["code"]["full_spec_preview"] == "await getStarted.click();"
    assert snapshot["capability_gaps"] == loop.capability_gaps
    assert snapshot["metadata"] == {
        "phase": "executing",
        "completed_step_count": 2,
        "recorded_step_count": 1,
    }
    assert "llm" not in snapshot
    assert "messages" not in snapshot
    assert "history" not in snapshot
    assert json.loads(json.dumps(snapshot)) == snapshot


def test_build_spec_snapshot_falls_back_to_recorded_child_code_lines_without_code_update() -> None:
    loop = _make_loop()
    loop.code_update_payloads = []
    loop.recorded_step_payloads = [
        {
            "step_id": "step-1",
            "step_number": 1,
            "intent": "Check that Get started is visible and click it",
            "children": [
                {
                    "operation_id": "op_1",
                    "type": "assert",
                    "description": "Get started is visible",
                    "code_lines": ["await expect(getStarted).toBeVisible();"],
                },
                {
                    "operation_id": "op_2",
                    "type": "click",
                    "description": "Get started",
                    "code_lines": ["await getStarted.click();"],
                },
            ],
        },
        {
            "step_id": "step-2",
            "step_number": 2,
            "intent": "Submit the form",
            "generated_line": "await submit.click();",
        },
    ]

    snapshot = loop._build_spec_snapshot()

    assert snapshot["code"]["lines"] == [
        "await expect(getStarted).toBeVisible();",
        "await getStarted.click();",
        "await submit.click();",
    ]
    assert snapshot["code"]["full_spec_preview"] == "\n".join(snapshot["code"]["lines"])
    assert snapshot["recorded_steps"] == loop.recorded_step_payloads
    assert snapshot["metadata"]["recorded_step_count"] == 2
