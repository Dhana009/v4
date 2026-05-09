from __future__ import annotations
from typing import TYPE_CHECKING, Any
if TYPE_CHECKING:
    from agent import AgentLoop


class Recorder:
    def __init__(self, loop: "AgentLoop") -> None:
        self._loop = loop

    def has_successful_action_to_record(self) -> bool:
        return self._loop._has_successful_action_to_record()

    def should_block_additional_execution_action(self, tool_name: str) -> bool:
        return self._loop._should_block_additional_execution_action(tool_name)

    def should_block_recording_wait_tool(self, tool_name: str) -> bool:
        return self._loop._should_block_recording_wait_tool(tool_name)

    def get_successful_action_for_step(self, step: Any) -> Any:
        return self._loop._get_successful_action_for_step(step)

    def get_successful_action_history_for_step(self, step: Any) -> Any:
        return self._loop._get_successful_action_history_for_step(step)

    async def record_step_payload(self, step: Any) -> Any:
        return await self._loop._record_step_payload(step)

    async def auto_record_successful_step(self) -> Any:
        return await self._loop._auto_record_successful_step()

    def build_step_record_payload(self, step: Any, **kwargs: Any) -> dict:
        return self._loop._build_step_record_payload(step, **kwargs)

    def append_recorded_step_payload(self, payload: dict) -> None:
        return self._loop._append_recorded_step_payload(payload)

    def append_code_update_payload(self, payload: dict) -> None:
        return self._loop._append_code_update_payload(payload)
