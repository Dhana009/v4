from __future__ import annotations

import asyncio
import json
import os
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest
from dotenv import dotenv_values
from openai import AsyncOpenAI

from runtime.llm_runtime_controller import LLMRuntimeController, PURPOSE_REGISTRY
from tests.e2e import harness as e2e_harness


class _PassThroughValidator:
    def validate(self, **_: Any) -> dict[str, Any]:
        return {
            "ok": True,
            "validation_status": "valid",
            "errors": [],
            "parsed_output": None,
        }


class _RecordingLiveClient:
    def __init__(self, api_key: str) -> None:
        self._client = AsyncOpenAI(api_key=api_key)
        self.calls: list[dict[str, Any]] = []
        self.chat = SimpleNamespace(
            completions=SimpleNamespace(create=self._create),
        )

    async def _create(self, **payload: Any) -> Any:
        self.calls.append(dict(payload))
        return await self._client.chat.completions.create(**payload)


def _tool(function_name: str, description: str, properties: dict[str, Any], required: list[str]) -> dict[str, Any]:
    return {
        "type": "function",
        "function": {
            "name": function_name,
            "description": description,
            "parameters": {
                "type": "object",
                "properties": properties,
                "required": required,
                "additionalProperties": False,
            },
        },
    }


def _contract_tools() -> list[dict[str, Any]]:
    return [
        _tool(
            "ask_user",
            (
                "Ask the user a clarification question and wait for their response. "
                "Required when multiple plausible Profile sections exist. "
                "Do not answer clarification as plain text. "
                "Do not continue DOM exploration once ambiguity is established."
            ),
            {
                "question": {"type": "string"},
                "options": {
                    "type": "array",
                    "items": {"type": "string"},
                    "minItems": 1,
                },
            },
            ["question", "options"],
        ),
        _tool(
            "send_to_overlay",
            (
                "Send a structured planning message. "
                "Use message_type='plan_ready' only for a complete plan proposal. "
                "Do not use message_type='llm_thinking' for this ambiguous contract probe."
            ),
            {
                "message_type": {
                    "type": "string",
                    "enum": ["plan_ready", "llm_thinking"],
                },
                "payload": {"type": "object"},
            },
            ["message_type", "payload"],
        ),
    ]


def _build_messages() -> list[dict[str, str]]:
    return [
        {
            "role": "user",
            "content": "Click the Edit button in the Profile section",
        },
        {
            "role": "system",
            "content": (
                "Multiple plausible Profile sections were found.\n"
                "Options:\n"
                "- Profile - John Smith - Edit\n"
                "- Profile - Jane Smith - Edit\n"
                "- Profile - Student Profile - Edit\n"
                "The correct terminal action is ask_user.\n"
                "Do not call llm_thinking.\n"
                "Do not continue DOM exploration.\n"
                "Do not answer in plain text."
            ),
        },
    ]


def _artifact_dir() -> Path:
    timestamp = datetime.now(UTC).strftime("%Y%m%d-%H%M%S")
    path = Path("test-results/llm-contract") / f"step_plan_normalizer_ambiguous_profile-{timestamp}"
    path.mkdir(parents=True, exist_ok=True)
    return path


def _repo_openai_key() -> str:
    values = dotenv_values(".env")
    repo_key = str(values.get("OPENAI_API_KEY", "")).strip()
    if repo_key.startswith("sk-"):
        return repo_key
    env_key = str(os.getenv("OPENAI_API_KEY", "")).strip()
    return env_key if env_key.startswith("sk-") else ""


def _extract_tool_calls(raw_tool_calls: list[Any]) -> list[dict[str, Any]]:
    extracted: list[dict[str, Any]] = []
    for raw_tool_call in raw_tool_calls:
        function = getattr(raw_tool_call, "function", None)
        name = getattr(function, "name", None)
        arguments = getattr(function, "arguments", None)
        extracted.append(
            {
                "name": name,
                "args_summary": arguments,
            }
        )
    return extracted


def _usage_summary(usage: Any) -> dict[str, Any]:
    if usage is None:
        return {}
    prompt_tokens_details = getattr(usage, "prompt_tokens_details", None)
    return {
        "prompt_tokens": getattr(usage, "prompt_tokens", None),
        "completion_tokens": getattr(usage, "completion_tokens", None),
        "total_tokens": getattr(usage, "total_tokens", None),
        "cached_tokens": getattr(prompt_tokens_details, "cached_tokens", 0),
    }


