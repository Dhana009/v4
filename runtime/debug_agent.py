"""
runtime/debug_agent.py

Deterministic Debug Report builder — PRD 07 §3 Debug Agent.

Inputs : failed_step dict  +  page_state dict  +  recent_events list  +
         optional failure_label string.
Outputs: DebugReport(hypothesis, evidence, suggested_repair, confidence,
         agent_invocation_id).

Design constraints
──────────────────
- Pure / stdlib-only.  No I/O, no LLM call.
- Optional import of runtime.failure_classifier.FailureType inside try/except
  so this module loads when failure_classifier is absent.
- Always produces a report even for sparse inputs (fallback hypothesis,
  confidence 0.0, empty repair dict).
- LLM-backed variant routes through controller.call(purpose="debug_agent")
  in a follow-up wire-in slice.
"""
from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Any

# ---------------------------------------------------------------------------
# Optional: import FailureType enum for normalised label lookup
# ---------------------------------------------------------------------------
try:
    from runtime.failure_classifier import FailureType as _FailureType  # type: ignore
    _FAILURE_TYPE_VALUES: frozenset[str] = frozenset(ft.value for ft in _FailureType)
except Exception:  # noqa: BLE001
    _FailureType = None  # type: ignore[assignment]
    _FAILURE_TYPE_VALUES = frozenset()


# ---------------------------------------------------------------------------
# Public data contract
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class DebugReport:
    """Structured debug report produced by the deterministic debug agent."""

    hypothesis: str
    evidence: list[str]
    suggested_repair: dict[str, Any]
    confidence: float
    agent_invocation_id: str | None = None


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

# Maps normalised failure_label substrings → (hypothesis template, repair kind)
_LABEL_RULES: list[tuple[str, str, str]] = [
    # (substring_in_label,  hypothesis_template,        repair_kind)
    ("locator_not_found",   "Locator could not be resolved on the current page",   "locator_replacement"),
    ("element_not_found",   "Locator could not be resolved on the current page",   "locator_replacement"),
    ("timeout",             "Step timed out waiting for element or navigation",     "increase_timeout"),
    ("network_error",       "A network error prevented the step from completing",   "retry_with_backoff"),
    ("navigation_error",    "Navigation to the required URL failed",                "wait_for_navigation"),
    ("assertion_failure",   "A page assertion did not match the expected value",    "assertion_relaxation"),
    ("permission_denied",   "Action was blocked due to insufficient permissions",   "permission_escalation"),
    ("wrong_url",           "Page URL does not match the URL required by the step", "wait_for_navigation"),
    ("stale_element",       "Element reference became stale during execution",      "locator_replacement"),
]

_DEFAULT_CANDIDATE_STRATEGIES = ["role+name", "label-for", "placeholder", "css-id", "aria-label", "text-content", "xpath"]


def _normalise_label(label: str | None) -> str:
    """Return lowercase, underscore-normalised failure label."""
    if not label:
        return ""
    return label.strip().lower().replace("-", "_").replace(" ", "_")


def _url_mismatch(page_state: dict, failed_step: dict) -> bool:
    """True when page URL and step's required_url differ meaningfully."""
    page_url: str = str(page_state.get("url", "")).rstrip("/")
    required_url: str = str(failed_step.get("required_url", "")).rstrip("/")
    return bool(required_url) and page_url != required_url


def _last_event_types(recent_events: list[dict], n: int = 5) -> list[str]:
    """Return up to n most recent event type strings."""
    return [
        str(ev.get("type", "unknown"))
        for ev in recent_events[-n:]
    ]


def _confidence_from_evidence(evidence: list[str]) -> float:
    """Scale confidence 0.40–0.85 by evidence count (capped)."""
    n = min(len(evidence), 5)
    if n == 0:
        return 0.0
    # 1 item → 0.40, each additional item adds 0.09, max 5 items → 0.76 → cap 0.85
    raw = 0.40 + (n - 1) * 0.09
    return round(min(raw, 0.85), 4)


def _build_locator_repair(failed_step: dict) -> dict[str, Any]:
    locator = failed_step.get("locator") or failed_step.get("selector") or failed_step.get("target") or ""
    return {
        "kind": "locator_replacement",
        "current": locator,
        "candidate_strategies": _DEFAULT_CANDIDATE_STRATEGIES,
    }


def _build_navigation_repair(failed_step: dict) -> dict[str, Any]:
    return {
        "kind": "wait_for_navigation",
        "url": failed_step.get("required_url", ""),
    }


