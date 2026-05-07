from __future__ import annotations

from collections.abc import Mapping, Sequence
from copy import deepcopy
from dataclasses import dataclass, field
from hashlib import sha1
from html.parser import HTMLParser
import re
from typing import Any

SECTION_TAGS = {
    "article",
    "aside",
    "dialog",
    "footer",
    "form",
    "header",
    "main",
    "nav",
    "section",
}

INTERACTIVE_TAGS = {
    "a",
    "button",
    "input",
    "select",
    "summary",
    "textarea",
}

TEXT_BLOCK_TAGS = {"code", "pre"}

PREFERRED_CONTAINER_TYPES = ["section", "card", "form", "dialog", "table-row", "list-item"]

LOCATOR_RANK_ORDER = {
    "data-testid": 0,
    "role+name": 1,
    "role": 1,
    "label": 2,
    "placeholder": 3,
    "alt/title": 4,
    "alt": 4,
    "title": 4,
    "scoped_text": 5,
    "section_scope": 6,
    "stable_id": 7,
    "scoped_css": 8,
    "css": 9,
    "generated_class": 10,
    "xpath": 11,
    "nth": 12,
}


def _normalize_text(value: Any) -> str:
    text = re.sub(r"\s+", " ", str(value or "")).strip()
    return text


def _normalize_optional_text(value: Any) -> str | None:
    text = _normalize_text(value)
    return text or None


def _normalize_list(values: Sequence[Any] | None) -> list[str]:
    if not values:
        return []
    normalized: list[str] = []
    for value in values:
        text = _normalize_text(value)
        if text:
            normalized.append(text)
    return normalized


def _attrs_to_dict(attrs: Sequence[tuple[str, Any]]) -> dict[str, str]:
    normalized: dict[str, str] = {}
    for key, value in attrs:
        normalized[str(key).strip().lower()] = _normalize_text(value)
    return normalized


def _truthy_attr(attrs: Mapping[str, str], key: str) -> bool:
    value = _normalize_text(attrs.get(key))
    return value.lower() in {"1", "true", "yes", "on", "y"}


def _stable_candidate_id(prefix: str, *parts: Any) -> str:
    payload = "|".join(_normalize_text(part).lower() for part in parts if _normalize_text(part))
    digest = sha1(payload.encode("utf-8")).hexdigest()[:12]
    return f"{prefix}-{digest}"


def _escape_selector_value(value: Any) -> str:
    return _normalize_text(value).replace("\\", "\\\\").replace('"', '\\"')


def _escape_css_id(value: Any) -> str:
    return _normalize_text(value).replace("\\", "\\\\").replace(".", "\\.")


def _infer_role(tag: str, attrs: Mapping[str, str]) -> str:
    explicit_role = _normalize_text(attrs.get("role")).lower()
    if explicit_role:
        return explicit_role

    tag = _normalize_text(tag).lower()
    input_type = _normalize_text(attrs.get("type")).lower()
    if tag == "button":
        return "button"
    if tag == "a":
        return "link"
    if tag == "select":
        return "combobox"
    if tag == "textarea":
        return "textbox"
    if tag == "input":
        if input_type in {"button", "submit", "reset"}:
            return "button"
        if input_type == "checkbox":
            return "checkbox"
        if input_type == "radio":
            return "radio"
        if input_type in {"search", "email", "tel", "url", "text", ""}:
            return "textbox"
    return ""


def _is_internal_control(tag: str, attrs: Mapping[str, str], text: str) -> bool:
    if _truthy_attr(attrs, "data-aw-internal-control"):
        return True
    if _truthy_attr(attrs, "data-autoworkbench-internal"):
        return True

    data_testid = _normalize_text(attrs.get("data-testid")).lower()
    if data_testid.startswith("aw-") or data_testid.startswith("aw_"):
        return True

    marker_text = _normalize_text(text).lower()
    if "debug overlay" in marker_text or "internal control" in marker_text:
        return True

    aria_label = _normalize_text(attrs.get("aria-label")).lower()
    if "debug overlay" in aria_label or "internal control" in aria_label:
        return True

    tag = _normalize_text(tag).lower()
    if tag.startswith("aw-"):
        return True
    return False


def _selector_for_candidate(tag: str, attrs: Mapping[str, str], *, text: str | None = None) -> str:
    data_testid = _normalize_text(attrs.get("data-testid"))
    if data_testid:
        return f'[data-testid="{_escape_selector_value(data_testid)}"]'

    element_id = _normalize_text(attrs.get("id"))
    if element_id:
        return f"#{_escape_css_id(element_id)}"

    aria_label = _normalize_text(attrs.get("aria-label"))
    if aria_label:
        return f'get_by_label("{_escape_selector_value(aria_label)}")'

    role = _infer_role(tag, attrs)
    if role and text:
        return f'get_by_role("{role}", name="{_escape_selector_value(text)}")'

    if text:
        return f'text="{_escape_selector_value(text)}"'

    return _normalize_text(tag) or "*"


def _primary_name(tag: str, attrs: Mapping[str, str], text: str | None = None) -> str | None:
    candidates = (
        attrs.get("aria-label"),
        attrs.get("label"),
        attrs.get("placeholder"),
        attrs.get("alt"),
        attrs.get("title"),
        text,
    )
    for candidate in candidates:
        normalized = _normalize_optional_text(candidate)
        if normalized:
            return normalized
    if _normalize_text(tag) in SECTION_TAGS:
        return _normalize_optional_text(attrs.get("aria-label") or attrs.get("title") or attrs.get("id"))
    return None


def _section_type(tag: str, attrs: Mapping[str, str]) -> str:
    tag = _normalize_text(tag).lower()
    if tag in {"form", "dialog"}:
        return tag
    if tag in {"main", "nav", "header", "footer", "aside", "article"}:
        return "section"
    if tag == "section":
        return "section"
    return "section"


def _container_scope_name(tag: str, attrs: Mapping[str, str], text: str | None = None) -> str:
    label = _primary_name(tag, attrs, text)
    if label:
        return label
    element_id = _normalize_optional_text(attrs.get("id"))
    if element_id:
        return element_id
    return _normalize_text(tag) or "page"


