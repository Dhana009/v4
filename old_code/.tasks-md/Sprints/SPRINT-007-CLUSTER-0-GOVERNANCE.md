# Sprint 7 — Cluster 0: Governance, Source Mapping, Test Architecture, Execution Protocol

**Sprint:** Sprint 7
**Cluster:** 0
**Status:** Planning
**Date:** 2026-05-13
**HEAD at planning:** 8bdd8def90b71fdaa24890943ec792b55397c66f

---

## Sprint 7 Goal

After Sprint 7, Complete LLM Mode must work end-to-end through the real frontend:
- Backend emits typed lifecycle events for every meaningful phase transition
- Frontend renders backend truth (not inferred state, not demo content)
- Frontend sends typed commands to backend (no fire-and-forget string messages)
- LLM remains proposer and reasoner only — it does not decide step completion, recording finality, or failure resolution
- Execution, recording, code generation, replay, and run completion remain backend-owned
- A local browser E2E smoke test proves the main flows against the real UI

Sprint 8 will focus on controlled realistic testing and hardening.
Sprint 9 will focus on real-world/live-site testing.

---

## Scope

**In Scope — Sprint 7 (Clusters 0–11):**
- C0: Governance, source mapping, test architecture, execution protocol
- C1: Backend event and command seam completion
- C2: LLM/runtime live integration gaps (Page Intelligence, recommendation, plan diff, locator, recovery, telemetry, capability, fail-closed)
- C3: Frontend architecture and design prototype extraction
- C4: Docked Shadow DOM host and page compensation
- C5: Typed frontend event store and command dispatcher
- C6: LLM tab complete live workflow
- C7: Steps tab, Manual Mode foundation, picker/locator workflows
- C8: Recorded + Code + Replay + Save/Load UI
- C9: Trace + Artifacts + Agent visibility
- C10: Integrated local browser E2E smoke gate (fake-LLM only)
- C11: Sprint 7 final acceptance, handoff, push readiness

**Manual Mode — Sprint 7 in-scope (foundation):**
- Mode toggle inside Steps tab (LLM Mode / Manual Mode)
- Manual Mode workspace layout
- Manual action builder (baseline)
- Manual assertion builder (baseline)
- Expected value / test data handling
- Wrong-page / missing-data / weak-locator states

**Out of Scope — Sprint 7:**
- Paid LLM browser E2E (Sprint 8)
- Real-world / live-site testing (Sprint 9)
- Advanced Manual Mode hardening (Sprint 8): expanded action/assertion vocabulary beyond Sprint 7 baseline, multi-step manual authoring polish, advanced special-case handling
- Manual exploratory hardening on realistic fixture pages (Sprint 8)
- Advanced Playwright vocabulary hardening (Phase 5)
- Agent Control Center full multi-model UI (only limited live view in C9)
- Page Maps, persistent locator library, session memory
- Multi-model orchestration specialist agents beyond Page Intelligence

---

## Non-Negotiable Architecture Rules

These rules carry forward from Sprint 6 unchanged. Any story that violates them is rejected before implementation begins.

1. **Backend owns runtime truth.** Step lifecycle, finality, recording, replay status, and run completion are backend-owned. Frontend must not infer or simulate any of these.
2. **LLM proposes and reasons only.** LLM output is never treated as execution confirmation, step recording approval, or failure resolution. Backend validates everything.
3. **Frontend renders typed backend events and sends typed backend commands only.** No frontend-local state machine that mirrors or extrapolates backend phase from LLM text.
4. **DOM/Page Intelligence provides candidates and context only.** Step Runner validates candidates; it does not accept them blindly.
5. **Trace and artifacts are evidence only.** They do not drive UI state.
6. **Frontend must not infer lifecycle truth.** If a backend event is missing, frontend waits or shows unknown — it does not synthesize a state.
7. **No source rule → no test.** Every test must reference the PRD rule or governance doc that requires it.
8. **No test → no implementation.** Tests are written and reviewed before implementation code is written.
9. **No negative tests → no merge.** Every story must include tests for invalid/stale/malformed inputs.
10. **No Done without evidence.** Evidence = committed test files passing + implementation committed + story updated.
11. **No bug fix without bug ticket.** All bugs tracked under `.tasks-md/Bugs/`.
12. **Code must remain modular.** No expanding monoliths: `agent.py`, `server.py`, `browser.py`, `frontend/src/main.jsx`, `aw-ide-panel.jsx`.
13. **No paid LLM calls in Sprint 7.** Fake-LLM / fixture-based only until Sprint 8 explicit acceptance gate.
14. **No browser E2E in Clusters 0–9.** Browser E2E is Cluster 10 only, after backend, LLM/runtime integration, frontend extraction, Shadow DOM host, event store, and all tab UIs are complete.

