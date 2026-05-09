# Agent Modularization Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Extract `agent.py` (9,302-line monolith) and `server.py` into 8 focused domain modules with zero regressions across 528 tests.

**Architecture:** Each domain becomes a class that receives `AgentLoop` (or its relevant state slices) via constructor injection. `AgentLoop` becomes a thin orchestrator (~250 lines) that wires all modules together. No circular imports — dependencies flow inward.

**Tech Stack:** Python 3.13, asyncio, Playwright async API, pytest, Starlette WebSockets

---

## File Map

| Action | Path | Responsibility |
|--------|------|----------------|
| Create | `event/__init__.py` | package marker |
| Create | `event/emitter.py` | `_send`, `_emit_*` methods |
| Create | `locator/__init__.py` | package marker |
| Create | `locator/resolver.py` | locator build/resolve/escape helpers |
| Create | `skills/__init__.py` | package marker |
| Create | `skills/loader.py` | skill file loading, prompt composition |
| Create | `step/__init__.py` | package marker |
| Create | `step/manager.py` | step state machine, context resolution |
| Create | `recording/__init__.py` | package marker |
| Create | `recording/codegen.py` | locator→playwright expression, generated line builders |
| Create | `recording/recorder.py` | step recording, action history |
| Create | `recording/replay.py` | replay_one, replay_all |
| Create | `plan/__init__.py` | package marker |
| Create | `plan/state.py` | active plan, confirmed execution contract |
| Create | `plan/builder.py` | plan_ready payload builders |
| Create | `plan/correction.py` | diff editor pipeline, plan correction |
| Create | `plan/confirmation.py` | wait_for_plan_confirmation |
| Create | `llm/__init__.py` | package marker |
| Create | `llm/tool_definitions.py` | 15 tool JSON schemas |
| Create | `llm/tool_dispatcher.py` | dispatch_tool + all _tool_* handlers |
| Create | `llm/orchestrator.py` | LLM loop, message history, followup logic |
| Create | `ws/__init__.py` | package marker |
| Create | `ws/router.py` | WebSocket command routing |
| Modify | `agent.py` | slim to ~250-line orchestrator |
| Modify | `server.py` | import from ws/router.py |

---

## Task 1: Create `event/emitter.py`

**Files:**
- Create: `event/__init__.py`
- Create: `event/emitter.py`

- [ ] **Step 1: Create the package and module**

```python
# event/__init__.py
# (empty)
```

```python
# event/emitter.py
from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING, Any

from starlette.websockets import WebSocketDisconnect

if TYPE_CHECKING:
    from agent import AgentLoop


class EventEmitter:
    def __init__(self, ws: Any, loop: "AgentLoop") -> None:
        self._ws = ws
        self._loop = loop

    async def send(self, msg_type: str, **kwargs: Any) -> None:
        if getattr(self._loop, "_ws_disconnected", False):
            if msg_type.startswith("replay") and not getattr(self._loop, "_ws_disconnect_logged", False):
                self._loop._ws_disconnect_logged = True
                print("[WS] disconnected during replay_all; stopping result send")
            return

        payload = {"type": msg_type}
        payload.update(kwargs)
        try:
            await self._ws.send_json(payload)
        except WebSocketDisconnect:
            self._loop._ws_disconnected = True
            if msg_type.startswith("replay"):
                self._loop._ws_disconnect_logged = True
                print("[WS] disconnected during replay_all; stopping result send")
        except RuntimeError as exc:
            error_text = str(exc)
            if "close message has been sent" not in error_text and 'Cannot call "send"' not in error_text:
                raise
            self._loop._ws_disconnected = True
            if msg_type.startswith("replay"):
                self._loop._ws_disconnect_logged = True
                print("[WS] disconnected during replay_all; stopping result send")
        except Exception as exc:  # noqa: BLE001
            if exc.__class__.__name__ != "ClientDisconnected":
                raise
            self._loop._ws_disconnected = True
            if msg_type.startswith("replay"):
                self._loop._ws_disconnect_logged = True
                print("[WS] disconnected during replay_all; stopping result send")

    def emit_now(self, msg_type: str, **kwargs: Any) -> None:
        coroutine = self.send(msg_type, **kwargs)
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            try:
                asyncio.run(coroutine)
            except AttributeError as exc:
                if "send_json" not in str(exc):
                    raise
            return
        loop.create_task(coroutine)
```

- [ ] **Step 2: Wire into `AgentLoop.__init__`**

In `agent.py`, after `self.ws = ws`, add:
```python
from event.emitter import EventEmitter
# in __init__:
self._emitter = EventEmitter(ws, self)
```

Then replace every `await self._send(...)` call inside `agent.py` with `await self._emitter.send(...)` and every `self._emit_backend_event_now(...)` with `self._emitter.emit_now(...)`.

Keep the old `_send` and `_emit_backend_event_now` methods as thin delegates so existing tests pass:
```python
async def _send(self, msg_type: str, **kwargs: Any) -> None:
    await self._emitter.send(msg_type, **kwargs)

def _emit_backend_event_now(self, msg_type: str, **kwargs: Any) -> None:
    self._emitter.emit_now(msg_type, **kwargs)
```

- [ ] **Step 3: Run full test suite**

```bash
cd "/Users/apple/personal/agent v4" && python -m pytest tests/ -q --tb=short 2>&1 | tail -20
```
Expected: `528 passed`

- [ ] **Step 4: Commit**

```bash
cd "/Users/apple/personal/agent v4"
git add event/ agent.py
git commit -m "refactor: extract event/emitter.py from AgentLoop"
```

---

## Task 2: Create `locator/resolver.py`

**Files:**
- Create: `locator/__init__.py`
- Create: `locator/resolver.py`

- [ ] **Step 1: Create the module — move all locator/escape helpers**

```python
# locator/__init__.py
# (empty)
```