def _normalize_candidate(candidate: Mapping[str, Any]) -> dict[str, Any]:
    normalized = dict(candidate)
    strategy = _normalize_text(normalized.get("strategy")).lower()
    if strategy:
        normalized["strategy"] = strategy
    risk_flags = _normalize_list(normalized.get("risk_flags") if isinstance(normalized.get("risk_flags"), Sequence) else None)
    if risk_flags:
        normalized["risk_flags"] = risk_flags
    candidate_id = _normalize_optional_text(normalized.get("candidate_id"))
    if candidate_id:
        normalized["candidate_id"] = candidate_id
    return normalized


def _rank_score(candidate: Mapping[str, Any], index: int, target_text: str | None = None) -> tuple[int, int, int]:
    strategy = _normalize_text(candidate.get("strategy")).lower()
    risk_flags = {flag.lower() for flag in _normalize_list(candidate.get("risk_flags") if isinstance(candidate.get("risk_flags"), Sequence) else None)}

    if strategy == "css" and "generated_class" in risk_flags:
        strategy_key = "generated_class"
    elif strategy == "css" and "nth" in risk_flags:
        strategy_key = "nth"
    elif strategy in {"role", "role+name"}:
        strategy_key = "role+name"
    elif strategy in {"alt", "title", "alt/title"}:
        strategy_key = "alt/title"
    elif strategy in {"scoped_text", "text", "exact_text", "partial_text"}:
        strategy_key = "scoped_text"
    elif strategy in {"section_scope", "section"}:
        strategy_key = "section_scope"
    elif strategy in {"stable_id", "id"}:
        strategy_key = "stable_id"
    elif strategy in {"scoped_css", "css"} and "generated_class" not in risk_flags:
        strategy_key = "scoped_css"
    elif strategy in {"xpath", "absolute_xpath", "relative_xpath"}:
        strategy_key = "xpath"
    elif strategy in {"nth", "index"} or "fragile_last_resort" in risk_flags:
        strategy_key = "nth"
    elif strategy in {"placeholder", "label", "data-testid"}:
        strategy_key = strategy
    else:
        strategy_key = strategy or "css"

    base_score = LOCATOR_RANK_ORDER.get(strategy_key, 99)
    if target_text and strategy_key == "scoped_text":
        base_score = min(base_score, 5)
    if "generated_class" in risk_flags and base_score < LOCATOR_RANK_ORDER["generated_class"]:
        base_score = LOCATOR_RANK_ORDER["generated_class"]
    if "fragile_last_resort" in risk_flags and base_score < LOCATOR_RANK_ORDER["nth"]:
        base_score = LOCATOR_RANK_ORDER["nth"]
    return (base_score, 0 if strategy_key != "nth" else 1, index)


@dataclass(slots=True)
class _Frame:
    tag: str
    attrs: dict[str, str]
    kind: str
    candidate_id: str | None = None
    section_ref: str | None = None
    scope: str | None = None
    ancestor_chain: list[str] = field(default_factory=list)
    text_parts: list[str] = field(default_factory=list)
    internal: bool = False