---

## Source Hierarchy

When any conflict exists, use this priority order:

1. PRD v2.3 guidance (all documents in `PRD_v2_3_Modular_Pack_v2/`)
2. Sprint 7 Cluster 0 governance (this document)
3. Sprint 6 HANDOFF document (`SPRINT-006-HANDOFF.md`)
4. Story-specific implementation notes
5. Sprint 6 story files (reference only; do not regress them)

If a v2.2 section in any PRD doc conflicts with v2.3 guidance, v2.3 wins.

---

## Testing Strategy

### Test-First Protocol

For every Sprint 7 story:
1. Read story file completely before writing any code.
2. Write all listed tests in the `Tests First` section first.
3. Run tests — they must fail (red) before implementation.
4. Implement the minimum code to make tests pass (green).
5. Refactor to maintain modularity.
6. Confirm tests still pass.
7. Confirm no regression in existing cheap suite.
8. Commit implementation + tests together.

### Test Taxonomy

| Type | Description | Where |
|------|-------------|-------|
| Unit | Single function/module behavior, pure inputs/outputs | `tests/test_*.py` |
| Contract | Interface boundary — event builder payloads, command envelope shapes | `tests/test_*_contract*.py` |
| Reducer/store | Frontend state reducer logic, pure functions | `tests/test_frontend_*.py` or frontend test files |
| Command dispatcher | Frontend → backend command routing and validation | `tests/test_command_*.py` |
| Integration | Multi-module interaction without full browser/LLM | `tests/test_*_integration*.py` |
| Frontend component | Component render against typed backend event data | frontend test suite |
| Shadow DOM / browser | Component behavior inside Shadow DOM container | Cluster 10 only |
| Local fake-LLM E2E | Full backend flow with fixture LLM responses | `tests/e2e/` |
| Regression guard | Run suite that must stay green across all clusters | `tests/test_sprint7_regression_guard.py` |
| Paid LLM E2E | Real model, real browser — gated to Sprint 8 only | Not in Sprint 7 |

### Regression Gate

The Sprint 6 cheap regression suite (1689 tests, 12 tracked pre-existing failures) must remain stable throughout Sprint 7. Any new failure introduced by Sprint 7 work is a blocker — stop and investigate before continuing.

Command:
```bash
python -m pytest -q --ignore=tests/e2e 2>&1 | tail -5
```

---

## TDD Workflow

```
1. Story file reviewed → source rules confirmed
2. Test file created with failing tests
3. git add test file (not implementation)
4. git commit "test: <story-id> failing tests for <feature>"
5. Implementation written
6. Tests pass
7. git add implementation + test updates
8. git commit "feat: <story-id> <feature>"
9. Regression guard run
10. Story status updated to Done with evidence
```

---

## Modularization Rules

- New backend logic goes in a focused module under `runtime/` or a new `ws/` router module — not in `agent.py` or `server.py` directly.
- New frontend logic goes in focused modules: transport, store, command dispatcher, tab components, cards — not in `main.jsx` or `aw-ide-panel.jsx` directly.
- `agent.py` may only be touched at thin event-emission seams.
- `server.py` may only be touched at command-routing seams.
- `frontend/src/main.jsx` may only receive wiring changes that thread live transport state into `IDEPanel` — not new logic blocks.
- `aw-ide-panel.jsx` may only be touched at component prop/callback boundaries — not new logic.
- Each new module must have its own test file.
- No module may exceed 300 lines without a planned split boundary documented in the story.

