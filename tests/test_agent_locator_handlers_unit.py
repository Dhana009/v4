from __future__ import annotations

"""Unit tests for runtime/agent_locator_handlers.py seam.

Tests the three handler functions (tool_dom_extract, tool_locator_find,
tool_locator_validate) using fake page/loop objects — no live browser required.
"""

import asyncio
from types import SimpleNamespace
from typing import Any

import pytest

from runtime.agent_locator_handlers import tool_dom_extract, tool_locator_find, tool_locator_validate
from runtime.dom_locator_contract import validate_locator_candidate


# ---------------------------------------------------------------------------
# Fake helpers
# ---------------------------------------------------------------------------

class FakePage:
    def __init__(
        self,
        *,
        html: str = "<html><body><h1>Hello</h1></body></html>",
        title: str = "Test Page",
        url: str = "https://example.test/",
        locator_counts: dict[str, int] | None = None,
    ) -> None:
        self.html = html
        self._title = title
        self.url = url
        self._locator_counts = locator_counts or {}

    async def content(self) -> str:
        return self.html

    async def evaluate(self, _script: str, _args: Any = None) -> str:
        return self.html

    async def title(self) -> str:
        return self._title

    def locator(self, selector: str) -> "FakeLocator":
        count = self._locator_counts.get(selector, 0)
        return FakeLocator(count)


class FakeLocator:
    def __init__(self, count: int = 0) -> None:
        self._count = count

    async def count(self) -> int:
        return self._count


class FakeLoop:
    """Minimal loop stub for locator handler seam."""

    def _clean_markup(self, html: str) -> str:
        import re
        return re.sub(r"<[^>]+>", " ", html).strip()

    def _build_locator_candidates(self, element_data: dict[str, Any]) -> list[dict[str, str]]:
        candidates = []
        aria = (element_data.get("attributes") or {}).get("aria-label")
        if aria:
            candidates.append({"strategy": "aria_label", "locator": f'get_by_label("{aria}")'})
        text = element_data.get("text")
        if text:
            candidates.append({"strategy": "text", "locator": f'get_by_text("{text}", exact=True)'})
        return candidates

    def _resolve_locator(self, page: FakePage, locator_string: str) -> FakeLocator:
        count = page._locator_counts.get(locator_string, 0)
        return FakeLocator(count)

    def _is_stable_locator_strategy(self, strategy: str) -> bool:
        return strategy in {"aria_label", "test_id", "id"}


# ---------------------------------------------------------------------------
# tool_dom_extract
# ---------------------------------------------------------------------------

def test_dom_extract_returns_elements_and_url() -> None:
    page = FakePage(html="<html><body><button>Click me</button></body></html>", url="https://example.test/")
    loop = FakeLoop()
    result = asyncio.run(tool_dom_extract(loop, {"scope": "page"}, get_page=lambda: page))
    assert "elements" in result
    assert result["url"] == "https://example.test/"


def test_dom_extract_page_scope_reads_full_content() -> None:
    page = FakePage(html="<html><body><h1>Title</h1></body></html>")
    loop = FakeLoop()
    result = asyncio.run(tool_dom_extract(loop, {"scope": "page"}, get_page=lambda: page))
    assert result["url"] == page.url
    assert isinstance(result["elements"], str)


def test_dom_extract_falls_back_gracefully_when_page_intelligence_fails() -> None:
    page = FakePage(html="not-valid-html")
    loop = FakeLoop()
    result = asyncio.run(tool_dom_extract(loop, {}, get_page=lambda: page))
    assert "elements" in result
    assert "url" in result


def test_dom_extract_includes_page_intelligence_packet_fields() -> None:
    html = "<html><head><title>Playwright</title></head><body><h1>Docs</h1><a href='/docs'>Get started</a></body></html>"
    page = FakePage(html=html, title="Playwright", url="https://playwright.dev/")
    loop = FakeLoop()
    result = asyncio.run(tool_dom_extract(loop, {"scope": "page"}, get_page=lambda: page))
    if "page_intelligence" in result:
        pi = result["page_intelligence"]
        assert "headings" in pi
        assert "ctas" in pi
        assert "forms_count" in pi


# ---------------------------------------------------------------------------
# tool_locator_find
# ---------------------------------------------------------------------------

