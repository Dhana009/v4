from __future__ import annotations
from typing import TYPE_CHECKING, Any
if TYPE_CHECKING:
    from agent import AgentLoop


class Recorder:
    def __init__(self, loop: "AgentLoop") -> None:
        self._loop = loop

    def has_successful_action_to_record(self) -> bool:
        return self._loop._has_successful_action_to_record()

    def should_block_additional_execution_action(self, tool_name: str) -> bool:
        return self._loop._should_block_additional_execution_action(tool_name)

    def should_block_recording_wait_tool(self, tool_name: str) -> bool:
        return self._loop._should_block_recording_wait_tool(tool_name)

    def get_successful_action_for_step(self, step: Any) -> Any:
        return self._loop._get_successful_action_for_step(step)

    def get_successful_action_history_for_step(self, step: Any) -> Any:
        return self._loop._get_successful_action_history_for_step(step)

    async def record_step_payload(self, step: Any) -> Any:
        return await self._loop._record_step_payload(step)

    async def auto_record_successful_step(self) -> Any:
        return await self._loop._auto_record_successful_step()

    def build_step_record_payload(self, step: Any, **kwargs: Any) -> dict:
        return self._loop._build_step_record_payload(step, **kwargs)

    def append_recorded_step_payload(self, payload: dict) -> None:
        return self._loop._append_recorded_step_payload(payload)

    def append_code_update_payload(self, payload: dict) -> None:
        return self._loop._append_code_update_payload(payload)

    def reset_lifecycle_state(self, steps: list[dict] | None = None) -> None:
        self.phase = "planning"
        self.plan_confirmed = False
        self._loop.current_steps = list(steps or [])
        self._loop.phase_tracker.current_phase = "idle"
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
        self._loop._loaded_skill_names = []
        self._loop._loaded_skill_entries = []
        self._loop._missing_skill_names = set()
        self._loop._last_skill_load_phase = None
        self._loop._recording_steps = []
        self._loop._recording_step_index = 0
        self._loop._recorded_step_ids = set()
        self._loop._last_action_context = None
        self._loop._awaiting_step_record = False
        self._loop._recording_wait_guard_armed = False
        self.run_stop_requested = False
        self._loop._run_completion_requested = False
        self._loop._pending_failure_followup = False
        self._loop._active_plan_state = None
        self._loop._active_plan_correction_state = None
        self._loop._plan_correction_pending = False
        self._loop._clear_confirmed_execution_contract_state()
        self.capability_gaps = []
        self.recorded_step_payloads = []
        self.code_update_payloads = []
        if steps is not None:
            self.replay_recorded_step_payloads_by_step_id = {}
            self.replay_action_history_by_step_id = {}
        self._loop._run_session_id = self._loop._new_run_session_id()
        self._loop._run_completed_emitted = False
        self._loop._clear_plan_review_context()
        telemetry_sink = getattr(self, "_plan_diff_editor_telemetry", None)
        if isinstance(telemetry_sink, list):
            telemetry_sink.clear()
        self._loop._llm_call_counter = 0

    async def capture_browser_state(self) -> dict[str, str] | None:
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

    def normalize_browser_state_snapshot(self, browser_state: Any) -> dict[str, str] | None:
        if not isinstance(browser_state, dict):
            return None
        return {
            "url": str(browser_state.get("url") or ""),
            "title": str(browser_state.get("title") or ""),
        }

    def build_observed_outcome(
    self,
    action_history: list[dict[str, Any]],
    expected_outcome: Any,
    ) -> dict[str, Any]:
        before_state = None
        after_state = None
        if action_history:
            first_action = action_history[0]
            if isinstance(first_action, dict):
                before_state = self._loop._normalize_browser_state_snapshot(first_action.get("browser_state_before"))
            last_action = action_history[-1]
            if isinstance(last_action, dict):
                after_state = self._loop._normalize_browser_state_snapshot(last_action.get("browser_state_after"))

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
            expected_type = self._loop._normalize_space(str(expected_outcome.get("type") or "")).strip().lower()

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

    def capture_action_context(
    self,
    tool_name: str,
    args: dict[str, Any],
    result: dict[str, Any],
    browser_state_before: dict[str, str] | None = None,
    browser_state_after: dict[str, str] | None = None,
    ) -> None:
        action = self._loop._action_name_for_tool(tool_name)
        if not action:
            return
        step_context = self._loop._resolve_step_context(tool_name, args, result)
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
            captured["step_number"] = self._loop._coerce_step_number((step_context or {}).get("step_number"))
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
        normalized_browser_state_before = self._loop._normalize_browser_state_snapshot(browser_state_before)
        if normalized_browser_state_before is not None:
            captured["browser_state_before"] = normalized_browser_state_before
        normalized_browser_state_after = self._loop._normalize_browser_state_snapshot(browser_state_after)
        if normalized_browser_state_after is not None:
            captured["browser_state_after"] = normalized_browser_state_after
        generated_line = self._loop._build_generated_line(action, str(action_context.get("locator") or ""), action_context)
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
        self._loop._last_action_context = action_context
        confirmed_contract = self._loop._confirmed_execution_contract_for_step(step_context or step_id)
        if isinstance(confirmed_contract, dict):
            if self._loop._confirmed_execution_step_ready_to_record(step_context or step_id):
                self._loop._awaiting_step_record = True
                self._loop.phase_tracker.set_phase("recording", reason="action_success", step_id=step_id)
            else:
                self._loop._awaiting_step_record = False
                self._loop.phase_tracker.set_phase("executing", reason="child_success", step_id=step_id)
        else:
            self._loop._awaiting_step_record = True
            self._loop.phase_tracker.set_phase("recording", reason="action_success", step_id=step_id)

    def action_name_for_tool(self, tool_name: str) -> str:
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

    def build_spec_snapshot(self) -> dict[str, Any]:
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

        session_id = self._loop._current_run_session_id()
        original_user_intent = str(getattr(self, "last_plan_original_user_intent", "") or "").strip() or None
        phase = self._loop._current_phase()
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

    def build_session_state_payload(self) -> dict[str, Any]:
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
