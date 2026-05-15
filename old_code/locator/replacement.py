"""locator.replacement — Pure module for proposing stable locator replacements.

Given an existing (potentially brittle) locator string and fresh element data,
produces a ranked list of candidate replacements and selects the best one
according to the P1 preference order:

    1. Stable semantic strategies  : role+name, data-testid, label-for
    2. Any candidate scored >= 0.6  (score assigned by strategy-order table)
    3. No suitable candidate found  → chosen=None, confidence=0.0

Public API
----------
LocatorReplacement  – frozen dataclass carrying the result.
propose_replacement – top-level entry point.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

# ---------------------------------------------------------------------------
# Score table — maps strategy name (as produced by LocatorResolver) to a
# numeric score in [0, 1].  Higher = more stable / preferred.
# ---------------------------------------------------------------------------
_STRATEGY_SCORES: dict[str, float] = {
    "locator_hint":  1.0,   # explicit hint → treat as oracle
    "role+name":     0.95,
    "data-testid":   0.93,
    "label-for":     0.90,
    "aria-label":    0.85,
    "name-attr":     0.75,
    "placeholder":   0.70,
    "id":            0.65,
    "exact_text":    0.60,
    "partial_text":  0.50,
    "title":         0.45,
    "alt-text":      0.55,
    "css":           0.30,
    "xpath":         0.10,
}

# Strategies that are always considered "preferred" regardless of score.
_PREFERRED_STRATEGIES = frozenset({"role+name", "data-testid", "label-for"})

# Minimum score for a candidate to be auto-selected when none is preferred.
_MIN_SCORE = 0.6


# ---------------------------------------------------------------------------
# LocatorReplacement dataclass
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class LocatorReplacement:
    """Result of a locator replacement proposal.

    Attributes
    ----------
    original:    The original (potentially brittle) locator string.
    candidates:  All ranked candidate dicts (each has at least ``strategy``
                 and ``locator`` keys, plus ``score``).
    chosen:      The selected best candidate dict, or ``None`` if no suitable
                 candidate was found.
    confidence:  Score of the chosen candidate in [0, 1], or 0.0 if none.
    reasons:     Human-readable rationale lines for the selection decision.
    """

    original: str
    candidates: list[dict]
    chosen: dict | None
    confidence: float
    reasons: list[str]


# ---------------------------------------------------------------------------
# Inline fallback candidate generator (used if locator.resolver is absent)
# ---------------------------------------------------------------------------

def _normalize_space(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def _css_escape(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"')


def _tool_escape(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"')


def _infer_role(element_data: dict[str, Any]) -> str:
    tag = str(element_data.get("tag") or "").strip().lower()
    input_type = str(element_data.get("type") or "").strip().lower()
    role_map = {
        "button": "button",
        "a": "link",
        "select": "combobox",
        "textarea": "textbox",
        "h1": "heading", "h2": "heading", "h3": "heading",
        "h4": "heading", "h5": "heading", "h6": "heading",
    }
    if tag in role_map:
        return role_map[tag]
    if tag == "input":
        if input_type in {"button", "submit", "reset"}:
            return "button"
        if input_type == "checkbox":
            return "checkbox"
        if input_type == "radio":
            return "radio"
        return "textbox"
    return ""


def _fallback_candidates(element_data: dict[str, Any]) -> list[dict[str, str]]:
    """Minimal inline candidate generator — mirrors LocatorResolver.build_locator_candidates."""
    candidates: list[dict[str, str]] = []
    attributes: dict[str, Any] = (
        element_data.get("attributes")
        if isinstance(element_data.get("attributes"), dict)
        else {}
    )

    text_raw = str(element_data.get("text") or element_data.get("innerText") or "").strip()
    text = _normalize_space(text_raw)
    partial_text = text[:80].strip()
    tag = re.sub(r"[^a-zA-Z0-9:_-]", "", str(element_data.get("tag") or "").strip()).lower()

    role = (
        _normalize_space(str(element_data.get("role") or attributes.get("role") or ""))
        or _infer_role(element_data)
    )

    # locator_hint pass-through
    locator_hint = str(element_data.get("locator_hint") or element_data.get("locatorHint") or "").strip()
    if locator_hint:
        candidates.append({"strategy": "locator_hint", "locator": locator_hint})

    # role+name
    if role and partial_text:
        candidates.append({
            "strategy": "role+name",
            "locator": f'get_by_role("{_tool_escape(role)}", name="{_tool_escape(partial_text)}")',
        })

    # data-testid family
    data_testid = str(
        element_data.get("data_testid")
        or element_data.get("dataTestid")
        or attributes.get("data-testid")
        or attributes.get("data-test-id")
        or attributes.get("data-test")
        or attributes.get("data-qa")
        or attributes.get("data-cy")
        or attributes.get("data-automation-id")
        or ""
    ).strip()
    if data_testid:
        candidates.append({
            "strategy": "data-testid",
            "locator": f'get_by_test_id("{_tool_escape(data_testid)}")',
        })

    # aria-label
    aria_label = _normalize_space(
        str(element_data.get("aria_label") or element_data.get("ariaLabel") or attributes.get("aria-label") or "")
    )
    if aria_label:
        candidates.append({
            "strategy": "aria-label",
            "locator": f'get_by_label("{_tool_escape(aria_label)}")',
        })

    # label-for
    label_for_text = _normalize_space(
        str(element_data.get("label_for_text") or element_data.get("labelForText") or element_data.get("label_text") or "")
    )
    if label_for_text and label_for_text != aria_label:
        candidates.append({
            "strategy": "label-for",
            "locator": f'get_by_label("{_tool_escape(label_for_text)}")',
        })

    # name-attr
    name_attr = str(attributes.get("name") or element_data.get("name_attr") or "").strip()
    if name_attr and tag in {"input", "select", "textarea", "button"}:
        candidates.append({
            "strategy": "name-attr",
            "locator": f'[name="{_css_escape(name_attr)}"]',
        })

    # placeholder
    placeholder = _normalize_space(str(element_data.get("placeholder") or attributes.get("placeholder") or ""))
    if placeholder:
        candidates.append({
            "strategy": "placeholder",
            "locator": f'get_by_placeholder("{_tool_escape(placeholder)}")',
        })

    # exact_text
    if text:
        candidates.append({
            "strategy": "exact_text",
            "locator": f'get_by_text("{_tool_escape(text)}", exact=True)',
        })

    # partial_text
    if partial_text and partial_text != text:
        candidates.append({
            "strategy": "partial_text",
            "locator": f'get_by_text("{_tool_escape(partial_text)}", exact=False)',
        })

    # title
    title_attr = _normalize_space(str(element_data.get("title") or attributes.get("title") or ""))
    if title_attr:
        candidates.append({
            "strategy": "title",
            "locator": f'[title="{_css_escape(title_attr)}"]',
        })

    # alt-text
    alt_text = _normalize_space(str(element_data.get("alt") or attributes.get("alt") or ""))
    if alt_text and tag in {"img", "area", "input"}:
        candidates.append({
            "strategy": "alt-text",
            "locator": f'get_by_alt_text("{_tool_escape(alt_text)}")',
        })

    # id
    element_id = str(element_data.get("id") or attributes.get("id") or "").strip()
    if element_id:
        candidates.append({"strategy": "id", "locator": f"#{_css_escape(element_id)}"})

    # css
    class_name = str(
        element_data.get("class") or element_data.get("className") or attributes.get("class") or ""
    ).strip()
    if tag:
        tag_part = tag or "*"
        classes = [
            re.sub(r"[^a-zA-Z0-9_-]", "", c)
            for c in class_name.split()
            if re.sub(r"[^a-zA-Z0-9_-]", "", c)
        ]
        css = tag_part
        if classes:
            css += "." + ".".join(classes[:3])
        if css and css != "*":
            candidates.append({"strategy": "css", "locator": css})

    return candidates


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _score_candidate(candidate: dict[str, Any]) -> float:
    """Return a numeric score for a candidate dict.

    Uses the ``score`` key if already present; otherwise looks up the
    strategy in the global score table; falls back to 0.0.
    """
    if "score" in candidate:
        try:
            return float(candidate["score"])
        except (TypeError, ValueError):
            pass
    strategy = str(candidate.get("strategy") or "").strip()
    return _STRATEGY_SCORES.get(strategy, 0.0)


def _annotate_candidates(candidates: list[dict[str, Any]]) -> list[dict]:
    """Return a new list of candidate dicts enriched with a ``score`` key."""
    result = []
    for c in candidates:
        enriched = dict(c)
        enriched["score"] = _score_candidate(c)
        result.append(enriched)
    # Sort descending by score so highest-confidence candidates appear first.
    result.sort(key=lambda x: x["score"], reverse=True)
    return result


# ---------------------------------------------------------------------------
# _REQUIRED_FIELDS — minimum keys needed for a meaningful proposal
# ---------------------------------------------------------------------------
_REQUIRED_FIELDS = frozenset({"tag", "text", "attributes"})


def _has_sufficient_data(element_data: dict[str, Any]) -> bool:
    """Return True if element_data has at least one useful identifying field."""
    if not isinstance(element_data, dict):
        return False
    # Accept if any of the three primary groups is present with a non-empty value.
    tag = str(element_data.get("tag") or "").strip()
    text = str(element_data.get("text") or element_data.get("innerText") or "").strip()
    attrs = element_data.get("attributes")
    has_attrs = isinstance(attrs, dict) and bool(attrs)
    return bool(tag or text or has_attrs)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def propose_replacement(
    original_locator: str,
    element_data: dict,
    *,
    max_candidates: int = 5,
) -> LocatorReplacement:
    """Propose a stable replacement for *original_locator*.

    Parameters
    ----------
    original_locator:
        The existing locator string that should be replaced (e.g. ``//div[3]/button[2]``).
    element_data:
        Dict describing the target element.  Expected keys (all optional but
        at least one must carry a value): ``tag``, ``text``, ``attributes``
        (nested dict), ``role``, ``aria_label``, ``data_testid``,
        ``label_for_text``, ``placeholder``, ``id``, ``class``, etc.
    max_candidates:
        Maximum number of candidates to return in ``LocatorReplacement.candidates``.

    Returns
    -------
    LocatorReplacement
        Frozen dataclass.  ``chosen`` is ``None`` when no candidate meets the
        minimum quality bar.
    """
    original_locator = str(original_locator or "").strip()

    # Guard: insufficient element data
    if not _has_sufficient_data(element_data):
        return LocatorReplacement(
            original=original_locator,
            candidates=[],
            chosen=None,
            confidence=0.0,
            reasons=["insufficient element_data"],
        )

    # ------------------------------------------------------------------
    # 1. Build raw candidates via LocatorResolver (preferred) or fallback
    # ------------------------------------------------------------------
    raw_candidates: list[dict[str, Any]]
    source: str

    try:
        from locator.resolver import LocatorResolver  # lazy import
        resolver = LocatorResolver()
        raw_candidates = resolver.build_locator_candidates(element_data)
        source = "resolver"
    except Exception:  # ImportError, AttributeError, or runtime error
        raw_candidates = _fallback_candidates(element_data)
        source = "fallback"

    # ------------------------------------------------------------------
    # 2. Annotate with scores and truncate
    # ------------------------------------------------------------------
    scored = _annotate_candidates(raw_candidates)
    scored = scored[:max_candidates]

    # ------------------------------------------------------------------
    # 3. Build reasons list
    # ------------------------------------------------------------------
    reasons: list[str] = [f"candidate_source={source}"]
    for rank, c in enumerate(scored, start=1):
        strategy = c.get("strategy", "unknown")
        score = c.get("score", 0.0)
        reasons.append(f"rank={rank} strategy_kind={strategy} score={score:.2f}")

    # ------------------------------------------------------------------
    # 4. Selection rule
    #    Rule A: first candidate whose strategy is in _PREFERRED_STRATEGIES
    #    Rule B: first candidate with score >= _MIN_SCORE
    #    Rule C: no suitable candidate
    # ------------------------------------------------------------------
    chosen: dict | None = None
    confidence: float = 0.0

    # Rule A — preferred strategies (role+name / data-testid / label-for)
    for c in scored:
        if c.get("strategy") in _PREFERRED_STRATEGIES:
            chosen = c
            confidence = float(c.get("score", 0.0))
            reasons.append(
                f"selected_by=preferred_strategy strategy={c.get('strategy')} confidence={confidence:.2f}"
            )
            break

    if chosen is None:
        # Rule B — first candidate with score >= threshold
        for c in scored:
            if float(c.get("score", 0.0)) >= _MIN_SCORE:
                chosen = c
                confidence = float(c.get("score", 0.0))
                reasons.append(
                    f"selected_by=score_threshold strategy={c.get('strategy')} confidence={confidence:.2f}"
                )
                break

    if chosen is None:
        reasons.append("selected_by=none no_candidate_met_threshold")

    return LocatorReplacement(
        original=original_locator,
        candidates=scored,
        chosen=chosen,
        confidence=confidence,
        reasons=reasons,
    )
