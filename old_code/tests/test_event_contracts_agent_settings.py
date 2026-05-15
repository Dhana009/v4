"""
E1 — agent_settings event contract.

Plan ref: .tasks-md/Planning/S7-CROSS-LAYER-COMPLETION-PLAN.md (Backend Seam B1).
Spec source: autoworkbench_complete_llm_mode_runtime_policy_spec.md (agent registry).

These tests pin the schema BEFORE wiring the builder. They define:
  - payload shape (version + agents[] with required keys)
  - S9 redaction denylist (api_key / system_prompt_body / provider_credential / secret / token)
  - rejection on bad input
  - read-only behaviour when runtime cannot toggle (Sprint 7 stance)

No production code may reference DEFAULT_AGENTS or any hardcoded UI-side mock.
"""
from __future__ import annotations

import pytest

from runtime.agent_registry import (
    AGENT_REGISTRY_V1,
    build_agent_settings_payload,
)
from runtime.event_contracts import (
    BACKEND_EVENT_SCHEMA_VERSION,
    build_agent_settings_event,
)


REQUIRED_AGENT_KEYS = {
    "key",
    "name",
    "required",
    "enabled",
    "model_class",
    "status",
    "last_activity_at",
}

REQUIRED_TOP_LEVEL_KEYS = {"version", "agents"}


# --------------------------------------------------------------------------- #
# Payload shape
# --------------------------------------------------------------------------- #
def test_agent_settings_payload_has_required_top_level_keys():
    payload = build_agent_settings_payload()
    assert REQUIRED_TOP_LEVEL_KEYS.issubset(payload.keys())


def test_agent_settings_payload_version_is_positive_int():
    payload = build_agent_settings_payload()
    assert isinstance(payload["version"], int)
    assert payload["version"] >= 1


def test_agent_settings_payload_agents_is_list_of_required_shape():
    payload = build_agent_settings_payload()
    agents = payload["agents"]
    assert isinstance(agents, list)
    assert agents, "registry must contain at least one agent (orchestrator)"
    for agent in agents:
        missing = REQUIRED_AGENT_KEYS - set(agent.keys())
        assert not missing, f"agent {agent.get('key')!r} missing keys: {missing}"


def test_agent_registry_includes_main_orchestrator_required():
    payload = build_agent_settings_payload()
    orchestrators = [a for a in payload["agents"] if a["key"] == "orchestrator"]
    assert len(orchestrators) == 1, "orchestrator must be present exactly once"
    assert orchestrators[0]["required"] is True
    assert orchestrators[0]["enabled"] is True


def test_agent_status_values_are_in_allowed_set():
    allowed = {"idle", "running", "disabled", "active", "standby"}
    payload = build_agent_settings_payload()
    for agent in payload["agents"]:
        assert agent["status"] in allowed, agent


# --------------------------------------------------------------------------- #
# S9 redaction denylist
# --------------------------------------------------------------------------- #
DENYLIST_KEYS = ("api_key", "system_prompt_body", "provider_credential", "secret", "token")


@pytest.mark.parametrize("denied_key", DENYLIST_KEYS)
def test_agent_settings_payload_omits_denylisted_keys(denied_key):
    """S9: builder must never expose secrets even if registry contains them by mistake."""
    payload = build_agent_settings_payload()
    for agent in payload["agents"]:
        assert denied_key not in agent, (
            f"agent {agent['key']} leaks {denied_key} — S9 denylist violated"
        )


def test_agent_settings_payload_drops_extra_secret_fields_from_registry_entry():
    """Builder must scrub denylisted keys defensively even if a registry entry adds them."""
    bad_entry = {
        "key": "rogue",
        "name": "Rogue Agent",
        "required": False,
        "enabled": True,
        "model_class": "live",
        "status": "idle",
        "last_activity_at": None,
        # the following must be stripped:
        "api_key": "sk-leak",
        "system_prompt_body": "you are a sneaky LLM",
        "provider_credential": "AKIA-leak",
        "secret": "shh",
        "token": "ghp_leak",
    }
    payload = build_agent_settings_payload(extra_agents=[bad_entry])
    leaked = next(a for a in payload["agents"] if a["key"] == "rogue")
    for denied in DENYLIST_KEYS:
        assert denied not in leaked, f"S9: {denied} leaked through builder"
    # Allowed keys preserved
    assert leaked["name"] == "Rogue Agent"


# --------------------------------------------------------------------------- #
# Envelope
# --------------------------------------------------------------------------- #
def test_build_agent_settings_event_returns_typed_envelope():
    event = build_agent_settings_event()
    assert event["type"] == "agent_settings"
    assert event["schema_version"] == BACKEND_EVENT_SCHEMA_VERSION
    assert "payload" in event
    payload = event["payload"]
    assert REQUIRED_TOP_LEVEL_KEYS.issubset(payload.keys())


def test_build_agent_settings_event_carries_event_id_and_timestamp():
    event = build_agent_settings_event()
    assert event.get("event_id"), "envelope must auto-generate event_id"
    assert event.get("emitted_at"), "envelope must auto-generate emitted_at"


def test_build_agent_settings_event_does_not_mutate_registry():
    """Builder must defensively copy; consumers cannot mutate AGENT_REGISTRY_V1."""
    snapshot = [dict(a) for a in AGENT_REGISTRY_V1]
    event = build_agent_settings_event()
    event["payload"]["agents"][0]["enabled"] = False  # mutate result
    after = [dict(a) for a in AGENT_REGISTRY_V1]
    assert snapshot == after, "registry mutated through emitted event reference"


# --------------------------------------------------------------------------- #
# Read-only stance (Sprint 7)
# --------------------------------------------------------------------------- #
def test_agent_settings_event_reports_read_only_mode():
    """Sprint 7 cannot truly toggle agents; payload must mark read-only.

    Frontend uses this to keep toggles disabled with an honest reason.
    """
    payload = build_agent_settings_payload()
    assert "control_mode" in payload
    assert payload["control_mode"] == "read_only"


# --------------------------------------------------------------------------- #
# WS integration: agent_settings is emitted right after ready
# --------------------------------------------------------------------------- #
def _collect_initial_events(monkeypatch):
    from fastapi.testclient import TestClient
    import server
    from tests.test_event_contracts import _install_server_stubs

    _install_server_stubs(monkeypatch)
    events: list[dict] = []
    with TestClient(server.app) as client:
        with client.websocket_connect("/ws") as websocket:
            # The server sends a small burst of init events; pull until we
            # see agent_settings or hit a small ceiling.
            for _ in range(6):
                events.append(websocket.receive_json())
                if events[-1].get("type") == "agent_settings":
                    break
    return events


def test_websocket_emits_agent_settings_on_connect(monkeypatch):
    events = _collect_initial_events(monkeypatch)
    types = [e.get("type") for e in events]
    assert "agent_settings" in types, f"agent_settings not emitted on WS connect; got {types}"


def test_websocket_agent_settings_payload_matches_registry(monkeypatch):
    events = _collect_initial_events(monkeypatch)
    event = next(e for e in events if e.get("type") == "agent_settings")
    payload = event["payload"]
    assert payload["control_mode"] == "read_only"
    keys = {a["key"] for a in payload["agents"]}
    assert {"orchestrator", "page_intelligence"}.issubset(keys)