---

## Story Lifecycle Rules

| Status | Meaning |
|--------|---------|
| Planning | Story defined, not started. Tests not yet written. |
| In Progress | Tests written (failing). Implementation underway. |
| Done | Tests passing. Implementation committed. Evidence linked. Story file updated. |
| Blocked | Dependency unresolved. Blocking issue filed. |
| Cancelled | Out of scope. Reason documented. |

Rules:
- No story moves to In Progress without a test plan.
- No story moves to Done without committed evidence.
- No story moves to Done if regression suite has new failures caused by the story.
- No story is marked Done with placeholders or pending items.

---

## Bug Ticket Rules

- Every bug discovered during Sprint 7 work gets its own bug ticket before any fix is attempted.
- Bug path: `.tasks-md/Bugs/Backlog/BUG-S7-<NNN>-<description>.md`
- Bug ticket must include: severity, source rule violated, reproduction steps, failing test, fix plan.
- No fix is committed without a referenced bug ticket.
- Pre-existing bugs from Sprint 6 (BUG-S6-FINAL-001, BUG-S6-FINAL-002) are tracked separately — do not close them in Sprint 7 unless explicitly tasked.

---

## Evidence Requirements

Every story marked Done must provide:
- [ ] Implementation file(s) committed
- [ ] Test file(s) committed with all tests passing
- [ ] Regression suite passes (no new failures)
- [ ] Coverage ≥ 95% for new modules
- [ ] Story file updated with Done status and evidence links
- [ ] Commit message references story ID and test count

---

## Coverage Expectations

- New backend modules: ≥ 95% line coverage
- New frontend modules: covered by contract + component tests
- No new module merged without a coverage run
- Coverage command per story:
  ```bash
  python -m pytest tests/<story_test_file>.py --cov=<module_path> --cov-fail-under=95
  ```

---

## Local Browser E2E Policy

- Browser E2E is Cluster 10 only.
- Uses fake-LLM fixture responses — no real model calls.
- No paid LLM in E2E during Sprint 7.
- E2E must pass locally before any merge of Cluster 10.
- E2E target: smoke test the main LLM Mode flow end-to-end through the real frontend.

---

## Paid E2E Policy

- Paid E2E is **Sprint 8 only**.
- No paid LLM calls during Sprint 7 planning, implementation, or testing.
- Paid E2E gate ticket: will be created in Sprint 8 Cluster 0.

---

## Stop Conditions

Stop implementation and escalate if any of the following occur:

1. A Sprint 7 story requires changes to forbidden files not listed in its allowed files.
2. A new test failure appears in the Sprint 6 regression suite that is not a tracked pre-existing issue.
3. A story's implementation requires touching more than its allowed module boundary without a planned refactor story.
4. A bug is found that cannot be fixed within the current story scope.
5. Tests reveal an architecture conflict with a core PRD invariant.
6. Coverage falls below 95% and root cause is not immediately clear.
7. Frontend wiring requires frontend to infer lifecycle state (violates architecture rule 6).
8. Any paid LLM call is triggered accidentally.

---

## Cluster Sequence Overview

| Cluster | Focus | Prerequisite |
|---------|-------|-------------|
| C0 | Governance, source mapping, test architecture, execution protocol | None |
| C1 | Backend event and command seam completion | C0 approved |
| C2 | LLM/runtime live integration gaps | C1 Done |
| C3 | Frontend architecture and design prototype extraction | C0 approved (UI work blocked on C5) |
| C4 | Docked Shadow DOM host and page compensation | C3 Done |
| C5 | Typed frontend event store and command dispatcher | C1 Done, C2 Done |
| C6 | LLM tab complete live workflow | C5 Done |
| C7 | Steps tab, Manual Mode foundation, picker/locator workflows | C5 Done |
| C8 | Recorded + Code + Replay + Save/Load UI | C5 Done, C1 save/load seams Done |
| C9 | Trace + Artifacts + Agent visibility | C5 Done, C2 telemetry payloads Done |
| C10 | Integrated local browser E2E smoke gate (fake-LLM only) | C3–C9 Done |
| C11 | Sprint 7 final acceptance, handoff, push readiness | C10 Done |

