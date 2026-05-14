"""Unified logging helper for backend + frontend ingest.

Format: `[ISO_TIME] [SUBSYS] [CATEGORY] key=val key=val ...`
All output goes to stdout with flush=True so launch.log captures it live.

Levels:
- info  (default) — high-signal events.
- debug — firehose. Enable with env AW_LOG=debug.

Use:
    from runtime.log import log, log_error
    log("WS_RECV", type="run_steps", n=1)
    log("LLM_REQ", model=name, msgs=len(msgs))
    log_error("FAST_PATH", "locator validation failed", exc=e)
"""
from __future__ import annotations

import os
import sys
import time
import traceback
from typing import Any

_LEVEL = (os.getenv("AW_LOG") or "info").strip().lower()
_DEBUG = _LEVEL == "debug"

_INFO_CATEGORIES = {
    "WS_RECV", "WS_SEND", "WS_OPEN", "WS_CLOSE", "WS_ERROR",
    "AGENT", "AGENT_RUN", "AGENT_RECORD", "PHASE", "STATE",
    "FAST_PATH", "RUNTIME",
    "LLM_REQ", "LLM_RES", "LLM_ERR",
    "COMMAND", "REDUCER",
    "ERROR", "BACKEND_READY", "PANEL",
}


def _iso_now() -> str:
    t = time.time()
    ms = int((t - int(t)) * 1000)
    return time.strftime("%H:%M:%S.", time.localtime(t)) + f"{ms:03d}"


def _fmt_kv(kv: dict[str, Any]) -> str:
    out: list[str] = []
    for k, v in kv.items():
        if v is None:
            out.append(f"{k}=null")
            continue
        s = str(v)
        if len(s) > 240:
            s = s[:237] + "..."
        if " " in s or "=" in s or "\n" in s:
            s = s.replace("\n", "\\n").replace('"', '\\"')
            s = f'"{s}"'
        out.append(f"{k}={s}")
    return " ".join(out)


def log(category: str, *, subsys: str = "BACK", **kv: Any) -> None:
    """Emit a single structured log line. Always flushes."""
    if not _DEBUG and category not in _INFO_CATEGORIES:
        return
    line = f"[{_iso_now()}] [{subsys}] [{category}] {_fmt_kv(kv)}".rstrip()
    print(line, flush=True)


def log_error(category: str, message: str, *, subsys: str = "BACK", exc: BaseException | None = None, **kv: Any) -> None:
    """Emit an ERROR line + optional traceback. Always emitted regardless of level."""
    line = f"[{_iso_now()}] [{subsys}] [{category}] level=error message={message!r} " + _fmt_kv(kv)
    print(line.rstrip(), flush=True)
    if exc is not None:
        try:
            tb = "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))
        except Exception:  # noqa: BLE001
            tb = repr(exc)
        # prefix every traceback line so it greps clearly
        for tline in tb.splitlines():
            print(f"[{_iso_now()}] [{subsys}] [{category}] tb {tline}", flush=True)


def log_front(payload: dict[str, Any]) -> None:
    """Re-emit a frontend-shipped line. Called by /api/log endpoint."""
    if not isinstance(payload, dict):
        return
    category = str(payload.get("category") or "FRONT").strip() or "FRONT"
    extra = {k: v for k, v in payload.items() if k != "category"}
    log(category, subsys="FRONT", **extra)


__all__ = ["log", "log_error", "log_front", "_DEBUG"]
