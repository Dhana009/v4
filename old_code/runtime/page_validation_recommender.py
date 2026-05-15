"""
runtime/page_validation_recommender.py

Page validation recommendation engine.

Source rule: S6-0304 — recommender turns page intelligence into
grouped, prioritized recommendations. No execution, no auto-acceptance.
Capability gaps are explicit. Ambiguities are flagged, not resolved.

Modularization rule: policy logic in focused runtime/ modules, not agent.py.
"""
from __future__ import annotations

import uuid
from typing import Any

from runtime.recommendation_contracts import (
    PageValidationRecommenderOutput,
    ValidationRecommendation,
    ValidationRecommendationGroup,
)


# ---------------------------------------------------------------------------
# Supported assertion/action types
# ---------------------------------------------------------------------------

SUPPORTED_ASSERTION_TYPES: frozenset[str] = frozenset({
    "text_content", "visibility", "attribute", "count", "enabled",
    "checked", "value", "url_contains", "title_contains",
})

SUPPORTED_ACTION_TYPES: frozenset[str] = frozenset({
    "click", "fill", "submit", "select", "hover", "scroll",
})

# Element roles that map to specific recommendation types
_ROLE_TO_REC_TYPE: dict[str, str] = {
    "button": "action",
    "textbox": "assertion",
    "heading": "assertion",
    "link": "action",
    "checkbox": "assertion",
    "combobox": "assertion",
    "listitem": "assertion",
    "table": "assertion",
    "canvas": "assertion",  # unsupported
}

_ROLE_TO_PRIORITY: dict[str, str] = {
    "button": "useful",
    "textbox": "critical",
    "heading": "useful",
    "link": "optional",
    "checkbox": "useful",
    "combobox": "useful",
    "canvas": "optional",
}

_UNSUPPORTED_ROLES: frozenset[str] = frozenset({"canvas", "svg", "video", "audio"})


def _classify_element(element: dict[str, Any]) -> tuple[str, str, str]:
    """Return (rec_type, priority, capability_status) for an element."""
    role = element.get("role", "").lower()
    if element.get("unsupported"):
        return "assertion", "optional", "capability_gap"
    if role in _UNSUPPORTED_ROLES:
        return "assertion", "optional", "capability_gap"
    rec_type = _ROLE_TO_REC_TYPE.get(role, "assertion")
    priority = _ROLE_TO_PRIORITY.get(role, "optional")
    return rec_type, priority, "supported"


def _stable_id(section_id: str, label: str, rec_type: str) -> str:
    """Generate a stable (deterministic) recommendation ID."""
    key = f"{section_id}:{label}:{rec_type}"
    # Use first 8 chars of a uuid5-style hash for stability
    import hashlib
    digest = hashlib.md5(key.encode()).hexdigest()[:8]  # noqa: S324
    return f"rec-{digest}"


def recommend_page_validations(
    page_intelligence_summary: dict[str, Any],
) -> PageValidationRecommenderOutput:
    """Convert a page intelligence summary into grouped validation recommendations.

    Groups by section, assigns priorities, filters by capability.
    No execution, no auto-acceptance.
    """
    sections = page_intelligence_summary.get("sections", [])
    all_groups: list[ValidationRecommendationGroup] = []
    all_capability_gaps: list[Any] = []
    all_warnings: list[Any] = []
    total = 0
    critical = 0

    for section in sections:
        section_id = section.get("section_id", "unknown")
        section_name = section.get("section_name", section_id)
        elements = section.get("elements", [])
        recs: list[ValidationRecommendation] = []

        for element in elements:
            label = element.get("label", element.get("role", "element"))
            rec_type, priority, cap_status = _classify_element(element)

            assertion_type: str | None = None
            action_type: str | None = None
            if rec_type == "assertion":
                assertion_type = "text_content"
            elif rec_type == "action":
                action_type = "click"

            rec_id = _stable_id(section_id, label, rec_type)
            rec = ValidationRecommendation(
                id=rec_id,
                recommendation_type=rec_type,
                assertion_type=assertion_type,
                action_type=action_type,
                section_id=section_id,
                description=f"Verify {label} in {section_name}",
                locator_hint=element.get("locator_hint", ""),
                expected_value=None,
                priority=priority,
                confidence=0.8,
                capability_status=cap_status,
            )
            recs.append(rec)
            total += 1
            if priority == "critical":
                critical += 1
            if cap_status == "capability_gap":
                all_capability_gaps.append({
                    "section_id": section_id,
                    "element_label": label,
                    "reason": "unsupported_role",
                })

        group = ValidationRecommendationGroup(
            section_id=section_id,
            section_name=section_name,
            recommendations=recs,
            ambiguities=[],
        )
        all_groups.append(group)

    return PageValidationRecommenderOutput(
        groups=all_groups,
        total_recommendations=total,
        critical_count=critical,
        capability_gaps=all_capability_gaps,
        warnings=all_warnings,
    )
