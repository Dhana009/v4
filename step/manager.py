from __future__ import annotations
from typing import TYPE_CHECKING, Any
if TYPE_CHECKING:
    from agent import AgentLoop


class StepManager:
    def __init__(self, loop: "AgentLoop") -> None:
        self._loop = loop

    def mark_step_executing(self, step: Any) -> Any:
        return self._loop._mark_step_executing(step)

    def mark_step_failed(self, step: Any, error: Any) -> Any:
        return self._loop._mark_step_failed(step, error)

    def mark_step_recorded(self, step: Any, **kwargs: Any) -> Any:
        return self._loop._mark_step_recorded(step, **kwargs)

    def mark_step_skipped(self, step: Any) -> Any:
        return self._loop._mark_step_skipped(step)

    def clear_failed_step_success_state(self, step: Any) -> None:
        return self._loop._clear_failed_step_success_state(step)

    def get_step_context(self, step_id: Any = None) -> Any:
        return self._loop._get_step_context(step_id)

    def resolve_recording_target_step(self, payload: Any = None) -> Any:
        return self._loop._resolve_recording_target_step(payload)

    def get_failed_step_context(self) -> Any:
        return self._loop._get_failed_step_context()

    def score_step_context(self, step: Any) -> Any:
        return self._loop._score_step_context(step)

    def resolve_step_context(self, step_id: Any = None) -> Any:
        return self._loop._resolve_step_context(step_id)

    def current_pending_step(self) -> Any:
        return self._loop._current_pending_step()

    def find_step_for_recording(self, payload: Any = None) -> Any:
        return self._loop._find_step_for_recording(payload)

    def has_unresolved_steps(self) -> bool:
        return self._loop._has_unresolved_steps()

    def has_unresolved_failure(self) -> bool:
        return self._loop._has_unresolved_failure()

    def all_steps_done(self) -> bool:
        return self._loop._all_steps_done()

    def all_steps_resolved(self) -> bool:
        return self._loop._all_steps_resolved()

    def step_state_summary(self) -> Any:
        return self._loop._step_state_summary()

    def advance_recording_cursor(self) -> None:
        return self._loop._advance_recording_cursor()

    def coerce_step_number(self, value: Any) -> Any:
        return self._loop._coerce_step_number(value)

    def prepare_recording_steps(self, steps: list) -> None:
        return self._loop._prepare_recording_steps(steps)

    def derive_locator_from_step_context(self, step: Any) -> str:
        return self._loop._derive_locator_from_step_context(step)

    def derive_step_context_element_name(self, step: Any) -> str:
        return self._loop._derive_step_context_element_name(step)

    def step_context_text(self, step: Any) -> str:
        return self._loop._step_context_text(step)
