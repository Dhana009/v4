# S6-0002 Sprint 6 test strategy and test taxonomy

**Sprint:** Sprint 6  
**Cluster:** 0 (Governance)  
**Type:** Documentation  
**Status:** Planning  
**Owner:** Testing Architecture  

---

## Purpose

Define what each test layer means, when it is required, naming conventions, and folder structure. Establish a shared vocabulary for all Sprint 6 work.

---

## Source docs

- Existing test patterns in `tests/`
- Sprint 5 coverage (fake model, contract, E2E harness)
- `test_sprint5_llm_runtime_guardrails.py` — guardrail test example

---

## Current evidence

### Existing test patterns

- **Unit tests:** `test_skill_selector.py`, `test_telemetry_breakdown.py` — single function/class
- **Contract tests:** `test_planning_convergence_contract.py`, `test_tool_schema_filter.py` — interface boundaries
- **Integration tests:** `test_llm_runtime_controller_contract.py` — multiple modules
- **E2E tests:** `tests/e2e/test_basic_click_flow.py`, `test_llm_required_ambiguous_action_flow.py` — full flow with LLM
- **Regression tests:** `test_sprint5_llm_runtime_guardrails.py` — smoke suite
- **Paid tests:** `test_real_llm_planner_contract.py` (RUN_PAID_LLM_CONTRACT=1), paid E2E harness

### What's unclear

- When is a test "contract" vs "integration"?
- When must a paid LLM test be added?
- What folder structure enforces cheap vs paid boundary?
- Are there pytest markers defined?

---

## Desired behavior

Output: `.tasks-md/Planning/S6-TEST-STRATEGY.md`

Define each test layer:

### 1. Unit tests

```
Definition: Single function or class. No backend, LLM, or browser.
Dependencies: Only stdlib, pytest, dataclasses.
When required: Always for new functions with logic.
Speed: <100ms per test (expect 1000+ tests to run in <1s)
Folder: tests/test_*.py (mixed with other layers for now)
Naming: test_<function_name>_<case>
Markers: None required (always runs)
Example: test_confidence_for_testid_returns_high_confidence()
```

### 2. Contract tests

```
Definition: Typed interface boundary. Fake/mock dependencies. Verify contract shape.
Dependencies: Fake/mock objects, no real HTTP/LLM/browser.
When required: For every public function that produces/consumes typed events, payloads, or tool calls.
Speed: <500ms per test (expect 200–300 contract tests)
Folder: tests/test_*_contract.py
Naming: test_<interface_name>_<expectation>
Markers: None required (always runs)
Example: test_planner_message_is_token_bounded(), test_plan_ready_backend_event_drives_plan_review_read_model()
```

### 3. Integration tests

```
Definition: Two or more modules interact. No real backend/LLM/browser.
Dependencies: Real module imports, fake HTTP/LLM responses, controlled state.
When required: When multiple modules must coordinate without full E2E overhead.
Speed: <1s per test (expect 50–100 integration tests)
Folder: tests/test_*_integration.py or tests/test_*_contract.py with broader scope
Naming: test_<workflow>_<integration_point>
Markers: None required (always runs)
Example: test_planning_through_controller_fake_model()
```

### 4. E2E tests (cheap, local)

```
Definition: Full flow with real backend, real browser, no real LLM.
Dependencies: Real Python backend, real Playwright browser, fake LLM client.
When required: For complete user journeys, UI state rendering, live browser interaction.
Speed: 5–15s per test (expect 6–10 cheap E2E tests)
Folder: tests/e2e/test_*.py
Naming: test_<user_flow>_flow
Markers: None required, but may use @pytest.mark.e2e for filtering
Example: test_basic_click_flow(), test_correction_assert_then_click_flow()
```

### 5. Regression tests (guardrails)

```
Definition: Focused cheap suite that validates no prior clusters broke.
Dependencies: Same as unit/contract (no LLM/browser).
When required: Run after every cluster done.
Speed: <2 minutes total for full regression suite
Folder: Individual test files listed in S6-REGRESSION-GUARD.md
Naming: Existing test names (no rename required)
Markers: None (just cherry-picked existing tests)
Example: Command runs 12 focused suites, 365 tests total in ~2 min
```

### 6. Paid LLM tests (controlled)

```
Definition: Calls real OpenAI API (gpt-4o-mini). Verifies model behavior.
Dependencies: OPENAI_API_KEY env var. Real HTTP. No browser.
When required: Only after contract/unit/cheap E2E all pass. Once per cluster, not per commit.
Speed: 5–15s per test (expect 1 per cluster, max 5 total)
Folder: tests/test_*_contract.py with @pytest.mark.paid_llm
Naming: test_<purpose>_with_paid_llm()
Markers: @pytest.mark.paid_llm (require RUN_PAID_LLM_CONTRACT=1 to run)
Example: test_real_llm_planner_contract()
Gating: Requires env RUN_PAID_LLM_CONTRACT=1 (pytest default skips)
Artifact: llm-calls.json recording required in artifact dir
```

### 7. Paid browser E2E (final acceptance)