class _SnapshotParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.frames: list[_Frame] = []
        self.sections: list[dict[str, Any]] = []
        self.interactive_elements: list[dict[str, Any]] = []
        self.text_blocks: list[dict[str, Any]] = []
        self.extraction_warnings: list[str] = []
        self._title_parts: list[str] = []
        self._in_title = False
        self._open_sections: list[dict[str, Any]] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, Any]]) -> None:
        tag_name = _normalize_text(tag).lower()
        attrs_map = _attrs_to_dict(attrs)
        current_section = self._open_sections[-1] if self._open_sections else None
        ancestor_chain = [section["name"] for section in self._open_sections if section.get("name")]
        text_context = ""

        kind = ""
        if tag_name == "title":
            self._in_title = True
        if tag_name in SECTION_TAGS:
            kind = "section"
        elif tag_name in INTERACTIVE_TAGS or _infer_role(tag_name, attrs_map):
            kind = "interactive"
        elif tag_name in TEXT_BLOCK_TAGS:
            kind = "text_block"

        internal = _is_internal_control(tag_name, attrs_map, text_context)
        candidate_id = None
        scope = "page"
        section_ref = None
        if current_section:
            scope = f"section:{current_section['name']}"
            section_ref = current_section["candidate_id"]
        if kind == "section":
            section_name = _container_scope_name(tag_name, attrs_map)
            candidate_id = _stable_candidate_id("section", tag_name, len(self.sections), section_name, attrs_map.get("id"), attrs_map.get("aria-label"))
            section_record = {
                "candidate_id": candidate_id,
                "element_id": _normalize_optional_text(attrs_map.get("id")),
                "element_ref": candidate_id,
                "candidate_type": _section_type(tag_name, attrs_map),
                "tag": tag_name,
                "role": _infer_role(tag_name, attrs_map) or "region",
                "name": section_name,
                "text": "",
                "scope": scope,
                "section_ref": section_ref,
                "ancestor_chain": ancestor_chain,
                "selector": _selector_for_candidate(tag_name, attrs_map),
                "source": "dom_snapshot",
                "visibility": "visible",
                "enabled": True,
                "risk_flags": [],
            }
            self._open_sections.append(section_record)
            self.frames.append(_Frame(
                tag=tag_name,
                attrs=attrs_map,
                kind=kind,
                candidate_id=candidate_id,
                section_ref=section_ref,
                scope=scope,
                ancestor_chain=ancestor_chain,
                internal=internal,
            ))
            return

        if kind in {"interactive", "text_block"}:
            name = _primary_name(tag_name, attrs_map)
            candidate_id = _stable_candidate_id(kind, tag_name, len(self.interactive_elements), name, attrs_map.get("id"), attrs_map.get("data-testid"))
            frame = _Frame(
                tag=tag_name,
                attrs=attrs_map,
                kind=kind,
                candidate_id=candidate_id,
                section_ref=section_ref,
                scope=scope,
                ancestor_chain=ancestor_chain,
                internal=internal,
            )
            self.frames.append(frame)
            return

        self.frames.append(_Frame(tag=tag_name, attrs=attrs_map, kind=kind, internal=internal))

    def handle_endtag(self, tag: str) -> None:
        tag_name = _normalize_text(tag).lower()
        if tag_name == "title":
            self._in_title = False

        if not self.frames:
            return

        while self.frames:
            frame = self.frames.pop()
            if frame.tag != tag_name:
                continue

            text = _normalize_optional_text(" ".join(frame.text_parts))
            if frame.kind == "section":
                if self._open_sections:
                    section_record = self._open_sections.pop()
                    section_record["text"] = text or section_record.get("name") or ""
                    if not section_record.get("name"):
                        section_record["name"] = section_record["text"] or section_record.get("element_id") or frame.tag
                    if not frame.internal:
                        self.sections.append(section_record)
                return

            if frame.kind in {"interactive", "text_block"}:
                if frame.internal:
                    self.extraction_warnings.append(f"excluded_internal_{frame.tag}")
                    return

                attrs = frame.attrs
                name = _primary_name(frame.tag, attrs, text)
                record = {
                    "candidate_id": frame.candidate_id or _stable_candidate_id("element", frame.tag, len(self.interactive_elements), name, attrs.get("id")),
                    "element_id": _normalize_optional_text(attrs.get("id")),
                    "element_ref": _normalize_optional_text(attrs.get("id")) or frame.candidate_id,
                    "candidate_type": "text_block" if frame.kind == "text_block" or frame.tag in TEXT_BLOCK_TAGS else ("action_target" if frame.tag in {"button", "a", "summary"} or _infer_role(frame.tag, attrs) in {"button", "link"} else "form_field"),
                    "tag": frame.tag,
                    "role": _infer_role(frame.tag, attrs) or ("text_block" if frame.kind == "text_block" else ""),
                    "name": name or text or _normalize_optional_text(attrs.get("aria-label")) or _normalize_optional_text(attrs.get("placeholder")),
                    "text": text or "",
                    "target_text": text or name or "",
                    "expected_value": None,
                    "data_testid": _normalize_optional_text(attrs.get("data-testid")),
                    "label": _normalize_optional_text(attrs.get("label")),
                    "placeholder": _normalize_optional_text(attrs.get("placeholder")),
                    "alt": _normalize_optional_text(attrs.get("alt")),
                    "title": _normalize_optional_text(attrs.get("title")),
                    "selector": _selector_for_candidate(frame.tag, attrs, text=text),
                    "source": "dom_snapshot",
                    "scope": frame.scope or "page",
                    "section_ref": frame.section_ref,
                    "ancestor_chain": frame.ancestor_chain,
                    "visibility": "visible",
                    "enabled": not _truthy_attr(attrs, "disabled"),
                    "risk_flags": [],
                }
                if _truthy_attr(attrs, "hidden") or _truthy_attr(attrs, "aria-hidden"):
                    record["visibility"] = "hidden"
                    record["risk_flags"].append("hidden")
                if frame.kind == "text_block":
                    record["candidate_type"] = "text_block"
                self.interactive_elements.append(record)
                if frame.kind == "text_block":
                    self.text_blocks.append(record)
                return

            return

    def handle_data(self, data: str) -> None:
        if self._in_title:
            text = _normalize_text(data)
            if text:
                self._title_parts.append(text)

        text = _normalize_text(data)
        if not text:
            return
        for frame in self.frames:
            frame.text_parts.append(text)

    @property
    def title_text(self) -> str:
        return _normalize_text(" ".join(self._title_parts))


def build_page_snapshot(
    html: str | None = None,
    url: str | None = None,
    title: str | None = None,
    scope: str | None = None,
    captured_at: str | None = None,
    timestamp: str | None = None,
    **_: Any,
) -> dict[str, Any]:
    parser = _SnapshotParser()
    parser.feed(html or "")
    parser.close()

    resolved_title = _normalize_optional_text(title) or parser.title_text or None
    resolved_timestamp = _normalize_optional_text(captured_at) or _normalize_optional_text(timestamp)
    if not resolved_timestamp:
        resolved_timestamp = "1970-01-01T00:00:00Z"

    sections = deepcopy(parser.sections)
    interactive_elements = deepcopy(parser.interactive_elements)
    text_blocks = deepcopy(parser.text_blocks)
    if parser.extraction_warnings:
        warnings = list(parser.extraction_warnings)
    else:
        warnings = None

    dynamic_state = classify_dynamic_ui_state(
        page_url=url,
        page_title=resolved_title,
        state_evidence={
            "modal": [element for element in interactive_elements if _normalize_text(element.get("role")).lower() in {"dialog", "modal"}],
            "dropdown": [element for element in interactive_elements if _normalize_text(element.get("role")).lower() in {"listbox", "combobox", "dropdown"}],
            "toast": [element for element in interactive_elements if _normalize_text(element.get("role")).lower() in {"alert", "status"}],
            "loading": [element for element in interactive_elements if "load" in _normalize_text(element.get("text")).lower() or "spinner" in _normalize_text(element.get("text")).lower()],
        },
        states=[
            "modal"
            if any(_normalize_text(element.get("role")).lower() in {"dialog", "modal"} for element in interactive_elements)
            else None,
            "dropdown"
            if any(_normalize_text(element.get("role")).lower() in {"listbox", "combobox", "dropdown"} for element in interactive_elements)
            else None,
            "toast"
            if any(_normalize_text(element.get("role")).lower() in {"alert", "status"} for element in interactive_elements)
            else None,
            "loading"
            if any("load" in _normalize_text(element.get("text")).lower() or "spinner" in _normalize_text(element.get("text")).lower() for element in interactive_elements)
            else None,
        ],
        advisory_only=True,
    )

    snapshot: dict[str, Any] = {
        "url": _normalize_optional_text(url),
        "title": resolved_title,
        "captured_at": resolved_timestamp,
        "timestamp": resolved_timestamp,
        "scope": _normalize_optional_text(scope) or "full_page",
        "sections": sections,
        "landmarks": deepcopy(sections),
        "interactive_elements": interactive_elements,
        "text_blocks": text_blocks,
        "extraction_warnings": warnings,
        "dynamic_state": dynamic_state,
        "metadata": {
            "url": _normalize_optional_text(url),
            "title": resolved_title,
            "scope": _normalize_optional_text(scope) or "full_page",
            "captured_at": resolved_timestamp,
            "timestamp": resolved_timestamp,
            "section_count": len(sections),
            "interactive_element_count": len(interactive_elements),
            "text_block_count": len(text_blocks),
            "internal_controls_excluded": len(parser.extraction_warnings),
        },
    }
    return snapshot


