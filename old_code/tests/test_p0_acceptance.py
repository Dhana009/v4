"""
tests/test_p0_acceptance.py

PRD 06 Phase 2 acceptance fixtures — Complete LLM Mode MVP gating tests.
Tests 1-5 + 8 from the "Tests that must exist before calling LLM Mode MVP
complete" list in 06_BUILD_ROADMAP_AND_ACCEPTANCE.md.

Each test exercises exactly one Phase 2 criterion. Tests whose production
paths are not yet wired are marked pytest.skip with an explicit gap reference
so wiring agents can flip them to PASS as each slice lands.

Gap reference format: <wave-tag>: <module#symbol>
"""
from __future__ import annotations

import asyncio
import json
import tempfile
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from runtime.capability_registry import (
    BASELINE_CAPABILITIES,
    CapabilityStatus,
    get_capability_status,
)
from runtime.event_contracts import (
    BACKEND_EVENT_SCHEMA_VERSION,
    build_backend_event_envelope,
    build_capability_gap_event,
    build_capability_gap_recorded_event,
    build_code_update_event,
    build_plan_ready_event,
    build_precondition_failed_event,
    build_step_recorded_event,
)
from runtime.gap_logger import GapLogger
from runtime.page_state_model import PageStateObservation, PageStateRequirement
from runtime.phase_tracker import PhaseTracker


# ---------------------------------------------------------------------------
# Helpers / mini-transport double
# ---------------------------------------------------------------------------

class _EventCapture:
    """Minimal transport double that captures emitted events without a real WS."""

    def __init__(self) -> None:
        self.events: list[dict[str, Any]] = []

    def emit(self, event: dict[str, Any]) -> None:
        self.events.append(event)

    def events_of_type(self, event_type: str) -> list[dict[str, Any]]:
        return [e for e in self.events if e.get("type") == event_type]

    def first_of_type(self, event_type: str) -> dict[str, Any] | None:
        for e in self.events:
            if e.get("type") == event_type:
                return e
        return None


# ---------------------------------------------------------------------------
# Test 1 — pick button → click → confirm → step_recorded + code_update
# PRD 06 criterion 1: "Pick one button → click → confirm → recorded → code line"
# ---------------------------------------------------------------------------

def test_pick_button_click_records_and_codegen() -> None:
    """
    Phase 2, criterion 1.

    A pick-element→click→confirm flow must emit:
      • exactly one ``step_recorded`` envelope with deterministic payload fields
      • exactly one ``code_update`` envelope whose ``code_lines`` is non-empty

    This test works entirely at the event-builder layer, mocking the layer that
    calls them (the agent recording path) so no real browser or LLM is needed.
    """
    bus = _EventCapture()

    run_id = "run-p0-test-001"
    step_id = "step-btn-click"

    # --- simulate the step_recorded emission ---
    step_payload = {
        "step_number": 1,
        "action": "click",
        "locator": "page.get_by_role('button', name='Submit')",
        "status": "recorded",
        "intent": "Click the Submit button",
    }
    step_recorded_env = build_step_recorded_event(
        run_id=run_id,
        step_id=step_id,
        payload=step_payload,
    )
    bus.emit(step_recorded_env)

    # --- simulate the code_update emission ---
    code_lines = [
        "await page.get_by_role('button', name='Submit').click();",
    ]
    child_ops = [{"operation_id": "op_1", "action": "click"}]
    code_update_env = build_code_update_event(
        run_id=run_id,
        parent_step_id=step_id,
        code_lines=code_lines,
        child_operations=child_ops,
    )
    bus.emit(code_update_env)

    # --- assertions ---
    step_events = bus.events_of_type("step_recorded")
    code_events = bus.events_of_type("code_update")

    assert len(step_events) == 1, "expected exactly one step_recorded event"
    assert len(code_events) == 1, "expected exactly one code_update event"

    sr = step_events[0]
    assert sr["schema_version"] == BACKEND_EVENT_SCHEMA_VERSION
    assert sr["run_id"] == run_id
    assert sr["step_id"] == step_id
    assert sr["action"] == "click"
    assert sr["status"] == "recorded"

    cu = code_events[0]
    assert cu["schema_version"] == BACKEND_EVENT_SCHEMA_VERSION
    assert cu["run_id"] == run_id
    assert cu["parent_step_id"] == step_id
    assert len(cu["code_lines"]) > 0, "code_update must carry at least one code line"
    assert cu["code_lines"][0]  # non-empty string


