# S7-1101 — Final Requirement Matrix Update

**Sprint:** Sprint 7
**Cluster:** 11
**Tier:** 1 (core)
**Type:** Documentation
**Status:** Planning
**Blocks:** [S7-1106, S7-1107]
**Blocked by:** [All Clusters 1–10]

---

## Objective

Create final Sprint 7 requirement matrix classifying every requirement from PRD v2.3 as Done, Partial, Deferred, Pending, Blocked, or Missing Evidence. Every Done row must cite implementation and test evidence. No fake Done.

---

## Source Rules

- PRD v2.3: All product requirements
- GOV-S7-C0-007: No source rule → no test; every requirement must be testable
- GOV-S7-C11-001 (Cluster 11): Honest status required; no fake Done; evidence required

---

## Current Known Context

- Sprint 6 final matrix exists (SPRINT-006-HANDOFF.md)
- Sprint 7 Clusters 1–10 implement specific requirements
- Each cluster resolves some requirements fully, defers others
- BUG-S6-FINAL-002 (frontend not implemented) resolved by Clusters 3–9

---

## Tests First

```python
# No implementation tests for this documentation task
# Validation is manual audit:

def validate_requirement_matrix():
  for each row in final_matrix:
    if row.status == "Done":
      assert row.evidence_commit exists
      assert row.evidence_test_file exists
      assert row.test_passing == True
    elif row.status == "Partial":
      assert row.gaps_documented == True
      assert row.sprint_8_ticket exists
    elif row.status in ["Deferred", "Pending"]:
      assert row.rationale_documented == True
    else:
      assert False, "Unknown status"
```

---

## Matrix Structure

```csv
Requirement ID,PRD Section,Requirement Text,Status,Evidence File,Test File,Commit Hash,Sprint 8/9 Ticket,Notes

PRD-03-FE-001,03_FRONTEND_RUNTIME,Shadow DOM docking,Done,frontend/src/components/...,tests/e2e/test_flow_*.py,<commit>,—,Docked right/left/top/bottom verified in E2E

...
```

---

## Acceptance Criteria

- [ ] All PRD v2.3 requirements listed
- [ ] Status classification complete (no TBD rows)
- [ ] Every Done row has commit + test evidence
- [ ] Every Partial row has Sprint 8 ticket reference
- [ ] Every Deferred row has rationale
- [ ] BUG-S6-FINAL-002 status clear (Done via implementation or explicitly superseded)

---

## Evidence Required

- [ ] Final requirement matrix (CSV or JSON)
- [ ] Matrix file committed to .tasks-md/Artifacts/C11/

---

## Stop Conditions

- > 10 requirements with "Missing evidence" (indicates incomplete implementation)
- BUG-S6-FINAL-002 unresolved and no supersession (blocker)
