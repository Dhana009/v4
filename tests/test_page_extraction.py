"""
tests/test_page_extraction.py

Tests for S6-0302: Deterministic page/section extraction completeness.
"""
from __future__ import annotations

import pytest
from runtime.page_extraction import (
    PageExtractionResult,
    extract_page_structure,
)


def _semantic_page():
    return {
        "url": "https://example.com/login",
        "title": "Login",
        "headings": [{"level": 1, "text": "Sign In"}, {"level": 2, "text": "Enter Credentials"}],
        "buttons": [{"text": "Login", "aria_label": "Login button", "visible": True}],
        "forms": [{"fields": [
            {"type": "text", "name": "username", "label": "Username", "placeholder": "Enter username"},
            {"type": "password", "name": "password", "label": "Password", "placeholder": "Enter password"},
        ]}],
        "links": [{"text": "Forgot password?", "href": "/forgot"}],
        "landmarks": [{"role": "main", "label": "Main content"}],
    }


def _weak_page():
    return {
        "url": "https://example.com/weak",
        "title": "Page",
        "headings": [],
        "buttons": [
            {"text": "div_btn", "tag": "div", "visible": True},
            {"text": "span_btn", "tag": "span", "visible": True},
        ],
        "forms": [],
        "links": [],
        "landmarks": [],
    }


# ---------------------------------------------------------------------------
# Unit tests
# ---------------------------------------------------------------------------

def test_extracts_headings_from_semantic_fixture():
    result = extract_page_structure(_semantic_page())
    assert len(result.headings) >= 1
    assert any(h["text"] == "Sign In" for h in result.headings)


def test_extracts_buttons_from_semantic_fixture():
    result = extract_page_structure(_semantic_page())
    assert len(result.buttons) >= 1
    assert any(b["text"] == "Login" for b in result.buttons)


def test_extracts_forms_from_semantic_fixture():
    result = extract_page_structure(_semantic_page())
    assert len(result.forms) >= 1


def test_extracts_landmarks_from_semantic_fixture():
    result = extract_page_structure(_semantic_page())
    assert isinstance(result.landmarks, list)


def test_extracts_weak_div_span_candidates():
    result = extract_page_structure(_weak_page())
    assert isinstance(result.buttons, list)


def test_detects_duplicate_buttons():
    page = {
        "url": "https://example.com",
        "title": "T",
        "headings": [],
        "buttons": [
            {"text": "Submit", "visible": True},
            {"text": "Submit", "visible": True},
        ],
        "forms": [], "links": [], "landmarks": [],
    }
    result = extract_page_structure(page)
    assert result.has_duplicates is True


def test_semantic_quality_score_high_for_semantic_page():
    result = extract_page_structure(_semantic_page())
    assert result.semantic_quality_score >= 50


def test_semantic_quality_score_low_for_weak_page():
    result = extract_page_structure(_weak_page())
    assert result.semantic_quality_score <= 60


def test_risk_flags_empty_for_clean_page():
    result = extract_page_structure(_semantic_page())
    assert isinstance(result.risk_flags, list)


def test_output_is_bounded():
    # 30 buttons — should be capped
    page = {
        "url": "https://example.com",
        "title": "T",
        "headings": [],
        "buttons": [{"text": f"btn{i}", "visible": True} for i in range(30)],
        "forms": [], "links": [], "landmarks": [],
    }
    result = extract_page_structure(page)
    assert len(result.buttons) <= 20  # bounded at 20


def test_result_is_typed():
    result = extract_page_structure(_semantic_page())
    assert isinstance(result, PageExtractionResult)
    assert hasattr(result, "headings")
    assert hasattr(result, "buttons")
    assert hasattr(result, "forms")
    assert hasattr(result, "semantic_quality_score")
    assert hasattr(result, "risk_flags")
    assert hasattr(result, "has_duplicates")


# ---------------------------------------------------------------------------
# Contract tests
# ---------------------------------------------------------------------------

def test_extraction_is_deterministic():
    page = _semantic_page()
    r1 = extract_page_structure(page)
    r2 = extract_page_structure(page)
    assert r1.semantic_quality_score == r2.semantic_quality_score
    assert r1.headings == r2.headings


def test_output_bounded_per_category():
    page = {
        "url": "https://example.com",
        "title": "T",
        "headings": [{"level": 1, "text": f"H{i}"} for i in range(50)],
        "buttons": [], "forms": [], "links": [], "landmarks": [],
    }
    result = extract_page_structure(page)
    # Headings bounded too
    assert len(result.headings) <= 30
