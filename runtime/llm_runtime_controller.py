from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
import inspect
import time
from typing import Any

from runtime.prompt_pack_builder import (
    build_prompt_pack,
    build_plan_diff_editor_dynamic_context,
    build_recovery_diagnoser_dynamic_context,
    build_step_plan_normalizer_dynamic_context,
)
from runtime.prompt_packs import apply_prompt_pack_to_messages
from runtime.skill_selector import build_skill_prompt, select_skills_for_purpose
from runtime.telemetry import estimate_messages_tokens, estimate_tools_tokens
from runtime.tool_registry import PLANNING_SAFE_TOOL_NAMES
from runtime.tool_schema_policy import (
    PLAN_REVIEW_ONLY_TOOL_NAMES,
    RECOVERY_ONLY_TOOL_NAMES,
    STEP_PLAN_TOOL_NAMES,
    planning_tools_for_purpose,
    recovery_tools_for_purpose,
)


ALLOWED_PURPOSES = (
    "intent_classifier",
    "clarification_generator",
    "page_intelligence_summarizer",
    "page_validation_recommender",
    "journey_planner",
    "step_plan_normalizer",
    "plan_diff_editor",
    "locator_specialist",
    "custom_assertion_planner",
    "execution_driver",
    "recovery_diagnoser",
    "replay_repair_specialist",
    "user_response_writer",
    "trace_summarizer",
)

CORE_SKILLS = ("llm_runtime_controller",)
PERSONA_SKILL = "prompt_persona_skill_loading"
LOCATOR_SKILL = "locator_strategy"

DEFAULT_TELEMETRY_FIELDS = {
    "purpose": "str",
    "model": "str",
    "call_id": "str",
    "skill_count": "int",
    "skills_loaded": "list[str]",
    "tool_count": "int",
    "tools_exposed_count": "int",
    "context_mode": "str",
    "context_level": "str",
    "token_budget": "int",
    "estimated_input_tokens": "int",
    "estimated_output_tokens": "int|None",
    "retry_count": "int",
    "validation_status": "str",
    "latency_ms": "int",
    "schema_id": "str",
    "schema_version": "int",
    "error_code": "str|None",
}

PLANNING_TOOL_NAMES = (
    "send_to_overlay",
    "browser_get_state",
    "dom_extract",
    "locator_find",
    "locator_validate",
    "ask_user",
)

LOCATOR_TOOL_NAMES = (
    "browser_get_state",
    "dom_extract",
    "locator_find",
    "locator_validate",
    "ask_user",
)

def _normalize_names(values: Any) -> list[str]:
    if values is None:
        return []
    if isinstance(values, str):
        text = values.strip()
        return [text] if text else []
    if isinstance(values, Mapping):
        return [str(key).strip() for key in values.keys() if str(key).strip()]
    if isinstance(values, Sequence):
        names: list[str] = []
        for item in values:
            text = str(item).strip()
            if text:
                names.append(text)
        return names
    text = str(values).strip()
    return [text] if text else []


def _skill_policy(
    *,
    purpose: str,
    skill_names: Sequence[str],
    skill_level: str = "core_compact",
    token_budget: int = 2400,
) -> dict[str, Any]:
    normalized_skill_names = _normalize_names(skill_names)
    return {
        "purpose": purpose,
        "skill_level": skill_level,
        "load_all": False,
        "required_core_skills": list(CORE_SKILLS),
        "purpose_skills": normalized_skill_names,
        "skill_budget": token_budget,
        "skill_scope": "purpose_specific",
    }


def _context_policy(
    *,
    purpose: str,
    context_level: str = "compact",
    context_mode: str = "compact",
) -> dict[str, Any]:
    return {
        "purpose": purpose,
        "context_level": context_level,
        "context_mode": context_mode,
        "allow_full_dom": False,
        "allow_full_history": False,
        "allow_raw_dom": False,
        "allow_unbounded_context": False,
    }


def _tool_policy(
    *,
    purpose: str,
    planning_tools: Sequence[str],
    plan_review_tools: Sequence[str] | None = None,
    recovery_tools: Sequence[str] | None = None,
    executing_tools: Sequence[str] | None = None,
    completed_tools: Sequence[str] | None = None,
    deny_reason: str = "deny_by_default",
) -> dict[str, Any]:
    plan_review_phase_tools = PLAN_REVIEW_ONLY_TOOL_NAMES if plan_review_tools is None else plan_review_tools
    allowed_tools_by_phase = {
        "planning": _normalize_names(planning_tools),
        "plan_review": _normalize_names(plan_review_phase_tools),
        "awaiting_confirmation": _normalize_names(plan_review_phase_tools),
        "executing": _normalize_names(executing_tools or ()),
        "recovery": _normalize_names(recovery_tools or RECOVERY_ONLY_TOOL_NAMES),
        "completed": _normalize_names(completed_tools or ()),
    }
    return {
        "purpose": purpose,
        "allowed_tools_by_phase": allowed_tools_by_phase,
        "deny_reason": deny_reason,
        "default_deny_reason": deny_reason,
        "phase_policy": "deny_by_default",
    }


def _retry_policy(*, purpose: str, schema_retry_limit: int = 1) -> dict[str, Any]:
    return {
        "purpose": purpose,
        "schema_retry_limit": schema_retry_limit,
        "retry_limit": schema_retry_limit,
        "fallback_action": "fail_closed",
        "fallback": "fail_closed",
        "on_failure": "fail_closed",
    }


def _telemetry_fields(purpose: str) -> dict[str, str]:
    telemetry_fields = dict(DEFAULT_TELEMETRY_FIELDS)
    telemetry_fields["purpose"] = purpose
    telemetry_fields["model"] = "str"
    return telemetry_fields


def _output_schema(purpose: str) -> dict[str, Any]:
    return {
        "schema_id": f"{purpose}.v1",
        "schema_version": 1,
        "purpose": purpose,
        "format": "structured_json",
    }


def _purpose_policy(
    *,
    purpose: str,
    model_class: str,
    skill_names: Sequence[str],
    planning_tools: Sequence[str],
    plan_review_tools: Sequence[str] | None = None,
    executing_tools: Sequence[str] | None = None,
    token_budget: int,
    context_level: str = "compact",
    context_mode: str = "compact",
) -> dict[str, Any]:
    return {
        "purpose": purpose,
        "purpose_id": purpose,
        "owner": "DEV-2 LLM Runtime Controller",
        "model_class": model_class,
        "skill_policy": _skill_policy(
            purpose=purpose,
            skill_names=skill_names,
            token_budget=token_budget,
        ),
        "context_policy": _context_policy(
            purpose=purpose,
            context_level=context_level,
            context_mode=context_mode,
        ),
        "tool_policy": _tool_policy(
            purpose=purpose,
            planning_tools=planning_tools,
            plan_review_tools=plan_review_tools,
            executing_tools=executing_tools,
        ),
        "output_schema": _output_schema(purpose),
        "backend_validator": "schema_validator",
        "validator": "schema_validator",
        "retry_policy": _retry_policy(purpose=purpose, schema_retry_limit=1),
        "fallback": "fail_closed",
        "telemetry_fields": _telemetry_fields(purpose),
        "allowed_side_effects": ["none"],
        "token_budget": token_budget,
    }


