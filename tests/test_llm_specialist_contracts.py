from __future__ import annotations

from collections.abc import Callable
from copy import deepcopy
from dataclasses import dataclass, field
from types import SimpleNamespace
from typing import Any

import asyncio

import pytest

from runtime.llm_runtime_controller import LLMRuntimeController, PURPOSE_REGISTRY


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

EXECUTION_TOOL_NAMES = {
    "action_click",
    "action_fill",
    "action_assert",
    "page_navigate",
    "page_go_back",
    "page_go_forward",
    "page_reload",
    "scroll_into_view",
}

MIXED_TOOLS = [
    {"type": "function", "function": {"name": "action_click"}},
    {"type": "function", "function": {"name": "browser_get_state"}},
    {"type": "function", "function": {"name": "locator_find"}},
    {"type": "function", "function": {"name": "action_fill"}},
    {"type": "function", "function": {"name": "locator_validate"}},
    {"type": "function", "function": {"name": "dom_extract"}},
    {"type": "function", "function": {"name": "ask_user"}},
    {"type": "function", "function": {"name": "page_navigate"}},
    {"type": "function", "function": {"name": "action_assert"}},
]


def _response(content: Any) -> SimpleNamespace:
    return SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content=content))]
    )


def _is_missing(value: Any) -> bool:
    return value is None or value == "" or value == [] or value == {}


class FakeCallRecorder:
    def __init__(self, responses: list[Any] | None = None) -> None:
        self.calls: list[dict[str, Any]] = []
        self.responses = list(responses or [])

    def next_response(self) -> Any:
        if not self.responses:
            raise AssertionError("unexpected model call")
        return self.responses.pop(0)


class FakeOpenAIClient:
    def __init__(self, recorder: FakeCallRecorder) -> None:
        self._recorder = recorder
        self.chat = SimpleNamespace(
            completions=SimpleNamespace(create=self._create)
        )

    async def _create(self, **payload: Any) -> Any:
        self._recorder.calls.append({"kind": "client", "payload": dict(payload)})
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
            estimated_message_tokens=len(messages) * 10,
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


class FailIfCalledValidator:
    def validate(self, **payload: Any) -> dict[str, Any]:
        raise AssertionError(f"schema validation should not run: {payload!r}")


@dataclass(slots=True)
class ContractValidator:
    purpose: str
    required_fields: tuple[str, ...]
    forbidden_fields: tuple[str, ...] = ()
    nested_check: Callable[[dict[str, Any]], list[str]] | None = None
    calls: list[dict[str, Any]] = field(default_factory=list)

    def validate(self, **payload: Any) -> dict[str, Any]:
        self.calls.append(dict(payload))
        raw_output = payload.get("raw_output") or payload.get("output") or payload.get("response")
        output_schema = payload.get("output_schema")
        errors: list[str] = []

        if not isinstance(output_schema, dict) or output_schema.get("schema_id") != f"{self.purpose}.v1":
            errors.append("output_schema.schema_id")

        if not isinstance(raw_output, dict):
            errors.append("raw_output")
            return {
                "ok": False,
                "validation_status": "invalid",
                "errors": errors,
                "parsed_output": None,
            }

        if raw_output.get("schema_id") != f"{self.purpose}.v1":
            errors.append("schema_id")
        if raw_output.get("purpose") != self.purpose:
            errors.append("purpose")

        for field_name in self.required_fields:
            if _is_missing(raw_output.get(field_name)):
                errors.append(field_name)

        for field_name in self.forbidden_fields:
            if not _is_missing(raw_output.get(field_name)):
                errors.append(f"forbidden:{field_name}")

        if self.nested_check is not None:
            errors.extend(self.nested_check(raw_output))

        if errors:
            return {
                "ok": False,
                "validation_status": "invalid",
                "errors": errors,
                "parsed_output": None,
            }

        return {
            "ok": True,
            "validation_status": "valid",
            "errors": [],
            "parsed_output": deepcopy(raw_output),
        }


