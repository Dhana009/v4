from __future__ import annotations

import asyncio
from types import SimpleNamespace

import pytest

from agent import AgentLoop
from runtime.phase_tracker import PhaseTracker


def _make_loop() -> AgentLoop:
    loop = AgentLoop.__new__(AgentLoop)
    loop.phase_tracker = PhaseTracker()
    loop.phase_tracker.current_phase = "planning"
    loop.phase = "planning"
    loop.active_step_id = "step-1"
    loop.active_failed_step_id = None
    loop.current_steps = []
    loop.step_state_by_id = {}
    loop.step_context_by_id = {}
    loop.pending_recovery = False
    loop.completed_step_ids = set()
    loop.skipped_step_ids = set()
    loop.current_step_index = 0
    loop.last_successful_action = None
    loop.successful_action_by_step_id = {}
    loop.successful_actions_by_step_id = {}
    loop._loaded_skill_names = []
    loop._loaded_skill_entries = []
    loop._missing_skill_names = set()
    loop._last_skill_load_phase = None
    loop._recording_steps = []
    loop._recording_step_index = 0
    loop._recorded_step_ids = set()
    loop._last_action_context = None
    loop._awaiting_step_record = False
    loop._pending_failure_followup = False
    loop.capability_gaps = []
    loop._run_completion_requested = False
    loop.run_stop_requested = False
    loop._plan_correction_pending = False
    loop.llm = SimpleNamespace(messages=[], system_prompt="", reset=lambda: None)
    return loop


def test_record_capability_gap_appends_ordinal() -> None:
    loop = _make_loop()

    first = loop._record_capability_gap(
        "missing_skill",
        "_read_skill",
        "warn",
        "missing skill folder: dropdown",
        skill_name="dropdown",
    )
    second = loop._record_capability_gap(
        "unknown_tool",
        "_dispatch_tool",
        "error",
        "Unsupported tool requested.",
        tool_name="made_up_tool",
    )

    assert first["ordinal"] == 1
    assert second["ordinal"] == 2
    assert first["phase"] == "planning"
    assert first["step_id"] == "step-1"
    assert first["details"] == {"skill_name": "dropdown"}
    assert second["details"] == {"tool_name": "made_up_tool"}
    assert len(loop.capability_gaps) == 2
    assert loop.capability_gaps[0] == first
    assert loop.capability_gaps[1] == second
    assert isinstance(first["timestamp"], str) and first["timestamp"]
    assert isinstance(second["timestamp"], str) and second["timestamp"]


def test_reset_clears_capability_gaps() -> None:
    loop = _make_loop()
    loop._record_capability_gap(
        "missing_skill",
        "_read_skill",
        "warn",
        "missing skill folder: dropdown",
        skill_name="dropdown",
    )

    loop._reset_lifecycle_state([])

    assert loop.capability_gaps == []


def test_unknown_tool_records_gap_and_still_raises_runtime_error() -> None:
    loop = _make_loop()
    loop.phase_tracker.current_phase = "executing"
    loop.active_step_id = "step-9"

    with pytest.raises(RuntimeError, match="Unsupported tool requested: made_up_tool"):
        asyncio.run(loop._dispatch_tool("made_up_tool", {}))

    assert len(loop.capability_gaps) == 1
    gap = loop.capability_gaps[0]
    assert gap["ordinal"] == 1
    assert gap["category"] == "unknown_tool"
    assert gap["source"] == "_dispatch_tool"
    assert gap["severity"] == "error"
    assert gap["message"] == "Unsupported tool requested."
    assert gap["phase"] == "executing"
    assert gap["step_id"] == "step-9"
    assert gap["details"] == {"tool_name": "made_up_tool"}
