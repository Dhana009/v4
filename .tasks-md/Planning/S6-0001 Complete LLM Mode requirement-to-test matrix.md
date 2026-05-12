# S6-0001 Complete LLM Mode requirement-to-test matrix

**Sprint:** Sprint 6  
**Cluster:** 0 (Governance)  
**Type:** Documentation  
**Status:** Planning  
**Owner:** Testing Architecture  

---

## Purpose

Map every Complete LLM Mode PRD requirement to the test layers that protect it. No implementation. Only governance and mapping.

---

## Source docs

- `PRD_v2_3_Modular_Pack_v2/02_LLM_RUNTIME.md` — LLM runtime, planning, correction, recovery
- `PRD_v2_3_Modular_Pack_v2/03_FRONTEND_RUNTIME.md` — UI, state rendering
- `PRD_v2_3_Modular_Pack_v2/04_BACKEND_EVENT_CONTRACT.md` — events/commands
- `PRD_v2_3_Modular_Pack_v2/05_CODEGEN_REPLAY_PERSISTENCE.md` — recording, replay, repair, save/load
- `autoworkbench_complete_llm_mode_p_0_scenarios_spec (2).md` — scenarios 1–11
- `PRD_v2_3_Modular_Pack_v2/06_BUILD_ROADMAP_AND_ACCEPTANCE.md` — phases 2–5, acceptance matrix

---

## Current evidence

### What exists

- Sprint 5 closure: 365 cheap tests pass, 1 paid E2E passes, all test files for S5 features exist.
- Test coverage: `test_planning_convergence_contract.py`, `test_page_intelligence_schema.py`, `test_recording_codegen_truth_contract.py`, `test_replay_one.py`, `test_skill_escalation_contract.py`, `test_tool_schema_filter.py`.
- Frontend tests: `test_frontend_plan_recovery_rendering.py`, `test_frontend_recorded_code_rendering.py`, `test_frontend_picker_candidate_ui.py`.
- Backend event tests: `test_backend_event_sequences.py`, `test_event_contract.py`, `test_event_sequence_contract.py`.

### What's missing

- No explicit matrix mapping requirements → test layers.
- No coverage inventory for Complete LLM Mode phases 2–5.
- No test-layer assignment for journey planning, multi-action sections, plan discussion, recovery flows, replay repair, save/load, frontend UI.

---

## Desired behavior

Output: `.tasks-md/Testing/S6-COMPLETE-LLM-MODE-TEST-MATRIX.md`

A matrix table with columns:

```
| Req ID | Source | Requirement | Architecture invariant | Unit test | Contract test | Integration test | E2E test | Paid LLM test | Regression risk | Owner | Current | Tests exist |
```

Example rows:

```
| 02-LLM-001 | 02_LLM_RUNTIME | Purpose-specific prompt packs | Prompt pack builder is isolated; context manager uses it | test_prompt_pack_builder.py | test_prompt_pack_safety_rules.py | None | None | None | low | LLM runtime | Done | Yes |

| 03-FE-004 | 03_FRONTEND_RUNTIME | Plan review UI renders plan_ready event | Frontend reads backend plan_ready; UI shows steps; confirm/reject buttons present | None | test_frontend_plan_recovery_rendering.py | None | E2E harness | None | medium | Frontend | Partial | Partial |

| 05-REC-002 | 05_CODEGEN_REPLAY | Replay one step | Recorded step payload has all required fields; replay_one() executes and returns result | test_recorded_step_model.py | test_snapshot_archive_contract.py | test_e2e_harness.py | test_replay_one.py | None | high | Recording | Partial | Yes |

| SCENARIO-006 | P0 Scenarios | Replay broken → LLM repair → new version | Replay failure invokes LLM repair; repaired step updates archive; version save works | None | None | test_recovery_through_fake_model.py | None | Yes | high | Replay+LLM | Missing | No |
```

The matrix must:

- Cover all requirements from PRD phases 2–5
- Distinguish Done/Partial/Missing
- Show test coverage per layer
- Reference actual test files
- Identify gaps

---

## Out of scope

- No code implementation.
- No new tests (other stories create tests).
- No behavior changes.
- No product feature work.

---

## Allowed files

- `.tasks-md/Testing/S6-COMPLETE-LLM-MODE-TEST-MATRIX.md` (output)

---

## Forbidden files

- No changes to `agent.py`, `server.py`, or runtime modules.
- No test file changes.

---

## Acceptance criteria

- [ ] Matrix covers all requirements from PRD phases 2–5 (at least 50+ requirements)
- [ ] Each requirement has at least one test layer assigned
- [ ] No requirement marked Done without test evidence
- [ ] Matrix cross-references existing test files
- [ ] Missing test requirements are clearly flagged
- [ ] Regression risk is documented per requirement
- [ ] Owner/layer is assigned per requirement
- [ ] Output is markdown table or structured JSON
- [ ] File is stored in `.tasks-md/Testing/`

---

## Validation command

After creation, check completeness:

```bash
# Rough count: expect 50+ requirements
grep "^|" .tasks-md/Testing/S6-COMPLETE-LLM-MODE-TEST-MATRIX.md | wc -l

# Spot-check a few tests exist
python -m pytest tests/test_planning_convergence_contract.py tests/test_replay_one.py tests/test_frontend_plan_recovery_rendering.py -q
```

---

## Stop conditions

- PRD requirements cannot be reliably enumerated
- Test files are missing or unclear
- Cannot map requirements to current test structure
