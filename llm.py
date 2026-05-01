from __future__ import annotations

import os
from typing import Any

from openai import AsyncOpenAI


class LLMClient:
    def __init__(self) -> None:
        api_key = os.getenv("OPENAI_API_KEY", "").strip()
        if not api_key:
            raise RuntimeError("OPENAI_API_KEY is missing in env")

        self._client = AsyncOpenAI(api_key=api_key)
        self.messages: list[dict[str, Any]] = [
            {
                "role": "system",
                "content": (
                    "You are a browser automation assistant. You help understand user intent "
                    "for web automation steps and find correct ways to execute them."
                ),
            }
        ]

    async def chat(self, user_message: str) -> str:
        self.messages.append({"role": "user", "content": user_message})

        resp = await self._client.chat.completions.create(
            model="gpt-4.1-mini",
            messages=self.messages,
        )

        text = (resp.choices[0].message.content or "").strip()
        self.messages.append({"role": "assistant", "content": text})
        return text

    def reset(self) -> None:
        system = self.messages[0:1]
        self.messages = list(system)
