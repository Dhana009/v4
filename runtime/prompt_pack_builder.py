from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from runtime.prompt_packs import PromptPack, hash_stable_prefix
from runtime.telemetry import estimate_text_tokens


PROMPT_PACK_VERSION_STEP_PLAN_NORMALIZER = 1
PROMPT_PACK_ID_STEP_PLAN_NORMALIZER = "step_plan_normalizer.v1"

NON_NEGOTIABLE_RUNTIME_RULES: tuple[str, ...] = (
    "1. You reason and propose only. You do not decide step completion or recording.",
    "2. Backend Step Runner owns lifecycle truth. Your output is a proposal for backend validation.",
    "3. No browser action executes before user confirmation.",
    "4. You may not instruct the frontend to record steps or update lifecycle state.",
    "5. Do not change the active plan structure silently. Every change must be explicit.",
)

STEP_PLAN_NORMALIZER_DYNAMIC_SUFFIX_TEMPLATE = """
DYNAMIC_PLANNING_CONTEXT:
- User intent: {user_intent}
- Selected element/context: {selected_context}
- Page summary: {page_summary}
- Existing queued steps: {queued_steps}
- Validated locators available: {validated_locators}
- Skills loaded: {skills_loaded}
- Skill levels: {skill_levels}
- Output schema: {output_schema_reminder}
""".strip()

REGISTERED_PROMPT_PACK_PURPOSES: tuple[str, ...] = ("step_plan_normalizer",)

_STEP_PLAN_NORMALIZER_STABLE_PREFIX = """
PROMPT_PACK_ID: step_plan_normalizer.v1
PROMPT_PACK_VERSION: 1
PURPOSE: step_plan_normalizer

NON_NEGOTIABLE_RUNTIME_RULES:
1. You reason and propose only. You do not decide step completion or recording.
2. Backend Step Runner owns lifecycle truth. Your output is a proposal for backend validation.
3. No browser action executes before user confirmation.
4. You may not instruct the frontend to record steps or update lifecycle state.
5. Do not change the active plan structure silently. Every change must be explicit.

ROLE:
You convert the user's current automation intent into a concise backend-valid plan proposal.

OUTPUT_EXPECTATION:
- Produce a backend-valid plan proposal only.
- No completion or finality authority.
- No execution before confirmation.
- Preserve user intent order unless a correction explicitly changes it.
- Ask clarification when ambiguous.
- Do not invent validated locator truth.
- Backend validates all locators and actions.
- Use tools only according to the provided tool schema.
- Keep the plan concise and structured.

PLANNING_RULES:
- Represent broad user intent as parent steps with ordered child operations.
- Do not claim a locator, action, assertion, or result is validated.
- Do not mark any step as recorded, completed, skipped, or failed.
- Do not generate final Playwright code.
- Fail closed when the intent cannot be represented safely.
""".strip()


def _normalize_list(values: Sequence[str] | None) -> str:
    parts = [str(value).strip() for value in (values or ()) if str(value).strip()]
    return ", ".join(parts)


def _latest_user_message(messages: Sequence[Mapping[str, Any]] | None) -> str:
    for message in reversed(list(messages or [])):
        if not isinstance(message, Mapping):
            continue
        if str(message.get("role") or "").strip().lower() != "user":
            continue
        content = message.get("content")
        if content is None:
            continue
        return str(content).strip()
    return ""


def build_step_plan_normalizer_dynamic_context(
    *,
    messages: Sequence[Mapping[str, Any]] | None = None,
    metadata: Mapping[str, Any] | None = None,
    skills_loaded: Sequence[str] | None = None,
    skill_levels: Sequence[str] | None = None,
    output_schema: Mapping[str, Any] | None = None,
) -> dict[str, str]:
    normalized_metadata = dict(metadata or {})
    schema_id = ""
    if isinstance(output_schema, Mapping):
        schema_id = str(output_schema.get("schema_id") or "").strip()

    return {
        "user_intent": _latest_user_message(messages),
        "selected_context": str(
            normalized_metadata.get("selected_context")
            or normalized_metadata.get("context_mode")
            or normalized_metadata.get("phase")
            or ""
        ).strip(),
        "page_summary": str(
            normalized_metadata.get("page_summary")
            or normalized_metadata.get("context_summary")
            or ""
        ).strip(),
        "queued_steps": str(
            normalized_metadata.get("queued_steps")
            or normalized_metadata.get("final_message_count")
            or normalized_metadata.get("original_message_count")
            or ""
        ).strip(),
        "validated_locators": str(
            normalized_metadata.get("validated_locators")
            or normalized_metadata.get("validated_locator_count")
            or ""
        ).strip(),
        "skills_loaded": _normalize_list(skills_loaded),
        "skill_levels": _normalize_list(skill_levels),
        "output_schema_reminder": (
            f"return a plan proposal compatible with {schema_id} backend validation."
            if schema_id
            else "return a plan proposal compatible with backend validation."
        ),
    }


def build_step_plan_normalizer_pack(
    *,
    dynamic_context: Mapping[str, Any] | None = None,
    skills_loaded: Sequence[str] | None = None,
    skill_levels: Sequence[str] | None = None,
) -> PromptPack:
    del dynamic_context
    del skills_loaded
    del skill_levels
    stable_prefix = _STEP_PLAN_NORMALIZER_STABLE_PREFIX
    return PromptPack(
        purpose="step_plan_normalizer",
        prompt_pack_id=PROMPT_PACK_ID_STEP_PLAN_NORMALIZER,
        prompt_pack_version=PROMPT_PACK_VERSION_STEP_PLAN_NORMALIZER,
        stable_prefix=stable_prefix,
        dynamic_suffix_template=STEP_PLAN_NORMALIZER_DYNAMIC_SUFFIX_TEMPLATE,
        required_safety_rules=NON_NEGOTIABLE_RUNTIME_RULES,
        prefix_hash=hash_stable_prefix(stable_prefix),
        estimated_stable_tokens=estimate_text_tokens(stable_prefix),
    )


def build_prompt_pack(
    purpose: str,
    *,
    dynamic_context: Mapping[str, Any] | None = None,
    skills_loaded: Sequence[str] | None = None,
    skill_levels: Sequence[str] | None = None,
) -> PromptPack:
    normalized_purpose = str(purpose or "").strip()
    if normalized_purpose == "step_plan_normalizer":
        return build_step_plan_normalizer_pack(
            dynamic_context=dynamic_context,
            skills_loaded=skills_loaded,
            skill_levels=skill_levels,
        )
    raise ValueError(f"Unsupported prompt pack purpose: {normalized_purpose!r}")
