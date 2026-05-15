"""
runtime/section_action_planner.py

Selected section multi-action planning.

Source rule: S6-0405 — scoped actions planned for a selected page section.
No execution, no recording.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class SectionActionPlan:
    section_id: str
    proposed_actions: list[dict[str, Any]]
    capability_gaps: list[str]


_ROLE_TO_ACTION: dict[str, str] = {
    "button": "click",
    "textbox": "fill",
    "checkbox": "click",
    "combobox": "select",
    "link": "click",
    "heading": "assert_text",
}


def plan_actions_for_section(
    section_id: str,
    elements: list[dict[str, Any]],
) -> SectionActionPlan:
    """Plan scoped actions for elements in *section_id*."""
    proposed: list[dict[str, Any]] = []
    gaps: list[str] = []

    for element in elements:
        role = element.get("role", "").lower()
        label = element.get("label", element.get("text", "element"))
        action = _ROLE_TO_ACTION.get(role)
        if action:
            proposed.append({
                "action_type": action,
                "element_label": label,
                "role": role,
                "locator_hint": element.get("locator_hint", ""),
            })
        else:
            gaps.append(f"unsupported_role_{role}")

    return SectionActionPlan(
        section_id=section_id,
        proposed_actions=proposed,
        capability_gaps=gaps,
    )
