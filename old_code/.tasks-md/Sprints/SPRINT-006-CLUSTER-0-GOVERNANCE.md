# SPRINT-006 Cluster 0 — Test Architecture, Coverage, and Modularization Governance

**Sprint:** Sprint 6 — Complete LLM Mode Implementation Foundation  
**Cluster:** 0 — Governance & Testing Structure (Foundation only)  
**Status:** Planning  
**Type:** Foundation stories (documentation + validation, no product code)

---

## Overview

Cluster 0 establishes the safe execution framework for Complete LLM Mode. It defines:

- Test architecture and layers
- Coverage gates
- Story templates
- Regression validation
- Paid test policy
- Modularization boundaries

No product features are built in Cluster 0. No paid LLM is called. No agent.py changes. Only governance, documentation, and test scaffolding.

**Why first?** Complete LLM Mode spans ~100 stories across LLM runtime, context, frontend UI, recording, replay, recovery, and locator intelligence. Without governance, implementation becomes chaotic: tests scattered, coverage unknown, monoliths grow, regressions hidden, paid E2E abused.

---

## Story list (8 stories)

| ID | Title | Tier | Status | Acceptance Output |
|---|---|---|---|---|
| S6-0001 | Complete LLM Mode requirement-to-test matrix | 1 | Planning | `.tasks-md/Testing/S6-COMPLETE-LLM-MODE-TEST-MATRIX.md` |
| S6-0002 | Sprint 6 test strategy and test taxonomy | 1 | Planning | `.tasks-md/Planning/S6-TEST-STRATEGY.md` |
| S6-0003 | Coverage gate and command policy | 1 | Planning | `pyproject.toml` / `.coveragerc` + `.tasks-md/Testing/S6-COVERAGE-GATE.md` |
| S6-0004 | Modular code boundary rules | 1 | Planning | `.tasks-md/Planning/S6-MODULARIZATION-RULES.md` |
| S6-0005 | Sprint 6 story template | 1 | Planning | `.tasks-md/Planning/S6-STORY-TEMPLATE.md` |
| S6-0006 | Regression guard command set | 2 | Planning | `.tasks-md/Testing/S6-REGRESSION-GUARD.md` |
| S6-0007 | Paid LLM/E2E acceptance policy | 2 | Planning | `.tasks-md/Planning/S6-PAID-TEST-POLICY.md` |
| S6-0008 | Cluster execution protocol | 2 | Planning | `.tasks-md/Planning/S6-CLUSTER-EXECUTION-PROTOCOL.md` |

---

## Detailed story specs

### S6-0001 — Complete LLM Mode requirement-to-test matrix

**Purpose:** Map every Complete LLM Mode PRD requirement to test layers.

**Scope:**

For each Complete LLM Mode requirement from PRD v2.3 and scenario spec:

- Requirement ID (from PRD section/subsection)
- Source document
- Architecture invariant (what must be true)
- Unit test target (if any)
- Contract test target (if any)
- Integration test target (if any)
- E2E test target (if any)
- Regression risk (low/medium/high)
- Owner layer (backend/frontend/llm/recording/locator)
- Current status (Done/Partial/Missing)

**Output:** `.tasks-md/Testing/S6-COMPLETE-LLM-MODE-TEST-MATRIX.md` (markdown table or JSON).

**Acceptance criteria:**

- All requirements from PRD phases 2–4 are listed.
- Each requirement has at least one test layer assigned.
- No requirement marked Done without test evidence.
- Matrix is cross-referenced to existing tests.

**Must NOT:**

- Include implementation code.
- Claim Done without tests.
- Require paid LLM.
- Change product behavior.

---

### S6-0002 — Sprint 6 test strategy and test taxonomy

**Purpose:** Define what each test layer means and when it is required.

**Scope:**

Document the test taxonomy:

```text
Unit test — single function/class, no backend/LLM/browser
Contract test — typed interface boundary, fake/mock dependencies
Integration test — two or more modules, usually no backend/browser
E2E test — full flow with real backend, real browser, or real LLM
Paid LLM test — calls real OpenAI API; gated by RUN_PAID_LLM_CONTRACT
Paid browser E2E — calls real OpenAI API + real browser; expensive
Regression test — focused cheap smoke suite to catch regressions
```

For each layer:

- Definition
- When required (always/often/rarely/never)
- Folder convention
- Naming convention
- Marker (pytest.mark)
- Dependencies allowed
- Speed expectation

