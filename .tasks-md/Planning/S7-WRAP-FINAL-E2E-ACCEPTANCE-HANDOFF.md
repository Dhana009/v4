# S7 Wrap — Final E2E, Acceptance Gates, and Handoff Mini-Spec

**Status:** ACTIVE — Sprint 7 closeout execution guide.
**Branch:** `s7/clusters-6-11-complete-llm-mode`
**Authored at HEAD:** `6c34187 docs: record D-102 Recorded tab evidence view completion`
**Date:** 2026-05-14
**Master spec:** `.tasks-md/Planning/SPRINT-007-WRAP-UP-MASTER-SPEC.md`

Policy locks (non-negotiable, no per-spec override):

- Paid LLM E2E: **DEFAULT DENY**. No paid call without per-turn user approval logged verbatim in master §15.
- Live website E2E: **DENY** for Sprint 7. Sprint 9 scope.
- Manual Mode E2E: run only if D-105 resolves to class **A** (working foundation); else jsdom-only gate.

---

## 1. Final E2E Classification Plan

Run tests in this exact order at the final handoff HEAD (post-product-fixes, post-product-tests committed). Before each run, verify `git status --short` returns clean.

### 1.1 `tests/e2e/test_v4_panel_smoke.py`

```
python -m pytest tests/e2e/test_v4_panel_smoke.py -v --tb=short
```

**LLM dependency:** NONE. Local fixture only.
**Selector profile:** V4 testids (`aw-panel`, `aw-tabs`, `aw-tab-steps`, `recorded-tab`, `code-tab`, `trace-tab`, footer class compat alias). No legacy `.ide-*` solo paths.
**Expected fate:** `PASS`
**What to record in handoff §13:**
- Exact stdout test names + durations.
- Screenshot artifact path if captured.
- HEAD sha at time of run.
- If not PASS: classify per §3 triage tree, ticket number, and rerun gate.

### 1.2 `tests/e2e/test_mvp_001_lifecycle_smoke.py`

```
python -m pytest tests/e2e/test_mvp_001_lifecycle_smoke.py -v --tb=short
```

**LLM dependency:** NONE. Fake-LLM fixture (test fixture controls event stream, no paid call).
**Selector profile:** V4 testids (`aw-panel`, `aw-status-pill`, `aw-tab-llm`, `aw-tab-steps`, `recorded-tab`, `code-tab`, `trace-tab`, `plan-confirm`, `aw-panel-body`).
**Expected fate:** `PASS`
**What to record:** same as 1.1.

### 1.3 `tests/e2e/test_basic_click_flow.py`

```
python -m pytest tests/e2e/test_basic_click_flow.py -v --tb=short
```

**LLM dependency:** Fake-LLM via test fixture. No paid call expected; stop immediately if a paid call is attempted.
**Selector profile:** MIXED — harness tab aliasing maps logical names to V4 testids; some legacy `.ide-step-*` class selectors may appear in assertions.
**Expected fate:** `PASS` (if BUG-S7-V4-001 is resolved) or `PRODUCT_BUG` (if deep Steps backend round-trip still broken at handoff HEAD).
**What to record:**
- If PASS: stdout + duration + HEAD sha.
- If PRODUCT_BUG: exact failure line, which selector/assertion failed, BUG-S7-V4-001 open status. Do not weaken assertion. Record under handoff §13 with fate code.

### 1.4 `tests/e2e/test_exact_text_assertion_flow.py`

```
python -m pytest tests/e2e/test_exact_text_assertion_flow.py -v --tb=short
```

**LLM dependency:** Fake-LLM fixture.
**Selector profile:** MIXED — same as 1.3.
**Expected fate:** `PASS` or `PRODUCT_BUG` (same BUG-S7-V4-001 dependency as 1.3).
**What to record:** same as 1.3.

### 1.5 `tests/e2e/test_visible_assertion_flow.py`

```
python -m pytest tests/e2e/test_visible_assertion_flow.py -v --tb=short
```

