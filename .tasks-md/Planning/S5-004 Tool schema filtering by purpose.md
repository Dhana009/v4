# S5-004 Tool schema filtering by purpose

Status: Planning
Sprint: Sprint 5
Type: Story
Owner:
Priority: P0
Source docs: PRD v2.3 02_LLM_RUNTIME.md, runtime/llm_runtime_controller.py, runtime/tool_registry.py

## Problem / Goal

**Problem:** All tool schemas are sent to every LLM call (~410 tokens per call). Plan correction doesn't need browser tools. Recovery doesn't need planning tools. Tool schema is the third-largest token bucket.

**Goal:** Filter tool schemas by purpose and phase. step_plan_normalizer gets planning tools only. plan_diff_editor gets zero browser/action tools. recovery gets limited tools. Prove tool_schema bucket shrinks.

## Scope

- Build tool schema filter: `runtime/tool_schema_filter.py`
- Enforce tool_policy from PURPOSE_REGISTRY
- Planning phase: expose PLANNING_TOOL_NAMES only
- Correction phase: expose zero action tools
- Recovery phase: expose RECOVERY_TOOL_NAMES only
- Update tool schema estimation in telemetry

Out of scope:
- Tool implementation changes
- Tool naming/API changes
- Validation of missing tools (schema is optional)

## Required unit tests

- `test_tool_schema_filter.py`:
  - filter_tools_for_purpose(purpose="step_plan_normalizer", phase="planning") returns planning tools
  - filter_tools_for_purpose(purpose="plan_diff_editor", phase="plan_review") returns empty or minimal
  - filter_tools_for_purpose(purpose="recovery_diagnoser", phase="recovery") returns recovery tools
- `test_tool_schema_tokens.py`:
  - Tool schema token estimate reflects filtered schema
  - Comparison vs baseline (full schema)

## Required contract tests

- `test_tool_policy_contract.py`:
  - Forbidden tools are absent from schema for purpose
  - Allowed tools are present
  - phase-specific tool policy respected

## Required integration tests

- `test_planning_filtered_tool_schema.py`:
  - Planning call exposes planning tools only
  - Tool schema tokens reduced
  - Telemetry includes tool_count and tools_exposed_count

## Fixture/page needs

None.

## Paid E2E requirement

None.

## Acceptance criteria

- [ ] Tool schema filter module created
- [ ] PURPOSE_REGISTRY tool_policy enforced
- [ ] Planning calls expose only planning tools
- [ ] Correction calls expose no browser/action tools
- [ ] Recovery calls expose limited tools
- [ ] tool_schema_tokens bucket measured and reduced
- [ ] Telemetry includes tool_count and tools_exposed_count
- [ ] No missing required tools (verified in E2E)

## Evidence

Will include:
- `runtime/tool_schema_filter.py` module
- Unit test output showing tool filtering logic
- Contract test output proving forbidden tools absent
- Integration test telemetry with tool_count and tools_exposed_count
- Token estimate comparison: baseline full schema vs filtered schema

## Verification commands/results

```bash
pytest tests/test_tool_schema_filter.py -v
pytest tests/test_tool_schema_tokens.py -v
pytest tests/test_tool_policy_contract.py -v
pytest tests/test_planning_filtered_tool_schema.py -v

# Verify tool reduction
# Old baseline: ~410 tokens per call for all tools
# Expected: planning calls ~200–250 tokens, correction ~0–50 tokens
```

## Risk

- **Low:** Missing tool schema may confuse model if not documented
- **Low:** Tool policy in PURPOSE_REGISTRY may be incomplete

## Mitigation

- Contract test explicit about forbidden/allowed tools
- E2E observes if missing tools cause failures
- Tool policy audit in S5-015 (guardrails)
