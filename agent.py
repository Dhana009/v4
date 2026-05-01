from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any

from playwright.async_api import TimeoutError as PlaywrightTimeoutError
from playwright.async_api import expect

from browser import get_page
from llm import LLMClient


SKILL_KEYWORDS: list[tuple[str, tuple[str, ...]]] = [
    ("assertions", ("assert", "verify", "check", "expect", "visible")),
    ("actions", ("click", "fill", "type", "hover", "navigate", "go to")),
    ("locator", ("find", "locate", "element", "selector")),
    ("exploration", ("explore", "understand", "analyze", "map")),
    ("waiting", ("wait", "loading", "spinner", "timeout")),
    ("popup", ("popup", "dialog", "alert", "confirm")),
    ("upload", ("upload", "file", "attach")),
    ("download", ("download", "export", "save")),
    ("iframe", ("iframe", "frame", "embed")),
    ("dropdown", ("select", "dropdown", "option")),
    ("scroll", ("scroll",)),
    ("screenshot", ("screenshot", "capture")),
    ("network", ("network", "api", "request")),
    ("keyboard", ("keyboard", "press", "key")),
    ("auth", ("login", "auth", "session")),
    ("codegen", ("generate", "script", "typescript")),
    ("debugging", ("debug", "error", "fix", "broken")),
]


