# S6-0007 Paid LLM and E2E acceptance policy

**Sprint:** Sprint 6  
**Cluster:** 0 (Governance)  
**Type:** Documentation  
**Status:** Planning  
**Owner:** Testing Policy  

---

## Purpose

Define when paid LLM and paid browser E2E tests are allowed. Prevent paid calls from becoming the first debugging tool.

---

## Principle

```
Cheap first. Paid last.

Paid tests are for ACCEPTANCE, not for DEVELOPMENT.

Development uses fake models, contracts, and local E2E.
Only when all cheap tests pass, try paid.
```

---

## Paid LLM probe policy

### When allowed

```
1. ✓ All contract/unit tests pass
2. ✓ Regression guard passes (full suite)
3. ✓ Feature is stable in fake model tests
4. ✓ Need to verify real model behavior (gpt-4o-mini)
5. ✓ RUN_PAID_LLM_CONTRACT=1 is set in environment
6. ✓ OPENAI_API_KEY is present
```

### When forbidden

```
✗ Single function debugging
✗ Experimenting with model prompt
✗ Infrastructure changes
✗ Without prior cheap test evidence
✗ On every commit
✗ Before 24 hours after last paid call
```

### How to run

```bash
# Only if all conditions met above:
RUN_PAID_LLM_CONTRACT=1 python -m pytest tests/test_<feature>_contract.py::test_real_llm_<aspect> -q

# Example:
RUN_PAID_LLM_CONTRACT=1 python -m pytest tests/test_page_intelligence_fake_integration.py::test_fake_planner_records_call_without_paid_llm -q
```

### Expected artifact

```
.payloads/
├── llm_<timestamp>.json    — LLM call details (model, tokens, finish_reason)
└── cost_<timestamp>.txt    — Estimated cost
```

### Token expectations

- Single call: <500 input tokens
- Per-step planning: <2000 input tokens
- Full E2E: <6000 total input tokens

If exceeded, stop and investigate. Do not accept runaway token usage.

---

## Paid browser E2E acceptance policy

### When allowed

```
1. ✓ All cheap tests (unit + contract + cheap E2E) pass
2. ✓ Regression guard passes
3. ✓ Paid LLM probe passes (if applicable)
4. ✓ Feature is a complete new Complete LLM Mode flow
5. ✓ Browser interaction is required (not testable locally)
6. ✓ RUN_PAID_E2E_ACCEPTANCE=1 is set in environment
7. ✓ OPENAI_API_KEY is present
8. ✓ Pre-agreed token budget is set
```

### When forbidden

```
✗ Before cheap E2E passes
✗ For debugging locator failures
✗ For testing UI rendering (use cheap frontend tests)
✗ For experimenting with flow
✗ Without explicit pre-approval
```

### How to run

```bash
# Only if all conditions met above:
RUN_PAID_E2E_ACCEPTANCE=1 python -m pytest tests/e2e/test_<feature>_flow.py::test_<flow>_paid_e2e_acceptance -q

# Example:
RUN_PAID_E2E_ACCEPTANCE=1 python -m pytest tests/e2e/test_llm_required_ambiguous_action_flow.py::test_llm_required_ambiguous_action_flow -q
```

### Required artifact structure

```
test-results/autoworkbench-e2e/<flow>-<timestamp>-<pid>/
├── llm_calls.json
├── token_report.json
├── backend.log
├── traces/
│   ├── trace-<timestamp>.zip
│   └── ...
├── session.json
└── spec.ts
```

**Mandatory fields in artifacts:**

#### llm_calls.json

```json
{
  "calls": [
    {
      "id": "llm_001",
      "purpose": "step_plan_normalizer",
      "model": "gpt-4o-mini",
      "input_tokens": 2500,
      "output_tokens": 45,
      "finish_reason": "stop",
      "tool_calls": []
    }
  ],
  "total_calls": 2,
  "total_input_tokens": 5000,
  "total_output_tokens": 100
}
```

#### token_report.json

