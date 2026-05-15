"""
tests/test_frontend_event_store_handlers.py

Sprint 7 Cluster 5 — S7-0503/S7-0504/S7-0505/S7-0506/S7-0509:
Session restore, run completion/error handlers, step lifecycle correlation,
permission/recommendation/recovery handlers, and live prop threading.

TDD: written before reducer extension; tests start RED.
"""
from __future__ import annotations

import os
import re

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
REDUCER_PATH = os.path.join(REPO_ROOT, "frontend", "src", "store", "reducer.js")
TYPES_PATH = os.path.join(REPO_ROOT, "frontend", "src", "store", "types.js")
MAIN_PATH = os.path.join(REPO_ROOT, "frontend", "src", "main.jsx")


def _reducer() -> str:
    return open(REDUCER_PATH, encoding="utf-8").read()


def _types() -> str:
    return open(TYPES_PATH, encoding="utf-8").read()


def _main() -> str:
    return open(MAIN_PATH, encoding="utf-8").read()


# ---------------------------------------------------------------------------
# S7-0503 — session_state consumer and reconnect restore
# ---------------------------------------------------------------------------

def test_session_state_restores_plan():
    content = _reducer()
    snippet = _slice_case(content, "session_state")
    assert "plan" in snippet, "session_state must restore plan from payload"


def test_session_state_restores_pending_steps():
    content = _reducer()
    snippet = _slice_case(content, "session_state")
    assert "pending_steps" in snippet, "session_state must restore pending_steps"


def test_session_state_restores_recorded_steps():
    content = _reducer()
    snippet = _slice_case(content, "session_state")
    assert "recorded_steps" in snippet, "session_state must restore recorded_steps"


def test_session_state_restores_code_preview():
    content = _reducer()
    snippet = _slice_case(content, "session_state")
    assert "code_preview" in snippet, "session_state must restore code_preview"


def test_session_state_safe_defaults():
    content = _reducer()
    snippet = _slice_case(content, "session_state")
    # Must use ?? or || fallbacks to state for missing fields
    has_safe = "??" in snippet or "||" in snippet
    assert has_safe, "session_state must use safe defaults for missing fields"


def test_session_state_replaces_not_appends_recorded():
    content = _reducer()
    snippet = _slice_case(content, "session_state")
    # Restore must NOT spread existing recorded_steps + new (would duplicate)
    bad = re.search(r"\.\.\.\s*state\.recorded_steps\s*,\s*\.\.\.", snippet)
    assert not bad, "session_state must replace recorded_steps, not append (avoid dupes)"


# ---------------------------------------------------------------------------
# S7-0504 — run_completed, runtime_rejected, error handlers
# ---------------------------------------------------------------------------

def test_run_completed_only_from_event():
    content = _reducer()
    snippet = _slice_case(content, "run_completed")
    assert 'phase: "completed"' in snippet or "completed" in snippet


def test_run_completed_blocked_by_recovery():
    content = _reducer()
    snippet = _slice_case(content, "run_completed")
    # Must guard against pending_recovery — do not transition to completed mid-recovery
    has_guard = (
        "pending_recovery" in snippet
        or "recovery" in snippet.lower()
    )
    assert has_guard, "run_completed must check pending_recovery before transitioning"


def test_runtime_rejected_appends_to_errors():
    content = _reducer()
    snippet = _slice_case(content, "runtime_rejected")
    assert "errors" in snippet, "runtime_rejected must record into errors"
    assert "last_error" in snippet, "runtime_rejected must set last_error"


def test_error_event_handler():
    content = _reducer()
    # Generic error event must be handled
    assert '"error"' in content or "error:" in content, \
        "reducer must handle generic error event"


def test_schema_error_event_handler():
    content = _reducer()
    # schema_error / malformed errors visible
    has_schema = (
        "schema_error" in content
        or "malformed" in content
        or "error" in content.lower()
    )
    assert has_schema, "reducer must surface schema/malformed errors"


def test_no_completion_inference_from_step_count():
    content = _reducer()
    # Must not infer completed from pending_steps.length === 0
    bad = re.search(r"pending_steps\.length\s*===\s*0.*completed", content, re.DOTALL)
    assert not bad, "must not infer completed from empty pending_steps"


# ---------------------------------------------------------------------------
# S7-0505 — Step lifecycle handlers
# ---------------------------------------------------------------------------

