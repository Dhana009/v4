"""
runtime/context_levels.py

L0–L5 context level definitions for LLM runtime policy enforcement.

Source rule: Runtime Policy Spec — context levels L0–L5 defined with strict rules.
Planning/recommendation purposes never receive raw DOM by default.
Escalation only when sufficiency gates fail.

Modularization rule: policy logic in focused runtime/ modules, not agent.py.
"""
from __future__ import annotations

from typing import Any

# ---------------------------------------------------------------------------
# Context level definitions
# ---------------------------------------------------------------------------

CONTEXT_LEVELS: dict[str, dict[str, Any]] = {
    "L0": {
        "name": "user_message_only",
        "rank": 0,
        "includes": ["phase", "modal_state", "user_message"],
        "excludes": ["dom", "raw_dom", "element", "section_summary", "page_intelligence"],
        "description": "Minimal: user message + UI phase state only",
        "allows_dom": False,
        "allows_raw_dom": False,
    },
    "L1": {
        "name": "element_descriptor",
        "rank": 1,
        "includes": ["phase", "modal_state", "user_message", "element"],
        "excludes": ["dom", "raw_dom", "section_summary", "page_intelligence"],
        "description": "Adds selected element descriptor (tag, class, text, position)",
        "allows_dom": False,
        "allows_raw_dom": False,
    },
    "L2": {
        "name": "section_summary",
        "rank": 2,
        "includes": ["phase", "modal_state", "user_message", "element", "section_summary"],
        "excludes": ["dom", "raw_dom", "page_intelligence"],
        "description": "Adds nearby elements, visual context section summary",
        "allows_dom": False,
        "allows_raw_dom": False,
    },
    "L3": {
        "name": "page_intelligence_summary",
        "rank": 3,
        "includes": ["phase", "modal_state", "user_message", "element", "section_summary", "page_intelligence"],
        "excludes": ["dom", "raw_dom"],
        "description": "Adds page intelligence summary (structure, headings, DOM strength)",
        "allows_dom": False,
        "allows_raw_dom": False,
    },
    "L4": {
        "name": "focused_debug_packet",
        "rank": 4,
        "includes": ["phase", "modal_state", "user_message", "failure_evidence", "trace", "error"],
        "excludes": ["raw_dom"],
        "description": "Focused debug packet: failure evidence, locator packets, traces",
        "allows_dom": False,
        "allows_raw_dom": False,
    },
    "L5": {
        "name": "capped_raw_dom",
        "rank": 5,
        "includes": ["phase", "modal_state", "user_message", "raw_dom"],
        "excludes": ["password", "api_key", "token", "secret", "credential"],
        "description": "Capped raw DOM with secrets/credential redaction, max 50KB",
        "allows_dom": True,
        "allows_raw_dom": True,
        "max_dom_bytes": 50 * 1024,  # 50KB cap
    },
}

# Ordered list of levels low → high
LEVEL_ORDER: list[str] = ["L0", "L1", "L2", "L3", "L4", "L5"]

# ---------------------------------------------------------------------------
# Level comparison utilities
# ---------------------------------------------------------------------------

_SECRET_KEYS: frozenset[str] = frozenset({
    "password", "passwd", "api_key", "apikey", "token", "secret",
    "credential", "credentials", "auth_token", "access_token", "private_key",
})


def level_rank(level: str) -> int:
    """Return integer rank for comparison (L0=0, L5=5)."""
    defn = CONTEXT_LEVELS.get(level)
    if defn is None:
        raise ValueError(f"Unknown context level: {level!r}")
    return defn["rank"]


def is_within_ceiling(requested: str, ceiling: str) -> bool:
    """Return True if *requested* level is at or below *ceiling*."""
    return level_rank(requested) <= level_rank(ceiling)
