"""Deterministic permission/risk classifier for agent actions.

Per scenarios spec §3.9 + Scenario 7 §12.
Pure heuristic: action name → risk enum + permission verdict
(auto | ask | deny) conditioned on autonomy_mode (strict | balanced | auto).
No I/O. No external imports beyond stdlib.
"""
from __future__ import annotations

# ---------------------------------------------------------------------------
# Public enum values
# ---------------------------------------------------------------------------
RISK_LABELS: tuple[str, ...] = (
    "safe_read_or_assert",
    "medium_browser_action",
    "high_risk_submit_upload_download",
    "destructive_or_external_side_effect",
    "requires_human_input",
)

# ---------------------------------------------------------------------------
# Internal rule tables
# ---------------------------------------------------------------------------

# Actions that are purely observational / read-only → always safe
_SAFE_PREFIXES: tuple[str, ...] = ("assert_", "read_", "wait_")
_SAFE_EXACT: frozenset[str] = frozenset({"screenshot"})

# Standard browser interaction verbs → medium risk
_MEDIUM_EXACT: frozenset[str] = frozenset(
    {"click", "type", "select", "hover", "scroll", "press_key"}
)

# High-risk transaction/upload/download verbs (prefix or exact match)
_HIGH_RISK_EXACT: frozenset[str] = frozenset(
    {"submit", "upload", "download", "pay", "purchase", "confirm_order"}
)
_HIGH_RISK_PREFIXES: tuple[str, ...] = (
    "submit_",
    "upload_",
    "download_",
    "pay_",
    "purchase_",
)

# Destructive or external side-effect verbs
_DESTRUCTIVE_EXACT: frozenset[str] = frozenset(
    {"delete", "wipe", "dispose", "external_send", "email_send", "slack_send"}
)
_DESTRUCTIVE_PREFIXES: tuple[str, ...] = (
    "delete_",
    "wipe_",
    "dispose_",
    "external_send_",
    "email_send_",
    "slack_send_",
)

# Keywords that signal the action requires free-text or credential input
_HUMAN_INPUT_KEYWORDS: tuple[str, ...] = (
    "input_",
    "credential",
    "password",
    "captcha",
    "otp",
    "mfa",
    "2fa",
    "secret",
    "token_entry",
    "free_text",
    "manual_",
    "human_",
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _normalise(action: dict) -> str:
    """Return a lower-cased, stripped action name from the action dict."""
    raw = action.get("name") or action.get("type") or action.get("action") or ""
    return str(raw).strip().lower()


def _matches_any_prefix(name: str, prefixes: tuple[str, ...]) -> bool:
    return any(name.startswith(p) for p in prefixes)


def _matches_any_keyword(name: str, keywords: tuple[str, ...]) -> bool:
    return any(kw in name for kw in keywords)


# ---------------------------------------------------------------------------
# Public classifier
# ---------------------------------------------------------------------------

def classify_action_risk(
    action: dict,
    autonomy_mode: str = "balanced",
) -> dict:
    """Classify the risk of a single action and return a permission verdict.

    Parameters
    ----------
    action:
        Dict with at least a ``name`` (or ``type`` / ``action``) key describing
        the action to be taken.
    autonomy_mode:
        One of ``"strict"``, ``"balanced"``, ``"auto"``.

    Returns
    -------
    dict with keys:
        - ``risk``       : one of the values in ``RISK_LABELS``
        - ``permission`` : ``"auto"`` | ``"ask"`` | ``"deny"``
        - ``reasons``    : list of str explaining the verdict
    """
    mode = str(autonomy_mode or "balanced").strip().lower()
    name = _normalise(action)

    # ------------------------------------------------------------------
    # Rule 1: requires_human_input  (checked before other rules so that
    # credential/captcha actions are always escalated regardless of verb)
    # ------------------------------------------------------------------
    if _matches_any_keyword(name, _HUMAN_INPUT_KEYWORDS):
        return {
            "risk": "requires_human_input",
            "permission": "ask",
            "reasons": [
                f"Action '{name}' contains a keyword indicating free-text or "
                "credential input is needed; human confirmation required."
            ],
        }

    # ------------------------------------------------------------------
    # Rule 2: destructive / external side-effect → always deny
    # ------------------------------------------------------------------
    if name in _DESTRUCTIVE_EXACT or _matches_any_prefix(name, _DESTRUCTIVE_PREFIXES):
        return {
            "risk": "destructive_or_external_side_effect",
            "permission": "deny",
            "reasons": [
                f"Action '{name}' is classified as destructive or has an external "
                "side-effect; denied regardless of autonomy_mode."
            ],
        }

    # ------------------------------------------------------------------
    # Rule 3: safe read / assert / wait / screenshot → always auto
    # ------------------------------------------------------------------
    if name in _SAFE_EXACT or _matches_any_prefix(name, _SAFE_PREFIXES):
        return {
            "risk": "safe_read_or_assert",
            "permission": "auto",
            "reasons": [
                f"Action '{name}' is a read-only or assertion action; safe to run automatically."
            ],
        }

    # ------------------------------------------------------------------
    # Rule 4: high-risk submit / upload / download / pay / purchase
    # ------------------------------------------------------------------
    if name in _HIGH_RISK_EXACT or _matches_any_prefix(name, _HIGH_RISK_PREFIXES):
        if mode == "strict":
            permission = "deny"
            reasons = [
                f"Action '{name}' is high-risk; denied in strict autonomy_mode."
            ]
        else:
            # balanced or auto
            permission = "ask"
            reasons = [
                f"Action '{name}' is high-risk; requires confirmation in {mode!r} autonomy_mode."
            ]
        return {
            "risk": "high_risk_submit_upload_download",
            "permission": permission,
            "reasons": reasons,
        }

    # ------------------------------------------------------------------
    # Rule 5: medium browser interaction
    # ------------------------------------------------------------------
    if name in _MEDIUM_EXACT or _matches_any_prefix(name, ("click_", "type_", "select_", "hover_", "scroll_", "press_")):
        if mode == "strict":
            permission = "ask"
            reasons = [
                f"Action '{name}' is a browser interaction; requires confirmation in strict autonomy_mode."
            ]
        else:
            permission = "auto"
            reasons = [
                f"Action '{name}' is a standard browser interaction; auto-permitted in {mode!r} autonomy_mode."
            ]
        return {
            "risk": "medium_browser_action",
            "permission": permission,
            "reasons": reasons,
        }

    # ------------------------------------------------------------------
    # Fallback: unknown action — treat as medium browser action with the
    # same mode-conditioned logic so the caller always gets a verdict.
    # ------------------------------------------------------------------
    if mode == "strict":
        permission = "ask"
        reasons = [
            f"Action '{name}' is unrecognised; defaulting to ask in strict autonomy_mode."
        ]
    elif mode == "auto":
        permission = "auto"
        reasons = [
            f"Action '{name}' is unrecognised; defaulting to auto in auto autonomy_mode."
        ]
    else:
        permission = "ask"
        reasons = [
            f"Action '{name}' is unrecognised; defaulting to ask in balanced autonomy_mode."
        ]

    return {
        "risk": "medium_browser_action",
        "permission": permission,
        "reasons": reasons,
    }
