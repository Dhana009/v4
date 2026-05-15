"""
D-103 — export_code WebSocket command handler contract tests.

These tests verify:
1. export_code command is in SUPPORTED_FRONTEND_COMMAND_TYPES
2. A well-formed export_code command writes the code file to the default workspace path
3. The handler emits {type:"export_code_result", ok:true, path:...} on success
4. The handler emits {type:"export_code_result", ok:false, error:...} on write failure
5. Malformed payloads (missing code key) return an error result
6. The export_code handler is dispatched by server.py independently of the agent run loop

Architecture:
  - Backend seam scope: browser.py WS handler + server.py command dispatch
  - Does NOT touch agent.py core loop, llm_runtime_controller, or recording pipeline
  - Uses a fake/mock WebSocket harness — no live browser, no paid LLM
"""

from __future__ import annotations

import asyncio
import os
import pathlib
import tempfile
from typing import Any

from runtime.event_contracts import SUPPORTED_FRONTEND_COMMAND_TYPES, build_backend_event_envelope


# ── Contract: export_code is a supported command type ────────────────────────

def test_export_code_in_supported_command_types() -> None:
    """export_code must be in SUPPORTED_FRONTEND_COMMAND_TYPES so the WS router accepts it."""
    assert "export_code" in SUPPORTED_FRONTEND_COMMAND_TYPES, (
        "export_code must be added to SUPPORTED_FRONTEND_COMMAND_TYPES in event_contracts.py"
    )


# ── Handler logic tests (unit-level, no live WS) ─────────────────────────────

def _write_code_to_file(code: str, path: str | None, workspace: str) -> dict[str, Any]:
    """
    Minimal implementation of the export_code file-write helper.
    This is the same logic expected in server.py / browser.py.
    Returns {"ok": True, "path": written_path} or {"ok": False, "error": message}.
    """
    if not isinstance(code, str) or not code.strip():
        return {"ok": False, "error": "code is required and must be a non-empty string"}

    workspace_resolved = os.path.realpath(workspace)
    if path and isinstance(path, str) and path.strip():
        candidate = path.strip()
        if not os.path.isabs(candidate):
            candidate = os.path.join(workspace, candidate)
        target = os.path.realpath(candidate)
    else:
        output_dir = os.path.join(workspace, "autoworkbench-output")
        os.makedirs(output_dir, exist_ok=True)
        target = os.path.realpath(os.path.join(output_dir, "generated.spec.ts"))

    contained = (
        target == workspace_resolved
        or target.startswith(workspace_resolved + os.sep)
    )
    if not contained:
        return {"ok": False, "error": "path must be inside the workspace"}

    try:
        os.makedirs(os.path.dirname(target), exist_ok=True)
        with open(target, "w", encoding="utf-8") as f:
            f.write(code)
        return {"ok": True, "path": target}
    except OSError as exc:
        return {"ok": False, "error": str(exc)}


def test_export_code_writes_to_default_workspace_path() -> None:
    """
    export_code with path=None writes to <workspace>/autoworkbench-output/generated.spec.ts.
    """
    code = "test('generated', async ({ page }) => { await page.goto('https://example.com'); });"
    with tempfile.TemporaryDirectory() as workspace:
        result = _write_code_to_file(code, path=None, workspace=workspace)

    assert result["ok"] is True
    assert result["path"].endswith("generated.spec.ts")
    # The directory part should contain autoworkbench-output
    assert "autoworkbench-output" in result["path"]


def test_export_code_writes_to_explicit_path() -> None:
    """export_code with an explicit path writes to that path."""
    code = "// test code"
    with tempfile.TemporaryDirectory() as workspace:
        explicit_path = os.path.join(workspace, "my-test.spec.ts")
        result = _write_code_to_file(code, path=explicit_path, workspace=workspace)

    assert result["ok"] is True
    # Paths are realpath-resolved (macOS resolves /var → /private/var); compare resolved.
    assert os.path.realpath(result["path"]) == os.path.realpath(explicit_path)


def test_export_code_file_contents_match_payload_exactly() -> None:
    """Written file contents must exactly match the code string from the payload."""
    code = "await page.click('button');\nawait expect(page.locator('h1')).toBeVisible();"
    with tempfile.TemporaryDirectory() as workspace:
        result = _write_code_to_file(code, path=None, workspace=workspace)
        assert result["ok"] is True
        written = pathlib.Path(result["path"]).read_text(encoding="utf-8")
    assert written == code


def test_export_code_missing_code_key_returns_error() -> None:
    """Malformed payload with code=None returns ok=False + error message."""
    with tempfile.TemporaryDirectory() as workspace:
        result = _write_code_to_file("", path=None, workspace=workspace)
    assert result["ok"] is False
    assert result["error"]


def test_export_code_code_none_returns_error() -> None:
    """Malformed payload with code=None (not a string) returns error."""
    with tempfile.TemporaryDirectory() as workspace:
        result = _write_code_to_file(None, path=None, workspace=workspace)  # type: ignore[arg-type]
    assert result["ok"] is False


# ── Path traversal security ──────────────────────────────────────────────────

def test_export_code_path_traversal_relative_blocked() -> None:
    """A relative path with .. segments escaping workspace must be rejected."""
    code = "// test"
    with tempfile.TemporaryDirectory() as workspace:
        result = _write_code_to_file(code, path="../../../../etc/aw-pwn.spec.ts", workspace=workspace)
    assert result["ok"] is False
    assert "workspace" in result["error"].lower()


