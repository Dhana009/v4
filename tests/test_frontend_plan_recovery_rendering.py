from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
FRONTEND_MAIN = REPO_ROOT / "frontend/src/main.jsx"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _snippet_between(source: str, start_marker: str, end_marker: str) -> str:
    start = source.find(start_marker)
    assert start != -1, f"missing start marker: {start_marker}"
    end = source.find(end_marker, start + len(start_marker))
    assert end != -1, f"missing end marker: {end_marker}"
    return source[start:end]


def test_plan_ready_backend_event_drives_plan_review_read_model() -> None:
    main = _read(FRONTEND_MAIN)
    snippet = _snippet_between(main, '        case "plan_ready": {', '        case "clarification_needed": {')

    assert 'setRunState("awaiting_confirmation");' in snippet
    assert 'setInteractionMode("plan_review");' in snippet
    assert "setPlan(nextPlan);" in snippet
    assert 'setClarificationQuestion("");' in snippet
    assert 'setClarificationOptions([]);' in snippet
    assert 'setRecoveryText("");' in snippet
    assert "acknowledgePendingCommands(type," in snippet


def test_plan_review_command_paths_remain_typed_and_pending_only() -> None:
    main = _read(FRONTEND_MAIN)
    confirm_snippet = _snippet_between(
        main,
        "  const handleConfirmPlan = useCallback(() => {",
        "  const handleSendPlanCorrection = useCallback(() => {",
    )
    correction_snippet = _snippet_between(
        main,
        "  const handleSendPlanCorrection = useCallback(() => {",
        '  const handleSendClarificationAnswer = useCallback(',
    )

    assert 'buildFrontendCommandEnvelope("confirmed", commandPayload);' in confirm_snippet
    assert "recordPendingCommand(commandEnvelope," in confirm_snippet
    assert "setRunState(" not in confirm_snippet
    assert "setInteractionMode(" not in confirm_snippet
    assert "setPlan(" not in confirm_snippet

    assert 'buildFrontendCommandEnvelope("correction",' in correction_snippet
    assert "recordPendingCommand(commandEnvelope," in correction_snippet
    assert "setRunState(" not in correction_snippet
    assert "setInteractionMode(" not in correction_snippet
    assert "setPlan(" not in correction_snippet

    assert "onConfirmPlan: handleConfirmPlan" in main
    assert "onSendCorrection: handleSendPlanCorrection" in main
    assert "onSendPlanCorrection: handleSendPlanCorrection" in main


def test_clarification_needed_backend_event_drives_clarification_read_model() -> None:
    main = _read(FRONTEND_MAIN)
    snippet = _snippet_between(main, '        case "clarification_needed": {', '        case "error":')

    assert 'setRunState("awaiting_confirmation");' in snippet
    assert 'setInteractionMode("clarification");' in snippet
    assert "setClarificationQuestion(clarification.question);" in snippet
    assert "setClarificationOptions(clarification.options);" in snippet
    assert 'setClarificationAnswerText("");' in snippet
    assert 'setPlanCorrectionText("");' in snippet
    assert 'setRecoveryText("");' in snippet
    assert "acknowledgePendingCommands(type," in snippet


def test_clarification_answer_command_stays_typed_until_backend_event() -> None:
    main = _read(FRONTEND_MAIN)
    snippet = _snippet_between(
        main,
        '  const handleSendClarificationAnswer = useCallback(\n    (answerOverride = "") => {',
        '  const handleSendRecoveryInstruction = useCallback(() => {',
    )

    assert 'buildFrontendCommandEnvelope("option_selected", {' in snippet
    assert "recordPendingCommand(commandEnvelope," in snippet
    assert "setRunState(" not in snippet
    assert "setInteractionMode(" not in snippet
    assert "setClarificationQuestion(" not in snippet
    assert "setClarificationOptions(" not in snippet


