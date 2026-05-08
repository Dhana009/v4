from __future__ import annotations

from pathlib import Path

from runtime.llm_policy_gateway import LLMPolicyGateway
from runtime.llm_runtime_controller import PURPOSE_REGISTRY


def test_gateway_returns_no_model_for_deterministic_eligible_input() -> None:
    gateway = LLMPolicyGateway(PURPOSE_REGISTRY)

    decision = gateway.decide(
        phase="planning",
        steps=[{"intent": "click this button"}],
        locator_validated=True,
        locator_count=1,
    )

    assert decision.model_needed is False
    assert decision.purpose == "deterministic_fast_path"
    assert decision.allowed_tools == ()
    assert decision.deterministic_candidate_allowed is True
    assert decision.requires_confirmation is True


def test_gateway_returns_purpose_specific_decision_for_planning() -> None:
    gateway = LLMPolicyGateway(PURPOSE_REGISTRY)

    decision = gateway.decide(
        phase="planning",
        steps=[{"intent": "check this section"}],
        locator_validated=False,
        locator_count=0,
    )

    assert decision.model_needed is True
    assert decision.purpose == "step_plan_normalizer"
    assert decision.context_level == "compact"
    assert decision.schema_id == "step_plan_normalizer.v1"
    assert decision.budget == 2000


def test_gateway_restricts_tools_by_purpose() -> None:
    gateway = LLMPolicyGateway(PURPOSE_REGISTRY)

    planning = gateway.decide(phase="planning")
    correction = gateway.decide(phase="planning", correction_mode={"category": "rewrite"})

    assert planning.allowed_tools == ("send_to_overlay", "ask_user")
    assert correction.purpose == "plan_diff_editor"
    assert correction.allowed_tools == ()


def test_gateway_preserves_confirmation_requirement_in_execution_mode() -> None:
    gateway = LLMPolicyGateway(PURPOSE_REGISTRY)

    decision = gateway.decide(
        phase="executing",
        plan_confirmed=True,
        steps=[{"intent": "click this button"}],
    )

    assert decision.purpose == "execution_driver"
    assert decision.model_needed is True
    assert decision.allowed_tools == ("action_assert", "action_click", "action_fill")
    assert decision.requires_confirmation is True
    assert decision.fallback == "fail_closed"


def test_gateway_keeps_main_orchestrator_fallback_for_unknown_phase() -> None:
    gateway = LLMPolicyGateway(PURPOSE_REGISTRY)

    decision = gateway.decide(phase="mystery")

    assert decision.purpose == "main_orchestrator"
    assert decision.model_needed is True
    assert decision.fallback == "main_orchestrator"


def test_agent_loop_consults_policy_gateway_before_main_llm_call() -> None:
    source = Path("agent.py").read_text(encoding="utf-8")

    assert "LLMPolicyGateway" in source
    assert "self.llm_policy_gateway = LLMPolicyGateway(" in source
    assert "policy_decision = self.llm_policy_gateway.decide(" in source
    assert "effective_purpose = policy_decision.purpose if policy_decision.model_needed else policy_decision.fallback" in source
    assert "purpose=effective_purpose" in source
