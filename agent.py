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
        await self._emitter.send(msg_type, **kwargs)

    def _emit_backend_event_now(self, msg_type: str, **kwargs: Any) -> None:
        self._emitter.emit_now(msg_type, **kwargs)

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
        return self._plan_correction.select_plan_correction_child_target(candidates)

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
        return self._plan_correction.build_plan_correction_child_description(operation_type, target, assertion, value_text, raw_description, intent)

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
        return self._tool_dispatcher.normalize_wait_until(value)

    def _append_tool_response(self, tool_call_id: str, result: dict[str, Any]) -> None:
        return self._tool_dispatcher.append_tool_response(tool_call_id, result)

    def _append_skipped_tool_response(self, tool_call_id: str, reason: str) -> None:
        return self._tool_dispatcher.append_skipped_tool_response(tool_call_id, reason)

    def _append_skipped_tool_responses(self, tool_calls: list[Any], start_index: int, reason: str) -> None:
        return self._tool_dispatcher.append_skipped_tool_responses(tool_calls, start_index, reason)

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
