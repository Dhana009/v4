# Page-State / Preconditions / Postconditions / depends_on_step_ids — Schema Gap Audit

**Date:** 2026-05-15
**Branch:** s7/clusters-6-11-complete-llm-mode
**Scope:** Read-only audit. Step schema, precondition/postcondition flow,
depends_on_step_ids ordering, page_state state object versus PRD v2.3 +
Complete LLM Mode P0 spec.

---

## 1. Spec-required fields (per P0 §3.8, §15.6, §21.4, §21.7, §23.5, §23.8, §23.14)

Per **`autoworkbench_complete_llm_mode_p_0_scenarios_spec (2).md`**:

- **§3.8 lines 185–191** — every planned operation must carry:
  `required_page_state`, `precondition`, `postcondition`, `expected_outcome`,
  `depends_on_step_ids`, `locator_scope`.
- **§15.6 lines 1379–1387** ("Page ownership rule") — adds
  `source_page_url`, `page_snapshot_ref`, `section_snapshot_ref`.
- **§21.4 lines 1873–1888** ("Stored locator context per step/operation") — adds
  `original element_info`, `selected locator`, `candidate locator list`,
  `validation count`, `semantic_name`, `risk/confidence`, `locator_scope`,
  `nearby ancestor summaries`, `section_snapshot_ref`, `page_snapshot_ref`,
  `required_page_state`, `precondition`, `postcondition`, `expected_outcome`.
- **§21.7 lines 1940–1963** — `expected_outcome` should be explicit
  postcondition metadata with a typed category
  (navigation / modal_opens / dropdown_opens / new_tab_opens / content_changes
  / toast_appears / file_picker / download_starts / no_visible_change / unsure).
- **§23.5 lines 2160–2178** (`step_state`) — required fields include
  `step_id`, `step_order`, `intent`, `status`, `source`, `element_info`,
  `section_info`, `expected_outcome`, `postcondition`, `required_page_state`,
  `depends_on_step_ids`, `locator_state`, `linked_plan_id`,
  `linked_plan_version_id`, `warnings[]`, `created_at`, `updated_at`.
- **§23.8 lines 2259–2274** (`locator_state`) — must include
  `last_validated_page_state`, `can_live_validate`, `requires_page_state`.
- **§23.14 lines 2402–2411** (`page_state`) — must include `current_url`,
  `current_title`, `page_state_id`, `page_summary_ref`, `known_page_type`,
  `navigation_history_summary`, `active_frame_or_context`,
  `matches_required_state`.

PRD v2.3 reinforcement:

- **`02_LLM_RUNTIME.md` line 444** — pending step / `plan_ready` /
  `step_recorded` payloads must allow `expected_outcome` and `observed_outcome`.
- **`02_LLM_RUNTIME.md` lines 696, 1243–1244** — output schema includes
  preconditions/postconditions.
- **`04_BACKEND_EVENT_CONTRACT.md` lines 67–74** — typed events must carry
  expected outcome through `pending step / plan_ready / step_recorded /
  save_snapshot`.

---

## 2. Code today — current step schema fields

Production step schema lives in two places; neither matches the spec.

### 2a. `runtime/journey_plan.py` (the only typed step model)
`JourneyStep` dataclass — `runtime/journey_plan.py:40–50`:

| Field present | Type |
|---|---|
| `step_id` | str |
| `description` | str |
| `page_required` | str (plain string, not the §23.14 page_state object) |
| `preconditions` | list[str] (strings, not typed objects) |
| `postconditions` | list[str] |
| `expected_outcome` | str (no category) |
| `required_test_data` | list[str] |
| `risk_metadata` | dict |
| `capability_gaps` | list[str] |
| `operations` | list[ChildOperation] |

`ChildOperation` — `runtime/journey_plan.py:30–36`:
`operation_id`, `operation_type`, `target_description`, `locator_hint`,
`expected_outcome` (str), `capability_status`. No `precondition`,
`postcondition`, `depends_on`, `locator_scope`, `page_snapshot_ref`.

`validate_draft_plan` — `runtime/journey_plan.py:105–113` only requires
`step_id` and `expected_outcome` truthy. Nothing else is enforced.

### 2b. `agent.py` live step context (the running runtime)
Built in `_prepare_recording_steps` at `agent.py:3534–3567`. Fields stored
per step:

```
step_id, step_number, intent, element_info, element_name, locator,
last_error, status, recorded, expected_outcome
```