def _make_controller(
    recorder: FakeCallRecorder,
    telemetry_sink: FakeTelemetrySink,
    validator: Any,
    *,
    context_manager: FakeContextManager | None = None,
    skill_manager: FakeSkillManager | None = None,
) -> tuple[LLMRuntimeController, FakeContextManager, FakeSkillManager]:
    context_manager = context_manager or FakeContextManager()
    skill_manager = skill_manager or FakeSkillManager()
    controller = LLMRuntimeController(
        purpose_registry=PURPOSE_REGISTRY,
        schema_validator=validator,
        context_manager=context_manager,
        skill_manager=skill_manager,
        telemetry_sink=telemetry_sink,
        model_client=FakeOpenAIClient(recorder),
    )
    return controller, context_manager, skill_manager


def _run_call(
    purpose: str,
    response: Any | list[Any],
    validator: Any,
    *,
    tools: list[dict[str, object]] | None = None,
    messages: list[dict[str, Any]] | None = None,
    deterministic_safe: bool = False,
    deterministic_reason: str | None = None,
) -> tuple[dict[str, Any], FakeCallRecorder, FakeTelemetrySink, FakeContextManager, FakeSkillManager]:
    responses = response if isinstance(response, list) else [response]
    recorder = FakeCallRecorder([_response(item) for item in responses])
    telemetry_sink = FakeTelemetrySink()
    controller, context_manager, skill_manager = _make_controller(recorder, telemetry_sink, validator)
    result = asyncio.run(
        controller.call(
            purpose=purpose,
            messages=messages
            or [{"role": "user", "content": f"contract-check:{purpose}"}],
            phase="planning",
            tools=tools or [],
            deterministic_safe=deterministic_safe,
            deterministic_reason=deterministic_reason,
        )
    )
    return result, recorder, telemetry_sink, context_manager, skill_manager


