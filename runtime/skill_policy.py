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