**Output:** `.tasks-md/Planning/S6-TEST-STRATEGY.md`

**Acceptance criteria:**

- All test layers defined.
- Clear boundary between paid and cheap tests.
- Folder/naming convention is specific.
- Covers both positive and negative test obligations.

**Must NOT:**

- Implement tests yet.
- Require LLM calls.

---

### S6-0003 — Coverage gate and command policy

**Purpose:** Enforce 95%+ coverage for new/modified modules.

**Scope:**

- Audit current coverage config (if any).
- Set per-module coverage minimums.
- Define branch coverage for state machines / validators.
- Propose CI integration (if not already present).
- Document local command to check coverage.

**Output:** 

- Updated `pyproject.toml` and/or `.coveragerc`
- `.tasks-md/Testing/S6-COVERAGE-GATE.md` (strategy document)

**Example coverage commands:**

```bash
python -m pytest tests/ --cov=runtime --cov=recording --cov=locator --cov-report=term-missing --cov-fail-under=95
```

**Acceptance criteria:**

- Coverage gate is measurable and enforced locally.
- New modules must hit 95% coverage before merge.
- Strategy document explains exclusions (if any).
- Command is reproducible.

**Must NOT:**

- Lower coverage to pass.
- Exclude new code without justification.

---

### S6-0004 — Modular code boundary rules

**Purpose:** Prevent agent.py/server.py from becoming monoliths.

**Scope:**

Define module boundaries for:

- New LLM runtime features → focused runtime module
- New frontend features → frontend module + test
- New recording features → recording module
- New locator features → locator module
- Agent.py/Server.py → orchestration only, no business logic

Example rule:

```
Page Intelligence live wiring should be:
  ✗ NOT: directly in agent.py step_plan_normalizer planning
  ✓ YES: agent.py calls a focused helper in runtime/page_intelligence.py
```

**Output:** `.tasks-md/Planning/S6-MODULARIZATION-RULES.md`

**Acceptance criteria:**

- Clear module ownership.
- Max responsibility per file is defined.
- Orchestrator files remain thin.
- Rules prevent drift.

**Must NOT:**

- Move unrelated code.
- Change product behavior.

---

### S6-0005 — Sprint 6 story template

**Purpose:** Every future story follows a strict shape.

**Scope:**

Create a template file showing:

```text
# Story title

## Source rules
- Which PRD requirements / governance rules apply?

## Current evidence
- What exists in repo?
- What tests exist?
- What gaps are known?

## Desired behavior
- What must change?
- What must stay the same?

## Out of scope
- What is explicitly NOT included?

## Allowed files
- Which files can be changed?
- Which modules can be created?

## Forbidden files
- No changes to [list]

## Tests first
- Unit tests to write (list)
- Contract tests to write (list)
- Integration tests (list)
- E2E tests (if needed)

## Implementation notes
- Modular approach
- Key invariants
- Known risks

## Coverage requirement
- Minimum 95% for new modules

## Validation commands
- Focused test command
- Regression guard command
- Coverage check command

## Artifact/evidence requirement
- What must be committed?
- What evidence file required?

## Stop conditions
- When to halt and ask for clarification
```

**Output:** `.tasks-md/Planning/S6-STORY-TEMPLATE.md`

**Acceptance criteria:**

- Template is concrete and enforceable.
- Later stories use this template.
- No vague sections.

---

### S6-0006 — Regression guard command set

**Purpose:** Define the cheap regression suite that must pass after every cluster.

**Scope:**

Build a command that runs focused cheap tests covering:

```text
✓ Backend event contract truth
✓ Recording / code_update truth
✓ LLMRuntimeController
✓ Prompt packs
✓ Skill policy
✓ Tool schema policy
✓ Planning convergence
✓ Page Intelligence schema / fake integration
✓ Frontend contract tests
✓ Replay smoke
✓ Deterministic fast path
✓ Locator contracts
```

**Output:** 

```bash
# Command syntax:
REGRESSION_SUITE="tests/test_backend_event_sequences.py tests/test_recording_codegen_truth_contract.py tests/test_llm_runtime_controller_contract.py tests/test_prompt_pack_builder.py tests/test_skill_escalation_contract.py tests/test_tool_schema_filter.py tests/test_planning_convergence_contract.py tests/test_page_intelligence_schema.py tests/test_page_intelligence_fake_integration.py tests/test_replay_one.py tests/test_deterministic_fast_path.py tests/test_dom_locator_contracts.py"
python -m pytest $REGRESSION_SUITE -q
```

