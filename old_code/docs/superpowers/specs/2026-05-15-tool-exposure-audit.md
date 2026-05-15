# Tool Exposure Audit — Per-Purpose Allowlist (P0 Item 21)

**Date:** 2026-05-15  
**Spec ref:** runtime_policy §12 — tool exposure matrix per purpose  
**DG3 audit item:** P0-21 — tool exposure matrix has entries but no audit / tightening  
**Author:** Agent W7a  
**Branch:** s7/clusters-6-11-complete-llm-mode  

---

## Summary of Changes

`runtime/tool_schema_policy.py` — `PURPOSE_PLANNING_TOOL_NAMES` dict updated:

| Change type | Count |
|---|---|
| New entries added (classifier modules not previously registered) | 3 |
| Entries tightened (allowlist reduced) | 0 (pre-existing lock-in by contract tests) |
| Entries confirmed correct (no change needed) | 14 |
| Destructive write tools found in any allowlist | 0 |

---

## Per-Purpose Allowlist Table

### Classifiers — deterministic, no tool calls permitted

| Purpose | Old allowlist | New allowlist | Rationale | Spec violation flags |
|---|---|---|---|---|
| `intent_classifier` | `()` | `()` | Deterministic label; LLM escalation path must not invoke tools | None |
| `journey_classifier` | `()` | `()` | Deterministic routing; no browser state needed | None |
| `failure_classifier` | `()` | `()` | Deterministic label; read-only structured output | None |
| `plan_edit_classifier` | **MISSING** | `()` | Module exists (`runtime/plan_edit_classifier.py`) but had no policy entry. Deterministic classifier — empty allowlist correct. | **SPEC-VIOLATION: purpose module existed without policy entry** |
| `locator_issue_classifier` | **MISSING** | `()` | Module exists (`runtime/locator_issue_classifier.py`) but had no policy entry. Deterministic classifier — empty allowlist correct. | **SPEC-VIOLATION: purpose module existed without policy entry** |
| `capability_classifier` | **MISSING** | `()` | Module exists (`runtime/capability_classifier.py`) but had no policy entry. Deterministic classifier — empty allowlist correct. | **SPEC-VIOLATION: purpose module existed without policy entry** |

### Text-generation purposes — no browser interaction needed

| Purpose | Old allowlist | New allowlist | Rationale | Spec violation flags |
|---|---|---|---|---|
| `clarification_generator` | `PLAN_REVIEW_ONLY_TOOL_NAMES` = `(send_to_overlay, ask_user)` | unchanged | Needs overlay to deliver clarification + ask_user for back-and-forth | None |
| `user_response_writer` | `(ask_user,)` | unchanged | Terminal user-facing text; no DOM access needed | None |
| `trace_summarizer` | `()` | unchanged | Pure text summarization; no tools required | None |

### Read-only intelligence / analysis purposes

| Purpose | Old allowlist | New allowlist | Rationale | Spec violation flags |
|---|---|---|---|---|
| `page_intelligence_summarizer` | `READ_ONLY_DOM_TOOL_NAMES` = `(dom_extract,)` | unchanged | Read-only DOM extraction only; no click/type/submit | None |
| `page_validation_recommender` | `(browser_get_state, dom_extract, ask_user)` | unchanged | Read-only state + DOM inspection; no destructive actions | None |

### Plan-construction purposes

| Purpose | Old allowlist | New allowlist | Rationale | Spec violation flags |
|---|---|---|---|---|
| `journey_planner` | `STEP_PLAN_TOOL_NAMES` = all 6 planning-safe tools | unchanged | Contract test (test_llm_planning_contracts §005) locks this to `PLANNING_SAFE_TOOL_NAMES`. All 6 tools are read-safe — no `action_click` / `action_fill` / `action_assert`. Tightening to overlay-only would break the contract. Filed for follow-up. | **ADVISORY: broader than minimal (6 tools vs 2 needed). Pre-existing contract prevents tightening here.** |
| `step_plan_normalizer` | `STEP_PLAN_TOOL_NAMES` | unchanged | Needs full planning-safe surface to produce/validate the final plan | None |
| `plan_diff_editor` | `()` | unchanged | Structured JSON diff; no tool calls needed | None |

