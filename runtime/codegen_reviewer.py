"""
codegen_reviewer.py — Deterministic Playwright code reviewer (PRD 07 §3 / DG1 G11).

Pure heuristic ruleset; no I/O, stdlib only.
LLM-backed variant routes through controller.call(purpose="codegen_reviewer")
in a follow-up wire-in slice.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Literal


# ---------------------------------------------------------------------------
# Public data contracts
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class CodegenIssue:
    severity: Literal["info", "warn", "error"]
    rule: str
    line: int
    message: str
    suggestion: str | None = None


@dataclass(frozen=True)
class CodegenReview:
    score: int          # 0-100; higher is better
    issues: list[CodegenIssue]
    summary: str


# ---------------------------------------------------------------------------
# Rule weights
# ---------------------------------------------------------------------------

_RULE_WEIGHTS: dict[str, int] = {
    "brittle_xpath":                 8,
    "absolute_position_selector":    5,
    "missing_await":                15,
    "hard_coded_sleep":             10,
    "bare_click_without_assertion":  3,
    "password_in_source":           20,
    "missing_storage_state":         2,
    "non_idiomatic_getByText":       2,
}

# ---------------------------------------------------------------------------
# Individual rule checkers
# Each returns a (possibly empty) list[CodegenIssue].
# ---------------------------------------------------------------------------

# Rule 1 — brittle_xpath
_RE_XPATH = re.compile(r"//")

def _check_brittle_xpath(lines: list[str]) -> list[CodegenIssue]:
    issues: list[CodegenIssue] = []
    for lineno, text in enumerate(lines, start=1):
        if _RE_XPATH.search(text):
            issues.append(CodegenIssue(
                severity="warn",
                rule="brittle_xpath",
                line=lineno,
                message="XPath selector ('//') is brittle and ties tests to DOM structure.",
                suggestion="Use page.get_by_role(), get_by_label(), or get_by_text() instead.",
            ))
    return issues


# Rule 2 — absolute_position_selector  (nth(N) where N > 5)
_RE_NTH = re.compile(r"\.nth\(\s*(\d+)\s*\)")

def _check_absolute_position_selector(lines: list[str]) -> list[CodegenIssue]:
    issues: list[CodegenIssue] = []
    for lineno, text in enumerate(lines, start=1):
        for m in _RE_NTH.finditer(text):
            n = int(m.group(1))
            if n > 5:
                issues.append(CodegenIssue(
                    severity="warn",
                    rule="absolute_position_selector",
                    line=lineno,
                    message=f"nth({n}) relies on absolute DOM position which breaks on layout changes.",
                    suggestion="Use a unique role, label, or test-id attribute instead.",
                ))
    return issues


# Rule 3 — missing_await
# Fires once per async function that contains no `await page.` call.
_RE_ASYNC_DEF = re.compile(r"^\s*async\s+def\s+\w+")
_RE_AWAIT_PAGE = re.compile(r"\bawait[ \t]+page\.")

def _check_missing_await(lines: list[str]) -> list[CodegenIssue]:
    issues: list[CodegenIssue] = []
    i = 0
    while i < len(lines):
        if _RE_ASYNC_DEF.match(lines[i]):
            fn_start = i + 1  # 1-indexed line of the def
            fn_def_lineno = i + 1
            # Collect body lines: everything indented deeper than the def line.
            def_indent = len(lines[i]) - len(lines[i].lstrip())
            body: list[str] = []
            j = i + 1
            while j < len(lines):
                stripped = lines[j].rstrip()
                if stripped == "":
                    body.append(lines[j])
                    j += 1
                    continue
                cur_indent = len(lines[j]) - len(lines[j].lstrip())
                if cur_indent > def_indent:
                    body.append(lines[j])
                    j += 1
                else:
                    break
            body_text = "\n".join(body)
            if not _RE_AWAIT_PAGE.search(body_text):
                issues.append(CodegenIssue(
                    severity="error",
                    rule="missing_await",
                    line=fn_def_lineno,
                    message="async function does not contain any 'await page.' call; Playwright calls must be awaited.",
                    suggestion="Add 'await' before each Playwright action (e.g. await page.goto(...)).",
                ))
            i = j
        else:
            i += 1
    return issues


# Rule 4 — hard_coded_sleep
# time.sleep(<n>) or page.wait_for_timeout(<n>) where n > 5000
_RE_SLEEP = re.compile(
    r"(?:time\.sleep\(\s*([0-9]*\.?[0-9]+)\s*\)|page\.wait_for_timeout\(\s*([0-9]+)\s*\))"
)

def _check_hard_coded_sleep(lines: list[str]) -> list[CodegenIssue]:
    issues: list[CodegenIssue] = []
    for lineno, text in enumerate(lines, start=1):
        for m in _RE_SLEEP.finditer(text):
            raw = m.group(1) or m.group(2)
            try:
                val = float(raw)
            except ValueError:
                continue
            # time.sleep uses seconds; page.wait_for_timeout uses milliseconds.
            if m.group(1) is not None:
                # time.sleep — convert seconds → ms for comparison
                effective_ms = val * 1000
            else:
                effective_ms = val
            if effective_ms > 5000:
                issues.append(CodegenIssue(
                    severity="warn",
                    rule="hard_coded_sleep",
                    line=lineno,
                    message=f"Hard-coded sleep/wait of {val} (effective {effective_ms:.0f} ms) makes tests slow and flaky.",
                    suggestion="Use page.wait_for_selector(), page.wait_for_load_state(), or expect().to_be_visible().",
                ))
    return issues


# Rule 5 — bare_click_without_assertion (within next 5 lines)
_RE_CLICK = re.compile(r"\bpage\.click\s*\(")
_RE_EXPECT = re.compile(r"\bexpect\s*\(")

def _check_bare_click_without_assertion(lines: list[str]) -> list[CodegenIssue]:
    issues: list[CodegenIssue] = []
    n = len(lines)
    for lineno, text in enumerate(lines, start=1):
        if _RE_CLICK.search(text):
            window = lines[lineno : lineno + 5]  # next 5 lines (0-indexed slice)
            if not any(_RE_EXPECT.search(l) for l in window):
                issues.append(CodegenIssue(
                    severity="info",
                    rule="bare_click_without_assertion",
                    line=lineno,
                    message="page.click() is not followed by an expect() assertion within 5 lines.",
                    suggestion="Add expect(page.locator(...)).to_be_visible() after the click to verify the outcome.",
                ))
    return issues


# Rule 6 — password_in_source
_RE_PASSWORD = re.compile(r'(?:password\s*=\s*[\'"][^\'"]{1,}[\'"]|Bearer\s+[A-Za-z0-9\-_.~+/]+=*)')

def _check_password_in_source(lines: list[str]) -> list[CodegenIssue]:
    issues: list[CodegenIssue] = []
    for lineno, text in enumerate(lines, start=1):
        if _RE_PASSWORD.search(text):
            issues.append(CodegenIssue(
                severity="error",
                rule="password_in_source",
                line=lineno,
                message="Hard-coded credential (password= or Bearer token) found in source.",
                suggestion="Use environment variables or a secrets manager; never commit credentials.",
            ))
    return issues


# Rule 7 — missing_storage_state
_RE_LAUNCH = re.compile(r"chromium\.launch\s*\(")
_RE_STORAGE_STATE = re.compile(r"storage_state\s*=")

def _check_missing_storage_state(lines: list[str]) -> list[CodegenIssue]:
    issues: list[CodegenIssue] = []
    for lineno, text in enumerate(lines, start=1):
        if _RE_LAUNCH.search(text) and not _RE_STORAGE_STATE.search(text):
            issues.append(CodegenIssue(
                severity="info",
                rule="missing_storage_state",
                line=lineno,
                message="chromium.launch() does not include storage_state= argument.",
                suggestion="Pass storage_state= to reuse authentication cookies and speed up tests.",
            ))
    return issues


# Rule 8 — non_idiomatic_getByText
_RE_TEXT_LOCATOR = re.compile(r'page\.locator\(\s*["\']text=')

def _check_non_idiomatic_get_by_text(lines: list[str]) -> list[CodegenIssue]:
    issues: list[CodegenIssue] = []
    for lineno, text in enumerate(lines, start=1):
        if _RE_TEXT_LOCATOR.search(text):
            issues.append(CodegenIssue(
                severity="info",
                rule="non_idiomatic_getByText",
                line=lineno,
                message="page.locator(\"text=\") is the legacy text selector syntax.",
                suggestion="Use page.get_by_text('...') for cleaner, more idiomatic Playwright code.",
            ))
    return issues


# ---------------------------------------------------------------------------
# Ordered ruleset registry
# ---------------------------------------------------------------------------

_RULESETS: dict[str, list] = {
    "default": [
        _check_brittle_xpath,
        _check_absolute_position_selector,
        _check_missing_await,
        _check_hard_coded_sleep,
        _check_bare_click_without_assertion,
        _check_password_in_source,
        _check_missing_storage_state,
        _check_non_idiomatic_get_by_text,
    ]
}


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def review_playwright_code(code: str, *, ruleset: str = "default") -> CodegenReview:
    """Review *code* (a Playwright Python script) and return a CodegenReview.

    Parameters
    ----------
    code:
        Full source text of the Playwright test/script.
    ruleset:
        Named ruleset to apply.  Only ``"default"`` is defined today.

    Returns
    -------
    CodegenReview
        Immutable review result with score, issues, and summary string.
    """
    checkers = _RULESETS.get(ruleset)
    if checkers is None:
        raise ValueError(f"Unknown ruleset {ruleset!r}. Available: {list(_RULESETS)}")

    lines = code.splitlines()

    all_issues: list[CodegenIssue] = []
    for checker in checkers:
        all_issues.extend(checker(lines))

    # Deduplicate by (rule, line) — take first occurrence
    seen: set[tuple[str, int]] = set()
    deduped: list[CodegenIssue] = []
    for issue in all_issues:
        key = (issue.rule, issue.line)
        if key not in seen:
            seen.add(key)
            deduped.append(issue)

    # Score
    penalty = sum(_RULE_WEIGHTS.get(i.rule, 0) for i in deduped)
    score = max(0, 100 - penalty)

    # Summary
    errors = sum(1 for i in deduped if i.severity == "error")
    warns  = sum(1 for i in deduped if i.severity == "warn")
    infos  = sum(1 for i in deduped if i.severity == "info")
    summary = f"score={score}, {errors} errors, {warns} warns, {infos} infos"

    return CodegenReview(score=score, issues=deduped, summary=summary)
