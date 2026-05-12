"""S5-009 Page Intelligence LLM-facing schema and contract.

Lean schema that summarizes a DOM-heavy page for a cheap LLM (or fake model).
Built on top of the deterministic `PageIntelligencePacket` so the LLM never
receives raw DOM. Output is advisory only — Step Runner still validates every
locator before action.

Contract:
- Compact (≤1500 token estimate, ≤16 candidate_targets, ≤8 ambiguity_groups).
- Never includes raw HTML or large markup strings.
- recommended_action is a 3-value enum so the planner can decide quickly.
"""

from __future__ import annotations

import json
import re
from collections import defaultdict
from dataclasses import asdict, dataclass, field
from typing import Any, Literal

from runtime.page_intelligence import PageIntelligencePacket, build_page_intelligence_packet


RecommendedAction = Literal["ask_user", "plan_ready_possible", "needs_more_context"]

MAX_CANDIDATE_TARGETS = 16
MAX_AMBIGUITY_GROUPS = 8
MAX_SECTIONS = 12
MAX_WARNINGS = 6
MAX_TOKEN_ESTIMATE = 1500

_LOCATOR_HINT_RE = re.compile(r"\[(data-testid|data-cy|aria-label)=([^\]]+)\]")


@dataclass(slots=True)
class CandidateTarget:
    label: str
    role: str
    section: str
    locator_hint: str
    confidence: float

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class AmbiguityGroup:
    intent: str
    candidate_indices: list[int]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class SourceStats:
    elements_seen: int
    candidates_found: int
    ambiguous_groups: int
    sections_seen: int

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class PageIntelligenceSchema:
    page_summary: str
    sections: list[str]
    candidate_targets: list[CandidateTarget]
    ambiguity_groups: list[AmbiguityGroup]
    recommended_action: RecommendedAction
    reason: str
    source_stats: SourceStats
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "page_summary": self.page_summary,
            "sections": list(self.sections),
            "candidate_targets": [c.to_dict() for c in self.candidate_targets],
            "ambiguity_groups": [g.to_dict() for g in self.ambiguity_groups],
            "recommended_action": self.recommended_action,
            "reason": self.reason,
            "source_stats": self.source_stats.to_dict(),
            "warnings": list(self.warnings),
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), separators=(",", ":"), ensure_ascii=False)


def _strip_locator_hint(label: str) -> tuple[str, str]:
    m = _LOCATOR_HINT_RE.search(label)
    if not m:
        return label.strip(), ""
    locator = f"{m.group(1)}={m.group(2).strip()}"
    cleaned = _LOCATOR_HINT_RE.sub("", label).strip()
    return cleaned, locator


def _confidence_for(locator_hint: str, semantic_quality: str) -> float:
    if locator_hint.startswith(("data-testid=", "data-cy=")):
        base = 0.9
    elif locator_hint.startswith("aria-label="):
        base = 0.7
    else:
        base = 0.4
    if semantic_quality == "weak":
        base -= 0.2
    elif semantic_quality == "unknown":
        base -= 0.3
    return max(0.05, min(1.0, round(base, 2)))


def _normalize_intent(label: str) -> str:
    return re.sub(r"\s+", " ", label).strip().lower()


