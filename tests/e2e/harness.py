from __future__ import annotations

import asyncio
import os
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
from contextlib import asynccontextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Any, AsyncIterator


REPO_ROOT = Path(__file__).resolve().parents[2]
RESULTS_ROOT = REPO_ROOT / "test-results" / "autoworkbench-e2e"


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


def wait_for_process_log_markers(process: "ManagedProcess", markers: list[str], timeout_s: float = 120.0) -> str:
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
    wait_for_http_url(f"{process.base_url}/index.html", label="static server", process=process, timeout_s=30.0)
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
    env["PYTHONUNBUFFERED"] = "1"
    env["PORT"] = str(backend_port)
    env["START_URL"] = start_url
    env["AUTOWORKBENCH_REMOTE_DEBUGGING_PORT"] = str(debugging_port)
    process = start_managed_process(
        name="autoworkbench-backend",
        command=[sys.executable, "server.py"],
        cwd=REPO_ROOT,
        artifact_dir=artifact_dir,
        stdout_name="backend.stdout.log",
        stderr_name="backend.stderr.log",
        env=env,
        port=backend_port,
    )
    wait_for_http_url(f"{process.base_url}/docs", label="AutoWorkbench backend", process=process, timeout_s=90.0)
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
    static_server: ManagedProcess
    backend: ManagedProcess
    playwright: Any
    browser: Any
    context: Any
    page: Any
    console_entries: list[str]

    async def save_failure_artifacts(self, reason: str) -> None:
        ensure_directory(self.artifact_dir)
        (self.artifact_dir / "failure.txt").write_text(reason, encoding="utf-8")
        try:
            await self.page.screenshot(path=str(self.artifact_dir / "failure.png"), full_page=True)
        except Exception as exc:  # noqa: BLE001
            (self.artifact_dir / "failure-screenshot-error.txt").write_text(str(exc), encoding="utf-8")
        try:
            page_html = await self.page.content()
            (self.artifact_dir / "page.html").write_text(page_html, encoding="utf-8")
        except Exception as exc:  # noqa: BLE001
            (self.artifact_dir / "page-html-error.txt").write_text(str(exc), encoding="utf-8")

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
    deadline = time.monotonic() + 30.0
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
    page = await _wait_for_page(context, target_url, timeout_ms=30000)
    return playwright, browser, context, page


@asynccontextmanager
async def start_e2e_session(*, test_name: str, app_root: Path) -> AsyncIterator[E2ESession]:
    artifact_dir = create_run_artifact_dir(test_name)
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
            static_server=static_server,
            backend=backend,
            playwright=playwright,
            browser=browser,
            context=context,
            page=page,
            console_entries=console_entries,
        )
        yield session
    except Exception as exc:
        if session is not None:
            await session.save_failure_artifacts(str(exc))
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


async def wait_for_overlay_ready(page: Any, timeout_ms: int = 120000) -> None:
    await page.locator("#autoworkbench-root").wait_for(state="attached", timeout=timeout_ms)
    await page.get_by_role("button", name="Attach Element").first.wait_for(state="visible", timeout=timeout_ms)
    await page.get_by_role("button", name="Run Pending Steps").first.wait_for(state="visible", timeout=timeout_ms)


async def wait_for_agents_page(page: Any, timeout_ms: int = 120000) -> None:
    await page.wait_for_url("**/agents.html", timeout=timeout_ms)
    await page.get_by_role("heading", name="Playwright Test Agents").wait_for(state="visible", timeout=timeout_ms)
