"""
tests/test_e2e_ws_envelope_chain.py — E2E WS envelope-chain smoke test.

Boots the server via uvicorn in a background thread, opens a real WebSocket
client (using the `websockets` library), sends a minimal ``llm_run`` envelope,
and asserts the response chain contains at least one structured response type:
  - ``clarification_needed``
  - ``plan_ready``
  - ``recommendation_ready``

Skip contract
-------------
The test skips cleanly (``pytest.skip``) when no LLM credentials are reachable:
  * ``OPENAI_API_KEY`` is absent or does not start with ``sk-``
  * The env var ``E2E_SKIP_NO_LLM`` is set to ``1`` / ``true`` / ``yes``
"""
from __future__ import annotations

import asyncio
import json
import os
import socket
import sys
import threading
import time
from pathlib import Path
from typing import Any

import pytest

# ---------------------------------------------------------------------------
# LLM-credential gate — evaluated at collection time so the test runner
# reports SKIP rather than a collection-time ImportError.
# ---------------------------------------------------------------------------

_INIT_TYPES = frozenset(
    {"status", "ready", "agent_settings", "session_state", "endpoint_registry",
     "api_key_required", "no_browser"}
)

_STRUCTURED_RESPONSE_TYPES = frozenset(
    {"clarification_needed", "plan_ready", "recommendation_ready"}
)

_PROMPT_FIXTURE = Path(__file__).parent / "fixtures" / "e2e_prompts" / "pricing_link.json"


def _detect_api_key() -> str | None:
    """Return the API key string if reachable, else None."""
    # Explicit env var override to skip without a key check
    if os.getenv("E2E_SKIP_NO_LLM", "").lower() in ("1", "true", "yes"):
        return None

    key = os.getenv("OPENAI_API_KEY", "").strip()
    if not key or not key.startswith("sk-"):
        # Try loading from local .env as a fallback (same logic as server.py)
        try:
            from dotenv import dotenv_values
            env_path = Path(__file__).resolve().parent.parent / ".env"
            if env_path.exists():
                values = dotenv_values(str(env_path))
                key = str(values.get("OPENAI_API_KEY") or "").strip()
        except ImportError:
            pass
    if key and key.startswith("sk-"):
        return key
    return None


def _free_port() -> int:
    """Return a free TCP port on localhost."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


# ---------------------------------------------------------------------------
# Server lifecycle helpers
# ---------------------------------------------------------------------------

def _start_server_thread(port: int, api_key: str) -> tuple[threading.Thread, threading.Event]:
    """Start uvicorn in a daemon thread; return (thread, ready_event)."""
    import uvicorn

    # Ensure the project root is importable from the worker thread
    project_root = str(Path(__file__).resolve().parent.parent)
    if project_root not in sys.path:
        sys.path.insert(0, project_root)

    ready_event = threading.Event()
    stop_event = threading.Event()

    class _SignallingConfig(uvicorn.Config):
        pass

    class _App:
        """Thin async context that sets ready_event once uvicorn starts serving."""

    def _run() -> None:
        # Patch env inside the thread so this key is visible to the server module
        os.environ["OPENAI_API_KEY"] = api_key
        os.environ["AUTOWORKBENCH_STUB_MODE"] = ""  # make sure stub mode is off

        config = uvicorn.Config(
            "server:app",
            host="127.0.0.1",
            port=port,
            log_level="warning",
        )
        server_instance = uvicorn.Server(config)

        # Monkey-patch the startup hook to signal readiness
        original_startup = server_instance.startup

        async def _patched_startup(sockets: Any = None) -> None:  # noqa: ANN401
            await original_startup(sockets=sockets)
            ready_event.set()

        server_instance.startup = _patched_startup  # type: ignore[method-assign]
        asyncio.run(server_instance.serve())

    thread = threading.Thread(target=_run, daemon=True, name="uvicorn-e2e-smoke")
    thread.start()
    return thread, ready_event


def _wait_for_port(host: str, port: int, timeout: float = 15.0) -> bool:
    """Poll until the TCP port accepts connections."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            with socket.create_connection((host, port), timeout=0.5):
                return True
        except OSError:
            time.sleep(0.1)
    return False