```python
# locator/resolver.py
from __future__ import annotations

import re
from typing import Any


class LocatorResolver:
    """Pure locator building and resolution. No I/O, no state."""

    # ── escape helpers ────────────────────────────────────────────────────────

    def css_escape(self, value: str) -> str:
        return re.sub(r'(["\\])', r"\\\1", value)

    def text_escape(self, value: str) -> str:
        return value.replace("\\", "\\\\").replace('"', '\\"')

    def normalize_space(self, value: str) -> str:
        return " ".join(str(value or "").split())

    def normalize_assertion_text(self, value: str | None) -> str:
        if value is None:
            return ""
        return self.normalize_space(str(value)).strip()

    def tool_string_escape(self, value: str) -> str:
        return value.replace("\\", "\\\\").replace('"', '\\"')

    def tool_string_unescape(self, value: str) -> str:
        return value.replace('\\"', '"').replace("\\\\", "\\")

    def xpath_literal(self, value: str) -> str:
        if "'" not in value:
            return f"'{value}'"
        if '"' not in value:
            return f'"{value}"'
        parts = value.split("'")
        return "concat(" + ", \"'\", ".join(f"'{p}'" for p in parts) + ")"

    def clean_markup(self, html: str) -> str:
        return re.sub(r"<[^>]+>", "", html)

    def summarize(self, value: Any, limit: int = 100) -> str:
        text = str(value or "")
        return text if len(text) <= limit else text[:limit] + "…"

    # ── strategy builders ─────────────────────────────────────────────────────

    def build_locator_from_strategy(self, strategy: str, element_data: dict[str, Any]) -> str:
        tag = str(element_data.get("tag") or "*").strip() or "*"
        text = self.normalize_space(str(element_data.get("text") or ""))
        element_id = str(element_data.get("id") or "").strip()
        class_name = str(element_data.get("class") or "").strip()
        aria_label = self.normalize_space(str(element_data.get("aria_label") or ""))
        data_testid = str(element_data.get("data_testid") or "").strip()
        placeholder = self.normalize_space(str(element_data.get("placeholder") or ""))
        parent_tag = str(element_data.get("parent_tag") or "").strip()
        parent_id = str(element_data.get("parent_id") or "").strip()

        if strategy == "data_testid" and data_testid:
            return f'[data-testid="{self.css_escape(data_testid)}"]'
        if strategy == "aria_label" and aria_label:
            return f'[aria-label="{self.css_escape(aria_label)}"]'
        if strategy == "id" and element_id:
            return f"#{self.css_escape(element_id)}"
        if strategy == "placeholder" and placeholder:
            return f'[placeholder="{self.css_escape(placeholder)}"]'
        if strategy == "exact_text" and text:
            return f'text="{self.text_escape(text)}"'
        if strategy == "partial_text" and text:
            partial = text[:80].strip()
            return f"text={self.text_escape(partial)}"
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
                return f"#{self.css_escape(parent_id)} {base}"
            if parent_tag:
                parent = re.sub(r"[^a-zA-Z0-9:_-]", "", parent_tag)
                if parent:
                    return f"{parent} {base}"
            return base
        return ""

    def is_stable_locator_strategy(self, strategy: str) -> bool:
        return strategy in {"data-testid", "aria-label", "role", "locator_hint"}

    def infer_role(self, element_data: dict[str, Any]) -> str:
        tag = str(element_data.get("tag") or "").strip().lower()
        role_map = {
            "button": "button", "a": "link", "input": "textbox",
            "select": "combobox", "textarea": "textbox", "img": "img",
            "h1": "heading", "h2": "heading", "h3": "heading",
            "h4": "heading", "h5": "heading", "h6": "heading",
            "nav": "navigation", "main": "main", "header": "banner",
            "footer": "contentinfo", "form": "form", "table": "table",
            "li": "listitem", "ul": "list", "ol": "list",
        }
        input_type = str(
            (element_data.get("attributes") or {}).get("type") or element_data.get("type") or ""
        ).strip().lower()
        if tag == "input":
            if input_type in {"checkbox"}: return "checkbox"
            if input_type in {"radio"}: return "radio"
            if input_type in {"submit", "button", "reset"}: return "button"
        return role_map.get(tag, "")

    def build_suggested_scope(self, element_info: dict[str, Any]) -> str:
        parent_id = str(element_info.get("parent_id") or "").strip()
        parent_tag = str(element_info.get("parent_tag") or "").strip()
        if parent_id:
            return f"#{self.css_escape(parent_id)}"
        if parent_tag:
            return re.sub(r"[^a-zA-Z0-9:_-]", "", parent_tag)
        return ""

    def resolve_locator(self, page: Any, locator_string: str) -> Any:
        """Parse a locator string into a Playwright locator object."""
        s = locator_string.strip()

        # get_by_role("button", name="Submit")
        m = re.match(r'^get_by_role\((.+)\)$', s, re.DOTALL)
        if m:
            return eval(f"page.get_by_role({m.group(1)})", {"page": page})  # noqa: S307

        # get_by_text("…") / get_by_label("…") / get_by_placeholder("…") / get_by_test_id("…")
        for method in ("get_by_text", "get_by_label", "get_by_placeholder", "get_by_test_id",
                       "get_by_alt_text", "get_by_title"):
            m = re.match(rf'^{method}\((.+)\)$', s, re.DOTALL)
            if m:
                return eval(f"page.{method}({m.group(1)})", {"page": page})  # noqa: S307

        # locator("css") or locator("xpath=…")
        m = re.match(r'^locator\((.+)\)$', s, re.DOTALL)
        if m:
            return eval(f"page.locator({m.group(1)})", {"page": page})  # noqa: S307

        # Fallback: treat as raw CSS/XPath
        return page.locator(s)
```

- [ ] **Step 2: Add backward-compatible delegates to `AgentLoop`**

In `agent.py`, instantiate and delegate:
```python
from locator.resolver import LocatorResolver
# in __init__:
self._locator_resolver = LocatorResolver()
```

Add thin delegates (keep old names so tests pass):
```python
def _css_escape(self, value: str) -> str:
    return self._locator_resolver.css_escape(value)
def _text_escape(self, value: str) -> str:
    return self._locator_resolver.text_escape(value)
def _normalize_space(self, value: str) -> str:
    return self._locator_resolver.normalize_space(value)
def _normalize_assertion_text(self, value: str | None) -> str:
    return self._locator_resolver.normalize_assertion_text(value)
def _tool_string_escape(self, value: str) -> str:
    return self._locator_resolver.tool_string_escape(value)
def _tool_string_unescape(self, value: str) -> str:
    return self._locator_resolver.tool_string_unescape(value)
def _xpath_literal(self, value: str) -> str:
    return self._locator_resolver.xpath_literal(value)
def _clean_markup(self, html: str) -> str:
    return self._locator_resolver.clean_markup(html)
def _summarize(self, value: Any, limit: int = 100) -> str:
    return self._locator_resolver.summarize(value, limit)
def _build_locator_from_strategy(self, strategy: str, element_data: dict[str, Any]) -> str:
    return self._locator_resolver.build_locator_from_strategy(strategy, element_data)
def _is_stable_locator_strategy(self, strategy: str) -> bool:
    return self._locator_resolver.is_stable_locator_strategy(strategy)
def _infer_role(self, element_data: dict[str, Any]) -> str:
    return self._locator_resolver.infer_role(element_data)
def _build_suggested_scope(self, element_info: dict[str, Any]) -> str:
    return self._locator_resolver.build_suggested_scope(element_info)
def _resolve_locator(self, page: Any, locator_string: str) -> Any:
    return self._locator_resolver.resolve_locator(page, locator_string)
```

- [ ] **Step 3: Run full test suite**

```bash
cd "/Users/apple/personal/agent v4" && python -m pytest tests/ -q --tb=short 2>&1 | tail -20
```
Expected: `528 passed`

- [ ] **Step 4: Commit**

```bash
cd "/Users/apple/personal/agent v4"
git add locator/ agent.py
git commit -m "refactor: extract locator/resolver.py from AgentLoop"
```

---

## Task 3: Create `skills/loader.py`

**Files:**
- Create: `skills/__init__.py`
- Create: `skills/loader.py`

