from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

from tests.e2e import harness


NORMALIZED_EVIDENCE_ARTIFACTS = {
    "manifest": "manifest.json",
    "test_result": "test-result.json",
    "backend_log": "backend.log",
    "frontend_log": "frontend.log",
    "browser_console_log": "browser-console.log",
    "summary": "summary.md",
}
NORMALIZED_EVIDENCE_FILE_HASHES = {
    "backend.log": "sha256:backend-log",
    "frontend.log": "sha256:frontend-log",
    "browser-console.log": "sha256:browser-console-log",
    "summary.md": "sha256:summary-md",
}
NORMALIZED_EVIDENCE_NOTES = [
    "events.ndjson, commands.json, and rejections.json are deferred to a later backend event stream slice",
    "trace-summary and redaction-report are deferred to a later trace/export slice",
]


def _event(event_type: str, run_id: str = "run-123", **payload: object) -> dict[str, object]:
    event: dict[str, object] = {
        "schema_version": "autoworkbench.events.v1",
        "type": event_type,
        "run_id": run_id,
    }
    event.update(payload)
    return event


class _FakeLocator:
    def __init__(self, text: str = "", visible: bool = False) -> None:
        self._text = text
        self._visible = visible

    @property
    def first(self) -> "_FakeLocator":
        return self

    async def is_visible(self) -> bool:
        return self._visible

    async def inner_text(self) -> str:
        return self._text


class _FakePage:
    def __init__(self, url: str = "http://example.test/agents.html") -> None:
        self.url = url

    def locator(self, selector: str) -> _FakeLocator:
        if selector == "#autoworkbench-root .ide-panel":
            return _FakeLocator(visible=False)
        if selector == ".ide-tab.active":
            return _FakeLocator(text="")
        if selector == ".ide-hd-state":
            return _FakeLocator(text="")
        return _FakeLocator()

    async def screenshot(self, path: str, full_page: bool = True) -> None:  # noqa: ARG002
        Path(path).write_text("fake screenshot", encoding="utf-8")

    async def content(self) -> str:
        return "<html><body>fake page</body></html>"


class _FakeBrowser:
    async def close(self) -> None:
        return None


class _FakePlaywright:
    async def stop(self) -> None:
        return None


def _make_failure_session(tmp_path: Path) -> harness.E2ESession:
    stdout_path = tmp_path / "backend.stdout.log"
    stderr_path = tmp_path / "backend.stderr.log"
    stdout_path.write_text("[PLAN_READY] backend ready\n", encoding="utf-8")
    stderr_path.write_text("", encoding="utf-8")
    backend = SimpleNamespace(
        name="autoworkbench-backend",
        stdout_path=stdout_path,
        stderr_path=stderr_path,
        stop=lambda: None,
        poll=lambda: None,
        returncode=None,
    )
    static_server = SimpleNamespace(stop=lambda: None)
    return harness.E2ESession(
        artifact_dir=tmp_path,
        test_name="failure_artifacts",
        run_id="run-123",
        created_at="2026-05-07T00:00:00Z",
        static_server=static_server,
        backend=backend,
        playwright=_FakePlaywright(),
        browser=_FakeBrowser(),
        context=SimpleNamespace(),
        page=_FakePage(),
        console_entries=[],
    )


def test_resolve_e2e_port_prefers_explicit_value_then_env(monkeypatch) -> None:
    monkeypatch.setenv("AUTOWORKBENCH_E2E_BACKEND_PORT", "53101")

    assert (
        harness.resolve_e2e_port(
            53100,
            env_name="AUTOWORKBENCH_E2E_BACKEND_PORT",
            default=8765,
        )
        == 53100
    )
    assert (
        harness.resolve_e2e_port(
            None,
            env_name="AUTOWORKBENCH_E2E_BACKEND_PORT",
            default=8765,
        )
        == 53101
    )


def test_resolve_e2e_port_rejects_invalid_env_value(monkeypatch) -> None:
    monkeypatch.setenv("AUTOWORKBENCH_E2E_BACKEND_PORT", "not-a-number")

    with pytest.raises(RuntimeError, match="must be an integer"):
        harness.resolve_e2e_port(
            None,
            env_name="AUTOWORKBENCH_E2E_BACKEND_PORT",
            default=8765,
        )


