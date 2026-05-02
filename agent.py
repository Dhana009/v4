from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any

from playwright.async_api import TimeoutError as PlaywrightTimeoutError
from playwright.async_api import expect

from browser import get_page
from llm import LLMClient
from runtime.context_manager import ContextManager
from runtime.model_router import ModelRouter
from runtime.phase_tracker import PhaseTracker
from runtime.tool_registry import ToolRegistry, filter_tools_for_phase
from runtime.skill_manager import SkillManager
from runtime.telemetry import record_model_call_end, record_model_call_start


SKILL_KEYWORDS: list[tuple[str, tuple[str, ...]]] = [
    ("assertions", ("assert", "verify", "check", "expect", "visible")),
    ("actions", ("click", "fill", "type", "hover", "navigate", "go to")),
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
        self._recording_steps: list[dict[str, Any]] = []
        self._recording_step_index = 0
        self._recorded_step_ids: set[str] = set()
        self._last_action_context: dict[str, Any] | None = None
        self._awaiting_step_record = False
        self._pending_failure_followup = False
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
        self._recording_steps = []
        self._recording_step_index = 0
        self._recorded_step_ids = set()
        self._last_action_context = None
        self._awaiting_step_record = False
        self.run_stop_requested = False
        self._run_completion_requested = False
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

    async def run(self, steps: list[dict]) -> None:
        try:
            self._reset_lifecycle_state(steps)
            self.phase_tracker.set_phase("planning", reason="run_started")
            self._prepare_recording_steps(steps)
            loaded_skill_names, system_prompt, loaded_skills = self._load_skills_for_steps(steps)
            self.llm.system_prompt = system_prompt
            self.llm.reset()
            self._pending_failure_followup = False

            skill_diagnostics = self.skill_manager.analyze(
                loaded_skills,
                loaded_skill_names=loaded_skill_names,
            )
            print(f"[SKILLS LOADED] {' + '.join(loaded_skill_names)}")
            print(
                "[SKILL_DIAGNOSTICS] "
                f"skills={skill_diagnostics.skill_count} "
                f"names={','.join(skill_diagnostics.loaded_skill_names) or 'none'} "
                f"estimated_tokens={skill_diagnostics.estimated_total_skill_tokens} "
                f"largest={skill_diagnostics.largest_skill_name} "
                f"largest_tokens={skill_diagnostics.largest_skill_tokens} "
                f"policy={skill_diagnostics.suggested_future_policy}"
            )
            print("[AGENT] Starting tool-calling loop")

            self.llm.messages.append({"role": "user", "content": self._format_steps(steps)})

            while True:
                print("[AGENT] Requesting LLM response")
                current_phase = self._current_phase()
                filtered_tools = filter_tools_for_phase(self.tools, current_phase)
                context_bundle = self.context_manager.prepare_messages(
                    self.llm.messages,
                    purpose="main_orchestrator",
                    context_mode="normal",
                    metadata={
                        "skill_count": len(loaded_skill_names),
                        "tool_count": len(filtered_tools),
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
                    skill_count=len(loaded_skill_names),
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

                    result = await self._dispatch_tool(tool_name, args)
                    print(f"[TOOL RESULT] {self._summarize(result, limit=100)}")
                    step_context = self._resolve_step_context(tool_name, args, result)
                    tool_failed = result.get("success") is False and not result.get("skipped") and (
                        self._is_browser_state_tool(tool_name) or tool_name == "ask_user"
                    )
                    if tool_failed and tool_name in self.EXECUTION_TOOLS:
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
                        self._mark_step_executing(step_context)
                        self._capture_action_context(tool_name, args, result)
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
                        note = (
                            f"User corrected the plan: {correction}. "
                            "Revise the plan and ask for confirmation again before executing."
                        )
                        self.llm.messages.append({"role": "user", "content": note})
                        print(f"[AGENT] plan corrected: {self._summarize(note, limit=140)}")
                        self._append_skipped_tool_responses(tool_calls, index + 1, batch_stop_reason)
                        break
                    if tool_name in state_changing_tools and tool_failed:
                        print(f"[AGENT] {tool_name} failed; stopping batch for LLM recovery")
                        self._append_skipped_tool_responses(tool_calls, index + 1, batch_stop_reason)
                        break
                    if tool_name in state_changing_tools and result.get("success") is True and not result.get("skipped"):
                        pause_for_fresh_page = True
                        self.phase = "recovering" if had_tool_failure else "executing"
                    if tool_failed and self._is_browser_state_tool(tool_name):
                        print(f"[AGENT] {tool_name} failed; stopping batch for LLM recovery")
                        self._append_skipped_tool_responses(tool_calls, index + 1, batch_stop_reason)
                        break

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
        loaded_skills = {"core": self._read_skill("core")}
        contents = [loaded_skills["core"]]

        for skill_name, keywords in SKILL_KEYWORDS:
            if skill_name == "core":
                continue
            if any(keyword in intents for keyword in keywords):
                loaded_names.append(skill_name)
                skill_text = self._read_skill(skill_name)
                loaded_skills[skill_name] = skill_text
                contents.append(skill_text)

        return loaded_names, "\n\n".join(contents), loaded_skills

    def _read_skill(self, skill_name: str) -> str:
        skill_path = self.skills_root / skill_name / "SKILL.md"
        return skill_path.read_text(encoding="utf-8")

    def _format_steps(self, steps: list[dict]) -> str:
        lines = [
            "User steps:",
            json.dumps(self._normalize_steps(steps), ensure_ascii=True, indent=2),
            "",
            "Execution requirements:",
            "- Always use tools. Never guess.",
            '- Start by calling send_to_overlay with message_type "llm_thinking".',
            "- Use browser_get_state or dom_extract before deciding what is on the page.",
            "- If a step includes suggested_scope for a picked element, call dom_extract with that suggested_scope first.",
            "- Validate locators before using them for actions or assertions.",
            "- Use page_go_back, page_go_forward, and page_reload for browser history or refresh actions.",
            "- Use action_fill only on editable fields. Never use it on body to simulate navigation.",
            '- After a successful recorded step, call send_to_overlay with message_type "step_recorded" and include step_id, step_number, action, element_name, locator, generated_line, and status.',
            "- If the user corrects the plan, revise it before any action and ask for confirmation again.",
            '- When finished, report the outcome clearly through send_to_overlay or the final assistant response.',
        ]
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
            context = {
                "step_id": step_id,
                "step_number": idx,
                "intent": str(step.get("intent") or "").strip(),
                "element_info": raw_element_info,
                "element_name": self._derive_step_context_element_name(step, raw_element_info),
                "locator": None,
                "last_error": None,
                "status": "pending",
                "recorded": False,
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
        self.last_successful_action = None
        self._last_action_context = None
        self._awaiting_step_record = False
        self.current_step_index = max(0, int(context.get("step_number") or 1) - 1)
        print(f"[AGENT] step recovery_pending: {step_id}")
        return context

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
        attrs = element_info.get("attributes") or {}
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

    def _coerce_step_number(self, value: Any) -> int | None:
        try:
            number = int(value)
        except (TypeError, ValueError):
            return None
        return number if number > 0 else None

    def _capture_action_context(self, tool_name: str, args: dict[str, Any], result: dict[str, Any]) -> None:
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

        self.last_successful_action = captured
        if step_id:
            self.successful_action_by_step_id[step_id] = captured
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
        action_record = self._get_successful_action_for_step(step_context, clean_payload)
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
            clean_payload.get("step_id")
            or (recorded_step_context.get("step_id") if recorded_step_context else "")
            or (step_context.get("step_id") if step_context else "")
            or action_record.get("step_id")
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
        status = str(clean_payload.get("status") or "recorded").strip() or "recorded"

        if not action:
            action = "step"
        if not element_name:
            element_name = locator or action
        if not locator and step_context is not None:
            locator = self._derive_locator_from_step_context(step_context) or str(step_context.get("intent") or "").strip()
        if not generated_line:
            generated_line = self._build_generated_line(action, locator, action_context)

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
                if expected_value is None:
                    raise ValueError("expected_value is required for has_text")
                try:
                    actual_text = await locator.inner_text(timeout=timeout)
                except Exception:  # noqa: BLE001
                    actual_text = await locator.text_content(timeout=timeout)

                normalized_actual = self._normalize_assertion_text(actual_text)
                normalized_expected = self._normalize_assertion_text(str(expected_value))
                if normalized_expected not in normalized_actual:
                    return {
                        "success": False,
                        "error": (
                            "Expected normalized text to contain "
                            f"{normalized_expected!r}, got {normalized_actual!r}"
                        ),
                        "actual_text": normalized_actual,
                        "expected_text": normalized_expected,
                    }
                return {
                    "success": True,
                    "assertion": "has_text",
                    "actual_text": normalized_actual,
                    "expected_text": normalized_expected,
                }
            elif assertion == "has_value":
                if expected_value is None:
                    raise ValueError("expected_value is required for has_value")
                await expect(locator).to_have_value(str(expected_value), timeout=timeout)
            elif assertion == "checked":
                await expect(locator).to_be_checked(timeout=timeout)
            else:
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
            if not self._has_successful_action_to_record(target_step, payload):
                step_ref = str(
                    (target_step or {}).get("step_id")
                    or payload.get("step_id")
                    or payload.get("id")
                    or payload.get("stepId")
                    or "unknown"
                ).strip() or "unknown"
                print(f"[AGENT] no successful action context for recorded step: {step_ref}")
                return {
                    "sent": False,
                    "skipped": True,
                    "reason": "No successful confirmed action to record.",
                }

            recovered_context = any(
                not str(payload.get(key) or "").strip()
                for key in ("step_id", "action", "locator")
            )
            payload = self._build_step_record_payload(payload, target_step)
            if not payload:
                return {
                    "sent": False,
                    "skipped": True,
                    "reason": "No successful confirmed action to record.",
                }
            step_id = str(payload.get("step_id") or (target_step or {}).get("step_id") or "").strip()
            if step_id:
                print(f"[AGENT] using successful action for recorded step: {step_id}")
            if recovered_context:
                print(f"[AGENT] recording step with recovered context: {json.dumps(payload, ensure_ascii=True)}")
            else:
                print(f"[AGENT] recording step: {json.dumps(payload, ensure_ascii=True)}")
            await self._send(message_type, **payload)
            recorded_target_step = self.step_state_by_id.get(step_id) if step_id else None
            if recorded_target_step is not None and str(recorded_target_step.get("status") or "") in {"recorded", "skipped"}:
                recorded_target_step = None
            if recorded_target_step is None and target_step is not None:
                target_step_id = str(target_step.get("step_id") or "").strip()
                if not step_id or target_step_id == step_id:
                    recorded_target_step = target_step
            step_number = self._coerce_step_number(payload.get("step_number"))
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
                self._mark_step_recorded(recorded_target_step, payload)
            if step_id:
                self.successful_action_by_step_id.pop(step_id, None)
            last_action = self.last_successful_action or {}
            last_action_step = last_action.get("step_context") or {}
            last_action_step_id = str(last_action_step.get("step_id") or last_action.get("step_id") or "").strip()
            last_action_step_number = self._coerce_step_number(last_action_step.get("step_number") or last_action.get("step_number"))
            recorded_step_number = self._coerce_step_number(payload.get("step_number"))
            if step_id and last_action_step_id == step_id:
                self.last_successful_action = None
            elif step_id and recorded_step_number is not None and last_action_step_number == recorded_step_number:
                self.last_successful_action = None
            elif not step_id and recorded_step_number is not None and last_action_step_number == recorded_step_number:
                self.last_successful_action = None
            self._awaiting_step_record = False
            self._last_action_context = None
            if recorded_target_step is not None:
                recorded_step_id = str(
                    payload.get("step_id")
                    or (recorded_target_step or {}).get("step_id")
                    or payload.get("id")
                    or payload.get("stepId")
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
            return {"sent": True, "payload": payload}
        await self._send(message_type, **payload)
        if message_type == "plan_ready":
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
                answer = str(confirmation.get("answer") or "confirmed").strip() or "confirmed"
                print("[AGENT] plan confirmed; entering execution phase")
                return {"confirmed": True, "answer": answer, "phase": "executing"}

            self.plan_confirmed = False
            self.phase = "planning"
            self.phase_tracker.set_phase("planning", reason="correction", step_id=plan_step_id)
            self.last_successful_action = None
            self._last_action_context = None
            self._awaiting_step_record = False
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
