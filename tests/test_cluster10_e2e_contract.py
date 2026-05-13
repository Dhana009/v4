"""
tests/test_cluster10_e2e_contract.py

Sprint 7 Cluster 10 — S7-1001..S7-1010: Local browser E2E smoke gate.

This file verifies the E2E harness contract: harness has Shadow DOM
helpers, fake-event-stream utility exists, and the 7 required flows are
each modeled by a Python-level flow test feeding fake backend events
through the typed reducer. Actual Playwright runs remain a user gate.
"""
from __future__ import annotations

import os

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
HARNESS = os.path.join(REPO_ROOT, "tests", "e2e", "harness.py")
FAKE_STREAM = os.path.join(REPO_ROOT, "tests", "e2e", "fake_backend_stream.py")
FLOW_TESTS = os.path.join(REPO_ROOT, "tests", "test_cluster10_fake_flows.py")


def _read(path: str) -> str:
    if not os.path.exists(path):
        return ""
    return open(path, encoding="utf-8").read()


# S7-1001 — Harness has Shadow DOM helpers
def test_harness_has_shadow_host_helper():
    c = _read(HARNESS)
    # Either new SHADOW_HOST_ID or aw-shadow-host literal must be referenced
    assert "aw-shadow-host" in c or "SHADOW_HOST_ID" in c, \
        "harness must support docked Shadow DOM host selector"


def test_harness_has_panel_finder():
    c = _read(HARNESS)
    assert "find_autoworkbench_panel" in c


# S7-1002 — Fake backend event stream utility
def test_fake_event_stream_module_exists():
    assert os.path.exists(FAKE_STREAM), \
        "tests/e2e/fake_backend_stream.py must exist for C10"


def test_fake_event_stream_covers_required_events():
    c = _read(FAKE_STREAM)
    required = [
        "session_state",
        "clarification_needed",
        "recommendation_ready",
        "plan_ready",
        "permission_required",
        "locator_ambiguous",
        "recovery_needed",
        "step_recorded",
        "code_update",
        "replay_result",
        "run_completed",
        "runtime_rejected",
    ]
    for ev in required:
        assert ev in c, f"fake_backend_stream must include {ev}"


# S7-1003..S7-1010 — Flow tests exist
def test_flow_tests_file_exists():
    assert os.path.exists(FLOW_TESTS)


def test_flow_intent_to_plan_ready():
    c = _read(FLOW_TESTS)
    assert "test_flow_intent_to_plan_ready" in c


def test_flow_plan_correction_to_corrected_plan_ready():
    c = _read(FLOW_TESTS)
    assert "test_flow_plan_correction_to_corrected_plan_ready" in c


def test_flow_confirm_to_completed():
    c = _read(FLOW_TESTS)
    assert "test_flow_confirm_to_completed" in c


def test_flow_locator_ambiguity():
    c = _read(FLOW_TESTS)
    assert "test_flow_locator_ambiguity" in c


def test_flow_recovery():
    c = _read(FLOW_TESTS)
    assert "test_flow_recovery" in c


def test_flow_steps_tab_run():
    c = _read(FLOW_TESTS)
    assert "test_flow_steps_tab_run" in c


def test_flow_save_load_replay():
    c = _read(FLOW_TESTS)
    assert "test_flow_save_load_replay" in c
