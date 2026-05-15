# Sprint 7 Wrap-Up — Master Spec

**Status:** ACTIVE — drives Sprint 7 closeout.
**Branch:** `s7/clusters-6-11-complete-llm-mode`
**Spec authored at HEAD:** `6c34187 docs: record D-102 Recorded tab evidence view completion`
**Date:** 2026-05-14

This document is the primary planning artifact for Sprint 7 closeout. It is
referenced by every per-defect mini-spec, the final handoff doc
(`SPRINT-007-HANDOFF.md`), and the refactor audit
(`.tasks-md/Audit/S7_MODULARIZATION_AUDIT.md`). A secondary copy may live
under `docs/superpowers/specs/`; the canonical copy is here.

---

## 1. Source Hierarchy and Documents Checked

Authoritative source order (top wins on conflict):

1. PRD v2.3 modular pack — `PRD_v2_3_Modular_Pack_v2/`
   - `00_MASTER_INDEX.md`
   - `01_PRODUCT_WORKFLOWS.md`
   - `02_LLM_RUNTIME.md`
   - `03_FRONTEND_RUNTIME.md`
   - `04_BACKEND_EVENT_CONTRACT.md`
   - `05_CODEGEN_REPLAY_PERSISTENCE.md`
   - `06_BUILD_ROADMAP_AND_ACCEPTANCE.md`
   - `07_MULTI_MODEL_ORCHESTRATION.md`
2. Complete LLM Mode runtime policy spec (`autoworkbench_complete_llm_mode_runtime_policy_spec*.md` if present at repo root)
3. Frontend UI spec (`autoworkbench_complete_llm_mode_frontend_ui_spec*.md` if present)
4. P0 scenarios spec (`autoworkbench_complete_llm_mode_p_0_scenarios_spec*.md` if present)
5. Sprint 6 handoff — `.tasks-md/Sprints/SPRINT-006-HANDOFF.md`
6. Sprint 7 handoff — `.tasks-md/Sprints/SPRINT-007-HANDOFF.md`
7. V4 test-id contract — `.tasks-md/Audit/V4_TESTID_CONTRACT.md`
8. UI defects log — `.tasks-md/Audit/UI_DEFECTS.md`
9. Design reference (NON-AUTHORITATIVE for runtime) — `frontend_new_design_prototype/v4/`

**Conflict rule:** if v4 UI behavior and PRD diverge, **PRD wins** unless the
user explicitly approves UI-driven behavior in writing and the deviation is
recorded in this spec under §15 Stop Conditions Resolved. Static prototype
runtime state never becomes production truth — design pack is layout/labels
reference only.

PRD v2.2 archive is reference-only; v2.3 supersedes it on every conflict.

---

## 2. Goal and Non-Goals

**Goal.** Sprint 7 is complete only when **Complete LLM Mode is development-
complete under the PRD-P0-only seam rule.** Concretely:

- PRD-P0 controls are wired through typed dispatcher and tested.
- PRD-P0 backend/LLM/runtime seams are implemented or already-existing seams
  are wired through.
- Non-P0 controls are disabled-with-reason or hidden, with ticket and tooltip.
- No visible v4 control is active but non-functional.
- No static/mock data is treated as runtime truth in the production path.
- Full local E2E suite is either green or every failure is classified with an
  exact bug ticket + root-cause layer.
- Backend/LLM/runtime/frontend/tests reconciled against PRD per §7.

**Non-goals (Sprint 7 closeout).**

- Broad risky refactors. Sprint 7 ships an **audit doc only** at
  `.tasks-md/Audit/S7_MODULARIZATION_AUDIT.md`. Safe behavior-preserving
  extractions are allowed only if (a) characterization tests already cover the
  unit and (b) the extraction is committed separately from any product fix.
- Paid LLM usage in tests or runs. See §10 for the gate rule.
- Live external-website E2E. Sprint 9 scope.
- Manual exploratory hardening, realistic-fixture E2E expansion. Sprint 8 scope.
- Any new feature beyond PRD-P0 closure.

---

## 3. Architecture Invariants (frozen)

These are inherited from prior sprints. Spec-level breach = blocker.

- Backend owns runtime truth.
- LLM proposes and reasons only.
- Frontend renders typed backend/store truth and sends typed commands only.
- DOM / Page Intelligence provides context and candidates, never gates execution.
- Trace and artifacts are evidence only — no command surface.
- Recording and `code_update` must be backed by backend evidence.
- Frontend must not infer lifecycle, completion, or recording truth.
- No `code_update` before `step_recorded` for the same operation.
- No `run_completed` while recovery is open.
- No skipped or xfailed tests added without ticket + handoff entry.
- No paid LLM or live-website tests unless explicitly approved per turn.

---

## 4. Current Checkpoint (must verify before any code change)

| Item | Value |
|---|---|
| Branch | `s7/clusters-6-11-complete-llm-mode` |
| HEAD at spec authoring | `6c34187 docs: record D-102 Recorded tab evidence view completion` |
| Working tree | clean (verified pre-write) |
| Remote | `origin/s7/clusters-6-11-complete-llm-mode` (local ahead 19) |
| jsdom | 79 / 79 passed |
| pytest non-E2E | 2578 passed, 1 skipped, 2 xfailed |
| `npm run build` | OK |
| `test_v4_panel_smoke.py` | PASS |
| `test_mvp_001_lifecycle_smoke.py` | PASS |
| D-101 visual seams | DONE (Pass 4a/4b-1..4b-6) |
| D-101 command-only gaps | OPEN — `improve_locator`/`view_candidates`, blocked-action resolve, `change_precondition`/`navigate_to_expected` |
| D-102 Recorded tab evidence view | DONE (Pass 5) |
| D-103 Code tab | OPEN |
| D-104 Trace tab | OPEN |
| D-105 Manual Mode | OPEN |
| D-106 Agent popover | OPEN |
| D-107 Composer pick/camera | OPEN |
| D-108 Mock/static gating audit | OPEN |