def build_element_candidate(
    candidate_id: str | None = None,
    element_id: str | None = None,
    element_ref: str | None = None,
    candidate_type: str | None = None,
    role: str | None = None,
    accessible_name: str | None = None,
    text: str | None = None,
    target_text: str | None = None,
    expected_value: str | None = None,
    label: str | None = None,
    placeholder: str | None = None,
    alt: str | None = None,
    title: str | None = None,
    data_testid: str | None = None,
    selector: str | None = None,
    source: str | None = None,
    scope: str | None = None,
    ancestor_chain: Sequence[str] | None = None,
    locator_candidates: Sequence[Mapping[str, Any]] | None = None,
    risk_flags: Sequence[str] | None = None,
    section_ref: str | None = None,
    tag: str | None = None,
    visibility: str | None = None,
    enabled: bool | None = None,
    **_: Any,
) -> dict[str, Any]:
    normalized_text = _normalize_optional_text(text) or _normalize_optional_text(target_text) or _normalize_optional_text(accessible_name)
    normalized_target_text = _normalize_optional_text(target_text) or normalized_text
    normalized_expected_value = _normalize_optional_text(expected_value)
    normalized_role = _normalize_optional_text(role) or (_infer_role(_normalize_text(tag), {"role": _normalize_text(role)}) if tag else None)
    normalized_candidate_type = _normalize_optional_text(candidate_type) or ("assertion_target" if normalized_expected_value is not None else "action_target")
    normalized_scope = _normalize_optional_text(scope) or "page"
    normalized_ancestor_chain = _normalize_list(ancestor_chain)
    normalized_risk_flags = _normalize_list(risk_flags)
    normalized_locator_candidates = []
    if locator_candidates:
        raw_candidates = [_normalize_candidate(candidate) for candidate in locator_candidates if isinstance(candidate, Mapping)]
        raw_candidates = rank_locator_candidates(raw_candidates, target_text=normalized_target_text)
        normalized_locator_candidates = raw_candidates

    resolved_candidate_id = _normalize_optional_text(candidate_id)
    if not resolved_candidate_id:
        resolved_candidate_id = _stable_candidate_id(
            "candidate",
            normalized_candidate_type,
            element_ref,
            element_id,
            normalized_target_text,
            normalized_scope,
            data_testid,
        )

    record = {
        "candidate_id": resolved_candidate_id,
        "element_id": _normalize_optional_text(element_id),
        "element_ref": _normalize_optional_text(element_ref) or _normalize_optional_text(element_id) or resolved_candidate_id,
        "candidate_type": normalized_candidate_type,
        "role": normalized_role,
        "accessible_name": _normalize_optional_text(accessible_name) or _primary_name(tag or "", {"aria-label": accessible_name or "", "label": label or "", "placeholder": placeholder or "", "alt": alt or "", "title": title or ""}, normalized_text),
        "text": normalized_text,
        "target_text": normalized_target_text,
        "expected_value": normalized_expected_value,
        "label": _normalize_optional_text(label),
        "placeholder": _normalize_optional_text(placeholder),
        "alt": _normalize_optional_text(alt),
        "title": _normalize_optional_text(title),
        "data_testid": _normalize_optional_text(data_testid),
        "selector": _normalize_optional_text(selector) or _selector_for_candidate(tag or "", {"data-testid": data_testid or "", "id": element_id or "", "aria-label": accessible_name or label or "", "placeholder": placeholder or ""}, text=normalized_text),
        "source": _normalize_optional_text(source) or "dom_snapshot",
        "scope": normalized_scope,
        "section_ref": _normalize_optional_text(section_ref),
        "ancestor_chain": normalized_ancestor_chain,
        "locator_candidates": normalized_locator_candidates,
        "risk_flags": normalized_risk_flags,
        "visibility": _normalize_optional_text(visibility) or "visible",
        "enabled": bool(True if enabled is None else enabled),
    }
    return record


def rank_locator_candidates(
    candidates: Sequence[Mapping[str, Any]] | None = None,
    target_text: str | None = None,
    **_: Any,
) -> list[dict[str, Any]]:
    normalized_candidates = [_normalize_candidate(candidate) for candidate in (candidates or []) if isinstance(candidate, Mapping)]
    ranked = sorted(
        enumerate(normalized_candidates),
        key=lambda item: _rank_score(item[1], item[0], target_text=_normalize_optional_text(target_text)),
    )
    return [deepcopy(candidate) for _, candidate in ranked]


def validate_locator_candidate(
    locator_ref: str | None = None,
    matches: Sequence[Mapping[str, Any]] | None = None,
    visible_matches: Sequence[Mapping[str, Any]] | None = None,
    page_url: str | None = None,
    expected_value: str | None = None,
    locator: str | None = None,
    **_: Any,
) -> dict[str, Any]:
    normalized_locator_ref = _normalize_optional_text(locator_ref) or _normalize_optional_text(locator) or "locator"
    match_list = [deepcopy(match) for match in (matches or []) if isinstance(match, Mapping)]
    visible_list = [deepcopy(match) for match in (visible_matches or []) if isinstance(match, Mapping)]
    match_count = len(match_list)
    visible_count = len(visible_list)

    classification = "locator_unique"
    status = "unique"
    selected_element_ref: str | None = None
    ambiguity_candidates: list[dict[str, Any]] | None = None

    if match_count == 0:
        classification = "locator_not_found"
        status = "none"
    elif match_count > 1 or visible_count > 1:
        classification = "locator_matches_multiple"
        status = "multiple"
        ambiguity_candidates = [
            {
                "element_ref": _normalize_optional_text(match.get("element_ref")) or _normalize_optional_text(match.get("candidate_id")),
                "visible": bool(match.get("visible", True)),
                "text": _normalize_optional_text(match.get("text")),
                "role": _normalize_optional_text(match.get("role")),
            }
            for match in match_list
        ]
    else:
        selected = visible_list[0] if visible_list else match_list[0]
        selected_element_ref = _normalize_optional_text(selected.get("element_ref")) or _normalize_optional_text(selected.get("candidate_id"))
        selected_text = _normalize_optional_text(
            selected.get("text")
            or selected.get("name")
            or selected.get("label")
            or selected.get("accessible_name")
        )
        if (not visible_list and any(not bool(match.get("visible", True)) for match in match_list)) or selected.get("visible") is False:
            classification = "locator_hidden"
            status = "hidden"
        elif expected_value is not None and selected_text and _normalize_optional_text(expected_value) != selected_text:
            classification = "locator_text_mismatch"
            status = "unique"
        else:
            classification = "locator_unique"
            status = "unique"

    result: dict[str, Any] = {
        "locator_ref": normalized_locator_ref,
        "classification": classification,
        "status": status,
        "match_count": match_count,
        "visible_count": visible_count,
        "page_url": _normalize_optional_text(page_url),
        "backend_validation_needed": False,
        "backend_validated": True,
    }
    if selected_element_ref is not None:
        result["selected_element_ref"] = selected_element_ref
    if ambiguity_candidates is not None:
        result["ambiguity_candidates"] = ambiguity_candidates
    if classification == "locator_text_mismatch":
        result["failure_reason"] = "locator text mismatch"
    elif classification == "locator_hidden":
        result["failure_reason"] = "locator hidden"
    elif classification == "locator_matches_multiple":
        result["failure_reason"] = "locator matches multiple elements"
    elif classification == "locator_not_found":
        result["failure_reason"] = "locator not found"
    return result


