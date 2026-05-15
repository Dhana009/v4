# 2026-05-15 — Backend-Owned Execution / Recording / code_update Gap Audit

Scope: identify gaps between PRD v2.3 + Complete LLM Mode P0 spec and the current implementation for **backend-owned execution, step recording, and `code_update` emission**. Read-only audit. No code changes proposed; only minimum-fix sketches for follow-up.

References:
- P0 §3.1 backend-owns list, §6 event pipeline, §16 P0 item "backend-owned execution/recording/code_update" — `autoworkbench_complete_llm_mode_p_0_scenarios_spec (2).md`
- Runtime policy §4 deterministic-first list, §6.3 "no model" list — `autoworkbench_complete_llm_mode_runtime_policy_spec.md`
- PRD 01 §scenarios 1, 5, 6; PRD 05 v2.3 recording model + workspace storage; PRD 06 Phase 2 acceptance + tests 1, 2, 3, 5.

---

## 1. What the spec requires

1. **Backend owns lifecycle truth** — recording and code_update belong to the backend; LLM may propose, the runtime decides (P0 §3.1 lines 60–71; runtime §6.3 lines 199–213).
2. **Event-driven lifecycle** — every transition is a typed event including `recording` events and `codegen` events (P0 §3.2 lines 81–99).
3. **Deterministic-first recording/codegen** — no LLM call should produce the recorded step or code lines (runtime §4 lines 101–114).
4. **Canonical pipeline** — `operation_executed → observed_outcome_captured → step_recorded → code_update → run_completed` (P0 §6 lines 540–558).
5. **Parent step + child operations** — recorded step is a parent containing child operations with per-op `locator`, `status`, `code_lines` (PRD 05 lines 6–34).
6. **Multi-action expansion** — a section/multi-intent step decomposes into ordered child operations; codegen expands each child to lines (PRD 01 Scenario 3 lines 78–98; P0 Scenario 1 line 670 "upload/fill/submit/assertions").
7. **Unresolved-failure rule** — `failed unresolved step does not record/code_update` (P0 line 1129; PRD 01 Scenario 6 line 168).
8. **Expected/observed outcome** — recorded payload must include `expected_outcome` (PRD 05 §"Expected Outcome Capture" lines 660–688) and `observed_outcome` for evaluation (lines 695–705).
9. **Workspace-based storage** — outputs default to active workspace (`<workspace>/autoworkbench-output/`), not hardcoded `.hermes` (PRD 05 lines 44–72).
10. **Replay must not mutate recording unless validated repair accepted** (PRD 05 lines 91–96).
11. **Capability gap on unsupported action**, never fake the record (P0 Scenario 1 line 671 "capability_gap_recorded"; PRD 01 Scenario 9 lines 218–235).
12. **Codegen reviewer rule** — deterministic Playwright TS lines remain primary path; reviewer optional (PRD 05 lines 122–140).

---

## 2. What the code does today

