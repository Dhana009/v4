# S6-0005 Sprint 6 story template

**Sprint:** Sprint 6  
**Cluster:** 0 (Governance)  
**Type:** Documentation  
**Status:** Planning  
**Owner:** Process  

---

## Purpose

Every Sprint 6 story must follow a strict template. This prevents vague stories, ensures tests come first, and makes hand-offs to Claude Code explicit.

---

## The Template

Copy and fill in this structure for every future Sprint 6 story:

```markdown
# <STORY_ID> <Title>

## Metadata

**Sprint:** Sprint 6  
**Cluster:** <N>  
**Tier:** <1 = core, 2 = supporting, 3 = polish>  
**Type:** Feature / Refactor / Test / Documentation  
**Status:** Planning / In Progress / Done  
**Owner:** <Team or person>  
**Blocks:** [other story IDs]  
**Blocked by:** [other story IDs]  

---

## Purpose (1–3 sentences)

What user problem does this solve? What architecture gap does it close?

---

## Source rules

List the PRD requirements, governance rules, and architectural invariants this story must satisfy.

Example:
- PRD 02-LLM-001: Purpose-specific prompt packs must be isolated and independently testable
- PRD 05-REC-002: Recorded step must capture all required fields for replay
- Modularization rule: New feature logic goes in focused module, not agent.py
- Coverage requirement: New code must reach 95% coverage

---

## Current evidence

### What exists in the repo

List specific files, functions, tests that are relevant.

### What gaps exist

Clearly identify what's missing.

### Test status

Current unit/contract/E2E coverage for this feature.

---

## Desired behavior

### High-level expectation

What should the system do after this story? (3–5 bullet points)

### Interface changes

If this story modifies APIs, show before/after:

```python
# Before:
agent.run(steps)

# After:
agent.run(steps)
result = await agent.apply_page_intelligence(dom_html)  # New
```

### New files required

- `runtime/page_intelligence_live.py` — live trigger logic
- `tests/test_page_intelligence_live_contract.py` — contract tests

### Modified files

- `agent.py` — call new live trigger in planning loop
- `.tasks-md/Planning/S6-STORY-TEMPLATE.md` — update this file

### Behavior examples

Concrete before/after scenarios.

---

## Out of scope

Explicitly list what is NOT in this story.

Example:
- Do not implement journey planning (separate story)
- Do not refactor tool_registry (separate story)
- Do not build frontend UI (separate story)

---

## Allowed files

List exact files that may be modified/created.

Example:
- `runtime/page_intelligence_live.py` (new)
- `tests/test_page_intelligence_live_contract.py` (new)
- `agent.py` (modify only _call_step_plan_normalizer_controller)

---

## Forbidden files

Explicitly list what cannot be touched.

Example:
- ✗ server.py (no changes)
- ✗ frontend/ (no changes)
- ✗ recording/ (no changes)
- ✗ locator/ (no changes)
- ✗ Existing tests (no changes unless fixing broken tests)

---

## Tests first (required structure)

### Unit tests

List the unit tests to write.

Example:
- `test_build_page_intelligence_schema_returns_valid_schema()`
- `test_build_page_intelligence_schema_with_weak_dom_returns_weak_action()`

File: `tests/test_page_intelligence_schema.py` (or new file if needed)

### Contract tests

List contract tests (interface boundaries).

Example:
- `test_page_intelligence_live_invocation_injects_packet_into_planning_messages()`
- `test_page_intelligence_live_invocation_skips_when_no_weak_dom()`
- `test_page_intelligence_live_invocation_fails_gracefully_on_schema_error()`

File: `tests/test_page_intelligence_live_contract.py`

### Integration tests

Any integration tests needed (multi-module interaction without full E2E).

Example:
- (none for this story, already covered by contract)

### E2E tests (if needed)

Any new E2E tests (full flow with browser/LLM).

Example:
- (covered by existing S5-013 paid E2E, no new E2E required)

### Regression tests

How will this story be included in the regression guard?

Example:
- `tests/test_page_intelligence_live_contract.py` added to `S6-REGRESSION-GUARD.md`

---

## Implementation notes

### Approach

Describe the implementation strategy in 3–5 bullet points. Should sound modular and testable.

Example:
1. Create `runtime/page_intelligence_live.py` with `should_trigger_page_intelligence(dom_snapshot)` helper
2. Add check in `agent.py:_call_step_plan_normalizer_controller()` before planning
3. If weak DOM, call `build_page_intelligence_schema` + `schema_to_planner_context_message`
4. Inject packet as system message into LLM context
5. Log `[PAGE_INTELLIGENCE]` marker with recommended_action

### Key invariants

What must be true after implementation?

Example:
- Page Intelligence is never called for strong DOM (optimization)
- Packet injection is transparent: if schema fails, planning continues without packet
- All existing S5-013 convergence narrowing behavior is unchanged

### Known risks

What could go wrong? How is it mitigated?

Example:
- Risk: Page Intelligence packet is expensive token-wise
  Mitigation: Gate by DOM strength; skipped 80% of time
- Risk: Injection fails silently
  Mitigation: Log [PAGE_INTELLIGENCE] marker; tests verify injection

---

## Coverage requirement

Minimum 95% coverage for new modules.

Example:
```bash
python -m pytest tests/test_page_intelligence_live_contract.py --cov=runtime.page_intelligence_live --cov-fail-under=95
```

---

## Validation commands

Commands to run locally after implementation.

```bash
# Unit + contract tests
python -m pytest tests/test_page_intelligence_live_contract.py -q