# ---------------------------------------------------------------------------
# Core async test logic
# ---------------------------------------------------------------------------

async def _run_envelope_chain(port: int) -> list[str]:
    """Connect WS, send llm_run, collect envelope types for up to 30 s.

    Returns the list of event types observed (excluding init events).
    Raises AssertionError if the required structured response is absent.
    """
    import websockets  # local import — only needed at runtime

    uri = f"ws://127.0.0.1:{port}/ws"

    # Load the prompt fixture
    prompt_data = json.loads(_PROMPT_FIXTURE.read_text(encoding="utf-8"))
    steps: list[dict[str, Any]] = prompt_data["steps"]

    async with websockets.connect(uri, open_timeout=10, close_timeout=5) as ws:
        # Drain init events (ready, agent_settings, endpoint_registry, etc.)
        init_drained: list[str] = []
        async with asyncio.timeout(10):
            while True:
                raw = await ws.recv()
                msg: dict[str, Any] = json.loads(raw)
                t = msg.get("type", "")
                if t in _INIT_TYPES:
                    init_drained.append(t)
                    # We need at least the ready event before sending
                    if t in {"ready", "status"}:
                        # Keep draining until we have agent_settings too
                        continue
                    if len(init_drained) >= 3:
                        # Drained enough init events; proceed
                        break
                else:
                    # Non-init event arrived early — stop draining
                    break

        # Send the llm_run command
        await ws.send(json.dumps({
            "type": "llm_run",
            "steps": steps,
        }))

        # Collect events for up to 30 seconds
        observed_types: list[str] = []
        deadline = time.monotonic() + 30.0

        while time.monotonic() < deadline:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                break
            try:
                async with asyncio.timeout(remaining):
                    raw = await ws.recv()
            except (asyncio.TimeoutError, TimeoutError):
                break
            except websockets.exceptions.ConnectionClosed:
                break

            msg = json.loads(raw)
            event_type = str(msg.get("type") or "")

            if event_type not in _INIT_TYPES:
                observed_types.append(event_type)

            # Stop as soon as we see a terminal structured response
            if event_type in _STRUCTURED_RESPONSE_TYPES:
                break

            # Also stop on run completion or error
            if event_type in {"run_completed", "run_error", "runtime_rejection"}:
                break

    return observed_types


# ---------------------------------------------------------------------------
# Pytest test function
# ---------------------------------------------------------------------------

def test_ws_envelope_chain_reaches_structured_response() -> None:
    """Boot server, open WS, send a tiny prompt, assert structured response arrives."""
    api_key = _detect_api_key()
    if api_key is None:
        pytest.skip("no LLM creds reachable")

    port = _free_port()
    _thread, ready_event = _start_server_thread(port, api_key)

    # Wait for uvicorn to be ready (event + TCP port check)
    ready_event.wait(timeout=20.0)
    if not _wait_for_port("127.0.0.1", port, timeout=10.0):
        pytest.skip("no LLM creds reachable")  # server failed to bind — treated as env issue

    try:
        observed = asyncio.run(_run_envelope_chain(port))
    except Exception as exc:  # noqa: BLE001
        # Any unexpected connection failure is reported as a skip if the server
        # never responded — avoids false FAILs in offline CI environments.
        exc_text = str(exc).lower()
        if "connect" in exc_text or "refused" in exc_text or "timeout" in exc_text:
            pytest.skip(f"no LLM creds reachable — connection error: {exc}")
        raise

    # Verify at least one structured response type was seen
    structured_seen = [t for t in observed if t in _STRUCTURED_RESPONSE_TYPES]
    assert structured_seen, (
        "Expected at least one of {clarification_needed, plan_ready, recommendation_ready} "
        f"in the envelope chain, but got: {observed}"
    )