- `AgentLoop._record_step_payload` at `agent.py:6785-6948` is the canonical backend record path; emits `step_recorded` (6819) then builds + emits `code_update` (6847–6858).
- Recording is **driven by the LLM tool `send_to_overlay(message_type="step_recorded")`** (declared at `agent.py:8880-8881`; tool list at `agent.py:8870+`; the inbound dispatcher path runs at `agent.py:9221-9237` and at `llm/tool_dispatcher.py:274-290`). The deterministic auto-record path exists as a backup (`_auto_record_successful_step`) and is called when the LLM omits the tool (`agent.py:2153, 2435, 2799`).
- `_build_step_record_payload` at `agent.py:7555-7715+` deterministically synthesizes the recorded payload from `self.last_successful_action` / `successful_actions_by_step_id`, derives `locator`, `element_name`, `generated_line`, expands `children` via `_build_recorded_children`, attaches `expected_outcome` (7665–7673) and `observed_outcome` (7695, builder at `agent.py:7099-7141`).
- `_build_code_update_payload` at `agent.py:8323-8358` derives code lines deterministically from `children[*].code_lines` and emits `{step_id, operation_id, lines, full_spec_preview, diagnostics: []}`.
- `recording/recorder.py:34` and `recording/codegen.py:32` are thin shims — they call back into `AgentLoop._build_step_record_payload` / `_build_code_update_payload`. There is **no independent recording module**; recording state lives on `AgentLoop`.
- Awaiting-record guard: `_awaiting_step_record` set at `agent.py:7237, 7243`, enforced at `agent.py:2143-2188` ("RECORDING_GUARD blocked tool while awaiting_step_record"). Unblock guard before record at `2129-2141` and pre-confirmation block at `2113-2126`.
- `_has_successful_action_to_record` (called at `agent.py:6796`) prevents recording when no successful action exists — this is the "unresolved failure does not record" enforcement.
- Workspace save path: `runtime/session_store.py:103-106` defaults to `AUTOWORKBENCH_WORKSPACE or os.getcwd()` and writes `<workspace>/<name>_<ts>.json`. `server.py:457-482` writes generated spec to `<workspace>/autoworkbench-output/` only inside the `export_code` flow (D-103). `save_session` (server.py:895-937) does NOT route through `autoworkbench-output/`.
- `observed_outcome` builder (`agent.py:7099-7141`) only classifies `navigation` vs `no_visible_change`; no modal/dropdown/toast/new_tab/download/content_change detection. `matched_expected` only set if observed_type != unknown.
- `expected_outcome` normalization at `agent.py:3212-3235`; `_is_click_like_intent` (3225-area) makes it required for click intents — matches PRD 05 §"Required for click actions".
- Capability gap recording: `_record_capability_gap` at `agent.py:558-601`, invoked at `agent.py:2641`. Run-completion payload includes `capability_gaps` (1238–1261). No persistent workspace gap-log file is written.
- Replay: `replay_one` `agent.py:929-988`, `replay_all` `agent.py:1083+`. Replay precondition guard `agent.py:702-928`. Replay does not mutate `recorded_step_payloads` (no overwrite path observed); LLM repair loop during replay is **not wired** — `replay_one` simply re-executes recorded supported actions and returns ok/error (no `recovery_needed` emission inside replay).

---

## 3. Gap matrix

