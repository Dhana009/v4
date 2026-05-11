from __future__ import annotations

COMPACT_SKILL_SUMMARIES: dict[str, str] = {
    "llm_runtime_controller": (
        "Runtime policy boundary. Propose structured output only. "
        "Respect purpose policy, schema, confirmation gates, and fail closed on invalid output."
    ),
    "prompt_persona_skill_loading": (
        "Respond concisely. Use exact tool names. Ask the user only when necessary. "
        "Do not claim execution or recording success without backend evidence."
    ),
    "locator_strategy": (
        "Prefer stable semantic selectors and read-only DOM inspection before proposing actions. "
        "Surface ambiguity instead of guessing."
    ),
    "backend_step_runner": (
        "Backend truth wins. step_recorded, code_update, and run completion require confirmed runtime evidence."
    ),
    "codegen": (
        "Generate deterministic code lines only from confirmed recorded actions and validated assertions."
    ),
    "contract_testing": (
        "Preserve contract boundaries. Prefer explicit schema and state invariants over speculative behavior."
    ),
    "capability_framework": (
        "Escalated capability guidance. Use broader workflow knowledge only when retry/validation explicitly requires it."
    ),
    "replay_repair": (
        "Escalated replay repair guidance. Repair proposals must preserve backend truth and avoid unsafe auto-replay."
    ),
    "real_world_fixtures": (
        "Escalated fixture guidance. Use only when validation requires broader real-world page assumptions."
    ),
    "observability_trace": (
        "Debug mode. Use logs, traces, and telemetry to classify failures. Do not mutate runtime truth while diagnosing."
    ),
    "memory_human_feedback": (
        "Honor explicit user corrections and confirmed checkpoints. Preserve correction semantics and fail safely when unclear."
    ),
}


def get_skill_summary(skill_name: str) -> str:
    normalized_name = str(skill_name or "").strip()
    if not normalized_name:
        return ""
    return COMPACT_SKILL_SUMMARIES.get(
        normalized_name,
        f"{normalized_name}: compact runtime summary unavailable; keep reasoning narrow and fail closed.",
    )
