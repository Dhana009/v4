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


@dataclass(slots=True)
class ModelResolution:
    requested: str | None
    resolved_model: str
    fallback_used: bool
    fallback_chain: tuple[str, ...]


def _normalize_model_name(value: Any) -> str | None:
    text = str(value or "").strip()
    return text or None


def _is_internal_model_class(value: Any) -> bool:
    return _normalize_model_name(value) in INTERNAL_MODEL_CLASSES


def _normalize_configured(configured: Mapping[str, str] | None) -> dict[str, str]:
    out: dict[str, str] = {}
    if isinstance(configured, Mapping):
        for key, value in configured.items():
            k = _normalize_model_name(key)
            v = _normalize_model_name(value)
            if k and v:
                out[k] = v
    return out


def resolve_model(
    model_class: str | None,
    configured_models: Mapping[str, str] | None = None,
    default_model: str | None = None,
    *,
    strict: bool = False,
) -> ModelResolution:
    configured = _normalize_configured(configured_models)
    fallback_model = (
        _normalize_model_name(default_model)
        or configured.get("main")
        or DEFAULT_MODEL_NAME
    )
    requested = _normalize_model_name(model_class)

    if requested is None:
        return ModelResolution(
            requested=None,
            resolved_model=fallback_model,
            fallback_used=True,
            fallback_chain=("default",),
        )

    configured_match = configured.get(requested)
    if configured_match:
        return ModelResolution(
            requested=requested,
            resolved_model=configured_match,
            fallback_used=False,
            fallback_chain=(f"configured[{requested}]",),
        )

    if requested == "main":
        return ModelResolution(
            requested="main",
            resolved_model=fallback_model,
            fallback_used=True,
            fallback_chain=("default",),
        )

    if requested in {"cheap", "debug"}:
        if strict:
            raise ValueError(
                f"Model class {requested!r} requested under strict routing "
                "but no configured model exists. Configure it explicitly."
            )
        main_model = configured.get("main") or fallback_model
        return ModelResolution(
            requested=requested,
            resolved_model=main_model,
            fallback_used=True,
            fallback_chain=(f"configured[{requested}]", "configured[main]", "default"),
        )

    if requested == fallback_model or requested.startswith("gpt-"):
        return ModelResolution(
            requested=requested,
            resolved_model=requested,
            fallback_used=False,
            fallback_chain=("explicit_provider_model",),
        )

    raise ValueError(
        f"Unsupported model class or provider model name: {requested!r}. "
        "Resolve it explicitly before calling the provider."
    )


def resolve_model_name(
    model_class: str | None,
    configured_models: Mapping[str, str] | None = None,
    default_model: str | None = None,
) -> str:
    return resolve_model(
        model_class,
        configured_models=configured_models,
        default_model=default_model,
    ).resolved_model


class ModelRouter:
    def __init__(
        self,
        configured_models: Mapping[str, str] | None = None,
        default_model: str | None = None,
        *,
        purpose_model_classes: Mapping[str, str] | None = None,
        strict: bool = False,
    ) -> None:
        self.configured_models = dict(configured_models or {})
        self.default_model = _normalize_model_name(default_model)
        self.purpose_model_classes = dict(purpose_model_classes or {})
        self.strict = bool(strict)
        self.last_resolution: ModelResolution | None = None

    def resolve(
        self,
        model_class: str | None,
        *,
        configured_models: Mapping[str, str] | None = None,
        default_model: str | None = None,
        strict: bool | None = None,
    ) -> ModelResolution:
        resolution = resolve_model(
            model_class,
            configured_models=configured_models or self.configured_models,
            default_model=default_model or self.default_model,
            strict=self.strict if strict is None else bool(strict),
        )
        self.last_resolution = resolution
        return resolution

    def resolve_model_name(
        self,
        model_class: str | None,
        *,
        configured_models: Mapping[str, str] | None = None,
        default_model: str | None = None,
    ) -> str:
        return self.resolve(
            model_class,
            configured_models=configured_models,
            default_model=default_model,
        ).resolved_model

    def resolve_for_purpose(self, purpose: str) -> ModelResolution:
        purpose_key = _normalize_model_name(purpose)
        if not purpose_key:
            raise ValueError("Purpose must be a non-empty string for resolve_for_purpose")
        model_class = self.purpose_model_classes.get(purpose_key)
        if model_class is None:
            raise ValueError(
                f"No model class registered for purpose {purpose_key!r}. "
                "Register the purpose explicitly before routing."
            )
        return self.resolve(model_class)

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
            resolution = self.resolve(normalized_model)
        else:
            resolution = self.resolve(normalized_model)
        resolved_model = resolution.resolved_model

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
            f"model={request.model} "
            f"requested={resolution.requested} "
            f"fallback_used={resolution.fallback_used} "
            f"chain={'|'.join(resolution.fallback_chain)}"
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
