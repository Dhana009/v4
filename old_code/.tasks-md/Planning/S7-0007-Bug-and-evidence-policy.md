# S7-0007 — Bug and Evidence Policy

**Sprint:** Sprint 7
**Cluster:** 0 (Governance)
**Type:** Documentation
**Status:** Planning
**Owner:** Process

---

## Objective

Define the Sprint 7 bug ticket and evidence policy. No bug is fixed without a bug ticket. No story is marked Done without committed evidence. No fake Done.

---

## Source Rules

- Sprint 7 Cluster 0 Governance: "No bug fix without bug ticket. Evidence before assertions always."
- PRD `00_MASTER_INDEX.md`: "No Done without evidence."
- Sprint 6 HANDOFF: Pre-existing bugs BUG-S6-FINAL-001 and BUG-S6-FINAL-002 must not be silently closed

---

## Current Known Context

Sprint 6 established a Bugs directory at `.tasks-md/Bugs/`. Pre-existing bugs are:
- `BUG-S6-FINAL-001`: 12 model-class contract mismatch failures in cheap suite
- `BUG-S6-FINAL-002`: Frontend Complete LLM UI is contract-only

Sprint 6 governance required bug tickets but did not always enforce them rigorously. Sprint 7 makes this a hard gate.

---

## Tests First

This is a documentation/policy story. No implementation tests required.

---

## Bug Ticket Policy

### Rule 1: No Fix Without a Ticket

If a bug is discovered during Sprint 7 work:
1. Stop the current implementation.
2. Create a bug ticket at `.tasks-md/Bugs/Backlog/BUG-S7-<NNN>-<short-description>.md`.
3. If the bug is within the current story's scope and is a small, well-understood fix, note it in the bug ticket and proceed.
4. If the bug is outside the current story's scope or is large, the bug ticket goes to Backlog and implementation continues without fixing it.
5. Never commit a "fix" without a corresponding bug ticket.

### Rule 2: Bug Ticket Path Convention

```
.tasks-md/Bugs/Backlog/BUG-S7-<NNN>-<kebab-case-description>.md
```

Examples:
- `BUG-S7-001-run-started-missing-steps-field.md`
- `BUG-S7-002-stop-run-accepted-when-no-active-run.md`
- `BUG-S7-003-session-state-missing-plan-field-on-reconnect.md`

Sprint 7 bug numbering starts at 001. Pre-existing Sprint 6 bugs keep their `BUG-S6-` prefix and are NOT renumbered.

### Rule 3: Bug Ticket Required Fields

Every bug ticket must include:

```markdown
# BUG-S7-<NNN> — <Short description>

**Sprint:** Sprint 7
**Status:** Backlog / In Progress / Fixed
**Severity:** Critical / High / Medium / Low
**Source rule violated:** <PRD rule ID or governance rule ID>
**Discovered in:** <story ID or context>
**Blocks:** <story ID if blocking>

## Description

What is wrong? What should happen?

## Reproduction steps

1. Step 1
2. Step 2
3. Observed: <X>
4. Expected: <Y>

## Failing test

```python
def test_reproduces_bug():
    # paste failing test here
```

Or: "No test yet — must write before fixing."

## Fix plan

Brief description of the intended fix.

## Evidence required before closing

- [ ] Failing test committed (red)
- [ ] Fix committed
- [ ] Test passes (green)
- [ ] Regression suite still passes
- [ ] Bug ticket updated to Fixed
```

### Rule 4: Severity Definitions

| Severity | Definition |
|----------|-----------|
| Critical | Blocks the entire run flow, corrupts session state, or causes data loss |
| High | Breaks a required event or command seam; frontend cannot transition correctly |
| Medium | Missing or incomplete payload field; frontend degrades gracefully but is incomplete |
| Low | Cosmetic, non-blocking, or deferred to Sprint 8 |

### Rule 5: Pre-Existing Bug Handling

- **BUG-S6-FINAL-001** (12 model-class contract mismatches): Do not fix in Sprint 7 unless explicitly scheduled. Do not close. Do not hide by marking xfail. Track and report in Sprint 7 HANDOFF.
- **BUG-S6-FINAL-002** (Frontend contract-only): Sprint 7 Cluster 2–3 work is the planned resolution. Mark as Fixed only after real frontend source is committed and tested.
- Any other pre-existing bugs discovered during Sprint 7 work get a new BUG-S7 ticket referencing the pre-existing issue.

---

## Evidence Policy

### Rule 6: Evidence Before Done

No story, no bug fix, and no cluster is marked Done without committed evidence.

Evidence means ALL of the following:
- [ ] Implementation code committed (with story/bug ID in commit message)
- [ ] Test code committed (failing tests committed before implementation, passing tests committed after)
- [ ] Test output showing pass (paste the last few lines of pytest output or attach a file)
- [ ] Regression suite output showing no new failures
- [ ] Coverage output showing ≥ 95% for new modules (backend stories)
- [ ] Story file status updated from "In Progress" to "Done"
- [ ] Evidence section in story file populated with commit hashes or test output excerpts

### Rule 7: No Fake Done

The following do not count as Done:
- "Tests are passing" without showing the output
- "Coverage is fine" without running the command
- "Regression is green" without running the full suite
- Story status set to Done before evidence is committed
- Placeholders in acceptance criteria (`[ ] (TODO)`)
- Tests marked `@pytest.mark.skip` or `@pytest.mark.xfail` to hide failures
- Implementation committed without corresponding tests

### Rule 8: Story Evidence Format

At the bottom of every Done story, add an Evidence section:

```markdown
---

## Evidence (added when Done)

**Status:** Done
**Date:** YYYY-MM-DD
**Commit:** <git hash>

### Tests passing

```
pytest tests/<story_test_file>.py -v
... (paste last 10 lines)
```

### Regression suite

```
pytest -q --ignore=tests/e2e
1689 passed, 1 skipped, 12 failed (same 12 as BUG-S6-FINAL-001)
```

### Coverage

```
pytest tests/<story_test_file>.py --cov=<module> --cov-fail-under=95
... coverage: 97%
```
```

---

## Cluster Evidence Policy

Each cluster is complete only when:
- All stories in the cluster are Done with evidence
- Regression gate passes at or above Sprint 6 baseline
- Cluster sprint doc is updated with final status

---

## Implementation Boundaries

This is a documentation/policy story. No product code is created.

---

## Allowed Files

- `.tasks-md/Planning/S7-0007-Bug-and-evidence-policy.md` (this file)

---

## Forbidden Files

- No product code changes
- No changes to pre-existing bug tickets without explicit task

---

## Acceptance Criteria

- [ ] Bug ticket path convention is defined
- [ ] Required bug ticket fields are specified
- [ ] Severity definitions are clear
- [ ] Pre-existing Sprint 6 bugs are addressed (track, do not close)
- [ ] No Fake Done list is explicit
- [ ] Story evidence format is defined
- [ ] Cluster evidence policy is clear

---

## Evidence Required

- [ ] This file committed to `.tasks-md/Planning/`

---

## Stop Conditions

- A bug fix is committed without a bug ticket — revert and file the ticket first
- A story is marked Done without evidence — revert the status change
- BUG-S6-FINAL-001 or BUG-S6-FINAL-002 is closed without resolution evidence — reopen