| # | Requirement | Status | Exact gap | Minimum fix sketch |
|---|---|---|---|---|
| G1 | Recording must be backend-owned/deterministic (P0 §3.1; runtime §6.3) | partial | LLM still drives the record via `send_to_overlay(message_type="step_recorded")` tool exposed at `agent.py:8880-8881` and dispatched at `agent.py:9221-9237`; deterministic `_auto_record_successful_step` is only a fallback. Spec forbids LLM as source of truth. | Remove `step_recorded` from `send_to_overlay` enum + tool dispatcher; always auto-record from `_capture_action_context` once `_awaiting_step_record` & step_ready. Keep LLM unable to suppress/forge recording. |
| G2 | code_update is backend-owned deterministic (runtime §4, §6.3) | ✅ | `_build_code_update_payload` is deterministic from `children[*].code_lines`; emitted only via `_record_step_payload`. No LLM-driven path. | None. |
| G3 | code_update emitted for every successful operation, not just parent recording (PRD 06 Phase 2 "code_update for successful operations"; P0 line 670) | partial | code_update fires once per parent step at `agent.py:6847-6858`; it includes all child lines, but `operation_id` is taken from the **first** success child only (`agent.py:8338-8342`). Child-level `code_update` per operation is not emitted. | Either emit one `code_update` per recorded child operation, or extend payload with `operations:[{operation_id, lines}]`. |
| G4 | Parent + child decomposition for multi-action intent (PRD 05 v2.3 model; PRD 01 Scenario 3) | partial | `_build_recorded_children` exists and confirmed-plan children are honored, but in non-confirmed-plan mode a single successful action becomes a single child (no decomposition for "validate this section"). | Drive children from confirmed plan contract always; require confirmed plan before any multi-action execution. |
| G5 | Unresolved failure must not record/code_update (P0 line 1129; PRD 01 Scenario 6) | ✅ | `_has_successful_action_to_record` (`agent.py:6796`) and `result.get("success") is not True` check (`agent.py:7611`) plus `pending_recovery` guard at `agent.py:6505` prevent it. | None. |
| G6 | expected_outcome required for click + plumbed into recorded payload (PRD 05 §10 v1) | ✅ | `_normalize_expected_outcome` (`agent.py:3212`) + `_is_click_like_intent` enforces required; included in record at `agent.py:7712-7713`. | None. |
| G7 | observed_outcome captured per operation (PRD 05 §6 runtime, §10 v1 step 4) | partial | Only `navigation` / `no_visible_change` classified (`agent.py:7119-7124`); modal/dropdown/toast/new_tab/download/content_change/file_picker never set; observed lives at parent-step level not per-child. | Classify based on after-state diff signals (dialog count, tab count, toast/message visibility); attach `observed_outcome` per child in `_build_recorded_children`. |
| G8 | Workspace-based default storage `<workspace>/autoworkbench-output/` (PRD 05 lines 44–72) | partial | `save_session_to_file` writes to `<workspace>/<name>_<ts>.json` (root), not `autoworkbench-output/` (`runtime/session_store.py:103-106`). Only `export_code` honors that subdir (`server.py:457-462`). | Update `save_session_to_file` default path to `os.path.join(workspace, "autoworkbench-output", filename)`; ensure dir is auto-created. |
| G9 | Hidden internal under `<workspace>/.autoworkbench/` (PRD 05 line 60) | ❌ | `agent.py:9135` still uses hardcoded `.hermes/screenshots`. | Use `<workspace>/.autoworkbench/screenshots`. |
| G10 | step_recorded includes all PRD 05 v2.3 fields per child (`operation_id`, `type`, `locator`, `assertion`, `expected`, `status`, `code_lines`) | partial | `_build_recorded_children` populates these for known confirmed-plan flows, but for non-confirmed action paths the child fabricates `op_1` without `type` taxonomy match (assert/click/fill). Need to confirm parity by reading `_build_recorded_children` (not loaded in this audit). | Audit `_build_recorded_children`; enforce required keys & schema-validate before emit. |
| G11 | Codegen Reviewer hook for high-risk flows (PRD 05 lines 122–140) | ❌ | No reviewer call site; `_build_code_update_payload:8323` emits without any review step. | Add optional reviewer pass behind feature flag; runtime §6.2 (main model) only when triggered (popup/auth/locator-replacement/replay repair). |
| G12 | Replay does not mutate recording unless validated repair accepted (PRD 05 lines 91–96; PRD 06 Phase 3) | partial-not-needed-now | Replay paths (`agent.py:929+`, `1083+`) do not overwrite recorded payloads; **but** LLM repair-during-replay loop is absent. Phase 3 scope, not Phase 2 — note for downstream. | Out of scope for Phase 2. Track for Phase 3. |
| G13 | Capability gap persisted to active workspace (PRD 01 Scenario 9; P0 line 671) | partial | `_record_capability_gap` keeps gaps in-memory and includes them in `run_completed`; nothing writes to `<workspace>/.autoworkbench/capability-gaps.json` or similar. | Append each gap to `<workspace>/.autoworkbench/capability-gaps.json`. |
| G14 | Event taxonomy: emit `step_recorded` and `code_update` as typed events on backend channel (P0 §6, PRD 04 contract) | partial | Both are sent via `self._send(...)` which is the WS overlay channel, not via the typed `runtime/event_contracts.py` builders (no `build_step_recorded_event` / `build_code_update_event` exists in `event_contracts.py`). | Add typed builders + `emitted_at` + `run_id` envelopes; route through the same path as other typed events. |
| G15 | "Backend owns step identity" (P0 §3.1 line 66) | partial | `step_id` is sometimes taken from LLM payload first (`agent.py:7619-7625`). | Always derive step_id from confirmed plan / active step cursor; ignore LLM-supplied step_id on record. |

