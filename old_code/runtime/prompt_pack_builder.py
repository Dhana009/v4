from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from runtime.correction_context import build_plan_diff_editor_context_payload
from runtime.prompt_packs import PromptPack, hash_stable_prefix
from runtime.recovery_context import build_recovery_diagnoser_context_payload
from runtime.telemetry import estimate_text_tokens


PROMPT_PACK_VERSION_STEP_PLAN_NORMALIZER = 1
PROMPT_PACK_ID_STEP_PLAN_NORMALIZER = "step_plan_normalizer.v1"

PROMPT_PACK_VERSION_PLAN_DIFF_EDITOR = 1
PROMPT_PACK_ID_PLAN_DIFF_EDITOR = "plan_diff_editor.v1"

PROMPT_PACK_VERSION_RECOVERY_DIAGNOSER = 1
PROMPT_PACK_ID_RECOVERY_DIAGNOSER = "recovery_diagnoser.v1"

NON_NEGOTIABLE_RUNTIME_RULES: tuple[str, ...] = (
    "1. You reason and propose only. You do not decide step completion or recording.",
    "2. Backend Step Runner owns lifecycle truth. Your output is a proposal for backend validation.",
    "3. No browser action executes before user confirmation.",
    "4. You may not instruct the frontend to record steps or update lifecycle state.",
    "5. Do not change the active plan structure silently. Every change must be explicit.",
)

