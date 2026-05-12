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
from starlette.websockets import WebSocketDisconnect

from browser import get_page
from llm import LLMClient
from runtime.correction_context import (
    build_plan_diff_editor_context_payload,
    build_plan_diff_editor_schema_message,
    render_plan_diff_editor_context,
)
from runtime.context_manager import ContextManager
from runtime.event_contracts import (
    build_recovery_needed_payload,
    build_run_completed_payload,
    build_runtime_rejection_payload,
)
from runtime.llm_policy_gateway import LLMPolicyGateway
from runtime.llm_runtime_controller import LLMRuntimeController, PURPOSE_REGISTRY
from runtime.model_router import ModelRouter
from runtime.planning_loop_guard import PlanningLoopGuardState, advance_planning_loop_guard
from runtime.recovery_manager import classify_failure
from runtime.recovery_context import (
    build_recovery_diagnoser_context_payload,
    render_recovery_diagnoser_context,
)
from runtime.phase_tracker import PhaseTracker
from runtime.snapshot_archive import build_spec_snapshot
from runtime.agent_locator_handlers import tool_dom_extract, tool_locator_find, tool_locator_validate
from runtime.tool_registry import ToolRegistry, filter_tools_for_phase
from runtime.skill_manager import SkillManager
from runtime.skill_policy import get_skill_levels_for_names
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
        self.control_queue = control_queue
        self.skills_root = Path("/Users/apple/personal/agent v4/skills/playwright-automation")

        # Wire all domain modules first so delegates work before heavy dependencies init
        self._emitter = EventEmitter(ws, self)
        self._locator_resolver = LocatorResolver()
        self._skills_loader = SkillsLoader(self)
        self._step_manager = StepManager(self)
        self._codegen = Codegen(self)
        self._recorder = Recorder(self)
        self._replay = Replay(self)
        self._plan_state = PlanState(self)
        self._plan_builder = PlanBuilder(self)
        self._plan_correction = PlanCorrection(self)
        self._plan_confirmation = PlanConfirmation(self)
        self._tool_definitions = ToolDefinitions(self)
        self._tool_dispatcher = ToolDispatcher(self)
        self._llm_orchestrator = LLMOrchestrator(self)

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
        self._llm_runtime_controller = LLMRuntimeController(
            purpose_registry=PURPOSE_REGISTRY,
            schema_validator=self._validate_plan_diff_editor_output,
            context_manager=self.context_manager,
            skill_manager=self.skill_manager,
            telemetry_sink=self._plan_diff_editor_telemetry_sink,
            model_client=self.llm.client,
        )
        self._plan_diff_editor_controller = self._llm_runtime_controller
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
        self._planning_loop_guard_state: PlanningLoopGuardState = PlanningLoopGuardState()
        self._pending_planning_ambiguity: dict[str, Any] | None = None
        self._step_plan_convergence_narrowing: bool = False
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

    _MODULE_FACTORIES: dict[str, Any] = {}

    def __getattr__(self, name: str) -> Any:
        factories = {
            "_emitter": lambda: EventEmitter(getattr(self, "ws", None), self),
            "_locator_resolver": lambda: LocatorResolver(),
            "_skills_loader": lambda: SkillsLoader(self),
            "_step_manager": lambda: StepManager(self),
            "_codegen": lambda: Codegen(self),
            "_recorder": lambda: Recorder(self),
            "_replay": lambda: Replay(self),
            "_plan_state": lambda: PlanState(self),
            "_plan_builder": lambda: PlanBuilder(self),
            "_plan_correction": lambda: PlanCorrection(self),
            "_plan_confirmation": lambda: PlanConfirmation(self),
            "_tool_definitions": lambda: ToolDefinitions(self),
            "_tool_dispatcher": lambda: ToolDispatcher(self),
            "_llm_orchestrator": lambda: LLMOrchestrator(self),
        }
        if name in factories:
            obj = factories[name]()
            object.__setattr__(self, name, obj)
            return obj
        raise AttributeError(f"'AgentLoop' object has no attribute '{name}'")

    def _reset_lifecycle_state(self, steps: list[dict] | None = None) -> None:
        self.phase = "planning"
        self.plan_confirmed = False
        self.current_steps = list(steps or [])
        self.phase_tracker.current_phase = "idle"
        self.step_state_by_id = {}
        self.step_context_by_id = {}
        self.active_step_id = None
        self.active_failed_step_id = None
        self.pending_recovery = False
        self.completed_step_ids = set()
        self.skipped_step_ids = set()
        self.current_step_index = 0
        self.last_successful_action = None
        self.successful_action_by_step_id = {}
        self.successful_actions_by_step_id = {}
        self._loaded_skill_names = []
        self._loaded_skill_entries = []
        self._missing_skill_names = set()
        self._last_skill_load_phase = None
        self._recording_steps = []
        self._recording_step_index = 0
        self._recorded_step_ids = set()
        self._last_action_context = None
        self._awaiting_step_record = False
        self._recording_wait_guard_armed = False
        self.run_stop_requested = False
        self._run_completion_requested = False
        self._pending_failure_followup = False
        self._active_plan_state = None
        self._active_plan_correction_state = None
        self._plan_correction_pending = False
        self._planning_loop_guard_state = PlanningLoopGuardState()
        self._pending_planning_ambiguity = None
        self._step_plan_convergence_narrowing = False
        self._clear_confirmed_execution_contract_state()
        self.capability_gaps = []
        self.recorded_step_payloads = []
        self.code_update_payloads = []
        if steps is not None:
            self.replay_recorded_step_payloads_by_step_id = {}
            self.replay_action_history_by_step_id = {}
        self._run_session_id = self._new_run_session_id()
        self._run_completed_emitted = False
        self._clear_plan_review_context()
        telemetry_sink = getattr(self, "_plan_diff_editor_telemetry", None)
        if isinstance(telemetry_sink, list):
            telemetry_sink.clear()
        self._llm_call_counter = 0

    async def _send(self, msg_type: str, **kwargs: Any) -> None:
        if getattr(self, "_ws_disconnected", False):
            if msg_type.startswith("replay") and not getattr(self, "_ws_disconnect_logged", False):
                self._ws_disconnect_logged = True
                print("[WS] disconnected during replay_all; stopping result send")
            return

        payload = {"type": msg_type}
        payload.update(kwargs)
        if msg_type == "runtime_rejected":
            current_state = kwargs.get("current_state")
            current_state_data = current_state if isinstance(current_state, dict) else {}
            rejection_code = str(kwargs.get("rejection_code") or "").strip() or "unknown"
            phase = (
                str(current_state_data.get("phase") or self._current_phase() or self.phase or "").strip()
                or "unknown"
            )
            purpose = str(current_state_data.get("purpose") or "").strip() or "unknown"
            recoverable_value = kwargs.get("recoverable")
            recoverable = (
                str(recoverable_value).lower()
                if recoverable_value is not None
                else "unknown"
            )
            terminal = "true" if recoverable_value is False else "false"
            print(
                "[RUNTIME_REJECTED] "
                f"rejection_code={rejection_code} "
                f"phase={phase} "
                f"purpose={purpose} "
                f"recoverable={recoverable} "
                f"terminal={terminal}",
                flush=True,
            )
        try:
            await self.ws.send_json(payload)
        except WebSocketDisconnect:
            self._ws_disconnected = True
            if msg_type.startswith("replay"):
                self._ws_disconnect_logged = True
                print("[WS] disconnected during replay_all; stopping result send")
        except RuntimeError as exc:
            error_text = str(exc)
            if "close message has been sent" not in error_text and 'Cannot call "send"' not in error_text:
                raise
            self._ws_disconnected = True
            if msg_type.startswith("replay"):
                self._ws_disconnect_logged = True
                print("[WS] disconnected during replay_all; stopping result send")
        except Exception as exc:
            if exc.__class__.__name__ != "ClientDisconnected":
                raise
            self._ws_disconnected = True
            if msg_type.startswith("replay"):
                self._ws_disconnect_logged = True
                print("[WS] disconnected during replay_all; stopping result send")

    def _emit_backend_event_now(self, msg_type: str, **kwargs: Any) -> None:
        send = getattr(self, "_send", None)
        if not callable(send):
            return

        coroutine = send(msg_type, **kwargs)
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            try:
                asyncio.run(coroutine)
            except AttributeError as exc:
                if "send_json" not in str(exc):
                    raise
            return

        loop.create_task(coroutine)

    def _emit_recovery_needed_event(
        self,
        step: dict[str, Any] | str | None,
        error_summary: str,
    ) -> None:
        context = self._get_step_context(step) if not isinstance(step, dict) else step
        step_id = str((context or {}).get("step_id") or getattr(self, "active_failed_step_id", "") or "").strip()
        if not step_id:
            step_id = "unknown"

        operation_id = str(
            (context or {}).get("operation_id")
            or (context or {}).get("current_operation_id")
            or (self.last_successful_action or {}).get("operation_id")
            or ""
        ).strip() or None
        current_url = self._current_browser_url() or "unknown"
        tried = [
            {
                "step_id": step_id,
                "status": "failed",
                "error_summary": error_summary,
                "current_url": current_url,
            }
        ]
        recovery_payload = build_recovery_needed_payload(
            run_id=self._current_run_session_id(),
            step_id=step_id,
            error_summary=error_summary,
            current_url=current_url,
            tried=tried,
            options=["retry", "skip", "stop"],
            operation_id=operation_id,
        )
        self._emit_backend_event_now(
            recovery_payload["type"],
            **{
                key: value
                for key, value in recovery_payload.items()
                if key != "type"
            },
        )

    async def _emit_run_completed_event(
        self,
        source_payload: dict[str, Any],
        recorded_payload: dict[str, Any],
    ) -> None:
        if not self._run_completion_requested or getattr(self, "_run_completed_emitted", False):
            return

        run_id = str(
            source_payload.get("run_id")
            or recorded_payload.get("run_id")
            or self._current_run_session_id()
            or ""
        ).strip()
        if not run_id:
            return

        recorded_count = sum(
            1 for step in self._recording_steps if str(step.get("status") or "").strip() == "recorded"
        )
        skipped_count = sum(
            1 for step in self._recording_steps if str(step.get("status") or "").strip() == "skipped"
        )
        summary = str(
            getattr(self, "last_plan_summary", None)
            or getattr(getattr(self, "last_plan_ready_payload", None), "get", lambda *_: "")("summary")
            or "Run completed"
        ).strip() or "Run completed"
        run_completed_payload = build_run_completed_payload(
            run_id=run_id,
            summary=summary,
            recorded_count=recorded_count,
            skipped_count=skipped_count,
        )
        self._run_completed_emitted = True
        await self._send(
            run_completed_payload["type"],
            **{
                key: value
                for key, value in run_completed_payload.items()
                if key != "type"
            },
        )

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
        if value is None or isinstance(value, (bool, int, float)):
            return value

        if isinstance(value, str):
            text = self._normalize_space(value).strip()
            if len(text) > 160:
                text = f"{text[:157]}..."
            return text

        if isinstance(value, dict):
            sanitized: dict[str, Any] = {}
            for key, nested_value in value.items():
                key_text = self._normalize_space(str(key or "")).strip()
                if not key_text:
                    continue
                lowered_key = key_text.lower()
                if lowered_key in {
                    "dom",
                    "html",
                    "markup",
                    "prompt",
                    "tool_args",
                    "arguments",
                    "raw_dom",
                    "raw_prompt",
                    "raw_tool_args",
                }:
                    continue
                sanitized_value = self._sanitize_capability_gap_detail(nested_value)
                if sanitized_value in (None, "", [], {}):
                    continue
                sanitized[key_text] = sanitized_value
            return sanitized

        if isinstance(value, (list, tuple, set)):
            sanitized_items: list[Any] = []
            for item in value:
                sanitized_item = self._sanitize_capability_gap_detail(item)
                if sanitized_item in (None, "", [], {}):
                    continue
                sanitized_items.append(sanitized_item)
                if len(sanitized_items) >= 5:
                    break
            return sanitized_items

        text = self._normalize_space(str(value)).strip()
        if len(text) > 160:
            text = f"{text[:157]}..."
        return text

    def _record_capability_gap(
        self,
        category: str,
        source: str,
        severity: str,
        message: str,
        **details: Any,
    ) -> dict[str, Any]:
        capability_gaps = getattr(self, "capability_gaps", None)
        if not isinstance(capability_gaps, list):
            capability_gaps = []
            self.capability_gaps = capability_gaps

        category_text = self._normalize_space(str(category or "")).strip() or "unknown"
        source_text = self._normalize_space(str(source or "")).strip() or "unknown"
        severity_text = self._normalize_space(str(severity or "")).strip().lower()
        if severity_text not in {"warn", "error"}:
            severity_text = "warn"
        message_text = self._normalize_space(str(message or "")).strip() or "unspecified capability gap"
        phase_text = self._current_phase()
        step_id = str(getattr(self, "active_step_id", "") or "").strip() or None

        safe_details: dict[str, Any] = {}
        for key, value in details.items():
            key_text = self._normalize_space(str(key or "")).strip()
            if not key_text:
                continue
            safe_value = self._sanitize_capability_gap_detail(value)
            if safe_value in (None, "", [], {}):
                continue
            safe_details[key_text] = safe_value

        record = {
            "ordinal": len(capability_gaps) + 1,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "category": category_text,
            "source": source_text,
            "severity": severity_text,
            "message": message_text,
            "phase": phase_text,
            "step_id": step_id,
            "details": safe_details,
        }
        capability_gaps.append(record)

        log_line = (
            "[CAPABILITY_GAP] "
            f"ordinal={record['ordinal']} "
            f"category={category_text} "
            f"source={source_text} "
            f"severity={severity_text} "
            f"message={json.dumps(message_text, ensure_ascii=True)}"
        )
        if phase_text:
            log_line += f" phase={phase_text}"
        if step_id:
            log_line += f" step_id={step_id}"
        if safe_details:
            log_line += f" details={json.dumps(safe_details, ensure_ascii=True, separators=(',', ':'))}"
        print(log_line)

        return record

    def _append_recorded_step_payload(self, payload: dict[str, Any]) -> None:
        recorded_step_payloads = getattr(self, "recorded_step_payloads", None)
        if not isinstance(recorded_step_payloads, list):
            recorded_step_payloads = []
            self.recorded_step_payloads = recorded_step_payloads
        recorded_step_payloads.append(deepcopy(payload))

    def _append_code_update_payload(self, payload: dict[str, Any]) -> None:
        code_update_payloads = getattr(self, "code_update_payloads", None)
        if not isinstance(code_update_payloads, list):
            code_update_payloads = []
            self.code_update_payloads = code_update_payloads
        code_update_payloads.append(deepcopy(payload))

    def _get_replay_recorded_step_payload(self, step_id: str) -> dict[str, Any] | None:
        replay_step_id = str(step_id or "").strip()
        if not replay_step_id:
            return None

        recorded_step_payloads = getattr(self, "recorded_step_payloads", None)
        if isinstance(recorded_step_payloads, list):
            for payload in recorded_step_payloads:
                if not isinstance(payload, dict):
                    continue
                candidate_step_id = str(
                    payload.get("step_id")
                    or payload.get("stepId")
                    or payload.get("id")
                    or ""
                ).strip()
                if candidate_step_id == replay_step_id:
                    return deepcopy(payload)

        replay_recorded_step_payloads_by_step_id = getattr(
            self,
            "replay_recorded_step_payloads_by_step_id",
            None,
        )
        if isinstance(replay_recorded_step_payloads_by_step_id, dict):
            archived_payload = replay_recorded_step_payloads_by_step_id.get(replay_step_id)
            if isinstance(archived_payload, dict):
                return deepcopy(archived_payload)

        return None

    def _get_replay_action_history(self, step_id: str) -> list[dict[str, Any]]:
        replay_step_id = str(step_id or "").strip()
        if not replay_step_id:
            return []

        history_by_step_id = getattr(self, "successful_actions_by_step_id", None)
        if isinstance(history_by_step_id, dict):
            action_history = history_by_step_id.get(replay_step_id)
            if isinstance(action_history, list):
                return deepcopy(action_history)

        replay_action_history_by_step_id = getattr(self, "replay_action_history_by_step_id", None)
        if isinstance(replay_action_history_by_step_id, dict):
            archived_history = replay_action_history_by_step_id.get(replay_step_id)
            if isinstance(archived_history, list):
                return deepcopy(archived_history)

        return []

    def _safe_replay_error_message(self, message: Any) -> str:
        text = self._normalize_space(str(message or "")).strip()
        if not text:
            return "Replay failed"
        if len(text) > 200:
            return f"{text[:197]}..."
        return text

    def _get_replay_recorded_start_state(self, recorded_step_payload: dict[str, Any]) -> tuple[str, str]:
        observed_outcome = recorded_step_payload.get("observed_outcome")
        if not isinstance(observed_outcome, dict):
            return "", ""

        before_url = str(observed_outcome.get("before_url") or "").strip()
        before_title = str(observed_outcome.get("before_title") or "").strip()
        return before_url, before_title

    def _get_replay_precondition_target_locator(
        self,
        recorded_step_payload: dict[str, Any],
        action_history: list[dict[str, Any]],
    ) -> str:
        locator = str(recorded_step_payload.get("locator") or "").strip()
        if locator:
            return locator

        recorded_children = recorded_step_payload.get("children")
        if isinstance(recorded_children, list):
            for child in recorded_children:
                if not isinstance(child, dict):
                    continue
                locator = str(child.get("locator") or "").strip()
                if locator:
                    return locator

        for action_record in action_history:
            if not isinstance(action_record, dict):
                continue
            replay_args: dict[str, Any] = {}
            tool_args = action_record.get("tool_args")
            if isinstance(tool_args, dict):
                replay_args.update(tool_args)
            action_context = action_record.get("action_context")
            if isinstance(action_context, dict):
                for key, value in action_context.items():
                    if key not in replay_args:
                        replay_args[key] = value
            locator = str(replay_args.get("locator") or action_record.get("locator") or "").strip()
            if locator:
                return locator

        return ""

    async def _validate_replay_target_locator(self, locator: str) -> dict[str, Any]:
        locator_text = str(locator or "").strip()
        if not locator_text:
            return {"valid": False, "count": 0}

        try:
            page = get_page()
        except Exception:  # noqa: BLE001
            return {"valid": False, "count": 0}

        try:
            locator_count = await self._resolve_locator(page, locator_text).count()
        except Exception:  # noqa: BLE001
            locator_count = 0

        return {"valid": locator_count > 0, "count": locator_count}

    def _log_replay_precondition_failure(
        self,
        step_id: str,
        reason: str,
        expected_url: str,
        actual_url: str,
        locator: str = "",
    ) -> None:
        if reason == "url_mismatch":
            print(
                "[REPLAY_PRECONDITION] failed "
                f"step_id={step_id} "
                "reason=url_mismatch "
                f"expected_url={expected_url} "
                f"actual_url={actual_url}"
            )
            return

        if reason == "locator_missing":
            print(
                "[REPLAY_PRECONDITION] failed "
                f"step_id={step_id} "
                "reason=locator_missing "
                f"locator={locator}"
            )
            return

        print(
            "[REPLAY_PRECONDITION] failed "
            f"step_id={step_id} "
            "reason=unknown "
            f"expected_url={expected_url} "
            f"actual_url={actual_url}"
        )

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
        safe_message = self._safe_replay_error_message(message)
        self._log_replay_precondition_failure(step_id, log_reason, before_url, current_url, locator)
        return {
            "type": "replay_one_result",
            "ok": False,
            "step_id": step_id,
            "reason": "replay_precondition_failed",
            "failure_type": failure_type,
            "expected": {
                "before_url": before_url,
                "before_title": before_title,
            },
            "actual": {
                "url": current_url,
                "title": current_title,
            },
            "message": safe_message,
            "error": safe_message,
        }

    async def _check_replay_precondition(
        self,
        step_id: str,
        recorded_step_payload: dict[str, Any],
        action_history: list[dict[str, Any]],
    ) -> dict[str, Any] | None:
        before_url, before_title = self._get_replay_recorded_start_state(recorded_step_payload)
        if not before_url:
            print(f"[REPLAY_PRECONDITION] missing before_url step_id={step_id}")
            return None

        current_state = await self._capture_browser_state()
        current_url = str((current_state or {}).get("url") or "").strip()
        current_title = str((current_state or {}).get("title") or "").strip()
        if current_state is None:
            return self._build_replay_precondition_failure_result(
                step_id,
                before_url,
                before_title,
                current_url,
                current_title,
                "Replay blocked",
                failure_type="unknown",
                log_reason="unknown",
            )

        if current_url != before_url:
            return self._build_replay_precondition_failure_result(
                step_id,
                before_url,
                before_title,
                current_url,
                current_title,
                "Wrong start page",
                failure_type="wrong_start_page",
                log_reason="url_mismatch",
            )

        target_locator = self._get_replay_precondition_target_locator(recorded_step_payload, action_history)
        if not target_locator:
            return self._build_replay_precondition_failure_result(
                step_id,
                before_url,
                before_title,
                current_url,
                current_title,
                "Element not found",
                failure_type="locator_missing",
                log_reason="locator_missing",
                locator=target_locator,
            )

        locator_validation = await self._validate_replay_target_locator(target_locator)
        if locator_validation.get("valid") is not True:
            return self._build_replay_precondition_failure_result(
                step_id,
                before_url,
                before_title,
                current_url,
                current_title,
                "Element not found",
                failure_type="locator_missing",
                log_reason="locator_missing",
                locator=target_locator,
            )

        return None

    def _get_replay_archive_step_ids(self) -> list[str]:
        step_ids: list[str] = []
        seen_step_ids: set[str] = set()

        recorded_step_payloads = getattr(self, "recorded_step_payloads", None)
        if isinstance(recorded_step_payloads, list):
            for payload in recorded_step_payloads:
                if not isinstance(payload, dict):
                    continue
                step_id = str(
                    payload.get("step_id")
                    or payload.get("stepId")
                    or payload.get("id")
                    or ""
                ).strip()
                if not step_id or step_id in seen_step_ids:
                    continue
                seen_step_ids.add(step_id)
                step_ids.append(step_id)

        if step_ids:
            return step_ids

        replay_recorded_step_payloads_by_step_id = getattr(
            self,
            "replay_recorded_step_payloads_by_step_id",
            None,
        )
        if isinstance(replay_recorded_step_payloads_by_step_id, dict):
            for step_id in replay_recorded_step_payloads_by_step_id.keys():
                step_id_text = str(step_id or "").strip()
                if not step_id_text or step_id_text in seen_step_ids:
                    continue
                seen_step_ids.add(step_id_text)
                step_ids.append(step_id_text)

        return step_ids

    async def replay_one(self, step_id: str) -> dict[str, Any]:
        replay_step_id = str(step_id or "").strip()
        if not replay_step_id:
            return {
                "type": "replay_one_result",
                "ok": False,
                "step_id": "",
                "error": "Replay requires step_id",
            }

        recorded_step_payload = self._get_replay_recorded_step_payload(replay_step_id)
        if not isinstance(recorded_step_payload, dict):
            return {
                "type": "replay_one_result",
                "ok": False,
                "step_id": replay_step_id,
                "error": "Recorded step not found",
            }

        action_history = self._get_replay_action_history(replay_step_id)
        if not action_history:
            return {
                "type": "replay_one_result",
                "ok": False,
                "step_id": replay_step_id,
                "error": "Recorded action history unavailable for replay",
            }

        precondition_failure = await self._check_replay_precondition(
            replay_step_id,
            recorded_step_payload,
            action_history,
        )
        if precondition_failure is not None:
            return precondition_failure

        recorded_children = recorded_step_payload.get("children")
        if not isinstance(recorded_children, list):
            recorded_children = []

        supported_actions = {"assert", "click", "fill"}
        supported_assertions = {"visible", "hidden", "enabled", "disabled", "checked", "has_text", "has_value"}
        operation_count = 0

        for index, action_record in enumerate(action_history, start=1):
            child_operation_id = f"op_{index}"
            if index - 1 < len(recorded_children):
                child = recorded_children[index - 1]
                if isinstance(child, dict):
                    child_operation_id = str(child.get("operation_id") or child_operation_id).strip() or child_operation_id

            if not isinstance(action_record, dict):
                return {
                    "type": "replay_one_result",
                    "ok": False,
                    "step_id": replay_step_id,
                    "failed_operation_id": child_operation_id,
                    "error": self._safe_replay_error_message("Recorded action history entry is invalid"),
                }

            action_name = str(
                action_record.get("action")
                or self._action_name_for_tool(str(action_record.get("tool") or ""))
                or ""
            ).strip().lower()
            if action_name not in supported_actions:
                return {
                    "type": "replay_one_result",
                    "ok": False,
                    "step_id": replay_step_id,
                    "failed_operation_id": child_operation_id,
                    "error": self._safe_replay_error_message(f"Unsupported replay operation: {action_name or 'unknown'}"),
                }

            replay_args: dict[str, Any] = {}
            tool_args = action_record.get("tool_args")
            if isinstance(tool_args, dict):
                replay_args.update(tool_args)
            action_context = action_record.get("action_context")
            if isinstance(action_context, dict):
                for key, value in action_context.items():
                    if key not in replay_args:
                        replay_args[key] = value

            locator = str(replay_args.get("locator") or "").strip()
            if not locator:
                return {
                    "type": "replay_one_result",
                    "ok": False,
                    "step_id": replay_step_id,
                    "failed_operation_id": child_operation_id,
                    "error": self._safe_replay_error_message(f"Replay requires stored locator for {action_name}"),
                }

            if action_name == "fill" and ("value" not in replay_args or replay_args.get("value") is None):
                return {
                    "type": "replay_one_result",
                    "ok": False,
                    "step_id": replay_step_id,
                    "failed_operation_id": child_operation_id,
                    "error": self._safe_replay_error_message("Replay requires stored value for fill"),
                }

            if action_name == "assert":
                assertion = str(replay_args.get("assertion") or "").strip()
                if assertion not in supported_assertions:
                    return {
                        "type": "replay_one_result",
                        "ok": False,
                        "step_id": replay_step_id,
                        "failed_operation_id": child_operation_id,
                        "error": self._safe_replay_error_message(f"Unsupported replay assertion: {assertion or 'unknown'}"),
                    }
                if assertion in {"has_text", "has_value"} and (
                    "expected_value" not in replay_args or replay_args.get("expected_value") is None
                ):
                    return {
                        "type": "replay_one_result",
                        "ok": False,
                        "step_id": replay_step_id,
                        "failed_operation_id": child_operation_id,
                        "error": self._safe_replay_error_message(
                            f"Replay requires stored expected_value for {assertion}"
                        ),
                    }

            if action_name == "click":
                result = await self._tool_action_click(replay_args)
            elif action_name == "fill":
                result = await self._tool_action_fill(replay_args)
            else:
                result = await self._tool_action_assert(replay_args)

            if result.get("success") is not True or result.get("skipped"):
                return {
                    "type": "replay_one_result",
                    "ok": False,
                    "step_id": replay_step_id,
                    "failed_operation_id": child_operation_id,
                    "error": self._safe_replay_error_message(
                        result.get("error") or f"Replay operation failed: {action_name or 'unknown'}"
                    ),
                }

            operation_count = index

        return {
            "type": "replay_one_result",
            "ok": True,
            "step_id": replay_step_id,
            "status": "success",
            "operation_count": operation_count,
        }

    async def replay_all(self, stop_on_error: bool = True) -> dict[str, Any]:
        selected_step_ids = self._get_replay_archive_step_ids()
        step_count = len(selected_step_ids)
        self._replay_all_result_sent = False
        print(f"[REPLAY_ALL] started steps={step_count} stop_on_error={json.dumps(bool(stop_on_error))}")
        await self._send("replay_started", scope="all", step_count=step_count)

        replayed_count = 0
        passed_count = 0
        failed_count = 0
        first_failed_step_id = ""
        first_failed_operation_id = ""
        first_error = ""
        stop_after_failure = bool(stop_on_error)

        if selected_step_ids:
            first_step_id = selected_step_ids[0]
            first_step_payload = self._get_replay_recorded_step_payload(first_step_id)
            if isinstance(first_step_payload, dict):
                start_before_url, _ = self._get_replay_recorded_start_state(first_step_payload)
                if start_before_url:
                    print(f"[REPLAY_ALL] restoring_start_url url={start_before_url}")
                    try:
                        page = get_page()
                        await page.goto(start_before_url, wait_until="domcontentloaded")
                    except Exception as exc:  # noqa: BLE001
                        final_result = {
                            "type": "replay_all_result",
                            "ok": False,
                            "stop_on_error": stop_after_failure,
                            "step_ids": list(selected_step_ids),
                            "replayed_count": 0,
                            "passed_count": 0,
                            "failed_count": 1,
                            "failed_step_id": first_step_id,
                            "error": self._safe_replay_error_message(
                                f"Replay blocked because the replay start URL could not be restored: {type(exc).__name__}"
                            ),
                        }
                        print(
                            "[REPLAY_ALL] completed "
                            "total=0 passed=0 failed=1"
                        )
                        await self._send("replay_all_result", **final_result)
                        self._replay_all_result_sent = True
                        return final_result

        for step_id in selected_step_ids:
            try:
                step_result = await self.replay_one(step_id)
            except Exception as exc:  # noqa: BLE001
                step_result = {
                    "type": "replay_one_result",
                    "ok": False,
                    "step_id": step_id,
                    "error": self._safe_replay_error_message(f"Replay failed: {type(exc).__name__}"),
                }

            if not isinstance(step_result, dict):
                step_result = {
                    "type": "replay_one_result",
                    "ok": False,
                    "step_id": step_id,
                    "error": self._safe_replay_error_message("Replay failed"),
                }

            step_ok = step_result.get("ok") is True
            step_operation_count = 0
            try:
                step_operation_count = int(step_result.get("operation_count") or 0)
            except (TypeError, ValueError):
                step_operation_count = 0

            replay_event: dict[str, Any] = {
                "type": "replay_result",
                "step_id": step_id,
                "ok": step_ok,
                "status": "success" if step_ok else "failed",
                "operation_count": step_operation_count,
            }

            if step_ok:
                passed_count += 1
            else:
                failed_count += 1
                failed_step_id = str(step_result.get("step_id") or step_id or "").strip() or step_id
                failed_operation_id = str(step_result.get("failed_operation_id") or "").strip()
                error_text = self._safe_replay_error_message(step_result.get("error") or "Replay failed")
                if failed_step_id and not first_failed_step_id:
                    first_failed_step_id = failed_step_id
                if failed_operation_id and not first_failed_operation_id:
                    first_failed_operation_id = failed_operation_id
                if error_text and not first_error:
                    first_error = error_text
                if failed_operation_id:
                    replay_event["failed_operation_id"] = failed_operation_id
                for key in ("reason", "failure_type", "expected", "actual", "message"):
                    if key in step_result:
                        replay_event[key] = step_result[key]
                replay_event["error"] = error_text

            replayed_count += 1
            print(
                "[REPLAY_ALL] step_result "
                f"step_id={step_id} "
                f"ok={json.dumps(step_ok)} "
                f"operations={step_operation_count}"
            )
            await self._send("replay_result", **replay_event)

            if not step_ok and stop_after_failure:
                break

        final_result: dict[str, Any] = {
            "type": "replay_all_result",
            "ok": failed_count == 0,
            "stop_on_error": stop_after_failure,
            "step_ids": list(selected_step_ids),
            "replayed_count": replayed_count,
            "passed_count": passed_count,
            "failed_count": failed_count,
        }
        if first_failed_step_id:
            final_result["failed_step_id"] = first_failed_step_id
        if first_failed_operation_id:
            final_result["failed_operation_id"] = first_failed_operation_id
        if failed_count > 0:
            final_result["error"] = first_error or "Replay completed with failures"
        print(
            "[REPLAY_ALL] completed "
            f"total={replayed_count} "
            f"passed={passed_count} "
            f"failed={failed_count}"
        )
        await self._send("replay_all_result", **final_result)
        self._replay_all_result_sent = True
        return final_result

    def _build_spec_snapshot(self) -> dict[str, Any]:
        plan_ready_payload = getattr(self, "last_plan_ready_payload", None)
        plan_ready_summary = str(getattr(self, "last_plan_summary", "") or "").strip()
        if not plan_ready_summary and isinstance(plan_ready_payload, dict):
            plan_ready_summary = str(plan_ready_payload.get("summary") or "").strip()
        plan_ready_steps: list[dict[str, Any]] = []
        if isinstance(plan_ready_payload, dict):
            steps = plan_ready_payload.get("steps")
            if isinstance(steps, list):
                plan_ready_steps = deepcopy(steps)

        recorded_step_payloads = getattr(self, "recorded_step_payloads", None)
        if not isinstance(recorded_step_payloads, list):
            recorded_step_payloads = []
        code_update_payloads = getattr(self, "code_update_payloads", None)
        if not isinstance(code_update_payloads, list):
            code_update_payloads = []
        capability_gaps = getattr(self, "capability_gaps", None)
        if not isinstance(capability_gaps, list):
            capability_gaps = []

        session_id = self._current_run_session_id()
        original_user_intent = str(getattr(self, "last_plan_original_user_intent", "") or "").strip() or None
        phase = self._current_phase()
        completed_step_ids = getattr(self, "completed_step_ids", set())
        completed_step_count = len(completed_step_ids) if isinstance(completed_step_ids, (set, list, tuple)) else 0
        recorded_step_count = len(recorded_step_payloads)
        created_at = datetime.now(timezone.utc).isoformat()

        return build_spec_snapshot(
            schema_version="autoworkbench.spec.v1",
            session_id=session_id,
            created_at=created_at,
            original_user_intent=original_user_intent,
            plan_ready={
                "summary": plan_ready_summary or None,
                "steps": plan_ready_steps,
            },
            recorded_steps=recorded_step_payloads,
            code_update_payloads=code_update_payloads,
            capability_gaps=capability_gaps,
            phase=phase,
            completed_step_count=completed_step_count,
            recorded_step_count=recorded_step_count,
        )

    def _build_session_state_payload(self) -> dict[str, Any]:
        snapshot: dict[str, Any] = {}
        snapshot_builder = getattr(self, "_build_spec_snapshot", None)
        if callable(snapshot_builder):
            try:
                snapshot_candidate = snapshot_builder()
            except Exception:
                snapshot_candidate = {}
            if isinstance(snapshot_candidate, dict):
                snapshot = snapshot_candidate

        metadata = snapshot.get("metadata") if isinstance(snapshot.get("metadata"), dict) else {}
        plan_ready = snapshot.get("plan_ready") if isinstance(snapshot.get("plan_ready"), dict) else {}
        steps = plan_ready.get("steps") if isinstance(plan_ready.get("steps"), list) else []
        recorded_steps = snapshot.get("recorded_steps") if isinstance(snapshot.get("recorded_steps"), list) else []

        run_id = str(snapshot.get("session_id") or getattr(self, "_run_session_id", None) or "").strip()
        if not run_id:
            run_id_getter = getattr(self, "_current_run_session_id", None)
            if callable(run_id_getter):
                run_id = str(run_id_getter() or "").strip()

        phase = str(metadata.get("phase") or getattr(self, "phase", "") or "").strip() or "planning"
        return {
            "run_id": run_id,
            "phase": phase,
            "steps": deepcopy(steps),
            "recorded_steps": deepcopy(recorded_steps),
        }

    def _skill_entries_from_loaded_skills(
        self,
        loaded_skill_names: list[str],
        loaded_skills: Any,
    ) -> list[tuple[str, str]]:
        if isinstance(loaded_skills, dict):
            return [
                (skill_name, str(loaded_skills.get(skill_name) or ""))
                for skill_name in loaded_skill_names
                if skill_name in loaded_skills
            ]

        if isinstance(loaded_skills, (list, tuple)):
            skill_entries: list[tuple[str, str]] = []
            for index, item in enumerate(loaded_skills):
                if isinstance(item, dict):
                    skill_name = item.get("name") or item.get("skill_name") or item.get("id")
                    if skill_name is None and index < len(loaded_skill_names):
                        skill_name = loaded_skill_names[index]
                    skill_content = item.get("content")
                    if skill_content is None:
                        skill_content = item.get("text")
                    if skill_content is None:
                        skill_content = item.get("body")
                    skill_entries.append(
                        (
                            str(skill_name or f"skill_{index + 1}").strip() or f"skill_{index + 1}",
                            str(skill_content or ""),
                        )
                    )
                    continue

                if isinstance(item, (list, tuple)) and len(item) >= 2:
                    skill_name = str(item[0] or "").strip() or f"skill_{index + 1}"
                    skill_content = str(item[1] or "")
                    skill_entries.append((skill_name, skill_content))
                    continue

                if index < len(loaded_skill_names):
                    skill_entries.append((loaded_skill_names[index], str(item or "")))
                    continue

                skill_entries.append((f"skill_{index + 1}", str(item or "")))
            return skill_entries

        if isinstance(loaded_skills, str):
            skill_name = loaded_skill_names[0] if loaded_skill_names else "combined_skill_text"
            return [(skill_name, loaded_skills)]

        fallback_name = loaded_skill_names[0] if loaded_skill_names else "combined_skill_text"
        return [(fallback_name, str(loaded_skills or ""))]

    def _compose_skill_prompt_from_entries(self) -> str:
        skill_entries = list(getattr(self, "_loaded_skill_entries", []))
        return "\n\n".join(content for _, content in skill_entries)

    def _sync_skill_prompt_from_entries(self) -> str:
        prompt = self._compose_skill_prompt_from_entries()
        llm = getattr(self, "llm", None)
        if llm is None:
            return prompt

        llm.system_prompt = prompt
        messages = getattr(llm, "messages", None)
        if isinstance(messages, list) and messages:
            first_message = messages[0]
            if isinstance(first_message, dict) and first_message.get("role") == "system":
                first_message["content"] = prompt
        return prompt

    def _log_skill_load(self, added_skill_names: list[str], phase: str) -> None:
        added_text = ",".join(added_skill_names) if added_skill_names else "none"
        total_skill_count = len(getattr(self, "_loaded_skill_names", []))
        print(
            "[SKILL_LOAD] "
            f"added={added_text} "
            f"total={total_skill_count} "
            f"phase={phase}"
        )

    def _log_skill_diagnostics(self) -> None:
        skill_manager = getattr(self, "skill_manager", None)
        analyze = getattr(skill_manager, "analyze", None)
        if not callable(analyze):
            return

        loaded_skill_entries = list(getattr(self, "_loaded_skill_entries", []))
        loaded_skill_names = list(getattr(self, "_loaded_skill_names", []))
        skill_diagnostics = analyze(
            loaded_skill_entries,
            loaded_skill_names=loaded_skill_names,
        )
        print(
            "[SKILL_DIAGNOSTICS] "
            f"skills={skill_diagnostics.skill_count} "
            f"names={','.join(skill_diagnostics.loaded_skill_names) or 'none'} "
            f"estimated_tokens={skill_diagnostics.estimated_total_skill_tokens} "
            f"largest={skill_diagnostics.largest_skill_name} "
            f"largest_tokens={skill_diagnostics.largest_skill_tokens} "
            f"policy={skill_diagnostics.suggested_future_policy}"
        )

    def _requires_complex_codegen(self) -> bool:
        for step in list(getattr(self, "current_steps", [])):
            if not isinstance(step, dict):
                continue
            metadata = step.get("metadata")
            if not isinstance(metadata, dict):
                continue
            if metadata.get("complex_codegen") or metadata.get("requires_codegen") or metadata.get(
                "codegen_required"
            ):
                return True
            codegen_mode = str(metadata.get("codegen_mode") or "").strip().lower()
            if codegen_mode == "complex":
                return True
        return False

    def _load_phase_skill_expansion(self, phase: str) -> list[str]:
        normalized_phase = str(phase or "").strip().lower() or "planning"
        if normalized_phase == "recovering":
            normalized_phase = "recovery"

        phase_skill_names: list[str] = []
        pending_recovery = bool(getattr(self, "pending_recovery", False))
        active_failed_step_id = str(getattr(self, "active_failed_step_id", "") or "").strip()
        failed_step_context = None
        if active_failed_step_id:
            step_state_by_id = getattr(self, "step_state_by_id", {})
            if isinstance(step_state_by_id, dict):
                failed_step_context = step_state_by_id.get(active_failed_step_id)
        if failed_step_context is None:
            recording_steps = list(getattr(self, "_recording_steps", []))
            for recording_step in recording_steps:
                if isinstance(recording_step, dict) and str(recording_step.get("status") or "") in {
                    "failed",
                    "recovery_pending",
                }:
                    failed_step_context = recording_step
                    break
        if normalized_phase == "recovery" or pending_recovery or failed_step_context is not None:
            phase_skill_names.append("debugging")
        if self._requires_complex_codegen():
            phase_skill_names.append("codegen")

        loaded_skill_names = list(getattr(self, "_loaded_skill_names", []))
        loaded_skill_entries = list(getattr(self, "_loaded_skill_entries", []))
        loaded_skill_name_set = set(loaded_skill_names)
        added_skill_names: list[str] = []
        for skill_name in phase_skill_names:
            if skill_name in loaded_skill_name_set:
                continue
            # Recovery/debug phase expansions use full skills — they need complete details
            skill_text = self._read_skill(skill_name, compact_mode=False)
            if skill_text is None:
                continue
            loaded_skill_names.append(skill_name)
            loaded_skill_entries.append((skill_name, skill_text))
            loaded_skill_name_set.add(skill_name)
            added_skill_names.append(skill_name)

        previous_phase = getattr(self, "_last_skill_load_phase", None)
        if added_skill_names or normalized_phase != previous_phase:
            self._loaded_skill_names = loaded_skill_names
            self._loaded_skill_entries = loaded_skill_entries
            self._last_skill_load_phase = normalized_phase
            if added_skill_names:
                self._sync_skill_prompt_from_entries()
            self._log_skill_load(added_skill_names, normalized_phase)
            if added_skill_names:
                self._log_skill_diagnostics()

        return added_skill_names

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
                if (
                    effective_purpose == "step_plan_normalizer"
                    and (
                        getattr(self, "_step_plan_convergence_narrowing", False)
                        or isinstance(getattr(self, "_pending_planning_ambiguity", None), dict)
                    )
                ):
                    purpose_allowed_tool_names = {"ask_user", "send_to_overlay"}
                    print("[AGENT] step_plan_normalizer: tool surface narrowed to ask_user+send_to_overlay after convergence pressure")
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
                recovery_context = ""
                if effective_purpose == "recovery_diagnoser":
                    recovery_context = await self._build_recovery_diagnoser_context_message()
                    if recovery_context:
                        context_bundle.messages.append({"role": "user", "content": recovery_context})
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
                # S5-001: enrich telemetry with PURPOSE_REGISTRY attribution fields.
                # model_class, skills_loaded, and context_bucket are looked up from the
                # registry for the effective purpose so token reports can attribute costs.
                _s5_model_class: str | None = None
                _s5_context_bucket: str | None = None
                _s5_skills_loaded: list[str] | None = None
                _s5_skill_levels: list[str] | None = None
                try:
                    _purpose_policy = PURPOSE_REGISTRY.get_purpose_policy(effective_purpose)
                    _s5_model_class = str(_purpose_policy.get("model_class") or "")  or None
                    _s5_context_bucket = str(current_phase or "").strip() or None
                    _s5_skills_loaded = list(getattr(self, "_loaded_skill_names", [])) or None
                    if _s5_skills_loaded is not None:
                        _s5_skill_levels = get_skill_levels_for_names(_s5_skills_loaded)
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
                    model_class=_s5_model_class,
                    context_bucket=_s5_context_bucket,
                    skills_loaded=_s5_skills_loaded,
                    skill_levels=_s5_skill_levels,
                )
                try:
                    controller_result: dict[str, Any] | None = None
                    if effective_purpose == "step_plan_normalizer":
                        controller_result = await self._call_step_plan_normalizer_controller(
                            messages=context_bundle.messages,
                            phase=current_phase,
                            context_mode=execution_context,
                            tools=filtered_tools,
                            tool_choice="auto",
                        )
                    elif effective_purpose == "recovery_diagnoser":
                        controller_result = await self._call_recovery_diagnoser_controller(
                            messages=context_bundle.messages,
                            phase=current_phase,
                            context_mode="compact",
                            tools=filtered_tools,
                            tool_choice="auto",
                        )
                    if isinstance(controller_result, dict) and controller_result.get("used_controller"):
                        self._sync_controller_prompt_pack_telemetry(telemetry, controller_result)
                        response = controller_result.get("raw_response")
                        if response is None:
                            failure_detail_parts: list[str] = []
                            for key in ("error_code", "message", "validation_status"):
                                value = controller_result.get(key)
                                if value not in (None, "", [], {}, ()):
                                    text = str(value).strip()
                                    if text and text not in failure_detail_parts:
                                        failure_detail_parts.append(text)
                            errors = controller_result.get("errors")
                            if isinstance(errors, (list, tuple, set)):
                                for item in errors:
                                    text = str(item).strip()
                                    if text and text not in failure_detail_parts:
                                        failure_detail_parts.append(text)
                            elif errors not in (None, "", [], {}, ()):
                                text = str(errors).strip()
                                if text and text not in failure_detail_parts:
                                    failure_detail_parts.append(text)
                            failure_detail = " | ".join(failure_detail_parts)
                            if failure_detail:
                                raise RuntimeError(
                                    "step_plan_normalizer controller did not return raw_response: "
                                    f"{failure_detail}"
                                )
                            raise RuntimeError(
                                "step_plan_normalizer controller did not return raw_response"
                            )
                    else:
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
                    self._emit_llm_call_record(
                        call_id=call_id,
                        purpose=effective_purpose,
                        model=model,
                        model_class=_s5_model_class,
                        filtered_tools=filtered_tools,
                        telemetry=telemetry,
                        response=None,
                        error={
                            "type": type(exc).__name__,
                            "message": str(exc),
                        },
                    )
                    raise
                record_model_call_end(
                    telemetry,
                    success=True,
                    response_usage=getattr(response, "usage", None),
                )
                message = response.choices[0].message
                self._emit_llm_call_record(
                    call_id=call_id,
                    purpose=effective_purpose,
                    model=model,
                    model_class=_s5_model_class,
                    filtered_tools=filtered_tools,
                    telemetry=telemetry,
                    response=response,
                )
                if effective_purpose == "step_plan_normalizer":
                    guard_state = getattr(self, "_planning_loop_guard_state", None)
                    guard_result = advance_planning_loop_guard(
                        guard_state if isinstance(guard_state, PlanningLoopGuardState) else None,
                        message,
                        purpose=effective_purpose,
                    )
                    self._planning_loop_guard_state = guard_result.state
                    ambiguity_context = getattr(self, "_pending_planning_ambiguity", None)
                    if (
                        isinstance(ambiguity_context, dict)
                        and self._should_force_ambiguity_clarification(message)
                    ):
                        self.llm.messages.append(self._assistant_message_entry(message))
                        answer = await self._tool_ask_user({
                            "question": str(ambiguity_context.get("question") or "").strip(),
                            "options": list(ambiguity_context.get("options") or []),
                        })
                        answer_text = str(answer.get("answer") or "").strip()
                        self.llm.messages.append({
                            "role": "user",
                            "content": self._build_ambiguity_followup_message(ambiguity_context, answer_text),
                        })
                        self._pending_planning_ambiguity = None
                        print("[AGENT] ambiguity clarification forced from DOM evidence")
                        continue
                    if not guard_result.should_stop and guard_result.inspection.thinking_only:
                        self.llm.messages.append(self._assistant_message_entry(message))
                        self.llm.messages.append({
                            "role": "user",
                            "content": (
                                "You have sent a thinking message. Now you MUST call either:\n"
                                "  send_to_overlay(message_type='plan_ready', payload={...}) — to submit your plan, or\n"
                                "  ask_user(question='...') — if intent is still ambiguous.\n"
                                "Do not send another llm_thinking. Produce your terminal planning output now."
                            ),
                        })
                        ambiguity_instruction = self._build_pending_ambiguity_instruction()
                        if ambiguity_instruction:
                            self.llm.messages.append({"role": "user", "content": ambiguity_instruction})
                        self._step_plan_convergence_narrowing = True
                        print("[AGENT] planning convergence pressure: injected after llm_thinking turn")
                        continue
                    if guard_result.should_stop:
                        self.phase_tracker.set_phase(
                            "failed",
                            reason="planning_no_progress",
                            step_id=None,
                        )
                        self.phase = "failed"
                        rejection_message = guard_result.message or "Planning did not produce a terminal response."
                        await self._send(
                            "runtime_rejected",
                            **build_runtime_rejection_payload(
                                guard_result.reason_code or "PLANNING_NO_PROGRESS",
                                rejection_message,
                                detail=guard_result.detail,
                                current_state={
                                    "run_id": self._current_run_session_id(),
                                    "phase": self._current_phase(),
                                    "purpose": effective_purpose,
                                    "consecutive_thinking_only_turns": guard_result.state.consecutive_thinking_only_turns,
                                    "planning_turns_without_terminal_output": guard_result.state.planning_turns_without_terminal_output,
                                    "max_consecutive_thinking_only_turns": 2,
                                    "max_planning_turns_without_terminal_output": 3,
                                },
                                run_id=self._current_run_session_id(),
                                recoverable=False,
                                source="agent",
                            ),
                        )
                        self._pending_failure_followup = False
                        return
                self.llm.messages.append(self._assistant_message_entry(message))

                if not message.tool_calls:
                    final_text = (message.content or "").strip()
                    if effective_purpose == "step_plan_normalizer":
                        retry_message = (
                            "Do not answer planning in plain text. "
                            "Call send_to_overlay(message_type='plan_ready', payload={...}) when the plan is complete, "
                            "or call ask_user(question='...') when the target or required data is still ambiguous."
                        )
                        self.llm.messages.append({"role": "user", "content": retry_message})
                        ambiguity_instruction = self._build_pending_ambiguity_instruction()
                        if ambiguity_instruction:
                            self.llm.messages.append({"role": "user", "content": ambiguity_instruction})
                        print("[AGENT] planning schema retry: plain-text response is non-terminal")
                        continue
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
                    self._update_planning_ambiguity_from_tool_result(tool_name, result)
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
        text = self._normalize_space(final_text).lower()
        if not text:
            return had_tool_failure

        request_phrases = (
            "please advise",
            "how would you like to proceed",
            "await your instruction",
            "please confirm",
            "which option",
            "i need your input",
            "need your input",
            "i need your guidance",
            "can you clarify",
            "what should i do next",
            "please let me know how you would like to proceed",
            "please tell me how you would like to proceed",
            "what would you like me to do",
            "what would you like to do",
            "do you want me to",
            "would you like me to",
            "should i",
        )
        if any(phrase in text for phrase in request_phrases):
            return True

        blocked_phrases = (
            "cannot continue",
            "can't continue",
            "unable to continue",
            "unable to proceed",
            "i am blocked",
            "blocked",
            "stuck",
            "need guidance",
            "need correction",
            "need clarification",
            "need help",
            "i can't proceed",
            "i cannot proceed",
            "i am unable",
        )
        if any(phrase in text for phrase in blocked_phrases):
            return True

        if had_tool_failure and not self._looks_like_completion_message(text):
            return True

        return False

    def _looks_like_completion_message(self, text: str) -> bool:
        normalized = self._normalize_space(text).lower()
        if not normalized:
            return False

        word_patterns = (
            r"\bdone\b",
            r"\bfinished\b",
            r"\bcompleted\b",
            r"\bsuccessfully\b",
        )
        if any(re.search(pattern, normalized) for pattern in word_patterns):
            return True

        multi_word_phrases = (
            "task complete",
            "task is complete",
            "completed successfully",
            "all set",
            "wrapped up",
            "run is complete",
            "run complete",
        )
        return any(phrase in normalized for phrase in multi_word_phrases)

    def _format_user_followup_message(self, answer: str, event_type: str) -> str:
        answer_text = self._normalize_space(answer)
        if self._is_correction_followup(answer_text, event_type):
            details = answer_text or "the user requested a correction"
            return f"User correction: {details}. Revise the plan and continue safely."

        details = answer_text or "confirmed"
        return f"User confirmed: {details}. Continue safely from the current browser state."

    def _is_correction_followup(self, answer: str, event_type: str) -> bool:
        if event_type == "correction":
            return True
        if event_type != "option_selected":
            return False

        normalized = self._normalize_space(answer).lower()
        correction_markers = (
            "instead",
            "first",
            "then",
            "before",
            "after",
            "revise",
            "change",
            "fix",
            "retry",
            "go back",
            "navigate back",
            "assert",
            "click",
            "fill",
        )
        return any(marker in normalized for marker in correction_markers)

    def _is_browser_state_tool(self, tool_name: str) -> bool:
        return tool_name in {
            "dom_extract",
            "locator_find",
            "locator_validate",
            "action_click",
            "action_fill",
            "action_assert",
            "page_navigate",
            "page_go_back",
            "page_go_forward",
            "page_reload",
            "scroll_into_view",
            "browser_get_state",
            "screenshot_take",
        }

    def _load_skills_for_steps(self, steps: list[dict]) -> tuple[list[str], str, dict[str, str]]:
        intents = " ".join(str(step.get("intent") or "") for step in steps).lower()
        loaded_names = ["core"]
        core_skill_text = self._read_skill("core", compact_mode=True) or ""
        loaded_skills = {"core": core_skill_text}
        contents = [core_skill_text]

        for skill_name, keywords in SKILL_KEYWORDS:
            if skill_name == "core":
                continue
            if any(keyword in intents for keyword in keywords):
                skill_text = self._read_skill(skill_name, compact_mode=True)
                if skill_text is None:
                    continue
                loaded_names.append(skill_name)
                loaded_skills[skill_name] = skill_text
                contents.append(skill_text)

        return loaded_names, "\n\n".join(contents), loaded_skills

    def _read_skill(self, skill_name: str, *, compact_mode: bool = False) -> str | None:
        if compact_mode:
            compact_path = self.skills_root / skill_name / "SKILL_COMPACT.md"
            if compact_path.is_file():
                print(f"[SKILL_COMPACT] loading compact skill: {skill_name}")
                return compact_path.read_text(encoding="utf-8")
        skill_path = self.skills_root / skill_name / "SKILL.md"
        if not skill_path.is_file():
            missing_skill_names = getattr(self, "_missing_skill_names", set())
            if skill_name not in missing_skill_names:
                print(f"[SKILL_WARNING] missing skill folder: {skill_name}")
                self._record_capability_gap(
                    "missing_skill",
                    "_read_skill",
                    "warn",
                    f"missing skill folder: {skill_name}",
                    skill_name=skill_name,
                )
                missing_skill_names.add(skill_name)
                self._missing_skill_names = missing_skill_names
            return None
        return skill_path.read_text(encoding="utf-8")

    async def _try_deterministic_fast_path(self, steps: list[dict]) -> bool:
        """Attempt zero-LLM planning through the extracted deterministic gateway."""
        return await attempt_deterministic_fast_path(self, steps, get_page=get_page)

    def _build_confirmed_execution_tool_call(
        self,
        child: dict[str, Any],
        *,
        step_context: dict[str, Any] | None = None,
    ) -> tuple[str, dict[str, Any]]:
        child_type = self._normalize_space(str(child.get("type") or "")).strip().lower()
        locator = self._normalize_space(str(child.get("locator") or "")).strip()
        if not locator and isinstance(step_context, dict):
            locator = self._derive_locator_from_step_context(step_context)

        if child_type == "click":
            return "action_click", {"locator": locator}
        if child_type == "fill":
            return "action_fill", {
                "locator": locator,
                "value": child.get("value") or child.get("expected_value") or "",
            }
        if child_type == "assert":
            assertion = self._infer_confirmed_execution_child_assertion(child, source_step=step_context)
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

    async def _execute_deterministic_fast_path_confirmed_plan(self) -> None:
        confirmed_cursor = self._current_confirmed_execution_cursor()
        if not isinstance(confirmed_cursor, dict):
            print("[FAST_PATH] execution failed: confirmed execution cursor missing")
            await self._send(
                "llm_result",
                success=False,
                message="Deterministic execution failed safely because the confirmed execution contract was unavailable.",
            )
            self._pending_failure_followup = False
            return

        step_context = confirmed_cursor.get("step_context")
        contract = confirmed_cursor.get("contract")
        expected_child = confirmed_cursor.get("next_child")
        if not isinstance(contract, dict) or not isinstance(expected_child, dict):
            print("[FAST_PATH] execution failed: no confirmed child available")
            await self._send(
                "llm_result",
                success=False,
                message="Deterministic execution failed safely because no confirmed child operation was available.",
            )
            self._pending_failure_followup = False
            return

        tool_name, args = self._build_confirmed_execution_tool_call(
            expected_child,
            step_context=step_context if isinstance(step_context, dict) else None,
        )
        print(
            "[FAST_PATH] executing confirmed child "
            f"{self._describe_confirmed_execution_child(expected_child)} via {tool_name}"
        )

        confirmed_execution_check = self._validate_confirmed_execution_tool_call(tool_name, args)
        if isinstance(confirmed_execution_check, dict) and not confirmed_execution_check.get("allowed", False):
            blocked_result = dict(confirmed_execution_check)
            blocked_result.pop("allowed", None)
            if isinstance(expected_child, dict):
                self._record_confirmed_execution_child_result(
                    step_context,
                    expected_child,
                    tool_name=tool_name,
                    args=args,
                    result=blocked_result,
                    status="blocked",
                )
            self.phase_tracker.set_phase(
                "failed",
                reason="deterministic_execution_contract_blocked",
                step_id=str(contract.get("step_id") or "").strip() or None,
            )
            self.phase = "failed"
            await self._send(
                "llm_result",
                success=False,
                message=str(blocked_result.get("message") or "Deterministic execution was blocked."),
            )
            self._pending_failure_followup = False
            return

        browser_state_before = await self._capture_browser_state()
        result = await self._dispatch_tool(tool_name, args)
        print(f"[FAST_PATH] tool result: {self._summarize(result, limit=120)}")

        if result.get("success") is not True or result.get("skipped"):
            self._record_confirmed_execution_child_result(
                step_context,
                expected_child,
                tool_name=tool_name,
                args=args,
                result=result,
                status="failed" if result.get("success") is False else "blocked",
                browser_state_before=browser_state_before,
            )
            if isinstance(step_context, dict):
                self._mark_step_failed(step_context, result.get("error") or result.get("message") or "deterministic execution failed")
            self.phase_tracker.set_phase(
                "failed",
                reason="deterministic_execution_failed",
                step_id=str(contract.get("step_id") or "").strip() or None,
            )
            self.phase = "failed"
            await self._send(
                "llm_result",
                success=False,
                message=str(result.get("error") or result.get("message") or "Deterministic execution failed safely."),
            )
            self._pending_failure_followup = False
            return

        browser_state_after = await self._capture_browser_state()
        self._record_confirmed_execution_child_result(
            step_context,
            expected_child,
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
        recorded_payload = await self._auto_record_successful_step()
        if recorded_payload is None:
            if not self._confirmed_execution_step_ready_to_record(step_context):
                print("[FAST_PATH] confirmed child completed; awaiting remaining confirmed children")
                return
            print("[FAST_PATH] execution failed: auto-record did not produce a recorded payload")
            self.phase_tracker.set_phase(
                "failed",
                reason="deterministic_recording_missing",
                step_id=str(contract.get("step_id") or "").strip() or None,
            )
            self.phase = "failed"
            await self._send(
                "llm_result",
                success=False,
                message="Deterministic execution succeeded but recording failed safely.",
            )
            self._pending_failure_followup = False
            return

        if self._run_completion_requested:
            print("[FAST_PATH] execution completed without planning LLM call")
            self._pending_failure_followup = False
            self._reset_lifecycle_state()
            return

        print("[FAST_PATH] execution completed; run remains open for remaining work")

    def _is_click_like_intent(self, intent: Any) -> bool:
        normalized_intent = self._normalize_space(str(intent or "")).lower()
        return bool(CLICK_LIKE_INTENT_PATTERN.search(normalized_intent))

    def _is_outcome_like_label(self, value: Any) -> bool:
        normalized_value = self._normalize_space(str(value or "")).strip().lower()
        if not normalized_value:
            return False

        compact_value = re.sub(r"[\s-]+", "_", normalized_value)
        if compact_value in EXPECTED_OUTCOME_TYPES:
            return True

        if compact_value.startswith("expected_outcome"):
            return True

        if normalized_value == "expected outcome":
            return True

        if normalized_value == "picker" or normalized_value.startswith("picker:") or normalized_value.startswith("picker -"):
            return True

        for outcome_label in EXPECTED_OUTCOME_TYPES:
            for separator in (" ·", ":", " -", " —"):
                if normalized_value.startswith(f"{outcome_label}{separator}"):
                    return True

        return False

    def _extract_assertion_expected_value(self, value: Any) -> str:
        candidate_text = self._normalize_space(str(value or "")).strip()
        if not candidate_text or self._is_outcome_like_label(candidate_text):
            return ""

        quoted_match = re.search(r'["“”`](.+?)["“”`]', candidate_text)
        if quoted_match:
            quoted_text = self._normalize_space(quoted_match.group(1)).strip()
            if quoted_text and not self._is_outcome_like_label(quoted_text):
                return quoted_text

        lowered_text = candidate_text.lower()
        markers = (
            "exact text equal to",
            "exact text equals",
            "text equal to",
            "text equals",
            "exactly match",
            "exactly matches",
            "match exactly",
            "equal to",
            "equals",
            "contains text",
            "has text",
            "includes text",
            "includes",
            "include",
        )
        for marker in markers:
            marker_index = lowered_text.find(marker)
            if marker_index < 0:
                continue
            extracted_text = self._normalize_space(
                candidate_text[marker_index + len(marker) :]
            ).strip(" :,-–—")
            if extracted_text and not self._is_outcome_like_label(extracted_text):
                return extracted_text

        return ""

    def _select_plan_correction_child_target(self, candidates: list[tuple[str, Any]]) -> str:
        for field_name, candidate in candidates:
            candidate_text = self._normalize_space(str(candidate or "")).strip()
            if not candidate_text:
                continue
            if self._is_outcome_like_label(candidate_text):
                print(
                    "[PLAN_CORRECTION_CHILD] ignored outcome-like child field "
                    f"value={candidate_text} field={field_name}"
                )
                continue
            return candidate_text
        return ""

    def _canonicalize_assertion_operation(
        self,
        operation_spec: dict[str, Any],
        source_step: dict[str, Any] | None = None,
        anchor_child: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        operation_data = operation_spec if isinstance(operation_spec, dict) else {}
        source_step_data = source_step if isinstance(source_step, dict) else {}
        anchor_child_data = anchor_child if isinstance(anchor_child, dict) else {}

        operation_type = self._normalize_space(
            str(operation_data.get("type") or operation_data.get("action") or "")
        ).strip().lower()
        if operation_type != "assert":
            return {}

        source_element_info = self._resolve_selected_element_info(
            source_step_data.get("element_info") if isinstance(source_step_data.get("element_info"), dict) else {}
        )
        source_element_text = self._selected_element_text(source_element_info)

        hint_text_parts = [
            str(operation_data.get("description") or "").strip(),
            str(operation_data.get("text") or "").strip(),
            str(operation_data.get("target") or "").strip(),
            str(operation_data.get("value") or operation_data.get("expected_value") or operation_data.get("expected_text") or "").strip(),
            str(anchor_child_data.get("description") or "").strip(),
            str(anchor_child_data.get("target") or "").strip(),
            str(source_step_data.get("intent") or "").strip(),
            str(source_step_data.get("element_name") or "").strip(),
            source_element_text,
        ]
        hint_text = self._normalize_space(" ".join(part for part in hint_text_parts if part)).strip().lower()

        explicit_assertion = self._normalize_space(
            str(operation_data.get("assertion") or anchor_child_data.get("assertion") or "")
        ).strip().lower()
        assertion_aliases = {
            "exact_text": "has_text",
            "text_equal": "has_text",
            "text_equals": "has_text",
            "contains_text": "has_text",
            "includes_text": "has_text",
        }
        assertion = assertion_aliases.get(explicit_assertion, explicit_assertion)

        exact_text_mode = any(
            marker in hint_text
            for marker in (
                "exact text equal to",
                "exact text equals",
                "text equal to",
                "text equals",
                "exactly match",
                "exactly matches",
                "match exactly",
                "equal to",
                "equals",
            )
        )
        contains_text_mode = any(
            marker in hint_text
            for marker in (
                "contains text",
                "has text",
                "includes text",
                "includes",
                "include",
            )
        )
        visible_mode = any(
            marker in hint_text
            for marker in (
                " visible",
                "visible",
                "present",
                "on screen",
                "displayed",
            )
        )
        if exact_text_mode or contains_text_mode:
            assertion = "has_text"
        elif not assertion:
            if visible_mode:
                assertion = "visible"
            elif self._normalize_space(str(operation_data.get("value") or operation_data.get("expected_value") or "")).strip():
                assertion = "has_text"
            else:
                assertion = "visible"

        if assertion not in {"visible", "hidden", "enabled", "disabled", "checked", "has_text", "has_value"}:
            assertion = "has_text" if exact_text_mode or contains_text_mode else "visible"

        expected_value = ""
        direct_value_candidates = [
            operation_data.get("expected_value"),
            operation_data.get("expected_text"),
            operation_data.get("value"),
            operation_data.get("text"),
            anchor_child_data.get("expected_value"),
            anchor_child_data.get("expected_text"),
            anchor_child_data.get("value"),
            anchor_child_data.get("text"),
        ]
        for candidate in direct_value_candidates:
            candidate_text = self._normalize_space(str(candidate or "")).strip()
            if candidate_text and not self._is_outcome_like_label(candidate_text):
                expected_value = candidate_text
                break

        if not expected_value:
            parsed_value_candidates = [
                operation_data.get("description"),
                operation_data.get("target"),
                operation_data.get("element_name"),
                operation_data.get("intent"),
                anchor_child_data.get("description"),
                anchor_child_data.get("target"),
                source_step_data.get("intent"),
                source_step_data.get("element_name"),
                source_element_text,
            ]
            for candidate in parsed_value_candidates:
                parsed_value = self._extract_assertion_expected_value(candidate)
                if parsed_value:
                    expected_value = parsed_value
                    break

        if not expected_value and (exact_text_mode or contains_text_mode or assertion == "has_text"):
            for candidate in (
                operation_data.get("target"),
                operation_data.get("element_name"),
                anchor_child_data.get("target"),
                anchor_child_data.get("element_name"),
                source_step_data.get("element_name"),
                source_element_text,
            ):
                candidate_text = self._normalize_space(str(candidate or "")).strip()
                if candidate_text and not self._is_outcome_like_label(candidate_text):
                    expected_value = candidate_text
                    break

        locator = self._normalize_space(
            str(
                operation_data.get("locator")
                or anchor_child_data.get("locator")
                or source_step_data.get("locator")
                or self._derive_locator_from_step_context(source_step_data)
                or ""
            )
        ).strip()
        if locator in {"*", 'page.locator("")'}:
            locator = ""
        target = self._select_plan_correction_child_target(
            [
                ("operation.target", operation_data.get("target")),
                ("operation.element_name", operation_data.get("element_name")),
                ("anchor.target", anchor_child_data.get("target")),
                ("anchor.description", anchor_child_data.get("description")),
                ("source.element_name", source_step_data.get("element_name")),
                ("source.intent", source_step_data.get("intent")),
            ]
        )
        target_text = self._normalize_space(str(target or "")).strip()
        source_intent_text = self._normalize_space(str(source_step_data.get("intent") or "")).strip()
        operation_description_text = self._normalize_space(
            str(operation_data.get("description") or anchor_child_data.get("description") or "")
        ).strip()
        if assertion == "has_text" and expected_value:
            if (
                not target_text
                or self._is_outcome_like_label(target_text)
                or target_text == source_intent_text
                or target_text == operation_description_text
                or expected_value in target_text
                or target_text in expected_value
            ):
                target = expected_value

        visible_target_text = target_text
        if assertion == "visible" and expected_value:
            if (
                not visible_target_text
                or self._is_outcome_like_label(visible_target_text)
                or visible_target_text.lower() in {"main", "page", "body", "document"}
                or expected_value in visible_target_text
                or visible_target_text in expected_value
                or "heading" in visible_target_text.lower()
            ):
                visible_target_text = expected_value

        if assertion in {"visible", "has_text"} and source_element_text:
            if (
                not visible_target_text
                or self._is_outcome_like_label(visible_target_text)
                or visible_target_text.lower() in {"main", "page", "body", "document"}
                or "heading" in visible_target_text.lower()
            ):
                visible_target_text = source_element_text

        locator_label_text = self._locator_label_hint(locator)
        source_locator = self._normalize_space(str(source_step_data.get("locator") or "")).strip()
        source_locator_label = self._locator_label_hint(source_locator)
        preferred_visible_label = locator_label_text
        if source_locator_label:
            if not preferred_visible_label:
                preferred_visible_label = source_locator_label
            elif source_locator_label in preferred_visible_label and len(source_locator_label) < len(preferred_visible_label):
                preferred_visible_label = source_locator_label

        if assertion == "visible" and preferred_visible_label:
            if (
                not visible_target_text
                or self._is_outcome_like_label(visible_target_text)
                or visible_target_text.lower() in {"main", "page", "body", "document"}
                or "heading" in visible_target_text.lower()
                or preferred_visible_label in visible_target_text
            ):
                visible_target_text = preferred_visible_label

        if (
            assertion == "visible"
            and source_locator
            and source_locator_label
            and preferred_visible_label == source_locator_label
            and source_locator != locator
            and source_locator_label in visible_target_text
        ):
            locator = source_locator

        if assertion == "visible":
            if visible_target_text:
                target = visible_target_text
                target_text = visible_target_text
            locator_value_text = expected_value or target_text or source_element_text
            normalized_locator = self._normalize_space(locator).strip().lower()
            if locator_value_text and normalized_locator in {"main", 'page.locator("main")', "page.locator('main')"}:
                locator = f'get_by_text("{self._tool_string_escape(locator_value_text)}", exact=True)'

        if not locator and assertion == "has_text" and expected_value:
            locator = f'get_by_text("{self._tool_string_escape(expected_value)}", exact=True)'

        description = self._build_plan_correction_child_description(
            "assert",
            target,
            assertion,
            expected_value,
            str(operation_data.get("description") or anchor_child_data.get("description") or "").strip(),
            str(source_step_data.get("intent") or target or "").strip(),
        )

        normalized_child: dict[str, Any] = {
            "assertion": assertion,
            "target": target,
            "locator": locator,
            "description": description,
        }
        if expected_value:
            normalized_child["value"] = expected_value
            normalized_child["expected_value"] = expected_value
        return normalized_child

    def _build_plan_correction_child_description(
        self,
        operation_type: str,
        target: str,
        assertion: str,
        value_text: str,
        raw_description: str,
        intent: str,
    ) -> str:
        operation_name = self._normalize_space(str(operation_type or "")).strip().lower()
        target_text = self._normalize_space(str(target or "")).strip()
        assertion_text = self._normalize_space(str(assertion or "")).strip().lower()
        value_text = self._normalize_space(str(value_text or "")).strip()
        intent_text = self._normalize_space(str(intent or "")).strip()
        raw_description_text = self._normalize_space(str(raw_description or "")).strip()

        if operation_name == "assert":
            if raw_description_text and self._is_outcome_like_label(raw_description_text):
                print(
                    "[PLAN_CORRECTION_CHILD] ignored outcome-like child field "
                    f"value={raw_description_text} field=description"
                )
            action_context: dict[str, Any] = {}
            if assertion_text:
                action_context["assertion"] = assertion_text
            if value_text:
                action_context["value"] = value_text
            return self._build_recorded_child_description("assert", "assert", target_text, action_context, intent_text)

        if raw_description_text:
            if self._is_outcome_like_label(raw_description_text):
                print(
                    "[PLAN_CORRECTION_CHILD] ignored outcome-like child field "
                    f"value={raw_description_text} field=description"
                )
            else:
                return raw_description_text

        return self._build_planned_child_description(operation_name, target_text, intent_text)

    def _normalize_expected_outcome(
        self,
        expected_outcome: Any,
        required: bool = False,
    ) -> dict[str, Any] | None:
        if not isinstance(expected_outcome, dict):
            return None

        type_text = self._normalize_space(str(expected_outcome.get("type") or "")).lower()
        type_text = re.sub(r"[\s-]+", "_", type_text)
        if not type_text or type_text not in EXPECTED_OUTCOME_TYPES:
            return None

        description_text = self._normalize_space(str(expected_outcome.get("description") or "")).strip()
        normalized_outcome: dict[str, Any] = {
            "type": type_text,
            "source": "user",
            "required": bool(required or expected_outcome.get("required") is True),
        }
        if description_text:
            normalized_outcome["description"] = description_text
        return normalized_outcome

    def _expected_outcome_summary(self, expected_outcome: Any) -> str:
        if not isinstance(expected_outcome, dict):
            return ""

        type_text = self._normalize_space(str(expected_outcome.get("type") or "")).lower()
        type_text = re.sub(r"[\s-]+", "_", type_text)
        if not type_text or type_text not in EXPECTED_OUTCOME_TYPES:
            return ""

        description_text = self._normalize_space(str(expected_outcome.get("description") or "")).strip()
        summary = f"{type_text} · {description_text}" if description_text else type_text
        if len(summary) > 80:
            return f"{summary[:79]}..."
        return summary

    def _resolve_selected_element_info(self, element_info: dict[str, Any]) -> dict[str, Any]:
        if not isinstance(element_info, dict):
            return {}

        candidates = element_info.get("candidates")
        if not isinstance(candidates, list) or not candidates:
            return element_info

        selected_candidate_index = element_info.get("selected_candidate_index")
        selected_index: int | None = None
        if isinstance(selected_candidate_index, int):
            selected_index = selected_candidate_index
        else:
            try:
                selected_index = int(str(selected_candidate_index or "").strip())
            except (TypeError, ValueError):
                selected_index = None
        if selected_index is None or selected_index < 0 or selected_index >= len(candidates):
            selected_index = 0

        selected_candidate = candidates[selected_index]
        if not isinstance(selected_candidate, dict):
            return element_info

        selected_attributes = selected_candidate.get("attributes") if isinstance(selected_candidate.get("attributes"), dict) else {}
        merged = dict(element_info)
        merged["selected_candidate_index"] = selected_index
        merged["candidates"] = deepcopy(candidates)
        merged["tag"] = self._normalize_space(str(selected_candidate.get("tag") or merged.get("tag") or "")).strip().lower()
        merged["id"] = self._normalize_space(
            str(selected_candidate.get("id") or merged.get("id") or selected_attributes.get("id") or "")
        ).strip()
        merged["class"] = self._normalize_space(
            str(
                selected_candidate.get("className")
                or selected_candidate.get("class")
                or merged.get("className")
                or merged.get("class")
                or selected_attributes.get("className")
                or selected_attributes.get("class")
                or ""
            )
        ).strip()
        merged["className"] = merged["class"]

        selected_text = self._normalize_space(
            str(
                selected_candidate.get("cleanText")
                or selected_candidate.get("clean_text")
                or selected_candidate.get("text")
                or merged.get("clean_text")
                or merged.get("cleanText")
                or merged.get("text")
                or ""
            )
        ).strip()
        merged["text"] = selected_text
        merged["clean_text"] = selected_text
        merged["cleanText"] = selected_text

        role_value = self._normalize_space(
            str(selected_candidate.get("role") or merged.get("role") or selected_attributes.get("role") or "")
        ).strip()
        if role_value:
            merged["role"] = role_value

        aria_label_value = self._normalize_space(
            str(
                selected_candidate.get("ariaLabel")
                or selected_candidate.get("aria_label")
                or merged.get("ariaLabel")
                or merged.get("aria_label")
                or selected_attributes.get("aria-label")
                or ""
            )
        ).strip()
        if aria_label_value:
            merged["ariaLabel"] = aria_label_value
            merged["aria_label"] = aria_label_value

        semantic_value = self._normalize_space(
            str(
                selected_candidate.get("semanticType")
                or selected_candidate.get("semantic_type")
                or selected_candidate.get("category")
                or merged.get("semantic_type")
                or merged.get("semanticType")
                or ""
            )
        ).strip()
        if semantic_value:
            merged["semantic_type"] = semantic_value
            merged["semanticType"] = semantic_value

        selector_value = self._normalize_space(
            str(
                selected_candidate.get("selectorHint")
                or selected_candidate.get("selector_hint")
                or merged.get("selector_hint")
                or merged.get("selectorHint")
                or ""
            )
        ).strip()
        if selector_value:
            merged["selector_hint"] = selector_value
            merged["selectorHint"] = selector_value

        locator_value = self._normalize_space(
            str(
                selected_candidate.get("locatorHint")
                or selected_candidate.get("locator_hint")
                or merged.get("locator_hint")
                or merged.get("locatorHint")
                or ""
            )
        ).strip()
        if locator_value:
            merged["locator_hint"] = locator_value
            merged["locatorHint"] = locator_value

        merged["attributes"] = deepcopy(
            selected_attributes or (merged.get("attributes") if isinstance(merged.get("attributes"), dict) else {})
        )
        return merged

    def _selected_element_text(self, element_info: dict[str, Any]) -> str:
        selected_element_info = self._resolve_selected_element_info(element_info)
        attributes = selected_element_info.get("attributes") if isinstance(selected_element_info.get("attributes"), dict) else {}
        candidates = [
            selected_element_info.get("clean_text"),
            selected_element_info.get("cleanText"),
            selected_element_info.get("text"),
            attributes.get("aria-label"),
            selected_element_info.get("ariaLabel"),
            selected_element_info.get("aria_label"),
            attributes.get("placeholder"),
            attributes.get("data-testid"),
            selected_element_info.get("id"),
        ]
        for candidate in candidates:
            candidate_text = self._normalize_space(str(candidate or "")).strip()
            if candidate_text:
                return candidate_text
        return ""

    def _element_candidate_display_text(self, element_info: dict[str, Any]) -> str:
        if not isinstance(element_info, dict):
            return ""
        attributes = element_info.get("attributes") if isinstance(element_info.get("attributes"), dict) else {}
        candidates = [
            element_info.get("clean_text"),
            element_info.get("cleanText"),
            element_info.get("text"),
            attributes.get("aria-label"),
            element_info.get("ariaLabel"),
            element_info.get("aria_label"),
            attributes.get("placeholder"),
            attributes.get("data-testid"),
            element_info.get("id"),
        ]
        for candidate in candidates:
            candidate_text = self._normalize_space(str(candidate or "")).strip()
            if candidate_text:
                return candidate_text
        return ""

    def _best_fast_path_target_label(self, step: dict[str, Any], action_verb: str) -> str:
        step_data = step if isinstance(step, dict) else {}
        max_label_length = 80
        preferred_roles = {"heading", "link", "button", "textbox", "text"}
        explicit_name = self._normalize_space(str(step_data.get("element_name") or "")).strip()
        if explicit_name and len(explicit_name) <= max_label_length and explicit_name.lower() not in {"main", "page", "body", "document"}:
            return explicit_name

        element_info = step_data.get("element_info") if isinstance(step_data.get("element_info"), dict) else {}
        raw_candidates = element_info.get("candidates") if isinstance(element_info.get("candidates"), list) else []
        fallback_label = ""
        for raw_candidate in raw_candidates:
            if not isinstance(raw_candidate, dict):
                continue
            candidate_text = self._normalize_space(self._element_candidate_display_text(raw_candidate)).strip()
            if (
                not candidate_text
                or len(candidate_text) > max_label_length
                or candidate_text.lower() in {"main", "page", "body", "document"}
            ):
                continue
            candidate_role = self._normalize_space(
                str(
                    raw_candidate.get("role")
                    or raw_candidate.get("semanticType")
                    or raw_candidate.get("semantic_type")
                    or raw_candidate.get("category")
                    or raw_candidate.get("tag")
                    or ""
                )
            ).strip().lower()
            if action_verb in {"assert_visible", "assert_text"} and candidate_role in preferred_roles:
                return candidate_text
            if not fallback_label:
                fallback_label = candidate_text
        selected_text = self._normalize_space(self._selected_element_text(element_info)).strip()
        if selected_text and len(selected_text) <= max_label_length and selected_text.lower() not in {"main", "page", "body", "document"}:
            return selected_text
        return fallback_label

    def _should_replace_fast_path_locator_with_text(self, action_verb: str, locator: str) -> bool:
        if action_verb not in {"assert_visible", "assert_text"}:
            return False
        normalized_locator = self._normalize_space(str(locator or "")).strip().lower()
        return normalized_locator in {"main", "body", "page", 'page.locator("main")', "page.locator('main')"}

    def _compact_step_element_summary(self, step: dict[str, Any]) -> str:
        element_info = self._resolve_selected_element_info(step.get("element_info") or {})
        if not isinstance(element_info, dict):
            return ""

        attributes = element_info.get("attributes") if isinstance(element_info.get("attributes"), dict) else {}
        candidates = [
            self._selected_element_text(element_info),
            self._normalize_space(str(attributes.get("aria-label") or "")).strip(),
            self._normalize_space(str(attributes.get("placeholder") or "")).strip(),
            self._normalize_space(str(element_info.get("id") or "")).strip(),
            self._normalize_space(str(element_info.get("tag") or "")).strip(),
        ]
        parts = [part for part in candidates if part]
        return " · ".join(parts[:3])

    def _validate_recording_steps(self, steps: list[dict[str, Any]]) -> None:
        for index, step in enumerate(steps, start=1):
            if not isinstance(step, dict):
                continue

            intent = self._normalize_space(str(step.get("intent") or "")).strip()
            if not intent or not self._is_click_like_intent(intent):
                continue

            normalized_expected_outcome = self._normalize_expected_outcome(
                step.get("expected_outcome") or step.get("expectedOutcome"),
                True,
            )
            if normalized_expected_outcome is None or not str(normalized_expected_outcome.get("type") or "").strip():
                step_ref = str(step.get("id") or step.get("step_id") or step.get("stepId") or index).strip() or str(index)
                raise ValueError(f"Click-like step {step_ref} requires expected_outcome.type")

    def _format_steps(self, steps: list[dict]) -> str:
        normalized_steps = self._normalize_steps(steps)
        lines = ["User steps:"]
        for index, step in enumerate(normalized_steps, start=1):
            step_intent = self._normalize_space(str(step.get("intent") or "")).strip()
            lines.append(f"{index}. {step_intent}" if step_intent else f"{index}.")

            raw_step = steps[index - 1] if index - 1 < len(steps) and isinstance(steps[index - 1], dict) else {}
            step_expected_outcome = self._expected_outcome_summary(
                self._normalize_expected_outcome(
                    raw_step.get("expected_outcome") or raw_step.get("expectedOutcome"),
                    self._is_click_like_intent(step_intent),
                )
            )
            if step_expected_outcome:
                lines.append(f"   expected_outcome: {step_expected_outcome}")

            element_summary = self._compact_step_element_summary(raw_step)
            if element_summary:
                lines.append(f"   element: {element_summary}")

        lines.extend(
            [
                "",
                "Execution requirements:",
                "- Always use tools. Never guess.",
                '- Start by calling send_to_overlay with message_type "llm_thinking".',
                "- Use browser_get_state or dom_extract before deciding what is on the page.",
                "- If a step includes suggested_scope for a picked element, call dom_extract with that suggested_scope first.",
                "- Validate locators before using them for actions or assertions.",
                "- Use page_go_back, page_go_forward, and page_reload for browser history or refresh actions.",
                "- Use action_fill only on editable fields. Never use it on body to simulate navigation.",
                "- Recording is backend-owned. After successful execution, the runtime records the step automatically and emits code_update.",
                "- If the user corrects the plan, revise it before any action and ask for confirmation again.",
                '- When finished, report the outcome clearly through send_to_overlay or the final assistant response.',
            ]
        )
        return "\n".join(lines)

    def _prepare_recording_steps(self, steps: list[dict]) -> None:
        self.current_steps = list(steps)
        self._recording_steps = []
        self._recording_step_index = 0
        self._recorded_step_ids = set()
        self.step_state_by_id = {}
        self.step_context_by_id = self.step_state_by_id
        self._last_action_context = None
        self._awaiting_step_record = False
        self.current_step_index = 0

        for idx, step in enumerate(self.current_steps, start=1):
            raw_element_info = step.get("element_info") if isinstance(step.get("element_info"), dict) else {}
            resolved_element_info = self._resolve_selected_element_info(raw_element_info)
            step_id = str(step.get("id") or "").strip() or str(idx)
            intent_text = str(step.get("intent") or "").strip()
            context = {
                "step_id": step_id,
                "step_number": idx,
                "intent": intent_text,
                "element_info": resolved_element_info,
                "element_name": self._derive_step_context_element_name(step, resolved_element_info),
                "locator": None,
                "last_error": None,
                "status": "pending",
                "recorded": False,
                "expected_outcome": self._normalize_expected_outcome(
                    step.get("expected_outcome") or step.get("expectedOutcome"),
                    self._is_click_like_intent(intent_text),
                ),
            }
            self._recording_steps.append(context)
            self.step_state_by_id[step_id] = context
            print(f"[AGENT] step pending: {step_id}")

    def _get_step_context(self, step_id: str | None = None) -> dict[str, Any] | None:
        if step_id is not None:
            resolved_step_id = str(step_id).strip()
            if resolved_step_id:
                return self.step_state_by_id.get(resolved_step_id)

        if self.active_step_id:
            active_step = self.step_state_by_id.get(self.active_step_id)
            if active_step and active_step.get("status") not in {"recorded", "skipped"}:
                return active_step

        unresolved_steps = [
            step
            for step in self._recording_steps
            if str(step.get("status") or "") not in {"recorded", "skipped"}
        ]
        if len(unresolved_steps) == 1:
            return unresolved_steps[0]

        for step in self._recording_steps:
            if str(step.get("status") or "") in {"pending", "recovery_pending"}:
                return step

        return None

    def _resolve_recording_target_step(self, payload: dict[str, Any] | None = None) -> dict[str, Any] | None:
        confirmed_cursor = self._current_confirmed_execution_cursor()
        if isinstance(confirmed_cursor, dict):
            step_context = confirmed_cursor.get("step_context")
            if isinstance(step_context, dict):
                step_id = str(step_context.get("step_id") or "").strip() or "unknown"
                print(f"[RECORDING_TARGET] confirmed_mode=true step_id={step_id} source=confirmed_cursor")
                return step_context

        payload = payload or {}
        explicit_step_id = str(payload.get("step_id") or payload.get("id") or payload.get("stepId") or "").strip()
        if explicit_step_id:
            step = self.step_state_by_id.get(explicit_step_id)
            if step and str(step.get("status") or "") not in {"recorded", "skipped"}:
                return step

        explicit_step_number = self._coerce_step_number(payload.get("step_number"))
        if explicit_step_number is not None:
            return self._find_step_for_recording(None, explicit_step_number)

        unresolved_steps = [
            step
            for step in self._recording_steps
            if str(step.get("status") or "") not in {"recorded", "skipped"}
        ]
        if len(self.successful_action_by_step_id) > 1:
            if len(unresolved_steps) == 1:
                return unresolved_steps[0]
            return None

        for candidate_step_id in (self.active_step_id, self.active_failed_step_id):
            if not candidate_step_id:
                continue
            step = self.step_state_by_id.get(candidate_step_id)
            if step and str(step.get("status") or "") not in {"recorded", "skipped"}:
                return step

        last_action_step = (self.last_successful_action or {}).get("step_context") or {}
        last_action_step_id = str(last_action_step.get("step_id") or "").strip()
        if last_action_step_id:
            step = self.step_state_by_id.get(last_action_step_id)
            if step and str(step.get("status") or "") not in {"recorded", "skipped"}:
                return step

        return self._find_step_for_recording()

    def _get_failed_step_context(self) -> dict[str, Any] | None:
        if self.active_failed_step_id:
            step = self._get_step_context(self.active_failed_step_id)
            if step is not None:
                return step

        for step in self._recording_steps:
            if str(step.get("status") or "") in {"failed", "recovery_pending"}:
                return step

        return None

    def _mark_step_executing(self, step: dict[str, Any] | str | None) -> dict[str, Any] | None:
        context = self._get_step_context(step) if not isinstance(step, dict) else step
        if context is None:
            return None

        step_id = str(context.get("step_id") or "").strip()
        if not step_id:
            return None

        if context.get("status") not in {"recorded", "skipped"}:
            if context.get("status") != "recovery_pending":
                context["status"] = "executing"
            context["last_error"] = context.get("last_error")
        self.completed_step_ids.discard(step_id)
        self.skipped_step_ids.discard(step_id)
        self.active_step_id = step_id
        self.current_step_index = max(0, int(context.get("step_number") or 1) - 1)
        print(f"[AGENT] step executing: {step_id}")
        return context

    def _mark_step_failed(self, step: dict[str, Any] | str | None, error: Any) -> dict[str, Any] | None:
        context = self._get_step_context(step) if not isinstance(step, dict) else step
        if context is None:
            return None

        step_id = str(context.get("step_id") or "").strip()
        if not step_id:
            return None

        context["status"] = "recovery_pending"
        context["last_error"] = str(error or "").strip() or "execution tool failed"
        context["recorded"] = False
        self.pending_recovery = True
        self.active_failed_step_id = step_id
        self.active_step_id = step_id
        self.phase_tracker.set_phase("recovery", reason="tool_failed", step_id=step_id)
        self.phase = "recovering"
        self.completed_step_ids.discard(step_id)
        self.skipped_step_ids.discard(step_id)
        self._last_action_context = None
        self._awaiting_step_record = False
        self._recording_wait_guard_armed = False
        self.current_step_index = max(0, int(context.get("step_number") or 1) - 1)
        self._clear_failed_step_success_state(context)
        self._emit_recovery_needed_event(context, context["last_error"])
        print(f"[AGENT] step recovery_pending: {step_id}")
        return context

    def _clear_failed_step_success_state(self, step: dict[str, Any] | str | None) -> None:
        context = self._get_step_context(step) if not isinstance(step, dict) else step
        if context is None:
            return

        step_id = str(context.get("step_id") or "").strip()
        if not step_id:
            return

        step_number = self._coerce_step_number(context.get("step_number"))
        last_action = getattr(self, "last_successful_action", None) or {}
        last_action_step = last_action.get("step_context") or {}
        last_action_step_id = str(last_action_step.get("step_id") or last_action.get("step_id") or "").strip()
        last_action_step_number = self._coerce_step_number(
            last_action_step.get("step_number") or last_action.get("step_number")
        )
        if last_action_step_id == step_id or (
            step_number is not None and last_action_step_number is not None and last_action_step_number == step_number
        ):
            self.last_successful_action = None

        history_by_step_id = getattr(self, "successful_actions_by_step_id", None)
        if not isinstance(history_by_step_id, dict):
            history_by_step_id = {}
            self.successful_actions_by_step_id = history_by_step_id
        history_by_step_id.pop(step_id, None)
        successful_action_by_step_id = getattr(self, "successful_action_by_step_id", None)
        if not isinstance(successful_action_by_step_id, dict):
            successful_action_by_step_id = {}
            self.successful_action_by_step_id = successful_action_by_step_id
        successful_action_by_step_id.pop(step_id, None)
        self._last_action_context = None

    def _clear_plan_review_context(self) -> None:
        self.last_plan_ready_payload = None
        self.last_plan_step_ids = []
        self.last_plan_summary = None
        self.last_plan_original_user_intent = None

    def _clear_confirmed_execution_contract_state(self) -> None:
        self.confirmed_plan_by_step_id = {}
        self.confirmed_plan_step_ids = []
        self.confirmed_child_results_by_step_id = {}
        self.confirmed_execution_mismatch_count_by_step_id = {}

    def _clear_active_plan_correction_state(self) -> None:
        self._active_plan_correction_state = None
        self._plan_correction_pending = False

    def _clear_active_plan_state(self) -> None:
        self._active_plan_state = None
        self._clear_active_plan_correction_state()

    def _record_plan_diff_editor_telemetry(self, **payload: Any) -> None:
        self._plan_diff_editor_telemetry.append(dict(payload))

    def _validate_plan_diff_editor_output(self, **payload: Any) -> dict[str, Any]:
        raw_output = payload.get("raw_output") or payload.get("output") or payload.get("response")
        if isinstance(raw_output, str):
            try:
                parsed_output = json.loads(raw_output)
            except json.JSONDecodeError:
                return {
                    "ok": False,
                    "validation_status": "invalid",
                    "errors": ["invalid_json"],
                    "parsed_output": None,
                }
        elif isinstance(raw_output, dict):
            parsed_output = dict(raw_output)
        elif hasattr(raw_output, "__dict__"):
            parsed_output = dict(vars(raw_output))
        else:
            return {
                "ok": False,
                "validation_status": "invalid",
                "errors": ["unsupported_output"],
                "parsed_output": None,
            }

        if not isinstance(parsed_output, dict):
            return {
                "ok": False,
                "validation_status": "invalid",
                "errors": ["invalid_output"],
                "parsed_output": None,
            }

        errors: list[str] = []
        required_text_fields = (
            "schema_id",
            "purpose",
            "correction_intent",
            "target_plan_id",
        )
        for field_name in required_text_fields:
            if str(parsed_output.get(field_name) or "").strip() == "":
                errors.append(field_name)

        target_plan_version = parsed_output.get("target_plan_version")
        if not isinstance(target_plan_version, int):
            errors.append("target_plan_version")

        if str(parsed_output.get("schema_id") or "").strip() != "plan_diff_editor.v1":
            errors.append("schema_id")
        if str(parsed_output.get("purpose") or "").strip() != "plan_diff_editor":
            errors.append("purpose")
        if not isinstance(parsed_output.get("operations"), list) or not parsed_output.get("operations"):
            errors.append("operations")
        if not isinstance(parsed_output.get("requires_user_clarification"), bool) or parsed_output.get("requires_user_clarification") is not False:
            errors.append("requires_user_clarification")

        if errors:
            return {
                "ok": False,
                "validation_status": "invalid",
                "errors": errors,
                "parsed_output": None,
            }

        return {
            "ok": True,
            "validation_status": "valid",
            "errors": [],
            "parsed_output": parsed_output,
        }

    async def _call_plan_diff_editor_controller(
        self,
        *,
        messages: list[dict[str, Any]],
        phase: str | None,
        context_mode: str = "normal",
    ) -> dict[str, Any]:
        controller = getattr(self, "_plan_diff_editor_controller", None)
        call = getattr(controller, "call", None) if controller is not None else None
        if not callable(call):
            return {"used_controller": False}

        try:
            result = await call(
                purpose="plan_diff_editor",
                messages=messages,
                phase=phase,
                context_mode=context_mode,
                client=self.llm.client,
                tools=[],
                tool_choice=None,
            )
        except Exception as exc:  # noqa: BLE001
            return {
                "used_controller": True,
                "validation_status": "retry_failed",
                "parsed_output": None,
                "errors": [type(exc).__name__],
                "message": str(exc),
            }
        if not isinstance(result, dict):
            return {
                "used_controller": True,
                "validation_status": "retry_failed",
                "parsed_output": None,
                "errors": ["invalid_controller_result"],
            }
        result = dict(result)
        result["used_controller"] = True
        return result

    async def _call_step_plan_normalizer_controller(
        self,
        *,
        messages: list[dict[str, Any]],
        phase: str | None,
        context_mode: str,
        tools: list[dict[str, Any]],
        tool_choice: Any,
    ) -> dict[str, Any]:
        controller = getattr(self, "_llm_runtime_controller", None)
        if controller is None:
            controller = getattr(self, "_plan_diff_editor_controller", None)
        call = getattr(controller, "call_with_raw_response", None) if controller is not None else None
        if not callable(call):
            return {"used_controller": False}

        try:
            result = await call(
                purpose="step_plan_normalizer",
                messages=messages,
                phase=phase,
                context_mode=context_mode,
                client=self.llm.client,
                tools=tools,
                tool_choice=tool_choice,
            )
        except Exception as exc:  # noqa: BLE001
            return {
                "used_controller": True,
                "validation_status": "retry_failed",
                "parsed_output": None,
                "errors": [type(exc).__name__],
                "message": str(exc),
                "raw_response": None,
            }
        if not isinstance(result, dict):
            return {
                "used_controller": True,
                "validation_status": "retry_failed",
                "parsed_output": None,
                "errors": ["invalid_controller_result"],
                "raw_response": None,
            }
        result = dict(result)
        result["used_controller"] = True
        return result

    async def _call_recovery_diagnoser_controller(
        self,
        *,
        messages: list[dict[str, Any]],
        phase: str | None,
        context_mode: str,
        tools: list[dict[str, Any]],
        tool_choice: Any,
    ) -> dict[str, Any]:
        controller = getattr(self, "_llm_runtime_controller", None)
        if controller is None:
            controller = getattr(self, "_plan_diff_editor_controller", None)
        call = getattr(controller, "call_with_raw_response", None) if controller is not None else None
        if not callable(call):
            return {"used_controller": False}

        try:
            result = await call(
                purpose="recovery_diagnoser",
                messages=messages,
                phase=phase,
                context_mode=context_mode,
                client=self.llm.client,
                tools=tools,
                tool_choice=tool_choice,
            )
        except Exception as exc:  # noqa: BLE001
            return {
                "used_controller": True,
                "validation_status": "retry_failed",
                "parsed_output": None,
                "errors": [type(exc).__name__],
                "message": str(exc),
                "raw_response": None,
            }
        if not isinstance(result, dict):
            return {
                "used_controller": True,
                "validation_status": "retry_failed",
                "parsed_output": None,
                "errors": ["invalid_controller_result"],
                "raw_response": None,
            }
        result = dict(result)
        result["used_controller"] = True
        return result

    def _sync_controller_prompt_pack_telemetry(
        self,
        telemetry: Any,
        controller_result: dict[str, Any] | None,
    ) -> None:
        if telemetry is None or not isinstance(controller_result, dict):
            return

        field_map = (
            ("prompt_pack_id", "prompt_pack_id"),
            ("prompt_pack_version", "prompt_pack_version"),
            ("prefix_hash", "prefix_hash"),
            ("system_prompt_tokens", "system_prompt_tokens"),
            ("estimated_message_tokens", "estimated_message_tokens"),
            ("estimated_total_input_tokens", "estimated_input_tokens"),
        )
        for telemetry_field, result_field in field_map:
            value = controller_result.get(result_field)
            if value is not None:
                try:
                    setattr(telemetry, telemetry_field, value)
                except Exception:  # noqa: BLE001
                    continue

    async def _run_plan_diff_editor_correction(
        self,
        *,
        messages: list[dict[str, Any]],
        phase: str | None,
        context_mode: str = "normal",
    ) -> dict[str, Any]:
        controller_messages = list(messages)
        correction_context_message = self._build_plan_correction_context_message()
        if correction_context_message:
            controller_messages.append({"role": "user", "content": correction_context_message})
        schema_message = self._build_plan_diff_editor_schema_message()
        if schema_message:
            controller_messages.append({"role": "system", "content": schema_message})
        controller_context_mode = "normal" if context_mode == "compact" else context_mode
        controller_result = await self._call_plan_diff_editor_controller(
            messages=controller_messages,
            phase=phase,
            context_mode=controller_context_mode,
        )
        if not controller_result.get("used_controller"):
            return controller_result

        validation_status = str(
            controller_result.get("validation_status")
            or controller_result.get("status")
            or controller_result.get("result")
            or ""
        ).strip()
        parsed_output = controller_result.get("parsed_output")
        if validation_status != "valid" or not isinstance(parsed_output, dict):
            controller = getattr(self, "_plan_diff_editor_controller", None)
            if isinstance(controller, LLMRuntimeController):
                synthesized_output = self._synthesize_plan_diff_editor_output()
                if synthesized_output:
                    overlay_result = await self._tool_send_to_overlay(
                        {
                            "message_type": "plan_correction_diff",
                            "payload": synthesized_output,
                        }
                    )
                    if isinstance(overlay_result, dict):
                        result = dict(controller_result)
                        result["validation_status"] = "valid"
                        result["status"] = "valid"
                        result["result"] = "valid"
                        result["parsed_output"] = synthesized_output
                        result["fallback_used"] = True
                        result["overlay_result"] = dict(overlay_result)
                        result.update(dict(overlay_result))
                        result["used_controller"] = True
                        return result
            return controller_result

        result = dict(controller_result)
        overlay_result = await self._tool_send_to_overlay(
            {
                "message_type": "plan_correction_diff",
                "payload": parsed_output,
            }
        )
        if isinstance(overlay_result, dict):
            result.update(dict(overlay_result))
            result["overlay_result"] = dict(overlay_result)
        else:
            result["overlay_result"] = overlay_result
        result["used_controller"] = True
        return result

    def _current_active_plan_state(self) -> dict[str, Any] | None:
        active_plan_state = getattr(self, "_active_plan_state", None)
        if isinstance(active_plan_state, dict):
            return active_plan_state
        return None

    def _current_plan_version(self) -> int:
        candidates: list[Any] = []

        active_plan_state = self._current_active_plan_state()
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

        last_plan_ready_payload = getattr(self, "last_plan_ready_payload", None)
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

    def _confirmation_context(self, payload: dict[str, Any] | None) -> dict[str, str]:
        if not isinstance(payload, dict):
            return {}

        context: dict[str, str] = {}
        for key, alt_key in (("run_id", "runId"), ("plan_id", "planId"), ("plan_version", "planVersion")):
            value = str(payload.get(key) or payload.get(alt_key) or "").strip()
            if value:
                context[key] = value
        return context

    def _confirmation_context_mismatch_reason(
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

    def _completed_run_confirmation_rejection_reason(self, event_context: dict[str, str] | None) -> str | None:
        event_context_data = event_context if isinstance(event_context, dict) else {}
        run_id = str(event_context_data.get("run_id") or "").strip()
        if not run_id:
            return None
        if self._current_phase() != "completed" and not getattr(self, "_run_completed_emitted", False):
            return None
        return "completed run is already closed"

    def _plan_steps_from_state(self, plan_state: dict[str, Any] | None) -> list[dict[str, Any]]:
        if not isinstance(plan_state, dict):
            return []
        steps = plan_state.get("steps")
        if not isinstance(steps, list):
            return []
        return [step for step in steps if isinstance(step, dict)]

    def _plan_child_operations_from_step(self, step: dict[str, Any]) -> list[dict[str, Any]]:
        if not isinstance(step, dict):
            return []
        children = step.get("children")
        if isinstance(children, list) and children:
            return [child for child in children if isinstance(child, dict)]
        return [step]

    def _plan_operation_text(self, operation: dict[str, Any] | None) -> str:
        if not isinstance(operation, dict):
            return ""
        return self._normalize_space(
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

    def _plan_operation_type(self, operation: dict[str, Any] | None) -> str:
        if not isinstance(operation, dict):
            return ""
        return self._normalize_space(str(operation.get("type") or operation.get("action") or "")).lower()

    def _plan_operation_signature(self, operation: dict[str, Any] | None) -> str:
        if not isinstance(operation, dict):
            return ""
        operation_type = self._plan_operation_type(operation)
        target_text = self._normalize_space(self._plan_operation_text(operation)).lower()
        locator_text = self._normalize_space(str(operation.get("locator") or "")).lower()
        if not operation_type and not target_text and not locator_text:
            return ""
        if locator_text:
            return f"{operation_type}|{target_text}|{locator_text}"
        return f"{operation_type}|{target_text}"

    def _plan_operation_types_from_state(self, plan_state: dict[str, Any] | None) -> list[str]:
        operation_types: list[str] = []
        for step in self._plan_steps_from_state(plan_state):
            for operation in self._plan_child_operations_from_step(step):
                operation_type = self._plan_operation_type(operation)
                if operation_type:
                    operation_types.append(operation_type)
        return operation_types

    def _plan_operation_signatures_from_state(self, plan_state: dict[str, Any] | None) -> list[str]:
        operation_signatures: list[str] = []
        for step in self._plan_steps_from_state(plan_state):
            for operation in self._plan_child_operations_from_step(step):
                operation_signature = self._plan_operation_signature(operation)
                if operation_signature:
                    operation_signatures.append(operation_signature)
        return operation_signatures

    def _sequence_contains_subsequence(self, sequence: list[str], subsequence: list[str]) -> bool:
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

    def _build_active_plan_state(
        self,
        payload: dict[str, Any],
        source_plan_state: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        active_plan_state = deepcopy(payload) if isinstance(payload, dict) else {}
        plan_id = str(
            active_plan_state.get("plan_id")
            or active_plan_state.get("planId")
            or active_plan_state.get("id")
            or f"plan-{uuid4().hex}"
        ).strip()
        active_plan_state["plan_id"] = plan_id

        summary = self._normalize_space(str(active_plan_state.get("summary") or "")).strip() or None
        if summary is None:
            if isinstance(source_plan_state, dict):
                summary = self._normalize_space(str(source_plan_state.get("summary") or "")).strip() or None
            if summary is None:
                summary = self.last_plan_summary
        active_plan_state["summary"] = summary

        original_user_intent = self._normalize_space(str(active_plan_state.get("original_user_intent") or "")).strip() or None
        if original_user_intent is None:
            if isinstance(source_plan_state, dict):
                original_user_intent = self._normalize_space(
                    str(source_plan_state.get("original_user_intent") or "")
                ).strip() or None
            if original_user_intent is None:
                original_user_intent = self.last_plan_original_user_intent
        active_plan_state["original_user_intent"] = original_user_intent

        run_id = str(
            active_plan_state.get("run_id")
            or active_plan_state.get("runId")
            or (source_plan_state or {}).get("run_id")
            or (source_plan_state or {}).get("runId")
            or getattr(self, "session_id", None)
            or getattr(self, "_run_session_id", None)
            or ""
        ).strip()
        if run_id:
            active_plan_state["run_id"] = run_id

        steps = self._plan_steps_from_state(active_plan_state)
        active_plan_state["steps"] = steps
        active_plan_state["step_ids"] = [
            str(step.get("step_id") or step.get("id") or "").strip()
            for step in steps
            if str(step.get("step_id") or step.get("id") or "").strip()
        ]
        active_plan_state["target_step_id"] = active_plan_state["step_ids"][0] if active_plan_state["step_ids"] else None
        active_plan_state["source_payload"] = deepcopy(payload) if isinstance(payload, dict) else {}
        return active_plan_state

    def _infer_confirmed_execution_child_assertion(
        self,
        child: dict[str, Any] | None,
        source_step: dict[str, Any] | None = None,
    ) -> str:
        child_data = child if isinstance(child, dict) else {}
        assertion = self._normalize_space(str(child_data.get("assertion") or "")).strip().lower()
        if assertion:
            return assertion

        child_type = self._normalize_space(str(child_data.get("type") or child_data.get("action") or "")).strip().lower()
        if child_type != "assert":
            return ""

        canonical_child = self._canonicalize_assertion_operation(child_data, source_step=source_step)
        canonical_assertion = self._normalize_space(
            str(canonical_child.get("assertion") or "")
        ).strip().lower()
        if canonical_assertion:
            return canonical_assertion

        description = self._normalize_space(str(child_data.get("description") or "")).strip().lower()
        target = self._normalize_space(
            str(child_data.get("target") or child_data.get("element_name") or "")
        ).strip().lower()
        source_intent = self._normalize_space(str((source_step or {}).get("intent") or "")).strip().lower()
        hint_text = " ".join(part for part in (description, target, source_intent) if part).strip()

        for keyword in ("visible", "hidden", "enabled", "disabled", "checked"):
            if re.search(rf"\b{keyword}\b", hint_text):
                return keyword

        if "has text" in hint_text or "contains text" in hint_text:
            return "has_text"
        if "has value" in hint_text:
            return "has_value"

        return "visible"

    def _normalize_confirmed_execution_child(
        self,
        child: dict[str, Any] | None,
        source_step: dict[str, Any] | None = None,
        child_index: int = 1,
    ) -> dict[str, Any]:
        child_data = child if isinstance(child, dict) else {}
        operation_id = str(child_data.get("operation_id") or child_data.get("operationId") or "").strip()
        if not operation_id:
            operation_id = f"op_{child_index}"

        child_type = self._normalize_space(str(child_data.get("type") or child_data.get("action") or "")).strip().lower()
        target = self._select_plan_correction_child_target(
            [
                ("child.target", child_data.get("target")),
                ("child.element_name", child_data.get("element_name")),
                ("child.label", child_data.get("label")),
                ("child.description", child_data.get("description")),
                ("source.element_name", (source_step or {}).get("element_name")),
                ("source.intent", (source_step or {}).get("intent")),
            ]
        )
        locator = self._normalize_space(str(child_data.get("locator") or "")).strip()
        if not locator and isinstance(source_step, dict):
            locator = self._normalize_space(str(source_step.get("locator") or "")).strip()
            if not locator:
                locator = self._derive_locator_from_step_context(source_step)
        if locator in {"*", 'page.locator("")'}:
            locator = ""

        assertion = self._infer_confirmed_execution_child_assertion(child_data, source_step=source_step)
        value_text = self._normalize_space(
            str(child_data.get("value") or child_data.get("expected_value") or "")
        ).strip()
        description = self._normalize_space(str(child_data.get("description") or "")).strip()
        if child_type == "assert":
            canonical_child = self._canonicalize_assertion_operation(
                child_data,
                source_step=source_step,
            )
            if canonical_child:
                target = str(canonical_child.get("target") or target or "").strip()
                locator = str(canonical_child.get("locator") or locator or "").strip()
                assertion = str(canonical_child.get("assertion") or assertion or "").strip().lower()
                value_text = str(
                    canonical_child.get("value") or canonical_child.get("expected_value") or value_text or ""
                ).strip()
                canonical_description = str(canonical_child.get("description") or "").strip()
                if canonical_description:
                    description = canonical_description
        if child_type == "assert" and assertion == "visible":
            locator_target_hint = self._normalize_space(self._locator_label_hint(locator)).strip()
            if locator_target_hint and not self._is_outcome_like_label(locator_target_hint):
                if locator_target_hint.lower() not in {"main", "page", "body", "document"}:
                    target = locator_target_hint
        if not description:
            description = self._build_plan_correction_child_description(
                child_type or self._infer_operation_type(target),
                target,
                assertion,
                value_text,
                str(child_data.get("description") or ""),
                str((source_step or {}).get("intent") or target or "").strip(),
            )
        code_lines: list[str] = []
        child_code_lines = child_data.get("code_lines")
        if isinstance(child_code_lines, list):
            for code_line in child_code_lines:
                line_text = str(code_line or "").strip()
                if line_text:
                    code_lines.append(line_text)
        if not code_lines:
            child_code = self._normalize_space(str(child_data.get("code") or "")).strip()
            if child_code:
                code_lines.append(child_code)

        normalized_child: dict[str, Any] = {
            "operation_id": operation_id,
            "type": child_type or "unknown",
            "description": description or target or child_type or "child",
            "target": target,
            "locator": locator,
            "status": self._normalize_space(str(child_data.get("status") or "planned")).strip().lower() or "planned",
        }
        if assertion:
            normalized_child["assertion"] = assertion
        if value_text:
            normalized_child["value"] = value_text
            normalized_child.setdefault("expected_value", value_text)
        if code_lines:
            normalized_child["code_lines"] = code_lines
        return normalized_child

    def _build_confirmed_execution_plan(
        self,
        payload: dict[str, Any],
        source_plan_state: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        confirmed_plan = deepcopy(payload) if isinstance(payload, dict) else {}
        source_plan = source_plan_state if isinstance(source_plan_state, dict) else self._current_active_plan_state()
        source_steps = self._plan_steps_from_state(source_plan)
        source_steps_by_id: dict[str, dict[str, Any]] = {}
        for index, source_step in enumerate(source_steps, start=1):
            if not isinstance(source_step, dict):
                continue
            source_step_id = str(source_step.get("step_id") or source_step.get("id") or "").strip()
            if source_step_id:
                source_steps_by_id[source_step_id] = source_step
            if index == 1 and "1" not in source_steps_by_id:
                source_steps_by_id["1"] = source_step

        confirmed_steps = self._plan_steps_from_state(confirmed_plan)
        confirmed_plan_by_step_id: dict[str, dict[str, Any]] = {}
        confirmed_step_ids: list[str] = []
        confirmed_child_results_by_step_id: dict[str, dict[str, Any]] = {}
        confirmed_execution_mismatch_count_by_step_id: dict[str, int] = {}

        for index, confirmed_step in enumerate(confirmed_steps, start=1):
            if not isinstance(confirmed_step, dict):
                continue

            source_step = source_steps_by_id.get(str(confirmed_step.get("step_id") or confirmed_step.get("id") or "").strip())
            if source_step is None and index - 1 < len(source_steps):
                source_candidate = source_steps[index - 1]
                if isinstance(source_candidate, dict):
                    source_step = source_candidate

            normalized_step = dict(confirmed_step)
            step_id = str(
                normalized_step.get("step_id")
                or normalized_step.get("id")
                or (source_step or {}).get("step_id")
                or (source_step or {}).get("id")
                or index
            ).strip() or str(index)
            step_number = (
                self._coerce_step_number(normalized_step.get("step_number"))
                or self._coerce_step_number(normalized_step.get("number"))
                or self._coerce_step_number((source_step or {}).get("step_number"))
                or index
            )
            parent_intent = self._normalize_space(
                str(
                    normalized_step.get("intent")
                    or normalized_step.get("title")
                    or normalized_step.get("text")
                    or normalized_step.get("label")
                    or (source_step or {}).get("intent")
                    or ""
                )
            ).strip()
            expected_outcome = self._normalize_expected_outcome(
                normalized_step.get("expected_outcome")
                or normalized_step.get("expectedOutcome")
                or (source_step or {}).get("expected_outcome")
                or (source_step or {}).get("expectedOutcome"),
                self._is_click_like_intent(parent_intent),
            )
            normalized_children: list[dict[str, Any]] = []
            children = normalized_step.get("children")
            if not isinstance(children, list):
                children = []
            for child_index, child in enumerate(children, start=1):
                normalized_children.append(
                    self._normalize_confirmed_execution_child(
                        child if isinstance(child, dict) else {},
                        source_step=source_step,
                        child_index=child_index,
                    )
                )

            confirmed_plan_by_step_id[step_id] = {
                "step_id": step_id,
                "step_number": step_number,
                "parent_intent": parent_intent,
                "expected_outcome": expected_outcome,
                "children": normalized_children,
                "plan_id": str(confirmed_plan.get("plan_id") or "").strip() or None,
                "summary": str(confirmed_plan.get("summary") or "").strip() or None,
                "original_user_intent": str(confirmed_plan.get("original_user_intent") or "").strip() or None,
            }
            if isinstance(source_step, dict) and source_step.get("element_info") is not None:
                confirmed_plan_by_step_id[step_id]["element_info"] = deepcopy(source_step.get("element_info"))
            confirmed_step_ids.append(step_id)
            confirmed_child_results_by_step_id[step_id] = {}
            confirmed_execution_mismatch_count_by_step_id[step_id] = 0

        confirmed_plan["steps"] = [confirmed_plan_by_step_id[step_id] for step_id in confirmed_step_ids]
        if str(confirmed_plan.get("plan_id") or "").strip() == "":
            confirmed_plan["plan_id"] = str((source_plan or {}).get("plan_id") or "").strip() or None
        if str(confirmed_plan.get("summary") or "").strip() == "":
            confirmed_plan["summary"] = str((source_plan or {}).get("summary") or "").strip() or None
        if str(confirmed_plan.get("original_user_intent") or "").strip() == "":
            confirmed_plan["original_user_intent"] = str((source_plan or {}).get("original_user_intent") or "").strip() or None
        confirmed_plan["step_ids"] = list(confirmed_step_ids)
        confirmed_plan["target_step_id"] = confirmed_step_ids[0] if confirmed_step_ids else None

        self.confirmed_plan_by_step_id = confirmed_plan_by_step_id
        self.confirmed_plan_step_ids = confirmed_step_ids
        self.confirmed_child_results_by_step_id = confirmed_child_results_by_step_id
        self.confirmed_execution_mismatch_count_by_step_id = confirmed_execution_mismatch_count_by_step_id
        return confirmed_plan

    def _store_confirmed_execution_plan(self, payload: dict[str, Any]) -> dict[str, Any]:
        confirmed_plan = self._build_confirmed_execution_plan(
            payload,
            source_plan_state=self._current_active_plan_state(),
        )
        step_count = len(self.confirmed_plan_step_ids)
        print(
            "[CONFIRMED_PLAN] stored "
            f"plan_id={str(confirmed_plan.get('plan_id') or '').strip() or 'unknown'} "
            f"steps={step_count}"
        )
        for step_id in self.confirmed_plan_step_ids:
            contract = self.confirmed_plan_by_step_id.get(step_id) or {}
            print(
                "[CONFIRMED_PLAN] "
                f"stored step_id={step_id} "
                f"step_number={contract.get('step_number') or 'unknown'} "
                f"children={len(contract.get('children') or [])}"
            )
        return confirmed_plan

    def _current_confirmed_execution_cursor(self) -> dict[str, Any] | None:
        confirmed_plan_by_step_id = getattr(self, "confirmed_plan_by_step_id", None)
        if not isinstance(confirmed_plan_by_step_id, dict) or not confirmed_plan_by_step_id:
            return None

        confirmed_step_ids = getattr(self, "confirmed_plan_step_ids", None)
        if not isinstance(confirmed_step_ids, list) or not confirmed_step_ids:
            confirmed_step_ids = list(confirmed_plan_by_step_id.keys())

        recorded_step_ids = getattr(self, "_recorded_step_ids", set())
        skipped_step_ids = getattr(self, "skipped_step_ids", set())

        for candidate_step_id in confirmed_step_ids:
            resolved_candidate_step_id = str(candidate_step_id or "").strip()
            if not resolved_candidate_step_id:
                continue

            contract = confirmed_plan_by_step_id.get(resolved_candidate_step_id)
            if not isinstance(contract, dict):
                continue

            step_context = self.step_state_by_id.get(resolved_candidate_step_id)
            if not isinstance(step_context, dict):
                step_context = contract

            step_status = str(step_context.get("status") or "").strip().lower()
            if (
                step_status in {"recorded", "skipped"}
                or resolved_candidate_step_id in recorded_step_ids
                or resolved_candidate_step_id in skipped_step_ids
            ):
                continue

            current_contract, next_child, next_child_result = self._confirmed_execution_next_child_for_step(
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

    def _log_confirmed_execution_cursor(self, prefix: str) -> None:
        confirmed_cursor = self._current_confirmed_execution_cursor()
        if not isinstance(confirmed_cursor, dict):
            return

        current_contract = confirmed_cursor.get("contract")
        if not isinstance(current_contract, dict):
            current_contract = {}
        current_step_id = str(confirmed_cursor.get("step_id") or "").strip() or "unknown"
        current_step_number = self._coerce_step_number(current_contract.get("step_number"))
        next_child = confirmed_cursor.get("next_child")
        next_child_description = (
            self._describe_confirmed_execution_child(next_child) if isinstance(next_child, dict) else "none"
        )
        print(
            f"{prefix} current step_id={current_step_id} "
            f"step_number={current_step_number or 'unknown'} next_child={next_child_description}"
        )

    def _confirmed_execution_contract_for_step(
        self,
        step: dict[str, Any] | str | None = None,
    ) -> dict[str, Any] | None:
        confirmed_plan_by_step_id = getattr(self, "confirmed_plan_by_step_id", None)
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

    def _confirmed_execution_results_for_step(self, step_id: str | None) -> dict[str, Any]:
        confirmed_child_results_by_step_id = getattr(self, "confirmed_child_results_by_step_id", None)
        if not isinstance(confirmed_child_results_by_step_id, dict):
            confirmed_child_results_by_step_id = {}
            self.confirmed_child_results_by_step_id = confirmed_child_results_by_step_id

        resolved_step_id = str(step_id or "").strip()
        if not resolved_step_id:
            return {}

        step_results = confirmed_child_results_by_step_id.get(resolved_step_id)
        if not isinstance(step_results, dict):
            step_results = {}
            confirmed_child_results_by_step_id[resolved_step_id] = step_results
        return step_results

    def _confirmed_execution_next_child_for_step(
        self,
        step: dict[str, Any] | str | None = None,
    ) -> tuple[dict[str, Any] | None, dict[str, Any] | None, dict[str, Any] | None]:
        contract = self._confirmed_execution_contract_for_step(step)
        if not isinstance(contract, dict):
            return None, None, None

        step_id = str(contract.get("step_id") or "").strip()
        step_results = self._confirmed_execution_results_for_step(step_id)
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

    def _confirmed_execution_step_ready_to_record(
        self,
        step: dict[str, Any] | str | None = None,
    ) -> bool:
        confirmed_cursor = self._current_confirmed_execution_cursor()
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

        contract, next_child, _ = self._confirmed_execution_next_child_for_step(confirmed_cursor.get("step_id"))
        return isinstance(contract, dict) and next_child is None

    def _build_confirmed_execution_context_message(self) -> str:
        confirmed_cursor = self._current_confirmed_execution_cursor()
        if not isinstance(confirmed_cursor, dict):
            return ""

        current_contract = confirmed_cursor.get("contract")
        if not isinstance(current_contract, dict):
            return ""

        step_id = str(current_contract.get("step_id") or "").strip()
        step_results = self._confirmed_execution_results_for_step(step_id)
        _, next_child, _ = self._confirmed_execution_next_child_for_step(step_id)

        lines = ["Confirmed execution plan:"]
        step_number = self._coerce_step_number(current_contract.get("step_number"))
        header_parts = [part for part in (step_id, f"step {step_number}" if step_number else "") if part]
        if header_parts:
            lines.append(f'Current step: {" | ".join(header_parts)}')
        parent_intent = self._normalize_space(str(current_contract.get("parent_intent") or "")).strip()
        if parent_intent:
            lines.append(f'Parent intent: "{parent_intent}"')
        expected_outcome_text = self._expected_outcome_summary(current_contract.get("expected_outcome"))
        if expected_outcome_text:
            lines.append(f"Expected outcome: {expected_outcome_text}")
        children = current_contract.get("children")
        if isinstance(children, list) and children:
            lines.append("Children:")
            for index, child in enumerate(children, start=1):
                if not isinstance(child, dict):
                    continue
                operation_id = str(child.get("operation_id") or "").strip() or f"op_{index}"
                child_result = step_results.get(operation_id)
                status = "pending"
                if isinstance(child_result, dict):
                    status = str(child_result.get("status") or "").strip().lower() or "pending"
                    if status == "success":
                        status = "passed"
                    elif status == "blocked":
                        status = "blocked"
                    elif status == "failed":
                        status = "failed"
                elif next_child is not None and operation_id == str(next_child.get("operation_id") or "").strip():
                    status = "next"
                elif index == 1:
                    status = "next"
                child_description = self._describe_confirmed_execution_child(child)
                lines.append(f"{index}. {child_description} [{status}]")
        lines.append("Use these confirmed children in order.")
        lines.append("- Use the confirmed child locator exactly as written.")
        lines.append("- Do not swap a confirmed locator for a different equivalent locator during retries.")
        lines.append("Do not replace them with page.title assertions.")
        lines.append("Do not skip or reorder children.")
        return "\n".join(lines)

    def _locator_matches_confirmed_execution_child(
        self,
        expected_locator: str,
        actual_locator: str,
    ) -> bool:
        expected = self._canonical_confirmed_execution_locator(expected_locator)
        actual = self._canonical_confirmed_execution_locator(actual_locator)
        if not expected:
            return True
        if expected == actual:
            return True

        return False

    def _assertion_matches_confirmed_execution_child(
        self,
        expected_child: dict[str, Any],
        actual_assertion: str,
        actual_args: dict[str, Any],
    ) -> bool:
        expected_assertion = self._normalize_space(
            str(expected_child.get("assertion") or self._infer_confirmed_execution_child_assertion(expected_child) or "")
        ).strip().lower()
        actual_assertion_text = self._normalize_space(str(actual_assertion or "")).strip().lower()
        assertion_aliases = {
            "exact_text": "has_text",
            "text_equal": "has_text",
            "text_equals": "has_text",
            "contains_text": "has_text",
            "includes_text": "has_text",
        }
        expected_assertion = assertion_aliases.get(expected_assertion, expected_assertion)
        actual_assertion_text = assertion_aliases.get(actual_assertion_text, actual_assertion_text)
        if not expected_assertion:
            return True
        if expected_assertion != actual_assertion_text:
            return False

        if expected_assertion in {"has_text", "has_value"}:
            expected_value = self._normalize_space(
                str(expected_child.get("value") or expected_child.get("expected_value") or "")
            ).strip()
            actual_value = self._normalize_space(str(actual_args.get("expected_value") or actual_args.get("value") or "")).strip()
            if expected_value and actual_value and expected_value != actual_value:
                return False

        return True

    def _value_matches_confirmed_execution_child(
        self,
        expected_child: dict[str, Any],
        actual_args: dict[str, Any],
    ) -> bool:
        expected_value = self._normalize_space(
            str(expected_child.get("value") or expected_child.get("expected_value") or "")
        ).strip()
        if not expected_value:
            return True
        actual_value = self._normalize_space(str(actual_args.get("value") or actual_args.get("expected_value") or "")).strip()
        return not actual_value or expected_value == actual_value

    def _describe_confirmed_execution_child(self, child: dict[str, Any] | None) -> str:
        if not isinstance(child, dict):
            return "unknown child"

        operation_id = str(child.get("operation_id") or "").strip() or "child"
        child_type = str(child.get("type") or "").strip() or "unknown"
        target = self._normalize_space(str(child.get("target") or "")).strip()
        locator = self._normalize_space(str(child.get("locator") or "")).strip()
        assertion = self._normalize_space(str(child.get("assertion") or "")).strip().lower()
        value_text = self._normalize_space(str(child.get("value") or child.get("expected_value") or "")).strip()

        parts = [operation_id, child_type]
        if target:
            parts.append(f'target="{target}"')
        if locator:
            parts.append(f'locator="{locator}"')
        if assertion:
            parts.append(f'assertion="{assertion}"')
        if value_text:
            parts.append(f'value="{value_text}"')
        return " ".join(parts)

    def _describe_confirmed_execution_call(self, tool_name: str, args: dict[str, Any]) -> str:
        action = self._action_name_for_tool(tool_name) or tool_name
        locator = self._normalize_space(str(args.get("locator") or "")).strip()
        assertion = self._normalize_space(str(args.get("assertion") or "")).strip().lower()
        value_text = self._normalize_space(str(args.get("value") or args.get("expected_value") or "")).strip()
        parts = [action]
        if locator:
            parts.append(f'locator="{locator}"')
        if assertion:
            parts.append(f'assertion="{assertion}"')
        if value_text:
            parts.append(f'value="{value_text}"')
        return " ".join(parts)

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
        contract = self._confirmed_execution_contract_for_step(step)
        if not isinstance(contract, dict) or not isinstance(child, dict):
            return None

        step_id = str(contract.get("step_id") or "").strip()
        operation_id = str(child.get("operation_id") or "").strip()
        if not step_id or not operation_id:
            return None

        step_results = self._confirmed_execution_results_for_step(step_id)
        child_result = step_results.get(operation_id)
        if not isinstance(child_result, dict):
            child_result = {}
            step_results[operation_id] = child_result

        action = self._action_name_for_tool(tool_name)
        action_context: dict[str, Any] = {
            "locator": self._normalize_space(str(args.get("locator") or result.get("locator") or child.get("locator") or "")).strip(),
        }
        if "assertion" in args:
            action_context["assertion"] = self._normalize_space(str(args.get("assertion") or "")).strip().lower()
        if "value" in args:
            action_context["value"] = args.get("value")
        if "expected_value" in args:
            action_context["expected_value"] = args.get("expected_value")
        if "url" in args:
            action_context["url"] = self._normalize_space(str(args.get("url") or "")).strip()
        if "wait_until" in args:
            action_context["wait_until"] = self._normalize_space(str(args.get("wait_until") or "")).strip()
        if "filename" in args:
            action_context["filename"] = self._normalize_space(str(args.get("filename") or "")).strip()
        if result.get("url") and not action_context.get("url"):
            action_context["url"] = self._normalize_space(str(result.get("url") or "")).strip()

        child_result.update(
            {
                "operation_id": operation_id,
                "step_id": step_id,
                "step_number": contract.get("step_number"),
                "type": child.get("type") or "unknown",
                "target": child.get("target") or "",
                "locator": child.get("locator") or action_context.get("locator") or "",
                "assertion": child.get("assertion") or action_context.get("assertion") or "",
                "value": child.get("value") or child.get("expected_value") or action_context.get("value") or action_context.get("expected_value") or "",
                "status": status,
                "tool": tool_name,
                "action": action,
                "action_context": action_context,
                "tool_args": dict(args),
                "result": dict(result),
                "step_context": dict(step) if isinstance(step, dict) else None,
            }
        )

        if browser_state_before is not None:
            child_result["browser_state_before"] = self._normalize_browser_state_snapshot(browser_state_before)
        if browser_state_after is not None:
            child_result["browser_state_after"] = self._normalize_browser_state_snapshot(browser_state_after)

        attempts = child_result.get("attempts")
        if not isinstance(attempts, list):
            attempts = []
        attempt: dict[str, Any] = {
            "status": status,
            "tool": tool_name,
            "action": action,
            "tool_args": dict(args),
            "result": dict(result),
        }
        if action_context:
            attempt["action_context"] = dict(action_context)
        if browser_state_before is not None:
            attempt["browser_state_before"] = self._normalize_browser_state_snapshot(browser_state_before)
        if browser_state_after is not None:
            attempt["browser_state_after"] = self._normalize_browser_state_snapshot(browser_state_after)
        error_text = str(result.get("error") or result.get("message") or "").strip()
        if error_text:
            attempt["error"] = error_text
            child_result["error"] = error_text
        if status == "blocked":
            child_result["blocked"] = True
        elif status == "failed":
            child_result["blocked"] = False
        attempts.append(attempt)
        child_result["attempts"] = attempts
        child_result["attempt_count"] = len(attempts)

        if status == "success":
            generated_line = self._build_generated_line(action or child_result.get("type") or "", str(child_result.get("locator") or ""), action_context)
            if generated_line:
                child_result["generated_line"] = generated_line
                child_result["code_lines"] = [generated_line]
            else:
                child_result["code_lines"] = list(child_result.get("code_lines") or [])
            mismatch_counts = getattr(self, "confirmed_execution_mismatch_count_by_step_id", None)
            if not isinstance(mismatch_counts, dict):
                mismatch_counts = {}
                self.confirmed_execution_mismatch_count_by_step_id = mismatch_counts
            mismatch_counts[step_id] = 0
        else:
            child_result["code_lines"] = list(child_result.get("code_lines") or [])

        step_results[operation_id] = child_result
        return child_result

    def _validate_confirmed_execution_tool_call(
        self,
        tool_name: str,
        args: dict[str, Any],
        result: dict[str, Any] | None = None,
    ) -> dict[str, Any] | None:
        if tool_name not in self.EXECUTION_TOOLS:
            return None

        confirmed_cursor = self._current_confirmed_execution_cursor()
        if not isinstance(confirmed_cursor, dict):
            return None

        step_context = confirmed_cursor.get("step_context")
        contract = confirmed_cursor.get("contract")
        expected_child = confirmed_cursor.get("next_child")
        expected_child_result = confirmed_cursor.get("next_child_result")
        if not isinstance(contract, dict):
            return None

        step_id = str(contract.get("step_id") or "").strip()
        if not step_id or not isinstance(expected_child, dict):
            return None

        expected_description = self._describe_confirmed_execution_child(expected_child)
        actual_description = self._describe_confirmed_execution_call(tool_name, args)
        expected_tool = str(expected_child.get("type") or "").strip().lower()
        actual_tool = self._action_name_for_tool(tool_name)
        actual_locator = str(args.get("locator") or (result or {}).get("locator") or "").strip()
        expected_locator = str(expected_child.get("locator") or "").strip()
        actual_assertion = self._normalize_space(str(args.get("assertion") or (result or {}).get("assertion") or "")).strip().lower()
        expected_assertion = self._normalize_space(
            str(expected_child.get("assertion") or self._infer_confirmed_execution_child_assertion(expected_child, source_step=step_context) or "")
        ).strip().lower()
        actual_value = self._normalize_space(str(args.get("value") or args.get("expected_value") or "")).strip()
        expected_value = self._normalize_space(
            str(expected_child.get("value") or expected_child.get("expected_value") or "")
        ).strip()

        self._log_confirmed_execution_cursor("[CONFIRMED_CURSOR]")
        print(f"[EXECUTION_CONTRACT] expected step_id={step_id} op={expected_tool} actual={actual_tool}")

        expected_tool_name = {
            "assert": "action_assert",
            "click": "action_click",
            "fill": "action_fill",
        }.get(expected_tool)
        if expected_tool_name is None:
            return {
                "allowed": False,
                "blocked": True,
                "skipped": True,
                "reason": "execution_contract_unsupported",
                "message": (
                    "Execution blocked: confirmed plan child type "
                    f"{expected_tool!r} is not supported by the execution contract."
                ),
                "requires_replan": False,
                "step_id": step_id,
                "expected_child": deepcopy(expected_child),
                "actual_tool": tool_name,
                "actual_description": actual_description,
                "terminal": True,
            }

        locator_matches = self._locator_matches_confirmed_execution_child(expected_locator, actual_locator)
        assertion_matches = self._assertion_matches_confirmed_execution_child(expected_child, actual_assertion, args)
        value_matches = self._value_matches_confirmed_execution_child(expected_child, args)
        tool_matches = expected_tool_name == tool_name
        allowed = tool_matches and locator_matches and assertion_matches and value_matches

        print(
            "[EXECUTION_CONTRACT] expected "
            f"{expected_description} actual={actual_description}"
        )
        if allowed:
            return {
                "allowed": True,
                "step_id": step_id,
                "expected_child": deepcopy(expected_child),
            }

        mismatch_counts = getattr(self, "confirmed_execution_mismatch_count_by_step_id", None)
        if not isinstance(mismatch_counts, dict):
            mismatch_counts = {}
            self.confirmed_execution_mismatch_count_by_step_id = mismatch_counts
        mismatch_count = int(mismatch_counts.get(step_id) or 0) + 1
        mismatch_counts[step_id] = mismatch_count
        terminal = mismatch_count >= 2
        if not terminal and isinstance(expected_child_result, dict):
            expected_child_result.setdefault("status", "pending")
        message = (
            "Execution blocked: confirmed plan expected "
            f"{expected_description}, but model tried {actual_description}."
        )
        if terminal:
            message = (
                f"{message} Execution contract violated twice for step {step_id}. "
                "Failing closed."
            )
        print(f"[EXECUTION_CONTRACT] blocked mismatch step_id={step_id} expected={expected_tool} actual={actual_tool}")
        return {
            "allowed": False,
            "blocked": True,
            "skipped": True,
            "reason": "execution_contract_mismatch",
            "message": message,
            "requires_replan": False,
            "step_id": step_id,
            "expected_child": deepcopy(expected_child),
            "actual_tool": tool_name,
            "actual_description": actual_description,
            "actual_locator": actual_locator,
            "actual_assertion": actual_assertion,
            "actual_value": actual_value,
            "expected_locator": expected_locator,
            "expected_assertion": expected_assertion,
            "expected_value": expected_value,
            "terminal": terminal,
        }

    def _classify_plan_correction(
        self,
        correction: str,
        active_plan_state: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        normalized = self._normalize_space(correction).lower()
        ordered_types = self._infer_planned_operation_sequence(normalized)
        active_operation_count = len(self._plan_operation_signatures_from_state(active_plan_state))

        explicit_remove = any(
            marker in normalized
            for marker in (
                "don't",
                "do not",
                "remove",
                "only",
                "no need",
                "skip",
                "without",
            )
        )
        explicit_order = any(
            marker in normalized
            for marker in (
                " first",
                " then",
                " before",
                " after",
                " order",
                " next",
                "swap",
                "reverse",
            )
        )
        explicit_replace = any(
            marker in normalized
            for marker in (
                "replace",
                "instead of",
                "instead",
                "swap",
                "change it to",
            )
        )
        explicit_target_change = any(
            marker in normalized
            for marker in (
                "use the",
                "switch",
                "header button",
                "button",
                "link",
                "target",
                "selector",
                "locator",
            )
        )
        explicit_expected_outcome = any(
            marker in normalized
            for marker in (
                "should open",
                "should show",
                "should navigate",
                "expected",
                "modal",
                "new tab",
                "visible",
                "hidden",
                "enabled",
                "disabled",
            )
        )
        explicit_split_merge = any(marker in normalized for marker in ("split", "merge"))
        explicit_add = any(
            marker in normalized
            for marker in (
                "add",
                "also",
                "check",
                "verify",
                "validate",
                "ensure",
            )
        )
        if not explicit_add and "assert" in normalized and not explicit_remove:
            explicit_add = True

        category = "ambiguous"
        if not normalized:
            category = "ambiguous"
        elif explicit_split_merge:
            if "split" in normalized and "merge" not in normalized:
                category = "split_step"
            elif "merge" in normalized and "split" not in normalized:
                category = "merge_steps"
            else:
                category = "ambiguous"
        elif explicit_replace:
            category = "replace_operation"
        elif explicit_target_change and not explicit_add and not explicit_remove and not explicit_order:
            category = "change_target"
        elif explicit_expected_outcome and not explicit_add and not explicit_remove and not explicit_order:
            category = "change_expected_outcome"
        elif explicit_order and len(ordered_types) > 1:
            if active_operation_count > 0 and len(ordered_types) > active_operation_count:
                category = "add_and_reorder_operations"
            else:
                category = "reorder_operations"
        elif explicit_add and not explicit_remove:
            category = "add_operation"
        elif explicit_remove and not explicit_add:
            category = "remove_operation"
        elif ordered_types and active_operation_count == len(ordered_types) and ordered_types != self._plan_operation_types_from_state(active_plan_state):
            category = "reorder_operations"

        return {
            "category": category,
            "ordered_types": ordered_types,
            "explicit_add": explicit_add,
            "explicit_remove": explicit_remove,
            "explicit_order": explicit_order,
            "explicit_replace": explicit_replace,
            "explicit_target_change": explicit_target_change,
            "explicit_expected_outcome": explicit_expected_outcome,
            "explicit_split_merge": explicit_split_merge,
        }

    def _build_plan_correction_validation_feedback(
        self,
        correction_state: dict[str, Any],
        validation_reason: str,
        active_plan_state: dict[str, Any] | None = None,
        proposed_payload: dict[str, Any] | None = None,
    ) -> str:
        category = str(correction_state.get("category") or "").strip() or "ambiguous"
        ordered_types = list(correction_state.get("ordered_types") or [])
        active_operation_signatures = self._plan_operation_signatures_from_state(active_plan_state)
        proposed_operation_signatures = self._plan_operation_signatures_from_state(proposed_payload)
        active_operation_types = self._plan_operation_types_from_state(active_plan_state)
        active_steps = self._plan_steps_from_state(active_plan_state)
        active_operation_texts: list[str] = []
        for step in active_steps:
            for child in self._plan_child_operations_from_step(step):
                child_signature = self._plan_operation_signature(child)
                if child_signature and child_signature not in active_operation_signatures:
                    continue
                child_text = self._plan_operation_text(child)
                active_operation_texts.append(child_text or self._plan_operation_type(child) or "child")
        validation_reason_text = self._normalize_space(validation_reason).strip()

        if correction_state.get("needs_clarification") or category == "ambiguous":
            if category in {"add_operation", "add_and_reorder_operations"}:
                added_types = [operation_type for operation_type in ordered_types if operation_type not in active_operation_types]
                kept_types = [operation_type for operation_type in active_operation_types if operation_type in ordered_types]
                if "click" in kept_types and "assert" in added_types:
                    return "Should I keep the click and add an assertion before it?"
                if kept_types and added_types:
                    kept_text = " and ".join(kept_types)
                    added_text = " and ".join(added_types)
                    return f"Should I keep the {kept_text} and add the {added_text}?"
                if ordered_types:
                    return f"Should I add {' then '.join(ordered_types)} and keep the existing child operations?"
            if category == "remove_operation":
                removed_types = [operation_type for operation_type in active_operation_types if operation_type not in ordered_types]
                if "click" in removed_types:
                    return "Should I remove the click and keep the remaining child operations?"
                if removed_types:
                    removed_text = " and ".join(removed_types)
                    return f"Should I remove the {removed_text} operation and keep the remaining child operations?"
            if category in {"reorder_operations", "add_and_reorder_operations"} and ordered_types:
                return f"Should I keep the same child operations but reorder them as {' then '.join(ordered_types)}?"
            return "Should I keep the current plan and apply the correction as written?"

        if category in {"add_operation", "add_and_reorder_operations"} and len(proposed_operation_signatures) <= len(active_operation_signatures):
            missing_active_operation = ""
            for index, active_signature in enumerate(active_operation_signatures):
                if active_signature not in proposed_operation_signatures:
                    missing_active_operation = (
                        active_operation_texts[index]
                        if index < len(active_operation_texts) and active_operation_texts[index]
                        else ""
                    )
                    break
            if missing_active_operation:
                missing_active_operation_type = ""
                if index < len(active_steps):
                    missing_child = None
                    for child in self._plan_child_operations_from_step(active_steps[index]):
                        if self._plan_operation_signature(child) == active_signature:
                            missing_child = child
                            break
                    if isinstance(missing_child, dict):
                        missing_active_operation_type = self._plan_operation_type(missing_child)
                missing_active_operation_label = missing_active_operation_type or missing_active_operation
                if ordered_types:
                    return (
                        f"Corrected plan is invalid because existing {missing_active_operation_label} operation was dropped. "
                        f"Return one parent step with {' then '.join(ordered_types)}."
                    )
                return f"Corrected plan is invalid because existing {missing_active_operation_label} operation was dropped. Restore the dropped child operation."
            if ordered_types:
                return f"Corrected plan is invalid because the added {' then '.join(ordered_types)} operation is missing. Return one parent step with {' then '.join(ordered_types)}."
            return "Corrected plan is invalid because the added operation is missing. Return one parent step with the requested child operations."

        if category == "remove_operation" and len(proposed_operation_signatures) >= len(active_operation_signatures):
            return "Corrected plan is invalid because no operation was removed. Remove the explicitly rejected child operation and try again."

        if category in {"reorder_operations", "add_and_reorder_operations"} and ordered_types:
            ordered_text = " then ".join(ordered_types)
            if ordered_text:
                return f"Corrected plan is invalid because the child order does not match the correction. Return one parent step with {ordered_text}."

        if validation_reason_text:
            return validation_reason_text

        return "Corrected plan is invalid. Preserve the active child operations or ask one clarification."

    def _build_plan_correction_operation_context_lines(
        self,
        active_plan_state: dict[str, Any] | None,
    ) -> list[str]:
        if not isinstance(active_plan_state, dict):
            return []

        lines: list[str] = []
        for step in self._plan_steps_from_state(active_plan_state):
            if not isinstance(step, dict):
                continue
            step_id = str(step.get("step_id") or step.get("id") or "").strip()
            intent = self._normalize_space(
                str(step.get("intent") or step.get("title") or step.get("text") or step.get("label") or "")
            ).strip()
            header_parts = [part for part in (step_id, intent) if part]
            if header_parts:
                lines.append(f'Parent step: {" | ".join(header_parts)}')
            expected_outcome_text = self._expected_outcome_summary(
                self._normalize_expected_outcome(
                    step.get("expected_outcome") or step.get("expectedOutcome"),
                    self._is_click_like_intent(intent),
                )
            )
            if expected_outcome_text:
                lines.append(f"  expected_outcome: {expected_outcome_text}")
            children = self._plan_child_operations_from_step(step)
            if not children:
                lines.append("  child operations: none")
                continue
            for child in children:
                if not isinstance(child, dict):
                    continue
                child_operation_id = str(child.get("operation_id") or "").strip()
                child_type = str(child.get("type") or "").strip()
                child_target = self._normalize_space(str(child.get("target") or child.get("description") or "")).strip()
                child_locator = self._normalize_space(str(child.get("locator") or "")).strip()
                child_parts = [part for part in (child_operation_id, child_type) if part]
                child_text = " ".join(child_parts) if child_parts else "child"
                if child_target:
                    child_text += f' target="{child_target}"'
                if child_locator:
                    child_text += f' locator="{child_locator}"'
                lines.append(f"  - {child_text}")
        return lines

    def _build_plan_correction_context_message(self) -> str:
        correction_state = getattr(self, "_active_plan_correction_state", None)
        active_plan_state = self._current_active_plan_state()
        if not isinstance(correction_state, dict) or not isinstance(active_plan_state, dict):
            return ""

        payload = build_plan_diff_editor_context_payload(
            active_plan_state=active_plan_state,
            correction_state=correction_state,
            correction_text=self._normalize_space(str(correction_state.get("correction_text") or "")).strip(),
            validation_feedback=self._normalize_space(
                str(correction_state.get("last_validation_feedback") or correction_state.get("last_validation_reason") or "")
            ).strip() or None,
            allowed_edit_policy=self._normalize_space(
                str(correction_state.get("allowed_edit_policy") or "")
            ).strip() or None,
        )
        lines = [render_plan_diff_editor_context(payload)]
        correction_text = self._normalize_space(str(correction_state.get("correction_text") or "")).strip()
        answer_text = self._normalize_space(str(correction_state.get("clarification_answer") or "")).strip()
        lines.extend(
            [
                "Structured plan correction event.",
                f'active_plan_id: "{str(correction_state.get("plan_id") or "")}"',
                f'target_step_id: "{str(correction_state.get("target_step_id") or "")}"',
                f"target_plan_version: {self._current_plan_version()}",
                f'correction_type: "{str(correction_state.get("category") or "ambiguous")}"',
                f'Correction: "{correction_text}"',
            ]
        )
        if answer_text:
            lines.append(f'Clarification answer: "{answer_text}"')
        previous_plan_summary = self._normalize_space(str(active_plan_state.get("summary") or "")).strip()
        if previous_plan_summary:
            lines.append(f'Previous plan summary: "{previous_plan_summary}"')
        lines.extend(self._build_plan_correction_operation_context_lines(active_plan_state))
        lines.append("Mutation rules:")
        lines.append("- You MUST respond with send_to_overlay message_type='plan_correction_diff'.")
        lines.append("- Your send_to_overlay call must include a payload with target_step_id and mutations.")
        lines.append("- An empty or message_type-only plan_correction_diff call is invalid.")
        lines.append("- Do NOT respond with plan_ready during correction mode.")
        lines.append("- Do NOT respond with llm_thinking during correction mode.")
        lines.append("- Do NOT use ask_user unless the correction category is ambiguous.")
        lines.append("- Allowed mutation ops: keep, add, remove, reorder, change_expected_outcome.")
        lines.append("- Required mutation object shape: {\"op\": \"keep\"|\"add\"|\"remove\"|\"reorder\"|\"change_expected_outcome\", ...}")
        lines.append("- For \"add\": include operation object with type, target, and optional locator/assertion.")
        lines.append("- For \"keep\" and \"remove\": reference existing operation_id.")
        lines.append("- For \"reorder\": reference existing operation_id and include it in final position.")
        lines.append("- List mutations in final child order.")
        lines.append("- Preserve every existing child operation unless it is explicitly removed or reordered.")
        lines.append("- Do not reconstruct a full plan_ready in correction mode.")
        lines.append("- Do not call DOM extraction or locator search for pure plan edits.")
        lines.append("- Ask one clarification only if the correction is ambiguous.")
        return "\n".join(lines).strip()

    def _build_plan_diff_editor_schema_message(self) -> str:
        correction_state = getattr(self, "_active_plan_correction_state", None)
        active_plan_state = self._current_active_plan_state()
        if not isinstance(correction_state, dict) or not isinstance(active_plan_state, dict):
            return ""

        payload = build_plan_diff_editor_context_payload(
            active_plan_state=active_plan_state,
            correction_state=correction_state,
            correction_text=self._normalize_space(str(correction_state.get("correction_text") or "")).strip(),
            validation_feedback=self._normalize_space(
                str(correction_state.get("last_validation_feedback") or correction_state.get("last_validation_reason") or "")
            ).strip() or None,
            allowed_edit_policy=self._normalize_space(
                str(correction_state.get("allowed_edit_policy") or "")
            ).strip() or None,
        )
        return build_plan_diff_editor_schema_message(payload)

    async def _build_recovery_diagnoser_context_message(self) -> str:
        failed_step = self._get_failed_step_context()
        if not isinstance(failed_step, dict):
            return ""

        browser_state = await self._capture_browser_state()
        current_page = ""
        if isinstance(browser_state, dict):
            current_url = self._normalize_space(str(browser_state.get("url") or "")).strip()
            current_title = self._normalize_space(str(browser_state.get("title") or "")).strip()
            current_page = " | ".join(part for part in (current_url, current_title) if part)

        step_id = str(
            failed_step.get("step_id")
            or failed_step.get("id")
            or self.active_failed_step_id
            or ""
        ).strip() or None
        operation_id = str(
            failed_step.get("operation_id")
            or failed_step.get("current_operation_id")
            or (self.last_successful_action or {}).get("operation_id")
            or ""
        ).strip() or None
        error_summary = str(
            failed_step.get("last_error")
            or failed_step.get("error_summary")
            or failed_step.get("error")
            or ""
        ).strip() or None
        payload = build_recovery_diagnoser_context_payload(
            run_id=self._current_run_session_id(),
            failed_step_state=failed_step,
            failed_step_id=step_id,
            failed_operation_id=operation_id,
            error_summary=error_summary,
            current_page=current_page or None,
            messages=list(getattr(self.llm, "messages", []) or []),
            metadata={
                "run_id": self._current_run_session_id(),
                "failed_step_id": step_id,
                "failed_operation_id": operation_id,
                "error_summary": error_summary,
                "current_page": current_page or None,
            },
        )
        return render_recovery_diagnoser_context(payload)

    def _synthesize_plan_diff_editor_output(self) -> dict[str, Any]:
        correction_state = getattr(self, "_active_plan_correction_state", None)
        active_plan_state = self._current_active_plan_state()
        if not isinstance(correction_state, dict) or not isinstance(active_plan_state, dict):
            return {}

        category = str(correction_state.get("category") or "").strip()
        if category not in {"add_operation", "add_and_reorder_operations"}:
            return {}

        active_steps = self._plan_steps_from_state(active_plan_state)
        if not active_steps:
            return {}
        source_step = active_steps[0] if isinstance(active_steps[0], dict) else {}
        active_children = self._plan_child_operations_from_step(source_step)
        if not active_children:
            return {}

        click_child = None
        for child in active_children:
            if self._plan_operation_type(child) == "click":
                click_child = child
                break
        if click_child is None:
            click_child = active_children[0]

        click_operation_id = str(click_child.get("operation_id") or "").strip()
        if not click_operation_id:
            return {}

        target = self._select_plan_correction_child_target(
            [
                ("child.target", click_child.get("target")),
                ("child.element_name", click_child.get("element_name")),
                ("child.label", click_child.get("label")),
                ("source.element_name", source_step.get("element_name")),
                ("source.intent", source_step.get("intent")),
            ]
        )
        if not target:
            return {}

        correction_text = self._normalize_space(str(correction_state.get("correction_text") or "")).strip()
        plan_id = str(correction_state.get("plan_id") or active_plan_state.get("plan_id") or "").strip()
        plan_version = self._current_plan_version()
        return {
            "schema_id": "plan_diff_editor.v1",
            "purpose": "plan_diff_editor",
            "correction_intent": correction_text,
            "target_plan_id": plan_id,
            "target_plan_version": plan_version,
            "operations": [
                {
                    "action": "add",
                    "target_type": "operation",
                    "patch": {
                        "type": "assert",
                        "target": target,
                        "assertion": "visible",
                    },
                    "reason": "add visible assertion before the click",
                },
                {
                    "action": "reorder",
                    "target_type": "operation",
                    "target_id": click_operation_id,
                    "position": 2,
                    "reason": "keep the click after the assertion",
                },
            ],
            "reasoning_summary": "Add a visible assertion before the click and keep the click second.",
            "ambiguity": [],
            "requires_user_clarification": False,
        }

    def _build_plan_correction_clarification_message(
        self,
        correction_state: dict[str, Any],
        answer: str,
    ) -> str:
        clarification_question = self._normalize_space(
            str(correction_state.get("clarification_question") or correction_state.get("last_validation_feedback") or "")
        ).strip()
        correction_text = self._normalize_space(str(correction_state.get("correction_text") or "")).strip()
        category = str(correction_state.get("category") or "").strip() or "ambiguous"
        answer_text = self._normalize_space(answer).strip() or "answered"
        lines = [
            "Structured correction clarification resolved.",
            f'User answered: "{answer_text}"',
        ]
        if clarification_question:
            lines.append(f'Clarification question: "{clarification_question}"')
        if correction_text:
            lines.append(f'Original correction: "{correction_text}"')
        lines.append(f'Correction type: "{category}"')
        lines.append("Do not ask the same clarification again.")
        lines.append("List mutations in final child order.")
        lines.append("Send a structured correction diff.")
        return "\n".join(lines)

    def _build_plan_correction_state(
        self,
        correction: str,
        source_plan_state: dict[str, Any] | None = None,
        target_step_id: str | None = None,
    ) -> dict[str, Any]:
        active_plan_state = source_plan_state if isinstance(source_plan_state, dict) else self._current_active_plan_state()
        correction_classification = self._classify_plan_correction(correction, active_plan_state)
        correction_text = self._normalize_space(correction).strip()
        plan_id = str((active_plan_state or {}).get("plan_id") or "").strip() or None
        active_target_step_id = target_step_id or str((active_plan_state or {}).get("target_step_id") or "").strip() or None
        if active_target_step_id is None and active_plan_state is not None:
            step_ids = list((active_plan_state or {}).get("step_ids") or [])
            active_target_step_id = step_ids[0] if step_ids else None

        return {
            "plan_id": plan_id,
            "target_step_id": active_target_step_id,
            "correction_text": correction_text,
            "category": correction_classification["category"],
            "ordered_types": list(correction_classification["ordered_types"]),
            "explicit_add": bool(correction_classification["explicit_add"]),
            "explicit_remove": bool(correction_classification["explicit_remove"]),
            "explicit_order": bool(correction_classification["explicit_order"]),
            "explicit_replace": bool(correction_classification["explicit_replace"]),
            "explicit_target_change": bool(correction_classification["explicit_target_change"]),
            "explicit_expected_outcome": bool(correction_classification["explicit_expected_outcome"]),
            "explicit_split_merge": bool(correction_classification["explicit_split_merge"]),
            "retry_count": 0,
            "needs_clarification": correction_classification["category"] == "ambiguous",
            "clarification_question": None,
            "clarification_answer": None,
            "clarification_resolved": False,
            "clarification_closed": False,
            "correction_failed": False,
            "no_progress_count": 0,
            "schema_retry_count": 0,
            "last_validation_reason": None,
            "last_validation_feedback": None,
        }

    def _build_plan_correction_added_child(
        self,
        operation_spec: dict[str, Any],
        source_step: dict[str, Any],
        anchor_child: dict[str, Any] | None,
        operation_id: str,
    ) -> dict[str, Any]:
        operation_type = self._normalize_space(
            str(operation_spec.get("type") or operation_spec.get("action") or "")
        ).strip().lower()
        if not operation_type or operation_type == "unknown":
            return {}

        target = self._select_plan_correction_child_target(
            [
                ("operation.target", operation_spec.get("target")),
                ("operation.element_name", operation_spec.get("element_name")),
                ("anchor.target", (anchor_child or {}).get("target")),
                ("anchor.description", (anchor_child or {}).get("description")),
                ("source.element_name", source_step.get("element_name")),
                ("source.intent", source_step.get("intent")),
            ]
        )
        if not target and operation_type != "assert":
            return {}

        locator = self._normalize_space(
            str(
                operation_spec.get("locator")
                or (anchor_child or {}).get("locator")
                or source_step.get("locator")
                or self._derive_locator_from_step_context(source_step)
                or ""
            )
        ).strip()
        if locator in {"*", 'page.locator("")'}:
            locator = ""

        canonical_child: dict[str, Any] = {}
        assertion = self._normalize_space(str(operation_spec.get("assertion") or "")).strip().lower()
        value_text = self._normalize_space(
            str(operation_spec.get("value") or operation_spec.get("expected_value") or "")
        ).strip()
        description = str(operation_spec.get("description") or "").strip()
        if operation_type == "assert":
            canonical_child = self._canonicalize_assertion_operation(
                operation_spec,
                source_step=source_step,
                anchor_child=anchor_child,
            )
            if canonical_child:
                target = str(canonical_child.get("target") or target or "").strip()
                locator = str(canonical_child.get("locator") or locator or "").strip()
                assertion = str(canonical_child.get("assertion") or assertion or "").strip().lower()
                value_text = str(
                    canonical_child.get("value") or canonical_child.get("expected_value") or value_text or ""
                ).strip()
                description = str(canonical_child.get("description") or description or "").strip()
        if not assertion and operation_type == "assert":
            assertion = "visible"
        if operation_type != "assert" and not description:
            description = self._build_plan_correction_child_description(
                operation_type,
                target,
                assertion,
                value_text,
                str(operation_spec.get("description") or ""),
                str(source_step.get("intent") or "").strip(),
            )
        elif operation_type == "assert" and not description:
            description = self._build_plan_correction_child_description(
                operation_type,
                target,
                assertion,
                value_text,
                str(operation_spec.get("description") or ""),
                str(source_step.get("intent") or "").strip(),
            )
        if operation_type == "assert":
            print(
                "[PLAN_CORRECTION_CHILD] canonicalized assert "
                f"target={target!r} assertion={assertion or 'visible'!r} locator_present={bool(locator)}"
            )

        child = {
            "operation_id": operation_id,
            "type": operation_type,
            "description": description or target or operation_type,
            "target": target,
            "locator": locator,
            "status": "planned",
        }
        if assertion:
            child["assertion"] = assertion
        if value_text:
            child["value"] = value_text
            child["expected_value"] = value_text
        return child

    def _build_structured_plan_correction_payload_from_diff(
        self,
        diff_payload: dict[str, Any],
    ) -> dict[str, Any]:
        active_plan_state = self._current_active_plan_state()
        correction_state = getattr(self, "_active_plan_correction_state", None)
        if not isinstance(active_plan_state, dict) or not isinstance(correction_state, dict):
            return {}

        proposed_diff = deepcopy(diff_payload) if isinstance(diff_payload, dict) else {}
        active_plan_id = str(active_plan_state.get("plan_id") or "").strip()
        proposed_target_plan_id = str(
            proposed_diff.get("target_plan_id")
            or proposed_diff.get("targetPlanId")
            or correction_state.get("plan_id")
            or ""
        ).strip()
        if proposed_target_plan_id and active_plan_id and proposed_target_plan_id != active_plan_id:
            return {}

        def _patch_value(patch: dict[str, Any], *names: str) -> Any:
            for name in names:
                value = patch.get(name)
                if value not in (None, "", [], {}, ()):
                    return value
            return None

        def _normalize_step_patch(patch: dict[str, Any]) -> dict[str, Any]:
            if any(name in patch for name in ("children", "operations")):
                return {}

            updates: dict[str, Any] = {}
            intent_value = _patch_value(patch, "intent", "title", "text", "label")
            if intent_value is not None:
                intent_text = self._normalize_space(str(intent_value)).strip()
                if intent_text:
                    updates["intent"] = intent_text

            expected_outcome_value = _patch_value(patch, "expected_outcome", "expectedOutcome")
            if expected_outcome_value is not None:
                updates["expected_outcome"] = deepcopy(expected_outcome_value)
            return updates

        mutations = proposed_diff.get("mutations")
        if not isinstance(mutations, list):
            operations = proposed_diff.get("operations")
            if not isinstance(operations, list):
                return {}

            mutations = []
            for operation in operations:
                if not isinstance(operation, dict):
                    return {}
                mutation_op = self._normalize_space(
                    str(operation.get("op") or operation.get("action") or "")
                ).strip().lower()
                target_type = self._normalize_space(
                    str(operation.get("target_type") or operation.get("targetType") or "")
                ).strip().lower()
                target_id = self._normalize_space(
                    str(operation.get("target_id") or operation.get("targetId") or "")
                ).strip()

                if mutation_op in {"keep", "remove", "reorder"}:
                    if target_type and target_type not in {"operation", "child"}:
                        return {}
                    if not target_id:
                        return {}
                    mutation: dict[str, Any] = {"op": mutation_op, "operation_id": target_id}
                    for key in (
                        "position",
                        "relative_to_operation_id",
                        "relativeToOperationId",
                        "before_operation_id",
                        "beforeOperationId",
                        "after_operation_id",
                        "afterOperationId",
                    ):
                        value = _patch_value(operation, key)
                        if value is not None:
                            mutation[key] = value
                    mutations.append(mutation)
                    continue

                if mutation_op == "add":
                    if target_type and target_type not in {"operation", "child"}:
                        return {}
                    operation_spec = _patch_value(operation, "operation", "patch", "child", "child_operation")
                    if not isinstance(operation_spec, dict):
                        return {}
                    mutation = {"op": "add", "operation": deepcopy(operation_spec)}
                    for key in (
                        "position",
                        "relative_to_operation_id",
                        "relativeToOperationId",
                        "before_operation_id",
                        "beforeOperationId",
                        "after_operation_id",
                        "afterOperationId",
                    ):
                        value = _patch_value(operation, key)
                        if value is not None:
                            mutation[key] = value
                    mutations.append(mutation)
                    continue

                if mutation_op == "update":
                    patch = _patch_value(operation, "patch")
                    if not isinstance(patch, dict):
                        return {}
                    if target_type == "step":
                        step_updates = _normalize_step_patch(patch)
                        if not step_updates:
                            return {}
                        mutations.append({"op": "step_update", "step_updates": step_updates})
                        continue
                    if target_type == "operation":
                        expected_outcome = _patch_value(patch, "expected_outcome", "expectedOutcome")
                        if expected_outcome is None:
                            return {}
                        mutations.append(
                            {
                                "op": "change_expected_outcome",
                                "expected_outcome": deepcopy(expected_outcome),
                            }
                        )
                        continue
                    return {}

                return {}

        step_updates: dict[str, Any] = {}

        target_step_id = str(
            proposed_diff.get("target_step_id")
            or proposed_diff.get("targetStepId")
            or correction_state.get("target_step_id")
            or ""
        ).strip()

        corrected_payload = deepcopy(active_plan_state)
        corrected_steps: list[dict[str, Any]] = []
        target_step_found = False

        for active_step in self._plan_steps_from_state(active_plan_state):
            step_copy = deepcopy(active_step)
            step_id = str(step_copy.get("step_id") or step_copy.get("id") or "").strip()
            if target_step_found or (target_step_id and step_id != target_step_id):
                corrected_steps.append(step_copy)
                continue

            target_step_found = True
            active_children = self._plan_child_operations_from_step(step_copy)
            child_by_id: dict[str, dict[str, Any]] = {}
            for child in active_children:
                child_operation_id = str(child.get("operation_id") or "").strip()
                if child_operation_id:
                    child_by_id[child_operation_id] = child

            next_operation_index = 1
            for child_operation_id in child_by_id:
                if not child_operation_id.startswith("op_"):
                    continue
                try:
                    next_operation_index = max(next_operation_index, int(child_operation_id.split("_", 1)[1]) + 1)
                except (IndexError, ValueError):
                    continue

            def allocate_operation_id() -> str:
                nonlocal next_operation_index
                while True:
                    candidate = f"op_{next_operation_index}"
                    next_operation_index += 1
                    if candidate not in child_by_id:
                        return candidate

            new_children: list[dict[str, Any]] = []
            changed_expected_outcome = None
            seen_operation_ids: set[str] = set()

            for mutation in mutations:
                if not isinstance(mutation, dict):
                    return {}
                mutation_op = self._normalize_space(
                    str(mutation.get("op") or mutation.get("type") or "")
                ).strip().lower()
                if mutation_op == "step_update":
                    step_update_values = mutation.get("step_updates")
                    if not isinstance(step_update_values, dict):
                        return {}
                    step_updates.update(dict(step_update_values))
                    continue
                if mutation_op in {"keep", "reorder", "remove"}:
                    operation_id = self._normalize_space(
                        str(mutation.get("operation_id") or mutation.get("operationId") or "")
                    ).strip()
                    if not operation_id or operation_id not in child_by_id or operation_id in seen_operation_ids:
                        return {}
                    seen_operation_ids.add(operation_id)
                    if mutation_op != "remove":
                        new_children.append(deepcopy(child_by_id[operation_id]))
                    continue
                if mutation_op == "add":
                    operation_spec = mutation.get("operation")
                    if not isinstance(operation_spec, dict):
                        return {}
                    anchor_operation_id = self._normalize_space(
                        str(
                            mutation.get("relative_to_operation_id")
                            or mutation.get("relativeToOperationId")
                            or mutation.get("before_operation_id")
                            or mutation.get("beforeOperationId")
                            or mutation.get("after_operation_id")
                            or mutation.get("afterOperationId")
                            or ""
                        )
                    ).strip()
                    anchor_child = child_by_id.get(anchor_operation_id) if anchor_operation_id else None
                    added_operation_id = allocate_operation_id()
                    added_child = self._build_plan_correction_added_child(
                        operation_spec,
                        step_copy,
                        anchor_child,
                        added_operation_id,
                    )
                    if not added_child:
                        return {}
                    new_children.append(added_child)
                    continue
                if mutation_op == "change_expected_outcome":
                    changed_expected_outcome = mutation.get("expected_outcome") or mutation.get("expectedOutcome")
                    continue
                if mutation_op in {"split_step", "merge_steps", "replace_target", "ambiguous"}:
                    return {}
                return {}

            if step_updates:
                intent_value = step_updates.get("intent")
                if intent_value is not None:
                    step_copy["intent"] = self._normalize_space(str(intent_value)).strip()
                expected_outcome_value = step_updates.get("expected_outcome")
                if expected_outcome_value is not None:
                    normalized_expected_outcome = self._normalize_expected_outcome(
                        expected_outcome_value,
                        self._is_click_like_intent(
                            str(step_copy.get("intent") or step_copy.get("title") or step_copy.get("text") or "").strip(),
                        ),
                    )
                    if normalized_expected_outcome is None:
                        return {}
                    step_copy["expected_outcome"] = normalized_expected_outcome

            if changed_expected_outcome is not None:
                normalized_expected_outcome = self._normalize_expected_outcome(
                    changed_expected_outcome,
                    self._is_click_like_intent(
                        str(step_copy.get("intent") or step_copy.get("title") or step_copy.get("text") or "").strip(),
                    ),
                )
                if normalized_expected_outcome is None:
                    return {}
                step_copy["expected_outcome"] = normalized_expected_outcome

            step_copy["children"] = new_children
            corrected_steps.append(step_copy)

        if target_step_id and not target_step_found:
            return {}

        corrected_payload["steps"] = corrected_steps
        return corrected_payload

    def _validate_structured_plan_step(
        self,
        active_step: dict[str, Any],
        proposed_step: dict[str, Any],
        correction_state: dict[str, Any],
        active_plan_state: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        active_children = self._plan_child_operations_from_step(active_step)
        proposed_children = self._plan_child_operations_from_step(proposed_step)
        category = str(correction_state.get("category") or "").strip()
        ordered_types = list(correction_state.get("ordered_types") or [])
        explicit_add = bool(correction_state.get("explicit_add"))
        explicit_remove = bool(correction_state.get("explicit_remove"))
        explicit_order = bool(correction_state.get("explicit_order"))
        explicit_replace = bool(correction_state.get("explicit_replace"))
        explicit_target_change = bool(correction_state.get("explicit_target_change"))
        explicit_expected_outcome = bool(correction_state.get("explicit_expected_outcome"))
        explicit_split_merge = bool(correction_state.get("explicit_split_merge"))

        active_signatures = [
            self._plan_operation_signature(child)
            for child in active_children
            if self._plan_operation_signature(child)
        ]
        proposed_signatures = [
            self._plan_operation_signature(child)
            for child in proposed_children
            if self._plan_operation_signature(child)
        ]
        active_types = [
            self._plan_operation_type(child)
            for child in active_children
            if self._plan_operation_type(child)
        ]
        proposed_types = [
            self._plan_operation_type(child)
            for child in proposed_children
            if self._plan_operation_type(child)
        ]

        active_count = len(active_signatures)
        proposed_count = len(proposed_signatures)

        if category == "ambiguous" or correction_state.get("needs_clarification"):
            return {
                "valid": False,
                "reason": "ambiguous correction",
                "needs_clarification": True,
            }

        if category in {"split_step", "merge_steps"}:
            return {
                "valid": False,
                "reason": "split and merge corrections are not yet accepted in this path",
                "needs_clarification": True,
            }

        if category in {"change_target", "change_expected_outcome", "replace_operation"}:
            if proposed_count != active_count:
                return {
                    "valid": False,
                    "reason": "replacement or target change must preserve the current child count",
                }
            normalized_children = []
            for index, proposed_child in enumerate(proposed_children):
                normalized_child = dict(proposed_child)
                active_child = active_children[index] if index < len(active_children) else {}
                active_operation_id = str(active_child.get("operation_id") or "").strip()
                if active_operation_id:
                    normalized_child["operation_id"] = active_operation_id
                elif not str(normalized_child.get("operation_id") or "").strip():
                    normalized_child["operation_id"] = f"op_{index + 1}"
                normalized_children.append(normalized_child)

            normalized_step = dict(proposed_step)
            if str(active_step.get("step_id") or "").strip():
                normalized_step["step_id"] = str(active_step.get("step_id") or "").strip()
            normalized_step["children"] = normalized_children
            return {"valid": True, "normalized_step": normalized_step}

        if category == "remove_operation":
            if proposed_count >= active_count:
                return {
                    "valid": False,
                    "reason": "remove correction did not drop any child operation",
                }
            if not self._sequence_contains_subsequence(active_signatures, proposed_signatures):
                return {
                    "valid": False,
                    "reason": "remaining child operations were reordered or changed unexpectedly",
                }
        elif category == "add_operation":
            if proposed_count <= active_count:
                return {
                    "valid": False,
                    "reason": "added child operation is missing",
                }
            if not self._sequence_contains_subsequence(proposed_signatures, active_signatures):
                return {
                    "valid": False,
                    "reason": "existing child operations were reordered or changed unexpectedly",
                }
        elif category in {"reorder_operations", "add_and_reorder_operations"}:
            if not all(active_signature in proposed_signatures for active_signature in active_signatures):
                return {
                    "valid": False,
                    "reason": "existing child operation was dropped",
                }
            if ordered_types and not self._sequence_contains_subsequence(proposed_types, ordered_types):
                return {
                    "valid": False,
                    "reason": "child order does not match the correction text",
                }
            if category == "reorder_operations" and proposed_count != active_count:
                return {
                    "valid": False,
                    "reason": "reorder correction changed the child count",
                }
            if category == "add_and_reorder_operations" and proposed_count <= active_count:
                return {
                    "valid": False,
                    "reason": "added child operation is missing",
                }
        else:
            if proposed_count != active_count:
                return {
                    "valid": False,
                    "reason": "plan correction changed the child count without an explicit category",
                }
            if not self._sequence_contains_subsequence(proposed_signatures, active_signatures):
                return {
                    "valid": False,
                    "reason": "existing child operations were reordered or changed unexpectedly",
                }

        normalized_children: list[dict[str, Any]] = []
        existing_operation_ids = {
            str(child.get("operation_id") or "").strip()
            for child in active_children
            if str(child.get("operation_id") or "").strip()
        }
        next_operation_index = 1

        def allocate_operation_id() -> str:
            nonlocal next_operation_index
            while True:
                candidate = f"op_{next_operation_index}"
                next_operation_index += 1
                if candidate not in existing_operation_ids:
                    existing_operation_ids.add(candidate)
                    return candidate

        if category == "reorder_operations":
            matched_indices: set[int] = set()
            for proposed_child in proposed_children:
                normalized_child = dict(proposed_child)
                normalized_signature = self._plan_operation_signature(normalized_child)
                matched_index = -1
                for index, active_child in enumerate(active_children):
                    if index in matched_indices:
                        continue
                    if self._plan_operation_signature(active_child) == normalized_signature:
                        matched_index = index
                        break
                if matched_index >= 0:
                    matched_indices.add(matched_index)
                    active_child = active_children[matched_index]
                    active_operation_id = str(active_child.get("operation_id") or "").strip()
                    if active_operation_id:
                        normalized_child["operation_id"] = active_operation_id
                    elif not str(normalized_child.get("operation_id") or "").strip():
                        normalized_child["operation_id"] = allocate_operation_id()
                else:
                    normalized_child["operation_id"] = str(normalized_child.get("operation_id") or "").strip() or allocate_operation_id()
                normalized_children.append(normalized_child)
        else:
            matched_indices: set[int] = set()
            for proposed_child in proposed_children:
                normalized_child = dict(proposed_child)
                normalized_signature = self._plan_operation_signature(normalized_child)
                matched_index = -1
                for index, active_child in enumerate(active_children):
                    if index in matched_indices:
                        continue
                    active_signature = self._plan_operation_signature(active_child)
                    active_type = self._plan_operation_type(active_child)
                    proposed_type = self._plan_operation_type(normalized_child)
                    if category == "add_operation":
                        signature_matches = active_signature == normalized_signature
                    elif category == "remove_operation":
                        signature_matches = active_signature == normalized_signature
                    else:
                        signature_matches = (
                            active_signature == normalized_signature
                            or (
                                category in {"change_target", "change_expected_outcome", "replace_operation"}
                                and active_type == proposed_type
                            )
                        )
                    if signature_matches:
                        matched_index = index
                        break
                if matched_index >= 0:
                    matched_indices.add(matched_index)
                    active_child = active_children[matched_index]
                    active_operation_id = str(active_child.get("operation_id") or "").strip()
                    if active_operation_id:
                        normalized_child["operation_id"] = active_operation_id
                    elif not str(normalized_child.get("operation_id") or "").strip():
                        normalized_child["operation_id"] = allocate_operation_id()
                else:
                    normalized_child["operation_id"] = str(normalized_child.get("operation_id") or "").strip() or allocate_operation_id()
                normalized_children.append(normalized_child)

        normalized_step = dict(proposed_step)
        active_step_id = str(active_step.get("step_id") or active_step.get("id") or "").strip()
        if active_step_id:
            normalized_step["step_id"] = active_step_id
        elif not str(normalized_step.get("step_id") or normalized_step.get("id") or "").strip():
            normalized_step["step_id"] = str(proposed_step.get("step_id") or proposed_step.get("id") or "").strip() or "1"
        normalized_step["children"] = normalized_children
        return {"valid": True, "normalized_step": normalized_step}

    def _validate_structured_plan_correction(
        self,
        proposed_payload: dict[str, Any],
    ) -> dict[str, Any]:
        active_plan_state = self._current_active_plan_state()
        correction_state = getattr(self, "_active_plan_correction_state", None)
        proposed_plan = deepcopy(proposed_payload) if isinstance(proposed_payload, dict) else {}

        if not isinstance(active_plan_state, dict) or not isinstance(correction_state, dict):
            return {"valid": True, "normalized_payload": proposed_plan}

        active_steps = self._plan_steps_from_state(active_plan_state)
        proposed_steps = self._plan_steps_from_state(proposed_plan)
        category = str(correction_state.get("category") or "").strip()

        if correction_state.get("needs_clarification") or category == "ambiguous":
            return {
                "valid": False,
                "reason": "ambiguous correction",
                "needs_clarification": True,
            }

        if len(active_steps) != len(proposed_steps) and category not in {"split_step", "merge_steps"}:
            return {
                "valid": False,
                "reason": "parent step count changed",
            }

        normalized_steps: list[dict[str, Any]] = []
        for index, active_step in enumerate(active_steps):
            proposed_step = proposed_steps[index] if index < len(proposed_steps) else {}
            validation = self._validate_structured_plan_step(
                active_step,
                proposed_step,
                correction_state,
                active_plan_state=active_plan_state,
            )
            if not validation.get("valid"):
                return validation
            normalized_steps.append(validation["normalized_step"])

        normalized_payload = deepcopy(proposed_plan)
        normalized_payload["steps"] = normalized_steps
        if str(active_plan_state.get("plan_id") or "").strip():
            normalized_payload["plan_id"] = str(active_plan_state.get("plan_id") or "").strip()
        if str(active_plan_state.get("summary") or "").strip():
            normalized_payload["summary"] = str(active_plan_state.get("summary") or "").strip()
        if str(active_plan_state.get("original_user_intent") or "").strip():
            normalized_payload["original_user_intent"] = str(active_plan_state.get("original_user_intent") or "").strip()
        return {
            "valid": True,
            "normalized_payload": normalized_payload,
        }

    def _remember_plan_review_context(self, payload: dict[str, Any]) -> None:
        plan_ready_payload = deepcopy(payload) if isinstance(payload, dict) else {}
        steps = plan_ready_payload.get("steps") if isinstance(plan_ready_payload.get("steps"), list) else []
        plan_step_ids: list[str] = []
        for step in steps:
            if not isinstance(step, dict):
                continue
            step_id = str(step.get("step_id") or step.get("id") or "").strip()
            if step_id:
                plan_step_ids.append(step_id)

        source_steps = list(getattr(self, "current_steps", []))
        if not source_steps:
            source_steps = list(steps)
        intent_parts: list[str] = []
        for source_step in source_steps:
            if not isinstance(source_step, dict):
                continue
            intent_text = self._normalize_space(str(source_step.get("intent") or "")).strip()
            if intent_text:
                intent_parts.append(intent_text)

        self.last_plan_ready_payload = plan_ready_payload
        self.last_plan_step_ids = plan_step_ids
        self.last_plan_summary = str(plan_ready_payload.get("summary") or "").strip() or None
        self.last_plan_original_user_intent = " | ".join(intent_parts).strip() or None
        self._active_plan_state = self._build_active_plan_state(
            plan_ready_payload,
            source_plan_state=self._current_active_plan_state(),
        )

    def _build_plan_step_context_lines(self, plan_payload: dict[str, Any] | None = None) -> list[str]:
        plan_ready_payload = plan_payload if isinstance(plan_payload, dict) else getattr(self, "last_plan_ready_payload", None)
        if not isinstance(plan_ready_payload, dict):
            return []

        steps = plan_ready_payload.get("steps")
        if not isinstance(steps, list):
            return []

        step_lines: list[str] = []
        for index, step in enumerate(steps, start=1):
            if not isinstance(step, dict):
                continue
            step_intent = self._normalize_space(
                str(step.get("intent") or step.get("title") or step.get("text") or step.get("label") or "")
            ).strip()
            step_lines.append(f"{index}. {step_intent}" if step_intent else f"{index}.")
            expected_outcome_text = self._expected_outcome_summary(
                self._normalize_expected_outcome(
                    step.get("expected_outcome") or step.get("expectedOutcome"),
                    self._is_click_like_intent(step_intent),
                )
            )
            if expected_outcome_text:
                step_lines.append(f"   expected_outcome: {expected_outcome_text}")
            children = step.get("children")
            if not isinstance(children, list):
                continue
            for child in children:
                if not isinstance(child, dict):
                    continue
                child_operation_id = str(child.get("operation_id") or "").strip()
                child_type = str(child.get("type") or "").strip()
                child_description = self._normalize_space(str(child.get("description") or "")).strip()
                child_parts = [part for part in (child_operation_id, child_type, child_description) if part]
                if child_parts:
                    step_lines.append(f"   - {' '.join(child_parts)}")
                child_locator = self._normalize_space(str(child.get("locator") or "")).strip()
                if child_locator:
                    step_lines.append(f"     locator: {child_locator}")
        return step_lines

    def _build_plan_correction_message(
        self,
        correction: str,
        plan_id: str | None = None,
        target_step_id: str | None = None,
    ) -> str:
        correction_text = self._normalize_space(correction) or "the user requested a correction"
        active_plan_state = self._current_active_plan_state()
        correction_state = self._build_plan_correction_state(
            correction_text,
            source_plan_state=active_plan_state,
            target_step_id=target_step_id,
        )
        if plan_id:
            correction_state["plan_id"] = plan_id
        lines = [
            "Structured plan correction event.",
            f'active_plan_id: "{str(correction_state.get("plan_id") or "")}"',
            f'target_step_id: "{str(correction_state.get("target_step_id") or "")}"',
            f'correction_type: "{str(correction_state.get("category") or "ambiguous")}"',
            f'Correction: "{correction_text}"',
        ]
        original_user_intent = str(
            (active_plan_state or {}).get("original_user_intent")
            or self.last_plan_original_user_intent
            or ""
        ).strip()
        if original_user_intent:
            lines.append(f'Original user intent: "{original_user_intent}"')
        previous_summary = str(
            (active_plan_state or {}).get("summary")
            or self.last_plan_summary
            or ""
        ).strip()
        if previous_summary:
            lines.append(f'Previous plan summary: "{previous_summary}"')
        lines.append(f"Current plan version: {self._current_plan_version()}")
        step_lines = self._build_plan_step_context_lines(active_plan_state)
        if step_lines:
            lines.append("Previous plan steps:")
            lines.extend(step_lines)
        else:
            lines.append("Previous plan steps: none available.")
        lines.append("Validation rules:")
        lines.append("- Do not drop child operations unless the correction explicitly removes them.")
        lines.append("- Do not reorder child operations unless the correction explicitly states order.")
        lines.append("- Keep one parent step unless split or merge is explicit.")
        lines.append("- Ask clarification if the correction is ambiguous.")
        lines.append("- List mutations in final child order.")
        lines.append("Return a structured correction diff. Do not execute. Do not reconstruct a full plan_ready.")
        return "\n".join(lines)

    def _append_plan_correction_message(
        self,
        correction: str,
        plan_id: str | None = None,
        target_step_id: str | None = None,
    ) -> str:
        message = self._build_plan_correction_message(
            correction,
            plan_id=plan_id,
            target_step_id=target_step_id,
        )
        correction_state = self._build_plan_correction_state(
            correction,
            source_plan_state=self._current_active_plan_state(),
            target_step_id=target_step_id,
        )
        if plan_id:
            correction_state["plan_id"] = plan_id
        self._active_plan_correction_state = correction_state
        self._plan_correction_pending = True
        self.llm.messages.append({"role": "user", "content": message})
        self._clear_plan_review_context()
        return message

    def _mark_step_skipped(self, step: dict[str, Any] | str | None, reason: Any) -> dict[str, Any] | None:
        context = self._get_step_context(step) if not isinstance(step, dict) else step
        if context is None:
            return None

        step_id = str(context.get("step_id") or "").strip()
        if not step_id:
            return None

        context["status"] = "skipped"
        context["last_error"] = str(reason or "").strip() or None
        context["recorded"] = False
        self.skipped_step_ids.add(step_id)
        self.completed_step_ids.discard(step_id)
        if self.active_failed_step_id == step_id:
            self.active_failed_step_id = None
            self.pending_recovery = False
            self._pending_failure_followup = False
        if self.active_step_id == step_id:
            self.active_step_id = None
        if self.plan_confirmed:
            self.phase = "executing"
        self._recording_wait_guard_armed = False
        self.current_step_index = max(0, int(context.get("step_number") or 1) - 1)
        print(f"[AGENT] step skipped: {step_id}")
        self._log_confirmed_execution_cursor("[CONFIRMED_CURSOR]")
        return context

    def _has_unresolved_steps(self) -> bool:
        return any(
            str(step.get("status") or "") in {"pending", "executing", "failed", "recovery_pending"}
            for step in self._recording_steps
        )

    def _has_unresolved_failure(self) -> bool:
        return self.pending_recovery or self._get_failed_step_context() is not None

    def _all_steps_done(self) -> bool:
        if not self._recording_steps:
            return True
        return all(str(step.get("status") or "") in {"recorded", "skipped"} for step in self._recording_steps)

    def _all_steps_resolved(self) -> bool:
        if not self._recording_steps:
            return False
        if not self.plan_confirmed:
            return False
        if self._awaiting_step_record or self.pending_recovery or self._pending_failure_followup:
            return False
        if self.active_step_id or self.active_failed_step_id:
            return False
        if self._has_unresolved_failure():
            return False
        return all(str(step.get("status") or "") in {"recorded", "skipped"} for step in self._recording_steps)

    def _step_state_summary(self, step: dict[str, Any] | None) -> dict[str, Any]:
        if step is None:
            return {}
        element_info = self._resolve_selected_element_info(step.get("element_info") if isinstance(step.get("element_info"), dict) else {})
        return {
            "step_id": str(step.get("step_id") or "").strip(),
            "step_number": step.get("step_number"),
            "intent": str(step.get("intent") or "").strip(),
            "element_info": element_info,
            "status": str(step.get("status") or "").strip(),
            "locator": str(step.get("locator") or "").strip() or None,
            "last_error": str(step.get("last_error") or "").strip() or None,
            "recorded": bool(step.get("recorded")),
        }

    def _current_browser_url(self) -> str:
        try:
            return str(get_page().url or "").strip()
        except Exception:  # noqa: BLE001
            return ""

    def _build_failure_recovery_question(self, step: dict[str, Any] | None, final_text: str) -> str:
        step_summary = self._step_state_summary(step)
        browser_url = self._current_browser_url()
        parts = [
            "Recovery required for the failed original step.",
            f"Failed step: {json.dumps(step_summary, ensure_ascii=True)}",
            f"Current browser URL: {browser_url or 'unknown'}",
        ]
        if final_text:
            parts.append(f"Model summary: {self._normalize_space(final_text)}")
        parts.append("Reply with the correction, or say skip/stop/end.")
        return "\n".join(parts)

    def _build_failure_followup_message(
        self,
        step: dict[str, Any] | None,
        answer_text: str,
        *,
        skipped: bool,
    ) -> str:
        step_summary = self._step_state_summary(step)
        browser_url = self._current_browser_url()
        prefix = "User skipped unresolved failed step" if skipped else "User correction for unresolved failed step"
        details = self._normalize_space(answer_text) or ("skip" if skipped else "confirmed")
        return (
            f"{prefix} {step_summary.get('step_id') or 'unknown'}: {details}. "
            f"Continue recovery. Do not finalize until the failed step is recorded or skipped. "
            f"Original failed step context: {json.dumps(step_summary, ensure_ascii=True)}. "
            f"Current browser URL: {browser_url or 'unknown'}."
        )

    def _build_stop_followup_message(self, step: dict[str, Any] | None, answer_text: str) -> str:
        step_summary = self._step_state_summary(step)
        browser_url = self._current_browser_url()
        return (
            f"User explicitly ended the run for unresolved failed step {step_summary.get('step_id') or 'unknown'}: "
            f"{self._normalize_space(answer_text) or 'stop'}. "
            f"Provide a concise final summary and do not request more actions. "
            f"Original failed step context: {json.dumps(step_summary, ensure_ascii=True)}. "
            f"Current browser URL: {browser_url or 'unknown'}."
        )

    def _build_continue_prompt(self, final_text: str) -> str:
        unresolved_steps = [
            self._step_state_summary(step)
            for step in self._recording_steps
            if str(step.get("status") or "") in {"pending", "executing", "recovery_pending", "failed"}
        ]
        prompt = {
            "instruction": "Continue the unresolved steps. Do not finalize yet.",
            "unresolved_steps": unresolved_steps,
        }
        if final_text:
            prompt["llm_text"] = self._normalize_space(final_text)
        return f"Continue with the remaining steps: {json.dumps(prompt, ensure_ascii=True)}"

    def _response_requests_skip(self, answer_text: str) -> bool:
        normalized = self._normalize_space(answer_text).lower()
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

    def _response_requests_stop(self, answer_text: str) -> bool:
        normalized = self._normalize_space(answer_text).lower()
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

    def _derive_step_context_element_name(self, step: dict[str, Any], element_info: dict[str, Any]) -> str:
        element_info = self._resolve_selected_element_info(element_info)
        attrs = element_info.get("attributes") if isinstance(element_info.get("attributes"), dict) else {}
        candidates = [
            self._selected_element_text(element_info),
            str(attrs.get("aria-label") or "").strip(),
            str(attrs.get("placeholder") or "").strip(),
            str(attrs.get("data-testid") or "").strip(),
            str(step.get("intent") or "").strip(),
        ]
        for candidate in candidates:
            if candidate:
                return candidate[:160]
        return "step"

    def _step_context_text(self, step: dict[str, Any]) -> str:
        element_info = self._resolve_selected_element_info(step.get("element_info") or {})
        attrs = element_info.get("attributes") or {}
        parts = [
            str(step.get("intent") or "").strip(),
            str(step.get("element_name") or "").strip(),
            self._selected_element_text(element_info),
            str(attrs.get("aria-label") or "").strip(),
            str(attrs.get("placeholder") or "").strip(),
            str(attrs.get("data-testid") or "").strip(),
            str(element_info.get("id") or "").strip(),
        ]
        return self._normalize_space(" ".join(part for part in parts if part))

    def _score_step_context(
        self,
        step: dict[str, Any],
        locator_hint: str,
        intent_hint: str,
        element_text_hint: str,
    ) -> int:
        score = 0
        step_blob = self._step_context_text(step).lower()
        if intent_hint and (intent_hint in step_blob or step_blob in intent_hint):
            score += 4
        if element_text_hint and (element_text_hint in step_blob or step_blob in element_text_hint):
            score += 3
        if locator_hint:
            if locator_hint in step_blob or step_blob in locator_hint:
                score += 4
            for candidate in (
                str(step.get("element_name") or "").strip().lower(),
                self._normalize_space(
                    str((step.get("element_info") or {}).get("text") or "")
                ).lower(),
            ):
                if candidate and (candidate in locator_hint or locator_hint in candidate):
                    score += 2
                    break
        if 0 <= self.current_step_index < len(self._recording_steps):
            try:
                if int(step.get("step_number") or 0) - 1 == self.current_step_index:
                    score += 1
            except (TypeError, ValueError):
                pass
        return score

    def _resolve_step_context(
        self,
        tool_name: str,
        args: dict[str, Any],
        result: dict[str, Any],
    ) -> dict[str, Any] | None:
        confirmed_cursor = self._current_confirmed_execution_cursor()
        if isinstance(confirmed_cursor, dict):
            step_context = confirmed_cursor.get("step_context")
            if isinstance(step_context, dict):
                return step_context

        explicit_step_id = str(args.get("step_id") or result.get("step_id") or "").strip()
        if explicit_step_id and explicit_step_id in self.step_context_by_id:
            return self.step_context_by_id[explicit_step_id]

        explicit_step_number = self._coerce_step_number(args.get("step_number") or result.get("step_number"))
        if explicit_step_number is not None:
            for step in self._recording_steps:
                if int(step.get("step_number") or 0) == explicit_step_number:
                    return step

        pending_steps = [step for step in self._recording_steps if not step.get("recorded")]
        if len(pending_steps) == 1:
            return pending_steps[0]

        locator = str(args.get("locator") or result.get("locator") or "").strip()
        locator_hint = self._normalize_space(self._locator_label_hint(locator) or locator).lower()
        intent_hint = self._normalize_space(
            str(args.get("intent") or result.get("intent") or self._action_name_for_tool(tool_name) or "")
        ).lower()
        element_text_hint = self._normalize_space(
            str(
                args.get("element_text")
                or args.get("element_name")
                or result.get("element_text")
                or result.get("element_name")
                or ""
            )
        ).lower()

        candidate_steps = pending_steps or self._recording_steps
        best_step: dict[str, Any] | None = None
        best_score = 0
        for step in candidate_steps:
            if step.get("recorded"):
                continue
            score = self._score_step_context(step, locator_hint, intent_hint, element_text_hint)
            if score > best_score:
                best_score = score
                best_step = step
        if best_step is not None and best_score > 0:
            return best_step

        if 0 <= self.current_step_index < len(self._recording_steps):
            current_step = self._recording_steps[self.current_step_index]
            if not current_step.get("recorded"):
                return current_step

        return None

    def _has_successful_action_to_record(
        self,
        step_context: dict[str, Any] | None = None,
        payload: dict[str, Any] | None = None,
    ) -> bool:
        confirmed_cursor = self._current_confirmed_execution_cursor()
        if isinstance(confirmed_cursor, dict):
            return self._confirmed_execution_step_ready_to_record(confirmed_cursor.get("step_context"))
        if self._confirmed_execution_contract_for_step(step_context or payload) is not None:
            return self._confirmed_execution_step_ready_to_record(step_context or payload)
        action = self._get_successful_action_for_step(step_context, payload)
        if not action:
            return False
        result = action.get("result") or {}
        return result.get("success") is True and not result.get("skipped")

    def _should_block_additional_execution_action(
        self,
        tool_name: str,
        args: dict[str, Any],
    ) -> bool:
        if tool_name not in self.EXECUTION_TOOLS:
            return False
        if not getattr(self, "_recording_wait_guard_armed", False):
            return False

        history_by_step_id = getattr(self, "successful_actions_by_step_id", None)
        if not isinstance(history_by_step_id, dict):
            return True

        active_step_id = str(getattr(self, "active_step_id", "") or "").strip()
        step_context = self.step_state_by_id.get(active_step_id) if active_step_id else None
        if step_context is None:
            step_context = self._resolve_step_context(tool_name, args, {})
        if step_context is None:
            return True

        resolved_step_id = str(step_context.get("step_id") or "").strip()
        if not resolved_step_id:
            return True
        if active_step_id and resolved_step_id != active_step_id:
            return True

        return False

    async def _record_step_payload(
        self,
        payload: dict[str, Any],
        step_context: dict[str, Any] | None = None,
    ) -> dict[str, Any] | None:
        confirmed_cursor = self._current_confirmed_execution_cursor()
        confirmed_mode = isinstance(confirmed_cursor, dict)
        if confirmed_mode:
            target_step = confirmed_cursor.get("step_context")
        else:
            target_step = step_context or self._resolve_recording_target_step(payload)
        if not self._has_successful_action_to_record(target_step, payload):
            step_ref = str(
                (target_step or {}).get("step_id")
                or payload.get("step_id")
                or payload.get("id")
                or payload.get("stepId")
                or "unknown"
            ).strip() or "unknown"
            if self._confirmed_execution_contract_for_step(target_step or payload) is not None:
                print(f"[AGENT] confirmed execution contract not ready for recorded step: {step_ref}")
            else:
                print(f"[AGENT] no successful action context for recorded step: {step_ref}")
            return None

        recorded_payload = self._build_step_record_payload(payload, target_step)
        if not recorded_payload:
            return None

        step_id = str((target_step or {}).get("step_id") or recorded_payload.get("step_id") or "").strip()
        if step_id:
            print(f"[AGENT] using successful action for recorded step: {step_id}")
        print(f"[AGENT] recording step: {json.dumps(recorded_payload, ensure_ascii=True)}")

        await self._send("step_recorded", **recorded_payload)
        self._append_recorded_step_payload(recorded_payload)

        recorded_target_step = self.step_state_by_id.get(step_id) if step_id else None
        if recorded_target_step is not None and str(recorded_target_step.get("status") or "") in {"recorded", "skipped"}:
            recorded_target_step = None
        if recorded_target_step is None and target_step is not None:
            target_step_id = str(target_step.get("step_id") or "").strip()
            if not step_id or target_step_id == step_id:
                recorded_target_step = target_step
        step_number = self._coerce_step_number(recorded_payload.get("step_number"))
        if not confirmed_mode and recorded_target_step is None and (step_id or step_number is not None):
            recorded_target_step = self._find_step_for_recording(
                step_id or None,
                step_number,
            )
        if not confirmed_mode and recorded_target_step is None:
            unresolved_steps = [
                step
                for step in self._recording_steps
                if str(step.get("status") or "") not in {"recorded", "skipped"}
            ]
            if len(unresolved_steps) == 1:
                recorded_target_step = unresolved_steps[0]
        if confirmed_mode and recorded_target_step is None:
            recorded_target_step = target_step
        if recorded_target_step is not None:
            self._mark_step_recorded(recorded_target_step, recorded_payload)
            code_update_payload = self._build_code_update_payload(recorded_payload, step_id)
            if code_update_payload:
                try:
                    await self._send("code_update", **code_update_payload)
                    self._append_code_update_payload(code_update_payload)
                    print(
                        f"[CODE_UPDATE] step_id={step_id} "
                        f"operation_id={code_update_payload.get('operation_id') or 'op_1'} "
                        f"lines={len(code_update_payload.get('lines') or [])}"
                    )
                except Exception as exc:  # noqa: BLE001
                    print(f"[AGENT] code_update emit failed: {type(exc).__name__}: {exc}")

        replay_recorded_step_payloads_by_step_id = getattr(
            self,
            "replay_recorded_step_payloads_by_step_id",
            None,
        )
        if not isinstance(replay_recorded_step_payloads_by_step_id, dict):
            replay_recorded_step_payloads_by_step_id = {}
            self.replay_recorded_step_payloads_by_step_id = replay_recorded_step_payloads_by_step_id
        if step_id:
            replay_recorded_step_payloads_by_step_id[step_id] = deepcopy(recorded_payload)
            history_by_step_id = getattr(self, "successful_actions_by_step_id", None)
            if isinstance(history_by_step_id, dict):
                history_by_step_id.pop(step_id, None)
            self.successful_action_by_step_id.pop(step_id, None)

        last_action = self.last_successful_action or {}
        last_action_step = last_action.get("step_context") or {}
        last_action_step_id = str(last_action_step.get("step_id") or last_action.get("step_id") or "").strip()
        last_action_step_number = self._coerce_step_number(
            last_action_step.get("step_number") or last_action.get("step_number")
        )
        recorded_step_number = self._coerce_step_number(recorded_payload.get("step_number"))
        if step_id and last_action_step_id == step_id:
            self.last_successful_action = None
        elif step_id and recorded_step_number is not None and last_action_step_number == recorded_step_number:
            self.last_successful_action = None
        elif not step_id and recorded_step_number is not None and last_action_step_number == recorded_step_number:
            self.last_successful_action = None

        self._awaiting_step_record = False
        self._recording_wait_guard_armed = False
        self._last_action_context = None
        if recorded_target_step is not None:
            recorded_step_id = str(
                (recorded_target_step or {}).get("step_id")
                or recorded_payload.get("step_id")
                or recorded_payload.get("id")
                or recorded_payload.get("stepId")
                or ""
            ).strip() or None
            if self._all_steps_resolved():
                self._run_completion_requested = True
                self.phase_tracker.set_phase(
                    "completed",
                    reason="all_steps_resolved",
                    step_id=recorded_step_id,
                )
            elif not self.pending_recovery and not self._pending_failure_followup:
                self.phase_tracker.set_phase(
                    "executing",
                    reason="step_recorded",
                    step_id=recorded_step_id,
                )

        return recorded_payload

    async def _auto_record_successful_step(self) -> dict[str, Any] | None:
        confirmed_cursor = self._current_confirmed_execution_cursor()
        if isinstance(confirmed_cursor, dict):
            target_step = confirmed_cursor.get("step_context")
        else:
            target_step = self._resolve_recording_target_step()
        if target_step is None:
            return None

        step_id = str(target_step.get("step_id") or "").strip()
        if not step_id:
            return None

        if not self._has_successful_action_to_record(
            target_step,
            {"step_id": step_id, "step_number": target_step.get("step_number")},
        ):
            return None

        print(f"[AGENT] auto-recording successful step: {step_id}")
        payload = {
            "step_id": step_id,
            "step_number": target_step.get("step_number"),
        }
        recorded_payload = await self._record_step_payload(payload, target_step)
        if recorded_payload:
            await self._emit_run_completed_event(payload, recorded_payload)
        return recorded_payload

    def _should_block_recording_wait_tool(
        self,
        tool_name: str,
        args: dict[str, Any],
    ) -> bool:
        if not getattr(self, "_recording_wait_guard_armed", False):
            return False
        if tool_name == "ask_user":
            return False
        if tool_name == "send_to_overlay":
            return str(args.get("message_type") or "").strip() != "step_recorded"
        return True

    def _get_successful_action_for_step(
        self,
        step_context: dict[str, Any] | None = None,
        payload: dict[str, Any] | None = None,
    ) -> dict[str, Any] | None:
        confirmed_cursor = self._current_confirmed_execution_cursor()
        if isinstance(confirmed_cursor, dict):
            strict_step_id = str(confirmed_cursor.get("step_id") or "").strip()
            if not strict_step_id:
                return None
            return self.successful_action_by_step_id.get(strict_step_id)

        payload = payload or {}
        step_context = step_context or {}

        candidate_step_ids: list[str] = []
        for source in (step_context, payload):
            if not isinstance(source, dict):
                continue
            for key in ("step_id", "id", "stepId"):
                candidate_step_id = str(source.get(key) or "").strip()
                if candidate_step_id and candidate_step_id not in candidate_step_ids:
                    candidate_step_ids.append(candidate_step_id)

        for candidate_step_id in candidate_step_ids:
            action_record = self.successful_action_by_step_id.get(candidate_step_id)
            if action_record is not None:
                return action_record

        candidate_step_number = self._coerce_step_number(
            step_context.get("step_number") if isinstance(step_context, dict) else None
        )
        if candidate_step_number is None:
            candidate_step_number = self._coerce_step_number(payload.get("step_number"))
        if candidate_step_number is not None:
            matching_records = [
                action_record
                for action_record in self.successful_action_by_step_id.values()
                if self._coerce_step_number((action_record.get("step_context") or {}).get("step_number"))
                == candidate_step_number
            ]
            if len(matching_records) == 1:
                return matching_records[0]
            if len(matching_records) > 1:
                return None

        if not candidate_step_ids and candidate_step_number is None:
            if len(self.successful_action_by_step_id) == 1:
                return next(iter(self.successful_action_by_step_id.values()))
            if len(self.successful_action_by_step_id) == 0:
                last_action = self.last_successful_action or {}
                if last_action:
                    return last_action
            return None

        last_action = self.last_successful_action or {}
        if not last_action:
            return None

        last_step_context = last_action.get("step_context") or {}
        last_step_id = str(last_step_context.get("step_id") or last_action.get("step_id") or "").strip()
        last_step_number = self._coerce_step_number(last_step_context.get("step_number") or last_action.get("step_number"))
        if candidate_step_ids and last_step_id and last_step_id in candidate_step_ids:
            return last_action
        if candidate_step_number is not None and last_step_number == candidate_step_number:
            return last_action
        return None

    def _get_successful_action_history_for_step(
        self,
        step_context: dict[str, Any] | None = None,
        payload: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        confirmed_cursor = self._current_confirmed_execution_cursor()
        if isinstance(confirmed_cursor, dict):
            strict_step_id = str(confirmed_cursor.get("step_id") or "").strip()
            if not strict_step_id:
                return []
            history_by_step_id = getattr(self, "successful_actions_by_step_id", None)
            if not isinstance(history_by_step_id, dict):
                return []
            action_history = history_by_step_id.get(strict_step_id)
            if isinstance(action_history, list):
                return action_history
            return []

        payload = payload or {}
        step_context = step_context or {}
        history_by_step_id = getattr(self, "successful_actions_by_step_id", None)
        if not isinstance(history_by_step_id, dict):
            return []

        candidate_step_ids: list[str] = []
        for source in (step_context, payload):
            if not isinstance(source, dict):
                continue
            for key in ("step_id", "id", "stepId"):
                candidate_step_id = str(source.get(key) or "").strip()
                if candidate_step_id and candidate_step_id not in candidate_step_ids:
                    candidate_step_ids.append(candidate_step_id)

        for candidate_step_id in candidate_step_ids:
            action_history = history_by_step_id.get(candidate_step_id)
            if isinstance(action_history, list):
                return action_history

        return []

    def _coerce_step_number(self, value: Any) -> int | None:
        try:
            number = int(value)
        except (TypeError, ValueError):
            return None
        return number if number > 0 else None

    async def _capture_browser_state(self) -> dict[str, str] | None:
        try:
            page = get_page()
        except Exception:  # noqa: BLE001
            return None

        try:
            page_url = str(page.url or "")
        except Exception:  # noqa: BLE001
            return None

        try:
            page_title = str(await page.title() or "")
        except Exception:  # noqa: BLE001
            page_title = ""

        return {"url": page_url, "title": page_title}

    def _normalize_browser_state_snapshot(self, browser_state: Any) -> dict[str, str] | None:
        if not isinstance(browser_state, dict):
            return None
        return {
            "url": str(browser_state.get("url") or ""),
            "title": str(browser_state.get("title") or ""),
        }

    def _build_observed_outcome(
        self,
        action_history: list[dict[str, Any]],
        expected_outcome: Any,
    ) -> dict[str, Any]:
        before_state = None
        after_state = None
        if action_history:
            first_action = action_history[0]
            if isinstance(first_action, dict):
                before_state = self._normalize_browser_state_snapshot(first_action.get("browser_state_before"))
            last_action = action_history[-1]
            if isinstance(last_action, dict):
                after_state = self._normalize_browser_state_snapshot(last_action.get("browser_state_after"))

        before_url = before_state.get("url") if before_state is not None else None
        after_url = after_state.get("url") if after_state is not None else None
        before_title = before_state.get("title") if before_state is not None else None
        after_title = after_state.get("title") if after_state is not None else None

        observed_type = "unknown"
        if before_state is not None and after_state is not None:
            if before_url != after_url:
                observed_type = "navigation"
            elif before_title == after_title:
                observed_type = "no_visible_change"

        expected_type = ""
        if isinstance(expected_outcome, dict):
            expected_type = self._normalize_space(str(expected_outcome.get("type") or "")).strip().lower()

        matched_expected: bool | None = None
        if observed_type != "unknown" and expected_type and expected_type != "not_sure":
            matched_expected = observed_type == expected_type

        return {
            "type": observed_type,
            "before_url": before_url,
            "after_url": after_url,
            "before_title": before_title,
            "after_title": after_title,
            "matched_expected": matched_expected,
        }

    def _capture_action_context(
        self,
        tool_name: str,
        args: dict[str, Any],
        result: dict[str, Any],
        browser_state_before: dict[str, str] | None = None,
        browser_state_after: dict[str, str] | None = None,
    ) -> None:
        action = self._action_name_for_tool(tool_name)
        if not action:
            return
        step_context = self._resolve_step_context(tool_name, args, result)
        action_context: dict[str, Any] = {
            "locator": str(args.get("locator") or result.get("locator") or "").strip(),
        }
        if "value" in args:
            action_context["value"] = args.get("value")
        if "assertion" in args:
            action_context["assertion"] = str(args.get("assertion") or "").strip()
        if "expected_value" in args:
            action_context["expected_value"] = args.get("expected_value")
        elif action == "assert" and action_context.get("assertion") in {"has_text", "has_value"} and "value" in args:
            action_context["expected_value"] = args.get("value")
        if "url" in args:
            action_context["url"] = str(args.get("url") or "").strip()
        if "wait_until" in args:
            action_context["wait_until"] = str(args.get("wait_until") or "").strip()
        if "filename" in args:
            action_context["filename"] = str(args.get("filename") or "").strip()
        if result.get("url") and not action_context.get("url"):
            action_context["url"] = str(result.get("url") or "").strip()

        if step_context is not None:
            self.current_step_index = max(0, int(step_context.get("step_number") or 1) - 1)

        captured: dict[str, Any] = {
            "tool": tool_name,
            "action": action,
            "locator": action_context.get("locator", ""),
            "result": dict(result),
            "step_context": dict(step_context) if step_context is not None else None,
            "action_context": action_context,
            "tool_args": dict(args),
        }
        step_id = str((step_context or {}).get("step_id") or "").strip()
        if step_id:
            captured["step_id"] = step_id
            captured["step_number"] = self._coerce_step_number((step_context or {}).get("step_number"))
        if "value" in args:
            captured["value"] = args.get("value")
        if "assertion" in args:
            captured["assertion"] = str(args.get("assertion") or "").strip()
        if "expected_value" in args:
            captured["expected_value"] = args.get("expected_value")
        elif action == "assert" and captured.get("assertion") in {"has_text", "has_value"} and "value" in args:
            captured["expected_value"] = args.get("value")
        if "wait_until" in args:
            captured["wait_until"] = str(args.get("wait_until") or "").strip()
        if "filename" in args:
            captured["filename"] = str(args.get("filename") or "").strip()
        normalized_browser_state_before = self._normalize_browser_state_snapshot(browser_state_before)
        if normalized_browser_state_before is not None:
            captured["browser_state_before"] = normalized_browser_state_before
        normalized_browser_state_after = self._normalize_browser_state_snapshot(browser_state_after)
        if normalized_browser_state_after is not None:
            captured["browser_state_after"] = normalized_browser_state_after
        generated_line = self._build_generated_line(action, str(action_context.get("locator") or ""), action_context)
        if generated_line:
            captured["generated_line"] = generated_line

        self.last_successful_action = captured
        if step_id:
            history_by_step_id = getattr(self, "successful_actions_by_step_id", None)
            if not isinstance(history_by_step_id, dict):
                history_by_step_id = {}
                self.successful_actions_by_step_id = history_by_step_id
            step_history = history_by_step_id.get(step_id)
            if not isinstance(step_history, list):
                step_history = []
                history_by_step_id[step_id] = step_history
            step_history.append(captured)
            self.successful_action_by_step_id[step_id] = captured
            replay_action_history_by_step_id = getattr(self, "replay_action_history_by_step_id", None)
            if not isinstance(replay_action_history_by_step_id, dict):
                replay_action_history_by_step_id = {}
                self.replay_action_history_by_step_id = replay_action_history_by_step_id
            replay_action_history_by_step_id[step_id] = deepcopy(step_history)
            print(f"[AGENT] stored successful action for step: {step_id}")
        else:
            print("[AGENT] stored successful action without step id")
        self._last_action_context = action_context
        confirmed_contract = self._confirmed_execution_contract_for_step(step_context or step_id)
        if isinstance(confirmed_contract, dict):
            if self._confirmed_execution_step_ready_to_record(step_context or step_id):
                self._awaiting_step_record = True
                self.phase_tracker.set_phase("recording", reason="action_success", step_id=step_id)
            else:
                self._awaiting_step_record = False
                self.phase_tracker.set_phase("executing", reason="child_success", step_id=step_id)
        else:
            self._awaiting_step_record = True
            self.phase_tracker.set_phase("recording", reason="action_success", step_id=step_id)

    def _action_name_for_tool(self, tool_name: str) -> str:
        if tool_name == "page_navigate":
            return "navigate"
        if tool_name == "page_go_back":
            return "go back"
        if tool_name == "page_go_forward":
            return "go forward"
        if tool_name == "page_reload":
            return "reload"
        if tool_name == "scroll_into_view":
            return "scroll"
        if tool_name.startswith("action_"):
            return tool_name.removeprefix("action_")
        return ""

    def _current_pending_step(self) -> dict[str, Any] | None:
        confirmed_cursor = self._current_confirmed_execution_cursor()
        if isinstance(confirmed_cursor, dict):
            step_context = confirmed_cursor.get("step_context")
            if isinstance(step_context, dict):
                return step_context

        self._advance_recording_cursor()
        if self._recording_step_index >= len(self._recording_steps):
            return None
        step = self._recording_steps[self._recording_step_index]
        self.current_step_index = self._recording_step_index
        if step.get("recorded") or str(step.get("status") or "") == "skipped":
            return None
        step_id = str(step.get("step_id") or "").strip()
        if step_id and (step_id in self._recorded_step_ids or step_id in self.skipped_step_ids):
            return None
        return step

    def _find_step_for_recording(
        self,
        step_id: str | None = None,
        step_number: int | None = None,
    ) -> dict[str, Any] | None:
        confirmed_cursor = self._current_confirmed_execution_cursor()
        if isinstance(confirmed_cursor, dict):
            current_step_context = confirmed_cursor.get("step_context")
            current_step_id = str(confirmed_cursor.get("step_id") or "").strip()
            current_contract = confirmed_cursor.get("contract")
            current_step_number = self._coerce_step_number(
                current_contract.get("step_number") if isinstance(current_contract, dict) else None
            )
            if step_id:
                if step_id != current_step_id:
                    return None
                return current_step_context if isinstance(current_step_context, dict) else None
            if step_number is not None:
                if current_step_number != step_number:
                    return None
                return current_step_context if isinstance(current_step_context, dict) else None
            return current_step_context if isinstance(current_step_context, dict) else None

        if step_id:
            for step in self._recording_steps:
                if (
                    str(step.get("step_id") or "").strip() == step_id
                    and not step.get("recorded")
                    and str(step.get("status") or "") != "skipped"
                ):
                    return step
            return None

        if step_number is not None:
            for step in self._recording_steps:
                if (
                    int(step.get("step_number") or 0) == step_number
                    and not step.get("recorded")
                    and str(step.get("status") or "") != "skipped"
                ):
                    return step
            return None

        return self._current_pending_step()

    def _advance_recording_cursor(self) -> None:
        while self._recording_step_index < len(self._recording_steps):
            step = self._recording_steps[self._recording_step_index]
            if step.get("recorded") or str(step.get("status") or "") == "skipped":
                self._recording_step_index += 1
                continue
            step_id = str(step.get("step_id") or "").strip()
            if step_id and (step_id in self._recorded_step_ids or step_id in self.skipped_step_ids):
                self._recording_step_index += 1
                continue
            break
        if self._recording_step_index < len(self._recording_steps):
            self.current_step_index = self._recording_step_index
        elif self._recording_steps:
            self.current_step_index = len(self._recording_steps) - 1

    def _mark_step_recorded(
        self,
        step: dict[str, Any] | str | None,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any] | None:
        context = self._get_step_context(step) if not isinstance(step, dict) else step
        if context is None:
            return None

        step_id = str(context.get("step_id") or "").strip()
        if not step_id:
            return None

        metadata = dict(metadata or {})
        context["recorded"] = True
        context["status"] = "recorded"
        context["last_error"] = None
        for key in ("step_number", "action", "locator", "element_name", "generated_line"):
            if key in metadata and metadata.get(key) not in (None, "", [], {}):
                context[key] = metadata.get(key)
        if metadata.get("locator"):
            context["locator"] = str(metadata.get("locator") or "").strip() or context.get("locator")
        if metadata.get("element_name"):
            context["element_name"] = str(metadata.get("element_name") or "").strip() or context.get("element_name")
        self.completed_step_ids.add(step_id)
        self.skipped_step_ids.discard(step_id)
        self._recorded_step_ids.add(step_id)
        if self.active_failed_step_id == step_id:
            self.active_failed_step_id = None
            self.pending_recovery = False
            self._pending_failure_followup = False
        if self.active_step_id == step_id:
            self.active_step_id = None
        if self.plan_confirmed:
            self.phase = "executing"
        print(f"[AGENT] marked step recorded: {step_id}")
        self._advance_recording_cursor()
        self._log_confirmed_execution_cursor("[CONFIRMED_CURSOR]")
        return context

    def _derive_element_name(
        self,
        step: dict[str, Any],
        action_context: dict[str, Any],
        locator: str,
    ) -> str:
        element_info = self._resolve_selected_element_info(step.get("element_info") or {})
        attrs = element_info.get("attributes") or {}
        candidates = [
            self._selected_element_text(element_info),
            str(attrs.get("aria-label") or "").strip(),
            str(attrs.get("placeholder") or "").strip(),
            str(attrs.get("data-testid") or "").strip(),
            str(step.get("intent") or "").strip(),
            self._locator_label_hint(locator),
            str(action_context.get("locator") or "").strip(),
        ]
        for candidate in candidates:
            if candidate:
                return candidate[:160]
        return "step"

    def _locator_label_hint(self, locator: str) -> str:
        locator = str(locator or "").strip()
        if not locator:
            return ""

        if match := self._match_tool_locator_call(locator, "get_by_test_id"):
            return match
        if match := self._match_tool_locator_call(locator, "get_by_label"):
            return match
        if match := self._match_tool_locator_call(locator, "get_by_placeholder"):
            return match
        if match := self._match_tool_locator_text(locator):
            return match[0]
        if match := self._match_tool_locator_role(locator):
            return match[1]

        if locator.startswith("#"):
            return locator[1:]
        return ""

    def _canonical_confirmed_execution_locator(self, locator: str) -> str:
        locator = str(locator or "").strip()
        if not locator:
            return ""

        if match := self._match_tool_locator_call(locator, "get_by_test_id"):
            return f'get_by_test_id({json.dumps(match, ensure_ascii=True)})'

        if match := self._match_tool_locator_call(locator, "get_by_label"):
            return f'get_by_label({json.dumps(match, ensure_ascii=True)})'

        if match := self._match_tool_locator_call(locator, "get_by_placeholder"):
            return f'get_by_placeholder({json.dumps(match, ensure_ascii=True)})'

        if match := self._match_tool_locator_text(locator):
            text, exact = match
            return f'get_by_text({json.dumps(text, ensure_ascii=True)}, exact={str(exact).lower()})'

        if match := self._match_tool_locator_role(locator):
            role, name = match
            return f'get_by_role({json.dumps(role, ensure_ascii=True)}, name={json.dumps(name, ensure_ascii=True)})'

        if locator.startswith("#"):
            return f"#{locator[1:]}"
        return self._normalize_space(locator).strip()

    def _match_tool_locator_call(self, locator: str, function_name: str) -> str:
        return _locator_resolver.match_tool_locator_call(locator, function_name)
    def _match_tool_locator_text(self, locator: str) -> tuple[str, bool] | None:
        return _locator_resolver.match_tool_locator_text(locator)
    def _match_tool_locator_role(self, locator: str) -> tuple[str, str] | None:
        return _locator_resolver.match_tool_locator_role(locator)
    def _build_generated_line(
        self,
        action: str,
        locator: str,
        action_context: dict[str, Any],
    ) -> str:
        action = str(action or "").strip().lower()
        locator_expr = self._locator_to_playwright_expression(locator)

        if action == "click":
            if not locator_expr:
                locator_expr = "page.locator(\"\")"
            return f"await {locator_expr}.click();"
        if action == "fill":
            if not locator_expr:
                locator_expr = "page.locator(\"\")"
            return f"await {locator_expr}.fill({json.dumps(str(action_context.get('value') or ''), ensure_ascii=True)});"
        if action == "navigate":
            url = str(action_context.get("url") or "").strip()
            return f"await page.goto({json.dumps(url, ensure_ascii=True)});"
        if action == "go back":
            wait_until = str(action_context.get("wait_until") or "domcontentloaded").strip() or "domcontentloaded"
            return f'await page.goBack({{ waitUntil: {json.dumps(wait_until, ensure_ascii=True)} }});'
        if action == "go forward":
            wait_until = str(action_context.get("wait_until") or "domcontentloaded").strip() or "domcontentloaded"
            return f'await page.goForward({{ waitUntil: {json.dumps(wait_until, ensure_ascii=True)} }});'
        if action == "reload":
            wait_until = str(action_context.get("wait_until") or "domcontentloaded").strip() or "domcontentloaded"
            return f'await page.reload({{ waitUntil: {json.dumps(wait_until, ensure_ascii=True)} }});'
        if action == "scroll":
            if not locator_expr:
                locator_expr = "page.locator(\"\")"
            return f"await {locator_expr}.scrollIntoViewIfNeeded();"
        if action == "assert":
            if not locator_expr:
                locator_expr = "page.locator(\"\")"
            assertion = str(action_context.get("assertion") or "").strip()
            if assertion in {"exact_text", "text_equal", "text_equals", "contains_text", "includes_text"}:
                assertion = "has_text"
            if assertion == "visible":
                return f"await expect({locator_expr}).toBeVisible();"
            if assertion == "hidden":
                return f"await expect({locator_expr}).toBeHidden();"
            if assertion == "enabled":
                return f"await expect({locator_expr}).toBeEnabled();"
            if assertion == "disabled":
                return f"await expect({locator_expr}).toBeDisabled();"
            if assertion == "checked":
                return f"await expect({locator_expr}).toBeChecked();"
            if assertion == "has_value":
                expected_value = str(action_context.get("expected_value") or action_context.get("value") or "").strip()
                if not expected_value:
                    return ""
                return (
                    f"await expect({locator_expr}).toHaveValue("
                    f"{json.dumps(expected_value, ensure_ascii=True)});"
                )
            if assertion == "has_text":
                expected_value = str(action_context.get("expected_value") or action_context.get("value") or "").strip()
                if not expected_value:
                    return ""
                return (
                    f"await expect({locator_expr}).toContainText("
                    f"{json.dumps(expected_value, ensure_ascii=True)});"
                )
            return f"await expect({locator_expr}).toBeVisible();"
        if not locator_expr:
            locator_expr = "page.locator(\"\")"
        return f"await {locator_expr}.{action}();"

    def _locator_to_playwright_expression(self, locator: str) -> str:
        locator = str(locator or "").strip()
        if not locator:
            return ""

        if match := self._match_tool_locator_call(locator, "get_by_test_id"):
            return f'page.getByTestId({json.dumps(match, ensure_ascii=True)})'

        if match := self._match_tool_locator_call(locator, "get_by_label"):
            return f'page.getByLabel({json.dumps(match, ensure_ascii=True)})'

        if match := self._match_tool_locator_call(locator, "get_by_placeholder"):
            return f'page.getByPlaceholder({json.dumps(match, ensure_ascii=True)})'

        if match := self._match_tool_locator_text(locator):
            text, exact = match
            return f'page.getByText({json.dumps(text, ensure_ascii=True)}, {{ exact: {str(exact).lower()} }})'

        if match := self._match_tool_locator_role(locator):
            role, name = match
            return (
                f'page.getByRole({json.dumps(role, ensure_ascii=True)}, '
                f'{{ name: {json.dumps(name, ensure_ascii=True)} }})'
            )

        if locator.startswith("#") and len(locator) > 1:
            return f'page.getByTestId({json.dumps(locator[1:], ensure_ascii=True)})'

        return f'page.locator({json.dumps(locator, ensure_ascii=True)})'

    def _build_step_record_payload(
        self,
        payload: dict[str, Any],
        step_context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        clean_payload = {
            key: value
            for key, value in payload.items()
            if value not in (None, "", [], {})
        }
        confirmed_cursor = self._current_confirmed_execution_cursor()
        confirmed_mode = isinstance(confirmed_cursor, dict)
        if confirmed_mode:
            step_context = confirmed_cursor.get("step_context")
            confirmed_contract = confirmed_cursor.get("contract")
        else:
            step_context = step_context or self._resolve_recording_target_step(clean_payload)
            confirmed_contract = self._confirmed_execution_contract_for_step(step_context or clean_payload)
        confirmed_child_results: dict[str, Any] = {}
        if isinstance(confirmed_contract, dict):
            if not self._confirmed_execution_step_ready_to_record(step_context or clean_payload):
                return {}
            confirmed_step_id = str(confirmed_contract.get("step_id") or "").strip()
            confirmed_child_results = self._confirmed_execution_results_for_step(confirmed_step_id)
        action_history = self._get_successful_action_history_for_step(step_context, clean_payload)
        if action_history:
            action_record = action_history[-1]
        else:
            action_record = self._get_successful_action_for_step(step_context, clean_payload)
            if action_record:
                action_history = [action_record]
            elif isinstance(confirmed_contract, dict):
                confirmed_step_id = str(confirmed_contract.get("step_id") or "").strip()
                confirmed_step_results = self._confirmed_execution_results_for_step(confirmed_step_id)
                confirmed_children = confirmed_contract.get("children")
                if isinstance(confirmed_children, list):
                    for confirmed_child in reversed(confirmed_children):
                        if not isinstance(confirmed_child, dict):
                            continue
                        operation_id = str(confirmed_child.get("operation_id") or "").strip()
                        child_result = confirmed_step_results.get(operation_id)
                        if isinstance(child_result, dict) and str(child_result.get("status") or "").strip().lower() == "success":
                            action_record = child_result
                            action_history = [child_result]
                            break
        if not action_record:
            step_ref = str(
                (step_context or {}).get("step_id")
                or clean_payload.get("step_id")
                or clean_payload.get("id")
                or clean_payload.get("stepId")
                or "unknown"
            ).strip() or "unknown"
            print(f"[AGENT] no successful action context for recorded step: {step_ref}")
            return {}
        result = action_record.get("result") or {}
        if result.get("success") is not True or result.get("skipped"):
            return {}

        action_context = dict(action_record.get("action_context") or {})
        recorded_step_context = action_record.get("step_context") or {}
        if recorded_step_context:
            step_context = recorded_step_context

        step_id = str(
            (step_context.get("step_id") if step_context else "")
            or (recorded_step_context.get("step_id") if recorded_step_context else "")
            or action_record.get("step_id")
            or clean_payload.get("step_id")
            or ""
        ).strip()
        step_number = (
            self._coerce_step_number(clean_payload.get("step_number"))
            or self._coerce_step_number(recorded_step_context.get("step_number") if recorded_step_context else None)
            or self._coerce_step_number(step_context.get("step_number") if step_context else None)
            or self._coerce_step_number(action_record.get("step_number"))
        )

        action = str(
            action_record.get("action")
            or clean_payload.get("action")
            or self._action_name_for_tool(str(action_record.get("tool") or ""))
            or ""
        ).strip()
        locator = str(
            action_context.get("locator")
            or action_record.get("locator")
            or clean_payload.get("locator")
            or ""
        ).strip()
        if not locator and step_context is not None:
            locator = self._derive_locator_from_step_context(step_context)
        element_name = str(
            (step_context.get("element_name") if step_context else "")
            or (recorded_step_context.get("element_name") if recorded_step_context else "")
            or clean_payload.get("element_name")
            or self._derive_element_name(step_context or {}, action_context, locator)
            or ""
        ).strip()
        generated_line = str(
            self._build_generated_line(action, locator, action_context)
            or clean_payload.get("generated_line")
            or ""
        ).strip()
        intent = str(
            clean_payload.get("intent")
            or (recorded_step_context.get("intent") if recorded_step_context else "")
            or (step_context.get("intent") if step_context else "")
            or ""
        ).strip()
        expected_outcome = self._normalize_expected_outcome(
            clean_payload.get("expected_outcome")
            or clean_payload.get("expectedOutcome")
            or (recorded_step_context.get("expected_outcome") if recorded_step_context else None)
            or (recorded_step_context.get("expectedOutcome") if recorded_step_context else None)
            or (step_context.get("expected_outcome") if step_context else None)
            or (step_context.get("expectedOutcome") if step_context else None),
            self._is_click_like_intent(intent),
        )
        status = "success"

        if not action:
            action = "step"
        if not element_name:
            element_name = locator or action
        if not locator and step_context is not None:
            locator = self._derive_locator_from_step_context(step_context) or str(step_context.get("intent") or "").strip()
        if not generated_line:
            generated_line = self._build_generated_line(action, locator, action_context)
        if not intent:
            intent = str(step_context.get("intent") if step_context else "").strip()
        children = self._build_recorded_children(
            action_history,
            intent,
            element_name,
            locator,
            confirmed_children=(confirmed_contract or {}).get("children") if isinstance(confirmed_contract, dict) else None,
            confirmed_child_results=confirmed_child_results,
            confirmed_step=confirmed_contract if isinstance(confirmed_contract, dict) else None,
        )
        observed_outcome = self._build_observed_outcome(action_history, expected_outcome)

        merged: dict[str, Any] = dict(clean_payload)
        if step_id:
            merged["step_id"] = step_id
        else:
            merged.pop("step_id", None)
        if step_number is not None:
            merged["step_number"] = int(step_number)
        else:
            merged.pop("step_number", None)
        merged["action"] = action
        merged["element_name"] = element_name
        merged["locator"] = locator
        merged["generated_line"] = generated_line
        merged["status"] = status
        merged["intent"] = intent
        if expected_outcome is not None:
            merged["expected_outcome"] = expected_outcome
        else:
            merged.pop("expected_outcome", None)
        merged.pop("observed_outcome", None)
        merged.pop("browser_state_before", None)
        merged.pop("browser_state_after", None)
        merged["observed_outcome"] = observed_outcome
        merged["children"] = children

        required = ("action", "element_name", "locator", "generated_line")
        if not all(str(merged.get(key) or "").strip() for key in required):
            return {}

        return merged

    def _derive_locator_from_step_context(self, step: dict[str, Any]) -> str:
        element_info = self._resolve_selected_element_info(step.get("element_info") or {})
        if not isinstance(element_info, dict):
            return ""

        candidates = self._build_locator_candidates(element_info)
        for candidate in candidates:
            locator = str(candidate.get("locator") or "").strip()
            if locator:
                return locator

        return self._build_locator_from_strategy("css", element_info)

    def _normalize_steps(self, steps: list[dict]) -> list[dict[str, Any]]:
        normalized: list[dict[str, Any]] = []
        for idx, step in enumerate(steps, start=1):
            element_info = self._resolve_selected_element_info(step.get("element_info") or {})
            attrs = element_info.get("attributes") or {}
            normalized.append(
                {
                    "id": str(step.get("id") or idx),
                    "intent": str(step.get("intent") or "").strip(),
                    "element_data": {
                        "tag": element_info.get("tag", ""),
                        "text": element_info.get("text", ""),
                        "id": element_info.get("id", ""),
                        "class": element_info.get("class", ""),
                        "aria_label": attrs.get("aria-label", ""),
                        "data_testid": attrs.get("data-testid", ""),
                        "placeholder": attrs.get("placeholder", ""),
                        "parent_tag": element_info.get("parent_tag", ""),
                        "parent_id": element_info.get("parent_id", ""),
                    },
                    "suggested_scope": self._build_suggested_scope(element_info),
                    "raw_element_info": element_info,
                }
            )
        return normalized

    def _infer_operation_type(self, intent: str) -> str:
        normalized = self._normalize_space(str(intent or "")).lower()
        if not normalized:
            return "unknown"

        click_match = re.search(r"\b(?:click|tap|press)\b", normalized)
        assert_match = re.search(r"\b(?:assert|verify|check|expect)\b", normalized)
        fill_match = re.search(r"\b(?:fill|type|enter|input)\b", normalized)

        matches = [
            operation_type
            for operation_type, matched in (
                ("click", click_match),
                ("assert", assert_match),
                ("fill", fill_match),
            )
            if matched
        ]
        if len(matches) == 1:
            return matches[0]
        return "unknown"

    def _infer_planned_operation_sequence(self, intent: str) -> list[str]:
        normalized = self._normalize_space(str(intent or "")).lower()
        if not normalized:
            return []

        operation_patterns = (
            ("assert", r"\b(?:validate|check|assert|verify)\b"),
            ("click", r"\b(?:click|tap|press)\b"),
            ("fill", r"\b(?:fill|type|enter|input)\b"),
        )
        matched_operations: list[tuple[int, str]] = []
        for operation_type, pattern in operation_patterns:
            match = re.search(pattern, normalized)
            if match:
                matched_operations.append((match.start(), operation_type))

        matched_operations.sort(key=lambda item: item[0])
        return [operation_type for _, operation_type in matched_operations]

    def _build_planned_child_description(self, operation_type: str, target: str, intent: str) -> str:
        target_text = self._normalize_space(str(target or "")).strip()
        intent_text = self._normalize_space(str(intent or "")).lower()

        if operation_type == "assert":
            if target_text:
                if any(keyword in intent_text for keyword in ("disabled", "enabled", "checked", "hidden")):
                    if "disabled" in intent_text:
                        return f"{target_text} is disabled"
                    if "enabled" in intent_text:
                        return f"{target_text} is enabled"
                    if "checked" in intent_text:
                        return f"{target_text} is checked"
                    if "hidden" in intent_text:
                        return f"{target_text} is hidden"
                return f"{target_text} is visible"
            return "Assert"

        if operation_type == "click":
            return target_text or "Click"

        if operation_type == "fill":
            return target_text or "Fill"

        if operation_type == "navigate":
            return target_text or "Navigate"

        if operation_type == "hover":
            return target_text or "Hover"

        return target_text or operation_type

    def _build_planned_children(
        self,
        step: dict[str, Any],
        existing_plan_data: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        step_data = step if isinstance(step, dict) else {}
        plan_data = existing_plan_data if isinstance(existing_plan_data, dict) else {}

        intent = str(
            step_data.get("intent")
            or plan_data.get("intent")
            or plan_data.get("description")
            or plan_data.get("text")
            or ""
        ).strip()
        action_hint = str(step_data.get("action") or plan_data.get("action") or "").strip()
        operation_hint = " ".join(
            part for part in (action_hint, intent, str(plan_data.get("description") or "").strip()) if part
        )
        operation_type = self._infer_operation_type(operation_hint)
        target = str(
            plan_data.get("target")
            or plan_data.get("element_name")
            or step_data.get("element_name")
            or ""
        ).strip()
        locator = str(
            plan_data.get("locator")
            or step_data.get("locator")
            or self._derive_locator_from_step_context(step_data)
            or ""
        ).strip()
        if locator in {"*", 'page.locator("")'}:
            locator = ""
        operation_types = self._infer_planned_operation_sequence(intent or operation_hint)
        if not operation_types:
            operation_types = [operation_type]
        if any(current_operation_type == "unknown" for current_operation_type in operation_types):
            self._record_capability_gap(
                "unknown_planned_operation",
                "_build_planned_children",
                "warn",
                "Planned child operation fell back to unknown.",
                operation_type=operation_type,
                planned_child_count=len(operation_types),
            )

        planned_children: list[dict[str, Any]] = []
        for index, current_operation_type in enumerate(operation_types, start=1):
            child_target = target
            child_locator = locator
            child_description = self._build_planned_child_description(current_operation_type, child_target, intent)
            child_value = ""
            child_assertion = ""
            if current_operation_type in {"click", "fill"}:
                if self._is_technical_recorded_label_text(child_target):
                    human_target = self._normalize_space(str(step_data.get("element_name") or "")).strip()
                    if not human_target:
                        human_target = self._normalize_space(
                            self._selected_element_text(step_data.get("element_info") or {})
                        ).strip()
                    if not human_target:
                        human_target = self._normalize_space(self._locator_label_hint(child_locator)).strip()
                    if human_target and not self._is_technical_recorded_label_text(human_target):
                        child_target = human_target
                        child_description = self._build_planned_child_description(
                            current_operation_type,
                            child_target,
                            intent,
                        )
            if current_operation_type == "assert":
                canonical_child = self._canonicalize_assertion_operation(
                    {
                        "type": current_operation_type,
                        "target": target,
                        "locator": locator,
                        "description": intent,
                        "intent": intent,
                    },
                    source_step=step_data,
                    anchor_child=plan_data,
                )
                if canonical_child:
                    child_target = str(canonical_child.get("target") or child_target or "").strip()
                    child_locator = str(canonical_child.get("locator") or child_locator or "").strip()
                    child_description = str(canonical_child.get("description") or child_description or "").strip()
                    child_assertion = str(canonical_child.get("assertion") or "").strip().lower()
                    child_value = str(
                        canonical_child.get("value") or canonical_child.get("expected_value") or ""
                    ).strip()
                if current_operation_type == "assert":
                    source_element_name = self._normalize_space(str(step_data.get("element_name") or "")).strip()
                    if (
                        source_element_name
                        and source_element_name not in {"main", "page", "body", "document"}
                        and source_element_name in child_target
                        and len(source_element_name) < len(child_target)
                    ):
                        child_target = source_element_name
                        child_description = self._build_planned_child_description(
                            current_operation_type,
                            child_target,
                            intent,
                        )
                if child_assertion == "visible":
                    locator_target_hint = self._normalize_space(self._locator_label_hint(child_locator)).strip()
                    if locator_target_hint and not self._is_outcome_like_label(locator_target_hint):
                        if locator_target_hint.lower() not in {"main", "page", "body", "document"}:
                            child_target = locator_target_hint
                            child_description = self._build_planned_child_description(
                                current_operation_type,
                                child_target,
                                intent,
                            )
            child_payload: dict[str, Any] = {
                "operation_id": f"op_{index}",
                "type": current_operation_type,
                "description": child_description,
                "target": child_target,
                "locator": child_locator,
                "status": "planned",
            }
            if child_assertion:
                child_payload["assertion"] = child_assertion
            if child_value:
                child_payload["value"] = child_value
                child_payload["expected_value"] = child_value
            planned_children.append(child_payload)

        return planned_children

    def _build_plan_ready_parent_step(
        self,
        plan_step: dict[str, Any],
        source_step: dict[str, Any],
        step_index: int,
    ) -> dict[str, Any]:
        parent_step = dict(plan_step) if isinstance(plan_step, dict) else {"text": str(plan_step or "").strip()}
        source_step_data = source_step if isinstance(source_step, dict) else {}

        step_id = str(
            parent_step.get("step_id")
            or parent_step.get("id")
            or source_step_data.get("step_id")
            or source_step_data.get("id")
            or step_index + 1
        ).strip()
        intent = str(
            source_step_data.get("intent")
            or parent_step.get("intent")
            or parent_step.get("description")
            or parent_step.get("text")
            or ""
        ).strip()
        if not intent:
            intent = str(parent_step.get("action") or "").strip()

        parent_step["step_id"] = step_id
        parent_step["intent"] = intent
        normalized_expected_outcome = self._normalize_expected_outcome(
            source_step_data.get("expected_outcome") or source_step_data.get("expectedOutcome"),
            self._is_click_like_intent(intent),
        )
        if normalized_expected_outcome is not None:
            parent_step["expected_outcome"] = normalized_expected_outcome
        parent_step["status"] = "planned"
        parent_step["children"] = self._build_planned_children(source_step_data, parent_step)

        display_text = intent or str(parent_step.get("text") or "").strip()
        if display_text:
            parent_step["text"] = display_text
            parent_step["label"] = display_text
            parent_step["title"] = display_text
        parent_step["kind"] = "step"
        parent_step["type"] = "step"
        return parent_step

    def _build_recorded_child_description(
        self,
        action: str,
        operation_type: str,
        target: str,
        action_context: dict[str, Any],
        intent: str,
    ) -> str:
        operation_name = str(action or operation_type or "").strip().lower()
        target_text = self._normalize_space(str(target or "")).strip()
        intent_text = self._normalize_space(str(intent or "")).strip()
        value_text = self._normalize_space(
            str(action_context.get("value") or action_context.get("expected_value") or "")
        ).strip()
        assertion_text = str(action_context.get("assertion") or "").strip().lower()

        if operation_name in {"click", "tap", "press"}:
            return target_text or intent_text

        if operation_name in {"fill", "type"}:
            if target_text and value_text:
                return f"{target_text}: {value_text}"
            return target_text or value_text or intent_text

        if operation_name == "assert" or assertion_text:
            if assertion_text in {"exact_text", "text_equal", "text_equals", "contains_text", "includes_text"}:
                assertion_text = "has_text"
            if assertion_text == "visible":
                return f"{target_text} is visible" if target_text else intent_text
            if assertion_text == "hidden":
                return f"{target_text} is hidden" if target_text else intent_text
            if assertion_text == "enabled":
                return f"{target_text} is enabled" if target_text else intent_text
            if assertion_text == "disabled":
                return f"{target_text} is disabled" if target_text else intent_text
            if assertion_text == "checked":
                return f"{target_text} is checked" if target_text else intent_text
            if assertion_text == "has_text":
                if target_text and value_text:
                    if target_text == value_text:
                        return f"Text equals {value_text}"
                    return f"{target_text} has text {value_text}"
                return target_text or value_text or intent_text
            if assertion_text == "has_value":
                if target_text and value_text:
                    return f"{target_text} has value {value_text}"
                return target_text or value_text or intent_text
            return target_text or intent_text

        if operation_name == "navigate":
            return target_text or intent_text

        if operation_name == "hover":
            return target_text or intent_text

        return target_text or intent_text

    def _is_technical_recorded_label_text(self, value: Any) -> bool:
        text = self._normalize_space(str(value or "")).strip()
        if not text:
            return False
        lowered = text.lower()
        technical_markers = (
            "get_by_",
            "page.locator(",
            "locator(",
            "[data-testid",
            "css=",
            "xpath=",
            "role=",
        )
        return lowered.startswith("#") or any(marker in lowered for marker in technical_markers)

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
        if isinstance(confirmed_children, list) and confirmed_children:
            recorded_children: list[dict[str, Any]] = []
            confirmed_results = confirmed_child_results if isinstance(confirmed_child_results, dict) else {}
            confirmed_step_data = confirmed_step if isinstance(confirmed_step, dict) else {}
            for index, confirmed_child in enumerate(confirmed_children, start=1):
                if not isinstance(confirmed_child, dict):
                    continue
                operation_id = str(confirmed_child.get("operation_id") or "").strip() or f"op_{index}"
                child_result = confirmed_results.get(operation_id)
                if not isinstance(child_result, dict):
                    child_result = {}

                action_context = dict(child_result.get("action_context") or {})
                child_locator = str(
                    child_result.get("locator")
                    or confirmed_child.get("locator")
                    or action_context.get("locator")
                    or locator
                    or self._derive_locator_from_step_context(confirmed_step_data)
                    or ""
                ).strip()
                child_action = str(
                    child_result.get("action")
                    or confirmed_child.get("type")
                    or self._action_name_for_tool(str(child_result.get("tool") or ""))
                    or ""
                ).strip()
                if not child_action:
                    child_action = str(confirmed_child.get("type") or "").strip()
                confirmed_target = str(confirmed_child.get("target") or "").strip()
                human_target = str(
                    confirmed_step_data.get("element_name")
                    or element_name
                    or ""
                ).strip()
                if not human_target:
                    locator_target_hint = self._locator_label_hint(child_locator)
                    if locator_target_hint and not self._is_technical_recorded_label_text(locator_target_hint):
                        human_target = locator_target_hint
                child_value_text = str(
                    child_result.get("value")
                    or child_result.get("expected_value")
                    or confirmed_child.get("value")
                    or confirmed_child.get("expected_value")
                    or action_context.get("value")
                    or action_context.get("expected_value")
                    or ""
                ).strip()
                child_generated_line = str(
                    child_result.get("generated_line")
                    or self._build_generated_line(child_action, child_locator, action_context)
                    or ""
                ).strip()
                child_status = str(child_result.get("status") or confirmed_child.get("status") or "pending").strip().lower()
                if child_status not in {"success", "failed", "blocked", "pending", "skipped"}:
                    child_status = "pending"
                description = str(
                    child_result.get("description")
                    or confirmed_child.get("description")
                    or ""
                ).strip()
                if self._is_technical_recorded_label_text(description):
                    description = ""
                if not description:
                    description = self._build_recorded_child_description(
                        child_action,
                        child_action,
                        str(
                            (
                                confirmed_target
                                if child_action == "assert" and not self._is_technical_recorded_label_text(confirmed_target)
                                else ""
                            )
                            or (human_target if not self._is_technical_recorded_label_text(human_target) else "")
                            or child_result.get("target")
                            or (
                                self._locator_label_hint(child_locator)
                                if not self._is_technical_recorded_label_text(self._locator_label_hint(child_locator))
                                else ""
                            )
                            or confirmed_target
                            or element_name
                            or intent
                            or ""
                        ).strip(),
                        action_context,
                        intent,
                    )
                if not description:
                    description = str(
                        (
                            confirmed_target
                            if child_action == "assert" and not self._is_technical_recorded_label_text(confirmed_target)
                            else ""
                        )
                        or (human_target if not self._is_technical_recorded_label_text(human_target) else "")
                        or confirmed_target
                        or element_name
                        or intent
                        or child_action
                        or ""
                    ).strip()
                target = str(
                    (
                        confirmed_target
                        if child_action == "assert" and not self._is_technical_recorded_label_text(confirmed_target)
                        else ""
                    )
                    or (human_target if not self._is_technical_recorded_label_text(human_target) else "")
                    or child_result.get("target")
                    or confirmed_target
                    or element_name
                    or (
                        self._locator_label_hint(child_locator)
                        if not self._is_technical_recorded_label_text(self._locator_label_hint(child_locator))
                        else ""
                    )
                    or intent
                    or child_action
                    or ""
                ).strip()

                child_payload: dict[str, Any] = {
                    "operation_id": operation_id,
                    "type": str(confirmed_child.get("type") or child_action or "unknown").strip() or "unknown",
                    "description": description or target or child_action,
                    "target": target,
                    "locator": child_locator,
                    "status": child_status,
                    "code_lines": [],
                }
                if confirmed_child.get("assertion"):
                    child_payload["assertion"] = confirmed_child.get("assertion")
                if child_value_text:
                    child_payload["value"] = child_value_text
                    if child_action == "assert":
                        child_payload["expected_value"] = child_value_text
                elif confirmed_child.get("value") not in (None, "", [], {}):
                    child_payload["value"] = confirmed_child.get("value")
                if confirmed_child.get("expected_value") not in (None, "", [], {}):
                    child_payload["expected_value"] = confirmed_child.get("expected_value")
                error_text = str(child_result.get("error") or child_result.get("message") or "").strip()
                if error_text:
                    child_payload["error"] = error_text
                if child_status == "success":
                    code_lines = list(child_result.get("code_lines") or [])
                    if not code_lines and child_generated_line:
                        code_lines = [child_generated_line]
                    child_payload["code_lines"] = code_lines
                recorded_children.append(child_payload)

            return recorded_children

        recorded_children: list[dict[str, Any]] = []
        for index, action_record in enumerate(action_records, start=1):
            if not isinstance(action_record, dict):
                continue

            action_context = dict(action_record.get("action_context") or {})
            recorded_step_context = action_record.get("step_context") or {}
            if not isinstance(recorded_step_context, dict):
                recorded_step_context = {}

            action = str(
                action_record.get("action")
                or self._action_name_for_tool(str(action_record.get("tool") or ""))
                or ""
            ).strip()
            child_locator = str(
                action_context.get("locator")
                or action_record.get("locator")
                or locator
                or self._derive_locator_from_step_context(recorded_step_context)
                or ""
            ).strip()
            child_generated_line = str(
                action_record.get("generated_line")
                or self._build_generated_line(action, child_locator, action_context)
                or ""
            ).strip()
            operation_type = self._infer_operation_type(action)
            if operation_type == "unknown" and action:
                operation_type = action
            description_target = str(
                action_record.get("element_name")
                or recorded_step_context.get("element_name")
                or self._locator_label_hint(child_locator)
                or ""
            ).strip()
            description = self._build_recorded_child_description(
                action,
                operation_type,
                description_target,
                action_context,
                intent,
            )
            if not description:
                description = str(action_record.get("description") or "").strip()
            if not description:
                description = str(element_name or action or operation_type or intent or "").strip()
            target = str(
                action_record.get("element_name")
                or element_name
                or child_locator
                or intent
                or action
                or ""
            ).strip()

            recorded_children.append(
                {
                    "operation_id": f"op_{index}",
                    "type": operation_type,
                    "description": description,
                    "target": target,
                    "locator": child_locator,
                    "status": "success",
                    "code_lines": [child_generated_line] if child_generated_line else [],
                }
            )

        return recorded_children

    def _build_code_update_payload(self, payload: dict[str, Any], step_id: str) -> dict[str, Any]:
        if not step_id:
            return {}

        children = payload.get("children")
        lines: list[str] = []
        operation_id = "op_1"
        operation_id_set = False
        if isinstance(children, list) and children:
            for child in children:
                if not isinstance(child, dict):
                    continue
                child_status = str(child.get("status") or "").strip().lower()
                if child_status not in {"success", "recorded"}:
                    continue
                if not operation_id_set:
                    child_operation_id = str(child.get("operation_id") or "").strip()
                    if child_operation_id:
                        operation_id = child_operation_id
                    operation_id_set = True
                child_code_lines = child.get("code_lines")
                if not isinstance(child_code_lines, list):
                    continue
                for child_code_line in child_code_lines:
                    line_text = str(child_code_line or "").strip()
                    if line_text:
                        lines.append(line_text)
        if not lines:
            return {}
        return {
            "step_id": step_id,
            "operation_id": operation_id,
            "lines": lines,
            "full_spec_preview": "\n".join(lines),
            "diagnostics": [],
        }

    def _build_plan_ready_payload(
        self,
        payload: dict[str, Any],
        prefer_plan_step_source: bool = False,
    ) -> dict[str, Any]:
        plan_ready_payload = dict(payload)
        steps = payload.get("steps")
        if not isinstance(steps, list):
            return plan_ready_payload

        current_steps = list(getattr(self, "current_steps", []))
        use_plan_step_source = bool(prefer_plan_step_source)
        if len(current_steps) == 1 and len(steps) > 1:
            first_plan_step = steps[0] if isinstance(steps[0], dict) else {"text": str(steps[0] or "").strip()}
            if use_plan_step_source and isinstance(current_steps[0], dict):
                correction_context_step = current_steps[0]
                correction_context_locator = self._normalize_space(
                    str(correction_context_step.get("locator") or "")
                ).strip()
                if not correction_context_locator:
                    correction_context_locator = self._derive_locator_from_step_context(correction_context_step)
                if correction_context_locator and not str(first_plan_step.get("locator") or "").strip():
                    first_plan_step["locator"] = correction_context_locator
                if (
                    isinstance(correction_context_step.get("element_info"), dict)
                    and not isinstance(first_plan_step.get("element_info"), dict)
                ):
                    first_plan_step["element_info"] = deepcopy(correction_context_step.get("element_info"))
            source_step = first_plan_step if use_plan_step_source else (
                current_steps[0] if isinstance(current_steps[0], dict) else {}
            )
            plan_ready_payload["steps"] = [self._build_plan_ready_parent_step(first_plan_step, source_step, 0)]
            return plan_ready_payload

        planned_steps: list[dict[str, Any]] = []
        for index, step in enumerate(steps):
            parent_step = dict(step) if isinstance(step, dict) else {"text": str(step or "").strip()}
            source_step = current_steps[index] if index < len(current_steps) and isinstance(current_steps[index], dict) else {}
            if use_plan_step_source:
                if isinstance(source_step, dict):
                    correction_context_locator = self._normalize_space(str(source_step.get("locator") or "")).strip()
                    if not correction_context_locator:
                        correction_context_locator = self._derive_locator_from_step_context(source_step)
                    if correction_context_locator and not str(parent_step.get("locator") or "").strip():
                        parent_step["locator"] = correction_context_locator
                    if isinstance(source_step.get("element_info"), dict) and not isinstance(parent_step.get("element_info"), dict):
                        parent_step["element_info"] = deepcopy(source_step.get("element_info"))
                source_step = parent_step
            planned_steps.append(self._build_plan_ready_parent_step(parent_step, source_step, index))

        plan_ready_payload["steps"] = planned_steps
        return plan_ready_payload

    def _assistant_message_entry(self, message: Any) -> dict[str, Any]:
        entry: dict[str, Any] = {"role": "assistant", "content": message.content or ""}
        if message.tool_calls:
            entry["tool_calls"] = [
                {
                    "id": tool_call.id,
                    "type": tool_call.type,
                    "function": {
                        "name": tool_call.function.name,
                        "arguments": tool_call.function.arguments,
                    },
                }
                for tool_call in message.tool_calls
            ]
        return entry

    def _safe_llm_artifact_text(self, value: Any) -> str:
        text = str(value or "")
        text = re.sub(r"\bsk-[A-Za-z0-9-]+\b", "[REDACTED_TOKEN]", text)
        text = re.sub(r"\bBearer\s+[A-Za-z0-9._-]+\b", "[REDACTED_BEARER]", text)
        return text

    def _llm_tool_names(self, tools: list[dict[str, Any]]) -> list[str]:
        names: list[str] = []
        for tool in tools:
            function = tool.get("function") if isinstance(tool, dict) else {}
            if not isinstance(function, dict):
                continue
            name = str(function.get("name") or "").strip()
            if name:
                names.append(name)
        return names

    def _llm_tool_schema_summary(self, tools: list[dict[str, Any]]) -> dict[str, Any]:
        normalized_tools: list[dict[str, Any]] = []
        for tool in tools:
            function = tool.get("function") if isinstance(tool, dict) else {}
            if not isinstance(function, dict):
                continue
            parameters = function.get("parameters")
            properties = parameters.get("properties") if isinstance(parameters, dict) else {}
            normalized_tools.append({
                "name": str(function.get("name") or "").strip(),
                "description": self._safe_llm_artifact_text(function.get("description") or ""),
                "params": sorted(str(key) for key in properties.keys()) if isinstance(properties, dict) else [],
            })
        return {
            "tool_count": len(normalized_tools),
            "tools": normalized_tools,
        }

    def _llm_tool_call_summaries(self, message: Any) -> list[dict[str, Any]]:
        summaries: list[dict[str, Any]] = []
        for tool_call in list(getattr(message, "tool_calls", []) or []):
            function = getattr(tool_call, "function", None)
            name = str(getattr(function, "name", "") or "").strip()
            arguments = getattr(function, "arguments", "") or ""
            parsed_arguments = self._parse_tool_args(arguments) if isinstance(arguments, str) else {}
            summaries.append({
                "name": name,
                "args_summary": self._safe_llm_artifact_text(json.dumps(parsed_arguments, sort_keys=True)),
            })
        return summaries

    def _llm_token_usage_summary(self, response: Any) -> dict[str, Any]:
        usage = getattr(response, "usage", None)
        if usage is None:
            return {}
        prompt_tokens_details = getattr(usage, "prompt_tokens_details", None)
        cached_tokens = getattr(prompt_tokens_details, "cached_tokens", None) if prompt_tokens_details is not None else None
        return {
            "prompt_tokens": getattr(usage, "prompt_tokens", None),
            "completion_tokens": getattr(usage, "completion_tokens", None),
            "total_tokens": getattr(usage, "total_tokens", None),
            "cached_tokens": cached_tokens,
        }

    def _emit_llm_call_record(
        self,
        *,
        call_id: str,
        purpose: str,
        model: str,
        model_class: str | None,
        filtered_tools: list[dict[str, Any]],
        telemetry: Any,
        response: Any,
        error: dict[str, Any] | None = None,
    ) -> None:
        try:
            choice = response.choices[0] if response is not None and getattr(response, "choices", None) else None
            message = choice.message if choice is not None else None
            assistant_text = None
            if message is not None and not list(getattr(message, "tool_calls", []) or []):
                assistant_text = self._safe_llm_artifact_text(getattr(message, "content", "") or "")
            record = {
                "call_id": call_id,
                "purpose": purpose,
                "model": model,
                "model_class": model_class,
                "prompt_pack_id": getattr(telemetry, "prompt_pack_id", None),
                "prefix_hash": getattr(telemetry, "prefix_hash", None),
                "tool_names": self._llm_tool_names(filtered_tools),
                "tool_schema": self._llm_tool_schema_summary(filtered_tools),
                "assistant_text": assistant_text,
                "tool_calls": self._llm_tool_call_summaries(message) if message is not None else [],
                "finish_reason": getattr(choice, "finish_reason", None),
                "token_usage": self._llm_token_usage_summary(response),
                "error": error or {},
            }
            print(f"[LLM_CALL] {json.dumps(record, sort_keys=True)}")
        except Exception as exc:  # noqa: BLE001
            fallback = {
                "call_id": call_id,
                "purpose": purpose,
                "error": {
                    "type": type(exc).__name__,
                    "message": str(exc),
                },
            }
            print(f"[LLM_CALL] {json.dumps(fallback, sort_keys=True)}")

    def _profile_heading_options_from_result(self, result: dict[str, Any]) -> list[str]:
        candidates: list[str] = []
        headings = result.get("headings")
        if isinstance(headings, list):
            candidates.extend(str(item or "").strip() for item in headings)
        page_intelligence = result.get("page_intelligence")
        if isinstance(page_intelligence, dict):
            for key in ("headings", "sections"):
                values = page_intelligence.get(key)
                if isinstance(values, list):
                    candidates.extend(str(item or "").strip() for item in values)
        normalized: list[str] = []
        for candidate in candidates:
            if not candidate or "profile" not in candidate.lower():
                continue
            if candidate not in normalized:
                normalized.append(candidate)
        return normalized

    def _build_ambiguity_question(self, options: list[str]) -> str:
        option_text = ", ".join(options[:4])
        return (
            "Multiple plausible targets were found. Which Profile section did you mean? "
            f"Choose one of: {option_text}."
        )

    def _update_planning_ambiguity_from_tool_result(self, tool_name: str, result: dict[str, Any]) -> None:
        current_phase = str(self._current_phase() or "").strip()
        fallback_phase = str(getattr(self, "phase", "") or "").strip()
        if tool_name != "dom_extract" or self.plan_confirmed:
            return
        if current_phase != "planning" and fallback_phase != "planning":
            return
        if not isinstance(result, dict):
            return
        options = self._profile_heading_options_from_result(result)
        if len(options) < 2:
            return
        self._pending_planning_ambiguity = {
            "options": options,
            "question": self._build_ambiguity_question(options),
        }

    def _build_pending_ambiguity_instruction(self) -> str | None:
        ambiguity = getattr(self, "_pending_planning_ambiguity", None)
        if not isinstance(ambiguity, dict):
            return None
        options = [str(option).strip() for option in ambiguity.get("options") or [] if str(option).strip()]
        if len(options) < 2:
            return None
        return (
            "Multiple plausible targets were found. Call ask_user with options. "
            "Do not continue DOM exploration. Do not answer in plain text. "
            f"Options: {', '.join(options[:4])}."
        )

    def _should_force_ambiguity_clarification(self, message: Any) -> bool:
        ambiguity = getattr(self, "_pending_planning_ambiguity", None)
        if not isinstance(ambiguity, dict):
            return False
        raw_tool_calls = list(getattr(message, "tool_calls", []) or [])
        if raw_tool_calls:
            tool_names = {
                str(getattr(getattr(tool_call, "function", None), "name", "") or "").strip()
                for tool_call in raw_tool_calls
            }
            if "ask_user" in tool_names:
                return False
            if "send_to_overlay" in tool_names:
                for tool_call in raw_tool_calls:
                    function = getattr(tool_call, "function", None)
                    if str(getattr(function, "name", "") or "").strip() != "send_to_overlay":
                        continue
                    arguments = getattr(function, "arguments", "") or ""
                    payload = self._parse_tool_args(arguments) if isinstance(arguments, str) else {}
                    message_type = str(payload.get("message_type") or "").strip()
                    if message_type == "plan_ready":
                        return False
        return True

    def _build_ambiguity_followup_message(self, ambiguity_context: dict[str, Any], answer_text: str) -> str:
        options = [str(option).strip() for option in ambiguity_context.get("options") or [] if str(option).strip()]
        selected = answer_text or "no selection provided"
        return (
            f"User clarification: {selected}. "
            f"Available options were: {', '.join(options[:4])}. "
            "Continue planning safely from this clarified target."
        )

    def _parse_tool_args(self, raw_args: str) -> dict[str, Any]:
        parsed = json.loads(raw_args or "{}")
        if not isinstance(parsed, dict):
            raise ValueError("Tool arguments must decode to an object")
        return parsed

    def _build_tool_definitions(self) -> list[dict[str, Any]]:
        return [
            {
                "type": "function",
                "function": {
                    "name": "dom_extract",
                    "description": "Get interactive elements from current page or a scoped element",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "scope": {
                                "type": "string",
                                "description": 'CSS selector to scope extraction, or "page" for full page',
                            }
                        },
                        "required": ["scope"],
                        "additionalProperties": False,
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "locator_find",
                    "description": "Find best locator for element using priority waterfall",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "element_data": {
                                "type": "object",
                                "properties": {
                                    "tag": {"type": "string"},
                                    "text": {"type": "string"},
                                    "id": {"type": "string"},
                                    "class": {"type": "string"},
                                    "role": {"type": "string"},
                                    "aria_label": {"type": "string"},
                                    "data_testid": {"type": "string"},
                                    "placeholder": {"type": "string"},
                                    "parent_tag": {"type": "string"},
                                    "parent_id": {"type": "string"},
                                },
                                "required": [],
                                "additionalProperties": True,
                            },
                        },
                        "required": ["element_data"],
                        "additionalProperties": False,
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "locator_validate",
                    "description": "Validate a locator resolves to exactly 1 element on live page",
                    "parameters": {
                        "type": "object",
                        "properties": {"locator": {"type": "string"}},
                        "required": ["locator"],
                        "additionalProperties": False,
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "action_click",
                    "description": "Click an interactive element on the live page. Use real UI controls only; do not use body clicks or clicks to simulate navigation.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "locator": {"type": "string"},
                            "timeout": {"type": "integer", "default": 30000},
                        },
                        "required": ["locator"],
                        "additionalProperties": False,
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "action_fill",
                    "description": "Fill an editable field only (input, textarea, select, or contenteditable). Never use this on body or to simulate navigation.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "locator": {"type": "string"},
                            "value": {"type": "string"},
                            "timeout": {"type": "integer", "default": 30000},
                        },
                        "required": ["locator", "value"],
                        "additionalProperties": False,
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "action_assert",
                    "description": "Assert element state on live page. Auto-retries until condition met or timeout.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "locator": {"type": "string"},
                            "assertion": {
                                "type": "string",
                                "enum": [
                                    "visible",
                                    "hidden",
                                    "enabled",
                                    "disabled",
                                    "has_text",
                                    "has_value",
                                    "checked",
                                ],
                            },
                            "expected_value": {"type": "string"},
                            "timeout": {"type": "integer", "default": 5000},
                        },
                        "required": ["locator", "assertion"],
                        "additionalProperties": False,
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "page_navigate",
                    "description": "Navigate browser to a URL. Use for direct URL changes only; use page_go_back, page_go_forward, or page_reload for history and refresh actions.",
                    "parameters": {
                        "type": "object",
                        "properties": {"url": {"type": "string"}},
                        "required": ["url"],
                        "additionalProperties": False,
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "page_go_back",
                    "description": "Go back in browser history. Use when user says go back, previous page, return to previous page, or navigate back.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "wait_until": {
                                "type": "string",
                                "enum": ["load", "domcontentloaded", "networkidle"],
                                "default": "domcontentloaded",
                            }
                        },
                        "additionalProperties": False,
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "page_go_forward",
                    "description": "Go forward in browser history. Use when user says go forward or next page in history.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "wait_until": {
                                "type": "string",
                                "enum": ["load", "domcontentloaded", "networkidle"],
                                "default": "domcontentloaded",
                            }
                        },
                        "additionalProperties": False,
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "page_reload",
                    "description": "Reload or refresh the current page. Use when user says reload, refresh, or reload current page.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "wait_until": {
                                "type": "string",
                                "enum": ["load", "domcontentloaded", "networkidle"],
                                "default": "domcontentloaded",
                            }
                        },
                        "additionalProperties": False,
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "scroll_into_view",
                    "description": "Scroll an element into view before interacting or asserting.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "locator": {"type": "string"},
                            "timeout": {"type": "integer", "default": 5000},
                        },
                        "required": ["locator"],
                        "additionalProperties": False,
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "browser_get_state",
                    "description": "Get current browser URL and page title",
                    "parameters": {
                        "type": "object",
                        "properties": {},
                        "additionalProperties": False,
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "screenshot_take",
                    "description": "Take screenshot of current page for debugging",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "filename": {"type": "string", "default": "screenshot.png"}
                        },
                        "additionalProperties": False,
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "send_to_overlay",
                    "description": "Send message to user in the browser overlay panel",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "message_type": {
                                "type": "string",
                                "enum": [
                                "llm_thinking",
                                "plan_ready",
                                "plan_correction_diff",
                                "clarification_needed",
                                "step_recorded",
                                "code_update",
                                "llm_result",
                                    "error",
                                ],
                            },
                            "payload": {"type": "object", "additionalProperties": True},
                        },
                        "required": ["message_type", "payload"],
                        "additionalProperties": False,
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "ask_user",
                    "description": "Ask user a question and wait for their response",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "question": {"type": "string"},
                            "options": {"type": "array", "items": {"type": "string"}},
                        },
                        "required": ["question"],
                        "additionalProperties": False,
                    },
                },
            },
        ]

    async def _dispatch_tool(self, tool_name: str, args: dict[str, Any]) -> dict[str, Any]:
        handlers = {
            "dom_extract": self._tool_dom_extract,
            "locator_find": self._tool_locator_find,
            "locator_validate": self._tool_locator_validate,
            "action_click": self._tool_action_click,
            "action_fill": self._tool_action_fill,
            "action_assert": self._tool_action_assert,
            "page_navigate": self._tool_page_navigate,
            "page_go_back": self._tool_page_go_back,
            "page_go_forward": self._tool_page_go_forward,
            "page_reload": self._tool_page_reload,
            "scroll_into_view": self._tool_scroll_into_view,
            "browser_get_state": self._tool_browser_get_state,
            "screenshot_take": self._tool_screenshot_take,
            "send_to_overlay": self._tool_send_to_overlay,
            "ask_user": self._tool_ask_user,
        }
        if tool_name not in handlers:
            self._record_capability_gap(
                "unknown_tool",
                "_dispatch_tool",
                "error",
                "Unsupported tool requested.",
                tool_name=tool_name,
            )
            raise RuntimeError(f"Unsupported tool requested: {tool_name}")
        return await handlers[tool_name](args)

    async def _tool_dom_extract(self, args: dict[str, Any]) -> dict[str, Any]:
        return await tool_dom_extract(self, args, get_page=get_page)

    async def _tool_locator_find(self, args: dict[str, Any]) -> dict[str, Any]:
        return await tool_locator_find(self, args, get_page=get_page)

    async def _tool_locator_validate(self, args: dict[str, Any]) -> dict[str, Any]:
        return await tool_locator_validate(self, args, get_page=get_page)

    async def _tool_action_click(self, args: dict[str, Any]) -> dict[str, Any]:
        page = get_page()
        locator_string = str(args.get("locator") or "").strip()
        timeout = int(args.get("timeout") or 30000)
        try:
            await self._resolve_locator(page, locator_string).first.click(timeout=timeout)
            return {"success": True, "error": None}
        except Exception as exc:  # noqa: BLE001
            return {"success": False, "error": str(exc)}

    async def _tool_action_fill(self, args: dict[str, Any]) -> dict[str, Any]:
        page = get_page()
        locator_string = str(args.get("locator") or "").strip()
        value = str(args.get("value") or "")
        timeout = int(args.get("timeout") or 30000)
        try:
            locator = self._resolve_locator(page, locator_string).first
            tag = str(await locator.evaluate("(el) => el.tagName.toLowerCase()"))
            contenteditable = bool(await locator.evaluate("(el) => el.isContentEditable"))
            if tag not in {"input", "textarea", "select"} and not contenteditable:
                return {
                    "success": False,
                    "error": "Cannot fill non-editable element",
                    "tag": tag,
                }
            await locator.fill(value, timeout=timeout)
            return {"success": True, "error": None}
        except Exception as exc:  # noqa: BLE001
            return {"success": False, "error": str(exc)}

    async def _tool_action_assert(self, args: dict[str, Any]) -> dict[str, Any]:
        page = get_page()
        locator_text = str(args.get("locator") or "").strip()
        assertion = str(args.get("assertion") or "").strip()
        expected_value = args.get("expected_value")
        if expected_value is None:
            expected_value = args.get("value")
        timeout = int(args.get("timeout") or 5000)

        if assertion in {"has_text", "has_value"} and expected_value is None:
            return {
                "success": False,
                "error": "expected_value_required",
                "assertion": assertion,
            }

        try:
            locator = self._resolve_locator(page, locator_text).first
            if assertion == "visible":
                await expect(locator).to_be_visible(timeout=timeout)
            elif assertion == "hidden":
                await expect(locator).to_be_hidden(timeout=timeout)
            elif assertion == "enabled":
                await expect(locator).to_be_enabled(timeout=timeout)
            elif assertion == "disabled":
                await expect(locator).to_be_disabled(timeout=timeout)
            elif assertion == "has_text":
                normalized_expected = self._normalize_assertion_text(str(expected_value))
                poll_timeout = max(1, min(max(timeout, 0), 250))
                deadline = asyncio.get_running_loop().time() + max(timeout, 0) / 1000
                actual_text = ""
                normalized_actual = ""

                while True:
                    try:
                        actual_text = await locator.inner_text(timeout=poll_timeout)
                    except Exception:  # noqa: BLE001
                        try:
                            actual_text = await locator.text_content(timeout=poll_timeout)
                        except Exception:  # noqa: BLE001
                            actual_text = ""

                    normalized_actual = self._normalize_assertion_text(actual_text)
                    if normalized_expected in normalized_actual:
                        return {
                            "success": True,
                            "assertion": "has_text",
                            "actual_text": normalized_actual,
                            "expected_text": normalized_expected,
                        }
                    if timeout <= 0 or asyncio.get_running_loop().time() >= deadline:
                        return {
                            "success": False,
                            "assertion": "has_text",
                            "error": (
                                "Expected normalized text to contain "
                                f"{normalized_expected!r}, got {normalized_actual!r}"
                            ),
                            "actual_text": normalized_actual,
                            "expected_text": normalized_expected,
                        }
                    await asyncio.sleep(min(0.1, max(deadline - asyncio.get_running_loop().time(), 0.01)))
            elif assertion == "has_value":
                await expect(locator).to_have_value(str(expected_value), timeout=timeout)
            elif assertion == "checked":
                await expect(locator).to_be_checked(timeout=timeout)
            else:
                self._record_capability_gap(
                    "unsupported_assertion",
                    "_tool_action_assert",
                    "error",
                    "Unsupported assertion requested.",
                    assertion=assertion,
                )
                raise ValueError(f"Unsupported assertion: {assertion}")
            return {"success": True, "error": None}
        except (AssertionError, PlaywrightTimeoutError, ValueError) as exc:
            return {"success": False, "error": str(exc)}
        except Exception as exc:  # noqa: BLE001
            return {"success": False, "error": str(exc)}

    async def _tool_page_navigate(self, args: dict[str, Any]) -> dict[str, Any]:
        page = get_page()
        url = str(args.get("url") or "").strip()
        invalid_literals = {"", "current page", "same page", "this page", "current"}
        valid_prefixes = ("http://", "https://", "file://", "about:")

        if url.lower() in invalid_literals or not url.startswith(valid_prefixes):
            return {"success": False, "error": "Invalid navigation URL", "url": url}

        if url == page.url:
            return {
                "success": True,
                "skipped": True,
                "reason": "Already on requested URL",
                "url": url,
            }

        await page.goto(url, wait_until="domcontentloaded")
        return {"success": True, "url": page.url}

    async def _tool_page_go_back(self, args: dict[str, Any]) -> dict[str, Any]:
        page = get_page()
        wait_until = self._normalize_wait_until(args.get("wait_until"))
        try:
            response = await page.go_back(wait_until=wait_until)
            return {
                "success": True,
                "url": page.url,
                "title": await page.title(),
                "navigated": response is not None,
            }
        except Exception as exc:  # noqa: BLE001
            return {"success": False, "error": str(exc), "url": page.url}

    async def _tool_page_go_forward(self, args: dict[str, Any]) -> dict[str, Any]:
        page = get_page()
        wait_until = self._normalize_wait_until(args.get("wait_until"))
        try:
            response = await page.go_forward(wait_until=wait_until)
            return {
                "success": True,
                "url": page.url,
                "title": await page.title(),
                "navigated": response is not None,
            }
        except Exception as exc:  # noqa: BLE001
            return {"success": False, "error": str(exc), "url": page.url}

    async def _tool_page_reload(self, args: dict[str, Any]) -> dict[str, Any]:
        page = get_page()
        wait_until = self._normalize_wait_until(args.get("wait_until"))
        try:
            await page.reload(wait_until=wait_until)
            return {"success": True, "url": page.url, "title": await page.title()}
        except Exception as exc:  # noqa: BLE001
            return {"success": False, "error": str(exc), "url": page.url}

    async def _tool_scroll_into_view(self, args: dict[str, Any]) -> dict[str, Any]:
        page = get_page()
        locator_string = str(args.get("locator") or "").strip()
        timeout = int(args.get("timeout") or 5000)
        try:
            locator = self._resolve_locator(page, locator_string).first
            await locator.scroll_into_view_if_needed(timeout=timeout)
            return {"success": True, "locator": locator_string}
        except Exception as exc:  # noqa: BLE001
            return {"success": False, "error": str(exc), "locator": locator_string}

    async def _tool_browser_get_state(self, args: dict[str, Any]) -> dict[str, Any]:  # noqa: ARG002
        page = get_page()
        return {"url": page.url, "title": await page.title()}

    async def _tool_screenshot_take(self, args: dict[str, Any]) -> dict[str, Any]:
        page = get_page()
        filename = str(args.get("filename") or "screenshot.png")
        output_dir = Path(".hermes/screenshots")
        output_dir.mkdir(parents=True, exist_ok=True)
        path = output_dir / filename
        await page.screenshot(path=str(path))
        return {"path": str(path), "success": True}

    async def _send_plan_ready_after_confirmation(self, payload: dict[str, Any]) -> dict[str, Any]:
        await self._send("plan_ready", **payload)
        self._remember_plan_review_context(payload)
        plan_step_id = str(
            payload.get("target_step_id")
            or payload.get("step_id")
            or payload.get("id")
            or payload.get("stepId")
            or ""
        ).strip() or None
        self.phase_tracker.set_phase(
            "awaiting_confirmation",
            reason="plan_ready",
            step_id=plan_step_id,
        )
        print("[AGENT] plan_ready sent; waiting for user confirmation")
        confirmation = await self._wait_for_plan_confirmation()
        if confirmation.get("confirmed"):
            self.plan_confirmed = True
            self.phase = "executing"
            self.phase_tracker.set_phase("executing", reason="confirmed", step_id=plan_step_id)
            self._pending_failure_followup = False
            self._awaiting_step_record = False
            self._recording_wait_guard_armed = False
            self._store_confirmed_execution_plan(payload)
            self._clear_active_plan_state()
            self._plan_correction_pending = False
            self._clear_plan_review_context()
            answer = str(confirmation.get("answer") or "confirmed").strip() or "confirmed"
            print("[AGENT] plan confirmed; entering execution phase")
            return {"confirmed": True, "answer": answer, "phase": "executing"}

        self.plan_confirmed = False
        self.phase = "planning"
        self.phase_tracker.set_phase("planning", reason="correction", step_id=plan_step_id)
        self.last_successful_action = None
        self._last_action_context = None
        self._awaiting_step_record = False
        self._recording_wait_guard_armed = False
        self._pending_failure_followup = False
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

    async def _tool_send_to_overlay(self, args: dict[str, Any]) -> dict[str, Any]:
        message_type = str(args.get("message_type") or "").strip()
        payload = args.get("payload") or {}
        if not isinstance(payload, dict):
            raise ValueError("payload must be an object")
        extra_payload = {
            key: value for key, value in args.items() if key not in {"message_type", "payload"}
        }
        if extra_payload:
            payload = {**extra_payload, **payload}
        if message_type == "step_recorded":
            if not self.plan_confirmed:
                return {
                    "sent": False,
                    "blocked": True,
                    "requires_confirmation": True,
                    "reason": "step_recorded blocked before confirmed execution.",
                }
            target_step = self._resolve_recording_target_step(payload)
            recorded_payload = await self._record_step_payload(payload, target_step)
            if not recorded_payload:
                return {
                    "sent": False,
                    "skipped": True,
                    "reason": "No successful confirmed action to record.",
                }
            await self._emit_run_completed_event(payload, recorded_payload)
            return {"sent": True, "payload": recorded_payload}

        correction_state = getattr(self, "_active_plan_correction_state", None)
        if isinstance(correction_state, dict) and message_type == "llm_thinking":
            no_progress_count = int(correction_state.get("no_progress_count") or 0) + 1
            schema_retry_count = int(correction_state.get("schema_retry_count") or 0) + 1
            correction_state["no_progress_count"] = no_progress_count
            correction_state["schema_retry_count"] = schema_retry_count
            if schema_retry_count <= 1:
                retry_message = (
                    "Your previous response did not return a structured correction diff. "
                    "Return only message_type='plan_correction_diff' with target_step_id and mutations. "
                    "Do not send plan_ready or llm_thinking."
                )
                print("[AGENT] correction schema retry: llm_thinking blocked in correction mode")
                return {
                    "sent": False,
                    "blocked": True,
                    "reason": "correction_schema_retry",
                    "message": retry_message,
                    "requires_replan": False,
                }
            failure_message = (
                "Correction failed safely. The model did not return a structured correction diff. "
                "You can edit the pending step or run it again."
            )
            correction_state["correction_failed"] = True
            correction_state["clarification_closed"] = True
            correction_state["needs_clarification"] = False
            correction_state["last_validation_reason"] = "no correction diff"
            correction_state["last_validation_feedback"] = failure_message
            print(
                "[AGENT] correction failed without diff: "
                f"{self._summarize(failure_message, limit=140)}"
            )
            return {
                "sent": False,
                "blocked": True,
                "reason": "correction_failed",
                "message": failure_message,
                "requires_replan": False,
            }
        if message_type == "plan_correction_diff":
            if not isinstance(correction_state, dict):
                return {
                    "sent": False,
                    "blocked": True,
                    "reason": "no_active_correction",
                    "message": "No active structured correction is available.",
                    "requires_replan": False,
                }
            corrected_payload = self._build_structured_plan_correction_payload_from_diff(payload)
            if not corrected_payload:
                failure_message = (
                    "Correction failed safely. The model did not return a valid structured correction diff. "
                    "You can edit the pending step or run it again."
                )
                correction_state["correction_failed"] = True
                correction_state["clarification_closed"] = True
                correction_state["needs_clarification"] = False
                correction_state["last_validation_reason"] = "invalid correction diff"
                correction_state["last_validation_feedback"] = failure_message
                print(
                    "[AGENT] correction diff rejected: "
                    f"{self._summarize(failure_message, limit=140)}"
                )
                return {
                    "sent": False,
                    "blocked": True,
                    "reason": "correction_failed",
                    "message": failure_message,
                    "requires_replan": False,
                }
            payload = corrected_payload

        if message_type == "plan_ready":
            pending_recovery = bool(getattr(self, "pending_recovery", False))
            active_failed_step_id = str(getattr(self, "active_failed_step_id", "") or "").strip()
            pending_failure_followup = bool(getattr(self, "_pending_failure_followup", False))
            if pending_recovery or active_failed_step_id or pending_failure_followup:
                print(
                    "[RECOVERY_SCOPE_GUARD] blocked plan_ready during unresolved recovery "
                    f"step_id={active_failed_step_id or 'unknown'}"
                )
                return {
                    "sent": False,
                    "blocked": True,
                    "reason": "plan_ready_blocked_during_recovery",
                    "message": (
                        "Recovery is unresolved. Completed steps are locked; retry, skip, "
                        "stop, or ask about the failed step only."
                    ),
                }
            current_phase = self._current_phase()
            if current_phase in {"executing", "recording"}:
                print("[PLAN_READY_GUARD] blocked during execution")
                return {
                    "sent": False,
                    "blocked": True,
                    "reason": "plan_ready_blocked_during_execution",
                    "message": (
                        "Plan changes are blocked during execution. Continue the confirmed plan or fail safely."
                    ),
                }
            if isinstance(correction_state, dict):
                no_progress_count = int(correction_state.get("no_progress_count") or 0) + 1
                schema_retry_count = int(correction_state.get("schema_retry_count") or 0) + 1
                correction_state["no_progress_count"] = no_progress_count
                correction_state["schema_retry_count"] = schema_retry_count
                if schema_retry_count <= 1:
                    retry_message = (
                        "Correction mode is active. Do not send plan_ready. "
                        "Return only message_type='plan_correction_diff' with target_step_id and mutations."
                    )
                    print(
                        "[AGENT] plan_ready blocked during structured correction; "
                        f"schema retry {schema_retry_count}: {self._summarize(retry_message, limit=140)}"
                    )
                    return {
                        "sent": False,
                        "blocked": True,
                        "reason": "correction_schema_retry",
                        "message": retry_message,
                        "requires_replan": False,
                    }
                failure_message = (
                    "Correction failed safely. The model returned a full plan instead of a structured correction diff. "
                    "You can edit the pending step or run it again."
                )
                correction_state["correction_failed"] = True
                correction_state["clarification_closed"] = True
                correction_state["needs_clarification"] = False
                correction_state["last_validation_reason"] = "correction diff required"
                correction_state["last_validation_feedback"] = failure_message
                print(
                    "[AGENT] plan_ready blocked during structured correction: "
                    f"{self._summarize(failure_message, limit=140)}"
                )
                return {
                "sent": False,
                "blocked": True,
                "reason": "correction_diff_required",
                "message": failure_message,
                "requires_replan": False,
            }
            plan_correction_pending = bool(getattr(self, "_plan_correction_pending", False))
            payload = self._build_plan_ready_payload(
                payload,
                prefer_plan_step_source=plan_correction_pending,
            )
            plan_id = str(payload.get("plan_id") or payload.get("planId") or "").strip()
            if not plan_id:
                active_plan_state = self._current_active_plan_state()
                plan_id = str((active_plan_state or {}).get("plan_id") or "").strip()
            if not plan_id:
                plan_id = f"plan-{uuid4().hex}"
            payload["plan_id"] = plan_id
            target_step_id = str(payload.get("target_step_id") or payload.get("targetStepId") or "").strip()
            if not target_step_id:
                plan_steps = payload.get("steps")
                if isinstance(plan_steps, list) and plan_steps:
                    first_step = plan_steps[0] if isinstance(plan_steps[0], dict) else {}
                    target_step_id = str(first_step.get("step_id") or first_step.get("id") or "").strip()
            if target_step_id:
                payload["target_step_id"] = target_step_id

        if isinstance(correction_state, dict):
            validation_result = self._validate_structured_plan_correction(payload)
            if not validation_result.get("valid"):
                validation_reason = str(validation_result.get("reason") or "").strip() or "invalid corrected plan"
                correction_state["retry_count"] = int(correction_state.get("retry_count") or 0) + 1
                if correction_state.get("clarification_resolved"):
                    validation_feedback = (
                        "Corrected plan is still invalid after clarification. "
                        f"{validation_reason} You can edit the pending step or run it again."
                    ).strip()
                    correction_state["clarification_closed"] = True
                    correction_state["correction_failed"] = True
                    correction_state["needs_clarification"] = False
                    correction_state["last_validation_reason"] = validation_reason
                    correction_state["last_validation_feedback"] = validation_feedback
                    print(
                        "[AGENT] corrected plan rejected after clarification: "
                        f"{self._summarize(validation_feedback, limit=140)}"
                    )
                    return {
                        "sent": False,
                        "blocked": True,
                        "reason": "correction_failed",
                        "message": validation_feedback,
                        "requires_replan": False,
                    }
                if validation_result.get("needs_clarification") or correction_state["retry_count"] > 1:
                    correction_state["needs_clarification"] = True
                    correction_state["clarification_question"] = ""
                    correction_state["clarification_answer"] = None
                    correction_state["clarification_resolved"] = False
                    correction_state["clarification_closed"] = False
                correction_state["last_validation_reason"] = validation_reason
                validation_feedback = self._build_plan_correction_validation_feedback(
                    correction_state,
                    validation_reason,
                    active_plan_state=self._current_active_plan_state(),
                    proposed_payload=payload,
                )
                if correction_state.get("needs_clarification"):
                    correction_state["clarification_question"] = validation_feedback
                correction_state["last_validation_feedback"] = validation_feedback
                print(f"[AGENT] corrected plan rejected: {self._summarize(validation_feedback, limit=140)}")
                return {
                    "sent": False,
                    "blocked": True,
                    "reason": "invalid_corrected_plan",
                    "message": validation_feedback,
                    "requires_replan": True,
                }
            normalized_payload = validation_result.get("normalized_payload")
            if isinstance(normalized_payload, dict):
                payload = normalized_payload
                if not str(payload.get("plan_id") or "").strip():
                    active_plan_state = self._current_active_plan_state()
                    plan_id = str((active_plan_state or {}).get("plan_id") or "").strip()
                    if plan_id:
                        payload["plan_id"] = plan_id
                if not str(payload.get("target_step_id") or "").strip():
                    target_step_id = str(payload.get("target_step_id") or payload.get("targetStepId") or "").strip()
                    if target_step_id:
                        payload["target_step_id"] = target_step_id
                self._active_plan_state = self._build_active_plan_state(
                    payload,
                    source_plan_state=self._current_active_plan_state(),
                )

        if message_type in {"plan_ready", "plan_correction_diff"}:
            return await self._send_plan_ready_after_confirmation(payload)

        await self._send(message_type, **payload)
        return {"sent": True}

    def _normalize_wait_until(self, value: Any) -> str:
        wait_until = str(value or "domcontentloaded").strip() or "domcontentloaded"
        if wait_until not in {"load", "domcontentloaded", "networkidle"}:
            return "domcontentloaded"
        return wait_until

    def _append_tool_response(self, tool_call_id: str, result: dict[str, Any]) -> None:
        self.llm.messages.append(
            {
                "role": "tool",
                "tool_call_id": tool_call_id,
                "content": json.dumps(result, ensure_ascii=True),
            }
        )

    def _append_skipped_tool_response(self, tool_call_id: str, reason: str) -> None:
        self._append_tool_response(
            tool_call_id,
            {
                "success": False,
                "skipped": True,
                "reason": reason,
                "requires_replan": True,
            },
        )

    def _append_skipped_tool_responses(self, tool_calls: list[Any], start_index: int, reason: str) -> None:
        for skipped_call in tool_calls[start_index:]:
            self._append_skipped_tool_response(skipped_call.id, reason)

    async def _wait_for_plan_confirmation(self) -> dict[str, Any]:
        active_confirmation_context = self._confirmation_context(self._current_active_plan_state())
        while True:
            event = await self.control_queue.get()
            event_type = str(event.get("type") or "")
            answer = str(event.get("message") or event.get("answer") or "").strip()
            event_context = self._confirmation_context(event)
            if event_type == "correction":
                completed_run_reason = self._completed_run_confirmation_rejection_reason(event_context)
                if completed_run_reason:
                    completed_run_id = event_context.get("run_id") or self._current_run_session_id()
                    await self._send(
                        "runtime_rejected",
                        **build_runtime_rejection_payload(
                            "STALE_CONFIRMATION",
                            "Correction does not match the active plan context.",
                            detail=f"correction after completion: {completed_run_reason}",
                            current_state={
                                "run_id": completed_run_id,
                                "phase": self._current_phase(),
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
                mismatch_reason = self._confirmation_context_mismatch_reason(active_confirmation_context, event_context)
                if mismatch_reason:
                    await self._send(
                        "runtime_rejected",
                        **build_runtime_rejection_payload(
                            "STALE_CONFIRMATION",
                            "Correction does not match the active plan context.",
                            detail=f"correction context mismatch: {mismatch_reason}",
                            current_state=active_confirmation_context
                            or self._confirmation_context(self._current_active_plan_state()),
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
                completed_run_reason = self._completed_run_confirmation_rejection_reason(event_context)
                if completed_run_reason:
                    completed_run_id = event_context.get("run_id") or self._current_run_session_id()
                    await self._send(
                        "runtime_rejected",
                        **build_runtime_rejection_payload(
                            "STALE_CONFIRMATION",
                            "Confirmation does not match the active plan context.",
                            detail=f"confirmation after completion: {completed_run_reason}",
                            current_state={
                                "run_id": completed_run_id,
                                "phase": self._current_phase(),
                            },
                            run_id=completed_run_id,
                            recoverable=False,
                            source="agent",
                        ),
                    )
                    return {"confirmed": False, "answer": answer or "confirmed"}
                mismatch_reason = self._confirmation_context_mismatch_reason(active_confirmation_context, event_context)
                if mismatch_reason:
                    await self._send(
                        "runtime_rejected",
                        **build_runtime_rejection_payload(
                            "STALE_CONFIRMATION",
                            "Confirmation does not match the active plan context.",
                            detail=f"confirmation context mismatch: {mismatch_reason}",
                            current_state=active_confirmation_context or self._confirmation_context(self._current_active_plan_state()),
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
                completed_run_reason = self._completed_run_confirmation_rejection_reason(event_context)
                if completed_run_reason:
                    completed_run_id = event_context.get("run_id") or self._current_run_session_id()
                    await self._send(
                        "runtime_rejected",
                        **build_runtime_rejection_payload(
                            "STALE_CONFIRMATION",
                            "Confirmation does not match the active plan context.",
                            detail=f"option_selected after completion: {completed_run_reason}",
                            current_state={
                                "run_id": completed_run_id,
                                "phase": self._current_phase(),
                            },
                            run_id=completed_run_id,
                            recoverable=False,
                            source="agent",
                        ),
                    )
                    return {"confirmed": False, "answer": answer}
                mismatch_reason = self._confirmation_context_mismatch_reason(active_confirmation_context, event_context)
                if mismatch_reason:
                    await self._send(
                        "runtime_rejected",
                        **build_runtime_rejection_payload(
                            "STALE_CONFIRMATION",
                            "Confirmation does not match the active plan context.",
                            detail=f"confirmation context mismatch: {mismatch_reason}",
                            current_state=active_confirmation_context or self._confirmation_context(self._current_active_plan_state()),
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

    async def _tool_ask_user(self, args: dict[str, Any]) -> dict[str, Any]:
        question = str(args.get("question") or "").strip()
        options = args.get("options") or []
        if not isinstance(options, list):
            options = []
        correction_state = getattr(self, "_active_plan_correction_state", None)
        if isinstance(correction_state, dict):
            stored_question = self._normalize_space(
                str(correction_state.get("clarification_question") or correction_state.get("last_validation_feedback") or "")
            ).strip().lower()
            normalized_question = self._normalize_space(question).strip().lower()
            if correction_state.get("clarification_closed") or (
                correction_state.get("clarification_resolved")
                and stored_question
                and normalized_question
                and normalized_question == stored_question
            ):
                print("[AGENT] duplicate clarification blocked; correction already resolved")
                correction_state["clarification_closed"] = True
                correction_state["correction_failed"] = True
                correction_state["needs_clarification"] = False
                correction_state["last_validation_reason"] = "clarification already answered"
                correction_state["last_validation_feedback"] = (
                    "Clarification already answered. Produce a correction diff."
                )
                return {
                    "answer": str(correction_state.get("clarification_answer") or "").strip(),
                    "event_type": "duplicate_clarification",
                    "success": False,
                    "skipped": True,
                    "blocked": True,
                    "reason": "clarification_already_answered",
                    "message": "Clarification already answered. Produce a correction diff.",
                    "requires_replan": False,
                    "clarification_resolved": True,
                }

        await self._send(
            "clarification_needed",
            question=question,
            options=[str(option) for option in options],
        )

        while True:
            event = await self.control_queue.get()
            event_type = str(event.get("type") or "")
            if event_type == "option_selected":
                answer = str(event.get("answer") or event.get("message") or "").strip()
                result = {"answer": answer, "event_type": "option_selected", "success": True}
                if isinstance(correction_state, dict) and correction_state.get("needs_clarification"):
                    correction_state["clarification_answer"] = answer
                    correction_state["clarification_resolved"] = True
                    correction_state["clarification_closed"] = False
                    correction_state["needs_clarification"] = False
                    correction_state["clarification_question"] = question
                    result["clarification_resolved"] = True
                    result["clarification_answer"] = answer
                    result["clarification_resolution_message"] = self._build_plan_correction_clarification_message(
                        correction_state,
                        answer,
                    )
                return result
            if event_type == "correction":
                return {
                    "answer": str(event.get("message") or "").strip(),
                    "event_type": "correction",
                }
            if event_type == "confirmed":
                return {"answer": "confirmed", "event_type": "confirmed"}

    def _build_locator_from_strategy(self, strategy: str, element_data: dict[str, Any]) -> str:
        return _locator_resolver.build_locator_from_strategy(strategy, element_data)
    def _build_locator_candidates(self, element_data: dict[str, Any]) -> list[dict[str, str]]:
        element_data = self._resolve_selected_element_info(element_data)
        text = self._selected_element_text(element_data)
        tag = re.sub(r"[^a-zA-Z0-9:_-]", "", str(element_data.get("tag") or "").strip())
        attributes = element_data.get("attributes") if isinstance(element_data.get("attributes"), dict) else {}
        role = (
            str(element_data.get("role") or attributes.get("role") or "").strip()
            or self._infer_role(element_data)
        )
        class_name = str(element_data.get("class") or element_data.get("className") or attributes.get("class") or "").strip()
        classes = [
            re.sub(r"[^a-zA-Z0-9_-]", "", item)
            for item in class_name.split()
            if re.sub(r"[^a-zA-Z0-9_-]", "", item)
        ]
        partial_text = text[:50].strip()
        candidates: list[dict[str, str]] = []

        locator_hint = str(element_data.get("locator_hint") or element_data.get("locatorHint") or "").strip()
        if locator_hint:
            candidates.append(
                {
                    "strategy": "locator_hint",
                    "locator": locator_hint,
                }
            )

        data_testid = str(
            element_data.get("data_testid")
            or element_data.get("dataTestid")
            or attributes.get("data-testid")
            or attributes.get("data-test-id")
            or attributes.get("data-test")
            or attributes.get("data-qa")
            or attributes.get("data-cy")
            or ""
        ).strip()
        if data_testid:
            candidates.append(
                {
                    "strategy": "data-testid",
                    "locator": f'get_by_test_id("{self._tool_string_escape(data_testid)}")',
                }
            )

        aria_label = self._normalize_space(
            str(element_data.get("aria_label") or element_data.get("ariaLabel") or attributes.get("aria-label") or "")
        )
        if aria_label:
            candidates.append(
                {
                    "strategy": "aria-label",
                    "locator": f'get_by_label("{self._tool_string_escape(aria_label)}")',
                }
            )

        element_id = str(element_data.get("id") or attributes.get("id") or "").strip()
        if element_id:
            candidates.append({"strategy": "id", "locator": f"#{self._css_escape(element_id)}"})

        placeholder = self._normalize_space(str(element_data.get("placeholder") or attributes.get("placeholder") or ""))
        if placeholder:
            candidates.append(
                {
                    "strategy": "placeholder",
                    "locator": f'get_by_placeholder("{self._tool_string_escape(placeholder)}")',
                }
            )

        if text:
            candidates.append(
                {
                    "strategy": "exact_text",
                    "locator": f'get_by_text("{self._tool_string_escape(text)}", exact=True)',
                }
            )

        if partial_text:
            candidates.append(
                {
                    "strategy": "partial_text",
                    "locator": f'get_by_text("{self._tool_string_escape(partial_text)}", exact=False)',
                }
            )

        if role and partial_text:
            candidates.append(
                {
                    "strategy": "role+name",
                    "locator": (
                        f'get_by_role("{self._tool_string_escape(role)}", '
                        f'name="{self._tool_string_escape(partial_text)}")'
                    ),
                }
            )

        css_locator = self._build_locator_from_strategy("css", element_data)
        if css_locator:
            candidates.append({"strategy": "css", "locator": css_locator})

        if tag and partial_text:
            candidates.append(
                {
                    "strategy": "relative_xpath",
                    "locator": f"//{tag}[contains(normalize-space(.), {self._xpath_literal(partial_text)})]",
                }
            )

        if tag:
            if element_id:
                absolute_xpath = f"//{tag}[@id={self._xpath_literal(element_id)}]"
            elif classes:
                absolute_xpath = f"//{tag}[contains(@class, {self._xpath_literal(classes[0])})]"
            else:
                absolute_xpath = f"//{tag}"
            candidates.append({"strategy": "absolute_xpath", "locator": absolute_xpath})

        return candidates

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
