from __future__ import annotations

import re
from collections import OrderedDict
from dataclasses import dataclass, field, asdict
from html.parser import HTMLParser
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
_ARIA_LABEL_RE = re.compile(r'aria-label=["\']([^"\']+)["\']', re.IGNORECASE)
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


# ---------------------------------------------------------------------------
# §3.6 / runtime §11 — deterministic summarize_page (P0 item 9)
# ---------------------------------------------------------------------------

_IMPLICIT_LANDMARK_ROLES: dict[str, str] = {
    "header": "banner",
    "main": "main",
    "nav": "navigation",
    "aside": "complementary",
    "footer": "contentinfo",
    "form": "form",
    "search": "search",
    "section": "region",
}

_HEADING_TAGS_SET = {"h1", "h2", "h3", "h4", "h5", "h6"}

_LANDMARK_ROLES_SET = {
    "banner", "main", "navigation", "complementary",
    "contentinfo", "search", "form", "region",
}

_ACTION_ROLES = {"button", "submit", "reset", "image"}  # input types that are actions
_INTERACTIVE_TAGS = {"button", "a", "input", "select", "textarea"}


def _norm_ws(text: str) -> str:
    """Collapse whitespace and strip."""
    return re.sub(r"\s+", " ", text).strip()


class _PageParser(HTMLParser):
    """Single-pass HTML parser collecting the full element tree."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        # Flat list of events: ("open", tag, attrs_dict) | ("close", tag) | ("data", text)
        self._events: list[tuple] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        d = {k: (v or "") for k, v in attrs}
        self._events.append(("open", tag.lower(), d))

    def handle_endtag(self, tag: str) -> None:
        self._events.append(("close", tag.lower(), {}))

    def handle_data(self, data: str) -> None:
        stripped = data.strip()
        if stripped:
            self._events.append(("data", "#text", {"_text": stripped}))

    # Void elements that never get a close tag
    _VOID = frozenset(
        "area base br col embed hr img input link meta param source track wbr".split()
    )

    def events(self) -> list[tuple]:
        return self._events


def _parse_html(html: str) -> list[tuple]:
    p = _PageParser()
    p.feed(html)
    return p.events()


def _collect_text_from_events(events: list[tuple], start: int) -> str:
    """Collect all text data between the open tag at *start* and its matching close."""
    depth = 0
    buf: list[str] = []
    tag_name = events[start][1]
    for ev in events[start:]:
        kind = ev[0]
        if kind == "open":
            depth += 1
        elif kind == "close" and ev[1] == tag_name:
            depth -= 1
            if depth == 0:
                break
        elif kind == "data":
            buf.append(ev[2]["_text"])
    return _norm_ws(" ".join(buf))


def _build_id_text_map(events: list[tuple]) -> dict[str, str]:
    """Return {id: text_content} for every element that has an id attribute."""
    id_map: dict[str, str] = {}
    for i, ev in enumerate(events):
        if ev[0] == "open":
            eid = ev[2].get("id", "")
            if eid:
                id_map[eid] = _collect_text_from_events(events, i)
    return id_map


def _build_label_map(events: list[tuple]) -> dict[str, str]:
    """Return {input_id: label_text} from <label for=...> associations."""
    label_map: dict[str, str] = {}
    for i, ev in enumerate(events):
        if ev[0] == "open" and ev[1] == "label":
            for_id = ev[2].get("for", "")
            if for_id:
                label_map[for_id] = _collect_text_from_events(events, i)
    return label_map


def _extract_title(events: list[tuple]) -> str:
    for i, ev in enumerate(events):
        if ev[0] == "open" and ev[1] == "title":
            return _collect_text_from_events(events, i)
    return ""


def _extract_url(events: list[tuple], dom: dict | None) -> str:
    if dom and isinstance(dom, dict):
        return dom.get("url", "")
    return ""


def _selector_hint(attrs: dict) -> str:
    """Best stable selector hint from element attributes."""
    testid = attrs.get("data-testid", "")
    if testid:
        return f"[data-testid='{testid}']"
    aria_label = attrs.get("aria-label", "")
    role = attrs.get("role", "")
    name = attrs.get("name", "")
    if aria_label and role:
        return f"[role='{role}'][aria-label='{aria_label}']"
    if aria_label:
        return f"[aria-label='{aria_label}']"
    if name:
        return f"[name='{name}']"
    eid = attrs.get("id", "")
    if eid:
        return f"#{eid}"
    return ""


def _events_from_dict(dom: dict) -> list[tuple]:
    """Convert a dict DOM tree into the same flat event list that the HTML parser emits."""
    events: list[tuple] = []

    def _walk(node: Any) -> None:
        if not isinstance(node, dict):
            return
        tag = (node.get("tag") or node.get("nodeName") or node.get("type") or "").lower()
        tag = tag.lstrip("#")
        if not tag or tag == "document":
            for child in node.get("children", []):
                _walk(child)
            return

        if tag == "text":
            txt = (node.get("text") or node.get("nodeValue") or "").strip()
            if txt:
                events.append(("data", "#text", {"_text": txt}))
            return

        attrs: dict[str, str] = {}
        for k, v in (node.get("attributes") or node.get("attrs") or {}).items():
            attrs[k.lower()] = str(v)

        events.append(("open", tag, attrs))
        for child in node.get("children", []):
            _walk(child)
        events.append(("close", tag, {}))

    _walk(dom)
    return events


def summarize_page(
    dom_snapshot: "dict | str",
    *,
    max_elements: int = 200,
) -> dict:
    """Deterministic page summarizer — spec §3.6 / runtime §11.

    Args:
        dom_snapshot: Either a raw HTML string or a parsed dict tree.
        max_elements: Hard cap on how many elements are processed.

    Returns:
        A dict with keys: url, title, headings, landmarks, primary_actions,
        form_fields, links_count, interactive_count, warnings.
    """
    dom_dict: dict | None = None
    if isinstance(dom_snapshot, dict):
        dom_dict = dom_snapshot
        events = _events_from_dict(dom_snapshot)
    else:
        events = _parse_html(str(dom_snapshot))

    # Pre-build lookup maps
    id_text_map = _build_id_text_map(events)
    label_map = _build_label_map(events)

    url: str = ""
    if dom_dict:
        url = dom_dict.get("url", "")
        if not url:
            url = dom_dict.get("documentURL", "")

    title: str = _extract_title(events)
    if not title and dom_dict:
        title = dom_dict.get("title", "")

    headings: list[dict] = []
    landmarks: list[dict] = []
    primary_actions: list[dict] = []
    form_fields: list[dict] = []
    warnings: list[str] = []

    links_count = 0
    interactive_count = 0
    elements_seen = 0

    # Track heading levels for out-of-order detection
    last_heading_level: int = 0

    # Track landmark stacks for name extraction
    # landmark_stack: list of (index_in_landmarks, tag, open_event_index)
    landmark_stack: list[tuple[int, str, int]] = []

    # We need to process events with context — use index iteration
    for i, ev in enumerate(events):
        kind = ev[0]
        if kind != "open":
            continue
        if elements_seen >= max_elements:
            break
        elements_seen += 1

        tag = ev[1]
        attrs = ev[2]

        # ---- headings ----
        if tag in _HEADING_TAGS_SET:
            level = int(tag[1])
            text = _collect_text_from_events(events, i)
            if text:
                headings.append({"level": level, "text": text})
                if last_heading_level > 0 and level > last_heading_level + 1:
                    warnings.append(
                        f"heading_out_of_order: h{last_heading_level} → h{level}"
                    )
                last_heading_level = level

        # ---- landmarks ----
        explicit_role = attrs.get("role", "").lower()
        implicit_role = _IMPLICIT_LANDMARK_ROLES.get(tag, "")
        landmark_role = explicit_role if explicit_role in _LANDMARK_ROLES_SET else implicit_role

        if landmark_role:
            name = attrs.get("aria-label", "")
            if not name:
                labelledby = attrs.get("aria-labelledby", "")
                if labelledby:
                    name = _norm_ws(id_text_map.get(labelledby, ""))
            entry: dict = {"role": landmark_role, "name": name}
            landmarks.append(entry)
            # Track for heading-based name fallback
            landmark_stack.append((len(landmarks) - 1, tag, i))

        # ---- fill landmark names from first heading inside (deferred) ----
        # We patch landmark names when we encounter a heading inside a landmark
        if tag in _HEADING_TAGS_SET and landmark_stack:
            # Find innermost landmark with no name yet
            for lm_idx, _lm_tag, _lm_open_i in reversed(landmark_stack):
                lm = landmarks[lm_idx]
                if not lm["name"]:
                    heading_text = _collect_text_from_events(events, i)
                    if heading_text:
                        lm["name"] = heading_text
                    break

        # ---- interactive & links count ----
        if tag == "a":
            links_count += 1
            interactive_count += 1
        elif tag in _INTERACTIVE_TAGS:
            interactive_count += 1

        # ---- primary actions: buttons + submit-type inputs (top 10) ----
        if len(primary_actions) < 10:
            if tag == "button":
                label_text = attrs.get("aria-label", "") or _collect_text_from_events(events, i)
                label_text = _norm_ws(label_text)
                if label_text:
                    role_val = attrs.get("role", "button")
                    hint = _selector_hint(attrs) or f"button:contains('{label_text[:40]}')"
                    primary_actions.append({
                        "label": label_text,
                        "role": role_val or "button",
                        "selector_hint": hint,
                    })
            elif tag == "input":
                input_type = attrs.get("type", "text").lower()
                if input_type in ("submit", "button", "reset", "image"):
                    label_text = (
                        attrs.get("value", "")
                        or attrs.get("aria-label", "")
                        or input_type
                    )
                    label_text = _norm_ws(label_text)
                    hint = _selector_hint(attrs) or f"[type='{input_type}']"
                    primary_actions.append({
                        "label": label_text,
                        "role": "button",
                        "selector_hint": hint,
                    })

        # ---- form fields: input/select/textarea ----
        if tag in ("input", "select", "textarea"):
            input_type = attrs.get("type", "text").lower()
            if input_type in ("hidden", "submit", "button", "reset", "image"):
                continue
            input_name = attrs.get("name", "")
            input_id = attrs.get("id", "")
            required = attrs.get("required", None) is not None or attrs.get("required", "") in ("", "true", "required")
            # Label resolution: explicit for=, aria-labelledby, aria-label
            field_label = ""
            if input_id:
                field_label = label_map.get(input_id, "")
            if not field_label:
                labelledby = attrs.get("aria-labelledby", "")
                if labelledby:
                    field_label = _norm_ws(id_text_map.get(labelledby, ""))
            if not field_label:
                field_label = attrs.get("aria-label", "")
            if not field_label:
                field_label = attrs.get("placeholder", "")

            if not field_label:
                warnings.append(f"missing_label: {tag}[name={input_name or input_type}]")

            form_fields.append({
                "label": _norm_ws(field_label),
                "name": input_name,
                "type": input_type if tag == "input" else tag,
                "required": bool(
                    attrs.get("required") is not None
                    and attrs.get("required", "false").lower() != "false"
                    or "required" in attrs
                ),
            })

        # ---- img alt-text warnings ----
        if tag == "img":
            alt = attrs.get("alt")
            if alt is None:
                warnings.append("missing_alt_text: img without alt attribute")
            elif alt.strip() == "":
                warnings.append("missing_alt_text: img with empty alt")

    # Clean landmark stack (close tracking not strictly needed for name patching above)

    # De-duplicate warnings while preserving order
    seen_warnings: dict[str, None] = OrderedDict()
    for w in warnings:
        seen_warnings[w] = None
    warnings = list(seen_warnings.keys())

    return {
        "url": url,
        "title": title,
        "headings": headings,
        "landmarks": landmarks,
        "primary_actions": primary_actions[:10],
        "form_fields": form_fields,
        "links_count": links_count,
        "interactive_count": interactive_count,
        "warnings": warnings,
    }


# ---------------------------------------------------------------------------
# LLM-fallback variant — deterministic-first, controller.call on sparse DOM
# ---------------------------------------------------------------------------

async def summarize_page_with_llm(
    controller: "Any",
    dom_snapshot: "dict | str",
    **ctx: "Any",
) -> "dict | str":
    """Deterministic-first page summariser with LLM fallback.

    Fast path: ``summarize_page`` if headings + form_fields + primary_actions >= 3.
    Slow path: ``controller.call(purpose='page_intelligence', ...)`` when the
    deterministic result is too sparse to be useful.

    Parameters
    ----------
    controller:
        An ``LLMRuntimeController`` instance (or any object with a
        ``call(purpose, system, user, schema)`` coroutine).
    dom_snapshot:
        Raw HTML string or parsed dict DOM tree.
    **ctx:
        Extra keyword arguments forwarded as metadata (ignored by this helper
        but kept for forward-compat).

    Returns
    -------
    dict
        The deterministic summary dict when rich enough, otherwise a plain-text
        string (wrapped in ``{"llm_summary": ...}`` to keep callers consistent).
    """
    det_result = summarize_page(dom_snapshot)
    headings_count = len(det_result.get("headings") or [])
    form_fields_count = len(det_result.get("form_fields") or [])
    primary_actions_count = len(det_result.get("primary_actions") or [])
    if headings_count + form_fields_count + primary_actions_count >= 3:
        return det_result

    # Sparse DOM — fall back to LLM.
    try:
        if isinstance(dom_snapshot, dict):
            dom_text = str(dom_snapshot)[:4000]
        else:
            dom_text = str(dom_snapshot)[:4000]
        llm_response = await controller.call(
            purpose="page_intelligence",
            system=(
                "You are a page intelligence assistant. "
                "Given a DOM snapshot, extract: page title, main headings, "
                "primary actions (buttons/links), form fields, and any risk flags. "
                "Be concise. Return plain text."
            ),
            user=f"DOM snapshot (truncated):\n{dom_text}",
            schema=None,
        )
        llm_text = str(llm_response or "").strip()
        if llm_text:
            return {"llm_summary": llm_text, "source": "llm"}
    except Exception:  # noqa: BLE001
        pass

    # LLM failed — return deterministic result regardless of sparsity.
    return det_result
