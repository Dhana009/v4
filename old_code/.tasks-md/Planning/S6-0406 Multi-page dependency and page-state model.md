# S6-0406 Multi-page dependency and page-state model

**Sprint:** Sprint 6  
**Cluster:** 4 (Journey Planner + Steps Mode + Multi-step Flows)  
**Tier:** 1 (core)  
**Type:** Feature / Schema  
**Status:** Planning  
**Owner:** Page State Model  
**Blocks:** S6-0407  
**Blocked by:** S6-0405  

---

## Purpose

Make each step/operation carry page-state assumptions. Source_page_url, required_page_state, precondition, postcondition, expected_outcome, depends_on_step_ids, locator_scope, page_snapshot_ref/section_snapshot_ref. No full session restore, no replay repair, no raw snapshot dumping into prompts.

---

## Source rules

- Scenario spec: every step or operation that depends on page state must store enough page context for backend validation
- Multi-page workflows require tracking page state transitions
- Locator is only valid on specific page state
- Dependencies between steps must be explicit

---

## What it contains

```
- source_page_url
- required_page_state
- precondition
- postcondition
- expected_outcome
- depends_on_step_ids
- locator_scope
- page_snapshot_ref / section_snapshot_ref when available
```

---

## What it must NOT contain

```
- no full session restore
- no replay repair
- no raw snapshot dumping into prompts
```

---

## Tests first

### Unit tests

```
- navigation step creates postcondition
- later operation depends on prior page transition
- operation stores locator scope/page snapshot ref
```

### Contract tests

```
- page-dependent operation must have required_page_state
- missing page-state metadata blocks execution or asks clarification
```

### Integration tests

```
- multi-step plan correctly tracks page-state assumptions
```

Coverage: **95% for page_state_model module**

---

## Out of scope

- Do not implement session restore
- Do not implement replay repair
- Do not dump raw snapshots into LLM context

---

## Allowed files

```
runtime/page_state_model.py (new)
tests/test_page_state_model.py (new)
Minor edits to:
  - DraftPlanStep schema
  - step_plan_normalizer.py
```

---

## Forbidden files

- No session restore logic
- No replay repair logic
- No raw snapshot dumping

---

## Implementation notes

### Schema (in page_state_model.py)

```
PageStateRequirement:
  - url: optional string (expected URL)
  - title_contains: optional string
  - visible_elements: list[LocatorHint] (expected to be on page)
  - hidden_elements: list[LocatorHint] (expected to be off-page)
  - custom_state: optional dict (e.g., authentication state)

PageStateChange:
  - from_url: optional string
  - to_url: string (where we navigate)
  - state_changes: dict (what changed on the page)

OperationWithPageState:
  (extends DraftPlanStep)
  - source_page_url: string (where this operation starts)
  - required_page_state: PageStateRequirement (what must be true before)
  - postcondition: PageStateChange (what changes after)
  - depends_on_step_ids: list[string] (which prior steps this depends on)
  - locator_scope: string (CSS scope or landmark where locator is valid)
  - page_snapshot_ref: optional string (reference to page snapshot if captured)
  - section_snapshot_ref: optional string (reference to section snapshot)
```

### Approach

1. Create `runtime/page_state_model.py` with:
   - PageStateRequirement, PageStateChange, OperationWithPageState schema
   - `track_page_state(step_sequence)` → list[OperationWithPageState]
   - For each step in sequence:
     - Set source_page_url from prior postcondition
     - Set required_page_state (what must be true)
     - Set postcondition (what changes)
     - Track depends_on_step_ids (navigation, etc.)
     - Set locator_scope (if known)
   - Validate: postcondition of step N matches precondition of step N+1

2. Create `tests/test_page_state_model.py`:
   - Page-state tracking across steps
   - Dependency detection
   - Validation (precondition ↔ postcondition matching)

3. Update `step_plan_normalizer.py`:
   - Call `track_page_state()` after planning
   - Enrich DraftPlanStep with page-state metadata

### Key invariants

- Every step has source_page_url and required_page_state
- Postcondition of step N matches precondition of step N+1 (or warning)
- Dependencies are explicit (not inferred from URL)
- No raw DOM dumped (only references/snapshots)

---

## Validation commands

```bash
python -m pytest tests/test_page_state_model.py::test_page_state_tracking -v
python -m pytest tests/test_page_state_model.py::test_dependency_detection -v
python -m pytest tests/test_page_state_model.py::test_precondition_postcondition_matching -v
python -m pytest tests/test_page_state_model.py::test_validation -v
coverage run -m pytest tests/test_page_state_model.py
```

---

## Artifact/evidence requirement

- [ ] `runtime/page_state_model.py` created
- [ ] `tests/test_page_state_model.py` created
- [ ] PageStateRequirement/PageStateChange/OperationWithPageState defined
- [ ] Page-state tracking working
- [ ] Dependency detection working
- [ ] Validation enforced
- [ ] No raw snapshots dumped
- [ ] 95% coverage

---

## Stop conditions

- Snapshot format unclear (define in story)
- Dependency detection too complex (simplify to navigation + explicit depends_on)

---

## Sign-off

- [x] Story is specific (add page-state model)
- [x] Scope is bounded (schema/tracking, no restore/replay)
- [x] Tests are first
- [x] Blocks S6-0407 (precondition handling)