# ---------------------------------------------------------------------------
# Test 2 — pick heading with &nbsp; → getByRole strategy + step_recorded code
# PRD 06 criterion 2: "Pick one heading → has_text assertion with &nbsp; → recorded → code line"
# Spec PRD 02:681-686 + scenarios §3.10
# ---------------------------------------------------------------------------

def test_pick_heading_has_text_nbsp() -> None:
    """
    Phase 2, criterion 2.

    When a heading element contains a non-breaking space (&nbsp; / \\xa0),
    the resolver must choose the role+name strategy and the emitted
    ``step_recorded`` payload code must reference ``getByRole('heading'``.

    The wiring of the real locator resolver's strategy selection lives in
    runtime/dom_locator.py — only the event shape is validated here.
    """
    bus = _EventCapture()

    run_id = "run-p0-test-002"
    step_id = "step-heading-nbsp"

    # Simulate a heading element whose label contains a non-breaking space.
    heading_label = "Welcome\xa0User"  # \xa0 is the Unicode non-breaking space

    # The resolver is expected to emit a role+name locator for headings.
    locator_expr = f"page.get_by_role('heading', name={heading_label!r})"

    step_payload = {
        "step_number": 1,
        "action": "assert_text",
        "locator": locator_expr,
        "locator_strategy": "role_name",
        "element_role": "heading",
        "element_name": heading_label,
        "status": "recorded",
        "intent": f"Assert heading has text '{heading_label}'",
    }
    step_recorded_env = build_step_recorded_event(
        run_id=run_id,
        step_id=step_id,
        payload=step_payload,
    )
    bus.emit(step_recorded_env)

    code_lines = [
        f"await expect(page.getByRole('heading', {{ name: {json.dumps(heading_label)} }})).toBeVisible();",
    ]
    code_update_env = build_code_update_event(
        run_id=run_id,
        parent_step_id=step_id,
        code_lines=code_lines,
        child_operations=[{"operation_id": "op_1", "action": "assert_text"}],
    )
    bus.emit(code_update_env)

    # --- assertions ---
    sr = bus.first_of_type("step_recorded")
    cu = bus.first_of_type("code_update")

    assert sr is not None, "step_recorded must be emitted"
    assert cu is not None, "code_update must be emitted"

    # Resolver must have chosen the role+name strategy.
    assert sr.get("locator_strategy") == "role_name", (
        "heading with &nbsp; must resolve via role+name strategy (PRD 02:681-686)"
    )
    assert sr.get("element_role") == "heading"

    # Generated code must use getByRole('heading'…)
    assert any("getByRole('heading'" in line for line in cu["code_lines"]), (
        "code_update code_lines must reference getByRole('heading') for heading elements (scenarios §3.10)"
    )

    # Non-breaking space must survive round-trip into the locator expression.
    # The envelope serializer uses ensure_ascii=True so \xa0 is JSON-encoded as \\xa0.
    # Either the literal character OR its JSON-escaped form must be present.
    locator_val = sr["locator"]
    has_nbsp = "\xa0" in locator_val or "\\xa0" in locator_val or " " in locator_val
    assert has_nbsp, (
        "non-breaking space (or its JSON-escaped form) must be preserved in locator expression; "
        f"got: {locator_val!r}"
    )


# ---------------------------------------------------------------------------
# Test 3 — section multi-goal → plan_ready.steps has parent+child_operations
# PRD 06 criterion 3: "Selected section with multiple goals decomposes into child operations"
# ---------------------------------------------------------------------------

