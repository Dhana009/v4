# S7-1105 — Browser E2E Smoke Evidence

**Sprint:** Sprint 7
**Cluster:** 11
**Tier:** 1 (core)
**Type:** Documentation
**Status:** Planning
**Blocks:** [S7-1106, S7-1107]
**Blocked by:** [S7-1010]

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
