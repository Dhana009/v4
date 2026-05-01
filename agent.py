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
                                    "role": {"type": "string"},
                                    "aria_label": {"type": "string"},
                                    "data_testid": {"type": "string"},
                                    "placeholder": {"type": "string"},
                                    "parent_tag": {"type": "string"},
                                    "parent_id": {"type": "string"},
                                },
                                "required": [],
                                "additionalProperties": True,
                            },
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
        candidates = self._build_locator_candidates(element_data)
        tried: list[dict[str, Any]] = []

        for candidate in candidates:
            locator_string = candidate["locator"]
            strategy = candidate["strategy"]

            try:
                locator = self._resolve_locator(page, locator_string)
                count = await locator.count()
            except Exception as exc:  # noqa: BLE001
                tried.append(
                    {
                        "strategy": strategy,
                        "locator": locator_string,
                        "count": 0,
                        "error": str(exc),
                    }
                )
                continue

            if count == 1:
                return {
                    "found": True,
                    "locator": locator_string,
                    "strategy": strategy,
                    "count": 1,
                    "stable": self._is_stable_locator_strategy(strategy),
                    "tried": tried,
                }

            tried.append(
                {
                    "strategy": strategy,
                    "locator": locator_string,
                    "count": count,
                }
            )

        return {
            "found": False,
            "locator": "",
            "strategy": "",
            "count": 0,
            "stable": False,
            "tried": tried,
        }

    async def _tool_locator_validate(self, args: dict[str, Any]) -> dict[str, Any]:
        page = get_page()
        locator_string = str(args.get("locator") or "").strip()
        count = 0
        if locator_string:
            try:
                count = await self._resolve_locator(page, locator_string).count()
            except Exception:  # noqa: BLE001
                count = 0
        return {"valid": count == 1, "count": count}

    async def _tool_action_click(self, args: dict[str, Any]) -> dict[str, Any]:
        page = get_page()
        locator_string = str(args.get("locator") or "").strip()
        timeout = int(args.get("timeout") or 30000)
        try:
            await self._resolve_locator(page, locator_string).first.click(timeout=timeout)
            return {"success": True, "error": None}
        except Exception as exc:  # noqa: BLE001
            return {"success": False, "error": str(exc)}

    async def _tool_action_fill(self, args: dict[str, Any]) -> dict[str, Any]:
        page = get_page()
        locator_string = str(args.get("locator") or "").strip()
        value = str(args.get("value") or "")
        timeout = int(args.get("timeout") or 30000)
        try:
            await self._resolve_locator(page, locator_string).first.fill(value, timeout=timeout)
            return {"success": True, "error": None}
        except Exception as exc:  # noqa: BLE001
            return {"success": False, "error": str(exc)}

    async def _tool_action_assert(self, args: dict[str, Any]) -> dict[str, Any]:
        page = get_page()
        locator_text = str(args.get("locator") or "").strip()
        assertion = str(args.get("assertion") or "").strip()
        expected_value = args.get("expected_value")
        timeout = int(args.get("timeout") or 5000)

        try:
            locator = self._resolve_locator(page, locator_text).first
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
                try:
                    actual_text = await locator.inner_text(timeout=timeout)
                except Exception:  # noqa: BLE001
                    actual_text = await locator.text_content(timeout=timeout)

                normalized_actual = self._normalize_assertion_text(actual_text)
                normalized_expected = self._normalize_assertion_text(str(expected_value))
                if normalized_expected not in normalized_actual:
                    return {
                        "success": False,
                        "error": (
                            "Expected normalized text to contain "
                            f"{normalized_expected!r}, got {normalized_actual!r}"
                        ),
                        "actual_text": normalized_actual,
                        "expected_text": normalized_expected,
                    }
                return {
                    "success": True,
                    "assertion": "has_text",
                    "actual_text": normalized_actual,
                    "expected_text": normalized_expected,
                }
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
        invalid_literals = {"", "current page", "same page", "this page", "current"}
        valid_prefixes = ("http://", "https://", "file://", "about:")

        if url.lower() in invalid_literals or not url.startswith(valid_prefixes):
            return {"success": False, "error": "Invalid navigation URL", "url": url}

        if url == page.url:
            return {
                "success": True,
                "skipped": True,
                "reason": "Already on requested URL",
                "url": url,
            }

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

    def _build_locator_candidates(self, element_data: dict[str, Any]) -> list[dict[str, str]]:
        text = self._normalize_space(str(element_data.get("text") or ""))
        tag = re.sub(r"[^a-zA-Z0-9:_-]", "", str(element_data.get("tag") or "").strip())
        role = str(element_data.get("role") or "").strip() or self._infer_role(element_data)
        class_name = str(element_data.get("class") or "").strip()
        classes = [
            re.sub(r"[^a-zA-Z0-9_-]", "", item)
            for item in class_name.split()
            if re.sub(r"[^a-zA-Z0-9_-]", "", item)
        ]
        partial_text = text[:50].strip()
        candidates: list[dict[str, str]] = []

        data_testid = str(element_data.get("data_testid") or "").strip()
        if data_testid:
            candidates.append(
                {
                    "strategy": "data-testid",
                    "locator": f'get_by_test_id("{self._tool_string_escape(data_testid)}")',
                }
            )

        aria_label = self._normalize_space(str(element_data.get("aria_label") or ""))
        if aria_label:
            candidates.append(
                {
                    "strategy": "aria-label",
                    "locator": f'get_by_label("{self._tool_string_escape(aria_label)}")',
                }
            )

        element_id = str(element_data.get("id") or "").strip()
        if element_id:
            candidates.append({"strategy": "id", "locator": f"#{self._css_escape(element_id)}"})

        placeholder = self._normalize_space(str(element_data.get("placeholder") or ""))
        if placeholder:
            candidates.append(
                {
                    "strategy": "placeholder",
                    "locator": f'get_by_placeholder("{self._tool_string_escape(placeholder)}")',
                }
            )

        if text:
            candidates.append(
                {
                    "strategy": "exact_text",
                    "locator": f'get_by_text("{self._tool_string_escape(text)}", exact=True)',
                }
            )

        if partial_text:
            candidates.append(
                {
                    "strategy": "partial_text",
                    "locator": f'get_by_text("{self._tool_string_escape(partial_text)}", exact=False)',
                }
            )

        if role and partial_text:
            candidates.append(
                {
                    "strategy": "role+name",
                    "locator": (
                        f'get_by_role("{self._tool_string_escape(role)}", '
                        f'name="{self._tool_string_escape(partial_text)}")'
                    ),
                }
            )

        css_locator = self._build_locator_from_strategy("css", element_data)
        if css_locator:
            candidates.append({"strategy": "css", "locator": css_locator})

        if tag and partial_text:
            candidates.append(
                {
                    "strategy": "relative_xpath",
                    "locator": f"//{tag}[contains(normalize-space(.), {self._xpath_literal(partial_text)})]",
                }
            )

        if tag:
            if element_id:
                absolute_xpath = f"//{tag}[@id={self._xpath_literal(element_id)}]"
            elif classes:
                absolute_xpath = f"//{tag}[contains(@class, {self._xpath_literal(classes[0])})]"
            else:
                absolute_xpath = f"//{tag}"
            candidates.append({"strategy": "absolute_xpath", "locator": absolute_xpath})

        return candidates

    def _resolve_locator(self, page: Any, locator_string: str) -> Any:
        locator_string = str(locator_string or "").strip()
        if not locator_string:
            raise ValueError("locator is required")

        if match := re.fullmatch(r'get_by_test_id\("((?:\\.|[^"])*)"\)', locator_string):
            return page.get_by_test_id(self._tool_string_unescape(match.group(1)))

        if match := re.fullmatch(r'get_by_label\("((?:\\.|[^"])*)"\)', locator_string):
            return page.get_by_label(self._tool_string_unescape(match.group(1)))

        if match := re.fullmatch(r'get_by_placeholder\("((?:\\.|[^"])*)"\)', locator_string):
            return page.get_by_placeholder(self._tool_string_unescape(match.group(1)))

        if match := re.fullmatch(
            r'get_by_text\("((?:\\.|[^"])*)", exact=(True|False)\)', locator_string
        ):
            return page.get_by_text(
                self._tool_string_unescape(match.group(1)),
                exact=match.group(2) == "True",
            )

        if match := re.fullmatch(
            r'get_by_role\("((?:\\.|[^"])*)", name="((?:\\.|[^"])*)"\)', locator_string
        ):
            return page.get_by_role(
                self._tool_string_unescape(match.group(1)),
                name=self._tool_string_unescape(match.group(2)),
            )

        return page.locator(locator_string)

    def _is_stable_locator_strategy(self, strategy: str) -> bool:
        return strategy in {"data-testid", "aria-label", "id", "role+name"}

    def _infer_role(self, element_data: dict[str, Any]) -> str:
        explicit_role = str(element_data.get("role") or "").strip()
        if explicit_role:
            return explicit_role

        tag = str(element_data.get("tag") or "").strip().lower()
        input_type = str(element_data.get("type") or "").strip().lower()

        if tag == "button":
            return "button"
        if tag == "a":
            return "link"
        if tag == "select":
            return "combobox"
        if tag == "textarea":
            return "textbox"
        if tag == "input":
            if input_type in {"button", "submit", "reset"}:
                return "button"
            if input_type in {"checkbox"}:
                return "checkbox"
            if input_type in {"radio"}:
                return "radio"
            return "textbox"
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

    def _normalize_assertion_text(self, value: str | None) -> str:
        if value is None:
            return ""
        normalized = str(value)
        normalized = normalized.replace("&nbsp;", " ")
        normalized = normalized.replace("\u00a0", " ")
        normalized = normalized.replace("\u202f", " ")
        normalized = normalized.replace("\u2007", " ")
        normalized = normalized.replace("\u0000", "")
        normalized = re.sub(r"[\x01-\x08\x0b\x0c\x0e-\x1f\x7f]", "", normalized)
        normalized = re.sub(r"\s+", " ", normalized)
        return normalized.strip()

    def _tool_string_escape(self, value: str) -> str:
        return value.replace("\\", "\\\\").replace('"', '\\"')

    def _tool_string_unescape(self, value: str) -> str:
        return value.replace('\\"', '"').replace("\\\\", "\\")

    def _xpath_literal(self, value: str) -> str:
        if "'" not in value:
            return f"'{value}'"
        if '"' not in value:
            return f'"{value}"'
        parts = value.split("'")
        quoted_parts = [f"'{part}'" for part in parts]
        return 'concat(' + ', "\'", '.join(quoted_parts) + ')'