One cluster at a time within a dependency chain. Do not begin a cluster until its prerequisites are Done with evidence. Browser E2E is **Cluster 10 only**; no browser E2E in Clusters 0–9. Final acceptance (C11) runs only after C10 passes.

---

## Cluster 0 Stories

| Story | Title |
|-------|-------|
| S7-0001 | Complete LLM Mode requirement matrix |
| S7-0002 | Source-rule-to-test mapping |
| S7-0003 | Sprint 7 test taxonomy and regression gate |
| S7-0004 | Frontend-backend seam readiness matrix |
| S7-0005 | Modular frontend architecture and design extraction policy |
| S7-0006 | Sprint 7 story template |
| S7-0007 | Bug and evidence policy |
| S7-0008 | Cluster execution protocol and stop conditions |

All Cluster 0 stories are planning/documentation only. No product code is written in Cluster 0.

---

## Anchored Rule ID Index (GOV-S7-C0-NNN)

Stories cite synthetic governance rule IDs. The full anchored set is:

### Architecture invariants (GOV-S7-C0-001 … GOV-S7-C0-014)

Each ID maps 1:1 to the numbered rule in the "Non-Negotiable Architecture Rules" section above:

| ID | Rule |
|----|------|
| GOV-S7-C0-001 | Backend owns runtime truth. |
| GOV-S7-C0-002 | LLM proposes and reasons only. |
| GOV-S7-C0-003 | Frontend renders typed backend events and sends typed backend commands only. |
| GOV-S7-C0-004 | DOM/Page Intelligence provides candidates and context only. |
| GOV-S7-C0-005 | Trace and artifacts are evidence only. |
| GOV-S7-C0-006 | Frontend must not infer lifecycle truth. |
| GOV-S7-C0-007 | No source rule → no test. |
| GOV-S7-C0-008 | No test → no implementation. |
| GOV-S7-C0-009 | No negative tests → no merge. |
| GOV-S7-C0-010 | No Done without evidence. |
| GOV-S7-C0-011 | No bug fix without bug ticket. |
| GOV-S7-C0-012 | Code must remain modular (no monolith growth). |
| GOV-S7-C0-013 | No paid LLM calls in Sprint 7. |
| GOV-S7-C0-014 | No browser E2E in Clusters 0–9 (E2E is C10 only). |

### Test architecture invariants (GOV-S7-C0-015 … GOV-S7-C0-029)

| ID | Rule |
|----|------|
| GOV-S7-C0-015 | Test taxonomy: Unit, Contract, Reducer/store, Command dispatcher, Integration, Frontend component, Shadow DOM/browser, Local fake-LLM E2E, Regression guard, Paid LLM E2E (deferred). |
| GOV-S7-C0-016 | Test-first protocol: write all listed tests before any implementation. |
| GOV-S7-C0-017 | Tests must fail (red) before implementation. |
| GOV-S7-C0-018 | Implement minimum code to make tests pass (green). |
| GOV-S7-C0-019 | Refactor without breaking tests. |
| GOV-S7-C0-020 | Confirm no regression in existing cheap suite. |
| GOV-S7-C0-021 | Commit implementation + tests together. |
| GOV-S7-C0-022 | Regression gate: Sprint 6 cheap suite baseline must stay stable. |
| GOV-S7-C0-023 | Test file naming follows taxonomy (`tests/test_*.py`, `*_contract*`, `*_integration*`). |
| GOV-S7-C0-024 | Contract tests assert envelope shape and required fields. |
| GOV-S7-C0-025 | Integration tests assert multi-module behavior without browser/LLM. |
| GOV-S7-C0-026 | Frontend component tests render against typed backend event data. |
| GOV-S7-C0-027 | Negative tests cover stale command, missing id, unknown event, malformed payload. |
| GOV-S7-C0-028 | Regression tests guard prior-cluster work after each new cluster. |
| GOV-S7-C0-029 | Test fixtures must be deterministic; no random delays, no network. |

