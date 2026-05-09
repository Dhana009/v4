from __future__ import annotations
from typing import TYPE_CHECKING, Any
if TYPE_CHECKING:
    from agent import AgentLoop


class PlanCorrection:
    def __init__(self, loop: "AgentLoop") -> None:
        self._loop = loop

    def classify_plan_correction(self, message: Any) -> Any:
        return self._loop._classify_plan_correction(message)

    def build_plan_correction_validation_feedback(self, result: Any) -> Any:
        return self._loop._build_plan_correction_validation_feedback(result)

    def build_plan_correction_operation_context_lines(self, step: Any) -> Any:
        return self._loop._build_plan_correction_operation_context_lines(step)

    def build_plan_correction_context_message(self, correction_text: Any = None) -> Any:
        return self._loop._build_plan_correction_context_message(correction_text)

    def build_plan_diff_editor_schema_message(self) -> Any:
        return self._loop._build_plan_diff_editor_schema_message()

    def synthesize_plan_diff_editor_output(self, raw: Any) -> Any:
        return self._loop._synthesize_plan_diff_editor_output(raw)

    def build_plan_correction_clarification_message(self, reason: Any) -> Any:
        return self._loop._build_plan_correction_clarification_message(reason)

    def build_plan_correction_state(self, correction_text: Any) -> Any:
        return self._loop._build_plan_correction_state(correction_text)

    def build_plan_correction_added_child(self, op: Any) -> Any:
        return self._loop._build_plan_correction_added_child(op)

    def build_structured_plan_correction_payload_from_diff(self, diff: Any) -> Any:
        return self._loop._build_structured_plan_correction_payload_from_diff(diff)

    def patch_value(self, original: Any, patch: Any) -> Any:
        return self._loop._patch_value(original, patch)

    def normalize_step_patch(self, patch: Any) -> Any:
        return self._loop._normalize_step_patch(patch)

    def validate_structured_plan_step(self, step: Any) -> Any:
        return self._loop._validate_structured_plan_step(step)

    def validate_structured_plan_correction(self, correction: Any) -> Any:
        return self._loop._validate_structured_plan_correction(correction)

    def remember_plan_review_context(self, payload: Any) -> None:
        return self._loop._remember_plan_review_context(payload)

    def build_plan_step_context_lines(self, step: Any) -> Any:
        return self._loop._build_plan_step_context_lines(step)

    def build_plan_correction_message(self, correction_text: Any) -> Any:
        return self._loop._build_plan_correction_message(correction_text)

    def append_plan_correction_message(self, correction_text: Any) -> None:
        return self._loop._append_plan_correction_message(correction_text)

    def select_plan_correction_child_target(self, candidates: Any) -> str:
        return self._loop._select_plan_correction_child_target(candidates)

    def build_plan_correction_child_description(self, op_type: Any, target: Any) -> str:
        return self._loop._build_plan_correction_child_description(op_type, target)

    def clear_plan_review_context(self) -> None:
        return self._loop._clear_plan_review_context()

    def clear_active_plan_correction_state(self) -> None:
        return self._loop._clear_active_plan_correction_state()

    async def call_plan_diff_editor_controller(self, **kwargs: Any) -> Any:
        return await self._loop._call_plan_diff_editor_controller(**kwargs)

    async def run_plan_diff_editor_correction(self, **kwargs: Any) -> Any:
        return await self._loop._run_plan_diff_editor_correction(**kwargs)
