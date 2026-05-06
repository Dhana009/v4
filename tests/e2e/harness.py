from __future__ import annotations

import asyncio
import json
import os
import socket
import subprocess
import sys
import time
from datetime import datetime, timezone
import urllib.error
import urllib.request
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, AsyncIterator, Awaitable, Callable, Mapping, TypeVar

from dotenv import dotenv_values


REPO_ROOT = Path(__file__).resolve().parents[2]
RESULTS_ROOT = REPO_ROOT / "test-results" / "autoworkbench-e2e"
E2E_LLM_MARKERS = ["[MODEL_ROUTER]", "[LLM_TELEMETRY]", "[CONTEXT_MANAGER]"]
E2E_LIFECYCLE_MARKERS = [
    "[PHASE]",
    "[CONFIRMED_PLAN]",
    "[EXECUTION_CONTRACT]",
    "[RECORDING_TARGET]",
    "[CODE_UPDATE]",
]
E2E_ARTIFACT_SCHEMA_VERSION = "autoworkbench.e2e.artifacts.v1"
DEFAULT_E2E_ARTIFACT_PATHS: dict[str, str] = {
    "manifest": "manifest.json",
    "test_result": "test-result.json",
    "backend_stdout": "backend.stdout.log",
    "backend_stderr": "backend.stderr.log",
    "static_server_stdout": "static-server.stdout.log",
    "static_server_stderr": "static-server.stderr.log",
    "frontend_console": "frontend.console.log",
    "backend_tail": "backend.tail.log",
    "frontend_console_tail": "frontend.console.tail.log",
    "failure": "failure.txt",
    "failure_context": "failure-context.json",
    "failure_screenshot": "failure.png",
    "page_html": "page.html",
}
T = TypeVar("T")