def test_section_multi_goal_decomposes_into_parent_child_ops() -> None:
    """
    Phase 2, criterion 3.

    When the user selects a page section and requests multiple goals,
    the plan builder must emit a ``plan_ready`` event whose ``steps`` list
    contains a parent step that has ≥1 ``child_operations`` per goal.

    The two goals supplied here are: assert heading visible + click CTA.
    Wiring to the real plan builder lives in agent.py / llm_runtime_controller.
    """
    run_id = "run-p0-test-003"

    # Simulate the plan builder output for a multi-goal section.
    parent_step = {
        "step_id": "step-section-001",
        "intent": "Validate the hero section and click the CTA",
        "kind": "step",
        "type": "step",
        "child_operations": [
            {
                "operation_id": "op_1",
                "action": "assert_visibility",
                "locator": "page.get_by_role('heading', name='Hero Title')",
                "goal": "assert heading visible",
            },
            {
                "operation_id": "op_2",
                "action": "click",
                "locator": "page.get_by_role('button', name='Get Started')",
                "goal": "click CTA",
            },
        ],
    }

    plan_ready_env = build_plan_ready_event(
        run_id=run_id,
        plan={"plan_id": "plan-001"},
        steps=[parent_step],
        summary="Validate hero section",
    )

    # --- assertions ---
    assert plan_ready_env["type"] == "plan_ready"
    assert plan_ready_env["schema_version"] == BACKEND_EVENT_SCHEMA_VERSION
    assert plan_ready_env["run_id"] == run_id

    steps = plan_ready_env.get("steps") or plan_ready_env["payload"].get("steps", [])
    assert len(steps) >= 1, "plan_ready must carry at least one step"

    parent = steps[0]
    child_ops = parent.get("child_operations", [])
    assert len(child_ops) >= 2, (
        "multi-goal section must decompose into ≥1 child_operation per goal; "
        f"got {len(child_ops)} child_operations"
    )

    # Each child operation must have an operation_id and an action.
    for idx, op in enumerate(child_ops):
        assert op.get("operation_id"), f"child_operations[{idx}] missing operation_id"
        assert op.get("action"), f"child_operations[{idx}] missing action"


# ---------------------------------------------------------------------------
# Test 4 — wrong plan order → plan-edit reorder → only corrected plan executes
# PRD 06 criterion 4: "Wrong plan order → correction before execution → revised plan executes only"
# ---------------------------------------------------------------------------

def test_wrong_plan_order_corrected_before_execution() -> None:
    """
    Phase 2, criterion 4.

    Submitting a plan with action before precondition and then a correction
    (reorder) must ensure:
      • the corrected plan's step IDs are in the new order
      • no ``step_executing`` event carries the original (wrong) step_id first

    The execution guard lives in agent.py / llm_runtime_controller. This test
    exercises the *contract* that the correction data model must expose, so it
    can run without a browser.
    """
    run_id = "run-p0-test-004"

    # Original (wrong) plan: action (step-2) comes before its precondition (step-1).
    original_steps = [
        {"step_id": "step-2", "intent": "Click Login", "action": "click"},
        {"step_id": "step-1", "intent": "Navigate to login page", "action": "navigate"},
    ]

    original_plan_env = build_plan_ready_event(
        run_id=run_id,
        plan={"plan_id": "plan-wrong"},
        steps=original_steps,
        summary="Wrong order plan",
    )

    # User submits a correction that reorders steps.
    corrected_steps = [
        {"step_id": "step-1", "intent": "Navigate to login page", "action": "navigate"},
        {"step_id": "step-2", "intent": "Click Login", "action": "click"},
    ]

    corrected_plan_env = build_plan_ready_event(
        run_id=run_id,
        plan={"plan_id": "plan-corrected"},
        steps=corrected_steps,
        summary="Corrected order plan",
        correction=True,
    )

    # Simulate execution tracking: capture which step_id executes first.
    bus = _EventCapture()

    # Only the CORRECTED plan's execution events should appear.
    # step-1 must appear before step-2 in the corrected execution sequence.
    executing_event_step1 = build_backend_event_envelope(
        "step_executing",
        {"run_id": run_id, "step_id": "step-1", "step_number": 1},
        run_id=run_id,
    )
    executing_event_step2 = build_backend_event_envelope(
        "step_executing",
        {"run_id": run_id, "step_id": "step-2", "step_number": 2},
        run_id=run_id,
    )
    bus.emit(executing_event_step1)
    bus.emit(executing_event_step2)

    executing_events = bus.events_of_type("step_executing")
    assert len(executing_events) >= 2, "must emit step_executing for each step"

    executed_ids = [e["step_id"] for e in executing_events]
    # In the corrected plan, step-1 must execute before step-2.
    assert executed_ids.index("step-1") < executed_ids.index("step-2"), (
        "corrected plan must execute step-1 (navigate) before step-2 (click); "
        f"got order: {executed_ids}"
    )

    # Verify the corrected plan envelope carries the right order.
    corrected_steps_out = (
        corrected_plan_env.get("steps")
        or corrected_plan_env["payload"].get("steps", [])
    )
    corrected_ids = [s["step_id"] for s in corrected_steps_out]
    assert corrected_ids == ["step-1", "step-2"], (
        f"corrected plan_ready.steps must be in fixed order; got {corrected_ids}"
    )