def test_recovery_needed_backend_event_drives_recovery_read_model() -> None:
    main = _read(FRONTEND_MAIN)
    snippet = _snippet_between(main, '        case "recovery_needed": {', '        case "runtime_rejected": {')

    assert 'setRunState("recovery");' in snippet
    assert 'setInteractionMode("recovery");' in snippet
    assert "setLastError(recoveryReason);" in snippet
    assert 'setPlanCorrectionText("");' in snippet
    assert 'setClarificationQuestion("");' in snippet
    assert 'setClarificationOptions([]);' in snippet
    assert 'setClarificationAnswerText("");' in snippet
    assert 'setRecoveryText("");' in snippet
    assert "appendConversation(\"system\", recoveryReason);" in snippet
    assert 'appendTimeline(recoveryReason, "err");' in snippet
    assert "acknowledgePendingCommands(type," in snippet


def test_recovery_instruction_command_stays_typed_without_closing_recovery_locally() -> None:
    main = _read(FRONTEND_MAIN)
    snippet = _snippet_between(
        main,
        "  const handleSendRecoveryInstruction = useCallback(() => {",
        "  const handleBackendMessage = useCallback(",
    )

    assert 'buildFrontendCommandEnvelope("correction", {' in snippet
    assert "recordPendingCommand(commandEnvelope," in snippet
    assert "setRunState(" not in snippet
    assert "setInteractionMode(" not in snippet
    assert 'setRecoveryText("");' in snippet


def test_runtime_rejected_preserves_backend_reason_and_current_state() -> None:
    main = _read(FRONTEND_MAIN)
    snippet = _snippet_between(main, '        case "runtime_rejected": {', '        case "llm_result": {')

    assert "rejectPendingCommand(rejectionCommandId," in snippet
    assert "rejection_code: rejectionCode" in snippet
    assert "rejection_reason: rejectionReason" in snippet
    assert "current_state: currentState," in snippet
    assert "setLastError(rejectionReason);" in snippet
    assert "currentStateSummary" in snippet
    assert "setRunState(" not in snippet
    assert "setInteractionMode(" not in snippet


def test_status_completion_does_not_clear_open_clarification_or_recovery_state() -> None:
    main = _read(FRONTEND_MAIN)
    snippet = _snippet_between(main, '        case "status": {', '        case "llm_thinking":')

    assert "if (nextState) {" in snippet
    assert "setRunState(nextState);" in snippet
    assert "setInteractionMode(nextState);" in snippet
    assert 'setClarificationQuestion("");' not in snippet
    assert 'setClarificationOptions([]);' not in snippet
    assert 'setRecoveryText("");' not in snippet
    assert 'setPlanCorrectionText("");' not in snippet


def test_unknown_or_malformed_event_keeps_lifecycle_truth_backend_owned() -> None:
    main = _read(FRONTEND_MAIN)
    snippet = _snippet_between(main, "        default:", "    },\n    [acknowledgePendingCommands, appendConversation, appendTimeline, rejectPendingCommand]\n  );")

    assert "appendTimeline(text || type, \"ok\");" in snippet
    assert "setRunState(" not in snippet
    assert "setInteractionMode(" not in snippet
    assert "setPlan(" not in snippet
    assert "setClarificationQuestion(" not in snippet
    assert "setRecoveryText(" not in snippet


def test_shadow_dom_runtime_bridge_exposes_plan_clarification_and_recovery_hooks() -> None:
    main = _read(FRONTEND_MAIN)

    assert "function AutoWorkbenchRuntime({ config }) {" in main
    assert "const shadowRoot = ensureShadowHost(node);" in main
    assert "const mountNode = shadowRoot ? ensureShadowMount(shadowRoot) : node;" in main
    assert "const panelState = toPanelState(transport.runState || normalized.panelState);" in main
    assert "const IDEPanel = window.IDEPanel;" in main
    assert "runtime={{" in main
    assert "plan," in main
    assert "pendingCommands," in main
    assert "clarificationQuestion," in main
    assert "clarificationOptions," in main
    assert "recoveryText," in main
    assert "lastError," in main
    assert "state={panelState}" in main
