from __future__ import annotations

import asyncio
from copy import deepcopy
import importlib
import importlib.util
import inspect
from types import SimpleNamespace
from typing import Any

import pytest

from runtime.tool_registry import PLANNING_SAFE_TOOL_NAMES

ALLOWED_PURPOSES = {
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
}

FOUNDATION_PURPOSES = {
    "intent_classifier",
    "clarification_generator",
    "journey_planner",
    "step_plan_normalizer",
    "plan_diff_editor",
    "locator_specialist",
    "recovery_diagnoser",
    "user_response_writer",
    "trace_summarizer",
}

RUNTIME_IMPACTING_PURPOSES = {
    "journey_planner",
    "step_plan_normalizer",
    "plan_diff_editor",
    "locator_specialist",
    "custom_assertion_planner",
    "execution_driver",
    "recovery_diagnoser",
    "replay_repair_specialist",
}

ALLOWED_MODEL_CLASSES = {
    "cheap",
    "small",
    "cheap/small",
    "cheap_small",
    "cheap-small",
    "main",
    "main_model",
    "main-model",
    "no_model",
    "no-model",
    "no model",
    "none",
}

ALLOWED_SKILL_LEVELS = {
    "none",
    "core_compact",
    "core-compact",
    "compact_core",
    "compact",
    "skill_summary",
    "summary",
    "capability_skill",
    "capability",
    "debug_skill",
    "debug",
}

EXPECTED_TELEMETRY_FIELDS = {
    "purpose",
    "model",
    "skill_count",
    "tool_count",
    "context_mode",
    "context_level",
    "token_budget",
    "retry_count",
    "validation_status",
    "latency_ms",
}

BLOCKED_BROWSER_TOOLS = {
    "action_click",
    "action_fill",
    "action_assert",
    "page_navigate",
    "step_recorded",
    "run_completed",
}

MODULE_CANDIDATES = (
    "runtime.llm_controller",
    "runtime.llm_runtime_controller",
)

TARGET_CANDIDATES = (
    "LLMRuntimeController",
    "RuntimeController",
    "LLMController",
)

REGISTRY_CANDIDATES = (
    "PURPOSE_REGISTRY",
    "purpose_registry",
    "LLM_PURPOSE_REGISTRY",
    "registry",
)

CALL_CANDIDATES = (
    "call",
    "run",
    "invoke",
    "execute",
    "plan_call",
    "prepare_call",
    "decide_call",
    "decide",
    "plan",
)


class FakeCallRecorder:
    def __init__(self, responses: list[Any] | None = None) -> None:
        self.calls: list[dict[str, Any]] = []
        self.responses = list(responses or [])

    def next_response(self) -> Any:
        if not self.responses:
            raise AssertionError("unexpected model call")
        return self.responses.pop(0)


def _response(content: str) -> SimpleNamespace:
    return SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content=content))]
    )


def _tool_call_response(*tool_names: str) -> SimpleNamespace:
    tool_calls = [
        SimpleNamespace(
            id=f"call-{index + 1}",
            type="function",
            function=SimpleNamespace(name=name, arguments='{"ok":true}'),
        )
        for index, name in enumerate(tool_names)
    ]
    return SimpleNamespace(
        choices=[
            SimpleNamespace(
                message=SimpleNamespace(
                    content="",
                    tool_calls=tool_calls,
                )
            )
        ]
    )


def _fake_invalid_json_response() -> SimpleNamespace:
    return _response("{ not-json }")


def _fake_valid_json_response() -> SimpleNamespace:
    return _response(
        '{"purpose":"plan_diff_editor","schema_id":"plan_diff_editor.v1","retry_count":1}'
    )


class FakeOpenAIClient:
    def __init__(self, recorder: FakeCallRecorder) -> None:
        self._recorder = recorder
        self.chat = SimpleNamespace(
            completions=SimpleNamespace(create=self._create)
        )

    async def _create(self, **payload: Any) -> Any:
        self._recorder.calls.append({"kind": "client", "payload": dict(payload)})
        return self._recorder.next_response()