def test_start_autoworkbench_backend_uses_selected_port_for_env_and_readiness(monkeypatch, tmp_path: Path) -> None:
    captured: dict[str, object] = {}
    expected_repo_key = "sk-repo-key"

    monkeypatch.setenv("OPENAI_API_KEY", "sk-stale-shell-key")
    monkeypatch.setattr(
        harness,
        "_load_repo_env_values",
        lambda: {
            "OPENAI_API_KEY": expected_repo_key,
            "REPO_ONLY_FLAG": "enabled",
        },
    )

    def fake_start_managed_process(**kwargs):
        captured["command"] = kwargs["command"]
        captured["env"] = kwargs["env"]
        captured["port"] = kwargs["port"]
        return SimpleNamespace(
            port=kwargs["port"],
            base_url=f"http://127.0.0.1:{kwargs['port']}",
            stdout_path=tmp_path / "backend.stdout.log",
            stderr_path=tmp_path / "backend.stderr.log",
            poll=lambda: None,
            returncode=None,
        )

    def fake_wait_for_http_url(url: str, *, label: str, process=None, timeout_s: float = 0.0) -> None:
        captured["wait_url"] = url
        captured["wait_label"] = label
        captured["wait_process_port"] = getattr(process, "port", None)
        captured["wait_timeout_s"] = timeout_s

    monkeypatch.setattr(harness, "start_managed_process", fake_start_managed_process)
    monkeypatch.setattr(harness, "wait_for_http_url", fake_wait_for_http_url)

    process = harness.start_autoworkbench_backend(
        start_url="http://127.0.0.1:9999/index.html",
        artifact_dir=tmp_path,
        port=53211,
        remote_debugging_port=53212,
    )

    assert process.port == 53211
    assert captured["port"] == 53211
    assert captured["env"]["OPENAI_API_KEY"] == expected_repo_key
    assert captured["env"]["REPO_ONLY_FLAG"] == "enabled"
    assert captured["env"]["PORT"] == "53211"
    assert captured["env"]["START_URL"] == "http://127.0.0.1:9999/index.html"
    assert captured["env"]["AUTOWORKBENCH_REMOTE_DEBUGGING_PORT"] == "53212"
    assert captured["wait_url"] == "http://127.0.0.1:53211/docs"
    assert captured["wait_label"] == "AutoWorkbench backend"
    assert captured["wait_process_port"] == 53211

    command = captured["command"]
    assert command[:2] == [sys.executable, "-c"]
    assert "dotenv.load_dotenv = lambda *args, **kwargs: None" in command[2]
    assert "runpy.run_module('server', run_name='__main__')" in command[2]


def test_wait_for_http_url_classifies_permission_error(tmp_path: Path) -> None:
    stdout_path = tmp_path / "stdout.log"
    stderr_path = tmp_path / "stderr.log"
    stdout_path.write_text("", encoding="utf-8")
    stderr_path.write_text("PermissionError [Errno 1] Operation not permitted\n", encoding="utf-8")

    process = SimpleNamespace(
        name="autoworkbench-backend",
        stdout_path=stdout_path,
        stderr_path=stderr_path,
        poll=lambda: 1,
        returncode=1,
    )

    with pytest.raises(RuntimeError, match="local socket allocation is blocked"):
        harness.wait_for_http_url(
            "http://127.0.0.1:8765/docs",
            label="AutoWorkbench backend",
            process=process,
            timeout_s=0.01,
        )


def test_default_artifact_paths_include_normalized_evidence_files() -> None:
    assert harness.DEFAULT_E2E_ARTIFACT_PATHS["backend_log"] == "backend.log"
    assert harness.DEFAULT_E2E_ARTIFACT_PATHS["frontend_log"] == "frontend.log"
    assert harness.DEFAULT_E2E_ARTIFACT_PATHS["browser_console_log"] == "browser-console.log"
    assert harness.DEFAULT_E2E_ARTIFACT_PATHS["summary"] == "summary.md"