Any pass that begins under this spec must first run `git status --short --branch`,
`git rev-parse HEAD`, and `git log --oneline -15` and refuse to start if the
tree is dirty unexpectedly.

---

## 5. PRD-P0-Only Seam Rule (precise)

For every v4 control or backend behavior the spec touches:

1. **Backend seam already exists** → wire through typed dispatcher; add
   frontend dispatch test; if backend changed add backend command-validation
   test. Fate code: `WIRE_EXISTING_SEAM`.
2. **No backend seam and PRD explicitly names it as Sprint-7 acceptance**
   (Phase 1–4 of `06_BUILD_ROADMAP_AND_ACCEPTANCE.md`, the "Must have v1"
   list, or `06 §Acceptance matrix`) → build the smallest typed seam with
   contract tests, then wire frontend, then jsdom test. Fate code:
   `BUILD_P0_SEAM`.
3. **No seam, PRD mentions feature only generally, or PRD defers, or PRD is
   silent** → disable or hide with tooltip explaining why, file ticket,
   document under §6 control inventory and in `UI_DEFECTS.md`. Fate code:
   `DISABLE_WITH_REASON` (disabled but visible) or `HIDE_AS_NON_P0` (hidden).
4. **Control is dead / handler absent / unreachable** → fate code
   `REMOVE_AS_INVALID`.
5. **Ambiguous PRD coverage** → **STOP and ask user.** Do not guess.

P0 indicator examples (positive):

- 06 Phase 1 Core runtime + contract → P0.
- 06 Phase 2 LLM Mode MVP → P0.
- 06 Phase 3 Recording/save/replay/repair/versioning → P0.
- 06 Phase 4 Manual Mode using same runtime → P0.
- 06 Must have v1 #1–#18 → P0.
- 06 Acceptance matrix LLM Mode / Recording / Replay / Locator update /
  Frontend / Backend contract / Codegen / Storage / Capability gaps → P0.

P0 indicator examples (negative):

- 06 Phase 5 advanced/polish → non-P0 (DEFER to S8/S9).
- 06 Should have → non-P0.
- 06 Deferred v2+ → non-P0.
- 07 Multi-model orchestration agent control center → non-P0 for Sprint 7
  closeout (Page Intelligence usage IS P0 because Phase 2 LLM MVP depends on
  it; the multi-model UI surfacing is not).

---

## 6. V4 Control Inventory

Source files scanned: `frontend/src/v4/chrome.jsx`, `frontend/src/v4/llm-cards.jsx`,
`frontend/src/v4/secondary-tabs.jsx`, `frontend/aw-ide-panel.jsx`.

PRD-P0 column initially seeded `TBD`; cross-walk with §7 reconciliation table
fills it. Final fate column applies the §5 rule.

