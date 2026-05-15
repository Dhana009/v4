# S6-0407 Wrong-current-page precondition flow

**Sprint:** Sprint 6  
**Cluster:** 4 (Journey Planner + Steps Mode + Multi-step Flows)  
**Tier:** 1 (core)  
**Type:** Feature  
**Status:** Planning  
**Owner:** Precondition Handling  
**Blocks:** S6-0408  
**Blocked by:** S6-0406  

---

## Purpose

Handle case where the browser is on the wrong page before execution. Precondition check before locator/action, precondition_failed event, and deterministic resolution options: navigate to expected URL, replay dependency steps, ask user to move manually, skip, or stop. No LLM call for deterministic mismatch, no silent navigation in strict mode, no execution on wrong page.

---

## Source rules

- Scenario spec: wrong current browser state must trigger precondition handling before locator/action
- Page-state model (S6-0406) provides required_page_state and depends_on_step_ids
- Deterministic mismatch should not call LLM (just navigate or ask)
- Strict mode requires user choice before navigation

---

## What it contains

```
- precondition check before locator/action
- precondition_failed event
- deterministic resolution options:
  - navigate to expected URL
  - replay dependency steps
  - ask user to move manually
  - skip
  - stop
```

---

## What it must NOT contain

```
- no LLM call for deterministic mismatch
- no silent navigation in strict mode
- no execution on wrong page
```

---

## Tests first

### Unit tests

```
- wrong URL/page emits precondition_failed
- strict mode requires user choice before navigation
- dependency chain option is generated
- LLM not called for deterministic mismatch
```

### Contract tests

```
- precondition_failed includes expected/current state and next actions
- execution is blocked until resolved
```

### Integration tests

```
- multi-step plan correctly checks preconditions
- wrong page triggers event/resolution flow
```

Coverage: **95% for precondition_checks module**

---

## Out of scope

- Do not implement replay repair
- Do not call LLM for deterministic mismatches
- Do not navigate without user choice in strict mode

---

## Allowed files

```
runtime/precondition_checks.py (new)
tests/test_precondition_checks.py (new)
Minor edits to:
  - agent.py (dispatch to precondition checker)
  - runtime/llm_runtime_controller.py (check before action)
```

---

## Forbidden files

- No replay repair logic
- No LLM integration for simple mismatch
- No silent navigation

---

## Implementation notes

### Schema (in precondition_checks.py)

```
PreconditionCheckResult:
  - is_satisfied: bool
  - expected_url: string
  - current_url: string
  - expected_state: PageStateRequirement
  - current_state: PageStateRequirement (inferred)
  - mismatch_reason: string

ResolutionOption:
  - type: enum (navigate / replay_steps / ask_user / skip / stop)
  - description: string
  - dependency_steps: optional list[str] (if replay_steps)

PreconditionFailedEvent:
  - operation_id: string
  - check_result: PreconditionCheckResult
  - resolution_options: list[ResolutionOption]
  - timestamp: ISO8601
```

### Approach

1. Create `runtime/precondition_checks.py` with:
   - `check_precondition(operation, current_state)` → PreconditionCheckResult
   - Compare current_url with expected URL
   - Compare current state with required_page_state
   - If mismatch, generate resolution options:
     - Navigate to expected URL (if straightforward)
     - Replay depends_on_step_ids (if dependencies exist)
     - Ask user to navigate manually
     - Skip this operation (if optional)
     - Stop execution
   - Return result + options

2. Create `tests/test_precondition_checks.py`:
   - URL mismatch detection
   - State mismatch detection
   - Resolution option generation
   - Dependency chain handling
   - Strict mode enforcement

3. Update `agent.py` or executor:
   - Before executing action, call `check_precondition()`
   - If failed, emit `precondition_failed` event
   - Wait for user choice
   - Execute chosen resolution

### Key invariants

- Precondition checked before action
- No execution if precondition fails
- No LLM call for deterministic mismatch
- User choice required in strict mode
- Resolution options are deterministic (no AI guessing)

---

## Validation commands

```bash
python -m pytest tests/test_precondition_checks.py::test_url_mismatch -v
python -m pytest tests/test_precondition_checks.py::test_state_mismatch -v
python -m pytest tests/test_precondition_checks.py::test_resolution_options -v
python -m pytest tests/test_precondition_checks.py::test_strict_mode -v
python -m pytest tests/test_precondition_checks.py::test_no_llm_call -v
coverage run -m pytest tests/test_precondition_checks.py
```

---

## Artifact/evidence requirement

- [ ] `runtime/precondition_checks.py` created
- [ ] `tests/test_precondition_checks.py` created
- [ ] PreconditionCheckResult and ResolutionOption defined
- [ ] URL/state mismatch detection working
- [ ] Resolution options generated
- [ ] Strict mode enforced
- [ ] No LLM call for deterministic mismatch
- [ ] 95% coverage

---

## Stop conditions

- Current page state inference unclear (simplify to URL + visible elements)
- Dependency replay concept too complex (defer to S6-0408)

---

## Sign-off

- [x] Story is specific (handle wrong-page preconditions)
- [x] Scope is bounded (check + resolve, no LLM, no replay)
- [x] Tests are first
- [x] Blocks S6-0408 (integration proof)
