from __future__ import annotations

import asyncio
from types import SimpleNamespace

import agent as agent_module
from agent import AgentLoop
from runtime.deterministic_fast_path import (
    classify_fast_path,
    build_deterministic_plan,
    _is_compound_intent,
    _extract_action_verb,
)
from runtime.phase_tracker import PhaseTracker


# --- classify_fast_path ---

def test_simple_click_unique_locator_qualifies():
    qualifies, reason = classify_fast_path(
        user_message="click the submit button",
        locator_validated=True,
        locator_count=1,
    )
    assert qualifies is True
    assert "fast_path" in reason


def test_simple_assert_visible_qualifies():
    qualifies, reason = classify_fast_path(
        user_message="assert visible the heading",
        locator_validated=True,
        locator_count=1,
    )
    assert qualifies is True


def test_simple_fill_qualifies():
    qualifies, reason = classify_fast_path(
        user_message="fill the email input",
        locator_validated=True,
        locator_count=1,
    )
    assert qualifies is True


def test_compound_intent_does_not_qualify():
    qualifies, reason = classify_fast_path(
        user_message="click this and then verify the next page",
        locator_validated=True,
        locator_count=1,
    )
    assert qualifies is False
    assert reason == "compound_intent"


def test_fill_and_submit_does_not_qualify():
    qualifies, reason = classify_fast_path(
        user_message="fill this form and submit",
        locator_validated=True,
        locator_count=1,
    )
    assert qualifies is False
    assert reason == "compound_intent"


def test_check_everything_does_not_qualify():
    qualifies, reason = classify_fast_path(
        user_message="check everything on this page",
        locator_validated=True,
        locator_count=1,
    )
    assert qualifies is False
    assert reason == "compound_intent"


def test_multi_match_locator_does_not_qualify():
    qualifies, reason = classify_fast_path(
        user_message="click the button",
        locator_validated=True,
        locator_count=3,
    )
    assert qualifies is False
    assert "locator_not_unique" in reason


def test_zero_match_locator_does_not_qualify():
    qualifies, reason = classify_fast_path(
        user_message="click the button",
        locator_validated=False,
        locator_count=0,
    )
    assert qualifies is False
    assert "locator_not_unique" in reason


def test_unknown_action_verb_does_not_qualify():
    qualifies, reason = classify_fast_path(
        user_message="hover over the menu",
        locator_validated=True,
        locator_count=1,
    )
    assert qualifies is False
    assert reason == "no_deterministic_action_verb"


def test_whole_section_does_not_qualify():
    qualifies, reason = classify_fast_path(
        user_message="test this whole section",
        locator_validated=True,
        locator_count=1,
    )
    assert qualifies is False


def test_multi_step_with_semicolon_does_not_qualify():
    qualifies, reason = classify_fast_path(
        user_message="click this; verify the result",
        locator_validated=True,
        locator_count=1,
    )
    assert qualifies is False
    assert reason == "compound_intent"


# --- build_deterministic_plan ---

def test_plan_has_zero_llm_calls():
    plan = build_deterministic_plan(
        user_message="click the button",
        locator="button[data-testid='submit']",
        action_verb="click",
    )
    assert plan["llm_calls"] == 0
    assert plan["model_called"] is False


def test_plan_includes_locator_and_action():
    plan = build_deterministic_plan(
        user_message="click the submit button",
        locator="button[data-testid='submit']",
        action_verb="click",
    )
    assert len(plan["steps"]) == 1
    step = plan["steps"][0]
    child = step["children"][0]
    assert step["step_id"] == "1"
    assert step["kind"] == "step"
    assert step["type"] == "step"
    assert child["locator"] == "button[data-testid='submit']"
    assert child["type"] == "click"
    assert child["operation_id"] == "op_1"
    assert child["status"] == "planned"


def test_plan_prefers_human_target_label_over_locator():
    plan = build_deterministic_plan(
        user_message="assert this is visible",
        locator='page.locator("main")',
        action_verb="assert_visible",
        target_label="Playwright Test Agents",
    )
    child = plan["steps"][0]["children"][0]
    assert child["locator"] == 'page.locator("main")'
    assert child["target"] == "Playwright Test Agents"
    assert child["description"] == "Playwright Test Agents is visible"