class AgentLoop:
    def __init__(self, ws: Any, control_queue: Any) -> None:
        self.ws = ws
        self.control_queue = control_queue
        self.skills_root = Path("/Users/apple/personal/agent v4/skills/playwright-automation")
        self.llm = LLMClient()
        self.tools = self._build_tool_definitions()

    async def _send(self, msg_type: str, **kwargs: Any) -> None:
        payload = {"type": msg_type}
        payload.update(kwargs)
        await self.ws.send_json(payload)

    async def run(self, steps: list[dict]) -> None:
        try:
            loaded_skill_names, system_prompt = self._load_skills_for_steps(steps)
            self.llm.system_prompt = system_prompt
            self.llm.reset()

            print(f"[SKILLS LOADED] {' + '.join(loaded_skill_names)}")
            print("[AGENT] Starting tool-calling loop")

            self.llm.messages.append({"role": "user", "content": self._format_steps(steps)})

            while True:
                print("[AGENT] Requesting LLM response")
                response = await self.llm.client.chat.completions.create(
                    model="gpt-4.1-mini",
                    messages=self.llm.messages,
                    tools=self.tools,
                    tool_choice="auto",
                )
                message = response.choices[0].message
                self.llm.messages.append(self._assistant_message_entry(message))

                if not message.tool_calls:
                    final_text = (message.content or "").strip()
                    print("[AGENT] LLM final response received")
                    await self._send("llm_result", success=True, message=final_text)
                    return

                print(f"[AGENT] Executing {len(message.tool_calls)} tool call(s)")
                for tool_call in message.tool_calls:
                    args = self._parse_tool_args(tool_call.function.arguments or "{}")
                    print(
                        f"[TOOL CALL] {tool_call.function.name}({self._summarize(args, limit=100)})"
                    )
                    result = await self._dispatch_tool(tool_call.function.name, args)
                    print(f"[TOOL RESULT] {self._summarize(result, limit=100)}")
                    self.llm.messages.append(
                        {
                            "role": "tool",
                            "tool_call_id": tool_call.id,
                            "content": json.dumps(result, ensure_ascii=True),
                        }
                    )
        except Exception as exc:  # noqa: BLE001
            print(f"[AGENT] Failed: {type(exc).__name__}: {exc}")
            await self._send("error", message=f"Agent failed: {type(exc).__name__}: {exc}")

    def _load_skills_for_steps(self, steps: list[dict]) -> tuple[list[str], str]:
        intents = " ".join(str(step.get("intent") or "") for step in steps).lower()
        loaded_names = ["core"]
        contents = [self._read_skill("core")]

        for skill_name, keywords in SKILL_KEYWORDS:
            if skill_name == "core":
                continue
            if any(keyword in intents for keyword in keywords):
                loaded_names.append(skill_name)
                contents.append(self._read_skill(skill_name))

        return loaded_names, "\n\n".join(contents)

    def _read_skill(self, skill_name: str) -> str:
        skill_path = self.skills_root / skill_name / "SKILL.md"
        return skill_path.read_text(encoding="utf-8")

    def _format_steps(self, steps: list[dict]) -> str:
        lines = [
            "User steps:",
            json.dumps(self._normalize_steps(steps), ensure_ascii=True, indent=2),
            "",
            "Execution requirements:",
            "- Always use tools. Never guess.",
            '- Start by calling send_to_overlay with message_type "llm_thinking".',
            "- Use browser_get_state or dom_extract before deciding what is on the page.",
            "- If a step includes suggested_scope for a picked element, call dom_extract with that suggested_scope first.",
            "- Validate locators before using them for actions or assertions.",
            '- After a successful recorded step, call send_to_overlay with message_type "step_recorded".',
            '- When finished, report the outcome clearly through send_to_overlay or the final assistant response.',
        ]
        return "\n".join(lines)

    def _normalize_steps(self, steps: list[dict]) -> list[dict[str, Any]]:
        normalized: list[dict[str, Any]] = []
        for idx, step in enumerate(steps, start=1):
            element_info = step.get("element_info") or {}
            attrs = element_info.get("attributes") or {}
            normalized.append(
                {
                    "id": str(step.get("id") or idx),
                    "intent": str(step.get("intent") or "").strip(),
                    "element_data": {
                        "tag": element_info.get("tag", ""),
                        "text": element_info.get("text", ""),
                        "id": element_info.get("id", ""),
                        "class": element_info.get("class", ""),
                        "aria_label": attrs.get("aria-label", ""),
                        "data_testid": attrs.get("data-testid", ""),
                        "placeholder": attrs.get("placeholder", ""),
                        "parent_tag": element_info.get("parent_tag", ""),
                        "parent_id": element_info.get("parent_id", ""),
                    },
                    "suggested_scope": self._build_suggested_scope(element_info),
                    "raw_element_info": element_info,
                }
            )
        return normalized

    def _assistant_message_entry(self, message: Any) -> dict[str, Any]:
        entry: dict[str, Any] = {"role": "assistant", "content": message.content or ""}
        if message.tool_calls:
            entry["tool_calls"] = [
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
        return entry

    def _parse_tool_args(self, raw_args: str) -> dict[str, Any]:
        parsed = json.loads(raw_args or "{}")
        if not isinstance(parsed, dict):
            raise ValueError("Tool arguments must decode to an object")
        return parsed

    def _build_tool_definitions(self) -> list[dict[str, Any]]:
        return [
            {
                "type": "function",
                "function": {
                    "name": "dom_extract",
                    "description": "Get interactive elements from current page or a scoped element",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "scope": {
                                "type": "string",
                                "description": 'CSS selector to scope extraction, or "page" for full page',
                            }
                        },
                        "required": ["scope"],
                        "additionalProperties": False,
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "locator_find",
                    "description": "Find best locator for element using priority waterfall",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "element_data": {
                                "type": "object",
                                "properties": {
                                    "tag": {"type": "string"},
                                    "text": {"type": "string"},
                                    "id": {"type": "string"},
                                    "class": {"type": "string"},
                                    "aria_label": {"type": "string"},
                                    "data_testid": {"type": "string"},
                                    "placeholder": {"type": "string"},
                                    "parent_tag": {"type": "string"},
                                    "parent_id": {"type": "string"},
                                },
                                "required": [],
                                "additionalProperties": True,
                            },
                            "strategy": {"type": "string"},
                        },
                        "required": ["element_data"],
                        "additionalProperties": False,
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "locator_validate",
                    "description": "Validate a locator resolves to exactly 1 element on live page",
                    "parameters": {
                        "type": "object",
                        "properties": {"locator": {"type": "string"}},
                        "required": ["locator"],
                        "additionalProperties": False,
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "action_click",
                    "description": "Click an element on the live page",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "locator": {"type": "string"},
                            "timeout": {"type": "integer", "default": 30000},
                        },
                        "required": ["locator"],
                        "additionalProperties": False,
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "action_fill",
                    "description": "Fill an input field with a value",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "locator": {"type": "string"},
                            "value": {"type": "string"},
                            "timeout": {"type": "integer", "default": 30000},
                        },
                        "required": ["locator", "value"],
                        "additionalProperties": False,
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "action_assert",
                    "description": "Assert element state on live page. Auto-retries until condition met or timeout.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "locator": {"type": "string"},
                            "assertion": {
                                "type": "string",
                                "enum": [
                                    "visible",
                                    "hidden",
                                    "enabled",
                                    "disabled",
                                    "has_text",
                                    "has_value",
                                    "checked",
                                ],
                            },
                            "expected_value": {"type": "string"},
                            "timeout": {"type": "integer", "default": 5000},
                        },
                        "required": ["locator", "assertion"],
                        "additionalProperties": False,
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "page_navigate",
                    "description": "Navigate browser to a URL",
                    "parameters": {
                        "type": "object",
                        "properties": {"url": {"type": "string"}},
                        "required": ["url"],
                        "additionalProperties": False,
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "browser_get_state",
                    "description": "Get current browser URL and page title",
                    "parameters": {
                        "type": "object",
                        "properties": {},
                        "additionalProperties": False,
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "screenshot_take",
                    "description": "Take screenshot of current page for debugging",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "filename": {"type": "string", "default": "screenshot.png"}
                        },
                        "additionalProperties": False,
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "send_to_overlay",
                    "description": "Send message to user in the browser overlay panel",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "message_type": {
                                "type": "string",
                                "enum": [
                                    "llm_thinking",
                                    "plan_ready",
                                    "clarification_needed",
                                    "step_recorded",
                                    "code_update",
                                    "llm_result",
                                    "error",
                                ],
                            },
                            "payload": {"type": "object", "additionalProperties": True},
                        },
                        "required": ["message_type", "payload"],
                        "additionalProperties": False,
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "ask_user",
                    "description": "Ask user a question and wait for their response",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "question": {"type": "string"},
                            "options": {"type": "array", "items": {"type": "string"}},
                        },
                        "required": ["question"],
                        "additionalProperties": False,
                    },
                },
            },
        ]

    async def _dispatch_tool(self, tool_name: str, args: dict[str, Any]) -> dict[str, Any]:
        handlers = {
            "dom_extract": self._tool_dom_extract,
            "locator_find": self._tool_locator_find,
            "locator_validate": self._tool_locator_validate,
            "action_click": self._tool_action_click,
            "action_fill": self._tool_action_fill,
            "action_assert": self._tool_action_assert,
            "page_navigate": self._tool_page_navigate,
            "browser_get_state": self._tool_browser_get_state,
            "screenshot_take": self._tool_screenshot_take,
            "send_to_overlay": self._tool_send_to_overlay,
            "ask_user": self._tool_ask_user,
        }
        if tool_name not in handlers:
            raise RuntimeError(f"Unsupported tool requested: {tool_name}")
        return await handlers[tool_name](args)

    async def _tool_dom_extract(self, args: dict[str, Any]) -> dict[str, Any]:
        page = get_page()
        scope = str(args.get("scope") or "page").strip() or "page"
        html = ""

        if scope == "page":
            html = await page.content()
        else:
            html = await page.evaluate(
                """
                ({ scope }) => {
                  const node = document.querySelector(scope);
                  return node ? node.outerHTML : "";
                }
                """,
                {"scope": scope},
            )

        cleaned = self._clean_markup(html)[:3000]
        return {"elements": cleaned, "url": page.url}

    async def _tool_locator_find(self, args: dict[str, Any]) -> dict[str, Any]:
        page = get_page()
        element_data = args.get("element_data") or {}
        force_strategy = str(args.get("strategy") or "").strip()
        ordered = [
            "data-testid",
            "aria-label",
            "id",
            "placeholder_text",
            "exact_text_match",
            "partial_text_match",
            "css_selector",
            "role+name",
            "relative_xpath",
            "absolute_xpath",
        ]
        aliases = {
            "data_testid": "data-testid",
            "aria_label": "aria-label",
            "placeholder": "placeholder_text",
            "exact_text": "exact_text_match",
            "partial_text": "partial_text_match",
            "css": "css_selector",
            "role_name": "role+name",
        }
        strategy_name = aliases.get(force_strategy, force_strategy)
        strategies = [strategy_name] if strategy_name else ordered
        first_positive: dict[str, Any] | None = None

        def stable_for(strategy: str) -> bool:
            return strategy in {"data-testid", "aria-label", "id", "role+name"}

        def esc_css(value: str) -> str:
            return value.replace("\\", "\\\\").replace('"', '\\"')

        def esc_xpath(value: str) -> str:
            return value.replace("'", "\\'")

        for strategy in strategies:
            locator = None
            locator_string = ""
            count = 0

            try:
                if strategy == "data-testid":
                    testid = str(element_data.get("data_testid", "") or "").strip()
                    locator_string = f'get_by_test_id("{testid}")'
                    if testid:
                        locator = page.get_by_test_id(testid)
                        count = await locator.count()

                elif strategy == "aria-label":
                    aria_label = str(element_data.get("aria_label", "") or "").strip()
                    locator_string = f'get_by_label("{aria_label}")'
                    if aria_label:
                        locator = page.get_by_label(aria_label)
                        count = await locator.count()

                elif strategy == "id":
                    id_val = str(element_data.get("id", "") or "").strip()
                    if id_val:
                        locator_string = f"#{esc_css(id_val)}"
                        locator = page.locator(locator_string)
                        count = await locator.count()

                elif strategy == "placeholder_text":
                    placeholder = str(element_data.get("placeholder", "") or "").strip()
                    locator_string = f'get_by_placeholder("{placeholder}")'
                    if placeholder:
                        locator = page.get_by_placeholder(placeholder)
                        count = await locator.count()

                elif strategy == "exact_text_match":
                    text = str(element_data.get("text", "") or "")
                    if text:
                        locator_string = f'get_by_text("{text}", exact=True)'
                        locator = page.get_by_text(text, exact=True)
                        count = await locator.count()

                elif strategy == "partial_text_match":
                    text = str(element_data.get("text", "") or "")
                    short_text = text[:50].strip()
                    if short_text:
                        locator_string = f'get_by_text("{short_text}", exact=False)'
                        locator = page.get_by_text(short_text, exact=False)
                        count = await locator.count()

                elif strategy == "css_selector":
                    tag = str(element_data.get("tag", "") or "").strip()
                    class_value = str(element_data.get("class", "") or "").strip()
                    cls = class_value.split()[0] if class_value else ""
                    if tag and cls:
                        locator_string = f"{tag}.{cls}"
                        locator = page.locator(locator_string)
                    elif tag:
                        locator_string = tag
                        locator = page.locator(locator_string)
                    if tag and locator is not None:
                        count = await locator.count()

                elif strategy == "role+name":
                    role = str(element_data.get("role", "") or "").strip()
                    name = str(element_data.get("text", "") or "")[:50]
                    if role and name:
                        locator_string = f'get_by_role("{role}", name="{name}")'
                        locator = page.get_by_role(role, name=name)
                        count = await locator.count()

                elif strategy == "relative_xpath":
                    tag = str(element_data.get("tag", "") or "").strip()
                    text = str(element_data.get("text", "") or "")[:50].strip()
                    if tag and text:
                        locator_string = f"//{tag}[contains(.,'{esc_xpath(text)}')]"
                        locator = page.locator(locator_string)
                        count = await locator.count()

                elif strategy == "absolute_xpath":
                    tag = str(element_data.get("tag", "") or "").strip()
                    class_value = str(element_data.get("class", "") or "").strip()
                    cls = class_value.split()[0] if class_value else ""
                    if tag and cls:
                        locator_string = f"//{tag}[@class='{esc_xpath(cls)}']"
                        locator = page.locator(locator_string)
                        count = await locator.count()
            except Exception:  # noqa: BLE001
                count = 0

            if count > 0 and strategy_name:
                return {
                    "found": True,
                    "locator": locator_string,
                    "strategy": strategy,
                    "count": count,
                    "stable": stable_for(strategy),
                }

            if count == 1:
                return {
                    "found": True,
                    "locator": locator_string,
                    "strategy": strategy,
                    "count": count,
                    "stable": stable_for(strategy),
                }

            if count > 0 and first_positive is None:
                first_positive = {
                    "found": True,
                    "locator": locator_string,
                    "strategy": strategy,
                    "count": count,
                    "stable": stable_for(strategy),
                }

        if first_positive is not None:
            return first_positive

        return {
            "found": False,
            "locator": "",
            "strategy": strategy_name or "",
            "count": 0,
            "stable": False,
        }

    async def _tool_locator_validate(self, args: dict[str, Any]) -> dict[str, Any]:
        page = get_page()
        locator = str(args.get("locator") or "").strip()
        count = 0
        if locator:
            try:
                count = await page.locator(locator).count()
            except Exception:  # noqa: BLE001
                count = 0
        return {"valid": count == 1, "count": count}

    async def _tool_action_click(self, args: dict[str, Any]) -> dict[str, Any]:
        page = get_page()
        locator = str(args.get("locator") or "").strip()
        timeout = int(args.get("timeout") or 30000)
        try:
            await page.locator(locator).first.click(timeout=timeout)
            return {"success": True, "error": None}
        except Exception as exc:  # noqa: BLE001
            return {"success": False, "error": str(exc)}

    async def _tool_action_fill(self, args: dict[str, Any]) -> dict[str, Any]:
        page = get_page()
        locator = str(args.get("locator") or "").strip()
        value = str(args.get("value") or "")
        timeout = int(args.get("timeout") or 30000)
        try:
            await page.locator(locator).first.fill(value, timeout=timeout)
            return {"success": True, "error": None}
        except Exception as exc:  # noqa: BLE001
            return {"success": False, "error": str(exc)}

    async def _tool_action_assert(self, args: dict[str, Any]) -> dict[str, Any]:
        page = get_page()
        locator_text = str(args.get("locator") or "").strip()
        assertion = str(args.get("assertion") or "").strip()
        expected_value = args.get("expected_value")
        timeout = int(args.get("timeout") or 5000)
        locator = page.locator(locator_text).first

        try:
            if assertion == "visible":
                await expect(locator).to_be_visible(timeout=timeout)
            elif assertion == "hidden":
                await expect(locator).to_be_hidden(timeout=timeout)
            elif assertion == "enabled":
                await expect(locator).to_be_enabled(timeout=timeout)
            elif assertion == "disabled":
                await expect(locator).to_be_disabled(timeout=timeout)
            elif assertion == "has_text":
                if expected_value is None:
                    raise ValueError("expected_value is required for has_text")
                await expect(locator).to_contain_text(str(expected_value), timeout=timeout)
            elif assertion == "has_value":
                if expected_value is None:
                    raise ValueError("expected_value is required for has_value")
                await expect(locator).to_have_value(str(expected_value), timeout=timeout)
            elif assertion == "checked":
                await expect(locator).to_be_checked(timeout=timeout)
            else:
                raise ValueError(f"Unsupported assertion: {assertion}")
            return {"success": True, "error": None}
        except (AssertionError, PlaywrightTimeoutError, ValueError) as exc:
            return {"success": False, "error": str(exc)}
        except Exception as exc:  # noqa: BLE001
            return {"success": False, "error": str(exc)}

    async def _tool_page_navigate(self, args: dict[str, Any]) -> dict[str, Any]:
        page = get_page()
        url = str(args.get("url") or "").strip()
        await page.goto(url, wait_until="domcontentloaded")
        return {"success": True, "url": page.url}

    async def _tool_browser_get_state(self, args: dict[str, Any]) -> dict[str, Any]:  # noqa: ARG002
        page = get_page()
        return {"url": page.url, "title": await page.title()}

    async def _tool_screenshot_take(self, args: dict[str, Any]) -> dict[str, Any]:
        page = get_page()
        filename = str(args.get("filename") or "screenshot.png")
        output_dir = Path(".hermes/screenshots")
        output_dir.mkdir(parents=True, exist_ok=True)
        path = output_dir / filename
        await page.screenshot(path=str(path))
        return {"path": str(path), "success": True}

    async def _tool_send_to_overlay(self, args: dict[str, Any]) -> dict[str, Any]:
        message_type = str(args.get("message_type") or "").strip()
        payload = args.get("payload") or {}
        if not isinstance(payload, dict):
            raise ValueError("payload must be an object")
        await self._send(message_type, **payload)
        return {"sent": True}

    async def _tool_ask_user(self, args: dict[str, Any]) -> dict[str, Any]:
        question = str(args.get("question") or "").strip()
        options = args.get("options") or []
        if not isinstance(options, list):
            options = []

        await self._send(
            "clarification_needed",
            question=question,
            options=[str(option) for option in options],
        )

        while True:
            event = await self.control_queue.get()
            event_type = str(event.get("type") or "")
            if event_type == "option_selected":
                answer = str(event.get("answer") or event.get("message") or "").strip()
                return {"answer": answer}
            if event_type == "correction":
                return {"answer": str(event.get("message") or "").strip()}
            if event_type == "confirmed":
                return {"answer": "confirmed"}

    def _build_locator_from_strategy(self, strategy: str, element_data: dict[str, Any]) -> str:
        tag = str(element_data.get("tag") or "*").strip() or "*"
        text = self._normalize_space(str(element_data.get("text") or ""))
        element_id = str(element_data.get("id") or "").strip()
        class_name = str(element_data.get("class") or "").strip()
        aria_label = self._normalize_space(str(element_data.get("aria_label") or ""))
        data_testid = str(element_data.get("data_testid") or "").strip()
        placeholder = self._normalize_space(str(element_data.get("placeholder") or ""))
        parent_tag = str(element_data.get("parent_tag") or "").strip()
        parent_id = str(element_data.get("parent_id") or "").strip()

        if strategy == "data_testid" and data_testid:
            return f'[data-testid="{self._css_escape(data_testid)}"]'
        if strategy == "aria_label" and aria_label:
            return f'[aria-label="{self._css_escape(aria_label)}"]'
        if strategy == "id" and element_id:
            return f"#{self._css_escape(element_id)}"
        if strategy == "placeholder" and placeholder:
            return f'[placeholder="{self._css_escape(placeholder)}"]'
        if strategy == "exact_text" and text:
            return f'text="{self._text_escape(text)}"'
        if strategy == "partial_text" and text:
            partial = text[:80].strip()
            return f"text={self._text_escape(partial)}"
        if strategy == "css":
            tag_part = re.sub(r"[^a-zA-Z0-9:_-]", "", tag) or "*"
            classes = [
                re.sub(r"[^a-zA-Z0-9_-]", "", item)
                for item in class_name.split()
                if re.sub(r"[^a-zA-Z0-9_-]", "", item)
            ]
            base = tag_part
            if classes:
                base += "." + ".".join(classes[:3])
            if parent_id:
                return f"#{self._css_escape(parent_id)} {base}"
            if parent_tag:
                parent = re.sub(r"[^a-zA-Z0-9:_-]", "", parent_tag)
                if parent:
                    return f"{parent} {base}"
            return base
        return ""

    def _build_suggested_scope(self, element_info: dict[str, Any]) -> str:
        tag = re.sub(r"[^a-zA-Z0-9:_-]", "", str(element_info.get("tag") or "").strip())
        if not tag:
            return "page"
        element_id = str(element_info.get("id") or "").strip()
        if element_id:
            return f"{tag}#{self._css_escape(element_id)}"
        class_name = str(element_info.get("class") or "").strip()
        classes = [
            re.sub(r"[^a-zA-Z0-9_-]", "", item)
            for item in class_name.split()
            if re.sub(r"[^a-zA-Z0-9_-]", "", item)
        ]
        if classes:
            return f"{tag}." + ".".join(classes[:3])
        return tag

    def _clean_markup(self, html: str) -> str:
        cleaned = html or ""
        for tag in ("style", "script", "svg"):
            cleaned = re.sub(
                rf"<{tag}\b[^>]*>.*?</{tag}>",
                "",
                cleaned,
                flags=re.IGNORECASE | re.DOTALL,
            )
        cleaned = re.sub(r"\s+", " ", cleaned).strip()
        return cleaned

    def _summarize(self, value: Any, limit: int = 100) -> str:
        if isinstance(value, dict):
            if "elements" in value:
                text = str(value.get("elements") or "")
            elif "message" in value:
                text = str(value.get("message") or "")
            else:
                text = json.dumps(value, ensure_ascii=True)
        else:
            text = json.dumps(value, ensure_ascii=True) if not isinstance(value, str) else value
        text = text.replace("\n", " ").strip()
        return text[:limit]

    def _css_escape(self, value: str) -> str:
        return value.replace("\\", "\\\\").replace('"', '\\"')

    def _text_escape(self, value: str) -> str:
        return value.replace("\\", "\\\\").replace('"', '\\"')

    def _normalize_space(self, value: str) -> str:
        return re.sub(r"\s+", " ", value).strip()