def scope_candidates(
    target_text: str | None = None,
    candidates: Sequence[Mapping[str, Any]] | None = None,
    preferred_container_types: Sequence[str] | None = None,
    escalate_to: Sequence[str] | None = None,
    **_: Any,
) -> dict[str, Any]:
    normalized_candidates = [_normalize_candidate(candidate) for candidate in (candidates or []) if isinstance(candidate, Mapping)]
    preferred_types = [text.lower() for text in _normalize_list(preferred_container_types) if text]
    if not preferred_types:
        preferred_types = list(PREFERRED_CONTAINER_TYPES)
    escalation_options = [text.lower() for text in _normalize_list(escalate_to)]

    def candidate_score(item: tuple[int, Mapping[str, Any]]) -> tuple[int, int, int]:
        index, candidate = item
        scope = _normalize_text(candidate.get("scope")).lower()
        section_ref = _normalize_optional_text(candidate.get("section_ref"))
        candidate_type = _normalize_text(candidate.get("candidate_type")).lower()
        score = len(preferred_types)
        if scope in preferred_types:
            score = preferred_types.index(scope)
        elif candidate_type in preferred_types:
            score = preferred_types.index(candidate_type)
        elif section_ref:
            score = len(preferred_types) - 1 if preferred_types else 0
        if scope == "page":
            score += 2
        return (score, 0 if section_ref else 1, index)

    ranked = sorted(enumerate(normalized_candidates), key=candidate_score)
    if ranked:
        best_index, best_candidate = ranked[0]
        best_scope = _normalize_text(best_candidate.get("scope")).lower() or "page"
        preferred_container_type = best_scope if best_scope in preferred_types else (_normalize_text(best_candidate.get("candidate_type")).lower() or "section")
        ambiguity = len(normalized_candidates) > 1
        escalation = None
        if ambiguity:
            escalation = "clarification"
            if "locator_specialist" in escalation_options and best_scope == "page":
                escalation = "locator_specialist"
        return {
            "candidate_id": _normalize_optional_text(best_candidate.get("candidate_id")),
            "recommended_candidate_id": _normalize_optional_text(best_candidate.get("candidate_id")),
            "candidate_count": len(normalized_candidates),
            "preferred_container_type": preferred_container_type,
            "scope": best_scope,
            "target_text": _normalize_optional_text(target_text),
            "escalation": escalation,
            "needs_clarification": ambiguity,
            "execute": False,
            "ranked_candidates": [deepcopy(candidate) for _, candidate in ranked],
        }

    return {
        "candidate_id": None,
        "recommended_candidate_id": None,
        "candidate_count": 0,
        "preferred_container_type": None,
        "scope": "page",
        "target_text": _normalize_optional_text(target_text),
        "escalation": "clarification" if escalation_options else None,
        "needs_clarification": True,
        "execute": False,
        "ranked_candidates": [],
    }


def classify_assertion_target(
    assertion_type: str | None = None,
    target_candidate: Mapping[str, Any] | None = None,
    expected_outcome_metadata_ref: str | None = None,
    expected_outcome: Mapping[str, Any] | None = None,
    expected_value: str | None = None,
    source_of_expected_value: str | None = None,
    compatibility_flags: Sequence[str] | None = None,
    expected_outcome_metadata: Mapping[str, Any] | None = None,
    **_: Any,
) -> dict[str, Any]:
    normalized_assertion_type = _normalize_optional_text(assertion_type) or _normalize_optional_text(
        target_candidate.get("candidate_type") if isinstance(target_candidate, Mapping) else None
    ) or "visible"
    normalized_flags = {flag.lower() for flag in _normalize_list(compatibility_flags)}
    candidate_snapshot = deepcopy(target_candidate) if isinstance(target_candidate, Mapping) else {}
    target_candidate_id = _normalize_optional_text(candidate_snapshot.get("candidate_id")) or _normalize_optional_text(
        candidate_snapshot.get("element_ref")
    ) or _normalize_optional_text(candidate_snapshot.get("element_id"))
    target_text = _normalize_optional_text(
        candidate_snapshot.get("target_text")
        or candidate_snapshot.get("text")
        or candidate_snapshot.get("accessible_name")
    )
    resolved_expected_value = _normalize_optional_text(expected_value) or _normalize_optional_text(
        candidate_snapshot.get("expected_value")
    )

    if normalized_assertion_type in {"visible", "hidden", "enabled", "disabled", "checked"}:
        resolved_expected_value = None
    elif normalized_assertion_type in {"has_text", "exact_text", "has_value"} and not resolved_expected_value:
        resolved_expected_value = _normalize_optional_text(candidate_snapshot.get("target_text"))

    validation_status = "valid"
    if normalized_assertion_type in {"has_text", "exact_text", "has_value"} and not resolved_expected_value:
        validation_status = "invalid"
    if "visible+has_text invalid" in normalized_flags:
        validation_status = "invalid"

    outcome_metadata = deepcopy(expected_outcome_metadata) if isinstance(expected_outcome_metadata, Mapping) else None
    outcome_metadata_ref = _normalize_optional_text(expected_outcome_metadata_ref)
    if outcome_metadata_ref is None and isinstance(expected_outcome, Mapping):
        outcome_metadata_ref = _normalize_optional_text(
            expected_outcome.get("ref")
            or expected_outcome.get("metadata_ref")
            or expected_outcome.get("parent_ref")
            or expected_outcome.get("step_ref")
        )

    result: dict[str, Any] = {
        "assertion_type": normalized_assertion_type,
        "target_candidate_id": target_candidate_id,
        "target_text": target_text,
        "expected_value": resolved_expected_value,
        "source_of_expected_value": _normalize_optional_text(source_of_expected_value),
        "expected_outcome_metadata_ref": outcome_metadata_ref,
        "expected_outcome_metadata": outcome_metadata,
        "compatibility_flags": _normalize_list(compatibility_flags),
        "validation_status": validation_status,
        "status": "proposal" if validation_status == "valid" else "rejected",
        "advisory_only": True,
        "execute": False,
        "backend_validation_required": True,
        "browser_validation_required": True,
        "candidate": candidate_snapshot,
    }
    if result["candidate"]:
        result["candidate"]["candidate_type"] = "assertion_target"
    return result


