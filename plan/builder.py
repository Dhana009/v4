from __future__ import annotations
from typing import TYPE_CHECKING, Any
if TYPE_CHECKING:
    from agent import AgentLoop


class PlanBuilder:
    def __init__(self, loop: "AgentLoop") -> None:
        self._loop = loop

    def normalize_steps(self, steps: Any) -> Any:
        return self._loop._normalize_steps(steps)

    def format_steps(self, steps: Any) -> Any:
        return self._loop._format_steps(steps)

    def validate_recording_steps(self, steps: Any) -> Any:
        return self._loop._validate_recording_steps(steps)

    def infer_operation_type(self, intent: Any) -> str:
        return self._loop._infer_operation_type(intent)

    def infer_planned_operation_sequence(self, intent: Any) -> list[str]:
        return self._loop._infer_planned_operation_sequence(intent)

    def build_planned_child_description(self, operation_type: Any, target: Any, intent: Any) -> str:
        return self._loop._build_planned_child_description(operation_type, target, intent)

    def build_planned_children(self, step: Any) -> list[dict[str, Any]]:
        return self._loop._build_planned_children(step)

    def build_plan_ready_parent_step(self, step: Any) -> dict[str, Any]:
        return self._loop._build_plan_ready_parent_step(step)

    def build_recorded_child_description(self, child: Any) -> str:
        return self._loop._build_recorded_child_description(child)

    def is_technical_recorded_label_text(self, value: Any) -> bool:
        return self._loop._is_technical_recorded_label_text(value)

    def build_recorded_children(self, step: Any) -> list[dict[str, Any]]:
        return self._loop._build_recorded_children(step)

    def build_plan_ready_payload(self, steps: Any) -> dict[str, Any]:
        return self._loop._build_plan_ready_payload(steps)
