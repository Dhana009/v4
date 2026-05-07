from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
FRONTEND_MAIN = REPO_ROOT / "frontend/src/main.jsx"
FRONTEND_PANEL = REPO_ROOT / "frontend/aw-ide-panel.jsx"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _snippet_between(source: str, start_marker: str, end_marker: str) -> str:
    start = source.find(start_marker)
    assert start != -1, f"missing start marker: {start_marker}"
    end = source.find(end_marker, start + len(start_marker))
    assert end != -1, f"missing end marker: {end_marker}"
    return source[start:end]


def test_trace_surface_is_backend_read_model_driven_and_shadow_dom_ready() -> None:
    main = _read(FRONTEND_MAIN)
    panel = _read(FRONTEND_PANEL)

    assert "traceEntries" in main
    assert "setTraceEntries" in main
    assert "normalizeTraceEntry" in main
    assert "buildTraceEntryFromBackendMessage" in main
    assert "mergeTraceEntryList" in main
    assert 'traceEntries,' in main
    assert 'data-testid="trace"' in panel
    assert 'aria-label="Trace"' in panel
    assert 'data-testid="trace-row"' in panel
    assert 'data-testid="trace-artifacts"' in panel
    assert 'testId="trace-log"' in panel
    assert '"trace-tab"' in panel
    assert 'aria-label="Trace"' in panel


def test_trace_entry_normalizer_is_display_only_and_keeps_evidence_fields() -> None:
    main = _read(FRONTEND_MAIN)
    snippet = _snippet_between(main, "function normalizeTraceEntry(", "function normalizeTraceEntries(")

    for field in (
        "type",
        "category",
        "timestamp",
        "source",
        "evidenceRef",
        "redactionStatus",
        "redactionWarning",
        "rejectionReason",
        "currentStateLabel",
        "artifacts",
        "diagnostic",
        "severity",
    ):
        assert f"{field}:" in snippet or f"{field}," in snippet
    assert "setRunState(" not in snippet
    assert "setInteractionMode(" not in snippet
    assert "setRecordedSteps(" not in snippet
    assert "setCodePreview(" not in snippet
    assert "setPendingCommands(" not in snippet


def test_backend_messages_feed_trace_entries_without_becoming_lifecycle_truth() -> None:
    main = _read(FRONTEND_MAIN)
    snippet = _snippet_between(
        main,
        "      const traceEntry = buildTraceEntryFromBackendMessage(message);",
        "      switch (type) {",
    )
    record_snippet = _snippet_between(
        main,
        "  const recordTraceEntry = useCallback((traceEntry) => {",
        "  const recordPendingCommand = useCallback(",
    )

    assert "buildTraceEntryFromBackendMessage(message);" in snippet
    assert "recordTraceEntry(traceEntry);" in snippet
    assert "setTraceEntries((current) => mergeTraceEntryList(current, traceEntry));" in record_snippet
    assert "setRunState(" not in snippet
    assert "setInteractionMode(" not in snippet
    assert "setRecordedSteps(" not in snippet
    assert "setCodePreview(" not in snippet
    assert "setPendingCommands(" not in snippet


def test_trace_rows_preserve_rejection_redaction_and_artifact_metadata() -> None:
    main = _read(FRONTEND_MAIN)
    panel = _read(FRONTEND_PANEL)

    assert "rejectionReason" in main
    assert "currentStateLabel" in main
    assert "redactionStatus" in main
    assert "redactionWarning" in main
    assert "artifacts" in main
    assert "entry.rejectionReason" in panel or "rejectionReason" in panel
    assert "entry.currentStateLabel" in panel or "currentStateLabel" in panel
    assert "entry.redactionStatus" in panel or "redactionStatus" in panel
    assert "entry.redactionWarning" in panel or "redactionWarning" in panel
    assert "entry.artifacts" in panel or "artifacts" in panel


def test_missing_evidence_ref_and_unknown_trace_rows_render_as_diagnostics() -> None:
    main = _read(FRONTEND_MAIN)
    panel = _read(FRONTEND_PANEL)

    assert "Evidence ref missing" in main
    assert "Unknown trace event" in main
    assert "entry.diagnostic" in panel
    assert "ide-trace-warning" in panel


def test_trace_artifact_metadata_can_reference_dev4_outputs_by_name_only() -> None:
    main = _read(FRONTEND_MAIN)

    for artifact_name in (
        "manifest.json",
        "test-result.json",
        "summary.md",
        "events.ndjson",
        "commands.json",
        "rejections.json",
        "redaction-report.json",
    ):
        assert artifact_name in main