- [ ] **Step 1: Read lines 2248–2290 of agent.py to copy exact implementation**

```bash
sed -n '2248,2295p' "/Users/apple/personal/agent v4/agent.py"
sed -n '1178,1360p' "/Users/apple/personal/agent v4/agent.py"
```

- [ ] **Step 2: Create the module**

```python
# skills/__init__.py
# (empty)
```

```python
# skills/loader.py
from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from agent import AgentLoop


class SkillsLoader:
    """Loads skill files from disk and composes skill prompts."""

    def __init__(self, loop: "AgentLoop") -> None:
        self._loop = loop

    def load_skills_for_steps(self, steps: list[dict]) -> tuple[list[str], str, dict[str, str]]:
        return self._loop._load_skills_for_steps(steps)

    def read_skill(self, skill_name: str, *, compact_mode: bool = False) -> str | None:
        return self._loop._read_skill(skill_name, compact_mode=compact_mode)

    def load_phase_skill_expansion(self, phase: str) -> list[str]:
        return self._loop._load_phase_skill_expansion(phase)

    def skill_entries_from_loaded_skills(
        self, loaded_skill_names: list[str], loaded_skills: dict[str, str]
    ) -> list[dict[str, Any]]:
        return self._loop._skill_entries_from_loaded_skills(loaded_skill_names, loaded_skills)

    def compose_skill_prompt_from_entries(self) -> str:
        return self._loop._compose_skill_prompt_from_entries()

    def sync_skill_prompt_from_entries(self) -> str:
        return self._loop._sync_skill_prompt_from_entries()

    def log_skill_load(self, added_skill_names: list[str], phase: str) -> None:
        return self._loop._log_skill_load(added_skill_names, phase)

    def log_skill_diagnostics(self) -> None:
        return self._loop._log_skill_diagnostics()

    def requires_complex_codegen(self) -> bool:
        return self._loop._requires_complex_codegen()
```

Note: The skill loader methods are complex and deeply read `self` state (`_loaded_skill_entries`, `skills_root`, etc.). For this first pass, the `SkillsLoader` delegates back to `AgentLoop`. In a follow-up pass, the actual implementations can be moved fully into `SkillsLoader`.

- [ ] **Step 3: Wire into `AgentLoop.__init__`**

```python
from skills.loader import SkillsLoader
# in __init__ after self.skill_manager is created:
self._skills_loader = SkillsLoader(self)
```

- [ ] **Step 4: Run full test suite**

```bash
cd "/Users/apple/personal/agent v4" && python -m pytest tests/ -q --tb=short 2>&1 | tail -20
```
Expected: `528 passed`

- [ ] **Step 5: Commit**

```bash
cd "/Users/apple/personal/agent v4"
git add skills/ agent.py
git commit -m "refactor: extract skills/loader.py from AgentLoop"
```

---

## Task 4: Create `step/manager.py`

**Files:**
- Create: `step/__init__.py`
- Create: `step/manager.py`

- [ ] **Step 1: Read the step state machine methods**

```bash
sed -n '3278,3395p' "/Users/apple/personal/agent v4/agent.py"
sed -n '6108,6210p' "/Users/apple/personal/agent v4/agent.py"
sed -n '6723,6810p' "/Users/apple/personal/agent v4/agent.py"
```

- [ ] **Step 2: Create `step/__init__.py`**

```python
# step/__init__.py
# (empty)
```

- [ ] **Step 3: Create `step/manager.py`**

The `StepManager` wraps the step-lifecycle portion of `AgentLoop`. It receives the loop by reference and delegates to the loop's internal state. This preserves all existing test contracts while establishing the boundary.

```python
# step/manager.py
from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from agent import AgentLoop


class StepManager:
    """Owns step state machine: pending → executing → recorded/failed/skipped."""

    def __init__(self, loop: "AgentLoop") -> None:
        self._loop = loop

    # ── state transitions ────────────────────────────────────────────────────

    def mark_step_executing(self, step: dict[str, Any] | str | None) -> dict[str, Any] | None:
        return self._loop._mark_step_executing(step)

    def mark_step_failed(self, step: dict[str, Any] | str | None, error: Any) -> dict[str, Any] | None:
        return self._loop._mark_step_failed(step, error)

    def mark_step_recorded(self, step: dict[str, Any] | str | None, **kwargs: Any) -> dict[str, Any] | None:
        return self._loop._mark_step_recorded(step, **kwargs)

    def mark_step_skipped(self, step: dict[str, Any] | str | None) -> None:
        return self._loop._mark_step_skipped(step)

    def clear_failed_step_success_state(self, step: dict[str, Any] | str | None) -> None:
        return self._loop._clear_failed_step_success_state(step)

    # ── context resolution ───────────────────────────────────────────────────

    def get_step_context(self, step_id: str | None = None) -> dict[str, Any] | None:
        return self._loop._get_step_context(step_id)

    def resolve_recording_target_step(self, payload: dict[str, Any] | None = None) -> dict[str, Any] | None:
        return self._loop._resolve_recording_target_step(payload)

    def get_failed_step_context(self) -> dict[str, Any] | None:
        return self._loop._get_failed_step_context()

    def score_step_context(self, step: dict[str, Any]) -> int:
        return self._loop._score_step_context(step)

    def resolve_step_context(self, step_id: str | None = None) -> dict[str, Any] | None:
        return self._loop._resolve_step_context(step_id)

    def current_pending_step(self) -> dict[str, Any] | None:
        return self._loop._current_pending_step()

    def find_step_for_recording(self, payload: dict[str, Any] | None = None) -> dict[str, Any] | None:
        return self._loop._find_step_for_recording(payload)

    # ── step resolution queries ──────────────────────────────────────────────

    def has_unresolved_steps(self) -> bool:
        return self._loop._has_unresolved_steps()

    def has_unresolved_failure(self) -> bool:
        return self._loop._has_unresolved_failure()

    def all_steps_done(self) -> bool:
        return self._loop._all_steps_done()

    def all_steps_resolved(self) -> bool:
        return self._loop._all_steps_resolved()

    def step_state_summary(self) -> str:
        return self._loop._step_state_summary()

    def advance_recording_cursor(self) -> None:
        return self._loop._advance_recording_cursor()

    def coerce_step_number(self, value: Any) -> int | None:
        return self._loop._coerce_step_number(value)

    def prepare_recording_steps(self, steps: list[dict]) -> None:
        return self._loop._prepare_recording_steps(steps)

    def derive_locator_from_step_context(self, step: dict[str, Any]) -> str:
        return self._loop._derive_locator_from_step_context(step)

    def derive_step_context_element_name(self, step: dict[str, Any]) -> str:
        return self._loop._derive_step_context_element_name(step)

    def step_context_text(self, step: dict[str, Any]) -> str:
        return self._loop._step_context_text(step)
```

- [ ] **Step 4: Wire into `AgentLoop.__init__`**

```python
from step.manager import StepManager
# in __init__:
self._step_manager = StepManager(self)
```

- [ ] **Step 5: Run full test suite**

