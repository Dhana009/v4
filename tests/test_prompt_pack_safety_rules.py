from __future__ import annotations

import pytest

from runtime.prompt_pack_builder import (
    NON_NEGOTIABLE_RUNTIME_RULES,
    REGISTERED_PROMPT_PACK_PURPOSES,
    build_prompt_pack,
)


FORBIDDEN_PHRASES = (
    "mark the step completed",
    "record the step",
    "execute before confirmation",
    "frontend should update lifecycle",
)


def test_every_registered_prompt_pack_includes_all_safety_rules() -> None:
    for purpose in REGISTERED_PROMPT_PACK_PURPOSES:
        pack = build_prompt_pack(purpose)
        for rule in NON_NEGOTIABLE_RUNTIME_RULES:
            assert rule in pack.stable_prefix


def test_step_plan_normalizer_pack_has_all_safety_rules_and_backend_truth_guard() -> None:
    pack = build_prompt_pack("step_plan_normalizer")
    assert pack.required_safety_rules == NON_NEGOTIABLE_RUNTIME_RULES
    assert "Backend Step Runner owns lifecycle truth." in pack.stable_prefix
    assert "backend-valid plan proposal" in pack.stable_prefix
    assert "Do not change the active plan structure silently" in pack.stable_prefix


def test_step_plan_normalizer_pack_does_not_use_forbidden_finality_phrases() -> None:
    pack = build_prompt_pack("step_plan_normalizer")
    stable_prefix = pack.stable_prefix.lower()
    for phrase in FORBIDDEN_PHRASES:
        assert phrase not in stable_prefix


def test_safety_rules_survive_rendering_with_dynamic_context() -> None:
    pack = build_prompt_pack("step_plan_normalizer")
    rendered = pack.render_prompt(
        {
            "user_intent": "click the button",
            "selected_context": "primary CTA",
            "page_summary": "landing page",
            "queued_steps": "step-1",
            "validated_locators": "get_by_text('Get started')",
            "skills_loaded": "llm_runtime_controller, prompt_persona_skill_loading",
            "skill_levels": "core_compact, core_compact",
            "output_schema_reminder": "return a plan proposal compatible with backend validation.",
        }
    )
    for rule in NON_NEGOTIABLE_RUNTIME_RULES:
        assert rule in rendered


def test_prompt_pack_builder_raises_controlled_error_for_unsupported_purpose() -> None:
    with pytest.raises(ValueError, match="Unsupported prompt pack purpose"):
        build_prompt_pack("recovery_diagnoser")