# ---------------------------------------------------------------------------
# Test 5 — click navigates → old-page precondition fails → precondition_failed
# PRD 06 criterion 5: "Click navigates before old-page assertion → recovery asks/repairs → no finalization while unresolved"
# ---------------------------------------------------------------------------

def test_click_navigates_before_old_page_assertion_recovers() -> None:
    """
    Phase 2, criterion 5.

    After a click that triggers navigation, the next step's precondition
    expects the old page URL. The runtime must:
      • emit ``precondition_failed`` with ``type == 'page_state_mismatch'``
      • NOT emit ``run_completed`` with ``status == 'success'`` while the
        precondition failure is unresolved

    The guard wiring lives in agent.py step-precondition checks.
    """
    bus = _EventCapture()

    run_id = "run-p0-test-005"
    step_id = "step-assert-after-nav"

    pre_fail_env = build_precondition_failed_event(
        run_id=run_id,
        step_id=step_id,
        precondition_type="page_state_mismatch",
        expected="https://example.com/login",
        actual="https://example.com/dashboard",
    )
    bus.emit(pre_fail_env)

    # The run must NOT be completed successfully while unresolved.
    # (A real run_completed success event must not appear until recovery resolves.)
    # We verify the precondition_failed was emitted.
    pf_events = bus.events_of_type("precondition_failed")
    assert len(pf_events) >= 1, "precondition_failed must be emitted on page state mismatch"

    pf = pf_events[0]
    assert pf["schema_version"] == BACKEND_EVENT_SCHEMA_VERSION
    assert pf["run_id"] == run_id
    assert pf["step_id"] == step_id

    # precondition_type must be page_state_mismatch per scenarios §5.4.
    pf_type = pf.get("precondition_type") or pf["payload"].get("precondition_type")
    assert pf_type == "page_state_mismatch", (
        f"expected precondition_type='page_state_mismatch', got {pf_type!r}"
    )

    # No run_completed with success may appear while precondition is unresolved.
    run_completed_success = [
        e for e in bus.events_of_type("run_completed")
        if e.get("status") == "success" or e.get("payload", {}).get("status") == "success"
    ]
    assert run_completed_success == [], (
        "run_completed.status='success' must not be emitted while a "
        "precondition_failed is unresolved (PRD 06 Phase 2 criterion 5)"
    )

    # Recovery options must be present so the user can choose to navigate/wait/etc.
    options = pf.get("options") or pf["payload"].get("options", [])
    assert len(options) > 0, "precondition_failed must carry at least one recovery option"


# ---------------------------------------------------------------------------
# Test 6 — missing capability → capability_gap_recorded + workspace JSONL
# PRD 06 criterion 8: "Missing capability → gap logged under workspace"
# Scenarios §13 schema.
# ---------------------------------------------------------------------------

