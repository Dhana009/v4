# S6-0003 Coverage gate and command policy

**Sprint:** Sprint 6  
**Cluster:** 0 (Governance)  
**Type:** Documentation + Configuration  
**Status:** Planning  
**Owner:** Testing Infrastructure  

---

## Purpose

Define and enforce minimum 95% code coverage for new/modified modules. Establish local and CI coverage commands.

---

## Source docs

- Existing `pyproject.toml` / pytest configuration
- Sprint 5 test results (365 passing tests)
- Standard Python coverage tool expectations

---

## Current evidence

### Coverage config status

- No explicit `.coveragerc` or `pyproject.toml [tool.coverage]` section found (audit needed)
- No coverage reports currently generated
- No CI enforcement (assume GitHub Actions or similar)

### Coverage baseline

- Sprint 5: 365 cheap tests passing
- Estimate: Most runtime modules have >80% coverage, some have <70%
- Unknown: Which modules are below 95%?

---

## Desired behavior

### 1. Local coverage command

```bash
python -m pytest tests/ \
  --cov=runtime \
  --cov=recording \
  --cov=locator \
  --cov=llm \
  --cov=event \
  --cov-report=html \
  --cov-report=term-missing \
  --cov-fail-under=95 \
  -q
```

This command:

- Measures coverage for key modules (runtime, recording, locator, llm, event)
- Generates HTML report in `htmlcov/` for visual inspection
- Displays missing lines in terminal
- Fails if coverage drops below 95%

### 2. Configuration (pyproject.toml or .coveragerc)

```toml
[tool.coverage.run]
source = ["runtime", "recording", "locator", "llm", "event", "agent", "server"]
omit = [
    "*/migrations/*",
    "*/__pycache__/*",
    "*/venv/*",
    "*/site-packages/*",
]

[tool.coverage.report]
precision = 2
show_missing = True
skip_covered = False
exclude_lines = [
    "pragma: no cover",
    "def __repr__",
    "if __name__ == .__main__.:",
    "raise AssertionError",
    "raise NotImplementedError",
]

[tool.coverage.html]
directory = "htmlcov"
```

### 3. Module-specific minimums

Per-module coverage requirement:

| Module | Min Coverage | Reason |
|---|---|---|
| `runtime/llm_runtime_controller.py` | 95% | Core LLM orchestration, high criticality |
| `runtime/prompt_pack_builder.py` | 95% | Token control, must be tested |
| `runtime/skill_policy.py` | 95% | Policy enforcement |
| `runtime/tool_schema_policy.py` | 95% | Safety boundary |
| `runtime/model_router.py` | 95% | Multi-model routing |
| `recording/recorder.py` | 95% | Recording truth |
| `recording/codegen.py` | 90% | Code generation (some edge cases acceptable) |
| `locator/engine.py` | 90% | Locator ranking (some strategies may have lower coverage) |
| `llm/client.py` | 90% | HTTP boundaries |
| Other runtime | 85% | Helpers and utilities |

### 4. Branch coverage for state machines

For classes with state transitions (e.g., `PhaseTracker`, `SessionLifecycle`, `PlanCorrection`), enforce branch coverage:

```bash
--cov-report=term-missing:skip-covered \
  --fail-under=90
```

This ensures both true and false branches are tested.

### 5. Exclusions

Allow exclusions only for:

- `pragma: no cover` — documented exceptional cases
- `if __name__ == "__main__"` — CLI only
- Raised exceptions in factories/getters that fail fast
- Platform-specific code (e.g., macOS file picker, Windows-only paths)

---

## Out of scope

- No code changes to achieve coverage.
- No lowering of coverage minimums.
- No excluding new code without justification.
- No changes to test implementations to hide missing coverage.

---

## Allowed files

- `pyproject.toml` — add `[tool.coverage]` section if not present
- `.coveragerc` — create if pyproject.toml not suitable
- `.tasks-md/Testing/S6-COVERAGE-GATE.md` — output document

---

## Forbidden files

- No changes to runtime modules.
- No changes to test files.

---

## Acceptance criteria

- [ ] Coverage command is defined and documented
- [ ] Module-specific minimums are listed
- [ ] Branch coverage strategy for state machines is clear
- [ ] Exclusions are justified and limited
- [ ] Config is stored in pyproject.toml or .coveragerc
- [ ] Local coverage command produces HTML report
- [ ] HTML report is readable and accurate
- [ ] Document is stored in `.tasks-md/Testing/S6-COVERAGE-GATE.md`

---

## Validation commands

After setup:

```bash
# Run coverage on runtime modules
python -m pytest tests/ --cov=runtime --cov=recording --cov=locator --cov-report=term-missing --cov-fail-under=95 -q

# Check if htmlcov/ is generated
ls -la htmlcov/index.html

# Inspect for modules below 95%
grep -E "^(runtime|recording|locator)" htmlcov/status.json | grep -v "100%"
```

---

## Stop conditions

- Coverage tool not installed (expect: `pytest-cov` in requirements)
- Existing coverage config conflicts
- Cannot determine which modules need 95% vs 85%