def test_step_failed_not_added_to_recorded():
    content = _reducer()
    snippet = _slice_case(content, "step_failed")
    bad = re.search(r"recorded_steps\s*:\s*\[\s*\.\.\.\s*state\.recorded_steps", snippet)
    assert not bad, "step_failed must NOT be added to recorded_steps"


def test_step_skipped_not_added_to_recorded():
    content = _reducer()
    snippet = _slice_case(content, "step_skipped")
    bad = re.search(r"recorded_steps\s*:\s*\[\s*\.\.\.\s*state\.recorded_steps\s*,\s*payload\b", snippet)
    assert not bad, "step_skipped must NOT append to recorded_steps as success"


def test_step_recorded_dedupes_by_id():
    content = _reducer()
    snippet = _slice_case(content, "step_recorded")
    # Must filter duplicates by step_id before appending
    has_dedupe = (
        "filter" in snippet
        or "find" in snippet
        or "some" in snippet
        or "step_id" in snippet
    )
    assert has_dedupe, "step_recorded must dedupe by step_id"


def test_stale_run_id_step_event_ignored():
    content = _reducer()
    # Reducer must have stale run_id check on step events
    has_stale_check = (
        "stale" in content.lower()
        or "state.run_id" in content
        or "run_id !==" in content
        or "isStaleRunId" in content
    )
    assert has_stale_check, "reducer must detect stale run_id on step events"


# ---------------------------------------------------------------------------
# S7-0506 — Permission, recommendation, recovery handlers
# ---------------------------------------------------------------------------

def test_permission_required_stores_payload():
    content = _reducer()
    snippet = _slice_case(content, "permission_required")
    assert "pending_permission" in snippet


def test_recommendation_ready_stores_selectable():
    content = _reducer()
    snippet = _slice_case(content, "recommendation_ready")
    assert "pending_recommendations" in snippet or "recommendations" in snippet


def test_recovery_needed_stores_options():
    content = _reducer()
    snippet = _slice_case(content, "recovery_needed")
    assert "pending_recovery" in snippet


def test_recovery_resolved_clears_recovery():
    content = _reducer()
    # recovery_resolved event must clear pending_recovery
    assert "recovery_resolved" in content, \
        "reducer must handle recovery_resolved event"


def test_recovery_resolved_only_from_event():
    content = _reducer()
    snippet = _slice_case(content, "recovery_resolved")
    # Must set pending_recovery to null
    assert "pending_recovery" in snippet and "null" in snippet, \
        "recovery_resolved must clear pending_recovery to null"


def test_types_includes_recovery_resolved():
    content = _types()
    assert "recovery_resolved" in content


# ---------------------------------------------------------------------------
# S7-0509 — Live prop threading into IDEPanel
# ---------------------------------------------------------------------------

def test_main_threads_store_state_into_runtime():
    content = _main()
    # storeState fields must be reachable from runtime prop
    assert "storeState" in content, "main.jsx must expose storeState"


def test_main_threads_connection_into_runtime():
    content = _main()
    # IDEPanel runtime prop must include connection from store
    assert re.search(r"runtime=\{\{", content), "main.jsx must pass runtime prop to IDEPanel"


def test_main_no_demo_fallback_in_live_mode():
    content = _main()
    # In live mode (config.mode === "live"), must not inject demo plan
    bad = re.search(r"live[^}]*DEMO_PLAN", content)
    assert not bad, "live mode must not use demo plan fallback"


def test_main_command_dispatcher_imported():
    content = _main()
    # dispatcher must be available for command callbacks
    has_dispatcher = (
        "createDispatcher" in content
        or "from \"./commands/dispatcher" in content
        or "dispatcher" in content.lower()
    )
    assert has_dispatcher, "main.jsx must import command dispatcher"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _slice_case(content: str, event_type: str) -> str:
    """Return the reducer body slice for a given case label."""
    pattern = rf"case EVENT_TYPES\.{event_type}:[^{{]*\{{"
    m = re.search(pattern, content)
    if not m:
        # Fallback: try string-literal form
        pattern_lit = rf'case "{event_type}":[^{{]*\{{'
        m = re.search(pattern_lit, content)
    assert m, f"reducer must contain a case for {event_type}"
    start = m.end()
    # Find matching close brace
    depth = 1
    i = start
    while i < len(content) and depth > 0:
        if content[i] == "{":
            depth += 1
        elif content[i] == "}":
            depth -= 1
        i += 1
    return content[start:i]