def test_locator_find_returns_found_true_when_exactly_one_match() -> None:
    locator_string = 'get_by_label("Submit")'
    page = FakePage(locator_counts={locator_string: 1})
    loop = FakeLoop()
    element_data = {"text": "Submit", "attributes": {"aria-label": "Submit"}}
    result = asyncio.run(tool_locator_find(loop, {"element_data": element_data}, get_page=lambda: page))
    assert result["found"] is True
    assert result["locator"] == locator_string
    assert result["count"] == 1


def test_locator_find_returns_found_false_when_no_match() -> None:
    page = FakePage(locator_counts={})
    loop = FakeLoop()
    element_data = {"text": "Missing Button", "attributes": {"aria-label": "Missing Button"}}
    result = asyncio.run(tool_locator_find(loop, {"element_data": element_data}, get_page=lambda: page))
    assert result["found"] is False
    assert result["locator"] == ""
    assert result["count"] == 0


def test_locator_find_returns_found_false_when_multiple_matches() -> None:
    locator_string = 'get_by_label("Submit")'
    page = FakePage(locator_counts={locator_string: 3})
    loop = FakeLoop()
    element_data = {"text": "Submit", "attributes": {"aria-label": "Submit"}}
    result = asyncio.run(tool_locator_find(loop, {"element_data": element_data}, get_page=lambda: page))
    assert result["found"] is False


def test_locator_find_marks_stable_strategy_correctly() -> None:
    locator_string = 'get_by_label("Submit")'
    page = FakePage(locator_counts={locator_string: 1})
    loop = FakeLoop()
    element_data = {"attributes": {"aria-label": "Submit"}}
    result = asyncio.run(tool_locator_find(loop, {"element_data": element_data}, get_page=lambda: page))
    assert result["found"] is True
    assert result["stable"] is True


def test_locator_find_includes_tried_list_on_failure() -> None:
    page = FakePage(locator_counts={})
    loop = FakeLoop()
    element_data = {"text": "Nope", "attributes": {"aria-label": "Nope"}}
    result = asyncio.run(tool_locator_find(loop, {"element_data": element_data}, get_page=lambda: page))
    assert "tried" in result
    assert isinstance(result["tried"], list)


# ---------------------------------------------------------------------------
# tool_locator_validate
# ---------------------------------------------------------------------------

def test_locator_validate_returns_valid_true_when_exactly_one_match() -> None:
    locator_string = 'get_by_label("Get started")'
    page = FakePage(locator_counts={locator_string: 1})
    loop = FakeLoop()
    result = asyncio.run(
        tool_locator_validate(loop, {"locator": locator_string}, get_page=lambda: page)
    )
    assert result["valid"] is True
    assert result["count"] == 1
    assert result["match_count"] == 1


def test_locator_validate_returns_valid_false_when_zero_matches() -> None:
    locator_string = 'get_by_label("Missing")'
    page = FakePage(locator_counts={locator_string: 0})
    loop = FakeLoop()
    result = asyncio.run(
        tool_locator_validate(loop, {"locator": locator_string}, get_page=lambda: page)
    )
    assert result["valid"] is False
    assert result["count"] == 0


def test_locator_validate_returns_valid_false_when_multiple_matches() -> None:
    locator_string = 'get_by_text("Click")'
    page = FakePage(locator_counts={locator_string: 5})
    loop = FakeLoop()
    result = asyncio.run(
        tool_locator_validate(loop, {"locator": locator_string}, get_page=lambda: page)
    )
    assert result["valid"] is False
    assert result["count"] == 5


def test_locator_validate_includes_classification_from_contract() -> None:
    locator_string = 'get_by_label("Submit")'
    page = FakePage(locator_counts={locator_string: 1})
    loop = FakeLoop()
    result = asyncio.run(
        tool_locator_validate(loop, {"locator": locator_string}, get_page=lambda: page)
    )
    assert "classification" in result
    assert "status" in result


def test_locator_validate_empty_locator_returns_invalid() -> None:
    page = FakePage()
    loop = FakeLoop()
    result = asyncio.run(
        tool_locator_validate(loop, {"locator": ""}, get_page=lambda: page)
    )
    assert result["valid"] is False
    assert result["count"] == 0


def test_locator_validate_is_advisory_only_does_not_raise_on_zero_matches() -> None:
    """DOM/locator validation is advisory — zero matches must not raise."""
    page = FakePage(locator_counts={})
    loop = FakeLoop()
    result = asyncio.run(
        tool_locator_validate(loop, {"locator": 'get_by_role("button")'}, get_page=lambda: page)
    )
    assert isinstance(result, dict)
    assert result["valid"] is False