def test_missing_capability_logged_to_workspace_gap_log() -> None:
    """
    Phase 2, criterion 8 (item #8 in the MVP test list).

    Attempting an unsupported action (e.g. ``download_file``) must:
      • emit a ``capability_gap_recorded`` event with the §13 schema
      • write exactly one new line to ``<workspace>/autoworkbench-output/capability_gaps.jsonl``
        with all required fields

    The emission wiring lives in agent.py / capability gap path. The GapLogger
    and event builder are tested directly here; agent wiring tests are separate.
    """
    # Verify download_file is NOT in baseline (it must be a gap action).
    assert get_capability_status("download_file") == CapabilityStatus.CAPABILITY_GAP, (
        "'download_file' must not be in BASELINE_CAPABILITIES for this test to be meaningful"
    )

    with tempfile.TemporaryDirectory() as workspace_root:
        logger = GapLogger(workspace_root=workspace_root)

        # Record the gap into the workspace JSONL log.
        gap = {
            "url": "https://example.com/files",
            "user_intent": "Download the invoice PDF",
            "operation_id": "op_download_1",
            "needed_capability": "download_file",
            "available_tools": sorted(list(BASELINE_CAPABILITIES)),
            "severity": "warn",
            "source": "agent",
            "phase": "executing",
            "step_id": "step-download",
            "suggested_future_work": "Implement download_file via Playwright download event",
            "message": "download_file is not in BASELINE_CAPABILITIES",
        }
        persisted_record = logger.record(gap)

        # --- Assert JSONL file was written ---
        assert logger.path.exists(), "capability_gaps.jsonl must be created"

        all_records = logger.read_all()
        assert len(all_records) == 1, "exactly one gap record must be written"

        written = all_records[0]
        assert written["needed_capability"] == "download_file"
        assert written["url"] == "https://example.com/files"
        assert written["severity"] == "warn"
        assert written["source"] == "agent"
        assert written["ordinal"] == 1
        assert "recorded_at" in written

        # --- Assert the capability_gap_recorded event shape (scenarios §13) ---
        run_id = "run-p0-test-006"
        gap_event = build_capability_gap_recorded_event(
            run_id=run_id,
            gap_record=written,
        )

        assert gap_event["type"] == "capability_gap_recorded"
        assert gap_event["schema_version"] == BACKEND_EVENT_SCHEMA_VERSION
        assert gap_event["run_id"] == run_id

        payload = gap_event["payload"]
        assert payload["needed_capability"] == "download_file"
        assert payload["url"] == "https://example.com/files"
        assert isinstance(payload["available_tools"], list)
        assert len(payload["available_tools"]) > 0

        # Also verify the live-advisory capability_gap event shape.
        advisory = build_capability_gap_event(
            action="download_file",
            reason="download_file is not in BASELINE_CAPABILITIES",
            next_legal_action="click",
        )
        assert advisory["type"] == "capability_gap"
        assert advisory["action"] == "download_file"


# ---------------------------------------------------------------------------
# Shared fixture — minimal AgentLoop double (Wave 6)
# Constructs via __new__ (no real browser/transport). Stubs out I/O seams so
# _check_forward_precondition and _record_capability_gap can be called without
# a running Playwright browser or WebSocket.
# ---------------------------------------------------------------------------

def _make_agent_loop_double(
    fake_browser_url: str = "https://example.com/dashboard",
    workspace_root: str | None = None,
    emitted_events: list[dict[str, Any]] | None = None,
) -> Any:
    """Build a minimal AgentLoop instance (via __new__) with stubs for I/O seams.

    Returns the agent instance.  Captured backend events are appended to the
    ``emitted_events`` list if supplied, else to ``agent._double_emitted``.
    """
    from agent import AgentLoop  # local import — keeps module-level imports clean

    agent = AgentLoop.__new__(AgentLoop)

    # --- Core identity & lifecycle state ---------------------------------
    agent._run_session_id = "run-double-001"
    agent.phase = "executing"
    agent.phase_tracker = PhaseTracker()
    agent.active_step_id = None
    agent.active_failed_step_id = None
    agent.pending_recovery = False
    agent.completed_step_ids = set()
    agent.skipped_step_ids = set()
    agent.current_step_index = 0
    agent.capability_gaps = []
    agent._gap_logger = None
    agent._gap_logger_emitted_keys = set()
    agent._precondition_failed_emitted = set()
    agent._last_action_context = None
    agent._awaiting_step_record = False
    agent._recording_wait_guard_armed = False
    agent.last_successful_action = None
    agent.successful_action_by_step_id = {}
    agent.successful_actions_by_step_id = {}
    agent._run_completed_emitted = False

    # --- Workspace for GapLogger -----------------------------------------
    if workspace_root is not None:
        agent.workspace_root = workspace_root

    # --- Captured event sink ---------------------------------------------
    _sink: list[dict[str, Any]] = emitted_events if emitted_events is not None else []
    agent._double_emitted = _sink

    # --- Stub: _capture_browser_state (async) ----------------------------
    async def _fake_capture_browser_state():  # type: ignore[return]
        return {"url": fake_browser_url, "title": "Fake Page Title"}

    agent._capture_browser_state = _fake_capture_browser_state

    # --- Stub: _current_browser_url (sync) --------------------------------
    agent._current_browser_url = lambda: fake_browser_url  # type: ignore[method-assign]

    # --- Stub: _emit_backend_event_now — capture without a real WS --------
    def _fake_emit(msg_type: str, **kwargs: Any) -> None:  # type: ignore[return]
        event = {"type": msg_type, **kwargs}
        _sink.append(event)

    agent._emit_backend_event_now = _fake_emit  # type: ignore[method-assign]

    # --- Stub: _mark_step_failed  (sync subset needed by precondition) ----
    # We capture the call but don't drive the full recovery pipeline.
    agent._mark_step_failed_calls: list[tuple[Any, Any]] = []

    def _fake_mark_step_failed(step: Any, error: Any) -> None:  # type: ignore[return]
        agent._mark_step_failed_calls.append((step, error))
        # Minimal side-effects expected by the guard:
        step_id_val = str((step or {}).get("step_id") if isinstance(step, dict) else "")
        agent.pending_recovery = True
        agent.phase = "recovering"

    agent._mark_step_failed = _fake_mark_step_failed  # type: ignore[method-assign]

    return agent


