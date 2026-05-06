# Skill: Replay and Repair

## Purpose
Guide replay one/all and validated repair behavior without mutating recorded truth unsafely.

## When to use
Use for replay_one, replay_all, replay preconditions, replay UI, replay repair, locator repair from recorded steps, versioned repairs.

## Source of truth
- PRD replay/repair persistence guidance
- Complete LLM Mode Recorded tab/replay design
- Backend runtime contract

## Non-negotiable rules
1. Replay is backend-owned.
2. Replay checks preconditions before execution.
3. Recorded steps are immutable evidence by default.
4. Repair creates validated diff/version or explicit update event.
5. LLM may suggest repair, backend validates.
6. Do not simulate replay in frontend.
7. Wrong page/state must produce clear precondition failure.
8. Replay repair must not silently change original recording.
9. Do not let repair mutate recorded truth without backend validation.

## Required implementation behavior
Replay should check:
```text
required page state
current page state
test data availability
locator validity
permission state
capability support
```

Repair flow:
```text
replay fails
→ classify failure
→ deterministic repair first
→ LLM replay_repair_specialist if needed
→ backend validates repair
→ user accepts
→ versioned update
```

## Required tests
- replay precondition tests
- replay one/all result tests
- wrong page failure tests
- repair diff tests
- recorded immutability tests
- UI event tests where relevant

## Verification commands
```bash
python -m pytest tests/test_replay_one.py tests/test_replay_all.py -q
```

## Stop conditions
Stop if:
- required evidence is missing, unclear, or contradictory
- replay starts from unknown/wrong state without warning
- repair mutates recording silently
- replay failure lacks classification
- frontend is doing replay logic
- unsupported replay capability proceeds as success

## Reporting format
Report:
1. Replay/repair behavior changed
2. Preconditions checked
3. Events emitted
4. Tests/results
5. Remaining replay limitations