# Regression guard (ensure nothing broke)
python -m pytest tests/test_planning_convergence_contract.py tests/test_llm_required_ambiguous_action_flow.py -q

# Coverage check
python -m pytest tests/test_page_intelligence_live_contract.py --cov=runtime.page_intelligence_live --cov-fail-under=95
```

---

## Artifact/evidence requirement

What evidence must be committed/reported?

Example:
- [ ] `runtime/page_intelligence_live.py` — implementation
- [ ] `tests/test_page_intelligence_live_contract.py` — test suite (8+ tests)
- [ ] Update `.tasks-md/Testing/S6-REGRESSION-GUARD.md` to add new test file
- [ ] Task board: mark story Done with evidence link
- [ ] Commit message references PRD section and test count

---

## Stop conditions

When to halt and ask for clarification.

Example:
- Cannot determine when Page Intelligence trigger should activate
- Page Intelligence packet causes regression in existing convergence tests
- Coverage below 95% (investigate root cause before lowering requirement)
- New feature requires changes to forbidden files

---

## Sign-off

- [ ] Story is specific and enforceable
- [ ] Tests are designed (not yet implemented)
- [ ] Modularization rules are followed
- [ ] No forbidden files are touched
- [ ] Coverage requirement is clear
- [ ] Stop conditions are listed
```

---

## Out of scope

- No product implementation yet (this story is template only)
- No test implementation yet
- No behavior changes

---

## Allowed files

- `.tasks-md/Planning/S6-STORY-TEMPLATE.md` (this file)

---

## Forbidden files

- No changes to product code

---

## Acceptance criteria

- [ ] Template covers all required sections
- [ ] Template is specific (not vague)
- [ ] Template enforces tests-first
- [ ] Template enforces modularization rules
- [ ] Template lists stop conditions
- [ ] Template can be copied and filled for each future story
- [ ] Future stories use this exact structure

---

## Usage

After Cluster 0 is approved:

1. Copy this template
2. Fill in sections for the next story
3. Review before implementation starts
4. Hand to Claude Code with this structure intact

Example handoff:

```
Task: Implement S6-0101 Page Intelligence Live Invocation

Story file: .tasks-md/Planning/S6-0101-Page-Intelligence-Live-Invocation.md

Expected structure:
  - Source rules (2–3 PRD references)
  - Current evidence (what exists)
  - Desired behavior (interface changes)
  - Tests first (8+ contract tests listed)
  - Implementation notes (modular approach)
  - Validation commands (3–5 commands)
  - Coverage requirement (95%)
  - Artifact requirements
  - Stop conditions

Do not:
  - Add features beyond the story scope
  - Change forbidden files
  - Proceed if coverage < 95%
  - Call paid LLM without approval
```

---

## Notes

This template enforces:

1. **Source traceability** — every story ties back to PRD
2. **Test-first** — tests are designed before code
3. **Modularity** — boundaries are explicit
4. **Verifiability** — acceptance is testable
5. **Safety** — stop conditions prevent drift
