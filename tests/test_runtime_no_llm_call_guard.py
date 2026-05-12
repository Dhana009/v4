"""
tests/test_runtime_no_llm_call_guard.py

Expanded no-LLM-call guard: scans ALL runtime/*.py modules.

Requirement: No runtime module may import or call live LLM/provider APIs
directly (AsyncOpenAI, OpenAI, anthropic client, chat.completions,
responses.create, LLMClient direct call).

All LLM calls must go through LLMRuntimeController via the purpose registry.

Allowlist:
- runtime/llm_runtime_controller.py  — owns the controller boundary; references
  model_router and purpose-registry but does NOT call the provider directly.
- runtime/model_router.py            — routes by model_class; is called by the
  controller, not a public bypass.
- runtime/llm_policy_registry.py     — policy metadata only; no network calls.
- runtime/llm_purpose_policy.py      — policy dataclasses; no network calls.
- runtime/llm_policy_gateway.py      — gateway contract; validated separately.
- runtime/llm_controller.py          — legacy thin-wrapper; separately classified.

Any match outside this allowlist is a hard failure.
"""
from __future__ import annotations

import pathlib
import re

import pytest

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

RUNTIME_DIR = pathlib.Path(__file__).resolve().parents[1] / "runtime"

# Patterns that indicate a direct live LLM/provider API call.
# These are forbidden in runtime modules (except those in ALLOWLIST).
FORBIDDEN_PATTERNS: list[tuple[str, str]] = [
    (r"^\s*(?:from\s+openai\b|import\s+openai\b)", "openai direct import"),
    (r"^\s*(?:from\s+openai\s+import|import\s+openai\s+import)\s+.*\bAsyncOpenAI\b", "AsyncOpenAI direct import"),
    (r"\bAsyncOpenAI\s*\(", "AsyncOpenAI direct client instantiation"),
    (r"^\s*(?:from\s+openai\s+import|import\s+openai)\b", "openai module import"),
    (r"chat\.completions\.create\s*\(", "chat.completions.create direct call"),
    (r"responses\.create\s*\(", "responses.create direct call"),
    (r"^\s*import\s+anthropic\b", "anthropic direct import"),
    (r"^\s*from\s+anthropic\b", "anthropic direct import (from)"),
    (r"\bAnthropic\s*\(\)", "Anthropic() direct client instantiation"),
]

# Modules that are structurally part of the LLM dispatch path and are
# explicitly reviewed; they do NOT bypass the purpose-registry contract.
ALLOWLIST: frozenset[str] = frozenset({
    "llm_runtime_controller.py",  # owns controller boundary
    "model_router.py",             # called by controller, not a bypass
    "llm_policy_registry.py",      # policy metadata; no network
    "llm_purpose_policy.py",       # policy dataclasses; no network
    "llm_policy_gateway.py",       # gateway contract; tested separately
    "llm_controller.py",           # legacy wrapper; classified separately
})


# ---------------------------------------------------------------------------
# Collect all runtime modules
# ---------------------------------------------------------------------------

def _all_runtime_modules() -> list[pathlib.Path]:
    modules = [
        p for p in sorted(RUNTIME_DIR.glob("*.py"))
        if p.name != "__init__.py"
        and p.name not in ALLOWLIST
    ]
    return modules


# ---------------------------------------------------------------------------
# Parametrised guard: one test per module
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("module_path", _all_runtime_modules(), ids=lambda p: p.name)
def test_runtime_module_has_no_direct_llm_call(module_path: pathlib.Path):
    """
    Each runtime module (outside the explicit allowlist) must not contain
    patterns that indicate a direct live LLM/provider API call.
    """
    source = module_path.read_text(encoding="utf-8")
    violations: list[str] = []
    for pattern, description in FORBIDDEN_PATTERNS:
        if re.search(pattern, source, re.MULTILINE):
            violations.append(
                f"  FORBIDDEN [{description}]: pattern `{pattern}` matched in {module_path.name}"
            )
    if violations:
        pytest.fail(
            f"Direct LLM/provider API call detected in runtime module {module_path.name}:\n"
            + "\n".join(violations)
            + "\n\nAll LLM calls must go through LLMRuntimeController via the purpose registry."
        )


# ---------------------------------------------------------------------------
# Coverage count guard: confirm we are scanning all non-init, non-allow modules
# ---------------------------------------------------------------------------

def test_guard_covers_minimum_module_count():
    """
    Guard must scan at least 60 runtime modules (72 total - 1 __init__ - 6 allowlist - buffer).
    This ensures the guard itself does not silently shrink.
    """
    modules = _all_runtime_modules()
    assert len(modules) >= 60, (
        f"Expected to scan at least 60 runtime modules; only found {len(modules)}. "
        "Check if ALLOWLIST or RUNTIME_DIR is misconfigured."
    )


def test_allowlist_is_minimal():
    """Allowlist must remain small and explicit — no unbounded wildcards."""
    assert len(ALLOWLIST) <= 10, (
        f"Allowlist has {len(ALLOWLIST)} entries — review whether entries are still justified."
    )


def test_allowlist_modules_all_exist():
    """Every module in the allowlist must actually exist in runtime/."""
    for name in ALLOWLIST:
        p = RUNTIME_DIR / name
        assert p.exists(), f"Allowlist entry {name} does not exist in runtime/"
