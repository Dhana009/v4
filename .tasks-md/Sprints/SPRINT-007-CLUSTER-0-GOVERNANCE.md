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

**In Scope — Sprint 7:**
- Backend event and command seam completion (Cluster 1)
- Frontend transport, state, and interaction mode completion (Cluster 2)
- Real frontend component wiring to live backend events (Cluster 3)
- Local browser E2E smoke proof with fake-LLM (Cluster 4)

**Out of Scope — Sprint 7:**
- Paid LLM browser E2E (Sprint 8)
- Real-world/live-site testing (Sprint 9)
- Manual Mode (Phase 4)
- Advanced Playwright vocabulary hardening (Phase 5)
- Agent Control Center multi-model UI (stabilized architecture)
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
14. **No browser E2E in Clusters 0–3.** Browser E2E is Cluster 4 only, after backend and frontend clusters are complete.

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
| Shadow DOM / browser | Component behavior inside Shadow DOM container | Cluster 4 only |
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

- Browser E2E is Cluster 4 only.
- Uses fake-LLM fixture responses — no real model calls.
- No paid LLM in E2E during Sprint 7.
- E2E must pass locally before any merge of Cluster 4.
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
| 0 | Governance, source mapping, test architecture | None |
| 1 | Backend event and command seam completion | Cluster 0 approved |
| 2 | Frontend transport, state, interaction mode completion | Cluster 1 Done |
| 3 | Real frontend component wiring to live backend events | Cluster 2 Done |
| 4 | Local browser E2E smoke proof | Cluster 3 Done |

One cluster at a time. Do not begin Cluster 2 until Cluster 1 is Done with evidence. Do not begin Cluster 3 until Cluster 2 is Done with evidence. Do not begin E2E (Cluster 4) until Cluster 3 is Done.

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
