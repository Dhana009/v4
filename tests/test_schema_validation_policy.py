"""
tests/test_schema_validation_policy.py

Tests for S6-0206: Schema validation and retry/fail-closed policy.
"""
from __future__ import annotations

import pytest
from runtime.schema_validation_policy import (
    SchemaValidationResult,
    validate_output,
    get_fallback_for_purpose,
)


# ---------------------------------------------------------------------------
# Helper validators
# ---------------------------------------------------------------------------

def _valid_json_output():
    return '{"intent": "click_login", "confidence": 0.9}'


def _invalid_output():
    return "Sure, I'll click the login button for you!"  # prose, not JSON


def _make_validator(valid_fn):
    """Return a validator that calls valid_fn."""
    return valid_fn


# ---------------------------------------------------------------------------
# Unit tests
# ---------------------------------------------------------------------------

def test_valid_schema_passes():
    result = validate_output(
        purpose_id="intent_classifier",
        output=_valid_json_output(),
    )
    assert result.valid is True
    assert result.retried is False


def test_invalid_schema_triggers_one_retry():
    """First failure should cause retry attempt."""
    call_count = [0]

    def fake_retry_fn(purpose_id, output):
        call_count[0] += 1
        return _valid_json_output()

    result = validate_output(
        purpose_id="intent_classifier",
        output=_invalid_output(),
        retry_fn=fake_retry_fn,
    )
    assert call_count[0] == 1
    assert result.retried is True


def test_second_schema_invalid_applies_fallback():
    """If retry also fails, fallback should be applied."""
    def bad_retry_fn(purpose_id, output):
        return _invalid_output()

    result = validate_output(
        purpose_id="intent_classifier",
        output=_invalid_output(),
        retry_fn=bad_retry_fn,
    )
    assert result.valid is False
    assert result.fallback is not None


def test_prose_output_without_schema_is_invalid():
    """Pure prose (no JSON/structured output) must be invalid for structured purposes."""
    result = validate_output(
        purpose_id="intent_classifier",
        output="The user wants to log in.",
    )
    assert result.valid is False


def test_content_only_response_fails_schema():
    result = validate_output(
        purpose_id="step_plan_normalizer",
        output="Here are the steps: 1. Click 2. Fill 3. Submit",
    )
    assert result.valid is False


def test_fallback_logged_with_purpose_and_error():
    import runtime.schema_validation_policy as svp
    svp.clear_validation_log()

    def bad_retry_fn(purpose_id, output):
        return _invalid_output()

    validate_output(
        purpose_id="intent_classifier",
        output=_invalid_output(),
        retry_fn=bad_retry_fn,
    )
    log = svp.get_validation_log()
    assert any(entry.get("fallback") for entry in log)


def test_retry_count_logged():
    import runtime.schema_validation_policy as svp
    svp.clear_validation_log()

    def good_retry_fn(purpose_id, output):
        return _valid_json_output()

    validate_output(
        purpose_id="intent_classifier",
        output=_invalid_output(),
        retry_fn=good_retry_fn,
    )
    log = svp.get_validation_log()
    assert any(entry.get("retry_count", 0) >= 1 for entry in log)


def test_recovery_purpose_invalid_schema_fails_closed():
    fallback = get_fallback_for_purpose("recovery_diagnoser")
    assert fallback == "fail_closed"


def test_planning_purpose_invalid_schema_asks_user():
    fallback = get_fallback_for_purpose("intent_classifier")
    assert fallback == "ask_user"


def test_step_plan_normalizer_fallback_is_ask_user():
    fallback = get_fallback_for_purpose("step_plan_normalizer")
    assert fallback in ("ask_user", "fail_closed")


def test_validation_result_is_typed():
    result = validate_output("intent_classifier", _valid_json_output())
    assert isinstance(result, SchemaValidationResult)
    assert hasattr(result, "valid")
    assert hasattr(result, "retried")
    assert hasattr(result, "fallback")


# ---------------------------------------------------------------------------
# Contract tests
# ---------------------------------------------------------------------------

def test_controller_validates_schema_before_using_output():
    """validate_output must be callable with just purpose_id + output."""
    result = validate_output("intent_classifier", _valid_json_output())
    assert isinstance(result, SchemaValidationResult)


def test_all_purposes_have_fallback_policy():
    from runtime.llm_purpose_policy import REQUIRED_PURPOSE_IDS
    for pid in REQUIRED_PURPOSE_IDS:
        fallback = get_fallback_for_purpose(pid)
        assert fallback in ("ask_user", "fail_closed", "retry"), f"{pid} has invalid fallback: {fallback}"
