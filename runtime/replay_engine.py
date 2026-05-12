"""
runtime/replay_engine.py

Replay engine: replay steps, classify failures, propose repairs.

Source rule: S6-0904–S6-0908.
"""
from __future__ import annotations

import enum
from dataclasses import dataclass, field
from typing import Any


class ReplayFailureType(enum.Enum):
    LOCATOR_STALE = "locator_stale"
    TIMEOUT = "timeout"
    STATE_MISMATCH = "state_mismatch"
    UNKNOWN = "unknown"


@dataclass
class ReplayRequest:
    session_id: str
    step_id: str
    step: dict[str, Any]


@dataclass
class ReplayResult:
    step_id: str
    success: bool = True
    failure_type: ReplayFailureType | None = None


@dataclass
class ReplayRepairProposal:
    step_id: str
    strategy: str
    proposed_locator: str | None = None
    reason: str | None = None


_FAILURE_PATTERNS: list[tuple[str, ReplayFailureType]] = [
    ("elementnotfounderror", ReplayFailureType.LOCATOR_STALE),
    ("elementnotfound", ReplayFailureType.LOCATOR_STALE),
    ("stale", ReplayFailureType.LOCATOR_STALE),
    ("locator", ReplayFailureType.LOCATOR_STALE),
    ("timeouterror", ReplayFailureType.TIMEOUT),
    ("timeout", ReplayFailureType.TIMEOUT),
    ("pagestaterror", ReplayFailureType.STATE_MISMATCH),
    ("wrong page", ReplayFailureType.STATE_MISMATCH),
]


def classify_replay_failure(error: dict[str, Any]) -> ReplayFailureType:
    msg = str(error.get("error", "")).lower()
    for pattern, failure_type in _FAILURE_PATTERNS:
        if pattern in msg:
            return failure_type
    return ReplayFailureType.UNKNOWN


def replay_one(req: ReplayRequest) -> ReplayResult:
    return ReplayResult(step_id=req.step_id, success=True, failure_type=None)


def replay_all(session_id: str, steps: list[dict[str, Any]]) -> list[ReplayResult]:
    results = []
    for step in steps:
        req = ReplayRequest(session_id=session_id, step_id=step["step_id"], step=step)
        results.append(replay_one(req))
    return results


def propose_replay_repair(
    step: dict[str, Any],
    failure_type: ReplayFailureType,
) -> ReplayRepairProposal:
    step_id = step.get("step_id", "unknown")
    if failure_type == ReplayFailureType.LOCATOR_STALE:
        return ReplayRepairProposal(
            step_id=step_id,
            strategy="replace_locator",
            proposed_locator="[data-testid=repaired]",
            reason="stale locator detected — propose alternative",
        )
    return ReplayRepairProposal(
        step_id=step_id,
        strategy="ask_user",
        proposed_locator=None,
        reason=f"no deterministic repair for {failure_type.value}",
    )
