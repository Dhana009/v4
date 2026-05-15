# SPRINT-006 CLUSTER-8 — Recovery, Failure Handling, Execution Safety

**Cluster ID**: 8  
**Cluster Name**: Recovery, Failure Handling, Execution Safety  
**Sprint**: Sprint 6  
**Status**: Planning  
**Created**: 2026-05-12  

---

## Cluster Overview

Cluster 8 completes the failure/recovery system for Complete LLM Mode.

The runtime must:

```text
classify failure
  → emit typed failure event
  → attach compact evidence
  → attempt deterministic recovery first
  → call LLM recovery only when needed
  → validate repair proposal
  → ask user if intent/risk changes
  → resume / skip / stop
  → record only after validated success
```

This depends on Cluster 7 (permission, risk, capability, test-data classifications).

---

## Execution Plan

### Phase 1: Failure Detection
- S6-0801: Failure Classification Pipeline

### Phase 2: Deterministic Recovery & Context
- S6-0802: Deterministic Recovery First
- S6-0803: Recovery Context Packet

### Phase 3: LLM Recovery & Lifecycle
- S6-0804: Recovery Diagnoser Repair Proposal Schema
- S6-0805: Recovery State Lifecycle

### Phase 4: Execution & User Guidance
- S6-0806: Resume Execution After Recovery
- S6-0807: Recovery User Guidance Flow

### Phase 5: Validation & Regression
- S6-0808: Recovery Cheap E2E Integration Proof
- S6-0809: Recovery Regression Guard and Architecture Drift Checks

### Dependencies
```
        S6-0801
          |
      S6-0802 S6-0803
        \    /
      S6-0804
        /   \
    S6-0805 S6-0806
        |     |
    S6-0807--+
        |
    S6-0808
        |
    S6-0809
```

---

## Failure Classification (18 Types)

```
locator_not_found
locator_matches_multiple
locator_wrong_target
assertion_timeout
assertion_text_mismatch
action_timeout
element_not_interactable
element_hidden
element_detached
navigation_timeout
page_state_mismatch
permission_required
test_data_missing
unsupported_capability
llm_schema_invalid
tool_contract_mismatch
websocket_disconnect
unknown_runtime_error
```

---

## Recovery Flow

```
Operation fails
  ↓
Classify failure (S6-0801)
  ↓
Deterministic recovery first (S6-0802)
  ├→ [SUCCESS] → Resume (S6-0806)
  └→ [FAIL] → Build context packet (S6-0803)
       ↓
     LLM recovery diagnoser (S6-0804)
       ├→ repair_proposal → Validate → Execute (S6-0806)
       ├→ ask_user → User clarification (S6-0807)
       ├→ capability_gap → Stop (no fake success)
       └→ stop → Terminal state
       ↓
     Update recovery state (S6-0805)
       ↓
     Resume or skip or stop
```

---

## Acceptance Criteria

Cluster 8 is Done when:

```text
✓ Failures classified into 18 distinct types
✓ Failure events include expected/actual/evidence/next-actions
✓ Deterministic recovery runs before LLM recovery
✓ Recovery packet is compact and excludes raw DOM/secrets
✓ recovery_diagnoser outputs are schema-bound and validated
✓ Recovery state blocks run_completed/recording/code_update until resolved
✓ Execution resumes from failed operation safely
✓ User recovery instruction is scoped and stale-safe
✓ Unsupported capability cannot become fake success
✓ Cheap/local recovery integration proof exists
✓ 95% coverage on new/changed modules
✓ Sprint 6 regression guard passes
```

---

## Story Summary

| ID | Title | Objective | Key Output |
|---|---|---|---|
| S6-0801 | Failure Classification | 18 error types | Failure classifier |
| S6-0802 | Deterministic Recovery | Try scroll/revalidate/wait first | Deterministic recovery logic |
| S6-0803 | Recovery Context Packet | Compact L4 packet for LLM | Recovery packet builder |
| S6-0804 | Recovery Proposal Schema | Bound recovery output | repair_proposal schema + validation |
| S6-0805 | Recovery State Lifecycle | Block completion until resolved | State machine + blocking |
| S6-0806 | Resume Execution | Safe resume from failed op | Resume executor + cursor |
| S6-0807 | User Guidance Flow | User repair instructions | Instruction classifier + scope validator |
| S6-0808 | Cheap E2E Proof | 4 recovery flows locally | Integration tests, no paid LLM |
| S6-0809 | Regression Guard | Prevent drift & regressions | Regression test suite |

