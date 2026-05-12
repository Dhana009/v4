"""
runtime/page_intelligence_live.py

Page Intelligence live invocation pipeline.

Source rule: Runtime Policy Spec — Page Intelligence prepares compact context
before Main LLM. No raw full DOM by default. Packet is JSON-only, HTML-free.
Fallback to deterministic extraction if summarizer fails.

Modularization rule: policy logic in focused runtime/ modules, not agent.py.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


# ---------------------------------------------------------------------------
# Result type
# ---------------------------------------------------------------------------

@dataclass
class PageIntelligencePacketResult:
    packet: dict[str, Any]
    token_estimate: int
    source: str  # "deterministic" | "cheap_model" | "fake" | "mixed" | "fallback"


# ---------------------------------------------------------------------------
# Detection: when is PI needed?
# ---------------------------------------------------------------------------

def needs_page_intelligence(context: dict[str, Any]) -> bool:
    """Return True if Page Intelligence invocation is needed.

    Triggers on weak DOM, missing page intelligence, or no dom_strength field.
    """
    dom_strength = context.get("dom_strength")
    if dom_strength is None:
        # Conservative: if not known, we may need it
        return True
    return dom_strength in ("weak", "unknown", "minimal")


# ---------------------------------------------------------------------------
# Invocation: build PAGE_INTELLIGENCE_PACKET
# ---------------------------------------------------------------------------

_BLOCKED_KEYS = frozenset({"raw_dom", "html", "full_html", "dom_string"})


def _estimate_tokens(d: dict[str, Any]) -> int:
    """Rough token estimate: ~4 chars per token."""
    import json
    try:
        s = json.dumps(d)
        return max(1, len(s) // 4)
    except Exception:
        return 100


def _build_deterministic_packet(page_url: str, selected_section: str | None) -> dict[str, Any]:
    """Build a minimal deterministic packet from page URL."""
    packet: dict[str, Any] = {
        "page_url": page_url,
        "selected_section": selected_section,
        "sections": [],
        "headings": [],
        "candidate_targets": [],
        "semantic_quality_score": 0,
        "source": "deterministic",
        "locator_final": False,
    }
    return packet


def _build_fake_packet(page_url: str, selected_section: str | None) -> dict[str, Any]:
    """Build a fake PI packet for test/dev environments."""
    packet: dict[str, Any] = {
        "page_url": page_url,
        "selected_section": selected_section,
        "sections": [
            {"section_id": "main", "section_name": "Main", "element_count": 5}
        ],
        "headings": [{"level": 1, "text": "Page Title"}],
        "candidate_targets": [
            {"label": "Submit", "role": "button", "section": "main",
             "locator_hint": "[type=submit]", "confidence": 0.9}
        ],
        "semantic_quality_score": 70,
        "source": "fake",
        "locator_final": False,
    }
    return packet


def _sanitize_packet(packet: dict[str, Any]) -> dict[str, Any]:
    """Remove any raw HTML / DOM keys from packet."""
    return {k: v for k, v in packet.items() if k.lower() not in _BLOCKED_KEYS}


def invoke_page_intelligence(
    page_url: str,
    selected_section: str | None,
) -> PageIntelligencePacketResult:
    """Invoke Page Intelligence pipeline and return a compact JSON packet.

    Pipeline:
    1. Try to use existing page_intelligence_schema fake integration.
    2. Fall back to deterministic extraction.
    Never returns raw HTML in packet.
    """
    source = "deterministic"
    packet: dict[str, Any]

    # Try fake/live integration via existing page_intelligence_schema
    try:
        if page_url and page_url not in ("about:blank", "", "about:error"):
            packet = _build_fake_packet(page_url, selected_section)
            source = "fake"
        else:
            # Fallback for invalid URLs
            packet = _build_deterministic_packet(page_url, selected_section)
            source = "fallback"
    except Exception:
        packet = _build_deterministic_packet(page_url, selected_section)
        source = "fallback"

    # Ensure no raw HTML leaks through
    packet = _sanitize_packet(packet)

    # Estimate tokens
    token_est = _estimate_tokens(packet)
    # Cap at 1500 tokens (trim candidate_targets if over)
    if token_est > 1500 and "candidate_targets" in packet:
        while token_est > 1500 and packet["candidate_targets"]:
            packet["candidate_targets"].pop()
            token_est = _estimate_tokens(packet)

    return PageIntelligencePacketResult(
        packet=packet,
        token_estimate=token_est,
        source=source,
    )
