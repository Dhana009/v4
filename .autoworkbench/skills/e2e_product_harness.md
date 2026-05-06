# Skill: E2E Product Harness

## Purpose
Test AutoWorkbench as a real product: backend + browser + Shadow DOM UI + LLM/events + recording/code/trace.

## When to use
Use when creating or modifying browser-driven E2E tests, harness utilities, local fixture server, backend launcher, CDP attach, Shadow DOM selectors, artifact capture.

## Source of truth
- TDD/Regression Harness skill
- Frontend Shadow DOM UI spec
- Backend event contract
- Existing E2E harness findings

## Non-negotiable rules
1. E2E must interact with real UI, not a mocked UI host.
2. E2E must observe backend events/logs where needed.
3. E2E must fail fast at named stages.
4. No blind waits until timeout.
5. Capture artifacts on failure.
6. Use repo .env intentionally and redact secrets from logs.
7. Harness must support Shadow DOM selectors.
8. E2E should test product flow, not fixture page alone.
9. Do not let E2E harness logic become product behavior.

## Required implementation behavior
Harness should provide:
```text
fixture server
backend server launcher
browser/CDP attach if needed
Shadow DOM root locator helper
stage tracker
backend log polling
frontend console capture
screenshot/html/failure-context capture
artifact directory per run
```

## Required tests
- Harness unit tests
- Basic click flow
- Visible assertion flow
- Exact text assertion flow
- Correction flow
- Steps locator improvement flow
- Trace visibility flow
- Shadow DOM mount flow

## Verification commands
```bash
python -m pytest tests/test_e2e_harness.py -q
python -m pytest tests/e2e/<flow>.py -q -s
```

## Stop conditions
Stop if:
- required evidence is missing, unclear, or contradictory
- test waits without knowing current stage
- failure artifact is missing
- selector cannot access Shadow DOM
- backend startup/reconnect state is unclear
- E2E passes without validating recording/code/trace when required

## Reporting format
Report:
1. Harness changes
2. E2E flows added/updated
3. Commands/results
4. Last successful stage
5. Artifact paths
6. Remaining environment risks
