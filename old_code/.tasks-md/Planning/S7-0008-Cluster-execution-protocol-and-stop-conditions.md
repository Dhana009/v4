# S7-0008 — Cluster Execution Protocol and Stop Conditions

**Sprint:** Sprint 7
**Cluster:** 0 (Governance)
**Type:** Documentation
**Status:** Planning
**Owner:** Process

---

## Objective

Define the step-by-step execution protocol for Sprint 7 clusters. One cluster at a time, tests first, focused implementation, focused validation, regression guard after every cluster, commit per cluster, stop on cross-cluster blockers.

---

## Source Rules

- Sprint 7 Cluster 0 Governance: Cluster sequence overview and stop conditions
- Sprint 7 S7-0003: Regression gate definition and command
- Sprint 7 S7-0006: Story template — tests-first workflow
- PRD `00_MASTER_INDEX.md`: "No Done without evidence. No bug fix without bug ticket."

---

## Current Known Context

Sprint 6 ran clusters sequentially with generally good discipline. Two areas to tighten for Sprint 7:
1. Regression gate was not always run after every story — Sprint 7 runs it after every story and after every cluster.
2. Some Sprint 6 stories were marked Done without full evidence — Sprint 7 enforces the evidence checklist.

---

## Tests First

This is a documentation/protocol story. No implementation tests required.

---

## Cluster Execution Protocol

### Phase 0: Pre-Cluster Preparation

Before any Cluster 1 implementation begins:

1. **Confirm Cluster 0 complete.** All 8 Cluster 0 stories are in Planning status. No implementation gaps.
2. **Capture regression baseline.** Run:
   ```bash
   python -m pytest -q --ignore=tests/e2e 2>&1 | tail -5
   ```
   Record output in `.tasks-md/Testing/S7-REGRESSION-GUARD.md`. Expected: ~1689 passed, 12 pre-existing failures.
3. **Confirm no unexpected dirty files.** Run `git status --short`. Only `.DS_Store`, `AGENTS.md`, `.playwright-cli/`, `frontend_new_design_prototype/` may be dirty.
4. **Read the cluster sprint doc** completely before starting any story.

---

### Phase 1: Per-Story Protocol

For every story in the cluster:

**Step 1: Read story file**
- Read the full story file.
- Confirm all required sections are present (per S7-0006 template).
- Confirm source rules are listed with rule IDs.
- Confirm allowed and forbidden files are listed.
- If any section is missing — stop and complete the story file before coding.

**Step 2: Write failing tests**
- Create the test file(s) listed in the story's `Tests first` section.
- Write all tests — unit, contract, integration, and negative tests.
- Run tests — they must fail (red) at this point.
- Commit the test file:
  ```bash
  git add tests/<story_test_file>.py
  git commit -m "test: <story-id> failing tests for <feature>"
  ```

**Step 3: Implement**
- Write the minimum implementation to make tests pass.
- Touch only the files listed in `Allowed files`.
- If implementation requires a file not in the allowed list — stop. Either update the story file with a justified addition, or file a new story for the additional scope.

**Step 4: Verify tests pass**
- Run story tests:
  ```bash
  python -m pytest tests/<story_test_file>.py -v
  ```
- All tests must pass. No skips. No xfail.

**Step 5: Run coverage**
- Check coverage for new modules:
  ```bash
  python -m pytest tests/<story_test_file>.py --cov=<module> --cov-fail-under=95
  ```
- Coverage must be ≥ 95%. If not, add tests before merging.

**Step 6: Run regression guard**
- Run the full cheap suite:
  ```bash
  python -m pytest -q --ignore=tests/e2e 2>&1 | tail -5
  ```
- Compare against baseline. No new failures allowed.
- If a new failure appears — stop. Investigate before continuing.

**Step 7: Commit implementation**
- Stage implementation file(s) and updated test file(s):
  ```bash
  git add <implementation_files> <test_files>
  git commit -m "feat: <story-id> <feature description>"
  ```

**Step 8: Update story status**
- Add evidence section to story file (test output, regression output, coverage output).
- Update story `Status:` from `In Progress` to `Done`.
- Commit story file update:
  ```bash
  git add .tasks-md/Planning/<story_file>.md
  git commit -m "docs: <story-id> mark done with evidence"
  ```