Click-like steps additionally require `expected_outcome.type`
(`agent.py:3487–3493`). No `precondition`, no `postcondition`, no
`required_page_state`, no `depends_on_step_ids`, no `locator_scope`,
no `source_page_url`, no `page_snapshot_ref`.

`_normalize_expected_outcome` (`agent.py:3212–3233`) accepts only
`{type, required, description}` — does not match the §21.7 typed category
list and does not carry assertion target/locator scope.

### 2c. `runtime/page_state_model.py`
Defines `PageStateDependency` (lines 16–21) and
`PreconditionCheckResult` (23–28). `check_page_precondition`
(line 30) reads `step.page_required` and returns blocked/reason. **The
expanded schema documented in `.tasks-md/Planning/S6-0406…md:113–135`
(`PageStateRequirement`, `PageStateChange`, `OperationWithPageState` with
`source_page_url`, `required_page_state`, `postcondition`,
`depends_on_step_ids`, `locator_scope`, `page_snapshot_ref`,
`section_snapshot_ref`) is NOT implemented.**

### 2d. `runtime/event_contracts.py`
`_PRECONDITION_TYPES` — line 853: only four types allowed
(`page_url`, `element_present`, `auth_state`, `data_ready`). No
`page_state_mismatch` type per spec §5.4 line 501.
`build_precondition_failed_event` — line 1060 — payload carries
`run_id`, `step_id`, `precondition_type`, `expected`, `actual`,
`operation_id?`, `options`. Missing the §21.3 payload fields
`required_page_state`, `current_page_state`, `required_url_or_pattern`,
`current_url`, plus §23.14 `page_state_id`.

---

## 3. Precondition check flow

Spec §3.8 / §10 / §15.6 / §6 line 551: backend must run
`operation_precondition_check` (§6 line 551) and
`step_precondition_check_started` (§10 line 1009) **before** every step's
locator/action and emit `precondition_failed` with deterministic resolution
options when mismatched.

Code today:

- `check_page_precondition` (`runtime/page_state_model.py:30`) is the only
  production helper. It is referenced **only by tests**
  (`tests/test_journey_plan_schema.py:217, 227`,
  `tests/test_complete_llm_mode_integration.py:65`). **No call site in
  `agent.py`, `server.py`, `runtime/llm_runtime_controller.py`,
  `runtime/multi_step_queue.py`, or `runtime/recovery_pipeline.py`.**
- `build_precondition_failed_event` (`runtime/event_contracts.py:1060`) is
  referenced **only by tests**
  (`tests/test_execution_lifecycle_events_contract.py:25, 177, 192, 206,
  221, 229`). **No production emitter.**
- The only live precondition gate is **replay-only**:
  `_check_replay_precondition` (`agent.py:823–889`) compares
  `recorded.before_url` to current browser URL and validates the recorded
  locator. It fires **after** a recorded step exists; it never runs for the
  first-time forward execution path called from `run()` at `agent.py:1471`.
- The execution lifecycle (`execution_started` →
  `operation_locator_validated` → `operation_executed`) in `agent.py` and
  `runtime/event_contracts.py:884` (`build_execution_started_event`,
  `build_operation_executed_event`) emits no `precondition_check_started`
  or `precondition_failed` event before action dispatch.

Result: **§3.8 precondition flow does not exist for forward execution**.
Only replay enforces a URL/locator gate.

---

## 4. Postcondition flow

Spec §3.8, §21.7, §23.5: every step records a postcondition; after action,
backend captures `observed_outcome` and validates it against
`postcondition` / `expected_outcome` (§6 line 554
`observed_outcome_captured`).

Code today:

- `JourneyStep.postconditions` is `list[str]` (free-form, not typed).
  `validate_draft_plan` does not enforce postcondition→precondition
  matching (the S6-0406 invariant at planning task line 148).
- Agent stores `expected_outcome` in the step context but never compares it
  against an `observed_outcome` field. `recorded_step_payloads`
  (`agent.py:621–626`) contains `observed_outcome` only as a copy from the
  recorded payload — there is no postcondition validator path. Grep for
  `observed_outcome` validation returns no comparator.
- No `step_precondition_check_started`,
  `precondition_resolution_options_ready`, `observed_outcome_captured`,
  `page_state_mismatch`, or `change_postcondition` events are emitted from
  production code. (Spec event names from §6, §10, §23.4 line 2139.)

---

