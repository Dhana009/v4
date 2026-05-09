from __future__ import annotations
from typing import TYPE_CHECKING, Any
if TYPE_CHECKING:
    from agent import AgentLoop


class PlanState:
    """Active plan and confirmed execution contract state."""

    def __init__(self, loop: "AgentLoop") -> None:
        self._loop = loop

    def current_active_plan_state(self) -> dict[str, Any] | None:
        return self._loop._current_active_plan_state()

    def current_plan_version(self) -> int:
        return self._loop._current_plan_version()

    def build_active_plan_state(self, payload: Any) -> dict[str, Any]:
        return self._loop._build_active_plan_state(payload)

    def plan_steps_from_state(self, state: Any) -> list[dict[str, Any]]:
        return self._loop._plan_steps_from_state(state)

    def plan_child_operations_from_step(self, step: Any) -> list[dict[str, Any]]:
        return self._loop._plan_child_operations_from_step(step)

    def plan_operation_text(self, op: Any) -> str:
        return self._loop._plan_operation_text(op)

    def plan_operation_type(self, op: Any) -> str:
        return self._loop._plan_operation_type(op)

    def plan_operation_signature(self, op: Any) -> str:
        return self._loop._plan_operation_signature(op)

    def plan_operation_types_from_state(self, state: Any) -> list[str]:
        return self._loop._plan_operation_types_from_state(state)

    def plan_operation_signatures_from_state(self, state: Any) -> list[str]:
        return self._loop._plan_operation_signatures_from_state(state)

    def sequence_contains_subsequence(self, seq: list[str], sub: list[str]) -> bool:
        return self._loop._sequence_contains_subsequence(seq, sub)

    def clear_active_plan_state(self) -> None:
        return self._loop._clear_active_plan_state()

    def build_confirmed_execution_plan(self, payload: Any) -> dict[str, Any]:
        return self._loop._build_confirmed_execution_plan(payload)

    def store_confirmed_execution_plan(self, plan: Any) -> None:
        return self._loop._store_confirmed_execution_plan(plan)

    def confirmed_execution_contract_for_step(self, step_id: Any) -> Any:
        return self._loop._confirmed_execution_contract_for_step(step_id)

    def confirmed_execution_results_for_step(self, step_id: Any) -> Any:
        return self._loop._confirmed_execution_results_for_step(step_id)

    def confirmed_execution_next_child_for_step(self, step_id: Any) -> Any:
        return self._loop._confirmed_execution_next_child_for_step(step_id)

    def confirmed_execution_step_ready_to_record(self, step_id: Any) -> Any:
        return self._loop._confirmed_execution_step_ready_to_record(step_id)

    def build_confirmed_execution_context_message(self, step_id: Any) -> Any:
        return self._loop._build_confirmed_execution_context_message(step_id)

    def current_confirmed_execution_cursor(self) -> Any:
        return self._loop._current_confirmed_execution_cursor()

    def log_confirmed_execution_cursor(self) -> None:
        return self._loop._log_confirmed_execution_cursor()

    def record_confirmed_execution_child_result(self, step_id: Any, result: Any) -> None:
        return self._loop._record_confirmed_execution_child_result(step_id, result)

    def validate_confirmed_execution_tool_call(self, tool_name: Any, args: Any) -> Any:
        return self._loop._validate_confirmed_execution_tool_call(tool_name, args)

    def locator_matches_confirmed_execution_child(self, locator: Any, child: Any) -> Any:
        return self._loop._locator_matches_confirmed_execution_child(locator, child)

    def assertion_matches_confirmed_execution_child(self, assertion: Any, child: Any) -> Any:
        return self._loop._assertion_matches_confirmed_execution_child(assertion, child)

    def value_matches_confirmed_execution_child(self, value: Any, child: Any) -> Any:
        return self._loop._value_matches_confirmed_execution_child(value, child)

    def describe_confirmed_execution_child(self, child: Any) -> str:
        return self._loop._describe_confirmed_execution_child(child)

    def describe_confirmed_execution_call(self, tool_name: Any, args: Any) -> str:
        return self._loop._describe_confirmed_execution_call(tool_name, args)

    def infer_confirmed_execution_child_assertion(self, child: Any) -> str:
        return self._loop._infer_confirmed_execution_child_assertion(child)

    def normalize_confirmed_execution_child(self, child: Any) -> dict[str, Any]:
        return self._loop._normalize_confirmed_execution_child(child)

    def clear_confirmed_execution_contract_state(self) -> None:
        return self._loop._clear_confirmed_execution_contract_state()
