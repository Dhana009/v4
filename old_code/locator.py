from __future__ import annotations

import re
from typing import Any


def _css_escape(value: str) -> str:
    # Minimal CSS string escape for attribute values.
    return value.replace("\\", "\\\\").replace('"', '\\"')


def _normalize_space(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip()


def find_best_locator(element_info: dict | None, locator_hint: str | None) -> str:
    """
    Returns a single best selector string.

    Priority (when element_info present): data-testid -> aria-label -> id -> text -> css fallback.
    If element_info is missing, uses locator_hint to produce a best-effort text/role-ish locator.
    """
    if element_info:
        attrs: dict[str, Any] = element_info.get("attributes") or {}

        dtid = attrs.get("data-testid")
        if isinstance(dtid, str) and dtid.strip():
            v = _css_escape(dtid.strip())
            return f'[data-testid="{v}"]'

        aria = attrs.get("aria-label")
        if isinstance(aria, str) and aria.strip():
            v = _css_escape(_normalize_space(aria))
            return f'[aria-label="{v}"]'

        el_id = element_info.get("id")
        if isinstance(el_id, str) and el_id.strip():
            # Prefer id as a direct CSS id selector.
            return f"#{_css_escape(el_id.strip())}"

        text = element_info.get("text")
        if isinstance(text, str) and _normalize_space(text):
            v = _css_escape(_normalize_space(text))
            # Playwright text selector engine.
            return f'text="{v}"'

        tag = element_info.get("tag") or "*"
        cls = element_info.get("class") or ""
        classes = [c for c in str(cls).split() if c]
        if classes:
            safe_classes = [re.sub(r"[^a-zA-Z0-9_-]", "", c) for c in classes[:3]]
            safe_classes = [c for c in safe_classes if c]
            if safe_classes:
                return f"{tag}." + ".".join(safe_classes)

        return str(tag)

    hint = (locator_hint or "").strip()
    if hint:
        v = _css_escape(_normalize_space(hint))
        return f'text="{v}"'

    return "*"