**LLM dependency:** Fake-LLM fixture.
**Selector profile:** MIXED.
**Expected fate:** `PASS` or `PRODUCT_BUG`.
**What to record:** same as 1.3.

### 1.6 `tests/e2e/test_correction_assert_then_click_flow.py`

```
python -m pytest tests/e2e/test_correction_assert_then_click_flow.py -v --tb=short
```

**LLM dependency:** Fake-LLM fixture.
**Selector profile:** MIXED.
**Expected fate:** `PASS` or `PRODUCT_BUG`.
**What to record:** same as 1.3.

### 1.7 `tests/e2e/test_llm_required_ambiguous_action_flow.py`

```
python -m pytest tests/e2e/test_llm_required_ambiguous_action_flow.py -v --tb=short
```

**LLM dependency:** Test name contains "llm_required" — **verify before running** that this test uses the fake/fixture LLM path, not a paid model call. Check for `[MODEL_ROUTER]` log markers or `openai`/`anthropic` API calls in backend stdout.

- If fake fixture confirmed: run as above, expected fate `PASS` or `PRODUCT_BUG`.
- If paid call confirmed: **STOP immediately**, fate code `PAID_LLM_PAUSE`, ask user for per-turn approval before proceeding. Do not run the test.

**What to record:** fate code + evidence of LLM path (fake or paid) + result.

---

### Full-suite batch shortcut (after manual review of 1.7 LLM path)

```
python -m pytest tests/e2e/test_v4_panel_smoke.py \
                 tests/e2e/test_mvp_001_lifecycle_smoke.py \
                 tests/e2e/test_basic_click_flow.py \
                 tests/e2e/test_exact_text_assertion_flow.py \
                 tests/e2e/test_visible_assertion_flow.py \
                 tests/e2e/test_correction_assert_then_click_flow.py \
                 tests/e2e/test_llm_required_ambiguous_action_flow.py \
                 -v --tb=short 2>&1 | tee /tmp/s7-e2e-run.txt
```

Record `/tmp/s7-e2e-run.txt` content verbatim in handoff §13.

---

## 2. Selector Migration Plan

If any test fails with a "locator not found" error on a legacy `.ide-*` class selector, apply the mapping below. Do not weaken the assertion — migrate to the v4 testid equivalent. Every migration commit must re-run the affected test to confirm green before handoff.

Source: `V4_TESTID_CONTRACT.md` §10 + §11.

| Failing legacy selector | V4 replacement selector | Notes |
|---|---|---|
| `#aw-root` | `#autoworkbench-root` (host) + `[data-testid="aw-panel"]` | compat shim exists; prefer testid |
| `.ide-panel` | `[data-testid="aw-panel"]` | — |
| `.ide-hd-state` | `[data-testid="aw-footer"]` | footer co-carries legacy class but testid preferred |
| `.ide-tabs` | `[data-testid="aw-tabs"]` | harness ORs both; prefer testid |
| `.ide-step-row`, `.ide-step-card` | `[data-testid^="step-row-"]` | D-101 port pending |
| `.ide-step-input` | `[data-testid^="step-input-"]` | — |
| `.ide-step-target-summary` | `[data-testid^="step-target-"]` | — |
| `.ide-step-outcome` | `[data-testid^="step-outcome-"]` | — |
| `.ide-badge.b-ready`, `.ide-badge.b-await` | `[data-testid^="step-status-"]` | status via class pending attribute-first switch |
| Logical tab name `workbench` | `[data-testid="aw-tab-llm"]` | harness alias — do not break harness `_TAB_TESTID_MAP` |
| Logical tab name `recorded` / `rec` | `[data-testid="aw-tab-rec"]` | same |
| Logical tab name `debug` | `[data-testid="aw-tab-trace"]` | same |

**Migration commit tag:** `test(e2e): align v4 selector for <test-name>` — one commit per test file migrated.

Do not remove legacy compat aliases from `harness.py` during Sprint 7. That cleanup is Pass 3 scope (Sprint 8).

---

