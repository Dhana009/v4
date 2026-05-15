"""
INT-DOM-001: Contract tests for deterministic locator handler wiring in agent.py.

Tests verify that _tool_locator_find and _tool_locator_validate produce the
enriched response fields from the DOM locator contract (ranked_candidates,
scope_suggestions, classification, status, match_count).

Strategy: mock _build_locator_candidates so tests don't need a full AgentLoop,
and patch get_page() to return a mock Playwright page.
"""
from __future__ import annotations

import asyncio
import types
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch


def _make_mock_page(count_map: dict[str, int]) -> Any:
    """Return a mock Playwright page where locator(...).count() returns from count_map."""
    page = MagicMock()

    def make_locator(selector: str) -> Any:
        loc = MagicMock()
        loc.count = AsyncMock(return_value=count_map.get(selector, 0))
        return loc

    page.locator = MagicMock(side_effect=make_locator)
    page.get_by_test_id = MagicMock(side_effect=lambda v: make_locator(f"get_by_test_id:{v}"))
    page.get_by_label = MagicMock(side_effect=lambda v, **kw: make_locator(f"get_by_label:{v}"))
    page.get_by_placeholder = MagicMock(side_effect=lambda v: make_locator(f"get_by_placeholder:{v}"))
    page.get_by_role = MagicMock(side_effect=lambda role, **kw: make_locator(f"get_by_role:{role}"))
    page.get_by_text = MagicMock(side_effect=lambda v, **kw: make_locator(f"get_by_text:{v}"))
    page.url = "http://localhost:9000/test.html"
    return page


def _run_locator_find(element_data: dict, count_map: dict[str, int], built_candidates: list[dict]) -> dict:
    """
    Run _tool_locator_find with a mocked page and pre-built candidates list.
    Bypasses _build_locator_candidates (which requires full AgentLoop internals).
    """
    import agent as agent_module

    page = _make_mock_page(count_map)

    with patch.object(agent_module, "get_page", return_value=page):
        stub = types.SimpleNamespace()
        real_cls = agent_module.AgentLoop

        for method_name in [
            "_tool_locator_find",
            "_resolve_locator",
            "_is_stable_locator_strategy",
            "_match_tool_locator_call",
            "_match_tool_locator_text",
            "_match_tool_locator_role",
        ]:
            method = getattr(real_cls, method_name)
            setattr(stub, method_name, method.__get__(stub, type(stub)))

        # Bypass _build_locator_candidates to avoid full AgentLoop dependency
        stub._build_locator_candidates = MagicMock(return_value=built_candidates)

        return asyncio.run(stub._tool_locator_find({"element_data": element_data}))


def _run_locator_validate(locator: str, count_map: dict[str, int], expected_value: Any = None) -> dict:
    """Run _tool_locator_validate with a mocked page."""
    import agent as agent_module

    page = _make_mock_page(count_map)

    with patch.object(agent_module, "get_page", return_value=page):
        stub = types.SimpleNamespace()
        real_cls = agent_module.AgentLoop

        for method_name in [
            "_tool_locator_validate",
            "_resolve_locator",
            "_match_tool_locator_call",
            "_match_tool_locator_text",
            "_match_tool_locator_role",
        ]:
            method = getattr(real_cls, method_name)
            setattr(stub, method_name, method.__get__(stub, type(stub)))

        args: dict[str, Any] = {"locator": locator}
        if expected_value is not None:
            args["expected_value"] = expected_value
        return asyncio.run(stub._tool_locator_validate(args))


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_locator_find_handler_returns_ranked_candidates() -> None:
    """_tool_locator_find must return a ranked_candidates list on success."""
    element_data = {
        "id": "submit-btn",
        "candidates": [
            {"candidate_id": "c0", "locator": "#submit-btn", "text": "Submit", "scope": "form"},
        ],
    }
    built = [{"locator": "#submit-btn", "strategy": "id"}]
    result = _run_locator_find(element_data, {"#submit-btn": 1}, built)

    assert result["found"] is True
    assert "ranked_candidates" in result, "ranked_candidates missing from locator_find success response"
    assert isinstance(result["ranked_candidates"], list)


def test_locator_validate_handler_returns_classification() -> None:
    """_tool_locator_validate must return classification, status, and match_count for unique match."""
    result = _run_locator_validate("#unique-el", {"#unique-el": 1})

    assert "classification" in result, "classification missing from locator_validate response"
    assert "status" in result, "status missing from locator_validate response"
    assert "match_count" in result, "match_count missing from locator_validate response"
    assert result["valid"] is True
    assert result["match_count"] == 1
    assert result["classification"] == "locator_unique"
    assert result["status"] == "unique"


def test_scope_candidates_invoked_on_multiple_match() -> None:
    """When no unique match is found, response must include scope_suggestions."""
    element_data = {
        "candidates": [
            {"candidate_id": "c0", "locator": ".btn", "text": "Click me", "scope": "section"},
        ],
    }
    # All built candidates match multiple — no unique found
    built = [{"locator": ".btn", "strategy": "css"}]
    result = _run_locator_find(element_data, {".btn": 2}, built)

    assert result["found"] is False
    assert "scope_suggestions" in result, "scope_suggestions missing when no unique match found"


def test_unique_deterministic_candidate_does_not_need_llm_locator_reasoning() -> None:
    """A unique match must not produce scope_suggestions or needs_clarification=True."""
    element_data = {
        "id": "hero-cta",
        "candidates": [
            {"candidate_id": "c0", "locator": "#hero-cta", "text": "Get Started", "scope": "main"},
        ],
    }
    built = [{"locator": "#hero-cta", "strategy": "id"}]
    result = _run_locator_find(element_data, {"#hero-cta": 1}, built)

    assert result["found"] is True
    assert not result.get("scope_suggestions"), "Unique match should not produce scope_suggestions"
    assert not result.get("needs_clarification", False), "Unique match should not flag needs_clarification"


def test_locator_validate_not_found_returns_not_found_classification() -> None:
    """When locator resolves 0 matches, classification must be locator_not_found."""
    result = _run_locator_validate("#ghost-element", {})

    assert result["valid"] is False
    assert result["match_count"] == 0
    assert result["classification"] == "locator_not_found"
    assert result["status"] == "none"
