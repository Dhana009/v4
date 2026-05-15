# Skill: Backend Runtime / Step Runner

## Purpose
Guide backend lifecycle, execution, recording, recovery, and replay behavior.

## When to use
Use when touching Step Runner, agent loop, phases, pending steps, plan confirmation, execution, recording, recovery, replay, save/load, or code_update.

## Source of truth
- PRD backend event contract
- Complete LLM Mode architecture spec
- Handoff notes on backend-owned recording and strict cursor

## Non-negotiable rules
1. Backend owns lifecycle truth.
2. Confirmed plan children are the execution contract.
3. LLM tool calls must be validated against the next expected child.
4. Strict cursor must be used in confirmed mode.
5. Do not resolve confirmed steps by last_successful_action, current_step_index, first unresolved step, or step_number alone.
6. Backend owns recording from execution evidence.
7. Do not depend on LLM-emitted step_recorded in normal path.
8. Recording must preserve parent step and child operation order.
9. expected_outcome remains parent metadata.
10. Replay is backend-owned and precondition-aware.

## Required implementation behavior
- Maintain stable step_id across pending → plan → confirmation → execution → recording.
- Validate phase before allowing tools.
- Validate operation type, locator/action/assertion compatibility, and step identity.
- Record only after validated success.
- Emit typed events for phase, plan, execution, recording, failure, replay, code_update.
- Keep recovery bounded.
- Store enough evidence for recorded_step_detail and replay.

## Required tests
Add/update:
- phase transition tests
- confirmed execution contract tests
- strict cursor tests
- recording payload tests
- code_update order tests
- expected_outcome separation tests
- recovery fail-safe tests
- replay precondition tests where relevant

## Verification commands
```bash
python -m pytest tests/test_*step* tests/test_*record* tests/test_*execution* -q
```
Adjust to exact focused tests.

## Stop conditions
Stop if:
- execution path can mutate plan silently
- LLM can bypass confirmed contract
- recording source is ambiguous
- multi-step identity resolution is heuristic in confirmed mode
- unsupported behavior would be recorded as success

## Reporting format
Report:
1. Lifecycle behavior changed
2. Event/command contract affected
3. Tests added
4. Commands/results
5. Remaining lifecycle risks
