from __future__ import annotations

"""Unit tests for runtime/deterministic_fast_path_gateway.py.

Tests the gateway decision logic — qualify/skip/fallback — using fake loop
and fake page objects. No live browser, no live LLM.
"""

import asyncio
from types import SimpleNamespace
from typing import Any

import pytest

from runtime.deterministic_fast_path import classify_fast_path, build_deterministic_plan
from runtime.deterministic_fast_path_gateway import attempt_deterministic_fast_path


# ---------------------------------------------------------------------------
# Fake helpers
# ---------------------------------------------------------------------------

class FakePage:
    def __init__(self, url: str = "https://example.test/", locator_counts: dict[str, int] | None = None) -> None:
        self.url = url
        self._locator_counts = locator_counts or {}

    def locator(self, selector: str) -> "FakeLocator":
        return FakeLocator(self._locator_counts.get(selector, 0))


class FakeLocator:
    def __init__(self, count: int = 0) -> None:
        self._count = count

    async def count(self) -> int:
        return self._count


class FakeLoop:
    def __init__(self, *, locator_count: int = 1, confirmed: bool = True) -> None:
        self._locator_count = locator_count
        self._confirmed = confirmed
        self.last_plan_ready_payload: dict[str, Any] | None = None
        self._plan_correction_messages: list[str] = []
        self._fast_path_executed = False

    def _normalize_space(self, text: str) -> str:
        import re
        return re.sub(r"\s+", " ", text).strip()

    def _derive_locator_from_step_context(self, step: dict[str, Any]) -> str:
        return str(step.get("locator") or "")

    def _resolve_locator(self, page: FakePage, locator: str) -> FakeLocator:
        return FakeLocator(self._locator_count)

    def _resolve_selected_element_info(self, element_info: dict[str, Any]) -> dict[str, Any]:
        return element_info or {}

    def _best_fast_path_target_label(self, step: dict[str, Any], action_verb: str) -> str:
        return str(step.get("element_name") or "")

    def _should_replace_fast_path_locator_with_text(self, action_verb: str, locator: str) -> bool:
        return False

    def _selected_element_text(self, element_info: dict[str, Any]) -> str:
        return str(element_info.get("text") or "")

    def _tool_string_escape(self, text: str) -> str:
        return text.replace('"', '\\"')

    async def _send_plan_ready_after_confirmation(self, payload: dict[str, Any]) -> dict[str, Any]:
        self.last_plan_ready_payload = payload
        if self._confirmed:
            return {"confirmed": True, "answer": "confirmed"}
        return {"confirmed": False, "correction": "use a different locator"}

    async def _execute_deterministic_fast_path_confirmed_plan(self) -> None:
        self._fast_path_executed = True

    def _append_plan_correction_message(
        self,
        correction: str,
        plan_id: str | None = None,
        target_step_id: str | None = None,
    ) -> None:
        self._plan_correction_messages.append(correction)


def _make_step(
    intent: str = "Click the submit button",
    locator: str = 'get_by_label("Submit")',
    step_id: str = "step-1",
) -> dict[str, Any]:
    return {
        "id": step_id,
        "intent": intent,
        "locator": locator,
        "element_name": "Submit",
    }


# ---------------------------------------------------------------------------
# classify_fast_path unit tests
# ---------------------------------------------------------------------------

def test_classify_fast_path_qualifies_simple_click() -> None:
    qualifies, reason = classify_fast_path(
        user_message="Click the submit button",
        locator_validated=True,
        locator_count=1,
    )
    assert qualifies is True
    assert "click" in reason


def test_classify_fast_path_qualifies_assert_visible() -> None:
    qualifies, reason = classify_fast_path(
        user_message="Assert that Get started is visible",
        locator_validated=True,
        locator_count=1,
    )
    assert qualifies is True
    assert "assert_visible" in reason


def test_classify_fast_path_qualifies_fill() -> None:
    qualifies, reason = classify_fast_path(
        user_message="Fill the email field",
        locator_validated=True,
        locator_count=1,
    )
    assert qualifies is True
    assert "fill" in reason


def test_classify_fast_path_rejects_compound_intent() -> None:
    qualifies, reason = classify_fast_path(
        user_message="Click submit and then verify the success message",
        locator_validated=True,
        locator_count=1,
    )
    assert qualifies is False
    assert "compound" in reason


