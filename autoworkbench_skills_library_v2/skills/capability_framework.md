# Skill: Capability Framework

## Purpose
Support Playwright actions, assertions, browser behaviors, and advanced interactions through one consistent backend contract.

## When to use
Use when adding/editing action/assertion types, upload/download/dropdown/modal/new-tab/table/auth/iframe/shadow DOM support, capability gaps, or capability-specific codegen/recovery.

## Source of truth
- Complete LLM Mode capability framework
- PRD Playwright capability guidance
- LLM Runtime Policy capability routing

## Non-negotiable rules
1. Do not create one-off architecture per Playwright feature.
2. Every capability uses a standard contract.
3. Unsupported capability must produce capability_gap, not fake success.
4. Capability must define inputs, risk, preconditions, handler, postconditions, recording, codegen, recovery.
5. Backend validates capability support before execution.
6. Risky capabilities require permission policy.

## Capability contract
```text
capability_type
category
required_inputs
risk_level
preconditions
handler_strategy
postconditions
recording_shape
codegen_template
recovery_strategy
capability_gap_if_unsupported
```

## Capability categories
```text
action_capabilities
assertion_capabilities
navigation_capabilities
input_data_capabilities
browser_context_capabilities
file_capabilities
popup_tab_dialog_capabilities
table_list_capabilities
network_wait_capabilities
auth_session_capabilities
visual_debug_capabilities
```

## Required tests
- capability classification tests
- supported/unsupported tests
- permission-required tests
- postcondition validation tests
- codegen template tests
- recovery/gap tests

## Verification commands
```bash
python -m pytest tests/test_*capability* tests/test_*assertion* tests/test_*code* -q
```

## Stop conditions
Stop if:
- capability lacks postcondition
- required input is missing
- risky action lacks permission path
- codegen shape is undefined
- unsupported behavior would proceed silently

## Reporting format
Report:
1. Capability changed
2. Contract fields implemented
3. Tests/results
4. Gaps/unsupported cases