### Evidence and story lifecycle invariants (GOV-S7-C0-030 … GOV-S7-C0-044)

| ID | Rule |
|----|------|
| GOV-S7-C0-030 | Story Planning state requires: title, source rules, objective, current context, tests-first plan. |
| GOV-S7-C0-031 | Story In-Progress state requires failing tests committed first. |
| GOV-S7-C0-032 | Story Done state requires implementation + tests committed and evidence linked. |
| GOV-S7-C0-033 | Story Done state forbids placeholders or pending items. |
| GOV-S7-C0-034 | Story Blocked state requires linked blocking ticket. |
| GOV-S7-C0-035 | Story Cancelled state requires documented reason. |
| GOV-S7-C0-036 | Evidence must include implementation files committed. |
| GOV-S7-C0-037 | Evidence must include test files committed with all tests passing. |
| GOV-S7-C0-038 | Evidence must include regression suite pass (no new failures). |
| GOV-S7-C0-039 | Evidence must include coverage ≥ 95% for new modules. |
| GOV-S7-C0-040 | Evidence must include story file updated with Done status. |
| GOV-S7-C0-041 | Commit message references story ID and test count. |
| GOV-S7-C0-042 | No module exceeds 300 lines without documented split boundary. |
| GOV-S7-C0-043 | Each new module must have its own test file. |
| GOV-S7-C0-044 | Pre-existing Sprint 6 bugs tracked separately; do not close without explicit task. |

### Coverage, bug-policy, and E2E invariants (GOV-S7-C0-045 … GOV-S7-C0-059)

| ID | Rule |
|----|------|
| GOV-S7-C0-045 | Coverage threshold: ≥ 95% line coverage on new backend modules; do not lower threshold. |
| GOV-S7-C0-046 | Coverage runs per story via `pytest --cov=<module_path> --cov-fail-under=95`. |
| GOV-S7-C0-047 | Frontend new modules covered by contract + component tests. |
| GOV-S7-C0-048 | No new module merged without a coverage run. |
| GOV-S7-C0-049 | Bug ticket path: `.tasks-md/Bugs/Backlog/BUG-S7-<NNN>-<description>.md`. |
| GOV-S7-C0-050 | Bug ticket must include severity, source rule violated, repro, failing test, fix plan. |
| GOV-S7-C0-051 | No fix committed without referenced bug ticket. |
| GOV-S7-C0-052 | Local E2E uses fake-LLM only; no paid APIs. |
| GOV-S7-C0-053 | Local E2E uses local fixture sites only; no live external sites. |
| GOV-S7-C0-054 | Local E2E captures screenshots, event log, command log, error log, manifest. |
| GOV-S7-C0-055 | Local E2E flakiness < 5% across 3 consecutive runs. |
| GOV-S7-C0-056 | Paid E2E gated to Sprint 8 only; explicit acceptance ticket required. |
| GOV-S7-C0-057 | Live-site testing gated to Sprint 9 only. |
| GOV-S7-C0-058 | E2E harness must locate `aw-shadow-host` and interact through docked layout. |
| GOV-S7-C0-059 | Forbidden staging: AGENTS.md, .DS_Store, .tasks-md/.DS_Store, .playwright-cli, frontend_new_design_prototype. |

### Stop conditions and architecture-drift invariants (GOV-S7-C0-060 … GOV-S7-C0-063)

| ID | Rule |
|----|------|
| GOV-S7-C0-060 | Stop if any forbidden file is touched outside its story's allowed list. |
| GOV-S7-C0-061 | Stop if new regression failure appears outside tracked pre-existing list. |
| GOV-S7-C0-062 | Stop if architecture invariant is violated (any of GOV-S7-C0-001 … GOV-S7-C0-006). |
| GOV-S7-C0-063 | Stop if static/demo runtime truth appears in live mode (no demo fallback). |

The range `GOV-S7-C0-001 … GOV-S7-C0-063` defines the complete Sprint 7 governance ID space. Stories that reference an ID outside this range must update this index before merge.