def test_plan_source_is_deterministic():
    plan = build_deterministic_plan(
        user_message="assert visible heading",
        locator="h1",
        action_verb="assert_visible",
    )
    assert plan["source"] == "deterministic_fast_path"


def test_plan_fill_includes_value():
    plan = build_deterministic_plan(
        user_message="fill the email input",
        locator="input[name='email']",
        action_verb="fill",
        fill_value="test@example.com",
    )
    child = plan["steps"][0]["children"][0]
    assert child["type"] == "fill"
    assert child["value"] == "test@example.com"
    assert plan["steps"][0]["expected_outcome"]["type"] == "content_change"


def test_plan_assert_text_includes_expected():
    plan = build_deterministic_plan(
        user_message="assert text of heading",
        locator="h1",
        action_verb="assert_text",
        expected_text="Welcome",
    )
    child = plan["steps"][0]["children"][0]
    assert child["type"] == "assert"
    assert child["assertion"] == "has_text"
    assert child["expected_value"] == "Welcome"
    assert child["value"] == "Welcome"


def test_plan_assert_visible_has_assertion_child():
    plan = build_deterministic_plan(
        user_message="assert visible heading",
        locator="h1",
        action_verb="assert_visible",
    )
    child = plan["steps"][0]["children"][0]
    assert child["type"] == "assert"
    assert child["assertion"] == "visible"


def test_plan_is_compatible_with_confirmed_execution_contract():
    payload = build_deterministic_plan(
        user_message="assert text of heading",
        locator="h1",
        action_verb="assert_text",
        step_id="step-1",
        expected_text="Welcome",
    )
    loop = AgentLoop.__new__(AgentLoop)
    loop.confirmed_plan_by_step_id = {}
    loop.confirmed_plan_step_ids = []
    loop.confirmed_child_results_by_step_id = {}
    loop.confirmed_execution_mismatch_count_by_step_id = {}

    confirmed_plan = loop._build_confirmed_execution_plan(payload, source_plan_state=payload)

    assert confirmed_plan["target_step_id"] == "step-1"
    assert confirmed_plan["steps"][0]["step_id"] == "step-1"
    assert confirmed_plan["steps"][0]["children"][0]["operation_id"] == "op_1"
    assert confirmed_plan["steps"][0]["children"][0]["type"] == "assert"
    assert confirmed_plan["steps"][0]["children"][0]["assertion"] == "has_text"
    assert confirmed_plan["steps"][0]["children"][0]["expected_value"] == "Welcome"


def test_confirmation_gate_not_bypassed():
    """The plan payload has model_called=False, but plan_ready still goes through
    _send_plan_ready_after_confirmation which requires user confirmation. This test
    verifies the payload does NOT auto-execute (no 'confirmed' key set)."""
    plan = build_deterministic_plan(
        user_message="click button",
        locator="button",
        action_verb="click",
    )
    assert "confirmed" not in plan
    assert plan.get("model_called") is False


def test_try_deterministic_fast_path_executes_confirmed_plan_without_llm_instruction(monkeypatch):
    class _FakeResolvedLocator:
        async def count(self) -> int:
            return 1

    loop = AgentLoop.__new__(AgentLoop)
    loop.llm = SimpleNamespace(messages=[])
    loop._resolve_locator = lambda page, locator: _FakeResolvedLocator()
    loop._normalize_space = AgentLoop._normalize_space.__get__(loop, AgentLoop)
    loop._derive_locator_from_step_context = lambda step: ""
    executed: list[bool] = []

    async def fake_send_plan_ready_after_confirmation(payload):
        return {"confirmed": True}

    async def fake_execute():
        executed.append(True)

    monkeypatch.setattr(agent_module, "get_page", lambda: object())
    loop._send_plan_ready_after_confirmation = fake_send_plan_ready_after_confirmation
    loop._execute_deterministic_fast_path_confirmed_plan = fake_execute

    handled = asyncio.run(
        loop._try_deterministic_fast_path(
            [
                {
                    "id": "step-1",
                    "intent": "Click the submit button",
                    "locator": 'get_by_role("button", name="Submit")',
                }
            ]
        )
    )

    assert handled is True
    assert executed == [True]
    assert loop.llm.messages == []


