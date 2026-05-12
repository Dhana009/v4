"""
runtime/page_extraction.py

Deterministic page/section extraction for Page Intelligence.

Source rule: Runtime Policy Spec — Page Intelligence must start with
deterministic structured extraction (no LLM, no screenshot).
Extraction is bounded, deduplicated, and risk-flagged.

Modularization rule: policy logic in focused runtime/ modules, not agent.py.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


# ---------------------------------------------------------------------------
# Extraction limits
# ---------------------------------------------------------------------------

MAX_BUTTONS = 20
MAX_HEADINGS = 30
MAX_LINKS = 25
MAX_FORMS = 10
MAX_LANDMARKS = 15


# ---------------------------------------------------------------------------
# Result type
# ---------------------------------------------------------------------------

@dataclass
class PageExtractionResult:
    url: str
    title: str
    headings: list[dict[str, Any]] = field(default_factory=list)
    buttons: list[dict[str, Any]] = field(default_factory=list)
    forms: list[dict[str, Any]] = field(default_factory=list)
    links: list[dict[str, Any]] = field(default_factory=list)
    landmarks: list[dict[str, Any]] = field(default_factory=list)
    tables: list[dict[str, Any]] = field(default_factory=list)
    modals: list[dict[str, Any]] = field(default_factory=list)
    semantic_quality_score: int = 0   # 0–100
    risk_flags: list[str] = field(default_factory=list)
    has_duplicates: bool = False


# ---------------------------------------------------------------------------
# Extraction logic
# ---------------------------------------------------------------------------

def _score_page(page_context: dict[str, Any]) -> int:
    """Compute semantic quality score 0–100."""
    score = 0
    headings = page_context.get("headings", [])
    buttons = page_context.get("buttons", [])
    forms = page_context.get("forms", [])
    landmarks = page_context.get("landmarks", [])

    if headings:
        score += 20
    if any(b.get("aria_label") or b.get("label") for b in buttons):
        score += 20
    if forms:
        fields = forms[0].get("fields", []) if forms else []
        if any(f.get("label") for f in fields):
            score += 20
    if landmarks:
        score += 20
    if page_context.get("title"):
        score += 10
    # Weak DOM signal: div/span buttons reduce score
    weak_buttons = [b for b in buttons if b.get("tag") in ("div", "span")]
    if len(weak_buttons) > len(buttons) // 2 and buttons:
        score = max(0, score - 20)

    return min(100, score)


def _detect_duplicates(buttons: list[dict[str, Any]]) -> bool:
    texts = [b.get("text", "") for b in buttons]
    return len(texts) != len(set(texts))


def _detect_risk_flags(page_context: dict[str, Any]) -> list[str]:
    flags: list[str] = []
    buttons = page_context.get("buttons", [])
    forms = page_context.get("forms", [])
    headings = page_context.get("headings", [])

    if not headings:
        flags.append("no_headings")
    # Buttons without labels
    unlabeled = [b for b in buttons if not b.get("aria_label") and not b.get("label") and not b.get("text")]
    if unlabeled:
        flags.append("unlabeled_buttons")
    # Forms without labels
    for form in forms:
        fields = form.get("fields", [])
        if any(not f.get("label") for f in fields):
            flags.append("form_fields_missing_labels")
            break
    return flags


def extract_page_structure(page_context: dict[str, Any]) -> PageExtractionResult:
    """Deterministically extract page structure from *page_context*.

    Returns PageExtractionResult with bounded, deduplicated candidates.
    No LLM call, deterministic (same input → same output).
    """
    url = page_context.get("url", "")
    title = page_context.get("title", "")

    # Extract and bound each category
    headings = list(page_context.get("headings", []))[:MAX_HEADINGS]
    buttons = list(page_context.get("buttons", []))[:MAX_BUTTONS]
    forms = list(page_context.get("forms", []))[:MAX_FORMS]
    links = list(page_context.get("links", []))[:MAX_LINKS]
    landmarks = list(page_context.get("landmarks", []))[:MAX_LANDMARKS]
    tables = list(page_context.get("tables", []))
    modals = list(page_context.get("modals", []))

    # Detect duplicates
    has_duplicates = _detect_duplicates(buttons)

    # Compute semantic quality
    semantic_quality_score = _score_page(page_context)

    # Risk flags
    risk_flags = _detect_risk_flags(page_context)

    return PageExtractionResult(
        url=url,
        title=title,
        headings=headings,
        buttons=buttons,
        forms=forms,
        links=links,
        landmarks=landmarks,
        tables=tables,
        modals=modals,
        semantic_quality_score=semantic_quality_score,
        risk_flags=risk_flags,
        has_duplicates=has_duplicates,
    )
