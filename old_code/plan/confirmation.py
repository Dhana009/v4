from __future__ import annotations
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from agent import AgentLoop


class PlanConfirmation:
    def __init__(self, loop: "AgentLoop") -> None:
        self._loop = loop

    async def wait_for_plan_confirmation(self) -> dict[str, Any]:
        from runtime.event_contracts import build_runtime_rejection_payload
        active_confirmation_context = self.confirmation_context(self._loop._current_active_plan_state())
        while True:
            event = await self._loop.control_queue.get()
            event_type = str(event.get("type") or "")
            answer = str(event.get("message") or event.get("answer") or "").strip()
            event_context = self.confirmation_context(event)
            if event_type == "correction":
                completed_run_reason = self.completed_run_confirmation_rejection_reason(event_context)
                if completed_run_reason:
                    completed_run_id = event_context.get("run_id") or self._loop._current_run_session_id()
                    await self._loop._send(
                        "runtime_rejected",
                        **build_runtime_rejection_payload(
                            "STALE_CONFIRMATION",
                            "Correction does not match the active plan context.",
                            detail=f"correction after completion: {completed_run_reason}",
                            current_state={
                                "run_id": completed_run_id,
                                "phase": self._loop._current_phase(),
                            },
                            run_id=completed_run_id,
                            recoverable=False,
                            source="agent",
                            command_type="correction",
                        ),
                    )
                    return {
                        "confirmed": False,
                        "correction": answer or "the user requested a correction",
                    }
                mismatch_reason = self.confirmation_context_mismatch_reason(active_confirmation_context, event_context)
                if mismatch_reason:
                    await self._loop._send(
                        "runtime_rejected",
                        **build_runtime_rejection_payload(
                            "STALE_CONFIRMATION",
                            "Correction does not match the active plan context.",
                            detail=f"correction context mismatch: {mismatch_reason}",
                            current_state=active_confirmation_context
                            or self.confirmation_context(self._loop._current_active_plan_state()),
                            run_id=event_context.get("run_id") or active_confirmation_context.get("run_id") or None,
                            recoverable=False,
                            source="agent",
                            command_type="correction",
                        ),
                    )
                    return {
                        "confirmed": False,
                        "correction": answer or "the user requested a correction",
                        "plan_id": str(event.get("plan_id") or event.get("planId") or "").strip() or None,
                        "target_step_id": str(event.get("target_step_id") or event.get("targetStepId") or "").strip() or None,
                    }
                return {
                    "confirmed": False,
                    "correction": answer,
                    "plan_id": str(event.get("plan_id") or event.get("planId") or "").strip() or None,
                    "target_step_id": str(event.get("target_step_id") or event.get("targetStepId") or "").strip() or None,
                }
            if event_type == "confirmed":
                completed_run_reason = self.completed_run_confirmation_rejection_reason(event_context)
                if completed_run_reason:
                    completed_run_id = event_context.get("run_id") or self._loop._current_run_session_id()
                    await self._loop._send(
                        "runtime_rejected",
                        **build_runtime_rejection_payload(
                            "STALE_CONFIRMATION",
                            "Confirmation does not match the active plan context.",
                            detail=f"confirmation after completion: {completed_run_reason}",
                            current_state={
                                "run_id": completed_run_id,
                                "phase": self._loop._current_phase(),
                            },
                            run_id=completed_run_id,
                            recoverable=False,
                            source="agent",
                        ),
                    )
                    return {"confirmed": False, "answer": answer or "confirmed"}
                mismatch_reason = self.confirmation_context_mismatch_reason(active_confirmation_context, event_context)
                if mismatch_reason:
                    await self._loop._send(
                        "runtime_rejected",
                        **build_runtime_rejection_payload(
                            "STALE_CONFIRMATION",
                            "Confirmation does not match the active plan context.",
                            detail=f"confirmation context mismatch: {mismatch_reason}",
                            current_state=active_confirmation_context or self.confirmation_context(self._loop._current_active_plan_state()),
                            run_id=event_context.get("run_id") or active_confirmation_context.get("run_id") or None,
                            recoverable=False,
                            source="agent",
                        ),
                    )
                    continue
                result = {"confirmed": True, "answer": "confirmed"}
                run_id = event_context.get("run_id") or active_confirmation_context.get("run_id")
                if run_id:
                    result["run_id"] = run_id
                plan_id = event_context.get("plan_id") or active_confirmation_context.get("plan_id")
                if plan_id:
                    result["plan_id"] = plan_id
                plan_version = event_context.get("plan_version") or active_confirmation_context.get("plan_version")
                if plan_version:
                    result["plan_version"] = plan_version
                return result
            if event_type == "option_selected":
                completed_run_reason = self.completed_run_confirmation_rejection_reason(event_context)
                if completed_run_reason:
                    completed_run_id = event_context.get("run_id") or self._loop._current_run_session_id()
                    await self._loop._send(
                        "runtime_rejected",
                        **build_runtime_rejection_payload(
                            "STALE_CONFIRMATION",
                            "Confirmation does not match the active plan context.",
                            detail=f"option_selected after completion: {completed_run_reason}",
                            current_state={
                                "run_id": completed_run_id,
                                "phase": self._loop._current_phase(),
                            },
                            run_id=completed_run_id,
                            recoverable=False,
                            source="agent",
                        ),
                    )
                    return {"confirmed": False, "answer": answer}
                mismatch_reason = self.confirmation_context_mismatch_reason(active_confirmation_context, event_context)
                if mismatch_reason:
                    await self._loop._send(
                        "runtime_rejected",
                        **build_runtime_rejection_payload(
                            "STALE_CONFIRMATION",
                            "Confirmation does not match the active plan context.",
                            detail=f"confirmation context mismatch: {mismatch_reason}",
                            current_state=active_confirmation_context or self.confirmation_context(self._loop._current_active_plan_state()),
                            run_id=event_context.get("run_id") or active_confirmation_context.get("run_id") or None,
                            recoverable=False,
                            source="agent",
                        ),
                    )
                    continue
                result = {"confirmed": True, "answer": answer}
                run_id = event_context.get("run_id") or active_confirmation_context.get("run_id")
                if run_id:
                    result["run_id"] = run_id
                plan_id = event_context.get("plan_id") or active_confirmation_context.get("plan_id")
                if plan_id:
                    result["plan_id"] = plan_id
                plan_version = event_context.get("plan_version") or active_confirmation_context.get("plan_version")
                if plan_version:
                    result["plan_version"] = plan_version
                return result

    async def send_plan_ready_after_confirmation(self, payload: Any) -> Any:
        await self._loop._send("plan_ready", **payload)
        self._loop._remember_plan_review_context(payload)
        plan_step_id = str(
            payload.get("target_step_id")
            or payload.get("step_id")
            or payload.get("id")
            or payload.get("stepId")
            or ""
        ).strip() or None
        self._loop.phase_tracker.set_phase(
            "awaiting_confirmation",
            reason="plan_ready",
            step_id=plan_step_id,
        )
        print("[AGENT] plan_ready sent; waiting for user confirmation")
        confirmation = await self.wait_for_plan_confirmation()
        if confirmation.get("confirmed"):
            self._loop.plan_confirmed = True
            self._loop.phase = "executing"
            self._loop.phase_tracker.set_phase("executing", reason="confirmed", step_id=plan_step_id)
            self._loop._pending_failure_followup = False
            self._loop._awaiting_step_record = False
            self._loop._recording_wait_guard_armed = False
            self._loop._store_confirmed_execution_plan(payload)
            self._loop._clear_active_plan_state()
            self._loop._plan_correction_pending = False
            self._loop._clear_plan_review_context()
            answer = str(confirmation.get("answer") or "confirmed").strip() or "confirmed"
            print("[AGENT] plan confirmed; entering execution phase")
            return {"confirmed": True, "answer": answer, "phase": "executing"}

        self._loop.plan_confirmed = False
        self._loop.phase = "planning"
        self._loop.phase_tracker.set_phase("planning", reason="correction", step_id=plan_step_id)
        self._loop.last_successful_action = None
        self._loop._last_action_context = None
        self._loop._awaiting_step_record = False
        self._loop._recording_wait_guard_armed = False
        self._loop._pending_failure_followup = False
        correction = str(confirmation.get("correction") or "").strip() or "the user requested a correction"
        print("[AGENT] correction received; staying in planning phase")
        result = {
            "confirmed": False,
            "correction": correction,
            "phase": "planning",
        }
        correction_plan_id = str(confirmation.get("plan_id") or payload.get("plan_id") or "").strip()
        if correction_plan_id:
            result["plan_id"] = correction_plan_id
        correction_target_step_id = str(confirmation.get("target_step_id") or plan_step_id or "").strip()
        if correction_target_step_id:
            result["target_step_id"] = correction_target_step_id
        return result

    def confirmation_context(self, payload: dict[str, Any] | None) -> dict[str, str]:
        if not isinstance(payload, dict):
            return {}

        context: dict[str, str] = {}
        for key, alt_key in (("run_id", "runId"), ("plan_id", "planId"), ("plan_version", "planVersion")):
            value = str(payload.get(key) or payload.get(alt_key) or "").strip()
            if value:
                context[key] = value
        return context

    def confirmation_context_mismatch_reason(
        self,
        active_context: dict[str, str] | None,
        event_context: dict[str, str] | None,
    ) -> str | None:
        active_context_data = active_context if isinstance(active_context, dict) else {}
        event_context_data = event_context if isinstance(event_context, dict) else {}
        if not active_context_data or not event_context_data:
            return None

        mismatches: list[str] = []
        for key in ("run_id", "plan_id", "plan_version"):
            received_value = str(event_context_data.get(key) or "").strip()
            if not received_value:
                continue
            expected_value = str(active_context_data.get(key) or "").strip()
            if expected_value and received_value != expected_value:
                mismatches.append(key)

        if not mismatches:
            return None
        return ", ".join(mismatches)

    def completed_run_confirmation_rejection_reason(self, event_context: dict[str, str] | None) -> str | None:
        event_context_data = event_context if isinstance(event_context, dict) else {}
        run_id = str(event_context_data.get("run_id") or "").strip()
        if not run_id:
            return None
        if self._loop._current_phase() != "completed" and not getattr(self._loop, "_run_completed_emitted", False):
            return None
        return "completed run is already closed"
