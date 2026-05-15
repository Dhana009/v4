from __future__ import annotations
from copy import deepcopy
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from agent import AgentLoop


class Replay:
    def __init__(self, loop: "AgentLoop") -> None:
        self._loop = loop

    async def replay_one(self, step_id: str) -> dict:
        replay_step_id = str(step_id or "").strip()
        if not replay_step_id:
            return {
                "type": "replay_one_result",
                "ok": False,
                "step_id": "",
                "error": "Replay requires step_id",
            }

        recorded_step_payload = self.get_replay_recorded_step_payload(replay_step_id)
        if not isinstance(recorded_step_payload, dict):
            return {
                "type": "replay_one_result",
                "ok": False,
                "step_id": replay_step_id,
                "error": "Recorded step not found",
            }

        action_history = self.get_replay_action_history(replay_step_id)
        if not action_history:
            return {
                "type": "replay_one_result",
                "ok": False,
                "step_id": replay_step_id,
                "error": "Recorded action history unavailable for replay",
            }

        precondition_failure = await self.check_replay_precondition(
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
                    "error": self.safe_replay_error_message("Recorded action history entry is invalid"),
                }

            action_name = str(
                action_record.get("action")
                or self._loop._action_name_for_tool(str(action_record.get("tool") or ""))
                or ""
            ).strip().lower()
            if action_name not in supported_actions:
                return {
                    "type": "replay_one_result",
                    "ok": False,
                    "step_id": replay_step_id,
                    "failed_operation_id": child_operation_id,
                    "error": self.safe_replay_error_message(f"Unsupported replay operation: {action_name or 'unknown'}"),
                }

            replay_args: dict = {}
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
                    "error": self.safe_replay_error_message(f"Replay requires stored locator for {action_name}"),
                }

            if action_name == "fill" and ("value" not in replay_args or replay_args.get("value") is None):
                return {
                    "type": "replay_one_result",
                    "ok": False,
                    "step_id": replay_step_id,
                    "failed_operation_id": child_operation_id,
                    "error": self.safe_replay_error_message("Replay requires stored value for fill"),
                }

            if action_name == "assert":
                assertion = str(replay_args.get("assertion") or "").strip()
                if assertion not in supported_assertions:
                    return {
                        "type": "replay_one_result",
                        "ok": False,
                        "step_id": replay_step_id,
                        "failed_operation_id": child_operation_id,
                        "error": self.safe_replay_error_message(f"Unsupported replay assertion: {assertion or 'unknown'}"),
                    }
                if assertion in {"has_text", "has_value"} and (
                    "expected_value" not in replay_args or replay_args.get("expected_value") is None
                ):
                    return {
                        "type": "replay_one_result",
                        "ok": False,
                        "step_id": replay_step_id,
                        "failed_operation_id": child_operation_id,
                        "error": self.safe_replay_error_message(
                            f"Replay requires stored expected_value for {assertion}"
                        ),
                    }

            if action_name == "click":
                result = await self._loop._tool_action_click(replay_args)
            elif action_name == "fill":
                result = await self._loop._tool_action_fill(replay_args)
            else:
                result = await self._loop._tool_action_assert(replay_args)

            if result.get("success") is not True or result.get("skipped"):
                return {
                    "type": "replay_one_result",
                    "ok": False,
                    "step_id": replay_step_id,
                    "failed_operation_id": child_operation_id,
                    "error": self.safe_replay_error_message(
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

    async def replay_all(self, stop_on_error: bool = True) -> dict:
        import json
        from browser import get_page
        selected_step_ids = self.get_replay_archive_step_ids()
        step_count = len(selected_step_ids)
        self._loop._replay_all_result_sent = False
        print(f"[REPLAY_ALL] started steps={step_count} stop_on_error={json.dumps(bool(stop_on_error))}")
        await self._loop._send("replay_started", scope="all", step_count=step_count)

        replayed_count = 0
        passed_count = 0
        failed_count = 0
        first_failed_step_id = ""
        first_failed_operation_id = ""
        first_error = ""
        stop_after_failure = bool(stop_on_error)

        if selected_step_ids:
            first_step_id = selected_step_ids[0]
            first_step_payload = self.get_replay_recorded_step_payload(first_step_id)
            if isinstance(first_step_payload, dict):
                start_before_url, _ = self.get_replay_recorded_start_state(first_step_payload)
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
                            "error": self.safe_replay_error_message(
                                f"Replay blocked because the replay start URL could not be restored: {type(exc).__name__}"
                            ),
                        }
                        print(
                            "[REPLAY_ALL] completed "
                            "total=0 passed=0 failed=1"
                        )
                        await self._loop._send("replay_all_result", **final_result)
                        self._loop._replay_all_result_sent = True
                        return final_result

        for step_id in selected_step_ids:
            try:
                step_result = await self.replay_one(step_id)
            except Exception as exc:  # noqa: BLE001
                step_result = {
                    "type": "replay_one_result",
                    "ok": False,
                    "step_id": step_id,
                    "error": self.safe_replay_error_message(f"Replay failed: {type(exc).__name__}"),
                }

            if not isinstance(step_result, dict):
                step_result = {
                    "type": "replay_one_result",
                    "ok": False,
                    "step_id": step_id,
                    "error": self.safe_replay_error_message("Replay failed"),
                }

            step_ok = step_result.get("ok") is True
            step_operation_count = 0
            try:
                step_operation_count = int(step_result.get("operation_count") or 0)
            except (TypeError, ValueError):
                step_operation_count = 0

            replay_event: dict = {
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
                error_text = self.safe_replay_error_message(step_result.get("error") or "Replay failed")
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
            await self._loop._send("replay_result", **replay_event)

            if not step_ok and stop_after_failure:
                break

        final_result: dict = {
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
        await self._loop._send("replay_all_result", **final_result)
        self._loop._replay_all_result_sent = True
        return final_result

    def append_recorded_step_payload(self, payload: dict[str, Any]) -> None:
        recorded_step_payloads = getattr(self._loop, "recorded_step_payloads", None)
        if not isinstance(recorded_step_payloads, list):
            recorded_step_payloads = []
            self._loop.recorded_step_payloads = recorded_step_payloads
        recorded_step_payloads.append(deepcopy(payload))

    def append_code_update_payload(self, payload: dict[str, Any]) -> None:
        code_update_payloads = getattr(self._loop, "code_update_payloads", None)
        if not isinstance(code_update_payloads, list):
            code_update_payloads = []
            self._loop.code_update_payloads = code_update_payloads
        code_update_payloads.append(deepcopy(payload))

    def get_replay_recorded_step_payload(self, step_id: str) -> dict[str, Any] | None:
        replay_step_id = str(step_id or "").strip()
        if not replay_step_id:
            return None

        recorded_step_payloads = getattr(self._loop, "recorded_step_payloads", None)
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
            self._loop,
            "replay_recorded_step_payloads_by_step_id",
            None,
        )
        if isinstance(replay_recorded_step_payloads_by_step_id, dict):
            archived_payload = replay_recorded_step_payloads_by_step_id.get(replay_step_id)
            if isinstance(archived_payload, dict):
                return deepcopy(archived_payload)

        return None

    def get_replay_action_history(self, step_id: str) -> list[dict[str, Any]]:
        replay_step_id = str(step_id or "").strip()
        if not replay_step_id:
            return []

        history_by_step_id = getattr(self._loop, "successful_actions_by_step_id", None)
        if isinstance(history_by_step_id, dict):
            action_history = history_by_step_id.get(replay_step_id)
            if isinstance(action_history, list):
                return deepcopy(action_history)

        replay_action_history_by_step_id = getattr(self._loop, "replay_action_history_by_step_id", None)
        if isinstance(replay_action_history_by_step_id, dict):
            archived_history = replay_action_history_by_step_id.get(replay_step_id)
            if isinstance(archived_history, list):
                return deepcopy(archived_history)

        return []

    def safe_replay_error_message(self, message: Any) -> str:
        text = self._loop._normalize_space(str(message or "")).strip()
        if not text:
            return "Replay failed"
        if len(text) > 200:
            return f"{text[:197]}..."
        return text

    def get_replay_recorded_start_state(self, recorded_step_payload: dict[str, Any]) -> tuple[str, str]:
        observed_outcome = recorded_step_payload.get("observed_outcome")
        if not isinstance(observed_outcome, dict):
            return "", ""

        before_url = str(observed_outcome.get("before_url") or "").strip()
        before_title = str(observed_outcome.get("before_title") or "").strip()
        return before_url, before_title

    def get_replay_precondition_target_locator(
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

    async def validate_replay_target_locator(self, locator: str) -> dict[str, Any]:
        from browser import get_page
        locator_text = str(locator or "").strip()
        if not locator_text:
            return {"valid": False, "count": 0}

        try:
            page = get_page()
        except Exception:  # noqa: BLE001
            return {"valid": False, "count": 0}

        try:
            locator_count = await self._loop._resolve_locator(page, locator_text).count()
        except Exception:  # noqa: BLE001
            locator_count = 0

        return {"valid": locator_count > 0, "count": locator_count}

    def log_replay_precondition_failure(
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

    def build_replay_precondition_failure_result(
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
        safe_message = self.safe_replay_error_message(message)
        self.log_replay_precondition_failure(step_id, log_reason, before_url, current_url, locator)
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

    async def check_replay_precondition(
        self,
        step_id: str,
        recorded_step_payload: dict[str, Any],
        action_history: list[dict[str, Any]],
    ) -> dict[str, Any] | None:
        before_url, before_title = self.get_replay_recorded_start_state(recorded_step_payload)
        if not before_url:
            print(f"[REPLAY_PRECONDITION] missing before_url step_id={step_id}")
            return None

        current_state = await self._loop._capture_browser_state()
        current_url = str((current_state or {}).get("url") or "").strip()
        current_title = str((current_state or {}).get("title") or "").strip()
        if current_state is None:
            return self.build_replay_precondition_failure_result(
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
            return self.build_replay_precondition_failure_result(
                step_id,
                before_url,
                before_title,
                current_url,
                current_title,
                "Wrong start page",
                failure_type="wrong_start_page",
                log_reason="url_mismatch",
            )

        target_locator = self.get_replay_precondition_target_locator(recorded_step_payload, action_history)
        if not target_locator:
            return self.build_replay_precondition_failure_result(
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

        locator_validation = await self.validate_replay_target_locator(target_locator)
        if locator_validation.get("valid") is not True:
            return self.build_replay_precondition_failure_result(
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

    def get_replay_archive_step_ids(self) -> list[str]:
        step_ids: list[str] = []
        seen_step_ids: set[str] = set()

        recorded_step_payloads = getattr(self._loop, "recorded_step_payloads", None)
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
            self._loop,
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
