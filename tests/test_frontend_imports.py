"""
tests/test_frontend_imports.py

Sprint 7 Cluster 3 — S7-0306: Frontend module import boundary verification.
TDD: written before implementation.
"""
from __future__ import annotations

import os
import re
from collections import defaultdict

import pytest

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
FRONTEND_SRC = os.path.join(REPO_ROOT, "frontend", "src")

_IMPORT_RE = re.compile(r"""(?:^|\n)\s*import\s+.*?from\s+['"]([^'"]+)['"]""")
_REQUIRE_RE = re.compile(r"""require\(['"]([^'"]+)['"]\)""")


def _get_module_imports(fpath: str) -> list[str]:
    content = open(fpath, encoding="utf-8", errors="ignore").read()
    found = _IMPORT_RE.findall(content) + _REQUIRE_RE.findall(content)
    return [f for f in found if f.startswith(".")]


def _module_name(fpath: str) -> str:
    rel = os.path.relpath(fpath, FRONTEND_SRC)
    parts = rel.split(os.sep)
    return parts[0] if len(parts) > 1 else "root"


def _collect_all_src_files():
    result = []
    for dirpath, _dirs, files in os.walk(FRONTEND_SRC):
        for fname in files:
            if fname.endswith((".js", ".jsx")):
                result.append(os.path.join(dirpath, fname))
    return result


# ---------------------------------------------------------------------------
# S7-0306 — No backend imports anywhere in frontend/src/
# ---------------------------------------------------------------------------

_BACKEND_PATTERNS = [
    r"""from\s+['"][./]*runtime""",
    r"""from\s+['"][./]*agent""",
    r"""from\s+['"][./]*server""",
    r"""from\s+['"][./]*browser""",
    r"""require\(['"][./]*runtime""",
]
_BACKEND_RE = re.compile("|".join(_BACKEND_PATTERNS))


def test_no_backend_imports_in_any_src_file():  # S7-0306
    violations = []
    for fpath in _collect_all_src_files():
        content = open(fpath, encoding="utf-8", errors="ignore").read()
        for lineno, line in enumerate(content.splitlines(), 1):
            if _BACKEND_RE.search(line):
                violations.append(f"{fpath}:{lineno}: {line.strip()}")
    assert not violations, "Backend imports in frontend:\n" + "\n".join(violations)


# ---------------------------------------------------------------------------
# S7-0306 — transport/ does not import from components/
# ---------------------------------------------------------------------------

def test_transport_does_not_import_components():  # S7-0306
    transport_dir = os.path.join(FRONTEND_SRC, "transport")
    if not os.path.exists(transport_dir):
        pytest.skip("transport/ not yet created")
    for fname in os.listdir(transport_dir):
        if not fname.endswith((".js", ".jsx")):
            continue
        fpath = os.path.join(transport_dir, fname)
        content = open(fpath).read()
        assert "from '../components" not in content
        assert 'from "../components' not in content


# ---------------------------------------------------------------------------
# S7-0306 — store/ does not import from components/ or transport/
# ---------------------------------------------------------------------------

def test_store_does_not_import_components():  # S7-0306
    store_dir = os.path.join(FRONTEND_SRC, "store")
    if not os.path.exists(store_dir):
        pytest.skip("store/ not yet created")
    for fname in os.listdir(store_dir):
        if not fname.endswith((".js", ".jsx")):
            continue
        fpath = os.path.join(store_dir, fname)
        content = open(fpath).read()
        assert "from '../components" not in content
        assert 'from "../components' not in content


def test_store_does_not_import_transport():  # S7-0306
    store_dir = os.path.join(FRONTEND_SRC, "store")
    if not os.path.exists(store_dir):
        pytest.skip("store/ not yet created")
    for fname in os.listdir(store_dir):
        if not fname.endswith((".js", ".jsx")):
            continue
        fpath = os.path.join(store_dir, fname)
        content = open(fpath).read()
        assert "from '../transport" not in content
        assert 'from "../transport' not in content


# ---------------------------------------------------------------------------
# S7-0306 — commands/ does not import from components/ or transport/
# ---------------------------------------------------------------------------

def test_commands_does_not_import_components():  # S7-0306
    commands_dir = os.path.join(FRONTEND_SRC, "commands")
    if not os.path.exists(commands_dir):
        pytest.skip("commands/ not yet created")
    for fname in os.listdir(commands_dir):
        if not fname.endswith((".js", ".jsx")):
            continue
        fpath = os.path.join(commands_dir, fname)
        content = open(fpath).read()
        assert "from '../components" not in content
        assert 'from "../components' not in content


# ---------------------------------------------------------------------------
# S7-0306 — Stub files export at least one named export or default export
# ---------------------------------------------------------------------------

def test_store_reducer_has_export():  # S7-0306
    path = os.path.join(FRONTEND_SRC, "store", "reducer.js")
    if not os.path.exists(path):
        pytest.skip("reducer.js not yet created")
    content = open(path).read()
    assert "export" in content, "reducer.js must have at least one export"


def test_store_types_has_export():  # S7-0306
    path = os.path.join(FRONTEND_SRC, "store", "types.js")
    if not os.path.exists(path):
        pytest.skip("types.js not yet created")
    content = open(path).read()
    assert "export" in content, "types.js must have at least one export"


def test_store_selectors_has_export():  # S7-0306
    path = os.path.join(FRONTEND_SRC, "store", "selectors.js")
    if not os.path.exists(path):
        pytest.skip("selectors.js not yet created")
    content = open(path).read()
    assert "export" in content, "selectors.js must have at least one export"


def test_command_builder_has_export():  # S7-0306
    path = os.path.join(FRONTEND_SRC, "commands", "command-builder.js")
    if not os.path.exists(path):
        pytest.skip("command-builder.js not yet created")
    content = open(path).read()
    assert "export" in content, "command-builder.js must have at least one export"


def test_transport_websocket_client_has_export():  # S7-0306
    path = os.path.join(FRONTEND_SRC, "transport", "websocket-client.js")
    if not os.path.exists(path):
        pytest.skip("websocket-client.js not yet created")
    content = open(path).read()
    assert "export" in content, "websocket-client.js must have at least one export"


# ---------------------------------------------------------------------------
# S7-0306 — No circular imports between modules (basic check)
# ---------------------------------------------------------------------------

def _build_import_graph():
    graph = defaultdict(set)
    for fpath in _collect_all_src_files():
        module = _module_name(fpath)
        for imp in _get_module_imports(fpath):
            abs_imp = os.path.normpath(os.path.join(os.path.dirname(fpath), imp))
            target_module = _module_name(abs_imp)
            if target_module != module and target_module != "root":
                graph[module].add(target_module)
    return dict(graph)


def _has_cycle(graph, start, visited=None, stack=None):
    if visited is None:
        visited = set()
    if stack is None:
        stack = set()
    visited.add(start)
    stack.add(start)
    for neighbor in graph.get(start, []):
        if neighbor not in visited:
            if _has_cycle(graph, neighbor, visited, stack):
                return True
        elif neighbor in stack:
            return True
    stack.remove(start)
    return False


def test_no_circular_imports_between_modules():  # S7-0306
    graph = _build_import_graph()
    cycles = []
    for module in graph:
        if _has_cycle(graph, module):
            cycles.append(module)
    assert not cycles, f"Circular imports detected involving modules: {cycles}"
