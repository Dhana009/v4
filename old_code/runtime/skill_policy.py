from __future__ import annotations

# Sprint 3 INT-LLM-002: canonical skill-level mapping.
# Single source of truth for which skills load at which level.
# - core_compact: always loaded, minimal tokens
# - skill_summary: loaded only when purpose/capability needs it
# - full_skill: loaded only on explicit escalation
# - debug_skill: loaded only in recovery/debug phase

SKILL_LEVEL_MAP: dict[str, str] = {
    # core_compact — always present
    "llm_runtime_controller": "core_compact",
    "prompt_persona_skill_loading": "core_compact",
    # skill_summary — loaded only when the purpose needs it
    "locator_strategy": "skill_summary",
    "backend_step_runner": "skill_summary",
    "codegen": "skill_summary",
    "contract_testing": "skill_summary",
    # full_skill — only on explicit escalation
    "capability_framework": "full_skill",
    "replay_repair": "full_skill",
    "real_world_fixtures": "full_skill",
    # debug_skill — only in recovery/debug context
    "observability_trace": "debug_skill",
    "memory_human_feedback": "debug_skill",
}

MINIMAL_CORE_SKILLS: tuple[str, ...] = ("llm_runtime_controller",)
PURPOSE_DEBUG_SKILLS: tuple[str, ...] = ("observability_trace", "memory_human_feedback")
FULL_SKILL_ESCALATION_PURPOSES: frozenset[str] = frozenset({
    "journey_planner",
    "step_plan_normalizer",
    "locator_specialist",
    "custom_assertion_planner",
    "page_validation_recommender",
    "recovery_diagnoser",
    "replay_repair_specialist",
})
FULL_SKILL_ESCALATION_REASONS: frozenset[str] = frozenset({
    "schema_retry",
    "validation_failure",
    "invalid_output",
    "developer_override",
    "user_override",
})

# Purposes that must NEVER load full action/browser/locator skills by default.
# plan_diff_editor only needs persona — no DOM/browser skill content.
COMPACT_ONLY_PURPOSES: frozenset[str] = frozenset({
    "plan_diff_editor",
    "intent_classifier",
    "clarification_generator",
    "user_response_writer",
    "trace_summarizer",
})

# Purposes that may load locator skill summary.
LOCATOR_SUMMARY_PURPOSES: frozenset[str] = frozenset({
    "locator_specialist",
    "page_intelligence_summarizer",
    "page_validation_recommender",
    "custom_assertion_planner",
})

# Purposes that may load debug/recovery skill.
DEBUG_SKILL_PURPOSES: frozenset[str] = frozenset({
    "recovery_diagnoser",
    "replay_repair_specialist",
})


def get_skill_level(skill_name: str) -> str:
    """Return the loading level for a skill name. Defaults to skill_summary."""
    return SKILL_LEVEL_MAP.get(str(skill_name or "").strip(), "skill_summary")


def should_load_full_skill(skill_name: str, *, escalation: bool = False) -> bool:
    """Return True only if full skill content is warranted."""
    level = get_skill_level(skill_name)
    if level == "core_compact":
        return True
    if level == "full_skill":
        return escalation
    return False


def get_default_skill_names(
    purpose: str,
    configured_skill_names: list[str] | tuple[str, ...] | None = None,
) -> list[str]:
    normalized_purpose = str(purpose or "").strip()
    configured = [str(name).strip() for name in (configured_skill_names or ()) if str(name).strip()]
    if not configured:
        configured = list(MINIMAL_CORE_SKILLS)

    skill_names = list(dict.fromkeys(list(MINIMAL_CORE_SKILLS) + configured))
    if normalized_purpose in DEBUG_SKILL_PURPOSES:
        skill_names.extend(PURPOSE_DEBUG_SKILLS)
    return list(dict.fromkeys(skill_names))


def get_skill_levels_for_names(skill_names: list[str] | tuple[str, ...]) -> list[str]:
    return [get_skill_level(name) for name in (skill_names or ())]


def can_escalate_to_full_skills(
    purpose: str,
    *,
    escalation_reason: str | None = None,
    override_full: bool = False,
) -> bool:
    normalized_purpose = str(purpose or "").strip()
    if normalized_purpose in COMPACT_ONLY_PURPOSES:
        return False
    if override_full:
        return normalized_purpose in FULL_SKILL_ESCALATION_PURPOSES
    normalized_reason = str(escalation_reason or "").strip()
    if normalized_reason not in FULL_SKILL_ESCALATION_REASONS:
        return False
    return normalized_purpose in FULL_SKILL_ESCALATION_PURPOSES
