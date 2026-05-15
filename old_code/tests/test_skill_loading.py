from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from agent import AgentLoop
from runtime.phase_tracker import PhaseTracker
from runtime.skill_manager import SkillManager


def _write_skill(root: Path, name: str, content: str) -> None:
    skill_dir = root / name
    skill_dir.mkdir(parents=True, exist_ok=True)
    (skill_dir / "SKILL.md").write_text(content, encoding="utf-8")


def _make_loop(tmp_path: Path) -> AgentLoop:
    loop = AgentLoop.__new__(AgentLoop)
    loop.skills_root = tmp_path
    loop.llm = SimpleNamespace(messages=[], system_prompt="", reset=lambda: None)
    loop.skill_manager = SkillManager()
    loop.phase_tracker = PhaseTracker()
    loop.phase = "planning"
    loop.pending_recovery = False
    loop.active_failed_step_id = None
    loop.step_state_by_id = {}
    loop._recording_steps = []
    loop._loaded_skill_names = []
    loop._loaded_skill_entries = []
    loop._missing_skill_names = set()
    loop._last_skill_load_phase = None
    loop.capability_gaps = []
    return loop


def test_core_always_loads(tmp_path: Path) -> None:
    _write_skill(tmp_path, "core", "CORE")
    loop = _make_loop(tmp_path)

    loaded_names, system_prompt, loaded_skills = loop._load_skills_for_steps([])

    assert loaded_names == ["core"]
    assert system_prompt == "CORE"
    assert loaded_skills == {"core": "CORE"}


def test_click_intent_loads_actions(tmp_path: Path) -> None:
    _write_skill(tmp_path, "core", "CORE")
    _write_skill(tmp_path, "actions", "ACTIONS")
    loop = _make_loop(tmp_path)

    loaded_names, system_prompt, _ = loop._load_skills_for_steps(
        [{"intent": "Click the submit button"}]
    )

    assert loaded_names == ["core", "actions"]
    assert system_prompt == "CORE\n\nACTIONS"


def test_assert_intent_loads_assertions(tmp_path: Path) -> None:
    _write_skill(tmp_path, "core", "CORE")
    _write_skill(tmp_path, "assertions", "ASSERTIONS")
    loop = _make_loop(tmp_path)

    loaded_names, system_prompt, _ = loop._load_skills_for_steps(
        [{"intent": "Assert the message"}]
    )

    assert loaded_names == ["core", "assertions"]
    assert system_prompt == "CORE\n\nASSERTIONS"


def test_combined_click_assert_loads_in_stable_order(tmp_path: Path) -> None:
    _write_skill(tmp_path, "core", "CORE")
    _write_skill(tmp_path, "actions", "ACTIONS")
    _write_skill(tmp_path, "assertions", "ASSERTIONS")
    loop = _make_loop(tmp_path)

    loaded_names, system_prompt, _ = loop._load_skills_for_steps(
        [{"intent": "Click and assert the result"}]
    )

    assert loaded_names == ["core", "actions", "assertions"]
    assert system_prompt == "CORE\n\nACTIONS\n\nASSERTIONS"


def test_simple_click_recording_does_not_add_codegen(tmp_path: Path) -> None:
    _write_skill(tmp_path, "core", "CORE")
    _write_skill(tmp_path, "actions", "ACTIONS")
    loop = _make_loop(tmp_path)

    loaded_names, _, loaded_skills = loop._load_skills_for_steps(
        [{"intent": "Click the submit button"}]
    )
    loop._loaded_skill_names = list(loaded_names)
    loop._loaded_skill_entries = loop._skill_entries_from_loaded_skills(
        loaded_names,
        loaded_skills,
    )
    loop._sync_skill_prompt_from_entries()
    loop.llm.messages = [
        {"role": "system", "content": loop.llm.system_prompt},
        {"role": "user", "content": "keep history"},
    ]

    first_added = loop._load_phase_skill_expansion("recording")
    second_added = loop._load_phase_skill_expansion("recording")

    assert first_added == []
    assert second_added == []
    assert loop._loaded_skill_names == ["core", "actions"]
    assert loop.llm.messages[0]["content"] == "CORE\n\nACTIONS"
    assert loop.llm.messages[1]["content"] == "keep history"


