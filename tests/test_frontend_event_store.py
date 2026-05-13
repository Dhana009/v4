"""
tests/test_frontend_event_store.py

Sprint 7 Cluster 5 — S7-0501/S7-0502: Typed event model and reducer/store.
TDD: written before implementation; tests start RED.
"""
from __future__ import annotations

import os
import re

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
STORE_DIR = os.path.join(REPO_ROOT, "frontend", "src", "store")
TYPES_PATH = os.path.join(STORE_DIR, "types.js")
REDUCER_PATH = os.path.join(STORE_DIR, "reducer.js")
SELECTORS_PATH = os.path.join(STORE_DIR, "selectors.js")


def _types() -> str:
    return open(TYPES_PATH, encoding="utf-8").read()


def _reducer() -> str:
    return open(REDUCER_PATH, encoding="utf-8").read()


def _selectors() -> str:
    return open(SELECTORS_PATH, encoding="utf-8").read()


# ---------------------------------------------------------------------------
# S7-0501 — types.js: Event type definitions
# ---------------------------------------------------------------------------

def test_types_exports_event_types():
    content = _types()
    assert "EVENT_TYPES" in content, "types.js must export EVENT_TYPES"


def test_types_has_session_state_event():
    content = _types()
    assert "session_state" in content


def test_types_has_run_started_event():
    content = _types()
    assert "run_started" in content


def test_types_has_plan_ready_event():
    content = _types()
    assert "plan_ready" in content


def test_types_has_clarification_needed_event():
    content = _types()
    assert "clarification_needed" in content


def test_types_has_run_completed_event():
    content = _types()
    assert "run_completed" in content


def test_types_has_runtime_rejected_event():
    content = _types()
    assert "runtime_rejected" in content


def test_types_has_step_events():
    content = _types()
    for ev in ["step_validating", "step_executing", "step_failed", "step_skipped", "step_recorded"]:
        assert ev in content, f"types.js must include {ev}"


def test_types_has_permission_required():
    content = _types()
    assert "permission_required" in content


def test_types_has_recommendation_ready():
    content = _types()
    assert "recommendation_ready" in content


def test_types_has_recovery_needed():
    content = _types()
    assert "recovery_needed" in content


def test_types_has_code_update():
    content = _types()
    assert "code_update" in content


def test_types_exports_command_types():
    content = _types()
    assert "COMMAND_TYPES" in content, "types.js must export COMMAND_TYPES"


def test_types_has_confirm_plan_command():
    content = _types()
    assert "confirm_plan" in content


def test_types_has_permission_decision_command():
    content = _types()
    assert "permission_decision" in content


def test_types_has_skip_step_command():
    content = _types()
    assert "skip_step" in content


def test_types_has_stop_run_command():
    content = _types()
    assert "stop_run" in content


# ---------------------------------------------------------------------------
# S7-0502 — reducer.js: Full implementation (not stub)
# ---------------------------------------------------------------------------

def test_reducer_not_stub():
    content = _reducer()
    # S7-0306 stub had only 13 lines; full implementation must be substantially larger
    non_comment_lines = [l for l in content.splitlines() if l.strip() and not l.strip().startswith("//")]
    assert len(non_comment_lines) >= 50, \
        f"reducer.js still looks like a stub ({len(non_comment_lines)} non-comment lines)"


def test_reducer_exports_reducer_function():
    content = _reducer()
    assert "export function reducer" in content or "export const reducer" in content, \
        "reducer.js must export reducer(state, event) function"


def test_reducer_exports_create_initial_state():
    content = _reducer()
    assert "createInitialState" in content


def test_reducer_initial_state_has_required_fields():
    content = _reducer()
    required = [
        "connected", "run_id", "phase", "plan", "pending_steps", "recorded_steps",
        "errors", "interaction_mode",
    ]
    for field in required:
        assert field in content, f"createInitialState must include field: {field}"


