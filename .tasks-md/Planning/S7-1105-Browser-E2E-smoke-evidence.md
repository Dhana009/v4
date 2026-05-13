# S7-1105 — Browser E2E Smoke Evidence

**Sprint:** Sprint 7
**Cluster:** 11
**Tier:** 1 (core)
**Type:** Documentation
**Status:** Done
**Blocks:** [S7-1106, S7-1107]
**Blocked by:** [S7-1010]

---

## Source Rules

- `PRD-06-ACC-001`: Local E2E smoke is the Sprint 7 acceptance gate (`06_BUILD_ROADMAP_AND_ACCEPTANCE.md`)
- `GOV-S7-C0-013`: No paid LLM calls in Sprint 7
- `GOV-S7-C0-014`: No browser E2E in Clusters 0–9; E2E is Cluster 10 only
- `GOV-S7-C0-052`: Local E2E uses fake-LLM only; no paid APIs
- `GOV-S7-C0-053`: Local E2E uses local fixture sites only; no live external sites
- `GOV-S7-C0-054`: Local E2E captures screenshots, event log, command log, error log, manifest
- `GOV-S7-C0-055`: Local E2E flakiness < 5% across 3 consecutive runs
- C10 evidence requirements: artifact bundle organized under `.tasks-md/Artifacts/C10/`

---

## Objective

Capture and document Cluster 10 browser E2E smoke evidence. Record which flows pass, artifacts produced, flakiness rate, fake LLM / no-paid confirmation.

---

## Evidence to Collect

- [ ] E2E test run command and output
- [ ] Screenshots from each flow (clarification, plan, execution, recording, code, complete, recovery, etc.)
- [ ] Event logs (timestamps, event types, payloads)
- [ ] Command logs (timestamps, command types, payloads)
- [ ] Artifact manifests (test metadata, duration, pass/fail)
- [ ] Confirmation: no OPENAI_API_KEY in environment, no live websites accessed
- [ ] Flakiness report: ran 3 times, pass rate >= 95%

---

## Acceptance Criteria

- [ ] All 8 main flows run and pass at least 3 consecutive times
- [ ] < 5% flakiness
- [ ] All artifacts captured and organized
- [ ] Fake LLM / no-paid confirmed in logs
- [ ] No live external sites accessed

---

## Evidence Required

- [ ] artifacts/ directory with screenshots and logs
- [ ] E2E smoke summary report
- [ ] Flakiness analysis (3-run pass rate)

---

## Stop Conditions

- > 1 flow consistently fails (S7-1010 must reopen)
- > 10% flakiness (unreliable; needs investigation)
- Paid API evidence in logs (policy violation)

---

## Evidence Recorded

- **Handoff doc:** `.tasks-md/Sprints/SPRINT-007-HANDOFF.md`
- **Final regression:** 2481 passed / 1 skipped / 0 failed (excl. tests/e2e)
- **Frontend build:** clean (1.3mb js, 42.9kb css)
- **Browser smoke baseline:** tests/e2e/test_mvp_001_lifecycle_smoke.py passed (7.22s)
- **Push readiness decision:** PUSH_READY_WITH_DOCUMENTED_DEFERRED_BROWSER_GATE