def test_generate_intent_loads_codegen(tmp_path: Path) -> None:
    _write_skill(tmp_path, "core", "CORE")
    _write_skill(tmp_path, "codegen", "CODEGEN")
    loop = _make_loop(tmp_path)

    loaded_names, system_prompt, _ = loop._load_skills_for_steps(
        [{"intent": "Generate a playwright script"}]
    )

    assert loaded_names == ["core", "codegen"]
    assert system_prompt == "CORE\n\nCODEGEN"


def test_complex_codegen_metadata_allows_recording_codegen(tmp_path: Path) -> None:
    _write_skill(tmp_path, "core", "CORE")
    _write_skill(tmp_path, "actions", "ACTIONS")
    _write_skill(tmp_path, "codegen", "CODEGEN")
    loop = _make_loop(tmp_path)

    loaded_names, _, loaded_skills = loop._load_skills_for_steps(
        [{"intent": "Click the submit button"}]
    )
    loop.current_steps = [
        {
            "intent": "Click the submit button",
            "metadata": {"complex_codegen": True},
        }
    ]
    loop._loaded_skill_names = list(loaded_names)
    loop._loaded_skill_entries = loop._skill_entries_from_loaded_skills(
        loaded_names,
        loaded_skills,
    )
    loop._sync_skill_prompt_from_entries()
    loop.llm.messages = [
        {"role": "system", "content": loop.llm.system_prompt},
        {"role": "user", "content": "keep history"},
    ]

    added_names = loop._load_phase_skill_expansion("recording")

    assert added_names == ["codegen"]
    assert loop._loaded_skill_names == ["core", "actions", "codegen"]
    assert loop.llm.messages[0]["content"] == "CORE\n\nACTIONS\n\nCODEGEN"


def test_missing_mapped_folder_does_not_crash(tmp_path: Path, capsys) -> None:
    _write_skill(tmp_path, "core", "CORE")
    loop = _make_loop(tmp_path)

    loaded_names, system_prompt, loaded_skills = loop._load_skills_for_steps(
        [{"intent": "Select the option"}]
    )

    captured = capsys.readouterr()

    assert loaded_names == ["core"]
    assert system_prompt == "CORE"
    assert loaded_skills == {"core": "CORE"}
    assert "[SKILL_WARNING] missing skill folder: dropdown" in captured.out
    assert len(loop.capability_gaps) == 1
    gap = loop.capability_gaps[0]
    assert gap["ordinal"] == 1
    assert gap["category"] == "missing_skill"
    assert gap["source"] == "_read_skill"
    assert gap["severity"] == "warn"
    assert gap["message"] == "missing skill folder: dropdown"
    assert gap["details"] == {"skill_name": "dropdown"}


def test_recovery_phase_adds_debugging(tmp_path: Path) -> None:
    _write_skill(tmp_path, "core", "CORE")
    _write_skill(tmp_path, "debugging", "DEBUGGING")
    loop = _make_loop(tmp_path)
    loop.pending_recovery = False
    loop.active_failed_step_id = "step-1"
    loop.step_state_by_id = {"step-1": {"status": "recovery_pending"}}

    loaded_names, _, loaded_skills = loop._load_skills_for_steps([])
    loop._loaded_skill_names = list(loaded_names)
    loop._loaded_skill_entries = loop._skill_entries_from_loaded_skills(
        loaded_names,
        loaded_skills,
    )
    loop._sync_skill_prompt_from_entries()
    loop.llm.messages = [
        {"role": "system", "content": loop.llm.system_prompt},
        {"role": "user", "content": "recover"},
    ]

    added_names = loop._load_phase_skill_expansion("recovery")

    assert added_names == ["debugging"]
    assert loop._loaded_skill_names == ["core", "debugging"]
    assert loop.llm.messages[0]["content"] == "CORE\n\nDEBUGGING"
