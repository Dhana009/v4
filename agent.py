from __future__ import annotations

import json
from typing import Any

from browser import get_page
from executor import execute_action
from llm import LLMClient
from locator import find_best_locator


class AgentLoop:
    def __init__(self, ws: Any, control_queue: Any) -> None:
        self.ws = ws
        self.control_queue = control_queue
        self.llm = LLMClient()

    async def _send(self, msg_type: str, **kwargs: Any) -> None:
        payload = {"type": msg_type}
        payload.update(kwargs)
        await self.ws.send_json(payload)

    async def run(self, steps: list[dict]) -> None:
        try:
            planned_actions = await self._phase_understand_confirm(steps)
            await self._phase_execute_with_heal(steps, planned_actions)
            await self._send("status", message="Run completed.")
        except Exception as e:  # noqa: BLE001
            await self._send("error", message=f"Agent failed: {type(e).__name__}: {e}")

    async def _phase_understand_confirm(self, steps: list[dict]) -> list[dict]:
        current_steps = steps
        while True:
            await self._send("status", message="Phase 1: understanding requested steps...")
            schema_hint = (
                '[{"step_id":"1","action_type":"click|fill|navigate","locator_hint":"string","value":"string or null"}]'
            )
            prompt = (
                "Here are the automation steps the user wants.\n"
                "For each step, return STRICT JSON only (no markdown, no extra text) as an array with schema:\n"
                f"{schema_hint}\n"
                "Rules:\n"
                "- action_type must be one of click, fill, navigate\n"
                "- locator_hint must be natural-language element hint string\n"
                "- value must be string or null\n"
                "- step_id must match input step id\n\n"
                f"INPUT STEPS JSON:\n{json.dumps(current_steps, ensure_ascii=True)}"
            )
            llm_response = await self.llm.chat(prompt)
            actions = self._parse_action_json(llm_response)

            await self._send("confirm", message=llm_response)
            await self._send("status", message="Phase 2: waiting for confirmation/correction...")

            while True:
                event = await self.control_queue.get()
                event_type = event.get("type")
                if event_type == "confirmed":
                    await self._send("status", message="Confirmed. Starting execution.")
                    return actions
                if event_type == "correction":
                    correction = (event.get("message") or "").strip()
                    self.llm.messages.append(
                        {
                            "role": "user",
                            "content": (
                                "User correction received. Re-plan with STRICT JSON output only.\n"
                                f"Correction: {correction}\n"
                                f"Original steps: {json.dumps(current_steps, ensure_ascii=True)}"
                            ),
                        }
                    )
                    await self._send("status", message="Correction received. Re-understanding...")
                    break

    async def _phase_execute_with_heal(self, steps: list[dict], actions: list[dict]) -> None:
        step_by_id = {str(s.get("id")): s for s in steps}
        page = get_page()

        for idx, action in enumerate(actions, start=1):
            step_id = str(action.get("step_id", ""))
            step = step_by_id.get(step_id, {})
            action_type = str(action.get("action_type") or "").strip()
            value = action.get("value")
            locator_hint = str(action.get("locator_hint") or "").strip()
            element_info = step.get("element_info")

            locator = find_best_locator(element_info, locator_hint)
            run_action = {"locator": locator, "action_type": action_type, "value": value}

            await self._send("status", message=f"Step {idx}: executing ({action_type})...")
            result = await execute_action(page, run_action)
            if result.get("success"):
                await self._send("status", message=f"Step {idx}: done")
                continue

            await self._send("status", message=f"Step {idx}: failed, entering heal loop...")
            healed = await self._heal_and_retry(idx, step, run_action, str(result.get("error") or ""))
            if not healed:
                await self._send("error", message=f"Step {idx} failed after 3 attempts.")
                return

    async def _heal_and_retry(
        self, step_index: int, step: dict, action: dict, error_text: str
    ) -> bool:
        page = get_page()
        for attempt in range(1, 4):
            await self._send("status", message=f"Step {step_index}: heal attempt {attempt}/3")
            try:
                url = page.url
                dom = (await page.content())[:3000]
            except Exception as e:  # noqa: BLE001
                url = ""
                dom = f"DOM capture failed: {type(e).__name__}: {e}"

            prompt = (
                "This step failed. Return STRICT JSON only with this exact schema as a one-item array:\n"
                '[{"step_id":"1","action_type":"click|fill|navigate","locator_hint":"string","value":"string or null"}]\n'
                f"Failed step JSON: {json.dumps(step, ensure_ascii=True)}\n"
                f"Failed action JSON: {json.dumps(action, ensure_ascii=True)}\n"
                f"Error: {error_text}\n"
                f"Current URL: {url}\n"
                f"DOM snippet (first 3000 chars): {dom}"
            )
            llm_response = await self.llm.chat(prompt)
            corrected = self._parse_action_json(llm_response)[0]

            locator = find_best_locator(step.get("element_info"), corrected.get("locator_hint"))
            retry_action = {
                "locator": locator,
                "action_type": corrected.get("action_type"),
                "value": corrected.get("value"),
            }
            result = await execute_action(page, retry_action)
            if result.get("success"):
                await self._send("status", message=f"Step {step_index}: heal successful")
                return True
            error_text = str(result.get("error") or "unknown error")

        return False

    def _parse_action_json(self, content: str) -> list[dict]:
        text = (content or "").strip()
        start = text.find("[")
        end = text.rfind("]")
        if start != -1 and end != -1 and end > start:
            text = text[start : end + 1]
        parsed = json.loads(text)
        if not isinstance(parsed, list):
            raise ValueError("LLM output is not a JSON list")
        if not parsed:
            raise ValueError("LLM output JSON list is empty")
        return parsed

