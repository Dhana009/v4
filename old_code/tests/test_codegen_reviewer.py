"""Unit tests for runtime.codegen_reviewer."""
from __future__ import annotations

import pytest

from runtime.codegen_reviewer import review_playwright_code


# ---------------------------------------------------------------------------
# 1. brittle_xpath fires on //div
# ---------------------------------------------------------------------------

def test_brittle_xpath_fires() -> None:
    code = 'element = page.locator("//div[@id=\'main\']/button[1]")\n'
    review = review_playwright_code(code)
    rules = [i.rule for i in review.issues]
    assert "brittle_xpath" in rules


# ---------------------------------------------------------------------------
# 2. missing_await fires when no 'await page.' in async def
# ---------------------------------------------------------------------------

def test_missing_await_fires_in_async_def() -> None:
    code = (
        "async def test_login(page):\n"
        "    x = 1 + 1\n"
        "    return x\n"
    )
    review = review_playwright_code(code)
    rules = [i.rule for i in review.issues]
    assert "missing_await" in rules


# ---------------------------------------------------------------------------
# 3. password literal triggers error
# ---------------------------------------------------------------------------

def test_password_literal_triggers_error() -> None:
    code = 'password = "supersecret123"\n'
    review = review_playwright_code(code)
    errors = [i for i in review.issues if i.rule == "password_in_source"]
    assert len(errors) >= 1
    assert errors[0].severity == "error"


# ---------------------------------------------------------------------------
# 4. Non-issue code scores 100
# ---------------------------------------------------------------------------

def test_clean_code_scores_100() -> None:
    code = (
        "async def test_login(page):\n"
        "    await page.goto(BASE_URL)\n"
        "    await page.get_by_role('button', name='Login').click()\n"
        "    await page.wait_for_url('**/dashboard')\n"
    )
    review = review_playwright_code(code)
    assert review.score == 100
    assert review.issues == []


# ---------------------------------------------------------------------------
# 5. Summary string format includes score, errors, warns, infos
# ---------------------------------------------------------------------------

def test_summary_string_format() -> None:
    code = 'el = page.locator("//button")\n'
    review = review_playwright_code(code)
    assert "score=" in review.summary
    assert "errors" in review.summary
    assert "warns" in review.summary
    assert "infos" in review.summary


# ---------------------------------------------------------------------------
# 6. Unknown ruleset raises ValueError
# ---------------------------------------------------------------------------

def test_unknown_ruleset_raises() -> None:
    with pytest.raises(ValueError, match="Unknown ruleset"):
        review_playwright_code("x = 1", ruleset="nonexistent")


# ---------------------------------------------------------------------------
# 7. Score is reduced for each issue found
# ---------------------------------------------------------------------------

def test_score_reduced_for_issues() -> None:
    # password_in_source carries weight 20
    code = 'password = "hunter2"\n'
    review = review_playwright_code(code)
    assert review.score <= 80