### Locator / assertion purposes — read-only DOM, no destructive actions

| Purpose | Old allowlist | New allowlist | Rationale | Spec violation flags |
|---|---|---|---|---|
| `locator_specialist` | `(browser_get_state, dom_extract, locator_find, locator_validate, ask_user)` | unchanged | Read-only locator resolution; no click/type | None |
| `custom_assertion_planner` | `(browser_get_state, dom_extract, locator_find, locator_validate, ask_user)` | unchanged | Read-only assertion strategy; no click/type | None |

### Execution / recovery purposes

| Purpose | Old allowlist | New allowlist | Rationale | Spec violation flags |
|---|---|---|---|---|
| `execution_driver` | `EXECUTION_DRIVER_PLANNING_TOOL_NAMES` = `(ask_user,)` | unchanged | Planning-phase tools only; actual execution tools gated separately via `executing_tools` in policy registry | None |
| `recovery_diagnoser` | `RECOVERY_ONLY_TOOL_NAMES` = `(browser_get_state, ask_user)` | unchanged | State-read + user escalation only during recovery | None |
| `replay_repair_specialist` | `RECOVERY_ONLY_TOOL_NAMES` = `(browser_get_state, ask_user)` | unchanged | Same as recovery_diagnoser; no write tools | None |

### Agent fallback

| Purpose | Old allowlist | New allowlist | Rationale | Spec violation flags |
|---|---|---|---|---|
| `agent_fallback` | `STEP_PLAN_TOOL_NAMES` | unchanged | `PLANNING_SAFE_TOOL_NAMES` = `{ask_user, browser_get_state, dom_extract, locator_find, locator_validate, send_to_overlay}` — zero destructive write tools (`action_click`, `action_fill`, `action_assert` are absent). No downgrade required. | **ADVISORY: retire purpose once all agent paths have dedicated purposes (per TODO in llm_policy_registry.py).** |

---

## Spec-Violation Flags Summary

| Flag | Severity | Purpose(s) | Status |
|---|---|---|---|
| Purpose module exists but no policy entry | P0 | `plan_edit_classifier`, `locator_issue_classifier`, `capability_classifier` | **FIXED** — entries added with `()` |
| Allowlist broader than minimal | Advisory | `journey_planner`, `agent_fallback` | Not fixed — pre-existing contract test (`journey_planner`) or intentional broad fallback (`agent_fallback`). |
| `agent_fallback` should be retired | Advisory | `agent_fallback` | Tracked via TODO in `llm_policy_registry.py` |

---

## `PLANNING_SAFE_TOOL_NAMES` Destructive-Write Audit

`PLANNING_SAFE_TOOL_NAMES` (from `runtime/tool_registry.py`):

```
ask_user
browser_get_state
dom_extract
locator_find
locator_validate
send_to_overlay
```

**None of these are destructive write tools.** The destructive execution tools (`action_click`, `action_fill`, `action_assert`) are ONLY exposed via `executing_tools` in `llm_policy_registry._build_policy()` for `execution_driver`, and via `recovery_tools` for recovery purposes. They are NOT present in any planning-phase allowlist.

---

## Purposes in `REQUIRED_PURPOSE_IDS` Not in `PURPOSE_PLANNING_TOOL_NAMES`

After this audit, all 17 purposes in `REQUIRED_PURPOSE_IDS` have entries in `PURPOSE_PLANNING_TOOL_NAMES`. The three classifier purposes (`plan_edit_classifier`, `locator_issue_classifier`, `capability_classifier`) are NOT currently in `REQUIRED_PURPOSE_IDS` — they exist as module files but have not been formally registered. This is a follow-up gap.

---

## Files Changed

- `/Users/apple/personal/agent v4/runtime/tool_schema_policy.py` — added 3 classifier entries, reorganized with section comments
- `/Users/apple/personal/agent v4/docs/superpowers/specs/2026-05-15-tool-exposure-audit.md` — this file
