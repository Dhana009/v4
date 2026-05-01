from __future__ import annotations

from typing import Any


async def execute_action(page: Any, action: dict) -> dict:
    """
    action: { locator: str, action_type: str, value?: str }
    returns: { success: bool, error: str }
    """
    try:
        action_type = (action.get("action_type") or "").strip()
        locator = (action.get("locator") or "").strip()
        value = action.get("value")

        if action_type == "navigate":
            if not isinstance(value, str) or not value.strip():
                return {"success": False, "error": "navigate requires non-empty value (URL)"}
            await page.goto(value.strip())
            return {"success": True, "error": ""}

        if action_type == "click":
            if not locator:
                return {"success": False, "error": "click requires locator"}
            await page.locator(locator).first.click()
            return {"success": True, "error": ""}

        if action_type == "fill":
            if not locator:
                return {"success": False, "error": "fill requires locator"}
            if value is None:
                value = ""
            await page.locator(locator).first.fill(str(value))
            return {"success": True, "error": ""}

        return {"success": False, "error": f"unsupported action_type: {action_type!r}"}
    except Exception as e:  # noqa: BLE001
        return {"success": False, "error": f"{type(e).__name__}: {e}"}