def classify_dynamic_ui_state(
    page_url: str | None = None,
    page_title: str | None = None,
    state_evidence: Mapping[str, Any] | None = None,
    states: Sequence[str] | None = None,
    advisory_only: bool | None = None,
    **_: Any,
) -> dict[str, Any]:
    evidence_map = dict(state_evidence or {}) if isinstance(state_evidence, Mapping) else {}
    normalized_states = [state.lower() for state in _normalize_list(states)]
    if not normalized_states:
        normalized_states = [state.lower() for state in evidence_map.keys() if _normalize_text(state)]

    observed_states: list[dict[str, Any]] = []
    capability_gaps: list[dict[str, Any]] = []
    classification: str | None = None

    supported_map = {
        "modal": "modal",
        "dialog": "modal",
        "dropdown": "dropdown",
        "listbox": "dropdown",
        "toast": "toast",
        "alert": "toast",
        "loading": "loading",
        "spinner": "loading",
        "navigation": "navigation",
        "page_change": "navigation",
        "route_change": "navigation",
    }
    gap_states = {"iframe", "popup", "upload", "file_picker", "permission", "download"}

    for state_name in normalized_states:
        if not state_name:
            continue
        evidence = evidence_map.get(state_name) or evidence_map.get(state_name.replace("_", "-")) or evidence_map.get(state_name.replace("-", "_"))
        evidence_summary = deepcopy(evidence) if isinstance(evidence, (Mapping, list, tuple)) else evidence
        if state_name in gap_states:
            capability_gaps.append(
                {
                    "state": state_name,
                    "classification": "capability_gap",
                    "advisory_only": True,
                    "evidence": evidence_summary,
                }
            )
            if classification is None:
                classification = "capability_gap"
            continue

        state_classification = supported_map.get(state_name)
        if state_classification is None:
            capability_gaps.append(
                {
                    "state": state_name,
                    "classification": "uncertain",
                    "advisory_only": True,
                    "evidence": evidence_summary,
                }
            )
            if classification is None:
                classification = "uncertain"
            continue

        observed = {
            "state": state_classification,
            "source_state": state_name,
            "advisory_only": True,
            "evidence": evidence_summary,
        }
        if state_classification in {"loading", "navigation"}:
            observed["unstable"] = state_classification == "loading"
        observed_states.append(observed)
        if classification is None:
            classification = state_classification

    if observed_states and classification in {"capability_gap", "uncertain"}:
        classification = observed_states[0]["state"]

    if not classification:
        classification = "uncertain" if capability_gaps else None

    return {
        "page_url": _normalize_optional_text(page_url),
        "page_title": _normalize_optional_text(page_title),
        "states": normalized_states,
        "observed_states": observed_states,
        "capability_gaps": capability_gaps,
        "classification": classification,
        "status": "observed_state_proposal" if observed_states or capability_gaps else "uncertain",
        "advisory_only": True if advisory_only is None else bool(advisory_only),
        "execute": False,
        "needs_recovery": bool(observed_states or capability_gaps),
    }


