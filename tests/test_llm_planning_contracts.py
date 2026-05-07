from __future__ import annotations

from collections.abc import Callable
from copy import deepcopy
from dataclasses import dataclass, field
from types import SimpleNamespace
from typing import Any

import asyncio

import pytest

from runtime.llm_runtime_controller import LLMRuntimeController, PURPOSE_REGISTRY
from runtime.tool_registry import PLANNING_SAFE_TOOL_NAMES


EXPECTED_TELEMETRY_FIELDS = {
    "call_id",
    "purpose",
    "model",
    "skill_count",
    "skills_loaded",
    "tool_count",
    "tools_exposed_count",
    "context_mode",
    "context_level",
    "token_budget",
    "estimated_input_tokens",
    "estimated_output_tokens",
    "retry_count",
    "validation_status",
    "latency_ms",
    "schema_id",
    "schema_version",
    "error_code",
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


def _tool(name: str) -> dict[str, object]:
    return {"type": "function", "function": {"name": name}}


def _mixed_tools() -> list[dict[str, object]]:
    return [
        _tool("action_click"),
        _tool("send_to_overlay"),
        _tool("locator_find"),
        _tool("page_navigate"),
        _tool("locator_validate"),
        _tool("dom_extract"),
        _tool("action_fill"),
        _tool("ask_user"),
        _tool("browser_get_state"),
        _tool("action_assert"),
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


@dataclass(slots=True)
class ContractValidator:
    purpose: str
    required_fields: tuple[str, ...]
    field_check: Callable[[dict[str, Any]], list[str]] | None = None
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

        if self.field_check is not None:
            errors.extend(self.field_check(raw_output))

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
    validator: ContractValidator,
) -> LLMRuntimeController:
    return LLMRuntimeController(
        purpose_registry=PURPOSE_REGISTRY,
        schema_validator=validator,
        context_manager=FakeContextManager(),
        skill_manager=FakeSkillManager(),
        telemetry_sink=telemetry_sink,
        model_client=FakeOpenAIClient(recorder),
    )


def _run_contract_call(
    purpose: str,
    responses: list[Any],
    validator: ContractValidator,
    *,
    tools: list[dict[str, object]] | None = None,
) -> tuple[dict[str, Any], FakeCallRecorder, FakeTelemetrySink]:
    recorder = FakeCallRecorder([_response(content) for content in responses])
    telemetry_sink = FakeTelemetrySink()
    controller = _make_controller(recorder, telemetry_sink, validator)
    runtime_state = {"plan_id": "plan-1", "plan_version": 1, "mutation_log": []}
    before = deepcopy(runtime_state)
    result = asyncio.run(
        controller.call(
            purpose=purpose,
            messages=[{"role": "user", "content": f"{purpose} contract check"}],
            phase="planning",
            context_mode="compact",
            runtime_state=runtime_state,
            tools=tools if tools is not None else _mixed_tools(),
        )
    )
    assert runtime_state == before
    return result, recorder, telemetry_sink


def _intent_classifier_output() -> dict[str, Any]:
    return {
        "schema_id": "intent_classifier.v1",
        "purpose": "intent_classifier",
        "intent_type": "unknown",
        "confidence": "low",
        "missing_info": ["target", "scope"],
        "clarification_question": "What should I work on?",
        "suggested_options": ["Open the dashboard", "Edit the journey plan"],
        "risk_flags": ["ambiguous"],
        "planner_ready": False,
    }


def _clarification_generator_output() -> dict[str, Any]:
    return {
        "schema_id": "clarification_generator.v1",
        "purpose": "clarification_generator",
        "clarification_question": "What should I work on?",
        "suggested_options": ["Open the dashboard", "Edit the journey plan"],
        "requires_user_clarification": True,
        "confidence": "medium",
    }


def _journey_planner_output() -> dict[str, Any]:
    return {
        "schema_id": "journey_planner.v1",
        "purpose": "journey_planner",
        "plan_intent": "open settings and verify profile visibility",
        "steps": [
            {
                "proposed_step_id": "step-1",
                "intent": "Open the settings page",
                "expected_outcome_metadata": {
                    "type": "navigation",
                    "description": "settings page opens",
                },
                "children": [
                    {
                        "type": "navigate",
                        "subtype": "page",
                        "target_semantic_name": "settings page",
                        "locator_candidate_ref": "page:/settings",
                        "order_index": 1,
                    }
                ],
                "precondition": "dashboard is loaded",
                "postcondition": "settings page is visible",
            }
        ],
        "assumptions": ["user is signed in"],
        "clarifications_needed": [],
        "risks": ["ambiguous target"],
        "confidence": "high",
    }


def _plan_diff_editor_output() -> dict[str, Any]:
    return {
        "schema_id": "plan_diff_editor.v1",
        "purpose": "plan_diff_editor",
        "correction_intent": "clarify the target and keep the confirm step after navigate",
        "target_plan_id": "plan-7",
        "target_plan_version": 3,
        "operations": [
            {
                "action": "update",
                "target_type": "step",
                "target_id": "step-1",
                "patch": {"intent": "Open the settings page"},
                "reason": "clarify the step intent",
            },
            {
                "action": "reorder",
                "target_type": "operation",
                "target_id": "op-2",
                "position": 2,
                "reason": "keep the confirm step after the navigate step",
            },
            {
                "action": "remove",
                "target_type": "operation",
                "target_id": "op-3",
                "reason": "remove redundant duplicate",
            },
        ],
        "reasoning_summary": "Keep the corrected path while removing duplication.",
        "ambiguity": [],
        "requires_user_clarification": False,
    }


def _intent_classifier_errors(output: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if str(output.get("intent_type") or "").strip() not in {
        "create_plan",
        "correction",
        "question",
        "replay",
        "unknown",
    }:
        errors.append("intent_type")
    if str(output.get("confidence") or "").strip() not in {"high", "medium", "low"}:
        errors.append("confidence")
    if not isinstance(output.get("missing_info"), list) or not output.get("missing_info"):
        errors.append("missing_info")
    if _is_missing(output.get("clarification_question")):
        errors.append("clarification_question")
    if not isinstance(output.get("suggested_options"), list) or not output.get("suggested_options"):
        errors.append("suggested_options")
    if not isinstance(output.get("risk_flags"), list):
        errors.append("risk_flags")
    if output.get("planner_ready") is not False:
        errors.append("planner_ready")
    return errors


def _clarification_generator_errors(output: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if _is_missing(output.get("clarification_question")):
        errors.append("clarification_question")
    if not isinstance(output.get("suggested_options"), list) or not output.get("suggested_options"):
        errors.append("suggested_options")
    if output.get("requires_user_clarification") is not True:
        errors.append("requires_user_clarification")
    if str(output.get("confidence") or "").strip() not in {"high", "medium", "low"}:
        errors.append("confidence")
    return errors


def _journey_planner_errors(output: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if _is_missing(output.get("plan_intent")):
        errors.append("plan_intent")
    if not isinstance(output.get("steps"), list) or not output.get("steps"):
        errors.append("steps")
        return errors

    for step_index, step in enumerate(output["steps"]):
        if not isinstance(step, dict):
            errors.append(f"steps[{step_index}]")
            continue
        if _is_missing(step.get("intent")):
            errors.append(f"steps[{step_index}].intent")
        if not isinstance(step.get("children"), list) or not step.get("children"):
            errors.append(f"steps[{step_index}].children")
            continue
        for child_index, child in enumerate(step["children"]):
            if not isinstance(child, dict):
                errors.append(f"steps[{step_index}].children[{child_index}]")
                continue
            if _is_missing(child.get("type")):
                errors.append(f"steps[{step_index}].children[{child_index}].type")
            if _is_missing(child.get("order_index")):
                errors.append(f"steps[{step_index}].children[{child_index}].order_index")
    return errors


def _plan_diff_editor_errors(output: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if output.get("requires_user_clarification") is not False:
        errors.append("requires_user_clarification")
    if not isinstance(output.get("operations"), list) or not output.get("operations"):
        errors.append("operations")
        return errors

    for op_index, operation in enumerate(output["operations"]):
        if not isinstance(operation, dict):
            errors.append(f"operations[{op_index}]")
            continue
        action = str(operation.get("action") or "").strip().lower()
        if action not in {"add", "update", "remove", "reorder"}:
            errors.append(f"operations[{op_index}].action")
        if _is_missing(operation.get("target_type")):
            errors.append(f"operations[{op_index}].target_type")
        if action in {"update", "remove", "reorder"} and _is_missing(operation.get("target_id")):
            errors.append(f"operations[{op_index}].target_id")
        if action in {"add", "update"} and _is_missing(operation.get("patch")):
            errors.append(f"operations[{op_index}].patch")
        if action == "reorder" and _is_missing(operation.get("position")):
            errors.append(f"operations[{op_index}].position")
        if action in {"remove", "reorder"} and _is_missing(operation.get("reason")):
            errors.append(f"operations[{op_index}].reason")
    return errors


@pytest.mark.parametrize(
    ("purpose", "expected_model_class", "expected_planning_tools"),
    [
        ("intent_classifier", "cheap", set()),
        ("clarification_generator", "cheap", {"ask_user", "send_to_overlay"}),
        ("journey_planner", "main", set(PLANNING_SAFE_TOOL_NAMES)),
        ("plan_diff_editor", "main", {"ask_user", "send_to_overlay"}),
    ],
)
def test_llm_005_006_007_purpose_registry_exposes_planning_slice_contracts(
    purpose: str,
    expected_model_class: str,
    expected_planning_tools: set[str],
) -> None:
    policy = PURPOSE_REGISTRY.get_purpose_policy(purpose)
    tool_policy = policy["tool_policy"]
    allowed_tools_by_phase = tool_policy["allowed_tools_by_phase"]

    assert policy["purpose"] == purpose
    assert policy["purpose_id"] == purpose
    assert policy["owner"] == "DEV-2 LLM Runtime Controller"
    assert policy["model_class"] == expected_model_class
    assert policy["backend_validator"] == "schema_validator"
    assert policy["validator"] == "schema_validator"
    assert policy["fallback"] == "fail_closed"
    assert policy["retry_policy"]["schema_retry_limit"] == 1
    assert policy["retry_policy"]["fallback"] == "fail_closed"
    assert policy["retry_policy"]["on_failure"] == "fail_closed"
    assert policy["skill_policy"]["skill_level"] == "core_compact"
    assert policy["skill_policy"]["load_all"] is False
    assert policy["skill_policy"]["required_core_skills"] == ["llm_runtime_controller"]
    assert policy["skill_policy"]["purpose_skills"] == ["prompt_persona_skill_loading"]
    assert policy["context_policy"]["context_level"] == "compact"
    assert policy["context_policy"]["context_mode"] == "compact"
    assert policy["context_policy"]["allow_full_dom"] is False
    assert policy["context_policy"]["allow_full_history"] is False
    assert policy["context_policy"]["allow_raw_dom"] is False
    assert policy["context_policy"]["allow_unbounded_context"] is False
    assert policy["output_schema"]["schema_id"] == f"{purpose}.v1"
    assert policy["output_schema"]["schema_version"] == 1
    assert policy["output_schema"]["purpose"] == purpose
    assert policy["output_schema"]["format"] == "structured_json"
    assert set(policy["telemetry_fields"]) == EXPECTED_TELEMETRY_FIELDS
    assert set(allowed_tools_by_phase["planning"]) == expected_planning_tools
    assert set(allowed_tools_by_phase["plan_review"]) == {"send_to_overlay", "ask_user"}
    assert set(allowed_tools_by_phase["awaiting_confirmation"]) == {"send_to_overlay", "ask_user"}
    assert set(allowed_tools_by_phase["executing"]) == set()
    assert set(allowed_tools_by_phase["recovery"]) <= {"browser_get_state", "ask_user"}
    assert set(allowed_tools_by_phase["completed"]) == set()
    assert expected_planning_tools.isdisjoint(EXECUTION_TOOL_NAMES)


def test_llm_005_intent_classifier_returns_clarification_ready_payload() -> None:
    output = _intent_classifier_output()
    validator = ContractValidator(
        "intent_classifier",
        (
            "intent_type",
            "confidence",
            "missing_info",
            "clarification_question",
            "suggested_options",
            "risk_flags",
            "planner_ready",
        ),
        field_check=_intent_classifier_errors,
    )

    result, recorder, telemetry_sink = _run_contract_call(
        "intent_classifier",
        [output],
        validator,
    )

    assert result["validation_status"] == "valid"
    assert result["retry_count"] == 0
    assert result["model"] == "cheap"
    assert result["skill_count"] == 2
    assert result["parsed_output"] == output
    assert result["parsed_output"]["planner_ready"] is False
    assert result["parsed_output"]["clarification_question"] == "What should I work on?"
    assert len(recorder.calls) == 1
    assert len(telemetry_sink.records) == 1
    assert telemetry_sink.records[0]["validation_status"] == "valid"
    assert result["tool_count"] == 0
    assert telemetry_sink.records[0]["tool_count"] == 0
    assert telemetry_sink.records[0]["skill_count"] == 2


def test_llm_005_clarification_generator_returns_user_followup_payload() -> None:
    output = _clarification_generator_output()
    validator = ContractValidator(
        "clarification_generator",
        (
            "clarification_question",
            "suggested_options",
            "requires_user_clarification",
        ),
        field_check=_clarification_generator_errors,
    )

    result, recorder, telemetry_sink = _run_contract_call(
        "clarification_generator",
        [output],
        validator,
    )

    assert result["validation_status"] == "valid"
    assert result["retry_count"] == 0
    assert result["model"] == "cheap"
    assert result["skill_count"] == 2
    assert result["tool_count"] == 2
    assert result["parsed_output"] == output
    assert result["parsed_output"]["requires_user_clarification"] is True
    assert result["parsed_output"]["suggested_options"] == [
        "Open the dashboard",
        "Edit the journey plan",
    ]
    assert len(recorder.calls) == 1
    assert len(telemetry_sink.records) == 1
    assert telemetry_sink.records[0]["validation_status"] == "valid"
    assert telemetry_sink.records[0]["tool_count"] == 2
    assert telemetry_sink.records[0]["skill_count"] == 2


def test_llm_006_journey_planner_returns_structured_plan_proposal() -> None:
    output = _journey_planner_output()
    validator = ContractValidator(
        "journey_planner",
        (
            "plan_intent",
            "steps",
            "confidence",
        ),
        field_check=_journey_planner_errors,
    )

    result, recorder, telemetry_sink = _run_contract_call(
        "journey_planner",
        [output],
        validator,
    )

    assert result["validation_status"] == "valid"
    assert result["retry_count"] == 0
    assert result["model"] == "main"
    assert result["skill_count"] == 2
    assert result["tool_count"] == len(PLANNING_SAFE_TOOL_NAMES)
    assert result["parsed_output"] == output
    assert result["parsed_output"]["steps"][0]["children"][0]["order_index"] == 1
    assert result["parsed_output"]["steps"][0]["children"][0]["target_semantic_name"] == "settings page"
    assert len(recorder.calls) == 1
    assert len(telemetry_sink.records) == 1
    assert telemetry_sink.records[0]["validation_status"] == "valid"
    assert telemetry_sink.records[0]["tool_count"] == len(PLANNING_SAFE_TOOL_NAMES)
    assert telemetry_sink.records[0]["skill_count"] == 2


def test_llm_007_plan_diff_editor_returns_mutation_only_diff() -> None:
    output = _plan_diff_editor_output()
    validator = ContractValidator(
        "plan_diff_editor",
        (
            "correction_intent",
            "target_plan_id",
            "target_plan_version",
            "operations",
            "requires_user_clarification",
        ),
        field_check=_plan_diff_editor_errors,
    )

    result, recorder, telemetry_sink = _run_contract_call(
        "plan_diff_editor",
        [output],
        validator,
    )

    assert result["validation_status"] == "valid"
    assert result["retry_count"] == 0
    assert result["model"] == "main"
    assert result["skill_count"] == 2
    assert result["tool_count"] == 2
    assert result["parsed_output"] == output
    assert result["parsed_output"]["operations"][1]["action"] == "reorder"
    assert result["parsed_output"]["operations"][2]["reason"] == "remove redundant duplicate"
    assert result["parsed_output"]["requires_user_clarification"] is False
    assert len(recorder.calls) == 1
    assert len(telemetry_sink.records) == 1
    assert telemetry_sink.records[0]["validation_status"] == "valid"
    assert telemetry_sink.records[0]["tool_count"] == 2
    assert telemetry_sink.records[0]["skill_count"] == 2


@pytest.mark.parametrize(
    ("purpose", "bad_output", "validator", "expected_tool_count"),
    [
        (
            "intent_classifier",
            {
                "schema_id": "intent_classifier.v1",
                "purpose": "intent_classifier",
                "intent_type": "unknown",
                "confidence": "low",
                "missing_info": ["target"],
                "clarification_question": "",
                "suggested_options": ["Open the dashboard"],
                "risk_flags": ["ambiguous"],
                "planner_ready": True,
            },
            ContractValidator(
                "intent_classifier",
                (
                    "intent_type",
                    "confidence",
                    "missing_info",
                    "clarification_question",
                    "suggested_options",
                    "risk_flags",
                    "planner_ready",
                ),
                field_check=_intent_classifier_errors,
            ),
            0,
        ),
        (
            "clarification_generator",
            {
                "schema_id": "clarification_generator.v1",
                "purpose": "clarification_generator",
                "clarification_question": "What should I work on?",
                "suggested_options": [],
                "requires_user_clarification": False,
                "confidence": "medium",
            },
            ContractValidator(
                "clarification_generator",
                (
                    "clarification_question",
                    "suggested_options",
                    "requires_user_clarification",
                ),
                field_check=_clarification_generator_errors,
            ),
            2,
        ),
        (
            "journey_planner",
            {
                "schema_id": "journey_planner.v1",
                "purpose": "journey_planner",
                "plan_intent": "open settings and verify profile visibility",
                "steps": [],
                "assumptions": ["user is signed in"],
                "clarifications_needed": [],
                "risks": ["ambiguous target"],
                "confidence": "high",
            },
            ContractValidator(
                "journey_planner",
                (
                    "plan_intent",
                    "steps",
                    "confidence",
                ),
                field_check=_journey_planner_errors,
            ),
            len(PLANNING_SAFE_TOOL_NAMES),
        ),
        (
            "plan_diff_editor",
            {
                "schema_id": "plan_diff_editor.v1",
                "purpose": "plan_diff_editor",
                "correction_intent": "clarify the target and keep the confirm step after navigate",
                "target_plan_id": "plan-7",
                "target_plan_version": 3,
                "operations": [
                    {
                        "action": "update",
                        "target_type": "step",
                        "target_id": "step-1",
                        "patch": {"intent": "Open the settings page"},
                        "reason": "clarify the step intent",
                    },
                    {
                        "action": "reorder",
                        "target_type": "operation",
                        "target_id": "op-2",
                        "position": 2,
                        "reason": "",
                    },
                ],
                "reasoning_summary": "Keep the corrected path while removing duplication.",
                "ambiguity": [],
                "requires_user_clarification": False,
            },
            ContractValidator(
                "plan_diff_editor",
                (
                    "correction_intent",
                    "target_plan_id",
                    "target_plan_version",
                    "operations",
                    "requires_user_clarification",
                ),
                field_check=_plan_diff_editor_errors,
            ),
            2,
        ),
    ],
)
def test_llm_005_006_007_invalid_outputs_fail_closed_after_one_retry(
    purpose: str,
    bad_output: dict[str, Any],
    validator: ContractValidator,
    expected_tool_count: int,
) -> None:
    result, recorder, telemetry_sink = _run_contract_call(
        purpose,
        [bad_output, bad_output],
        validator,
    )

    assert result["validation_status"] == "retry_failed"
    assert result["retry_count"] == 1
    assert result["parsed_output"] is None
    assert result["skill_count"] == 2
    assert len(recorder.calls) == 2
    assert len(telemetry_sink.records) == 1
    assert telemetry_sink.records[0]["validation_status"] == "retry_failed"
    assert result["tool_count"] == expected_tool_count
    assert telemetry_sink.records[0]["tool_count"] == expected_tool_count
    assert telemetry_sink.records[0]["skill_count"] == 2
