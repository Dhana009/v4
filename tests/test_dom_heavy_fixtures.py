"""S5-011 DOM-heavy fixture page structure tests.

Asserts presence + DOM-heavy traits of the new local fixture pages used by
S5-009/S5-010 Page Intelligence work. No network, no LLM, no browser.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

FIXTURES_DIR = Path(__file__).parent / "e2e" / "fixtures" / "test_app"

WEAK_DIVS = FIXTURES_DIR / "weak-divs.html"
DUPLICATE_PROFILES = FIXTURES_DIR / "duplicate-profiles.html"
NESTED_CARDS = FIXTURES_DIR / "nested-cards.html"
DATA_TABLE = FIXTURES_DIR / "data-table.html"
MODAL_RECOVERY = FIXTURES_DIR / "modal-recovery.html"

ALL_FIXTURES = [WEAK_DIVS, DUPLICATE_PROFILES, NESTED_CARDS, DATA_TABLE, MODAL_RECOVERY]


@pytest.mark.parametrize("path", ALL_FIXTURES)
def test_fixture_file_exists(path: Path) -> None:
    assert path.is_file(), f"Fixture page missing: {path}"


@pytest.mark.parametrize("path", ALL_FIXTURES)
def test_fixture_is_local_no_external_assets(path: Path) -> None:
    text = path.read_text(encoding="utf-8")
    assert "<script src=\"http" not in text
    assert "<link rel=\"stylesheet\" href=\"http" not in text
    assert "src=\"//" not in text
    assert "href=\"//" not in text


@pytest.mark.parametrize("path", ALL_FIXTURES)
def test_fixture_has_doctype_and_title(path: Path) -> None:
    text = path.read_text(encoding="utf-8")
    assert text.lstrip().lower().startswith("<!doctype html>")
    assert "<title>" in text


def test_weak_divs_has_no_semantic_anchors_on_pseudo_buttons() -> None:
    text = WEAK_DIVS.read_text(encoding="utf-8")
    # Pseudo-buttons are .pill divs with no role, aria-label, or data-testid
    assert "class=\"pill\"" in text
    # Pill elements should not carry any of these semantic anchors
    pill_block = re.findall(r"<div class=\"pill\"[^>]*>", text)
    assert pill_block, "expected pill divs"
    for el in pill_block:
        assert "role=" not in el
        assert "aria-label=" not in el
        assert "data-testid=" not in el


def test_weak_divs_has_repeated_identical_button_text() -> None:
    text = WEAK_DIVS.read_text(encoding="utf-8")
    assert text.count(">Action<") >= 3
    assert text.count(">Continue<") >= 3


def test_duplicate_profiles_has_at_least_three_profile_sections() -> None:
    text = DUPLICATE_PROFILES.read_text(encoding="utf-8")
    assert len(re.findall(r"<h2>Profile</h2>", text)) >= 3


def test_duplicate_profiles_repeats_save_and_edit_buttons() -> None:
    text = DUPLICATE_PROFILES.read_text(encoding="utf-8")
    assert text.count(">Save</button>") >= 3
    assert text.count(">Edit</button>") >= 3


def test_nested_cards_has_three_or_more_levels() -> None:
    text = NESTED_CARDS.read_text(encoding="utf-8")
    assert "data-testid=\"outer-card\"" in text
    assert "data-testid=\"inner-card-items\"" in text
    assert "data-testid=\"deep-card\"" in text


def test_nested_cards_has_semantic_form_anchors() -> None:
    text = NESTED_CARDS.read_text(encoding="utf-8")
    assert "aria-label=\"Add item\"" in text
    assert "aria-label=\"Apply discount\"" in text
    assert text.count("<form ") >= 2


def test_data_table_has_table_and_list_structures() -> None:
    text = DATA_TABLE.read_text(encoding="utf-8")
    assert "<table" in text
    assert "<thead>" in text
    assert text.count("<tr ") >= 5
    assert "<ul " in text
    assert text.count("<li>") >= 5


def test_data_table_rows_have_distinguishable_aria_labels() -> None:
    text = DATA_TABLE.read_text(encoding="utf-8")
    # Each row's action buttons get a per-user aria-label
    for name in ("Alice", "Bob", "Carol", "Dan", "Eve"):
        assert f"aria-label=\"Edit {name}\"" in text
        assert f"aria-label=\"Delete {name}\"" in text


def test_modal_recovery_has_dialog_role_and_open_toggle() -> None:
    text = MODAL_RECOVERY.read_text(encoding="utf-8")
    assert text.count("role=\"dialog\"") >= 2
    assert "classList.add('open')" in text
    assert "classList.remove('open')" in text


def test_modal_recovery_modals_start_hidden() -> None:
    text = MODAL_RECOVERY.read_text(encoding="utf-8")
    # Backdrop defaults to display: none and only `.open` class shows it
    assert "display: none" in text
    assert ".backdrop.open" in text
