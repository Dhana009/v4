from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any


DEFAULT_MODEL_NAME = "gpt-4o-mini"
INTERNAL_MODEL_CLASSES = {"main", "cheap", "debug"}


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


def _normalize_model_name(value: Any) -> str | None:
    text = str(value or "").strip()
    return text or None


def _is_internal_model_class(value: Any) -> bool:
    return _normalize_model_name(value) in INTERNAL_MODEL_CLASSES


def resolve_model_name(
    model_class: str | None,
    configured_models: Mapping[str, str] | None = None,
    default_model: str | None = None,
) -> str:
    normalized_configured_models: dict[str, str] = {}
    if isinstance(configured_models, Mapping):
        for key, value in configured_models.items():
            key_name = _normalize_model_name(key)
            value_name = _normalize_model_name(value)
            if key_name and value_name:
                normalized_configured_models[key_name] = value_name

    fallback_model = (
        _normalize_model_name(default_model)
        or normalized_configured_models.get("main")
        or DEFAULT_MODEL_NAME
    )
    normalized_model_class = _normalize_model_name(model_class)
    if normalized_model_class is None:
        return fallback_model

    configured_model = normalized_configured_models.get(normalized_model_class)
    if configured_model:
        return configured_model

    if normalized_model_class == "main":
        return normalized_configured_models.get("main") or fallback_model
    if normalized_model_class == "cheap":
        return (
            normalized_configured_models.get("cheap")
            or normalized_configured_models.get("main")
            or fallback_model
        )
    if normalized_model_class == "debug":
        return (
            normalized_configured_models.get("debug")
            or normalized_configured_models.get("main")
            or fallback_model
        )
    if normalized_model_class == fallback_model or normalized_model_class.startswith("gpt-"):
        return normalized_model_class

    raise ValueError(
        f"Unsupported model class or provider model name: {normalized_model_class!r}. "
        "Resolve it explicitly before calling the provider."
    )


class ModelRouter:
    def __init__(
        self,
        configured_models: Mapping[str, str] | None = None,
        default_model: str | None = None,
    ) -> None:
        self.configured_models = dict(configured_models or {})
        self.default_model = _normalize_model_name(default_model)

    def resolve_model_name(
        self,
        model_class: str | None,
        *,
        configured_models: Mapping[str, str] | None = None,
        default_model: str | None = None,
    ) -> str:
        return resolve_model_name(
            model_class,
            configured_models=configured_models or self.configured_models,
            default_model=default_model or self.default_model,
        )

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
        normalized_model = _normalize_model_name(model)
        if _is_internal_model_class(normalized_model) or normalized_model is None:
            resolved_model = self.resolve_model_name(normalized_model)
        else:
            resolved_model = normalized_model
        request = ModelCallRequest(
            purpose=str(purpose or "").strip(),
            client=client,
            model=resolved_model,
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
