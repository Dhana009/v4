from __future__ import annotations
import asyncio
import json
from pathlib import Path
from typing import TYPE_CHECKING, Any
from uuid import uuid4

from browser import get_page
from playwright.async_api import TimeoutError as PlaywrightTimeoutError
from playwright.async_api import expect

if TYPE_CHECKING:
    from agent import AgentLoop


class ToolDispatcher:
    def __init__(self, loop: "AgentLoop") -> None:
        self._loop = loop

    def is_browser_state_tool(self, tool_name: str) -> bool:
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

    def parse_tool_args(self, raw_args: str) -> dict[str, Any]:
        parsed = json.loads(raw_args or "{}")
        if not isinstance(parsed, dict):
            raise ValueError("Tool arguments must decode to an object")
        return parsed

    def normalize_wait_until(self, value: Any) -> str:
        wait_until = str(value or "domcontentloaded").strip() or "domcontentloaded"
        if wait_until not in {"load", "domcontentloaded", "networkidle"}:
            return "domcontentloaded"
        return wait_until

    def append_tool_response(self, tool_call_id: str, result: dict[str, Any]) -> None:
        self._loop.llm.messages.append(
            {
                "role": "tool",
                "tool_call_id": tool_call_id,
                "content": json.dumps(result, ensure_ascii=True),
            }
        )

    def append_skipped_tool_response(self, tool_call_id: str, reason: str) -> None:
        self.append_tool_response(
            tool_call_id,
            {
                "success": False,
                "skipped": True,
                "reason": reason,
                "requires_replan": True,
            },
        )

    def append_skipped_tool_responses(self, tool_calls: list[Any], start_index: int, reason: str) -> None:
        for skipped_call in tool_calls[start_index:]:
            self.append_skipped_tool_response(skipped_call.id, reason)

    async def dispatch(self, tool_name: str, args: dict[str, Any]) -> dict[str, Any]:
        return await self._loop._dispatch_tool(tool_name, args)

    async def tool_action_click(self, args: dict[str, Any]) -> dict[str, Any]:
        page = get_page()
        locator_string = str(args.get("locator") or "").strip()
        timeout = int(args.get("timeout") or 30000)
        try:
            await self._loop._resolve_locator(page, locator_string).first.click(timeout=timeout)
            return {"success": True, "error": None}
        except Exception as exc:  # noqa: BLE001
            return {"success": False, "error": str(exc)}

    async def tool_action_fill(self, args: dict[str, Any]) -> dict[str, Any]:
        page = get_page()
        locator_string = str(args.get("locator") or "").strip()
        value = str(args.get("value") or "")
        timeout = int(args.get("timeout") or 30000)
        try:
            locator = self._loop._resolve_locator(page, locator_string).first
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

    async def tool_action_assert(self, args: dict[str, Any]) -> dict[str, Any]:
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
            locator = self._loop._resolve_locator(page, locator_text).first
            if assertion == "visible":
                await expect(locator).to_be_visible(timeout=timeout)
            elif assertion == "hidden":
                await expect(locator).to_be_hidden(timeout=timeout)
            elif assertion == "enabled":
                await expect(locator).to_be_enabled(timeout=timeout)
            elif assertion == "disabled":
                await expect(locator).to_be_disabled(timeout=timeout)
            elif assertion == "has_text":
                normalized_expected = self._loop._normalize_assertion_text(str(expected_value))
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

                    normalized_actual = self._loop._normalize_assertion_text(actual_text)
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
                self._loop._record_capability_gap(
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

    async def tool_page_navigate(self, args: dict[str, Any]) -> dict[str, Any]:
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

    async def tool_page_go_back(self, args: dict[str, Any]) -> dict[str, Any]:
        page = get_page()
        wait_until = self._loop._normalize_wait_until(args.get("wait_until"))
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

    async def tool_page_go_forward(self, args: dict[str, Any]) -> dict[str, Any]:
        page = get_page()
        wait_until = self._loop._normalize_wait_until(args.get("wait_until"))
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

    async def tool_page_reload(self, args: dict[str, Any]) -> dict[str, Any]:
        page = get_page()
        wait_until = self._loop._normalize_wait_until(args.get("wait_until"))
        try:
            await page.reload(wait_until=wait_until)
            return {"success": True, "url": page.url, "title": await page.title()}
        except Exception as exc:  # noqa: BLE001
            return {"success": False, "error": str(exc), "url": page.url}

    async def tool_scroll_into_view(self, args: dict[str, Any]) -> dict[str, Any]:
        page = get_page()
        locator_string = str(args.get("locator") or "").strip()
        timeout = int(args.get("timeout") or 5000)
        try:
            locator = self._loop._resolve_locator(page, locator_string).first
            await locator.scroll_into_view_if_needed(timeout=timeout)
            return {"success": True, "locator": locator_string}
        except Exception as exc:  # noqa: BLE001
            return {"success": False, "error": str(exc), "locator": locator_string}

    async def tool_screenshot_take(self, args: dict[str, Any]) -> dict[str, Any]:
        page = get_page()
        filename = str(args.get("filename") or "screenshot.png")
        output_dir = Path(".hermes/screenshots")
        output_dir.mkdir(parents=True, exist_ok=True)
        path = output_dir / filename
        await page.screenshot(path=str(path))
        return {"path": str(path), "success": True}

    async def tool_send_to_overlay(self, args: dict[str, Any]) -> dict[str, Any]:
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
            if not self._loop.plan_confirmed:
                return {
                    "sent": False,
                    "blocked": True,
                    "requires_confirmation": True,
                    "reason": "step_recorded blocked before confirmed execution.",
                }
            target_step = self._loop._resolve_recording_target_step(payload)
            recorded_payload = await self._loop._record_step_payload(payload, target_step)
            if not recorded_payload:
                return {
                    "sent": False,
                    "skipped": True,
                    "reason": "No successful confirmed action to record.",
                }
            await self._loop._emit_run_completed_event(payload, recorded_payload)
            return {"sent": True, "payload": recorded_payload}

        correction_state = getattr(self._loop, "_active_plan_correction_state", None)
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
                f"{self._loop._summarize(failure_message, limit=140)}"
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
            corrected_payload = self._loop._build_structured_plan_correction_payload_from_diff(payload)
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
                    f"{self._loop._summarize(failure_message, limit=140)}"
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
            pending_recovery = bool(getattr(self._loop, "pending_recovery", False))
            active_failed_step_id = str(getattr(self._loop, "active_failed_step_id", "") or "").strip()
            pending_failure_followup = bool(getattr(self._loop, "_pending_failure_followup", False))
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
            current_phase = self._loop._current_phase()
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
                        f"schema retry {schema_retry_count}: {self._loop._summarize(retry_message, limit=140)}"
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
                    f"{self._loop._summarize(failure_message, limit=140)}"
                )
                return {
                "sent": False,
                "blocked": True,
                "reason": "correction_diff_required",
                "message": failure_message,
                "requires_replan": False,
            }
            plan_correction_pending = bool(getattr(self._loop, "_plan_correction_pending", False))
            payload = self._loop._build_plan_ready_payload(
                payload,
                prefer_plan_step_source=plan_correction_pending,
            )
            plan_id = str(payload.get("plan_id") or payload.get("planId") or "").strip()
            if not plan_id:
                active_plan_state = self._loop._current_active_plan_state()
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
            validation_result = self._loop._validate_structured_plan_correction(payload)
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
                        f"{self._loop._summarize(validation_feedback, limit=140)}"
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
                validation_feedback = self._loop._build_plan_correction_validation_feedback(
                    correction_state,
                    validation_reason,
                    active_plan_state=self._loop._current_active_plan_state(),
                    proposed_payload=payload,
                )
                if correction_state.get("needs_clarification"):
                    correction_state["clarification_question"] = validation_feedback
                correction_state["last_validation_feedback"] = validation_feedback
                print(f"[AGENT] corrected plan rejected: {self._loop._summarize(validation_feedback, limit=140)}")
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
                    active_plan_state = self._loop._current_active_plan_state()
                    plan_id = str((active_plan_state or {}).get("plan_id") or "").strip()
                    if plan_id:
                        payload["plan_id"] = plan_id
                if not str(payload.get("target_step_id") or "").strip():
                    target_step_id = str(payload.get("target_step_id") or payload.get("targetStepId") or "").strip()
                    if target_step_id:
                        payload["target_step_id"] = target_step_id
                self._loop._active_plan_state = self._loop._build_active_plan_state(
                    payload,
                    source_plan_state=self._loop._current_active_plan_state(),
                )

        if message_type in {"plan_ready", "plan_correction_diff"}:
            return await self._loop._send_plan_ready_after_confirmation(payload)

        await self._loop._send(message_type, **payload)
        return {"sent": True}

    async def tool_ask_user(self, args: dict[str, Any]) -> dict[str, Any]:
        question = str(args.get("question") or "").strip()
        options = args.get("options") or []
        if not isinstance(options, list):
            options = []
        correction_state = getattr(self._loop, "_active_plan_correction_state", None)
        if isinstance(correction_state, dict):
            stored_question = self._loop._normalize_space(
                str(correction_state.get("clarification_question") or correction_state.get("last_validation_feedback") or "")
            ).strip().lower()
            normalized_question = self._loop._normalize_space(question).strip().lower()
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

        await self._loop._send(
            "clarification_needed",
            question=question,
            options=[str(option) for option in options],
        )

        while True:
            event = await self._loop.control_queue.get()
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
                    result["clarification_resolution_message"] = self._loop._build_plan_correction_clarification_message(
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