def build_locator_escalation_request(
    target_text: str | None = None,
    candidate_summary: Mapping[str, Any] | None = None,
    page_context: Mapping[str, Any] | None = None,
    validation_requirements: Sequence[str] | None = None,
    skills_loaded: Sequence[str] | None = None,
    tool_policy: Mapping[str, Any] | None = None,
    advisory_only: bool | None = None,
    candidates: Sequence[Mapping[str, Any]] | None = None,
    preferred_container_types: Sequence[str] | None = None,
    escalate_to: Sequence[str] | None = None,
    raw_dom: str | None = None,
    full_dom: str | None = None,
    **_: Any,
) -> dict[str, Any]:
    summary: dict[str, Any]
    if isinstance(candidate_summary, Mapping):
        summary = deepcopy(dict(candidate_summary))
    elif candidates:
        summary = scope_candidates(
            target_text=target_text,
            candidates=candidates,
            preferred_container_types=preferred_container_types,
            escalate_to=escalate_to,
        )
    else:
        summary = {
            "candidate_ids": [],
            "recommended_candidate_id": None,
            "ranked_candidates": [],
            "needs_clarification": True,
            "escalation": None,
            "scope": "page",
        }

    candidate_ids = summary.get("candidate_ids")
    if not isinstance(candidate_ids, list):
        candidate_ids = []
        ranked_candidates = summary.get("ranked_candidates")
        if isinstance(ranked_candidates, Sequence):
            for candidate in ranked_candidates:
                if isinstance(candidate, Mapping):
                    candidate_id = _normalize_optional_text(candidate.get("candidate_id"))
                    if candidate_id:
                        candidate_ids.append(candidate_id)
    candidate_ids = [candidate_id for candidate_id in candidate_ids if _normalize_optional_text(candidate_id)]

    page_context_map = dict(page_context or {}) if isinstance(page_context, Mapping) else {}
    minimal_page_context = {
        "url": _normalize_optional_text(page_context_map.get("url") or page_context_map.get("page_url")),
        "title": _normalize_optional_text(page_context_map.get("title") or page_context_map.get("page_title")),
        "scope": _normalize_optional_text(page_context_map.get("scope")),
        "page_id": _normalize_optional_text(page_context_map.get("page_id")),
    }

    normalized_validation_requirements = _normalize_list(validation_requirements)
    normalized_skills_loaded = _normalize_list(skills_loaded)
    normalized_tool_policy = dict(tool_policy or {}) if isinstance(tool_policy, Mapping) else {}
    target_text_value = _normalize_optional_text(target_text)

    recommended_candidate_id = _normalize_optional_text(
        summary.get("recommended_candidate_id") or summary.get("candidate_id")
    )
    if recommended_candidate_id is None and candidate_ids:
        recommended_candidate_id = candidate_ids[0]

    return {
        "purpose": "locator_specialist",
        "target_text": target_text_value,
        "candidate_summary": summary,
        "candidate_ids": candidate_ids,
        "recommended_candidate_id": recommended_candidate_id,
        "page_context": minimal_page_context,
        "validation_requirements": normalized_validation_requirements,
        "skills_loaded": normalized_skills_loaded,
        "tool_policy": {
            "deny_execution": True,
            "backend_validation_required": True,
            "browser_validation_required": True,
            "policy": normalized_tool_policy,
        },
        "advisory_only": True if advisory_only is None else bool(advisory_only),
        "execute": False,
        "backend_validation_required": True,
        "browser_validation_required": True,
        "needs_user_selection": bool(summary.get("needs_clarification")),
        "status": "escalation_proposal",
        "escalation_reason": _normalize_optional_text(summary.get("escalation"))
        or ("insufficient_deterministic_evidence" if candidate_ids or summary else "no_locator_evidence"),
    }


def build_update_locator_command(
    type: str | None = None,  # noqa: A002 - command field name
    command_id: str | None = None,
    run_id: str | None = None,
    step_id: str | None = None,
    operation_id: str | None = None,
    locator_candidate: Mapping[str, Any] | None = None,
    locator_history: Sequence[Mapping[str, Any]] | None = None,
    reason: str | None = None,
    source: str | None = None,
    user_hint: str | None = None,
    backend_validation_required: bool | None = None,
    active_locator: str | None = None,
    parent_scope: str | None = None,
    group_scope: str | None = None,
    operation_scope: str | None = None,
    validation_result: Mapping[str, Any] | None = None,
    validation_status: str | None = None,
    scope: Mapping[str, Any] | None = None,
    advisory_only: bool | None = None,
    **_: Any,
) -> dict[str, Any]:
    history = [deepcopy(item) for item in locator_history or [] if isinstance(item, Mapping)]
    proposed_locator = deepcopy(locator_candidate) if isinstance(locator_candidate, Mapping) else None
    validation_payload = deepcopy(validation_result) if isinstance(validation_result, Mapping) else None

    if active_locator is not None:
        current_active_locator = _normalize_optional_text(active_locator)
    else:
        current_active_locator = None
        for history_item in history:
            candidate_ref = _normalize_optional_text(
                history_item.get("locator_ref")
                or history_item.get("candidate_id")
                or history_item.get("element_ref")
                or history_item.get("element_id")
            )
            if candidate_ref:
                current_active_locator = candidate_ref
                break

    normalized_validation_status = _normalize_optional_text(validation_status)
    validation_ok = None
    if validation_payload is not None:
        if "valid" in validation_payload:
            validation_ok = bool(validation_payload.get("valid"))
        elif "ok" in validation_payload:
            validation_ok = bool(validation_payload.get("ok"))
        elif "accepted" in validation_payload:
            validation_ok = bool(validation_payload.get("accepted"))
        elif _normalize_optional_text(validation_payload.get("status")) in {"valid", "accepted", "unique"}:
            validation_ok = True
        elif _normalize_optional_text(validation_payload.get("status")) in {"invalid", "rejected", "multiple", "hidden", "not_found"}:
            validation_ok = False

    if normalized_validation_status is None:
        if validation_ok is True:
            normalized_validation_status = "valid"
        elif validation_ok is False:
            normalized_validation_status = "invalid"
        elif validation_payload is not None:
            normalized_validation_status = _normalize_optional_text(validation_payload.get("status")) or "pending"
        else:
            normalized_validation_status = "pending"

    if validation_payload is None:
        command_status = "pending_validation"
    elif validation_ok is True:
        command_status = "validated"
    elif validation_ok is False:
        command_status = "rejected"
    else:
        command_status = "pending_validation"

    scope_payload = dict(scope or {}) if isinstance(scope, Mapping) else {}
    scope_payload.update(
        {
            "run_id": _normalize_optional_text(run_id),
            "step_id": _normalize_optional_text(step_id),
            "operation_id": _normalize_optional_text(operation_id),
            "parent_scope": _normalize_optional_text(parent_scope),
            "group_scope": _normalize_optional_text(group_scope),
            "operation_scope": _normalize_optional_text(operation_scope),
        }
    )

    return {
        "type": "update_locator",
        "command_id": _normalize_optional_text(command_id),
        "run_id": _normalize_optional_text(run_id),
        "step_id": _normalize_optional_text(step_id),
        "operation_id": _normalize_optional_text(operation_id),
        "reason": _normalize_optional_text(reason),
        "source": _normalize_optional_text(source),
        "user_hint": _normalize_optional_text(user_hint),
        "locator_candidate": proposed_locator,
        "replacement_locator": deepcopy(proposed_locator) if proposed_locator is not None else None,
        "locator_history": deepcopy(history),
        "previous_locator_history": deepcopy(history),
        "active_locator": current_active_locator,
        "scope": scope_payload,
        "backend_validation_required": True if backend_validation_required is None else bool(backend_validation_required),
        "validation_status": normalized_validation_status,
        "validation_result": validation_payload,
        "command_status": command_status,
        "advisory_only": True if advisory_only is None else bool(advisory_only),
        "execute": False,
        "applied": False,
        "mutation_allowed": False,
        "history_preserved": True,
        "validated_locator_ref": _normalize_optional_text(
            proposed_locator.get("candidate_id")
            if isinstance(proposed_locator, Mapping)
            else None
        )
        if validation_ok is True
        else None,
    }


