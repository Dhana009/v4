from __future__ import annotations

import asyncio
from copy import deepcopy
from datetime import datetime, timezone
import json
import os
import re
from pathlib import Path
from types import SimpleNamespace
from typing import Any
from uuid import uuid4

from playwright.async_api import TimeoutError as PlaywrightTimeoutError
from playwright.async_api import expect

from browser import get_page
from llm import LLMClient
from runtime.context_manager import ContextManager
from runtime.event_contracts import (
    build_recovery_needed_payload,
    build_run_completed_payload,
    build_runtime_rejection_payload,
)
from runtime.llm_policy_gateway import LLMPolicyGateway
from runtime.llm_runtime_controller import LLMRuntimeController, PURPOSE_REGISTRY
from runtime.model_router import ModelRouter
from runtime.recovery_manager import classify_failure
from runtime.phase_tracker import PhaseTracker
from runtime.snapshot_archive import build_spec_snapshot
from runtime.agent_locator_handlers import tool_dom_extract, tool_locator_find, tool_locator_validate
from runtime.tool_registry import ToolRegistry, filter_tools_for_phase
from runtime.skill_manager import SkillManager
from runtime.telemetry import record_model_call_end, record_model_call_start
from runtime.deterministic_fast_path_gateway import attempt_deterministic_fast_path
from event.emitter import EventEmitter
from locator.resolver import LocatorResolver
from skills.loader import SkillsLoader
from step.manager import StepManager
from recording.codegen import Codegen
from recording.recorder import Recorder
from recording.replay import Replay
from plan.state import PlanState
from plan.builder import PlanBuilder
from plan.correction import PlanCorrection
from plan.confirmation import PlanConfirmation
from llm.tool_definitions import ToolDefinitions
from llm.tool_dispatcher import ToolDispatcher
from llm.orchestrator import LLMOrchestrator

# Module-level singleton — delegates use this so they work even when the
# AgentLoop instance was created via __new__ (bypassing __init__).
_locator_resolver = LocatorResolver()


SKILL_KEYWORDS: list[tuple[str, tuple[str, ...]]] = [
    ("actions", ("click", "fill", "type", "hover", "navigate", "go to")),
    ("assertions", ("assert", "verify", "check", "expect", "visible")),
    ("locator", ("find", "locate", "element", "selector")),
    ("exploration", ("explore", "understand", "analyze", "map")),
    ("waiting", ("wait", "loading", "spinner", "timeout")),
    ("popup", ("popup", "dialog", "alert", "confirm")),
    ("upload", ("upload", "file", "attach")),
    ("download", ("download", "export", "save")),
    ("iframe", ("iframe", "frame", "embed")),
    ("dropdown", ("select", "dropdown", "option")),
    ("scroll", ("scroll",)),
    ("screenshot", ("screenshot", "capture")),
    ("network", ("network", "api", "request")),
    ("keyboard", ("keyboard", "press", "key")),
    ("auth", ("login", "auth", "session")),
    ("codegen", ("generate", "script", "typescript")),
    ("debugging", ("debug", "error", "fix", "broken")),
]

EXPECTED_OUTCOME_TYPES: set[str] = {
    "navigation",
    "modal",
    "dropdown",
    "new_tab",
    "toast_or_message",
    "content_change",
    "download",
    "file_picker",
    "no_visible_change",
    "not_sure",
}
CLICK_LIKE_INTENT_PATTERN = re.compile(r"(^|\b)(click|tap|press|open)\b", re.IGNORECASE)