def build_page_intelligence_schema(
    *,
    html: str,
    url: str = "",
    title: str = "",
    page_id: str = "",
    packet: PageIntelligencePacket | None = None,
) -> PageIntelligenceSchema:
    packet = packet or build_page_intelligence_packet(
        html=html, url=url, title=title, page_id=page_id
    )

    sections = list(packet.sections[:MAX_SECTIONS])

    candidates: list[CandidateTarget] = []
    intent_to_indices: dict[str, list[int]] = defaultdict(list)
    section_for_cta = sections[0] if sections else ""

    for raw_label in packet.ctas[:MAX_CANDIDATE_TARGETS]:
        text, locator = _strip_locator_hint(raw_label)
        confidence = _confidence_for(locator, packet.semantic_quality)
        candidate = CandidateTarget(
            label=text,
            role="button_or_link",
            section=section_for_cta,
            locator_hint=locator,
            confidence=confidence,
        )
        candidates.append(candidate)
        intent_to_indices[_normalize_intent(text)].append(len(candidates) - 1)

    # Form inputs as candidates (lower confidence, no label normalization)
    for input_meta in packet.inputs[:MAX_CANDIDATE_TARGETS - len(candidates)]:
        name = input_meta.get("name") or input_meta.get("type") or "input"
        input_type = input_meta.get("type") or "text"
        candidate = CandidateTarget(
            label=name,
            role=f"input:{input_type}",
            section=section_for_cta,
            locator_hint=f"name={name}" if name else "",
            confidence=_confidence_for("", packet.semantic_quality),
        )
        candidates.append(candidate)

    if "dialog" in (packet.title or "").lower() or any(
        "modal" in (h or "").lower() or "dialog" in (h or "").lower()
        for h in packet.headings
    ):
        warning_modal = True
    else:
        warning_modal = bool(re.search(r'role=["\']dialog["\']', html))

    ambiguity_groups: list[AmbiguityGroup] = []
    for intent, idxs in intent_to_indices.items():
        if len(idxs) >= 2 and len(ambiguity_groups) < MAX_AMBIGUITY_GROUPS:
            ambiguity_groups.append(AmbiguityGroup(intent=intent, candidate_indices=list(idxs)))

    warnings: list[str] = []
    for risk in packet.risk_flags[:MAX_WARNINGS]:
        warnings.append(risk)
    for amb in packet.ambiguities[:MAX_WARNINGS - len(warnings)]:
        warnings.append(amb)
    if warning_modal and "modal_or_dialog_visible" not in warnings:
        if len(warnings) < MAX_WARNINGS:
            warnings.append("modal_or_dialog_visible")
    if not candidates and len(warnings) < MAX_WARNINGS:
        warnings.append("no_candidates_found")

    repeated_sections: list[str] = []
    seen: dict[str, int] = defaultdict(int)
    for s in sections:
        seen[s] += 1
    for name, count in seen.items():
        if count >= 2 and len(warnings) < MAX_WARNINGS:
            warnings.append(f"repeated_section:{name}")
            repeated_sections.append(name)

    if ambiguity_groups or repeated_sections:
        recommended_action: RecommendedAction = "ask_user"
        reason = "ambiguous_candidates" if ambiguity_groups else "repeated_sections"
    elif packet.semantic_quality in ("weak", "unknown") or not candidates:
        recommended_action = "needs_more_context"
        reason = (
            "weak_semantic_dom"
            if packet.semantic_quality == "weak"
            else ("no_candidates" if not candidates else "unknown_dom")
        )
    else:
        recommended_action = "plan_ready_possible"
        reason = "clear_candidates"

    page_summary = (packet.title or url or "page").strip()
    if packet.headings:
        page_summary = f"{page_summary}: {packet.headings[0]}"
    page_summary = page_summary[:160]

    source_stats = SourceStats(
        elements_seen=len(packet.headings) + len(packet.ctas) + len(packet.inputs),
        candidates_found=len(candidates),
        ambiguous_groups=len(ambiguity_groups),
        sections_seen=len(sections),
    )

    schema = PageIntelligenceSchema(
        page_summary=page_summary,
        sections=sections,
        candidate_targets=candidates,
        ambiguity_groups=ambiguity_groups,
        recommended_action=recommended_action,
        reason=reason,
        source_stats=source_stats,
        warnings=warnings[:MAX_WARNINGS],
    )
    return schema


def schema_to_planner_context_message(schema: PageIntelligenceSchema) -> dict[str, Any]:
    """Render a compact, token-safe context message for the planner LLM.

    The message body is a JSON serialization of the schema dict. No raw HTML.
    """
    body = schema.to_json()
    return {
        "role": "system",
        "name": "page_intelligence",
        "content": f"PAGE_INTELLIGENCE_PACKET={body}",
    }

