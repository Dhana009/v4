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
# Selector-string classification (Pass 4b-1)
#
# Deterministic, no LLM. Used to annotate plan_ready step.locator_kind so the
# frontend Steps tab / Plan-ready card can render strong/weak/unknown chips
# from backend truth instead of inferring.
# ---------------------------------------------------------------------------

@dataclass
class LocatorStrengthAssessment:
    strength: LocatorStrength | None  # None = unknown / no locator
    kind: str  # "ok" (strong), "med" (medium), "warn" (weak), "unknown"
    reason: str  # short backend-generated explanation


_STRONG_SELECTOR_PATTERNS = (
    ("data-testid=", "uses data-testid"),
    ("[data-testid", "uses data-testid"),
    ("data-cy=", "uses data-cy"),
    ("[data-cy", "uses data-cy"),
    ("getByTestId(", "uses getByTestId"),
    ("getByRole(", "uses role+name"),
    ("getByLabel(", "uses accessible label"),
    ("getByAltText(", "uses alt text"),
    ("getByPlaceholder(", "uses placeholder"),
    ("getByTitle(", "uses title"),
)

_MEDIUM_SELECTOR_PATTERNS = (
    ("aria-label", "uses aria-label"),
    ("aria-labelledby", "uses aria-labelledby"),
    ("placeholder=", "uses placeholder"),
    ("name=", "uses name attribute"),
    ("getByText(", "matches visible text"),
    (":has-text(", "matches visible text"),
)

_WEAK_SELECTOR_MARKERS = (
    (":nth-child", "positional CSS — breaks if siblings change"),
    (":nth-of-type", "positional CSS — breaks if siblings change"),
    (">", "deep descendant chain — fragile"),
    ("//", "absolute xpath — fragile"),
    ("xpath=", "xpath selector — fragile"),
)


def classify_locator_strength_from_selector(selector: Any) -> LocatorStrengthAssessment:
    """Classify a locator string (CSS / Playwright getBy / xpath) by structural cues.

    Deterministic. No DOM access. Conservative — defaults to MEDIUM when the
    selector looks reasonable but lacks a strong identifier.
    """
    if selector is None:
        return LocatorStrengthAssessment(strength=None, kind="unknown", reason="no locator")
    text = str(selector).strip()
    if not text:
        return LocatorStrengthAssessment(strength=None, kind="unknown", reason="no locator")

    for marker, reason in _STRONG_SELECTOR_PATTERNS:
        if marker in text:
            return LocatorStrengthAssessment(strength=LocatorStrength.STRONG, kind="ok", reason=reason)

    for marker, reason in _WEAK_SELECTOR_MARKERS:
        if marker in text:
            return LocatorStrengthAssessment(strength=LocatorStrength.WEAK, kind="warn", reason=reason)

    for marker, reason in _MEDIUM_SELECTOR_PATTERNS:
        if marker in text:
            return LocatorStrengthAssessment(strength=LocatorStrength.MEDIUM, kind="med", reason=reason)

    if text.startswith("#") and " " not in text:
        return LocatorStrengthAssessment(strength=LocatorStrength.STRONG, kind="ok", reason="uses id")

    if text.startswith(".") and " " not in text and ">" not in text:
        return LocatorStrengthAssessment(
            strength=LocatorStrength.WEAK,
            kind="warn",
            reason="class-only — likely shared by other elements",
        )

    return LocatorStrengthAssessment(
        strength=LocatorStrength.MEDIUM,
        kind="med",
        reason="generic selector",
    )


def annotate_plan_steps_with_locator_kind(payload: dict[str, Any]) -> dict[str, Any]:
    """Walk plan_ready payload steps, classify each step's locator, attach metadata.

    Adds three fields per step (when a locator string is present):
      - locator_strength: "strong" | "medium" | "weak"
      - locator_kind:     "ok" | "med" | "warn"   (frontend chip class)
      - locator_reason:   short human-readable reason
    Steps without a locator string get locator_kind="unknown" and locator_strength=None.
    Returns the same payload object for chaining.
    """
    if not isinstance(payload, dict):
        return payload
    steps = payload.get("steps")
    if not isinstance(steps, list):
        return payload
    for step in steps:
        if not isinstance(step, dict):
            continue
        locator = step.get("locator")
        if isinstance(locator, dict):
            value = locator.get("value") or locator.get("selector")
        else:
            value = locator
        if value is None:
            value = step.get("selector") or (
                step.get("element_info", {}).get("locator")
                if isinstance(step.get("element_info"), dict)
                else None
            )
        assessment = classify_locator_strength_from_selector(value)
        # Don't clobber explicit backend-provided values.
        if "locator_kind" not in step:
            step["locator_kind"] = assessment.kind
        if "locator_strength" not in step:
            step["locator_strength"] = (
                assessment.strength.value if assessment.strength else "unknown"
            )
        if "locator_reason" not in step:
            step["locator_reason"] = assessment.reason
    return payload


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
