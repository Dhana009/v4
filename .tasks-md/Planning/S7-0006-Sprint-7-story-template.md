# S7-0006 — Sprint 7 Story Template

**Sprint:** Sprint 7
**Cluster:** 0 (Governance)
**Type:** Documentation
**Status:** Planning
**Owner:** Process

---

## Objective

Define the mandatory story template for all Sprint 7 stories (Cluster 1–4). Every story handed to Claude Code must use this structure. Stories that do not follow this template are rejected before implementation begins.

---

## Source Rules

- Sprint 7 Cluster 0 Governance: Story lifecycle rules, test-first requirement, evidence requirements
- Sprint 6 S6-0005: Prior story template (baseline for this template)
- PRD `00_MASTER_INDEX.md`: "No source rule → no test. No test → no implementation."

---

## Current Known Context

Sprint 6 used a story template (S6-0005) that worked well but was not always enforced as a hard gate. Sprint 7 tightens this: the template is mandatory, and stories missing required sections are not started.

Key additions vs Sprint 6 template:
- Explicit `Source rules` with rule IDs (format: `PRD-04-BE-001`)
- Explicit `Current known context` (what exists in repo, what gaps exist, current test status)
- `Tests first` section split into: unit, contract, reducer/store, command dispatcher, integration, component, E2E, negative, regression
- Explicit `negative tests` subsection (required — no merge without them)
- `Implementation boundaries` section (what modules to touch and how)
- `Evidence required` as a checklist
- `Stop conditions` as an explicit list

---

## Tests First

This is a documentation/template story. No implementation tests required.

---

## The Sprint 7 Story Template

```markdown
# <STORY_ID> — <Title>

**Sprint:** Sprint 7
**Cluster:** <N>
**Tier:** <1 = core, 2 = supporting, 3 = polish>
**Type:** Feature / Refactor / Test / Documentation
**Status:** Planning
**Owner:** <Team or person>
**Blocks:** [other story IDs]
**Blocked by:** [other story IDs]

---

## Objective

1–3 sentences. What backend or frontend gap does this close?
What is broken/missing before this story? What works after?

---

## Source Rules

List every PRD rule and governance rule this story must satisfy.
Use the format: <RULE_ID>: <summary text>

Example:
- PRD-04-BE-001: run_started event must include run_id and steps[]
- PRD-03-FE-003: planning mode must be triggered by run_started event, not inferred
- GOV-S7-C0-007: No source rule → no test; no test → no implementation
- GOV-S7-C0-012: Code must remain modular; do not expand monoliths

---

## Current Known Context

### What exists in the repo
List specific files, functions, and existing test coverage relevant to this story.

Example:
- `runtime/event_contracts.py` has `build_backend_event_envelope()` but no `run_started` builder
- `SUPPORTED_FRONTEND_COMMAND_TYPES` set does not include `stop_run`
- `session_store.py` has in-memory save/load but no WS command wiring

### What gaps exist
Describe what is missing. Be specific.

### Current test status
What tests currently cover the area being modified?
What is the coverage percentage for affected modules?

---

## Tests First

### Unit Tests

List every unit test to write. Must reference source rule.

Format:
```
test_<function>_<scenario>()  # PRD-04-BE-001
```

File: `tests/test_<feature>_unit.py`

Minimum: 3 unit tests per new builder/validator function.

### Contract Tests

List every contract test.

Format:
```
test_<event_or_command>_contract_<scenario>()  # PRD-04-BE-001
```

File: `tests/test_<feature>_contract.py`

### Reducer/Store Tests (frontend stories)

List state reducer tests where applicable.

Format:
```
test_reducer_<event>_<scenario>()  # PRD-03-FE-003
```

### Command Dispatcher Tests (frontend stories)

List command dispatch tests where applicable.

### Integration Tests

List multi-module interaction tests.

Format:
```
test_integration_<flow>_<scenario>()  # PRD-04-BE-001
```

### Frontend Component Tests (Cluster 3 stories)

List component render tests.

Format:
```
test_<component>_renders_<event>_<scenario>()  # PRD-03-FE-003
```

### E2E Tests (Cluster 4 only)

List local E2E tests. Leave blank for Cluster 0–3 stories.

### Negative Tests (required — no merge without these)

List every negative/invalid scenario test.

Format:
```
test_<feature>_rejects_<invalid_scenario>()  # GOV-S7-C0-004
```

Minimum: 2 negative tests per new event builder or command handler.

### Regression Tests

Which existing test files must still pass after this story?
Run: `python -m pytest tests/<relevant_files> -q`

---

## Implementation Boundaries

Describe what modules to touch and how. Follow S7-0005 modular frontend policy.

### Allowed files

List every file that may be modified or created.

```
- runtime/event_contracts.py (add build_run_started_payload function only)
- tests/test_run_started_event_contract.py (new)
```

No other files may be touched. If a fix requires a different file, stop and file a new story.

### Forbidden files

List files that must NOT be touched.

```
- frontend/ (no UI changes in this story)
- agent.py (no broad refactor — only thin event emission seam)
- server.py (no broad refactor — only command routing seam)
- aw-ide-panel.jsx (not in Cluster 1 scope)
- tests/test_sprint6_*.py (do not modify Sprint 6 tests)
```

---

## Implementation Notes

### Approach

3–5 bullet points describing the implementation strategy.

1. Create builder function in `runtime/event_contracts.py`
2. Add to `SUPPORTED_FRONTEND_COMMAND_TYPES` if a new command type
3. Wire emission point in `agent.py` at the thinnest possible seam
4. Do not add any other logic to the same function

### Key invariants

What must be true after implementation?

### Known risks

What could go wrong? How is it mitigated?

---

## Coverage Requirement

Minimum 95% line coverage for new modules.

```bash
python -m pytest tests/<story_test_file>.py --cov=<module_path> --cov-fail-under=95
```

---

## Validation Commands

Commands to run locally after implementation.

```bash
# Unit + contract tests
python -m pytest tests/<story_test_file>.py -v

