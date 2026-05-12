"""
tests/test_journey_classifier.py

Tests for S6-0401: Full journey automation classifier and pipeline.
"""
from __future__ import annotations

import pytest
from runtime.journey_classifier import (
    JourneyClassification,
    IntentType,
    classify_journey_intent,
)


def test_broad_journey_request_classified_as_full_journey():
    result = classify_journey_intent("build a test for the login and checkout flow")
    assert result.intent_type == IntentType.FULL_JOURNEY_AUTOMATION


def test_single_action_not_classified_as_journey():
    result = classify_journey_intent("click the login button")
    assert result.intent_type != IntentType.FULL_JOURNEY_AUTOMATION


def test_upload_submit_identifies_missing_file():
    result = classify_journey_intent("upload a file and submit the form")
    assert result.requires_clarification or result.missing_fields


def test_unsupported_crm_api_marked_as_capability_risk():
    result = classify_journey_intent("validate the CRM API response and update Salesforce")
    assert result.has_capability_risks


def test_broad_journey_emits_clarification_not_execution():
    result = classify_journey_intent("automate the entire user registration journey")
    assert result.next_action in ("clarification_needed", "page_analysis_requested", "draft_plan_requested")
    assert result.next_action != "execution_started"


def test_missing_test_data_triggers_clarification():
    result = classify_journey_intent("fill the checkout form and pay")
    # Missing credit card test data → clarification or test_data_required
    assert result.next_action in ("clarification_needed", "test_data_required", "draft_plan_requested", "page_analysis_requested")


def test_result_is_typed():
    result = classify_journey_intent("run a smoke test on the dashboard")
    assert isinstance(result, JourneyClassification)
    assert hasattr(result, "intent_type")
    assert hasattr(result, "next_action")
    assert hasattr(result, "requires_clarification")
    assert hasattr(result, "missing_fields")
    assert hasattr(result, "has_capability_risks")


def test_full_journey_with_pages_list_can_request_draft_plan():
    result = classify_journey_intent(
        "test the login page and dashboard page",
        context={"target_pages": ["login", "dashboard"]},
    )
    assert result.next_action in ("draft_plan_requested", "page_analysis_requested", "clarification_needed")


def test_empty_intent_requires_clarification():
    result = classify_journey_intent("")
    assert result.requires_clarification is True


def test_intent_type_enum_values():
    assert IntentType.FULL_JOURNEY_AUTOMATION is not None
    assert IntentType.SINGLE_ACTION is not None
    assert IntentType.RECOMMENDATION_REQUEST is not None
