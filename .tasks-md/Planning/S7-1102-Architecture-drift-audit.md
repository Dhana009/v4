# S7-1102 — Architecture Drift Audit

**Sprint:** Sprint 7
**Cluster:** 11
**Tier:** 1 (core)
**Type:** Documentation
**Status:** Planning
**Blocks:** [S7-1106, S7-1107]
**Blocked by:** [All Clusters 1–10]

---

## Objective

Audit final implementation against architecture invariants from Cluster 0 governance. Verify:
- Backend truth preserved; no frontend mutation
- LLM proposer only; no decision-making
- Frontend renders events/sends commands only
- No lifecycle inference
- Trace is evidence only
- Modular boundaries preserved
- No paid LLM in default path
- No static/demo runtime truth

---

## Source Rules

- GOV-S7-C0-045 through GOV-S7-C0-063: Non-negotiable invariants
- GOV-S7-C11-001: No drift; architecture audit required before push

---

## Tests First

```
Manual audit checklist:

1. Backend truth:
  - grep -r "recordedSteps" frontend/src/ → only from events, never mutation
  - grep -r "codePreview\s*=" frontend/src/ → only from code_update event
  - Step lifecycle: never marked complete before run_completed event
  - → PASS if no violations; FAIL if violations found

2. LLM proposer only:
  - LLM output never used to confirm execution
  - Backend validates all LLM suggestions
  - Step recording never inferred from LLM reasoning
  - → PASS; FAIL if violations

3. Frontend command only:
  - No direct backend mutations from frontend
  - All backend changes via typed commands
  - → PASS; FAIL if violations

4. No inference:
  - Frontend does not synthesize lifecycle state
  - Unknown states shown as unknown, not guessed
  - → PASS; FAIL if violations

5. Modular boundaries:
  - agent.py < 500 new lines (thin seam)
  - server.py < 300 new lines (thin seam)
  - main.jsx < 200 new lines (transport + dispatch)
  - aw-ide-panel.jsx < 100 new lines (prop threading)
  - → PASS if lines within budget; FAIL if lines exceeded

6. Paid LLM default path:
  - Default LLM mode uses fake/local
  - OpenAI key not required for dev
  - → PASS; FAIL if required
```

---

## Acceptance Criteria

- [ ] Backend truth check: no violations
- [ ] LLM proposer check: no violations
- [ ] Frontend rendering check: no violations
- [ ] No inference check: no violations
- [ ] Trace evidence check: no violations
- [ ] Modular boundaries: within budget
- [ ] No paid LLM default: PASS
- [ ] No demo runtime truth: PASS

---

## Evidence Required

- [ ] Drift audit report (text or checklist)
- [ ] Any violations documented with commits and rationale
- [ ] Report committed to .tasks-md/Artifacts/C11/

---

## Stop Conditions

- > 3 architecture violations found (must fix before push)
- Monoliths exceed size budget and no rationale (must refactor)
- Paid LLM required for default development path (policy violation)
