"""
E2 — typed state-card event contracts.

Plan ref: .tasks-md/Planning/S7-CROSS-LAYER-COMPLETION-PLAN.md Backend Seam B2.

These tests pin schema + redaction for the four runtime state-card events
BEFORE wiring the builders:

  - no_browser           (browser_unavailable advisory)
  - api_key_required     (config_required advisory; never carries the key)
  - human_input_required (otp / password / browser_prompt; sensitive=true)
  - e2e_pending          (acceptance pending; advisory only)

Sprint 7 ships builders + frontend cards. Backend emission lives in later
batches once safe detection seams exist (the current lifespan crashes when
the key/browser is missing, so there is no mid-session emission point yet).

Security gates (matrix S1, S2, S9 in the plan):
  - api_key_required payload must NEVER carry the actual key.
  - human_input_required marks payload sensitive=true so the frontend
    refuses to ship it through any LLM context.
  - all four events route through redact_payload to strip stray secrets.
"""
from __future__ import annotations

import pytest

from runtime.event_contracts import (
    BACKEND_EVENT_SCHEMA_VERSION,
    build_api_key_required_event,
    build_e2e_pending_event,
    build_human_input_required_event,
    build_no_browser_event,
)
from runtime.redaction_policy import REDACTED_SENTINEL


# --------------------------------------------------------------------------- #
# no_browser
# --------------------------------------------------------------------------- #
def test_no_browser_event_minimal_shape():
    event = build_no_browser_event(reason="not_launched")
    assert event["type"] == "no_browser"
    assert event["schema_version"] == BACKEND_EVENT_SCHEMA_VERSION
    payload = event["payload"]
    assert payload["reason"] == "not_launched"
    # Defaults
    assert payload["recoverable"] is True
    assert payload["message"]


def test_no_browser_event_carries_optional_fields():
    event = build_no_browser_event(
        reason="crashed",
        recoverable=False,
        current_url="https://example.com/app",
        message="Browser context crashed; please relaunch.",
        suggested_action="relaunch_browser",
    )
    payload = event["payload"]
    assert payload["reason"] == "crashed"
    assert payload["recoverable"] is False
    assert payload["current_url"] == "https://example.com/app"
    assert payload["suggested_action"] == "relaunch_browser"


def test_no_browser_event_rejects_blank_reason():
    with pytest.raises(ValueError):
        build_no_browser_event(reason="")


# --------------------------------------------------------------------------- #
# api_key_required
# --------------------------------------------------------------------------- #
def test_api_key_required_event_minimal_shape():
    event = build_api_key_required_event(provider="openai")
    payload = event["payload"]
    assert event["type"] == "api_key_required"
    assert payload["provider"] == "openai"
    assert payload["reason"] == "missing"  # default
    assert payload["message"]


@pytest.mark.parametrize("reason", ["missing", "invalid", "quota_exhausted"])
def test_api_key_required_event_accepts_known_reasons(reason):
    event = build_api_key_required_event(provider="openai", reason=reason)
    assert event["payload"]["reason"] == reason


def test_api_key_required_event_rejects_unknown_reason():
    with pytest.raises(ValueError):
        build_api_key_required_event(provider="openai", reason="bogus")


def test_api_key_required_event_never_carries_the_key():
    """S1: builder strips any field that looks like a secret."""
    event = build_api_key_required_event(
        provider="openai",
        # Caller mistakenly passes a key via setup_hint; builder must strip.
        setup_hint={"api_key": "sk-leak", "url": "https://platform.openai.com/keys"},
        purpose="journey_planner",
    )
    payload = event["payload"]
    hint = payload["setup_hint"]
    assert hint.get("api_key") == REDACTED_SENTINEL
    assert hint.get("url") == "https://platform.openai.com/keys"
    assert payload["purpose"] == "journey_planner"


def test_api_key_required_event_missing_config_keys_lists_names_only():
    event = build_api_key_required_event(
        provider="openai",
        missing_config_keys=["OPENAI_API_KEY", "OPENAI_BASE_URL"],
    )
    payload = event["payload"]
    assert payload["missing_config_keys"] == ["OPENAI_API_KEY", "OPENAI_BASE_URL"]
    # Sanity: no actual value smuggled in
    for value in payload["missing_config_keys"]:
        assert value.isupper() or "_" in value
        assert not value.startswith("sk-")


