from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from runtime.skill_policy import (
    can_escalate_to_full_skills,
    get_default_skill_names,
    get_skill_levels_for_names,
)
from runtime.skill_summaries import get_skill_summary


@dataclass(slots=True)
class SkillSelection:
    purpose: str
    loaded_skill_names: list[str]
    skill_levels: list[str]
    skill_entries: list[tuple[str, str]]
    preserve_full_prompt: bool
    escalation_reason: str | None = None


def select_skills_for_purpose(
    purpose: str,
    *,
    policy: Mapping[str, Any] | None = None,
    escalation_reason: str | None = None,
    override_full: bool = False,
) -> SkillSelection:
    normalized_purpose = str(purpose or "").strip()
    skill_policy = policy.get("skill_policy") if isinstance(policy, Mapping) else {}
    if not isinstance(skill_policy, Mapping):
        skill_policy = {}

    configured_skill_names = list(skill_policy.get("required_core_skills") or [])
    configured_skill_names.extend(list(skill_policy.get("purpose_skills") or []))
    loaded_skill_names = get_default_skill_names(
        normalized_purpose,
        configured_skill_names=configured_skill_names,
    )
    skill_levels = get_skill_levels_for_names(loaded_skill_names)
    preserve_full_prompt = can_escalate_to_full_skills(
        normalized_purpose,
        escalation_reason=escalation_reason,
        override_full=override_full,
    )
    if preserve_full_prompt:
        return SkillSelection(
            purpose=normalized_purpose,
            loaded_skill_names=loaded_skill_names,
            skill_levels=skill_levels,
            skill_entries=[],
            preserve_full_prompt=True,
            escalation_reason=escalation_reason,
        )

    skill_entries = [
        (skill_name, get_skill_summary(skill_name))
        for skill_name in loaded_skill_names
    ]
    return SkillSelection(
        purpose=normalized_purpose,
        loaded_skill_names=loaded_skill_names,
        skill_levels=skill_levels,
        skill_entries=skill_entries,
        preserve_full_prompt=False,
        escalation_reason=escalation_reason,
    )


def build_skill_prompt(selection: SkillSelection) -> str:
    sections = [content.strip() for _name, content in selection.skill_entries if str(content or "").strip()]
    return "\n\n".join(sections)
