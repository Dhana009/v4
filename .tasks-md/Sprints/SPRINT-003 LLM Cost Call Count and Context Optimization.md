# SPRINT-003 LLM Cost, Call Count, and Context Optimization

Status: Planning
Sprint: Sprint 3
Duration: Bi-weekly
Primary focus: Complete LLM Mode cost reduction and context control
Priority: P0

## Sprint goal

Reduce LLM cost and make LLM Mode scalable before adding more broad product features.

Sprint 3 focuses on both:

1. Reducing the number of LLM calls per flow.
2. Reducing input tokens per LLM call.

## Why this sprint exists

Recent usage evidence showed high input-token usage during repeated E2E/regression runs.

Observed concerns:

- repeated large system/skill prompts
- simple flows making multiple LLM calls
- full or broad skill content included when compact context should be enough
- need for local telemetry instead of relying only on OpenAI dashboard
- need to measure before and after optimization

## Source rules

- PRD v2.3 Complete LLM Mode
- Complete LLM Mode Runtime Policy Spec
- Complete LLM Mode P0 Scenario Spec
- Token efficiency rule: deterministic backend/DOM first; LLM only when required
- Context policy: never send raw full DOM or full history by default
- Skill policy: compact core always, summaries by purpose, full skills only on escalation
- Backend truth rule: LLM proposes; backend validates and owns truth

## Selected Sprint 3 stories

Core Sprint 3:

1. INT-OBS-001 LLM call and token telemetry report
2. INT-LLM-002 Compact system prompt and skill summaries
3. INT-CALL-001 Deterministic fast path for simple picked-element actions
4. INT-CTX-001 Context budget gate and history compaction
5. INT-DOM-002 Compact page and section intelligence packet
6. INT-E2E-002 Token-budget regression checks

Stretch only:

7. INT-LLM-003 Route step_plan_normalizer through LLMRuntimeController

## Execution order

1. INT-OBS-001 — measure call count and token usage first
2. INT-LLM-002 — reduce repeated system/skill prompt size
3. INT-CALL-001 — reduce LLM calls for simple deterministic flows
4. INT-CTX-001 — cap/summarize history and DOM/tool outputs
5. INT-DOM-002 — provide compact page intelligence instead of raw DOM
6. INT-E2E-002 — add regression-level token budget checks
7. INT-LLM-003 — stretch only after the above are stable

## Success criteria

Sprint 3 is successful only if:

- existing 5 E2E tests still pass
- LLM call count is visible per test/run
- total estimated input tokens are visible per test/run
- largest prompt is visible
- system/skill token contribution is visible
- DOM/history token contribution is visible
- simple picked-element flows reduce LLM call count
- simple flows reduce system/skill prompt tokens by at least 50%
- average input tokens per simple E2E flow reduce by at least 30–50%
- no raw DOM/full history is resent by default
- backend still owns runtime truth
- no confirmation/execution safety gate is removed

## Explicit non-goals

Do not implement in Sprint 3 unless explicitly approved:

- full multi-model routing
- cheap/nano model production split
- full Trace UI redesign
- frontend tab rename/redesign
- docked/devtools-style frontend layout
- replay repair/versioning
- permission/autonomy mode
- broad product feature expansion

## Dependency rules

- INT-OBS-001 must complete before INT-E2E-002.
- INT-OBS-001 should run before optimization work so we can measure baseline.
- INT-LLM-002 and INT-CTX-001 must prove token reduction using INT-OBS-001 telemetry.
- INT-CALL-001 must prove call-count reduction using INT-OBS-001 telemetry.
- Quality gates must run after every optimization story.

## Sprint 3 principle

Every LLM call must justify itself.
Every token must have a reason.
If deterministic backend/DOM can do it safely, no LLM call.
If LLM is needed, send the smallest purpose-specific context.
