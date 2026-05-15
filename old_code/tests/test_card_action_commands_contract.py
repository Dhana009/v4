"""
E3 — typed command contracts for wired LLM card actions.

Plan ref: .tasks-md/Planning/S7-CROSS-LAYER-COMPLETION-PLAN.md
  Backend Seams B3 (highlight_locator), B5 (switch_endpoint + registry).

The other three stubs land as honest UI changes only:
  - CardOffline "View log" routes to the existing Trace tab (frontend-only).
  - CardSchemaError "Edit plan manually" reuses the existing `correction`
    command (no new backend cmd).
  - CardSchemaError "Open raw response" toggles a local <pre> view of the
    redacted raw text the backend already passes via `rejection.detail.raw_response_redacted`.

These tests pin: command-type registration, payload shape, rejection on
malformed input, endpoint registry event shape + secret stripping.
"""
from __future__ import annotations

import pytest

from runtime.event_contracts import (
    BACKEND_EVENT_SCHEMA_VERSION,
    SUPPORTED_FRONTEND_COMMAND_TYPES,
    build_endpoint_registry_event,
    normalize_frontend_command,
)


# --------------------------------------------------------------------------- #
# highlight_locator
# --------------------------------------------------------------------------- #
def test_highlight_locator_is_registered_command_type():
    assert "highlight_locator" in SUPPORTED_FRONTEND_COMMAND_TYPES


def test_highlight_locator_command_canonical_envelope_accepted():
    command, rejection = normalize_frontend_command(
        {
            "type": "highlight_locator",
            "schema_version": "autoworkbench.command.v1",
            "command_id": "cmd-h1",
            "source": "frontend",
            "payload": {"candidate_id": "cand-2", "duration_ms": 1500},
        }
    )
    assert rejection is None
    assert command is not None
    assert command["type"] == "highlight_locator"
    assert command["payload"]["candidate_id"] == "cand-2"


def test_highlight_locator_legacy_envelope_accepted_for_compat():
    """Frontend may send the legacy short form during reconnects."""
    command, rejection = normalize_frontend_command(
        {"type": "highlight_locator", "candidate_id": "cand-3"}
    )
    assert rejection is None
    assert command is not None
    assert command["type"] == "highlight_locator"


# --------------------------------------------------------------------------- #
# switch_endpoint
# --------------------------------------------------------------------------- #
def test_switch_endpoint_is_registered_command_type():
    assert "switch_endpoint" in SUPPORTED_FRONTEND_COMMAND_TYPES


def test_switch_endpoint_canonical_envelope_accepted():
    command, rejection = normalize_frontend_command(
        {
            "type": "switch_endpoint",
            "schema_version": "autoworkbench.command.v1",
            "command_id": "cmd-se-1",
            "source": "frontend",
            "payload": {"endpoint_id": "local"},
        }
    )
    assert rejection is None
    assert command is not None
    assert command["payload"]["endpoint_id"] == "local"


# --------------------------------------------------------------------------- #
# endpoint_registry event
# --------------------------------------------------------------------------- #
def test_endpoint_registry_event_minimal_shape():
    event = build_endpoint_registry_event(
        active_id="local",
        entries=[{"id": "local", "label": "Local", "base_url": "ws://127.0.0.1:8765", "kind": "local"}],
    )
    assert event["type"] == "endpoint_registry"
    assert event["schema_version"] == BACKEND_EVENT_SCHEMA_VERSION
    payload = event["payload"]
    assert payload["active_id"] == "local"
    assert payload["entries"][0]["id"] == "local"
    assert payload["entries"][0]["base_url"] == "ws://127.0.0.1:8765"


def test_endpoint_registry_event_strips_secret_fields_per_entry():
    """B5 security: registry must NEVER expose tokens/keys embedded in URLs or fields."""
    event = build_endpoint_registry_event(
        active_id="local",
        entries=[
            {
                "id": "local",
                "label": "Local",
                "base_url": "ws://127.0.0.1:8765",
                # rogue extra fields a future contributor might add by mistake:
                "api_key": "sk-leak",
                "token": "ghp_leak",
                "password": "hunter2",
                "kind": "local",
            }
        ],
    )
    entry = event["payload"]["entries"][0]
    for forbidden in ("api_key", "token", "password"):
        assert forbidden not in entry, f"{forbidden} leaked through registry builder"
    assert entry["base_url"] == "ws://127.0.0.1:8765"


def test_endpoint_registry_event_rejects_missing_active_id():
    with pytest.raises(ValueError):
        build_endpoint_registry_event(active_id="", entries=[])


def test_endpoint_registry_event_rejects_active_id_not_in_entries():
    with pytest.raises(ValueError):
        build_endpoint_registry_event(
            active_id="bogus",
            entries=[{"id": "local", "label": "Local", "base_url": "ws://x", "kind": "local"}],
        )
