# S6-0704 — Action and Assertion Capability Baseline

## Story ID
S6-0704

## Objective
Define baseline capability contracts for common actions and assertions (9 actions, 17 assertions).

## Actions scope

```
click
fill
press
hover
scroll
select_option
check/uncheck
upload_file
submit
```

## Assertions scope

```
visible
hidden
enabled
disabled
has_text
exact_text
contains_text
has_value
checked
unchecked
url_matches
title_matches
count_equals
table_contains
list_contains
attribute_equals
css_state
```

## What it contains

- Registry entries for all 26 capabilities
- Required inputs per capability
- Risk/precondition/postcondition per capability
- Recording shape per capability
- Unsupported assertion mapping (which get capability_gap)
- Codegen template per capability

## What it must NOT contain

- Browser execution
- Test implementation (that's integration tests)
- Permission logic (that's S6-0701)

## Tests first

### Unit tests

- Each action declares required inputs
- Each action declares risk (most medium, submit/upload/download high)
- Each assertion declares expected value requirement when needed
- Exact_text requires expected text input
- Visible assertion does not require expected value
- Unsupported assertion (e.g., specific complex interactions) becomes capability_gap
- Registry lookup returns correct metadata for each action/assertion
- Required inputs validation deterministic

### Contract tests

- Expected_outcome does not automatically become assertion target/value
- Assertion capability maps to supported backend handler or gap
- Action postcondition metadata matches handler signature
- Recording shape includes all required assertion metadata

## Integration tests

- Each action/assertion can be registered and queried through S6-0703 registry
- Unsupported assertion does not execute (becomes gap, not fake success)
- Action/assertion metadata flows to recorder (S5 integration)

## Acceptance criteria

- All 26 capabilities registered with complete metadata
- Clear which assertions require expected value
- Required input/postcondition matrix documented
- 95% coverage on baseline capability definitions
- At least one integration test per capability
- Unsupported capability behavior verified
- Sprint 6 regression guard passes

## Dependencies

- Requires: S6-0703 (Capability Registry)
- Blocks: S6-0705, S6-0802

## Notes

- Baseline covers Playwright Core + IKS recorder contracts
- Future capabilities added via same registry pattern (no code changes needed)
- Recording shape critical for codegen; test both happy and error cases
- Design for replay: codegen template must produce valid locator/assertion replay