def test_classify_fast_path_rejects_when_locator_not_unique() -> None:
    qualifies, reason = classify_fast_path(
        user_message="Click the button",
        locator_validated=False,
        locator_count=3,
    )
    assert qualifies is False
    assert "locator_not_unique" in reason


def test_classify_fast_path_rejects_unknown_action() -> None:
    qualifies, reason = classify_fast_path(
        user_message="Navigate to the docs page",
        locator_validated=True,
        locator_count=1,
    )
    assert qualifies is False
    assert "no_deterministic_action_verb" in reason


def test_classify_fast_path_rejects_multi_step_comma_pattern() -> None:
    qualifies, reason = classify_fast_path(
        user_message="Click submit, then verify success",
        locator_validated=True,
        locator_count=1,
    )
    assert qualifies is False


# ---------------------------------------------------------------------------
# build_deterministic_plan unit tests
# ---------------------------------------------------------------------------

def test_build_deterministic_plan_returns_plan_ready_shape() -> None:
    plan = build_deterministic_plan(
        user_message="Click the submit button",
        locator='get_by_label("Submit")',
        action_verb="click",
        step_id="step-1",
        target_label="Submit",
        fill_value=None,
        expected_text=None,
    )
    assert "plan_id" in plan
    assert "steps" in plan or "operations" in plan or "summary" in plan


def test_build_deterministic_plan_includes_locator() -> None:
    locator = 'get_by_label("Submit")'
    plan = build_deterministic_plan(
        user_message="Click the submit button",
        locator=locator,
        action_verb="click",
        step_id="step-1",
        target_label="Submit",
        fill_value=None,
        expected_text=None,
    )
    plan_str = str(plan)
    assert locator in plan_str or "Submit" in plan_str


# ---------------------------------------------------------------------------
# attempt_deterministic_fast_path gateway tests
# ---------------------------------------------------------------------------

def test_gateway_returns_false_for_multi_step_run() -> None:
    loop = FakeLoop()
    page = FakePage()
    steps = [_make_step(), _make_step(step_id="step-2")]
    result = asyncio.run(
        attempt_deterministic_fast_path(loop, steps, get_page=lambda: page)
    )
    assert result is False


def test_gateway_returns_false_when_no_locator_derivable() -> None:
    loop = FakeLoop()
    page = FakePage()
    step = {"id": "step-1", "intent": "Click the button", "locator": ""}
    result = asyncio.run(
        attempt_deterministic_fast_path(loop, [step], get_page=lambda: page)
    )
    assert result is False


def test_gateway_returns_false_when_locator_not_unique() -> None:
    loop = FakeLoop(locator_count=3)
    page = FakePage()
    result = asyncio.run(
        attempt_deterministic_fast_path(loop, [_make_step()], get_page=lambda: page)
    )
    assert result is False


def test_gateway_returns_false_when_intent_is_compound() -> None:
    loop = FakeLoop(locator_count=1)
    page = FakePage()
    step = _make_step(intent="Click submit and then verify the success message")
    result = asyncio.run(
        attempt_deterministic_fast_path(loop, [step], get_page=lambda: page)
    )
    assert result is False


def test_gateway_returns_true_and_executes_when_confirmed() -> None:
    loop = FakeLoop(locator_count=1, confirmed=True)
    page = FakePage()
    result = asyncio.run(
        attempt_deterministic_fast_path(loop, [_make_step()], get_page=lambda: page)
    )
    assert result is True
    assert loop._fast_path_executed is True


def test_gateway_returns_false_and_appends_correction_when_rejected() -> None:
    loop = FakeLoop(locator_count=1, confirmed=False)
    page = FakePage()
    result = asyncio.run(
        attempt_deterministic_fast_path(loop, [_make_step()], get_page=lambda: page)
    )
    assert result is False
    assert len(loop._plan_correction_messages) == 1
    assert "use a different locator" in loop._plan_correction_messages[0]


def test_gateway_does_not_call_llm_on_fast_path() -> None:
    """Fast path must never touch LLM — validated by absence of llm attribute access."""
    llm_called = []

    class StrictLoop(FakeLoop):
        @property
        def llm(self):
            llm_called.append("llm_accessed")
            return SimpleNamespace(messages=[], client=None)

    loop = StrictLoop(locator_count=1, confirmed=True)
    page = FakePage()
    asyncio.run(attempt_deterministic_fast_path(loop, [_make_step()], get_page=lambda: page))
    assert llm_called == [], "Fast path must not access LLM"
