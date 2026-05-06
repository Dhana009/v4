# Skill: Refactor Safety

## Purpose
Safely refactor large fragile files without changing behavior accidentally.

## When to use
Use for agent.py modularization, frontend restructuring, runtime extraction, Shadow DOM migration, WebSocket/event refactors, LLM controller extraction, or test harness refactors.

## Source of truth
- PRD architecture rules
- Current approved specs
- Existing regression tests
- Current behavior evidence

## Non-negotiable rules
1. Do not combine broad refactor and feature work unless explicitly approved.
2. Move one subsystem at a time.
3. Add tests before extraction.
4. Preserve public events/commands unless changing a typed contract intentionally.
5. Preserve stable IDs and runtime behavior.
6. Do not delete fallback/legacy behavior unless explicitly scoped.
7. No sweeping rewrites.
8. Runtime variable safety check is required.
9. Do not turn a refactor into an architecture rewrite.

## Required implementation behavior
Before refactor:
- Identify subsystem boundaries.
- List files/functions/classes to move.
- Add or identify tests protecting behavior.
- Define allowed files and forbidden files.
- Define rollback/stop conditions.

During refactor:
- Extract without behavior change first.
- Keep adapter/shim if needed.
- Avoid changing schemas and logic simultaneously.
- Run focused tests after each extraction.

After refactor:
- Run focused tests.
- Run syntax/build checks.
- Compare event payloads if applicable.
- Report any behavior changes explicitly.

## Required tests
- Existing behavior regression tests must pass.
- Add import/smoke tests for new modules.
- Add contract tests when event/schema boundaries move.
- Add E2E only if user-visible flow can be affected.

## Verification commands
```bash
python -m py_compile <changed-python-files>
python -m pytest <focused-tests> -q
npm run build
```

## Stop conditions
Stop if:
- required evidence is missing, unclear, or contradictory
- behavior changes while extracting
- tests are insufficient to prove safety
- file dependencies are unclear
- circular imports appear
- refactor touches unrelated areas
- architecture conflict is discovered

## Reporting format
Report:
1. Subsystem extracted/refactored
2. Files changed
3. Behavior intentionally preserved/changed
4. Tests protecting behavior
5. Commands/results
6. New module boundaries
7. Risks/follow-ups