def test_write_artifact_manifest_creates_required_keys_and_status(tmp_path: Path) -> None:
    manifest = harness.write_artifact_manifest(
        artifact_dir=tmp_path,
        test_name="fresh_artifact_baseline",
        created_at="2026-05-07T00:00:00Z",
        status="running",
        artifacts={
            "manifest": "manifest.json",
            "test_result": "test-result.json",
            "backend_stdout": "backend.stdout.log",
        },
    )

    manifest_path = tmp_path / "manifest.json"
    assert manifest_path.exists()

    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert payload == manifest
    assert payload["schema_version"] == harness.E2E_ARTIFACT_SCHEMA_VERSION
    assert payload["test_name"] == "fresh_artifact_baseline"
    assert payload["run_id"] == tmp_path.name
    assert payload["artifact_dir"] == str(tmp_path)
    assert payload["created_at"] == "2026-05-07T00:00:00Z"
    assert payload["status"] == "running"
    assert payload["artifacts"]["backend_stdout"] == "backend.stdout.log"
    assert payload["artifacts"]["test_result"] == "test-result.json"


def test_write_artifact_manifest_records_normalized_evidence_metadata(tmp_path: Path) -> None:
    manifest = harness.write_artifact_manifest(
        artifact_dir=tmp_path,
        test_name="fresh_artifact_baseline",
        created_at="2026-05-07T00:00:00Z",
        status="running",
        artifacts=NORMALIZED_EVIDENCE_ARTIFACTS,
        file_hashes=NORMALIZED_EVIDENCE_FILE_HASHES,
        optional_absence_notes=NORMALIZED_EVIDENCE_NOTES,
    )

    payload = json.loads((tmp_path / "manifest.json").read_text(encoding="utf-8"))
    assert payload == manifest
    assert payload["artifacts"] == NORMALIZED_EVIDENCE_ARTIFACTS
    assert payload["file_hashes"] == NORMALIZED_EVIDENCE_FILE_HASHES
    assert payload["optional_absence_notes"] == NORMALIZED_EVIDENCE_NOTES


def test_write_test_result_creates_failed_result_with_error_summary(tmp_path: Path) -> None:
    result = harness.write_test_result(
        artifact_dir=tmp_path,
        test_name="fresh_artifact_baseline",
        status="failed",
        error_summary="Timeout waiting for overlay ready",
    )

    result_path = tmp_path / "test-result.json"
    assert result_path.exists()

    payload = json.loads(result_path.read_text(encoding="utf-8"))
    assert payload == result
    assert payload["schema_version"] == harness.E2E_ARTIFACT_SCHEMA_VERSION
    assert payload["test_name"] == "fresh_artifact_baseline"
    assert payload["run_id"] == tmp_path.name
    assert payload["artifact_dir"] == str(tmp_path)
    assert payload["status"] == "failed"
    assert payload["error_summary"] == "Timeout waiting for overlay ready"


def test_finalize_test_result_writes_normalized_evidence_files(tmp_path: Path) -> None:
    artifact_texts = {
        "backend.log": "backend stdout\nbackend stderr\n",
        "frontend.log": "frontend console\n",
        "browser-console.log": "[console:log] browser ready\n",
        "summary.md": "# Summary\n\nNormalized evidence baseline.\n",
    }

    manifest, result = harness.finalize_test_result(
        artifact_dir=tmp_path,
        test_name="fresh_artifact_baseline",
        created_at="2026-05-07T00:00:00Z",
        status="unknown",
        error_summary=None,
        artifacts=NORMALIZED_EVIDENCE_ARTIFACTS,
        artifact_texts=artifact_texts,
        file_hashes=NORMALIZED_EVIDENCE_FILE_HASHES,
        optional_absence_notes=NORMALIZED_EVIDENCE_NOTES,
    )

    manifest_path = tmp_path / "manifest.json"
    result_path = tmp_path / "test-result.json"
    assert manifest_path.exists()
    assert result_path.exists()
    assert (tmp_path / "backend.log").exists()
    assert (tmp_path / "frontend.log").exists()
    assert (tmp_path / "browser-console.log").exists()
    assert (tmp_path / "summary.md").exists()
    assert (tmp_path / "backend.log").read_text(encoding="utf-8") == artifact_texts["backend.log"]
    assert (tmp_path / "frontend.log").read_text(encoding="utf-8") == artifact_texts["frontend.log"]
    assert (tmp_path / "browser-console.log").read_text(encoding="utf-8") == artifact_texts["browser-console.log"]
    assert (tmp_path / "summary.md").read_text(encoding="utf-8") == artifact_texts["summary.md"]

    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    result_payload = json.loads(result_path.read_text(encoding="utf-8"))
    assert payload == manifest
    assert result_payload == result
    assert payload["artifacts"] == NORMALIZED_EVIDENCE_ARTIFACTS
    assert payload["file_hashes"] == NORMALIZED_EVIDENCE_FILE_HASHES
    assert payload["optional_absence_notes"] == NORMALIZED_EVIDENCE_NOTES
    assert payload["status"] == "unknown"
    assert result_payload["status"] == "unknown"


