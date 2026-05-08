from __future__ import annotations

from runtime.skill_policy import (
    SKILL_LEVEL_MAP,
    COMPACT_ONLY_PURPOSES,
    LOCATOR_SUMMARY_PURPOSES,
    DEBUG_SKILL_PURPOSES,
    get_skill_level,
    should_load_full_skill,
)
from runtime.llm_runtime_controller import PURPOSE_REGISTRY


def test_core_skills_are_core_compact():
    assert get_skill_level("llm_runtime_controller") == "core_compact"
    assert get_skill_level("prompt_persona_skill_loading") == "core_compact"


def test_purpose_skills_are_skill_summary():
    assert get_skill_level("locator_strategy") == "skill_summary"
    assert get_skill_level("backend_step_runner") == "skill_summary"
    assert get_skill_level("codegen") == "skill_summary"
    assert get_skill_level("contract_testing") == "skill_summary"


def test_escalation_skills_are_full_skill():
    assert get_skill_level("capability_framework") == "full_skill"
    assert get_skill_level("replay_repair") == "full_skill"
    assert get_skill_level("real_world_fixtures") == "full_skill"


def test_debug_skills_are_debug_skill():
    assert get_skill_level("observability_trace") == "debug_skill"
    assert get_skill_level("memory_human_feedback") == "debug_skill"


def test_unknown_skill_defaults_to_skill_summary():
    assert get_skill_level("some_unknown_skill") == "skill_summary"
    assert get_skill_level("") == "skill_summary"


def test_full_skill_only_loads_with_escalation():
    assert should_load_full_skill("capability_framework", escalation=False) is False
    assert should_load_full_skill("capability_framework", escalation=True) is True
    assert should_load_full_skill("replay_repair", escalation=False) is False


def test_core_compact_always_loads():
    assert should_load_full_skill("llm_runtime_controller") is True
    assert should_load_full_skill("prompt_persona_skill_loading") is True


def test_plan_diff_editor_is_compact_only_purpose():
    assert "plan_diff_editor" in COMPACT_ONLY_PURPOSES


def test_compact_only_purposes_do_not_include_locator_or_browser_skills():
    for purpose in COMPACT_ONLY_PURPOSES:
        policy = PURPOSE_REGISTRY.get_purpose_policy(purpose)
        skill_policy = policy["skill_policy"]
        purpose_skills = skill_policy.get("purpose_skills", [])
        # compact-only purposes must not include action/browser/locator full skills
        forbidden = {"actions", "assertions", "locator", "backend_step_runner", "codegen"}
        loaded_set = set(purpose_skills)
        overlap = forbidden & loaded_set
        assert not overlap, (
            f"Purpose '{purpose}' loaded forbidden full skills: {overlap}"
        )


def test_locator_purposes_include_locator_skill():
    for purpose in LOCATOR_SUMMARY_PURPOSES:
        policy = PURPOSE_REGISTRY.get_purpose_policy(purpose)
        skill_policy = policy["skill_policy"]
        purpose_skills = skill_policy.get("purpose_skills", [])
        assert "locator_strategy" in purpose_skills, (
            f"Purpose '{purpose}' should include locator_strategy"
        )


def test_recovery_purposes_in_debug_skill_set():
    assert "recovery_diagnoser" in DEBUG_SKILL_PURPOSES
    assert "replay_repair_specialist" in DEBUG_SKILL_PURPOSES


def test_all_purpose_registry_purposes_have_skill_policy():
    for purpose in PURPOSE_REGISTRY.list_purposes():
        policy = PURPOSE_REGISTRY.get_purpose_policy(purpose)
        assert "skill_policy" in policy
        skill_policy = policy["skill_policy"]
        assert "purpose_skills" in skill_policy
        assert "skill_budget" in skill_policy


def test_skill_level_map_has_no_empty_keys():
    for key in SKILL_LEVEL_MAP:
        assert key.strip(), "SKILL_LEVEL_MAP has empty key"