def find_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def ensure_directory(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def tail_text(path: Path, line_count: int = 80) -> str:
    if not path.exists():
        return ""
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    if not lines:
        return ""
    return "\n".join(lines[-line_count:])


def tail_lines_text(text: str, line_count: int = 30) -> str:
    lines = text.splitlines()
    if not lines:
        return ""
    return "\n".join(lines[-line_count:])


def _compact_reason(exc: BaseException) -> str:
    text = " ".join(str(exc).split())
    if not text:
        return "timeout"
    return text[:160] if len(text) > 160 else text


def _detect_marker_line(lines: list[str], markers: list[str]) -> str | None:
    for line in reversed(lines):
        if any(marker in line for marker in markers):
            return line
    return None


def wait_for_process_log_markers(process: "ManagedProcess", markers: list[str], timeout_s: float = 30.0) -> str:
    deadline = time.monotonic() + timeout_s
    last_text = ""
    while time.monotonic() < deadline:
        last_text = process.stdout_path.read_text(encoding="utf-8", errors="replace")
        last_text = f"{last_text}\n{process.stderr_path.read_text(encoding='utf-8', errors='replace')}"
        if all(marker in last_text for marker in markers):
            return last_text
        if process.poll() is not None:
            raise RuntimeError(
                f"{process.name} exited early with code {process.returncode}\n"
                f"stdout:\n{tail_text(process.stdout_path)}\n"
                f"stderr:\n{tail_text(process.stderr_path)}"
            )
        time.sleep(0.25)
    missing = [marker for marker in markers if marker not in last_text]
    raise TimeoutError(f"Timed out waiting for log markers {missing!r} in {process.name}")


async def wait_for_process_log_markers_async(process: "ManagedProcess", markers: list[str], timeout_s: float = 30.0) -> str:
    deadline = time.monotonic() + timeout_s
    last_text = ""
    while time.monotonic() < deadline:
        last_text = process.stdout_path.read_text(encoding="utf-8", errors="replace")
        last_text = f"{last_text}\n{process.stderr_path.read_text(encoding='utf-8', errors='replace')}"
        if all(marker in last_text for marker in markers):
            return last_text
        if process.poll() is not None:
            raise RuntimeError(
                f"{process.name} exited early with code {process.returncode}\n"
                f"stdout:\n{tail_text(process.stdout_path)}\n"
                f"stderr:\n{tail_text(process.stderr_path)}"
            )
        await asyncio.sleep(0.25)
    missing = [marker for marker in markers if marker not in last_text]
    raise TimeoutError(f"Timed out waiting for log markers {missing!r} in {process.name}")


def wait_for_http_url(url: str, *, label: str, process: "ManagedProcess | None" = None, timeout_s: float = 60.0) -> None:
    deadline = time.monotonic() + timeout_s
    last_error: Exception | None = None

    while time.monotonic() < deadline:
        if process is not None and process.poll() is not None:
            raise RuntimeError(
                f"{label} exited early with code {process.returncode}\n"
                f"stdout:\n{tail_text(process.stdout_path)}\n"
                f"stderr:\n{tail_text(process.stderr_path)}"
            )

        try:
            with urllib.request.urlopen(url, timeout=2) as response:
                if 200 <= response.status < 300:
                    return
        except Exception as exc:  # noqa: BLE001
            last_error = exc
        time.sleep(0.25)

    raise TimeoutError(f"Timed out waiting for {label} at {url}: {last_error}")


def create_run_artifact_dir(test_name: str) -> Path:
    ensure_directory(RESULTS_ROOT)
    stamp = time.strftime("%Y%m%d-%H%M%S")
    run_dir = RESULTS_ROOT / f"{test_name}-{stamp}-{os.getpid()}"
    ensure_directory(run_dir)
    return run_dir


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _normalize_artifact_paths(artifacts: Mapping[str, str | Path] | None) -> dict[str, str]:
    if artifacts is None:
        return dict(DEFAULT_E2E_ARTIFACT_PATHS)
    normalized: dict[str, str] = {}
    for name, path in artifacts.items():
        normalized[name] = str(path)
    return normalized


def write_json_artifact(path: Path, payload: dict[str, Any]) -> dict[str, Any]:
    ensure_directory(path.parent)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    return payload


def build_artifact_manifest(
    *,
    artifact_dir: Path,
    test_name: str,
    status: str = "running",
    created_at: str | None = None,
    artifacts: Mapping[str, str | Path] | None = None,
    run_id: str | None = None,
) -> dict[str, Any]:
    return {
        "schema_version": E2E_ARTIFACT_SCHEMA_VERSION,
        "test_name": test_name,
        "run_id": run_id or artifact_dir.name,
        "created_at": created_at or _utc_now_iso(),
        "artifact_dir": str(artifact_dir),
        "status": status,
        "artifacts": _normalize_artifact_paths(artifacts),
    }


def write_artifact_manifest(
    *,
    artifact_dir: Path,
    test_name: str,
    status: str = "running",
    created_at: str | None = None,
    artifacts: Mapping[str, str | Path] | None = None,
    run_id: str | None = None,
) -> dict[str, Any]:
    manifest = build_artifact_manifest(
        artifact_dir=artifact_dir,
        test_name=test_name,
        status=status,
        created_at=created_at,
        artifacts=artifacts,
        run_id=run_id,
    )
    return write_json_artifact(artifact_dir / "manifest.json", manifest)


def build_test_result(
    *,
    artifact_dir: Path,
    test_name: str,
    status: str = "unknown",
    error_summary: str | None = None,
    run_id: str | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "schema_version": E2E_ARTIFACT_SCHEMA_VERSION,
        "test_name": test_name,
        "run_id": run_id or artifact_dir.name,
        "artifact_dir": str(artifact_dir),
        "status": status,
    }
    if error_summary:
        payload["error_summary"] = error_summary
    return payload


def write_test_result(
    *,
    artifact_dir: Path,
    test_name: str,
    status: str = "unknown",
    error_summary: str | None = None,
    run_id: str | None = None,
) -> dict[str, Any]:
    result = build_test_result(
        artifact_dir=artifact_dir,
        test_name=test_name,
        status=status,
        error_summary=error_summary,
        run_id=run_id,
    )
    return write_json_artifact(artifact_dir / "test-result.json", result)


def finalize_test_result(
    *,
    artifact_dir: Path,
    test_name: str,
    status: str,
    error_summary: str | None = None,
    created_at: str | None = None,
    artifacts: Mapping[str, str | Path] | None = None,
    run_id: str | None = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    manifest = write_artifact_manifest(
        artifact_dir=artifact_dir,
        test_name=test_name,
        status=status,
        created_at=created_at,
        artifacts=artifacts,
        run_id=run_id,
    )
    result = write_test_result(
        artifact_dir=artifact_dir,
        test_name=test_name,
        status=status,
        error_summary=error_summary,
        run_id=run_id,
    )
    return manifest, result


def _load_repo_env_values() -> dict[str, str]:
    env_path = REPO_ROOT / ".env"
    raw_values = dotenv_values(env_path)
    repo_env = {key: value for key, value in raw_values.items() if key and value is not None}
    openai_key = str(repo_env.get("OPENAI_API_KEY", "")).strip()
    if not openai_key or not openai_key.startswith("sk-"):
        raise RuntimeError("Repo .env missing valid OPENAI_API_KEY")
    return {key: str(value) for key, value in repo_env.items()}


def _backend_launch_command() -> list[str]:
    return [
        sys.executable,
        "-c",
        "import dotenv; dotenv.load_dotenv = lambda *args, **kwargs: None; "
        "import runpy; runpy.run_module('server', run_name='__main__')",
    ]


@dataclass
class ManagedProcess:
    name: str
    process: subprocess.Popen[str]
    stdout_path: Path
    stderr_path: Path
    stdout_handle: Any
    stderr_handle: Any
    port: int
    base_url: str

    def poll(self) -> int | None:
        return self.process.poll()

    @property
    def returncode(self) -> int | None:
        return self.process.returncode

    def stop(self, timeout_s: float = 10.0) -> None:
        if self.poll() is None:
            self.process.terminate()
            try:
                self.process.wait(timeout=timeout_s)
            except subprocess.TimeoutExpired:
                self.process.kill()
                self.process.wait(timeout=timeout_s)
        for handle in (self.stdout_handle, self.stderr_handle):
            try:
                handle.flush()
            except Exception:
                pass
            try:
                handle.close()
            except Exception:
                pass


def start_managed_process(
    *,
    name: str,
    command: list[str],
    cwd: Path,
    artifact_dir: Path,
    stdout_name: str,
    stderr_name: str,
    env: dict[str, str],
    port: int,
) -> ManagedProcess:
    ensure_directory(artifact_dir)
    stdout_path = artifact_dir / stdout_name
    stderr_path = artifact_dir / stderr_name
    stdout_handle = stdout_path.open("w", encoding="utf-8", buffering=1)
    stderr_handle = stderr_path.open("w", encoding="utf-8", buffering=1)
    process = subprocess.Popen(
        command,
        cwd=str(cwd),
        env=env,
        stdout=stdout_handle,
        stderr=stderr_handle,
        text=True,
    )
    return ManagedProcess(
        name=name,
        process=process,
        stdout_path=stdout_path,
        stderr_path=stderr_path,
        stdout_handle=stdout_handle,
        stderr_handle=stderr_handle,
        port=port,
        base_url=f"http://127.0.0.1:{port}",
    )


def start_static_server(app_root: Path, artifact_dir: Path, port: int | None = None) -> ManagedProcess:
    server_port = port or find_free_port()
    env = os.environ.copy()
    env["PYTHONUNBUFFERED"] = "1"
    process = start_managed_process(
        name="static-server",
        command=[sys.executable, "-m", "http.server", str(server_port), "--bind", "127.0.0.1"],
        cwd=app_root,
        artifact_dir=artifact_dir,
        stdout_name="static-server.stdout.log",
        stderr_name="static-server.stderr.log",
        env=env,
        port=server_port,
    )
    wait_for_http_url(f"{process.base_url}/index.html", label="static server", process=process, timeout_s=10.0)
    return process


def start_autoworkbench_backend(
    start_url: str,
    artifact_dir: Path,
    port: int | None = None,
    remote_debugging_port: int | None = None,
) -> ManagedProcess:
    backend_port = port or find_free_port()
    debugging_port = remote_debugging_port or find_free_port()
    env = os.environ.copy()
    env.update(_load_repo_env_values())
    env["PYTHONUNBUFFERED"] = "1"
    env["PORT"] = str(backend_port)
    env["START_URL"] = start_url
    env["AUTOWORKBENCH_REMOTE_DEBUGGING_PORT"] = str(debugging_port)
    assert env["OPENAI_API_KEY"].startswith("sk-")
    assert env["PORT"] == str(backend_port)
    assert env["AUTOWORKBENCH_REMOTE_DEBUGGING_PORT"] == str(debugging_port)
    process = start_managed_process(
        name="autoworkbench-backend",
        command=_backend_launch_command(),
        cwd=REPO_ROOT,
        artifact_dir=artifact_dir,
        stdout_name="backend.stdout.log",
        stderr_name="backend.stderr.log",
        env=env,
        port=backend_port,
    )
    assert process.port == backend_port
    assert process.base_url == f"http://127.0.0.1:{backend_port}"
    wait_for_http_url(f"{process.base_url}/docs", label="AutoWorkbench backend", process=process, timeout_s=20.0)
    return process


async def _import_playwright_async_api() -> Any:
    try:
        from playwright.async_api import async_playwright
    except ImportError as exc:  # pragma: no cover - skip path is exercised by runtime environment
        raise RuntimeError("playwright.async_api is required for the E2E harness") from exc
    return async_playwright


async def _wait_for_page(context: Any, target_url: str, timeout_ms: int) -> Any:
    deadline = time.monotonic() + timeout_ms / 1000
    last_seen_urls: list[str] = []
    while time.monotonic() < deadline:
        pages = list(getattr(context, "pages", []))
        for page in pages:
            current_url = getattr(page, "url", "")
            if current_url:
                last_seen_urls.append(current_url)
            if current_url.startswith(target_url):
                try:
                    await page.wait_for_load_state("domcontentloaded", timeout=5000)
                except Exception:
                    pass
                return page
        await asyncio.sleep(0.25)
    seen = ", ".join(last_seen_urls[-5:]) if last_seen_urls else "<no pages>"
    raise TimeoutError(f"Timed out waiting for browser page {target_url}. Seen: {seen}")


async def _wait_for_locator_text(locator: Any, expected_text: str, timeout_ms: int = 120000) -> str:
    deadline = time.monotonic() + timeout_ms / 1000
    last_text = ""
    while time.monotonic() < deadline:
        try:
            last_text = await locator.inner_text()
        except Exception as exc:  # noqa: BLE001
            last_text = f"<error: {exc}>"
        if expected_text in last_text:
            return last_text
        await asyncio.sleep(0.25)
    raise TimeoutError(f"Timed out waiting for text {expected_text!r}. Last text: {last_text!r}")


@dataclass
class E2ESession:
    artifact_dir: Path
    test_name: str
    run_id: str
    created_at: str
    static_server: ManagedProcess
    backend: ManagedProcess
    playwright: Any
    browser: Any
    context: Any
    page: Any
    console_entries: list[str]
    current_stage: str = "initialized"
    stage_history: list[str] = field(default_factory=list)
    failure_artifacts_captured: bool = False
    result_status: str = "unknown"
    result_error_summary: str | None = None

    def log_stage_ok(self, stage: str) -> None:
        self.current_stage = stage
        self.stage_history.append(stage)
        print(f"[E2E_STAGE] {stage} ok")

    def _backend_log_text(self) -> str:
        return f"{self.backend.stdout_path.read_text(encoding='utf-8', errors='replace')}\n{self.backend.stderr_path.read_text(encoding='utf-8', errors='replace')}"

    def _backend_log_lines(self) -> list[str]:
        return self._backend_log_text().splitlines()

    def _backend_marker_lines(self, markers: list[str]) -> dict[str, str | None]:
        lines = self._backend_log_lines()
        return {marker: _detect_marker_line(lines, [marker]) for marker in markers}

    def _llm_activity(self) -> tuple[bool, str | None]:
        lines = self._backend_log_lines()
        marker_line = _detect_marker_line(lines, E2E_LLM_MARKERS)
        return marker_line is not None, marker_line

    async def _page_state(self) -> dict[str, Any]:
        current_url = getattr(self.page, "url", "")
        overlay_visible = False
        active_tab = ""
        active_mode = ""
        try:
            overlay_visible = bool(await self.page.locator("#autoworkbench-root .ide-panel").first.is_visible())
        except Exception:
            overlay_visible = False
        try:
            active_tab = (await self.page.locator(".ide-tab.active").first.inner_text()).strip()
        except Exception:
            active_tab = ""
        try:
            active_mode = (await self.page.locator(".ide-hd-state").first.inner_text()).strip()
        except Exception:
            active_mode = ""
        return {
            "current_url": current_url,
            "overlay_visible": overlay_visible,
            "active_tab": active_tab or None,
            "active_mode": active_mode or None,
        }

    async def save_failure_artifacts(self, reason: str, stage: str | None = None) -> dict[str, Any]:
        if self.failure_artifacts_captured:
            return {}
        self.failure_artifacts_captured = True
        self.result_status = "failed"
        self.result_error_summary = reason
        stage_name = stage or self.current_stage
        ensure_directory(self.artifact_dir)
        backend_log_text = self._backend_log_text()
        backend_tail = tail_lines_text(backend_log_text, 30)
        frontend_tail = "\n".join(self.console_entries[-30:])
        llm_triggered, last_llm_marker = self._llm_activity()
        lifecycle_markers = self._backend_marker_lines(E2E_LIFECYCLE_MARKERS)
        page_state: dict[str, Any] = {}
        page_error: str | None = None
        try:
            page_state = await self._page_state()
        except Exception as exc:  # noqa: BLE001
            page_error = str(exc)
            page_state = {
                "current_url": getattr(self.page, "url", ""),
                "overlay_visible": False,
                "active_tab": None,
                "active_mode": None,
            }
        context = {
            "artifact_dir": str(self.artifact_dir),
            "screenshot_path": str(self.artifact_dir / "failure.png"),
            "page_html_path": str(self.artifact_dir / "page.html"),
            "backend_tail_path": str(self.artifact_dir / "backend.tail.log"),
            "frontend_console_tail_path": str(self.artifact_dir / "frontend.console.tail.log"),
            "stage": stage_name,
            "reason": reason,
            "page_state": page_state,
            "page_error": page_error,
            "llm_triggered": llm_triggered,
            "last_llm_marker": last_llm_marker,
            "backend_lifecycle_markers": lifecycle_markers,
            "stage_history": self.stage_history + [stage_name],
        }
        (self.artifact_dir / "failure.txt").write_text(
            f"stage={stage_name}\nreason={reason}\nartifact_dir={self.artifact_dir}\n",
            encoding="utf-8",
        )
        (self.artifact_dir / "failure-context.json").write_text(
            json.dumps(context, indent=2, sort_keys=True),
            encoding="utf-8",
        )
        (self.artifact_dir / "backend.tail.log").write_text(backend_tail, encoding="utf-8")
        (self.artifact_dir / "frontend.console.tail.log").write_text(frontend_tail, encoding="utf-8")
        try:
            await self.page.screenshot(path=str(self.artifact_dir / "failure.png"), full_page=True)
        except Exception as exc:  # noqa: BLE001
            (self.artifact_dir / "failure-screenshot-error.txt").write_text(str(exc), encoding="utf-8")
        try:
            page_html = await self.page.content()
            (self.artifact_dir / "page.html").write_text(page_html, encoding="utf-8")
        except Exception as exc:  # noqa: BLE001
            (self.artifact_dir / "page-html-error.txt").write_text(str(exc), encoding="utf-8")
        return context

    async def run_stage(self, stage: str, timeout_s: float, action: Callable[[], Awaitable[T]]) -> T:
        self.current_stage = stage
        try:
            result = await asyncio.wait_for(action(), timeout=timeout_s)
        except Exception as exc:  # noqa: BLE001
            context = await self.save_failure_artifacts(_compact_reason(exc), stage=stage)
            llm_triggered = str(context.get("llm_triggered", False)).lower()
            last_llm_marker = context.get("last_llm_marker") or "none"
            print(
                f"[E2E_STAGE] {stage} failed reason={_compact_reason(exc)} "
                f"llm_triggered={llm_triggered} last_llm_marker={last_llm_marker} artifact_dir={self.artifact_dir}"
            )
            raise
        else:
            self.log_stage_ok(stage)
            return result

    def write_console_log(self) -> None:
        ensure_directory(self.artifact_dir)
        (self.artifact_dir / "frontend.console.log").write_text(
            "\n".join(self.console_entries),
            encoding="utf-8",
        )

    def backend_logs(self) -> str:
        return f"{self.backend.stdout_path.read_text(encoding='utf-8', errors='replace')}\n{self.backend.stderr_path.read_text(encoding='utf-8', errors='replace')}"

    async def close(self) -> None:
        self.write_console_log()
        self.backend.stop()
        self.static_server.stop()
        try:
            await self.browser.close()
        except Exception:
            pass
        try:
            await self.playwright.stop()
        except Exception:
            pass
        finalize_test_result(
            artifact_dir=self.artifact_dir,
            test_name=self.test_name,
            status=self.result_status,
            error_summary=self.result_error_summary,
            created_at=self.created_at,
            run_id=self.run_id,
        )


def _capture_console(console_entries: list[str], page: Any) -> None:
    def on_console(message: Any) -> None:
        try:
            text = message.text
        except Exception:
            text = str(message)
        try:
            entry_type = message.type
        except Exception:
            entry_type = "log"
        console_entries.append(f"[console:{entry_type}] {text}")

    def on_page_error(error: Any) -> None:
        console_entries.append(f"[pageerror] {error}")

    def on_request_failed(request: Any) -> None:
        try:
            url = request.url
        except Exception:
            url = "<unknown>"
        try:
            failure = request.failure.error_text
        except Exception:
            failure = "request failed"
        console_entries.append(f"[requestfailed] {url} :: {failure}")

    page.on("console", on_console)
    page.on("pageerror", on_page_error)
    page.on("requestfailed", on_request_failed)


async def _connect_browser_page(remote_debugging_port: int, target_url: str) -> tuple[Any, Any, Any, Any]:
    async_playwright = await _import_playwright_async_api()
    playwright = await async_playwright().start()
    endpoint_url = f"http://127.0.0.1:{remote_debugging_port}"
    deadline = time.monotonic() + 20.0
    last_error: Exception | None = None
    while time.monotonic() < deadline:
        try:
            browser = await playwright.chromium.connect_over_cdp(endpoint_url)
            break
        except Exception as exc:  # noqa: BLE001
            last_error = exc
            await asyncio.sleep(0.25)
    else:
        await playwright.stop()
        raise RuntimeError(f"Timed out connecting to backend browser at {endpoint_url}: {last_error}")

    contexts = list(getattr(browser, "contexts", []))
    if not contexts:
        await browser.close()
        await playwright.stop()
        raise RuntimeError("No browser context available after CDP connection")

    context = contexts[0]
    page = await _wait_for_page(context, target_url, timeout_ms=15000)
    return playwright, browser, context, page


@asynccontextmanager
async def start_e2e_session(*, test_name: str, app_root: Path) -> AsyncIterator[E2ESession]:
    artifact_dir = create_run_artifact_dir(test_name)
    created_at = _utc_now_iso()
    run_id = artifact_dir.name
    write_artifact_manifest(
        artifact_dir=artifact_dir,
        test_name=test_name,
        status="running",
        created_at=created_at,
        run_id=run_id,
    )
    write_test_result(
        artifact_dir=artifact_dir,
        test_name=test_name,
        status="unknown",
        run_id=run_id,
    )
    static_server: ManagedProcess | None = None
    backend: ManagedProcess | None = None
    playwright: Any | None = None
    browser: Any | None = None
    context: Any | None = None
    page: Any | None = None
    session: E2ESession | None = None
    try:
        static_server = start_static_server(app_root, artifact_dir)
        start_url = f"{static_server.base_url}/index.html"
        backend_remote_debugging_port = find_free_port()
        backend = start_autoworkbench_backend(
            start_url=start_url,
            artifact_dir=artifact_dir,
            remote_debugging_port=backend_remote_debugging_port,
        )
        console_entries: list[str] = []
        playwright, browser, context, page = await _connect_browser_page(backend_remote_debugging_port, start_url)
        _capture_console(console_entries, page)
        session = E2ESession(
            artifact_dir=artifact_dir,
            test_name=test_name,
            run_id=run_id,
            created_at=created_at,
            static_server=static_server,
            backend=backend,
            playwright=playwright,
            browser=browser,
            context=context,
            page=page,
            console_entries=console_entries,
        )
        session.log_stage_ok("backend_started")
        session.log_stage_ok("websocket_connected")
        yield session
        session.result_status = "passed"
    except Exception as exc:
        if session is not None and not session.failure_artifacts_captured:
            await session.save_failure_artifacts(str(exc), stage=session.current_stage)
        elif session is None:
            finalize_test_result(
                artifact_dir=artifact_dir,
                test_name=test_name,
                status="failed",
                error_summary=_compact_reason(exc),
                created_at=created_at,
                run_id=run_id,
            )
        raise
    finally:
        if session is not None:
            await session.close()
        else:
            if browser is not None:
                try:
                    await browser.close()
                except Exception:
                    pass
            if playwright is not None:
                try:
                    await playwright.stop()
                except Exception:
                    pass
            if backend is not None:
                backend.stop()
            if static_server is not None:
                static_server.stop()


async def wait_for_overlay_ready(page: Any, timeout_ms: int = 10000) -> None:
    await page.locator("#autoworkbench-root").wait_for(state="attached", timeout=timeout_ms)
    await page.get_by_role("button", name="Run Pending Steps").first.wait_for(state="visible", timeout=timeout_ms)


async def wait_for_agents_page(page: Any, timeout_ms: int = 15000) -> None:
    await page.wait_for_url("**/agents.html", timeout=timeout_ms)
    await page.get_by_role("heading", name="Playwright Test Agents").wait_for(state="visible", timeout=timeout_ms)
