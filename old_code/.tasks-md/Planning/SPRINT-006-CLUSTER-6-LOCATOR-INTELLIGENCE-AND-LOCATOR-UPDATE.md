# Sprint 6 Cluster 6 — Locator Intelligence + Locator Update

**Sprint:** Sprint 6
**Cluster:** 6 (Locator Intelligence + Locator Update)
**Depends on:** Cluster 1 (Purpose Coverage), Cluster 2 (Policy Enforcement), Cluster 3 (Page Intelligence)
**Release gate:** All 8 stories Done + 95% module coverage + regression pass (Clusters 0–5)

---

## Cluster goal

Make locator resolution **deterministic-first, LLM-last, always backend-validated**, and make every produced locator **updatable** with full context preservation. The locator specialist receives a tiny focused packet (never the raw DOM, never action tools), and every suggestion is backend-validated before activation. User-requested updates and wrong-page updates have explicit, typed flows.

---

## Source docs

- `autoworkbench_complete_llm_mode_runtime_policy_spec.md` — locator strategy priority, scoping/chaining, weak-DOM classification, locator specialist contract, validation, update flow
- `autoworkbench_complete_llm_mode_p_0_scenarios_spec (2).md` — P0 scenarios: ambiguous element, user "use the one in dialog", wrong page during update
- `autoworkbench_complete_llm_mode_frontend_ui_spec.md` — locator status surface, ambiguity candidate chooser, update affordance
- PRD locator policy + replay/repair preconditions

---

## Architecture invariants

1. **Deterministic first.** If a deterministic candidate validates `matched_count == 1`, LLM is not called.
2. **Duplicate resolution before LLM.** Try scoping/chaining (filter/has/hasText/role+name within container) before specialist.
3. **Weak-DOM classification produces candidates, not truth.** Output is marked "requires live validation".
4. **Locator ambiguity is a typed user-visible state.** Execution blocks until user chooses a candidate.
5. **Specialist gets a focused packet only.** No raw full DOM. No browser/action tools.
6. **Every LLM-suggested locator is backend-validated before activation.** Activation requires live `matched_count == 1`.
7. **Every operation stores locator context** for update / replay / repair.
8. **User-requested update preserves old locator in `update_history`.**
9. **Wrong-page update triggers a precondition flow.** Strict mode requires explicit user choice; relaxed mode auto-selects a safe option; no silent navigation.
10. **No unvalidated locator activation. No silent `nth(index)`** — `nth` is fragile and requires explicit user approval.

---

## Stories

| ID | Title | Tier | Depends on | Blocks |
|----|-------|------|------------|--------|
| S6-0601 | Deterministic locator candidate pipeline | 1 | Cluster 3 | S6-0602, S6-0604 |
| S6-0602 | Duplicate locator scoping and chaining | 1 | S6-0601 | S6-0604 |
| S6-0603 | Weak DOM semantic classification path | 1 | S6-0601 | S6-0605 |
| S6-0604 | Locator ambiguity candidate choice contract | 1 | S6-0602 | S6-0606 |
| S6-0605 | Locator specialist focused packet and schema | 1 | S6-0603 | S6-0606 |
| S6-0606 | Per operation locator context persistence | 1 | S6-0604, S6-0605 | S6-0607, S6-0608 |
| S6-0607 | User requested locator update flow | 1 | S6-0606 | S6-0608 |
| S6-0608 | Wrong page locator update precondition flow | 1 | S6-0607 | (release gate) |

---

## Dependency / sequence notes

- 0601 establishes the deterministic candidate ranking; 0602 layers scoping/chaining on top.
- 0603 covers weak DOM classification — distinct path from 0601/0602.
- 0604 surfaces ambiguity to the user as a typed state.
- 0605 defines the specialist packet/schema; depends on 0603 because weak-DOM classification is a precondition for specialist invocation.
- 0606 persists context per operation; everything downstream uses it.
- 0607 is the user-requested update flow.
- 0608 is the wrong-page precondition flow that wraps update.

