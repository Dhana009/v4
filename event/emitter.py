from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING, Any

from starlette.websockets import WebSocketDisconnect

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