def test_try_deterministic_fast_path_correction_falls_back_with_message(monkeypatch):
    class _FakeResolvedLocator:
        async def count(self) -> int:
            return 1

    loop = AgentLoop.__new__(AgentLoop)
    loop.llm = SimpleNamespace(messages=[])
    loop._resolve_locator = lambda page, locator: _FakeResolvedLocator()
    loop._normalize_space = AgentLoop._normalize_space.__get__(loop, AgentLoop)
    loop._derive_locator_from_step_context = lambda step: ""
    appended_corrections: list[tuple[str, str | None, str | None]] = []

    def fake_append_plan_correction_message(correction, plan_id=None, target_step_id=None):
        appended_corrections.append((correction, plan_id, target_step_id))
        loop.llm.messages.append({"role": "user", "content": f'Correction: "{correction}"'})
        return correction

    loop._append_plan_correction_message = fake_append_plan_correction_message

    async def fake_send_plan_ready_after_confirmation(payload):
        return {
            "confirmed": False,
            "correction": "Use the primary CTA instead",
            "plan_id": "deterministic-step-1",
            "target_step_id": "step-1",
        }

    monkeypatch.setattr(agent_module, "get_page", lambda: object())
    loop._send_plan_ready_after_confirmation = fake_send_plan_ready_after_confirmation

    handled = asyncio.run(
        loop._try_deterministic_fast_path(
            [
                {
                    "id": "step-1",
                    "intent": "Click the submit button",
                    "locator": 'get_by_role("button", name="Submit")',
                }
            ]
        )
    )

    assert handled is False
    assert appended_corrections == [("Use the primary CTA instead", "deterministic-step-1", "step-1")]
    assert loop.llm.messages == [
        {"role": "user", "content": 'Correction: "Use the primary CTA instead"'}
    ]


def test_try_deterministic_fast_path_derives_expected_text_from_selected_element(monkeypatch):
    class _FakeResolvedLocator:
        async def count(self) -> int:
            return 1

    captured_plan_payloads: list[dict[str, object]] = []
    loop = AgentLoop.__new__(AgentLoop)
    loop.llm = SimpleNamespace(messages=[])
    loop._resolve_locator = lambda page, locator: _FakeResolvedLocator()
    loop._normalize_space = AgentLoop._normalize_space.__get__(loop, AgentLoop)
    loop._derive_locator_from_step_context = lambda step: ""
    loop._resolve_selected_element_info = AgentLoop._resolve_selected_element_info.__get__(loop, AgentLoop)
    loop._selected_element_text = AgentLoop._selected_element_text.__get__(loop, AgentLoop)
    loop._append_plan_correction_message = lambda correction, plan_id=None, target_step_id=None: loop.llm.messages.append(
        {"role": "user", "content": f'Correction: "{correction}"'}
    )

    async def fake_send_plan_ready_after_confirmation(payload):
        captured_plan_payloads.append(payload)
        return {"confirmed": False, "correction": "adjust later"}

    monkeypatch.setattr(agent_module, "get_page", lambda: object())
    loop._send_plan_ready_after_confirmation = fake_send_plan_ready_after_confirmation

    asyncio.run(
        loop._try_deterministic_fast_path(
            [
                {
                    "id": "step-1",
                    "intent": "assert exact text equal to npx playwright init-agents --loop=opencode",
                    "locator": 'get_by_text("npx playwright init-agents --loop=opencode", exact=True)',
                    "element_info": {
                        "text": "npx playwright init-agents --loop=opencode",
                    },
                }
            ]
        )
    )

    assert captured_plan_payloads
    child = captured_plan_payloads[0]["steps"][0]["children"][0]
    assert child["assertion"] == "has_text"
    assert child["target"] == "npx playwright init-agents --loop=opencode"
    assert child["expected_value"] == "npx playwright init-agents --loop=opencode"