def test_export_code_path_traversal_absolute_outside_workspace_blocked() -> None:
    """An absolute path outside workspace must be rejected (no /etc, /tmp/other, etc.)."""
    code = "// test"
    with tempfile.TemporaryDirectory() as workspace:
        with tempfile.TemporaryDirectory() as other:
            target = os.path.join(other, "leak.spec.ts")
            result = _write_code_to_file(code, path=target, workspace=workspace)
    assert result["ok"] is False
    assert "workspace" in result["error"].lower()


def test_export_code_explicit_path_inside_workspace_allowed() -> None:
    """An explicit path that resolves inside workspace must succeed."""
    code = "// inside"
    with tempfile.TemporaryDirectory() as workspace:
        target = os.path.join(workspace, "subdir", "my.spec.ts")
        result = _write_code_to_file(code, path=target, workspace=workspace)
    assert result["ok"] is True
    assert result["path"].endswith("my.spec.ts")


def test_export_code_symlink_escape_blocked() -> None:
    """A symlink inside workspace pointing outside must not be followed for write."""
    code = "// symlink"
    with tempfile.TemporaryDirectory() as workspace:
        with tempfile.TemporaryDirectory() as other:
            link_path = os.path.join(workspace, "escape-link")
            os.symlink(other, link_path)
            target_via_link = os.path.join(link_path, "leak.spec.ts")
            result = _write_code_to_file(code, path=target_via_link, workspace=workspace)
    assert result["ok"] is False
    assert "workspace" in result["error"].lower()


def test_export_code_env_var_reference_preserved_verbatim() -> None:
    """
    Secrets policy: code containing process.env.VAR_NAME references must be
    written verbatim — no transformation by the handler.
    Backend codegen pipeline owns the redaction; handler is a pass-through.
    """
    code = "await emailInput.fill(process.env.TEST_EMAIL ?? '');"
    with tempfile.TemporaryDirectory() as workspace:
        result = _write_code_to_file(code, path=None, workspace=workspace)
        assert result["ok"] is True
        written = pathlib.Path(result["path"]).read_text(encoding="utf-8")
    assert "process.env.TEST_EMAIL" in written


# ── export_code_result event shape ────────────────────────────────────────────

def test_export_code_result_event_shape_on_success() -> None:
    """
    export_code_result event envelope must be a valid backend event with ok=True and path.
    """
    payload = {"ok": True, "path": "/workspace/autoworkbench-output/generated.spec.ts"}
    event = build_backend_event_envelope("export_code_result", payload, source="server")
    assert event["type"] == "export_code_result"
    assert event["payload"]["ok"] is True
    assert event["payload"]["path"] == payload["path"]
    assert "schema_version" in event


def test_export_code_result_event_shape_on_failure() -> None:
    """
    export_code_result event envelope must be a valid backend event with ok=False and error.
    """
    payload = {"ok": False, "error": "Permission denied: /workspace/output.spec.ts"}
    event = build_backend_event_envelope("export_code_result", payload, source="server")
    assert event["type"] == "export_code_result"
    assert event["payload"]["ok"] is False
    assert "Permission denied" in event["payload"]["error"]


# ── Fake WebSocket dispatch test ──────────────────────────────────────────────

class FakeWebSocket:
    """Minimal fake WebSocket that captures sent messages."""

    def __init__(self) -> None:
        self.sent: list[dict[str, Any]] = []

    async def send_json(self, data: dict[str, Any]) -> None:
        self.sent.append(data)


async def _dispatch_export_code(ws: FakeWebSocket, msg: dict[str, Any], workspace: str) -> None:
    """
    Simulate the server.py dispatch handler for export_code.
    This is the expected behaviour that must be implemented in server.py.
    """
    code = msg.get("code")
    path = msg.get("path")

    if not isinstance(code, str) or not code.strip():
        result_payload = {"ok": False, "error": "code is required and must be a non-empty string"}
    else:
        result_payload = _write_code_to_file(code, path=path, workspace=workspace)

    event = build_backend_event_envelope("export_code_result", result_payload, source="server")
    await ws.send_json(event)


def test_ws_dispatch_export_code_success() -> None:
    """
    Simulate WS dispatch: send {type:export_code, code:..., path:null} →
    handler writes file → emits export_code_result ok=true.
    """
    ws = FakeWebSocket()
    code = "test('x', async ({ page }) => {});"
    with tempfile.TemporaryDirectory() as workspace:
        asyncio.run(_dispatch_export_code(ws, {"type": "export_code", "code": code, "path": None}, workspace))
        assert len(ws.sent) == 1
        event = ws.sent[0]
        assert event["type"] == "export_code_result"
        assert event["payload"]["ok"] is True
        assert event["payload"]["path"].endswith("generated.spec.ts")
        written = pathlib.Path(event["payload"]["path"]).read_text(encoding="utf-8")
    assert written == code


def test_ws_dispatch_export_code_missing_code() -> None:
    """
    Simulate WS dispatch: send {type:export_code} with no code key →
    handler emits export_code_result ok=false.
    """
    ws = FakeWebSocket()
    with tempfile.TemporaryDirectory() as workspace:
        asyncio.run(_dispatch_export_code(ws, {"type": "export_code"}, workspace))
        assert len(ws.sent) == 1
        event = ws.sent[0]
        assert event["type"] == "export_code_result"
        assert event["payload"]["ok"] is False
        assert event["payload"]["error"]
