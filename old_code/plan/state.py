from __future__ import annotations
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from agent import AgentLoop


class PlanState:
    """Active plan and confirmed execution contract state."""

    def __init__(self, loop: "AgentLoop") -> None:
        self._loop = loop

    def current_active_plan_state(self) -> dict[str, Any] | None:
        active_plan_state = getattr(self._loop, "_active_plan_state", None)
        if isinstance(active_plan_state, dict):
            return active_plan_state
        return None

    def current_plan_version(self) -> int:
        candidates: list[Any] = []

        active_plan_state = self.current_active_plan_state()
        if isinstance(active_plan_state, dict):
            candidates.extend(
                [
                    active_plan_state.get("plan_version"),
                    active_plan_state.get("planVersion"),
                ]
            )
            source_payload = active_plan_state.get("source_payload")
            if isinstance(source_payload, dict):
                candidates.extend(
                    [
                        source_payload.get("plan_version"),
                        source_payload.get("planVersion"),
                    ]
                )

        last_plan_ready_payload = getattr(self._loop, "last_plan_ready_payload", None)
        if isinstance(last_plan_ready_payload, dict):
            candidates.extend(
                [
                    last_plan_ready_payload.get("plan_version"),
                    last_plan_ready_payload.get("planVersion"),
                ]
            )

        for candidate in candidates:
            try:
                version = int(str(candidate).strip())
            except (TypeError, ValueError):
                continue
            if version > 0:
                return version
        return 1

    def plan_steps_from_state(self, plan_state: dict[str, Any] | None) -> list[dict[str, Any]]:
        if not isinstance(plan_state, dict):
            return []
        steps = plan_state.get("steps")
        if not isinstance(steps, list):
            return []
        return [step for step in steps if isinstance(step, dict)]

    def plan_child_operations_from_step(self, step: dict[str, Any]) -> list[dict[str, Any]]:
        if not isinstance(step, dict):
            return []
        children = step.get("children")
        if isinstance(children, list) and children:
            return [child for child in children if isinstance(child, dict)]
        return [step]

    def plan_operation_text(self, operation: dict[str, Any] | None) -> str:
        if not isinstance(operation, dict):
            return ""
        return self._loop._normalize_space(
            str(
                operation.get("description")
                or operation.get("target")
                or operation.get("locator")
                or operation.get("text")
                or operation.get("label")
                or operation.get("title")
                or ""
            )
        ).strip()

    def plan_operation_type(self, operation: dict[str, Any] | None) -> str:
        if not isinstance(operation, dict):
            return ""
        return self._loop._normalize_space(str(operation.get("type") or operation.get("action") or "")).lower()

    def plan_operation_signature(self, operation: dict[str, Any] | None) -> str:
        if not isinstance(operation, dict):
            return ""
        operation_type = self.plan_operation_type(operation)
        target_text = self._loop._normalize_space(self.plan_operation_text(operation)).lower()
        locator_text = self._loop._normalize_space(str(operation.get("locator") or "")).lower()
        if not operation_type and not target_text and not locator_text:
            return ""
        if locator_text:
            return f"{operation_type}|{target_text}|{locator_text}"
        return f"{operation_type}|{target_text}"

    def plan_operation_types_from_state(self, plan_state: dict[str, Any] | None) -> list[str]:
        operation_types: list[str] = []
        for step in self.plan_steps_from_state(plan_state):
            for operation in self.plan_child_operations_from_step(step):
                operation_type = self.plan_operation_type(operation)
                if operation_type:
                    operation_types.append(operation_type)
        return operation_types

    def plan_operation_signatures_from_state(self, plan_state: dict[str, Any] | None) -> list[str]:
        operation_signatures: list[str] = []
        for step in self.plan_steps_from_state(plan_state):
            for operation in self.plan_child_operations_from_step(step):
                operation_signature = self.plan_operation_signature(operation)
                if operation_signature:
                    operation_signatures.append(operation_signature)
        return operation_signatures

    def sequence_contains_subsequence(self, sequence: list[str], subsequence: list[str]) -> bool:
        if not subsequence:
            return True
        if not sequence:
            return False

        search_index = 0
        for expected_item in subsequence:
            found_index = -1
            for index in range(search_index, len(sequence)):
                if sequence[index] == expected_item:
                    found_index = index
                    break
            if found_index < 0:
                return False
            search_index = found_index + 1
        return True

    def clear_active_plan_state(self) -> None:
        self._loop._active_plan_state = None
        self.clear_active_plan_correction_state()

    def clear_confirmed_execution_contract_state(self) -> None:
        self._loop.confirmed_plan_by_step_id = {}
        self._loop.confirmed_plan_step_ids = []
        self._loop.confirmed_child_results_by_step_id = {}
        self._loop.confirmed_execution_mismatch_count_by_step_id = {}

    def clear_active_plan_correction_state(self) -> None:
        self._loop._active_plan_correction_state = None
        self._loop._plan_correction_pending = False

    def confirmed_execution_contract_for_step(
        self,
        step: dict[str, Any] | str | None = None,
    ) -> dict[str, Any] | None:
        confirmed_plan_by_step_id = getattr(self._loop, "confirmed_plan_by_step_id", None)
        if not isinstance(confirmed_plan_by_step_id, dict) or not confirmed_plan_by_step_id:
            return None

        candidate_step_ids: list[str] = []
        if isinstance(step, dict):
            for key in ("step_id", "id", "stepId"):
                candidate_step_id = str(step.get(key) or "").strip()
                if candidate_step_id and candidate_step_id not in candidate_step_ids:
                    candidate_step_ids.append(candidate_step_id)
        else:
            candidate_step_id = str(step or "").strip()
            if candidate_step_id:
                candidate_step_ids.append(candidate_step_id)

        for candidate_step_id in candidate_step_ids:
            contract = confirmed_plan_by_step_id.get(candidate_step_id)
            if isinstance(contract, dict):
                return contract

        return None

    def confirmed_execution_results_for_step(self, step_id: str | None) -> dict[str, Any]:
        confirmed_child_results_by_step_id = getattr(self._loop, "confirmed_child_results_by_step_id", None)
        if not isinstance(confirmed_child_results_by_step_id, dict):
            confirmed_child_results_by_step_id = {}
            self._loop.confirmed_child_results_by_step_id = confirmed_child_results_by_step_id

        resolved_step_id = str(step_id or "").strip()
        if not resolved_step_id:
            return {}

        step_results = confirmed_child_results_by_step_id.get(resolved_step_id)
        if not isinstance(step_results, dict):
            step_results = {}
            confirmed_child_results_by_step_id[resolved_step_id] = step_results
        return step_results

    def confirmed_execution_next_child_for_step(
        self,
        step: dict[str, Any] | str | None = None,
    ) -> tuple[dict[str, Any] | None, dict[str, Any] | None, dict[str, Any] | None]:
        contract = self.confirmed_execution_contract_for_step(step)
        if not isinstance(contract, dict):
            return None, None, None

        step_id = str(contract.get("step_id") or "").strip()
        step_results = self.confirmed_execution_results_for_step(step_id)
        children = contract.get("children")
        if not isinstance(children, list):
            return contract, None, None

        for child in children:
            if not isinstance(child, dict):
                continue
            operation_id = str(child.get("operation_id") or "").strip()
            if not operation_id:
                continue
            child_result = step_results.get(operation_id)
            if not isinstance(child_result, dict) or str(child_result.get("status") or "").strip().lower() != "success":
                return contract, child, child_result if isinstance(child_result, dict) else None

        return contract, None, None

    def confirmed_execution_step_ready_to_record(
        self,
        step: dict[str, Any] | str | None = None,
    ) -> bool:
        confirmed_cursor = self._loop._current_confirmed_execution_cursor()
        if not isinstance(confirmed_cursor, dict):
            return False

        if step is not None:
            candidate_step_id = ""
            if isinstance(step, dict):
                for key in ("step_id", "id", "stepId"):
                    candidate_step_id = str(step.get(key) or "").strip()
                    if candidate_step_id:
                        break
            else:
                candidate_step_id = str(step or "").strip()
            if candidate_step_id and candidate_step_id != str(confirmed_cursor.get("step_id") or "").strip():
                return False

        contract, next_child, _ = self.confirmed_execution_next_child_for_step(confirmed_cursor.get("step_id"))
        return isinstance(contract, dict) and next_child is None

    def current_confirmed_execution_cursor(self) -> dict[str, Any] | None:
        confirmed_plan_by_step_id = getattr(self._loop, "confirmed_plan_by_step_id", None)
        if not isinstance(confirmed_plan_by_step_id, dict) or not confirmed_plan_by_step_id:
            return None

        confirmed_step_ids = getattr(self._loop, "confirmed_plan_step_ids", None)
        if not isinstance(confirmed_step_ids, list) or not confirmed_step_ids:
            confirmed_step_ids = list(confirmed_plan_by_step_id.keys())

        recorded_step_ids = getattr(self._loop, "_recorded_step_ids", set())
        skipped_step_ids = getattr(self._loop, "skipped_step_ids", set())

        for candidate_step_id in confirmed_step_ids:
            resolved_candidate_step_id = str(candidate_step_id or "").strip()
            if not resolved_candidate_step_id:
                continue

            contract = confirmed_plan_by_step_id.get(resolved_candidate_step_id)
            if not isinstance(contract, dict):
                continue

            step_context = self._loop.step_state_by_id.get(resolved_candidate_step_id)
            if not isinstance(step_context, dict):
                step_context = contract

            step_status = str(step_context.get("status") or "").strip().lower()
            if (
                step_status in {"recorded", "skipped"}
                or resolved_candidate_step_id in recorded_step_ids
                or resolved_candidate_step_id in skipped_step_ids
            ):
                continue

            current_contract, next_child, next_child_result = self.confirmed_execution_next_child_for_step(
                resolved_candidate_step_id
            )
            if not isinstance(current_contract, dict):
                current_contract = contract

            return {
                "step_id": resolved_candidate_step_id,
                "step_context": step_context,
                "contract": current_contract,
                "next_child": next_child,
                "next_child_result": next_child_result,
            }

        return None

    def log_confirmed_execution_cursor(self, prefix: str) -> None:
        confirmed_cursor = self.current_confirmed_execution_cursor()
        if not isinstance(confirmed_cursor, dict):
            return

        current_contract = confirmed_cursor.get("contract")
        if not isinstance(current_contract, dict):
            current_contract = {}
        current_step_id = str(confirmed_cursor.get("step_id") or "").strip() or "unknown"
        current_step_number = self._loop._coerce_step_number(current_contract.get("step_number"))
        next_child = confirmed_cursor.get("next_child")
        next_child_description = (
            self._loop._describe_confirmed_execution_child(next_child) if isinstance(next_child, dict) else "none"
        )
        print(
            f"{prefix} current step_id={current_step_id} "
            f"step_number={current_step_number or 'unknown'} next_child={next_child_description}"
        )

    def record_confirmed_execution_child_result(
        self,
        step: dict[str, Any] | str | None,
        child: dict[str, Any] | None,
        *,
        tool_name: str,
        args: dict[str, Any],
        result: dict[str, Any],
        status: str,
        browser_state_before: dict[str, str] | None = None,
        browser_state_after: dict[str, str] | None = None,
    ) -> dict[str, Any] | None:
        return self._loop._record_confirmed_execution_child_result(
            step, child,
            tool_name=tool_name, args=args, result=result, status=status,
            browser_state_before=browser_state_before, browser_state_after=browser_state_after,
        )

    def locator_matches_confirmed_execution_child(
        self,
        expected_locator: str,
        actual_locator: str,
    ) -> bool:
        return self._loop._locator_matches_confirmed_execution_child(expected_locator, actual_locator)

    def assertion_matches_confirmed_execution_child(
        self,
        expected_child: dict[str, Any],
        actual_assertion: str,
        actual_args: dict[str, Any],
    ) -> bool:
        return self._loop._assertion_matches_confirmed_execution_child(expected_child, actual_assertion, actual_args)

    def value_matches_confirmed_execution_child(
        self,
        expected_child: dict[str, Any],
        actual_args: dict[str, Any],
    ) -> bool:
        return self._loop._value_matches_confirmed_execution_child(expected_child, actual_args)

    def describe_confirmed_execution_child(self, child: dict[str, Any] | None) -> str:
        return self._loop._describe_confirmed_execution_child(child)

    def describe_confirmed_execution_call(self, tool_name: str, args: dict[str, Any]) -> str:
        return self._loop._describe_confirmed_execution_call(tool_name, args)

    def infer_confirmed_execution_child_assertion(self, child: Any) -> str:
        return self._loop._infer_confirmed_execution_child_assertion(child)

    def normalize_confirmed_execution_child(self, child: Any) -> dict[str, Any]:
        return self._loop._normalize_confirmed_execution_child(child)

    def build_active_plan_state(self, payload: Any) -> dict[str, Any]:
        return self._loop._build_active_plan_state(payload)

    def build_confirmed_execution_plan(self, payload: Any) -> dict[str, Any]:
        return self._loop._build_confirmed_execution_plan(payload)

    def store_confirmed_execution_plan(self, plan: Any) -> None:
        return self._loop._store_confirmed_execution_plan(plan)

    def build_confirmed_execution_context_message(self, step_id: Any) -> Any:
        return self._loop._build_confirmed_execution_context_message(step_id)

    def validate_confirmed_execution_tool_call(self, tool_name: Any, args: Any) -> Any:
        return self._loop._validate_confirmed_execution_tool_call(tool_name, args)

    def build_confirmed_execution_tool_call(
    self,
    child: dict[str, Any],
    *,
    step_context: dict[str, Any] | None = None,
    ) -> tuple[str, dict[str, Any]]:
        child_type = self._loop._normalize_space(str(child.get("type") or "")).strip().lower()
        locator = self._loop._normalize_space(str(child.get("locator") or "")).strip()
        if not locator and isinstance(step_context, dict):
            locator = self._loop._derive_locator_from_step_context(step_context)

        if child_type == "click":
            return "action_click", {"locator": locator}
        if child_type == "fill":
            return "action_fill", {
                "locator": locator,
                "value": child.get("value") or child.get("expected_value") or "",
            }
        if child_type == "assert":
            assertion = self._loop._infer_confirmed_execution_child_assertion(child, source_step=step_context)
            expected_value = child.get("expected_value")
            if expected_value is None:
                expected_value = child.get("value")
            args: dict[str, Any] = {
                "locator": locator,
                "assertion": assertion,
            }
            if expected_value not in (None, ""):
                args["expected_value"] = expected_value
            return "action_assert", args
        raise RuntimeError(f"Unsupported deterministic confirmed child type: {child_type or 'unknown'}")

    async def execute_deterministic_fast_path_confirmed_plan(self) -> None:
        confirmed_cursor = self._loop._current_confirmed_execution_cursor()
        if not isinstance(confirmed_cursor, dict):
            print("[FAST_PATH] execution failed: confirmed execution cursor missing")
            await self._loop._send(
                "llm_result",
                success=False,
                message="Deterministic execution failed safely because the confirmed execution contract was unavailable.",
            )
            self._loop._pending_failure_followup = False
            return

        step_context = confirmed_cursor.get("step_context")
        contract = confirmed_cursor.get("contract")
        expected_child = confirmed_cursor.get("next_child")
        if not isinstance(contract, dict) or not isinstance(expected_child, dict):
            print("[FAST_PATH] execution failed: no confirmed child available")
            await self._loop._send(
                "llm_result",
                success=False,
                message="Deterministic execution failed safely because no confirmed child operation was available.",
            )
            self._loop._pending_failure_followup = False
            return

        tool_name, args = self._loop._build_confirmed_execution_tool_call(
            expected_child,
            step_context=step_context if isinstance(step_context, dict) else None,
        )
        print(
            "[FAST_PATH] executing confirmed child "
            f"{self._loop._describe_confirmed_execution_child(expected_child)} via {tool_name}"
        )

        confirmed_execution_check = self._loop._validate_confirmed_execution_tool_call(tool_name, args)
        if isinstance(confirmed_execution_check, dict) and not confirmed_execution_check.get("allowed", False):
            blocked_result = dict(confirmed_execution_check)
            blocked_result.pop("allowed", None)
            if isinstance(expected_child, dict):
                self._loop._record_confirmed_execution_child_result(
                    step_context,
                    expected_child,
                    tool_name=tool_name,
                    args=args,
                    result=blocked_result,
                    status="blocked",
                )
            self._loop.phase_tracker.set_phase(
                "failed",
                reason="deterministic_execution_contract_blocked",
                step_id=str(contract.get("step_id") or "").strip() or None,
            )
            self._loop.phase = "failed"
            await self._loop._send(
                "llm_result",
                success=False,
                message=str(blocked_result.get("message") or "Deterministic execution was blocked."),
            )
            self._loop._pending_failure_followup = False
            return

        browser_state_before = await self._loop._capture_browser_state()
        result = await self._loop._dispatch_tool(tool_name, args)
        print(f"[FAST_PATH] tool result: {self._loop._summarize(result, limit=120)}")

        if result.get("success") is not True or result.get("skipped"):
            self._loop._record_confirmed_execution_child_result(
                step_context,
                expected_child,
                tool_name=tool_name,
                args=args,
                result=result,
                status="failed" if result.get("success") is False else "blocked",
                browser_state_before=browser_state_before,
            )
            if isinstance(step_context, dict):
                self._loop._mark_step_failed(step_context, result.get("error") or result.get("message") or "deterministic execution failed")
            self._loop.phase_tracker.set_phase(
                "failed",
                reason="deterministic_execution_failed",
                step_id=str(contract.get("step_id") or "").strip() or None,
            )
            self._loop.phase = "failed"
            await self._loop._send(
                "llm_result",
                success=False,
                message=str(result.get("error") or result.get("message") or "Deterministic execution failed safely."),
            )
            self._loop._pending_failure_followup = False
            return

        browser_state_after = await self._loop._capture_browser_state()
        self._loop._record_confirmed_execution_child_result(
            step_context,
            expected_child,
            tool_name=tool_name,
            args=args,
            result=result,
            status="success",
            browser_state_before=browser_state_before,
            browser_state_after=browser_state_after,
        )
        self._loop._mark_step_executing(step_context)
        self._loop._capture_action_context(
            tool_name,
            args,
            result,
            browser_state_before=browser_state_before,
            browser_state_after=browser_state_after,
        )
        recorded_payload = await self._loop._auto_record_successful_step()
        if recorded_payload is None:
            if not self._loop._confirmed_execution_step_ready_to_record(step_context):
                print("[FAST_PATH] confirmed child completed; awaiting remaining confirmed children")
                return
            print("[FAST_PATH] execution failed: auto-record did not produce a recorded payload")
            self._loop.phase_tracker.set_phase(
                "failed",
                reason="deterministic_recording_missing",
                step_id=str(contract.get("step_id") or "").strip() or None,
            )
            self._loop.phase = "failed"
            await self._loop._send(
                "llm_result",
                success=False,
                message="Deterministic execution succeeded but recording failed safely.",
            )
            self._loop._pending_failure_followup = False
            return

        if self._loop._run_completion_requested:
            print("[FAST_PATH] execution completed without planning LLM call")
            self._loop._pending_failure_followup = False
            self._loop._reset_lifecycle_state()
            return

        print("[FAST_PATH] execution completed; run remains open for remaining work")
