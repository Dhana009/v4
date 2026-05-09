from __future__ import annotations
from typing import TYPE_CHECKING, Any
if TYPE_CHECKING:
    from agent import AgentLoop


class Replay:
    def __init__(self, loop: "AgentLoop") -> None:
        self._loop = loop

    async def replay_one(self, step_id: str) -> dict:
        return await self._loop.replay_one(step_id)

    async def replay_all(self, stop_on_error: bool = True) -> dict:
        return await self._loop.replay_all(stop_on_error)

    def get_replay_recorded_step_payload(self, step_id: str) -> Any:
        return self._loop._get_replay_recorded_step_payload(step_id)

    def get_replay_action_history(self, step_id: str) -> Any:
        return self._loop._get_replay_action_history(step_id)

    def get_replay_archive_step_ids(self) -> list:
        return self._loop._get_replay_archive_step_ids()

    def get_replay_recorded_start_state(self, payload: dict) -> Any:
        return self._loop._get_replay_recorded_start_state(payload)

    def get_replay_precondition_target_locator(self, step: Any) -> Any:
        return self._loop._get_replay_precondition_target_locator(step)

    async def validate_replay_target_locator(self, locator: str) -> dict:
        return await self._loop._validate_replay_target_locator(locator)

    def log_replay_precondition_failure(self, step: Any, reason: str) -> None:
        return self._loop._log_replay_precondition_failure(step, reason)

    def build_replay_precondition_failure_result(self, step: Any, reason: str) -> dict:
        return self._loop._build_replay_precondition_failure_result(step, reason)

    async def check_replay_precondition(self, step: Any) -> Any:
        return await self._loop._check_replay_precondition(step)

    def safe_replay_error_message(self, message: Any) -> str:
        return self._loop._safe_replay_error_message(message)
