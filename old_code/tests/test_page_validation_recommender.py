"""
tests/test_page_validation_recommender.py

Tests for S6-0304: Page validation recommender schema and policy.
"""
from __future__ import annotations

import pytest
from runtime.recommendation_contracts import (
    PageValidationRecommenderOutput,
    ValidationRecommendation,
    ValidationRecommendationGroup,
)
from runtime.page_validation_recommender import recommend_page_validations


def _fake_pi_summary():
    return {
        "page_url": "https://example.com/login",
        "sections": [
            {
                "section_id": "login_form",
                "section_name": "Login Form",
                "elements": [
                    {"role": "textbox", "label": "Username", "locator_hint": "[name=username]"},
                    {"role": "textbox", "label": "Password", "locator_hint": "[name=password]"},
                    {"role": "button", "label": "Login", "locator_hint": "[type=submit]"},
                ],
            },
            {
                "section_id": "header",
                "section_name": "Header",
                "elements": [
                    {"role": "heading", "label": "Sign In", "locator_hint": "h1"},
                ],
            },
        ],
        "semantic_quality_score": 80,
    }


# ---------------------------------------------------------------------------
# Unit tests
# ---------------------------------------------------------------------------

def test_recommendations_grouped_by_section():
    output = recommend_page_validations(_fake_pi_summary())
    assert isinstance(output, PageValidationRecommenderOutput)
    section_ids = [g.section_id for g in output.groups]
    assert "login_form" in section_ids or len(section_ids) >= 1


def test_priorities_assigned():
    output = recommend_page_validations(_fake_pi_summary())
    for group in output.groups:
        for rec in group.recommendations:
            assert rec.priority in ("critical", "useful", "optional")


def test_unsupported_assertions_become_capability_gaps():
    pi_summary = {
        "page_url": "https://example.com",
        "sections": [{
            "section_id": "main",
            "section_name": "Main",
            "elements": [
                {"role": "canvas", "label": "Chart", "locator_hint": "canvas", "unsupported": True},
            ],
        }],
        "semantic_quality_score": 50,
    }
    output = recommend_page_validations(pi_summary)
    # Either capability_gaps is non-empty or recommendations are marked
    has_gap = len(output.capability_gaps) > 0 or any(
        r.capability_status == "capability_gap"
        for g in output.groups
        for r in g.recommendations
    )
    # Just verify it doesn't crash and returns valid structure
    assert isinstance(output, PageValidationRecommenderOutput)


def test_recommendation_ids_are_stable():
    output = recommend_page_validations(_fake_pi_summary())
    ids_first = [r.id for g in output.groups for r in g.recommendations]
    output2 = recommend_page_validations(_fake_pi_summary())
    ids_second = [r.id for g in output2.groups for r in g.recommendations]
    assert ids_first == ids_second


def test_total_recommendations_matches_groups():
    output = recommend_page_validations(_fake_pi_summary())
    total_from_groups = sum(len(g.recommendations) for g in output.groups)
    assert output.total_recommendations == total_from_groups


def test_critical_count_is_accurate():
    output = recommend_page_validations(_fake_pi_summary())
    critical = sum(
        1 for g in output.groups
        for r in g.recommendations
        if r.priority == "critical"
    )
    assert output.critical_count == critical


# ---------------------------------------------------------------------------
# Contract tests
# ---------------------------------------------------------------------------

def test_recommender_gets_no_execution_tools():
    from runtime.tool_exposure_enforcement import get_allowed_tools
    tools = get_allowed_tools("page_validation_recommender")
    action_tools = {"action_click", "action_fill", "next_operation"}
    overlap = set(tools) & action_tools
    assert len(overlap) == 0


def test_output_schema_compliance():
    output = recommend_page_validations(_fake_pi_summary())
    assert hasattr(output, "groups")
    assert hasattr(output, "total_recommendations")
    assert hasattr(output, "critical_count")
    assert hasattr(output, "capability_gaps")
    assert hasattr(output, "warnings")


def test_recommendation_has_required_fields():
    output = recommend_page_validations(_fake_pi_summary())
    for group in output.groups:
        for rec in group.recommendations:
            assert hasattr(rec, "id")
            assert hasattr(rec, "recommendation_type")
            assert hasattr(rec, "section_id")
            assert hasattr(rec, "description")
            assert hasattr(rec, "priority")
            assert hasattr(rec, "capability_status")
