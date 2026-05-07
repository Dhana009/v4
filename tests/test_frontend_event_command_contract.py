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


def _snippet_between(source: str, start_marker: str, end_marker: str) -> str:
    start = source.find(start_marker)
    assert start != -1, f"missing start marker: {start_marker}"
    end = source.find(end_marker, start + len(start_marker))
    assert end != -1, f"missing end marker: {end_marker}"
    return source[start:end]


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


@pytest.mark.parametrize(
    ("handler_name", "start_marker", "end_marker", "forbidden_markers"),
    [
        (
            "confirm",
            "  const handleConfirmPlan = useCallback(() => {",
            "  }, [appendConversation, appendTimeline, sendPayload]);",
            ("setRunState(", "setInteractionMode(", "setPlan("),
        ),
        (
            "correction",
            "  const handleSendPlanCorrection = useCallback(() => {",
            "  }, [appendConversation, appendTimeline, plan, planCorrectionText, sendPayload]);",
            ("setRunState(", "setInteractionMode(", "setPlan("),
        ),
        (
            "clarification",
            '  const handleSendClarificationAnswer = useCallback(\n    (answerOverride = "") => {',
            '    [appendConversation, appendTimeline, clarificationAnswerText, sendPayload]\n  );',
            ("setRunState(", "setInteractionMode(", "setClarificationQuestion(", "setClarificationOptions("),
        ),
        (
            "recovery",
            "  const handleSendRecoveryInstruction = useCallback(() => {",
            "  }, [appendConversation, appendTimeline, recoveryText, sendPayload]);",
            ("setRunState(", "setInteractionMode("),
        ),
    ],
)
def test_frontend_command_handlers_do_not_locally_mutate_lifecycle_truth(
    handler_name: str,
    start_marker: str,
    end_marker: str,
    forbidden_markers: tuple[str, ...],
) -> None:
    main = _read(FRONTEND_MAIN)
    snippet = _snippet_between(main, start_marker, end_marker)

    assert "sendPayload(" in snippet, f"{handler_name} should still submit a typed command"
    for marker in forbidden_markers:
        assert marker not in snippet, f"{handler_name} should not optimistically mutate lifecycle truth"


def test_frontend_runtime_rejected_reports_without_flipping_lifecycle_truth() -> None:
    main = _read(FRONTEND_MAIN)
    snippet = _snippet_between(main, '        case "runtime_rejected": {', '        case "llm_result": {')

    assert "setLastError(rejectionReason);" in snippet
    assert "appendTimeline([rejectionCode, rejectionReason, currentStateSummary].filter(Boolean).join(\" · \"), \"err\");" in snippet
    assert "setRunState(" not in snippet
    assert "setInteractionMode(" not in snippet


def test_frontend_backend_events_remain_the_only_lifecycle_source() -> None:
    main = _read(FRONTEND_MAIN)
    snippet = _snippet_between(main, "  const handleBackendMessage = useCallback(\n    (message) => {", "  useEffect(() => {")

    assert 'case "status": {' in snippet
    assert 'case "llm_thinking":' in snippet
    assert 'case "plan_ready": {' in snippet
    assert 'case "clarification_needed": {' in snippet
    assert 'case "error":' in snippet
    assert 'case "step_recorded": {' in snippet
    assert "setRunState(" in snippet
    assert "setInteractionMode(" in snippet
    assert "setPlan(" in snippet
    assert "setRecordedSteps(" in snippet
