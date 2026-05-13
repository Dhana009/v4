from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
FRONTEND_MAIN = REPO_ROOT / "frontend/src/main.jsx"
FRONTEND_PANEL = REPO_ROOT / "frontend/aw-ide-panel.jsx"
RECORDED_STEP_MODEL = REPO_ROOT / "tests/test_recorded_step_model.py"
CODE_UPDATE_TEST = REPO_ROOT / "tests/test_code_update.py"
RECORDING_CODEGEN_TEST = REPO_ROOT / "tests/test_recording_codegen_truth_contract.py"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _snippet_between(source: str, start_marker: str, end_marker: str) -> str:
    start = source.find(start_marker)
    assert start != -1, f"missing start marker: {start_marker}"
    end = source.find(end_marker, start + len(start_marker))
    assert end != -1, f"missing end marker: {end_marker}"
    return source[start:end]


def test_frontend_recorded_code_surface_is_source_anchored() -> None:
    main = _read(FRONTEND_MAIN)
    panel = _read(FRONTEND_PANEL)

    assert "setRecordedSteps" in main
    assert "setCodePreview" in main
    assert "setCodeDiagnostics" in main
    assert "codeDiagnostics" in main
    assert 'case "step_recorded":' in main
    assert 'case "code_update":' in main
    assert "IDERecordedStepsSection" in panel
    assert "IDERecordedOutput" in panel
    assert "IDECodePreview" in panel
    assert "const codeDiagnostics = Array.isArray(runtime.codeDiagnostics) ? runtime.codeDiagnostics : [];" in panel
    assert 'codeDiagnostics={codeDiagnostics}' in panel
    assert 'testId="recorded"' in panel
    assert 'testId="code"' in panel


def test_step_recorded_event_drives_recorded_read_model_and_preserves_backend_ordering() -> None:
    main = _read(FRONTEND_MAIN)
    snippet = _snippet_between(main, '        case "step_recorded": {', '        case "code_update": {')

    assert "const nextRecordedStep = buildRecordedStepFromPayload(" in snippet
    assert "setRecordedSteps((current) => mergeRecordedStepList(current, nextRecordedStep));" in snippet
    assert "const nextPlan = updatePlanAfterRecordedStep(planRef.current, {" in snippet
    assert 'setRunState((current) => (current === "completed" ? current : planCompleted ? "completed" : "executing"));' in snippet
    assert 'setInteractionMode(planCompleted ? "completed" : "executing");' in snippet
    assert "acknowledgePendingCommands(type," in snippet
    assert "recorded_step_id: firstNonEmptyText(nextRecordedStep.id, nextRecordedStep.step_id)," in snippet
    assert "setCodePreview(" not in snippet
    assert "setCodeDiagnostics(" not in snippet


def test_code_update_event_drives_code_read_model_without_faking_recorded_truth() -> None:
    main = _read(FRONTEND_MAIN)
    snippet = _snippet_between(main, '        case "code_update": {', '        case "replay_started": {')

    assert "const nextCode = extractCodePreview(payload);" in snippet
    assert "if (nextCode) {" in snippet
    assert "setCodePreview(nextCode);" in snippet
    assert "setCodeDiagnostics(" in snippet
    assert "normalizeCodeDiagnostics(" in snippet
    assert "acknowledgePendingCommands(type," in snippet
    assert 'appendTimeline(text || "Code updated", "ok");' in snippet
    assert "setRecordedSteps(" not in snippet
    assert "mergeRecordedStepList(" not in snippet
    assert "updatePlanAfterRecordedStep(" not in snippet
    assert "setRunState(" not in snippet


