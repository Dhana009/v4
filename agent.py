from __future__ import annotations

import json
import re
from typing import Any

from browser import get_page
from llm import LLMClient


class AgentLoop:
    def __init__(self, ws: Any, control_queue: Any) -> None:
        self.ws = ws
        self.control_queue = control_queue
        self.system_prompt = (
            "You are a browser automation agent with access to tools.\n"
            "When given steps, first call dom_snapshot to understand what is currently on the page, "
            "then explain in plain English what you see and what you plan to do for each step.\n"
            "Always use your tools. Never guess."
        )
        self.llm = LLMClient(system_prompt=self.system_prompt)
        self.tools = [
            {
                "type": "function",
                "function": {
                    "name": "dom_snapshot",
                    "description": "Get the current page DOM to understand what is on the page",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "scope": {
                                "type": "string",
                                "enum": ["element", "page"],
                                "description": "Choose page for the full document or element for the picked element.",
                            },
                            "element_data": {
                                "type": ["object", "null"],
                                "description": "Picked element info if available.",
                            },
                        },
                        "required": ["scope", "element_data"],
                        "additionalProperties": False,
                    },
                },
            }
        ]

    async def _send(self, msg_type: str, **kwargs: Any) -> None:
        payload = {"type": msg_type}
        payload.update(kwargs)
        await self.ws.send_json(payload)

    async def run(self, steps: list[dict]) -> None:
        try:
            self.llm.reset()
            print("[AGENT] Starting tool-calling loop")

            step_text = self._format_steps(steps)
            self.llm.messages.append({"role": "user", "content": step_text})

            while True:
                resp = await self.llm.client.chat.completions.create(
                    model="gpt-4.1-mini",
                    messages=self.llm.messages,
                    tools=self.tools,
                    tool_choice="auto",
                )
                message = resp.choices[0].message

                assistant_entry: dict[str, Any] = {
                    "role": "assistant",
                    "content": message.content or "",
                }
                if message.tool_calls:
                    assistant_entry["tool_calls"] = [
                        {
                            "id": tool_call.id,
                            "type": tool_call.type,
                            "function": {
                                "name": tool_call.function.name,
                                "arguments": tool_call.function.arguments,
                            },
                        }
                        for tool_call in message.tool_calls
                    ]
                self.llm.messages.append(assistant_entry)

                if not message.tool_calls:
                    final_text = (message.content or "").strip()
                    print("[AGENT] LLM final response received")
                    await self._send("confirm", message=final_text)
                    return

                for tool_call in message.tool_calls:
                    if tool_call.function.name != "dom_snapshot":
                        raise RuntimeError(f"Unsupported tool requested: {tool_call.function.name}")

                    raw_args = tool_call.function.arguments or "{}"
                    print(f"[TOOL CALL] dom_snapshot({raw_args})")
                    args = json.loads(raw_args)
                    result = await self._dom_snapshot(
                        scope=str(args.get("scope") or "").strip(),
                        element_data=args.get("element_data"),
                    )
                    result_json = json.dumps(result, ensure_ascii=True)
                    preview = result_json[:200]
                    print(f"[TOOL RESULT] {preview}")
                    self.llm.messages.append(
                        {
                            "role": "tool",
                            "tool_call_id": tool_call.id,
                            "content": result_json,
                        }
                    )
        except Exception as e:  # noqa: BLE001
            await self._send("error", message=f"Agent failed: {type(e).__name__}: {e}")

    def _format_steps(self, steps: list[dict]) -> str:
        lines = ["User steps:"]
        for idx, step in enumerate(steps, start=1):
            step_id = str(step.get("id") or idx)
            intent = str(step.get("intent") or "").strip()
            element_info = step.get("element_info")
            lines.append(f"Step {step_id}: {intent}")
            lines.append(f"Picked element: {json.dumps(element_info, ensure_ascii=True)}")
        return "\n".join(lines)

    async def _dom_snapshot(self, scope: str, element_data: dict[str, Any] | None) -> dict[str, str]:
        page = get_page()
        dom = ""

        if scope == "page":
            dom = await page.content()
        elif scope == "element" and element_data:
            dom = await page.evaluate(
                """
                ({ elementData }) => {
                  const normalize = (value) => (value || "").replace(/\\s+/g, " ").trim();
                  const tag = normalize(elementData?.tag).toLowerCase();
                  const id = normalize(elementData?.id);
                  const text = normalize(elementData?.text);
                  const candidates = Array.from(document.querySelectorAll(tag || "*"));

                  const exact = candidates.find((node) => {
                    const nodeId = normalize(node.id);
                    const nodeText = normalize(node.innerText || node.textContent || "");
                    if (id && nodeId !== id) return false;
                    if (text && nodeText !== text) return false;
                    return true;
                  });
                  if (exact) return exact.outerHTML;

                  const fuzzy = candidates.find((node) => {
                    const nodeId = normalize(node.id);
                    const nodeText = normalize(node.innerText || node.textContent || "");
                    if (id && nodeId !== id) return false;
                    if (!text) return true;
                    return nodeText.includes(text) || text.includes(nodeText);
                  });
                  if (fuzzy) return fuzzy.outerHTML;

                  if (candidates.length === 1) return candidates[0].outerHTML;

                  return "";
                }
                """,
                {"elementData": element_data},
            )
            if not dom:
                dom = await page.content()
        else:
            dom = await page.content()

        cleaned = self._clean_dom(dom)[:3000]
        return {"dom": cleaned, "url": page.url}

    def _clean_dom(self, dom: str) -> str:
        cleaned = dom or ""
        for tag in ("style", "script", "svg"):
            cleaned = re.sub(
                rf"<{tag}\b[^>]*>.*?</{tag}>",
                "",
                cleaned,
                flags=re.IGNORECASE | re.DOTALL,
            )
        cleaned = re.sub(r"\s+", " ", cleaned).strip()
        return cleaned