def test_reducer_handles_session_state():
    content = _reducer()
    assert "session_state" in content, "reducer must handle session_state event"


def test_reducer_handles_run_started():
    content = _reducer()
    assert "run_started" in content, "reducer must handle run_started event"


def test_reducer_handles_plan_ready():
    content = _reducer()
    assert "plan_ready" in content, "reducer must handle plan_ready event"


def test_reducer_handles_run_completed():
    content = _reducer()
    assert "run_completed" in content, "reducer must handle run_completed event"


def test_reducer_handles_runtime_rejected():
    content = _reducer()
    assert "runtime_rejected" in content, "reducer must handle runtime_rejected event"


def test_reducer_handles_step_events():
    content = _reducer()
    for ev in ["step_validating", "step_executing", "step_failed", "step_skipped", "step_recorded"]:
        assert ev in content, f"reducer must handle {ev}"


def test_reducer_handles_permission_required():
    content = _reducer()
    assert "permission_required" in content


def test_reducer_handles_recommendation_ready():
    content = _reducer()
    assert "recommendation_ready" in content


def test_reducer_handles_recovery_needed():
    content = _reducer()
    assert "recovery_needed" in content


def test_reducer_handles_code_update():
    content = _reducer()
    assert "code_update" in content


def test_reducer_handles_unknown_event_safely():
    content = _reducer()
    # Must have a default case or else/fallback that returns state unchanged
    has_default = (
        "default:" in content
        or "return state" in content
        or "return { ...state }" in content
    )
    assert has_default, "reducer must handle unknown events safely (return state unchanged)"


def test_reducer_no_mutation_pattern():
    content = _reducer()
    # Reducer must not mutate state directly (no state.xxx = yyy without spread)
    # Check: no direct mutations like state.plan = ... outside of return
    bad_pattern = re.search(r"(?<!return\s)state\.\w+\s*=\s*(?!>)", content)
    # This heuristic may not catch everything, but reject obvious patterns
    assert not re.search(r"\bstate\.(run_id|plan|phase|errors)\s*=\s*[^>]", content), \
        "reducer must not directly mutate state fields"


def test_reducer_no_lifecycle_inference():
    content = _reducer()
    # Must not contain patterns that infer completion from step count
    assert "total_steps" not in content or "recorded_steps.length" not in content or \
        "run_completed" in content, "reducer must not infer run completion from step count"
    # More specific: no pattern like pendingSteps.length === 0 => completed
    assert not re.search(r"pending_steps\.length\s*===\s*0.*completed", content, re.DOTALL), \
        "reducer must not infer completion from empty pending_steps"


def test_reducer_no_demo_constants():
    content = _reducer()
    assert "DEMO_" not in content
    assert "MOCK_" not in content
    assert "FAKE_" not in content


def test_reducer_no_backend_imports():
    content = _reducer()
    bad = re.search(r"(from|import)\s+['\"][./]*(?:runtime|agent|server|browser)[/\"']", content)
    assert not bad, f"reducer.js must not import backend modules"


def test_reducer_under_400_lines():
    content = _reducer()
    lines = content.splitlines()
    assert len(lines) <= 400, f"reducer.js has {len(lines)} lines; max 400"


# ---------------------------------------------------------------------------
# S7-0502 — selectors.js: State access helpers
# ---------------------------------------------------------------------------

def test_selectors_not_stub():
    content = _selectors()
    assert "SELECTORS_STUB" not in content or "selectPlan" in content, \
        "selectors.js must have actual selector implementations"


def test_selectors_exports_select_plan():
    content = _selectors()
    assert "selectPlan" in content or "select_plan" in content, \
        "selectors.js must export selectPlan"


def test_selectors_exports_select_interaction_mode():
    content = _selectors()
    assert "selectInteractionMode" in content or "interaction_mode" in content


def test_selectors_exports_select_pending_steps():
    content = _selectors()
    assert "selectPendingSteps" in content or "pending_steps" in content
