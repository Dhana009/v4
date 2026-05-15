# S6-0008 Cluster execution protocol

**Sprint:** Sprint 6  
**Cluster:** 0 (Governance)  
**Type:** Documentation  
**Status:** Planning  
**Owner:** Process  

---

## Purpose

Define how each Sprint 6 cluster is executed. One cluster at a time. Test-first, implementation second. Clear review gates between clusters.

---

## The protocol

### Phase 1: Cluster approval (human)

```
1. Story files for Cluster N are reviewed.
2. All 8–10 stories in cluster have:
   - Clear source rules
   - Current evidence documented
   - Desired behavior specified
   - Tests-first structure
   - Modularization constraints
   - Stop conditions
3. Reviewer approves → Cluster N is ready
4. Cluster N is handed to Claude Code with explicit scope
```

### Phase 2: Story execution (Claude Code)

For each story in Cluster N:

```
1. Read the story file (source rules, evidence, desired behavior)
2. Design tests first (do not implement yet)
3. Review test design for completeness:
   - Unit tests
   - Contract tests
   - Integration tests (if needed)
   - E2E tests (if needed)
   - Regression coverage
4. Implement minimal code to pass tests
5. Run regression guard (all prior clusters must pass)
6. Check coverage (95% for new modules)
7. Commit with evidence (test count, coverage report)
8. Update task board: Story → Done
9. Report: implementation summary + test results
10. Stop if any stop condition triggered
```

### Phase 3: Cluster completion (human)

```
1. Claude Code reports Cluster N done
2. Review commits:
   - Test count matches expected
   - Coverage meets 95%
   - Regression guard passes
   - No forbidden files were touched
3. If regression guard fails, stop and debug before proceeding
4. If coverage <95%, investigate (do not lower requirement)
5. Approve Cluster N → Cluster N+1 can start
```

---

## Cluster handoff template

When giving a cluster to Claude Code, use this structure:

```markdown
# Cluster N Handoff

## Scope

This cluster implements:
- [List of 8–10 specific stories]
- Focused on: [Feature area]
- Does NOT include: [Explicitly list what's NOT in this cluster]

## Story files

All story files are in `.tasks-md/Planning/S6-<N>-<title>.md`

Required for each story:
- Source rules (PRD references)
- Current evidence (what exists)
- Desired behavior
- Test structure (tests designed first)
- Allowed files (explicit list)
- Forbidden files (explicit list)
- Stop conditions

## Execution rules

1. **Test-first**: Design all tests before implementing code.
2. **One story at a time**: Do not skip ahead or start multiple stories in parallel.
3. **Regression guard**: Run after each story. Must pass.
4. **Coverage**: 95% minimum for new modules. Investigate if below.
5. **Modularization**: Follow S6-MODULARIZATION-RULES.md.
6. **No forbidden files**: Do not touch files in "Forbidden" list.
7. **Commit often**: One commit per story.
8. **Report**: After each story, summarize test count and coverage.

## Stop conditions

Stop and ask for clarification if:
- A story's desired behavior is unclear
- Tests cannot be designed for a story
- Coverage requirement cannot be met
- A forbidden file must be modified
- Regression guard fails and root cause unclear
- Multiple stories conflict or have unclear dependencies

## Validation commands

After each story:

```bash
# Run story-specific tests
python -m pytest tests/test_<feature>_*.py -q

# Run regression guard
python -m pytest tests/test_backend_event_sequences.py tests/test_planning_convergence_contract.py -q

# Check coverage
python -m pytest tests/test_<feature>_*.py --cov=runtime.<feature> --cov-fail-under=95 -q
```

## Deliverables per story

- [ ] Test file created with 8+ tests
- [ ] Implementation code committed
- [ ] Coverage ≥95%
- [ ] Regression guard passes
- [ ] Task board updated (story → Done)
- [ ] Commit includes test count and evidence

## Next cluster

After Cluster N is approved:
- [ ] No implementation gaps remain
- [ ] All regressions fixed
- [ ] Coverage verified
- [ ] Task board is current
- [ ] Ready for Cluster N+1

---

## After Cluster N done

1. Human reviews all commits
2. Human checks:
   - Regression guard passes ✓
   - Coverage ≥95% ✓
   - Story files are accurate ✓
   - No regressions vs prior clusters ✓
3. If all pass → Cluster N+1 ready
4. If any fail → Debug before proceeding
```

