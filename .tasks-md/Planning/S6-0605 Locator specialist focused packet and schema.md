# S6-0605 Locator specialist focused packet and schema

## Metadata

**Sprint:** Sprint 6
**Cluster:** 6
**Tier:** 1 (core)
**Type:** Feature
**Status:** Pending implementation
**Owner:** Locator Specialist
**Blocks:** S6-0606
**Blocked by:** S6-0603

---

## Purpose

Define the focused packet handed to the `locator_specialist` purpose and the typed `LocatorAlternative` output schema. The specialist sees a tiny, redacted, validated packet — never the raw DOM — and has access only to locator/context tools (no action tools). Every suggestion is backend-validated before activation.

---

## Source rules

- `autoworkbench_complete_llm_mode_runtime_policy_spec.md` — specialist packet contents, tool restrictions, validation
- `autoworkbench_complete_llm_mode_p_0_scenarios_spec (2).md` — specialist invoked only after deterministic + scoping fail or weak-DOM defers
- Cluster 2 (S6-0205) — tool exposure enforcement
- Cluster 2 (S6-0207) — token budget

---

## Current known context

- S6-0603 emits weak-DOM defers.
- No specialist packet schema or tool filter exists.

---

## Desired behavior

### Packet contents (target < 1000 tokens)

```
{
  step_id,
  operation_id,
  target_semantic_name,
  current_locator (if any) + last validation result,
  attempted_strategies: [{strategy, locator_expression, matched_count}],
  section_summary (NOT raw DOM),
  page_summary (NOT raw DOM),
  ancestor_headings: [string],
  user_preferences: { avoid_xpath: bool, prefer_role_name: bool, ... },
  failure_reason: string
}
```

### Tools exposed

- Locator / context read-only tools (e.g., `get_section_summary`, `get_ancestor_headings`).
- **No action tools** (`click`, `fill`, `navigate`, `execute_script` are forbidden).

### Output schema

```
LocatorAlternative = {
  locator_expression,
  reason,
  stability,
  risk
}
LocatorAlternativeList = [LocatorAlternative]  # 1..N
```

### Validation

- Backend live-validates every suggestion (`matched_count == 1`).
- One schema retry; then fail-closed.
- No activation without live unique match.

---

## Out of scope

- Context persistence (S6-0606)
- Update flow (S6-0607)
- Wrong-page flow (S6-0608)

---

## Allowed files

- `runtime/locator_specialist_packet.py` (new)
- `runtime/locator_specialist_schema.py` (new)
- `tests/test_locator_specialist_packet.py` (new)
- `tests/test_locator_specialist_schema.py` (new)

---

## Forbidden files

- ✗ Broad `agent.py` refactor
- ✗ Broad `server.py` refactor
- ✗ `AGENTS.md` commit
- ✗ `.DS_Store` commit
- ✗ Paid LLM / paid E2E
- ✗ Raw full-DOM injection into the packet
- ✗ Exposing action / browser-mutating tools to the specialist
- ✗ Unvalidated activation

---

## Tests first

### Unit

- `test_packet_includes_required_fields`.
- `test_packet_excludes_raw_dom`.
- `test_packet_token_count_under_1000_for_realistic_section_summary`.
- `test_packet_includes_attempted_strategies_with_matched_count`.
- `test_locator_alternative_schema_round_trip`.

### Contract

- `test_specialist_purpose_tool_filter_excludes_click_fill_navigate_execute_script`.
- `test_specialist_purpose_tool_filter_includes_only_locator_context_tools`.
- `test_one_schema_retry_then_fail_closed`.
- `test_every_suggested_locator_is_backend_live_validated_before_activation`.
- `test_user_preferences_avoid_xpath_filters_out_xpath_suggestions`.

### Integration

- `test_weak_dom_defer_invokes_specialist_with_focused_packet`.
- `test_specialist_suggestion_with_matched_count_eq_1_activates`.
- `test_specialist_suggestion_with_matched_count_not_eq_1_does_not_activate`.

### Negative

- `test_specialist_cannot_call_click_tool`.
- `test_specialist_cannot_call_fill_tool`.
- `test_specialist_cannot_call_navigate_tool`.
- `test_specialist_cannot_call_execute_script_tool`.
- `test_packet_does_not_contain_secrets_or_pii` (rely on Cluster 7 redaction if present; otherwise hard exclusion).
- `test_malformed_specialist_output_first_retry_then_fail_closed`.

### Regression

- Cluster 2 tool-exposure tests pass.
- Cluster 2 schema-retry tests pass.
- Cluster 3 page/section summary tests pass.
- S6-0603 weak-DOM defer tests pass.

---

## Implementation notes

1. Packet builder consumes Cluster 3 section/page summaries; never the raw DOM.
2. Tool filter registered on the `locator_specialist` purpose (per Cluster 1/2 conventions).
3. Schema retry uses Cluster 2 harness.
4. Backend live validation runs after every suggestion; activation requires `matched_count == 1`.

### Key invariants

- No raw DOM.
- No action tools.
- One retry; then closed.
- No unvalidated activation.

---

## Coverage target

**95%** on both modules.

---

## Stop conditions

- Packet exceeds 1000 tokens → tighten section/page summaries; never include raw DOM.
- Tool registry not extensible to per-purpose filter → defer to Cluster 1 hooks; do not weaken filter.
- Coverage < 95% → diagnose.

---

## Regression guard checklist

- [ ] Cluster 2 tool-exposure tests pass
- [ ] Cluster 2 schema-retry tests pass
- [ ] Cluster 3 summary tests pass
- [ ] S6-0603 tests pass

---

## Acceptance criteria / Sign-off

- [ ] Packet < 1000 tokens, no raw DOM
- [ ] `LocatorAlternative` schema defined and validated
- [ ] Specialist purpose has no action tools
- [ ] Every suggestion backend-validated
- [ ] One retry then fail-closed
- [ ] 95% coverage on both modules
- [ ] Regression guard green