def _build_repair_for_kind(kind: str, failed_step: dict, page_state: dict) -> dict[str, Any]:
    if kind == "locator_replacement":
        return _build_locator_repair(failed_step)
    if kind in ("wait_for_navigation",):
        return _build_navigation_repair(failed_step)
    if kind == "increase_timeout":
        current_timeout = failed_step.get("timeout_ms") or failed_step.get("timeout") or 5000
        return {
            "kind": "increase_timeout",
            "current_timeout_ms": current_timeout,
            "suggested_timeout_ms": int(current_timeout) * 2,
        }
    if kind == "retry_with_backoff":
        return {
            "kind": "retry_with_backoff",
            "max_retries": 3,
            "backoff_ms": 1000,
        }
    if kind == "assertion_relaxation":
        return {
            "kind": "assertion_relaxation",
            "note": "consider contains() or partial match instead of exact equality",
        }
    if kind == "permission_escalation":
        return {
            "kind": "permission_escalation",
            "note": "step requires elevated permissions; check auth state",
        }
    # generic fallback
    return {"kind": kind}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def build_debug_report(
    failed_step: dict[str, Any],
    page_state: dict[str, Any],
    recent_events: list[dict[str, Any]],
    failure_label: str | None = None,
) -> DebugReport:
    """Build a deterministic DebugReport from available context.

    Heuristic priority
    ──────────────────
    1. failure_label  (explicit classification from failure_classifier)
    2. URL mismatch   (page_state.url vs failed_step.required_url)
    3. Recent event types (step_failed / navigation_failed / timeout, etc.)
    4. Fallback       (unknown failure; insufficient evidence)

    Parameters
    ----------
    failed_step:
        Dict describing the step that failed.  Recognised keys:
        ``step_id``, ``required_url``, ``locator``/``selector``/``target``,
        ``timeout_ms``.
    page_state:
        Current browser page state.  Recognised keys: ``url``, ``title``.
    recent_events:
        Ordered list of recent runtime event dicts (``type`` + ``payload``).
    failure_label:
        Optional string from failure_classifier (e.g. ``"locator_not_found"``).
        Values matching FailureType.value enum members are accepted directly.

    Returns
    -------
    DebugReport
        Always returns a valid report even when inputs are sparse.
    """
    evidence: list[str] = []
    hypothesis: str = ""
    repair_kind: str = ""

    norm_label = _normalise_label(failure_label)

    # ── Pass 1: failure_label ────────────────────────────────────────────────
    if norm_label:
        for substring, hyp_template, r_kind in _LABEL_RULES:
            if substring in norm_label:
                hypothesis = hyp_template
                repair_kind = r_kind
                evidence.append(f"failure_label={failure_label!r} matched rule '{substring}'")
                break

    # ── Pass 2: URL mismatch ─────────────────────────────────────────────────
    if _url_mismatch(page_state, failed_step):
        page_url = page_state.get("url", "")
        req_url = failed_step.get("required_url", "")
        evidence.append(
            f"URL mismatch: page is {page_url!r}, step requires {req_url!r}"
        )
        if not hypothesis:
            hypothesis = "Page URL does not match the URL required by the step"
            repair_kind = "wait_for_navigation"

    # ── Pass 3: recent event type scan ───────────────────────────────────────
    event_types = _last_event_types(recent_events)
    if event_types:
        evidence.append(f"last event types: {event_types}")

    for ev_type in event_types:
        ev_lower = ev_type.lower()
        if "timeout" in ev_lower and not hypothesis:
            hypothesis = "Step timed out waiting for element or navigation"
            repair_kind = "increase_timeout"
            evidence.append(f"timeout signal in event type {ev_type!r}")
            break
        if ("navigation" in ev_lower or "navigate" in ev_lower) and not hypothesis:
            hypothesis = "Navigation event suggests wrong page at time of step execution"
            repair_kind = "wait_for_navigation"
            evidence.append(f"navigation signal in event type {ev_type!r}")
            break
        if ("locator" in ev_lower or "element" in ev_lower or "selector" in ev_lower) and not hypothesis:
            hypothesis = "Locator could not be resolved on the current page"
            repair_kind = "locator_replacement"
            evidence.append(f"locator/element signal in event type {ev_type!r}")
            break

    # Inspect step_failed payload reason for additional evidence
    for ev in reversed(recent_events):
        if str(ev.get("type", "")) == "step_failed":
            payload = ev.get("payload", {}) or {}
            reason = str(payload.get("reason", "")).strip()
            if reason:
                evidence.append(f"step_failed reason: {reason!r}")
                # Use reason text to refine if still no hypothesis
                reason_lower = reason.lower()
                if not hypothesis:
                    if "locator" in reason_lower or "not found" in reason_lower or "element" in reason_lower:
                        hypothesis = "Locator could not be resolved on the current page"
                        repair_kind = "locator_replacement"
                    elif "timeout" in reason_lower or "timed out" in reason_lower:
                        hypothesis = "Step timed out waiting for element or navigation"
                        repair_kind = "increase_timeout"
                    elif "network" in reason_lower:
                        hypothesis = "A network error prevented the step from completing"
                        repair_kind = "retry_with_backoff"
            break  # only most recent step_failed event

    # ── Pass 4: fallback ─────────────────────────────────────────────────────
    if not hypothesis:
        return DebugReport(
            hypothesis="unknown failure; insufficient evidence",
            evidence=evidence,
            suggested_repair={},
            confidence=0.0,
        )

    # Build suggested_repair dict from repair_kind
    suggested_repair = _build_repair_for_kind(repair_kind, failed_step, page_state)

    confidence = _confidence_from_evidence(evidence)

    return DebugReport(
        hypothesis=hypothesis,
        evidence=evidence,
        suggested_repair=suggested_repair,
        confidence=confidence,
    )


def serialize_debug_report(report: DebugReport) -> dict[str, Any]:
    """Convert a DebugReport to an envelope-friendly plain dict."""
    d = asdict(report)
    # ensure evidence is a plain list (asdict already does this, but be explicit)
    d["evidence"] = list(d.get("evidence", []))
    return d
