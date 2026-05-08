from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class ModelCallRequest:
    purpose: str
    client: Any
    model: str
    messages: list[dict[str, Any]]
    tools: list[dict[str, Any]] | None = None
    tool_choice: Any = None
    kwargs: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class ModelCallResult:
    request: ModelCallRequest
    response: Any


class ModelRouter:
    async def call(
        self,
        *,
        purpose: str,
        client: Any,
        model: str,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        tool_choice: Any = None,
        **kwargs: Any,
    ) -> Any:
        request = ModelCallRequest(
            purpose=str(purpose or "").strip(),
            client=client,
            model=model,
            messages=messages,
            tools=tools,
            tool_choice=tool_choice,
            kwargs=dict(kwargs),
        )

        if not request.purpose:
            raise ValueError(
                f"Unsupported model routing purpose: {request.purpose!r}. "
                "Purpose must be a non-empty string"
            )

        print(
            f"[MODEL_ROUTER] purpose={request.purpose} "
            f"agent={request.purpose} "
            f"model={request.model}"
        )

        payload: dict[str, Any] = {
            "model": request.model,
            "messages": request.messages,
        }
        if request.tools is not None:
            payload["tools"] = request.tools
        if request.tool_choice is not None:
            payload["tool_choice"] = request.tool_choice
        payload.update(request.kwargs)

        response = await request.client.chat.completions.create(**payload)
        result = ModelCallResult(request=request, response=response)
        return result.response
