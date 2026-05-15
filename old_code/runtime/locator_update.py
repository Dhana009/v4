"""
runtime/locator_update.py

Locator update flow: user-requested locator update with history preservation
and wrong-page precondition check.

Source rule: S6-0607/0608 — every LLM locator is backend-validated.
Locator update preserves old locator history. Wrong-page update blocked.

Modularization rule: policy logic in focused runtime/ modules, not agent.py.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class LocatorHistory:
    step_id: str
    locator_versions: list[dict[str, Any]]  # each: {"locator": str, "version": int}


@dataclass
class LocatorUpdateRequest:
    step_id: str
    new_locator: str
    reason: str
    current_page: str
    required_page: str


@dataclass
class LocatorUpdateResult:
    updated: bool
    history: LocatorHistory
    error: str | None = None


@dataclass
class LocatorPreconditionResult:
    blocked: bool
    reason: str | None


def check_locator_update_precondition(req: LocatorUpdateRequest) -> LocatorPreconditionResult:
    """Check if current page satisfies the locator update's required page."""
    if req.current_page != req.required_page:
        return LocatorPreconditionResult(
            blocked=True,
            reason=f"Locator update requires page '{req.required_page}' but current is '{req.current_page}'",
        )
    return LocatorPreconditionResult(blocked=False, reason=None)


def process_locator_update(
    req: LocatorUpdateRequest,
    history: LocatorHistory,
) -> LocatorUpdateResult:
    """Process a locator update request.

    Preserves existing locator history, appends new version.
    Validates precondition (page must match).
    """
    check = check_locator_update_precondition(req)
    if check.blocked:
        return LocatorUpdateResult(
            updated=False,
            history=history,
            error=check.reason,
        )

    # Append new version preserving all old ones
    new_version = len(history.locator_versions) + 1
    updated_versions = list(history.locator_versions) + [
        {"locator": req.new_locator, "version": new_version, "reason": req.reason}
    ]
    updated_history = LocatorHistory(
        step_id=req.step_id,
        locator_versions=updated_versions,
    )
    return LocatorUpdateResult(
        updated=True,
        history=updated_history,
    )