---

## Allowed future implementation files

```
runtime/locator_deterministic.py        # strategy priority + ranking + early stop
runtime/locator_scoping.py              # container scoping + chaining + nth fragility
runtime/locator_weak_dom.py             # semantic classification heuristics
runtime/locator_ambiguity.py            # ambiguous state, candidate IDs, user selection
runtime/locator_specialist_packet.py    # focused packet builder + tool filter
runtime/locator_specialist_schema.py    # LocatorAlternative schema + validator
runtime/locator_context.py              # LocatorContext dataclass + persistence
runtime/locator_update_flow.py          # improve_locator flow
runtime/locator_wrong_page_flow.py      # precondition flow for updates
tests/test_locator_deterministic.py
tests/test_locator_scoping.py
tests/test_locator_weak_dom.py
tests/test_locator_ambiguity.py
tests/test_locator_specialist_packet.py
tests/test_locator_specialist_schema.py
tests/test_locator_context.py
tests/test_locator_update_flow.py
tests/test_locator_wrong_page_flow.py
tests/test_cluster6_integration.py
```

---

## Forbidden files / actions

- Broad `agent.py` refactor (narrow dispatch hooks only)
- Broad `server.py` refactor
- `AGENTS.md` commit from this cluster
- `.DS_Store` commit
- Paid LLM in tests
- Paid browser E2E
- Raw full-DOM injection into specialist prompts
- Unvalidated locator activation
- Silent `nth(index)` usage
- Specialist invocation of action/click/fill tools

---

## Tests-first policy

Every story lists Unit / Contract / Integration / Negative / Regression cases before implementation. S6-0606 onwards depend on persisted `LocatorContext`; tests cover serialization and secret exclusion.

---

## Coverage requirement

**95% line + branch coverage** on every new/changed module listed under "Allowed future implementation files".

---

## Regression guard

Each story must keep these green:

- Cluster 0 governance
- Cluster 1 purpose policy
- Cluster 2 enforcement (schema retry, fail-closed, tool exposure, token budget)
- Cluster 3 page intelligence + recommendation
- Cluster 4 journey planner / steps / precondition
- Cluster 5 plan discussion / correction / direct edit
- S5-013 convergence narrowing

---

## Definition of Done

- [ ] Deterministic candidate pipeline ranks strategies by stability
- [ ] Scoping/chaining resolves duplicates before any LLM call
- [ ] Weak-DOM classification produces candidates marked "requires live validation"
- [ ] Ambiguity is a typed user-facing state with stable candidate IDs
- [ ] Specialist packet is <1000 tokens, no raw DOM, no action tools
- [ ] Every LLM suggestion is backend-validated to `matched_count == 1` before activation
- [ ] `LocatorContext` is persisted per operation and is secret-safe
- [ ] User-requested update preserves old locator in `update_history`
- [ ] Wrong-page update emits `precondition_failed_for_locator_update` with typed options
- [ ] No silent `nth(index)` activation
- [ ] 95% coverage on each module
- [ ] Regression guard passes

---

## Stop conditions

- Deterministic strategy priority disputed → freeze on the ordering in S6-0601 and defer changes
- Scoping container set disputed → freeze on the 7 listed in S6-0602
- Weak-DOM signal set disputed → freeze on the signals listed in S6-0603
- Specialist packet exceeds budget → tighten section/page summary; never include raw DOM
- Live validation impossible (page navigated mid-update) → enter wrong-page flow (S6-0608)
- Regression breaks → stop and triage

---

## Evidence requirements

- [ ] All 8 stories filed under `.tasks-md/Planning/` with `S6-060N` filenames
- [ ] Each story passes the template checklist (Source rules, Tests first, Forbidden, Coverage, Stop conditions, Sign-off)
- [ ] Cluster integration spot-checks (where present in individual stories) use fakes only
- [ ] Update to `.tasks-md/Testing/S6-REGRESSION-GUARD.md` planned (not executed)