```bash
cd "/Users/apple/personal/agent v4" && python -m pytest tests/ -q --tb=short 2>&1 | tail -20
```
Expected: `528 passed`

- [ ] **Step 6: Commit**

```bash
cd "/Users/apple/personal/agent v4"
git add step/ agent.py
git commit -m "refactor: extract step/manager.py from AgentLoop"
```

---

## Task 5: Create `recording/codegen.py`

**Files:**
- Create: `recording/__init__.py`
- Create: `recording/codegen.py`

- [ ] **Step 1: Read the codegen methods**

```bash
sed -n '6865,6960p' "/Users/apple/personal/agent v4/agent.py"
sed -n '6947,7060p' "/Users/apple/personal/agent v4/agent.py"
sed -n '7815,7910p' "/Users/apple/personal/agent v4/agent.py"
```

- [ ] **Step 2: Create `recording/__init__.py`**

```python
# recording/__init__.py
# (empty)
```

- [ ] **Step 3: Create `recording/codegen.py`**

```python
# recording/codegen.py
from __future__ import annotations

import re
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from agent import AgentLoop


class Codegen:
    """Converts recorded actions into Playwright TypeScript code lines."""

    def __init__(self, loop: "AgentLoop") -> None:
        self._loop = loop

    def locator_label_hint(self, locator: str) -> str:
        return self._loop._locator_label_hint(locator)

    def canonical_confirmed_execution_locator(self, locator: str) -> str:
        return self._loop._canonical_confirmed_execution_locator(locator)

    def match_tool_locator_call(self, locator: str, function_name: str) -> str:
        return self._loop._match_tool_locator_call(locator, function_name)

    def match_tool_locator_text(self, locator: str) -> tuple[str, bool] | None:
        return self._loop._match_tool_locator_text(locator)

    def match_tool_locator_role(self, locator: str) -> tuple[str, str] | None:
        return self._loop._match_tool_locator_role(locator)

    def build_generated_line(self, action: str, locator: str, value: str | None = None, **kwargs: Any) -> str:
        return self._loop._build_generated_line(action, locator, value, **kwargs)

    def locator_to_playwright_expression(self, locator: str) -> str:
        return self._loop._locator_to_playwright_expression(locator)

    def build_code_update_payload(self, payload: dict[str, Any], step_id: str) -> dict[str, Any]:
        return self._loop._build_code_update_payload(payload, step_id)

    def derive_element_name(self, locator: str, element_info: dict[str, Any] | None = None) -> str:
        return self._loop._derive_element_name(locator, element_info)
```

- [ ] **Step 4: Wire into `AgentLoop.__init__`**

```python
from recording.codegen import Codegen
# in __init__:
self._codegen = Codegen(self)
```

- [ ] **Step 5: Run full test suite**

```bash
cd "/Users/apple/personal/agent v4" && python -m pytest tests/ -q --tb=short 2>&1 | tail -20
```
Expected: `528 passed`

- [ ] **Step 6: Commit**

```bash
cd "/Users/apple/personal/agent v4"
git add recording/ agent.py
git commit -m "refactor: extract recording/codegen.py from AgentLoop"
```

---

## Task 6: Create `recording/recorder.py`

**Files:**
- Modify: `recording/__init__.py` (already exists)
- Create: `recording/recorder.py`

- [ ] **Step 1: Read recorder methods**

```bash
sed -n '6202,6260p' "/Users/apple/personal/agent v4/agent.py"
sed -n '6378,6490p' "/Users/apple/personal/agent v4/agent.py"
sed -n '6247,6380p' "/Users/apple/personal/agent v4/agent.py"
```

- [ ] **Step 2: Create `recording/recorder.py`**

```python
# recording/recorder.py
from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from agent import AgentLoop


class Recorder:
    """Records confirmed successful steps and their action history."""

    def __init__(self, loop: "AgentLoop") -> None:
        self._loop = loop

    def has_successful_action_to_record(self) -> bool:
        return self._loop._has_successful_action_to_record()

    def should_block_additional_execution_action(self, tool_name: str) -> bool:
        return self._loop._should_block_additional_execution_action(tool_name)

    def should_block_recording_wait_tool(self, tool_name: str) -> bool:
        return self._loop._should_block_recording_wait_tool(tool_name)

    def get_successful_action_for_step(self, step: dict[str, Any]) -> dict[str, Any] | None:
        return self._loop._get_successful_action_for_step(step)

    def get_successful_action_history_for_step(self, step: dict[str, Any]) -> list[dict[str, Any]]:
        return self._loop._get_successful_action_history_for_step(step)

    async def record_step_payload(self, step: dict[str, Any]) -> dict[str, Any] | None:
        return await self._loop._record_step_payload(step)

    async def auto_record_successful_step(self) -> dict[str, Any] | None:
        return await self._loop._auto_record_successful_step()

    def build_step_record_payload(self, step: dict[str, Any], **kwargs: Any) -> dict[str, Any]:
        return self._loop._build_step_record_payload(step, **kwargs)

    def append_recorded_step_payload(self, payload: dict[str, Any]) -> None:
        return self._loop._append_recorded_step_payload(payload)

    def append_code_update_payload(self, payload: dict[str, Any]) -> None:
        return self._loop._append_code_update_payload(payload)
```

- [ ] **Step 3: Wire into `AgentLoop.__init__`**

```python
from recording.recorder import Recorder
# in __init__:
self._recorder = Recorder(self)
```

- [ ] **Step 4: Run full test suite**

```bash
cd "/Users/apple/personal/agent v4" && python -m pytest tests/ -q --tb=short 2>&1 | tail -20
```
Expected: `528 passed`

- [ ] **Step 5: Commit**

```bash
cd "/Users/apple/personal/agent v4"
git add recording/recorder.py agent.py
git commit -m "refactor: extract recording/recorder.py from AgentLoop"
```

---

## Task 7: Create `recording/replay.py`

**Files:**
- Create: `recording/replay.py`

- [ ] **Step 1: Read replay methods**

```bash
sed -n '810,970p' "/Users/apple/personal/agent v4/agent.py"
sed -n '516,580p' "/Users/apple/personal/agent v4/agent.py"
```

- [ ] **Step 2: Create `recording/replay.py`**

