from __future__ import annotations

import asyncio
from types import SimpleNamespace

import pytest

from runtime.model_router import ModelRouter


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
