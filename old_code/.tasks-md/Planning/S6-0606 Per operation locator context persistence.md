# S6-0606 Per operation locator context persistence

## Metadata

**Sprint:** Sprint 6
**Cluster:** 6
**Tier:** 1 (core)
**Type:** Feature
**Status:** Pending implementation
**Owner:** Locator Context
**Blocks:** S6-0607, S6-0608
**Blocked by:** S6-0604, S6-0605

---

## Purpose

Persist a typed `LocatorContext` per operation so update, replay, and repair flows can reconstruct the exact decision path. Context is JSON-serializable, secret-safe, and retrievable by `operation_id`.

---

## Source rules

- `autoworkbench_complete_llm_mode_runtime_policy_spec.md` — locator context per operation for update/replay/repair
- `autoworkbench_complete_llm_mode_p_0_scenarios_spec (2).md` — update flow requires prior context
- Cluster 7 (if present) secret redaction policy; this story enforces hard exclusion regardless

---

## Current known context

- Today operations store the final selector only; not the decision path.
- No update/replay can reconstruct previously attempted strategies.

---

## Desired behavior

### Dataclass

```
LocatorContext = {
  operation_id, step_id,
  original_element_info: {tag, attributes_summary, semantic_name},
  evaluated_candidates: [LocatorCandidate],
  selected_locator: LocatorCandidate,
  validation_status: {matched_count, validated_at},
  final_matched_count,
  risk_rating,
  section_name,
  ancestor_headings: [string],
  page_snapshot_ref: optional,
  update_history: [{prev_locator, reason, replaced_at}],
  user_preferences: { avoid_xpath, prefer_role_name, ... }
}
```

### Behavior

- Serialized as JSON; round-trips losslessly.
- Stored keyed by `operation_id`.
- Excludes secrets (passwords, tokens, PII). Hard exclusion list checked on write.
- Missing-context reads → return typed `LocatorContextMissing` diagnostic (never silently fail).

---

## Out of scope

- Update flow itself (S6-0607)
- Wrong-page flow (S6-0608)
- Replay repair product flow

---

## Allowed files

- `runtime/locator_context.py` (new)
- `tests/test_locator_context.py` (new)

---

## Forbidden files

- ✗ Broad `agent.py` refactor
- ✗ Broad `server.py` refactor
- ✗ `AGENTS.md` commit
- ✗ `.DS_Store` commit
- ✗ Paid LLM / paid E2E
- ✗ Persisting raw full DOM
- ✗ Persisting secrets / passwords / tokens
- ✗ Returning silent defaults on missing context

---

## Tests first

### Unit

- `test_locator_context_dataclass_required_fields_present`.
- `test_locator_context_serializes_to_json_and_round_trips`.
- `test_update_history_appends_in_order`.
- `test_evaluated_candidates_preserved_in_order`.

### Contract

- `test_store_then_retrieve_by_operation_id`.
- `test_missing_context_returns_typed_locator_context_missing`.
- `test_page_snapshot_ref_is_optional_and_not_required`.

### Integration

- `test_context_populated_after_deterministic_pipeline_success` (with S6-0601).
- `test_context_populated_after_ambiguity_selection` (with S6-0604).
- `test_context_populated_after_specialist_suggestion` (with S6-0605).

### Negative (secret-safety)

- `test_context_serialization_strips_password_field_if_present_in_input`.
- `test_context_serialization_strips_token_field_if_present_in_input`.
- `test_context_serialization_strips_pii_email_field_if_marked_pii`.
- `test_context_serialization_does_not_persist_raw_dom`.

### Regression

- S6-0601 / S6-0602 / S6-0604 / S6-0605 tests pass.
- Cluster 2 token budget tests pass.

---

## Implementation notes

1. `LocatorContext` as dataclass with explicit `to_dict()` / `from_dict()` that runs the redaction list.
2. Store backed by an injectable interface; default in-memory.
3. `LocatorContextMissing` is a typed sentinel, not `None`.
4. Hard exclusion list: `password`, `token`, `secret`, `api_key`, `cookie`, fields tagged `pii=True`.

### Key invariants

- No silent context loss.
- No secret persistence.
- No raw DOM persistence.

---

## Coverage target

**95%** on `runtime/locator_context.py`.

---

## Stop conditions

- Redaction list disputed → freeze on the listed names; add via follow-up.
- Storage interface unclear → use in-memory default.
- Coverage < 95% → diagnose.

---

## Regression guard checklist

- [ ] S6-0601 / S6-0602 / S6-0604 / S6-0605 tests pass
- [ ] Cluster 2 enforcement tests pass

---

## Acceptance criteria / Sign-off

- [ ] `LocatorContext` dataclass complete
- [ ] JSON round-trip lossless
- [ ] Store/retrieve by `operation_id`
- [ ] Missing context returns typed diagnostic
- [ ] Secrets / raw DOM excluded
- [ ] 95% coverage
- [ ] Regression guard green