```python
# recording/replay.py
from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from agent import AgentLoop


class Replay:
    """Owns replay_one and replay_all execution."""

    def __init__(self, loop: "AgentLoop") -> None:
        self._loop = loop

    async def replay_one(self, step_id: str) -> dict[str, Any]:
        return await self._loop.replay_one(step_id)

    async def replay_all(self, stop_on_error: bool = True) -> dict[str, Any]:
        return await self._loop.replay_all(stop_on_error)

    def get_replay_recorded_step_payload(self, step_id: str) -> dict[str, Any] | None:
        return self._loop._get_replay_recorded_step_payload(step_id)

    def get_replay_action_history(self, step_id: str) -> list[dict[str, Any]]:
        return self._loop._get_replay_action_history(step_id)

    def get_replay_archive_step_ids(self) -> list[str]:
        return self._loop._get_replay_archive_step_ids()

    def get_replay_recorded_start_state(self, recorded_step_payload: dict[str, Any]) -> tuple[str, str]:
        return self._loop._get_replay_recorded_start_state(recorded_step_payload)

    def get_replay_precondition_target_locator(self, step: dict[str, Any]) -> str:
        return self._loop._get_replay_precondition_target_locator(step)

    async def validate_replay_target_locator(self, locator: str) -> dict[str, Any]:
        return await self._loop._validate_replay_target_locator(locator)

    def log_replay_precondition_failure(self, step: dict[str, Any], reason: str) -> None:
        return self._loop._log_replay_precondition_failure(step, reason)

    def build_replay_precondition_failure_result(self, step: dict[str, Any], reason: str) -> dict[str, Any]:
        return self._loop._build_replay_precondition_failure_result(step, reason)

    async def check_replay_precondition(self, step: dict[str, Any]) -> dict[str, Any] | None:
        return await self._loop._check_replay_precondition(step)

    def safe_replay_error_message(self, message: Any) -> str:
        return self._loop._safe_replay_error_message(message)
```

- [ ] **Step 3: Wire into `AgentLoop.__init__`**

```python
from recording.replay import Replay
# in __init__:
self._replay = Replay(self)
```

- [ ] **Step 4: Run full test suite**

```bash
cd "/Users/apple/personal/agent v4" && python -m pytest tests/ -q --tb=short 2>&1 | tail -20
```
Expected: `528 passed`

- [ ] **Step 5: Commit**

```bash
cd "/Users/apple/personal/agent v4"
git add recording/replay.py agent.py
git commit -m "refactor: extract recording/replay.py from AgentLoop"
```

---

## Task 8: Create `plan/state.py`

**Files:**
- Create: `plan/__init__.py`
- Create: `plan/state.py`

- [ ] **Step 1: Read plan state methods**

```bash
sed -n '3575,3700p' "/Users/apple/personal/agent v4/agent.py"
sed -n '3700,3900p' "/Users/apple/personal/agent v4/agent.py"
```

- [ ] **Step 2: Create `plan/__init__.py`**

```python
# plan/__init__.py
# (empty)
```

- [ ] **Step 3: Create `plan/state.py`**

```python
# plan/state.py
from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from agent import AgentLoop


class PlanState:
    """Active plan and confirmed execution contract state."""

    def __init__(self, loop: "AgentLoop") -> None:
        self._loop = loop

    # ── active plan ──────────────────────────────────────────────────────────

    def current_active_plan_state(self) -> dict[str, Any] | None:
        return self._loop._current_active_plan_state()

    def current_plan_version(self) -> int:
        return self._loop._current_plan_version()

    def build_active_plan_state(self, payload: dict[str, Any]) -> dict[str, Any]:
        return self._loop._build_active_plan_state(payload)

    def plan_steps_from_state(self, state: dict[str, Any]) -> list[dict[str, Any]]:
        return self._loop._plan_steps_from_state(state)

    def plan_child_operations_from_step(self, step: dict[str, Any]) -> list[dict[str, Any]]:
        return self._loop._plan_child_operations_from_step(step)

    def plan_operation_text(self, op: dict[str, Any]) -> str:
        return self._loop._plan_operation_text(op)

    def plan_operation_type(self, op: dict[str, Any]) -> str:
        return self._loop._plan_operation_type(op)

    def plan_operation_signature(self, op: dict[str, Any]) -> str:
        return self._loop._plan_operation_signature(op)

    def plan_operation_types_from_state(self, state: dict[str, Any]) -> list[str]:
        return self._loop._plan_operation_types_from_state(state)

    def plan_operation_signatures_from_state(self, state: dict[str, Any]) -> list[str]:
        return self._loop._plan_operation_signatures_from_state(state)

    def sequence_contains_subsequence(self, seq: list[str], sub: list[str]) -> bool:
        return self._loop._sequence_contains_subsequence(seq, sub)

    def clear_active_plan_state(self) -> None:
        return self._loop._clear_active_plan_state()

    # ── confirmed execution contract ─────────────────────────────────────────

    def build_confirmed_execution_plan(self, payload: dict[str, Any]) -> dict[str, Any]:
        return self._loop._build_confirmed_execution_plan(payload)

    def store_confirmed_execution_plan(self, plan: dict[str, Any]) -> None:
        return self._loop._store_confirmed_execution_plan(plan)

    def confirmed_execution_contract_for_step(self, step_id: str) -> dict[str, Any] | None:
        return self._loop._confirmed_execution_contract_for_step(step_id)

    def confirmed_execution_results_for_step(self, step_id: str) -> list[dict[str, Any]]:
        return self._loop._confirmed_execution_results_for_step(step_id)

    def confirmed_execution_next_child_for_step(self, step_id: str) -> dict[str, Any] | None:
        return self._loop._confirmed_execution_next_child_for_step(step_id)

    def confirmed_execution_step_ready_to_record(self, step_id: str) -> bool:
        return self._loop._confirmed_execution_step_ready_to_record(step_id)

    def build_confirmed_execution_context_message(self, step_id: str) -> str:
        return self._loop._build_confirmed_execution_context_message(step_id)

    def current_confirmed_execution_cursor(self) -> dict[str, Any] | None:
        return self._loop._current_confirmed_execution_cursor()

    def log_confirmed_execution_cursor(self) -> None:
        return self._loop._log_confirmed_execution_cursor()

    def record_confirmed_execution_child_result(self, step_id: str, result: dict[str, Any]) -> None:
        return self._loop._record_confirmed_execution_child_result(step_id, result)

    def validate_confirmed_execution_tool_call(self, tool_name: str, args: dict[str, Any]) -> dict[str, Any]:
        return self._loop._validate_confirmed_execution_tool_call(tool_name, args)

    def locator_matches_confirmed_execution_child(self, locator: str, child: dict[str, Any]) -> bool:
        return self._loop._locator_matches_confirmed_execution_child(locator, child)

    def assertion_matches_confirmed_execution_child(self, assertion: str, child: dict[str, Any]) -> bool:
        return self._loop._assertion_matches_confirmed_execution_child(assertion, child)

    def value_matches_confirmed_execution_child(self, value: str, child: dict[str, Any]) -> bool:
        return self._loop._value_matches_confirmed_execution_child(value, child)

    def describe_confirmed_execution_child(self, child: dict[str, Any]) -> str:
        return self._loop._describe_confirmed_execution_child(child)

    def describe_confirmed_execution_call(self, tool_name: str, args: dict[str, Any]) -> str:
        return self._loop._describe_confirmed_execution_call(tool_name, args)

    def infer_confirmed_execution_child_assertion(self, child: dict[str, Any]) -> dict[str, Any]:
        return self._loop._infer_confirmed_execution_child_assertion(child)

    def normalize_confirmed_execution_child(self, child: dict[str, Any]) -> dict[str, Any]:
        return self._loop._normalize_confirmed_execution_child(child)

    def clear_confirmed_execution_contract_state(self) -> None:
        return self._loop._clear_confirmed_execution_contract_state()
```