---

## Cluster sequence (recommended)

After Cluster 0 approval, proceed in this order:

```
Cluster 0 ✓ (governance & testing structure)
  ↓
Cluster 1 — LLM Runtime Purpose Coverage
  (expand from Sprint 5 LLM controller; add journey planner scaffolding)
  ↓
Cluster 2 — Context/Memory/Token/Tool/Schema Policy
  (comprehensive policy wiring)
  ↓
Cluster 3 — Page Intelligence Live Invocation
  (auto-trigger weak DOM; inject packet into planning)
  ↓
Cluster 4 — Journey Planner + Steps Mode
  (new flow type: multi-step planning)
  ↓
Cluster 5 — Plan Discussion/Correction/Editing
  (plan workflow: revision, editing, submission)
  ↓
Cluster 6 — Locator Intelligence + Locator Update
  (weak locator recovery; locator update flow)
  ↓
Cluster 7 — Permission/Capability/Feature Handling
  (gap logging; capability detection)
  ↓
Cluster 8 — Replay Repair + Save/Load/Versioning
  (persistence: replay repair, version save)
  ↓
Cluster 9 — Frontend Complete LLM UI
  (shadow DOM + docked layout + full LLM UI)
  ↓
Cluster 10 — Trace/Artifacts/Observability
  (backend logs; frontend trace panel)
  ↓
Cluster 11 — Final Complete LLM Mode Acceptance
  (E2E multi-flow; full scenario acceptance)
```

Each cluster is:
- 8–12 stories
- 1–2 weeks
- 1–3 new modules
- 95% coverage
- Full regression guard pass

---

## Multi-cluster dependencies

Some clusters depend on prior clusters:

```
Cluster 0 (governance) ← required by all
Cluster 1 (LLM runtime) ← required by 3, 4, 5
Cluster 2 (policies) ← required by 1, 3, 4
Cluster 3 (Page Intel) ← required by 4 (optional for journey planning)
Cluster 4 (journey) ← required by 5, 6
Cluster 5 (plan discussion) ← required by nothing new
Cluster 6 (locator) ← required by 8
Cluster 7 (gaps) ← required by 10
Cluster 8 (replay) ← required by 9, 10
Cluster 9 (frontend) ← required by 10, 11
Cluster 10 (trace) ← required by 11
Cluster 11 (acceptance) ← final gate
```

If a later cluster's dependencies are not done, it cannot start.

---

## When to pivot or stop

**Pivot to a different cluster if:**

- Current cluster is blocked on external dependency
- Unforeseen gap requires work in earlier cluster
- Regression cannot be fixed without broader refactor

**Stop and ask for guidance if:**

- Cluster scope becomes unclear (>20% growth)
- Multiple cluster dependencies are discovered
- Cost or timeline explodes
- Architecture assumption proves wrong
- Cannot achieve 95% coverage on new modules

---

## Out of scope

- No cluster execution yet (this story is template only)
- No specific stories implemented yet

---

## Allowed files

- `.tasks-md/Planning/S6-CLUSTER-EXECUTION-PROTOCOL.md` (this output)

---

## Forbidden files

- No changes to product code
- No test implementations
- No cluster stories implemented

---

## Acceptance criteria

- [ ] Protocol defines 3 phases (approval, execution, completion)
- [ ] Handoff template is specific and actionable
- [ ] Test-first requirement is enforced
- [ ] Regression guard is mandatory after each story
- [ ] Coverage requirement is non-negotiable
- [ ] Stop conditions are listed
- [ ] Cluster sequence is defined
- [ ] Dependencies are mapped
- [ ] Pivot/stop criteria are clear
- [ ] File is stored in `.tasks-md/Planning/S6-CLUSTER-EXECUTION-PROTOCOL.md`

---

## Validation

Before giving Cluster 1 to Claude Code, verify:

```bash
# All governance documents exist
ls -la .tasks-md/Planning/S6-000*.md
ls -la .tasks-md/Testing/S6-000*.md

# Cluster 1 stories are defined
ls -la .tasks-md/Planning/S6-1*.md  # Should have 8–10 files

# Regression guard can run
python -m pytest tests/test_backend_event_sequences.py tests/test_planning_convergence_contract.py -q
```

---

## Notes

- One cluster at a time
- No multi-cluster tasks
- Tests designed, then implemented, then verified
- Review happens between clusters
- No automatic continuation
