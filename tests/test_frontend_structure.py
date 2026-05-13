"""
tests/test_frontend_structure.py

Sprint 7 Cluster 3 — S7-0306: Frontend module structure creation.
TDD: written before implementation; module folder tests start RED.
"""
from __future__ import annotations

import os
import re

import pytest

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
FRONTEND_SRC = os.path.join(REPO_ROOT, "frontend", "src")


# ---------------------------------------------------------------------------
# Module folder existence — S7-0306
# ---------------------------------------------------------------------------

def test_host_module_folder_exists():  # S7-0306
    assert os.path.isdir(os.path.join(FRONTEND_SRC, "host"))


def test_transport_module_folder_exists():  # S7-0306
    assert os.path.isdir(os.path.join(FRONTEND_SRC, "transport"))


def test_store_module_folder_exists():  # S7-0306
    assert os.path.isdir(os.path.join(FRONTEND_SRC, "store"))


def test_commands_module_folder_exists():  # S7-0306
    assert os.path.isdir(os.path.join(FRONTEND_SRC, "commands"))


def test_components_module_folder_exists():  # S7-0306
    assert os.path.isdir(os.path.join(FRONTEND_SRC, "components"))


def test_components_primitives_folder_exists():  # S7-0306, S7-0307
    assert os.path.isdir(os.path.join(FRONTEND_SRC, "components", "primitives"))


def test_components_shell_folder_exists():  # S7-0306
    assert os.path.isdir(os.path.join(FRONTEND_SRC, "components", "shell"))


def test_components_llm_folder_exists():  # S7-0306
    assert os.path.isdir(os.path.join(FRONTEND_SRC, "components", "llm"))


def test_components_steps_folder_exists():  # S7-0306
    assert os.path.isdir(os.path.join(FRONTEND_SRC, "components", "steps"))


def test_styles_folder_exists():  # S7-0306, S7-0303
    assert os.path.isdir(os.path.join(FRONTEND_SRC, "styles"))


def test_test_utils_folder_exists():  # S7-0306
    assert os.path.isdir(os.path.join(FRONTEND_SRC, "test-utils"))


# ---------------------------------------------------------------------------
# Stub file existence — S7-0306
# ---------------------------------------------------------------------------

def test_host_jsx_stub_exists():  # S7-0306
    assert os.path.exists(os.path.join(FRONTEND_SRC, "host", "host.jsx"))


def test_websocket_client_stub_exists():  # S7-0306
    assert os.path.exists(os.path.join(FRONTEND_SRC, "transport", "websocket-client.js"))


def test_event_receiver_stub_exists():  # S7-0306
    assert os.path.exists(os.path.join(FRONTEND_SRC, "transport", "event-receiver.js"))


def test_command_sender_stub_exists():  # S7-0306
    assert os.path.exists(os.path.join(FRONTEND_SRC, "transport", "command-sender.js"))


def test_store_reducer_stub_exists():  # S7-0306
    assert os.path.exists(os.path.join(FRONTEND_SRC, "store", "reducer.js"))


def test_store_types_stub_exists():  # S7-0306
    assert os.path.exists(os.path.join(FRONTEND_SRC, "store", "types.js"))


def test_store_selectors_stub_exists():  # S7-0306
    assert os.path.exists(os.path.join(FRONTEND_SRC, "store", "selectors.js"))


def test_commands_builder_stub_exists():  # S7-0306
    assert os.path.exists(os.path.join(FRONTEND_SRC, "commands", "command-builder.js"))


def test_commands_validation_stub_exists():  # S7-0306
    assert os.path.exists(os.path.join(FRONTEND_SRC, "commands", "validation.js"))


def test_test_utils_render_stub_exists():  # S7-0306
    assert os.path.exists(os.path.join(FRONTEND_SRC, "test-utils", "render.js"))


# ---------------------------------------------------------------------------
# No backend imports in frontend/src — S7-0306 architecture boundary
# ---------------------------------------------------------------------------

def _collect_frontend_src_files():
    result = []
    for dirpath, _dirs, files in os.walk(FRONTEND_SRC):
        for fname in files:
            if fname.endswith((".js", ".jsx", ".ts", ".tsx")):
                result.append(os.path.join(dirpath, fname))
    return result


_BACKEND_IMPORT_RE = re.compile(
    r"""(from|import)\s+['"][./]*(?:runtime|agent|server|browser)[/"']"""
)


def test_no_backend_imports_in_frontend_src():  # S7-0306
    violations = []
    for fpath in _collect_frontend_src_files():
        content = open(fpath, encoding="utf-8", errors="ignore").read()
        for lineno, line in enumerate(content.splitlines(), 1):
            if _BACKEND_IMPORT_RE.search(line):
                violations.append(f"{fpath}:{lineno}: {line.strip()}")
    assert not violations, "Backend imports found in frontend/src/:\n" + "\n".join(violations)


def test_no_runtime_import_in_host_stub():  # S7-0306
    host_path = os.path.join(FRONTEND_SRC, "host", "host.jsx")
    if not os.path.exists(host_path):
        pytest.skip("host.jsx not yet created")
    content = open(host_path).read()
    assert "from 'runtime" not in content
    assert 'from "runtime' not in content


def test_no_runtime_import_in_transport_stub():  # S7-0306
    ws_path = os.path.join(FRONTEND_SRC, "transport", "websocket-client.js")
    if not os.path.exists(ws_path):
        pytest.skip("websocket-client.js not yet created")
    content = open(ws_path).read()
    assert "from 'runtime" not in content
    assert 'from "runtime' not in content


# ---------------------------------------------------------------------------
# Stub files are stubs (not full implementations) — S7-0306 boundary
# ---------------------------------------------------------------------------

def test_store_reducer_is_stub_not_full_implementation():  # S7-0306 vs S7-0502
    # S7-0502 complete: reducer is now a full implementation (not a stub)
    reducer_path = os.path.join(FRONTEND_SRC, "store", "reducer.js")
    if not os.path.exists(reducer_path):
        pytest.skip("reducer.js not yet created")
    content = open(reducer_path).read()
    # Full implementation must NOT have the stub marker
    assert "REDUCER_STUB" not in content, "reducer.js must not contain REDUCER_STUB (S7-0502 implemented)"