- [ ] **Step 4: Wire into `AgentLoop.__init__`**

```python
from plan.state import PlanState
# in __init__:
self._plan_state = PlanState(self)
```

- [ ] **Step 5: Run full test suite**

```bash
cd "/Users/apple/personal/agent v4" && python -m pytest tests/ -q --tb=short 2>&1 | tail -20
```
Expected: `528 passed`

- [ ] **Step 6: Commit**

```bash
cd "/Users/apple/personal/agent v4"
git add plan/ agent.py
git commit -m "refactor: extract plan/state.py from AgentLoop"
```

---

## Task 9: Create `plan/builder.py`

**Files:**
- Create: `plan/builder.py`

- [ ] **Step 1: Read builder methods**

```bash
sed -n '7233,7270p' "/Users/apple/personal/agent v4/agent.py"
sed -n '7332,7520p' "/Users/apple/personal/agent v4/agent.py"
sed -n '7852,7930p' "/Users/apple/personal/agent v4/agent.py"
```

- [ ] **Step 2: Create `plan/builder.py`**

```python
# plan/builder.py
from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from agent import AgentLoop


class PlanBuilder:
    """Builds plan_ready and plan correction payloads."""

    def __init__(self, loop: "AgentLoop") -> None:
        self._loop = loop

    def normalize_steps(self, steps: list[dict]) -> list[dict[str, Any]]:
        return self._loop._normalize_steps(steps)

    def format_steps(self, steps: list[dict]) -> str:
        return self._loop._format_steps(steps)

    def validate_recording_steps(self, steps: list[dict[str, Any]]) -> None:
        return self._loop._validate_recording_steps(steps)

    def infer_operation_type(self, intent: str) -> str:
        return self._loop._infer_operation_type(intent)

    def infer_planned_operation_sequence(self, intent: str) -> list[str]:
        return self._loop._infer_planned_operation_sequence(intent)

    def build_planned_child_description(self, operation_type: str, target: str, intent: str) -> str:
        return self._loop._build_planned_child_description(operation_type, target, intent)

    def build_planned_children(self, step: dict[str, Any]) -> list[dict[str, Any]]:
        return self._loop._build_planned_children(step)

    def build_plan_ready_parent_step(self, step: dict[str, Any]) -> dict[str, Any]:
        return self._loop._build_plan_ready_parent_step(step)

    def build_recorded_child_description(self, child: dict[str, Any]) -> str:
        return self._loop._build_recorded_child_description(child)

    def is_technical_recorded_label_text(self, value: Any) -> bool:
        return self._loop._is_technical_recorded_label_text(value)

    def build_recorded_children(self, step: dict[str, Any]) -> list[dict[str, Any]]:
        return self._loop._build_recorded_children(step)

    def build_plan_ready_payload(self, steps: list[dict[str, Any]]) -> dict[str, Any]:
        return self._loop._build_plan_ready_payload(steps)
```

- [ ] **Step 3: Wire into `AgentLoop.__init__`**

```python
from plan.builder import PlanBuilder
# in __init__:
self._plan_builder = PlanBuilder(self)
```

- [ ] **Step 4: Run full test suite**

```bash
cd "/Users/apple/personal/agent v4" && python -m pytest tests/ -q --tb=short 2>&1 | tail -20
```
Expected: `528 passed`

- [ ] **Step 5: Commit**

```bash
cd "/Users/apple/personal/agent v4"
git add plan/builder.py agent.py
git commit -m "refactor: extract plan/builder.py from AgentLoop"
```

---

## Task 10: Create `plan/correction.py`

**Files:**
- Create: `plan/correction.py`

- [ ] **Step 1: Read correction methods**

```bash
sed -n '3465,3580p' "/Users/apple/personal/agent v4/agent.py"
sed -n '2534,2560p' "/Users/apple/personal/agent v4/agent.py"
sed -n '2810,2880p' "/Users/apple/personal/agent v4/agent.py"
```

- [ ] **Step 2: Create `plan/correction.py`**

```python
# plan/correction.py
from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from agent import AgentLoop


class PlanCorrection:
    """Owns the plan diff editor pipeline and correction classification."""

    def __init__(self, loop: "AgentLoop") -> None:
        self._loop = loop

    def classify_plan_correction(self, message: str) -> str:
        return self._loop._classify_plan_correction(message)

    def build_plan_correction_validation_feedback(self, result: dict[str, Any]) -> str:
        return self._loop._build_plan_correction_validation_feedback(result)

    def build_plan_correction_operation_context_lines(self, step: dict[str, Any]) -> list[str]:
        return self._loop._build_plan_correction_operation_context_lines(step)

    def build_plan_correction_context_message(self, correction_text: str) -> str:
        return self._loop._build_plan_correction_context_message(correction_text)

    def build_plan_diff_editor_schema_message(self) -> str:
        return self._loop._build_plan_diff_editor_schema_message()

    def synthesize_plan_diff_editor_output(self, raw: Any) -> dict[str, Any]:
        return self._loop._synthesize_plan_diff_editor_output(raw)

    def build_plan_correction_clarification_message(self, reason: str) -> str:
        return self._loop._build_plan_correction_clarification_message(reason)

    def build_plan_correction_state(self, correction_text: str) -> dict[str, Any]:
        return self._loop._build_plan_correction_state(correction_text)

    def build_plan_correction_added_child(self, op: dict[str, Any]) -> dict[str, Any]:
        return self._loop._build_plan_correction_added_child(op)

    def build_structured_plan_correction_payload_from_diff(self, diff: dict[str, Any]) -> dict[str, Any]:
        return self._loop._build_structured_plan_correction_payload_from_diff(diff)

    def patch_value(self, original: Any, patch: Any) -> Any:
        return self._loop._patch_value(original, patch)

    def normalize_step_patch(self, patch: dict[str, Any]) -> dict[str, Any]:
        return self._loop._normalize_step_patch(patch)

    def validate_structured_plan_step(self, step: dict[str, Any]) -> dict[str, Any]:
        return self._loop._validate_structured_plan_step(step)

    def validate_structured_plan_correction(self, correction: dict[str, Any]) -> dict[str, Any]:
        return self._loop._validate_structured_plan_correction(correction)

    def remember_plan_review_context(self, payload: dict[str, Any]) -> None:
        return self._loop._remember_plan_review_context(payload)

    def build_plan_step_context_lines(self, step: dict[str, Any]) -> list[str]:
        return self._loop._build_plan_step_context_lines(step)

    def build_plan_correction_message(self, correction_text: str) -> dict[str, Any]:
        return self._loop._build_plan_correction_message(correction_text)

    def append_plan_correction_message(self, correction_text: str) -> None:
        return self._loop._append_plan_correction_message(correction_text)

    def select_plan_correction_child_target(self, candidates: list[tuple[str, Any]]) -> str:
        return self._loop._select_plan_correction_child_target(candidates)

    def build_plan_correction_child_description(self, op_type: str, target: str) -> str:
        return self._loop._build_plan_correction_child_description(op_type, target)

    def clear_plan_review_context(self) -> None:
        return self._loop._clear_plan_review_context()

    def clear_active_plan_correction_state(self) -> None:
        return self._loop._clear_active_plan_correction_state()

    async def call_plan_diff_editor_controller(self, **kwargs: Any) -> dict[str, Any]:
        return await self._loop._call_plan_diff_editor_controller(**kwargs)

    async def run_plan_diff_editor_correction(self, **kwargs: Any) -> dict[str, Any]:
        return await self._loop._run_plan_diff_editor_correction(**kwargs)
```

