# S6-1205: Controlled Paid Browser E2E Acceptance

## Objective

Run smallest paid browser E2E suite needed to prove Complete LLM Mode works with real LLM.

## Preconditions

- [ ] Cheap regression passes (S6-1202)
- [ ] Cheap local E2E passes (S6-1203)
- [ ] Real LLM contract probes pass or justified (S6-1204)
- [ ] Artifact bundle ready (S6-1104)
- [ ] Redaction report ready (S6-1105)

## Candidate Paid E2E Flows

1. Ambiguous weak DOM (ask user/candidate choice)
2. Page recommendation flow
3. Plan correction flow
4. Recovery flow
5. Replay repair flow

## Hard Stops

No artifact bundle, Unredacted secrets, LLM emits execution success, Browser action before confirmation, run_completed while recovery open, code_update before step_recorded, raw_response/tool-call invariant error, Unbounded thinking loop

## Constraints

- Smallest suite possible (5 flows)
- Real websites where safe
- Real LLM behavior
- All artifacts captured and redacted

## Notes

Paid E2E is gated. Cost bounded (5 flows, ~10-15 paid LLM calls). Hard stops prevent wasting budget.


---

## Audit note (2026-05-13)

Evidence missing; not moved to Done. Paid browser E2E not run (per sprint policy S6-0007 and audit instruction). Status: Pending paid E2E. Do not claim Complete LLM Mode fully accepted.
