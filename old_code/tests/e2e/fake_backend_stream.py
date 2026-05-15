"""
tests/e2e/fake_backend_stream.py

Sprint 7 Cluster 10 — S7-1002: Deterministic fake backend event stream
for E2E flow tests. No paid LLM, no live websites.

Each helper returns an event dict shaped like the real backend payload.
These are intentionally minimal — enough for the reducer and components
to exercise their flows without a live runtime.
"""
from __future__ import annotations

from typing import Any


def session_state(run_id: str = "run-1", phase: str = "idle") -> dict[str, Any]:
    return {
        "type": "session_state",
        "payload": {"run_id": run_id, "phase": phase},
    }


def run_started(run_id: str = "run-1") -> dict[str, Any]:
    return {
        "type": "run_started",
        "payload": {"run_id": run_id, "timestamp": "2026-05-14T00:00:00Z"},
    }


def clarification_needed(
    run_id: str = "run-1", question: str = "Which step?", options=None
) -> dict[str, Any]:
    return {
        "type": "clarification_needed",
        "payload": {
            "run_id": run_id,
            "clarification": {
                "question_id": "q-1",
                "question": question,
                "options": options or [],
            },
        },
    }


def recommendation_ready(
    run_id: str = "run-1", recommendations=None
) -> dict[str, Any]:
    return {
        "type": "recommendation_ready",
        "payload": {
            "run_id": run_id,
            "recommendations": recommendations or [{"id": "r-1", "label": "Default"}],
        },
    }


def plan_ready(
    run_id: str = "run-1", plan_id: str = "plan-1", steps=None
) -> dict[str, Any]:
    return {
        "type": "plan_ready",
        "payload": {
            "run_id": run_id,
            "plan": {
                "plan_id": plan_id,
                "version": 1,
                "steps": steps or [{"step_id": "s-1", "description": "Click login"}],
            },
        },
    }


def permission_required(
    run_id: str = "run-1", operation: str = "open_external"
) -> dict[str, Any]:
    return {
        "type": "permission_required",
        "payload": {
            "run_id": run_id,
            "operation": operation,
            "risk_level": "medium",
            "reason": "external navigation",
        },
    }


def locator_ambiguous(
    run_id: str = "run-1", step_id: str = "s-1", candidates=None
) -> dict[str, Any]:
    return {
        "type": "locator_ambiguous",
        "payload": {
            "run_id": run_id,
            "step_id": step_id,
            "candidates": candidates
            or [
                {"id": "c-1", "locator": "#login", "validated": False},
                {"id": "c-2", "locator": "[data-testid=login]", "validated": False},
            ],
        },
    }


def recovery_needed(
    run_id: str = "run-1", step_id: str = "s-1", reason: str = "element not found"
) -> dict[str, Any]:
    return {
        "type": "recovery_needed",
        "payload": {
            "run_id": run_id,
            "step_id": step_id,
            "failure_reason": reason,
            "options": [
                {"id": "retry", "label": "Retry"},
                {"id": "skip", "label": "Skip"},
            ],
        },
    }


def recovery_resolved(run_id: str = "run-1", step_id: str = "s-1") -> dict[str, Any]:
    return {
        "type": "recovery_resolved",
        "payload": {"run_id": run_id, "step_id": step_id},
    }


def step_executing(run_id: str = "run-1", step_id: str = "s-1") -> dict[str, Any]:
    return {
        "type": "step_executing",
        "payload": {"run_id": run_id, "step_id": step_id},
    }


def step_recorded(
    run_id: str = "run-1", step_id: str = "s-1", state: str = "recorded"
) -> dict[str, Any]:
    return {
        "type": "step_recorded",
        "payload": {"run_id": run_id, "step_id": step_id, "state": state},
    }


def code_update(run_id: str = "run-1", code: str = "// generated") -> dict[str, Any]:
    return {
        "type": "code_update",
        "payload": {"run_id": run_id, "code": code},
    }


def replay_result(
    run_id: str = "run-1", step_id: str = "s-1", outcome: str = "success"
) -> dict[str, Any]:
    return {
        "type": "replay_result",
        "payload": {"run_id": run_id, "step_id": step_id, "outcome": outcome},
    }


def run_completed(run_id: str = "run-1") -> dict[str, Any]:
    return {
        "type": "run_completed",
        "payload": {"run_id": run_id, "summary": "All steps passed"},
    }


def runtime_rejected(run_id: str = "run-1", reason: str = "schema") -> dict[str, Any]:
    return {
        "type": "runtime_rejected",
        "payload": {"run_id": run_id, "rejection_reason": reason},
    }
