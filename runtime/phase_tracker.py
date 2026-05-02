from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class PhaseTransition:
    from_phase: str
    to_phase: str
    reason: str
    step_id: str


class PhaseTracker:
    def __init__(self, initial_phase: str = "idle") -> None:
        self.current_phase = str(initial_phase or "idle").strip() or "idle"

    def set_phase(
        self,
        new_phase: str,
        reason: str | None = None,
        step_id: str | None = None,
    ) -> PhaseTransition | None:
        normalized_phase = str(new_phase or "").strip()
        if not normalized_phase or normalized_phase == self.current_phase:
            return None

        transition = PhaseTransition(
            from_phase=self.current_phase,
            to_phase=normalized_phase,
            reason=str(reason or "").strip() or "unspecified",
            step_id=str(step_id or "").strip() or "none",
        )
        self.current_phase = normalized_phase
        print(
            "[PHASE] "
            f"from={transition.from_phase} "
            f"to={transition.to_phase} "
            f"reason={transition.reason} "
            f"step_id={transition.step_id}"
        )
        return transition

    def get_phase(self) -> str:
        return self.current_phase