def test_artifact_writers_do_not_require_live_runtime_dependencies(
    monkeypatch,
    tmp_path: Path,
) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    manifest, result = harness.finalize_test_result(
        artifact_dir=tmp_path,
        test_name="fresh_artifact_baseline",
        status="unknown",
        error_summary=None,
        created_at="2026-05-07T00:00:00Z",
        artifacts=NORMALIZED_EVIDENCE_ARTIFACTS,
        artifact_texts={
            "backend.log": "backend stdout\n",
            "frontend.log": "frontend console\n",
            "browser-console.log": "browser console\n",
            "summary.md": "# Summary\n\nNormalized evidence baseline.\n",
        },
        file_hashes=NORMALIZED_EVIDENCE_FILE_HASHES,
        optional_absence_notes=NORMALIZED_EVIDENCE_NOTES,
    )

    assert (tmp_path / "manifest.json").exists()
    assert (tmp_path / "test-result.json").exists()
    assert (tmp_path / "backend.log").exists()
    assert (tmp_path / "frontend.log").exists()
    assert (tmp_path / "browser-console.log").exists()
    assert (tmp_path / "summary.md").exists()
    assert (tmp_path / "backend.log").read_text(encoding="utf-8") == "backend stdout\n"
    assert (tmp_path / "frontend.log").read_text(encoding="utf-8") == "frontend console\n"
    assert (tmp_path / "browser-console.log").read_text(encoding="utf-8") == "browser console\n"
    assert (tmp_path / "summary.md").read_text(encoding="utf-8") == "# Summary\n\nNormalized evidence baseline.\n"
    assert manifest["artifacts"] == NORMALIZED_EVIDENCE_ARTIFACTS
    assert manifest["file_hashes"] == NORMALIZED_EVIDENCE_FILE_HASHES
    assert manifest["optional_absence_notes"] == NORMALIZED_EVIDENCE_NOTES
    assert manifest["status"] == "unknown"
    assert result["status"] == "unknown"


def test_wait_for_event_filters_captured_events_by_type() -> None:
    events = [
        _event("run_started"),
        _event("plan_ready", plan={"steps": 1}),
        _event("step_recorded", step_id="step-1"),
    ]

    matched = harness.wait_for_event(events, "plan_ready")

    assert matched["type"] == "plan_ready"
    assert matched["run_id"] == "run-123"
    assert matched["plan"] == {"steps": 1}


def test_assert_sequence_enforces_required_event_order() -> None:
    events = [
        _event("run_started"),
        _event("plan_ready"),
        _event("step_recorded"),
    ]

    harness.assert_sequence(events, ["run_started", "plan_ready", "step_recorded"])


def test_assert_no_event_passes_when_forbidden_event_absent() -> None:
    events = [
        _event("run_started"),
        _event("plan_ready"),
        _event("step_recorded"),
    ]

    harness.assert_no_event(events, "recovery_needed")


