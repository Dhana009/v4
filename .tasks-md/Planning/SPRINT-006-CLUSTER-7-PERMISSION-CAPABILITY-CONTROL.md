# SPRINT-006 CLUSTER-7 — Permission, Capability, Test Data, Auth, Human-in-loop

**Cluster ID**: 7  
**Cluster Name**: Permission, Capability, Test Data, Auth, Human-in-loop Control Layer  
**Sprint**: Sprint 6  
**Status**: Planning  
**Created**: 2026-05-12  

---

## Cluster Overview

Cluster 7 builds the control framework that decides:

```text
✓ Can this action run?
✓ Is it risky?
✓ Is required data available?
✓ Is this capability supported?
✓ Does the user need to provide permission/input?
✓ Should we proceed, ask, partially plan, or record a capability gap?
```

This is the permission/autonomy layer. Cluster 8 (recovery) depends on Cluster 7's classifications for recovery decisions.

---

## Execution Plan

### Phase 1: Foundation (Risk & Permission)
- S6-0702: Risk Classification Framework
- S6-0701: Permission/Autonomy Mode Contract

### Phase 2: Capability & Data Contract
- S6-0703: Capability Registry Framework
- S6-0704: Action and Assertion Capability Baseline
- S6-0705: Test Data Requirement Classification

### Phase 3: User-Facing Controls (Data, Auth, Human)
- S6-0706: Safe Generated Test Data Proposal Flow
- S6-0707: Sensitive Data Redaction Policy
- S6-0708: Auth/Login Precondition Handling
- S6-0709: Long-Running Async Result Strategy
- S6-0710: Human-In-Loop Flow

### Dependencies
```
           S6-0702
           /      \
      S6-0701   S6-0703
         |        /   \
      S6-0708  S6-0704  S6-0705
         |       |       /  \
      S6-0709   |    S6-0706 S6-0707
         |      |     /
      S6-0710--+----+
```

---

## Acceptance Criteria

Cluster 7 is Done when:

```text
✓ Permission modes (strict|balanced|auto) fully specified and tested
✓ Risk classification gates browser-changing/high-risk/destructive actions
✓ Capability registry covers actions, assertions, navigation, auth, files, tables
✓ Baseline action/assertion capability contracts complete (26 capabilities)
✓ Required test data detected before execution (15 classifications)
✓ Sensitive data redacted from prompts/logs/traces/artifacts
✓ Auth/login preconditions typed and safe (manual login, saved auth)
✓ Long-running result strategy with timeout and progress (S6-0709)
✓ Human-in-loop events pause/resume safely (OTP, captcha, manual login)
✓ Unsupported capability cannot fake success (capability_gap, not recorded)
✓ 95% coverage on new/changed modules
✓ Sprint 6 regression guard passes
```

---

## Story Summary

| ID | Title | Objective | Key Output |
|---|---|---|---|
| S6-0701 | Permission/Autonomy Mode Contract | Define strict/balanced/auto modes | Permission mode model + contract |
| S6-0702 | Risk Classification Framework | Classify actions into 6 risk tiers | Risk classifier with 6 levels |
| S6-0703 | Capability Registry Framework | Common capability contract | Registry schema + supported/unsupported logic |
| S6-0704 | Action/Assertion Baseline | 26 baseline capabilities | Registry entries for 9 actions + 17 assertions |
| S6-0705 | Test Data Classification | Detect required data (15 types) | Data classifier + 15 types |
| S6-0706 | Safe Generated Data Proposal | User-visible data generation | Proposal flow + deterministic templates |
| S6-0707 | Sensitive Data Redaction | Protect secrets across layers | Redaction policy + artifact redaction |
| S6-0708 | Auth/Login Precondition | Handle login/auth required | Auth detection + manual/saved options |
| S6-0709 | Long-Running Async Results | Support resume analysis, reports | Wait strategy + timeout + progress |
| S6-0710 | Human-In-Loop Flow | Support OTP, captcha, manual steps | Human input event + pause/resume |

---

## Constraints & Boundaries

### Allowed
```text
✓ New runtime modules (permission_policy, risk_classifier, capability_registry, etc.)
✓ Event contract definitions (S6-0001 matrix)
✓ Test infrastructure and fixtures
✓ Cheap validation (local tests, no paid LLM)
✓ S5 integration (controller wiring only, no S5 refactor)
```

### Forbidden
```text
✗ Broad agent.py refactor
✗ Frontend visual implementation
✗ Paid LLM or E2E testing
✗ Replay repair product flow
✗ Unvalidated recovery execution
✗ Fake recorded success for unsupported capability
✗ Code_update without backend evidence
✗ Raw DOM or unbounded prompting by default
✗ Secrets in prompts/logs/artifacts
✗ AGENTS.md/.DS_Store commits
```

---

## Integration Points

| Cluster | Integration | Notes |
|---------|-------------|-------|
| S5 | Controller wiring | Cluster 7 output feeds permission decisions |
| Cluster 8 | Recovery decisions | Recovery uses risk/test-data/capability classifications |
| S6-0001 | Test matrix | All events match requirement-to-test matrix |
| S6-0002 | Test taxonomy | Tests follow taxonomy: unit/contract/integration |

---

## Definition of Done Checklist

- [ ] All 10 stories specified and accepted
- [ ] Permission mode contract complete and tested
- [ ] Risk classifier 100% deterministic with 6 levels
- [ ] Capability registry covers all baseline capabilities
- [ ] Test data classifications comprehensive (15 types)
- [ ] Sensitive data redaction working across all layers
- [ ] Auth/login handling safe (manual + saved options)
- [ ] Long-running async with timeout + progress
- [ ] Human-in-loop pause/resume safe
- [ ] Unsupported capability → capability_gap (never fake success)
- [ ] 95% coverage on new modules
- [ ] Regression guard passing
- [ ] All story specifications documented
- [ ] No breaking changes to S5
- [ ] Ready for Cluster 8 (recovery)

---

## Next Steps

1. **Review & Approve**: Cluster 7 plan reviewed
2. **Implement Phase 1**: Risk + Permission foundation
3. **Implement Phase 2**: Capability + Data contract
4. **Implement Phase 3**: User-facing controls
5. **Validate**: 95% coverage + regression guard
6. **Sign Off**: Cluster 7 Done
7. **Begin Cluster 8**: Recovery, Failure, Execution Safety

---

## References

- Scenario spec: Complete LLM Mode with permission/autonomy tiers
- S6-0001: Requirement-to-Test Matrix
- S6-0002: Test Taxonomy
- S5 convergence: Page intelligence + planning validation
