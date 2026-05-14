"""
runtime/agent_registry.py — Sprint 7 cluster-completion E1 (B1).

Minimal real-agent registry that backs the v4 AgentsPopover (D-106).
Replaces the prior "honest empty / Sprint 8 deferred" state in the frontend
with a backend-driven payload, while keeping the toggle read-only because
Sprint 7 runtime cannot yet enable/disable agents at runtime.

Spec refs:
  - autoworkbench_complete_llm_mode_runtime_policy_spec.md (agent_settings)
  - .tasks-md/Planning/S7-CROSS-LAYER-COMPLETION-PLAN.md (Backend Seam B1)
  - .tasks-md/Planning/S7-WRAP-D106-AGENT-POPOVER.md

S9 denylist (security): the builder strips known-sensitive keys defensively
even if a registry entry mistakenly adds them. Toggles are read-only in
Sprint 7 — the payload exposes ``control_mode == "read_only"`` so the
frontend renders an honest disabled state with a real reason instead of
silently dropping events.
"""
from __future__ import annotations

from copy import deepcopy
from typing import Any, Iterable

# Keys that must never leak through agent_settings, regardless of registry
# content. See Security Matrix S9 in the cross-layer completion plan.
_DENYLISTED_KEYS = (
    "api_key",
    "system_prompt_body",
    "provider_credential",
    "secret",
    "token",
)

# Keys the contract requires for every emitted agent entry. Extras are
# dropped unless explicitly allow-listed below.
_REQUIRED_AGENT_KEYS = (
    "key",
    "name",
    "required",
    "enabled",
    "model_class",
    "status",
    "last_activity_at",
)

_ALLOWED_EXTRA_KEYS: tuple[str, ...] = ()

_AGENT_SETTINGS_VERSION = 1


# Minimal real registry — only agents the Sprint 7 backend actually runs.
# Adding to this list must be paired with backend support that observably
# exercises the new agent; otherwise the popover would lie.
AGENT_REGISTRY_V1: list[dict[str, Any]] = [
    {
        "key": "orchestrator",
        "name": "Main Orchestrator",
        "required": True,
        "enabled": True,
        "model_class": "live",
        "status": "active",
        "last_activity_at": None,
    },
    {
        "key": "page_intelligence",
        "name": "Page Intelligence",
        "required": False,
        "enabled": True,
        "model_class": "live",
        "status": "standby",
        "last_activity_at": None,
    },
]


def _sanitize_agent_entry(entry: dict[str, Any]) -> dict[str, Any]:
    """Apply S9 denylist + key allow-list to a single registry entry."""
    cleaned: dict[str, Any] = {}
    for key in _REQUIRED_AGENT_KEYS:
        cleaned[key] = entry.get(key)
    for extra in _ALLOWED_EXTRA_KEYS:
        if extra in entry:
            cleaned[extra] = entry[extra]
    for denied in _DENYLISTED_KEYS:
        cleaned.pop(denied, None)
    return cleaned


def build_agent_settings_payload(
    *,
    extra_agents: Iterable[dict[str, Any]] | None = None,
    version: int = _AGENT_SETTINGS_VERSION,
    control_mode: str = "read_only",
) -> dict[str, Any]:
    """Build the inner payload for the ``agent_settings`` event.

    Parameters
    ----------
    extra_agents:
        Optional additional registry entries (test seam; not used in prod).
    version:
        Optimistic-concurrency version (B1 rejection ``STALE_AGENT_SETTINGS_VERSION``).
    control_mode:
        ``"read_only"`` (Sprint 7) or ``"writable"`` once ``set_agent_enabled``
        ships in a later batch.
    """
    source = list(AGENT_REGISTRY_V1)
    if extra_agents:
        source = source + list(extra_agents)
    agents = [_sanitize_agent_entry(deepcopy(entry)) for entry in source]
    return {
        "version": int(version),
        "control_mode": control_mode,
        "agents": agents,
    }