def _build_purpose_policy_map() -> dict[str, dict[str, Any]]:
    planner_skill = (PERSONA_SKILL,)
    locator_skill = (LOCATOR_SKILL,)
    mixed_skill = (PERSONA_SKILL, LOCATOR_SKILL)
    debug_skill = (PERSONA_SKILL,)

    return {
        "intent_classifier": _purpose_policy(
            purpose="intent_classifier",
            model_class="cheap",
            skill_names=planner_skill,
            planning_tools=planning_tools_for_purpose("intent_classifier"),
            token_budget=1000,
        ),
        "clarification_generator": _purpose_policy(
            purpose="clarification_generator",
            model_class="cheap",
            skill_names=planner_skill,
            planning_tools=planning_tools_for_purpose("clarification_generator"),
            token_budget=1000,
        ),
        "page_intelligence_summarizer": _purpose_policy(
            purpose="page_intelligence_summarizer",
            model_class="cheap",
            skill_names=locator_skill,
            planning_tools=planning_tools_for_purpose("page_intelligence_summarizer"),
            token_budget=1400,
        ),
        "page_validation_recommender": _purpose_policy(
            purpose="page_validation_recommender",
            model_class="main",
            skill_names=locator_skill,
            planning_tools=planning_tools_for_purpose("page_validation_recommender"),
            token_budget=1800,
        ),
        "journey_planner": _purpose_policy(
            purpose="journey_planner",
            model_class="main",
            skill_names=planner_skill,
            planning_tools=planning_tools_for_purpose("journey_planner"),
            token_budget=2400,
        ),
        "step_plan_normalizer": _purpose_policy(
            purpose="step_plan_normalizer",
            model_class="main",
            skill_names=planner_skill,
            planning_tools=planning_tools_for_purpose("step_plan_normalizer"),
            token_budget=3000,
        ),
        "plan_diff_editor": _purpose_policy(
            purpose="plan_diff_editor",
            model_class="main",
            skill_names=planner_skill,
            planning_tools=planning_tools_for_purpose("plan_diff_editor"),
            plan_review_tools=(),
            token_budget=2200,
        ),
        "locator_specialist": _purpose_policy(
            purpose="locator_specialist",
            model_class="main",
            skill_names=locator_skill,
            planning_tools=planning_tools_for_purpose("locator_specialist"),
            token_budget=2200,
        ),
        "custom_assertion_planner": _purpose_policy(
            purpose="custom_assertion_planner",
            model_class="main",
            skill_names=mixed_skill,
            planning_tools=planning_tools_for_purpose("custom_assertion_planner"),
            token_budget=2200,
        ),
        "execution_driver": _purpose_policy(
            purpose="execution_driver",
            model_class="main",
            skill_names=planner_skill,
            planning_tools=planning_tools_for_purpose("execution_driver"),
            executing_tools=("action_assert", "action_click", "action_fill"),
            token_budget=1800,
        ),
        "recovery_diagnoser": _purpose_policy(
            purpose="recovery_diagnoser",
            model_class="main",
            skill_names=debug_skill,
            planning_tools=planning_tools_for_purpose("recovery_diagnoser"),
            token_budget=1800,
        ),
        "replay_repair_specialist": _purpose_policy(
            purpose="replay_repair_specialist",
            model_class="main",
            skill_names=debug_skill,
            planning_tools=planning_tools_for_purpose("replay_repair_specialist"),
            token_budget=1800,
        ),
        "user_response_writer": _purpose_policy(
            purpose="user_response_writer",
            model_class="cheap",
            skill_names=planner_skill,
            planning_tools=planning_tools_for_purpose("user_response_writer"),
            token_budget=1000,
        ),
        "trace_summarizer": _purpose_policy(
            purpose="trace_summarizer",
            model_class="cheap",
            skill_names=planner_skill,
            planning_tools=planning_tools_for_purpose("trace_summarizer"),
            token_budget=1000,
        ),
    }


class PurposeRegistry(dict[str, dict[str, Any]]):
    def __init__(self, initial_policies: Mapping[str, Mapping[str, Any]] | None = None) -> None:
        super().__init__()
        for purpose, policy in (initial_policies or {}).items():
            self.register(purpose, policy)

    def register(self, purpose: str, policy: Mapping[str, Any]) -> None:
        normalized_purpose = str(purpose or "").strip()
        if normalized_purpose not in ALLOWED_PURPOSES:
            raise ValueError(f"Unknown LLM purpose: {normalized_purpose!r}")
        dict.__setitem__(self, normalized_purpose, dict(policy))

    def get_purpose_policy(self, purpose: str) -> dict[str, Any]:
        normalized_purpose = str(purpose or "").strip()
        if normalized_purpose not in self:
            raise KeyError(normalized_purpose)
        return dict.__getitem__(self, normalized_purpose)

    def list_purposes(self) -> list[str]:
        return list(self.keys())


PURPOSE_REGISTRY = PurposeRegistry(_build_purpose_policy_map())
LLM_PURPOSE_REGISTRY = PURPOSE_REGISTRY
purpose_registry = PURPOSE_REGISTRY
registry = PURPOSE_REGISTRY


def _value(payload: Any, *names: str, default: Any = None) -> Any:
    for name in names:
        if isinstance(payload, Mapping):
            if name in payload:
                candidate = payload[name]
            else:
                continue
        else:
            if not hasattr(payload, name):
                continue
            candidate = getattr(payload, name)
        if candidate not in (None, "", [], {}, ()):
            return candidate
    return default


def _content_from_response(response: Any) -> Any:
    if isinstance(response, str):
        return response

    if isinstance(response, Mapping):
        choices = response.get("choices")
    else:
        choices = getattr(response, "choices", None)

    if isinstance(choices, Sequence) and choices:
        first_choice = choices[0]
        if isinstance(first_choice, Mapping):
            message = first_choice.get("message")
        else:
            message = getattr(first_choice, "message", None)

        if isinstance(message, Mapping):
            content = message.get("content")
        else:
            content = getattr(message, "content", None)

        if content is not None:
            return content

    return response


def _message_from_response(response: Any) -> Any:
    if isinstance(response, Mapping):
        choices = response.get("choices")
    else:
        choices = getattr(response, "choices", None)

    if isinstance(choices, Sequence) and choices:
        first_choice = choices[0]
        if isinstance(first_choice, Mapping):
            return first_choice.get("message")
        return getattr(first_choice, "message", None)

    return None


def _tool_calls_from_message(message: Any) -> list[Any]:
    if isinstance(message, Mapping):
        tool_calls = message.get("tool_calls")
    else:
        tool_calls = getattr(message, "tool_calls", None)
    if isinstance(tool_calls, Sequence) and not isinstance(tool_calls, (str, bytes)):
        return list(tool_calls)
    return []


def _content_from_message(message: Any) -> Any:
    if isinstance(message, Mapping):
        return message.get("content")
    if message is None:
        return None
    return getattr(message, "content", None)


def _call_if_available(target: Any, *candidate_names: str, **payload: Any) -> Any:
    for name in candidate_names:
        callable_obj = getattr(target, name, None)
        if callable(callable_obj):
            result = callable_obj(**payload)
            if inspect.isawaitable(result):
                return result
            return result
    return None


def _maybe_await(value: Any) -> Any:
    if inspect.isawaitable(value):
        return value
    return value


@dataclass(slots=True)
class ControllerTelemetry:
    call_id: str
    purpose: str
    model: str
    skill_count: int
    skills_loaded: list[str]
    skill_levels: list[str]
    tool_count: int
    tools_exposed_count: int
    context_mode: str
    context_level: str
    token_budget: int
    estimated_input_tokens: int
    estimated_output_tokens: int | None
    retry_count: int
    validation_status: str
    latency_ms: int
    schema_id: str
    schema_version: int
    error_code: str | None


