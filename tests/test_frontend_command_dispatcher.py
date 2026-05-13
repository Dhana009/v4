"""
tests/test_frontend_command_dispatcher.py

Sprint 7 Cluster 5 — S7-0507/S7-0508: Typed command dispatcher and blocking.
TDD: written before implementation; tests start RED.
"""
from __future__ import annotations

import os
import re

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
CMD_DIR = os.path.join(REPO_ROOT, "frontend", "src", "commands")
BUILDER_PATH = os.path.join(CMD_DIR, "command-builder.js")
VALIDATION_PATH = os.path.join(CMD_DIR, "validation.js")
DISPATCHER_PATH = os.path.join(CMD_DIR, "dispatcher.js")
TYPES_PATH = os.path.join(REPO_ROOT, "frontend", "src", "store", "types.js")


def _builder() -> str:
    return open(BUILDER_PATH, encoding="utf-8").read()


def _validation() -> str:
    return open(VALIDATION_PATH, encoding="utf-8").read()


def _dispatcher() -> str:
    return open(DISPATCHER_PATH, encoding="utf-8").read()


# ---------------------------------------------------------------------------
# S7-0507 — dispatcher.js exists
# ---------------------------------------------------------------------------

def test_dispatcher_js_exists():
    assert os.path.exists(DISPATCHER_PATH), "frontend/src/commands/dispatcher.js missing"


def test_dispatcher_not_empty():
    assert os.path.getsize(DISPATCHER_PATH) > 100


# ---------------------------------------------------------------------------
# S7-0507 — command-builder.js: typed command construction
# ---------------------------------------------------------------------------

def test_builder_exports_schema_version():
    content = _builder()
    assert "FRONTEND_COMMAND_SCHEMA_VERSION" in content


def test_builder_exports_command_types():
    content = _builder()
    assert "COMMAND_TYPES" in content or "confirm_plan" in content, \
        "command-builder.js must list command types"


def test_builder_exports_build_command():
    content = _builder()
    assert "buildCommand" in content, "command-builder.js must export buildCommand"


def test_builder_includes_run_id_in_commands():
    content = _builder()
    assert "run_id" in content, "buildCommand must include run_id"


def test_builder_includes_command_id():
    content = _builder()
    assert "command_id" in content or "createCommandId" in content, \
        "command-builder.js must assign command_id to each command"


def test_builder_includes_schema_version_in_payload():
    content = _builder()
    assert "FRONTEND_COMMAND_SCHEMA_VERSION" in content and "version" in content, \
        "buildCommand must include schema version in payload"


# ---------------------------------------------------------------------------
# S7-0507 — dispatcher.js: dispatch function
# ---------------------------------------------------------------------------

def test_dispatcher_exports_dispatch():
    content = _dispatcher()
    assert "dispatch" in content, "dispatcher.js must export dispatch function"


def test_dispatcher_exports_create_dispatcher():
    content = _dispatcher()
    assert "createDispatcher" in content or "dispatch" in content, \
        "dispatcher.js must export dispatcher factory or dispatch function"


def test_dispatcher_validates_before_send():
    content = _dispatcher()
    # Must call validateCommand or canDispatch before sending
    has_validation = (
        "validateCommand" in content
        or "canDispatch" in content
        or "validation" in content.lower()
    )
    assert has_validation, "dispatcher.js must validate command before sending"


def test_dispatcher_does_not_mutate_store():
    content = _dispatcher()
    # Dispatcher must not set state, only send commands
    bad_patterns = [
        "setInteractionMode",
        "setRunState",
        "reducer(",
    ]
    for bp in bad_patterns:
        assert bp not in content, f"dispatcher.js must not call {bp} (no store mutation)"


def test_dispatcher_handles_transport_unavailable():
    content = _dispatcher()
    # Must guard against missing/null transport
    has_guard = (
        "transport" in content
        and ("null" in content or "undefined" in content or "!" in content or "typeof" in content)
    )
    assert has_guard, "dispatcher.js must handle unavailable transport"


def test_dispatcher_no_backend_imports():
    content = _dispatcher()
    bad = re.search(r"(from|import)\s+['\"][./]*(?:runtime|agent|server|browser)[/\"']", content)
    assert not bad, "dispatcher.js must not import backend modules"


# ---------------------------------------------------------------------------
# S7-0508 — validation.js: stale/missing ID blocking
# ---------------------------------------------------------------------------

def test_validation_not_stub():
    content = _validation()
    assert "VALIDATION_STUB" not in content or "validateCommand" in content, \
        "validation.js must be implemented (not stub)"


def test_validation_exports_validate_command():
    content = _validation()
    assert "validateCommand" in content, "validation.js must export validateCommand"


def test_validation_exports_can_dispatch():
    content = _validation()
    assert "canDispatch" in content, "validation.js must export canDispatch"


def test_validation_checks_run_id():
    content = _validation()
    assert "run_id" in content, "validation.js must check run_id presence"


def test_validation_returns_disabled_reason():
    content = _validation()
    # validateCommand or canDispatch must return a reason string
    has_reason = (
        "reason" in content
        or "disabledReason" in content
        or "disabled_reason" in content
    )
    assert has_reason, "validation.js must return reason when command is invalid"


def test_validation_stale_run_id_blocking():
    content = _validation()
    # Must compare command run_id against current state run_id
    has_stale_check = (
        "state.run_id" in content
        or "run_id !== state" in content
        or "stale" in content.lower()
        or "current_run_id" in content
    )
    assert has_stale_check, "validation.js must detect stale run_id commands"


def test_validation_confirm_plan_requires_plan_id():
    content = _validation()
    assert "plan_id" in content, "validation.js must check plan_id for confirm_plan"


def test_validation_skip_step_requires_step_id():
    content = _validation()
    assert "step_id" in content, "validation.js must check step_id for skip_step"


def test_validation_no_backend_imports():
    content = _validation()
    bad = re.search(r"(from|import)\s+['\"][./]*(?:runtime|agent|server|browser)[/\"']", content)
    assert not bad, "validation.js must not import backend modules"


def test_validation_no_demo_constants():
    content = _validation()
    assert "DEMO_" not in content
    assert "MOCK_" not in content


# ---------------------------------------------------------------------------
# S7-0508 — All command files under size limits
# ---------------------------------------------------------------------------

def test_builder_under_200_lines():
    content = _builder()
    assert len(content.splitlines()) <= 200, "command-builder.js too large (max 200 lines)"


def test_validation_under_200_lines():
    content = _validation()
    assert len(content.splitlines()) <= 200, "validation.js too large (max 200 lines)"


def test_dispatcher_under_150_lines():
    content = _dispatcher()
    assert len(content.splitlines()) <= 150, "dispatcher.js too large (max 150 lines)"
