# S6-0703 — Capability Registry Framework

## Story ID
S6-0703

## Objective
Create common capability contract for actions, assertions, navigation, browser context, files, tables/lists, auth, visual/debug, and unsupported features.

## Capability contract schema

```
capability_type
category (action|assertion|navigation|context|file|table|auth|visual|unsupported)
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

## What it contains

- Capability registry data structure
- Contract schema definition
- Registry loader from Python/JSON config
- Validation that all required fields present
- Supported vs unsupported resolution logic
- Metadata for each category (action, assertion, navigation, etc.)

## What it must NOT contain

- Full implementation of every capability
- Browser execution
- Codegen rewrite
- Permission or risk enforcement (those are S6-0701, S6-0702)

## Tests first

### Unit tests

- Supported capability resolves handler metadata
- Unsupported capability returns typed unsupported result
- Capability missing required input triggers required-data event
- Each capability declares risk/preconditions/recording shape
- Registry lookup deterministic
- Unknown capability type → capability_gap (not exception)
- Precondition check does not execute, only validates

### Contract tests

- Unsupported capability cannot produce recorded success
- Capability gap payload includes needed_capability, suggested_future_work
- Registry contract matches S6-0001 matrix
- Capability metadata immutable after registry init

## Integration tests

- Registry integrates with capability baseline (S6-0704)
- Unsupported lookup flows to capability-gap handler
- Failed capability lookup does not crash runtime

## Acceptance criteria

- Registry schema fully specified and documented
- Supported/unsupported resolution logic 100% clear
- Category taxonomy defined (action|assertion|navigation|context|file|table|auth|visual|unsupported)
- 95% coverage on registry.py
- At least one integration test per category
- Sprint 6 regression guard passes

## Dependencies

- Requires: S6-0702 (Risk Classification)
- Blocks: S6-0704, S6-0705, S6-0708

## Notes

- Registry is the single source of truth for capability metadata
- Design for lazy loading: capabilities loaded as needed
- Preconditions are descriptive, not executable checks (see S6-0708 for auth checks)
- Scenario spec requires common contract vs. one-off architectures per capability
