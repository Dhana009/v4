from __future__ import annotations

import json
import re
from typing import Any


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
