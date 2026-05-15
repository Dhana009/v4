from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING, Any

from starlette.websockets import WebSocketDisconnect
from runtime.event_contracts import build_run_completed_payload

if TYPE_CHECKING:
    from agent import AgentLoop


class EventEmitter:
    def __init__(self, ws: Any, loop: "AgentLoop") -> None:
        self._ws = ws
        self._loop = loop

    async def send(self, msg_type: str, **kwargs: Any) -> None:
        if getattr(self._loop, "_ws_disconnected", False):
            if msg_type.startswith("replay") and not getattr(self._loop, "_ws_disconnect_logged", False):
                self._loop._ws_disconnect_logged = True
                print("[WS] disconnected during replay_all; stopping result send")
            return

        payload = {"type": msg_type}
        payload.update(kwargs)
        try:
            await self._ws.send_json(payload)
        except WebSocketDisconnect:
            self._loop._ws_disconnected = True
            if msg_type.startswith("replay"):
                self._loop._ws_disconnect_logged = True
                print("[WS] disconnected during replay_all; stopping result send")
        except RuntimeError as exc:
            error_text = str(exc)
            if "close message has been sent" not in error_text and 'Cannot call "send"' not in error_text:
                raise
            self._loop._ws_disconnected = True
            if msg_type.startswith("replay"):
                self._loop._ws_disconnect_logged = True
                print("[WS] disconnected during replay_all; stopping result send")
        except Exception as exc:
            if exc.__class__.__name__ != "ClientDisconnected":
                raise
            self._loop._ws_disconnected = True
            if msg_type.startswith("replay"):
                self._loop._ws_disconnect_logged = True
                print("[WS] disconnected during replay_all; stopping result send")

    def emit_now(self, msg_type: str, **kwargs: Any) -> None:
        coroutine = self.send(msg_type, **kwargs)
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

    def emit_recovery_needed_event(
    self,
    step: dict[str, Any] | str | None,
    error_summary: str,
    ) -> None:
        context = self._loop._get_step_context(step) if not isinstance(step, dict) else step
        step_id = str((context or {}).get("step_id") or getattr(self._loop, "active_failed_step_id", "") or "").strip()
        if not step_id:
            step_id = "unknown"

        operation_id = str(
            (context or {}).get("operation_id")
            or (context or {}).get("current_operation_id")
            or (getattr(self._loop, "last_successful_action", None) or {}).get("operation_id")
            or ""
        ).strip() or None
        current_url = self._loop._current_browser_url() or "unknown"
        tried = [
            {
                "step_id": step_id,
                "status": "failed",
                "error_summary": error_summary,
                "current_url": current_url,
            }
        ]
        recovery_payload = build_recovery_needed_payload(
            run_id=self._loop._current_run_session_id(),
            step_id=step_id,
            error_summary=error_summary,
            current_url=current_url,
            tried=tried,
            options=["retry", "skip", "stop"],
            operation_id=operation_id,
        )
        self._loop._emit_backend_event_now(
            recovery_payload["type"],
            **{
                key: value
                for key, value in recovery_payload.items()
                if key != "type"
            },
        )

    async def emit_run_completed_event(
    self,
    source_payload: dict[str, Any],
    recorded_payload: dict[str, Any],
    ) -> None:
        if not self._loop._run_completion_requested or getattr(self._loop, "_run_completed_emitted", False):
            return

        run_id = str(
            source_payload.get("run_id")
            or recorded_payload.get("run_id")
            or self._loop._current_run_session_id()
            or ""
        ).strip()
        if not run_id:
            return

        recorded_count = sum(
            1 for step in self._loop._recording_steps if str(step.get("status") or "").strip() == "recorded"
        )
        skipped_count = sum(
            1 for step in self._loop._recording_steps if str(step.get("status") or "").strip() == "skipped"
        )
        summary = str(
            getattr(self._loop, "last_plan_summary", None)
            or getattr(getattr(self._loop, "last_plan_ready_payload", None), "get", lambda *_: "")("summary")
            or "Run completed"
        ).strip() or "Run completed"
        run_completed_payload = build_run_completed_payload(
            run_id=run_id,
            summary=summary,
            recorded_count=recorded_count,
            skipped_count=skipped_count,
        )
        self._loop._run_completed_emitted = True
        await self._loop._send(
            run_completed_payload["type"],
            **{
                key: value
                for key, value in run_completed_payload.items()
                if key != "type"
            },
        )
