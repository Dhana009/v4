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

    def current_browser_url(self) -> str:
        try:
            return str(get_page().url or "").strip()
        except Exception:  # noqa: BLE001
            return ""

    def build_failure_recovery_question(self, step: dict[str, Any] | None, final_text: str) -> str:
        step_summary = self._loop._step_state_summary(step)
        browser_url = self._loop._current_browser_url()
        parts = [
            "Recovery required for the failed original step.",
            f"Failed step: {json.dumps(step_summary, ensure_ascii=True)}",
            f"Current browser URL: {browser_url or 'unknown'}",
        ]
        if final_text:
            parts.append(f"Model summary: {self._loop._normalize_space(final_text)}")
        parts.append("Reply with the correction, or say skip/stop/end.")
        return "\n".join(parts)

    def build_failure_followup_message(
    self,
    step: dict[str, Any] | None,
    answer_text: str,
    *,
    skipped: bool,
    ) -> str:
        step_summary = self._loop._step_state_summary(step)
        browser_url = self._loop._current_browser_url()
        prefix = "User skipped unresolved failed step" if skipped else "User correction for unresolved failed step"
        details = self._loop._normalize_space(answer_text) or ("skip" if skipped else "confirmed")
        return (
            f"{prefix} {step_summary.get('step_id') or 'unknown'}: {details}. "
            f"Continue recovery. Do not finalize until the failed step is recorded or skipped. "
            f"Original failed step context: {json.dumps(step_summary, ensure_ascii=True)}. "
            f"Current browser URL: {browser_url or 'unknown'}."
        )

    def build_stop_followup_message(self, step: dict[str, Any] | None, answer_text: str) -> str:
        step_summary = self._loop._step_state_summary(step)
        browser_url = self._loop._current_browser_url()
        return (
            f"User explicitly ended the run for unresolved failed step {step_summary.get('step_id') or 'unknown'}: "
            f"{self._loop._normalize_space(answer_text) or 'stop'}. "
            f"Provide a concise final summary and do not request more actions. "
            f"Original failed step context: {json.dumps(step_summary, ensure_ascii=True)}. "
            f"Current browser URL: {browser_url or 'unknown'}."
        )

    def build_continue_prompt(self, final_text: str) -> str:
        unresolved_steps = [
            self._loop._step_state_summary(step)
            for step in self._loop._recording_steps
            if str(step.get("status") or "") in {"pending", "executing", "recovery_pending", "failed"}
        ]
        prompt = {
            "instruction": "Continue the unresolved steps. Do not finalize yet.",
            "unresolved_steps": unresolved_steps,
        }
        if final_text:
            prompt["llm_text"] = self._loop._normalize_space(final_text)
        return f"Continue with the remaining steps: {json.dumps(prompt, ensure_ascii=True)}"

    def response_requests_skip(self, answer_text: str) -> bool:
        normalized = self._loop._normalize_space(answer_text).lower()
        if not normalized:
            return False
        skip_phrases = (
            "skip this",
            "skip it",
            "skip step",
            "ignore this step",
            "move on",
        )
        return normalized == "skip" or any(phrase in normalized for phrase in skip_phrases)

    def response_requests_stop(self, answer_text: str) -> bool:
        normalized = self._loop._normalize_space(answer_text).lower()
        if not normalized:
            return False
        stop_phrases = (
            "stop here",
            "stop the run",
            "stop",
            "end",
            "end the run",
            "cancel",
        )
        return any(phrase in normalized for phrase in stop_phrases)