# --------------------------------------------------------------------------- #
# human_input_required (otp / password / browser_prompt)
# --------------------------------------------------------------------------- #
def test_human_input_required_event_minimal_shape():
    event = build_human_input_required_event(
        input_type="otp",
        prompt="Enter the 6-digit code from your authenticator.",
        correlation_id="hin-001",
    )
    payload = event["payload"]
    assert event["type"] == "human_input_required"
    assert payload["input_type"] == "otp"
    assert payload["sensitive"] is True
    assert payload["redaction_required"] is True
    assert payload["correlation_id"] == "hin-001"


@pytest.mark.parametrize(
    "input_type",
    ["otp", "password", "file_picker", "browser_prompt", "unknown"],
)
def test_human_input_required_event_accepts_known_input_types(input_type):
    event = build_human_input_required_event(
        input_type=input_type, prompt="x", correlation_id="hin-x"
    )
    assert event["payload"]["input_type"] == input_type


def test_human_input_required_event_rejects_unknown_input_type():
    with pytest.raises(ValueError):
        build_human_input_required_event(
            input_type="ssn", prompt="x", correlation_id="hin-bad"
        )


def test_human_input_required_event_redacts_smuggled_secret_in_prompt_fields():
    """S2: even if upstream caller passes a value, builder must redact it."""
    event = build_human_input_required_event(
        input_type="otp",
        prompt="Enter your code",
        correlation_id="hin-002",
        # Deliberately attempt to leak via metadata
        metadata={"password": "hunter2", "origin": "auth.example.com"},
    )
    payload = event["payload"]
    metadata = payload["metadata"]
    assert metadata["password"] == REDACTED_SENTINEL
    assert metadata["origin"] == "auth.example.com"


def test_human_input_required_event_origin_is_safe_string_when_present():
    event = build_human_input_required_event(
        input_type="browser_prompt",
        prompt="Please confirm in your browser.",
        correlation_id="hin-003",
        origin="https://login.example.com",
    )
    payload = event["payload"]
    assert payload["origin"] == "https://login.example.com"


# --------------------------------------------------------------------------- #
# e2e_pending
# --------------------------------------------------------------------------- #
def test_e2e_pending_event_minimal_shape():
    event = build_e2e_pending_event(reason="browser_warming")
    payload = event["payload"]
    assert event["type"] == "e2e_pending"
    assert payload["reason"] == "browser_warming"
    assert payload["pending_tests"] == []
    assert payload["last_result_summary"] is None


def test_e2e_pending_event_carries_pending_test_ids_only():
    event = build_e2e_pending_event(
        reason="acceptance_gate",
        pending_tests=["test_v4_panel_smoke", "test_mvp_001_lifecycle_smoke"],
        last_result_summary="2 / 2 passed",
        command_hint="python -m pytest tests/e2e -q",
    )
    payload = event["payload"]
    assert payload["pending_tests"] == [
        "test_v4_panel_smoke",
        "test_mvp_001_lifecycle_smoke",
    ]
    assert payload["last_result_summary"] == "2 / 2 passed"
    assert payload["command_hint"] == "python -m pytest tests/e2e -q"


def test_e2e_pending_event_rejects_blank_reason():
    with pytest.raises(ValueError):
        build_e2e_pending_event(reason="")


# --------------------------------------------------------------------------- #
# Cross-cutting
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize(
    "builder, args",
    [
        (build_no_browser_event, {"reason": "not_launched"}),
        (build_api_key_required_event, {"provider": "openai"}),
        (
            build_human_input_required_event,
            {"input_type": "otp", "prompt": "code", "correlation_id": "x"},
        ),
        (build_e2e_pending_event, {"reason": "acceptance_gate"}),
    ],
)
def test_state_card_event_envelopes_carry_event_id_and_timestamp(builder, args):
    event = builder(**args)
    assert event.get("event_id"), f"{builder.__name__} missing event_id"
    assert event.get("emitted_at"), f"{builder.__name__} missing emitted_at"
    assert event.get("source") == "server"
