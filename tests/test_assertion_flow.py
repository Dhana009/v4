from __future__ import annotations

import asyncio
from types import SimpleNamespace

import agent as agent_module
from agent import AgentLoop


class FakeLocator:
    def __init__(self, inner_text_values: list[str] | None = None) -> None:
        self._inner_text_values = list(inner_text_values or [])
        self._last_inner_text = ""
        self.inner_text_calls = 0
        self.text_content_calls = 0

    async def inner_text(self, timeout: int | None = None) -> str:
        self.inner_text_calls += 1
        if self._inner_text_values:
            self._last_inner_text = self._inner_text_values.pop(0)
        return self._last_inner_text

    async def text_content(self, timeout: int | None = None) -> str:
        self.text_content_calls += 1
        raise AssertionError("unexpected text_content call")


class FakeClock:
    def __init__(self) -> None:
        self.now = 0.0

    def time(self) -> float:
        return self.now


def _make_loop(monkeypatch, locator: object) -> AgentLoop:
    loop = AgentLoop.__new__(AgentLoop)
    monkeypatch.setattr(agent_module, "get_page", lambda: object())
    monkeypatch.setattr(
        AgentLoop,
        "_resolve_locator",
        lambda self, page, locator_string: SimpleNamespace(first=locator),
    )
    return loop


def _unexpected_expect(locator: object) -> object:
    raise AssertionError("unexpected expect call")


def test_has_text_normalizes_nbsp_and_repeated_whitespace(monkeypatch) -> None:
    locator = FakeLocator(["  Hello\u00a0   world\n\nagain  "])
    loop = _make_loop(monkeypatch, locator)
    monkeypatch.setattr(agent_module, "expect", _unexpected_expect)

    result = asyncio.run(
        loop._tool_action_assert(
            {
                "locator": 'get_by_label("Greeting")',
                "assertion": "has_text",
                "expected_value": "Hello world again",
                "timeout": 500,
            }
        )
    )

    assert result == {
        "success": True,
        "assertion": "has_text",
        "actual_text": "Hello world again",
        "expected_text": "Hello world again",
    }
    assert locator.inner_text_calls == 1
    assert locator.text_content_calls == 0


def test_has_text_retries_until_text_appears(monkeypatch) -> None:
    locator = FakeLocator(["", "  Ready\u00a0 now  "])
    fake_clock = FakeClock()
    loop = _make_loop(monkeypatch, locator)

    async def fake_sleep(delay: float) -> None:
        fake_clock.now += delay

    monkeypatch.setattr(agent_module.asyncio, "get_running_loop", lambda: fake_clock)
    monkeypatch.setattr(agent_module.asyncio, "sleep", fake_sleep)
    monkeypatch.setattr(agent_module, "expect", _unexpected_expect)

    result = asyncio.run(
        loop._tool_action_assert(
            {
                "locator": 'get_by_label("Greeting")',
                "assertion": "has_text",
                "expected_value": "Ready now",
                "timeout": 1000,
            }
        )
    )

    assert result == {
        "success": True,
        "assertion": "has_text",
        "actual_text": "Ready now",
        "expected_text": "Ready now",
    }
    assert locator.inner_text_calls == 2
    assert locator.text_content_calls == 0


def test_has_text_failure_includes_normalized_texts_when_available(monkeypatch) -> None:
    locator = FakeLocator(["  Alpha\u00a0Beta  "])
    loop = _make_loop(monkeypatch, locator)
    monkeypatch.setattr(agent_module, "expect", _unexpected_expect)

    result = asyncio.run(
        loop._tool_action_assert(
            {
                "locator": 'get_by_label("Greeting")',
                "assertion": "has_text",
                "expected_value": "Gamma",
                "timeout": 0,
            }
        )
    )

    assert result["success"] is False
    assert result["assertion"] == "has_text"
    assert result["actual_text"] == "Alpha Beta"
    assert result["expected_text"] == "Gamma"
    assert result["error"] == "Expected normalized text to contain 'Gamma', got 'Alpha Beta'"


def test_has_text_missing_expected_value_returns_structured_failure(monkeypatch) -> None:
    loop = _make_loop(monkeypatch, FakeLocator())
    monkeypatch.setattr(agent_module, "expect", _unexpected_expect)

    result = asyncio.run(
        loop._tool_action_assert(
            {
                "locator": 'get_by_label("Greeting")',
                "assertion": "has_text",
            }
        )
    )

    assert result == {
        "success": False,
        "error": "expected_value_required",
        "assertion": "has_text",
    }


def test_has_value_missing_expected_value_returns_structured_failure(monkeypatch) -> None:
    loop = _make_loop(monkeypatch, FakeLocator())
    monkeypatch.setattr(agent_module, "expect", _unexpected_expect)

    result = asyncio.run(
        loop._tool_action_assert(
            {
                "locator": 'get_by_label("Greeting")',
                "assertion": "has_value",
            }
        )
    )

    assert result == {
        "success": False,
        "error": "expected_value_required",
        "assertion": "has_value",
    }


def test_visible_assertion_path_still_succeeds(monkeypatch) -> None:
    locator = object()
    called = {}
    loop = _make_loop(monkeypatch, locator)

    class FakeExpectation:
        def __init__(self, actual_locator: object) -> None:
            called["locator"] = actual_locator

        async def to_be_visible(self, timeout: int | None = None) -> None:
            called["timeout"] = timeout

    monkeypatch.setattr(agent_module, "expect", lambda actual_locator: FakeExpectation(actual_locator))

    result = asyncio.run(
        loop._tool_action_assert(
            {
                "locator": 'get_by_label("Greeting")',
                "assertion": "visible",
                "timeout": 321,
            }
        )
    )

    assert result == {"success": True, "error": None}
    assert called == {"locator": locator, "timeout": 321}
