# FE-008 Picker and element candidate UI

**Type:** Story  
**Status:** Testing  
**Priority:** P0  
**Epic:** EPIC-005 Shadow DOM Frontend  
**Owner:** DEV-3 Shadow DOM Frontend + Typed Rendering  
**Assignee:** Unassigned  
**Story Points:** TBD  
**Readiness:** Frontend display/proposal slice accepted; backend/browser locator validation remains downstream  
**Dependencies:** FE-002, FE-003, DOM-002, DOM-005, DOM-009  
**Blocks:** locator/picker workflow, DOM E2E  
**Version:** Batch 06 v1  

---

## Product contribution

This story displays exact element and ancestor candidates so the user can choose correct target level when needed.

## Architecture decision

Fixed:

- picker UI displays candidates; backend validates final locator
- exact node is not automatically final target
- ancestor levels are visible
- update_locator command is typed and backend-validated
- frontend selection remains proposal-only and does not claim final locator truth

## Candidate UI contract

| Display item | Source |
|---|---|
| exact node | DOM-002 candidate |
| interactive ancestor | DOM-005 |
| card/row/form/dialog/section | DOM-005 |
| risk flags | DOM-002/DOM-003/DOM-004 |
| validation status | DOM-004 |
| update action | DOM-009 command |

## Test matrix

| Test ID | Layer | Scenario | Expected |
|---|---|---|---|
| FE008-U-001 | Unit | nested span candidate | ancestor options shown |
| FE008-U-002 | Unit | duplicate CTA | risk/ambiguity shown |
| FE008-U-003 | Unit | select candidate | update_locator/selection command |
| FE008-U-004 | Unit | hidden candidate | warning shown |
| FE008-I-001 | Integration | picker target levels | UI displays levels |

## Subtasks

- source-rule mapping
- DEV-2 DOM candidate contract inventory
- picker candidate payload/read-model expectations
- candidate list display expectations
- selected candidate proposal expectation
- negative cases: ambiguous, hidden, detached, missing scope, no candidates
- boundary cases: duplicate candidates, low confidence, unknown candidate type, missing evidence_ref
- rule: frontend selection is proposal-only, not final locator truth
- test-only slice
- narrow frontend implementation slice
- verification commands
- stop conditions

## Delivery notes

- Frontend picker/candidate slice is display/proposal only.
- Candidate metadata is surfaced from existing DOM payloads in the Shadow DOM pending-step editor.
- Stable hooks now label the candidate surface and candidate selector.
- Candidate warnings cover multiple/hidden/low-confidence/missing-evidence conditions without claiming final locator truth.
- Backend/browser validation remains required before locator activation.
- No backend/runtime/LLM/DOM changes were made for this slice.

## Verification

- Added: `tests/test_frontend_picker_candidate_ui.py`
- Focused suite: `tests/test_frontend_picker_candidate_ui.py tests/test_frontend_accessibility_focus.py tests/test_frontend_event_command_contract.py -q`
- Result: `25 passed`
- Build required if frontend source changes: `cd frontend && npm run build`
- Build result: passed
- Remaining dependency: backend/browser locator validation still owns final locator truth.

## Edge cases

- long ancestor list
- identical candidate labels
- code block candidate
- stale validation result

---

## Acceptance notes

- Frontend picker/candidate slice is complete and source-tested.
- Candidate rows and warnings are display/proposal only.
- Backend/browser validation still owns final locator truth and activation.
- The stable candidate hook is inside the Shadow DOM pending-step editor.
- No backend/runtime/LLM/DOM changes were made for this slice.

---

## Stop conditions

Stop if:

- frontend would infer lifecycle truth locally
- implementation targets legacy overlay as the new product architecture
- event/command contracts are missing or incompatible
- backend truth fields are not enough to render safely
- UI command would mutate runtime state directly
- current code requires broad rewrite before tests
- frontend test hooks cannot be defined
- Shadow DOM isolation conflicts with product page behavior

---

## Codex execution summary

Completed frontend slice:

- Tests added: `tests/test_frontend_picker_candidate_ui.py`
- Frontend implementation committed: candidate surface hooks, candidate metadata chips, and candidate warnings
- Build verified: `cd frontend && npm run build`
- Focused tests verified: `25 passed`
- Backend/browser locator validation remains the remaining dependency for activation and truth
