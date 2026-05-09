from __future__ import annotations
from typing import TYPE_CHECKING, Any
if TYPE_CHECKING:
    from agent import AgentLoop


class SkillsLoader:
    def __init__(self, loop: "AgentLoop") -> None:
        self._loop = loop

    def load_skills_for_steps(self, steps: list) -> tuple:
        return self._loop._load_skills_for_steps(steps)

    def read_skill(self, skill_name: str, *, compact_mode: bool = False) -> Any:
        return self._loop._read_skill(skill_name, compact_mode=compact_mode)

    def load_phase_skill_expansion(self, phase: str) -> list:
        return self._loop._load_phase_skill_expansion(phase)

    def skill_entries_from_loaded_skills(self, names: list, skills: dict) -> list:
        return self._loop._skill_entries_from_loaded_skills(names, skills)

    def compose_skill_prompt_from_entries(self) -> str:
        return self._loop._compose_skill_prompt_from_entries()

    def sync_skill_prompt_from_entries(self) -> str:
        return self._loop._sync_skill_prompt_from_entries()

    def log_skill_load(self, names: list, phase: str) -> None:
        return self._loop._log_skill_load(names, phase)

    def log_skill_diagnostics(self) -> None:
        return self._loop._log_skill_diagnostics()

    def requires_complex_codegen(self) -> bool:
        return self._loop._requires_complex_codegen()
