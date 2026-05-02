from dotenv import load_dotenv
load_dotenv(override=True)

import asyncio
import os
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, WebSocket, WebSocketDisconnect

from agent import AgentLoop
from browser import arm_picker, launch_browser

PORT = int(os.getenv("PORT", "8765"))


@asynccontextmanager
async def lifespan(app: FastAPI):  # noqa: ARG001
    key = os.getenv("OPENAI_API_KEY", "")
    if not key or not key.startswith("sk-"):
        raise RuntimeError("OPENAI_API_KEY missing or invalid in .env")
    print(f"[startup] API key loaded: {key[:8]}...")
    print(f"[startup] PORT={PORT}")
    await launch_browser()
    yield


app = FastAPI(lifespan=lifespan)


@app.websocket("/ws")
async def ws_endpoint(ws: WebSocket) -> None:
    await ws.accept()

    await ws.send_json({"type": "status", "message": "Browser launched. Ready."})

    control_queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue()
    agent = AgentLoop(ws, control_queue)
    run_task: asyncio.Task[Any] | None = None

    async def picker_send(msg: dict) -> None:
        await ws.send_json(msg)

    try:
        while True:
            msg = await ws.receive_json()
            msg_type = msg.get("type")

            if msg_type == "run_steps":
                steps = msg.get("steps") or []
                if run_task and not run_task.done():
                    await ws.send_json({"type": "status", "message": "Run already in progress."})
                    continue
                run_task = asyncio.create_task(agent.run(steps))
                continue

            if msg_type == "save_snapshot":
                try:
                    snapshot = agent._build_spec_snapshot()
                    await ws.send_json(
                        {
                            "type": "save_snapshot_result",
                            "ok": True,
                            "snapshot": snapshot,
                        }
                    )
                except Exception as exc:  # noqa: BLE001
                    error_message = f"Snapshot save failed: {type(exc).__name__}"
                    await ws.send_json(
                        {
                            "type": "save_snapshot_result",
                            "ok": False,
                            "error": error_message,
                        }
                    )
                continue

            if msg_type == "replay_one":
                step_id = str(msg.get("step_id") or "").strip()
                try:
                    result = await agent.replay_one(step_id)
                except Exception as exc:  # noqa: BLE001
                    result = {
                        "type": "replay_one_result",
                        "ok": False,
                        "step_id": step_id,
                        "error": f"Replay failed: {type(exc).__name__}",
                    }
                await ws.send_json(result)
                continue

            if msg_type == "replay_all":
                stop_on_error_value = msg.get("stop_on_error", True)
                if isinstance(stop_on_error_value, bool):
                    stop_on_error = stop_on_error_value
                else:
                    stop_on_error_text = str(stop_on_error_value or "").strip().lower()
                    stop_on_error = stop_on_error_text not in {"false", "0", "no", "off", ""}
                try:
                    result = await agent.replay_all(stop_on_error=stop_on_error)
                except Exception as exc:  # noqa: BLE001
                    await ws.send_json(
                        {
                            "type": "replay_all_result",
                            "ok": False,
                            "stop_on_error": stop_on_error,
                            "step_ids": [],
                            "replayed_count": 0,
                            "passed_count": 0,
                            "failed_count": 0,
                            "error": f"Replay failed: {type(exc).__name__}",
                        }
                    )
                else:
                    if not getattr(agent, "_replay_all_result_sent", False):
                        if not isinstance(result, dict):
                            result = {
                                "type": "replay_all_result",
                                "ok": False,
                                "stop_on_error": stop_on_error,
                                "step_ids": [],
                                "replayed_count": 0,
                                "passed_count": 0,
                                "failed_count": 0,
                                "error": "Replay failed",
                            }
                        await ws.send_json(result)
                continue

            if msg_type in {"confirmed", "correction", "option_selected"}:
                await control_queue.put(msg)
                continue

            if msg_type == "arm_picker":
                step_id = str(msg.get("step_id") or "").strip()
                if not step_id:
                    await ws.send_json({"type": "error", "message": "arm_picker requires step_id"})
                    continue
                await arm_picker(step_id, picker_send)
                await ws.send_json({"type": "status", "message": f"Picker armed for step {step_id}"})
                continue

            if msg_type == "reset":
                agent.llm.reset()
                await ws.send_json({"type": "status", "message": "Session reset."})
                continue

            await ws.send_json({"type": "error", "message": f"Unsupported message type: {msg_type}"})
    except WebSocketDisconnect:
        if run_task and not run_task.done():
            run_task.cancel()


if __name__ == "__main__":
    import uvicorn

    print(f"[main] Starting server on 0.0.0.0:{int(os.getenv('PORT', 8765))}")
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", 8765)))
