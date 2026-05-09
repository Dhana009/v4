from __future__ import annotations
from typing import TYPE_CHECKING, Any
if TYPE_CHECKING:
    from agent import AgentLoop


class PlanConfirmation:
    def __init__(self, loop: "AgentLoop") -> None:
        self._loop = loop

    async def wait_for_plan_confirmation(self) -> dict[str, Any]:
        return await self._loop._wait_for_plan_confirmation()

    async def send_plan_ready_after_confirmation(self, payload: Any) -> Any:
        return await self._loop._send_plan_ready_after_confirmation(payload)

    def confirmation_context(self, payload: Any) -> dict[str, str]:
        return self._loop._confirmation_context(payload)

    def confirmation_context_mismatch_reason(self, payload: Any, expected: Any) -> str | None:
        return self._loop._confirmation_context_mismatch_reason(payload, expected)

    def completed_run_confirmation_rejection_reason(self, payload: Any) -> str | None:
        return self._loop._completed_run_confirmation_rejection_reason(payload)