## 3. Failure Triage Tree

Use this tree for every test that does not PASS. Fate code determines next action.

```
Did test PASS?
├── YES → record PASS + evidence → done
└── NO
    ├── Is the failure a selector not found / locator strict-mode error
    │   on a .ide-* class or legacy #aw-root / #aw-root path?
    │   ├── YES → fate SELECTOR_DRIFT
    │   │         action: apply §2 migration table, re-run
    │   │         record: which selector, which v4 replacement used
    │   └── NO
    │       ├── Is failure Playwright timeout / browser launch error /
    │       │   Python harness exception NOT caused by a product assertion
    │       │   (e.g. Chromium not found, port conflict, asyncio error,
    │       │   backend never started)?
    │       │   ├── YES → fate E2E_ENV_BLOCKED
    │       │   │         action: capture exact command + full stderr
    │       │   │                 in .tasks-md/Bugs/BUG-S8-ENV-*.md
    │       │   │         DO NOT treat as product bug
    │       │   │         record in handoff §13 with fate code + ticket
    │       │   └── NO
    │       │       ├── Does test attempt a paid LLM API call
    │       │       │   (OpenAI/Anthropic network call, real model token use,
    │       │       │   [MODEL_ROUTER] to non-fixture model)?
    │       │       │   ├── YES → fate PAID_LLM_PAUSE
    │       │       │   │         action: STOP. Do not run further.
    │       │       │   │                 Ask user for per-turn approval.
    │       │       │   │                 Log approval verbatim in master §15.
    │       │       │   └── NO
    │       │       │       └── Failure is a product assertion mismatch
    │       │       │           (wrong testid rendered, missing card, wrong
    │       │       │           dispatch, bad state, missing text, etc.)
    │       │       │           → fate PRODUCT_BUG
    │       │       │             action: is it in Sprint 7 defect scope
    │       │       │                     (D-101..D-108, BUG-S7-V4-001)?
    │       │       │             ├── YES → fix in current pass, re-run
    │       │       │             └── NO → create BUG-S8-*.md ticket,
    │       │       │                       record in handoff §13 + §14
```

**Key invariant:** never weaken an assertion to turn a PRODUCT_BUG into a PASS. Weakness = test debt + hidden defect.

---

## 4. Acceptance Gates Verification Checklist

Run in the order shown. Each command is copy-paste-ready. Gate 5 is the E2E suite from §1.

### Gate 1 — Working tree clean

```
git status --short
```

Expected: empty output (zero modified/untracked files that belong to the commit chain).
Pass condition: no M/A/D/? lines except for explicitly-excluded files (`.DS_Store`, `AGENTS.md`, `.playwright-cli/`, `frontend_new_design_prototype/`).
Fail action: stage and commit any in-scope changes, or explicitly drop uncommitted-by-design changes, before proceeding.

### Gate 2 — jsdom green

```
cd frontend && npm test
```

Expected: all tests pass, zero failures, zero new skips.
Baseline: 79 / 79 passed (master §4; older evidence at `2f20f4e` showed 35; recount at current HEAD).
Fail action: fix failing jsdom test or document as PRODUCT_BUG with ticket.

### Gate 3 — npm build clean

```
cd frontend && npm run build
```

Expected: exits 0, no error lines, `dist/autoworkbench.js` and `dist/autoworkbench.css` produced.
Fail action: fix build error before E2E run (broken dist = E2E tests will use stale bundle).

### Gate 4 — pytest non-E2E green

```
python -m pytest --tb=short -q --ignore=tests/e2e
```

Expected: `2578 passed, 1 skipped, 2 xfailed` (baseline at master §4 HEAD `6c34187`).
Fail condition: any new FAILED; any new skip/xfail not in baseline.
Pass condition: zero new failures; skipped/xfailed count does not exceed baseline.
Fail action: fix or document with ticket. Never add a new skip/xfail without a ticket and handoff entry.

### Gate 5 — E2E suite classified

