from __future__ import annotations

import asyncio
from types import SimpleNamespace

import pytest

from runtime.model_router import (
    ModelResolution,
    ModelRouter,
    resolve_model,
    resolve_model_name,
)


class _FakeClient:
    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []
        self.chat = SimpleNamespace(completions=SimpleNamespace(create=self._create))

    async def _create(self, **payload):
        self.calls.append(dict(payload))
        return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content="ok"))])


def test_model_router_accepts_explicit_runtime_purpose() -> None:
    client = _FakeClient()

    response = asyncio.run(
        ModelRouter().call(
            purpose="step_plan_normalizer",
            client=client,
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": "normalize this"}],
        )
    )

    assert response.choices[0].message.content == "ok"
    assert client.calls[0]["model"] == "gpt-4o-mini"


def test_resolve_model_name_maps_main_to_default_provider_model() -> None:
    assert resolve_model_name("main") == "gpt-4o-mini"


def test_resolve_model_name_cheap_falls_back_to_main_provider_model() -> None:
    assert resolve_model_name("cheap") == "gpt-4o-mini"


def test_resolve_model_name_prefers_configured_main_model() -> None:
    assert resolve_model_name(
        "main",
        configured_models={"main": "custom-main"},
        default_model="gpt-4o-mini",
    ) == "custom-main"


def test_resolve_model_name_allows_explicit_provider_model_name() -> None:
    assert resolve_model_name("gpt-4o-mini") == "gpt-4o-mini"


def test_resolve_model_name_rejects_unknown_model_class() -> None:
    with pytest.raises(ValueError, match="Unsupported model class"):
        resolve_model_name("definitely-not-a-model-class")


def test_model_router_resolves_internal_main_model_to_provider_model() -> None:
    client = _FakeClient()

    response = asyncio.run(
        ModelRouter().call(
            purpose="step_plan_normalizer",
            client=client,
            model="main",
            messages=[{"role": "user", "content": "normalize this"}],
        )
    )

    assert response.choices[0].message.content == "ok"
    assert client.calls[0]["model"] == "gpt-4o-mini"


def test_resolve_model_debug_falls_back_to_main_when_not_configured() -> None:
    resolution = resolve_model("debug")
    assert resolution.resolved_model == "gpt-4o-mini"
    assert resolution.fallback_used is True
    assert "configured[debug]" in resolution.fallback_chain


def test_resolve_model_cheap_uses_explicit_configured_cheap_model() -> None:
    resolution = resolve_model(
        "cheap",
        configured_models={"main": "gpt-4o", "cheap": "gpt-4o-mini"},
    )
    assert resolution.resolved_model == "gpt-4o-mini"
    assert resolution.fallback_used is False
    assert resolution.fallback_chain == ("configured[cheap]",)


def test_resolve_model_strict_cheap_fails_when_unconfigured() -> None:
    with pytest.raises(ValueError, match="strict routing"):
        resolve_model("cheap", strict=True)


def test_resolve_model_strict_debug_fails_when_unconfigured() -> None:
    with pytest.raises(ValueError, match="strict routing"):
        resolve_model("debug", strict=True)


def test_resolve_model_returns_resolution_metadata() -> None:
    resolution = resolve_model("main", configured_models={"main": "gpt-4o"})
    assert isinstance(resolution, ModelResolution)
    assert resolution.requested == "main"
    assert resolution.resolved_model == "gpt-4o"
    assert resolution.fallback_used is False


def test_model_router_records_last_resolution() -> None:
    router = ModelRouter(configured_models={"main": "gpt-4o", "cheap": "gpt-4o-mini"})
    resolution = router.resolve("cheap")
    assert router.last_resolution is resolution
    assert resolution.resolved_model == "gpt-4o-mini"


def test_model_router_resolve_for_purpose_uses_registered_class() -> None:
    router = ModelRouter(
        configured_models={"main": "gpt-4o", "cheap": "gpt-4o-mini"},
        purpose_model_classes={
            "step_plan_normalizer": "main",
            "page_intelligence_summarizer": "cheap",
        },
    )
    assert router.resolve_for_purpose("step_plan_normalizer").resolved_model == "gpt-4o"
    assert (
        router.resolve_for_purpose("page_intelligence_summarizer").resolved_model
        == "gpt-4o-mini"
    )


def test_model_router_resolve_for_purpose_rejects_unknown_purpose() -> None:
    router = ModelRouter(purpose_model_classes={"step_plan_normalizer": "main"})
    with pytest.raises(ValueError, match="No model class registered"):
        router.resolve_for_purpose("never_registered_purpose")


def test_model_router_strict_mode_fails_cheap_without_config() -> None:
    router = ModelRouter(strict=True)
    with pytest.raises(ValueError, match="strict routing"):
        router.resolve("cheap")


def test_model_router_call_logs_resolution_metadata(capsys: pytest.CaptureFixture[str]) -> None:
    client = _FakeClient()
    router = ModelRouter(configured_models={"main": "gpt-4o", "cheap": "gpt-4o-mini"})

    asyncio.run(
        router.call(
            purpose="page_intelligence_summarizer",
            client=client,
            model="cheap",
            messages=[{"role": "user", "content": "summarize"}],
        )
    )

    out = capsys.readouterr().out
    assert "[MODEL_ROUTER]" in out
    assert "purpose=page_intelligence_summarizer" in out
    assert "model=gpt-4o-mini" in out
    assert "requested=cheap" in out
    assert "fallback_used=False" in out


def test_model_router_call_resolves_cheap_to_configured_cheap_provider() -> None:
    client = _FakeClient()
    router = ModelRouter(configured_models={"main": "gpt-4o", "cheap": "gpt-4o-mini"})

    asyncio.run(
        router.call(
            purpose="page_intelligence_summarizer",
            client=client,
            model="cheap",
            messages=[{"role": "user", "content": "summarize"}],
        )
    )
    assert client.calls[0]["model"] == "gpt-4o-mini"


def test_model_router_rejects_empty_purpose() -> None:
    client = _FakeClient()

    with pytest.raises(ValueError, match="Purpose must be a non-empty string"):
        asyncio.run(
            ModelRouter().call(
                purpose="",
                client=client,
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": "normalize this"}],
            )
        )