def test_code_update_diagnostics_are_visibly_rendered_and_remain_display_only() -> None:
    panel = _read(FRONTEND_PANEL)
    snippet = _snippet_between(panel, 'function IDECodePreview({ codePreview, codeDiagnostics = [], live = false }) {', 'function IDETraceArtifactRow({ artifact }) {')

    assert "const diagnostics = Array.isArray(codeDiagnostics) ? codeDiagnostics.filter(Boolean) : [];" in snippet
    assert 'data-testid="code-diagnostics"' in snippet
    assert 'data-testid="code-diagnostic"' in snippet
    assert 'aria-label="Code diagnostics"' in snippet
    assert "firstText(entry.level, entry.severity, entry.kind, entry.type)" in snippet
    assert "firstText(entry.message, entry.reason, entry.detail, entry.text, entry.summary, entry.description, entry.note)" in snippet
    assert "firstText(entry.current_state, entry.currentState, entry.state)" in snippet
    assert "firstText(entry.evidence_ref, entry.evidenceRef)" in snippet
    assert "ide-code-diagnostic-message" in snippet
    assert "ide-code-diagnostic-state" in snippet
    assert "ide-code-diagnostic-evidence" in snippet
    assert "setRunState(" not in snippet
    assert "setInteractionMode(" not in snippet
    assert "setRecordedSteps(" not in snippet
    assert "setPendingCommands(" not in snippet
    assert 'Generated Playwright code will appear here.' in snippet
    assert 'Awaiting code_update…' in snippet


def test_recorded_step_child_structure_is_preserved_and_not_reinterpreted() -> None:
    main = _read(FRONTEND_MAIN)
    panel = _read(FRONTEND_PANEL)

    build_snippet = _snippet_between(
        main,
        "function buildRecordedStepFromPayload(payload, matchedStep, matchIndex, recordedStepId, recordedStepNumber, recordedStepIndex) {",
        "function isPlanStepCompleted(step) {",
    )
    normalize_snippet = _snippet_between(
        main,
        "function normalizeRecordedStep(step, index) {",
        "function sortRecordedSteps(steps) {",
    )
    recorded_card_snippet = _snippet_between(
        panel,
        "function IDERecordedStepCard({",
        "function IDERecordedStepsSection({",
    )
    output_snippet = _snippet_between(
        panel,
        "function IDERecordedOutput({",
        "function IDEPendingStepCard({",
    )

    assert 'children: source.children.map((child) => (child && typeof child === "object" ? { ...child } : child)),' in build_snippet
    assert "expected_outcome:" in normalize_snippet
    assert "child.code_lines" in recorded_card_snippet
    assert "child.generated_line" in recorded_card_snippet
    assert "child.description" in recorded_card_snippet
    assert "child.operationId" in recorded_card_snippet
    assert "child.kind" in recorded_card_snippet
    assert "child.code_lines" in output_snippet
    assert "child.generated_line" in output_snippet
    assert "expected_value" not in main
    assert "exact_text" not in main
    assert "expected_value" not in panel
    assert "exact_text" not in panel


def test_backend_contract_inventory_covers_exact_text_visible_and_diagnostics_cases() -> None:
    recorded_step_model = _read(RECORDED_STEP_MODEL)
    code_update = _read(CODE_UPDATE_TEST)

    assert "exact_text" in recorded_step_model
    assert "visible" in recorded_step_model
    assert "expected_value" in recorded_step_model
    assert "diagnostics" in code_update


def test_shadow_dom_runtime_bridge_exposes_recorded_and_code_surfaces() -> None:
    main = _read(FRONTEND_MAIN)

    assert "function AutoWorkbenchRuntime({ config }) {" in main
    assert "const hostResult = createHost(node);" in main  # Cluster 4: replaced ensureShadowHost
    assert "const mountNode = shadowRoot ? ensureShadowMount(shadowRoot) : node;" in main
    assert "runtime={{" in main
    assert "recordedSteps," in main
    assert "codePreview," in main
    assert "codeDiagnostics," in main
    assert 'state={panelState}' in main
    assert "aw-shadow-host" in main
    assert "aw-shadow-mount" in main
    panel = _read(FRONTEND_PANEL)
    assert 'testId="recorded"' in panel
    assert 'testId="code"' in panel
