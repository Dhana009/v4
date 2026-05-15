"""
tests/test_locator_strength_annotator.py

Pass 4b-1 — deterministic selector-string locator strength classifier and
plan_ready step annotator. No LLM, no DOM access.
"""
from __future__ import annotations

import pytest

from runtime.locator_intelligence import (
    LocatorStrength,
    annotate_plan_steps_with_locator_kind,
    classify_locator_strength_from_selector,
)


# ---------------------------------------------------------------------------
# classify_locator_strength_from_selector
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "selector",
    [
        '[data-testid="submit-btn"]',
        'data-testid=submit',
        'getByTestId("submit")',
        'getByRole("button", { name: "Submit" })',
        'getByLabel("Email")',
        'getByAltText("logo")',
        'getByPlaceholder("you@example.com")',
        'getByTitle("Close")',
        "#main-id",
        '[data-cy="card"]',
    ],
)
def test_selector_classified_strong(selector):
    a = classify_locator_strength_from_selector(selector)
    assert a.strength == LocatorStrength.STRONG
    assert a.kind == "ok"
    assert a.reason


@pytest.mark.parametrize(
    "selector",
    [
        '[aria-label="Submit"]',
        '[name="username"]',
        'getByText("Get started")',
        'div:has-text("Pricing")',
        '[placeholder="search"]',
    ],
)
def test_selector_classified_medium(selector):
    a = classify_locator_strength_from_selector(selector)
    assert a.strength == LocatorStrength.MEDIUM
    assert a.kind == "med"


@pytest.mark.parametrize(
    "selector",
    [
        "div:nth-child(2)",
        ".ws-plan > .ws-plan-tag",
        "//button[2]",
        "xpath=//button[1]",
        ".btn",
    ],
)
def test_selector_classified_weak(selector):
    a = classify_locator_strength_from_selector(selector)
    assert a.strength == LocatorStrength.WEAK
    assert a.kind == "warn"
    assert a.reason


@pytest.mark.parametrize("selector", [None, "", "   "])
def test_missing_locator_classified_unknown(selector):
    a = classify_locator_strength_from_selector(selector)
    assert a.strength is None
    assert a.kind == "unknown"
    assert a.reason == "no locator"


def test_classifier_is_pure_no_side_effects():
    """No DOM access, no LLM call: calling twice yields the same result."""
    a1 = classify_locator_strength_from_selector('[data-testid="x"]')
    a2 = classify_locator_strength_from_selector('[data-testid="x"]')
    assert a1.strength == a2.strength
    assert a1.kind == a2.kind
    assert a1.reason == a2.reason


# ---------------------------------------------------------------------------
# annotate_plan_steps_with_locator_kind
# ---------------------------------------------------------------------------

def test_annotator_adds_strong_metadata_to_step():
    payload = {
        "plan_id": "p1",
        "steps": [
            {"step_id": "s1", "description": "click Submit", "locator": '[data-testid="submit"]'},
        ],
    }
    annotated = annotate_plan_steps_with_locator_kind(payload)
    step = annotated["steps"][0]
    assert step["locator_kind"] == "ok"
    assert step["locator_strength"] == "strong"
    assert step["locator_reason"]


def test_annotator_marks_weak_locator_step_with_reason():
    payload = {"steps": [{"step_id": "s2", "locator": "div:nth-child(2)"}]}
    annotated = annotate_plan_steps_with_locator_kind(payload)
    step = annotated["steps"][0]
    assert step["locator_kind"] == "warn"
    assert step["locator_strength"] == "weak"
    assert "positional" in step["locator_reason"].lower() or "nth-child" in step["locator_reason"]


def test_annotator_marks_missing_locator_unknown():
    payload = {"steps": [{"step_id": "s3", "description": "section step"}]}
    annotated = annotate_plan_steps_with_locator_kind(payload)
    step = annotated["steps"][0]
    assert step["locator_kind"] == "unknown"
    assert step["locator_strength"] == "unknown"


def test_annotator_does_not_clobber_backend_values():
    payload = {
        "steps": [
            {
                "step_id": "s4",
                "locator": "div:nth-child(2)",
                "locator_kind": "ok",  # backend already classified explicitly
                "locator_strength": "strong",
                "locator_reason": "verified by runtime",
            }
        ]
    }
    annotated = annotate_plan_steps_with_locator_kind(payload)
    step = annotated["steps"][0]
    assert step["locator_kind"] == "ok"
    assert step["locator_strength"] == "strong"
    assert step["locator_reason"] == "verified by runtime"


def test_annotator_reads_nested_locator_object():
    payload = {
        "steps": [
            {"step_id": "s5", "locator": {"value": 'getByRole("button", {name: "OK"})', "strategy": "role"}},
        ]
    }
    annotated = annotate_plan_steps_with_locator_kind(payload)
    step = annotated["steps"][0]
    assert step["locator_kind"] == "ok"
    assert step["locator_strength"] == "strong"


def test_annotator_handles_non_dict_payload_safely():
    assert annotate_plan_steps_with_locator_kind(None) is None
    assert annotate_plan_steps_with_locator_kind({"steps": "not a list"}) == {"steps": "not a list"}
    assert annotate_plan_steps_with_locator_kind({}) == {}


def test_annotator_skips_non_dict_step_entries():
    payload = {"steps": ["bad", None, 42, {"step_id": "ok", "locator": "#id"}]}
    annotated = annotate_plan_steps_with_locator_kind(payload)
    # malformed entries left untouched; good entry annotated
    assert annotated["steps"][3]["locator_kind"] == "ok"


def test_annotator_pulls_locator_from_element_info_as_fallback():
    payload = {
        "steps": [
            {"step_id": "s6", "element_info": {"locator": "div:nth-child(3)"}},
        ]
    }
    annotated = annotate_plan_steps_with_locator_kind(payload)
    step = annotated["steps"][0]
    assert step["locator_kind"] == "warn"
