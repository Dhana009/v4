from __future__ import annotations

import re
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[1]
FRONTEND_MAIN = REPO_ROOT / "frontend/src/main.jsx"


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
    assert "type: \"confirmed\"" in main
    assert "type: \"correction\"" in main
    assert "type: \"option_selected\"" in main
    assert "type: \"replay_all\"" in main
    assert "type: \"replay_one\"" in main
    assert "type: \"run_steps\"" in main
    assert "type: \"save_snapshot\"" in main


def test_frontend_event_store_should_be_split_into_a_dedicated_shell() -> None:
    main = _read(FRONTEND_MAIN)

    missing = []
    if not any(marker in main for marker in ("useFrontendEventStore", "createFrontendEventStore", "typed event store")):
        missing.append("dedicated frontend event-store shell")
    if "normalizeBackendMessage" not in main or "handleBackendMessage" not in main:
        missing.append("backend event ingestion boundary")

    if missing:
        pytest.xfail("FE-002 shell contract not implemented yet: " + ", ".join(missing))

    assert any(marker in main for marker in ("useFrontendEventStore", "createFrontendEventStore"))
    assert "normalizeBackendMessage" in main
    assert "handleBackendMessage" in main


def test_frontend_command_dispatcher_should_emit_typed_command_envelopes() -> None:
    main = _read(FRONTEND_MAIN)
    payload_blocks = _send_payload_blocks(main)

    missing = []
    if not payload_blocks:
        missing.append("sendPayload envelope builders")
    if not any("command_id" in block for block in payload_blocks):
        missing.append("command_id")
    if not any("schema_version" in block for block in payload_blocks):
        missing.append("schema_version")
    if not any(any(field in block for field in ("run_id", "plan_id", "step_id", "target_step_id")) for block in payload_blocks):
        missing.append("run/plan correlation fields")

    if missing:
        pytest.xfail("FE-003 command envelope contract not implemented yet: " + ", ".join(missing))

    assert payload_blocks
    assert any("command_id" in block for block in payload_blocks)
    assert any("schema_version" in block for block in payload_blocks)
    assert any(any(field in block for field in ("run_id", "plan_id", "step_id", "target_step_id")) for block in payload_blocks)
