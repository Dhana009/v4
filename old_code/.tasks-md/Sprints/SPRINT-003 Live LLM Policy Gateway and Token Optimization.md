# SPRINT-003 Live LLM Policy Gateway and Token Optimization

Status: Done
Sprint: Sprint 3
Duration: Bi-weekly / Large optimization sprint
Type: Sprint
Priority: P0

## Goal

Make the live LLM path follow the planned runtime-policy architecture and reduce input-token cost without reducing quality.

## Sprint success target

Current baseline after partial optimization:

| Flow | Calls | Input tokens |
|---|---:|---:|
| basic click | 5 | 10,811 |
| exact text | 7 | 16,232 |
| visible assertion | 8 | 19,935 |
| correction assert-click | 8 | 22,853 |
| MVP lifecycle | 6 | 12,399 |

Sprint 3 target:

| Flow | Target |
|---|---|
| basic click | <=2-3 calls, ideally under 5k tokens |
| exact text | <=3-4 calls, under 8k tokens |
| visible assertion | <=3-4 calls, under 8k-10k tokens |
| correction | reduce safely, no quality loss |
| MVP lifecycle | reduce safely |
| all flows | 5/5 E2E must still pass |

## Sprint 3 Phase 0 - Measurement and Infrastructure Baseline

Done but not sufficient for sprint acceptance:

- INT-OBS-001 LLM call and token telemetry report
- INT-LLM-002 Compact system prompt and skill summaries
- INT-CTX-001 Context budget gate and history compaction
- INT-DOM-002 Compact page and section intelligence packet
- INT-E2E-002 Token-budget regression checks
- INT-CALL-001 Deterministic fast path for simple picked-element actions

Why this is phase 0:

- the modules exist
- the foundational tests pass
- live-path optimization is still incomplete
- simple flows still make too many calls
- tool schema overhead is still large
- deterministic fast path is not yet the live default for safe simple flows

## Sprint 3 core epics

### Epic 1 - Live LLM Policy Gateway

#### Problem

Current live path still behaves like:

`agent.py -> main_orchestrator loop -> repeated tool schemas -> repeated history/tool results`

This violates the planned runtime policy direction. Every call should have a purpose, allowed context, tool policy, schema, validator, budget, and fallback.

#### Stories

- INT-GATE-001 Add live LLM policy gateway before model calls
- INT-GATE-002 Route planning calls through explicit purposes

#### Acceptance

- No simple planning call runs as generic main_orchestrator unless explicitly allowed.
- Each live LLM call records purpose, phase, tools exposed, schema, context level, and budget.
- Tool schemas exposed per call are purpose-limited.
- All 5 E2E still pass.

### Epic 2 - Tool Schema Token Reduction

#### Problem

`tool_schema_tokens` is now the largest aggregate bucket. Planning calls repeatedly expose 6 tools, and execution calls expose around 15 tools.

#### Stories

- INT-TOOL-001 Fix token report top-source calculation
- INT-TOOL-002 Purpose-scoped tool schema exposure

#### Acceptance

- token-report.json correctly identifies `tool_schema_tokens` as top source when true.
- planning calls expose only required planning tools.
- `plan_diff_editor` exposes no browser/action tools.
- simple deterministic planning can avoid model calls entirely.
- all 5 E2E still pass.

### Epic 3 - Deterministic Fast Path with Backend Execution Contract

#### Problem

The deterministic fast path can classify simple flows, but it does not yet emit the backend-compatible parent/children execution-contract shape. Because of that, the live product falls back to the LLM planning loop.

#### Stories

- INT-CALL-001B Build backend-compatible deterministic plan parent/children
- INT-CALL-001C Wire fast path as pre-planner gate

#### Acceptance

- fast path emits parent step with children array
- child operation shape matches `_build_confirmed_execution_plan` expectations
- fast path never executes before confirmation
- `step_recorded` and `code_update` still happen after execution
- basic_click uses fast path and materially fewer calls
- visible_assertion and exact_text use fast path where safe
- all 5 E2E still pass