```
Definition: Full flow with real backend, real browser, real LLM (gpt-4o-mini).
Dependencies: OPENAI_API_KEY env var. Real browser. Real HTTP.
When required: Only after fake E2E passes and paid LLM contract passes. Once per complete flow, not frequently.
Speed: 15–30s per test (expect 1–3 total)
Folder: tests/e2e/test_*.py with @pytest.mark.paid_e2e_acceptance
Naming: test_<user_flow>_paid_e2e_acceptance
Markers: @pytest.mark.paid_e2e_acceptance (require RUN_PAID_E2E_ACCEPTANCE=1)
Example: test_llm_required_ambiguous_action_flow()
Gating: Requires env RUN_PAID_E2E_ACCEPTANCE=1
Artifact: llm-calls.json, token-report.json in artifact dir, backend logs, traces
```

---

## Folder structure

```
tests/
├── test_*.py                    (unit tests, mixed with contract)
├── test_*_contract.py           (contract tests, interface boundaries)
├── test_*_integration.py        (integration, multiple modules)
├── e2e/
│   ├── test_*.py                (full E2E flows, real backend/browser, fake LLM)
│   ├── test_*_paid_e2e.py       (paid browser E2E, gated by @pytest.mark)
│   └── fixtures/
│       └── test_app/            (HTML fixtures for testing)
└── ...
```

No separate `tests/unit/`, `tests/integration/`, `tests/e2e/` subdirs — use file naming convention instead.

---

## Naming conventions

### Test files

```
test_<module>_<aspect>.py           — Generic unit/contract tests
test_<module>_contract.py           — Typed interface boundaries
test_<module>_integration.py        — Multi-module workflows
test_*_paid_llm.py                  — Paid LLM tests
test_e2e_*.py or tests/e2e/test_*.py — E2E flows
```

### Test functions

```
test_<subject>_<expectation>()                       — Positive case
test_<subject>_<condition>_<expectation>()           — Conditional
test_<subject>_fails_when_<error_condition>()        — Negative case
test_<subject>_with_paid_llm_<aspect>()             — Paid LLM specific
```

Examples:

```
test_prompt_pack_builder_returns_valid_schema()
test_planning_convergence_contract_narrows_tool_surface_after_thinking()
test_model_router_fails_when_cheap_model_not_configured()
test_plan_ready_backend_event_drives_plan_review_read_model()
test_recovery_needed_with_paid_llm_invokes_diagnoser()
```

---

## Pytest markers

Define in `pyproject.toml` or `pytest.ini`:

```ini
[pytest]
markers =
    paid_llm: Requires RUN_PAID_LLM_CONTRACT=1 and OPENAI_API_KEY
    paid_e2e: Requires RUN_PAID_E2E_ACCEPTANCE=1 and real browser + OPENAI_API_KEY
    e2e: Full E2E flow with browser (no paid LLM)
    integration: Multi-module integration (no browser/LLM)
    contract: Typed interface boundary
```

Usage:

```python
@pytest.mark.paid_llm
def test_real_llm_planner_contract():
    ...

@pytest.mark.paid_e2e
def test_llm_required_ambiguous_action_flow():
    ...
```

Running:

```bash
# All cheap tests (default)
python -m pytest tests/ -q

# Paid LLM only (gated by env)
RUN_PAID_LLM_CONTRACT=1 python -m pytest tests/ -m paid_llm -q

# Paid E2E only (gated by env)
RUN_PAID_E2E_ACCEPTANCE=1 python -m pytest tests/e2e/ -m paid_e2e -q

# Exclude paid tests
python -m pytest tests/ -m "not paid_llm and not paid_e2e" -q
```

---

## Coverage expectations

- Unit tests: 95%+ coverage of new modules
- Contract tests: 100% of interface surface
- Integration tests: Happy path + key failure modes
- E2E: Happy path + 1 key error recovery flow
- Paid tests: Once per feature, no repeated paid calls

---

## Out of scope

- No code changes.
- No new tests (other stories write tests).
- No pytest configuration changes yet.

---

## Allowed files

- `.tasks-md/Planning/S6-TEST-STRATEGY.md` (output)
- Optional: `pyproject.toml` / `pytest.ini` additions (markers only, if not already present)

---

## Forbidden files

- No changes to test implementations.
- No changes to runtime modules.
- No changes to agent.py or server.py.

---

## Acceptance criteria

- [ ] Test taxonomy defines 7 layers (unit/contract/integration/E2E cheap/E2E paid/paid LLM/regression)
- [ ] Each layer has clear definition, speed, folder, naming
- [ ] Pytest markers are documented
- [ ] Running commands are specified
- [ ] Coverage expectations are clear
- [ ] Cheap vs paid boundary is explicit
- [ ] Document is stored in `.tasks-md/Planning/S6-TEST-STRATEGY.md`

---

## Validation command

After creation:

```bash
# Check pytest config exists
grep -r "@pytest.mark" tests/ | head -5

# Verify no pytest.ini conflicts with expected markers
cat pyproject.toml | grep -A 10 "\[tool.pytest"
```

---

## Stop conditions

- Pytest markers already defined inconsistently
- Folder structure cannot be enforced
- Cannot differentiate cheap vs paid tests clearly