---

### Phase 2: Post-Cluster Protocol

After all stories in a cluster are Done:

1. **Final regression run.**
   ```bash
   python -m pytest -q --ignore=tests/e2e 2>&1 | tail -5
   ```
   Must pass at or above baseline. Record in cluster sprint doc.

2. **Update cluster sprint doc.** Add final story status, any open bugs, and cluster evidence summary.

3. **Cluster commit.**
   ```bash
   git add .tasks-md/Sprints/SPRINT-007-CLUSTER-<N>-*.md .tasks-md/Planning/S7-<NNN>-*.md
   git commit -m "chore: complete sprint 7 cluster <N> evidence"
   ```

4. **Before starting next cluster.** Read the next cluster's sprint doc fully before beginning any story in it.

---

### Phase 3: Cross-Cluster Blocker Protocol

A cross-cluster blocker occurs when a story in Cluster N requires work that should belong to Cluster N+1 or is blocked by work not yet done in Cluster N-1.

**If blocked by a previous cluster:**
1. Stop the current story.
2. File a blocking note in the story file: `Blocked by: <story-id>`.
3. Return to the blocking story and complete it first.
4. Do not proceed in a blocked story.

**If a story requires scope from a future cluster:**
1. Stop the current story.
2. Extract the cross-cluster requirement into a new story in the correct cluster.
3. Mark the current story as blocked by the new story.
4. Continue in the new story.

---

## Stop Conditions

Implementation must stop and escalate in these situations:

| Condition | Action |
|-----------|--------|
| Story file missing required sections | Complete story file before any coding |
| Forbidden file would need to be modified | Stop. File new story for the additional scope or update allowed files with justification |
| Tests reveal architecture conflict with PRD invariant | Stop. Escalate for architecture decision |
| New regression failure appears | Stop. Investigate root cause before continuing |
| Coverage falls below 95% | Stop. Add tests. Do not lower the threshold |
| Bug discovered outside current story scope | File BUG-S7 ticket. Decide if it blocks current story |
| Frontend wiring would require inferring lifecycle state | Stop. Backend event must be added first |
| Paid LLM call is triggered | Stop. Revert. Fix the test configuration |
| `frontend_new_design_prototype/` is imported | Stop. Remove import. Prototype is reference-only |
| Monolith file grows beyond 300 lines | Stop. File a split story before adding more code |
| A story is marked Done without evidence | Revert status. Add evidence first |
| A bug is fixed without a bug ticket | Revert fix. File ticket first |

---

## Cluster Sequence

| Cluster | Focus | Prerequisite | Story count |
|---------|-------|-------------|------------|
| 0 | Governance | None | 8 stories |
| 1 | Backend event/command seams | Cluster 0 complete | 10 stories |
| 2 | Frontend transport/state/interaction modes | Cluster 1 Done | TBD |
| 3 | Frontend component wiring | Cluster 2 Done | TBD |
| 4 | Local browser E2E smoke | Cluster 3 Done | TBD |

Do not begin Cluster 2 until Cluster 1 is fully Done with evidence.
Do not begin Cluster 3 until Cluster 2 is fully Done with evidence.
Do not begin Cluster 4 (E2E) until Cluster 3 is fully Done.

---

## Implementation Boundaries

This is a documentation/protocol story. No product code is created.

---

## Allowed Files

- `.tasks-md/Planning/S7-0008-Cluster-execution-protocol-and-stop-conditions.md` (this file)

---

## Forbidden Files

- No product code changes

---

## Acceptance Criteria

- [ ] Per-story protocol has 8 steps with clear actions and commands
- [ ] Post-cluster protocol is defined
- [ ] Cross-cluster blocker protocol is defined
- [ ] Stop conditions table covers all Sprint 7 governance rules
- [ ] Cluster sequence is clear with prerequisites
- [ ] Protocol is referenced in Cluster 1 sprint doc

---

## Evidence Required

- [ ] This file committed to `.tasks-md/Planning/`

---

## Stop Conditions

- Protocol is not followed for a story — revert commits and follow protocol before re-committing
- A cluster is declared Done without the final regression run being recorded — revert Done status
