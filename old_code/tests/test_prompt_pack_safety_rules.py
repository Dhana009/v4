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


def test_plan_diff_editor_pack_has_correction_rules() -> None:
    pack = build_prompt_pack("plan_diff_editor")
    assert "do not silently drop operations" in pack.stable_prefix.lower()
    assert "do not silently reorder operations" in pack.stable_prefix.lower()
    assert "do not split or merge parent steps unless the user explicitly asks" in pack.stable_prefix.lower()
    assert "backend validates and applies the diff" in pack.stable_prefix.lower()


def test_recovery_diagnoser_pack_has_recovery_rules() -> None:
    pack = build_prompt_pack("recovery_diagnoser")
    assert "diagnose the failed step only" in pack.stable_prefix.lower()
    assert "stay anchored to the failed step" in pack.stable_prefix.lower()
    assert "propose retry, ask user, skip, or stop only" in pack.stable_prefix.lower()
    assert "backend validates any retry before execution" in pack.stable_prefix.lower()


def test_registered_prompt_packs_do_not_use_forbidden_finality_phrases() -> None:
    for purpose in REGISTERED_PROMPT_PACK_PURPOSES:
        pack = build_prompt_pack(purpose)
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
        build_prompt_pack("unknown_purpose")