# Regression guard
python -m pytest -q --ignore=tests/e2e 2>&1 | tail -5

# Coverage check
python -m pytest tests/<story_test_file>.py --cov=<module> --cov-fail-under=95
```

---

## Acceptance Criteria

- [ ] All tests pass (unit, contract, integration, negative)
- [ ] No new failures in regression guard
- [ ] Coverage ≥ 95% for new modules
- [ ] No forbidden files modified
- [ ] Evidence committed and linked

---

## Evidence Required

- [ ] Implementation file(s) committed
- [ ] Test file(s) committed
- [ ] All tests pass — output pasted or file attached
- [ ] Regression guard passes — output pasted
- [ ] Coverage ≥ 95% — output pasted
- [ ] Story status updated to Done

---

## Stop Conditions

When to halt and ask for clarification:

- Cannot determine which module owns the new logic without touching a monolith
- Tests reveal an architecture conflict with a PRD invariant
- Coverage falls below 95% and root cause is not clear
- Regression guard fails with a new failure
- Implementation requires forbidden files
- A bug is found that cannot be fixed within this story's scope — file a bug ticket first
```

---

## Usage

For each Sprint 7 story in Cluster 1–4:

1. Copy the template above.
2. Fill in all sections completely before handing to Claude Code.
3. Source rules section must have real rule IDs, not placeholder text.
4. Tests first section must list specific test function names.
5. Implementation boundaries must list specific file names.

Example handoff:

```
Task: Implement S7-0101 run_started event contract

Story file: .tasks-md/Planning/S7-0101-run-started-event-contract.md

Template check:
  - Source rules: 2 PRD references ✓
  - Tests first: 8 tests listed ✓
  - Negative tests: 3 tests listed ✓
  - Allowed files: 2 files ✓
  - Forbidden files: listed ✓
  - Acceptance criteria: 5 items ✓

Do not:
  - Add features beyond the story scope
  - Touch forbidden files
  - Proceed if coverage < 95%
  - Call paid LLM
  - Begin frontend wiring (Cluster 2 scope)
```

---

## Implementation Boundaries

This is a documentation/template story. No product code is created.

---

## Allowed Files

- `.tasks-md/Planning/S7-0006-Sprint-7-story-template.md` (this file)

---

## Forbidden Files

- No product code changes

---

## Acceptance Criteria

- [ ] Template covers all required sections (objective, source rules, context, tests, implementation boundaries, evidence, stop conditions)
- [ ] Negative tests subsection is explicitly required
- [ ] Allowed and forbidden files sections are required
- [ ] Template is more specific than S6-0005 baseline
- [ ] All Sprint 7 Cluster 1–4 story files use this structure

---

## Evidence Required

- [ ] This file committed to `.tasks-md/Planning/`

---

## Stop Conditions

- A Cluster 1–4 story is handed for implementation without following this template — reject and return for template completion first
