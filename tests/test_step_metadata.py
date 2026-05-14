"""
tests/test_step_metadata.py

Pass 4b-2 — deterministic step kind classifier and plan_ready annotator.
"""
from __future__ import annotations

import pytest

from runtime.step_metadata import (
    annotate_plan_steps_with_kind,
    classify_step_kind,
)


# ---------------------------------------------------------------------------
# classify_step_kind
# ---------------------------------------------------------------------------

def test_default_step_classified_atomic():
    step = {"step_id": "s1", "intent": "click Sign in"}
    assert classify_step_kind(step) == "atomic"


@pytest.mark.parametrize(
    "intent",
    [
        "Each pricing card has a CTA",
        "every row shows the user name",
        "For each link in the nav, verify the href",
        "All cards expose name + price + cta",
        "forEach button click and verify",
        "every option in dropdown",
    ],
)
def test_loop_intent_classified_loop(intent):
    step = {"step_id": "loop_step", "intent": intent}
    assert classify_step_kind(step) == "loop"


def test_section_classified_when_multiple_children():
    step = {
        "step_id": "sect",
        "intent": "Section: Pricing grid",
        "children": [
            {"description": "Count cards equals 3"},
            {"description": "Each card exposes name + price + cta"},
            {"description": "Pro card highlighted"},
        ],
    }
    assert classify_step_kind(step) == "section"


def test_single_child_does_not_promote_to_section():
    step = {
        "step_id": "fp",
        "intent": "click Get started",
        "children": [{"description": "click button"}],
    }
    assert classify_step_kind(step) == "atomic"


def test_loop_intent_with_children_prefers_section_when_multiple_children():
    """If the step has 2+ child operations, section wins over loop."""
    step = {
        "step_id": "sect_loop",
        "intent": "Each card",  # loop hint
        "children": [{"description": "a"}, {"description": "b"}],
    }
    assert classify_step_kind(step) == "section"


def test_malformed_step_classified_unknown():
    assert classify_step_kind(None) == "unknown"
    assert classify_step_kind("not a dict") == "unknown"
    assert classify_step_kind(42) == "unknown"
    assert classify_step_kind({}) == "unknown"


def test_classifier_is_deterministic():
    step = {"step_id": "s1", "intent": "every row matches"}
    a = classify_step_kind(step)
    b = classify_step_kind(step)
    assert a == b == "loop"


def test_classifier_does_not_call_llm(monkeypatch):
    """Smoke: classifier must be pure and not import openai/anthropic."""
    import sys
    pre = set(sys.modules.keys())
    classify_step_kind({"intent": "click X"})
    post = set(sys.modules.keys())
    assert not any(
        m.startswith(("openai", "anthropic"))
        for m in post - pre
    )


# ---------------------------------------------------------------------------
# annotate_plan_steps_with_kind
# ---------------------------------------------------------------------------

def test_annotator_classifies_atomic_step():
    payload = {"steps": [{"step_id": "s1", "intent": "click Submit"}]}
    annotated = annotate_plan_steps_with_kind(payload)
    assert annotated["steps"][0]["step_kind"] == "atomic"


def test_annotator_classifies_loop_step():
    payload = {"steps": [{"step_id": "s2", "intent": "Each pricing card has a CTA"}]}
    annotated = annotate_plan_steps_with_kind(payload)
    assert annotated["steps"][0]["step_kind"] == "loop"


def test_annotator_classifies_section_step():
    payload = {
        "steps": [
            {
                "step_id": "s3",
                "intent": "Section: Pricing grid",
                "children": [{"description": "a"}, {"description": "b"}],
            }
        ]
    }
    annotated = annotate_plan_steps_with_kind(payload)
    assert annotated["steps"][0]["step_kind"] == "section"


def test_annotator_preserves_explicit_valid_backend_kind():
    payload = {"steps": [{"step_id": "s4", "intent": "click X", "step_kind": "section"}]}
    annotated = annotate_plan_steps_with_kind(payload)
    assert annotated["steps"][0]["step_kind"] == "section"


def test_annotator_normalizes_invalid_backend_kind_to_unknown():
    """Invalid explicit value must be normalized; frontend must never read it raw."""
    payload = {"steps": [{"step_id": "s5", "intent": "click", "step_kind": "garbage"}]}
    annotated = annotate_plan_steps_with_kind(payload)
    assert annotated["steps"][0]["step_kind"] == "unknown"


def test_annotator_handles_non_dict_payload_safely():
    assert annotate_plan_steps_with_kind(None) is None
    assert annotate_plan_steps_with_kind({}) == {}
    assert annotate_plan_steps_with_kind({"steps": "nope"}) == {"steps": "nope"}


def test_annotator_skips_non_dict_step_entries():
    payload = {"steps": [None, 42, "bad", {"step_id": "ok", "intent": "click"}]}
    annotated = annotate_plan_steps_with_kind(payload)
    assert annotated["steps"][3]["step_kind"] == "atomic"


def test_annotator_does_not_disturb_locator_metadata():
    """Step kind annotator must not clobber locator_kind/locator_strength."""
    payload = {
        "steps": [
            {
                "step_id": "s6",
                "intent": "click Submit",
                "locator_kind": "ok",
                "locator_strength": "strong",
                "locator_reason": "uses data-testid",
            }
        ]
    }
    annotated = annotate_plan_steps_with_kind(payload)
    step = annotated["steps"][0]
    assert step["step_kind"] == "atomic"
    assert step["locator_kind"] == "ok"
    assert step["locator_strength"] == "strong"
    assert step["locator_reason"] == "uses data-testid"


def test_annotator_does_not_emit_other_kinds():
    """Output value is always one of the 4 allowed kinds."""
    payload = {
        "steps": [
            {"step_id": "a", "intent": "click"},
            {"step_id": "b", "intent": "Each card"},
            {"step_id": "c", "intent": "Section", "children": [{}, {}]},
            None,
            {"junk": True},
        ]
    }
    annotated = annotate_plan_steps_with_kind(payload)
    kinds = [s.get("step_kind") for s in annotated["steps"] if isinstance(s, dict)]
    for k in kinds:
        assert k in {"atomic", "loop", "section", "unknown"}