Run all seven tests per §1. Every test must have a recorded fate code. No test may be left "not run" at handoff unless fate is `PAID_LLM_PAUSE` (user decision pending) or `E2E_ENV_BLOCKED` (env ticket filed).

Record per test: fate code, stdout snippet (first + last 5 lines), duration, HEAD sha.

### Gate 6 — Control inventory resolved

Cross-check master spec §6 table. Confirm:
- Zero rows remain at fate `DEAD_CONTROL` (all resolved to WIRE/DISABLE/REMOVE/KEEP).
- Every `DISABLE_WITH_REASON` row satisfies master §8 (disabled attr, title, ticket, jsdom test).
- Every `BUILD_P0_SEAM` row either shipped (with commit reference) or has an explicit Sprint 8 ticket.

Verification command (grep for dead controls in source):
```
grep -r "DEAD_CONTROL\|dead_control" frontend/src/v4/ --include="*.jsx"
```

Expected: zero results (dead controls were replaced by disabled or wired, not left in place).

### Gate 7 — Mock audit pass (D-108)

D-108 spec verdict must be one of `CLEAN` (no runtime-reachable static arrays) or `GATED` (all identified rows gated on payload with commit reference).

Check: `DEFAULT_AGENTS` in `frontend/src/v4/chrome.jsx` — confirm it renders only when backend `agent_settings` payload is present (D-106/D-108 combined resolution) or is gated by `D-106 DISABLE_WITH_REASON` such that it is a label source only, not mock runtime data rendered as real state.

```
grep -n "DEFAULT_AGENTS" frontend/src/v4/chrome.jsx
```

Expected: `DEFAULT_AGENTS` is either removed, gated on payload presence, or used only as a fallback label/tooltip reference when backend has not emitted `agent_settings` and the popover is disabled.

### Gate 8 — Manual Mode classified

D-105 verdict must be exactly one of:

- **A — WORKING_FOUNDATION**: toggle wires runtime mode, ManualBuilder rendered, `manual_action`/`manual_assertion` dispatched, jsdom + local-fixture E2E cover happy path.
- **B — DISABLED_WITH_REASON**: toggle `disabled`, `title` cites D-105, ManualBuilder hidden, Sprint 8 ticket with acceptance criteria, user approval logged in master §15.

If verdict is B, confirm:
```
grep -n "manual" frontend/src/v4/chrome.jsx
```
Shows the toggle rendered as a disabled button with a non-empty title attribute.

Class C (MISSING_BLOCKER) blocks `COMPLETE_READY_FOR_SPRINT_8_TESTING` and forces `PARTIAL_NEEDS_FIXES` label.

### Gate 9 — PRD reconciliation complete

Master §7 table must have no row with `Final` column blank. Fill every `Final` cell with one of: `WORKING` / `PARTIAL` / `CONTRACT_ONLY` / `DISABLED_WITH_REASON` / `MISSING` / `DEFERRED_TO_SPRINT_8`.

Verification: open master §7, scan Final column, count blanks. Zero blanks = pass.

### Gate 10 — Bug tickets exist for PARTIAL and DEFERRED rows

Every §7 row with `Final` = `PARTIAL`, `MISSING`, or `DEFERRED_TO_SPRINT_8` must have a corresponding ticket in:
- `.tasks-md/Audit/UI_DEFECTS.md` Open table, or
- `.tasks-md/Bugs/BUG-S8-*.md`

Verification:
```
ls .tasks-md/Bugs/
```
Confirm ticket files cover: D-101 cmds, D-103, D-104, D-105 (if B), D-106, D-107, D-108 remaining, BUG-S7-V4-001, human-input/auth hardening, Manual Mode (if deferred), Page Intelligence visible card, capability_gap visible card.

---

## 5. Handoff Document Update Plan

At Sprint 7 close, update these files in this order before the final handoff commit.

