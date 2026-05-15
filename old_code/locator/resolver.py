from __future__ import annotations

import json
import re
from typing import Any

from runtime.dom_locator_contract import build_locator_escalation_request


class LocatorResolver:
    """Pure-function helpers for building and resolving Playwright locators.

    All methods are stateless; no constructor parameters are needed.
    AgentLoop holds a single shared instance and delegates to it.
    """

    # ------------------------------------------------------------------
    # String / escape helpers
    # ------------------------------------------------------------------

    def css_escape(self, value: str) -> str:
        return value.replace("\\", "\\\\").replace('"', '\\"')

    def text_escape(self, value: str) -> str:
        return value.replace("\\", "\\\\").replace('"', '\\"')

    def normalize_space(self, value: str) -> str:
        return re.sub(r"\s+", " ", value).strip()

    def normalize_assertion_text(self, value: str | None) -> str:
        if value is None:
            return ""
        normalized = str(value)
        normalized = normalized.replace("&nbsp;", " ")
        normalized = normalized.replace(" ", " ")
        normalized = normalized.replace(" ", " ")
        normalized = normalized.replace(" ", " ")
        normalized = normalized.replace("\u0000", "")
        normalized = re.sub(r"[\x01-\x08\x0b\x0c\x0e-\x1f\x7f]", "", normalized)
        normalized = re.sub(r"\s+", " ", normalized)
        return normalized.strip()

    def tool_string_escape(self, value: str) -> str:
        return value.replace("\\", "\\\\").replace('"', '\\"')

    def tool_string_unescape(self, value: str) -> str:
        return value.replace('\\"', '"').replace("\\\\", "\\")

    def xpath_literal(self, value: str) -> str:
        if "'" not in value:
            return f"'{value}'"
        if '"' not in value:
            return f'"{value}"'
        parts = value.split("'")
        quoted_parts = [f"'{part}'" for part in parts]
        return 'concat(' + ', "\'", '.join(quoted_parts) + ')'

    # ------------------------------------------------------------------
    # Markup helpers
    # ------------------------------------------------------------------

    def clean_markup(self, html: str) -> str:
        cleaned = html or ""
        for tag in ("style", "script", "svg"):
            cleaned = re.sub(
                rf"<{tag}\b[^>]*>.*?</{tag}>",
                "",
                cleaned,
                flags=re.IGNORECASE | re.DOTALL,
            )
        cleaned = re.sub(r"\s+", " ", cleaned).strip()
        return cleaned

    def summarize(self, value: Any, limit: int = 100) -> str:
        if isinstance(value, dict):
            if "elements" in value:
                text = str(value.get("elements") or "")
            elif "message" in value:
                text = str(value.get("message") or "")
            else:
                text = json.dumps(value, ensure_ascii=True)
        else:
            text = json.dumps(value, ensure_ascii=True) if not isinstance(value, str) else value
        text = text.replace("\n", " ").strip()
        return text[:limit]

    # ------------------------------------------------------------------
    # Locator-building helpers
    # ------------------------------------------------------------------

    def build_locator_from_strategy(self, strategy: str, element_data: dict[str, Any]) -> str:
        tag = str(element_data.get("tag") or "*").strip() or "*"
        text = self.normalize_space(str(element_data.get("text") or ""))
        element_id = str(element_data.get("id") or "").strip()
        class_name = str(element_data.get("class") or "").strip()
        aria_label = self.normalize_space(str(element_data.get("aria_label") or ""))
        data_testid = str(element_data.get("data_testid") or "").strip()
        placeholder = self.normalize_space(str(element_data.get("placeholder") or ""))
        parent_tag = str(element_data.get("parent_tag") or "").strip()
        parent_id = str(element_data.get("parent_id") or "").strip()

        if strategy == "data_testid" and data_testid:
            return f'[data-testid="{self.css_escape(data_testid)}"]'
        if strategy == "aria_label" and aria_label:
            return f'[aria-label="{self.css_escape(aria_label)}"]'
        if strategy == "id" and element_id:
            return f"#{self.css_escape(element_id)}"
        if strategy == "placeholder" and placeholder:
            return f'[placeholder="{self.css_escape(placeholder)}"]'
        if strategy == "exact_text" and text:
            return f'text="{self.text_escape(text)}"'
        if strategy == "partial_text" and text:
            partial = text[:80].strip()
            return f"text={self.text_escape(partial)}"
        if strategy == "css":
            tag_part = re.sub(r"[^a-zA-Z0-9:_-]", "", tag) or "*"
            classes = [
                re.sub(r"[^a-zA-Z0-9_-]", "", item)
                for item in class_name.split()
                if re.sub(r"[^a-zA-Z0-9_-]", "", item)
            ]
            base = tag_part
            if classes:
                base += "." + ".".join(classes[:3])
            if parent_id:
                return f"#{self.css_escape(parent_id)} {base}"
            if parent_tag:
                parent = re.sub(r"[^a-zA-Z0-9:_-]", "", parent_tag)
                if parent:
                    return f"{parent} {base}"
            return base
        return ""

    def is_stable_locator_strategy(self, strategy: str) -> bool:
        return strategy in {"data-testid", "aria-label", "id", "role+name"}

    def infer_role(self, element_data: dict[str, Any]) -> str:
        explicit_role = str(element_data.get("role") or "").strip()
        if explicit_role:
            return explicit_role

        tag = str(element_data.get("tag") or "").strip().lower()
        input_type = str(element_data.get("type") or "").strip().lower()

        if tag == "button":
            return "button"
        if tag == "a":
            return "link"
        if tag == "select":
            return "combobox"
        if tag == "textarea":
            return "textbox"
        if tag in {"h1", "h2", "h3", "h4", "h5", "h6"}:
            return "heading"
        if tag == "input":
            if input_type in {"button", "submit", "reset"}:
                return "button"
            if input_type in {"checkbox"}:
                return "checkbox"
            if input_type in {"radio"}:
                return "radio"
            return "textbox"
        return ""

    # ------------------------------------------------------------------
    # Locator-matching helpers (used by resolve_locator)
    # ------------------------------------------------------------------

    def match_tool_locator_call(self, locator: str, function_name: str) -> str:
        locator = str(locator or "").strip()
        if not locator:
            return ""

        for quote in ('"', "'"):
            pattern = rf"{re.escape(function_name)}\({quote}((?:\\.|[^{quote}])*){quote}\)"
            if match := re.fullmatch(pattern, locator):
                return self.tool_string_unescape(match.group(1))
        return ""

    def match_tool_locator_text(self, locator: str) -> tuple[str, bool] | None:
        locator = str(locator or "").strip()
        if not locator:
            return None

        for quote in ('"', "'"):
            pattern = rf"get_by_text\({quote}((?:\\.|[^{quote}])*){quote}, exact=(True|False)\)"
            if match := re.fullmatch(pattern, locator):
                return self.tool_string_unescape(match.group(1)), match.group(2) == "True"
        return None

    def match_tool_locator_role(self, locator: str) -> tuple[str, str] | None:
        locator = str(locator or "").strip()
        if not locator:
            return None

        for quote in ('"', "'"):
            pattern = rf"get_by_role\({quote}((?:\\.|[^{quote}])*){quote}, name={quote}((?:\\.|[^{quote}])*){quote}\)"
            if match := re.fullmatch(pattern, locator):
                return (
                    self.tool_string_unescape(match.group(1)),
                    self.tool_string_unescape(match.group(2)),
                )
        return None

    # ------------------------------------------------------------------
    # Locator resolution
    # ------------------------------------------------------------------

    def resolve_locator(self, page: Any, locator_string: str) -> Any:
        locator_string = str(locator_string or "").strip()
        if not locator_string:
            raise ValueError("locator is required")

        if match := self.match_tool_locator_call(locator_string, "get_by_test_id"):
            return page.get_by_test_id(match)

        if match := self.match_tool_locator_call(locator_string, "get_by_label"):
            return page.get_by_label(match)

        if match := self.match_tool_locator_call(locator_string, "get_by_placeholder"):
            return page.get_by_placeholder(match)

        if match := self.match_tool_locator_text(locator_string):
            return page.get_by_text(match[0], exact=match[1])

        if match := self.match_tool_locator_role(locator_string):
            return page.get_by_role(match[0], name=match[1])

        return page.locator(locator_string)

    def build_locator_candidates(self, element_data: dict[str, Any]) -> list[dict[str, str]]:
        """Build deterministic locator candidates in scenarios §3.10 order.

        Order: role+name → testid → label-for → placeholder → text/has_text →
               title → alt → css-stable.
        XPath is intentionally excluded from the programmatic layer; it is
        emitted only if the LLM proposes it (LLM-only path).
        """
        # ------------------------------------------------------------------
        # Resolve raw element fields
        # ------------------------------------------------------------------
        text_raw = str(element_data.get("text") or element_data.get("innerText") or "").strip()
        text = self.normalize_space(text_raw)
        tag = re.sub(r"[^a-zA-Z0-9:_-]", "", str(element_data.get("tag") or "").strip()).lower()
        attributes: dict[str, Any] = (
            element_data.get("attributes")
            if isinstance(element_data.get("attributes"), dict)
            else {}
        )
        role = (
            self.normalize_space(
                str(element_data.get("role") or attributes.get("role") or "")
            )
            or self.infer_role(element_data)
        )

        class_name = str(
            element_data.get("class")
            or element_data.get("className")
            or attributes.get("class")
            or ""
        ).strip()

        partial_text = text[:80].strip()
        candidates: list[dict[str, str]] = []

        # ------------------------------------------------------------------
        # 0. Locator hint (pass-through; highest priority)
        # ------------------------------------------------------------------
        locator_hint = str(
            element_data.get("locator_hint") or element_data.get("locatorHint") or ""
        ).strip()
        if locator_hint:
            candidates.append({"strategy": "locator_hint", "locator": locator_hint})

        # ------------------------------------------------------------------
        # §3.10 Priority 1 — role + accessible name
        # ------------------------------------------------------------------
        if role and partial_text:
            candidates.append(
                {
                    "strategy": "role+name",
                    "locator": (
                        f'get_by_role("{self.tool_string_escape(role)}", '
                        f'name="{self.tool_string_escape(partial_text)}")'
                    ),
                }
            )

        # ------------------------------------------------------------------
        # §3.10 Priority 2 — test-id attributes (data-testid family)
        # ------------------------------------------------------------------
        data_testid = str(
            element_data.get("data_testid")
            or element_data.get("dataTestid")
            or attributes.get("data-testid")
            or attributes.get("data-test-id")
            or attributes.get("data-test")
            or attributes.get("data-qa")
            or attributes.get("data-cy")
            or attributes.get("data-automation-id")
            or ""
        ).strip()
        if data_testid:
            candidates.append(
                {
                    "strategy": "data-testid",
                    "locator": f'get_by_test_id("{self.tool_string_escape(data_testid)}")',
                }
            )

        # ------------------------------------------------------------------
        # §3.10 Priority 3 — label association
        #   (a) aria-label → get_by_label (ARIA association)
        #   (b) label_for_text → get_by_label (true <label for="id"> association)
        #   (c) name attribute → [name="…"] CSS candidate for form inputs
        # ------------------------------------------------------------------
        aria_label = self.normalize_space(
            str(
                element_data.get("aria_label")
                or element_data.get("ariaLabel")
                or attributes.get("aria-label")
                or ""
            )
        )
        if aria_label:
            candidates.append(
                {
                    "strategy": "aria-label",
                    "locator": f'get_by_label("{self.tool_string_escape(aria_label)}")',
                }
            )

        # True <label for="id">text</label> association derived by page intelligence
        label_for_text = self.normalize_space(
            str(
                element_data.get("label_for_text")
                or element_data.get("labelForText")
                or element_data.get("label_text")
                or ""
            )
        )
        if label_for_text and label_for_text != aria_label:
            candidates.append(
                {
                    "strategy": "label-for",
                    "locator": f'get_by_label("{self.tool_string_escape(label_for_text)}")',
                }
            )

        # name attribute — form inputs (text strategy augmentation per PRD §3.10)
        name_attr = str(attributes.get("name") or element_data.get("name_attr") or "").strip()
        if name_attr and tag in {"input", "select", "textarea", "button"}:
            candidates.append(
                {
                    "strategy": "name-attr",
                    "locator": f'[name="{self.css_escape(name_attr)}"]',
                }
            )

        # ------------------------------------------------------------------
        # §3.10 Priority 4 — placeholder
        # ------------------------------------------------------------------
        placeholder = self.normalize_space(
            str(element_data.get("placeholder") or attributes.get("placeholder") or "")
        )
        if placeholder:
            candidates.append(
                {
                    "strategy": "placeholder",
                    "locator": f'get_by_placeholder("{self.tool_string_escape(placeholder)}")',
                }
            )

        # ------------------------------------------------------------------
        # §3.10 Priority 5 — text / has_text
        # ------------------------------------------------------------------
        if text:
            candidates.append(
                {
                    "strategy": "exact_text",
                    "locator": f'get_by_text("{self.tool_string_escape(text)}", exact=True)',
                }
            )

        if partial_text and partial_text != text:
            candidates.append(
                {
                    "strategy": "partial_text",
                    "locator": f'get_by_text("{self.tool_string_escape(partial_text)}", exact=False)',
                }
            )

        # ------------------------------------------------------------------
        # §3.10 Priority 6 — title attribute
        # ------------------------------------------------------------------
        title_attr = self.normalize_space(
            str(element_data.get("title") or attributes.get("title") or "")
        )
        if title_attr:
            candidates.append(
                {
                    "strategy": "title",
                    "locator": f'[title="{self.css_escape(title_attr)}"]',
                }
            )

        # ------------------------------------------------------------------
        # §3.10 Priority 7 — alt text (images)
        # ------------------------------------------------------------------
        alt_text = self.normalize_space(
            str(element_data.get("alt") or attributes.get("alt") or "")
        )
        if alt_text and tag in {"img", "area", "input"}:
            candidates.append(
                {
                    "strategy": "alt-text",
                    "locator": f'get_by_alt_text("{self.tool_string_escape(alt_text)}")',
                }
            )

        # ------------------------------------------------------------------
        # §3.10 Priority 8 — stable CSS (id → class combo)
        # ------------------------------------------------------------------
        element_id = str(element_data.get("id") or attributes.get("id") or "").strip()
        if element_id:
            candidates.append(
                {"strategy": "id", "locator": f"#{self.css_escape(element_id)}"}
            )

        css_locator = self.build_locator_from_strategy("css", element_data)
        if css_locator:
            candidates.append({"strategy": "css", "locator": css_locator})

        # NOTE: XPath is intentionally NOT emitted here (PRD lines 681–686:
        # "Never proactively generated"). XPath is only attached after LLM
        # proposes it via the escalation path.

        return candidates

    def build_locator_candidates_with_escalation(
        self,
        element_data: dict[str, Any],
        *,
        target_text: str | None = None,
        page_context: dict[str, Any] | None = None,
    ) -> tuple[list[dict[str, str]], dict[str, Any] | None]:
        """Return (candidates, escalation_payload).

        escalation_payload is non-None only if the caller has exhausted all
        candidates and needs LLM-specialist help.  The caller is responsible
        for emitting the ``locator_update_request`` event; this method only
        *builds* the payload — it does not emit anything.

        Typical usage::

            candidates, escalation = resolver.build_locator_candidates_with_escalation(
                element_data, target_text=text, page_context=page_ctx
            )
            # … iterate candidates; if none found:
            if escalation:
                emit("locator_update_request", escalation)
        """
        candidates = self.build_locator_candidates(element_data)
        escalation = build_locator_escalation_request(
            target_text=target_text or str(element_data.get("text") or "").strip() or None,
            candidates=[
                {"candidate_id": c["strategy"], "locator": c["locator"]}
                for c in candidates
            ],
            page_context=page_context,
            advisory_only=True,
        )
        return candidates, escalation
