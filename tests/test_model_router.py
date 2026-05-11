from __future__ import annotations

import asyncio
from types import SimpleNamespace

import pytest

from runtime.model_router import ModelRouter, resolve_model_name


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