| File | What to update | Priority |
|---|---|---|
| `.tasks-md/Sprints/SPRINT-007-HANDOFF.md` | Full re-pass: §1 executive summary label, §13 tests with full 7-test E2E evidence at current HEAD, §14 bugs with D-101..D-108 final statuses, §15 architecture invariant final verdict, §16 known limitations updated, §18 final conclusion updated. | CRITICAL — update last, after all other files done. |
| `.tasks-md/Audit/UI_DEFECTS.md` | D-101 through D-108: fill final status column (DONE / OPEN / DEFERRED). For DONE: commit reference. For OPEN: Sprint 8 ticket. | High |
| `.tasks-md/Audit/V4_TESTID_CONTRACT.md` | Add any new testids introduced by D-103 (Code export controls), D-104 (Trace failure-detail panel), D-107 (Composer pick). Update Status column for D-107 `aw-composer-pick` from `DEAD_CONTROL` to `ACTIVE` if wired. Mark `PLANNED_D103` and `PLANNED_D104` rows as `ACTIVE` if shipped. | High |
| `.tasks-md/Audit/S7_MODULARIZATION_AUDIT.md` | No code changes if audit-only. If either safe extraction (§11) shipped: add evidence row with commit hash + test count before/after. Otherwise: mark "extractions deferred to Sprint 8" and close the doc. | Medium |
| `.tasks-md/Planning/SPRINT-007-WRAP-UP-MASTER-SPEC.md` | Fill §7 Final column for all rows. Fill §15 Stop Conditions Resolved if any decisions were made. Update §4 checkpoint with final HEAD sha + test counts. | High |
| `.tasks-md/Bugs/BUG-S8-*.md` (new files) | One file per PARTIAL/DEFERRED row that does not yet have a Sprint 8 ticket. Follow bug template: title, sprint discovered, symptom, PRD reference, acceptance criteria for closure, owner layer. | High |

**Commit for handoff update:**
```
docs: update sprint 7 handoff and audit evidence
```
Stage only the files listed above. Never stage `AGENTS.md`, `.DS_Store`, `frontend_new_design_prototype/`, `node_modules`, `.playwright-cli/`.

---

## 6. Final-Label Decision Tree

```
All 10 gates pass?
├── YES
│   ├── D-105 class A (WORKING_FOUNDATION)
│   │   └── label: COMPLETE_READY_FOR_SPRINT_8_TESTING
│   └── D-105 class B with user approval in master §15
│       └── label: COMPLETE_READY_FOR_SPRINT_8_TESTING
└── NO
    ├── All failing gates are fixable within Sprint 7 scope and policy?
    │   └── YES → label: PARTIAL_NEEDS_FIXES
    │             action: fix gates, re-run, re-check
    └── Any gate fails due to user/scope decision (paid-LLM path,
        live website, out-of-scope PRD requirement, D-105 class C)?
        └── YES → label: BLOCKED
                  action: document blocking reason in master §15,
                          create ticket, ask user for resolution
```

**Current label at spec authoring:** `PARTIAL_NEEDS_FIXES` (master §12, handoff §18).
Target label at this pass close: `COMPLETE_READY_FOR_SPRINT_8_TESTING` (requires all 10 gates, Manual Mode A or B+approval).

---

## 7. Push-Readiness Checklist

Before pushing to `origin/s7/clusters-6-11-complete-llm-mode`:

- [ ] Working tree clean: `git status --short` returns zero in-scope changes.
- [ ] Branch ahead count matches expected new commits: `git log origin/s7/clusters-6-11-complete-llm-mode..HEAD --oneline` lists exactly the commits from this wrap pass (one per defect fix + one handoff update doc commit). No stray commits.
- [ ] No unstaged churn: `git diff --stat` is empty.
- [ ] All 10 acceptance gates verified green (or fates documented for any non-PASS E2E).
- [ ] Handoff doc updated per §5, including final label recorded in §18.
- [ ] User has explicitly approved push in this conversation turn. **Do not push without user confirmation.** Record approval here or in master §15.
- [ ] Do not `--force` push. Branch is not protected but force-push loses lineage.

---

## 8. Stop Conditions Specific to This Mini-Spec

Stop work on this spec and ask user when:

1. A test calls a paid LLM or live-website path. Fate `PAID_LLM_PAUSE`. Do not run.
2. A selector migration requires changing a test assertion (not just a selector) to pass. That is a test weakening — stop, document, ask.
3. A product fix to make a test pass would require touching more than 2 modules beyond the identified defect file. Stop, scope creep risk, ask.
4. Gate 4 (pytest non-E2E) gains new failures not explained by in-scope product fixes from this pass. Stop, diagnose root cause before continuing.
5. Gate 8 (Manual Mode) would require new backend work to achieve class A that is not clearly covered by `manual_action`/`manual_assertion` existing backend seams. Stop, default to B with user approval.
6. Any acceptance gate is in conflict with a PRD requirement (e.g. gate says PASS but PRD says behavior is wrong). Stop, PRD wins, ask user.
7. The handoff HEAD sha changes unexpectedly between gate runs (another agent or manual edit dirtied the tree). Stop, re-verify, re-run affected gates.

---

## 9. Final Handoff Evidence Section Template

The Sprint 7 handoff doc (`SPRINT-007-HANDOFF.md`) must contain these exact subsections at close. Add under `## 13. Tests and Validation` at the handoff HEAD:

```markdown
### 13a. pytest non-E2E (Gate 4) — final handoff run

Command: python -m pytest --tb=short -q --ignore=tests/e2e
HEAD: <sha>
Result: <N> passed, <N> skipped, <N> xfailed
New failures vs baseline: NONE  ← must say NONE

### 13b. jsdom (Gate 2) — final handoff run

Command: cd frontend && npm test
HEAD: <sha>
Result: <N> / <N> passed
New failures: NONE

### 13c. npm build (Gate 3) — final handoff run

Command: cd frontend && npm run build
Result: clean / dist sizes: autoworkbench.js <N> KB, autoworkbench.css <N> KB

### 13d. E2E — full 7-test suite (Gate 5)

HEAD: <sha>
Run date: 2026-05-<DD>

| Test file | Fate | Duration | Notes |
|---|---|---|---|
| test_v4_panel_smoke.py | PASS | Xs | — |
| test_mvp_001_lifecycle_smoke.py | PASS | Xs | — |
| test_basic_click_flow.py | <fate> | Xs | <BUG or PASS note> |
| test_exact_text_assertion_flow.py | <fate> | Xs | — |
| test_visible_assertion_flow.py | <fate> | Xs | — |
| test_correction_assert_then_click_flow.py | <fate> | Xs | — |
| test_llm_required_ambiguous_action_flow.py | <fate> | Xs | LLM path: fake/paid confirmed |

Full stdout: [link or paste from /tmp/s7-e2e-run.txt]

### 13e. Acceptance gates summary (Gate 1–10)

| Gate | Description | Result | Notes |
|---|---|---|---|
| 1 | Working tree clean | PASS/FAIL | — |
| 2 | jsdom green | PASS/FAIL | — |
| 3 | npm build clean | PASS/FAIL | — |
| 4 | pytest non-E2E green | PASS/FAIL | — |
| 5 | E2E suite classified | PASS/FAIL | all fate codes recorded |
| 6 | Control inventory resolved | PASS/FAIL | zero DEAD_CONTROL rows |
| 7 | Mock audit (D-108) clean | PASS/FAIL | DEFAULT_AGENTS verdict |
| 8 | Manual Mode classified | A/B/C | user approval if B |
| 9 | PRD reconciliation complete | PASS/FAIL | zero blank Final cells |
| 10 | Bug tickets for PARTIAL/DEFERRED | PASS/FAIL | list ticket ids |

### 13f. Final label

<COMPLETE_READY_FOR_SPRINT_8_TESTING | PARTIAL_NEEDS_FIXES | BLOCKED>

Reason: <one sentence>
```

The handoff document must not close without all subsections 13a–13f filled.

---

*End of S7-WRAP-FINAL-E2E-ACCEPTANCE-HANDOFF mini-spec.*