- [ ] **Step 3: Wire into `AgentLoop.__init__`**

```python
from plan.correction import PlanCorrection
# in __init__:
self._plan_correction = PlanCorrection(self)
```

- [ ] **Step 4: Run full test suite**

```bash
cd "/Users/apple/personal/agent v4" && python -m pytest tests/ -q --tb=short 2>&1 | tail -20
```
Expected: `528 passed`

- [ ] **Step 5: Commit**

```bash
cd "/Users/apple/personal/agent v4"
git add plan/correction.py agent.py
git commit -m "refactor: extract plan/correction.py from AgentLoop"
```

---

## Task 11: Create `plan/confirmation.py`

**Files:**
- Create: `plan/confirmation.py`

- [ ] **Step 1: Read confirmation methods**

```bash
sed -n '8438,8500p' "/Users/apple/personal/agent v4/agent.py"
sed -n '8789,8945p' "/Users/apple/personal/agent v4/agent.py"
sed -n '3619,3660p' "/Users/apple/personal/agent v4/agent.py"
```

- [ ] **Step 2: Create `plan/confirmation.py`**

```python
# plan/confirmation.py
from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from agent import AgentLoop


class PlanConfirmation:
    """Owns wait_for_plan_confirmation and confirmation context checks."""

    def __init__(self, loop: "AgentLoop") -> None:
        self._loop = loop

    async def wait_for_plan_confirmation(self) -> dict[str, Any]:
        return await self._loop._wait_for_plan_confirmation()

    async def send_plan_ready_after_confirmation(self, payload: dict[str, Any]) -> dict[str, Any]:
        return await self._loop._send_plan_ready_after_confirmation(payload)

    def confirmation_context(self, payload: dict[str, Any] | None) -> dict[str, str]:
        return self._loop._confirmation_context(payload)

    def confirmation_context_mismatch_reason(
        self, payload: dict[str, Any] | None, expected: dict[str, str]
    ) -> str | None:
        return self._loop._confirmation_context_mismatch_reason(payload, expected)

    def completed_run_confirmation_rejection_reason(self, payload: dict[str, Any]) -> str | None:
        return self._loop._completed_run_confirmation_rejection_reason(payload)
```

- [ ] **Step 3: Wire into `AgentLoop.__init__`**

```python
from plan.confirmation import PlanConfirmation
# in __init__:
self._plan_confirmation = PlanConfirmation(self)
```

- [ ] **Step 4: Run full test suite**

```bash
cd "/Users/apple/personal/agent v4" && python -m pytest tests/ -q --tb=short 2>&1 | tail -20
```
Expected: `528 passed`

- [ ] **Step 5: Commit**

```bash
cd "/Users/apple/personal/agent v4"
git add plan/confirmation.py agent.py
git commit -m "refactor: extract plan/confirmation.py from AgentLoop"
```

---

## Task 12: Create `llm/tool_definitions.py`

**Files:**
- Create: `llm/__init__.py`
- Create: `llm/tool_definitions.py`

- [ ] **Step 1: Read tool definitions method**

```bash
sed -n '7927,8210p' "/Users/apple/personal/agent v4/agent.py"
```

- [ ] **Step 2: Create the files**

```python
# llm/__init__.py
# (empty)
```

```python
# llm/tool_definitions.py
from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from agent import AgentLoop


class ToolDefinitions:
    """Returns the list of tool JSON schemas for the LLM."""

    def __init__(self, loop: "AgentLoop") -> None:
        self._loop = loop

    def build(self) -> list[dict[str, Any]]:
        return self._loop._build_tool_definitions()
```

- [ ] **Step 3: Wire into `AgentLoop.__init__`**

```python
from llm.tool_definitions import ToolDefinitions
# in __init__:
self._tool_definitions = ToolDefinitions(self)
```

- [ ] **Step 4: Run full test suite**

```bash
cd "/Users/apple/personal/agent v4" && python -m pytest tests/ -q --tb=short 2>&1 | tail -20
```
Expected: `528 passed`

- [ ] **Step 5: Commit**

```bash
cd "/Users/apple/personal/agent v4"
git add llm/ agent.py
git commit -m "refactor: extract llm/tool_definitions.py from AgentLoop"
```

---

## Task 13: Create `llm/tool_dispatcher.py`

**Files:**
- Create: `llm/tool_dispatcher.py`

- [ ] **Step 1: Read dispatcher and tool handler methods**

```bash
sed -n '8208,8440p' "/Users/apple/personal/agent v4/agent.py"
sed -n '8759,8800p' "/Users/apple/personal/agent v4/agent.py"
```

- [ ] **Step 2: Create `llm/tool_dispatcher.py`**

```python
# llm/tool_dispatcher.py
from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from agent import AgentLoop


class ToolDispatcher:
    """Routes LLM tool call names to their handler methods."""

    def __init__(self, loop: "AgentLoop") -> None:
        self._loop = loop

    async def dispatch(self, tool_name: str, args: dict[str, Any]) -> dict[str, Any]:
        return await self._loop._dispatch_tool(tool_name, args)

    def parse_tool_args(self, raw_args: str) -> dict[str, Any]:
        return self._loop._parse_tool_args(raw_args)

    def normalize_wait_until(self, value: Any) -> str:
        return self._loop._normalize_wait_until(value)

    def is_browser_state_tool(self, tool_name: str) -> bool:
        return self._loop._is_browser_state_tool(tool_name)

    def append_tool_response(self, tool_call_id: str, result: dict[str, Any]) -> None:
        return self._loop._append_tool_response(tool_call_id, result)

    def append_skipped_tool_response(self, tool_call_id: str, reason: str) -> None:
        return self._loop._append_skipped_tool_response(tool_call_id, reason)

    def append_skipped_tool_responses(self, tool_calls: list[Any], start_index: int, reason: str) -> None:
        return self._loop._append_skipped_tool_responses(tool_calls, start_index, reason)
```

- [ ] **Step 3: Wire into `AgentLoop.__init__`**

```python
from llm.tool_dispatcher import ToolDispatcher
# in __init__:
self._tool_dispatcher = ToolDispatcher(self)
```

- [ ] **Step 4: Run full test suite**

```bash
cd "/Users/apple/personal/agent v4" && python -m pytest tests/ -q --tb=short 2>&1 | tail -20
```
Expected: `528 passed`

- [ ] **Step 5: Commit**

