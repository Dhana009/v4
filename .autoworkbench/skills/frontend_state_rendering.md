# Skill: Frontend State Rendering

## Purpose
Ensure frontend renders backend truth correctly across LLM, Steps, Recorded, Code, and Trace tabs.

## When to use
Use when touching frontend state model, event handlers, UI cards, plan UI, step UI, recorded UI, code UI, trace UI, blocking/error states.

## Source of truth
- Frontend/UI Spec
- Backend/UI state contract
- Typed Event Contract Skill

## Non-negotiable rules
1. UI renders typed backend state.
2. UI does not infer completion, plan status, recording, or replay status.
3. Draft steps, confirmed plan, and recorded evidence are separate.
4. Blocking states must show clear next actions.
5. LLM tab owns chat/plan/clarification/permission/recovery.
6. Steps tab owns pending scoped steps and locator state.
7. Recorded tab owns execution evidence/history.
8. Code tab owns generated code and warnings.
9. Trace tab owns observability.
10. Global header shows current phase/status.
11. Do not let the UI infer runtime truth from prose or local heuristics.

## Required implementation behavior
Render these state objects:
```text
conversation_state
plan_state
plan_versions
plan_diff_state
step_state
locator_state
recorded_step_detail
code_state
trace_summary
permission_state
test_data_requirements
page_state
replay_state
```

Important UI states:
- clarification needed
- permission required
- locator ambiguous
- precondition failed
- dependency warning
- plan stale
- execution running
- recovery needed
- code generation failed
- API/backend/LLM config error

## Required tests
- State-to-tab rendering tests where possible
- E2E checks for key UI states
- Build check
- Event handler contract tests if available

## Verification commands
```bash
npm run build
python -m pytest tests/e2e/<focused_flow>.py -q -s
```

## Stop conditions
Stop if:
- required evidence is missing, unclear, or contradictory
- backend state object is missing
- UI would need to parse prose
- blocking state lacks action
- rendered state can contradict backend
- pending/confirmed/recorded concepts are mixed

## Reporting format
Report:
1. State rendered
2. UI destination
3. Commands emitted
4. Tests/results
5. Unclear/missing backend fields
