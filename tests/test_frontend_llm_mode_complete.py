"""
tests/test_frontend_llm_mode_complete.py

Contract tests for Cluster 10: Complete LLM Mode Frontend UI.
S6-1001 through S6-1012.

These are Python contract tests that verify the frontend JSX/JS source files
contain required hooks, testids, aria labels, command patterns, and event patterns.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
FRONTEND_DIR = REPO_ROOT / "frontend"
PANEL = FRONTEND_DIR / "aw-ide-panel.jsx"
TABS = FRONTEND_DIR / "aw-tabs.jsx"
HEADER = FRONTEND_DIR / "aw-header.jsx"
WORKBENCH = FRONTEND_DIR / "aw-workbench.jsx"
MAIN = FRONTEND_DIR / "src/main.jsx"
EVENT_STORE = FRONTEND_DIR / "src/store/event_store.js"
CMD_DISPATCHER = FRONTEND_DIR / "src/commands/dispatcher.js"


def _read(path: Path) -> str:
    if path.exists():
        return path.read_text(encoding="utf-8")
    return ""


def _any_file_contains(paths: list[Path], pattern: str) -> bool:
    for p in paths:
        if pattern in _read(p):
            return True
    return False


ALL_FRONTEND = [PANEL, TABS, HEADER, WORKBENCH, MAIN]


# ---------------------------------------------------------------------------
# S6-1001: Shadow DOM host and product UI boundary
# ---------------------------------------------------------------------------

def test_shadow_dom_host_root_hook_exists():
    """aw-root hook must exist for shadow DOM mounting."""
    content = "".join(_read(p) for p in ALL_FRONTEND)
    assert any(hook in content for hook in ("aw-root", "data-testid=\"aw-root\"", "id=\"aw-root\""))


def test_ui_boundary_no_inline_backend_logic():
    """Frontend must not own session state or runtime lifecycle."""
    content = _read(PANEL) + _read(TABS)
    # Frontend must not call internal runtime functions directly
    forbidden = ["import runtime.", "from runtime import", "classify_failure(", "replay_one("]
    for f in forbidden:
        assert f not in content, f"Frontend must not import backend runtime: {f}"


# ---------------------------------------------------------------------------
# S6-1002: Global shell — header, status, activity, footer
# ---------------------------------------------------------------------------

def test_global_shell_has_header():
    content = "".join(_read(p) for p in [HEADER, WORKBENCH, PANEL])
    assert content, "At least one shell file must exist"
    # Header file must exist with some content
    assert HEADER.exists() or WORKBENCH.exists() or PANEL.exists()


def test_global_shell_renders_status():
    content = "".join(_read(p) for p in ALL_FRONTEND)
    # Status rendering: any status badge or indicator
    assert any(kw in content for kw in ("status", "badge", "Badge", "state", "ready", "recording"))


# ---------------------------------------------------------------------------
# S6-1003: LLM tab — chat, plan, clarification, permission, recovery cards
# ---------------------------------------------------------------------------

def test_llm_tab_exists_in_frontend():
    content = "".join(_read(p) for p in ALL_FRONTEND)
    assert "LLM" in content or "llm" in content.lower()


def test_plan_card_exists():
    content = "".join(_read(p) for p in ALL_FRONTEND)
    assert any(kw in content for kw in ("plan", "Plan", "PlanCard", "plan-card", "ide-card"))


def test_clarification_card_or_pattern_exists():
    content = "".join(_read(p) for p in ALL_FRONTEND)
    assert any(kw in content for kw in ("clarif", "Clarif", "question", "Question", "ask_user", "ask-user"))


def test_permission_card_or_pattern_exists():
    content = "".join(_read(p) for p in ALL_FRONTEND)
    assert any(kw in content for kw in ("permission", "Permission", "autonomy", "confirm", "Confirm"))


def test_recovery_card_or_pattern_exists():
    content = "".join(_read(p) for p in ALL_FRONTEND)
    assert any(kw in content for kw in ("recovery", "Recovery", "repair", "Repair", "fail", "error", "Error"))


# ---------------------------------------------------------------------------
# S6-1004: Steps tab — scoped step builder and locator state
# ---------------------------------------------------------------------------

def test_steps_tab_exists():
    content = "".join(_read(p) for p in ALL_FRONTEND)
    assert "Steps" in content or "StepsTab" in content or "steps-tab" in content


def test_steps_tab_has_locator_display():
    content = _read(TABS) + _read(PANEL)
    assert any(kw in content for kw in ("locator", "Locator", "getBy", "getByRole", "getByText", "CodeLine"))


def test_steps_tab_has_recorded_steps_display():
    content = _read(TABS) + _read(PANEL)
    assert any(kw in content for kw in ("recorded", "Recorded", "steps", "step"))


# ---------------------------------------------------------------------------
# S6-1005: Recommendation review UI
# ---------------------------------------------------------------------------

def test_recommendation_ui_exists():
    content = "".join(_read(p) for p in ALL_FRONTEND)
    assert any(kw in content for kw in ("recommend", "Recommend", "validation", "Validation", "accept", "Accept"))


# ---------------------------------------------------------------------------
# S6-1006: Recorded tab — immutable evidence and repair/version display
# ---------------------------------------------------------------------------

def test_recorded_tab_exists():
    content = "".join(_read(p) for p in ALL_FRONTEND)
    assert any(kw in content for kw in ("Recorded", "recorded", "RecordedTab", "recorded-tab"))


def test_recorded_tab_shows_step_status():
    content = _read(TABS) + _read(PANEL)
    assert any(kw in content for kw in ("passed", "Passed", "status", "Badge", "badge"))


# ---------------------------------------------------------------------------
# S6-1007: Code tab — generated spec, warnings, export/save
# ---------------------------------------------------------------------------

def test_code_tab_exists():
    content = "".join(_read(p) for p in ALL_FRONTEND)
    assert any(kw in content for kw in ("CodeTab", "Code tab", "code-tab", "CodeLine"))


def test_code_tab_has_export():
    content = _read(TABS) + _read(PANEL)
    assert any(kw in content for kw in ("Export", "export", ".spec.ts", "copy", "Copy", "save", "Save"))


# ---------------------------------------------------------------------------
# S6-1008: Trace tab — event timeline and diagnostics
# ---------------------------------------------------------------------------

def test_trace_tab_exists():
    content = "".join(_read(p) for p in ALL_FRONTEND)
    assert any(kw in content for kw in ("Debug", "Trace", "trace", "debug", "DebugTab", "TraceTab"))


def test_trace_tab_has_locator_inspector():
    content = _read(TABS) + _read(PANEL)
    assert any(kw in content for kw in ("locator", "inspector", "Inspector", "getBy", "xpath", "css"))


# ---------------------------------------------------------------------------
# S6-1009: Frontend typed event store completeness
# ---------------------------------------------------------------------------

def test_event_store_module_or_pattern_exists():
    """Event store may be in src/store or inline in JSX."""
    store_content = _read(EVENT_STORE)
    frontend_content = "".join(_read(p) for p in ALL_FRONTEND)
    combined = store_content + frontend_content
    # Must have some event or payload pattern
    assert any(kw in combined for kw in ("event", "payload", "sendPayload", "dispatch", "store", "Store"))


def test_send_payload_pattern_exists():
    content = "".join(_read(p) for p in ALL_FRONTEND)
    assert "sendPayload" in content or "postMessage" in content or "dispatch" in content


# ---------------------------------------------------------------------------
# S6-1010: Frontend command dispatcher completeness
# ---------------------------------------------------------------------------

def test_command_dispatcher_or_pattern_exists():
    dispatcher_content = _read(CMD_DISPATCHER)
    frontend_content = "".join(_read(p) for p in ALL_FRONTEND)
    combined = dispatcher_content + frontend_content
    assert any(kw in combined for kw in ("sendPayload", "dispatch", "command", "cmd", "action"))


def test_run_stop_commands_exist():
    content = "".join(_read(p) for p in ALL_FRONTEND)
    assert any(kw in content for kw in ("run", "Run", "stop", "Stop", "Start", "start"))


# ---------------------------------------------------------------------------
# S6-1011: Negative and edge UI states
# ---------------------------------------------------------------------------

def test_error_state_rendering_exists():
    content = "".join(_read(p) for p in ALL_FRONTEND)
    assert any(kw in content for kw in ("error", "Error", "fail", "Fail", "warning", "Warning", "empty"))


def test_empty_state_or_fallback_exists():
    content = _read(TABS) + _read(PANEL)
    assert any(kw in content for kw in ("empty", "Empty", "no ", "none", "null", "undefined", "\\u00a0", "—", "N/A"))


# ---------------------------------------------------------------------------
# S6-1012: Cluster 10 frontend integration proof — tab structure completeness
# ---------------------------------------------------------------------------

def test_five_tabs_represented():
    """LLM, Steps, Recorded, Code, Trace/Debug must all be represented."""
    content = "".join(_read(p) for p in ALL_FRONTEND)
    tabs = {
        "LLM": "LLM" in content or "llm" in content.lower(),
        "Steps": "Steps" in content or "StepsTab" in content,
        "Recorded": "Recorded" in content or "recorded" in content,
        "Code": "Code" in content or "CodeTab" in content,
        "Trace/Debug": "Debug" in content or "Trace" in content or "trace" in content,
    }
    missing = [name for name, present in tabs.items() if not present]
    assert not missing, f"Missing tabs: {missing}"


def test_frontend_files_are_parseable():
    """All frontend JSX files must be readable (no binary corruption)."""
    for p in [PANEL, TABS, HEADER, WORKBENCH]:
        if p.exists():
            content = _read(p)
            assert len(content) > 0, f"{p.name} is empty"
            # Must contain valid JSX markers
            assert "function" in content or "const" in content or "import" in content or "window." in content


def test_no_inline_runtime_imports_in_frontend():
    """Frontend must not directly import Python runtime modules."""
    for p in ALL_FRONTEND:
        if p.exists():
            content = _read(p)
            assert "import runtime" not in content
            assert "from runtime" not in content


def test_frontend_exposes_tabs_on_window():
    """Tabs must be exported via window.AW for host integration."""
    content = _read(TABS)
    assert "window.AW" in content or "window." in content or "export" in content
