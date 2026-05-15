"""
tests/test_frontend_llm_cards.py

Sprint 7 Cluster 6 — S7-0601..S7-0610: Live LLM tab card components.
TDD: written before implementation; tests start RED.
"""
from __future__ import annotations

import os

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
LLM_DIR = os.path.join(REPO_ROOT, "frontend", "src", "components", "llm")


def _read(name: str) -> str:
    path = os.path.join(LLM_DIR, name)
    if not os.path.exists(path):
        return ""
    return open(path, encoding="utf-8").read()


# ---------------------------------------------------------------------------
# S7-0601 — Live chat and conversation rendering (ConversationView)
# ---------------------------------------------------------------------------

def test_conversation_view_exists():
    assert os.path.exists(os.path.join(LLM_DIR, "ConversationView.jsx"))


def test_conversation_view_not_stub():
    content = _read("ConversationView.jsx")
    assert "messages" in content, "ConversationView must render messages prop"
    assert "data-testid" in content, "ConversationView must expose testids"


def test_conversation_view_empty_state():
    content = _read("ConversationView.jsx")
    assert "empty" in content.lower() or "No messages" in content


def test_conversation_view_no_demo_fallback():
    content = _read("ConversationView.jsx")
    assert "DEMO_" not in content
    assert "MOCK_" not in content
    assert "FAKE_" not in content


# ---------------------------------------------------------------------------
# S7-0602 — Clarification card
# ---------------------------------------------------------------------------

def test_clarification_card_renders_question():
    content = _read("ClarificationCard.jsx")
    assert "question" in content, "ClarificationCard must read question from props"
    assert "options" in content, "ClarificationCard must render options"


def test_clarification_card_dispatches_option_selected():
    content = _read("ClarificationCard.jsx")
    assert "option_selected" in content or "onAnswer" in content


def test_clarification_card_empty_when_no_payload():
    content = _read("ClarificationCard.jsx")
    assert "return null" in content or "no clarification" in content.lower() \
        or "!clarification" in content or "!question" in content


def test_clarification_card_no_demo():
    content = _read("ClarificationCard.jsx")
    assert "DEMO_" not in content and "MOCK_" not in content


# ---------------------------------------------------------------------------
# S7-0603 — Recommendation review card
# ---------------------------------------------------------------------------

def test_recommendation_card_renders_options():
    content = _read("RecommendationCard.jsx")
    assert "recommendations" in content
    assert "data-testid" in content


def test_recommendation_card_accept_requires_selection():
    content = _read("RecommendationCard.jsx")
    # Accept button disabled when no selection
    assert "disabled" in content
    assert "selected" in content.lower()


def test_recommendation_card_dispatches_typed_command():
    content = _read("RecommendationCard.jsx")
    assert "accept_recommendations" in content or "onAccept" in content


# ---------------------------------------------------------------------------
# S7-0604 — Plan-ready review card
# ---------------------------------------------------------------------------

def test_plan_card_renders_plan():
    content = _read("PlanCard.jsx")
    assert "plan" in content
    assert "steps" in content.lower() or "step" in content.lower()


def test_plan_card_confirm_requires_plan_id():
    content = _read("PlanCard.jsx")
    assert "plan_id" in content


def test_plan_card_dispatches_confirm_plan():
    content = _read("PlanCard.jsx")
    assert "confirm_plan" in content or "onConfirm" in content


def test_plan_card_empty_when_no_plan():
    content = _read("PlanCard.jsx")
    assert "return null" in content or "!plan" in content


# ---------------------------------------------------------------------------
# S7-0605 — Plan correction discussion flow
# ---------------------------------------------------------------------------

def test_correction_card_renders_text_input():
    content = _read("CorrectionCard.jsx")
    assert "correction" in content.lower()
    assert "textarea" in content.lower() or "input" in content.lower()


def test_correction_card_does_not_mutate_plan_locally():
    content = _read("CorrectionCard.jsx")
    # Must NOT call setPlan or modify plan locally
    assert "setPlan(" not in content


