"""S5-009 Page Intelligence schema unit tests."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from runtime.page_intelligence_schema import (
    MAX_AMBIGUITY_GROUPS,
    MAX_CANDIDATE_TARGETS,
    MAX_TOKEN_ESTIMATE,
    AmbiguityGroup,
    CandidateTarget,
    PageIntelligenceSchema,
    SourceStats,
    build_page_intelligence_schema,
)

FIXTURES = Path(__file__).parent / "e2e" / "fixtures" / "test_app"


def _load(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


def test_schema_serializes_to_json_dict() -> None:
    schema = build_page_intelligence_schema(
        html=_load("duplicate-profiles.html"),
        url="http://t/duplicate-profiles.html",
        title="Duplicate Profiles Fixture",
    )
    payload = schema.to_dict()
    assert set(payload.keys()) >= {
        "page_summary",
        "sections",
        "candidate_targets",
        "ambiguity_groups",
        "recommended_action",
        "reason",
        "source_stats",
        "warnings",
    }
    # Round-trip through JSON to confirm primitive-safe
    encoded = schema.to_json()
    json.loads(encoded)


def test_schema_is_bounded() -> None:
    schema = build_page_intelligence_schema(
        html=_load("data-table.html"),
        url="http://t/data-table.html",
        title="Data Table Fixture",
    )
    assert len(schema.candidate_targets) <= MAX_CANDIDATE_TARGETS
    assert len(schema.ambiguity_groups) <= MAX_AMBIGUITY_GROUPS
    # Token estimate proxy: serialized JSON length / 4 should fit
    assert len(schema.to_json()) // 4 <= MAX_TOKEN_ESTIMATE


def test_schema_contains_no_raw_html() -> None:
    html = _load("nested-cards.html")
    schema = build_page_intelligence_schema(
        html=html,
        url="http://t/nested-cards.html",
        title="Nested Cards Fixture",
    )
    encoded = schema.to_json()
    # Raw markup must not leak into the schema
    assert "<div" not in encoded
    assert "<button" not in encoded
    assert "<form" not in encoded
    assert "<script" not in encoded


def test_duplicate_profiles_produces_ambiguity_group() -> None:
    schema = build_page_intelligence_schema(
        html=_load("duplicate-profiles.html"),
        url="http://t/dup",
        title="Duplicate Profiles Fixture",
    )
    assert schema.ambiguity_groups, "expected ambiguity from repeated Save/Edit buttons"
    intents = {g.intent for g in schema.ambiguity_groups}
    assert "save" in intents
    assert "edit" in intents
    for group in schema.ambiguity_groups:
        assert len(group.candidate_indices) >= 2
    assert schema.recommended_action == "ask_user"


def test_weak_divs_produces_low_confidence_and_warnings() -> None:
    schema = build_page_intelligence_schema(
        html=_load("weak-divs.html"),
        url="http://t/weak",
        title="Weak Divs Fixture",
    )
    # Weak DOM has no <button> tags so no CTA candidates; the schema must say so
    assert schema.recommended_action == "needs_more_context"
    assert any("weak" in w or "no_candidates" in w for w in schema.warnings)


def test_nested_cards_exposes_section_hierarchy() -> None:
    schema = build_page_intelligence_schema(
        html=_load("nested-cards.html"),
        url="http://t/nested",
        title="Nested Cards Fixture",
    )
    section_text = " ".join(schema.sections).lower()
    assert "order" in section_text or "items" in section_text
    # Buttons inside nested cards must show up as candidate targets
    labels = {c.label.lower() for c in schema.candidate_targets}
    assert "edit" in labels
    assert "add" in labels or "apply" in labels


def test_data_table_lists_row_action_candidates() -> None:
    schema = build_page_intelligence_schema(
        html=_load("data-table.html"),
        url="http://t/table",
        title="Data Table Fixture",
    )
    # Edit/Delete buttons should appear as candidate targets
    labels = {c.label.lower() for c in schema.candidate_targets}
    assert "edit" in labels
    assert "delete" in labels
    # Repeated identical labels across rows must surface as ambiguity
    intents = {g.intent for g in schema.ambiguity_groups}
    assert "edit" in intents
    assert "delete" in intents
    # Source stats sees lots of elements
    assert schema.source_stats.elements_seen >= 5


def test_modal_fixture_marks_dialog_warning() -> None:
    schema = build_page_intelligence_schema(
        html=_load("modal-recovery.html"),
        url="http://t/modal",
        title="Modal Recovery Fixture",
    )
    assert "modal_or_dialog_visible" in schema.warnings


def test_recommended_action_ask_user_on_ambiguity() -> None:
    schema = build_page_intelligence_schema(
        html=_load("duplicate-profiles.html"),
        url="http://t/dup",
        title="Duplicate Profiles Fixture",
    )
    assert schema.recommended_action == "ask_user"
    assert schema.reason in ("ambiguous_candidates", "repeated_sections")


def test_recommended_action_needs_more_context_on_weak_dom() -> None:
    schema = build_page_intelligence_schema(
        html=_load("weak-divs.html"),
        url="http://t/weak",
        title="Weak Divs Fixture",
    )
    assert schema.recommended_action == "needs_more_context"


def test_schema_dataclasses_are_serializable() -> None:
    ct = CandidateTarget(
        label="Save", role="button", section="Billing", locator_hint="data-testid=save", confidence=0.9
    )
    grp = AmbiguityGroup(intent="save", candidate_indices=[0, 1])
    stats = SourceStats(elements_seen=5, candidates_found=3, ambiguous_groups=1, sections_seen=2)
    schema = PageIntelligenceSchema(
        page_summary="t",
        sections=["A"],
        candidate_targets=[ct],
        ambiguity_groups=[grp],
        recommended_action="ask_user",
        reason="ambiguous_candidates",
        source_stats=stats,
        warnings=["w"],
    )
    payload = schema.to_dict()
    assert payload["candidate_targets"][0]["confidence"] == 0.9
    assert payload["ambiguity_groups"][0]["candidate_indices"] == [0, 1]
    assert payload["source_stats"]["candidates_found"] == 3


def test_schema_empty_html_returns_safe_defaults() -> None:
    schema = build_page_intelligence_schema(html="", url="", title="")
    assert schema.recommended_action == "needs_more_context"
    assert schema.candidate_targets == []
    assert schema.source_stats.candidates_found == 0
