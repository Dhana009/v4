from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
import inspect
import time
from typing import Any

from runtime.telemetry import estimate_messages_tokens
from runtime.tool_registry import PLANNING_SAFE_TOOL_NAMES


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
    "skill_count": "int",
    "tool_count": "int",
    "context_mode": "str",
    "context_level": "str",
    "token_budget": "int",
    "retry_count": "int",
    "validation_status": "str",
    "latency_ms": "int",
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

PLAN_REVIEW_TOOL_NAMES = (
    "send_to_overlay",
    "ask_user",
)

RECOVERY_TOOL_NAMES = (
    "browser_get_state",
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
    allowed_tools_by_phase = {
        "planning": _normalize_names(planning_tools),
        "plan_review": _normalize_names(plan_review_tools or PLAN_REVIEW_TOOL_NAMES),
        "awaiting_confirmation": _normalize_names(plan_review_tools or PLAN_REVIEW_TOOL_NAMES),
        "executing": _normalize_names(executing_tools or ()),
        "recovery": _normalize_names(recovery_tools or RECOVERY_TOOL_NAMES),
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

    return {
        "intent_classifier": _purpose_policy(
            purpose="intent_classifier",
            model_class="cheap",
            skill_names=planner_skill,
            planning_tools=(),
            token_budget=1000,
        ),
        "clarification_generator": _purpose_policy(
            purpose="clarification_generator",
            model_class="cheap",
            skill_names=planner_skill,
            planning_tools=("ask_user", "send_to_overlay"),
            token_budget=1000,
        ),
        "page_intelligence_summarizer": _purpose_policy(
            purpose="page_intelligence_summarizer",
            model_class="cheap",
            skill_names=locator_skill,
            planning_tools=LOCATOR_TOOL_NAMES,
            token_budget=1400,
        ),
        "page_validation_recommender": _purpose_policy(
            purpose="page_validation_recommender",
            model_class="main",
            skill_names=locator_skill,
            planning_tools=LOCATOR_TOOL_NAMES,
            token_budget=1800,
        ),
        "journey_planner": _purpose_policy(
            purpose="journey_planner",
            model_class="main",
            skill_names=planner_skill,
            planning_tools=PLANNING_TOOL_NAMES,
            token_budget=2400,
        ),
        "step_plan_normalizer": _purpose_policy(
            purpose="step_plan_normalizer",
            model_class="main",
            skill_names=planner_skill,
            planning_tools=PLAN_REVIEW_TOOL_NAMES,
            token_budget=2000,
        ),
        "plan_diff_editor": _purpose_policy(
            purpose="plan_diff_editor",
            model_class="main",
            skill_names=planner_skill,
            planning_tools=PLAN_REVIEW_TOOL_NAMES,
            token_budget=2200,
        ),
        "locator_specialist": _purpose_policy(
            purpose="locator_specialist",
            model_class="main",
            skill_names=locator_skill,
            planning_tools=LOCATOR_TOOL_NAMES,
            token_budget=2200,
        ),
        "custom_assertion_planner": _purpose_policy(
            purpose="custom_assertion_planner",
            model_class="main",
            skill_names=mixed_skill,
            planning_tools=LOCATOR_TOOL_NAMES,
            token_budget=2200,
        ),
        "execution_driver": _purpose_policy(
            purpose="execution_driver",
            model_class="main",
            skill_names=planner_skill,
            planning_tools=("ask_user",),
            token_budget=1800,
        ),
        "recovery_diagnoser": _purpose_policy(
            purpose="recovery_diagnoser",
            model_class="main",
            skill_names=planner_skill,
            planning_tools=RECOVERY_TOOL_NAMES,
            token_budget=1800,
        ),
        "replay_repair_specialist": _purpose_policy(
            purpose="replay_repair_specialist",
            model_class="main",
            skill_names=planner_skill,
            planning_tools=RECOVERY_TOOL_NAMES,
            token_budget=1800,
        ),
        "user_response_writer": _purpose_policy(
            purpose="user_response_writer",
            model_class="cheap",
            skill_names=planner_skill,
            planning_tools=("ask_user",),
            token_budget=1000,
        ),
        "trace_summarizer": _purpose_policy(
            purpose="trace_summarizer",
            model_class="cheap",
            skill_names=planner_skill,
            planning_tools=(),
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
    purpose: str
    model: str
    skill_count: int
    tool_count: int
    context_mode: str
    context_level: str
    token_budget: int
    retry_count: int
    validation_status: str
    latency_ms: int


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

    def _skill_names_for_policy(self, policy: Mapping[str, Any]) -> list[str]:
        skill_policy = _value(policy, "skill_policy", "skills_policy", default={})
        if not isinstance(skill_policy, Mapping):
            return []
        core_skills = _normalize_names(
            _value(skill_policy, "required_core_skills", "core_skills", "required_skills", "skills", default=[])
        )
        purpose_skills = _normalize_names(
            _value(skill_policy, "purpose_skills", "task_skills", "additional_skills", default=[])
        )
        return list(dict.fromkeys(core_skills + purpose_skills))

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
        policy: Mapping[str, Any],
    ) -> tuple[list[str], int]:
        skill_names = self._skill_names_for_policy(policy)
        if skill_manager is None or not skill_names:
            return skill_names, len(skill_names)

        skill_descriptors = [{"name": name, "content": ""} for name in skill_names]
        analyze = _call_if_available(
            skill_manager,
            "analyze",
            skills=skill_descriptors,
            loaded_skill_names=skill_names,
        )
        if inspect.isawaitable(analyze):
            raise TypeError("skill manager returned awaitable from synchronous helper")

        if analyze is None:
            return skill_names, len(skill_names)

        loaded_names = _value(analyze, "loaded_skill_names", default=skill_names)
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
            normalized_phase = str(phase or "").strip().lower() or "planning"
            if normalized_phase in {"planning", "awaiting_confirmation"}:
                return []
            return filtered_tools

        final_tools: list[Any] = []
        for index, tool in enumerate(filtered_tools):
            tool_name = _tool_name(tool, index)
            if tool_name in allowed_names:
                final_tools.append(tool)
        return final_tools

    def _emit_telemetry(self, telemetry_sink: Any | None, telemetry_record: ControllerTelemetry) -> None:
        if telemetry_sink is None:
            return

        payload = {
            "purpose": telemetry_record.purpose,
            "model": telemetry_record.model,
            "skill_count": telemetry_record.skill_count,
            "tool_count": telemetry_record.tool_count,
            "context_mode": telemetry_record.context_mode,
            "context_level": telemetry_record.context_level,
            "token_budget": telemetry_record.token_budget,
            "retry_count": telemetry_record.retry_count,
            "validation_status": telemetry_record.validation_status,
            "latency_ms": telemetry_record.latency_ms,
        }

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
        context_mode: str = "compact",
        context_level: str = "compact",
        token_budget: int = 0,
        latency_ms: int = 0,
    ) -> dict[str, Any]:
        return {
            "purpose": purpose,
            "purpose_id": _value(policy, "purpose_id", "purpose", default=purpose),
            "schema_id": _value(_value(policy, "output_schema", default={}), "schema_id", default=f"{purpose}.v1"),
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
            "context_mode": context_mode,
            "context_level": context_level,
            "token_budget": token_budget,
            "telemetry_fields": {
                "purpose": purpose,
                "model": model,
                "skill_count": skill_count,
                "tool_count": tool_count,
                "context_mode": context_mode,
                "context_level": context_level,
                "token_budget": token_budget,
                "retry_count": retry_count,
                "validation_status": validation_status,
                "latency_ms": latency_ms,
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

        started_at = time.perf_counter()
        if deterministic_safe:
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
                context_mode=str(context_mode or _value(context_policy_value, "context_mode", default="compact")),
                context_level=context_level,
                token_budget=token_budget,
                latency_ms=max(0, int((time.perf_counter() - started_at) * 1000)),
            )
            self._emit_telemetry(
                resolved_telemetry_sink,
                ControllerTelemetry(
                    purpose=normalized_purpose,
                    model=resolved_model,
                    skill_count=0,
                    tool_count=0,
                    context_mode=str(context_mode or _value(context_policy_value, "context_mode", default="compact")),
                    context_level=context_level,
                    token_budget=token_budget,
                    retry_count=0,
                    validation_status="deterministic",
                    latency_ms=max(0, int((time.perf_counter() - started_at) * 1000)),
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
        loaded_skill_names, skill_count = self._analyze_skills(
            skill_manager=resolved_skill_manager,
            policy=resolved_policy,
        )
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

        for attempt_index in range(max_attempts):
            if attempt_index > 0:
                retry_note = {
                    "role": "system",
                    "content": (
                        "Previous output failed schema validation. "
                        "Return only the structured response for the declared schema."
                    ),
                }
                attempt_messages = list(prepared_messages) + [retry_note]
            else:
                attempt_messages = list(prepared_messages)

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
                    context_mode=effective_context_mode,
                    context_level=context_level,
                    token_budget=token_budget,
                    latency_ms=max(0, int((time.perf_counter() - started_at) * 1000)),
                )
                self._emit_telemetry(
                    resolved_telemetry_sink,
                    ControllerTelemetry(
                        purpose=normalized_purpose,
                        model=resolved_model,
                        skill_count=result["skill_count"],
                        tool_count=tool_count,
                        context_mode=effective_context_mode,
                        context_level=context_level,
                        token_budget=token_budget,
                        retry_count=attempt_index,
                        validation_status="valid",
                        latency_ms=result["telemetry_fields"]["latency_ms"],
                    ),
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
            context_mode=effective_context_mode,
            context_level=context_level,
            token_budget=token_budget,
            latency_ms=max(0, int((time.perf_counter() - started_at) * 1000)),
        )
        self._emit_telemetry(
            resolved_telemetry_sink,
            ControllerTelemetry(
                purpose=normalized_purpose,
                model=resolved_model,
                skill_count=failure_result["skill_count"],
                tool_count=tool_count,
                context_mode=effective_context_mode,
                context_level=context_level,
                token_budget=token_budget,
                retry_count=max_attempts - 1,
                validation_status="retry_failed",
                latency_ms=failure_result["telemetry_fields"]["latency_ms"],
            ),
        )
        return failure_result


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
