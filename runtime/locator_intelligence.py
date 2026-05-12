"""
runtime/locator_intelligence.py

Locator intelligence: deterministic candidate pipeline, strength classification,
duplicate scoping, ambiguity typing.

Source rule: S6-0601–0604 — deterministic locator first. Duplicate scoping/chaining
before LLM. Weak DOM candidates are not truth. Locator ambiguity is typed and user-visible.

Modularization rule: policy logic in focused runtime/ modules, not agent.py.
"""
from __future__ import annotations

import enum
from dataclasses import dataclass, field
from typing import Any


# ---------------------------------------------------------------------------
# Locator strength classification
# ---------------------------------------------------------------------------

class LocatorStrength(enum.Enum):
    STRONG = "strong"   # data-testid, data-cy, id, aria-label
    MEDIUM = "medium"   # aria-label, name, placeholder, role+text
    WEAK = "weak"       # class, tag+text, div/span


_STRONG_ATTRS = frozenset({"data-testid", "data-cy", "id"})
_MEDIUM_ATTRS = frozenset({"aria-label", "aria-labelledby", "name", "placeholder"})


def classify_locator_strength(attrs: dict[str, Any]) -> LocatorStrength:
    """Classify locator strength based on element attributes."""
    for attr in _STRONG_ATTRS:
        if attr in attrs and attrs[attr]:
            return LocatorStrength.STRONG
    for attr in _MEDIUM_ATTRS:
        if attr in attrs and attrs[attr]:
            return LocatorStrength.MEDIUM
    return LocatorStrength.WEAK


# ---------------------------------------------------------------------------
# Locator candidate
# ---------------------------------------------------------------------------

@dataclass
class LocatorCandidate:
    locator: str
    element_tag: str
    strength: LocatorStrength
    text: str = ""
    section: str = ""
    is_final: bool = False
    confirmed: bool = False


def _build_locator_from_attrs(element: dict[str, Any]) -> str:
    """Build a CSS-like locator string from element attributes."""
    for attr in ("data-testid", "data-cy"):
        if element.get(attr):
            return f"[{attr}={element[attr]!r}]"
    if element.get("id"):
        return f"#{element['id']}"
    if element.get("aria-label"):
        return f"[aria-label={element['aria-label']!r}]"
    if element.get("name"):
        return f"[name={element['name']!r}]"
    tag = element.get("tag", "div")
    text = element.get("text", "")
    if text:
        return f"{tag}:has-text({text!r})"
    cls = element.get("class", "")
    if cls:
        first_class = cls.split()[0] if cls else ""
        return f".{first_class}"
    return tag


# ---------------------------------------------------------------------------
# Candidate pipeline
# ---------------------------------------------------------------------------

MAX_CANDIDATES = 20


@dataclass
class LocatorCandidatePipeline:
    candidates: list[LocatorCandidate]
    has_ambiguity: bool = False
    disambiguation_applied: bool = False


def build_locator_candidates(elements: list[dict[str, Any]]) -> LocatorCandidatePipeline:
    """Build deterministic locator candidates from DOM elements.

    Bounded to MAX_CANDIDATES. Strength classified. No LLM call.
    """
    candidates: list[LocatorCandidate] = []
    for element in elements[:MAX_CANDIDATES]:
        locator = _build_locator_from_attrs(element)
        strength = classify_locator_strength(element)
        candidate = LocatorCandidate(
            locator=locator,
            element_tag=element.get("tag", "unknown"),
            strength=strength,
            text=element.get("text", ""),
            section=element.get("section", ""),
        )
        candidates.append(candidate)

    # Sort: STRONG first, then MEDIUM, then WEAK
    _rank = {LocatorStrength.STRONG: 0, LocatorStrength.MEDIUM: 1, LocatorStrength.WEAK: 2}
    candidates.sort(key=lambda c: _rank[c.strength])

    return LocatorCandidatePipeline(candidates=candidates)


def scope_and_chain_candidates(pipeline: LocatorCandidatePipeline) -> LocatorCandidatePipeline:
    """Apply section scoping and chaining to disambiguate duplicate candidates."""
    texts = [c.text for c in pipeline.candidates if c.text]
    has_duplicates = len(texts) != len(set(texts))

    if not has_duplicates:
        return LocatorCandidatePipeline(
            candidates=pipeline.candidates,
            has_ambiguity=False,
            disambiguation_applied=False,
        )

    # Disambiguate by adding section scope to locator
    new_candidates: list[LocatorCandidate] = []
    seen_texts: dict[str, int] = {}
    for c in pipeline.candidates:
        count = seen_texts.get(c.text, 0)
        if count > 0 and c.section:
            # Chain with section scope
            scoped_locator = f"[data-section={c.section!r}] {c.locator}"
            new_candidates.append(LocatorCandidate(
                locator=scoped_locator,
                element_tag=c.element_tag,
                strength=c.strength,
                text=c.text,
                section=c.section,
            ))
        else:
            new_candidates.append(c)
        seen_texts[c.text] = count + 1

    return LocatorCandidatePipeline(
        candidates=new_candidates,
        has_ambiguity=False,
        disambiguation_applied=True,
    )


# ---------------------------------------------------------------------------
# Locator ambiguity
# ---------------------------------------------------------------------------

class LocatorAmbiguityType(enum.Enum):
    DUPLICATE_TEXT = "duplicate_text"
    MULTIPLE_MATCHES = "multiple_matches"
    WEAK_CLASSIFIER = "weak_classifier"
    NO_LABEL = "no_label"


@dataclass
class LocatorAmbiguity:
    ambiguity_type: LocatorAmbiguityType
    candidates: list[str]
    message: str
