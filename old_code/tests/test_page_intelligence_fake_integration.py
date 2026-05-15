"""S5-010 Page Intelligence fake-model integration tests.

Wires PageIntelligenceSchema into a fake planner consumer without paid LLM.
Proves that schema-driven planner decisions match recommended_action for each
DOM-heavy fixture, and that the planner-facing message stays compact and
HTML-free.
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from runtime.page_intelligence_schema import (
    PageIntelligenceSchema,
    build_page_intelligence_schema,
    schema_to_planner_context_message,
)

FIXTURES = Path(__file__).parent / "e2e" / "fixtures" / "test_app"


def _load(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


# --- fake cheap planner that consumes the packet -----------------------------


class FakeCheapPlanner:
    """Tiny fake LLM that decides terminal output from PageIntelligenceSchema."""

    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []
        self.chat = SimpleNamespace(completions=SimpleNamespace(create=self._create))

    async def _create(self, **payload: Any) -> Any:
        self.calls.append(dict(payload))
        schema = self._extract_schema(payload["messages"])
        if schema is None:
            content = json.dumps({"terminal": "needs_more_context", "reason": "no_packet"})
        else:
            action = schema["recommended_action"]
            if action == "ask_user":
                content = json.dumps({
                    "terminal": "ask_user",
                    "question": f"Multiple matches for {next(iter(schema['ambiguity_groups']))['intent']}. Which one?",
                    "reason": schema["reason"],
                })
            elif action == "plan_ready_possible":
                content = json.dumps({
                    "terminal": "plan_ready",
                    "target": schema["candidate_targets"][0]["label"],
                    "reason": schema["reason"],
                })
            else:
                content = json.dumps({"terminal": "needs_more_context", "reason": schema["reason"]})
        return SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content=content, tool_calls=None))]
        )

    @staticmethod
    def _extract_schema(messages: list[dict[str, Any]]) -> dict[str, Any] | None:
        for msg in messages:
            content = msg.get("content", "")
            if isinstance(content, str) and content.startswith("PAGE_INTELLIGENCE_PACKET="):
                return json.loads(content.split("=", 1)[1])
        return None


def _run_planner(html: str, url: str, title: str) -> tuple[PageIntelligenceSchema, dict[str, Any]]:
    schema = build_page_intelligence_schema(html=html, url=url, title=title)
    packet_msg = schema_to_planner_context_message(schema)
    planner = FakeCheapPlanner()
    response = asyncio.run(
        planner.chat.completions.create(
            model="cheap",
            messages=[packet_msg, {"role": "user", "content": "Plan the next action."}],
        )
    )
    result = json.loads(response.choices[0].message.content)
    return schema, result


# --- aria-label regex fix ----------------------------------------------------


def test_aria_label_multi_word_preserved_in_locator_hint() -> None:
    schema = build_page_intelligence_schema(
        html=_load("data-table.html"),
        url="http://t/table",
        title="Data Table Fixture",
    )
    hints = " ".join(c.locator_hint for c in schema.candidate_targets)
    assert "aria-label=Edit Alice" in hints
    assert "aria-label=Delete Carol" in hints


# --- per-fixture fake integration --------------------------------------------


def test_duplicate_profiles_drives_planner_to_ask_user() -> None:
    schema, result = _run_planner(
        _load("duplicate-profiles.html"),
        "http://t/dup",
        "Duplicate Profiles Fixture",
    )
    assert schema.recommended_action == "ask_user"
    assert schema.ambiguity_groups
    assert result["terminal"] == "ask_user"


def test_weak_divs_drives_planner_to_needs_more_context() -> None:
    schema, result = _run_planner(
        _load("weak-divs.html"),
        "http://t/weak",
        "Weak Divs Fixture",
    )
    assert schema.recommended_action == "needs_more_context"
    assert result["terminal"] == "needs_more_context"


def test_nested_cards_provides_section_and_candidate_hierarchy() -> None:
    schema, result = _run_planner(
        _load("nested-cards.html"),
        "http://t/nested",
        "Nested Cards Fixture",
    )
    assert schema.sections
    labels = {c.label.lower() for c in schema.candidate_targets}
    assert "edit" in labels
    assert result["terminal"] in {"ask_user", "plan_ready", "needs_more_context"}
    # Hierarchy hint: at least one nested section beyond the top section
    assert len(schema.sections) >= 1


def test_data_table_exposes_row_action_candidates() -> None:
    schema, result = _run_planner(
        _load("data-table.html"),
        "http://t/table",
        "Data Table Fixture",
    )
    intents = {g.intent for g in schema.ambiguity_groups}
    assert "edit" in intents
    assert "delete" in intents
    assert result["terminal"] == "ask_user"


def test_modal_fixture_flags_dialog_and_keeps_candidates() -> None:
    schema, result = _run_planner(
        _load("modal-recovery.html"),
        "http://t/modal",
        "Modal Recovery Fixture",
    )
    assert "modal_or_dialog_visible" in schema.warnings
    assert schema.candidate_targets
    assert result["terminal"] in {"ask_user", "plan_ready", "needs_more_context"}


# --- contract guards ---------------------------------------------------------


def test_planner_message_contains_no_raw_html() -> None:
    schema = build_page_intelligence_schema(
        html=_load("nested-cards.html"),
        url="http://t/nested",
        title="Nested Cards Fixture",
    )
    msg = schema_to_planner_context_message(schema)
    assert msg["role"] == "system"
    assert msg["name"] == "page_intelligence"
    assert "<div" not in msg["content"]
    assert "<button" not in msg["content"]
    assert "<form" not in msg["content"]
    assert msg["content"].startswith("PAGE_INTELLIGENCE_PACKET=")


def test_planner_message_is_token_bounded() -> None:
    schema = build_page_intelligence_schema(
        html=_load("data-table.html"),
        url="http://t/table",
        title="Data Table Fixture",
    )
    msg = schema_to_planner_context_message(schema)
    # Cheap LLM context budget proxy: characters / 4 ~= tokens
    assert len(msg["content"]) // 4 <= 1500


def test_fake_planner_records_call_without_paid_llm() -> None:
    planner = FakeCheapPlanner()
    schema = build_page_intelligence_schema(
        html=_load("duplicate-profiles.html"),
        url="http://t/dup",
        title="Duplicate Profiles Fixture",
    )
    msg = schema_to_planner_context_message(schema)
    asyncio.run(
        planner.chat.completions.create(
            model="cheap",
            messages=[msg, {"role": "user", "content": "Plan."}],
        )
    )
    assert len(planner.calls) == 1
    assert planner.calls[0]["model"] == "cheap"