Store in: `.tasks-md/Testing/S6-REGRESSION-GUARD.md`

**Acceptance criteria:**

- Command is documented.
- All suites listed.
- Runs locally in <2 minutes.
- Catches regressions from prior clusters.

**Must NOT:**

- Include paid LLM test.
- Include paid browser E2E.
- Change test implementations.

---

### S6-0007 — Paid LLM/E2E acceptance policy

**Purpose:** Prevent paid tests from becoming the first debugging tool.

**Scope:**

Define when paid LLM probes and paid browser E2E are allowed:

```text
Paid LLM probe allowed:
  - After all contract/unit tests pass
  - After regression guard passes
  - To verify real model behavior once
  - When ENV=RUN_PAID_LLM_CONTRACT=1

Paid browser E2E allowed:
  - After fake integration passes
  - After all cheap E2E pass
  - Only for new Complete LLM Mode flow
  - Token expectations pre-agreed
  - llm-calls.json + token-report.json required in artifact
  - Hard stop on PLANNING_NO_PROGRESS or unhandled error

Forbidden (no paid tests):
  - For debugging single function
  - For experimenting with model prompt
  - For testing infrastructure changes
  - Without prior cheap test evidence
```

**Output:** `.tasks-md/Planning/S6-PAID-TEST-POLICY.md`

**Acceptance criteria:**

- Policy is clear and enforceable.
- Artifact requirements are specific.
- Stop conditions are absolute.

---

### S6-0008 — Cluster execution protocol

**Purpose:** Define how each later cluster is requested and executed.

**Scope:**

Document the protocol:

```text
Step 1: Cluster story files are reviewed and approved.
Step 2: Cluster is given to Claude Code with specific scope.
Step 3: Claude Code executes test-first, implementation second.
Step 4: After cluster done, report is generated.
Step 5: Report is reviewed before next cluster starts.
No multi-cluster tasks.
No hidden implementation.
No automatic continuation.
```

Each cluster handoff should include:

- Story file path
- Expected test structure
- Forbidden files
- Validation commands
- Stop conditions
- Next cluster pre-requisites

**Output:** `.tasks-md/Planning/S6-CLUSTER-EXECUTION-PROTOCOL.md`

**Acceptance criteria:**

- Protocol is explicit and testable.
- Prevents scope creep.
- Enables review gates.

---

## Cluster 0 acceptance criteria

Cluster 0 is Done only when:

1. ✓ Complete LLM Mode requirements mapped to test layers (S6-0001)
2. ✓ Test taxonomy defined (S6-0002)
3. ✓ Coverage gate configured (S6-0003)
4. ✓ Modularization rules documented (S6-0004)
5. ✓ Story template created (S6-0005)
6. ✓ Regression command set documented (S6-0006)
7. ✓ Paid test policy established (S6-0007)
8. ✓ Cluster execution protocol defined (S6-0008)
9. ✓ No product behavior changed
10. ✓ No feature implementation started

---

## Recommended execution order

After Cluster 0 approval, proceed to:

```text
Cluster 1 — LLM Runtime Purpose Coverage (expand coverage from S5)
Cluster 2 — Context/Memory/Token/Tool/Schema Policy (comprehensive wiring)
Cluster 3 — Page Intelligence Live Invocation (auto-trigger weak DOM)
Cluster 4 — Journey Planner + Steps Mode (new flow type)
Cluster 5 — Plan Discussion/Correction/Editing (plan workflow)
Cluster 6 — Locator Intelligence + Locator Update (weak locator repair)
Cluster 7 — Permission/Capability/Feature Handling (gap logging)
Cluster 8 — Replay Repair + Save/Load/Versioning (persistence)
Cluster 9 — Frontend Complete LLM UI (shadow DOM + docked)
Cluster 10 — Trace/Artifacts/Observability (backend logs + frontend)
Cluster 11 — Final Complete LLM Mode Acceptance (E2E + multi-flow)
```

Each cluster is given one at a time, reviewed, then approved before next.

---

## Notes

- Cluster 0 is not optional.
- Cluster 0 prevents implementation chaos.
- Cluster 0 enables reviewable, modular, tested clusters.
- Cluster 0 must be complete and reviewed before any product code in Cluster 1.
