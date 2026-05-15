from __future__ import annotations

import asyncio
from types import SimpleNamespace
from typing import Any

from runtime.llm_runtime_controller import LLMRuntimeController, PURPOSE_REGISTRY


class FakeTelemetrySink:
    def __init__(self) -> None:
        self.records: list[dict[str, Any]] = []

    def record(self, **payload: Any) -> None:
        self.records.append(dict(payload))


class PassThroughSchemaValidator:
    def validate(self, **payload: Any) -> dict[str, Any]:
        raw_output = payload.get("raw_output")
        return {
            "ok": True,
            "validation_status": "valid",
            "errors": [],
            "parsed_output": raw_output,
        }


class FakeContextManager:
    def prepare_messages(self, messages, **_kwargs):
        return SimpleNamespace(
            messages=list(messages),
            metadata={},
            context_mode="compact",
            estimated_message_tokens=0,
        )


class FakeSkillManager:
    def analyze(self, skills, *, loaded_skill_names=None, **_kwargs):
        return SimpleNamespace(
            loaded_skill_names=list(loaded_skill_names or []),
            skill_count=len(loaded_skill_names or []),
            estimated_total_skill_tokens=sum(len(str(item.get("content") or "")) for item in skills or []),
        )


class FakeClient:
    def __init__(self, response: Any) -> None:
        self.calls: list[dict[str, Any]] = []
        self.chat = SimpleNamespace(
            completions=SimpleNamespace(create=self._create)
        )
        self._response = response

    async def _create(self, **payload: Any) -> Any:
        self.calls.append(dict(payload))
        return self._response


def _json_response(content: str) -> Any:
    return SimpleNamespace(
        choices=[
            SimpleNamespace(
                message=SimpleNamespace(
                    content=content,
                    tool_calls=[],
                )
            )
        ]
    )


def test_controller_emits_skill_levels_and_compact_prompt_for_step_plan_normalizer() -> None:
    telemetry_sink = FakeTelemetrySink()
    client = FakeClient(_json_response('{"purpose":"step_plan_normalizer","schema_id":"step_plan_normalizer.v1"}'))
    controller = LLMRuntimeController(
        purpose_registry=PURPOSE_REGISTRY,
        schema_validator=PassThroughSchemaValidator(),
        context_manager=FakeContextManager(),
        skill_manager=FakeSkillManager(),
        telemetry_sink=telemetry_sink,
        model_client=client,
    )

    asyncio.run(
        controller.call(
            purpose="step_plan_normalizer",
            messages=[{"role": "system", "content": "FULL SKILL PROMPT"}, {"role": "user", "content": "plan"}],
            phase="planning",
            context_mode="compact",
            tools=[],
        )
    )

    assert telemetry_sink.records
    record = telemetry_sink.records[-1]
    assert record["skills_loaded"] == [
        "llm_runtime_controller",
        "prompt_persona_skill_loading",
    ]
    assert record["skill_levels"] == ["core_compact", "core_compact"]
    assert client.calls
    system_message = client.calls[-1]["messages"][0]
    assert system_message["role"] == "system"
    assert system_message["content"] != "FULL SKILL PROMPT"


def test_schema_retry_allows_full_prompt_for_step_plan_normalizer() -> None:
    telemetry_sink = FakeTelemetrySink()
    responses = [
        _json_response("{ not-json }"),
        _json_response('{"purpose":"step_plan_normalizer","schema_id":"step_plan_normalizer.v1"}'),
    ]

    class RetryValidator:
        def __init__(self) -> None:
            self.calls = 0

        def validate(self, **payload: Any) -> dict[str, Any]:
            self.calls += 1
            raw_output = payload.get("raw_output")
            if self.calls == 1:
                return {
                    "ok": False,
                    "validation_status": "invalid",
                    "errors": ["invalid_json"],
                    "parsed_output": None,
                }
            return {
                "ok": True,
                "validation_status": "valid",
                "errors": [],
                "parsed_output": raw_output,
            }

    class RetryClient(FakeClient):
        async def _create(self, **payload: Any) -> Any:
            self.calls.append(dict(payload))
            return responses.pop(0)

    client = RetryClient(_json_response(""))
    controller = LLMRuntimeController(
        purpose_registry=PURPOSE_REGISTRY,
        schema_validator=RetryValidator(),
        context_manager=FakeContextManager(),
        skill_manager=FakeSkillManager(),
        telemetry_sink=telemetry_sink,
        model_client=client,
    )

    asyncio.run(
        controller.call(
            purpose="step_plan_normalizer",
            messages=[{"role": "system", "content": "FULL SKILL PROMPT"}, {"role": "user", "content": "plan"}],
            phase="planning",
            context_mode="compact",
            tools=[],
        )
    )

    assert len(client.calls) == 2
    assert client.calls[0]["messages"][0]["content"] != "FULL SKILL PROMPT"
    assert client.calls[1]["messages"][0]["content"] == "FULL SKILL PROMPT"