```json
{
  "breakdown": {
    "system": 2105,
    "skill": 3398,
    "tool_schema": 846,
    "history": 552,
    "dom_tool_result": 0
  },
  "model_classes": ["main"],
  "prompt_pack_ids": ["step_plan_normalizer.v1"],
  "skills_loaded": ["core", "actions", "download"]
}
```

#### backend.log excerpt (containing convergence evidence)

```
[MODEL_ROUTER] purpose=step_plan_normalizer model=gpt-4o-mini
[AGENT] planning convergence pressure: injected after llm_thinking turn
[AGENT] step_plan_normalizer: tool surface narrowed to ask_user+send_to_overlay
[AGENT] step_plan_normalizer: forcing tool_choice=ask_user
```

### Terminal output expectations

Acceptable:

```
ask_user(question="Could you clarify which element you intend to save?")
plan_ready(steps=[...])
needs_more_context(reason="weak_dom")
```

Unacceptable:

```
PLANNING_NO_PROGRESS
RuntimeError: (any unhandled error)
(blank output with exception in logs)
```

### Token expectations

| Flow type | Target | Max |
|---|---|---|
| Single-step click | 1000 input tokens | 2000 |
| Multi-step section | 3000 input tokens | 5000 |
| Recovery + repair | 2500 input tokens | 4000 |
| Full journey | 5000 input tokens | 8000 |

If a flow exceeds max, investigate token usage before accepting.

---

## Hard stops (automatic failure)

Paid E2E automatically fails and blocks next cluster if:

```
✗ PLANNING_NO_PROGRESS appears in any LLM call
✗ LLM returns unstructured text instead of ask_user/plan_ready/needs_more_context
✗ Tool call is made after convergence narrowing (should be ask_user only)
✗ Backend logs show RuntimeError or unhandled exception
✗ Artifact is incomplete (missing llm_calls.json or token_report.json)
✗ Token usage exceeds pre-agreed budget by >10%
✗ Browser test hangs or times out (>30s per step)
```

If hard stop triggers, do NOT proceed to next cluster. Fix root cause first.

---

## Cost tracking

Maintain a running cost log:

```
Sprint 6 Paid Test Cost Tracker

Cluster 0: No paid tests (governance only)
Cluster 1: ~5 paid LLM probes @ $0.003 each = ~$0.015
Cluster 2: ~3 paid LLM probes @ $0.003 each = ~$0.009
Cluster 3: ~2 paid E2E @ $0.10 each = ~$0.20
...

Target: <$5 total for all Sprint 6 clusters
```

---

## Out of scope

- No paid tests implemented yet
- No cost charged during Cluster 0
- No product code changes

---

## Allowed files

- `.tasks-md/Planning/S6-PAID-TEST-POLICY.md` (this output)
- `test_*_contract.py` with @pytest.mark.paid_llm marker (future)
- `tests/e2e/test_*_paid_e2e.py` with @pytest.mark.paid_e2e marker (future)

---

## Forbidden files

- No changes to product code
- No test implementation yet
- No OPENAI_API_KEY in code (env only)

---

## Acceptance criteria

- [ ] Paid LLM conditions are clear and enforceable
- [ ] Paid E2E conditions are clear and enforceable
- [ ] Artifact structure is defined
- [ ] Hard stop conditions are absolute
- [ ] Token expectations are specified per flow type
- [ ] Cost tracking is documented
- [ ] File is stored in `.tasks-md/Planning/S6-PAID-TEST-POLICY.md`

---

## Validation

After policy is created, document examples:

```bash
# Allowed:
RUN_PAID_LLM_CONTRACT=1 python -m pytest tests/test_real_llm_planner_contract.py -q

# Forbidden (will fail):
python -m pytest tests/test_real_llm_planner_contract.py -q  # Missing env gate

# Allowed:
RUN_PAID_E2E_ACCEPTANCE=1 python -m pytest tests/e2e/test_llm_required_ambiguous_action_flow.py -q

# Forbidden (will fail):
python -m pytest tests/e2e/test_llm_required_ambiguous_action_flow.py -q  # Missing env gate
```

---

## Stop conditions

- Token expectations cannot be pre-agreed
- Artifact structure cannot be defined
- Hard stop conditions are unclear
