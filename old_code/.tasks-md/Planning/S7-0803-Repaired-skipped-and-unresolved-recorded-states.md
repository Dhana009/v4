# S7-0803 — Repaired, Skipped, and Unresolved Recorded States

**Sprint:** Sprint 7
**Cluster:** 8
**Tier:** 1 (core)
**Type:** Feature
**Status:** Done
**Blocks:** []
**Blocked by:** [S7-0802]

---

## Objective

Display recorded steps in non-happy-path states: repaired (locator changed), skipped (manual skip), unresolved (failed but not recovered). Show state badges, old/new locators for repaired steps, skip reason for skipped steps. Do not mark unresolved as pass.

After S7-0803:
- Repaired steps show old and new locator
- Skipped steps show skip reason
- Unresolved steps show failure reason and recovery blocker
- No fake success badges

---

## Source Rules

- PRD-05-REC-004: Recorded step states include repaired, skipped, unresolved; each has metadata
- PRD-05-RECOVERY-001: Recovery manager provides repaired evidence and skip metadata
- PRD-03-FE-C8-001: Frontend renders backend evidence; no inference

---

## Current Known Context

### What exists
- S7-0801/0802 basic recorded rendering
- PRD defines repaired/skipped/unresolved states
- `step_recorded.state` field in event schema

### What gaps exist
- No state badge/indicator display
- No old/new locator display for repaired steps
- No skip reason display
- No unresolved failure context display

---

## Tests First

### Unit Tests

```python
test_repaired_step_displays_old_and_new_locator()  # PRD-05-REC-004
test_skipped_step_displays_skip_reason()  # PRD-05-REC-004
test_unresolved_step_displays_failure_reason()  # PRD-05-REC-004
test_state_badge_rendering()  # PRD-05-REC-004
test_malformed_state_safe_fallback()  # GOV-S7-C0-009
```

### Component Tests

```python
test_repaired_step_component_renders()  # PRD-05-REC-004
test_skipped_step_component_renders()  # PRD-05-REC-004
test_unresolved_step_component_renders()  # PRD-05-REC-004
test_unresolved_step_does_not_show_pass_badge()  # PRD-05-REC-004
```

### Negative Tests

```python
test_repaired_step_missing_new_locator_shows_fallback()  # GOV-S7-C0-009
test_skipped_step_missing_skip_reason_safe()  # GOV-S7-C0-009
test_unresolved_step_unknown_state_safe()  # GOV-S7-C0-009
```

---

## Implementation Boundaries

### Allowed Files

```
- frontend/src/components/recorded/RecordedStep.jsx (extend for state display)
- frontend/src/components/recorded/RecordedStepRepaired.jsx (new)
- frontend/src/components/recorded/RecordedStepSkipped.jsx (new)
- frontend/src/components/recorded/RecordedStepUnresolved.jsx (new)
- tests/test_frontend_recorded_evidence_rendering.py (extend)
```

### Forbidden Files

```
- agent.py
- runtime/*.py
- frontend_new_design_prototype/
```

---

## Stop Conditions

Stop if:

- `step_recorded.state` schema missing or does not match PRD
- Recovery manager (backend) does not provide repaired/skip metadata
- Implementation requires new backend field/command


---

## Evidence Recorded

- **Commit:** 4abbb27 — Cluster 8 components
- **Tests:** tests/test_frontend_recorded_code_replay_cards.py (27 tests)
- **Build:** dist/autoworkbench.js 1.3mb (clean)
- **Regression:** 2444 passed / 1 skipped / 0 failed
