# Sprint 6 Cluster 9 — Replay Repair, Save/Load, Session Restore, Versioning

**Sprint:** Sprint 6  
**Cluster:** 9 (Replay Repair, Save/Load, Session Restore, Versioning)  
**Depends on:** Cluster 1-8 (all prior layers)  
**Release gate:** Completion + 95% module coverage + regression pass  

---

## Cluster goal

Complete the post-recording product loop:

```
recorded flow
→ save session/spec
→ load later
→ replay one/all
→ replay failure classified
→ LLM repair specialist proposes repair diff
→ backend validates repair
→ recording/code updated
→ save new version
→ old history retained
```

This is not optional. The product workflow document says the complete product loop includes record flow, save session/spec, replay later, repair broken replay flows with LLM, validate fix, update recording, and save a new version.

---

## Stories (9 total)

| ID | Title | Tier | Depends on | Blocks |
|----|-------|------|-----------|--------|
| S6-0901 | Workspace save session/spec contract | 1 | S6-0408 | S6-0902 |
| S6-0902 | Load session and restore recorded state | 1 | S6-0901 | S6-0903 |
| S6-0903 | session_state reconnect restore | 1 | S6-0902 | S6-0904 |
| S6-0904 | Replay one/all backend product flow | 1 | S6-0903 | S6-0905 |
| S6-0905 | Replay failure classification and repair intake | 1 | S6-0904 | S6-0906 |
| S6-0906 | replay_repair_specialist controller path | 1 | S6-0905 | S6-0907 |
| S6-0907 | Backend-validated replay repair update | 1 | S6-0906 | S6-0908 |
| S6-0908 | Save repaired version and retain history | 1 | S6-0907 | S6-0909 |
| S6-0909 | Cluster 9 integration proof | 2 | S6-0908 | (release gate) |

---

## Cluster Definition of Done

Cluster 9 is Done only when:

```
1. Session/spec save uses workspace-relative paths.
2. Load session restores backend-owned recorded state.
3. session_state can restore frontend after reconnect/load.
4. replay_step / replay_operation / replay_all are backend-owned.
5. Replay failure is typed and evidence-backed.
6. replay_repair_specialist uses controller policy.
7. LLM repair produces diff, not direct mutation.
8. Backend validates repair before updating recording/code.
9. New repaired version can be saved.
10. Old locator/action/code history is retained.
11. 95% coverage exists for new/changed modules.
12. Sprint 6 regression guard passes.
```

---

## Cluster boundaries

### Allowed future implementation files

```
runtime/session_save_contracts.py
runtime/session_load_contracts.py
runtime/session_state_restore.py
runtime/replay_contracts.py
runtime/replay_failure_classifier.py
runtime/replay_repair_packet.py
runtime/replay_repair_flow.py
runtime/versioning_contracts.py
recording/replay.py
recording/versioning.py
recording/snapshot.py
tests/test_*.py for all above
```

### Forbidden in Cluster 9

```
No broad agent.py refactor.
No frontend UI implementation.
No replay repair mutation without backend validation.
No raw secret/session payloads in saved files.
No hardcoded user output paths.
No paid LLM/E2E unless explicitly approved.
```

---

## Integration with Cluster 8 and Cluster 10

**Cluster 8 dependencies:**
- Recording complete with code_update (S8 complete)
- Backend event contract (S8 complete)

**Cluster 10 dependencies:**
- Save/load contracts (S6-0901, S6-0902)
- session_state restore (S6-0903)
- Replay result events (S6-0904, S6-0905)
- Repair/version events (S6-0906, S6-0907, S6-0908)

Cluster 10 frontend renders backend Cluster 9 states and sends typed commands for replay/repair/save/load.

---

## Test-first strategy

- **Unit tests:** save/load, session state, replay classification, repair validation, versioning
- **Contract tests:** event envelopes, command payloads, schema compliance
- **Integration tests:** end-to-end save/load/replay/repair/version using fake/local fixtures
- **Regression tests:** existing recording, event contract, code_update, and recovery tests

Coverage target: **95% for new/changed modules**.

---

## Cheap E2E proof (S6-0909)

Required flows using local fixtures (no paid LLM/E2E):

```
1. record/save/load/replay one
2. replay all with ordered results
3. broken locator replay → repair → code_update
4. repaired session saved as new version
5. malformed load rejected safely
```

---

## Milestones

| Phase | Gate | Condition |
|-------|------|-----------|
| Unit/Contract | Story-level | Each story tests pass, 95% coverage |
| Integration | Cluster gate | All 9 stories integrated, replay/repair/version complete |
| Regression | Release gate | Full regression suite + Cluster 8 + S5-013 tests pass |

---

## Risk and mitigation

| Risk | Mitigation |
|------|-----------|
| Save overwrites unsaved work | Confirm before save, show save location |
| Load corrupts state | Validate session file, deep copy on load |
| Repair mutates without validation | Backend validation required before code_update |
| History lost after repair | Version metadata tracks old/new locator/action |
| Secrets in saved files | Redact before save, validate on load |