def _write_probe_artifacts(
    *,
    artifact_dir: Path,
    result: dict[str, Any],
    client_calls: list[dict[str, Any]],
    assertion_result: dict[str, Any],
) -> None:
    raw_response = result.get("raw_response")
    usage = getattr(raw_response, "usage", None) if raw_response is not None else None
    recorded_call = {
        "call_id": result.get("call_id"),
        "purpose": result.get("purpose"),
        "model": result.get("model"),
        "model_class": result.get("telemetry_fields", {}).get("model_class") or "main",
        "prompt_pack_id": result.get("prompt_pack_id"),
        "prefix_hash": result.get("prefix_hash"),
        "tool_names": [
            str(tool.get("function", {}).get("name"))
            for tool in (client_calls[0].get("tools") or [])
            if isinstance(tool, dict)
        ] if client_calls else [],
        "tool_schema": {
            "tool_count": len(client_calls[0].get("tools") or []) if client_calls else 0,
            "tools": [
                {
                    "name": tool.get("function", {}).get("name"),
                    "description": tool.get("function", {}).get("description"),
                    "params": sorted((tool.get("function", {}).get("parameters", {}).get("properties") or {}).keys()),
                }
                for tool in (client_calls[0].get("tools") or [])
                if isinstance(tool, dict)
            ],
        },
        "assistant_text": result.get("content"),
        "tool_calls": _extract_tool_calls(result.get("tool_calls") or []),
        "finish_reason": getattr(result.get("raw_message"), "finish_reason", None),
        "token_usage": _usage_summary(usage),
        "error": {
            "validation_status": result.get("validation_status"),
            "errors": list(result.get("errors") or []),
            "error_code": result.get("error_code"),
            "message": result.get("message"),
            "error_type": result.get("error_type"),
        },
    }
    e2e_harness.write_llm_calls_artifact(artifact_dir, [recorded_call])
    e2e_harness.write_json_artifact(
        artifact_dir / "prompt-tool-summary.json",
        {
            "purpose": result.get("purpose"),
            "model": result.get("model"),
            "prompt_pack_id": result.get("prompt_pack_id"),
            "prefix_hash": result.get("prefix_hash"),
            "message_count": len(client_calls[0].get("messages") or []) if client_calls else 0,
            "messages": client_calls[0].get("messages") if client_calls else [],
            "tool_names": recorded_call["tool_names"],
            "tool_count": recorded_call["tool_schema"]["tool_count"],
        },
    )
    e2e_harness.write_json_artifact(
        artifact_dir / "token-report.json",
        {
            "call_count": 1,
            "purpose": result.get("purpose"),
            "model": result.get("model"),
            "estimated_input_tokens": result.get("estimated_total_input_tokens") or result.get("estimated_input_tokens"),
            "token_usage": recorded_call["token_usage"],
            "tool_count": recorded_call["tool_schema"]["tool_count"],
            "prompt_pack_id": result.get("prompt_pack_id"),
            "prefix_hash": result.get("prefix_hash"),
        },
    )
    e2e_harness.write_json_artifact(
        artifact_dir / "assertion-result.json",
        assertion_result,
    )


async def _run_live_probe() -> tuple[dict[str, Any], Path]:
    api_key = _repo_openai_key()
    if not api_key:
        pytest.skip("OPENAI_API_KEY is missing; live planner contract probe disabled")

    artifact_dir = _artifact_dir()
    client = _RecordingLiveClient(api_key)
    controller = LLMRuntimeController(
        purpose_registry=PURPOSE_REGISTRY,
        schema_validator=_PassThroughValidator(),
        model_client=client,
    )
    result = await controller.call_with_raw_response(
        purpose="step_plan_normalizer",
        messages=_build_messages(),
        phase="planning",
        tools=_contract_tools(),
        tool_choice="required",
    )
    tool_calls = result.get("tool_calls") or []
    terminal_tool = None
    if tool_calls:
        terminal_tool = getattr(getattr(tool_calls[0], "function", None), "name", None)
    assertion_result = {
        "status": "failed",
        "expected_terminal_tool": "ask_user",
        "actual_terminal_tool": terminal_tool,
        "validation_status": result.get("validation_status"),
        "tool_call_count": len(tool_calls),
        "assistant_text_present": bool(result.get("content")),
        "message": result.get("message"),
        "error_type": result.get("error_type"),
    }
    _write_probe_artifacts(
        artifact_dir=artifact_dir,
        result=result,
        client_calls=client.calls,
        assertion_result=assertion_result,
    )
    return result, artifact_dir


@pytest.mark.skipif(
    os.getenv("RUN_PAID_LLM_CONTRACT") != "1",
    reason="Set RUN_PAID_LLM_CONTRACT=1 to run the paid live LLM planner contract probe.",
)
def test_real_llm_planner_contract_ambiguous_profile() -> None:
    result, artifact_dir = asyncio.run(_run_live_probe())
    tool_calls = result.get("tool_calls") or []

    assert tool_calls, f"Expected a terminal tool call. Artifact: {artifact_dir}"

    first_tool_call = tool_calls[0]
    function = getattr(first_tool_call, "function", None)
    tool_name = getattr(function, "name", None)
    arguments = getattr(function, "arguments", "") or ""
    lowered_arguments = str(arguments).lower()

    assert tool_name == "ask_user", (
        f"Expected ask_user for ambiguous Profile sections, got {tool_name!r}. "
        f"Artifact: {artifact_dir}"
    )
    assert "profile" in lowered_arguments or "which" in lowered_arguments or "ambigu" in lowered_arguments, (
        f"ask_user arguments did not mention ambiguity clearly. Artifact: {artifact_dir}"
    )