class FakeModelRouter:
    def __init__(self, recorder: FakeCallRecorder) -> None:
        self._recorder = recorder

    async def call(self, **kwargs: Any) -> Any:
        self._recorder.calls.append({"kind": "router", "payload": dict(kwargs)})
        return self._recorder.next_response()


class FakeContextManager:
    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []

    def prepare_messages(
        self,
        messages: list[dict[str, Any]],
        *,
        purpose: str,
        run_id: str | None = None,
        step_id: str | None = None,
        context_mode: str = "normal",
        metadata: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> SimpleNamespace:
        payload = {
            "messages": deepcopy(messages),
            "purpose": purpose,
            "run_id": run_id,
            "step_id": step_id,
            "context_mode": context_mode,
            "metadata": deepcopy(metadata or {}),
            "kwargs": dict(kwargs),
        }
        self.calls.append(payload)
        return SimpleNamespace(
            messages=payload["messages"],
            purpose=purpose,
            context_mode=context_mode,
            metadata=payload["metadata"],
            message_count=len(messages),
            estimated_message_tokens=0,
        )

    def build_context(self, *args: Any, **kwargs: Any) -> SimpleNamespace:
        return self.prepare_messages(*args, **kwargs)

    def prepare_context(self, *args: Any, **kwargs: Any) -> SimpleNamespace:
        return self.prepare_messages(*args, **kwargs)

    def build_messages(self, *args: Any, **kwargs: Any) -> SimpleNamespace:
        return self.prepare_messages(*args, **kwargs)


class FakeSkillManager:
    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []

    def analyze(
        self,
        skills: Any,
        *,
        loaded_skill_names: list[str] | None = None,
        **kwargs: Any,
    ) -> SimpleNamespace:
        payload = {
            "skills": skills,
            "loaded_skill_names": list(loaded_skill_names or []),
            "kwargs": dict(kwargs),
        }
        self.calls.append(payload)
        return SimpleNamespace(
            loaded_skill_names=payload["loaded_skill_names"],
            skill_count=len(payload["loaded_skill_names"]),
            estimated_total_skill_tokens=0,
            per_skill_estimated_tokens={},
            largest_skill_name="none",
            largest_skill_tokens=0,
            suggested_future_policy="ok_current",
        )


class FakeTelemetrySink:
    def __init__(self) -> None:
        self.records: list[dict[str, Any]] = []

    def record(self, **payload: Any) -> None:
        self.records.append(dict(payload))

    def emit(self, **payload: Any) -> None:
        self.records.append(dict(payload))

    def log(self, **payload: Any) -> None:
        self.records.append(dict(payload))

    def record_call(self, **payload: Any) -> None:
        self.records.append(dict(payload))


class FakeSchemaValidator:
    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []

    def __call__(self, **payload: Any) -> dict[str, Any]:
        return self.validate(**payload)

    def validate(self, **payload: Any) -> dict[str, Any]:
        self.calls.append(dict(payload))
        raw_output = payload.get("raw_output") or payload.get("output") or payload.get("response")
        if isinstance(raw_output, str) and raw_output.startswith("{ not-json"):
            return {
                "ok": False,
                "validation_status": "invalid",
                "errors": ["invalid_json"],
                "parsed_output": None,
            }
        if isinstance(raw_output, dict):
            if raw_output.get("schema_id") or raw_output.get("purpose") or raw_output.get("parsed_output"):
                return {
                    "ok": True,
                    "validation_status": "valid",
                    "errors": [],
                    "parsed_output": dict(raw_output),
                }
        if hasattr(raw_output, "__dict__"):
            raw_dict = dict(vars(raw_output))
            if raw_dict.get("schema_id") or raw_dict.get("purpose") or raw_dict.get("parsed_output"):
                return {
                    "ok": True,
                    "validation_status": "valid",
                    "errors": [],
                    "parsed_output": raw_dict,
                }
        if isinstance(raw_output, str) and '"schema_id"' in raw_output:
            return {
                "ok": True,
                "validation_status": "valid",
                "errors": [],
                "parsed_output": {"raw_output": raw_output},
            }
        return {
            "ok": False,
            "validation_status": "invalid",
            "errors": ["unrecognized_payload"],
            "parsed_output": None,
        }

    def validate_output(self, **payload: Any) -> dict[str, Any]:
        return self.validate(**payload)

    def check(self, **payload: Any) -> dict[str, Any]:
        return self.validate(**payload)


def _policy_value(policy: Any, *names: str, default: Any = None) -> Any:
    for name in names:
        if isinstance(policy, dict):
            if name in policy:
                value = policy[name]
            else:
                continue
        else:
            if not hasattr(policy, name):
                continue
            value = getattr(policy, name)
        if value not in (None, "", [], {}, ()):
            return value
    return default


def _registry_names(registry: Any) -> list[str]:
    if isinstance(registry, dict):
        return [str(name) for name in registry.keys()]

    keys = getattr(registry, "keys", None)
    if callable(keys):
        try:
            return [str(name) for name in keys()]
        except Exception:  # noqa: BLE001
            pass

    if isinstance(registry, (list, tuple, set)):
        names: list[str] = []
        for item in registry:
            name = _policy_value(item, "purpose", "purpose_id")
            if name is not None:
                names.append(str(name))
        return names

    list_purposes = getattr(registry, "list_purposes", None)
    if callable(list_purposes):
        result = list_purposes()
        if inspect.isawaitable(result):
            result = asyncio.run(result)
        return [str(name) for name in result]

    values = getattr(registry, "values", None)
    if callable(values):
        try:
            return [
                str(_policy_value(item, "purpose", "purpose_id"))
                for item in values()
                if _policy_value(item, "purpose", "purpose_id") is not None
            ]
        except Exception:  # noqa: BLE001
            pass

    return []


def _lookup_policy(registry: Any, purpose: str) -> Any:
    if isinstance(registry, dict):
        if purpose in registry:
            return registry[purpose]
        raise KeyError(purpose)

    getter_names = (
        "get_purpose_policy",
        "get_policy",
        "resolve",
        "lookup",
        "get",
    )
    for name in getter_names:
        getter = getattr(registry, name, None)
        if callable(getter):
            try:
                result = getter(purpose)
            except Exception:  # noqa: BLE001
                continue
            if result is not None:
                return result

    if isinstance(registry, (list, tuple, set)):
        for item in registry:
            if _policy_value(item, "purpose", "purpose_id") == purpose:
                return item

    raise KeyError(purpose)


def _find_controller_module() -> Any:
    for module_name in MODULE_CANDIDATES:
        if importlib.util.find_spec(module_name) is not None:
            return importlib.import_module(module_name)
    return None


def _load_controller_contract() -> SimpleNamespace:
    module = _find_controller_module()
    if module is None:
        pytest.xfail("No LLM Runtime Controller seam yet")

    registry = None
    for name in REGISTRY_CANDIDATES:
        candidate = getattr(module, name, None)
        if candidate is not None:
            registry = candidate
            break

    target: Any | None = None
    for name in TARGET_CANDIDATES:
        candidate = getattr(module, name, None)
        if inspect.isclass(candidate):
            target = candidate
            break

    if target is None:
        for name in CALL_CANDIDATES:
            candidate = getattr(module, name, None)
            if callable(candidate):
                target = module
                break

    if registry is None and inspect.isclass(target):
        for name in REGISTRY_CANDIDATES:
            candidate = getattr(target, name, None)
            if candidate is not None:
                registry = candidate
                break

    if registry is None:
        pytest.xfail("No LLM Runtime Controller purpose registry seam yet")

    if target is None:
        pytest.xfail("No LLM Runtime Controller call seam yet")

    return SimpleNamespace(module=module, registry=registry, target=target)


def _filter_kwargs(callable_obj: Any, payload: dict[str, Any]) -> dict[str, Any]:
    try:
        signature = inspect.signature(callable_obj)
    except (TypeError, ValueError):
        return dict(payload)

    if any(param.kind == inspect.Parameter.VAR_KEYWORD for param in signature.parameters.values()):
        return dict(payload)

    filtered: dict[str, Any] = {}
    for name in signature.parameters:
        if name == "self":
            continue
        if name in payload:
            filtered[name] = payload[name]
    return filtered


def _resolve_controller_target(target: Any, dependencies: dict[str, Any]) -> Any:
    if inspect.isclass(target):
        try:
            return target()
        except TypeError:
            ctor_kwargs = _filter_kwargs(target, dependencies)
            try:
                return target(**ctor_kwargs)
            except TypeError as exc:
                pytest.xfail(f"Unable to instantiate LLM Runtime Controller seam: {exc}")
    return target


def _invoke_controller(target: Any, **payload: Any) -> Any:
    for name in CALL_CANDIDATES:
        callable_obj = getattr(target, name, None)
        if callable(callable_obj):
            call_kwargs = _filter_kwargs(callable_obj, payload)
            result = callable_obj(**call_kwargs)
            if inspect.isawaitable(result):
                return asyncio.run(result)
            return result
    pytest.xfail("No LLM Runtime Controller call method available yet")


def _controller_dependencies(
    recorder: FakeCallRecorder,
    registry: Any | None = None,
) -> dict[str, Any]:
    schema_validator = FakeSchemaValidator()
    model_client = FakeOpenAIClient(recorder)
    model_router = FakeModelRouter(recorder)
    telemetry_sink = FakeTelemetrySink()
    return {
        "client": model_client,
        "model_client": model_client,
        "llm_client": model_client,
        "openai_client": model_client,
        "model_router": model_router,
        "router": model_router,
        "llm_router": model_router,
        "context_manager": FakeContextManager(),
        "skill_manager": FakeSkillManager(),
        "tool_registry": __import__("runtime.tool_registry", fromlist=["tool_registry"]),
        "telemetry": telemetry_sink,
        "telemetry_sink": telemetry_sink,
        "schema_validator": schema_validator,
        "validator": schema_validator,
        "purpose_registry": registry,
        "registry": registry,
    }


def _policy_payload(policy: Any) -> dict[str, Any]:
    if isinstance(policy, dict):
        return dict(policy)
    if hasattr(policy, "__dict__"):
        return dict(vars(policy))
    return {}


def test_controller_call_with_raw_response_preserves_tool_calls() -> None:
    contract = _load_controller_contract()
    recorder = FakeCallRecorder(
        responses=[_tool_call_response("send_to_overlay", "ask_user", "dom_extract")]
    )
    dependencies = _controller_dependencies(recorder, contract.registry)
    controller = _resolve_controller_target(contract.target, dependencies)
    call = getattr(controller, "call_with_raw_response", None)
    assert callable(call), "LLMRuntimeController must expose call_with_raw_response for planning"

    result = asyncio.run(
        call(
            purpose="step_plan_normalizer",
            messages=[{"role": "user", "content": "Plan the next step"}],
            phase="planning",
            context_mode="compact",
            tools=[
                {"type": "function", "function": {"name": "send_to_overlay"}},
                {"type": "function", "function": {"name": "ask_user"}},
                {"type": "function", "function": {"name": "dom_extract"}},
            ],
            tool_choice="auto",
            client=dependencies["client"],
        )
    )

    assert result["validation_status"] == "tool_calls_preserved"
    assert result["raw_response"] is not None
    assert result["raw_message"] is not None
    assert result["content"] == ""
    assert [tool_call.function.name for tool_call in result["tool_calls"]] == [
        "send_to_overlay",
        "ask_user",
        "dom_extract",
    ]
    assert recorder.calls
    assert recorder.calls[0]["kind"] == "client"


def test_purpose_registry_accepts_only_known_llm_purposes() -> None:
    contract = _load_controller_contract()
    purpose_names = _registry_names(contract.registry)

    assert purpose_names
    assert len(purpose_names) == len(set(purpose_names))
    assert set(purpose_names).issubset(ALLOWED_PURPOSES)
    assert FOUNDATION_PURPOSES.issubset(set(purpose_names))

    for purpose in FOUNDATION_PURPOSES:
        assert _lookup_policy(contract.registry, purpose)

    with pytest.raises((KeyError, LookupError, ValueError, AttributeError)):
        _lookup_policy(contract.registry, "definitely_not_a_real_llm_purpose")


def test_each_purpose_declaration_includes_required_contract_fields() -> None:
    contract = _load_controller_contract()
    purpose_names = _registry_names(contract.registry)

    for purpose in purpose_names:
        policy = _lookup_policy(contract.registry, purpose)

        purpose_id = _policy_value(policy, "purpose", "purpose_id")
        assert purpose_id == purpose

        owner = _policy_value(policy, "owner", "subsystem_owner")
        assert owner

        model_class = str(
            _policy_value(policy, "model_class", "model_route", "model_tier", "model")
        )
        assert model_class
        assert model_class in ALLOWED_MODEL_CLASSES

        skill_policy = _policy_value(policy, "skill_policy", "skills_policy")
        assert skill_policy
        skill_level = str(
            _policy_value(skill_policy, "skill_level", "level", "mode", "loading_mode")
        )
        if skill_level:
            assert skill_level in ALLOWED_SKILL_LEVELS
            assert skill_level != "full_skill"
        load_all = _policy_value(skill_policy, "load_all", "include_all_skills", "all_skills")
        assert load_all in (None, False, 0, "false", "False")

        core_skills = _policy_value(
            skill_policy,
            "required_core_skills",
            "core_skills",
            "required_skills",
            "skills",
        )
        assert core_skills

        context_policy = _policy_value(policy, "context_policy", "context")
        assert context_policy
        allow_full_dom = _policy_value(
            context_policy,
            "allow_full_dom",
            "include_full_dom",
            "full_dom",
        )
        if allow_full_dom is not None:
            assert allow_full_dom is False
        allow_full_history = _policy_value(
            context_policy,
            "allow_full_history",
            "include_full_history",
            "full_history",
        )
        if allow_full_history is not None:
            assert allow_full_history is False

        tool_policy = _policy_value(policy, "tool_policy", "tools_policy")
        assert tool_policy
        allowed_tools = _policy_value(
            tool_policy,
            "allowed_tools_by_phase",
            "phase_tools",
            "phase_allowlist",
            "planning",
            "plan_review",
            "recovery",
        )
        assert allowed_tools

        output_schema = _policy_value(
            policy,
            "output_schema",
            "output_schema_id",
            "schema",
            "schema_id",
        )
        assert output_schema

        validator = _policy_value(policy, "validator", "backend_validator")
        assert validator
        fallback = _policy_value(policy, "fallback", "retry_policy")
        assert fallback

        telemetry_fields = _policy_value(
            policy,
            "telemetry_fields",
            "telemetry",
            "trace_fields",
        )
        assert telemetry_fields
        if isinstance(telemetry_fields, dict):
            telemetry_field_names = set(telemetry_fields.keys())
        elif isinstance(telemetry_fields, (list, tuple, set)):
            telemetry_field_names = {str(item) for item in telemetry_fields}
        else:
            telemetry_field_names = {str(telemetry_fields)}

        assert {"purpose", "model"}.issubset(telemetry_field_names)
        assert {"skill_count", "tool_count"}.issubset(telemetry_field_names)
        assert {"retry_count", "validation_status"}.issubset(telemetry_field_names)
        assert {"context_mode", "context_level"}.intersection(telemetry_field_names)
        assert {"token_budget", "latency_ms"}.intersection(telemetry_field_names)

        allowed_side_effects = _policy_value(policy, "allowed_side_effects", "side_effects")
        if allowed_side_effects is not None:
            if isinstance(allowed_side_effects, str):
                side_effect_set = {allowed_side_effects.strip()}
            elif isinstance(allowed_side_effects, (list, tuple, set)):
                side_effect_set = {str(item).strip() for item in allowed_side_effects}
            else:
                side_effect_set = {str(allowed_side_effects).strip()}
            assert side_effect_set <= {"", "none"}


def test_runtime_impacting_purposes_require_backend_validator_and_single_schema_retry() -> None:
    contract = _load_controller_contract()

    for purpose in sorted(RUNTIME_IMPACTING_PURPOSES.intersection(_registry_names(contract.registry))):
        policy = _lookup_policy(contract.registry, purpose)

        backend_validator = _policy_value(policy, "backend_validator", "validator")
        assert backend_validator

        retry_policy = _policy_value(policy, "retry_policy", "fallback")
        assert retry_policy

        schema_retry_limit = _policy_value(
            retry_policy,
            "schema_retry_limit",
            "retry_limit",
            "retry_count",
        )
        assert schema_retry_limit == 1

        fallback = _policy_value(retry_policy, "fallback", "on_failure", "fallback_action")
        if fallback is not None:
            assert str(fallback) in {"fail_closed", "ask_user", "reject", "fail-closed"}


def test_tool_exposure_is_phase_and_purpose_scoped() -> None:
    contract = _load_controller_contract()
    policy = _lookup_policy(contract.registry, "journey_planner")

    tool_policy = _policy_value(policy, "tool_policy", "tools_policy")
    assert tool_policy

    allowed_by_phase = _policy_value(
        tool_policy,
        "allowed_tools_by_phase",
        "phase_tools",
        "phase_allowlist",
        "planning",
        "plan_review",
    )
    assert allowed_by_phase

    if isinstance(allowed_by_phase, dict):
        planning_tools = set(allowed_by_phase.get("planning") or allowed_by_phase.get("plan_review") or [])
    else:
        planning_tools = set(allowed_by_phase if isinstance(allowed_by_phase, (list, tuple, set)) else [])

    assert planning_tools
    assert planning_tools.issubset(set(PLANNING_SAFE_TOOL_NAMES))
    assert planning_tools.isdisjoint(BLOCKED_BROWSER_TOOLS)

    deny_reason = _policy_value(tool_policy, "deny_reason", "deny_code", "default_deny_reason")
    assert deny_reason


def test_minimal_skill_loading_uses_compact_core_plus_purpose_skills() -> None:
    contract = _load_controller_contract()
    policy = _lookup_policy(contract.registry, "journey_planner")

    skill_policy = _policy_value(policy, "skill_policy", "skills_policy")
    assert skill_policy

    skill_level = str(
        _policy_value(skill_policy, "skill_level", "level", "mode", "loading_mode")
    )
    assert skill_level in ALLOWED_SKILL_LEVELS
    assert skill_level != "full_skill"

    load_all = _policy_value(skill_policy, "load_all", "include_all_skills", "all_skills")
    assert load_all in (None, False, 0, "false", "False")

    core_skills = _policy_value(
        skill_policy,
        "required_core_skills",
        "core_skills",
        "required_skills",
    )
    assert core_skills

    purpose_skills = _policy_value(skill_policy, "purpose_skills", "task_skills", "additional_skills")
    if purpose_skills is not None:
        if isinstance(purpose_skills, (list, tuple, set)):
            purpose_skill_names = {str(item) for item in purpose_skills}
        else:
            purpose_skill_names = {str(purpose_skills)}
        assert purpose_skill_names
        assert purpose_skill_names != {"all"}

    context_policy = _policy_value(policy, "context_policy", "context")
    assert context_policy
    context_level = _policy_value(context_policy, "context_level", "level", "mode", "context_mode")
    assert context_level
    context_level_text = str(context_level)
    assert context_level_text not in {"full", "all", "unbounded", "raw_full_dom", "full_history"}


def test_deterministic_first_policy_skips_model_call_for_safe_locator_case() -> None:
    contract = _load_controller_contract()
    recorder = FakeCallRecorder()
    dependencies = _controller_dependencies(recorder, contract.registry)
    controller = _resolve_controller_target(contract.target, dependencies)

    locator_policy = _lookup_policy(contract.registry, "locator_specialist")
    runtime_state = {
        "run_id": "run-001",
        "plan_id": "plan-001",
        "plan_version": 1,
        "mutation_log": [],
    }
    before = deepcopy(runtime_state)

    result = _invoke_controller(
        controller,
        purpose="locator_specialist",
        policy=locator_policy,
        purpose_policy=locator_policy,
        client=dependencies["client"],
        model_client=dependencies["model_client"],
        model_router=dependencies["model_router"],
        context_manager=dependencies["context_manager"],
        skill_manager=dependencies["skill_manager"],
        tool_registry=dependencies["tool_registry"],
        telemetry=dependencies["telemetry"],
        telemetry_sink=dependencies["telemetry_sink"],
        messages=[
            {
                "role": "user",
                "content": "Locate the Get started button if the backend can do it deterministically.",
            }
        ],
        model="dummy-model",
        phase="planning",
        context_mode="compact",
        deterministic_safe=True,
        deterministic_reason="unique validated locator",
        runtime_state=runtime_state,
        output_schema=_policy_value(locator_policy, "output_schema", "schema", "schema_id"),
        retry_policy=_policy_value(locator_policy, "retry_policy", "fallback"),
        validator=_policy_value(locator_policy, "backend_validator", "validator"),
        tool_policy=_policy_value(locator_policy, "tool_policy", "tools_policy"),
        skill_policy=_policy_value(locator_policy, "skill_policy", "skills_policy"),
        context_policy=_policy_value(locator_policy, "context_policy", "context"),
    )

    assert recorder.calls == []
    assert runtime_state == before
    if result is not None:
        result_model_called = _policy_value(
            result,
            "model_called",
            "used_model",
            "llm_called",
            "call_model",
        )
        if result_model_called is not None:
            assert result_model_called is False


def test_invalid_structured_output_retries_once_then_fails_closed_without_runtime_mutation() -> None:
    contract = _load_controller_contract()
    recorder = FakeCallRecorder(
        responses=[
            _fake_invalid_json_response(),
            _fake_invalid_json_response(),
        ]
    )
    dependencies = _controller_dependencies(recorder, contract.registry)
    controller = _resolve_controller_target(contract.target, dependencies)

    policy = _lookup_policy(contract.registry, "plan_diff_editor")
    runtime_state = {
        "run_id": "run-002",
        "plan_id": "plan-002",
        "plan_version": 4,
        "mutation_log": [],
    }
    before = deepcopy(runtime_state)

    result = _invoke_controller(
        controller,
        purpose="plan_diff_editor",
        policy=policy,
        purpose_policy=policy,
        client=dependencies["client"],
        model_client=dependencies["model_client"],
        model_router=dependencies["model_router"],
        context_manager=dependencies["context_manager"],
        skill_manager=dependencies["skill_manager"],
        tool_registry=dependencies["tool_registry"],
        telemetry=dependencies["telemetry"],
        telemetry_sink=dependencies["telemetry_sink"],
        messages=[
            {
                "role": "user",
                "content": "Return only the structured plan diff.",
            }
        ],
        model="dummy-model",
        phase="planning",
        context_mode="compact",
        runtime_state=runtime_state,
        output_schema=_policy_value(policy, "output_schema", "schema", "schema_id"),
        retry_policy=_policy_value(policy, "retry_policy", "fallback"),
        validator=_policy_value(policy, "backend_validator", "validator"),
        tool_policy=_policy_value(policy, "tool_policy", "tools_policy"),
        skill_policy=_policy_value(policy, "skill_policy", "skills_policy"),
        context_policy=_policy_value(policy, "context_policy", "context"),
    )

    assert len(recorder.calls) == 2
    assert runtime_state == before
    assert result is not None

    result_status = _policy_value(
        result,
        "validation_status",
        "status",
        "type",
        "result",
    )
    if result_status is not None:
        assert str(result_status) in {
            "invalid",
            "retry_failed",
            "rejected",
            "llm_output_rejected",
            "fail_closed",
        }

    backend_applied = _policy_value(result, "backend_applied", "mutated_runtime", "applied")
    if backend_applied is not None:
        assert backend_applied is False