class LLMRuntimeController:
    PURPOSE_REGISTRY = PURPOSE_REGISTRY

    def __init__(
        self,
        *,
        purpose_registry: Mapping[str, Any],
        schema_validator: Any,
        context_manager: Any | None = None,
        skill_manager: Any | None = None,
        tool_registry: Any | None = None,
        telemetry_sink: Any | None = None,
        model_client: Any | None = None,
        client: Any | None = None,
        model_router: Any | None = None,
    ) -> None:
        if purpose_registry is None:
            raise TypeError("purpose_registry is required")
        if schema_validator is None:
            raise TypeError("schema_validator is required")

        self.purpose_registry = purpose_registry
        self.schema_validator = schema_validator
        self.context_manager = context_manager
        self.skill_manager = skill_manager
        self.tool_registry = tool_registry
        self.telemetry_sink = telemetry_sink
        self.model_client = model_client or client
        self.model_router = model_router

    def get_purpose_policy(self, purpose: str) -> dict[str, Any]:
        return self._resolve_policy(purpose)

    def resolve_purpose_policy(
        self,
        purpose: str,
        *,
        policy: Any | None = None,
        purpose_policy: Any | None = None,
    ) -> dict[str, Any]:
        if policy is not None:
            return dict(policy) if isinstance(policy, Mapping) else policy
        if purpose_policy is not None:
            return (
                dict(purpose_policy)
                if isinstance(purpose_policy, Mapping)
                else purpose_policy
            )
        return self._resolve_policy(purpose)

    def _resolve_policy(self, purpose: str) -> dict[str, Any]:
        normalized_purpose = str(purpose or "").strip()
        if normalized_purpose not in self.purpose_registry:
            raise ValueError(f"Unknown LLM purpose: {normalized_purpose!r}")

        policy = self.purpose_registry.get_purpose_policy(normalized_purpose)
        if not isinstance(policy, Mapping):
            raise TypeError(f"Invalid policy shape for {normalized_purpose!r}")
        return dict(policy)

    def _select_model_client(self, client: Any | None, model_client: Any | None, llm_client: Any | None, openai_client: Any | None) -> Any | None:
        for candidate in (
            client,
            model_client,
            llm_client,
            openai_client,
            self.model_client,
        ):
            if candidate is not None:
                return candidate
        return None

    def _select_validator(self, schema_validator: Any | None) -> Any:
        if schema_validator is not None:
            return schema_validator
        return self.schema_validator

    def _select_context_manager(self, context_manager: Any | None) -> Any | None:
        return context_manager if context_manager is not None else self.context_manager

    def _select_skill_manager(self, skill_manager: Any | None) -> Any | None:
        return skill_manager if skill_manager is not None else self.skill_manager

    def _select_tool_registry(self, tool_registry: Any | None) -> Any | None:
        return tool_registry if tool_registry is not None else self.tool_registry

    def _select_telemetry_sink(self, telemetry_sink: Any | None) -> Any | None:
        return telemetry_sink if telemetry_sink is not None else self.telemetry_sink

    def _apply_skill_selection(
        self,
        *,
        messages: list[dict[str, Any]],
        purpose: str,
        policy: Mapping[str, Any],
        escalation_reason: str | None = None,
    ) -> tuple[list[dict[str, Any]], Any]:
        selected = select_skills_for_purpose(
            purpose,
            policy=policy,
            escalation_reason=escalation_reason,
        )
        updated_messages = [
            dict(message) if isinstance(message, Mapping) else message
            for message in (messages or [])
        ]
        if selected.preserve_full_prompt:
            return updated_messages, selected

        compact_prompt = build_skill_prompt(selected).strip()
        if not compact_prompt:
            return updated_messages, selected

        for message in updated_messages:
            if isinstance(message, dict) and str(message.get("role") or "") == "system":
                message["content"] = compact_prompt
                return updated_messages, selected

        updated_messages.insert(0, {"role": "system", "content": compact_prompt})
        return updated_messages, selected

    def _apply_prompt_pack(
        self,
        *,
        messages: list[dict[str, Any]],
        purpose: str,
        metadata: Mapping[str, Any],
        skills_loaded: list[str],
        skill_levels: list[str],
        output_schema: Any,
    ) -> tuple[list[dict[str, Any]], dict[str, Any] | None]:
        if purpose not in {"step_plan_normalizer", "plan_diff_editor", "recovery_diagnoser"}:
            return messages, None

        if purpose == "step_plan_normalizer":
            prompt_context = build_step_plan_normalizer_dynamic_context(
                messages=messages,
                metadata=metadata,
                skills_loaded=skills_loaded,
                skill_levels=skill_levels,
                output_schema=output_schema if isinstance(output_schema, Mapping) else {},
            )
        elif purpose == "plan_diff_editor":
            prompt_context = build_plan_diff_editor_dynamic_context(
                messages=messages,
                active_plan_state=_value(metadata, "active_plan_state", default=None) if isinstance(metadata, Mapping) else None,
                correction_state=_value(metadata, "correction_state", default=None) if isinstance(metadata, Mapping) else None,
                validation_feedback=str(_value(metadata, "validation_feedback", default="") or "").strip() or None,
                allowed_edit_policy=str(_value(metadata, "allowed_edit_policy", default="") or "").strip() or None,
                validated_locators=_normalize_names(_value(metadata, "validated_locators", default=None)),
            )
        else:
            prompt_context = build_recovery_diagnoser_dynamic_context(
                messages=messages,
                metadata=metadata,
                failed_step_state=_value(metadata, "failed_step_state", default=None) if isinstance(metadata, Mapping) else None,
                failed_step_id=str(_value(metadata, "failed_step_id", default="") or "").strip() or None,
                failed_operation_id=str(_value(metadata, "failed_operation_id", default="") or "").strip() or None,
                error_summary=str(_value(metadata, "error_summary", default="") or "").strip() or None,
                current_page=str(_value(metadata, "current_page", default="") or "").strip() or None,
                tried_fixes=_value(metadata, "tried_fixes", default=None),
                failure_evidence=_value(metadata, "failure_evidence", default=None),
                user_recovery_instruction=str(_value(metadata, "user_recovery_instruction", default="") or "").strip() or None,
                retry_attempts=_value(metadata, "retry_attempts", default=None),
                run_id=str(_value(metadata, "run_id", default="") or "").strip() or None,
            )
        prompt_pack = build_prompt_pack(
            purpose,
            dynamic_context=prompt_context,
            skills_loaded=skills_loaded,
            skill_levels=skill_levels,
        )
        updated_messages, prompt_pack_metadata = apply_prompt_pack_to_messages(
            messages,
            prompt_pack,
            dynamic_context=prompt_context,
        )
        prompt_pack_metadata.update(
            {
                "prompt_pack_id": prompt_pack.prompt_pack_id,
                "prompt_pack_version": prompt_pack.prompt_pack_version,
                "prefix_hash": prompt_pack.prefix_hash,
                "estimated_stable_tokens": prompt_pack.estimated_stable_tokens,
            }
        )
        return updated_messages, prompt_pack_metadata

    def _apply_prompt_pack_result_metadata(
        self,
        result: dict[str, Any],
        prompt_pack_metadata: Mapping[str, Any] | None,
        *,
        estimated_total_input_tokens: int | None = None,
    ) -> dict[str, Any]:
        if not prompt_pack_metadata:
            return result

        prompt_pack_fields = {
            "prompt_pack_id": prompt_pack_metadata.get("prompt_pack_id"),
            "prompt_pack_version": prompt_pack_metadata.get("prompt_pack_version"),
            "prefix_hash": prompt_pack_metadata.get("prefix_hash"),
            "system_prompt_tokens": prompt_pack_metadata.get("system_prompt_tokens"),
            "estimated_message_tokens": prompt_pack_metadata.get("estimated_message_tokens"),
            "estimated_total_input_tokens": (
                estimated_total_input_tokens
                if estimated_total_input_tokens is not None
                else result.get("estimated_input_tokens")
            ),
            "prompt_pack_applied": bool(prompt_pack_metadata.get("prompt_pack_applied")),
            "estimated_stable_tokens": prompt_pack_metadata.get("estimated_stable_tokens"),
        }
        result.update({key: value for key, value in prompt_pack_fields.items() if value is not None})
        telemetry_fields = dict(result.get("telemetry_fields") or {})
        telemetry_fields.update({key: value for key, value in prompt_pack_fields.items() if value is not None})
        result["telemetry_fields"] = telemetry_fields
        return result

    def _tool_names_for_phase(self, policy: Mapping[str, Any], phase: str | None) -> list[str]:
        tool_policy = _value(policy, "tool_policy", "tools_policy", default={})
        if not isinstance(tool_policy, Mapping):
            return []
        allowed_tools_by_phase = _value(
            tool_policy,
            "allowed_tools_by_phase",
            "phase_tools",
            "phase_allowlist",
            default={},
        )
        if not isinstance(allowed_tools_by_phase, Mapping):
            return []
        normalized_phase = str(phase or "").strip().lower() or "planning"
        phase_tools = allowed_tools_by_phase.get(normalized_phase)
        if phase_tools is None and normalized_phase == "planning":
            phase_tools = allowed_tools_by_phase.get("plan_review")
        return _normalize_names(phase_tools)

    def _prepare_messages(
        self,
        *,
        context_manager: Any | None,
        messages: list[dict[str, Any]] | None,
        purpose: str,
        phase: str | None,
        context_mode: str | None,
        policy: Mapping[str, Any],
        run_id: str | None = None,
        step_id: str | None = None,
    ) -> tuple[list[dict[str, Any]], dict[str, Any], str, int]:
        copied_messages = [dict(message) if isinstance(message, Mapping) else message for message in (messages or [])]
        context_policy = _value(policy, "context_policy", "context", default={})
        context_level = str(
            _value(context_policy, "context_level", "level", "mode", "context_mode", default="compact")
        )
        effective_context_mode = str(context_mode or _value(context_policy, "context_mode", default="compact"))
        metadata = {
            "purpose": purpose,
            "phase": phase or "planning",
            "context_level": context_level,
            "context_mode": effective_context_mode,
            "policy_id": _value(policy, "purpose_id", "purpose", default=purpose),
        }

        if context_manager is None:
            return copied_messages, metadata, effective_context_mode, estimate_messages_tokens(copied_messages)

        prepare = _call_if_available(
            context_manager,
            "prepare_messages",
            "prepare_context",
            "build_context",
            "build_messages",
            messages=copied_messages,
            purpose=purpose,
            run_id=run_id,
            step_id=step_id,
            context_mode=effective_context_mode,
            metadata=metadata,
        )
        if prepare is None:
            return copied_messages, metadata, effective_context_mode, estimate_messages_tokens(copied_messages)

        if inspect.isawaitable(prepare):
            raise TypeError("context manager returned awaitable from synchronous helper")

        prepared_messages = _value(prepare, "messages", default=copied_messages)
        prepared_metadata = _value(prepare, "metadata", default=metadata)
        prepared_context_mode = str(_value(prepare, "context_mode", default=effective_context_mode))
        prepared_token_count = int(
            _value(prepare, "estimated_message_tokens", "final_estimated_tokens", default=estimate_messages_tokens(prepared_messages or []))
        )

        if not isinstance(prepared_messages, list):
            prepared_messages = copied_messages
        if not isinstance(prepared_metadata, Mapping):
            prepared_metadata = metadata

        return list(prepared_messages), dict(prepared_metadata), prepared_context_mode, prepared_token_count

    def _analyze_skills(
        self,
        *,
        skill_manager: Any | None,
        skill_entries: list[tuple[str, str]],
        loaded_skill_names: list[str],
    ) -> tuple[list[str], int]:
        if skill_manager is None or not loaded_skill_names:
            return list(loaded_skill_names), len(loaded_skill_names)

        skill_descriptors = [{"name": name, "content": content} for name, content in (skill_entries or [])]
        analyze = _call_if_available(
            skill_manager,
            "analyze",
            skills=skill_descriptors,
            loaded_skill_names=loaded_skill_names,
        )
        if inspect.isawaitable(analyze):
            raise TypeError("skill manager returned awaitable from synchronous helper")

        if analyze is None:
            return list(loaded_skill_names), len(loaded_skill_names)

        loaded_names = _value(analyze, "loaded_skill_names", default=loaded_skill_names)
        if not isinstance(loaded_names, list):
            loaded_names = _normalize_names(loaded_names)
        skill_count = int(_value(analyze, "skill_count", default=len(loaded_names)))
        return loaded_names, skill_count

    def _filter_tools_for_phase(
        self,
        *,
        tool_registry: Any | None,
        tools: Any | None,
        phase: str | None,
        policy: Mapping[str, Any],
    ) -> list[Any]:
        if tools is None:
            return []

        normalized_tools = list(tools) if isinstance(tools, Sequence) and not isinstance(tools, str) else [tools]
        filtered_tools = normalized_tools

        filter_func = _value(tool_registry, "filter_tools_for_phase", default=None) if tool_registry is not None else None
        if callable(filter_func):
            filtered_tools = list(filter_func(normalized_tools, phase or "planning"))

        allowed_names = set(self._tool_names_for_phase(policy, phase))
        if not allowed_names:
            return []

        final_tools: list[Any] = []
        for index, tool in enumerate(filtered_tools):
            tool_name = _tool_name(tool, index)
            if tool_name in allowed_names:
                final_tools.append(tool)
        return final_tools

    def _emit_telemetry(
        self,
        telemetry_sink: Any | None,
        telemetry_record: ControllerTelemetry,
        prompt_pack_metadata: Mapping[str, Any] | None = None,
    ) -> None:
        if telemetry_sink is None:
            return

        payload = {
            "call_id": telemetry_record.call_id,
            "purpose": telemetry_record.purpose,
            "model": telemetry_record.model,
            "skill_count": telemetry_record.skill_count,
            "skills_loaded": list(telemetry_record.skills_loaded),
            "skill_levels": list(telemetry_record.skill_levels),
            "tool_count": telemetry_record.tool_count,
            "tools_exposed_count": telemetry_record.tools_exposed_count,
            "context_mode": telemetry_record.context_mode,
            "context_level": telemetry_record.context_level,
            "token_budget": telemetry_record.token_budget,
            "estimated_input_tokens": telemetry_record.estimated_input_tokens,
            "estimated_output_tokens": telemetry_record.estimated_output_tokens,
            "retry_count": telemetry_record.retry_count,
            "validation_status": telemetry_record.validation_status,
            "latency_ms": telemetry_record.latency_ms,
            "schema_id": telemetry_record.schema_id,
            "schema_version": telemetry_record.schema_version,
            "error_code": telemetry_record.error_code,
        }
        if isinstance(prompt_pack_metadata, Mapping):
            for key in (
                "prompt_pack_id",
                "prompt_pack_version",
                "prefix_hash",
                "estimated_stable_tokens",
                "prompt_pack_applied",
            ):
                value = prompt_pack_metadata.get(key)
                if value is not None:
                    payload[key] = value

        for method_name in ("record", "emit", "log", "record_call"):
            method = getattr(telemetry_sink, method_name, None)
            if callable(method):
                method(**payload)
                return

    def _build_result(
        self,
        *,
        purpose: str,
        policy: Mapping[str, Any],
        model: str,
        model_called: bool,
        validation_status: str,
        retry_count: int,
        parsed_output: Any = None,
        errors: list[Any] | None = None,
        backend_applied: bool = False,
        skill_count: int = 0,
        tool_count: int = 0,
        tools_exposed_count: int | None = None,
        skills_loaded: list[str] | None = None,
        skill_levels: list[str] | None = None,
        context_mode: str = "compact",
        context_level: str = "compact",
        token_budget: int = 0,
        call_id: str = "llm_unknown",
        estimated_input_tokens: int = 0,
        estimated_output_tokens: int | None = None,
        latency_ms: int = 0,
        schema_id: str | None = None,
        schema_version: int | None = None,
        error_code: str | None = None,
    ) -> dict[str, Any]:
        normalized_skills_loaded = list(skills_loaded or [])
        normalized_skill_levels = list(skill_levels or [])
        normalized_tools_exposed_count = int(
            tool_count if tools_exposed_count is None else tools_exposed_count
        )
        normalized_schema_id = str(
            schema_id
            or _value(_value(policy, "output_schema", default={}), "schema_id", default=f"{purpose}.v1")
        )
        normalized_schema_version = int(
            schema_version
            or _value(_value(policy, "output_schema", default={}), "schema_version", default=1)
            or 1
        )
        return {
            "call_id": call_id,
            "purpose": purpose,
            "purpose_id": _value(policy, "purpose_id", "purpose", default=purpose),
            "schema_id": normalized_schema_id,
            "schema_version": normalized_schema_version,
            "model": model,
            "used_model": model,
            "model_called": model_called,
            "llm_called": model_called,
            "call_model": model_called,
            "validation_status": validation_status,
            "status": validation_status,
            "result": validation_status,
            "retry_count": retry_count,
            "backend_applied": backend_applied,
            "mutated_runtime": backend_applied,
            "applied": backend_applied,
            "parsed_output": parsed_output,
            "errors": list(errors or []),
            "skill_count": skill_count,
            "tool_count": tool_count,
            "tools_exposed_count": normalized_tools_exposed_count,
            "skills_loaded": normalized_skills_loaded,
            "skill_levels": normalized_skill_levels,
            "context_mode": context_mode,
            "context_level": context_level,
            "token_budget": token_budget,
            "estimated_input_tokens": estimated_input_tokens,
            "estimated_output_tokens": estimated_output_tokens,
            "error_code": error_code,
            "telemetry_fields": {
                "call_id": call_id,
                "purpose": purpose,
                "model": model,
                "skill_count": skill_count,
                "skills_loaded": normalized_skills_loaded,
                "skill_levels": normalized_skill_levels,
                "tool_count": tool_count,
                "tools_exposed_count": normalized_tools_exposed_count,
                "context_mode": context_mode,
                "context_level": context_level,
                "token_budget": token_budget,
                "estimated_input_tokens": estimated_input_tokens,
                "estimated_output_tokens": estimated_output_tokens,
                "retry_count": retry_count,
                "validation_status": validation_status,
                "latency_ms": latency_ms,
                "schema_id": normalized_schema_id,
                "schema_version": normalized_schema_version,
                "error_code": error_code,
            },
        }

    async def _call_model(
        self,
        *,
        purpose: str,
        model: str,
        messages: list[dict[str, Any]],
        tools: list[Any] | None,
        tool_choice: Any = None,
        client: Any | None,
    ) -> Any:
        if client is None:
            if purpose == "main_orchestrator" and self.model_router is not None:
                router_call = getattr(self.model_router, "call", None)
                if callable(router_call):
                    response = router_call(
                        purpose=purpose,
                        client=self.model_client,
                        model=model,
                        messages=messages,
                        tools=tools,
                        tool_choice=tool_choice,
                    )
                    return await _maybe_await(response)
            raise ValueError(f"No model client available for purpose {purpose!r}")

        chat = getattr(client, "chat", None)
        completions = getattr(chat, "completions", None)
        create = getattr(completions, "create", None)
        if not callable(create):
            raise TypeError("model client does not expose chat.completions.create")

        response = create(model=model, messages=messages, tools=tools, tool_choice=tool_choice)
        return await _maybe_await(response)

    def _validate_response(
        self,
        *,
        schema_validator: Any,
        raw_output: Any,
        purpose: str,
        output_schema: Any,
        retry_count: int,
        phase: str | None,
        context_mode: str,
    ) -> dict[str, Any]:
        validate = _call_if_available(
            schema_validator,
            "validate",
            "validate_output",
            "check",
            raw_output=raw_output,
            output=raw_output,
            response=raw_output,
            purpose=purpose,
            output_schema=output_schema,
            schema=output_schema,
            schema_id=_value(output_schema, "schema_id", default=output_schema if isinstance(output_schema, str) else None),
            retry_count=retry_count,
            phase=phase,
            context_mode=context_mode,
        )
        if inspect.isawaitable(validate):
            raise TypeError("schema validator returned awaitable from synchronous helper")
        if validate is None:
            validate = schema_validator(
                raw_output=raw_output,
                purpose=purpose,
                output_schema=output_schema,
                schema_id=_value(output_schema, "schema_id", default=output_schema if isinstance(output_schema, str) else None),
                retry_count=retry_count,
                phase=phase,
                context_mode=context_mode,
            )
            if inspect.isawaitable(validate):
                raise TypeError("schema validator returned awaitable from synchronous helper")

        if not isinstance(validate, Mapping):
            return {
                "ok": bool(validate),
                "validation_status": "valid" if validate else "invalid",
                "errors": [] if validate else ["schema_validation_failed"],
                "parsed_output": raw_output if validate else None,
            }
        return dict(validate)

    async def call(
        self,
        *,
        purpose: str,
        messages: list[dict[str, Any]] | None = None,
        model: str | None = None,
        phase: str | None = None,
        context_mode: str | None = None,
        deterministic_safe: bool = False,
        deterministic_reason: str | None = None,
        runtime_state: Any = None,
        client: Any | None = None,
        model_client: Any | None = None,
        llm_client: Any | None = None,
        openai_client: Any | None = None,
        model_router: Any | None = None,
        context_manager: Any | None = None,
        skill_manager: Any | None = None,
        tool_registry: Any | None = None,
        telemetry: Any | None = None,
        telemetry_sink: Any | None = None,
        schema_validator: Any | None = None,
        validator: Any | None = None,
        policy: Any | None = None,
        purpose_policy: Any | None = None,
        output_schema: Any | None = None,
        retry_policy: Any | None = None,
        tool_policy: Any | None = None,
        skill_policy: Any | None = None,
        context_policy: Any | None = None,
        tools: Any | None = None,
        tool_choice: Any | None = None,
        run_id: str | None = None,
        step_id: str | None = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        del kwargs
        del telemetry
        del tool_policy
        del skill_policy
        del context_policy

        resolved_policy = self.resolve_purpose_policy(
            purpose,
            policy=policy,
            purpose_policy=purpose_policy,
        )
        normalized_purpose = str(_value(resolved_policy, "purpose_id", "purpose", default=purpose))
        if normalized_purpose not in self.purpose_registry:
            raise ValueError(f"Unknown LLM purpose: {normalized_purpose!r}")

        resolved_context_manager = self._select_context_manager(context_manager)
        resolved_skill_manager = self._select_skill_manager(skill_manager)
        resolved_tool_registry = self._select_tool_registry(tool_registry)
        resolved_telemetry_sink = self._select_telemetry_sink(telemetry_sink)
        resolved_validator = self._select_validator(schema_validator)
        resolved_client = self._select_model_client(client, model_client, llm_client, openai_client)
        if resolved_client is None and model_router is not None:
            # Keep the fallback explicit: the current router is only a compatibility path
            # and should not become a new broad routing surface.
            self.model_router = model_router
            if normalized_purpose == "main_orchestrator":
                resolved_client = None

        resolved_model = str(model or _value(resolved_policy, "model", "model_class", default="unknown"))
        token_budget = int(_value(resolved_policy, "token_budget", "budget", default=0) or 0)
        context_policy_value = _value(resolved_policy, "context_policy", "context", default={})
        context_level = str(_value(context_policy_value, "context_level", "level", "mode", "context_mode", default="compact"))
        output_schema_value = output_schema or _value(resolved_policy, "output_schema", default={})
        schema_id = str(
            _value(
                output_schema_value,
                "schema_id",
                default=output_schema_value if isinstance(output_schema_value, str) else f"{normalized_purpose}.v1",
            )
        )
        schema_version = int(_value(output_schema_value, "schema_version", default=1) or 1)
        call_id = f"{normalized_purpose}-{time.time_ns()}"

        started_at = time.perf_counter()
        if deterministic_safe:
            deterministic_input_tokens = estimate_messages_tokens(messages or [])
            result = self._build_result(
                purpose=normalized_purpose,
                policy=resolved_policy,
                model=resolved_model,
                model_called=False,
                validation_status="deterministic",
                retry_count=0,
                parsed_output={
                    "purpose": normalized_purpose,
                    "deterministic_reason": deterministic_reason,
                    "deterministic_safe": True,
                },
                backend_applied=False,
                skill_count=0,
                tool_count=0,
                tools_exposed_count=0,
                skills_loaded=[],
                skill_levels=[],
                context_mode=str(context_mode or _value(context_policy_value, "context_mode", default="compact")),
                context_level=context_level,
                token_budget=token_budget,
                call_id=call_id,
                estimated_input_tokens=deterministic_input_tokens,
                estimated_output_tokens=None,
                latency_ms=max(0, int((time.perf_counter() - started_at) * 1000)),
                schema_id=schema_id,
                schema_version=schema_version,
                error_code=None,
            )
            self._emit_telemetry(
                resolved_telemetry_sink,
                ControllerTelemetry(
                    call_id=call_id,
                    purpose=normalized_purpose,
                    model=resolved_model,
                    skill_count=0,
                    skills_loaded=[],
                    skill_levels=[],
                    tool_count=0,
                    tools_exposed_count=0,
                    context_mode=str(context_mode or _value(context_policy_value, "context_mode", default="compact")),
                    context_level=context_level,
                    token_budget=token_budget,
                    estimated_input_tokens=deterministic_input_tokens,
                    estimated_output_tokens=None,
                    retry_count=0,
                    validation_status="deterministic",
                    latency_ms=max(0, int((time.perf_counter() - started_at) * 1000)),
                    schema_id=schema_id,
                    schema_version=schema_version,
                    error_code=None,
                ),
                None,
            )
            return result

        prepared_messages, prepared_metadata, effective_context_mode, estimated_message_tokens = self._prepare_messages(
            context_manager=resolved_context_manager,
            messages=messages,
            purpose=normalized_purpose,
            phase=phase,
            context_mode=context_mode,
            policy=resolved_policy,
            run_id=run_id,
            step_id=step_id,
        )
        original_prepared_messages = [
            dict(message) if isinstance(message, Mapping) else message
            for message in prepared_messages
        ]
        prepared_messages, skill_selection = self._apply_skill_selection(
            messages=original_prepared_messages,
            purpose=normalized_purpose,
            policy=resolved_policy,
        )
        prepared_messages, prompt_pack_metadata = self._apply_prompt_pack(
            messages=prepared_messages,
            purpose=normalized_purpose,
            metadata=prepared_metadata,
            skills_loaded=list(getattr(skill_selection, "loaded_skill_names", [])),
            skill_levels=list(getattr(skill_selection, "skill_levels", [])),
            output_schema=output_schema_value,
        )
        if prompt_pack_metadata is not None:
            prepared_metadata = dict(prepared_metadata)
            prepared_metadata.update(prompt_pack_metadata)
        estimated_message_tokens = estimate_messages_tokens(prepared_messages)
        loaded_skill_names, skill_count = self._analyze_skills(
            skill_manager=resolved_skill_manager,
            skill_entries=list(getattr(skill_selection, "skill_entries", [])),
            loaded_skill_names=list(getattr(skill_selection, "loaded_skill_names", [])),
        )
        skill_levels = list(getattr(skill_selection, "skill_levels", []))
        effective_context_mode = str(
            prepared_metadata.get("context_mode") or effective_context_mode or context_mode or "compact"
        )

        exposed_tools = self._filter_tools_for_phase(
            tool_registry=resolved_tool_registry,
            tools=tools,
            phase=phase,
            policy=resolved_policy,
        )
        tool_count = len(exposed_tools)
        estimated_input_tokens = int(
            _value(prepared_metadata, "final_estimated_tokens", "estimated_message_tokens", default=estimated_message_tokens)
            or estimated_message_tokens
            or 0
        ) + estimate_tools_tokens(exposed_tools)

        retry_policy_value = retry_policy
        if retry_policy_value is None:
            retry_policy_value = _value(resolved_policy, "retry_policy", "fallback", default={})
        schema_retry_limit = int(
            _value(
                retry_policy_value,
                "schema_retry_limit",
                "retry_limit",
                "retry_count",
                default=1,
            )
            or 1
        )
        max_attempts = max(1, schema_retry_limit + 1)
        schema_validator_obj = resolved_validator
        schema_validation = {}
        parsed_output: Any = None
        validation_status = "invalid"
        errors: list[Any] = []
        model_called = False

        if token_budget and estimated_input_tokens > token_budget:
            failure_result = self._build_result(
                purpose=normalized_purpose,
                policy=resolved_policy,
                model=resolved_model,
                model_called=False,
                validation_status="budget_exceeded",
                retry_count=0,
                parsed_output=None,
                errors=["TOKEN_BUDGET_EXCEEDED"],
                backend_applied=False,
                skill_count=skill_count if skill_count else len(loaded_skill_names),
                tool_count=tool_count,
                tools_exposed_count=tool_count,
                skills_loaded=loaded_skill_names,
                skill_levels=skill_levels,
                context_mode=effective_context_mode,
                context_level=context_level,
                token_budget=token_budget,
                call_id=call_id,
                estimated_input_tokens=estimated_input_tokens,
                estimated_output_tokens=None,
                latency_ms=max(0, int((time.perf_counter() - started_at) * 1000)),
                schema_id=schema_id,
                schema_version=schema_version,
                error_code="TOKEN_BUDGET_EXCEEDED",
            )
            failure_result = self._apply_prompt_pack_result_metadata(
                failure_result,
                prompt_pack_metadata,
                estimated_total_input_tokens=estimated_input_tokens,
            )
            self._emit_telemetry(
                resolved_telemetry_sink,
                ControllerTelemetry(
                    call_id=call_id,
                    purpose=normalized_purpose,
                    model=resolved_model,
                    skill_count=failure_result["skill_count"],
                    skills_loaded=list(loaded_skill_names),
                    skill_levels=list(skill_levels),
                    tool_count=tool_count,
                    tools_exposed_count=tool_count,
                    context_mode=effective_context_mode,
                    context_level=context_level,
                    token_budget=token_budget,
                    estimated_input_tokens=estimated_input_tokens,
                    estimated_output_tokens=None,
                    retry_count=0,
                    validation_status="budget_exceeded",
                    latency_ms=failure_result["telemetry_fields"]["latency_ms"],
                    schema_id=schema_id,
                    schema_version=schema_version,
                    error_code="TOKEN_BUDGET_EXCEEDED",
                ),
                prompt_pack_metadata,
            )
            return failure_result

        for attempt_index in range(max_attempts):
            if attempt_index > 0:
                attempt_base_messages, retry_skill_selection = self._apply_skill_selection(
                    messages=original_prepared_messages,
                    purpose=normalized_purpose,
                    policy=resolved_policy,
                    escalation_reason="schema_retry",
                )
                attempt_skill_levels = list(getattr(retry_skill_selection, "skill_levels", []))
                retry_note = {
                    "role": "system",
                    "content": (
                        "Previous output failed schema validation. "
                        "Return only the structured response for the declared schema."
                    ),
                }
                attempt_messages = list(attempt_base_messages) + [retry_note]
            else:
                attempt_messages = list(prepared_messages)
                attempt_skill_levels = list(skill_levels)

            response = await self._call_model(
                purpose=normalized_purpose,
                model=resolved_model,
                messages=attempt_messages,
                tools=exposed_tools or None,
                tool_choice=tool_choice,
                client=resolved_client,
            )
            model_called = True
            raw_output = _content_from_response(response)
            schema_validation = self._validate_response(
                schema_validator=schema_validator_obj,
                raw_output=raw_output,
                purpose=normalized_purpose,
                output_schema=output_schema or _value(resolved_policy, "output_schema", default={}),
                retry_count=attempt_index,
                phase=phase,
                context_mode=effective_context_mode,
            )
            validation_status = str(
                _value(
                    schema_validation,
                    "validation_status",
                    "status",
                    "result",
                    default="valid" if _value(schema_validation, "ok", default=False) else "invalid",
                )
            )
            if validation_status == "valid" or bool(_value(schema_validation, "ok", default=False)):
                parsed_output = _value(schema_validation, "parsed_output", default=raw_output)
                result = self._build_result(
                    purpose=normalized_purpose,
                    policy=resolved_policy,
                    model=resolved_model,
                    model_called=True,
                    validation_status="valid",
                    retry_count=attempt_index,
                    parsed_output=parsed_output,
                    errors=list(_value(schema_validation, "errors", default=[])),
                    backend_applied=False,
                    skill_count=skill_count if skill_count else len(loaded_skill_names),
                    tool_count=tool_count,
                    tools_exposed_count=tool_count,
                    skills_loaded=loaded_skill_names,
                    skill_levels=attempt_skill_levels,
                    context_mode=effective_context_mode,
                    context_level=context_level,
                    token_budget=token_budget,
                    call_id=call_id,
                    estimated_input_tokens=estimated_input_tokens,
                    estimated_output_tokens=None,
                    latency_ms=max(0, int((time.perf_counter() - started_at) * 1000)),
                    schema_id=schema_id,
                    schema_version=schema_version,
                    error_code=None,
                )
                result = self._apply_prompt_pack_result_metadata(
                    result,
                    prompt_pack_metadata,
                    estimated_total_input_tokens=estimated_input_tokens,
                )
                self._emit_telemetry(
                    resolved_telemetry_sink,
                    ControllerTelemetry(
                        call_id=call_id,
                        purpose=normalized_purpose,
                        model=resolved_model,
                        skill_count=result["skill_count"],
                        skills_loaded=list(loaded_skill_names),
                        skill_levels=list(attempt_skill_levels),
                        tool_count=tool_count,
                        tools_exposed_count=tool_count,
                        context_mode=effective_context_mode,
                        context_level=context_level,
                        token_budget=token_budget,
                        estimated_input_tokens=estimated_input_tokens,
                        estimated_output_tokens=None,
                        retry_count=attempt_index,
                        validation_status="valid",
                        latency_ms=result["telemetry_fields"]["latency_ms"],
                        schema_id=schema_id,
                        schema_version=schema_version,
                        error_code=None,
                    ),
                    prompt_pack_metadata,
                )
                return result

            errors = list(_value(schema_validation, "errors", default=[]))
            if attempt_index < max_attempts - 1:
                continue

        failure_result = self._build_result(
            purpose=normalized_purpose,
            policy=resolved_policy,
            model=resolved_model,
            model_called=model_called,
            validation_status="retry_failed",
            retry_count=max_attempts - 1,
            parsed_output=None,
            errors=errors or list(_value(schema_validation, "errors", default=[])),
            backend_applied=False,
            skill_count=skill_count if skill_count else len(loaded_skill_names),
            tool_count=tool_count,
            tools_exposed_count=tool_count,
            skills_loaded=loaded_skill_names,
            skill_levels=skill_levels,
            context_mode=effective_context_mode,
            context_level=context_level,
            token_budget=token_budget,
            call_id=call_id,
            estimated_input_tokens=estimated_input_tokens,
            estimated_output_tokens=None,
            latency_ms=max(0, int((time.perf_counter() - started_at) * 1000)),
            schema_id=schema_id,
            schema_version=schema_version,
            error_code="SCHEMA_RETRY_FAILED",
        )
        failure_result = self._apply_prompt_pack_result_metadata(
            failure_result,
            prompt_pack_metadata,
            estimated_total_input_tokens=estimated_input_tokens,
        )
        self._emit_telemetry(
            resolved_telemetry_sink,
            ControllerTelemetry(
                call_id=call_id,
                purpose=normalized_purpose,
                model=resolved_model,
                skill_count=failure_result["skill_count"],
                skills_loaded=list(loaded_skill_names),
                skill_levels=list(skill_levels),
                tool_count=tool_count,
                tools_exposed_count=tool_count,
                context_mode=effective_context_mode,
                context_level=context_level,
                token_budget=token_budget,
                estimated_input_tokens=estimated_input_tokens,
                estimated_output_tokens=None,
                retry_count=max_attempts - 1,
                validation_status="retry_failed",
                latency_ms=failure_result["telemetry_fields"]["latency_ms"],
                schema_id=schema_id,
                schema_version=schema_version,
                error_code="SCHEMA_RETRY_FAILED",
            ),
            prompt_pack_metadata,
        )
        return failure_result

    async def call_with_raw_response(
        self,
        *,
        purpose: str,
        messages: list[dict[str, Any]] | None = None,
        model: str | None = None,
        phase: str | None = None,
        context_mode: str | None = None,
        deterministic_safe: bool = False,
        deterministic_reason: str | None = None,
        runtime_state: Any = None,
        client: Any | None = None,
        model_client: Any | None = None,
        llm_client: Any | None = None,
        openai_client: Any | None = None,
        model_router: Any | None = None,
        context_manager: Any | None = None,
        skill_manager: Any | None = None,
        tool_registry: Any | None = None,
        telemetry: Any | None = None,
        telemetry_sink: Any | None = None,
        schema_validator: Any | None = None,
        validator: Any | None = None,
        policy: Any | None = None,
        purpose_policy: Any | None = None,
        output_schema: Any | None = None,
        retry_policy: Any | None = None,
        tool_policy: Any | None = None,
        skill_policy: Any | None = None,
        context_policy: Any | None = None,
        tools: Any | None = None,
        tool_choice: Any | None = None,
        run_id: str | None = None,
        step_id: str | None = None,
        **kwargs: Any,
    ) -> dict[str, Any]:
        del kwargs
        del telemetry
        del schema_validator
        del validator
        del output_schema
        del retry_policy
        del tool_policy
        del skill_policy
        del context_policy
        del runtime_state

        resolved_policy = self.resolve_purpose_policy(
            purpose,
            policy=policy,
            purpose_policy=purpose_policy,
        )
        normalized_purpose = str(_value(resolved_policy, "purpose_id", "purpose", default=purpose))
        if normalized_purpose not in self.purpose_registry:
            raise ValueError(f"Unknown LLM purpose: {normalized_purpose!r}")

        resolved_context_manager = self._select_context_manager(context_manager)
        resolved_skill_manager = self._select_skill_manager(skill_manager)
        resolved_tool_registry = self._select_tool_registry(tool_registry)
        resolved_telemetry_sink = self._select_telemetry_sink(telemetry_sink)
        resolved_client = self._select_model_client(client, model_client, llm_client, openai_client)
        if resolved_client is None and model_router is not None:
            self.model_router = model_router
            if normalized_purpose == "main_orchestrator":
                resolved_client = None

        resolved_model = str(model or _value(resolved_policy, "model", "model_class", default="unknown"))
        token_budget = int(_value(resolved_policy, "token_budget", "budget", default=0) or 0)
        context_policy_value = _value(resolved_policy, "context_policy", "context", default={})
        context_level = str(_value(context_policy_value, "context_level", "level", "mode", "context_mode", default="compact"))
        output_schema_value = _value(resolved_policy, "output_schema", default={})
        schema_id = str(
            _value(
                output_schema_value,
                "schema_id",
                default=output_schema_value if isinstance(output_schema_value, str) else f"{normalized_purpose}.v1",
            )
        )
        schema_version = int(_value(output_schema_value, "schema_version", default=1) or 1)
        call_id = f"{normalized_purpose}-{time.time_ns()}"

        started_at = time.perf_counter()
        if deterministic_safe:
            deterministic_input_tokens = estimate_messages_tokens(messages or [])
            result = self._build_result(
                purpose=normalized_purpose,
                policy=resolved_policy,
                model=resolved_model,
                model_called=False,
                validation_status="deterministic",
                retry_count=0,
                parsed_output={
                    "purpose": normalized_purpose,
                    "deterministic_reason": deterministic_reason,
                    "deterministic_safe": True,
                },
                backend_applied=False,
                skill_count=0,
                tool_count=0,
                tools_exposed_count=0,
                skills_loaded=[],
                skill_levels=[],
                context_mode=str(context_mode or _value(context_policy_value, "context_mode", default="compact")),
                context_level=context_level,
                token_budget=token_budget,
                call_id=call_id,
                estimated_input_tokens=deterministic_input_tokens,
                estimated_output_tokens=None,
                latency_ms=max(0, int((time.perf_counter() - started_at) * 1000)),
                schema_id=schema_id,
                schema_version=schema_version,
                error_code=None,
            )
            result["raw_response"] = None
            result["raw_message"] = None
            result["content"] = None
            result["tool_calls"] = []
            self._emit_telemetry(
                resolved_telemetry_sink,
                ControllerTelemetry(
                    call_id=call_id,
                    purpose=normalized_purpose,
                    model=resolved_model,
                    skill_count=0,
                    skills_loaded=[],
                    skill_levels=[],
                    tool_count=0,
                    tools_exposed_count=0,
                    context_mode=str(context_mode or _value(context_policy_value, "context_mode", default="compact")),
                    context_level=context_level,
                    token_budget=token_budget,
                    estimated_input_tokens=deterministic_input_tokens,
                    estimated_output_tokens=None,
                    retry_count=0,
                    validation_status="deterministic",
                    latency_ms=max(0, int((time.perf_counter() - started_at) * 1000)),
                    schema_id=schema_id,
                    schema_version=schema_version,
                    error_code=None,
                ),
            )
            return result

        prepared_messages, prepared_metadata, effective_context_mode, estimated_message_tokens = self._prepare_messages(
            context_manager=resolved_context_manager,
            messages=messages,
            purpose=normalized_purpose,
            phase=phase,
            context_mode=context_mode,
            policy=resolved_policy,
            run_id=run_id,
            step_id=step_id,
        )
        prepared_messages, skill_selection = self._apply_skill_selection(
            messages=prepared_messages,
            purpose=normalized_purpose,
            policy=resolved_policy,
        )
        prepared_messages, prompt_pack_metadata = self._apply_prompt_pack(
            messages=prepared_messages,
            purpose=normalized_purpose,
            metadata=prepared_metadata,
            skills_loaded=list(getattr(skill_selection, "loaded_skill_names", [])),
            skill_levels=list(getattr(skill_selection, "skill_levels", [])),
            output_schema=output_schema_value,
        )
        if prompt_pack_metadata is not None:
            prepared_metadata = dict(prepared_metadata)
            prepared_metadata.update(prompt_pack_metadata)
        estimated_message_tokens = estimate_messages_tokens(prepared_messages)
        loaded_skill_names, skill_count = self._analyze_skills(
            skill_manager=resolved_skill_manager,
            skill_entries=list(getattr(skill_selection, "skill_entries", [])),
            loaded_skill_names=list(getattr(skill_selection, "loaded_skill_names", [])),
        )
        skill_levels = list(getattr(skill_selection, "skill_levels", []))
        effective_context_mode = str(
            prepared_metadata.get("context_mode") or effective_context_mode or context_mode or "compact"
        )
        exposed_tools = self._filter_tools_for_phase(
            tool_registry=resolved_tool_registry,
            tools=tools,
            phase=phase,
            policy=resolved_policy,
        )
        tool_count = len(exposed_tools)
        estimated_input_tokens = int(
            _value(prepared_metadata, "final_estimated_tokens", "estimated_message_tokens", default=estimated_message_tokens)
            or estimated_message_tokens
            or 0
        ) + estimate_tools_tokens(exposed_tools)

        if token_budget and estimated_input_tokens > token_budget:
            failure_result = self._build_result(
                purpose=normalized_purpose,
                policy=resolved_policy,
                model=resolved_model,
                model_called=False,
                validation_status="budget_exceeded",
                retry_count=0,
                parsed_output=None,
                errors=["TOKEN_BUDGET_EXCEEDED"],
                backend_applied=False,
                skill_count=skill_count if skill_count else len(loaded_skill_names),
                tool_count=tool_count,
                tools_exposed_count=tool_count,
                skills_loaded=loaded_skill_names,
                skill_levels=skill_levels,
                context_mode=effective_context_mode,
                context_level=context_level,
                token_budget=token_budget,
                call_id=call_id,
                estimated_input_tokens=estimated_input_tokens,
                estimated_output_tokens=None,
                latency_ms=max(0, int((time.perf_counter() - started_at) * 1000)),
                schema_id=schema_id,
                schema_version=schema_version,
                error_code="TOKEN_BUDGET_EXCEEDED",
            )
            failure_result = self._apply_prompt_pack_result_metadata(
                failure_result,
                prompt_pack_metadata,
                estimated_total_input_tokens=estimated_input_tokens,
            )
            failure_result["raw_response"] = None
            failure_result["raw_message"] = None
            failure_result["content"] = None
            failure_result["tool_calls"] = []
            self._emit_telemetry(
                resolved_telemetry_sink,
                ControllerTelemetry(
                    call_id=call_id,
                    purpose=normalized_purpose,
                    model=resolved_model,
                    skill_count=failure_result["skill_count"],
                    skills_loaded=list(loaded_skill_names),
                    skill_levels=list(skill_levels),
                    tool_count=tool_count,
                    tools_exposed_count=tool_count,
                    context_mode=effective_context_mode,
                    context_level=context_level,
                    token_budget=token_budget,
                    estimated_input_tokens=estimated_input_tokens,
                    estimated_output_tokens=None,
                    retry_count=0,
                    validation_status="budget_exceeded",
                    latency_ms=failure_result["telemetry_fields"]["latency_ms"],
                    schema_id=schema_id,
                    schema_version=schema_version,
                    error_code="TOKEN_BUDGET_EXCEEDED",
                ),
                prompt_pack_metadata,
            )
            return failure_result

        def _build_call_failure_result(
            *,
            validation_status: str,
            error_code: str,
            error_message: str,
            error_type: str | None = None,
        ) -> dict[str, Any]:
            failure_result = self._build_result(
                purpose=normalized_purpose,
                policy=resolved_policy,
                model=resolved_model,
                model_called=True,
                validation_status=validation_status,
                retry_count=0,
                parsed_output=None,
                errors=[error_type or error_code],
                backend_applied=False,
                skill_count=skill_count if skill_count else len(loaded_skill_names),
                tool_count=tool_count,
                tools_exposed_count=tool_count,
                skills_loaded=loaded_skill_names,
                skill_levels=skill_levels,
                context_mode=effective_context_mode,
                context_level=context_level,
                token_budget=token_budget,
                call_id=call_id,
                estimated_input_tokens=estimated_input_tokens,
                estimated_output_tokens=None,
                latency_ms=max(0, int((time.perf_counter() - started_at) * 1000)),
                schema_id=schema_id,
                schema_version=schema_version,
                error_code=error_code,
            )
            failure_result = self._apply_prompt_pack_result_metadata(
                failure_result,
                prompt_pack_metadata,
                estimated_total_input_tokens=estimated_input_tokens,
            )
            failure_result["raw_response"] = None
            failure_result["raw_message"] = None
            failure_result["content"] = None
            failure_result["tool_calls"] = []
            failure_result["message"] = error_message
            if error_type is not None:
                failure_result["error_type"] = error_type
            self._emit_telemetry(
                resolved_telemetry_sink,
                ControllerTelemetry(
                    call_id=call_id,
                    purpose=normalized_purpose,
                    model=resolved_model,
                    skill_count=failure_result["skill_count"],
                    skills_loaded=list(loaded_skill_names),
                    skill_levels=list(skill_levels),
                    tool_count=tool_count,
                    tools_exposed_count=tool_count,
                    context_mode=effective_context_mode,
                    context_level=context_level,
                    token_budget=token_budget,
                    estimated_input_tokens=estimated_input_tokens,
                    estimated_output_tokens=None,
                    retry_count=0,
                    validation_status=validation_status,
                    latency_ms=failure_result["telemetry_fields"]["latency_ms"],
                    schema_id=schema_id,
                    schema_version=schema_version,
                    error_code=error_code,
                ),
                prompt_pack_metadata,
            )
            return failure_result

        try:
            response = await self._call_model(
                purpose=normalized_purpose,
                model=resolved_model,
                messages=list(prepared_messages),
                tools=exposed_tools or None,
                tool_choice=tool_choice,
                client=resolved_client,
            )
        except Exception as exc:  # noqa: BLE001
            return _build_call_failure_result(
                validation_status="retry_failed",
                error_code="MODEL_CALL_FAILED",
                error_message=str(exc),
                error_type=type(exc).__name__,
            )
        if response is None:
            return _build_call_failure_result(
                validation_status="invalid",
                error_code="EMPTY_MODEL_RESPONSE",
                error_message="model client returned no response",
            )
        message = _message_from_response(response)
        content = _content_from_message(message)
        tool_calls = _tool_calls_from_message(message)
        if tool_calls:
            validation_status = "tool_calls_preserved"
            errors: list[Any] = []
        elif content is None:
            validation_status = "invalid"
            errors = ["missing_message_content"]
        else:
            validation_status = "raw_response_preserved"
            errors = []

        result = self._build_result(
            purpose=normalized_purpose,
            policy=resolved_policy,
            model=resolved_model,
            model_called=True,
            validation_status=validation_status,
            retry_count=0,
            parsed_output=None,
            errors=errors,
            backend_applied=False,
            skill_count=skill_count if skill_count else len(loaded_skill_names),
            tool_count=tool_count,
            tools_exposed_count=tool_count,
            skills_loaded=loaded_skill_names,
            skill_levels=skill_levels,
            context_mode=effective_context_mode,
            context_level=context_level,
            token_budget=token_budget,
            call_id=call_id,
            estimated_input_tokens=estimated_input_tokens,
            estimated_output_tokens=None,
            latency_ms=max(0, int((time.perf_counter() - started_at) * 1000)),
            schema_id=schema_id,
            schema_version=schema_version,
            error_code=None,
        )
        result = self._apply_prompt_pack_result_metadata(
            result,
            prompt_pack_metadata,
            estimated_total_input_tokens=estimated_input_tokens,
        )
        result["raw_response"] = response
        result["raw_message"] = message
        result["content"] = content
        result["tool_calls"] = tool_calls
        self._emit_telemetry(
            resolved_telemetry_sink,
            ControllerTelemetry(
                call_id=call_id,
                purpose=normalized_purpose,
                model=resolved_model,
                skill_count=result["skill_count"],
                skills_loaded=list(loaded_skill_names),
                skill_levels=list(skill_levels),
                tool_count=tool_count,
                tools_exposed_count=tool_count,
                context_mode=effective_context_mode,
                context_level=context_level,
                token_budget=token_budget,
                estimated_input_tokens=estimated_input_tokens,
                estimated_output_tokens=None,
                retry_count=0,
                validation_status=validation_status,
                latency_ms=result["telemetry_fields"]["latency_ms"],
                schema_id=schema_id,
                schema_version=schema_version,
                error_code=None,
            ),
            prompt_pack_metadata,
        )
        return result


def _tool_name(tool: Any, index: int = 0) -> str:
    if isinstance(tool, Mapping):
        function = tool.get("function")
        if isinstance(function, Mapping):
            function_name = function.get("name")
            if function_name:
                return str(function_name)
        name = tool.get("name")
        if name:
            return str(name)
    text = str(tool).strip()
    return text or f"tool_{index + 1}"