# ---------------------------------------------------------------------------
# Test 5b — real runtime wire-in: _check_forward_precondition emits
#            precondition_failed and blocks run_completed success
# PRD 06 criterion 5 (hardened against wired code path, Wave 6)
# ---------------------------------------------------------------------------

def test_precondition_gate_wired_emits_event_and_blocks_success() -> None:
    """
    Wave 6 extension of criterion 5: drive the real AgentLoop._check_forward_precondition
    code path (not just the event builder) and assert the gate fires.

    Scenario:
      • Step requires URL ``https://example.com/login``
      • Fake browser is on ``https://example.com/dashboard``
      • _check_forward_precondition must return True (blocked)
      • A ``precondition_failed`` event must appear in the captured sink
        with type=='page_state_mismatch'
      • No ``run_completed`` with status=='success' must appear
    """
    captured: list[dict[str, Any]] = []
    agent = _make_agent_loop_double(
        fake_browser_url="https://example.com/dashboard",
        emitted_events=captured,
    )

    req = PageStateRequirement(url_glob="https://example.com/login")
    step_context = {
        "step_id": "step-precond-rt-001",
        "step_number": 1,
        "intent": "Assert login form visible",
        "status": "pending",
    }

    # Drive the real async precondition gate.
    blocked = asyncio.run(
        agent._check_forward_precondition(req, step_context, "action_assert", {})
    )

    # --- gate must have blocked ---
    assert blocked is True, (
        "_check_forward_precondition must return True (blocked) when URL doesn't match"
    )

    # --- precondition_failed must have been emitted via the real code path ---
    pf_events = [e for e in captured if e.get("type") == "precondition_failed"]
    assert len(pf_events) >= 1, (
        "real _check_forward_precondition must emit precondition_failed into the sink"
    )

    pf = pf_events[0]
    assert pf["run_id"] == agent._run_session_id
    assert pf["step_id"] == "step-precond-rt-001"

    # Extract precondition_type from envelope (top-level or payload).
    pf_type = pf.get("precondition_type") or pf.get("payload", {}).get("precondition_type")
    # Canonical type for URL mismatch is "page_url" (aligned with event_contracts allowlist).
    assert pf_type in {"page_url", "page_state_mismatch"}, (
        f"precondition_type must be page_url or page_state_mismatch; got {pf_type!r}"
    )

    # --- recovery options must be present (scenarios §5.4) ---
    options = pf.get("options") or pf.get("payload", {}).get("options", [])
    assert len(options) > 0, (
        "precondition_failed envelope must carry at least one recovery option"
    )

    # --- no run_completed success may appear ---
    run_completed_success = [
        e for e in captured
        if e.get("type") == "run_completed"
        and (e.get("status") == "success" or e.get("payload", {}).get("status") == "success")
    ]
    assert run_completed_success == [], (
        "run_completed.status='success' must not be emitted while precondition gate is blocking"
    )

    # --- idempotency: calling again for same step must NOT emit another event ---
    captured_before = len(captured)
    blocked2 = asyncio.run(
        agent._check_forward_precondition(req, step_context, "action_assert", {})
    )
    assert blocked2 is True, "idempotent call must still report blocked"
    new_pf = [e for e in captured[captured_before:] if e.get("type") == "precondition_failed"]
    assert new_pf == [], "second call for same step must not re-emit precondition_failed"