## 5. `depends_on_step_ids`

Spec §3.8 line 190, §15.6 line 1385, §23.5 line 2171, §23.7 line 2231,
plus S6-0503 plan-diff validator
(`.tasks-md/Planning/S6-0503…md:145, 164`) require dependency-graph
ordering and reorder validation.

Code today:

- **`depends_on_step_ids` does not appear in any Python source file** under
  `runtime/` or in `agent.py`/`server.py`. Grep restricted to `*.py`
  excluding `__pycache__` returns only spec/task documents
  (`autoworkbench_…spec (2).md`, S6-0406/S6-0503 planning notes).
- `DraftPlan.dependencies` (`runtime/journey_plan.py:60`) exists as a
  plan-level `list[str]` but is unused — `build_draft_plan` returns `[]`
  and `validate_draft_plan` does not consult it.
- No partial-rerun / reorder validator consumes the graph. Step ordering
  is positional list index only.

---

## 6. Gap matrix

| Field / flow | Status | Exact gap | Fix sketch (no code) |
|---|---|---|---|
| `required_page_state` (typed object §23.14) | Missing | Only `JourneyStep.page_required: str` and `agent.py` step context with no page field | Replace `page_required: str` with `PageStateRequirement` (URL pattern, title_contains, page_state_id, known_page_type, visible/hidden hints); persist on every plan step and recorded step |
| `precondition` (per-step / per-operation) | Missing | `JourneyStep.preconditions: list[str]`; no typed shape; `ChildOperation` has no precondition field | Make precondition a typed object (kind ∈ {page_url, element_present, auth_state, data_ready, page_state_mismatch}, expected, source_step_id, recoverable_options) on both step and child op |
| `postcondition` (per-step / per-operation) | Missing | `JourneyStep.postconditions: list[str]`; `ChildOperation` lacks it; no observed-vs-postcondition compare | Add typed `postcondition` mirroring §21.7 categories; emit `observed_outcome_captured` after every operation_executed and compare |
| `expected_outcome` typed category | Partial | `_normalize_expected_outcome` accepts {type, required, description} only; not constrained to the 10 categories in §21.7 lines 1953–1963 | Restrict `.type` to the enum; require `assertion_hint` for `content_changes`; persist into `step_recorded` payload |
| `depends_on_step_ids` | Missing | Field never declared in any module | Add `depends_on_step_ids: list[str]` to step model; populate during planning (auto-derive navigation deps); validate on reorder/delete (`steps_updated` → `dependency_warning`) |
| `locator_scope` | Partial | `change_locator_scope` command exists (`server.py:1209`, `event_contracts.py:29`) but no scope field stored on step | Store `locator_scope` per operation in step state and in `step_recorded` payload; expose via `locator_state.locator_scope` (§23.8) |
| `source_page_url`, `page_snapshot_ref`, `section_snapshot_ref` | Missing | Not in journey_plan, page_state_model, or agent context | Add to step model and recorder; capture from `page_intelligence_live` outputs |
| Precondition check before action | Missing | `check_page_precondition` defined but never called from forward path; `_check_replay_precondition` runs only on replay | Insert a gate in the run loop (between `execution_started` and `operation_locator_validated`) that calls `check_page_precondition` and emits `step_precondition_check_started` + `precondition_failed` |
| `precondition_failed` event payload completeness | Partial | Missing `required_page_state`, `current_page_state`, `required_url_or_pattern`, `current_url`, `available_resolution_options` (§21.3 lines 1849–1857) | Extend `build_precondition_failed_event` payload; add `page_state_mismatch` to `_PRECONDITION_TYPES` (line 853) |
| `precondition_resolution_options_ready` | Missing | Event not implemented | New emitter mirroring the §10 lines 1027–1032 option set (navigate / replay_dependency_steps / ask_user / skip / stop) |
| Postcondition validation after action | Missing | No comparator | After `operation_executed`, capture current URL/title/visibility; validate against step.postcondition; emit `observed_outcome_captured`; if mismatch, route to recovery |
| `page_state` state object (§23.14) | Missing | No struct; `_capture_browser_state` returns ad-hoc `{url, title}` | Introduce `PageState` dataclass with current_url, current_title, page_state_id, page_summary_ref, known_page_type, navigation_history_summary, active_frame_or_context, matches_required_state |
| `locator_state.requires_page_state`/`last_validated_page_state`/`can_live_validate` | Missing | No locator_state object emitted for Steps Mode | Per §21.6 / §23.8, emit locator_state per step/op with these three fields |
| Partial-rerun / dependency-aware execution | Missing | No graph; positional only | After adding `depends_on_step_ids`, expose `replay_dependency_steps` resolution option (§10 line 1028) and use the graph in `multi_step_queue` |

