# Sprint 6 Cluster 10 — Frontend Complete LLM Mode UI

**Sprint:** Sprint 6  
**Cluster:** 10 (Frontend Complete LLM Mode UI)  
**Depends on:** Cluster 1-9 (all prior layers, especially 9)  
**Release gate:** Completion + 95% module coverage + regression pass  

---

## Cluster goal

Complete the frontend user experience for the full Complete LLM Mode.

The frontend must make the product understandable, debuggable, and predictable while preserving:

```
Backend decides.
Frontend renders typed backend truth and collects user input.
LLM thinks and proposes.
```

The frontend spec requires five main tabs:

```
LLM | Steps | Recorded | Code | Trace
```

It also requires support for free LLM workflow, scoped Steps workflow, plan review/correction, locator inspection/improvement, execution progress/recovery, recorded inspection, code review/export, and trace/debug investigation.

---

## Stories (12 total)

| ID | Title | Tier | Depends on | Blocks |
|----|-------|------|-----------|--------|
| S6-1001 | Shadow DOM host and product UI boundary | 1 | S6-0909 | S6-1002 |
| S6-1002 | Global shell: header, status, activity, footer | 1 | S6-1001 | S6-1003, S6-1004, S6-1005 |
| S6-1003 | LLM tab: chat, plan, clarification, permission, recovery cards | 1 | S6-1002 | S6-1012 |
| S6-1004 | Steps tab: scoped step builder and locator state | 1 | S6-1002 | S6-1012 |
| S6-1005 | Recommendation review UI | 1 | S6-1002 | S6-1012 |
| S6-1006 | Recorded tab: immutable evidence and repair/version display | 1 | S6-1002 | S6-1012 |
| S6-1007 | Code tab: generated spec, warnings, export/save | 1 | S6-1002 | S6-1012 |
| S6-1008 | Trace tab: event timeline and diagnostics | 1 | S6-1002 | S6-1012 |
| S6-1009 | Frontend typed event store completeness | 1 | S6-1002 | S6-1012 |
| S6-1010 | Frontend command dispatcher completeness | 1 | S6-1002 | S6-1012 |
| S6-1011 | Negative and edge UI states | 1 | S6-1002 | S6-1012 |
| S6-1012 | Cluster 10 frontend integration proof | 2 | S6-1003 through S6-1011 | (release gate) |

---

## Cluster Definition of Done

Cluster 10 is Done only when:

```
1. Shadow DOM host/product UI separation is complete.
2. Global shell reflects backend truth.
3. LLM tab handles plan, clarification, permission, recovery, discussion.
4. Steps tab supports scoped steps, expected outcome, locator state, dependency warnings.
5. Recommendation review UI exists.
6. Recorded tab shows immutable evidence/version state.
7. Code tab shows generated spec/code_update/warnings/export.
8. Trace tab shows timeline, LLM calls, locators, recovery, artifacts.
9. Event store covers Complete LLM Mode events.
10. Command dispatcher covers Complete LLM Mode actions.
11. Negative/edge UI states are visible and safe.
12. No frontend lifecycle inference.
13. 95% coverage exists for new/changed frontend modules where tooling supports it.
14. Sprint 6 regression guard passes.
```

---

## Cluster boundaries

### Allowed future implementation modules

```
frontend/src/host/
frontend/src/store/
frontend/src/components/llm/
frontend/src/components/steps/
frontend/src/components/recommendations/
frontend/src/components/recorded/
frontend/src/components/code/
frontend/src/components/trace/
frontend/src/commands/
frontend/src/events/
frontend/src/test-utils/
```

### Allowed thin orchestration only

```
agent.py (thin dispatch only)
server.py (thin event relay only)
browser.py (injector only)
runtime/event_contracts.py (no logic)
```

### Forbidden in Cluster 10

```
No frontend lifecycle inference.
No frontend-generated runtime truth.
No frontend-owned state that backend doesn't know about.
No broad agent.py refactor.
No hardcoded .DS_Store or AGENTS.md commits.
```

---

## Integration with Cluster 9

**Cluster 9 dependencies:**
- Save/load contracts (S6-0901, S6-0902)
- session_state restore (S6-0903)
- Replay result events (S6-0904, S6-0905)
- Repair/version events (S6-0906, S6-0907, S6-0908)

Cluster 10 frontend renders all Cluster 9 backend states and sends typed commands:

```
run / stop
answer clarification
permission decision
accept/remove/reorder recommendations
confirm plan
send correction
apply/reject diff
run selected/all steps
improve/revalidate locator
replay step/all
save/load
export/copy
```

---

## Test-first strategy

- **Unit tests:** component rendering, store updates, command dispatch, state transitions
- **Contract tests:** event→store mapping, command payloads, negative states
- **Integration tests:** end-to-end UI flows using fake/local fixtures
- **Regression tests:** existing frontend tests, Shadow DOM contract, E2E harness

Coverage target: **95% for new/changed frontend modules** where tooling supports it.

---

## Cheap E2E proof (S6-1012)

Required flows using local fixtures (no paid LLM/E2E):

```
1. session_state → global header + recorded/code state
2. page recommendation → recommendation card → accept subset
3. plan_ready → confirm/correction
4. recovery_needed → recovery card
5. locator_ambiguous → candidate choice
6. replay_result → Recorded tab status
7. runtime_rejected → error state
8. websocket disconnect/reconnect
```

---

## Milestones

| Phase | Gate | Condition |
|-------|------|-----------|
| Unit/Contract | Story-level | Each story tests pass, 95% coverage where applicable |
| Integration | Cluster gate | All 12 stories integrated, all tabs complete |
| Regression | Release gate | Full regression suite + Cluster 9 + S5-013 tests pass |

---

## Risk and mitigation

| Risk | Mitigation |
|------|-----------|
| Frontend guesses lifecycle state | Event store only; unknown events logged as diagnostic |
| Stale cache conflicts with load | session_state from backend; confirm reload |
| Disconnected UI shows fake state | Show "Reconnecting..." explicitly; block mutations |
| Ambiguity choice not sent to backend | Command required; dispatch blocks until backend accepts |
| Trace tab too noisy | Filters, folding, failure focus; no raw terminal |

