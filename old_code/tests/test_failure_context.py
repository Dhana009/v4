"""
tests/test_failure_context.py

Tests for Cluster 11: Failure Context Artifact.
S6-1106.
"""
from __future__ import annotations

import pytest
from runtime.failure_context import (
    FailureContextArtifact,
    build_failure_context,
    NextLegalAction,
)


def test_failure_context_has_required_fields():
    ctx = build_failure_context(
        step_id="s1",
        expected="element [data-testid=btn] to be visible",
        actual="ElementNotFoundError",
        layer="browser",
        evidence={"page_url": "https://example.com"},
    )
    assert isinstance(ctx, FailureContextArtifact)
    assert ctx.step_id == "s1"
    assert ctx.expected is not None
    assert ctx.actual is not None
    assert ctx.layer is not None
    assert isinstance(ctx.next_actions, list)


def test_failure_context_next_actions_are_typed():
    ctx = build_failure_context(
        step_id="s1",
        expected="page loaded",
        actual="TimeoutError",
        layer="browser",
        evidence={},
    )
    for action in ctx.next_actions:
        assert isinstance(action, NextLegalAction)
        assert action.action is not None


def test_failure_context_layer_field():
    ctx = build_failure_context(
        step_id="s1",
        expected="ok",
        actual="NetworkError",
        layer="network",
        evidence={"url": "https://api.example.com"},
    )
    assert ctx.layer == "network"


def test_failure_context_element_not_found():
    ctx = build_failure_context(
        step_id="s2",
        expected="[data-testid=submit] visible",
        actual="ElementNotFoundError",
        layer="browser",
        evidence={"locator": "[data-testid=submit]"},
    )
    # Should suggest locator repair or ask_user
    action_names = [a.action for a in ctx.next_actions]
    assert any(a in action_names for a in ("repair_locator", "ask_user", "retry", "fail_closed"))


def test_failure_context_not_empty():
    ctx = build_failure_context(
        step_id="s3",
        expected="assertion passed",
        actual="AssertionError: expected Login got Sign In",
        layer="runtime",
        evidence={},
    )
    assert ctx.step_id == "s3"
    assert len(ctx.next_actions) > 0