REGISTERED_PROMPT_PACK_PURPOSES: tuple[str, ...] = (
    "step_plan_normalizer",
    "plan_diff_editor",
    "recovery_diagnoser",
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

PLAN_DIFF_EDITOR_DYNAMIC_SUFFIX_TEMPLATE = """
DYNAMIC_CORRECTION_CONTEXT:
- Structured correction diff context.
- Active plan id: {active_plan_id}
- Target step id: {target_step_id}
- User correction: {correction_text}
- Active plan summary: {active_plan_summary}
- Existing child operations: {child_operations}
- Validated locators available: {validated_locators}
- Validation feedback: {validation_feedback}
- Allowed edit policy: {allowed_edit_policy}
- Locator context required: {locator_context_required}
""".strip()

RECOVERY_DIAGNOSER_DYNAMIC_SUFFIX_TEMPLATE = """
DYNAMIC_RECOVERY_CONTEXT:
- Recovery required for the failed original step.
- Run id: {run_id}
- Failed step id: {failed_step_id}
- Failed operation id: {failed_operation_id}
- Failed step summary: {failed_step_summary}
- Error summary: {error_summary}
- Current URL/title: {current_page}
- Tried fixes for this failed step: {tried_fixes}
- Relevant locator/action evidence: {failure_evidence}
- User recovery instruction: {user_recovery_instruction}
- Retry attempts for this failed step: {retry_attempts}
""".strip()

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

TERMINAL_OUTPUT_REQUIREMENT:
- You MUST terminate planning in this turn by calling one of:
  (a) send_to_overlay(message_type="plan_ready", payload={...}) — when you have a complete plan proposal.
  (b) ask_user(question="...") — when intent is ambiguous and you cannot produce a safe plan without clarification.
- You MAY call send_to_overlay(message_type="llm_thinking", ...) at most once before your terminal call.
- After one llm_thinking call, you MUST produce plan_ready or ask_user in the same response or the very next response.
- Do NOT emit repeated llm_thinking calls. Repeated thinking without a terminal call is a protocol violation.
- Do not respond with plain text instead of a tool call. Every planning turn must end with a tool call.

AMBIGUITY_RULE:
- If DOM or page evidence shows multiple plausible targets, do not guess and do not keep exploring.
- Call ask_user immediately with one precise clarification question listing the distinguishing options.
- Example: if there are Profile Settings, Billing Profile, and Shipping Profile sections, ask which one.
- Do not call dom_extract or browser_get_state repeatedly when the page content is already known.

PLANNING_RULES:
- Represent broad user intent as parent steps with ordered child operations.
- Do not claim a locator, action, assertion, or result is validated.
- Do not mark any step as recorded, completed, skipped, or failed.
- Do not generate final Playwright code.
- Fail closed when the intent cannot be represented safely.
""".strip()

_PLAN_DIFF_EDITOR_STABLE_PREFIX = """
PROMPT_PACK_ID: plan_diff_editor.v1
PROMPT_PACK_VERSION: 1
PURPOSE: plan_diff_editor

NON_NEGOTIABLE_RUNTIME_RULES:
1. You reason and propose only. You do not decide step completion or recording.
2. Backend Step Runner owns lifecycle truth. Your output is a proposal for backend validation.
3. No browser action executes before user confirmation.
4. You may not instruct the frontend to record steps or update lifecycle state.
5. Do not change the active plan structure silently. Every change must be explicit.

ROLE:
You convert a user's correction into a structured plan edit proposal.

OUTPUT_EXPECTATION:
- Produce a backend-valid correction proposal only.
- No completion or finality authority.
- No execution before confirmation.
- Preserve existing child operations unless the user explicitly removes them.
- Preserve operation order unless the user explicitly reorders it.
- Do not split or merge parent steps unless the user explicitly asks.
- Ask clarification when ambiguous.

CORRECTION_RULES:
- Use the active plan as the source of truth.
- Do not silently drop operations.
- Do not silently reorder operations.
- Do not invent validated locator truth.
- Backend validates and applies the diff.
""".strip()

_RECOVERY_DIAGNOSER_STABLE_PREFIX = """
PROMPT_PACK_ID: recovery_diagnoser.v1
PROMPT_PACK_VERSION: 1
PURPOSE: recovery_diagnoser

NON_NEGOTIABLE_RUNTIME_RULES:
1. You reason and propose only. You do not decide step completion or recording.
2. Backend Step Runner owns lifecycle truth. Your output is a proposal for backend validation.
3. No browser action executes before user confirmation.
4. You may not instruct the frontend to record steps or update lifecycle state.
5. Do not change the active plan structure silently. Every change must be explicit.

ROLE:
You diagnose a failed backend operation and propose the next safe recovery action.

OUTPUT_EXPECTATION:
- Diagnose the failed step only.
- Stay anchored to the failed step.
- Propose retry, ask user, skip, or stop only.
- Do not mark the step recovered, recorded, skipped, failed, or completed.
- Backend validates any retry before execution.

RECOVERY_RULES:
- Stay anchored to the failed step and failed operation.
- Do not change the user's original goal unless the user explicitly changes it.
- Keep reasoning concise and based only on provided failure evidence.
- Avoid unrelated history and broad plan rewrites.
""".strip()


def _build_stable_prefix(
    *,
    prompt_pack_id: str,
    prompt_pack_version: int,
    purpose: str,
    role: str,
    output_expectation: Sequence[str],
    purpose_rules: Sequence[str] = (),
) -> str:
    lines = [
        f"PROMPT_PACK_ID: {prompt_pack_id}",
        f"PROMPT_PACK_VERSION: {prompt_pack_version}",
        f"PURPOSE: {purpose}",
        "",
        "NON_NEGOTIABLE_RUNTIME_RULES:",
        *NON_NEGOTIABLE_RUNTIME_RULES,
        "",
        "ROLE:",
        role,
        "",
        "OUTPUT_EXPECTATION:",
        *output_expectation,
    ]
    if purpose_rules:
        lines.extend(["", f"{purpose.split('_')[0].upper()}_RULES:"])
        lines.extend(list(purpose_rules))
    return "\n".join(lines).strip()


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


def build_plan_diff_editor_dynamic_context(
    *,
    messages: Sequence[Mapping[str, Any]] | None = None,
    active_plan_state: Mapping[str, Any] | None = None,
    correction_state: Mapping[str, Any] | None = None,
    validation_feedback: str | None = None,
    allowed_edit_policy: str | None = None,
    validated_locators: Sequence[str] | None = None,
) -> dict[str, str]:
    payload = build_plan_diff_editor_context_payload(
        active_plan_state=active_plan_state,
        correction_state=correction_state,
        validation_feedback=validation_feedback,
        allowed_edit_policy=allowed_edit_policy,
        validated_locators=validated_locators,
    )
    if messages:
        from runtime.correction_context import extract_plan_diff_editor_context_from_messages

        payload = extract_plan_diff_editor_context_from_messages(
            messages,
            active_plan_state=active_plan_state,
            correction_state=correction_state,
            validation_feedback=validation_feedback,
            allowed_edit_policy=allowed_edit_policy,
        )
    return {key: str(value) for key, value in payload.items()}


def build_recovery_diagnoser_dynamic_context(
    *,
    messages: Sequence[Mapping[str, Any]] | None = None,
    metadata: Mapping[str, Any] | None = None,
    failed_step_state: Mapping[str, Any] | None = None,
    failed_step_id: str | None = None,
    failed_operation_id: str | None = None,
    error_summary: str | None = None,
    current_page: str | None = None,
    tried_fixes: Sequence[Any] | str | None = None,
    failure_evidence: Sequence[Any] | str | None = None,
    user_recovery_instruction: str | None = None,
    retry_attempts: Sequence[Mapping[str, Any]] | Sequence[Any] | str | None = None,
    run_id: str | None = None,
) -> dict[str, str]:
    payload = build_recovery_diagnoser_context_payload(
        run_id=run_id,
        failed_step_state=failed_step_state,
        failed_step_id=failed_step_id,
        failed_operation_id=failed_operation_id,
        error_summary=error_summary,
        current_page=current_page,
        tried_fixes=tried_fixes,
        failure_evidence=failure_evidence,
        user_recovery_instruction=user_recovery_instruction,
        retry_attempts=retry_attempts,
        messages=messages,
        metadata=metadata,
    )
    if messages or metadata:
        from runtime.recovery_context import extract_recovery_diagnoser_context_from_messages

        payload = extract_recovery_diagnoser_context_from_messages(
            messages,
            metadata=metadata,
            failed_step_state=failed_step_state,
        )
    return {key: str(value) for key, value in payload.items()}


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


def build_plan_diff_editor_pack(
    *,
    dynamic_context: Mapping[str, Any] | None = None,
    skills_loaded: Sequence[str] | None = None,
    skill_levels: Sequence[str] | None = None,
) -> PromptPack:
    del dynamic_context
    del skills_loaded
    del skill_levels
    stable_prefix = _PLAN_DIFF_EDITOR_STABLE_PREFIX
    return PromptPack(
        purpose="plan_diff_editor",
        prompt_pack_id=PROMPT_PACK_ID_PLAN_DIFF_EDITOR,
        prompt_pack_version=PROMPT_PACK_VERSION_PLAN_DIFF_EDITOR,
        stable_prefix=stable_prefix,
        dynamic_suffix_template=PLAN_DIFF_EDITOR_DYNAMIC_SUFFIX_TEMPLATE,
        required_safety_rules=NON_NEGOTIABLE_RUNTIME_RULES,
        prefix_hash=hash_stable_prefix(stable_prefix),
        estimated_stable_tokens=estimate_text_tokens(stable_prefix),
    )


def build_recovery_diagnoser_pack(
    *,
    dynamic_context: Mapping[str, Any] | None = None,
    skills_loaded: Sequence[str] | None = None,
    skill_levels: Sequence[str] | None = None,
) -> PromptPack:
    del dynamic_context
    del skills_loaded
    del skill_levels
    stable_prefix = _RECOVERY_DIAGNOSER_STABLE_PREFIX
    return PromptPack(
        purpose="recovery_diagnoser",
        prompt_pack_id=PROMPT_PACK_ID_RECOVERY_DIAGNOSER,
        prompt_pack_version=PROMPT_PACK_VERSION_RECOVERY_DIAGNOSER,
        stable_prefix=stable_prefix,
        dynamic_suffix_template=RECOVERY_DIAGNOSER_DYNAMIC_SUFFIX_TEMPLATE,
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
    if normalized_purpose == "plan_diff_editor":
        return build_plan_diff_editor_pack(
            dynamic_context=dynamic_context,
            skills_loaded=skills_loaded,
            skill_levels=skill_levels,
        )
    if normalized_purpose == "recovery_diagnoser":
        return build_recovery_diagnoser_pack(
            dynamic_context=dynamic_context,
            skills_loaded=skills_loaded,
            skill_levels=skill_levels,
        )
    raise ValueError(f"Unsupported prompt pack purpose: {normalized_purpose!r}")
