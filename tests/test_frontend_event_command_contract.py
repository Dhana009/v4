from __future__ import annotations

import re
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[1]
FRONTEND_MAIN = REPO_ROOT / "frontend/src/main.jsx"
FRONTEND_PANEL = REPO_ROOT / "frontend/aw-ide-panel.jsx"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _send_payload_blocks(source: str) -> list[str]:
    return re.findall(r"sendPayload\s*\(\s*\{(?P<body>.*?)\}\s*,", source, re.S)


def test_frontend_event_store_shell_is_source_anchored() -> None:
    main = _read(FRONTEND_MAIN)

    assert "useAutoWorkbenchTransport" in main
    assert "normalizeBackendMessage" in main
    assert "handleBackendMessage" in main
    assert "setRunState" in main
    assert "setPlan" in main
    assert "setRecordedSteps" in main
    assert "setPendingSteps" in main
    assert "case \"plan_ready\"" in main
    assert "case \"step_recorded\"" in main
    assert "case \"code_update\"" in main
    assert "case \"replay_all_result\"" in main


def test_frontend_command_surface_routes_user_actions_through_transport() -> None:
    main = _read(FRONTEND_MAIN)

    assert "sendPayload" in main
    assert "handleConfirmPlan" in main
    assert "handleSendPlanCorrection" in main
    assert "handleSendClarificationAnswer" in main
    assert "handleSendRecoveryInstruction" in main
    assert "handleReplayRecordedStep" in main
    assert "handleReplayAllRecordedSteps" in main
    assert "handleRunPendingSteps" in main
    assert "handleSaveSnapshot" in main
    assert "handleAttachElement" in main
    assert "buildFrontendCommandEnvelope" in main
    assert "\"confirmed\"" in main
    assert "\"correction\"" in main
    assert "\"option_selected\"" in main
    assert "type: \"replay_all\"" in main
    assert "type: \"replay_one\"" in main
    assert "type: \"run_steps\"" in main
    assert "type: \"save_snapshot\"" in main


def test_frontend_event_store_should_be_split_into_a_dedicated_shell() -> None:
    main = _read(FRONTEND_MAIN)

    missing = []
    if not any(marker in main for marker in ("useFrontendEventStore", "createFrontendEventStore")):
        missing.append("dedicated frontend event-store shell")
    if "normalizeBackendMessage" not in main or "handleBackendMessage" not in main:
        missing.append("backend event ingestion boundary")
    if "case \"runtime_rejected\"" not in main:
        missing.append("typed runtime rejection handling")

    if missing:
        pytest.xfail("FE-002 shell contract not implemented yet: " + ", ".join(missing))

    assert any(marker in main for marker in ("useFrontendEventStore", "createFrontendEventStore"))
    assert "normalizeBackendMessage" in main
    assert "handleBackendMessage" in main
    assert "case \"runtime_rejected\"" in main


def test_frontend_command_dispatcher_should_emit_typed_command_envelopes() -> None:
    main = _read(FRONTEND_MAIN)

    missing = []
    if "buildFrontendCommandEnvelope" not in main:
        missing.append("typed command-envelope helper")
    if "command_id" not in main:
        missing.append("command_id")
    if "schema_version" not in main:
        missing.append("schema_version")
    if not any(field in main for field in ("plan_id", "plan_version", "step_id", "operation_id")):
        missing.append("typed command context fields")
    if "case \"runtime_rejected\"" not in main:
        missing.append("runtime rejection rendering")

    if missing:
        pytest.xfail("FE-003 command envelope contract not implemented yet: " + ", ".join(missing))

    assert "buildFrontendCommandEnvelope" in main
    assert "command_id" in main
    assert "schema_version" in main
    assert any(field in main for field in ("plan_id", "plan_version", "step_id", "operation_id"))
    assert "case \"runtime_rejected\"" in main


def test_frontend_rejection_rendering_should_preserve_backend_reason_and_state() -> None:
    main = _read(FRONTEND_MAIN)
    panel = _read(FRONTEND_PANEL)

    missing = []
    if "case \"runtime_rejected\"" not in main:
        missing.append("typed runtime rejection handler")
    if not any(marker in main for marker in ("rejection_code", "current_state")):
        missing.append("backend rejection details")
    if "lastError" not in panel:
        missing.append("panel rejection surface")

    if missing:
        pytest.xfail("FE-002/FE-003 rejection rendering contract not implemented yet: " + ", ".join(missing))

    assert "case \"runtime_rejected\"" in main
    assert "rejection_code" in main
    assert "current_state" in main
    assert "lastError" in panel
