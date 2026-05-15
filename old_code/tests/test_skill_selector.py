from __future__ import annotations

from copy import deepcopy

from runtime.llm_runtime_controller import PURPOSE_REGISTRY
from runtime.skill_selector import build_skill_prompt, select_skills_for_purpose


def test_step_plan_normalizer_defaults_to_compact_core_and_persona() -> None:
    policy = PURPOSE_REGISTRY.get_purpose_policy("step_plan_normalizer")

    selection = select_skills_for_purpose("step_plan_normalizer", policy=policy)

    assert selection.preserve_full_prompt is False
    assert selection.loaded_skill_names == [
        "llm_runtime_controller",
        "prompt_persona_skill_loading",
    ]
    assert selection.skill_levels == ["core_compact", "core_compact"]
    assert "Runtime policy boundary." in build_skill_prompt(selection)


def test_locator_purpose_uses_locator_summary_by_default() -> None:
    policy = PURPOSE_REGISTRY.get_purpose_policy("locator_specialist")

    selection = select_skills_for_purpose("locator_specialist", policy=policy)

    assert selection.preserve_full_prompt is False
    assert selection.loaded_skill_names == [
        "llm_runtime_controller",
        "locator_strategy",
    ]
    assert selection.skill_levels == ["core_compact", "skill_summary"]


def test_recovery_purpose_adds_debug_skills_without_mutating_policy() -> None:
    policy = PURPOSE_REGISTRY.get_purpose_policy("recovery_diagnoser")
    before = deepcopy(policy)

    selection = select_skills_for_purpose("recovery_diagnoser", policy=policy)

    assert selection.loaded_skill_names == [
        "llm_runtime_controller",
        "prompt_persona_skill_loading",
        "observability_trace",
        "memory_human_feedback",
    ]
    assert selection.skill_levels == [
        "core_compact",
        "core_compact",
        "debug_skill",
        "debug_skill",
    ]
    assert policy == before


def test_compact_only_purpose_never_preserves_full_prompt_on_schema_retry() -> None:
    policy = PURPOSE_REGISTRY.get_purpose_policy("plan_diff_editor")

    selection = select_skills_for_purpose(
        "plan_diff_editor",
        policy=policy,
        escalation_reason="schema_retry",
    )

    assert selection.preserve_full_prompt is False
    assert selection.loaded_skill_names == [
        "llm_runtime_controller",
        "prompt_persona_skill_loading",
    ]


def test_full_prompt_preserved_only_for_allowed_purpose_with_explicit_reason() -> None:
    policy = PURPOSE_REGISTRY.get_purpose_policy("step_plan_normalizer")

    selection = select_skills_for_purpose(
        "step_plan_normalizer",
        policy=policy,
        escalation_reason="schema_retry",
    )

    assert selection.preserve_full_prompt is True
    assert selection.skill_entries == []


def test_unknown_purpose_falls_back_to_compact_minimal_skill() -> None:
    selection = select_skills_for_purpose("unknown_future_purpose", policy=None)

    assert selection.preserve_full_prompt is False
    assert selection.loaded_skill_names == ["llm_runtime_controller"]
    assert selection.skill_levels == ["core_compact"]