def test_correction_card_dispatches_correction_command():
    content = _read("CorrectionCard.jsx")
    assert '"correction"' in content or "onSendCorrection" in content


# ---------------------------------------------------------------------------
# S7-0606 — Plan-diff apply/reject card
# ---------------------------------------------------------------------------

def test_plan_diff_card_exists():
    assert os.path.exists(os.path.join(LLM_DIR, "PlanDiffCard.jsx"))


def test_plan_diff_card_renders_operations():
    content = _read("PlanDiffCard.jsx")
    assert "diff" in content.lower()
    assert "operations" in content.lower() or "ops" in content.lower()


def test_plan_diff_card_apply_reject_commands():
    content = _read("PlanDiffCard.jsx")
    assert "apply_plan_diff" in content or "onApply" in content
    assert "reject_plan_diff" in content or "onReject" in content


def test_plan_diff_card_no_local_plan_mutation():
    content = _read("PlanDiffCard.jsx")
    assert "setPlan(" not in content


# ---------------------------------------------------------------------------
# S7-0607 — Permission card
# ---------------------------------------------------------------------------

def test_permission_card_renders_operation():
    content = _read("PermissionCard.jsx")
    assert "permission" in content.lower()
    assert "operation" in content.lower() or "risk" in content.lower()


def test_permission_card_allow_deny_commands():
    content = _read("PermissionCard.jsx")
    assert "permission_decision" in content or "onDecision" in content
    assert "allow" in content.lower()
    assert "deny" in content.lower()


def test_permission_card_no_local_approval():
    content = _read("PermissionCard.jsx")
    # Must NOT set approved state locally
    assert "setApproved" not in content
    assert "setPermissionGranted" not in content


def test_permission_card_empty_when_no_pending():
    content = _read("PermissionCard.jsx")
    assert "return null" in content or "!permission" in content


# ---------------------------------------------------------------------------
# S7-0608 — Locator ambiguity card
# ---------------------------------------------------------------------------

def test_locator_card_renders_candidates():
    content = _read("LocatorAmbiguityCard.jsx")
    assert "candidate" in content.lower()


def test_locator_card_choose_command():
    content = _read("LocatorAmbiguityCard.jsx")
    assert "choose_locator_candidate" in content or "onChoose" in content


def test_locator_card_no_local_activation():
    content = _read("LocatorAmbiguityCard.jsx")
    # Selection must not "activate" locator locally
    assert "setActiveLocator" not in content


# ---------------------------------------------------------------------------
# S7-0609 — Recovery-needed card
# ---------------------------------------------------------------------------

def test_recovery_card_renders_options():
    content = _read("RecoveryCard.jsx")
    assert "recovery" in content.lower()
    assert "options" in content.lower() or "option" in content.lower()


def test_recovery_card_retry_skip_stop_commands():
    content = _read("RecoveryCard.jsx")
    has_actions = (
        "retry_recovery" in content
        or "skip_step" in content
        or "stop_run" in content
        or "onRetry" in content
    )
    assert has_actions, "RecoveryCard must dispatch retry/skip/stop commands"


def test_recovery_card_no_success_inference():
    content = _read("RecoveryCard.jsx")
    # Must not mark resolved locally
    assert "setRecoveryResolved" not in content
    assert "setResolved" not in content


# ---------------------------------------------------------------------------
# S7-0610 — Completed/failed run summary card
# ---------------------------------------------------------------------------

def test_completed_card_renders_summary():
    content = _read("CompletedCard.jsx")
    assert "summary" in content.lower() or "completed" in content.lower() \
        or "completion" in content.lower()


def test_completed_card_handles_failed_state():
    content = _read("CompletedCard.jsx")
    assert "failed" in content.lower() or "rejected" in content.lower() \
        or "error" in content.lower()


def test_completed_card_no_inferred_completion():
    content = _read("CompletedCard.jsx")
    # Must rely on prop, never infer from steps
    assert "pending_steps.length" not in content
    assert "recorded_steps.length" not in content


def test_completed_card_empty_when_not_completed():
    content = _read("CompletedCard.jsx")
    assert "return null" in content or "!completion" in content or "!summary" in content
