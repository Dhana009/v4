"""
runtime/multi_step_queue.py

Queued multi-step planning flow.

Source rule: S6-0404 — steps are queued for planning in order.
No execution before confirmation.
"""
from __future__ import annotations

from collections import deque
from typing import Any


class MultiStepQueue:
    """FIFO queue for planning step IDs."""

    def __init__(self) -> None:
        self._queue: deque[str] = deque()

    def enqueue(self, step_id: str) -> None:
        self._queue.append(step_id)

    def dequeue(self) -> str:
        if not self._queue:
            raise IndexError("Queue is empty")
        return self._queue.popleft()

    def peek(self) -> str | None:
        if not self._queue:
            return None
        return self._queue[0]

    def is_empty(self) -> bool:
        return len(self._queue) == 0

    def size(self) -> int:
        return len(self._queue)

    def to_list(self) -> list[str]:
        return list(self._queue)