class AgentLoop:
    # Shared stateless resolver — available even when __new__ bypasses __init__
    _locator_resolver: LocatorResolver = LocatorResolver()

    PLANNING_ALLOWED_TOOLS = {
        "send_to_overlay",
        "dom_extract",
        "locator_find",
        "locator_validate",
        "browser_get_state",
        "screenshot_take",
        "ask_user",
    }
    EXECUTION_TOOLS = {
        "action_click",
        "action_fill",
        "action_assert",
        "page_navigate",
        "page_go_back",
        "page_go_forward",
        "page_reload",
        "scroll_into_view",
    }
    RECORDING_TOOL = {"send_to_overlay"}

    def __init__(self, ws: Any, control_queue: Any) -> None:
        self.ws = ws
        self._emitter = EventEmitter(ws, self)
        self._locator_resolver = LocatorResolver()
        self._skills_loader = SkillsLoader(self)
        self._step_manager = StepManager(self)
        self._codegen = Codegen(self)
        self._recorder = Recorder(self)
        self._replay = Replay(self)
        self.control_queue = control_queue
        self.skills_root = Path("/Users/apple/personal/agent v4/skills/playwright-automation")
        self.llm = LLMClient()
        self.context_manager = ContextManager()
        self.model_router = ModelRouter()
        self.skill_manager = SkillManager()
        self._plan_diff_editor_telemetry: list[dict[str, Any]] = []
        self._plan_diff_editor_telemetry_sink = SimpleNamespace(
            record=self._record_plan_diff_editor_telemetry,
            emit=self._record_plan_diff_editor_telemetry,
            log=self._record_plan_diff_editor_telemetry,
            record_call=self._record_plan_diff_editor_telemetry,
        )
        self._plan_diff_editor_controller = LLMRuntimeController(
            purpose_registry=PURPOSE_REGISTRY,
            schema_validator=self._validate_plan_diff_editor_output,
            context_manager=self.context_manager,
            skill_manager=self.skill_manager,
            telemetry_sink=self._plan_diff_editor_telemetry_sink,
            model_client=self.llm.client,
        )
        self.llm_policy_gateway = LLMPolicyGateway(PURPOSE_REGISTRY)
        self._last_policy_decision: dict[str, Any] | None = None
        self.phase_tracker = PhaseTracker()
        self.tools = self._build_tool_definitions()
        tool_diagnostics = ToolRegistry().analyze(self.tools)
        print(
            "[TOOL_DIAGNOSTICS] "
            f"tools={tool_diagnostics.tool_count} "
            f"estimated_tokens={tool_diagnostics.estimated_total_tool_tokens} "
            f"largest={tool_diagnostics.largest_tool_name} "
            f"largest_tokens={tool_diagnostics.largest_tool_tokens} "
            f"policy={tool_diagnostics.suggested_future_policy}"
        )
        self.phase = "planning"
        self.plan_confirmed = False
        self.current_steps: list[dict[str, Any]] = []
        self.step_state_by_id: dict[str, dict[str, Any]] = {}
        self.step_context_by_id: dict[str, dict[str, Any]] = {}
        self.active_step_id: str | None = None
        self.active_failed_step_id: str | None = None
        self.pending_recovery = False
        self.completed_step_ids: set[str] = set()
        self.skipped_step_ids: set[str] = set()
        self.current_step_index = 0
        self.last_successful_action: dict[str, Any] | None = None
        self.successful_action_by_step_id: dict[str, dict[str, Any]] = {}
        self.successful_actions_by_step_id: dict[str, list[dict[str, Any]]] = {}
        self._loaded_skill_names: list[str] = []
        self._loaded_skill_entries: list[tuple[str, str]] = []
        self._missing_skill_names: set[str] = set()
        self._last_skill_load_phase: str | None = None
        self._recording_steps: list[dict[str, Any]] = []
        self._recording_step_index = 0
        self._recorded_step_ids: set[str] = set()
        self._last_action_context: dict[str, Any] | None = None
        self._awaiting_step_record = False
        self._recording_wait_guard_armed = False
        self._pending_failure_followup = False
        self.last_plan_ready_payload: dict[str, Any] | None = None
        self.last_plan_step_ids: list[str] = []
        self.last_plan_summary: str | None = None
        self.last_plan_original_user_intent: str | None = None
        self._active_plan_state: dict[str, Any] | None = None
        self._active_plan_correction_state: dict[str, Any] | None = None
        self._plan_correction_pending = False
        self.confirmed_plan_by_step_id: dict[str, dict[str, Any]] = {}
        self.confirmed_plan_step_ids: list[str] = []
        self.confirmed_child_results_by_step_id: dict[str, dict[str, Any]] = {}
        self.confirmed_execution_mismatch_count_by_step_id: dict[str, int] = {}
        self.capability_gaps: list[dict[str, Any]] = []
        self.recorded_step_payloads: list[dict[str, Any]] = []
        self.code_update_payloads: list[dict[str, Any]] = []
        self.replay_recorded_step_payloads_by_step_id: dict[str, dict[str, Any]] = {}
        self.replay_action_history_by_step_id: dict[str, list[dict[str, Any]]] = {}
        self._run_session_id = self._new_run_session_id()
        self._run_completion_requested = False
        self._run_completed_emitted = False
        self.run_stop_requested = False
        self._llm_call_counter = 0
        self._ws_disconnected = False
        self._ws_disconnect_logged = False
        self._plan_state = PlanState(self)
        self._plan_builder = PlanBuilder(self)
        self._plan_correction = PlanCorrection(self)
        self._plan_confirmation = PlanConfirmation(self)
        self._tool_definitions = ToolDefinitions(self)
        self._tool_dispatcher = ToolDispatcher(self)
        self._llm_orchestrator = LLMOrchestrator(self)

    def _reset_lifecycle_state(self, steps: list[dict] | None = None) -> None:
        return self._recorder.reset_lifecycle_state(steps)

    async def _send(self, msg_type: str, **kwargs: Any) -> None:
        await self._emitter.send(msg_type, **kwargs)

    def _emit_backend_event_now(self, msg_type: str, **kwargs: Any) -> None:
        self._emitter.emit_now(msg_type, **kwargs)

    def _emit_recovery_needed_event(
        self,
        step: dict[str, Any] | str | None,
        error_summary: str,
    ) -> None:
        return self._emitter.emit_recovery_needed_event(step, error_summary)

    async def _emit_run_completed_event(
        self,
        source_payload: dict[str, Any],
        recorded_payload: dict[str, Any],
    ) -> None:
        return await self._emitter.emit_run_completed_event(source_payload, recorded_payload)

    def _current_phase(self) -> str:
        phase_tracker = getattr(self, "phase_tracker", None)
        phase_getter = getattr(phase_tracker, "get_phase", None)
        if callable(phase_getter):
            phase_name = str(phase_getter() or "").strip()
            if phase_name:
                return phase_name
        return str(getattr(self, "phase", "") or "").strip() or "planning"

    def _new_run_session_id(self) -> str:
        return f"run-{uuid4().hex}"

    def _current_run_session_id(self) -> str:
        session_id = str(
            getattr(self, "session_id", None)
            or getattr(self, "_run_session_id", None)
            or ""
        ).strip()
        if not session_id:
            session_id = self._new_run_session_id()
        self._run_session_id = session_id
        return session_id

    def _sanitize_capability_gap_detail(self, value: Any) -> Any:
        return self._plan_correction.sanitize_capability_gap_detail(value)

    def _record_capability_gap(
        self,
        category: str,
        source: str,
        severity: str,
        message: str,
        **details: Any,
    ) -> dict[str, Any]:
        return self._plan_correction.record_capability_gap(category, source, severity, message, **details)

    def _append_recorded_step_payload(self, payload: dict[str, Any]) -> None:
        return self._replay.append_recorded_step_payload(payload)

    def _append_code_update_payload(self, payload: dict[str, Any]) -> None:
        return self._replay.append_code_update_payload(payload)

    def _get_replay_recorded_step_payload(self, step_id: str) -> dict[str, Any] | None:
        return self._replay.get_replay_recorded_step_payload(step_id)

    def _get_replay_action_history(self, step_id: str) -> list[dict[str, Any]]:
        return self._replay.get_replay_action_history(step_id)

    def _safe_replay_error_message(self, message: Any) -> str:
        return self._replay.safe_replay_error_message(message)

    def _get_replay_recorded_start_state(self, recorded_step_payload: dict[str, Any]) -> tuple[str, str]:
        return self._replay.get_replay_recorded_start_state(recorded_step_payload)

    def _get_replay_precondition_target_locator(
        self,
        recorded_step_payload: dict[str, Any],
        action_history: list[dict[str, Any]],
    ) -> str:
        return self._replay.get_replay_precondition_target_locator(recorded_step_payload, action_history)

    async def _validate_replay_target_locator(self, locator: str) -> dict[str, Any]:
        return await self._replay.validate_replay_target_locator(locator)

    def _log_replay_precondition_failure(
        self,
        step_id: str,
        reason: str,
        expected_url: str,
        actual_url: str,
        locator: str = "",
    ) -> None:
        return self._replay.log_replay_precondition_failure(step_id, reason, expected_url, actual_url, locator)

    def _build_replay_precondition_failure_result(
        self,
        step_id: str,
        before_url: str,
        before_title: str,
        current_url: str,
        current_title: str,
        message: str,
        *,
        failure_type: str,
        log_reason: str,
        locator: str = "",
    ) -> dict[str, Any]:
        return self._replay.build_replay_precondition_failure_result(step_id, before_url, before_title, current_url, current_title, message)

    async def _check_replay_precondition(
        self,
        step_id: str,
        recorded_step_payload: dict[str, Any],
        action_history: list[dict[str, Any]],
    ) -> dict[str, Any] | None:
        return await self._replay.check_replay_precondition(step_id, recorded_step_payload, action_history)

    def _get_replay_archive_step_ids(self) -> list[str]:
        return self._replay.get_replay_archive_step_ids()

    async def replay_one(self, step_id: str) -> dict[str, Any]:
        return await self._replay.replay_one(step_id)

    async def replay_all(self, stop_on_error: bool = True) -> dict[str, Any]:
        return await self._replay.replay_all(stop_on_error)

    def _build_spec_snapshot(self) -> dict[str, Any]:
        return self._recorder.build_spec_snapshot()

    def _build_session_state_payload(self) -> dict[str, Any]:
        return self._recorder.build_session_state_payload()

    def _skill_entries_from_loaded_skills(
        self,
        loaded_skill_names: list[str],
        loaded_skills: Any,
    ) -> list[tuple[str, str]]:
        return self._skills_loader.skill_entries_from_loaded_skills(loaded_skill_names, loaded_skills)

    def _compose_skill_prompt_from_entries(self) -> str:
        skill_entries = list(getattr(self, "_loaded_skill_entries", []))
        return "\n\n".join(content for _, content in skill_entries)

    def _sync_skill_prompt_from_entries(self) -> str:
        return self._skills_loader.sync_skill_prompt_from_entries()

    def _log_skill_load(self, added_skill_names: list[str], phase: str) -> None:
        return self._skills_loader.log_skill_load(added_skill_names, phase)

    def _log_skill_diagnostics(self) -> None:
        return self._skills_loader.log_skill_diagnostics()

    def _requires_complex_codegen(self) -> bool:
        return self._skills_loader.requires_complex_codegen()

    def _load_phase_skill_expansion(self, phase: str) -> list[str]:
        return self._skills_loader.load_phase_skill_expansion(phase)

    async def run(self, steps: list[dict]) -> None:
        try:
            self._reset_lifecycle_state(steps)
            self.phase_tracker.set_phase("planning", reason="run_started")
            self._prepare_recording_steps(steps)
            self._validate_recording_steps(self.current_steps)
            loaded_skill_names, _, loaded_skills = self._load_skills_for_steps(steps)
            self._loaded_skill_names = list(loaded_skill_names)
            self._loaded_skill_entries = self._skill_entries_from_loaded_skills(
                loaded_skill_names,
                loaded_skills,
            )
            self._last_skill_load_phase = "planning"
            self._sync_skill_prompt_from_entries()
            self.llm.reset()
            self._pending_failure_followup = False

            self._log_skill_load([name for name in loaded_skill_names if name != "core"], "planning")
            self._log_skill_diagnostics()
            print(f"[SKILLS LOADED] {' + '.join(loaded_skill_names)}")
            print("[AGENT] Starting tool-calling loop")

            self.llm.messages.append({"role": "user", "content": self._format_steps(steps)})

            fast_path_handled = await self._try_deterministic_fast_path(self.current_steps)
            if fast_path_handled:
                return

            while True:
                print("[AGENT] Requesting LLM response")
                current_phase = self._current_phase()
                self._load_phase_skill_expansion(current_phase)
                awaiting_step_record = bool(
                    getattr(self, "_awaiting_step_record", False)
                    and getattr(self, "_recording_wait_guard_armed", False)
                )
                correction_mode = getattr(self, "_active_plan_correction_state", None)
                if isinstance(correction_mode, dict) and correction_mode.get("correction_failed"):
                    failure_message = str(
                        correction_mode.get("last_validation_feedback")
                        or "Correction failed safely. The corrected plan could not be validated without risking dropped operations."
                    ).strip()
                    if "You can edit the pending step" not in failure_message:
                        failure_message = f"{failure_message} You can edit the pending step or run it again."
                    print(f"[AGENT] correction failed safely: {self._summarize(failure_message, limit=140)}")
                    await self._send("llm_result", success=False, message=failure_message)
                    self._pending_failure_followup = False
                    self._clear_active_plan_correction_state()
                    return
                confirmed_cursor = self._current_confirmed_execution_cursor()
                if current_phase == "executing" and self.plan_confirmed and isinstance(confirmed_cursor, dict):
                    await self._execute_deterministic_fast_path_confirmed_plan()
                    if self._run_completion_requested:
                        return
                    continue
                if isinstance(correction_mode, dict):
                    correction_result = await self._run_plan_diff_editor_correction(
                        messages=self.llm.messages,
                        phase=current_phase,
                        context_mode="compact",
                    )
                    if correction_result.get("used_controller"):
                        validation_status = str(
                            correction_result.get("validation_status")
                            or correction_result.get("status")
                            or correction_result.get("result")
                            or ""
                        ).strip()
                        parsed_output = correction_result.get("parsed_output")
                        if validation_status != "valid" or not isinstance(parsed_output, dict):
                            failure_message = str(correction_result.get("message") or "").strip()
                            if not failure_message:
                                failure_message = (
                                    "Correction failed safely. The model did not return a structured correction diff. "
                                    "You can edit the pending step or run it again."
                                )
                            if "You can edit the pending step" not in failure_message:
                                failure_message = f"{failure_message} You can edit the pending step or run it again."
                            correction_mode["correction_failed"] = True
                            correction_mode["clarification_closed"] = True
                            correction_mode["needs_clarification"] = False
                            correction_mode["last_validation_reason"] = "invalid structured correction diff"
                            correction_mode["last_validation_feedback"] = failure_message
                            print(
                                "[AGENT] correction failed safely: "
                                f"{self._summarize(failure_message, limit=140)}"
                            )
                            await self._send("llm_result", success=False, message=failure_message)
                            self._pending_failure_followup = False
                            self._clear_active_plan_correction_state()
                            return

                        correction_reason = str(correction_result.get("reason") or "").strip()
                        if correction_reason in {"correction_failed", "correction_diff_required"}:
                            failure_message = str(correction_result.get("message") or "").strip()
                            if "You can edit the pending step" not in failure_message:
                                failure_message = f"{failure_message} You can edit the pending step or run it again."
                            print(
                                "[AGENT] structured correction closed safely: "
                                f"{self._summarize(failure_message or 'Correction failed safely.', limit=140)}"
                            )
                            await self._send(
                                "llm_result",
                                success=False,
                                message=failure_message or "Correction failed safely.",
                            )
                            self._pending_failure_followup = False
                            self._clear_active_plan_correction_state()
                            return

                        if correction_reason == "invalid_corrected_plan":
                            validation_feedback = str(correction_result.get("message") or "").strip()
                            if validation_feedback:
                                self.llm.messages.append({"role": "user", "content": validation_feedback})
                            print(
                                "[AGENT] corrected plan rejected: "
                                f"{self._summarize(validation_feedback or 'invalid corrected plan', limit=140)}"
                            )
                            continue

                        if correction_result.get("confirmed") is False:
                            correction = str(correction_result.get("correction") or "").strip() or "the user requested a correction"
                            note = self._append_plan_correction_message(
                                correction,
                                plan_id=str(correction_result.get("plan_id") or "").strip() or None,
                                target_step_id=str(correction_result.get("target_step_id") or "").strip() or None,
                            )
                            print(f"[AGENT] plan corrected: {self._summarize(note, limit=140)}")
                            continue

                        if correction_result.get("confirmed") is True:
                            continue

                        continue
                if not hasattr(self, "llm_policy_gateway") or self.llm_policy_gateway is None:
                    self.llm_policy_gateway = LLMPolicyGateway(PURPOSE_REGISTRY)
                policy_decision = self.llm_policy_gateway.decide(
                    phase=current_phase,
                    steps=self.current_steps,
                    correction_mode=correction_mode if isinstance(correction_mode, dict) else None,
                    awaiting_step_record=awaiting_step_record,
                    plan_confirmed=self.plan_confirmed,
                )
                self._last_policy_decision = {
                    "model_needed": policy_decision.model_needed,
                    "purpose": policy_decision.purpose,
                    "phase": policy_decision.phase,
                    "allowed_tools": list(policy_decision.allowed_tools),
                    "context_level": policy_decision.context_level,
                    "schema_id": policy_decision.schema_id,
                    "budget": policy_decision.budget,
                    "deterministic_candidate_allowed": policy_decision.deterministic_candidate_allowed,
                    "fallback": policy_decision.fallback,
                    "requires_confirmation": policy_decision.requires_confirmation,
                }
                print(
                    "[POLICY_GATEWAY] "
                    f"phase={policy_decision.phase} "
                    f"purpose={policy_decision.purpose} "
                    f"model_needed={str(policy_decision.model_needed).lower()} "
                    f"allowed_tools={len(policy_decision.allowed_tools)} "
                    f"context_level={policy_decision.context_level} "
                    f"schema_id={policy_decision.schema_id or 'none'} "
                    f"budget={policy_decision.budget} "
                    f"fallback={policy_decision.fallback}"
                )
                effective_purpose = policy_decision.purpose if policy_decision.model_needed else policy_decision.fallback
                purpose_allowed_tool_names = None
                if policy_decision.model_needed and policy_decision.purpose != "main_orchestrator":
                    purpose_allowed_tool_names = set(policy_decision.allowed_tools)
                filtered_tools = filter_tools_for_phase(
                    self.tools,
                    current_phase,
                    awaiting_step_record=awaiting_step_record,
                    correction_mode=correction_mode if isinstance(correction_mode, dict) else None,
                    allowed_tool_names=purpose_allowed_tool_names,
                )
                execution_context = self._build_confirmed_execution_context_message()
                correction_context = ""
                if isinstance(correction_mode, dict):
                    correction_context = self._build_plan_correction_context_message()
                context_bundle = self.context_manager.prepare_messages(
                    self.llm.messages,
                    purpose=effective_purpose,
                    context_mode="normal",
                    metadata={
                        "skill_count": len(self._loaded_skill_names),
                        "tool_count": len(filtered_tools),
                        "phase": current_phase,
                        "execution_context": execution_context,
                        "correction_context": correction_context,
                        "policy_gateway_purpose": policy_decision.purpose,
                        "policy_gateway_budget": policy_decision.budget,
                        "policy_gateway_context_level": policy_decision.context_level,
                        "policy_gateway_model_needed": policy_decision.model_needed,
                        "policy_gateway_deterministic_candidate_allowed": policy_decision.deterministic_candidate_allowed,
                        "policy_gateway_effective_purpose": effective_purpose,
                    },
                )
                self._llm_call_counter += 1
                call_id = f"llm_{self._llm_call_counter:03d}"
                model = "gpt-4o-mini"
                _skill_tokens: int | None = None
                _skill_manager = getattr(self, "skill_manager", None)
                _analyze = getattr(_skill_manager, "analyze", None)
                if callable(_analyze):
                    try:
                        _sd = _analyze(
                            list(getattr(self, "_loaded_skill_entries", [])),
                            loaded_skill_names=list(getattr(self, "_loaded_skill_names", [])),
                        )
                        _skill_tokens = _sd.estimated_total_skill_tokens
                    except Exception:
                        pass
                telemetry = record_model_call_start(
                    call_id=call_id,
                    purpose=effective_purpose,
                    model=model,
                    messages=context_bundle.messages,
                    tools=filtered_tools,
                    skill_count=len(self._loaded_skill_names),
                    skill_tokens=_skill_tokens,
                )
                try:
                    response = await self.model_router.call(
                        purpose=effective_purpose,
                        client=self.llm.client,
                        model=model,
                        messages=context_bundle.messages,
                        tools=filtered_tools,
                        tool_choice="auto",
                    )
                except Exception as exc:  # noqa: BLE001
                    record_model_call_end(
                        telemetry,
                        success=False,
                        error_type=type(exc).__name__,
                        error_message=str(exc),
                    )
                    raise
                record_model_call_end(
                    telemetry,
                    success=True,
                    response_usage=getattr(response, "usage", None),
                )
                message = response.choices[0].message
                self.llm.messages.append(self._assistant_message_entry(message))

                if not message.tool_calls:
                    final_text = (message.content or "").strip()
                    if isinstance(correction_mode, dict) and not correction_mode.get("correction_failed"):
                        correction_mode["no_progress_count"] = int(correction_mode.get("no_progress_count") or 0) + 1
                        schema_retry_count = int(correction_mode.get("schema_retry_count") or 0) + 1
                        correction_mode["schema_retry_count"] = schema_retry_count
                        if schema_retry_count <= 1:
                            retry_message = (
                                "Your previous response did not return a structured correction diff. "
                                "Return only message_type='plan_correction_diff' with target_step_id and mutations. "
                                "Do not send plan_ready or llm_thinking."
                            )
                            self.llm.messages.append({"role": "user", "content": retry_message})
                            print("[AGENT] correction schema retry: no tool calls in correction mode")
                            continue
                        failure_message = (
                            "Correction failed safely. The model did not return a structured correction diff. "
                            "You can edit the pending step or run it again."
                        )
                        correction_mode["correction_failed"] = True
                        correction_mode["clarification_closed"] = True
                        correction_mode["needs_clarification"] = False
                        correction_mode["last_validation_feedback"] = failure_message
                        print(f"[AGENT] correction failed without diff: {self._summarize(failure_message, limit=140)}")
                        await self._send("llm_result", success=False, message=failure_message)
                        self._pending_failure_followup = False
                        self._clear_active_plan_correction_state()
                        return
                    if self.run_stop_requested:
                        print("[AGENT] LLM final response received")
                        await self._send("llm_result", success=True, message=final_text)
                        self._pending_failure_followup = False
                        self._reset_lifecycle_state()
                        return

                    if self._has_unresolved_failure():
                        failed_step = self._get_failed_step_context()
                        failed_step_id = str(
                            (failed_step or {}).get("step_id")
                            or self.active_failed_step_id
                            or ""
                        ).strip() or "unknown"
                        print(f"[AGENT] final response blocked; unresolved failure: {failed_step_id}")
                        answer = await self._tool_ask_user(
                            {
                                "question": self._build_failure_recovery_question(
                                    failed_step,
                                    final_text,
                                ),
                            }
                        )
                        answer_text = str(answer.get("answer") or "").strip()
                        if self._response_requests_stop(answer_text):
                            self.run_stop_requested = True
                            stop_note = self._build_stop_followup_message(failed_step, answer_text)
                            self.llm.messages.append({"role": "user", "content": stop_note})
                            print(f"[AGENT] user requested stop: {self._summarize(stop_note, limit=140)}")
                            continue
                        if self._response_requests_skip(answer_text):
                            skipped_step = self._mark_step_skipped(
                                failed_step_id,
                                answer_text or "User requested skip",
                            )
                            if skipped_step is not None:
                                print(f"[AGENT] step skipped: {failed_step_id}")
                            skip_note = self._build_failure_followup_message(
                                failed_step,
                                answer_text or "skip",
                                skipped=True,
                            )
                            self.llm.messages.append({"role": "user", "content": skip_note})
                            self._pending_failure_followup = False
                            continue
                        followup_note = self._build_failure_followup_message(
                            failed_step,
                            answer_text or "confirmed",
                            skipped=False,
                        )
                        self.llm.messages.append({"role": "user", "content": followup_note})
                        self._pending_failure_followup = False
                        print(f"[AGENT] user follow-up received: {self._summarize(followup_note, limit=140)}")
                        continue

                    if not self._all_steps_done():
                        continue_note = self._build_continue_prompt(final_text)
                        self.llm.messages.append({"role": "user", "content": continue_note})
                        print(f"[AGENT] continuing unresolved steps: {self._summarize(continue_note, limit=140)}")
                        continue

                    if self._should_request_user_followup(final_text, self._pending_failure_followup):
                        print("[AGENT] LLM requested user input; waiting for clarification")
                        answer = await self._tool_ask_user({"question": final_text or "I need your input to continue."})
                        answer_text = str(answer.get("answer") or "").strip()
                        if self._response_requests_stop(answer_text):
                            self.run_stop_requested = True
                            stop_note = f"User explicitly ended the run: {answer_text or 'stop'}. Do not request more actions."
                            self.llm.messages.append({"role": "user", "content": stop_note})
                            print(f"[AGENT] user requested stop: {self._summarize(stop_note, limit=140)}")
                            continue
                        followup_note = self._format_user_followup_message(
                            answer_text,
                            str(answer.get("event_type") or "").strip(),
                        )
                        self.llm.messages.append({"role": "user", "content": followup_note})
                        self._pending_failure_followup = False
                        print(f"[AGENT] user follow-up received: {self._summarize(followup_note, limit=140)}")
                        continue

                    print("[AGENT] LLM final response received")
                    await self._send("llm_result", success=True, message=final_text)
                    self._pending_failure_followup = False
                    self._reset_lifecycle_state()
                    return

                print(f"[AGENT] Executing {len(message.tool_calls)} tool call(s)")
                had_tool_failure = False
                saw_successful_execution_action = False
                saw_step_recorded = False
                pause_for_fresh_page = False
                tool_calls = list(message.tool_calls)
                state_changing_tools = {
                    "action_click",
                    "action_fill",
                    "page_navigate",
                    "page_go_back",
                    "page_go_forward",
                    "page_reload",
                    "scroll_into_view",
                }
                stale_skip_reason = (
                    "Skipped because a previous browser action changed page state. "
                    "Re-query browser state before retrying."
                )
                batch_stop_reason = (
                    "Skipped because the batch was stopped early. Replan before retrying."
                )
                for index, tool_call in enumerate(tool_calls):
                    tool_name = tool_call.function.name
                    if pause_for_fresh_page and self._is_browser_state_tool(tool_name):
                        print(
                            "[AGENT] Pausing batch before stale browser tool "
                            f"{tool_name}; marking remaining tool calls skipped"
                        )
                        self._append_skipped_tool_responses(tool_calls, index, stale_skip_reason)
                        break

                    args = self._parse_tool_args(tool_call.function.arguments or "{}")
                    overlay_message_type = str(args.get("message_type") or "").strip()
                    print(
                        f"[TOOL CALL] {tool_name}({self._summarize(args, limit=100)})"
                    )

                    if not self.plan_confirmed and tool_name in self.EXECUTION_TOOLS:
                        print(f"[AGENT] blocked execution before confirmation: {tool_name}")
                        blocked_result = {
                            "success": False,
                            "blocked": True,
                            "requires_confirmation": True,
                            "reason": (
                                "Execution tool blocked before plan confirmation. "
                                "Send plan_ready and wait for confirmation first."
                            ),
                        }
                        print(f"[TOOL RESULT] {self._summarize(blocked_result, limit=100)}")
                        self._append_tool_response(tool_call.id, blocked_result)
                        continue

                    if (
                        tool_name == "send_to_overlay"
                        and overlay_message_type == "step_recorded"
                        and not self.plan_confirmed
                    ):
                        blocked_result = {
                            "sent": False,
                            "blocked": True,
                            "requires_confirmation": True,
                            "reason": "step_recorded blocked before confirmed execution.",
                        }
                        print(f"[TOOL RESULT] {self._summarize(blocked_result, limit=100)}")
                        self._append_tool_response(tool_call.id, blocked_result)
                        continue

                    if (
                        saw_successful_execution_action
                        and not saw_step_recorded
                        and not had_tool_failure
                        and tool_name not in self.EXECUTION_TOOLS
                        and not (
                            tool_name == "send_to_overlay"
                            and overlay_message_type == "step_recorded"
                        )
                    ):
                        auto_recorded_payload = await self._auto_record_successful_step()
                        if auto_recorded_payload is not None:
                            if self._run_completion_requested:
                                self.phase_tracker.set_phase(
                                    "completed",
                                    reason="all_steps_resolved",
                                    step_id=str(
                                        (auto_recorded_payload or {}).get("step_id")
                                        or ""
                                    ).strip() or None,
                                )
                                if index < len(tool_calls):
                                    self._append_skipped_tool_responses(
                                        tool_calls,
                                        index,
                                        "Skipped because all current steps were already resolved.",
                                    )
                                print("[AGENT] all steps resolved; ending run without extra LLM call")
                                self._pending_failure_followup = False
                                self._reset_lifecycle_state()
                                return

                    if self._should_block_recording_wait_tool(tool_name, args):
                        step_id = str(getattr(self, "active_step_id", "") or "").strip() or "unknown"
                        print(
                            "[RECORDING_GUARD] blocked tool while awaiting_step_record "
                            f"tool={tool_name} step_id={step_id}"
                        )
                        blocked_result = {
                            "success": False,
                            "blocked": True,
                            "reason": "awaiting_step_record",
                            "message": (
                                "A successful action is waiting to be recorded. "
                                "Record the step before using more browser tools."
                            ),
                        }
                        print(f"[TOOL RESULT] {self._summarize(blocked_result, limit=100)}")
                        self._append_tool_response(tool_call.id, blocked_result)
                        continue

                    if self._should_block_additional_execution_action(tool_name, args):
                        print(f"[AGENT] blocked additional execution action before recording: {tool_name}")
                        blocked_result = {
                            "success": False,
                            "blocked": True,
                            "reason": "multi_action_recording_not_supported",
                            "message": (
                                "Only one execution action can be recorded per step until "
                                "multi-action recording is implemented."
                            ),
                        }
                        print(f"[TOOL RESULT] {self._summarize(blocked_result, limit=100)}")
                        self._append_tool_response(tool_call.id, blocked_result)
                        continue

                    step_context = self._resolve_step_context(tool_name, args, {})
                    confirmed_execution_check = None
                    expected_confirmed_child = None
                    if tool_name in self.EXECUTION_TOOLS:
                        confirmed_execution_check = self._validate_confirmed_execution_tool_call(tool_name, args)
                        if isinstance(confirmed_execution_check, dict):
                            expected_confirmed_child = confirmed_execution_check.get("expected_child")
                            if not confirmed_execution_check.get("allowed", False):
                                blocked_result = dict(confirmed_execution_check)
                                blocked_result.pop("allowed", None)
                                print(f"[TOOL RESULT] {self._summarize(blocked_result, limit=100)}")
                                self._append_tool_response(tool_call.id, blocked_result)
                                if isinstance(expected_confirmed_child, dict):
                                    self._record_confirmed_execution_child_result(
                                        step_context or confirmed_execution_check.get("step_id"),
                                        expected_confirmed_child,
                                        tool_name=tool_name,
                                        args=args,
                                        result=blocked_result,
                                        status="blocked",
                                    )
                                if blocked_result.get("terminal"):
                                    contract_stop_reason = (
                                        "Skipped because confirmed execution contract closed the batch. "
                                        "Restart the step from the confirmed child only."
                                    )
                                    self._append_skipped_tool_responses(
                                        tool_calls,
                                        index + 1,
                                        contract_stop_reason,
                                    )
                                    failed_step_id = str(
                                        confirmed_execution_check.get("step_id")
                                        or self.active_failed_step_id
                                        or self.active_step_id
                                        or ""
                                    ).strip() or None
                                    self.phase_tracker.set_phase(
                                        "failed",
                                        reason="execution_contract_violation",
                                        step_id=failed_step_id,
                                    )
                                    self.phase = "failed"
                                    await self._send(
                                        "llm_result",
                                        success=False,
                                        message=str(blocked_result.get("message") or "Execution blocked."),
                                    )
                                    self._pending_failure_followup = False
                                    return
                                contract_stop_reason = (
                                    "Skipped because confirmed execution contract blocked the batch. "
                                    "Retry the confirmed child only."
                                )
                                self._append_skipped_tool_responses(tool_calls, index + 1, contract_stop_reason)
                                break

                    browser_state_before = None
                    if tool_name in self.EXECUTION_TOOLS:
                        browser_state_before = await self._capture_browser_state()

                    result = await self._dispatch_tool(tool_name, args)
                    print(f"[TOOL RESULT] {self._summarize(result, limit=100)}")
                    step_context = self._resolve_step_context(tool_name, args, result)
                    tool_failed = result.get("success") is False and not result.get("skipped") and (
                        self._is_browser_state_tool(tool_name) or tool_name == "ask_user"
                    )
                    recovery_decision = None
                    if tool_failed and tool_name in self.EXECUTION_TOOLS:
                        if step_context is None:
                            raise RuntimeError(
                                f"Unable to resolve failed step safely for {tool_name}"
                            )
                        failed_step_id = str(step_context.get("step_id") or "").strip()
                        if not failed_step_id:
                            raise RuntimeError(
                                f"Unable to resolve failed step id safely for {tool_name}"
                            )
                        recovery_decision = classify_failure(
                            tool_name,
                            step_id=failed_step_id,
                            result=result,
                        )
                        if isinstance(confirmed_execution_check, dict) and confirmed_execution_check.get("allowed", False):
                            expected_confirmed_child = confirmed_execution_check.get("expected_child")
                            if isinstance(expected_confirmed_child, dict):
                                self._record_confirmed_execution_child_result(
                                    step_context or confirmed_execution_check.get("step_id"),
                                    expected_confirmed_child,
                                    tool_name=tool_name,
                                    args=args,
                                    result=result,
                                    status="failed",
                                    browser_state_before=browser_state_before,
                                )
                        self._mark_step_failed(step_context, result.get("error") or "execution tool failed")
                    had_tool_failure = had_tool_failure or tool_failed
                    if (
                        result.get("success") is True
                        and not result.get("skipped")
                        and tool_name in self.EXECUTION_TOOLS
                    ):
                        browser_state_after = await self._capture_browser_state()
                        if isinstance(confirmed_execution_check, dict) and confirmed_execution_check.get("allowed", False):
                            expected_confirmed_child = confirmed_execution_check.get("expected_child")
                            if isinstance(expected_confirmed_child, dict):
                                self._record_confirmed_execution_child_result(
                                    step_context or confirmed_execution_check.get("step_id"),
                                    expected_confirmed_child,
                                    tool_name=tool_name,
                                    args=args,
                                    result=result,
                                    status="success",
                                    browser_state_before=browser_state_before,
                                    browser_state_after=browser_state_after,
                                )
                        self._mark_step_executing(step_context)
                        self._capture_action_context(
                            tool_name,
                            args,
                            result,
                            browser_state_before=browser_state_before,
                            browser_state_after=browser_state_after,
                        )
                        saw_successful_execution_action = True
                    if (
                        tool_name == "send_to_overlay"
                        and overlay_message_type == "step_recorded"
                        and result.get("sent") is True
                    ):
                        saw_step_recorded = True
                    self.llm.messages.append(
                        {
                            "role": "tool",
                            "tool_call_id": tool_call.id,
                            "content": json.dumps(result, ensure_ascii=True),
                        }
                    )
                    clarification_resolution_message = str(result.get("clarification_resolution_message") or "").strip()
                    if tool_name == "ask_user" and clarification_resolution_message:
                        self.llm.messages.append({"role": "user", "content": clarification_resolution_message})
                    if self._run_completion_requested:
                        self.phase_tracker.set_phase(
                            "completed",
                            reason="all_steps_resolved",
                            step_id=str(
                                (result.get("payload") or {}).get("step_id")
                                or ""
                            ).strip() or None,
                        )
                        if index + 1 < len(tool_calls):
                            self._append_skipped_tool_responses(
                                tool_calls,
                                index + 1,
                                "Skipped because all current steps were already resolved.",
                            )
                        print("[AGENT] all steps resolved; ending run without extra LLM call")
                        self._pending_failure_followup = False
                        self._reset_lifecycle_state()
                        return
                    is_correction_terminal = (
                        tool_name == "send_to_overlay"
                        and str(result.get("reason") or "").strip() in {"correction_failed", "correction_diff_required"}
                    )
                    if not is_correction_terminal and tool_name == "ask_user":
                        is_correction_terminal = str(result.get("reason") or "").strip() == "clarification_already_answered"
                    if is_correction_terminal:
                        self._append_skipped_tool_responses(tool_calls, index + 1, batch_stop_reason)
                        failure_message = str(result.get("message") or "").strip()
                        if "You can edit the pending step" not in failure_message:
                            failure_message = f"{failure_message} You can edit the pending step or run it again."
                        if failure_message:
                            self.llm.messages.append({"role": "user", "content": failure_message})
                        print(
                            "[AGENT] structured correction closed safely: "
                            f"{self._summarize(failure_message or 'Correction failed safely.', limit=140)}"
                        )
                        await self._send(
                            "llm_result",
                            success=False,
                            message=failure_message or "Correction failed safely.",
                        )
                        self._pending_failure_followup = False
                        self._clear_active_plan_correction_state()
                        return
                    is_plan_correction_rejected = (
                        tool_name == "send_to_overlay"
                        and overlay_message_type in {"plan_ready", "plan_correction_diff"}
                        and (
                            result.get("confirmed") is False
                            or str(result.get("reason") or "").strip() == "invalid_corrected_plan"
                        )
                    )
                    if is_plan_correction_rejected:
                        self._append_skipped_tool_responses(tool_calls, index + 1, batch_stop_reason)
                        if result.get("confirmed") is False:
                            correction = str(result.get("correction") or "").strip() or "the user requested a correction"
                            note = self._append_plan_correction_message(
                                correction,
                                plan_id=str(result.get("plan_id") or "").strip() or None,
                                target_step_id=str(result.get("target_step_id") or "").strip() or None,
                            )
                            print(f"[AGENT] plan corrected: {self._summarize(note, limit=140)}")
                        else:
                            validation_feedback = str(result.get("message") or "").strip()
                            if validation_feedback:
                                self.llm.messages.append({"role": "user", "content": validation_feedback})
                            print(
                                "[AGENT] corrected plan rejected: "
                                f"{self._summarize(validation_feedback or 'invalid corrected plan', limit=140)}"
                            )
                        break
                    if recovery_decision is not None and recovery_decision.stop_batch:
                        print(f"[AGENT] {tool_name} failed; stopping batch for LLM recovery")
                        self._append_skipped_tool_responses(tool_calls, index + 1, batch_stop_reason)
                        break
                    if tool_name in state_changing_tools and result.get("success") is True and not result.get("skipped"):
                        pause_for_fresh_page = True
                        self.phase = "recovering" if had_tool_failure else "executing"

                if (
                    saw_successful_execution_action
                    and not saw_step_recorded
                    and not had_tool_failure
                ):
                    auto_recorded_payload = await self._auto_record_successful_step()
                    if auto_recorded_payload is not None:
                        if self._run_completion_requested:
                            self.phase_tracker.set_phase(
                                "completed",
                                reason="all_steps_resolved",
                                step_id=str(
                                    (auto_recorded_payload or {}).get("step_id")
                                    or ""
                                ).strip() or None,
                            )
                            print("[AGENT] all steps resolved; ending run without extra LLM call")
                            self._pending_failure_followup = False
                            self._reset_lifecycle_state()
                            return

                if (
                    self._awaiting_step_record
                    and saw_successful_execution_action
                    and not saw_step_recorded
                ):
                    self._recording_wait_guard_armed = True
                elif not self._awaiting_step_record:
                    self._recording_wait_guard_armed = False

                if had_tool_failure:
                    self._pending_failure_followup = True
                    failed_step_id = str(self.active_failed_step_id or self.active_step_id or "").strip() or None
                    self.phase_tracker.set_phase(
                        "recovery",
                        reason="tool_failed",
                        step_id=failed_step_id,
                    )
                    self.phase = "recovering"
                    print("[AGENT] Tool failure observed in batch; awaiting LLM recovery")
                    continue
        except Exception as exc:  # noqa: BLE001
            failed_step_id = str(self.active_failed_step_id or self.active_step_id or "").strip() or None
            self._clear_plan_review_context()
            self._plan_correction_pending = False
            self.phase_tracker.set_phase(
                "failed",
                reason="unhandled_exception",
                step_id=failed_step_id,
            )
            print(f"[AGENT] Failed: {type(exc).__name__}: {exc}")
            await self._send("error", message=f"Agent failed: {type(exc).__name__}: {exc}")

    def _should_request_user_followup(self, final_text: str, had_tool_failure: bool) -> bool:
        return self._llm_orchestrator.should_request_user_followup(final_text, had_tool_failure)

    def _looks_like_completion_message(self, text: str) -> bool:
        return self._llm_orchestrator.looks_like_completion_message(text)

    def _format_user_followup_message(self, answer: str, event_type: str) -> str:
        return self._llm_orchestrator.format_user_followup_message(answer, event_type)

    def _is_correction_followup(self, answer: str, event_type: str) -> bool:
        return self._llm_orchestrator.is_correction_followup(answer, event_type)

    def _is_browser_state_tool(self, tool_name: str) -> bool:
        return self._tool_dispatcher.is_browser_state_tool(tool_name)

    def _load_skills_for_steps(self, steps: list[dict]) -> tuple[list[str], str, dict[str, str]]:
        return self._skills_loader.load_skills_for_steps(steps)

    def _read_skill(self, skill_name: str, *, compact_mode: bool = False) -> str | None:
        return self._skills_loader.read_skill(skill_name)

    async def _try_deterministic_fast_path(self, steps: list[dict]) -> bool:
        """Attempt zero-LLM planning through the extracted deterministic gateway."""
        return await attempt_deterministic_fast_path(self, steps, get_page=get_page)

    def _build_confirmed_execution_tool_call(
        self,
        child: dict[str, Any],
        *,
        step_context: dict[str, Any] | None = None,
    ) -> tuple[str, dict[str, Any]]:
        return self._plan_state.build_confirmed_execution_tool_call(child, step_context=step_context)

    async def _execute_deterministic_fast_path_confirmed_plan(self) -> None:
        return await self._plan_state.execute_deterministic_fast_path_confirmed_plan()

    def _is_click_like_intent(self, intent: Any) -> bool:
        normalized_intent = self._normalize_space(str(intent or "")).lower()
        return bool(CLICK_LIKE_INTENT_PATTERN.search(normalized_intent))

    def _is_outcome_like_label(self, value: Any) -> bool:
        return self._plan_builder.is_outcome_like_label(value)

    def _extract_assertion_expected_value(self, value: Any) -> str:
        return self._plan_builder.extract_assertion_expected_value(value)

    def _select_plan_correction_child_target(self, candidates: list[tuple[str, Any]]) -> str:
        return self._plan_correction.select_plan_correction_child_target(candidates)

    def _canonicalize_assertion_operation(
        self,
        operation_spec: dict[str, Any],
        source_step: dict[str, Any] | None = None,
        anchor_child: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        return self._plan_builder.canonicalize_assertion_operation(operation_spec, source_step, anchor_child)

    def _build_plan_correction_child_description(
        self,
        operation_type: str,
        target: str,
        assertion: str,
        value_text: str,
        raw_description: str,
        intent: str,
    ) -> str:
        return self._plan_correction.build_plan_correction_child_description(operation_type, target, assertion, value_text, raw_description, intent)

    def _normalize_expected_outcome(
        self,
        expected_outcome: Any,
        required: bool = False,
    ) -> dict[str, Any] | None:
        return self._plan_builder.normalize_expected_outcome(expected_outcome, required)

    def _expected_outcome_summary(self, expected_outcome: Any) -> str:
        return self._plan_builder.expected_outcome_summary(expected_outcome)

    def _resolve_selected_element_info(self, element_info: dict[str, Any]) -> dict[str, Any]:
        return self._plan_builder.resolve_selected_element_info(element_info)

    def _selected_element_text(self, element_info: dict[str, Any]) -> str:
        return self._plan_builder.selected_element_text(element_info)

    def _element_candidate_display_text(self, element_info: dict[str, Any]) -> str:
        return self._plan_builder.element_candidate_display_text(element_info)

    def _best_fast_path_target_label(self, step: dict[str, Any], action_verb: str) -> str:
        return self._plan_builder.best_fast_path_target_label(step, action_verb)

    def _should_replace_fast_path_locator_with_text(self, action_verb: str, locator: str) -> bool:
        return self._plan_builder.should_replace_fast_path_locator_with_text(action_verb, locator)

    def _compact_step_element_summary(self, step: dict[str, Any]) -> str:
        return self._plan_builder.compact_step_element_summary(step)

    def _validate_recording_steps(self, steps: list[dict[str, Any]]) -> None:
        return self._plan_builder.validate_recording_steps(steps)

    def _format_steps(self, steps: list[dict]) -> str:
        return self._plan_builder.format_steps(steps)

    def _prepare_recording_steps(self, steps: list[dict]) -> None:
        return self._step_manager.prepare_recording_steps(steps)

    def _get_step_context(self, step_id: str | None = None) -> dict[str, Any] | None:
        return self._step_manager.get_step_context(step_id)

    def _resolve_recording_target_step(self, payload: dict[str, Any] | None = None) -> dict[str, Any] | None:
        return self._step_manager.resolve_recording_target_step(payload)

    def _get_failed_step_context(self) -> dict[str, Any] | None:
        return self._step_manager.get_failed_step_context()

    def _mark_step_executing(self, step: dict[str, Any] | str | None) -> dict[str, Any] | None:
        return self._step_manager.mark_step_executing(step)

    def _mark_step_failed(self, step: dict[str, Any] | str | None, error: Any) -> dict[str, Any] | None:
        return self._step_manager.mark_step_failed(step, error)

    def _clear_failed_step_success_state(self, step: dict[str, Any] | str | None) -> None:
        return self._step_manager.clear_failed_step_success_state(step)

    def _clear_plan_review_context(self) -> None:
        return self._plan_correction.clear_plan_review_context()

    def _clear_confirmed_execution_contract_state(self) -> None:
        return self._plan_state.clear_confirmed_execution_contract_state()

    def _clear_active_plan_correction_state(self) -> None:
        return self._plan_state.clear_active_plan_correction_state()

    def _clear_active_plan_state(self) -> None:
        return self._plan_state.clear_active_plan_state()

    def _record_plan_diff_editor_telemetry(self, **payload: Any) -> None:
        self._plan_diff_editor_telemetry.append(dict(payload))

    def _validate_plan_diff_editor_output(self, **payload: Any) -> dict[str, Any]:
        return self._plan_correction.validate_plan_diff_editor_output(**payload)

    async def _call_plan_diff_editor_controller(
        self,
        *,
        messages: list[dict[str, Any]],
        phase: str | None,
        context_mode: str = "normal",
    ) -> dict[str, Any]:
        return await self._plan_correction.call_plan_diff_editor_controller()

    async def _run_plan_diff_editor_correction(
        self,
        *,
        messages: list[dict[str, Any]],
        phase: str | None,
        context_mode: str = "normal",
    ) -> dict[str, Any]:
        return await self._plan_correction.run_plan_diff_editor_correction()

    def _current_active_plan_state(self) -> dict[str, Any] | None:
        return self._plan_state.current_active_plan_state()

    def _current_plan_version(self) -> int:
        return self._plan_state.current_plan_version()

    def _confirmation_context(self, payload: dict[str, Any] | None) -> dict[str, str]:
        return self._plan_confirmation.confirmation_context(payload)

    def _confirmation_context_mismatch_reason(
        self,
        active_context: dict[str, str] | None,
        event_context: dict[str, str] | None,
    ) -> str | None:
        return self._plan_confirmation.confirmation_context_mismatch_reason(active_context, event_context)

    def _completed_run_confirmation_rejection_reason(self, event_context: dict[str, str] | None) -> str | None:
        return self._plan_confirmation.completed_run_confirmation_rejection_reason(event_context)

    def _plan_steps_from_state(self, plan_state: dict[str, Any] | None) -> list[dict[str, Any]]:
        return self._plan_state.plan_steps_from_state(plan_state)

    def _plan_child_operations_from_step(self, step: dict[str, Any]) -> list[dict[str, Any]]:
        return self._plan_state.plan_child_operations_from_step(step)

    def _plan_operation_text(self, operation: dict[str, Any] | None) -> str:
        return self._plan_state.plan_operation_text(operation)

    def _plan_operation_type(self, operation: dict[str, Any] | None) -> str:
        if not isinstance(operation, dict):
            return ""
        return self._normalize_space(str(operation.get("type") or operation.get("action") or "")).lower()

    def _plan_operation_signature(self, operation: dict[str, Any] | None) -> str:
        return self._plan_state.plan_operation_signature(operation)

    def _plan_operation_types_from_state(self, plan_state: dict[str, Any] | None) -> list[str]:
        return self._plan_state.plan_operation_types_from_state(plan_state)

    def _plan_operation_signatures_from_state(self, plan_state: dict[str, Any] | None) -> list[str]:
        return self._plan_state.plan_operation_signatures_from_state(plan_state)

    def _sequence_contains_subsequence(self, sequence: list[str], subsequence: list[str]) -> bool:
        return self._plan_state.sequence_contains_subsequence(sequence, subsequence)

    def _build_active_plan_state(
        self,
        payload: dict[str, Any],
        source_plan_state: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        return self._plan_state.build_active_plan_state(payload, source_plan_state)

    def _infer_confirmed_execution_child_assertion(
        self,
        child: dict[str, Any] | None,
        source_step: dict[str, Any] | None = None,
    ) -> str:
        return self._plan_state.infer_confirmed_execution_child_assertion(child, source_step)

    def _normalize_confirmed_execution_child(
        self,
        child: dict[str, Any] | None,
        source_step: dict[str, Any] | None = None,
        child_index: int = 1,
    ) -> dict[str, Any]:
        return self._plan_state.normalize_confirmed_execution_child(child, source_step, child_index)

    def _build_confirmed_execution_plan(
        self,
        payload: dict[str, Any],
        source_plan_state: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        return self._plan_state.build_confirmed_execution_plan(payload, source_plan_state)

    def _store_confirmed_execution_plan(self, payload: dict[str, Any]) -> dict[str, Any]:
        return self._plan_state.store_confirmed_execution_plan(payload)

    def _current_confirmed_execution_cursor(self) -> dict[str, Any] | None:
        return self._plan_state.current_confirmed_execution_cursor()

    def _log_confirmed_execution_cursor(self, prefix: str) -> None:
        return self._plan_state.log_confirmed_execution_cursor(prefix)

    def _confirmed_execution_contract_for_step(
        self,
        step: dict[str, Any] | str | None = None,
    ) -> dict[str, Any] | None:
        return self._plan_state.confirmed_execution_contract_for_step(step)

    def _confirmed_execution_results_for_step(self, step_id: str | None) -> dict[str, Any]:
        return self._plan_state.confirmed_execution_results_for_step(step_id)

    def _confirmed_execution_next_child_for_step(
        self,
        step: dict[str, Any] | str | None = None,
    ) -> tuple[dict[str, Any] | None, dict[str, Any] | None, dict[str, Any] | None]:
        return self._plan_state.confirmed_execution_next_child_for_step(step)

    def _confirmed_execution_step_ready_to_record(
        self,
        step: dict[str, Any] | str | None = None,
    ) -> bool:
        return self._plan_state.confirmed_execution_step_ready_to_record(step)

    def _build_confirmed_execution_context_message(self) -> str:
        return self._plan_state.build_confirmed_execution_context_message()

    def _locator_matches_confirmed_execution_child(
        self,
        expected_locator: str,
        actual_locator: str,
    ) -> bool:
        return self._plan_state.locator_matches_confirmed_execution_child(expected_locator, actual_locator)

    def _assertion_matches_confirmed_execution_child(
        self,
        expected_child: dict[str, Any],
        actual_assertion: str,
        actual_args: dict[str, Any],
    ) -> bool:
        return self._plan_state.assertion_matches_confirmed_execution_child(expected_child, actual_assertion, actual_args)

    def _value_matches_confirmed_execution_child(
        self,
        expected_child: dict[str, Any],
        actual_args: dict[str, Any],
    ) -> bool:
        return self._plan_state.value_matches_confirmed_execution_child(expected_child, actual_args)

    def _describe_confirmed_execution_child(self, child: dict[str, Any] | None) -> str:
        return self._plan_state.describe_confirmed_execution_child(child)

    def _describe_confirmed_execution_call(self, tool_name: str, args: dict[str, Any]) -> str:
        return self._plan_state.describe_confirmed_execution_call(tool_name, args)

    def _record_confirmed_execution_child_result(
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
        return self._plan_state.record_confirmed_execution_child_result(step, child)

    def _validate_confirmed_execution_tool_call(
        self,
        tool_name: str,
        args: dict[str, Any],
        result: dict[str, Any] | None = None,
    ) -> dict[str, Any] | None:
        return self._plan_state.validate_confirmed_execution_tool_call(tool_name, args, result)

    def _classify_plan_correction(
        self,
        correction: str,
        active_plan_state: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        return self._plan_correction.classify_plan_correction(correction, active_plan_state)

    def _build_plan_correction_validation_feedback(
        self,
        correction_state: dict[str, Any],
        validation_reason: str,
        active_plan_state: dict[str, Any] | None = None,
        proposed_payload: dict[str, Any] | None = None,
    ) -> str:
        return self._plan_correction.build_plan_correction_validation_feedback(correction_state, validation_reason, active_plan_state, proposed_payload)

    def _build_plan_correction_operation_context_lines(
        self,
        active_plan_state: dict[str, Any] | None,
    ) -> list[str]:
        return self._plan_correction.build_plan_correction_operation_context_lines(active_plan_state)

    def _build_plan_correction_context_message(self) -> str:
        return self._plan_correction.build_plan_correction_context_message()

    def _build_plan_diff_editor_schema_message(self) -> str:
        return self._plan_correction.build_plan_diff_editor_schema_message()

    def _synthesize_plan_diff_editor_output(self) -> dict[str, Any]:
        return self._plan_correction.synthesize_plan_diff_editor_output()

    def _build_plan_correction_clarification_message(
        self,
        correction_state: dict[str, Any],
        answer: str,
    ) -> str:
        return self._plan_correction.build_plan_correction_clarification_message(correction_state, answer)

    def _build_plan_correction_state(
        self,
        correction: str,
        source_plan_state: dict[str, Any] | None = None,
        target_step_id: str | None = None,
    ) -> dict[str, Any]:
        return self._plan_correction.build_plan_correction_state(correction, source_plan_state, target_step_id)

    def _build_plan_correction_added_child(
        self,
        operation_spec: dict[str, Any],
        source_step: dict[str, Any],
        anchor_child: dict[str, Any] | None,
        operation_id: str,
    ) -> dict[str, Any]:
        return self._plan_correction.build_plan_correction_added_child(operation_spec, source_step, anchor_child, operation_id)

    def _build_structured_plan_correction_payload_from_diff(
        self,
        diff_payload: dict[str, Any],
    ) -> dict[str, Any]:
        return self._plan_correction.build_structured_plan_correction_payload_from_diff(diff_payload)

    def _validate_structured_plan_step(
        self,
        active_step: dict[str, Any],
        proposed_step: dict[str, Any],
        correction_state: dict[str, Any],
        active_plan_state: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        return self._plan_correction.validate_structured_plan_step(active_step, proposed_step, correction_state, active_plan_state)

    def _validate_structured_plan_correction(
        self,
        proposed_payload: dict[str, Any],
    ) -> dict[str, Any]:
        return self._plan_correction.validate_structured_plan_correction(proposed_payload)

    def _remember_plan_review_context(self, payload: dict[str, Any]) -> None:
        return self._plan_correction.remember_plan_review_context(payload)

    def _build_plan_step_context_lines(self, plan_payload: dict[str, Any] | None = None) -> list[str]:
        return self._plan_correction.build_plan_step_context_lines(plan_payload)

    def _build_plan_correction_message(
        self,
        correction: str,
        plan_id: str | None = None,
        target_step_id: str | None = None,
    ) -> str:
        return self._plan_correction.build_plan_correction_message(correction, plan_id, target_step_id)

    def _append_plan_correction_message(
        self,
        correction: str,
        plan_id: str | None = None,
        target_step_id: str | None = None,
    ) -> str:
        return self._plan_correction.append_plan_correction_message(correction, plan_id, target_step_id)

    def _mark_step_skipped(self, step: dict[str, Any] | str | None, reason: Any) -> dict[str, Any] | None:
        return self._step_manager.mark_step_skipped(step, reason)

    def _has_unresolved_steps(self) -> bool:
        return self._step_manager.has_unresolved_steps()

    def _has_unresolved_failure(self) -> bool:
        return self._step_manager.has_unresolved_failure()

    def _all_steps_done(self) -> bool:
        return self._step_manager.all_steps_done()

    def _all_steps_resolved(self) -> bool:
        return self._step_manager.all_steps_resolved()

    def _step_state_summary(self, step: dict[str, Any] | None) -> dict[str, Any]:
        return self._step_manager.step_state_summary(step)

    def _current_browser_url(self) -> str:
        return self._step_manager.current_browser_url()

    def _build_failure_recovery_question(self, step: dict[str, Any] | None, final_text: str) -> str:
        return self._step_manager.build_failure_recovery_question(step, final_text)

    def _build_failure_followup_message(
        self,
        step: dict[str, Any] | None,
        answer_text: str,
        *,
        skipped: bool,
    ) -> str:
        return self._step_manager.build_failure_followup_message(step, answer_text, skipped)

    def _build_stop_followup_message(self, step: dict[str, Any] | None, answer_text: str) -> str:
        return self._step_manager.build_stop_followup_message(step, answer_text)

    def _build_continue_prompt(self, final_text: str) -> str:
        return self._step_manager.build_continue_prompt(final_text)

    def _response_requests_skip(self, answer_text: str) -> bool:
        return self._step_manager.response_requests_skip(answer_text)

    def _response_requests_stop(self, answer_text: str) -> bool:
        return self._step_manager.response_requests_stop(answer_text)

    def _derive_step_context_element_name(self, step: dict[str, Any], element_info: dict[str, Any]) -> str:
        return self._step_manager.derive_step_context_element_name(step, element_info)

    def _step_context_text(self, step: dict[str, Any]) -> str:
        return self._step_manager.step_context_text(step)

    def _score_step_context(
        self,
        step: dict[str, Any],
        locator_hint: str,
        intent_hint: str,
        element_text_hint: str,
    ) -> int:
        return self._step_manager.score_step_context(step, locator_hint, intent_hint, element_text_hint)

    def _resolve_step_context(
        self,
        tool_name: str,
        args: dict[str, Any],
        result: dict[str, Any],
    ) -> dict[str, Any] | None:
        return self._step_manager.resolve_step_context(tool_name, args, result)

    def _has_successful_action_to_record(
        self,
        step_context: dict[str, Any] | None = None,
        payload: dict[str, Any] | None = None,
    ) -> bool:
        return self._recorder.has_successful_action_to_record(step_context, payload)

    def _should_block_additional_execution_action(
        self,
        tool_name: str,
        args: dict[str, Any],
    ) -> bool:
        return self._recorder.should_block_additional_execution_action(tool_name, args)

    async def _record_step_payload(
        self,
        payload: dict[str, Any],
        step_context: dict[str, Any] | None = None,
    ) -> dict[str, Any] | None:
        return await self._recorder.record_step_payload(payload, step_context)

    async def _auto_record_successful_step(self) -> dict[str, Any] | None:
        return await self._recorder.auto_record_successful_step()

    def _should_block_recording_wait_tool(
        self,
        tool_name: str,
        args: dict[str, Any],
    ) -> bool:
        return self._recorder.should_block_recording_wait_tool(tool_name, args)

    def _get_successful_action_for_step(
        self,
        step_context: dict[str, Any] | None = None,
        payload: dict[str, Any] | None = None,
    ) -> dict[str, Any] | None:
        return self._recorder.get_successful_action_for_step(step_context, payload)

    def _get_successful_action_history_for_step(
        self,
        step_context: dict[str, Any] | None = None,
        payload: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        return self._recorder.get_successful_action_history_for_step(step_context, payload)

    def _coerce_step_number(self, value: Any) -> int | None:
        return self._step_manager.coerce_step_number(value)

    async def _capture_browser_state(self) -> dict[str, str] | None:
        return await self._recorder.capture_browser_state()

    def _normalize_browser_state_snapshot(self, browser_state: Any) -> dict[str, str] | None:
        return self._recorder.normalize_browser_state_snapshot(browser_state)

    def _build_observed_outcome(
        self,
        action_history: list[dict[str, Any]],
        expected_outcome: Any,
    ) -> dict[str, Any]:
        return self._recorder.build_observed_outcome(action_history, expected_outcome)

    def _capture_action_context(
        self,
        tool_name: str,
        args: dict[str, Any],
        result: dict[str, Any],
        browser_state_before: dict[str, str] | None = None,
        browser_state_after: dict[str, str] | None = None,
    ) -> None:
        return self._recorder.capture_action_context(tool_name, args, result, browser_state_before, browser_state_after)

    def _action_name_for_tool(self, tool_name: str) -> str:
        return self._recorder.action_name_for_tool(tool_name)

    def _current_pending_step(self) -> dict[str, Any] | None:
        return self._step_manager.current_pending_step()

    def _find_step_for_recording(
        self,
        step_id: str | None = None,
        step_number: int | None = None,
    ) -> dict[str, Any] | None:
        return self._step_manager.find_step_for_recording(step_id, step_number)

    def _advance_recording_cursor(self) -> None:
        return self._step_manager.advance_recording_cursor()

    def _mark_step_recorded(
        self,
        step: dict[str, Any] | str | None,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any] | None:
        return self._step_manager.mark_step_recorded(step, metadata)

    def _derive_element_name(
        self,
        step: dict[str, Any],
        action_context: dict[str, Any],
        locator: str,
    ) -> str:
        return self._codegen.derive_element_name(step, action_context, locator)

    def _locator_label_hint(self, locator: str) -> str:
        return self._codegen.locator_label_hint(locator)

    def _canonical_confirmed_execution_locator(self, locator: str) -> str:
        return self._codegen.canonical_confirmed_execution_locator(locator)

    def _match_tool_locator_call(self, locator: str, function_name: str) -> str:
        return self._codegen.match_tool_locator_call(locator, function_name)
    def _match_tool_locator_text(self, locator: str) -> tuple[str, bool] | None:
        return self._codegen.match_tool_locator_text(locator)
    def _match_tool_locator_role(self, locator: str) -> tuple[str, str] | None:
        return self._codegen.match_tool_locator_role(locator)
    def _build_generated_line(
        self,
        action: str,
        locator: str,
        action_context: dict[str, Any],
    ) -> str:
        return self._codegen.build_generated_line(action, locator, action_context)

    def _locator_to_playwright_expression(self, locator: str) -> str:
        return self._codegen.locator_to_playwright_expression(locator)

    def _build_step_record_payload(
        self,
        payload: dict[str, Any],
        step_context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        return self._recorder.build_step_record_payload(payload, step_context)

    def _derive_locator_from_step_context(self, step: dict[str, Any]) -> str:
        return self._step_manager.derive_locator_from_step_context(step)

    def _normalize_steps(self, steps: list[dict]) -> list[dict[str, Any]]:
        return self._plan_builder.normalize_steps(steps)

    def _infer_operation_type(self, intent: str) -> str:
        return self._plan_builder.infer_operation_type(intent)

    def _infer_planned_operation_sequence(self, intent: str) -> list[str]:
        return self._plan_builder.infer_planned_operation_sequence(intent)

    def _build_planned_child_description(self, operation_type: str, target: str, intent: str) -> str:
        return self._plan_builder.build_planned_child_description(operation_type, target, intent)

    def _build_planned_children(
        self,
        step: dict[str, Any],
        existing_plan_data: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        return self._plan_builder.build_planned_children(step, existing_plan_data)

    def _build_plan_ready_parent_step(
        self,
        plan_step: dict[str, Any],
        source_step: dict[str, Any],
        step_index: int,
    ) -> dict[str, Any]:
        return self._plan_builder.build_plan_ready_parent_step(plan_step, source_step, step_index)

    def _build_recorded_child_description(
        self,
        action: str,
        operation_type: str,
        target: str,
        action_context: dict[str, Any],
        intent: str,
    ) -> str:
        return self._plan_builder.build_recorded_child_description(action, operation_type, target, action_context, intent)

    def _is_technical_recorded_label_text(self, value: Any) -> bool:
        return self._plan_builder.is_technical_recorded_label_text(value)

    def _build_recorded_children(
        self,
        action_records: list[dict[str, Any]],
        intent: str,
        element_name: str,
        locator: str,
        confirmed_children: list[dict[str, Any]] | None = None,
        confirmed_child_results: dict[str, Any] | None = None,
        confirmed_step: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        return self._plan_builder.build_recorded_children(action_records, intent, element_name, locator, confirmed_children, confirmed_child_results, confirmed_step)

    def _build_code_update_payload(self, payload: dict[str, Any], step_id: str) -> dict[str, Any]:
        return self._codegen.build_code_update_payload(payload, step_id)

    def _build_plan_ready_payload(
        self,
        payload: dict[str, Any],
        prefer_plan_step_source: bool = False,
    ) -> dict[str, Any]:
        return self._plan_builder.build_plan_ready_payload(payload, prefer_plan_step_source)

    def _assistant_message_entry(self, message: Any) -> dict[str, Any]:
        return self._llm_orchestrator.assistant_message_entry(message)

    def _parse_tool_args(self, raw_args: str) -> dict[str, Any]:
        return self._tool_dispatcher.parse_tool_args(raw_args)

    def _build_tool_definitions(self) -> list[dict[str, Any]]:
        return self._tool_definitions.build()

    async def _dispatch_tool(self, tool_name: str, args: dict[str, Any]) -> dict[str, Any]:
        return await self._tool_dispatcher.dispatch(tool_name, args)

    async def _tool_dom_extract(self, args: dict[str, Any]) -> dict[str, Any]:
        return await tool_dom_extract(self, args, get_page=get_page)

    async def _tool_locator_find(self, args: dict[str, Any]) -> dict[str, Any]:
        return await tool_locator_find(self, args, get_page=get_page)

    async def _tool_locator_validate(self, args: dict[str, Any]) -> dict[str, Any]:
        return await tool_locator_validate(self, args, get_page=get_page)

    async def _tool_action_click(self, args: dict[str, Any]) -> dict[str, Any]:
        return await self._tool_dispatcher.tool_action_click(args)

    async def _tool_action_fill(self, args: dict[str, Any]) -> dict[str, Any]:
        return await self._tool_dispatcher.tool_action_fill(args)

    async def _tool_action_assert(self, args: dict[str, Any]) -> dict[str, Any]:
        return await self._tool_dispatcher.tool_action_assert(args)

    async def _tool_page_navigate(self, args: dict[str, Any]) -> dict[str, Any]:
        return await self._tool_dispatcher.tool_page_navigate(args)

    async def _tool_page_go_back(self, args: dict[str, Any]) -> dict[str, Any]:
        return await self._tool_dispatcher.tool_page_go_back(args)

    async def _tool_page_go_forward(self, args: dict[str, Any]) -> dict[str, Any]:
        return await self._tool_dispatcher.tool_page_go_forward(args)

    async def _tool_page_reload(self, args: dict[str, Any]) -> dict[str, Any]:
        return await self._tool_dispatcher.tool_page_reload(args)

    async def _tool_scroll_into_view(self, args: dict[str, Any]) -> dict[str, Any]:
        return await self._tool_dispatcher.tool_scroll_into_view(args)

    async def _tool_browser_get_state(self, args: dict[str, Any]) -> dict[str, Any]:  # noqa: ARG002
        page = get_page()
        return {"url": page.url, "title": await page.title()}

    async def _tool_screenshot_take(self, args: dict[str, Any]) -> dict[str, Any]:
        return await self._tool_dispatcher.tool_screenshot_take(args)

    async def _send_plan_ready_after_confirmation(self, payload: dict[str, Any]) -> dict[str, Any]:
        return await self._plan_confirmation.send_plan_ready_after_confirmation(payload)

    async def _tool_send_to_overlay(self, args: dict[str, Any]) -> dict[str, Any]:
        return await self._tool_dispatcher.tool_send_to_overlay(args)

    def _normalize_wait_until(self, value: Any) -> str:
        return self._tool_dispatcher.normalize_wait_until(value)

    def _append_tool_response(self, tool_call_id: str, result: dict[str, Any]) -> None:
        return self._tool_dispatcher.append_tool_response(tool_call_id, result)

    def _append_skipped_tool_response(self, tool_call_id: str, reason: str) -> None:
        return self._tool_dispatcher.append_skipped_tool_response(tool_call_id, reason)

    def _append_skipped_tool_responses(self, tool_calls: list[Any], start_index: int, reason: str) -> None:
        return self._tool_dispatcher.append_skipped_tool_responses(tool_calls, start_index, reason)

    async def _wait_for_plan_confirmation(self) -> dict[str, Any]:
        return await self._plan_confirmation.wait_for_plan_confirmation()

    async def _tool_ask_user(self, args: dict[str, Any]) -> dict[str, Any]:
        return await self._tool_dispatcher.tool_ask_user(args)

    def _build_locator_from_strategy(self, strategy: str, element_data: dict[str, Any]) -> str:
        return _locator_resolver.build_locator_from_strategy(strategy, element_data)
    def _build_locator_candidates(self, element_data: dict[str, Any]) -> list[dict[str, str]]:
        return self._locator_resolver.build_locator_candidates(element_data)

    def _resolve_locator(self, page: Any, locator_string: str) -> Any:
        return _locator_resolver.resolve_locator(page, locator_string)
    def _is_stable_locator_strategy(self, strategy: str) -> bool:
        return _locator_resolver.is_stable_locator_strategy(strategy)

    def _infer_role(self, element_data: dict[str, Any]) -> str:
        return _locator_resolver.infer_role(element_data)
    def _build_suggested_scope(self, element_info: dict[str, Any]) -> str:
        element_info = self._resolve_selected_element_info(element_info)
        tag = re.sub(r"[^a-zA-Z0-9:_-]", "", str(element_info.get("tag") or "").strip())
        if not tag:
            return "page"
        element_id = str(element_info.get("id") or "").strip()
        if element_id:
            return f"{tag}#{self._css_escape(element_id)}"
        class_name = str(element_info.get("class") or "").strip()
        classes = [
            re.sub(r"[^a-zA-Z0-9_-]", "", item)
            for item in class_name.split()
            if re.sub(r"[^a-zA-Z0-9_-]", "", item)
        ]
        if classes:
            return f"{tag}." + ".".join(classes[:3])
        return tag

    def _clean_markup(self, html: str) -> str:
        return _locator_resolver.clean_markup(html)

    def _summarize(self, value: Any, limit: int = 100) -> str:
        return _locator_resolver.summarize(value, limit)
    def _css_escape(self, value: str) -> str:
        return _locator_resolver.css_escape(value)

    def _text_escape(self, value: str) -> str:
        return _locator_resolver.text_escape(value)

    def _normalize_space(self, value: str) -> str:
        return _locator_resolver.normalize_space(value)

    def _normalize_assertion_text(self, value: str | None) -> str:
        return _locator_resolver.normalize_assertion_text(value)

    def _tool_string_escape(self, value: str) -> str:
        return _locator_resolver.tool_string_escape(value)

    def _tool_string_unescape(self, value: str) -> str:
        return _locator_resolver.tool_string_unescape(value)

    def _xpath_literal(self, value: str) -> str:
        return _locator_resolver.xpath_literal(value)