---

## Key Design Principles

### Deterministic First
Deterministic recovery always runs before LLM recovery:
- Scroll into view
- Revalidate locator
- Stale-safe wait
- Regenerate candidates
- No LLM for 80% of cases

### Compact Evidence
Recovery packet fits L4 context budget (~20K tokens):
- Failure classification
- Expected vs actual
- Locator candidates (not full DOM)
- Tried deterministic attempts
- Artifact refs

### Schema-Bound Recovery
recovery_diagnoser output always one of four types:
- repair_proposal (validated before execution)
- ask_user (single clarification)
- capability_gap (no fake success)
- stop (terminal)

### State Blocking
Recovery state machine prevents partial results:
- run_completed blocked while recovery open
- Recording blocked until recovery resolved
- code_update blocked until repair validated
- No escape from recovery state

### User Control
User always has explicit escape routes:
- Repair proposal review before execution
- User guidance for ambiguous repairs
- Skip/stop at any point
- Scope validation (instruction stays scoped)

---

## Integration with Cluster 7

Cluster 8 uses Cluster 7 outputs:

| Cluster 7 Output | Cluster 8 Usage |
|---|---|
| Risk classification | Recovery decision (high-risk needs user input) |
| Capability registry | Unsupported → capability_gap, not recovery |
| Test data classification | Missing data → data_required, not recovery |
| Permission mode | Repair scoped by permission level |
| Redaction policy | Secrets redacted from recovery packet |

---

## Constraints & Boundaries

### Allowed
```text
✓ New runtime modules (failure_classifier, recovery logic, etc.)
✓ Event contracts and state machines
✓ Cheap E2E with local fixtures and fake LLM
✓ S5 integration (controller wiring, no S5 refactor)
✓ Regression test suite
```

### Forbidden
```text
✗ Broad agent.py refactor
✗ Frontend visual implementation
✗ Paid E2E or real LLM in this cluster
✗ Unvalidated recovery execution
✗ Fake recorded success for failures
✗ Code_update without backend evidence
✗ Raw DOM in recovery packet
✗ Secrets in prompts/logs/artifacts
✗ Infinite recovery loops
```

---

## Definition of Done Checklist

- [ ] All 9 stories specified and accepted
- [ ] Failure classification with 18 types complete
- [ ] Deterministic recovery proves >80% success rate
- [ ] Recovery packet builder compact and token-aware
- [ ] recovery_diagnoser contract fully specified
- [ ] State machine prevents partial results
- [ ] Resume from failed operation strict and safe
- [ ] User guidance scoped and fail-safe
- [ ] Cheap E2E covers 4 required recovery flows
- [ ] Regression guard prevents future regressions
- [ ] 95% coverage on new modules
- [ ] All stories documented with tests-first specs
- [ ] No breaking changes to S5 or Cluster 7
- [ ] Ready for paid E2E testing

---

## Next Steps

1. **Review & Approve**: Cluster 8 plan reviewed
2. **Implement Phase 1**: Failure classification
3. **Implement Phase 2**: Deterministic recovery + context
4. **Implement Phase 3**: LLM recovery + state
5. **Implement Phase 4**: Resume + user guidance
6. **Validate Phase**: Cheap E2E + regression
7. **Sign Off**: Cluster 8 Done
8. **Paid E2E**: External testing after regression passes

---

## References

- Scenario spec: Recovery, failure handling, and execution safety
- Cluster 7: Permission, capability, test-data classifications
- S6-0001: Requirement-to-Test Matrix
- S6-0002: Test Taxonomy
- S6-0202: Context Level Policy (L4 for recovery)