---

## 4. Acceptance hooks — mapping to PRD 06 Phase 2 tests

PRD 06 lines 168–180 tests (Phase 2-relevant):

1. **Test 1** "Pick one button → click → confirm → recorded → code line" — blocked by **G1** (LLM still source of truth on the recording call) and **G14** (typed event channel). G6 satisfied.
2. **Test 2** "Pick one heading → has_text assertion with `&nbsp;` → recorded → code line" — blocked by **G1**, **G10** (child `type=assert` + `assertion=has_text` + `expected` field), **G14**.
3. **Test 3** "Select section → multi-assertions/actions → parent + child operations" — blocked by **G4** (non-confirmed-plan decomposition), **G3** (per-child code_update), **G10**, **G1**.
4. Test 5 "Click navigates before old-page assertion → recovery, no finalization while unresolved" — already covered by **G5** ✅ and `pending_recovery` guard.
5. PRD 06 Phase 2 acceptance bullet "code_update for successful operations" — blocked by **G3**.

Storage acceptance (PRD 06 acceptance matrix line: "output defaults to active workspace; custom save path supported") — blocked by **G8**, **G9**.

Phase 3 tests 6–7 (replay repair, locator replacement) — not gated by this audit beyond noting **G12** is deferred.

---

## 5. Risk / conflict notes for the implementer

- **`agent.py` is the only emit point** for `step_recorded` (`agent.py:6819`) and `code_update` (`agent.py:6850`). Any rewrite must keep these as the single source. `recording/recorder.py:34` and `recording/codegen.py:32` are pass-throughs and must not start emitting independently.
- Two write paths into the same emit: deterministic auto-record (`_auto_record_successful_step` → `_record_step_payload`) AND LLM-driven (`send_to_overlay(step_recorded)` → `agent.py:9221-9237` → `_emit_run_completed_event(payload, recorded_payload)`). Removing G1 must ensure the second path is fully retired *and* the awaiting-record guard at `agent.py:2143-2188` is not left dangling without an LLM unblock signal.
- `self._awaiting_step_record` is set in three places (`agent.py:7237, 7243; reset at 6889, 3542, 3708, 9178, 9193`) and observed by `plan/confirmation.py:187, 202`. Centralize state changes in `_capture_action_context` and `_record_step_payload`.
- `self.recorded_step_payloads`, `self.code_update_payloads`, `self.replay_recorded_step_payloads_by_step_id`, `self.successful_action_by_step_id`, `self.successful_actions_by_step_id`, `self.replay_action_history_by_step_id` are all mutated inside `_record_step_payload`. Any new typed-event refactor must keep these caches consistent for the spec snapshot (`_build_spec_snapshot` consumed by `server.py:904`).
- `_build_spec_snapshot` (consumed at `server.py:904`) is the bridge to `save_session_to_file` (`runtime/session_store.py:89`). Changing the default save path (G8) must be coordinated with `server.py:457-482` `export_code` to avoid two divergent defaults.
- `run_completed` emission (`_emit_run_completed_event` near `agent.py:6942`, builder at `runtime/event_contracts.py:224`) carries the recorded payload; ensure new typed `step_recorded` / `code_update` builders share its envelope conventions (`emitted_at`, `run_id`).
- `observed_outcome` widening (G7) touches the same `_normalize_browser_state_snapshot` already used by recovery and replay precondition; do not change its shape — add new fields, do not rename.
- Capability-gap persistence (G13) must use `<workspace>/.autoworkbench/`; do not write to `.hermes/*`, which is now legacy per PRD 05 lines 60–64.

---

## 6. Already satisfied (do not redo)

- G2 deterministic `code_update` payload builder.
- G5 unresolved-failure guard.
- G6 `expected_outcome` required-for-click + plumbed.
- Pre-confirmation execution + record blocks (`agent.py:2113-2141`).
- Replay precondition guard (`agent.py:702-928`).
- Recording-guard tool-block while awaiting record (`agent.py:2143-2188`).