def _locator_candidate_check(raw_output: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    candidates = raw_output.get("candidate_locators")
    if not isinstance(candidates, list) or not candidates:
        errors.append("candidate_locators")
        return errors

    for index, candidate in enumerate(candidates):
        if not isinstance(candidate, dict):
            errors.append(f"candidate_locators[{index}]")
            continue
        for field_name in ("candidate_id", "strategy", "selector_or_locator", "rationale", "risk"):
            if _is_missing(candidate.get(field_name)):
                errors.append(f"candidate_locators[{index}].{field_name}")
        if candidate.get("risk") not in {"low", "medium", "high"}:
            errors.append(f"candidate_locators[{index}].risk")
    return errors


def _recovery_option_check(raw_output: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    options = raw_output.get("suggested_options")
    if not isinstance(options, list) or not options:
        errors.append("suggested_options")
        return errors

    for index, option in enumerate(options):
        if not isinstance(option, dict):
            errors.append(f"suggested_options[{index}]")
            continue
        for field_name in ("option_id", "option_type", "label", "risk", "backend_validation_needed"):
            if _is_missing(option.get(field_name)):
                errors.append(f"suggested_options[{index}].{field_name}")
        if option.get("option_type") not in {"retry", "update_locator", "skip", "stop", "clarify", "gap"}:
            errors.append(f"suggested_options[{index}].option_type")
        if option.get("risk") not in {"low", "medium", "high"}:
            errors.append(f"suggested_options[{index}].risk")
    return errors


@pytest.mark.parametrize(
    ("purpose", "expected_model_class", "expected_skill_names", "expected_tool_names", "expected_token_budget"),
    [
        (
            "locator_specialist",
            "main",
            ("llm_runtime_controller", "locator_strategy"),
            {"browser_get_state", "dom_extract", "locator_find", "locator_validate", "ask_user"},
            2200,
        ),
        (
            "recovery_diagnoser",
            "main",
            ("llm_runtime_controller", "prompt_persona_skill_loading"),
            {"browser_get_state", "ask_user"},
            1800,
        ),
        (
            "trace_summarizer",
            "cheap",
            ("llm_runtime_controller", "prompt_persona_skill_loading"),
            set(),
            1000,
        ),
    ],
)
def test_llm_008_009_010_purpose_policies_are_complete_and_inspectable(
    purpose: str,
    expected_model_class: str,
    expected_skill_names: tuple[str, ...],
    expected_tool_names: set[str],
    expected_token_budget: int,
) -> None:
    policy = PURPOSE_REGISTRY[purpose]

    assert policy["purpose"] == purpose
    assert policy["purpose_id"] == purpose
    assert policy["owner"] == "DEV-2 LLM Runtime Controller"
    assert policy["model_class"] == expected_model_class
    assert policy["token_budget"] == expected_token_budget
    assert policy["allowed_side_effects"] == ["none"]

    skill_policy = policy["skill_policy"]
    assert skill_policy["purpose"] == purpose
    assert skill_policy["load_all"] is False
    assert skill_policy["required_core_skills"] == ["llm_runtime_controller"]
    assert tuple(skill_policy["purpose_skills"]) == expected_skill_names[1:]
    assert skill_policy["skill_scope"] == "purpose_specific"

    context_policy = policy["context_policy"]
    assert context_policy["purpose"] == purpose
    assert context_policy["context_level"] == "compact"
    assert context_policy["context_mode"] == "compact"
    assert context_policy["allow_full_dom"] is False
    assert context_policy["allow_full_history"] is False
    assert context_policy["allow_raw_dom"] is False
    assert context_policy["allow_unbounded_context"] is False

    tool_policy = policy["tool_policy"]
    assert tool_policy["purpose"] == purpose
    assert tool_policy["phase_policy"] == "deny_by_default"
    assert tool_policy["deny_reason"] == "deny_by_default"
    assert tool_policy["default_deny_reason"] == "deny_by_default"
    assert set(tool_policy["allowed_tools_by_phase"]) == {
        "planning",
        "plan_review",
        "awaiting_confirmation",
        "executing",
        "recovery",
        "completed",
    }
    assert set(tool_policy["allowed_tools_by_phase"]["planning"]) == expected_tool_names
    assert not EXECUTION_TOOL_NAMES.intersection(tool_policy["allowed_tools_by_phase"]["planning"])

    output_schema = policy["output_schema"]
    assert output_schema["schema_id"] == f"{purpose}.v1"
    assert output_schema["schema_version"] == 1
    assert output_schema["purpose"] == purpose
    assert output_schema["format"] == "structured_json"

    retry_policy = policy["retry_policy"]
    assert retry_policy["schema_retry_limit"] == 1
    assert retry_policy["retry_limit"] == 1
    assert retry_policy["fallback_action"] == "fail_closed"
    assert retry_policy["fallback"] == "fail_closed"
    assert retry_policy["on_failure"] == "fail_closed"

    telemetry_fields = policy["telemetry_fields"]
    assert telemetry_fields["purpose"] == purpose
    assert telemetry_fields["model"] == "str"
    assert EXPECTED_TELEMETRY_FIELDS.issubset(telemetry_fields)


def test_llm_008_locator_specialist_advisory_only_boundary() -> None:
    validator = ContractValidator(
        purpose="locator_specialist",
        required_fields=(
            "target_summary",
            "candidate_locators",
            "needs_user_selection",
            "confidence",
            "validation_requirements",
        ),
        forbidden_fields=("resolved", "completed", "executed", "action_taken"),
        nested_check=_locator_candidate_check,
    )
    response = {
        "schema_id": "locator_specialist.v1",
        "purpose": "locator_specialist",
        "target_summary": "Submit button located by label and role evidence",
        "candidate_locators": [
            {
                "candidate_id": "candidate-1",
                "strategy": "role",
                "selector_or_locator": "get_by_role('button', name='Submit')",
                "scope": "form",
                "rationale": "Role and label are stable",
                "risk": "low",
            },
            {
                "candidate_id": "candidate-2",
                "strategy": "text",
                "selector_or_locator": "text=Submit",
                "scope": "form",
                "rationale": "Fallback when role lookup is ambiguous",
                "risk": "medium",
            },
        ],
        "recommended_candidate_id": "candidate-1",
        "ambiguity_reason": "duplicate CTA text in the same form",
        "needs_user_selection": False,
        "confidence": 0.91,
        "validation_requirements": [
            "backend must re-check visibility",
            "backend must confirm candidate is unique",
        ],
    }

    result, recorder, telemetry_sink, _, skill_manager = _run_call(
        "locator_specialist",
        response,
        validator,
        tools=MIXED_TOOLS,
    )

    assert result["validation_status"] == "valid"
    assert result["tool_count"] == 5
    assert result["telemetry_fields"]["token_budget"] == 2200
    assert result["parsed_output"]["candidate_locators"][0]["strategy"] == "role"
    assert result["parsed_output"]["needs_user_selection"] is False
    assert len(recorder.calls) == 1
    assert len(telemetry_sink.records) == 1
    assert telemetry_sink.records[0]["validation_status"] == "valid"
    assert telemetry_sink.records[0]["tool_count"] == 5
    assert telemetry_sink.records[0]["token_budget"] == 2200
    assert skill_manager.calls[0]["loaded_skill_names"] == [
        "llm_runtime_controller",
        "locator_strategy",
    ]


def test_llm_009_recovery_diagnoser_contract_and_runtime_truth_boundary() -> None:
    validator = ContractValidator(
        purpose="recovery_diagnoser",
        required_fields=(
            "failure_summary",
            "likely_cause",
            "suggested_options",
            "needs_user_input",
            "confidence",
        ),
        forbidden_fields=("resolved", "completed", "skipped", "step_result", "execution_status"),
        nested_check=_recovery_option_check,
    )
    response = {
        "schema_id": "recovery_diagnoser.v1",
        "purpose": "recovery_diagnoser",
        "failure_summary": "Click failed because the button became hidden",
        "likely_cause": "The DOM changed after navigation",
        "suggested_options": [
            {
                "option_id": "option-1",
                "option_type": "update_locator",
                "label": "Re-evaluate the locator",
                "risk": "low",
                "backend_validation_needed": True,
            },
            {
                "option_id": "option-2",
                "option_type": "retry",
                "label": "Retry after a fresh page snapshot",
                "risk": "medium",
                "backend_validation_needed": True,
            },
        ],
        "recommended_option": "option-1",
        "needs_user_input": True,
        "unsupported_capability": None,
        "confidence": 0.77,
    }

    result, recorder, telemetry_sink, _, skill_manager = _run_call(
        "recovery_diagnoser",
        response,
        validator,
        tools=MIXED_TOOLS,
    )

    assert result["validation_status"] == "valid"
    assert result["tool_count"] == 2
    assert result["telemetry_fields"]["token_budget"] == 1800
    assert result["parsed_output"]["suggested_options"][0]["option_type"] == "update_locator"
    assert result["parsed_output"]["suggested_options"][0]["backend_validation_needed"] is True
    assert len(recorder.calls) == 1
    assert len(telemetry_sink.records) == 1
    assert telemetry_sink.records[0]["validation_status"] == "valid"
    assert telemetry_sink.records[0]["tool_count"] == 2
    assert telemetry_sink.records[0]["token_budget"] == 1800
    assert skill_manager.calls[0]["loaded_skill_names"] == [
        "llm_runtime_controller",
        "prompt_persona_skill_loading",
    ]


def test_llm_010_deterministic_trace_summarizer_skips_model_call_and_keeps_budget_metadata() -> None:
    recorder = FakeCallRecorder()
    telemetry_sink = FakeTelemetrySink()
    context_manager = FakeContextManager()
    skill_manager = FakeSkillManager()
    controller = LLMRuntimeController(
        purpose_registry=PURPOSE_REGISTRY,
        schema_validator=FailIfCalledValidator(),
        context_manager=context_manager,
        skill_manager=skill_manager,
        telemetry_sink=telemetry_sink,
        model_client=FakeOpenAIClient(recorder),
    )

    result = asyncio.run(
        controller.call(
            purpose="trace_summarizer",
            messages=[
                {
                    "role": "user",
                    "content": "x" * 4000,
                }
            ],
            deterministic_safe=True,
            deterministic_reason="trace already summarized",
        )
    )

    assert result["validation_status"] == "deterministic"
    assert result["model_called"] is False
    assert result["token_budget"] == 1000
    assert result["telemetry_fields"]["token_budget"] == 1000
    assert result["parsed_output"] == {
        "purpose": "trace_summarizer",
        "deterministic_reason": "trace already summarized",
        "deterministic_safe": True,
    }
    assert recorder.calls == []
    assert context_manager.calls == []
    assert skill_manager.calls == []
    assert len(telemetry_sink.records) == 1
    assert telemetry_sink.records[0]["validation_status"] == "deterministic"
    assert telemetry_sink.records[0]["token_budget"] == 1000
    assert EXPECTED_TELEMETRY_FIELDS.issubset(telemetry_sink.records[0])


@pytest.mark.parametrize(
    ("purpose", "validator", "response", "expected_tool_count"),
    [
        (
            "locator_specialist",
            ContractValidator(
                purpose="locator_specialist",
                required_fields=(
                    "target_summary",
                    "candidate_locators",
                    "needs_user_selection",
                    "confidence",
                    "validation_requirements",
                ),
                forbidden_fields=("resolved",),
                nested_check=_locator_candidate_check,
            ),
            [
                {
                    "schema_id": "locator_specialist.v1",
                    "purpose": "locator_specialist",
                    "target_summary": "Submit button located by label and role evidence",
                    "candidate_locators": [
                        {
                            "candidate_id": "candidate-1",
                            "strategy": "role",
                            "selector_or_locator": "get_by_role('button', name='Submit')",
                            "scope": "form",
                            "rationale": "Role and label are stable",
                            "risk": "low",
                        }
                    ],
                    "needs_user_selection": False,
                    "confidence": 0.82,
                    "validation_requirements": ["backend must re-check visibility"],
                    "resolved": True,
                },
                {
                    "schema_id": "locator_specialist.v1",
                    "purpose": "locator_specialist",
                    "target_summary": "Submit button located by label and role evidence",
                    "candidate_locators": [
                        {
                            "candidate_id": "candidate-1",
                            "strategy": "role",
                            "selector_or_locator": "get_by_role('button', name='Submit')",
                            "scope": "form",
                            "rationale": "Role and label are stable",
                            "risk": "low",
                        }
                    ],
                    "needs_user_selection": False,
                    "confidence": 0.82,
                    "validation_requirements": ["backend must re-check visibility"],
                    "resolved": True,
                },
            ],
            5,
        ),
        (
            "recovery_diagnoser",
            ContractValidator(
                purpose="recovery_diagnoser",
                required_fields=(
                    "failure_summary",
                    "likely_cause",
                    "suggested_options",
                    "needs_user_input",
                    "confidence",
                ),
                forbidden_fields=("completed",),
                nested_check=_recovery_option_check,
            ),
            [
                {
                    "schema_id": "recovery_diagnoser.v1",
                    "purpose": "recovery_diagnoser",
                    "failure_summary": "Click failed because the button became hidden",
                    "likely_cause": "The DOM changed after navigation",
                    "suggested_options": [
                        {
                            "option_id": "option-1",
                            "option_type": "update_locator",
                            "label": "Re-evaluate the locator",
                            "risk": "low",
                            "backend_validation_needed": True,
                        }
                    ],
                    "needs_user_input": True,
                    "confidence": 0.68,
                    "completed": True,
                },
                {
                    "schema_id": "recovery_diagnoser.v1",
                    "purpose": "recovery_diagnoser",
                    "failure_summary": "Click failed because the button became hidden",
                    "likely_cause": "The DOM changed after navigation",
                    "suggested_options": [
                        {
                            "option_id": "option-1",
                            "option_type": "update_locator",
                            "label": "Re-evaluate the locator",
                            "risk": "low",
                            "backend_validation_needed": True,
                        }
                    ],
                    "needs_user_input": True,
                    "confidence": 0.68,
                    "completed": True,
                },
            ],
            2,
        ),
    ],
)
def test_llm_008_009_invalid_specialist_outputs_fail_closed(
    purpose: str,
    validator: ContractValidator,
    response: Any | list[Any],
    expected_tool_count: int,
) -> None:
    result, recorder, telemetry_sink, _, _ = _run_call(
        purpose,
        response,
        validator,
        tools=MIXED_TOOLS,
    )

    assert result["validation_status"] == "retry_failed"
    assert result["retry_count"] == 1
    assert result["parsed_output"] is None
    assert result["tool_count"] == expected_tool_count
    assert len(recorder.calls) == 2
    assert len(telemetry_sink.records) == 1
    assert telemetry_sink.records[0]["validation_status"] == "retry_failed"
    assert telemetry_sink.records[0]["tool_count"] == expected_tool_count