---

## 7. Acceptance hook — PRD 06 Phase 2 test 5

`PRD_v2_3_Modular_Pack_v2/06_BUILD_ROADMAP_AND_ACCEPTANCE.md:172`:

> "Click navigates before old-page assertion → recovery asks/repairs → no
> finalization while unresolved."

Required machinery for the test to pass:

1. Step N+1 must declare `required_page_state` = old page.
2. Before executing step N+1, runtime must compare current URL/state to
   `required_page_state` and detect mismatch (current = new page after
   click). **Blocked**: forward-path precondition check is unimplemented
   (Section 3 above).
3. Mismatch must emit `precondition_failed` with resolution options.
   **Blocked**: event exists but is never emitted in production; payload
   missing `required_page_state` / `current_page_state` fields.
4. Recovery must consult `depends_on_step_ids` to offer "replay dependency
   steps." **Blocked**: field absent everywhere.
5. Step Runner must not finalize the run while the precondition is
   unresolved. **Partially OK**: `saw_step_recorded` guard
   (`agent.py:2078, 2432, 2454`) prevents finalization without a recorded
   step, but does not block on precondition state because no
   precondition state machine exists.

Net effect: test 5 cannot pass with current code. The minimum unblock is
items 1–4 in the gap matrix.

---

## 8. Conflict / overlap with other lanes

- **DG1 (recording)** — `agent.py:621` `_append_recorded_step_payload` is
  the canonical writer of recorded step payloads. Adding `precondition`,
  `postcondition`, `required_page_state`, `depends_on_step_ids`, and
  `locator_scope` to the recorded payload schema must be coordinated so
  DG1 does not strip unknown fields, and so the §23.9 `recorded_step_detail`
  shape (lines 2290–2307) is consistently materialised. Replay path
  (`_check_replay_precondition`, `agent.py:823`) already reads
  `recorded_step_payload` — its keys (`before_url`, `children`) overlap
  with the new schema; renaming/extending must keep backward compat for
  saved sessions in repo root (`rv5-suite_*.json`, `live-suite_*.json`).
- **DG3 (classifier)** — `runtime/failure_classifier.py` and the
  intent/correction classifier owns the `page_state_mismatch` →
  `precondition_failed` route (spec §5.4 line 501, §6 line 551). Adding
  `page_state_mismatch` to `_PRECONDITION_TYPES`
  (`event_contracts.py:853`) requires DG3 to map locator/action failures
  with wrong-URL evidence into this category instead of
  `locator_not_found`. Without DG3 buy-in, mismatches will keep being
  classified as locator failures and routed to the locator-repair pipeline
  rather than the precondition resolution pipeline.
- **Plan-diff lane (S6-0503/S6-0505)** — both planning tasks already
  reference `depends_on_step_ids` for diff validation; this audit's gap is
  the upstream provider. Once the field lands, DG3's
  `dependency_warning` / `blocking_error` emission (§23.7 lines 2240–2251)
  can be wired without further schema churn.

---

## 9. Key file references

- `/Users/apple/personal/agent v4/runtime/journey_plan.py` — current step
  schema (lines 21–113).
- `/Users/apple/personal/agent v4/runtime/page_state_model.py` — minimal
  precondition helper (lines 14–46); production-unused.
- `/Users/apple/personal/agent v4/runtime/event_contracts.py` —
  `_PRECONDITION_TYPES` (853), `build_precondition_failed_event` (1060),
  `_DEFAULT_PRECONDITION_OPTIONS` (1051).
- `/Users/apple/personal/agent v4/agent.py` — `_check_replay_precondition`
  (823), `_prepare_recording_steps` (3534), `_normalize_expected_outcome`
  (3212), forward run loop entry `run()` (1471).
- `/Users/apple/personal/agent v4/.tasks-md/Planning/S6-0406 Multi-page dependency and page-state model.md` — designed-but-not-built expanded schema (lines 113–164).
- `/Users/apple/personal/agent v4/.tasks-md/Planning/S6-0407 Wrong-current-page precondition flow.md` — wrong-page handling spec (status: Planning, blocked by S6-0406).