### Epic 4 - Context and History Compaction

#### Problem

History and tool-result resend still grows across calls, especially in correction flows.

#### Stories

- INT-CTX-001B Purpose-specific context windows
- INT-CTX-001C Tool-result summarization before re-inclusion

#### Acceptance

- each call includes only current-purpose context
- old DOM/tool results are not resent unless explicitly needed
- correction flow history token growth is reduced
- `budget_status` is meaningful: ok / capped / compacted / escalated
- all 5 E2E still pass

### Epic 5 - Page Intelligence Live Wiring

#### Problem

`runtime/page_intelligence.py` exists, but the live product still relies on the model loop to request DOM extraction and locator work. Page intelligence should be compact structured input, not raw tool chatter.

#### Stories

- INT-DOM-002B Wire page intelligence into live dom_extract result

#### Acceptance

- LLM-facing `dom_extract` output is compact page intelligence
- raw DOM is not included by default
- DOM/tool-result tokens are reduced below target
- locator validation still uses backend/browser truth
- all 5 E2E still pass

### Epic 6 - Token Report and Regression Budget

#### Problem

Telemetry exists, but we need reliable budget comparison and clear top-source attribution.

#### Stories

- INT-E2E-002B Per-test token-report.json and before/after comparison

#### Acceptance

- every E2E artifact has token-report.json
- report includes calls/test, tokens/test, top token source, and largest call
- report includes `tool_schema_tokens` in top-source logic
- sprint report shows before/after reductions
- no E2E quality loss

## Active Sprint 3 stories

- INT-GATE-001 Add live LLM policy gateway
- INT-GATE-002 Route planning calls through explicit purposes
- INT-TOOL-001 Fix token report top-source calculation
- INT-TOOL-002 Purpose-scoped tool schema exposure
- INT-CALL-001B Build backend-compatible deterministic plan parent/children
- INT-CALL-001C Wire fast path as pre-planner gate
- INT-CTX-001B Purpose-specific context windows
- INT-CTX-001C Tool-result summarization before re-inclusion
- INT-DOM-002B Wire page intelligence into live dom_extract result
- INT-E2E-002B Per-test token-report.json and before/after comparison

## Recommended execution order

### Phase 1 - Measurement correctness

1. INT-TOOL-001 Fix token report top-source calculation
2. INT-E2E-002B Ensure token-report.json is written for every E2E

### Phase 2 - Policy gateway

3. INT-GATE-001 Add live LLM policy gateway
4. INT-GATE-002 Route planning calls through explicit purposes
5. INT-TOOL-002 Purpose-scoped tool schema exposure

### Phase 3 - Deterministic fast path

6. INT-CALL-001B Build backend-compatible deterministic plan parent/children
7. INT-CALL-001C Wire fast path as pre-planner gate

### Phase 4 - Context and DOM compaction

8. INT-CTX-001B Purpose-specific context windows
9. INT-CTX-001C Tool-result summarization before re-inclusion
10. INT-DOM-002B Wire page intelligence into live dom_extract result

### Phase 5 - Acceptance

11. Run 5 E2E flows
12. Generate before/after token comparison
13. Mark Sprint 3 accepted only if quality and reduction targets are met

## Final acceptance

Sprint 3 is done only when all of this is true:

- 5/5 E2E tests pass
- unit and contract tests pass
- token-report.json exists for each E2E artifact
- `tool_schema_tokens` are visible in top-source logic
- at least one simple flow uses deterministic fast path
- basic_click call count drops materially
- input tokens drop materially from the current baseline
- backend confirmation and execution rules stay intact

## What not to do

- do not patch only basic_click
- do not bypass backend confirmation
- do not bypass execution contract
- do not hide tool schemas from telemetry
- do not mark a module done just because unit tests pass
- do not accept Sprint 3 unless live E2E token reduction is proven
- do not start Sprint 4 until Sprint 3 acceptance is real