_FIXTURE_REQUIREMENT_LIBRARY: dict[str, dict[str, Any]] = {
    "docs-style": {
        "fixture_class": "docs_style",
        "required_scenarios": ["sections", "code_blocks", "nav", "exact_text"],
        "expected_candidates": ["text_block", "link", "button"],
        "fixture_notes": "Playwright docs-style page",
    },
    "weak-div-span": {
        "fixture_class": "weak_dom",
        "required_scenarios": ["div/span ctas", "nested nodes", "duplicate sections"],
        "expected_candidates": ["ancestor_candidate", "section_scope", "scoped_text"],
        "fixture_notes": "Weak div/span page with nested targets",
    },
    "form-heavy": {
        "fixture_class": "form_heavy",
        "required_scenarios": ["labels", "placeholders", "validation", "upload gap"],
        "expected_candidates": ["label", "placeholder", "textbox", "button"],
        "fixture_notes": "Lead-magnet form page",
    },
    "modal-dropdown": {
        "fixture_class": "dynamic_state",
        "required_scenarios": ["dialog", "listbox", "toast", "loading"],
        "expected_candidates": ["dialog", "listbox", "alert", "status"],
        "fixture_notes": "Modal/dialog and portal dropdown page",
    },
    "table-card": {
        "fixture_class": "repeated_scope",
        "required_scenarios": ["repeated rows/cards", "scoped actions"],
        "expected_candidates": ["row_scope", "card_scope", "section_scope"],
        "fixture_notes": "Table/card dashboard page",
    },
    "semantic-accessibility": {
        "fixture_class": "semantic_accessibility",
        "required_scenarios": ["role/name/label/testid"],
        "expected_candidates": ["role+name", "label", "data-testid"],
        "fixture_notes": "Accessibility semantic page",
    },
}


def build_fixture_requirements(
    fixture_names: Sequence[str] | None = None,
    gap_needs: Sequence[str] | None = None,
    advisory_only: bool | None = None,
    **_: Any,
) -> dict[str, Any]:
    normalized_names = _normalize_list(fixture_names)
    normalized_gap_needs = _normalize_list(gap_needs)

    fixture_requirements: list[dict[str, Any]] = []
    for fixture_name in normalized_names:
        lookup_key = fixture_name.lower().replace("_", "-").replace(" ", "-")
        requirement = deepcopy(_FIXTURE_REQUIREMENT_LIBRARY.get(lookup_key) or {})
        if not requirement:
            requirement = {
                "fixture_class": "custom",
                "required_scenarios": [],
                "expected_candidates": [],
                "fixture_notes": fixture_name,
            }
        requirement["fixture_name"] = fixture_name
        requirement["advisory_only"] = True
        requirement["execute"] = False
        fixture_requirements.append(requirement)

    typed_gaps = [
        {
            "gap_name": gap_name,
            "classification": "capability_gap",
            "required": True,
            "advisory_only": True,
        }
        for gap_name in normalized_gap_needs
    ]

    return {
        "fixture_names": normalized_names,
        "fixture_requirements": fixture_requirements,
        "gap_needs": typed_gaps,
        "advisory_only": True if advisory_only is None else bool(advisory_only),
        "execute": False,
        "status": "fixture_requirement_proposal",
        "requires_live_sites": False,
    }


dom_snapshot = build_page_snapshot
snapshot_page = build_page_snapshot
build_dom_snapshot = build_page_snapshot

make_element_candidate = build_element_candidate
normalize_candidate = build_element_candidate
extract_element_candidate = build_element_candidate

rank_candidates = rank_locator_candidates
sort_locator_candidates = rank_locator_candidates
order_locator_candidates = rank_locator_candidates

validate_locator = validate_locator_candidate
browser_validate_locator = validate_locator_candidate
classify_locator_validation = validate_locator_candidate

select_scoped_candidates = scope_candidates
build_section_scope = scope_candidates
rank_scoped_candidates = scope_candidates

classify_assertion_target = classify_assertion_target
build_assertion_target_contract = classify_assertion_target
resolve_assertion_target = classify_assertion_target

classify_dynamic_ui_state = classify_dynamic_ui_state
detect_dynamic_ui_state = classify_dynamic_ui_state
build_dynamic_state_contract = classify_dynamic_ui_state

build_locator_escalation_request = build_locator_escalation_request
prepare_locator_specialist_request = build_locator_escalation_request
escalate_locator_specialist = build_locator_escalation_request

build_update_locator_command = build_update_locator_command
prepare_update_locator_command = build_update_locator_command
validate_update_locator_command = build_update_locator_command
apply_locator_update = build_update_locator_command

build_fixture_requirements = build_fixture_requirements
list_fixture_requirements = build_fixture_requirements
dom_fixture_requirements = build_fixture_requirements

__all__ = [
    "build_page_snapshot",
    "dom_snapshot",
    "snapshot_page",
    "build_dom_snapshot",
    "build_element_candidate",
    "make_element_candidate",
    "normalize_candidate",
    "extract_element_candidate",
    "rank_locator_candidates",
    "rank_candidates",
    "sort_locator_candidates",
    "order_locator_candidates",
    "validate_locator_candidate",
    "validate_locator",
    "browser_validate_locator",
    "classify_locator_validation",
    "scope_candidates",
    "select_scoped_candidates",
    "build_section_scope",
    "rank_scoped_candidates",
    "classify_assertion_target",
    "build_assertion_target_contract",
    "resolve_assertion_target",
    "classify_dynamic_ui_state",
    "detect_dynamic_ui_state",
    "build_dynamic_state_contract",
    "build_locator_escalation_request",
    "prepare_locator_specialist_request",
    "escalate_locator_specialist",
    "build_update_locator_command",
    "prepare_update_locator_command",
    "validate_update_locator_command",
    "apply_locator_update",
    "build_fixture_requirements",
    "list_fixture_requirements",
    "dom_fixture_requirements",
]
