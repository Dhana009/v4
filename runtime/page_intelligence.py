from __future__ import annotations

import re
from dataclasses import dataclass, field, asdict
from typing import Any

from runtime.telemetry import estimate_text_tokens

# Sprint 3 INT-DOM-002: compact page/section intelligence packet.
# Pipeline: dom/page extract → deterministic summary → candidate groups
#           → ambiguity/risk flags → compact payload → LLM receives summary, not raw DOM.

_HEADING_TAGS = re.compile(r"<h([1-6])[^>]*>(.*?)</h\1>", re.IGNORECASE | re.DOTALL)
_CTA_PATTERN = re.compile(
    r'<(button|a)([^>]*)>(.*?)</\1>',
    re.IGNORECASE | re.DOTALL,
)
_TESTID_RE = re.compile(r'data-testid=["\']([^"\'>\s]+)["\']', re.IGNORECASE)
_DATA_CY_RE = re.compile(r'data-cy=["\']([^"\'>\s]+)["\']', re.IGNORECASE)
_ARIA_LABEL_RE = re.compile(r'aria-label=["\']([^"\'>\s]+)["\']', re.IGNORECASE)
_INPUT_TYPE_RE = re.compile(r'type=["\']?(\w+)["\']?', re.IGNORECASE)
_INPUT_NAME_RE = re.compile(r'name=["\']?([^"\'>\s]+)["\']?', re.IGNORECASE)
_INPUT_TAG_RE = re.compile(r'<input([^>]*)>', re.IGNORECASE)
_FORM_PATTERN = re.compile(r"<form[^>]*>", re.IGNORECASE)
_TEXT_BLOCK = re.compile(r"<p[^>]*>(.*?)</p>", re.IGNORECASE | re.DOTALL)
_STRIP_TAGS = re.compile(r"<[^>]+>")
_WHITESPACE = re.compile(r"\s+")

_WEAK_DOM_SIGNALS = [
    re.compile(r'id=["\']?\d+["\']?'),
    re.compile(r'class=["\'][\w\s-]{0,4}["\']'),
]


def _strip(text: str) -> str:
    return _WHITESPACE.sub(" ", _STRIP_TAGS.sub("", text)).strip()


def _truncate(text: str, max_chars: int = 80) -> str:
    text = text.strip()
    return text[:max_chars] + ("…" if len(text) > max_chars else "")


@dataclass
class PageIntelligencePacket:
    page_id: str
    url: str
    title: str
    headings: list[str]
    ctas: list[str]
    forms_count: int
    inputs: list[dict[str, str]]
    text_blocks: list[str]
    candidate_locator_groups: list[str]
    semantic_quality: str          # good | weak | unknown
    ambiguities: list[str]
    risk_flags: list[str]
    token_estimate: int
    source: str = "deterministic"
    sections: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def to_compact_summary(self) -> str:
        lines = [
            f"page: {self.title or self.url}",
            f"headings: {', '.join(self.headings[:5]) or 'none'}",
            f"ctas: {', '.join(self.ctas[:8]) or 'none'}",
            f"inputs: {len(self.inputs)} ({', '.join(i.get('name', i.get('type', '?')) for i in self.inputs[:5])})",
            f"forms: {self.forms_count}",
            f"semantic_quality: {self.semantic_quality}",
        ]
        if self.ambiguities:
            lines.append(f"ambiguities: {'; '.join(self.ambiguities[:3])}")
        if self.risk_flags:
            lines.append(f"risk_flags: {'; '.join(self.risk_flags[:3])}")
        if self.text_blocks:
            lines.append(f"text_blocks: {len(self.text_blocks)}")
        return "\n".join(lines)


def build_page_intelligence_packet(
    *,
    html: str,
    url: str = "",
    title: str = "",
    page_id: str = "",
    candidate_locators: list[str] | None = None,
    escalation: bool = False,
) -> PageIntelligencePacket:
    """Build a compact page intelligence packet from raw HTML.

    If escalation=True, raw DOM is allowed. Otherwise only the packet is returned.
    """
    if not html:
        return PageIntelligencePacket(
            page_id=page_id or "unknown",
            url=url,
            title=title,
            headings=[],
            ctas=[],
            forms_count=0,
            inputs=[],
            text_blocks=[],
            candidate_locator_groups=list(candidate_locators or []),
            semantic_quality="unknown",
            ambiguities=["empty_dom"],
            risk_flags=["no_content"],
            token_estimate=0,
            source="deterministic",
        )

    headings = [_truncate(_strip(m.group(2))) for m in _HEADING_TAGS.finditer(html)]
    ctas: list[str] = []
    for m in _CTA_PATTERN.finditer(html):
        attrs_str = m.group(2)
        text = _strip(m.group(3))
        if not text:
            continue
        label = _truncate(text)
        # Append stable locator hints so the LLM can pass them to locator_find
        testid_m = _TESTID_RE.search(attrs_str)
        cy_m = _DATA_CY_RE.search(attrs_str)
        aria_m = _ARIA_LABEL_RE.search(attrs_str)
        if testid_m:
            label += f" [data-testid={testid_m.group(1)}]"
        elif cy_m:
            label += f" [data-cy={cy_m.group(1)}]"
        elif aria_m:
            label += f" [aria-label={aria_m.group(1)}]"
        ctas.append(label)
    forms_count = len(_FORM_PATTERN.findall(html))
    inputs: list[dict[str, str]] = []
    for m in _INPUT_TAG_RE.finditer(html):
        attrs = m.group(1)
        type_m = _INPUT_TYPE_RE.search(attrs)
        name_m = _INPUT_NAME_RE.search(attrs)
        input_type = (type_m.group(1) if type_m else "text").lower()
        input_name = name_m.group(1) if name_m else ""
        if input_type not in ("hidden", "submit", "button"):
            inputs.append({"type": input_type, "name": input_name})
    text_blocks = [_truncate(_strip(m.group(1))) for m in _TEXT_BLOCK.finditer(html) if _strip(m.group(1))]

    # Semantic quality: weak if DOM has only numeric IDs or very short classes
    weak_signals = sum(1 for p in _WEAK_DOM_SIGNALS if p.search(html))
    if weak_signals >= 2:
        semantic_quality = "weak"
    elif headings or ctas or inputs:
        semantic_quality = "good"
    else:
        semantic_quality = "unknown"

    ambiguities: list[str] = []
    risk_flags: list[str] = []

    if len(ctas) > 10:
        ambiguities.append(f"many_ctas:{len(ctas)}")
    if len(inputs) > 8:
        ambiguities.append(f"many_inputs:{len(inputs)}")
    if semantic_quality == "weak":
        risk_flags.append("weak_semantic_dom")
    if forms_count == 0 and inputs:
        risk_flags.append("inputs_outside_form")

    # Sections: derived from headings hierarchy
    sections = [h for h in headings[:10]]

    packet = PageIntelligencePacket(
        page_id=page_id or url or "unknown",
        url=url,
        title=title,
        headings=headings[:10],
        ctas=ctas[:12],
        forms_count=forms_count,
        inputs=inputs[:10],
        text_blocks=text_blocks[:5],
        candidate_locator_groups=list(candidate_locators or [])[:10],
        semantic_quality=semantic_quality,
        ambiguities=ambiguities,
        risk_flags=risk_flags,
        token_estimate=estimate_text_tokens(str(headings) + str(ctas) + str(inputs)),
        source="deterministic",
        sections=sections,
    )
    return packet
