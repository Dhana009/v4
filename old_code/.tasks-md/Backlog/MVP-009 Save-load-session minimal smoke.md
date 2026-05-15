# MVP-009 Save-load-session minimal smoke

**Type:** Story  
**Status:** Backlog  
**Priority:** P0  
**Epic:** EPIC-007 Complete LLM Mode MVP Flows  
**Owner:** Planning Brain / Cross-workstream  
**Assignee:** Unassigned  
**Story Points:** TBD  
**Readiness:** Ready for repo inspection; not ready for implementation  
**Dependencies:** EPIC-007, BE-001, EVENT-002, FE-002, E2E-001, E2E-002  
**Blocks:** session baseline and future persistence  
**Version:** Batch 08 v1  

---

## Product contribution

This story validates minimal save/load session behavior if the repo already supports it, or documents it as non-blocking P0 gap if not.

## Source evidence table

| Source | Extracted rule | Planning interpretation | Story impact |
|---|---|---|---|
| BE-001 | P0 runtime state may be in-memory unless accepted persistence exists | do not block MVP on full persistence | smoke only |
| EVENT-002 | save_session/load_session commands exist or placeholder | command validation needed | assert typed behavior |
| EPIC-006 | artifacts/session state must be testable | smoke should produce evidence | capture session_state |
| Handoff | save/load not production-ready | avoid over-scoping | gap if unsupported |

## Required behavior

If supported:

```text
save_session command
→ session_state/event/artifact
→ load_session
→ restored visible read-model/recorded data
```

If not supported:

```text
typed rejection or capability gap
→ documented as P1/P2
→ MVP not blocked unless source requires it
```

## Four-developer coordination

| Developer | Relationship |
|---|---|
| DEV-1 Backend | validates save/load support or rejection |
| DEV-2 LLM | no role except explanation if needed |
| DEV-3 Frontend | sends commands/renders session state |
| DEV-4 E2E | asserts support or typed gap |

## Test matrix

| Test ID | Layer | Scenario | Expected |
|---|---|---|---|
| MVP009-E-001 | E2E | save supported | session artifact/event |
| MVP009-E-002 | E2E | load supported | UI/store restored |
| MVP009-E-003 | E2E | unsupported | typed rejection/gap |
| MVP009-E-004 | E2E | no hardcoded hidden path | source-aligned storage |

## Edge cases

- reload loses in-memory state
- saved stale plan
- partial recorded steps
- unsupported persistence

---

## Required skills

Codex must load the smallest required skill pack only:

```text
.autoworkbench/skills/00_skill_usage_policy.md
.autoworkbench/skills/00_architecture_contract.md
.autoworkbench/skills/01_prd_scope_validation.md
.autoworkbench/skills/backend_step_runner.md
.autoworkbench/skills/typed_event_contract.md
.autoworkbench/skills/02_tdd_regression_harness.md
.autoworkbench/skills/03_refactor_safety.md
```

Add frontend, LLM, DOM/locator, or E2E-specific skills only when this story touches those areas.

---

## Repo-inspection requirement

Before implementation, Codex must inspect and report:

- current product flow for this scenario
- current backend lifecycle/event/command support
- current LLM runtime/schema support
- current DOM/locator support
- current Shadow DOM/frontend support
- current E2E/harness/fixture support
- existing tests covering this scenario
- source alignment gaps
- proposed narrow implementation path

Use the repo-inspection template from `PLAN-002`.

No implementation until the repo-inspection report is reviewed.

---

## Stop conditions

Stop if:

- scenario cannot be mapped to backend-owned truth
- frontend would need to infer lifecycle state
- LLM would own plan/execution/recording/completion truth
- event/command payloads are missing required IDs
- locator validation boundary is unclear
- E2E evidence cannot prove backend event + UI state
- implementation requires broad rewrite before tests
- scenario depends on live external site or nondeterministic LLM output as hard requirement

---

## Codex execution summary

First Codex task for MVP-009 should be read-only:

```text
Read MVP-009, SOURCE-001, PLAN-002, PLAN-005, EPIC-007, EPIC-001 through EPIC-006, and required skills.
Do not edit code.
Inspect current product support for Save-load-session minimal smoke.
Report gaps, current files, tests, risks, and a narrow implementation plan.
Do not implement until repo-inspection report is reviewed.
```
