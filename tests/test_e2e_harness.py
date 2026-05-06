from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace

from dotenv import dotenv_values

from tests.e2e import harness


def test_start_autoworkbench_backend_uses_selected_port_for_env_and_readiness(monkeypatch, tmp_path: Path) -> None:
    ports = iter([53211, 53212])
    captured: dict[str, object] = {}

    monkeypatch.setattr(harness, "find_free_port", lambda: next(ports))
    monkeypatch.setenv("OPENAI_API_KEY", "sk-stale-shell-key")
    expected_repo_key = dotenv_values(harness.REPO_ROOT / ".env")["OPENAI_API_KEY"]

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
