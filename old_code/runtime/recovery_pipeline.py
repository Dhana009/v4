"""
runtime/recovery_pipeline.py

Recovery pipeline: packet building, deterministic recovery proposals,
and recovery lifecycle state.

Source rule: S6-0802–0807 — deterministic recovery first.
Recovery state blocks completion/recording/code_update.
Resume from failed operation safely.
"""
from __future__ import annotations

import enum
from dataclasses import dataclass, field
from typing import Any

from runtime.failure_classifier import FailureType, classify_failure


# ---------------------------------------------------------------------------
# Recovery packet
# ---------------------------------------------------------------------------

@dataclass
class RecoveryPacket:
    step_id: str
    failure_type: FailureType
    error_message: str
    failed_locator: str | None
    page_url: str
    trace: list[str] = field(default_factory=list)


def build_recovery_packet(
    step_id: str,
    error: dict[str, Any],
    page_url: str,
    failed_locator: str | None,
) -> RecoveryPacket:
    """Build a focused recovery packet from failure evidence."""
    classification = classify_failure(error)
    return RecoveryPacket(
        step_id=step_id,
        failure_type=classification.failure_type,
        error_message=str(error.get("error", "unknown error")),
        failed_locator=failed_locator,
        page_url=page_url,
    )


# ---------------------------------------------------------------------------
# Recovery proposal
# ---------------------------------------------------------------------------

@dataclass
class RecoveryProposal:
    strategy: str    # "retry_locator" | "wait_and_retry" | "ask_user" | "fail_closed"
    proposed_locator: str | None = None
    confidence: float = 0.0
    reason: str | None = None


_DETERMINISTIC_STRATEGIES: dict[FailureType, str] = {
    FailureType.ELEMENT_NOT_FOUND: "retry_locator",
    FailureType.TIMEOUT: "wait_and_retry",
    FailureType.NETWORK_ERROR: "wait_and_retry",
    FailureType.ASSERTION_FAILURE: "ask_user",
    FailureType.NAVIGATION_ERROR: "wait_and_retry",
    FailureType.PERMISSION_DENIED: "fail_closed",
    FailureType.UNKNOWN: "ask_user",
}


def propose_deterministic_recovery(packet: RecoveryPacket) -> RecoveryProposal:
    """Propose a deterministic recovery strategy without LLM."""
    strategy = _DETERMINISTIC_STRATEGIES.get(packet.failure_type, "ask_user")
    return RecoveryProposal(
        strategy=strategy,
        proposed_locator=None,
        confidence=0.7 if strategy != "ask_user" else 0.3,
        reason=f"deterministic_{packet.failure_type.value}_recovery",
    )


# ---------------------------------------------------------------------------
# Recovery lifecycle state
# ---------------------------------------------------------------------------

class RecoveryStatus(enum.Enum):
    ACTIVE = "active"
    IN_RECOVERY = "in_recovery"
    RESOLVED = "resolved"
    FAILED_CLOSED = "failed_closed"


@dataclass
class RecoveryLifecycleState:
    step_id: str
    status: RecoveryStatus = RecoveryStatus.ACTIVE
    failure_type: FailureType | None = None

    def enter_recovery(self, failure_type: FailureType) -> None:
        self.failure_type = failure_type
        self.status = RecoveryStatus.IN_RECOVERY

    def mark_resolved(self) -> None:
        self.status = RecoveryStatus.RESOLVED

    def mark_failed_closed(self) -> None:
        self.status = RecoveryStatus.FAILED_CLOSED


def can_complete_after_recovery(state: RecoveryLifecycleState) -> bool:
    """Return True only if recovery is resolved (not in-progress or failed)."""
    return state.status == RecoveryStatus.RESOLVED


def can_record_after_recovery(state: RecoveryLifecycleState) -> bool:
    """Return True only if recovery is resolved — no recording while in recovery."""
    return state.status == RecoveryStatus.RESOLVED