def test_try_deterministic_fast_path_prefers_short_candidate_for_visible_assertion(monkeypatch):
    class _FakeResolvedLocator:
        async def count(self) -> int:
            return 1

    captured_plan_payloads: list[dict[str, object]] = []
    loop = AgentLoop.__new__(AgentLoop)
    loop.llm = SimpleNamespace(messages=[])
    loop._resolve_locator = lambda page, locator: _FakeResolvedLocator()
    loop._normalize_space = AgentLoop._normalize_space.__get__(loop, AgentLoop)
    loop._derive_locator_from_step_context = lambda step: "main"
    loop._resolve_selected_element_info = AgentLoop._resolve_selected_element_info.__get__(loop, AgentLoop)
    loop._selected_element_text = AgentLoop._selected_element_text.__get__(loop, AgentLoop)
    loop._element_candidate_display_text = AgentLoop._element_candidate_display_text.__get__(loop, AgentLoop)
    loop._best_fast_path_target_label = AgentLoop._best_fast_path_target_label.__get__(loop, AgentLoop)
    loop._should_replace_fast_path_locator_with_text = AgentLoop._should_replace_fast_path_locator_with_text.__get__(
        loop, AgentLoop
    )
    loop._tool_string_escape = AgentLoop._tool_string_escape.__get__(loop, AgentLoop)
    loop._append_plan_correction_message = lambda correction, plan_id=None, target_step_id=None: loop.llm.messages.append(
        {"role": "user", "content": f'Correction: "{correction}"'}
    )

    async def fake_send_plan_ready_after_confirmation(payload):
        captured_plan_payloads.append(payload)
        return {"confirmed": False, "correction": "adjust later"}

    monkeypatch.setattr(agent_module, "get_page", lambda: object())
    loop._send_plan_ready_after_confirmation = fake_send_plan_ready_after_confirmation

    asyncio.run(
        loop._try_deterministic_fast_path(
            [
                {
                    "id": "step-1",
                    "intent": "assert this is visible",
                    "locator": "main",
                    "element_info": {
                        "text": "Very long page copy that should not be used as the visible assertion target",
                        "selected_candidate_index": 0,
                        "candidates": [
                            {"tag": "main", "text": "Very long page copy that should not be used as the visible assertion target"},
                            {"tag": "h1", "role": "heading", "text": "Playwright Test Agents"},
                        ],
                    },
                }
            ]
        )
    )

    assert captured_plan_payloads
    child = captured_plan_payloads[0]["steps"][0]["children"][0]
    assert child["target"] == "Playwright Test Agents"
    assert child["locator"] == 'get_by_text("Playwright Test Agents", exact=True)'


def test_run_uses_fast_path_before_model_loop(monkeypatch):
    loop = AgentLoop.__new__(AgentLoop)
    loop.phase_tracker = PhaseTracker()
    loop.llm = SimpleNamespace(messages=[], reset=lambda: None)
    loop._reset_lifecycle_state = lambda steps=None: None
    loop._prepare_recording_steps = lambda steps: setattr(loop, "current_steps", list(steps))
    loop._validate_recording_steps = lambda steps: None
    loop._load_skills_for_steps = lambda steps: (["core"], "", [{"name": "core"}])
    loop._skill_entries_from_loaded_skills = lambda loaded_skill_names, loaded_skills: [{"name": "core"}]
    loop._sync_skill_prompt_from_entries = lambda: None
    loop._log_skill_load = lambda names, phase: None
    loop._log_skill_diagnostics = lambda: None
    loop._format_steps = lambda steps: "steps"
    loop._pending_failure_followup = False
    loop.current_steps = []
    loop.model_router = SimpleNamespace(
        call=lambda **kwargs: (_ for _ in ()).throw(AssertionError("model loop should not run"))
    )
    fast_path_calls: list[list[dict]] = []

    async def fake_fast_path(steps):
        fast_path_calls.append(list(steps))
        return True

    loop._try_deterministic_fast_path = fake_fast_path

    asyncio.run(loop.run([{"id": "step-1", "intent": "Click the submit button"}]))

    assert fast_path_calls == [[{"id": "step-1", "intent": "Click the submit button"}]]