def test_assert_no_event_fails_with_clear_message_when_forbidden_event_present() -> None:
    events = [
        _event("run_started"),
        _event("plan_ready"),
        _event("recovery_needed", error_summary="missing required evidence"),
    ]

    with pytest.raises(AssertionError, match="recovery_needed"):
        harness.assert_no_event(events, "recovery_needed")


def test_wait_for_event_fails_with_clear_message_when_expected_event_missing() -> None:
    events = [
        _event("run_started"),
        _event("step_recorded"),
    ]

    with pytest.raises(AssertionError, match="plan_ready"):
        harness.wait_for_event(events, "plan_ready")


def test_collect_events_can_model_capture_before_action_without_browser_server(
    monkeypatch,
    tmp_path: Path,
) -> None:
    run_id = "run-123"
    run_dir = tmp_path / run_id
    run_dir.mkdir()
    (run_dir / "events.ndjson").write_text(
        "\n".join(
            [
                json.dumps(_event("plan_ready", captured_at="before_action")),
                json.dumps(_event("step_recorded", captured_at="after_action")),
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    monkeypatch.setattr(harness, "RESULTS_ROOT", tmp_path)

    events = harness.collect_events(run_id)

    assert [event["type"] for event in events] == ["plan_ready", "step_recorded"]
    assert events[0]["captured_at"] == "before_action"
    assert events[1]["captured_at"] == "after_action"


def test_finalize_test_result_can_record_event_evidence_presence_and_absence_metadata(
    tmp_path: Path,
) -> None:
    event_evidence = {
        "present": ["events.ndjson", "commands.json"],
        "missing": ["rejections.json"],
    }

    manifest, result = harness.finalize_test_result(
        artifact_dir=tmp_path,
        test_name="fresh_artifact_baseline",
        status="failed",
        error_summary="expected event missing",
        artifacts=NORMALIZED_EVIDENCE_ARTIFACTS,
        artifact_texts={
            "summary.md": "# Summary\n\nEvent evidence metadata baseline.\n",
        },
        event_evidence=event_evidence,
    )

    assert manifest["event_evidence"] == event_evidence
    assert result["event_evidence"] == event_evidence


def test_finalize_test_result_writes_events_ndjson_and_lists_it_in_manifest(
    tmp_path: Path,
) -> None:
    event_records = [
        _event("run_started"),
        _event("plan_ready", plan={"steps": 1}),
    ]

    manifest, result = harness.finalize_test_result(
        artifact_dir=tmp_path,
        test_name="events_artifact_baseline",
        status="unknown",
        error_summary=None,
        artifacts={
            "manifest": "manifest.json",
            "test_result": "test-result.json",
            "summary": "summary.md",
            "events": "events.ndjson",
        },
        artifact_texts={
            "summary.md": "# Summary\n\nEvents emission baseline.\n",
        },
        event_records=event_records,
        event_evidence={
            "events": "events.ndjson",
            "event_count": len(event_records),
        },
    )

    events_path = tmp_path / "events.ndjson"
    assert events_path.exists()
    lines = events_path.read_text(encoding="utf-8").splitlines()
    assert [json.loads(line)["type"] for line in lines] == ["run_started", "plan_ready"]
    assert len(lines) == 2
    assert "events.ndjson" in manifest["artifacts"].values()
    assert manifest["file_hashes"]["events.ndjson"].startswith("sha256:")
    assert manifest["event_evidence"]["events"] == "events.ndjson"
    assert result["event_evidence"]["events"] == "events.ndjson"
    assert "events.ndjson" in (tmp_path / "summary.md").read_text(encoding="utf-8")


def test_finalize_test_result_omits_deferred_events_note_when_events_ndjson_is_written(
    tmp_path: Path,
) -> None:
    event_records = [
        _event("run_started"),
        _event("plan_ready"),
    ]

    manifest, result = harness.finalize_test_result(
        artifact_dir=tmp_path,
        test_name="events_artifact_baseline",
        status="unknown",
        error_summary=None,
        artifacts={
            "manifest": "manifest.json",
            "test_result": "test-result.json",
            "summary": "summary.md",
            "events": "events.ndjson",
        },
        artifact_texts={
            "summary.md": "# Summary\n\nEvents emission baseline.\n",
        },
        event_records=event_records,
        event_evidence={
            "events": "events.ndjson",
        },
    )

    summary = (tmp_path / "summary.md").read_text(encoding="utf-8")

    assert all("events.ndjson" not in note for note in manifest["optional_absence_notes"])
    assert result["event_evidence"]["events"] == "events.ndjson"
    assert "events.ndjson" in summary


def test_finalize_test_result_writes_commands_json_and_lists_it_in_manifest(
    tmp_path: Path,
) -> None:
    command_records = [
        {"type": "run_started", "run_id": "run-123"},
        {"type": "plan_ready", "run_id": "run-123", "plan_id": "plan-1"},
    ]

    manifest, result = harness.finalize_test_result(
        artifact_dir=tmp_path,
        test_name="commands_artifact_baseline",
        status="unknown",
        error_summary=None,
        artifacts={
            "manifest": "manifest.json",
            "test_result": "test-result.json",
            "summary": "summary.md",
            "commands": "commands.json",
        },
        artifact_texts={
            "summary.md": "# Summary\n\nCommands emission baseline.\n",
        },
        command_records=command_records,
        event_evidence={
            "commands": "commands.json",
            "command_count": len(command_records),
        },
    )

    commands_path = tmp_path / "commands.json"
    assert commands_path.exists()
    payload = json.loads(commands_path.read_text(encoding="utf-8"))
    assert isinstance(payload, list)
    assert [record["type"] for record in payload] == ["run_started", "plan_ready"]
    assert manifest["artifacts"]["commands"] == "commands.json"
    assert manifest["file_hashes"]["commands.json"].startswith("sha256:")
    assert manifest["event_evidence"]["commands"] == "commands.json"
    assert result["event_evidence"]["commands"] == "commands.json"


def test_finalize_test_result_omits_deferred_commands_note_when_commands_json_is_written(
    tmp_path: Path,
) -> None:
    command_records = [
        {"type": "run_started", "run_id": "run-123"},
    ]

    manifest, result = harness.finalize_test_result(
        artifact_dir=tmp_path,
        test_name="commands_artifact_baseline",
        status="unknown",
        error_summary=None,
        artifacts={
            "manifest": "manifest.json",
            "test_result": "test-result.json",
            "summary": "summary.md",
            "commands": "commands.json",
        },
        artifact_texts={
            "summary.md": "# Summary\n\nCommands emission baseline.\n",
        },
        command_records=command_records,
        event_evidence={
            "commands": "commands.json",
        },
    )

    summary = (tmp_path / "summary.md").read_text(encoding="utf-8")

    assert all("commands.json" not in note for note in manifest["optional_absence_notes"])
    assert result["event_evidence"]["commands"] == "commands.json"
    assert "commands.json" in summary


def test_finalize_test_result_keeps_events_behavior_when_commands_json_is_written(
    tmp_path: Path,
) -> None:
    event_records = [
        _event("run_started"),
        _event("plan_ready"),
    ]
    command_records = [
        {"type": "run_started", "run_id": "run-123"},
        {"type": "plan_ready", "run_id": "run-123", "plan_id": "plan-1"},
    ]

    manifest, result = harness.finalize_test_result(
        artifact_dir=tmp_path,
        test_name="events_and_commands_artifact_baseline",
        status="unknown",
        error_summary=None,
        artifacts={
            "manifest": "manifest.json",
            "test_result": "test-result.json",
            "summary": "summary.md",
            "events": "events.ndjson",
            "commands": "commands.json",
        },
        artifact_texts={
            "summary.md": "# Summary\n\nEvents and commands emission baseline.\n",
        },
        event_records=event_records,
        command_records=command_records,
        event_evidence={
            "events": "events.ndjson",
            "commands": "commands.json",
        },
    )

    events_path = tmp_path / "events.ndjson"
    commands_path = tmp_path / "commands.json"

    assert [json.loads(line)["type"] for line in events_path.read_text(encoding="utf-8").splitlines()] == [
        "run_started",
        "plan_ready",
    ]
    assert isinstance(json.loads(commands_path.read_text(encoding="utf-8")), list)
    assert manifest["artifacts"]["events"] == "events.ndjson"
    assert manifest["artifacts"]["commands"] == "commands.json"
    assert result["event_evidence"]["events"] == "events.ndjson"
    assert result["event_evidence"]["commands"] == "commands.json"


def test_failure_artifacts_record_expected_and_observed_event_metadata(tmp_path: Path) -> None:
    session = _make_failure_session(tmp_path)
    captured_before_action = harness.collect_events(
        [
            _event("run_started"),
        ]
    )
    observed_events = [
        _event("run_started"),
        _event("step_executing"),
    ]
    event_evidence = {
        "captured_before_action": [event["type"] for event in captured_before_action],
        "expected_event_type": "plan_ready",
        "observed_event_types": [event["type"] for event in observed_events],
    }

    context = asyncio.run(
        session.save_failure_artifacts(
            "missing plan_ready event",
            stage="awaiting_plan_ready",
            expected_event_type="plan_ready",
            observed_event_types=[event["type"] for event in observed_events],
            event_evidence=event_evidence,
        )
    )

    failure_text = (tmp_path / "failure.txt").read_text(encoding="utf-8")
    failure_context = json.loads((tmp_path / "failure-context.json").read_text(encoding="utf-8"))

    assert context["expected_event_type"] == "plan_ready"
    assert context["observed_event_types"] == ["run_started", "step_executing"]
    assert context["event_evidence"] == event_evidence
    assert failure_context["expected_event_type"] == "plan_ready"
    assert failure_context["observed_event_types"] == ["run_started", "step_executing"]
    assert failure_context["event_evidence"] == event_evidence
    assert "expected_event_type=plan_ready" in failure_text
    assert "observed_event_types=['run_started', 'step_executing']" in failure_text
    assert "captured_before_action" in failure_text


def test_failure_artifacts_will_persist_event_evidence_through_close(tmp_path: Path) -> None:
    session = _make_failure_session(tmp_path)
    event_evidence = {
        "captured_before_action": ["run_started"],
        "expected_event_type": "plan_ready",
        "observed_event_types": ["run_started", "step_executing"],
        "present": ["backend.log", "summary.md"],
    }

    asyncio.run(
        session.save_failure_artifacts(
            "missing plan_ready event",
            stage="awaiting_plan_ready",
            expected_event_type="plan_ready",
            observed_event_types=["run_started", "step_executing"],
            event_evidence=event_evidence,
        )
    )
    asyncio.run(session.close())

    manifest = json.loads((tmp_path / "manifest.json").read_text(encoding="utf-8"))
    result = json.loads((tmp_path / "test-result.json").read_text(encoding="utf-8"))
    summary = (tmp_path / "summary.md").read_text(encoding="utf-8")

    assert manifest["optional_absence_notes"] == NORMALIZED_EVIDENCE_NOTES
    assert not (tmp_path / "events.ndjson").exists()
    assert not (tmp_path / "commands.json").exists()
    assert not (tmp_path / "rejections.json").exists()
    assert manifest["event_evidence"] == event_evidence
    assert result["event_evidence"] == event_evidence
    assert "## Event evidence" in summary
    assert '"expected_event_type": "plan_ready"' in summary
    assert '"observed_event_types": [' in summary


def test_failure_summary_mentions_expected_and_observed_event_types(tmp_path: Path) -> None:
    session = _make_failure_session(tmp_path)
    event_evidence = {
        "captured_before_action": ["run_started"],
        "expected_event_type": "plan_ready",
        "observed_event_types": ["run_started"],
    }

    asyncio.run(
        session.save_failure_artifacts(
            "missing plan_ready event",
            stage="awaiting_plan_ready",
            expected_event_type="plan_ready",
            observed_event_types=["run_started"],
            event_evidence=event_evidence,
        )
    )

    failure_text = (tmp_path / "failure.txt").read_text(encoding="utf-8")

    assert "expected_event_type=plan_ready" in failure_text
    assert "observed_event_types=['run_started']" in failure_text
    assert "missing plan_ready event" in failure_text