| Control | Source file:line | data-testid | Surface | Current handler | Backend command | PRD-P0 | Current status | Fate | Ticket |
|---|---|---|---|---|---|---|---|---|---|
| Dock position button (right/left/top/float) | `chrome.jsx:28` | `aw-dock-${kind}` | Header | `setDock(kind)` | none | YES (06 Phase 5 covers docking, surfaced now via host) | ACTIVE | KEEP_ACTIVE | |
| Agents popover toggle | `chrome.jsx:62` | `aw-agents-toggle` | Header | `setAgentsOpen` | none | NO (07 multi-model UI) | ACTIVE (opens popover) | KEEP_ACTIVE | D-106 |
| Collapse panel button | `chrome.jsx:97` | `aw-collapse` | Header | `setCollapsed` | none | YES (FE host) | ACTIVE | KEEP_ACTIVE | |
| Settings button | `chrome.jsx:105` | none | Header | none | none | NO | DEAD_CONTROL | REMOVE_AS_INVALID | D-108 |
| Tab button (llm/steps/rec/code/trace) | `chrome.jsx:124` | `aw-tab-${id}` | TabStrip | `setTab` | none | YES (03 §FE tabs) | ACTIVE | KEEP_ACTIVE | |
| NowStrip primary action | `chrome.jsx:158` | `aw-now-primary` | NowStrip | `onPrimary` | context-routed (`confirm_plan`/`replay_all`/`pause_run`) | YES | ACTIVE | KEEP_ACTIVE | |
| Agents popover close X | `chrome.jsx:228` | `aw-agents-close` | AgentsPopover | `onClose` | none | YES (popover affordance) | ACTIVE | KEEP_ACTIVE | |
| Agent required toggle (locked) | `chrome.jsx:261` | none | AgentsPopover | disabled | none | NO | DISABLED_PENDING_SEAM | DISABLE_WITH_REASON | D-106 |
| Agent non-required toggle | `chrome.jsx:263` | `aw-agent-toggle-${key}` | AgentsPopover | none | `set_agent_enabled` (defined, not emitted; see §11) | NO (Sprint 8) | DEAD_CONTROL | DISABLE_WITH_REASON | D-106 |
| Collapsed rail expand | `chrome.jsx:299` | none | CollapsedRail | `setCollapsed(false)` | none | YES | ACTIVE | KEEP_ACTIVE | |
| Collapsed rail tab | `chrome.jsx:304` | `aw-rail-tab-${id}` | CollapsedRail | `setTab` | none | YES | ACTIVE | KEEP_ACTIVE | |
| LLM seed chip | `llm-cards.jsx:910` | `llm-seed-${word}` | LlmEmpty | `onSeed` | `user_message` | YES (01 Mode 2) | ACTIVE | KEEP_ACTIVE | |
| Clarification option | `llm-cards.jsx:114` | `clarification-option-${id}` | CardClarification | `setPick(id)` | local | YES | ACTIVE | KEEP_ACTIVE | |
| Clarification free-text | `llm-cards.jsx:140` | `clarification-free-input` | CardClarification | `setFree` | local | YES | ACTIVE | KEEP_ACTIVE | |
| Clarification submit | `llm-cards.jsx:149` | `clarification-submit` | CardClarification | `submit` | `option_selected` | YES | ACTIVE | KEEP_ACTIVE | |
| Clarification let-LLM-decide | `llm-cards.jsx:156` | `clarification-let-llm` | CardClarification | `onLetLLMDecide` | `option_selected` (`__llm_decide__`) | YES | ACTIVE | KEEP_ACTIVE | |
| Recommendation item checkbox | `llm-cards.jsx:204` | `recommendation-item-${id}` | CardRecommendation | `toggle` | local | YES (P0-scenarios §7) | ACTIVE | KEEP_ACTIVE | |
| Recommendation accept | `llm-cards.jsx:221` | `recommendation-accept` | CardRecommendation | `onAccept` | `accept_recommendations` | YES | ACTIVE | KEEP_ACTIVE | |
| Recommendation add-own | `llm-cards.jsx:231` | `recommendation-add-own` | CardRecommendation | `onAddOwn` | `add_recommendation_request` | YES | ACTIVE | KEEP_ACTIVE | |
| PlanDiff apply | `llm-cards.jsx:287` | `plan-diff-apply` | CardPlanDiff | `onApply` | `apply_plan_diff` | YES (02 §Plan Correction) | ACTIVE | KEEP_ACTIVE | |
| PlanDiff reject | `llm-cards.jsx:299` | `plan-diff-reject` | CardPlanDiff | `onReject` | `reject_plan_diff` | YES | ACTIVE | KEEP_ACTIVE | |
| PlanDiff revert | `llm-cards.jsx:306` | `plan-diff-revert` | CardPlanDiff | `onRevert` | `plan_revert` | YES | ACTIVE | KEEP_ACTIVE | |
| Plan confirm | `llm-cards.jsx:391` | `plan-confirm` | CardPlanReady | `onConfirm` | `confirm_plan` | YES | ACTIVE | KEEP_ACTIVE | |
| Plan edit | `llm-cards.jsx:403` | `plan-edit` | CardPlanReady | `onEdit` | `correction` | YES | ACTIVE | KEEP_ACTIVE | |
| Plan partial run | `llm-cards.jsx:409` | `plan-partial-run` | CardPlanReady | `onPartialRun` | `run_steps` | YES | ACTIVE | KEEP_ACTIVE | |
| Permission allow-once | `llm-cards.jsx:467` | `permission-allow-once` | CardPermission | decide | `permission_decision` | YES | ACTIVE | KEEP_ACTIVE | |
| Permission allow-plan | `llm-cards.jsx:471` | `permission-allow-plan` | CardPermission | decide | `permission_decision` | YES | ACTIVE | KEEP_ACTIVE | |
| Permission deny | `llm-cards.jsx:476` | `permission-deny` | CardPermission | decide | `permission_decision` | YES | ACTIVE | KEEP_ACTIVE | |
| Execution pause | `llm-cards.jsx:557` | `exec-pause` | CardExecution | `onPause` | `pause_run` | YES (Must-have #10) | ACTIVE | KEEP_ACTIVE | |
| Execution stop | `llm-cards.jsx:562` | `exec-stop` | CardExecution | `onStop` | `stop_run` | YES | ACTIVE | KEEP_ACTIVE | |
| Locator candidate select | `llm-cards.jsx:618` | `locator-select-${id}` | CardLocatorAmbiguity | `setPick` | local | YES | ACTIVE | KEEP_ACTIVE | |
| Locator ask-LLM | `llm-cards.jsx:635` | `locator-ask-llm` | CardLocatorAmbiguity | `onAskLLM` | `improve_locator` (D-101 gap) | YES (P0-scenarios §3.10.2) | DISPATCH_PRESENT / BACKEND_OPEN | BUILD_P0_SEAM | D-101 |
| Locator change-scope | `llm-cards.jsx:641` | `locator-change-scope` | CardLocatorAmbiguity | `onChangeScope` | `change_locator_scope` | YES | DISPATCH_PRESENT / BACKEND_TBD | VERIFY_THEN_WIRE | D-101 |
| Locator stop | `llm-cards.jsx:646` | `locator-stop` | CardLocatorAmbiguity | `onStop` | `stop_run` | YES | ACTIVE | KEEP_ACTIVE | |
| Locator confirm | `llm-cards.jsx:651` | `locator-confirm` | CardLocatorAmbiguity | `onChoose` | `choose_locator_candidate` | YES | ACTIVE | KEEP_ACTIVE | |
| Recovery apply-LLM-repair | `llm-cards.jsx:716` | `recovery-apply-llm` | CardRecovery | `onApplyRepair` | `retry_recovery` (`llm_repair`) | YES | ACTIVE | KEEP_ACTIVE | |
| Recovery retry | `llm-cards.jsx:721` | `recovery-retry` | CardRecovery | `onRetry` | `retry_recovery` (`retry_as_is`) | YES | ACTIVE | KEEP_ACTIVE | |
| Recovery choose-locator | `llm-cards.jsx:728` | `recovery-choose-locator` | CardRecovery | `onChooseLocator` | `choose_locator` | YES | ACTIVE | KEEP_ACTIVE | |
| Recovery stop | `llm-cards.jsx:734` | `recovery-stop` | CardRecovery | `onStop` | `stop_run` | YES | ACTIVE | KEEP_ACTIVE | |
| Completed replay-all | `llm-cards.jsx:801` | `completed-replay-all` | CardCompleted | `onReplayAll` | `replay_all` | YES | ACTIVE | KEEP_ACTIVE | |
| Completed save-session | `llm-cards.jsx:807` | `completed-save` | CardCompleted | `onSaveSession` | `save_session` | YES | ACTIVE | KEEP_ACTIVE | |
| Completed open-code | `llm-cards.jsx:813` | `completed-open-code` | CardCompleted | `onOpenCode` | local tab nav | YES | ACTIVE | KEEP_ACTIVE | |
| Completed download-trace | `llm-cards.jsx:819` | `completed-download-trace` | CardCompleted | `onDownloadTrace` | `trace_export` | YES | ACTIVE | KEEP_ACTIVE | |
| Offline reconnect | `llm-cards.jsx:851` | `offline-reconnect` | CardOffline | `onReconnect` | reconnect transport | YES | ACTIVE | KEEP_ACTIVE | |
| Schema repair | `llm-cards.jsx:887` | `schema-repair` | CardSchemaError | `onAskRepair` | `repair_plan` | YES | ACTIVE | KEEP_ACTIVE | |
| Composer pick-element | `llm-cards.jsx:945` | `aw-composer-pick` | Composer | none | `arm_picker` (seam exists) | YES (Composer pick is in FE spec §6.1) | DEAD_CONTROL | WIRE_EXISTING_SEAM | D-107 |
| Composer textarea | `llm-cards.jsx:932` | `aw-composer-input` | Composer | `setText` + Enter→send | `user_message` | YES | ACTIVE | KEEP_ACTIVE | |
| Composer send | `llm-cards.jsx:952` | `aw-composer-send` | Composer | `send` | `user_message` | YES | ACTIVE | KEEP_ACTIVE | |
| Composer camera/screenshot | (not yet rendered) | n/a | Composer | n/a | none | NO (not in P0 path) | MISSING | HIDE_AS_NON_P0 | D-107 |
| Steps add-step | `secondary-tabs.jsx:560` | `steps-add` | StepsTab | `onAdd` | local pending add | YES | ACTIVE | KEEP_ACTIVE | |
| Steps pick-element | `secondary-tabs.jsx:565` | `steps-pick` | StepsTab | `onPickElement` | `arm_picker` | YES | ACTIVE | KEEP_ACTIVE | |
| Steps filter | `secondary-tabs.jsx:573` | `steps-filter` | StepsTab | `setFilter` | local | YES | ACTIVE | KEEP_ACTIVE | |
| Steps run-all | `secondary-tabs.jsx:581` | `steps-run-all` | StepsTab | `onRunAll` | `run_steps` | YES | ACTIVE | KEEP_ACTIVE | |
| Steps run-selected | `secondary-tabs.jsx:592` | `steps-run-selected` | StepsTab | `onRunSelected` | `run_steps` | YES | ACTIVE | KEEP_ACTIVE | |
| Step intent input | `secondary-tabs.jsx:444` | `step-input-${stepId}` | PendingStepEditor | `onChangeIntent` | local | YES | ACTIVE | KEEP_ACTIVE | |
| Step picker candidate select | `secondary-tabs.jsx:466` | `picker-candidate-select` | PendingStepEditor | `onChangeElementTarget` | local | YES | ACTIVE | KEEP_ACTIVE | |
| Step outcome chip | `secondary-tabs.jsx:485` | `step-outcome-chip-${type}-${stepId}` | PendingStepEditor | `onChangeExpectedOutcome` | local | YES | ACTIVE | KEEP_ACTIVE | |
| Step attach-element | `secondary-tabs.jsx:507` | `step-attach-${stepId}` | PendingStepEditor | `onAttachElement` | `arm_picker` | YES | ACTIVE | KEEP_ACTIVE | |
| Step delete | `secondary-tabs.jsx:515` | `step-delete-${stepId}` | PendingStepEditor | `onDelete` | local | YES | ACTIVE | KEEP_ACTIVE | |
| Step blocked-action | `secondary-tabs.jsx:276` | `step-blocked-action-${stepId}` | StepBlockedStrip | disabled (`title="Resolve command not yet wired (Pass 4b-4.1)"`) | TBD per blocked.reason | YES (P0 unblocks Phase 2/3) | DISABLED_PENDING_SEAM | BUILD_P0_SEAM | D-101 |
| Step precondition-action | `secondary-tabs.jsx:145` | `step-precondition-action-${stepId}` | StepPreconditionStrip | disabled (`title="Change precondition command not yet wired (Pass 4b-5.1)"`) | `change_precondition` / `navigate_to_expected` | YES (Replay Precondition Guard v1) | DISABLED_PENDING_SEAM | BUILD_P0_SEAM | D-101 |
| Recorded replay-all | `secondary-tabs.jsx:679` | `recorded-replay-all` | RecordedTab | `onReplayAll` | `replay_all` | YES | ACTIVE | KEEP_ACTIVE | |
| Recorded replay-one | `secondary-tabs.jsx:776` | `recorded-replay-${id}` | RecordedTab | `onReplayOne` (disabled when no id/handler with title) | `replay_one` | YES | PARTIAL_DISABLED_WHEN_NO_ID | KEEP_ACTIVE | D-102 (closed) |
| Recorded artifact link | `secondary-tabs.jsx:853` | `recorded-artifact-${id}-${artifactId}` | RecordedTab | native nav | none | YES | ACTIVE | KEEP_ACTIVE | |
| Code copy | `secondary-tabs.jsx:922` | `code-copy` | CodeTab | `onCopy` (disabled when no code) | clipboard local | YES | ACTIVE | KEEP_ACTIVE | D-103 |
| Code save | `secondary-tabs.jsx:929` | `code-save` | CodeTab | `onSave` | `export_code` (verify) | YES | DISPATCH_PRESENT / BACKEND_VERIFY | VERIFY_THEN_WIRE | D-103 |
| Code export controls (additional) | not yet rendered | n/a | CodeTab | n/a | `export_code` payload extension | YES (06 Save options) | MISSING | BUILD_P0_SEAM | D-103 |
| Code diagnostics rows | `secondary-tabs.jsx::CodeDiagnostics` | `code-diagnostic-${i}` | CodeTab | none (render only) | none | YES | ACTIVE | KEEP_ACTIVE | D-103 |
| Trace filter input | `secondary-tabs.jsx:995` | `trace-filter` | TraceTab | `setFilter` | local | YES (FE §9) | ACTIVE | KEEP_ACTIVE | D-104 |
| Trace category chip | `secondary-tabs.jsx:1000` | `trace-filter-${k}` | TraceTab | `setKind` | local | YES | ACTIVE | KEEP_ACTIVE | D-104 |
| Trace failure-detail panel | not yet rendered | n/a | TraceTab | n/a | reads `step_failed` payload | YES | MISSING | BUILD_P0_SEAM | D-104 |
| Manual Mode toggle (header) | `chrome.jsx` (mode toggle) | tbd | Header | local `setMode` no-op | none | YES (06 Phase 4 / Must-have #1) | INERT | classify per §9 | D-105 |
| Manual Mode builder card | not rendered | n/a | StepsTab / dedicated | n/a | `manual_action` / `manual_assertion` (defined, FE not wiring) | YES | MISSING | classify per §9 | D-105 |

**Notes.**

- `VERIFY_THEN_WIRE` rows require a one-line backend-emission check before
  closing. If the backend handler exists but is untested, add the minimal
  contract test in the per-defect spec.
- Every `DISABLE_WITH_REASON` row must satisfy §8.
- Every `BUILD_P0_SEAM` row spawns work in a per-defect mini-spec (§13).

---

## 7. PRD Reconciliation Table (Sprint 7 closure)

Statuses: `WORKING` / `PARTIAL` / `CONTRACT_ONLY` / `DISABLED_WITH_REASON` /
`MISSING` / `DEFERRED_TO_SPRINT_8`. `Final` is filled at handoff time.

| PRD area | Required behavior (one line) | PRD source | P0? | Backend | LLM/runtime | Frontend | Tests | Final | Ticket |
|---|---|---|---|---|---|---|---|---|---|
| LLM Mode planning | Free intent → clarification → typed `plan_ready` before execution | `02 §Structured Plan Correction`, `01 §Mode 2` | YES | WORKING (S7-0202) | WORKING | WORKING (CardClarification + CardPlanReady) | jsdom + mvp_001 | | |
| Clarification flow | `clarification_needed` with options or free text; no exec until answered | `04 §lifecycle events`, `03 §FE modes` | YES | WORKING | WORKING | WORKING | jsdom | | |
| Recommendation review | Broad intent → grouped assertions → user accept | `P0-scenarios §7`, `FE §5.3` | YES | WORKING (S7-0202) | WORKING | WORKING (CardRecommendation; payload-gated) | jsdom | | |
| Plan review / confirm | Backend `plan_ready` → user confirms → exec | `02 §25.5`, `06 §Acceptance` | YES | WORKING (S7-0105/06) | WORKING | WORKING (CardPlanReady) | jsdom + mvp_001 | | |
| Plan correction / plan_diff | Typed correction → validated diff → corrected `plan_ready` | `02 §Plan Correction §1–13`, `P0-scenarios §9` | YES | WORKING (S7-0204) | WORKING | WORKING (CardPlanDiff payload-gated) | jsdom | | |
| Permission flow | `permission_required` → user decision → continue/deny | `P0-scenarios §12`, `FE §5.7` | YES | WORKING (S7-0104) | WORKING | WORKING (CardPermission) | jsdom | | |
| Locator ambiguity | `locator_ambiguous` / `candidate_choice_needed` → user choice | `P0-scenarios §8/§3.10`, `02 §Validation rule` | YES | WORKING (S7-0205) | WORKING | WORKING (CardLocatorAmbiguity) | jsdom | | |
| Improve-locator / view-candidates | User requests better locator anytime → regenerate, validate, choose | `P0-scenarios §3.10.2`, `05 §Locator update`, `FE §6.6` | YES | PARTIAL (`improve_locator` exists, inline-on-step path open) | PARTIAL | PARTIAL (LocatorAmbiguity card wired; step inline action missing) | needs jsdom + backend test | | D-101 |
| Recovery flow | Deterministic → LLM repair → user escalation; no finalize while open | `02 §Recovery loop`, `04 §recovery_needed` | YES | WORKING (S7-0206) | WORKING | WORKING (CardRecovery) | jsdom | | |
| Steps mode | Intent + outcome + attach + run + blocked + precondition + child ops | `FE §6 Steps tab`, `P0-scenarios §15.4` | YES | WORKING (locator/kind/children/blocked/precondition/child_count seams) | WORKING | WORKING (D-101 visual seams done; command-only gaps open) | jsdom (multiple) | | D-101 cmds |
| Manual Mode | Pick → action → assertion → dispatch via same Step Runner | `01 §Mode 1`, `06 §Phase 4`, `Must-have #1` | YES | PARTIAL (`manual_action`/`manual_assertion` defined; emission untested) | PARTIAL | MISSING (toggle inert; ManualBuilder absent) | none | | D-105 |
| Recording | Backend-owned `step_recorded` parent+children with locator/action/code | `02 §25.4`, `04 §step_recorded`, `05 §v2.3 recording`, `06 §Acceptance` | YES | WORKING | WORKING | WORKING (RecordedTab Pass 5) | jsdom (13) + source-pattern | | D-102 closed |
| Code generation | Backend emits `code_update` after each recorded op | `02 §25.5`, `04 §code_update`, `06 §Acceptance` | YES | WORKING | WORKING | PARTIAL (basic render OK; export/diagnostics richer payload open) | jsdom | | D-103 |
| Code copy/save/export/diagnostics | Full spec + per-step lines + warnings + copy/save/regenerate; no secrets | `FE §8 Code tab`, `05 §Save options`, `02 §Hard rule #8` | YES | PARTIAL (`export_code` payload extension TBD) | n/a | PARTIAL | jsdom existing | | D-103 |
| Replay one / replay all | `replay_step` / `replay_all`; precondition guard | `04 §commands`, `05 §Replay`, `05 §Precondition Guard v1` | YES | WORKING | WORKING | WORKING (LLM tab + Recorded row) | jsdom | | |
| Save / load session | `.spec.ts` + `.session.json`; auto-save after confirmed step | `04 §save_session/load_session`, `05 §One session = one output`, `06 §Phase 3` | YES | WORKING (S7-0109) | WORKING | WORKING (CardCompleted Save) | S7-0109 + jsdom | | |
| Trace timeline / filters / failure detail | Chronological events; filterable; failure-detail panel | `FE §9 Trace tab`, `P0-scenarios §3.11` | YES | WORKING (events emitted) | WORKING (telemetry events) | PARTIAL (filter chips OK; failure detail panel missing) | jsdom existing | | D-104 |
| Artifacts / redaction | Secrets never in chat/log/code; env-var refs in code | `02 §Hard rule #8`, `05 §Secrets`, `P0-scenarios §14.2` | YES | WORKING | WORKING | PARTIAL (redaction display in trace not explicit) | source-pattern | | D-104 |
| session_state reconnect | Reconnect → full state snapshot → UI reconciles | `04 §session_state`, `06 §Phase 5`, `06 §Tests #9` | YES | WORKING (S7-0110) | WORKING | WORKING | S7-0110 + jsdom | | |
| Capability gaps | `capability_gap_recorded` → workspace log → non-blocking | `02 §Capability gap logging`, `01 §Scenario 9`, `04 §capability_gap_recorded` | YES | WORKING (S7-0208) | WORKING | CONTRACT_ONLY (reducer wired; visible card minimal) | reducer test | | D-104 (visible card) |
| Human input / auth / OTP | Recovery / clarification events; auth save/load; agent waits | `01 §Auth State`, `05 §Auth`, `P0-scenarios §14.5/§14.1` | YES (auth save/load Must-have #16) | PARTIAL (auth save/load via session) | PARTIAL | PARTIAL | none specific | | DEFERRED_TO_SPRINT_8 (hardening) |
| Page Intelligence | Nano-model page summary; toggleable; required for some flows | `07 §3.2`, `04 §multi-agent events`, `06 §Multi-model track` | YES (Phase 2 LLM MVP depends on summary) | WORKING (S7-0203) | WORKING | PARTIAL (`page_analysis_started` reducer wired; summary card minimal) | reducer test | | DEFERRED_TO_SPRINT_8 (visible card) |
| Frontend docked panel + page compensation | Dock right/left/top/float; page compensates; Shadow DOM host | `03 §Docked panel`, `FE §4 Shadow DOM first`, `06 §Phase 5` | YES (Phase 5 host) | WORKING (S7-0401..0408) | n/a | WORKING (INTEGRATED) | mvp_001 + jsdom | | |
| Agent visibility / control center | `agent_settings/progress/result/failed/trace` events; UI center | `03 §Agent Control Center`, `07 §7`, `04 §agent_*`, `06 §Multi-model` | NO (Sprint 7 closure) | MISSING | MISSING | DISABLED_WITH_REASON (popover renders defaults, controls disabled) | none | | DEFERRED_TO_SPRINT_8 | D-106 |
| Composer pick / camera | Optional pre-step element/section pick before send | `01 §Mode 2`, `03 §picker`, `FE §6.1`, `02 §Scenario A` | YES (pick); NO (camera Sprint 7) | WORKING (`arm_picker`) for pick; camera N/A | n/a | DEAD_CONTROL (Composer pick); MISSING (camera) | none | | D-107 |

---

## 8. Disabled-Control Requirements

Every `DISABLE_WITH_REASON` row must satisfy all of:

1. `<button>` has `disabled` attribute (no faux-disabled styling alone).
2. `title=` attribute or visible helper text explains *why* in one sentence,
   citing ticket id and PRD section if applicable.
3. UI label text must not imply the control works (no "Click to ...";
   prefer "Coming soon — see D-XXX" or "Disabled: requires backend seam").
4. A ticket exists under `.tasks-md/Bugs/` or in `UI_DEFECTS.md` Open table.
5. jsdom test asserts: presence, `disabled` true, `title` non-empty, and
   absence of behavior on click.
6. Final handoff §14 lists the control under "Disabled controls and reasons".

**No dead clickable controls.** A control without a handler or with a no-op
handler is a defect, not a placeholder. Fates `DEAD_CONTROL` resolve to
`WIRE_EXISTING_SEAM` / `DISABLE_WITH_REASON` / `REMOVE_AS_INVALID`.

---

## 9. Manual Mode Classification

Manual Mode at Sprint 7 handoff must be classified **exactly one** of:

- **A. WORKING_FOUNDATION**
  - mode toggle flips runtime mode state
  - user can pick element from Manual Mode surface
  - selected target, action, assertion, expected value editable
  - typed `manual_action` / `manual_assertion` dispatched
  - backend validates/records via same Step Runner
  - jsdom + at least one local-fixture E2E covers minimal happy path
- **B. DISABLED_WITH_REASON**
  - toggle visible but disabled, `title` cites D-105 + ticket
  - Manual builder card hidden, not partially rendered
  - Sprint 8 ticket exists with acceptance criteria
- **C. MISSING_BLOCKER**
  - PRD-P0 demands it for Sprint 7 closure and we did not ship
  - blocks `COMPLETE_READY_FOR_SPRINT_8_TESTING` label
  - forces `PARTIAL_NEEDS_FIXES` label

**Decision.** Default fate is **B** unless §13 D-105 mini-spec proves a
minimal **A** path lands cleanly without new backend work and within the
PRD-P0-only seam rule. Manual Mode is PRD-P0 (06 Phase 4 + Must-have #1);
choosing B requires explicit user approval at handoff time recorded under §15.

---

## 10. E2E Pass Plan

Run order at the final-handoff HEAD (post-product-fixes, post-product-tests):

1. `tests/e2e/test_v4_panel_smoke.py`
2. `tests/e2e/test_mvp_001_lifecycle_smoke.py`
3. `tests/e2e/test_basic_click_flow.py`
4. `tests/e2e/test_exact_text_assertion_flow.py`
5. `tests/e2e/test_visible_assertion_flow.py`
6. `tests/e2e/test_correction_assert_then_click_flow.py`
7. `tests/e2e/test_llm_required_ambiguous_action_flow.py`

Selector style (verified): #1–#2 V4-only; #3–#7 BOTH (V4 testids via harness +
some legacy `.ide-*` class selectors). LLM dependency: #1–#2 NONE; #3–#7
FAKE-LLM via test fixtures. Browser target: all LOCAL_FIXTURE.

Per-test fate codes:

- `PASS` — record evidence (stdout snippet + duration) in handoff §13.
- `SELECTOR_DRIFT` — legacy selector fails because v4 redesign changed the
  surface. Migrate test to V4 test-ids per `V4_TESTID_CONTRACT.md`. Do not
  weaken assertions. Document mapping under V4 contract §10.
- `PRODUCT_BUG` — root cause is a product defect in Sprint 7 scope. Fix and
  re-run before handoff.
- `E2E_ENV_BLOCKED` — harness/Playwright/Chromium env failure unrelated to
  product. Capture exact command and stderr in a Bugs ticket. Allowed in
  handoff §13 with explicit env-blocked classification.
- `PAID_LLM_PAUSE` — test attempts a paid call. **STOP immediately and ask
  user.** Do not run. Allowed only with per-turn user approval. Record any
  approval verbatim under §15.

Smoke-only is not acceptable evidence for `COMPLETE_READY_FOR_SPRINT_8_TESTING`.

---

## 11. Refactor / Modularization Audit

Deliverable: `.tasks-md/Audit/S7_MODULARIZATION_AUDIT.md` (already seeded by
agent-F at HEAD `6c34187`).

**Sprint 7 scope:** audit doc only. Two extractions are conditionally allowed
if all of: (a) characterization tests already cover the unit, (b) extraction is
behavior-preserving, (c) extraction commit is separate from any product-fix
commit, (d) jsdom and non-E2E suites stay green after extraction.

Eligible (per audit): `runtime/event_contracts.py` (1452 LOC, contract-test
covered) → 4 sub-modules. `frontend/src/v4/secondary-tabs.jsx` (1044 LOC,
DOM-test covered) → 4 tab files. Either may be deferred if it competes with
defect closure for time. Everything else (`agent.py`, `llm-cards.jsx`,
`llm_runtime_controller.py`, `main.jsx`, `dom_locator_contract.py`,
`browser.py`, `server.py`) is audit-only.

Do not touch `frontend/dist/` directly except through `npm run build`.

---

## 12. Acceptance Gates (handoff cannot say COMPLETE without all true)

1. Working tree clean at handoff HEAD (no unstaged churn).
2. `cd frontend && npm test` green.
3. `cd frontend && npm run build` clean.
4. `python -m pytest --tb=short -q --ignore=tests/e2e` green (zero new
   skips/xfails beyond baseline; baseline at spec authoring is `2578 passed,
   1 skipped, 2 xfailed`).
5. Full local E2E suite (§10) executed; every test has a fate code recorded
   under handoff §13.
6. All v4 controls audited per §6; every row resolved to KEEP_ACTIVE /
   WIRE_EXISTING_SEAM / BUILD_P0_SEAM / DISABLE_WITH_REASON / HIDE_AS_NON_P0
   / REMOVE_AS_INVALID. No row left at DEAD_CONTROL.
7. Mock/static gating audit (D-108) passes — `DEFAULT_AGENTS` and any other
   `GATE_ON_PAYLOAD` rows from the audit pass produced commits or tickets;
   no runtime-reachable static array remains absent payload guard.
8. Manual Mode classified per §9.
9. PRD reconciliation table §7 has no row left with `Final` blank.
10. Bug tickets exist for every PARTIAL or DEFERRED row.

Final label rules:

- `COMPLETE_READY_FOR_SPRINT_8_TESTING` — all 10 gates pass and Manual Mode is
  class A or class B with user approval at §15.
- `PARTIAL_NEEDS_FIXES` — any gate fails for a fixable reason (re-pass to
  green).
- `BLOCKED` — gate fails for a reason that requires user/scope decision (e.g.
  PRD conflict, paid-LLM-only path).

---

## 13. Per-Defect Mini-Spec Plan

Create lightweight mini-specs in one batch under
`docs/superpowers/specs/2026-05-14-d{NNN}-*.md`. Each is short:

- current state (1–2 sentences)
- expected outcome (PRD §reference + acceptance line)
- seam fate per §5
- files likely touched
- tests to add (jsdom + backend if seam built)
- stop conditions (PRD conflict, broad refactor, paid LLM)

Mini-specs required:

| Mini-spec | Scope | Driver fate |
|---|---|---|
| `d101-improve-locator-and-view-candidates` | Wire `improve_locator` + `view_candidates` from step inline + ambiguity card | BUILD_P0_SEAM |
| `d101-blocked-action-resolve` | Wire `resolve_blocked_step` per `blocked.reason` (missing_data / wrong_page / locator_unstable / permission_required) | BUILD_P0_SEAM |
| `d101-change-precondition-and-navigate-to-expected` | Wire `change_precondition` + `navigate_to_expected` typed commands | BUILD_P0_SEAM |
| `d103-code-tab-export-and-diagnostics` | Verify `export_code` backend; extend payload for copy/save/regenerate + warnings; render redaction status | BUILD_P0_SEAM where missing, otherwise WIRE_EXISTING_SEAM |
| `d104-trace-failure-detail-and-redaction` | Render structured failure-detail panel + artifact/redaction status from existing `step_failed` / `trace_export` payloads | WIRE_EXISTING_SEAM (no new backend) |
| `d105-manual-mode-classification` | Decide A vs B per §9; if A, smallest seam through `manual_action` / `manual_assertion`; if B, disable toggle + Sprint 8 ticket | DISABLE_WITH_REASON or BUILD_P0_SEAM |
| `d106-agent-popover-policy` | Disable non-required toggles with reason + Sprint 8 ticket; render real read-only state where seam exists; no fake agent activity | DISABLE_WITH_REASON |
| `d107-composer-pick-and-camera` | Wire `aw-composer-pick` to existing `arm_picker`; hide camera as non-P0 | WIRE_EXISTING_SEAM + HIDE_AS_NON_P0 |
| `d108-mock-and-static-gating-audit` | Audit production frontend; resolve every `GATE_ON_PAYLOAD` / `REPLACE_WITH_BACKEND_STATE` row from the audit seed | mixed |

Each mini-spec is its own brainstorm pass only if its PRD basis is unclear or
its scope risks broad refactor. Otherwise write all nine in a single drafting
pass and proceed.

**Stop and ask user** if any mini-spec encounters: PRD conflict, new backend
behavior not clearly PRD-P0, broad-refactor requirement, paid-LLM dependency,
test weakening, repeated E2E infra failure not classified as `E2E_ENV_BLOCKED`.

---

## 14. Mock and Static Gating Audit Seed (D-108)

Runtime-reachable static data found:

| File:line | Identifier | Reachable | Recommendation |
|---|---|---|---|
| `frontend/src/v4/chrome.jsx:281` | `DEFAULT_AGENTS` (5 agent objects) | YES | `GATE_ON_PAYLOAD` — render only when backend emits `agent_settings`; with D-106 fate `DISABLE_WITH_REASON` this becomes a label-source rather than a mock data source |

All other constants surveyed are label/enum tables (`KEEP_AS_LABEL_DEFAULT`)
or selector/exclusion tokens, not mock runtime data. Full audit lives under
D-108 mini-spec.

---

## 15. Stop Conditions and Resolutions

Stop and ask user when any of:

- v4 UI demands behavior PRD does not describe.
- PRD demands behavior v4 UI deliberately deviates from.
- A backend seam would require touching more than two modules beyond the
  defect target.
- A refactor candidate would change behavior without test coverage.
- A test must be weakened to fit broken behavior.
- Full local E2E reveals repeated infra failure not product failure.
- Any paid LLM or live-website call would otherwise execute.
- Manual Mode classification A would require new backend work that is not
  explicitly PRD-P0 acceptance.

Resolutions recorded by adding a numbered bullet here with date + decision +
ticket. Empty at spec authoring.

---

## 16. Commit Discipline

This spec lands as `docs: add sprint 7 wrap-up master spec`.
Subsequent commits use small topical groupings:

- `feat(v4): wire improve_locator inline action` (D-101)
- `feat(v4): wire blocked-action resolve commands` (D-101)
- `feat(v4): wire change_precondition / navigate_to_expected` (D-101)
- `feat(v4): code tab export and diagnostics payload` (D-103)
- `feat(v4): trace failure detail panel` (D-104)
- `feat(v4): manual mode foundation` or `chore(v4): disable manual mode with reason` (D-105)
- `chore(v4): disable agent popover controls with reason` (D-106)
- `feat(v4): wire composer pick element` (D-107)
- `chore(v4): gate or remove static runtime data` (D-108)
- `test(e2e): align v4 local workflows` (E2E migrations)
- `refactor(*): extract <module>` (only if §11 conditions met)
- `docs: update sprint 7 handoff and audit evidence`

Before every commit:

```
git status --short --branch
git diff --cached --name-only
```

Never stage: `AGENTS.md`, `.DS_Store`, `.tasks-md/.DS_Store`, `.playwright-cli/`,
`node_modules`, `frontend_new_design_prototype/`, or unrelated edits.

---

## 17. Final Output Requirements (this master-spec pass)

After writing this spec and `S7_MODULARIZATION_AUDIT.md`:

- file path: `.tasks-md/Planning/SPRINT-007-WRAP-UP-MASTER-SPEC.md`
- sections: 1–17 above, with §6 and §7 tables fully seeded
- PRD ambiguities found: Manual Mode A-vs-B at Sprint 7 closure boundary —
  PRD requires Manual Mode (Phase 4 + Must-have #1) but does not name it as
  P0 *for Sprint 7 closure* explicitly; resolved by §9 default-B-with-user-
  approval-for-A.
- remaining user decisions:
  - confirm §9 default fate B for Manual Mode, or override to A.
  - confirm §11 whether to attempt two safe extractions inside Sprint 7 or
    push both to Sprint 8 audit-doc-only.
  - per-turn approval for any paid-LLM E2E (default: deny).
- readiness: ready to create per-defect mini-specs (§13) and execute.

No product code change in this master-spec pass.
