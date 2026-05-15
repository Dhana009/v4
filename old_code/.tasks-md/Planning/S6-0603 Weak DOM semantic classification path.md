# S6-0603 Weak DOM semantic classification path

## Metadata

**Sprint:** Sprint 6
**Cluster:** 6
**Tier:** 1 (core)
**Type:** Feature
**Status:** Pending implementation
**Owner:** Locator Weak DOM
**Blocks:** S6-0605
**Blocked by:** S6-0601

---

## Purpose

For `div`/`span` elements without role or accessible name, heuristically classify the likely semantic (button, textbox, heading, link) and emit a calibrated-confidence candidate. Output is always marked "candidate, requires live validation"; never asserted as truth.

---

## Source rules

- `autoworkbench_complete_llm_mode_runtime_policy_spec.md` — weak-DOM semantic classification signals and calibration
- `autoworkbench_complete_llm_mode_p_0_scenarios_spec (2).md` — "div used as button" scenarios
- Cluster 3 page intelligence weak-DOM detection

---

## Current known context

- Cluster 3 detects weak DOM at page/section level.
- No element-level classifier exists.

---

## Desired behavior

### Signals

- **Action words** in text (Save, Submit, Cancel, Edit, Delete, Next).
- **Class names** containing `btn`, `button`, `input`, `field`, `link`.
- **`onclick`** handler present.
- **Position / styling** (cursor:pointer; absolute-positioned in a toolbar).
- **Neighbors** (label-like sibling, icon child).

### Confidence calibration

```
3+ signals match            confidence 0.90+
2 signals match             confidence 0.70–0.89
1 signal matches            confidence 0.50–0.69
0 signals matched           confidence < 0.50 → defer to specialist (S6-0605) or user
```

### Output

`WeakDomCandidate = {inferred_role, signals_matched, confidence, requires_live_validation: True}`.

---

## Out of scope

- Specialist invocation (S6-0605)
- Ambiguity surface (S6-0604)
- Scoping (S6-0602)

---

## Allowed files

- `runtime/locator_weak_dom.py` (new)
- `tests/test_locator_weak_dom.py` (new)

---

## Forbidden files

- ✗ Broad `agent.py` refactor
- ✗ Broad `server.py` refactor
- ✗ `AGENTS.md` commit
- ✗ `.DS_Store` commit
- ✗ Paid LLM / paid E2E
- ✗ Raw full-DOM dump
- ✗ Asserting classification as truth (must remain a candidate)

---

## Tests first

### Unit

- `test_three_signals_button_action_word_btn_class_onclick_yields_confidence_at_least_0_90`.
- `test_two_signals_button_yields_confidence_between_0_70_and_0_89`.
- `test_one_signal_button_yields_confidence_between_0_50_and_0_69`.
- `test_zero_signals_yields_confidence_below_0_50_and_defers`.
- `test_textbox_signals_classname_field_plus_label_neighbor_classify_as_textbox`.
- `test_heading_signals_font_size_class_plus_position_classify_as_heading`.
- `test_link_signals_anchor_like_class_plus_underline_classify_as_link`.

### Contract

- `test_output_includes_signals_matched_list`.
- `test_output_marks_requires_live_validation_True`.
- `test_classifier_does_not_invoke_llm`.

### Integration

- `test_weak_dom_candidate_handed_off_to_specialist_when_confidence_below_threshold`.
- `test_weak_dom_candidate_handed_off_for_live_validation_before_activation`.

### Negative

- `test_div_with_no_signals_does_not_emit_high_confidence`.
- `test_classifier_does_not_assert_inferred_role_as_truth` (must remain candidate).
- `test_signal_double_counting_is_prevented` (e.g., `btn` class + `button` class still counts once for class signal).

### Regression

- S6-0601 deterministic tests pass.
- Cluster 3 weak-DOM detection tests pass.

---

## Implementation notes

1. Signal detectors are pure functions; classifier composes them.
2. Confidence calibration uses a small lookup; tests pin the boundaries.
3. Output flagged `requires_live_validation=True` — always.

### Key invariants

- Output is never authoritative.
- LLM not invoked here.
- Defer threshold is explicit (< 0.50).

---

## Coverage target

**95%** on `runtime/locator_weak_dom.py`.

---

## Stop conditions

- Signal set disputed → freeze on the 5 listed.
- Confidence boundaries disputed → freeze on the 4 listed.
- Coverage < 95% → diagnose.

---

## Regression guard checklist

- [ ] S6-0601 tests pass
- [ ] Cluster 3 tests pass
- [ ] Cluster 2 enforcement tests pass

---

## Acceptance criteria / Sign-off

- [ ] 5 signal detectors implemented
- [ ] Confidence calibration matches table
- [ ] Output marked `requires_live_validation=True`
- [ ] Defer path active below 0.50
- [ ] No LLM call from this module
- [ ] 95% coverage
- [ ] Regression guard green
