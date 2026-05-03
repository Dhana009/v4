from __future__ import annotations

import asyncio
from copy import deepcopy
from datetime import datetime, timezone
import json
import os
import re
from pathlib import Path
from typing import Any
from uuid import uuid4

from playwright.async_api import TimeoutError as PlaywrightTimeoutError
from playwright.async_api import expect

from browser import get_page
from llm import LLMClient
from runtime.context_manager import ContextManager
from runtime.model_router import ModelRouter
from runtime.recovery_manager import classify_failure
from runtime.phase_tracker import PhaseTracker
from runtime.spec_snapshot import build_spec_snapshot
from runtime.tool_registry import ToolRegistry, filter_tools_for_phase
from runtime.skill_manager import SkillManager
from runtime.telemetry import record_model_call_end, record_model_call_start


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
        self.llm = LLMClient()
        self.context_manager = ContextManager()
        self.model_router = ModelRouter()
        self.skill_manager = SkillManager()
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
        self._plan_correction_pending = False
        self.capability_gaps: list[dict[str, Any]] = []
        self.recorded_step_payloads: list[dict[str, Any]] = []
        self.code_update_payloads: list[dict[str, Any]] = []
        self.replay_recorded_step_payloads_by_step_id: dict[str, dict[str, Any]] = {}
        self.replay_action_history_by_step_id: dict[str, list[dict[str, Any]]] = {}
        self._run_session_id = self._new_run_session_id()
        self._run_completion_requested = False
        self.run_stop_requested = False
        self._llm_call_counter = 0

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
        self._plan_correction_pending = False
        self.capability_gaps = []
        self.recorded_step_payloads = []
        self.code_update_payloads = []
        if steps is not None:
            self.replay_recorded_step_payloads_by_step_id = {}
            self.replay_action_history_by_step_id = {}
        self._run_session_id = self._new_run_session_id()
        self._clear_plan_review_context()
        self._llm_call_counter = 0

    async def _send(self, msg_type: str, **kwargs: Any) -> None:
        payload = {"type": msg_type}
        payload.update(kwargs)
        await self.ws.send_json(payload)

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
            skill_text = self._read_skill(skill_name)
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

            while True:
                print("[AGENT] Requesting LLM response")
                current_phase = self._current_phase()
                self._load_phase_skill_expansion(current_phase)
                awaiting_step_record = bool(
                    getattr(self, "_awaiting_step_record", False)
                    and getattr(self, "_recording_wait_guard_armed", False)
                )
                filtered_tools = filter_tools_for_phase(
                    self.tools,
                    current_phase,
                    awaiting_step_record=awaiting_step_record,
                )
                context_bundle = self.context_manager.prepare_messages(
                    self.llm.messages,
                    purpose="main_orchestrator",
                    context_mode="normal",
                    metadata={
                        "skill_count": len(self._loaded_skill_names),
                        "tool_count": len(filtered_tools),
                        "phase": current_phase,
                    },
                )
                self._llm_call_counter += 1
                call_id = f"llm_{self._llm_call_counter:03d}"
                model = "gpt-4o-mini"
                telemetry = record_model_call_start(
                    call_id=call_id,
                    purpose="main_orchestrator",
                    model=model,
                    messages=context_bundle.messages,
                    tools=filtered_tools,
                    skill_count=len(self._loaded_skill_names),
                )
                try:
                    response = await self.model_router.call(
                        purpose="main_orchestrator",
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
                        and str(args.get("message_type") or "").strip() == "step_recorded"
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
                            and str(args.get("message_type") or "").strip() == "step_recorded"
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
                        self._mark_step_failed(step_context, result.get("error") or "execution tool failed")
                    had_tool_failure = had_tool_failure or tool_failed
                    is_plan_rejected = (
                        tool_name == "send_to_overlay"
                        and str(args.get("message_type") or "") == "plan_ready"
                        and result.get("confirmed") is False
                    )
                    if (
                        result.get("success") is True
                        and not result.get("skipped")
                        and tool_name in self.EXECUTION_TOOLS
                    ):
                        browser_state_after = await self._capture_browser_state()
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
                        and str(args.get("message_type") or "").strip() == "step_recorded"
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
                    if is_plan_rejected:
                        correction = str(result.get("correction") or "").strip() or "the user requested a correction"
                        note = self._append_plan_correction_message(correction)
                        print(f"[AGENT] plan corrected: {self._summarize(note, limit=140)}")
                        self._append_skipped_tool_responses(tool_calls, index + 1, batch_stop_reason)
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
        core_skill_text = self._read_skill("core") or ""
        loaded_skills = {"core": core_skill_text}
        contents = [core_skill_text]

        for skill_name, keywords in SKILL_KEYWORDS:
            if skill_name == "core":
                continue
            if any(keyword in intents for keyword in keywords):
                skill_text = self._read_skill(skill_name)
                if skill_text is None:
                    continue
                loaded_names.append(skill_name)
                loaded_skills[skill_name] = skill_text
                contents.append(skill_text)

        return loaded_names, "\n\n".join(contents), loaded_skills

    def _read_skill(self, skill_name: str) -> str | None:
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

    def _is_click_like_intent(self, intent: Any) -> bool:
        normalized_intent = self._normalize_space(str(intent or "")).lower()
        return bool(CLICK_LIKE_INTENT_PATTERN.search(normalized_intent))

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

    def _compact_step_element_summary(self, step: dict[str, Any]) -> str:
        element_info = step.get("element_info") or {}
        if not isinstance(element_info, dict):
            return ""

        attributes = element_info.get("attributes") if isinstance(element_info.get("attributes"), dict) else {}
        candidates = [
            self._normalize_space(str(element_info.get("text") or "")).strip(),
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
            step_id = str(step.get("id") or "").strip() or str(idx)
            intent_text = str(step.get("intent") or "").strip()
            context = {
                "step_id": step_id,
                "step_number": idx,
                "intent": intent_text,
                "element_info": raw_element_info,
                "element_name": self._derive_step_context_element_name(step, raw_element_info),
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

    def _build_plan_step_context_lines(self) -> list[str]:
        plan_ready_payload = getattr(self, "last_plan_ready_payload", None)
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
        return step_lines

    def _build_plan_correction_message(self, correction: str) -> str:
        correction_text = self._normalize_space(correction) or "the user requested a correction"
        lines = [
            "User corrected the current plan.",
            f'Correction: "{correction_text}"',
        ]
        original_user_intent = str(self.last_plan_original_user_intent or "").strip()
        if original_user_intent:
            lines.append(f'Original user intent: "{original_user_intent}"')
        previous_summary = str(self.last_plan_summary or "").strip()
        if previous_summary:
            lines.append(f'Previous plan summary: "{previous_summary}"')
        step_lines = self._build_plan_step_context_lines()
        if step_lines:
            lines.append("Previous plan steps:")
            lines.extend(step_lines)
        else:
            lines.append("Previous plan steps: none available.")
        lines.append("Revise the plan. Do not execute. Send a new plan_ready for confirmation.")
        return "\n".join(lines)

    def _append_plan_correction_message(self, correction: str) -> str:
        message = self._build_plan_correction_message(correction)
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
        element_info = step.get("element_info") if isinstance(step.get("element_info"), dict) else {}
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
        attrs = element_info.get("attributes") if isinstance(element_info.get("attributes"), dict) else {}
        candidates = [
            str(element_info.get("text") or "").strip(),
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
        element_info = step.get("element_info") or {}
        attrs = element_info.get("attributes") or {}
        parts = [
            str(step.get("intent") or "").strip(),
            str(step.get("element_name") or "").strip(),
            str(element_info.get("text") or "").strip(),
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
        target_step = step_context or self._resolve_recording_target_step(payload)
        if not self._has_successful_action_to_record(target_step, payload):
            step_ref = str(
                (target_step or {}).get("step_id")
                or payload.get("step_id")
                or payload.get("id")
                or payload.get("stepId")
                or "unknown"
            ).strip() or "unknown"
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
        if recorded_target_step is None and (step_id or step_number is not None):
            recorded_target_step = self._find_step_for_recording(
                step_id or None,
                step_number,
            )
        if recorded_target_step is None:
            unresolved_steps = [
                step
                for step in self._recording_steps
                if str(step.get("status") or "") not in {"recorded", "skipped"}
            ]
            if len(unresolved_steps) == 1:
                recorded_target_step = unresolved_steps[0]
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
        return await self._record_step_payload(payload, target_step)

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
        return context

    def _derive_element_name(
        self,
        step: dict[str, Any],
        action_context: dict[str, Any],
        locator: str,
    ) -> str:
        element_info = step.get("element_info") or {}
        attrs = element_info.get("attributes") or {}
        candidates = [
            str(element_info.get("text") or "").strip(),
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

        match = re.fullmatch(r'get_by_test_id\("((?:\\.|[^"])*)"\)', locator)
        if match:
            return self._tool_string_unescape(match.group(1))

        match = re.fullmatch(r'get_by_label\("((?:\\.|[^"])*)"\)', locator)
        if match:
            return self._tool_string_unescape(match.group(1))

        match = re.fullmatch(r'get_by_placeholder\("((?:\\.|[^"])*)"\)', locator)
        if match:
            return self._tool_string_unescape(match.group(1))

        match = re.fullmatch(r'get_by_text\("((?:\\.|[^"])*)", exact=(True|False)\)', locator)
        if match:
            return self._tool_string_unescape(match.group(1))

        match = re.fullmatch(r'get_by_role\("((?:\\.|[^"])*)", name="((?:\\.|[^"])*)"\)', locator)
        if match:
            return self._tool_string_unescape(match.group(2))

        if locator.startswith("#"):
            return locator[1:]
        return ""

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
                return (
                    f"await expect({locator_expr}).toHaveValue("
                    f"{json.dumps(str(action_context.get('expected_value') or ''), ensure_ascii=True)});"
                )
            if assertion == "has_text":
                return (
                    f"await expect({locator_expr}).toContainText("
                    f"{json.dumps(str(action_context.get('expected_value') or ''), ensure_ascii=True)});"
                )
            return f"await expect({locator_expr}).toBeVisible();"
        if not locator_expr:
            locator_expr = "page.locator(\"\")"
        return f"await {locator_expr}.{action}();"

    def _locator_to_playwright_expression(self, locator: str) -> str:
        locator = str(locator or "").strip()
        if not locator:
            return ""

        if match := re.fullmatch(r'get_by_test_id\("((?:\\.|[^"])*)"\)', locator):
            return f'page.getByTestId({json.dumps(self._tool_string_unescape(match.group(1)), ensure_ascii=True)})'

        if match := re.fullmatch(r'get_by_label\("((?:\\.|[^"])*)"\)', locator):
            return f'page.getByLabel({json.dumps(self._tool_string_unescape(match.group(1)), ensure_ascii=True)})'

        if match := re.fullmatch(r'get_by_placeholder\("((?:\\.|[^"])*)"\)', locator):
            return f'page.getByPlaceholder({json.dumps(self._tool_string_unescape(match.group(1)), ensure_ascii=True)})'

        if match := re.fullmatch(
            r'get_by_text\("((?:\\.|[^"])*)", exact=(True|False)\)', locator
        ):
            text = self._tool_string_unescape(match.group(1))
            exact = match.group(2) == "True"
            return f'page.getByText({json.dumps(text, ensure_ascii=True)}, {{ exact: {str(exact).lower()} }})'

        if match := re.fullmatch(
            r'get_by_role\("((?:\\.|[^"])*)", name="((?:\\.|[^"])*)"\)', locator
        ):
            role = self._tool_string_unescape(match.group(1))
            name = self._tool_string_unescape(match.group(2))
            return (
                f'page.getByRole({json.dumps(role, ensure_ascii=True)}, '
                f'{{ name: {json.dumps(name, ensure_ascii=True)} }})'
            )

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
        step_context = step_context or self._resolve_recording_target_step(clean_payload)
        action_history = self._get_successful_action_history_for_step(step_context, clean_payload)
        if action_history:
            action_record = action_history[-1]
        else:
            action_record = self._get_successful_action_for_step(step_context, clean_payload)
            if action_record:
                action_history = [action_record]
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
        children = self._build_recorded_children(action_history, intent, element_name, locator)
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
        element_info = step.get("element_info") or {}
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
            element_info = step.get("element_info") or {}
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

        return [
            {
                "operation_id": f"op_{index}",
                "type": current_operation_type,
                "description": self._build_planned_child_description(current_operation_type, target, intent),
                "target": target,
                "locator": locator,
                "status": "planned",
            }
            for index, current_operation_type in enumerate(operation_types, start=1)
        ]

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

    def _build_recorded_children(
        self,
        action_records: list[dict[str, Any]],
        intent: str,
        element_name: str,
        locator: str,
    ) -> list[dict[str, Any]]:
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
            generated_line = str(payload.get("generated_line") or "").strip()
            if not generated_line:
                return {}
            lines = [generated_line]
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
        page = get_page()
        scope = str(args.get("scope") or "page").strip() or "page"
        html = ""

        if scope == "page":
            html = await page.content()
        else:
            html = await page.evaluate(
                """
                ({ scope }) => {
                  const node = document.querySelector(scope);
                  return node ? node.outerHTML : "";
                }
                """,
                {"scope": scope},
            )

        cleaned = self._clean_markup(html)[:3000]
        return {"elements": cleaned, "url": page.url}

    async def _tool_locator_find(self, args: dict[str, Any]) -> dict[str, Any]:
        page = get_page()
        element_data = args.get("element_data") or {}
        candidates = self._build_locator_candidates(element_data)
        tried: list[dict[str, Any]] = []

        for candidate in candidates:
            locator_string = candidate["locator"]
            strategy = candidate["strategy"]

            try:
                locator = self._resolve_locator(page, locator_string)
                count = await locator.count()
            except Exception as exc:  # noqa: BLE001
                tried.append(
                    {
                        "strategy": strategy,
                        "locator": locator_string,
                        "count": 0,
                        "error": str(exc),
                    }
                )
                continue

            if count == 1:
                return {
                    "found": True,
                    "locator": locator_string,
                    "strategy": strategy,
                    "count": 1,
                    "stable": self._is_stable_locator_strategy(strategy),
                    "tried": tried,
                }

            tried.append(
                {
                    "strategy": strategy,
                    "locator": locator_string,
                    "count": count,
                }
            )

        return {
            "found": False,
            "locator": "",
            "strategy": "",
            "count": 0,
            "stable": False,
            "tried": tried,
        }

    async def _tool_locator_validate(self, args: dict[str, Any]) -> dict[str, Any]:
        page = get_page()
        locator_string = str(args.get("locator") or "").strip()
        count = 0
        if locator_string:
            try:
                count = await self._resolve_locator(page, locator_string).count()
            except Exception:  # noqa: BLE001
                count = 0
        return {"valid": count == 1, "count": count}

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
            return {"sent": True, "payload": recorded_payload}
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
            plan_correction_pending = bool(getattr(self, "_plan_correction_pending", False))
            payload = self._build_plan_ready_payload(
                payload,
                prefer_plan_step_source=plan_correction_pending,
            )
            self._plan_correction_pending = False
        await self._send(message_type, **payload)
        if message_type == "plan_ready":
            self._remember_plan_review_context(payload)
            plan_step_id = str(
                payload.get("step_id")
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
            return {"confirmed": False, "correction": correction, "phase": "planning"}
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
        while True:
            event = await self.control_queue.get()
            event_type = str(event.get("type") or "")
            answer = str(event.get("message") or event.get("answer") or "").strip()
            if event_type == "correction":
                return {"confirmed": False, "correction": answer}
            if event_type == "confirmed":
                return {"confirmed": True, "answer": "confirmed"}
            if event_type == "option_selected":
                return {"confirmed": True, "answer": answer}

    async def _tool_ask_user(self, args: dict[str, Any]) -> dict[str, Any]:
        question = str(args.get("question") or "").strip()
        options = args.get("options") or []
        if not isinstance(options, list):
            options = []

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
                return {"answer": answer, "event_type": "option_selected"}
            if event_type == "correction":
                return {
                    "answer": str(event.get("message") or "").strip(),
                    "event_type": "correction",
                }
            if event_type == "confirmed":
                return {"answer": "confirmed", "event_type": "confirmed"}

    def _build_locator_from_strategy(self, strategy: str, element_data: dict[str, Any]) -> str:
        tag = str(element_data.get("tag") or "*").strip() or "*"
        text = self._normalize_space(str(element_data.get("text") or ""))
        element_id = str(element_data.get("id") or "").strip()
        class_name = str(element_data.get("class") or "").strip()
        aria_label = self._normalize_space(str(element_data.get("aria_label") or ""))
        data_testid = str(element_data.get("data_testid") or "").strip()
        placeholder = self._normalize_space(str(element_data.get("placeholder") or ""))
        parent_tag = str(element_data.get("parent_tag") or "").strip()
        parent_id = str(element_data.get("parent_id") or "").strip()

        if strategy == "data_testid" and data_testid:
            return f'[data-testid="{self._css_escape(data_testid)}"]'
        if strategy == "aria_label" and aria_label:
            return f'[aria-label="{self._css_escape(aria_label)}"]'
        if strategy == "id" and element_id:
            return f"#{self._css_escape(element_id)}"
        if strategy == "placeholder" and placeholder:
            return f'[placeholder="{self._css_escape(placeholder)}"]'
        if strategy == "exact_text" and text:
            return f'text="{self._text_escape(text)}"'
        if strategy == "partial_text" and text:
            partial = text[:80].strip()
            return f"text={self._text_escape(partial)}"
        if strategy == "css":
            tag_part = re.sub(r"[^a-zA-Z0-9:_-]", "", tag) or "*"
            classes = [
                re.sub(r"[^a-zA-Z0-9_-]", "", item)
                for item in class_name.split()
                if re.sub(r"[^a-zA-Z0-9_-]", "", item)
            ]
            base = tag_part
            if classes:
                base += "." + ".".join(classes[:3])
            if parent_id:
                return f"#{self._css_escape(parent_id)} {base}"
            if parent_tag:
                parent = re.sub(r"[^a-zA-Z0-9:_-]", "", parent_tag)
                if parent:
                    return f"{parent} {base}"
            return base
        return ""

    def _build_locator_candidates(self, element_data: dict[str, Any]) -> list[dict[str, str]]:
        text = self._normalize_space(str(element_data.get("text") or ""))
        tag = re.sub(r"[^a-zA-Z0-9:_-]", "", str(element_data.get("tag") or "").strip())
        role = str(element_data.get("role") or "").strip() or self._infer_role(element_data)
        class_name = str(element_data.get("class") or "").strip()
        classes = [
            re.sub(r"[^a-zA-Z0-9_-]", "", item)
            for item in class_name.split()
            if re.sub(r"[^a-zA-Z0-9_-]", "", item)
        ]
        partial_text = text[:50].strip()
        candidates: list[dict[str, str]] = []

        data_testid = str(element_data.get("data_testid") or "").strip()
        if data_testid:
            candidates.append(
                {
                    "strategy": "data-testid",
                    "locator": f'get_by_test_id("{self._tool_string_escape(data_testid)}")',
                }
            )

        aria_label = self._normalize_space(str(element_data.get("aria_label") or ""))
        if aria_label:
            candidates.append(
                {
                    "strategy": "aria-label",
                    "locator": f'get_by_label("{self._tool_string_escape(aria_label)}")',
                }
            )

        element_id = str(element_data.get("id") or "").strip()
        if element_id:
            candidates.append({"strategy": "id", "locator": f"#{self._css_escape(element_id)}"})

        placeholder = self._normalize_space(str(element_data.get("placeholder") or ""))
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
        locator_string = str(locator_string or "").strip()
        if not locator_string:
            raise ValueError("locator is required")

        if match := re.fullmatch(r'get_by_test_id\("((?:\\.|[^"])*)"\)', locator_string):
            return page.get_by_test_id(self._tool_string_unescape(match.group(1)))

        if match := re.fullmatch(r'get_by_label\("((?:\\.|[^"])*)"\)', locator_string):
            return page.get_by_label(self._tool_string_unescape(match.group(1)))

        if match := re.fullmatch(r'get_by_placeholder\("((?:\\.|[^"])*)"\)', locator_string):
            return page.get_by_placeholder(self._tool_string_unescape(match.group(1)))

        if match := re.fullmatch(
            r'get_by_text\("((?:\\.|[^"])*)", exact=(True|False)\)', locator_string
        ):
            return page.get_by_text(
                self._tool_string_unescape(match.group(1)),
                exact=match.group(2) == "True",
            )

        if match := re.fullmatch(
            r'get_by_role\("((?:\\.|[^"])*)", name="((?:\\.|[^"])*)"\)', locator_string
        ):
            return page.get_by_role(
                self._tool_string_unescape(match.group(1)),
                name=self._tool_string_unescape(match.group(2)),
            )

        return page.locator(locator_string)

    def _is_stable_locator_strategy(self, strategy: str) -> bool:
        return strategy in {"data-testid", "aria-label", "id", "role+name"}

    def _infer_role(self, element_data: dict[str, Any]) -> str:
        explicit_role = str(element_data.get("role") or "").strip()
        if explicit_role:
            return explicit_role

        tag = str(element_data.get("tag") or "").strip().lower()
        input_type = str(element_data.get("type") or "").strip().lower()

        if tag == "button":
            return "button"
        if tag == "a":
            return "link"
        if tag == "select":
            return "combobox"
        if tag == "textarea":
            return "textbox"
        if tag == "input":
            if input_type in {"button", "submit", "reset"}:
                return "button"
            if input_type in {"checkbox"}:
                return "checkbox"
            if input_type in {"radio"}:
                return "radio"
            return "textbox"
        return ""

    def _build_suggested_scope(self, element_info: dict[str, Any]) -> str:
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
        cleaned = html or ""
        for tag in ("style", "script", "svg"):
            cleaned = re.sub(
                rf"<{tag}\b[^>]*>.*?</{tag}>",
                "",
                cleaned,
                flags=re.IGNORECASE | re.DOTALL,
            )
        cleaned = re.sub(r"\s+", " ", cleaned).strip()
        return cleaned

    def _summarize(self, value: Any, limit: int = 100) -> str:
        if isinstance(value, dict):
            if "elements" in value:
                text = str(value.get("elements") or "")
            elif "message" in value:
                text = str(value.get("message") or "")
            else:
                text = json.dumps(value, ensure_ascii=True)
        else:
            text = json.dumps(value, ensure_ascii=True) if not isinstance(value, str) else value
        text = text.replace("\n", " ").strip()
        return text[:limit]

    def _css_escape(self, value: str) -> str:
        return value.replace("\\", "\\\\").replace('"', '\\"')

    def _text_escape(self, value: str) -> str:
        return value.replace("\\", "\\\\").replace('"', '\\"')

    def _normalize_space(self, value: str) -> str:
        return re.sub(r"\s+", " ", value).strip()

    def _normalize_assertion_text(self, value: str | None) -> str:
        if value is None:
            return ""
        normalized = str(value)
        normalized = normalized.replace("&nbsp;", " ")
        normalized = normalized.replace("\u00a0", " ")
        normalized = normalized.replace("\u202f", " ")
        normalized = normalized.replace("\u2007", " ")
        normalized = normalized.replace("\u0000", "")
        normalized = re.sub(r"[\x01-\x08\x0b\x0c\x0e-\x1f\x7f]", "", normalized)
        normalized = re.sub(r"\s+", " ", normalized)
        return normalized.strip()

    def _tool_string_escape(self, value: str) -> str:
        return value.replace("\\", "\\\\").replace('"', '\\"')

    def _tool_string_unescape(self, value: str) -> str:
        return value.replace('\\"', '"').replace("\\\\", "\\")

    def _xpath_literal(self, value: str) -> str:
        if "'" not in value:
            return f"'{value}'"
        if '"' not in value:
            return f'"{value}"'
        parts = value.split("'")
        quoted_parts = [f"'{part}'" for part in parts]
        return 'concat(' + ', "\'", '.join(quoted_parts) + ')'
