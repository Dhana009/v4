# V4 Test-ID Contract

**Status:** ACTIVE — Sprint 7 Stabilization Pass 2
**HEAD at freeze:** `96c9408`
**Date:** 2026-05-14

## 1. Purpose

This document is the frozen, canonical inventory of stable `data-testid`
attributes for the v4 production UI. All jsdom render tests
(`frontend/tests-dom/**`) and Playwright E2E tests (`tests/e2e/**`)
target these IDs. UI styling, incidental copy, CSS class names, and
legacy `#aw-root` overlay paths are **not** part of the contract and
may change at any time without test updates.

Rules:

- No new interactive v4 control may ship without a stable `data-testid`.
- E2E targets `[data-testid="..."]`. CSS class selectors are forbidden
  except for the Shadow-DOM host/mount IDs and legacy compat aliases
  in the table below.
- jsdom render tests are the first guard. Add jsdom coverage before
  expanding E2E.
- Tests must not be weakened to fit broken UI. If a test fails, fix
  the UI or document a defect in `UI_DEFECTS.md`.
- `frontend_new_design_prototype/v4/` is design reference only.
  Production truth is backend event → store → typed dispatch driven.
- Static mock content (e.g. design's hardcoded "smoke / sanity /
  regression" clarification options) is never live runtime state.

## 2. Source of Truth

| Area | Authoritative source file |
|---|---|
| Shell + chrome | `frontend/src/v4/chrome.jsx` |
| LLM tab cards + composer + thread | `frontend/src/v4/llm-cards.jsx` |
| Steps / Recorded / Code / Trace tabs | `frontend/src/v4/secondary-tabs.jsx` |
| Panel mount + tab routing + dispatchers | `frontend/aw-ide-panel.jsx` |
| Host + Shadow DOM lifecycle | `frontend/src/host/host.jsx`, `frontend/src/main.jsx` |
| Backend bootstrap injection | `browser.py` (`AUTOWORKBENCH_ROOT_ID = "autoworkbench-root"`) |

Design reference (NOT production truth):
`frontend_new_design_prototype/v4/{app,chrome,llm-tab,secondary-tabs,styles}.jsx`.

## 3. Shadow-DOM Host & Mount

| Element | Selector | Where set | Status | Notes |
|---|---|---|---|---|
| Host div | `#autoworkbench-root` | `browser.py` `AUTOWORKBENCH_ROOT_ID` | ACTIVE | attaches open ShadowRoot |
| Mount inside shadow | `#aw-shadow-mount` | `frontend/src/host/host.jsx` `SHADOW_MOUNT_ID` | ACTIVE | React render target |
| Shadow host alias | `#aw-shadow-host` | host.jsx | ACTIVE | legacy compat |
| Legacy panel id | `#aw-root` | v4-compat shim | COMPAT_ONLY | kept for harness `find_autoworkbench_panel` until Pass 3 harness migration |

## 4. Chrome / Shell Inventory

| Area | Element / control | data-testid | Source | jsdom | E2E | Status | Notes |
|---|---|---|---|---|---|---|---|
| Panel | stage wrapper | `aw-stage` | `aw-ide-panel.jsx:393` | — | — | ACTIVE | carries `data-dock`, `data-state`, `data-tab` |
| Panel | panel root | `aw-panel` | `aw-ide-panel.jsx:397` | `panel-integration.test.jsx:81` | `test_v4_panel_smoke.py`, `test_mvp_001_lifecycle_smoke.py` | ACTIVE | canonical panel-visible signal |
| Panel | panel body | `aw-panel-body` | `aw-ide-panel.jsx:440` | — | `test_mvp_001_lifecycle_smoke.py:73` | ACTIVE | shown when active tab is LLM |
| Header | header bar | `aw-header` | `chrome.jsx:42` | — | — | ACTIVE | — |
| Header | connection status pill | `aw-status-pill` | `chrome.jsx:52` | `chrome.test.jsx:17` | `test_mvp_001_lifecycle_smoke.py:50` | ACTIVE | carries `data-status` (`connected\|busy\|reconnect\|offline\|error`) |
| Header | agents popover toggle | `aw-agents-toggle` | `chrome.jsx:66` | — | — | ACTIVE | — |
| Header | session run/token pill | `aw-run-pill` | `chrome.jsx:87` | — | — | ACTIVE | — |
| Header | collapse panel | `aw-collapse` | `chrome.jsx:101` | — | — | ACTIVE | — |
| Header | dock-mode button | `aw-dock-${kind}` (`left\|right\|top\|float`) | `chrome.jsx:33` | `chrome.test.jsx:23` (`aw-dock-left`) | — | ACTIVE | — |
| Tabs | tablist | `aw-tabs` | `chrome.jsx:122` | `panel-integration.test.jsx:82` | `test_v4_panel_smoke.py:53` | ACTIVE | — |
| Tabs | tab button | `aw-tab-${id}` where id ∈ `{llm, steps, rec, code, trace}` | `chrome.jsx:130` | `chrome.test.jsx:30`, `panel-integration.test.jsx:218` | `test_v4_panel_smoke.py:55`, `test_mvp_001_lifecycle_smoke.py:65` | ACTIVE | harness `_TAB_TESTID_MAP` aliases `workbench→aw-tab-llm`, `recorded→aw-tab-rec`, `debug→aw-tab-trace` |
| NowStrip | current-task strip | `aw-now` | `chrome.jsx:144` | — | — | ACTIVE | rendered only when phase ≠ idle |
| NowStrip | primary action button | `aw-now-primary` | `chrome.jsx:161` | `chrome.test.jsx:42` | — | ACTIVE | label from `PHASE_META[state].primaryLabel` |
| Footer | footer bar | `aw-footer` | `chrome.jsx:174` | `panel-integration.test.jsx:83` | `test_v4_panel_smoke.py:58` | ACTIVE | also carries legacy class `ide-hd-state` for compat |
| Footer | blocker text | `aw-footer-blocker` | `chrome.jsx:191` | `chrome.test.jsx:48` | — | ACTIVE | only rendered when `PHASE_META[state].blocker` set |
| Agents popover | dialog | `aw-agents-popover` | `chrome.jsx:210` | — | — | ACTIVE | static agent list, D-106 |
| Agents popover | close X | `aw-agents-close` | `chrome.jsx:228` | — | — | ACTIVE | — |
| Agents popover | agent row | `aw-agent-row-${key}` | `chrome.jsx:243` | `chrome.test.jsx:53,54` (`aw-agent-row-orch`, `aw-agent-row-sr`) | — | ACTIVE | — |
| Agents popover | agent toggle | `aw-agent-toggle-${key}` | `chrome.jsx:265` | — | — | ACTIVE | — |
| Collapsed rail | rail container | `aw-collapsed-rail` | `chrome.jsx:298` | — | — | ACTIVE | — |
| Collapsed rail | rail tab button | `aw-rail-tab-${id}` | `chrome.jsx:308` | `chrome.test.jsx:61` (`aw-rail-tab-steps`) | — | ACTIVE | — |

## 5. LLM Tab — Thread + Cards + Composer

| Area | Element / control | data-testid | Source | jsdom | E2E | Status | Notes |
|---|---|---|---|---|---|---|---|
| Thread | scroll container | `aw-thread` | `llm-cards.jsx:1002` | — | — | ACTIVE | — |
| Thread | empty state | `llm-empty` | `llm-cards.jsx:901` | — | — | ACTIVE | — |
| Thread | seed chip | `llm-seed-${first-word}` | `llm-cards.jsx:910` | — | — | ACTIVE | — |
| Conversation | user bubble | `aw-msg-user` | `llm-cards.jsx:49` | — | — | ACTIVE | — |
| Conversation | system message | `aw-msg-system` | `llm-cards.jsx:60` | — | — | ACTIVE | — |
| Clarification | card root | `card-clarification` | `llm-cards.jsx:96` | `llm-cards.test.jsx:37`, `panel-integration.test.jsx:132` | — | ACTIVE | `null` when no clarification payload |
| Clarification | options group | `clarification-options` | `llm-cards.jsx:107` | — | — | ACTIVE | — |
| Clarification | option label | `clarification-option-${id}` | `llm-cards.jsx:115` | `llm-cards.test.jsx:39`, `panel-integration.test.jsx:133` | — | ACTIVE | id = `option.id ?? option.value ?? label` |
| Clarification | free-text input | `clarification-free-input` | `llm-cards.jsx:140` | — | — | ACTIVE | only when no `options[]` |
| Clarification | submit | `clarification-submit` | `llm-cards.jsx:150` | `llm-cards.test.jsx:40`, `panel-integration.test.jsx:134` | — | ACTIVE | dispatches `{type:"option_selected", question_id, target_step, answer}` |
| Clarification | let LLM decide | `clarification-let-llm` | `llm-cards.jsx:157` | — | — | ACTIVE | — |
| Recommendation | card root | `card-recommendation` | `llm-cards.jsx:179` | — | — | ACTIVE | — |
| Recommendation | list | `recommendation-list` | `llm-cards.jsx:191` | — | — | ACTIVE | — |
| Recommendation | item | `recommendation-item-${id}` | `llm-cards.jsx:198` | `llm-cards.test.jsx:92` (`recommendation-item-r1`) | — | ACTIVE | — |
| Recommendation | accept selected | `recommendation-accept` | `llm-cards.jsx:222` | `llm-cards.test.jsx:90` | — | ACTIVE | disabled until ≥1 selected |
| Recommendation | add own | `recommendation-add-own` | `llm-cards.jsx:231` | — | — | ACTIVE | — |
| PlanDiff | card root | `card-plan-diff` | `llm-cards.jsx:251` | — | — | ACTIVE | — |
| PlanDiff | ops list | `plan-diff-ops` | `llm-cards.jsx:262` | — | — | ACTIVE | — |
| PlanDiff | op row | `plan-diff-op-${i}` | `llm-cards.jsx:267` | — | — | ACTIVE | — |
| PlanDiff | apply | `plan-diff-apply` | `llm-cards.jsx:288` | — | — | ACTIVE | — |
| PlanDiff | reject | `plan-diff-reject` | `llm-cards.jsx:299` | — | — | ACTIVE | — |
| PlanDiff | revert | `plan-diff-revert` | `llm-cards.jsx:306` | — | — | ACTIVE | — |
| PlanReady | card root | `card-plan-ready` | `llm-cards.jsx:326` | `llm-cards.test.jsx:61`, `panel-integration.test.jsx:105` | — | ACTIVE | requires `plan.plan_id` for confirm |
| PlanReady | step count | `plan-step-count` | `llm-cards.jsx:339` | `llm-cards.test.jsx:62`, `panel-integration.test.jsx:106` | — | ACTIVE | — |
| PlanReady | steps list | `plan-steps` | `llm-cards.jsx:352` | — | — | ACTIVE | — |
| PlanReady | step row | `plan-step-${stepId}` | `llm-cards.jsx:359` | — | — | ACTIVE | — |
| PlanReady | confirm | `plan-confirm` | `llm-cards.jsx:392` | `llm-cards.test.jsx:63,76`, `panel-integration.test.jsx:107` | — | ACTIVE | disabled when no `plan_id` |
| PlanReady | edit plan | `plan-edit` | `llm-cards.jsx:403` | — | — | ACTIVE | — |
| PlanReady | run partial | `plan-partial-run` | `llm-cards.jsx:409` | — | — | ACTIVE | — |
| Permission | card root | `card-permission` | `llm-cards.jsx:448` | — | — | ACTIVE | — |
| Permission | allow once | `permission-allow-once` | `llm-cards.jsx:467` | `llm-cards.test.jsx:108` | — | ACTIVE | — |
| Permission | allow plan | `permission-allow-plan` | `llm-cards.jsx:471` | — | — | ACTIVE | — |
| Permission | deny | `permission-deny` | `llm-cards.jsx:476` | `llm-cards.test.jsx:112` | — | ACTIVE | — |
| Execution | card root | `card-execution` | `llm-cards.jsx:495` | — | — | ACTIVE | only when `phase==="executing"` |
| Execution | current step state | `exec-current-step` | `llm-cards.jsx:500` | — | — | ACTIVE | — |
| Execution | recorded step | `exec-recorded-${id}` | `llm-cards.jsx:512` | — | — | ACTIVE | — |
| Execution | current step | `exec-current` | `llm-cards.jsx:525` | — | — | ACTIVE | — |
| Execution | pending step | `exec-pending-${id}` | `llm-cards.jsx:543` | — | — | ACTIVE | — |
| Execution | pause | `exec-pause` | `llm-cards.jsx:557` | — | — | ACTIVE | — |
| Execution | stop | `exec-stop` | `llm-cards.jsx:562` | — | — | ACTIVE | — |
| LocatorAmbiguity | card root | `card-locator-ambiguity` | `llm-cards.jsx:582` | `panel-integration.test.jsx:200` | — | ACTIVE | reuses recovery channel |
| LocatorAmbiguity | candidates list | `locator-candidates` | `llm-cards.jsx:597` | — | — | ACTIVE | — |
| LocatorAmbiguity | candidate row | `locator-candidate-${id}` | `llm-cards.jsx:605` | `llm-cards.test.jsx:133`, `panel-integration.test.jsx:201` | — | ACTIVE | — |
| LocatorAmbiguity | candidate radio | `locator-select-${id}` | `llm-cards.jsx:619` | — | — | ACTIVE | — |
| LocatorAmbiguity | ask LLM | `locator-ask-llm` | `llm-cards.jsx:635` | — | — | ACTIVE | — |
| LocatorAmbiguity | change scope | `locator-change-scope` | `llm-cards.jsx:641` | — | — | ACTIVE | — |
| LocatorAmbiguity | stop | `locator-stop` | `llm-cards.jsx:646` | — | — | ACTIVE | — |
| LocatorAmbiguity | confirm | `locator-confirm` | `llm-cards.jsx:651` | `llm-cards.test.jsx:132,134,135`, `panel-integration.test.jsx:202` | — | ACTIVE | disabled until candidate selected |
| Recovery | card root | `card-recovery` | `llm-cards.jsx:677` | `panel-integration.test.jsx:179` | — | ACTIVE | — |
| Recovery | evidence chip | `recovery-evidence-${i}` | `llm-cards.jsx:695` | — | — | ACTIVE | — |
| Recovery | attempts list | `recovery-attempts` | `llm-cards.jsx:706` | — | — | ACTIVE | — |
| Recovery | apply LLM | `recovery-apply-llm` | `llm-cards.jsx:716` | — | — | ACTIVE | — |
| Recovery | retry | `recovery-retry` | `llm-cards.jsx:721` | `llm-cards.test.jsx:151` | — | ACTIVE | — |
| Recovery | choose locator | `recovery-choose-locator` | `llm-cards.jsx:728` | — | — | ACTIVE | only when candidate options exist |
| Recovery | stop | `recovery-stop` | `llm-cards.jsx:734` | `llm-cards.test.jsx:155` | — | ACTIVE | — |
| Completed | card root | `card-completed` | `llm-cards.jsx:754` | — | — | ACTIVE | — |
| Completed | outcome state | `completed-state` | `llm-cards.jsx:758` | `llm-cards.test.jsx:165` | — | ACTIVE | reads `completion.outcome` |
| Completed | summary grid | `completed-summary-grid` | `llm-cards.jsx:767` | `llm-cards.test.jsx:166` | — | ACTIVE | — |
| Completed | summary text | `completed-summary-text` | `llm-cards.jsx:794` | — | — | ACTIVE | — |
| Completed | replay all | `completed-replay-all` | `llm-cards.jsx:801` | — | — | ACTIVE | — |
| Completed | save session | `completed-save` | `llm-cards.jsx:807` | — | — | ACTIVE | — |
| Completed | open code | `completed-open-code` | `llm-cards.jsx:813` | — | — | ACTIVE | — |
| Completed | download trace | `completed-download-trace` | `llm-cards.jsx:819` | — | — | ACTIVE | — |
| Offline | card root | `card-offline` | `llm-cards.jsx:834` | `llm-cards.test.jsx:177` | — | ACTIVE | hidden when `connection==="connected"` |
| Offline | reconnect | `offline-reconnect` | `llm-cards.jsx:851` | `llm-cards.test.jsx:178` | — | ACTIVE | — |
| SchemaError | card root | `card-schema-error` | `llm-cards.jsx:865` | — | — | ACTIVE | — |
| SchemaError | repair | `schema-repair` | `llm-cards.jsx:887` | — | — | ACTIVE | — |
| Composer | container | `aw-composer` | `llm-cards.jsx:930` | — | — | ACTIVE | — |
| Composer | input | `aw-composer-input` | `llm-cards.jsx:933` | — | — | ACTIVE | — |
| Composer | pick element | `aw-composer-pick` | `llm-cards.jsx:946` | — | — | DEAD_CONTROL (D-107) | no handler bound; resolve in later pass |
| Composer | send | `aw-composer-send` | `llm-cards.jsx:954` | — | — | ACTIVE | dispatches user_message |

## 6. Steps Tab Inventory

| Element / control | data-testid | Source | jsdom | E2E | Status | Notes |
|---|---|---|---|---|---|---|
| Tab root | `steps-tab` | `secondary-tabs.jsx:183` | `panel-integration.test.jsx:221`, `secondary-tabs.test.jsx:15+` | `test_v4_panel_smoke.py:62`, `test_mvp_001_lifecycle_smoke.py:65` | ACTIVE | — |
| Add step | `steps-add` | `secondary-tabs.jsx:186` | — | — | ACTIVE | — |
| Pick element | `steps-pick` | `secondary-tabs.jsx:191` | — | — | ACTIVE | — |
| Filter | `steps-filter` | `secondary-tabs.jsx:198` | — | — | ACTIVE | — |
| Run all | `steps-run-all` | `secondary-tabs.jsx:210` | `secondary-tabs.test.jsx:16,54` | — | ACTIVE | disabled with empty list |
| Run selected | `steps-run-selected` | `secondary-tabs.jsx:219` | — | — | ACTIVE | — |
| Blocked notice | `steps-blocked` | `secondary-tabs.jsx:228` | — | — | ACTIVE | — |
| Empty notice | `steps-empty` | `secondary-tabs.jsx:236` | `secondary-tabs.test.jsx:15` | — | ACTIVE | — |
| Step row | `step-row-${stepId}` | `secondary-tabs.jsx:67` | `secondary-tabs.test.jsx:31` (`step-row-s1`) | — | ACTIVE | — |
| Step intent input | `step-input-${stepId}` | `secondary-tabs.jsx:77` | `secondary-tabs.test.jsx:32` | — | ACTIVE | — |
| Step status badge | `step-status-${stepId}` | `secondary-tabs.jsx:83` | — | — | ACTIVE | — |
| Step target summary | `step-target-${stepId}` | `secondary-tabs.jsx:87` | — | — | ACTIVE | only after element picked |
| Step picker candidate select | `picker-candidate-select` | `secondary-tabs.jsx:93` | — | — | ACTIVE | — |
| Step outcome group | `step-outcome-${stepId}` | `secondary-tabs.jsx:105` | — | — | ACTIVE | — |
| Step outcome chip | `step-outcome-chip-${type}-${stepId}` | `secondary-tabs.jsx:114` | `secondary-tabs.test.jsx:34` (`step-outcome-chip-navigation-s1`) | — | ACTIVE | type ∈ {`navigation`, `visible`, `count`, …} |
| Step attach element | `step-attach-${stepId}` | `secondary-tabs.jsx:135` | `secondary-tabs.test.jsx:39` | — | PLANNED_BUG_S7_V4_001 | needs deep-workflow port |
| Step delete | `step-delete-${stepId}` | `secondary-tabs.jsx:143` | — | — | ACTIVE | — |
| Step locator chip | `step-locator-${stepId}` | `secondary-tabs.jsx::StepLocatorChip` | `secondary-tabs.test.jsx` (4 tests) | — | ACTIVE | Pass 4b-1. Carries `data-kind` (`ok\|med\|warn\|unknown`) and `data-strength` (`strong\|medium\|weak\|unknown`). Renders only when backend (`plan_ready` annotator or `element_picked`) provides `locator_kind` on step or `step.element_info`. Frontend never infers strength. |
| Step kind chip | `step-kind-${stepId}` | `secondary-tabs.jsx::StepKindChip` | `secondary-tabs.test.jsx` (6 tests) | — | ACTIVE | Pass 4b-2. Carries `data-kind` (`atomic\|loop\|section\|unknown`, clamped) and `data-raw-kind` (the original backend value, preserved for trace). Renders only when backend provides `step.step_kind`. Frontend never classifies; unknown values are clamped to `unknown` but never silently changed to atomic. |

## 7. Recorded Tab Inventory

| Element / control | data-testid | Source | jsdom | E2E | Status | Notes |
|---|---|---|---|---|---|---|
| Tab root | `recorded-tab` | `secondary-tabs.jsx:266` | `panel-integration.test.jsx:147` | `test_v4_panel_smoke.py:66`, `test_mvp_001_lifecycle_smoke.py:71` | ACTIVE | — |
| Count badge | `recorded-count` | `secondary-tabs.jsx:271` | — | — | ACTIVE | — |
| Replay all | `recorded-replay-all` | `secondary-tabs.jsx:275` | — | — | ACTIVE | — |
| Empty notice | `recorded-empty` | `secondary-tabs.jsx:282` | `secondary-tabs.test.jsx:62` | — | ACTIVE | — |
| Recorded item | `recorded-item-${id}` | `secondary-tabs.jsx:299` | `secondary-tabs.test.jsx:92-94`, `panel-integration.test.jsx:148,149` | — | ACTIVE | also carries `data-state` (`recorded\|repaired\|skipped\|failed`) |
| Recorded title | `recorded-title-${id}` | `secondary-tabs.jsx:312` | — | — | ACTIVE | — |
| Replay single | `recorded-replay-${id}` | `secondary-tabs.jsx:328` | — | — | ACTIVE | — |
| Children container | `recorded-children-${id}` | `secondary-tabs.jsx:337` | — | — | ACTIVE | — |
| Per-row evidence panel | (none yet) | — | — | — | PLANNED_D102 | locator-used / validation / screenshot rows pending |

## 8. Code Tab Inventory

| Element / control | data-testid | Source | jsdom | E2E | Status | Notes |
|---|---|---|---|---|---|---|
| Tab root | `code-tab` | `secondary-tabs.jsx:388` | `panel-integration.test.jsx:158` | `test_v4_panel_smoke.py:70`, `test_mvp_001_lifecycle_smoke.py:70` | ACTIVE | — |
| File label | `code-file-label` | `secondary-tabs.jsx:399` | — | — | ACTIVE | — |
| Copy | `code-copy` | `secondary-tabs.jsx:405` | `secondary-tabs.test.jsx:100,114`, `panel-integration.test.jsx:160` | — | ACTIVE | disabled when no code |
| Save | `code-save` | `secondary-tabs.jsx:411` | — | — | ACTIVE | — |
| Empty notice | `code-empty` | `secondary-tabs.jsx:419` | `secondary-tabs.test.jsx:99` | — | ACTIVE | — |
| Preview | `code-preview` | `secondary-tabs.jsx:425` | `secondary-tabs.test.jsx:112`, `panel-integration.test.jsx:159` | — | ACTIVE | — |
| Diagnostics list | `code-diagnostics` | `secondary-tabs.jsx:429` | `secondary-tabs.test.jsx:113` | — | ACTIVE | — |
| Diagnostic row | `code-diagnostic-${i}` | `secondary-tabs.jsx:435` | — | — | ACTIVE | — |
| Export controls | (none yet) | — | — | — | PLANNED_D103 | richer payload + export pending |

## 9. Trace Tab Inventory

| Element / control | data-testid | Source | jsdom | E2E | Status | Notes |
|---|---|---|---|---|---|---|
| Tab root | `trace-tab` | `secondary-tabs.jsx:473` | — | `test_v4_panel_smoke.py:74`, `test_mvp_001_lifecycle_smoke.py:72` | ACTIVE | — |
| Filter input | `trace-filter` | `secondary-tabs.jsx:477` | — | — | ACTIVE | — |
| Category chip | `trace-filter-${k}` | `secondary-tabs.jsx:485` | — | — | ACTIVE | k ∈ event category |
| Empty notice | `trace-empty` | `secondary-tabs.jsx:493` | `secondary-tabs.test.jsx:120` | — | ACTIVE | — |
| Row | `trace-row-${i}` | `secondary-tabs.jsx:508` | `secondary-tabs.test.jsx:130,131` | — | ACTIVE | — |
| Failure detail panel | (none yet) | — | — | — | PLANNED_D104 | — |

## 10. Legacy Selector Mapping

| Legacy / class selector | v4 replacement | Keep temporarily? | Removal condition |
|---|---|---|---|
| `#aw-root` | `#autoworkbench-root` host + `[data-testid="aw-panel"]` | YES (compat shim) | Pass 3 — harness migrated + `tests/test_e2e_harness.py` mocks updated |
| `.ide-panel` | `[data-testid="aw-panel"]` | YES | same as above |
| `.ide-hd-state` | `[data-testid="aw-footer"]` (footer co-carries class) | YES | same |
| `.ide-tabs` | `[data-testid="aw-tabs"]` | YES (harness still ORs) | same |
| `.ide-step-row` / `.ide-step-card` | `[data-testid^="step-row-"]` | YES | when D-101 deep workflow port lands |
| `.ide-step-input` | `[data-testid^="step-input-"]` | YES | same |
| `.ide-step-target-summary` | `[data-testid^="step-target-"]` | YES | same |
| `.ide-step-outcome` | `[data-testid^="step-outcome-"]` | YES | same |
| `.ide-badge.b-ready` / `.ide-badge.b-await` | `[data-testid^="step-status-"]` (status reflected via class) | YES | until status-as-attribute ships |
| `[role="tab"]` text-match | `[data-testid="aw-tab-${id}"]` | NO | already eliminated |

## 11. Harness Tab Aliasing

`tests/e2e/harness.py` lines 1843–1851 hold the canonical tab name map.
Tests refer to logical names; harness translates to v4 testid:

| Logical tab name | v4 testid |
|---|---|
| `workbench` | `aw-tab-llm` |
| `steps` | `aw-tab-steps` |
| `code` | `aw-tab-code` |
| `debug` | `aw-tab-trace` |
| `rec` / `recorded` | `aw-tab-rec` |

## 12. Out-of-Contract Areas (no stable testid yet)

These controls exist in source but are not part of the contract until
their feature work lands:

- Manual Mode header toggle (D-105) — toggle button not yet wired.
- Composer pick-element (D-107) — `aw-composer-pick` exists but DEAD.
- Manual builder card — entire surface (D-105).
- Tweaks panel — design prototype only.

When wired, each must add a stable `data-testid` and update this doc
plus add at least one jsdom render test before any E2E expansion.

## 13. Maintenance Rules

1. Adding a testid: update this file in the same commit as the source.
2. Renaming a testid: only via a deprecation pass that lists the old
   id under "Legacy Selector Mapping" with a removal condition. Never
   silently rename.
3. Removing a testid: requires confirmation that no jsdom or E2E
   reference remains (`grep -r data-testid=\"name\"` over `frontend/`
   and `tests/`).
4. Tests targeting non-testid selectors (CSS class, text content,
   nth-child) are non-conformant. New tests must use testids.