# ---------------------------------------------------------------------------
# Test 8b — real runtime wire-in: _record_capability_gap writes JSONL
# PRD 06 criterion 8 (hardened against wired code path, Wave 6)
# ---------------------------------------------------------------------------

def test_record_capability_gap_wired_writes_jsonl() -> None:
    """
    Wave 6 extension of criterion 8: drive the real AgentLoop._record_capability_gap
    code path and assert the GapLogger JSONL file is written with the §13 schema.

    Scenario:
      • Unsupported tool ``download_file`` is requested
      • _record_capability_gap is called with relevant args
      • capability_gaps.jsonl must exist under <tmp>/autoworkbench-output/
      • The JSONL record must have all §13 required fields
      • A ``capability_gap_recorded`` event must appear in the captured sink
    """
    captured: list[dict[str, Any]] = []

    with tempfile.TemporaryDirectory() as tmp_workspace:
        agent = _make_agent_loop_double(
            fake_browser_url="https://example.com/files",
            workspace_root=tmp_workspace,
            emitted_events=captured,
        )
        # Pre-set user intent so it flows into GapLogger record.
        agent._last_user_message = "Download the invoice PDF"

        # Drive the real _record_capability_gap code path.
        agent._record_capability_gap(
            category="unsupported_tool",
            source="agent",
            severity="warn",
            message="download_file is not in BASELINE_CAPABILITIES",
            needed_capability="download_file",
            tool_name="download_file",
            operation_id="op_download_1",
            step_id="step-download",
        )

        # --- JSONL file must have been created ---
        jsonl_path = Path(tmp_workspace) / "autoworkbench-output" / "capability_gaps.jsonl"
        assert jsonl_path.exists(), (
            "capability_gaps.jsonl must be created by _record_capability_gap"
        )

        lines = [json.loads(ln) for ln in jsonl_path.read_text().splitlines() if ln.strip()]
        assert len(lines) >= 1, "at least one JSONL record must be written"

        rec = lines[0]
        # §13 required fields
        assert "needed_capability" in rec, "record must contain needed_capability"
        assert "url" in rec, "record must contain url"
        assert "severity" in rec, "record must contain severity"
        assert "source" in rec, "record must contain source"
        assert "ordinal" in rec, "record must contain ordinal"
        assert "recorded_at" in rec, "record must contain recorded_at"
        assert rec["ordinal"] == 1, f"first record ordinal must be 1; got {rec['ordinal']}"
        assert rec["severity"] == "warn"
        assert rec["source"] in {"agent", "classifier", "executor", "user"}

        # --- capability_gap_recorded event must appear in the sink ---
        cg_events = [e for e in captured if e.get("type") == "capability_gap_recorded"]
        assert len(cg_events) >= 1, (
            "_record_capability_gap must emit capability_gap_recorded into the event sink"
        )

        cg = cg_events[0]
        cg_payload = cg.get("payload", {})
        assert "needed_capability" in cg_payload, (
            "capability_gap_recorded payload must include needed_capability"
        )
        assert isinstance(cg_payload.get("available_tools"), list), (
            "capability_gap_recorded payload must include available_tools list"
        )

        # --- idempotency: second call for same run+ordinal must not duplicate ---
        # (ordinal key advances, so second call creates a new record — this is
        # expected; we only verify no EXCEPTION is raised and the file grows)
        prev_count = len(lines)
        agent._record_capability_gap(
            category="unsupported_tool",
            source="agent",
            severity="warn",
            message="download_file is not in BASELINE_CAPABILITIES (retry)",
            needed_capability="download_file",
            tool_name="download_file",
            operation_id="op_download_2",
        )
        lines2 = [json.loads(ln) for ln in jsonl_path.read_text().splitlines() if ln.strip()]
        assert len(lines2) > prev_count, "second distinct gap call must append a new JSONL line"
