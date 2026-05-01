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

            if msg_type in {"confirmed", "correction"}:
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