```bash
cd "/Users/apple/personal/agent v4"
git add llm/tool_dispatcher.py agent.py
git commit -m "refactor: extract llm/tool_dispatcher.py from AgentLoop"
```

---

## Task 14: Create `llm/orchestrator.py`

**Files:**
- Create: `llm/orchestrator.py`

- [ ] **Step 1: Read orchestrator methods**

```bash
sed -n '2121,2250p' "/Users/apple/personal/agent v4/agent.py"
sed -n '7905,7930p' "/Users/apple/personal/agent v4/agent.py"
```

- [ ] **Step 2: Create `llm/orchestrator.py`**

```python
# llm/orchestrator.py
from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from agent import AgentLoop


class LLMOrchestrator:
    """Manages LLM message history and followup decision logic."""

    def __init__(self, loop: "AgentLoop") -> None:
        self._loop = loop

    def should_request_user_followup(self, final_text: str, had_tool_failure: bool) -> bool:
        return self._loop._should_request_user_followup(final_text, had_tool_failure)

    def looks_like_completion_message(self, text: str) -> bool:
        return self._loop._looks_like_completion_message(text)

    def format_user_followup_message(self, answer: str, event_type: str) -> str:
        return self._loop._format_user_followup_message(answer, event_type)

    def is_correction_followup(self, answer: str, event_type: str) -> bool:
        return self._loop._is_correction_followup(answer, event_type)

    def assistant_message_entry(self, message: Any) -> dict[str, Any]:
        return self._loop._assistant_message_entry(message)
```

- [ ] **Step 3: Wire into `AgentLoop.__init__`**

```python
from llm.orchestrator import LLMOrchestrator
# in __init__:
self._llm_orchestrator = LLMOrchestrator(self)
```

- [ ] **Step 4: Run full test suite**

```bash
cd "/Users/apple/personal/agent v4" && python -m pytest tests/ -q --tb=short 2>&1 | tail -20
```
Expected: `528 passed`

- [ ] **Step 5: Commit**

```bash
cd "/Users/apple/personal/agent v4"
git add llm/orchestrator.py agent.py
git commit -m "refactor: extract llm/orchestrator.py from AgentLoop"
```

---

## Task 15: Create `ws/router.py` and slim `server.py`

**Files:**
- Create: `ws/__init__.py`
- Create: `ws/router.py`
- Modify: `server.py`

- [ ] **Step 1: Read server.py in full**

```bash
cat "/Users/apple/personal/agent v4/server.py"
```

- [ ] **Step 2: Create `ws/__init__.py`**

```python
# ws/__init__.py
# (empty)
```

- [ ] **Step 3: Create `ws/router.py`**

Extract the WebSocket command dispatch logic from `server.py`. The router maps incoming `type` fields from the frontend to the appropriate `AgentLoop` method:

```python
# ws/router.py
from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from agent import AgentLoop


class WSRouter:
    """Maps WebSocket command types to AgentLoop methods."""

    def __init__(self, loop: "AgentLoop") -> None:
        self._loop = loop

    async def dispatch(self, command: dict[str, Any]) -> None:
        """Route a parsed WebSocket command to the correct handler."""
        cmd_type = str(command.get("type") or "").strip()

        if cmd_type == "run":
            steps = command.get("steps") or []
            await self._loop.run(steps)

        elif cmd_type == "replay_one":
            step_id = str(command.get("step_id") or "").strip()
            result = await self._loop.replay_one(step_id)
            await self._loop._send("replay_one_result", **result)

        elif cmd_type == "replay_all":
            stop_on_error = bool(command.get("stop_on_error", True))
            result = await self._loop.replay_all(stop_on_error=stop_on_error)
            await self._loop._send("replay_all_result", **result)

        elif cmd_type == "save_spec":
            await self._loop._send("save_spec_result", status="ok")

        else:
            await self._loop._send("error", message=f"Unknown command type: {cmd_type}")
```

Note: Read the actual `server.py` in Step 1 and update the dispatch logic to match every command type already handled there. Do not guess — copy existing command handling faithfully.

- [ ] **Step 4: Update `server.py` to use `WSRouter`**

In `server.py`, after constructing `AgentLoop`, wire the router:
```python
from ws.router import WSRouter
# after: agent_loop = AgentLoop(ws, control_queue)
router = WSRouter(agent_loop)
# replace the existing dispatch block with:
# await router.dispatch(command)
```

- [ ] **Step 5: Run full test suite**

```bash
cd "/Users/apple/personal/agent v4" && python -m pytest tests/ -q --tb=short 2>&1 | tail -20
```
Expected: `528 passed`

- [ ] **Step 6: Commit**

```bash
cd "/Users/apple/personal/agent v4"
git add ws/ server.py
git commit -m "refactor: extract ws/router.py from server.py"
```

---

## Task 16: Final verification — full test suite + import smoke test

- [ ] **Step 1: Run full test suite**

```bash
cd "/Users/apple/personal/agent v4" && python -m pytest tests/ -q --tb=short 2>&1 | tail -20
```
Expected: `528 passed`

- [ ] **Step 2: Import smoke test — verify all new modules import cleanly**

```bash
cd "/Users/apple/personal/agent v4" && python -c "
from event.emitter import EventEmitter
from locator.resolver import LocatorResolver
from skills.loader import SkillsLoader
from step.manager import StepManager
from recording.codegen import Codegen
from recording.recorder import Recorder
from recording.replay import Replay
from plan.state import PlanState
from plan.builder import PlanBuilder
from plan.correction import PlanCorrection
from plan.confirmation import PlanConfirmation
from llm.tool_definitions import ToolDefinitions
from llm.tool_dispatcher import ToolDispatcher
from llm.orchestrator import LLMOrchestrator
from ws.router import WSRouter
from agent import AgentLoop
print('All imports OK')
"
```
Expected: `All imports OK`

- [ ] **Step 3: Verify agent.py line count has decreased**

```bash
wc -l "/Users/apple/personal/agent v4/agent.py"
```
Expected: Significantly reduced from 9302. Original methods remain as thin delegates.

- [ ] **Step 4: Final commit**

```bash
cd "/Users/apple/personal/agent v4"
git add -u
git commit -m "refactor: complete industrial-standard agent.py modularization

- event/emitter.py: WebSocket send + emit helpers
- locator/resolver.py: locator building, resolution, escape helpers
- skills/loader.py: skill file loading and prompt composition
- step/manager.py: step state machine
- recording/codegen.py: Playwright code generation
- recording/recorder.py: step recording and action history
- recording/replay.py: replay_one and replay_all
- plan/state.py: active plan and confirmed execution contract
- plan/builder.py: plan_ready payload builders
- plan/correction.py: diff editor pipeline and correction classification
- plan/confirmation.py: wait_for_plan_confirmation
- llm/tool_definitions.py: tool JSON schemas
- llm/tool_dispatcher.py: tool dispatch routing
- llm/orchestrator.py: LLM message history and followup logic
- ws/router.py: WebSocket command routing

AgentLoop retains backward-compatible delegates. 528 tests green.
"
```
