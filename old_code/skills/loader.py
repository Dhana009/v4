from __future__ import annotations
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from agent import AgentLoop


class SkillsLoader:
    def __init__(self, loop: "AgentLoop") -> None:
        self._loop = loop

    def skill_entries_from_loaded_skills(
        self,
        loaded_skill_names: list[str],
        loaded_skills: Any,
    ) -> list[tuple[str, str]]:
        if isinstance(loaded_skills, dict):
            return [
                (skill_name, str(loaded_skills.get(skill_name) or ""))
                for skill_name in loaded_skill_names
                if skill_name in loaded_skills
            ]

        if isinstance(loaded_skills, (list, tuple)):
            skill_entries: list[tuple[str, str]] = []
            for index, item in enumerate(loaded_skills):
                if isinstance(item, dict):
                    skill_name = item.get("name") or item.get("skill_name") or item.get("id")
                    if skill_name is None and index < len(loaded_skill_names):
                        skill_name = loaded_skill_names[index]
                    skill_content = item.get("content")
                    if skill_content is None:
                        skill_content = item.get("text")
                    if skill_content is None:
                        skill_content = item.get("body")
                    skill_entries.append(
                        (
                            str(skill_name or f"skill_{index + 1}").strip() or f"skill_{index + 1}",
                            str(skill_content or ""),
                        )
                    )
                    continue

                if isinstance(item, (list, tuple)) and len(item) >= 2:
                    skill_name = str(item[0] or "").strip() or f"skill_{index + 1}"
                    skill_content = str(item[1] or "")
                    skill_entries.append((skill_name, skill_content))
                    continue

                if index < len(loaded_skill_names):
                    skill_entries.append((loaded_skill_names[index], str(item or "")))
                    continue

                skill_entries.append((f"skill_{index + 1}", str(item or "")))
            return skill_entries

        if isinstance(loaded_skills, str):
            skill_name = loaded_skill_names[0] if loaded_skill_names else "combined_skill_text"
            return [(skill_name, loaded_skills)]

        fallback_name = loaded_skill_names[0] if loaded_skill_names else "combined_skill_text"
        return [(fallback_name, str(loaded_skills or ""))]

    def compose_skill_prompt_from_entries(self) -> str:
        skill_entries = list(getattr(self._loop, "_loaded_skill_entries", []))
        return "\n\n".join(content for _, content in skill_entries)

    def sync_skill_prompt_from_entries(self) -> str:
        prompt = self.compose_skill_prompt_from_entries()
        llm = getattr(self._loop, "llm", None)
        if llm is None:
            return prompt

        llm.system_prompt = prompt
        messages = getattr(llm, "messages", None)
        if isinstance(messages, list) and messages:
            first_message = messages[0]
            if isinstance(first_message, dict) and first_message.get("role") == "system":
                first_message["content"] = prompt
        return prompt

    def log_skill_load(self, added_skill_names: list[str], phase: str) -> None:
        added_text = ",".join(added_skill_names) if added_skill_names else "none"
        total_skill_count = len(getattr(self._loop, "_loaded_skill_names", []))
        print(
            "[SKILL_LOAD] "
            f"added={added_text} "
            f"total={total_skill_count} "
            f"phase={phase}"
        )

    def log_skill_diagnostics(self) -> None:
        skill_manager = getattr(self._loop, "skill_manager", None)
        analyze = getattr(skill_manager, "analyze", None)
        if not callable(analyze):
            return

        loaded_skill_entries = list(getattr(self._loop, "_loaded_skill_entries", []))
        loaded_skill_names = list(getattr(self._loop, "_loaded_skill_names", []))
        skill_diagnostics = analyze(
            loaded_skill_entries,
            loaded_skill_names=loaded_skill_names,
        )
        print(
            "[SKILL_DIAGNOSTICS] "
            f"skills={skill_diagnostics.skill_count} "
            f"names={','.join(skill_diagnostics.loaded_skill_names) or 'none'} "
            f"estimated_tokens={skill_diagnostics.estimated_total_skill_tokens} "
            f"largest={skill_diagnostics.largest_skill_name} "
            f"largest_tokens={skill_diagnostics.largest_skill_tokens} "
            f"policy={skill_diagnostics.suggested_future_policy}"
        )

    def requires_complex_codegen(self) -> bool:
        for step in list(getattr(self._loop, "current_steps", [])):
            if not isinstance(step, dict):
                continue
            metadata = step.get("metadata")
            if not isinstance(metadata, dict):
                continue
            if metadata.get("complex_codegen") or metadata.get("requires_codegen") or metadata.get(
                "codegen_required"
            ):
                return True
            codegen_mode = str(metadata.get("codegen_mode") or "").strip().lower()
            if codegen_mode == "complex":
                return True
        return False

    def load_phase_skill_expansion(self, phase: str) -> list[str]:
        normalized_phase = str(phase or "").strip().lower() or "planning"
        if normalized_phase == "recovering":
            normalized_phase = "recovery"

        phase_skill_names: list[str] = []
        pending_recovery = bool(getattr(self._loop, "pending_recovery", False))
        active_failed_step_id = str(getattr(self._loop, "active_failed_step_id", "") or "").strip()
        failed_step_context = None
        if active_failed_step_id:
            step_state_by_id = getattr(self._loop, "step_state_by_id", {})
            if isinstance(step_state_by_id, dict):
                failed_step_context = step_state_by_id.get(active_failed_step_id)
        if failed_step_context is None:
            recording_steps = list(getattr(self._loop, "_recording_steps", []))
            for recording_step in recording_steps:
                if isinstance(recording_step, dict) and str(recording_step.get("status") or "") in {
                    "failed",
                    "recovery_pending",
                }:
                    failed_step_context = recording_step
                    break
        if normalized_phase == "recovery" or pending_recovery or failed_step_context is not None:
            phase_skill_names.append("debugging")
        if self.requires_complex_codegen():
            phase_skill_names.append("codegen")

        loaded_skill_names = list(getattr(self._loop, "_loaded_skill_names", []))
        loaded_skill_entries = list(getattr(self._loop, "_loaded_skill_entries", []))
        loaded_skill_name_set = set(loaded_skill_names)
        added_skill_names: list[str] = []
        for skill_name in phase_skill_names:
            if skill_name in loaded_skill_name_set:
                continue
            skill_text = self.read_skill(skill_name, compact_mode=False)
            if skill_text is None:
                continue
            loaded_skill_names.append(skill_name)
            loaded_skill_entries.append((skill_name, skill_text))
            loaded_skill_name_set.add(skill_name)
            added_skill_names.append(skill_name)

        previous_phase = getattr(self._loop, "_last_skill_load_phase", None)
        if added_skill_names or normalized_phase != previous_phase:
            self._loop._loaded_skill_names = loaded_skill_names
            self._loop._loaded_skill_entries = loaded_skill_entries
            self._loop._last_skill_load_phase = normalized_phase
            if added_skill_names:
                self.sync_skill_prompt_from_entries()
            self.log_skill_load(added_skill_names, normalized_phase)
            if added_skill_names:
                self.log_skill_diagnostics()

        return added_skill_names

    def load_skills_for_steps(self, steps: list[dict]) -> tuple[list[str], str, dict[str, str]]:
        from agent import SKILL_KEYWORDS
        intents = " ".join(str(step.get("intent") or "") for step in steps).lower()
        loaded_names = ["core"]
        core_skill_text = self.read_skill("core", compact_mode=True) or ""
        loaded_skills = {"core": core_skill_text}
        contents = [core_skill_text]

        for skill_name, keywords in SKILL_KEYWORDS:
            if skill_name == "core":
                continue
            if any(keyword in intents for keyword in keywords):
                skill_text = self.read_skill(skill_name, compact_mode=True)
                if skill_text is None:
                    continue
                loaded_names.append(skill_name)
                loaded_skills[skill_name] = skill_text
                contents.append(skill_text)

        return loaded_names, "\n\n".join(contents), loaded_skills

    def read_skill(self, skill_name: str, *, compact_mode: bool = False) -> str | None:
        if compact_mode:
            compact_path = self._loop.skills_root / skill_name / "SKILL_COMPACT.md"
            if compact_path.is_file():
                print(f"[SKILL_COMPACT] loading compact skill: {skill_name}")
                return compact_path.read_text(encoding="utf-8")
        skill_path = self._loop.skills_root / skill_name / "SKILL.md"
        if not skill_path.is_file():
            missing_skill_names = getattr(self._loop, "_missing_skill_names", set())
            if skill_name not in missing_skill_names:
                print(f"[SKILL_WARNING] missing skill folder: {skill_name}")
                self._loop._record_capability_gap(
                    "missing_skill",
                    "_read_skill",
                    "warn",
                    f"missing skill folder: {skill_name}",
                    skill_name=skill_name,
                )
                missing_skill_names.add(skill_name)
                self._loop._missing_skill_names = missing_skill_names
            return None
        return skill_path.read_text(encoding="utf-8")