def test_execute_deterministic_fast_path_confirmed_plan_emits_recording_and_code_update():
    loop = AgentLoop.__new__(AgentLoop)
    loop.phase_tracker = PhaseTracker()
    loop.phase = "executing"
    loop.plan_confirmed = True
    loop.pending_recovery = False
    loop._pending_failure_followup = False
    loop._awaiting_step_record = False
    loop._recording_wait_guard_armed = False
    loop._run_completion_requested = False
    loop._run_completed_emitted = False
    loop._run_session_id = "run-fast-path"
    loop.completed_step_ids = set()
    loop.skipped_step_ids = set()
    loop._recorded_step_ids = set()
    loop.current_step_index = 0
    loop.active_step_id = None
    loop.active_failed_step_id = None
    loop.last_successful_action = None
    loop._last_action_context = None
    loop.successful_action_by_step_id = {}
    loop.successful_actions_by_step_id = {}
    loop.replay_action_history_by_step_id = {}
    loop.replay_recorded_step_payloads_by_step_id = {}
    loop.recorded_step_payloads = []
    loop.code_update_payloads = []
    loop._emit_run_completed_event = lambda payload, recorded_payload: asyncio.sleep(0)
    sent_messages: list[tuple[str, dict[str, object]]] = []

    step_context = {
        "step_id": "step-1",
        "step_number": 1,
        "intent": "Click the submit button",
        "element_info": {
            "text": "Submit",
            "attributes": {"aria-label": "Submit"},
        },
        "element_name": "Submit",
        "locator": 'get_by_role("button", name="Submit")',
        "status": "pending",
        "recorded": False,
        "last_error": None,
        "expected_outcome": {"type": "navigation"},
    }
    loop.current_steps = [dict(step_context)]
    loop._recording_steps = [step_context]
    loop._recording_step_index = 0
    loop.step_state_by_id = {"step-1": step_context}
    loop.step_context_by_id = loop.step_state_by_id

    payload = build_deterministic_plan(
        user_message="Click the submit button",
        locator='get_by_role("button", name="Submit")',
        action_verb="click",
        step_id="step-1",
    )
    loop._build_confirmed_execution_plan(payload, source_plan_state=payload)

    async def fake_send(message_type: str, **kwargs):
        sent_messages.append((message_type, kwargs))

    async def fake_dispatch(tool_name: str, args: dict[str, object]):
        assert tool_name == "action_click"
        assert args["locator"] == 'get_by_role("button", name="Submit")'
        return {
            "success": True,
            "error": None,
            "locator": 'get_by_role("button", name="Submit")',
        }

    browser_states = iter(
        [
            {"url": "http://fixture/start", "title": "Start"},
            {"url": "http://fixture/next", "title": "Next"},
        ]
    )

    async def fake_capture_browser_state():
        return next(browser_states)

    loop._send = fake_send
    loop._dispatch_tool = fake_dispatch
    loop._capture_browser_state = fake_capture_browser_state

    asyncio.run(loop._execute_deterministic_fast_path_confirmed_plan())

    message_types = [message_type for message_type, _ in sent_messages]
    assert "llm_result" not in message_types
    assert message_types[:2] == ["step_recorded", "code_update"]

    recorded_payload = sent_messages[0][1]
    code_update_payload = sent_messages[1][1]
    assert recorded_payload["step_id"] == "step-1"
    assert recorded_payload["children"][0]["status"] == "success"
    assert recorded_payload["children"][0]["description"] == "Submit"
    assert recorded_payload["children"][0]["target"] == "Submit"
    assert recorded_payload["children"][0]["locator"] == 'get_by_role("button", name="Submit")'
    assert code_update_payload["lines"] == ['await page.getByRole("button", { name: "Submit" }).click();']


# --- helpers ---

def test_is_compound_intent_detects_and_then():
    assert _is_compound_intent("click this and then verify") is True


def test_is_compound_intent_clean_message():
    assert _is_compound_intent("click the submit button") is False


def test_extract_action_verb_click():
    assert _extract_action_verb("click the button") == "click"


def test_extract_action_verb_fill():
    assert _extract_action_verb("fill the input with test") == "fill"


def test_extract_action_verb_unknown():
    assert _extract_action_verb("hover over element") is None
