from __future__ import annotations

import json
import sys
from pathlib import Path
from types import SimpleNamespace

from tests.e2e import harness


def test_start_autoworkbench_backend_uses_selected_port_for_env_and_readiness(monkeypatch, tmp_path: Path) -> None:
    ports = iter([53211, 53212])
    captured: dict[str, object] = {}
    expected_repo_key = "sk-repo-key"

    monkeypatch.setattr(harness, "find_free_port", lambda: next(ports))
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


def test_manifest_includes_existing_known_artifact_filenames_when_provided(tmp_path: Path) -> None:
    artifacts = {
        "manifest": "manifest.json",
        "test_result": "test-result.json",
        "backend_stdout": "backend.stdout.log",
        "backend_stderr": "backend.stderr.log",
        "frontend_console": "frontend.console.log",
        "failure_screenshot": "failure.png",
    }

    harness.write_artifact_manifest(
        artifact_dir=tmp_path,
        test_name="fresh_artifact_baseline",
        created_at="2026-05-07T00:00:00Z",
        status="running",
        artifacts=artifacts,
    )

    payload = json.loads((tmp_path / "manifest.json").read_text(encoding="utf-8"))
    assert payload["artifacts"] == artifacts


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
        artifacts={
            "manifest": "manifest.json",
            "test_result": "test-result.json",
        },
    )

    assert (tmp_path / "manifest.json").exists()
    assert (tmp_path / "test-result.json").exists()
    assert manifest["status"] == "unknown"
    assert result["status"] == "unknown"
