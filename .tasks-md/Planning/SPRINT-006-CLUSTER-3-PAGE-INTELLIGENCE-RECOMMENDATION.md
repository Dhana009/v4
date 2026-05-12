# Sprint 6 Cluster 3 — Page Intelligence + Recommendation Mode

**Sprint:** Sprint 6  
**Cluster:** 3 (Page Intelligence + Recommendation Mode)  
**Depends on:** Cluster 1 (Purpose Coverage), Cluster 2 (Policy Enforcement)  
**Release gate:** Completion + 95% module coverage + regression pass  

---

## Cluster goal

Complete the **Page Intelligence and page/section recommendation layer**.

This cluster makes the system able to understand a page or selected section, summarize it compactly, identify sections/forms/CTAs/tables/ambiguities, and recommend useful test assertions/actions without immediately executing them.

The Runtime Policy says Page Intelligence prepares compact page/section context before the Main LLM sees it, and Main LLM should receive structured summaries, not raw DOM by default. 

The scenario spec says page/section validation recommendations are one of the strongest LLM Mode use cases: the user asks the agent to reduce thinking effort, not simply execute a known click.

---

## Stories (7 total)

| ID | Title | Tier | Depends on | Blocks |
|----|-------|------|-----------|--------|
| S6-0301 | Page Intelligence live invocation before planning | 1 | S6-0102 | S6-0302, S6-0303 |
| S6-0302 | Deterministic page/section extraction completeness | 1 | S6-0301 | S6-0303, S6-0304 |
| S6-0303 | Cheap-model page intelligence summarizer policy | 1 | S6-0302 | S6-0304, S6-0305 |
| S6-0304 | Page validation recommender schema and policy | 1 | S6-0303 | S6-0305, S6-0306 |
| S6-0305 | Recommendation review state and event contract | 1 | S6-0304 | S6-0306, S6-0307 |
| S6-0306 | Accepted recommendations become executable plan | 1 | S6-0305 | S6-0307 |
| S6-0307 | Page Intelligence and recommendation cheap E2E proof | 2 | S6-0306 | (release gate) |

---

## Cluster Definition of Done

Cluster 3 is Done only when:

```
1. Page Intelligence is live-invoked where needed before planning/recommendation.
2. Deterministic extraction produces bounded structured page/section context.
3. Cheap summarizer policy exists and fails safely.
4. Page validation recommender schema/policy exists.
5. Recommendation review event/state exists.
6. Accepted recommendations become backend-validated plan draft.
7. Unaccepted recommendations never execute.
8. No raw full DOM is sent by default.
9. S5-013 convergence behavior still passes.
10. 95% coverage exists for new/changed modules.
11. Regression guard passes.
```

---

## Cluster boundaries

### Allowed future implementation files

```
runtime/page_intelligence_live.py
runtime/page_extraction.py
runtime/page_validation_recommender.py
runtime/recommendation_contracts.py
tests/test_page_intelligence_live.py
tests/test_page_extraction.py
tests/test_page_validation_recommender.py
tests/test_recommendation_contracts.py
```

### Forbidden in Cluster 3

```
No broad agent.py refactor.
No frontend visual implementation.
No plan execution.
No browser-changing tools beyond inspection/locator verification.
No paid LLM calls for page intelligence unless explicitly approved.
No raw full DOM sent by default.
```

---

## Integration with downstream

**Cluster 4 dependencies:**
- Page Intelligence schema/contract (S6-0301, S6-0302, S6-0303)
- Recommendation contracts (S6-0305)
- Page-state model integration (downstream in S6-0406)

Cluster 4 journey/steps planning depends on Cluster 3 page/section intelligence and recommendation contracts.

---

## Test-first strategy

- **Unit tests:** extraction, schema validation, fallback behavior, state transitions
- **Contract tests:** schema compliance, tool filtering, telemetry format
- **Integration tests:** end-to-end flow using fake/local fixtures, no paid LLM
- **Regression tests:** existing convergence behavior, page intelligence schema tests

Coverage target: **95% for new/changed modules**.

---

## Cheap E2E proof (S6-0307)

Candidate flows using local fixtures (no paid LLM, no external website):

```
1. weak-divs page → recommendation mode → ambiguity shown
2. duplicate-profiles page → candidate ambiguity → ask user/recommendation review
3. data-table page → table/list recommendations grouped by row/section
4. modal-recovery page → dynamic UI risk identified
```

---

## Milestones

| Phase | Gate | Condition |
|-------|------|-----------|
| Unit/Contract | Story-level | Each story tests pass, 95% coverage |
| Integration | Cluster gate | All 7 stories integrated, convergence passes |
| Regression | Release gate | Full regression suite + S6 cluster 0 tests pass |

---

## Risk and mitigation

| Risk | Mitigation |
|------|-----------|
| Page extraction noise overloads LLM context | Bounded extraction + semantic quality score + fallback |
| Cheap summarizer fails frequently | Deterministic extraction fallback + L3 context limit |
| Ambiguous recommendations confuse user | Explicit ambiguity flags + user choice required |
| Full DOM still appears in context | Contract test validates no HTML in recommendation payload |

