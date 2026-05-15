# BUG-S5-013-012 step_plan_normalizer repeats llm_thinking instead of terminal planning output

**Status:** Done
**Sprint:** Sprint 5
**Owner:** Dhanunjaya
**Closed:** 2026-05-12

---

## Problem

Live `gpt-4o-mini` planner on ambiguous task ("Click Save", 3 Save buttons) emitted `send_to_overlay(message_type="llm_thinking")` twice. Backend guard fired `THINKING_NOT_ALLOWED_AFTER_CONVERGENCE_NARROWING`. Planner never produced terminal output (`plan_ready` | `ask_user`). Violates PRD §4 (one terminal planning outcome) and §5 (ambiguity → ask_user).

## Root cause

1. Natural-language instructions in prompt pack ignored by model.
2. JSON-schema `enum` not enforced at generation time by OpenAI — model emits values not in enum.
3. `tool_choice="auto"` left model free to repeat `llm_thinking` despite tool-surface narrowing.

## Fix

Three layers (defense-in-depth):

1. **Schema stripping** (`runtime/tool_registry.py::strip_llm_thinking_from_send_to_overlay`): deep-copy `send_to_overlay` tool def, remove `"llm_thinking"` from `message_type.enum`, rewrite description to forbid it.
2. **Forced tool_choice** (`agent.py` line ~1723): after `_step_plan_convergence_narrowing` flag set, force `tool_choice={"type":"function","function":{"name":"ask_user"}}` at API level. Conservative — if model emitted thinking first, it failed to draft plan in one shot → treat as ambiguity → ask user (PRD §5).
3. **Router observability** (`runtime/llm_runtime_controller.py::_call_model`): emit `[MODEL_ROUTER]` log for all purposes (not just `main_orchestrator`), so E2E observability covers all controller calls.

## Tests

- `tests/test_planning_convergence_contract.py::test_forced_ask_user_tool_choice_after_convergence_narrowing` — verifies tool_choice forcing.
- `tests/test_planning_convergence_contract.py::test_strip_llm_thinking_*` (4 tests) — verifies schema stripping.
- Paid E2E: `tests/e2e/test_llm_required_ambiguous_action_flow.py` — passes 9s, terminal output is `ask_user`.

## Evidence

Artifact: `test-results/autoworkbench-e2e/llm_required_ambiguous_action_flow-20260512-184303-75719/`

Trace:
```
llm_001 → send_to_overlay(message_type="llm_thinking")
→ [AGENT] planning convergence pressure injected
→ [AGENT] tool surface narrowed to ask_user+send_to_overlay
→ [AGENT] forcing tool_choice=ask_user
llm_002 → ask_user(question="Could you specify the context...?")
→ planning loop exits
```

Tokens: 2 calls, 5026 input, 45 output.

PRD compliance:
- §3 controller-routed: `[MODEL_ROUTER] purpose=step_plan_normalizer` ✓
- §4 terminal output: `ask_user` ✓
- §5 ambiguity → ask_user ✓
- §6 backend owns truth: narrowing + tool_choice forcing applied by backend ✓
