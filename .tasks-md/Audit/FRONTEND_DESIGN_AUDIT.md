# Frontend Design Audit — production v4 vs `yui (1)/` design source

**Date:** 2026-05-14
**Reference design:** `/Users/apple/personal/agent v4/yui (1)/v4/` + `1AutoWorkbench — print.pdf`
**Production:** `/Users/apple/personal/agent v4/frontend/` (the dir served by `browser.py:104,245`)
**HEAD:** `fb0b8e0`

This audit is **read-only**. No fixes applied. Lists every surface where
production diverges from the approved design or is missing entirely.

Status codes:
- `OK` — matches design intent
- `DIVERGES` — present but visually/structurally different
- `MISSING` — design has it, production does not
- `EXTRA` — production added something not in design
- `EMPTY` — present in JSX but no real backend wiring (Sprint 8)

Priority codes:
- `P0` — user-visible breakage right now
- `P1` — feature gap noted in PRD/Sprint 7 scope
- `P2` — polish or fidelity gap
- `S8` — explicitly deferred to Sprint 8

---

## A. Header (`frontend/src/v4/chrome.jsx::Header`)

| Element | Design | Production | Status | Priority |
|---|---|---|---|---|
| Logo + "AutoWorkbench" | `aw-brand` + `aw-logo` | same | OK | — |
| Brand divider | `aw-brand-divider` | same | OK | — |
| Connection pill | 5 statuses: connected/busy/reconnect/offline/error | All 5 mapped (chrome.jsx) | OK | — |
| Mode pill | **Single read-only "LLM" pill** (`aw-status-pill mode`) | **LLM/Manual segmented toggle** (D-105) with Manual disabled | DIVERGES | P0 |
| Agents button | `aw-agents-btn` with **5 mock dots** (`agentsSummary`) | After my R2 fix: shows muted "—" placeholder (`aw-agents-setup`) when no payload | DIVERGES | P1 |
| Page URL pill | `acme.dev/pricing` shrinkable | Same | OK | — |
| Tokens pill | `tok · $cost` | Same | OK | — |
| Dock buttons | right/left/top/float | Same | OK | — |
| Collapse, Settings | icon buttons | Same | OK | — |

**Notes:**
- **D-105 toggle vs design "LLM" pill**: Design assumes single LLM mode. PRD/Sprint 7 added Manual Mode classification (`BUG-S8-MANUAL-001`). Decision needed: drop toggle and match design, or keep toggle and update design reference.
- **Agent dots**: design used mock dots fed by `agentsSummary`. Production fabricated the same array from phase in `aw-ide-panel.jsx:294` (D-108 missed it); my R2 fix removed fake fabrication. Per architecture invariant, header dots should reflect real `state.agents` only; when backend has no `agent_settings`, design's mock UI is not honest. **Match design SHAPE** but feed real data only.

---

## B. TabStrip (`frontend/src/v4/chrome.jsx::TabStrip`)

| Element | Design | Production | Status | Priority |
|---|---|---|---|---|
| 5 tabs (LLM/Steps/Recorded/Code/Trace) | yes | yes | OK | — |
| Tab labels | "LLM", "Steps", "Recorded", "Code", "Trace" | Same | OK | — |
| Per-tab icon | `I.Spark/I.Steps/I.Camera/I.Code/I.Trace` | Same | OK | — |
| Tab badge | `t.badge != null` → `<span className="aw-badge">{badge}</span>` | Renders counts (Steps `•1` visible in screenshots) | OK | — |
| Active tab visual | `aw-tab.active` class | Same | OK | — |

**Status:** TabStrip OK.

---

## C. NowStrip (Current task strip)

Design: renders **only when `tab === "llm" && state !== "idle"`** (app.jsx:124).

Design variants (per `STATE_META` in app.jsx):

| state | NowStrip kind | task copy | refLabel | primaryLabel |
|---|---|---|---|---|
| idle | (not rendered) | — | — | — |
| planning | `run` | "Page Intelligence is scanning…" | — | none |
| clarify | `decide` | "Choose how deep this run should go…" | "step 0 of 0" | "Jump to question" |
| recommend | `decide` | "Pick which assertions to include…" | — | "Use selected (5)" |
| plan | `decide` | "Plan v2 is ready — 6 steps, ~28s…" | — | "Confirm & run" |
| diff | `decide` | "I drafted plan v2 with your edits…" | — | "Apply changes" |
| permit | `decide` | "Need permission for one medium-risk click…" | "stp_d8e2" | "Allow once" |
| exec | `run` | "Resolving locator for the Most popular tag…" | "stp_c4d7" | "Pause" |
| locator | `block` | "Three visible Get started links — pick a candidate…" | "stp_d8e2" | "Choose candidate" |
| recover | `block` | "Assertion failed — actual text was $49 /mo…" | "stp_e1f4" | "Apply LLM repair" |
| done | `ok` | "6 of 6 recorded · 1 repaired · 31.2s…" | — | "Replay all" |
| offline | `block` | "Lost the websocket mid-step…" | — | "Reconnect now" |
| schema | `block` | "Model returned an unknown operation kind…" | — | "Ask LLM to repair" |
| nobrowser | `block` | "Backend is up but there's no browser…" | — | "Launch chromium" |
| apikey | `block` | "Main Orchestrator can't call the model…" | — | "Add key" |
| otp | `decide` | "Step 4 hit a 2FA prompt — type the 6-digit code…" | "stp_d8e2" | "Submit code" |
| e2e | `ok` | "Local run is recorded, but the paid E2E suite…" | — | "Trigger E2E now" |

**Production:** `aw-ide-panel.jsx:441-451` renders `NowStrip` via `phaseMetaFor(state, runtime)`. Need to verify all 17 states map. Earlier RC3 finding revealed `NowStrip` onPrimary guard expected `awaiting_confirmation` but prop holds `await` alias — that was fixed in `a5e4278` but exposes that the state→NowStrip mapping needs an audit.

| Status | Priority |
|---|---|
| DIVERGES | P1 — need state-map completeness check |

---

## D. Footer (`Footer` in design chrome.jsx:117)

| Element | Design | Production | Status |
|---|---|---|---|
| Phase label (with optional `aw-bar` busy stripe) | yes | yes | OK |
| `last:` event text | yes | yes | OK |
| Blocker (red highlighted) | conditional | conditional | OK |
| Next action (right side with caret) | conditional | conditional | OK |

**Status:** Footer OK.

---

## E. AgentsPopover (`frontend/src/v4/chrome.jsx::AgentsPopover`)

| Element | Design | Production | Status | Priority |
|---|---|---|---|---|
| 6 hardcoded agent rows (MO/PI/SR/DA/CR/RJ) | yes | DEFAULT_AGENTS removed (D-106) | DIVERGES | S8 |
| "5 active · 1 off" count | hardcoded text | replaced with "Read-only — Sprint 8" badge | DIVERGES | S8 |
| Agent row layout: initials avatar + name + model + last + ctrl buttons | rich | rendered when payload present | EMPTY when no payload | S8 |
| Status pill (running/active/standby/queued/disabled) | colored with ldot | rendered when payload present | EMPTY | S8 |
| Toggle (locked for required, on/off for others) | yes | rendered as `disabled` per D-106 | DIVERGES | S8 |
| Header icon + title + count | yes | yes | OK | — |
| Foot info + "Open agent trace" link | yes | similar copy points at `BUG-S8-AGENT-001` | DIVERGES | S8 |

**Tension:** Design assumes 6 mock agents always render; production refuses fake state per architecture invariants. Backend `agent_settings` event not yet emitted (Sprint 8 — `BUG-S8-AGENT-001`). Resolution: keep production's honest empty state until backend ships `agent_settings`, then design SHAPE renders from real payload.

---

## F. CollapsedRail

Design (`yui (1)/v4/app.jsx:191`): expand button + tab icons + status dot, vertical strip.

Production: `chrome.jsx::CollapsedRail` mounts when `collapsed === true`.

**Status:** Need to render-verify (not screenshot-checked this session). Mark `OK pending visual check`. Priority P2.

---

## G. LLM tab — Card inventory

Production exports 12 cards. Design has 16 cards. Production missing 4.

| Card | Design | Production | Status |
|---|---|---|---|
| `CardClarification` | yes | yes | OK |
| `CardRecommendation` | yes | yes | OK |
| `CardPlanDiff` | yes | yes | OK |
| `CardPlanReady` | yes | yes | OK |
| `CardPermission` | yes | yes | OK |
| `CardExecution` | yes | yes | OK |
| `CardLocatorAmbiguity` | yes | yes | OK |
| `CardRecovery` | yes | yes | OK |
| `CardCompleted` | yes | yes | OK |
| `CardOffline` | yes | yes | OK |
| `CardSchemaError` | yes | yes | OK |
| `CardNoBrowser` | yes | **NO** | MISSING |
| `CardApiKey` | yes | **NO** | MISSING |
| `CardOtp` | yes | **NO** | MISSING |
| `CardE2EPending` | yes | **NO** | MISSING |
| `LlmEmpty` | yes | yes | OK |
| `Composer` | yes | yes | OK (see I) |

**Priority:** P1 — `CardOtp` is OTP/2FA human input handler called out in PRD as P0 capability (`runtime_policy_spec` redaction policy). `CardApiKey` is fail-closed for missing key — important UX. `CardNoBrowser`, `CardE2EPending` lower priority.

**Atomic pieces in design also worth checking:**
- `Bubble` ✓ in production
- `Sys` ✓ in production
- `Reason` (think-head + bullet list, e.g. "Analyzing page" with DOM facts) — **MISSING in production**. Used in design `LlmThread` planning state to show LLM's reasoning steps. Production has no equivalent thinking/streaming render.
- `Conf` (confidence indicator with bars + High/Med/Low + %) — ✓ exported in production (`llm-cards.jsx:32`).

---

## H. LLM tab — Empty state (`LlmEmpty`)

| Element | Design | Production | Status |
|---|---|---|---|
| Icon | `I.Spark` | same | OK |
| Heading | "Describe what you want to automate or validate." | same | OK |
| Paragraph | "Tell me about a page, attach a selection from the page, or paste a Playwright snippet. I'll plan a flow, ask before running, and record evidence on the way." | same | OK |
| Suggestion chips | **4 chips**: "Validate this pricing page" / "Smoke test the login flow" / "Repair my flaky checkout spec" / "Record an Add-to-cart journey" | **3 chips** (missing "Record an Add-to-cart journey") | DIVERGES P2 |
| Chip onSeed wiring | yes | yes (post LLM-empty fix) | OK |

---

## I. LLM tab — Composer

| Element | Design | Production | Status | Priority |
|---|---|---|---|---|
| Context chips row (top) | `aw-context-chip` with page URL · selected count · file (e.g. "users.csv") + "Add" button | **MISSING** — production composer has no top context chips | DIVERGES | P1 |
| Textarea | rows=1, "Reply, refine the plan, or paste a step…" | same | OK | — |
| Bottom-left icons | **3 icons**: Paperclip · Mouse · Camera | **1 icon**: Mouse only (camera hidden by D-107, paperclip never added) | DIVERGES | P1 (paperclip), S8 (camera) |
| Provider badge | "complete-llm · gpt-class" small text next to icons | **MISSING** | DIVERGES | P2 |
| Send button | Primary with arrow icon + "Send" + `aw-kbd ↵` | same | OK | — |
| Render condition | Only when `tab === "llm" && state !== "idle"` (design app.jsx:128) | Always renders on LLM tab regardless of state | DIVERGES | P1 |

---

## J. Steps tab — Toolbar (`aw-list-toolbar`)

| Element | Design | Production | Status | Priority |
|---|---|---|---|---|
| **Add step** button (`aw-btn primary` + `I.Plus`) | yes | yes (but called `steps-add`) | OK | — |
| **Pick element** button (`aw-btn` + `I.Mouse`) | yes | yes (`steps-pick`) | OK | — |
| Filter search input (`aw-search` + `I.Search` + input) | yes | yes (`steps-filter`) | OK | — |
| Filter button (icon only) | yes | **MISSING** | DIVERGES | P2 |

**Info strip** (below toolbar):
| Element | Design | Production | Status |
|---|---|---|---|
| Info icon + "Step display order is for your convenience…" text | yes | yes | OK |
| **Run all** button — design label: "Run all through LLM" | yes | yes — production label: "Run Pending Steps" | DIVERGES P2 (copy) |
| **Run selected** button (with count) | yes | yes | OK |

---

## K. Steps tab — Step row structure

Design step row (`aw-step-row`):
```
[handle] [step-idx (pending/warn/err/vio)] 
  [aw-step-title with .id]
  [aw-step-meta: aw-badge-i ok|warn|err|info|vio|outline]
  [aw-step-attached (or warn-styled with locator hint)]
  [aw-step-op rows for sections]
[actions: Duplicate / More icons]
```

Step rows are **display-only** with rich badge variants.

Production step row (`secondary-tabs.jsx::StepRow ~line 540`):
```
[handle] [step-idx pending] 
  [ide-step-topline: <input> + status badge]    ← INTERACTIVE INPUT, not title text
  [ide-step-target-summary]                     ← target text
  [StepLocatorChip, StepKindChip, StepChildCountBadge, StepBlockedStrip, StepPreconditionStrip, StepChildrenList]
  [optional candidate <select>]
  [ide-step-outcome: chip buttons]              ← INTERACTIVE outcome picker
  [ide-step-actions: Attach Element / Duplicate / Remove buttons]
```

**Status:** DIVERGES P1 (intentional). Production added drafting capability (intent input + outcome chips + actions) that design didn't have. Design was display-only mockup. The Sprint 7 D-101 metadata strips (locator/kind/count/blocked/precondition/children) extend the meta area with backend-driven badges — design has the same badges via `aw-badge-i` but no draft input.

Post `fb0b8e0` (my CSS fix), the `ide-*` interactive elements now have styling. Need visual verification that combined drafting + design badges render coherently.

| Sub-element | Issue |
|---|---|
| Step title vs step input | Production shows `<input>` for intent — design shows static title with step ID badge. After step is "ready" (backend confirmed?) production could switch to title display. Sprint 8 polish. |
| Step ID badge (`.id`) | Design shows `stp_001` etc; production not visibly rendered. Need to add `data-testid="step-id-${stepId}"` with mono-font small text. |
| Section step children rendering (`aw-step-op` with `op-tag`) | Production renders via `StepChildrenList`; styles now match (just added). Need visual check. |
| Multiple background colors for blocked/wrong-page (red-soft, yellow-soft) | Design uses inline `borderColor:"#E8B9AE", background:"#FBEEEA"` for blocked; production `aw-step-blocked` CSS I just added. Matches. |

---

## L. Recorded tab

Design row (`aw-rec-item`):
```
[aw-rec-head: step-idx ok|warn|skip · title · "Repeat"/"More" icons]
  [aw-step-meta with badges: "recorded" · "locator: getByRole(...)" · timing · count]
[aw-step-ops with op-tag chips for child operations]   (for some rows)
[aw-rec-shot div]                                       (for some rows — screenshot strip)
[aw-diff add/rem rows]                                  (for repaired rows)
[aw-step-meta repair reason]                            (for repaired rows)
```

Production (`RecordedTab` `secondary-tabs.jsx:780+`): renders `recorded-row-${id}` with `recorded-status`, `recorded-locator`, `recorded-expected`/`recorded-observed`, `recorded-child-list`, `recorded-artifact`. D-102 implementation.

| Sub-element | Status | Priority |
|---|---|---|
| Step idx with check/sync/skip icon | Design uses I.Check, I.Sync, I.Skip variants; production likely uses same | OK pending visual check |
| Title with `rec_xxxx · v1` mono ID | Design has it; production needs verification | UNKNOWN |
| Repair diff (`aw-diff add|rem` rows) | Design has `expect(loc).toHaveText(...)` → `expect(loc).toContainText(...)` style | Production: not in current recorded JSX. Sprint 8? | MISSING P1 |
| Repair reason "repair reason: actual text was X · relaxed by LLM repair…" | Design has it | Production: missing | MISSING P1 |
| Screenshot strip (`aw-rec-shot`) | Design renders blank-ish gradient strip when screenshot present | Production: `recorded-artifact-${stepId}-${artifactId}` text links, no visual screenshot tile | DIVERGES P1 |
| Skipped row state (dashed border idx, color-faded title, "not recorded — no evidence to show") | Design has it | Production may have it via `data-status="skipped"` | UNKNOWN P2 |

---

## M. Code tab

Design layout:
```
[aw-info-strip blue: "Code is rendered from code_update events emitted by the backend after successful recording. Frontend does not generate code."]
[aw-list-toolbar sticky: 
   I.Doc + path "tests/pricing.spec.ts" mono + aw-badge-i info "updated 4s ago"
   spacer
   "Copy" / "Save" / "More" buttons]
[padding 10px 14px]
  [aw-badge-i row: "1 fragile locator" + "2 placeholder values" + "mapped to 5 recorded steps"]
  [aw-code <pre> with syntax-highlighted classes: com/kw/var/pun/fn/str/num]
  [aw-card-section-title "Warnings inline"]
  [aw-dotlist:
     L18 fragile selector hint
     L24 repaired assertion · replay history link
     code_gen FAQ skipped]
```

Production `CodeTab` (D-103):
| Element | Status |
|---|---|
| aw-info-strip blue header explaining provenance | UNKNOWN — verify |
| Toolbar with file path + badge | Present, may differ |
| Copy / Save / Export | Wired via D-103 export_code typed seam |
| Save result chip (`code-save-result`) | Production has it, design doesn't |
| Code preview with syntax highlighting | Design has classes (`com`, `kw`, `var`, `pun`, `fn`, `str`, `num`). Production: need to verify if syntax-highlighting is applied or raw text only | DIVERGES P1 likely |
| Top badge row (fragile / placeholder / mapped) | MISSING in production | MISSING P2 |
| Section title "Warnings inline" | Production has `codeDiagnostics` array but rendered differently | DIVERGES P2 |
| Per-line warning dotlist with line markers | MISSING in production likely | MISSING P2 |

---

## N. Trace tab

Design:
```
[aw-list-toolbar:
   aw-search input "Filter events…"
   filter chips: all (info active) / llm (outline) / step (outline) / permission (outline) / error (outline)
   spacer
   Download icon button]
[aw-info-strip red: Failure detail with fail-grid (expected/actual/layer/next)]
[Per-event rows: aw-trace-row {cls}: timestamp · icon · type · desc]
```

Production `TraceTab` (D-104):
| Element | Status |
|---|---|
| Search input | Wired — text filter on `summary` |
| Filter chips | 7 chips: all / llm / step / permission / error / code / gap (added by D-104) | EXTRA OK (more granular than design 5; design's gap belongs in this set) |
| Download icon | UNKNOWN |
| Failure detail strip (red) | D-104 implements via `trace-failure-detail-${i}` for step_failed rows | OK |
| Event rows with type / icon / desc | yes | OK |
| Row classes (`io|llm|ok|warn|err`) | Production: type-based variants | OK |
| LLM telemetry section | Production has `trace-llm-unavailable` honest fallback | EXTRA OK |
| Artifact list per row | Production: `trace-artifact-list-${i}` | OK |
| Capability gap card | Production: `trace-gap-card-${i}` (D-104) | EXTRA OK |
| Redaction chip | `trace-redaction-chip-${i}` | EXTRA OK |

**Status:** Trace tab is the most complete vs design — production EXTENDED design with gap/telemetry/redaction. Good.

---

## O. CSS coverage

**Pre-fb0b8e0:** 16 `ide-*` + 12 `aw-*` Sprint 7 classes had zero CSS rules → layout broken.

**Post-fb0b8e0:** all classes covered. `comm` of JSX classes vs CSS classes = zero unstyled.

**Status:** OK.

**Remaining CSS-only fidelity questions:**
- Does production v4.css match design styles.css for `aw-step-title`/`aw-step-meta`/`aw-step-attached`/`aw-card-foot`/`aw-card-head`/`aw-thread`/`aw-msg-system`/`aw-msg-user`/`aw-empty`/`aw-suggestions`/`aw-context-chip` exactly? Diff earlier showed only the mode-toggle additions differ. **Spot check needed.**
- Design uses inline `style={{ background:"#FBEEEA", borderColor:"#E8B9AE" }}` for warning strips; production uses CSS classes (`.aw-step-blocked`). Renders equivalent.

---

## P. State coverage (LLM lifecycle)

Design defines 17 states in `STATE_META` (idle / planning / clarify / recommend / plan / diff / permit / exec / locator / recover / done / offline / schema / nobrowser / apikey / otp / e2e).

Production `phaseMetaFor(state, runtime)` in `aw-ide-panel.jsx`: need full audit of which states map to what NowStrip + Card combination.

| State | NowStrip+Card design intent | Production wiring | Status |
|---|---|---|---|
| idle | LlmEmpty card, no NowStrip, no Composer | OK | OK |
| planning | NowStrip "Analyzing", Reason+Sys+CardClarification gate | Reason missing; NowStrip likely OK | DIVERGES (no Reason render) |
| clarify | + CardClarification | OK | OK |
| recommend | + CardRecommendation | OK | OK |
| plan | + CardPlanReady (with optional CardPlanDiff if diff also present) | OK | OK |
| diff | + CardPlanDiff | OK | OK |
| permit | + CardPermission | OK | OK |
| exec | + CardExecution | OK | OK |
| locator | + CardLocatorAmbiguity | OK | OK |
| recover | + CardRecovery | OK | OK |
| done | + CardCompleted | OK | OK |
| offline | + CardOffline | OK | OK |
| schema | + CardSchemaError | OK | OK |
| nobrowser | + CardNoBrowser | **MISSING card** | MISSING P1 |
| apikey | + CardApiKey | **MISSING card** | MISSING P1 |
| otp | + CardOtp | **MISSING card** | MISSING P1 |
| e2e | + CardCompleted + CardE2EPending | **MISSING CardE2EPending** | MISSING P2 |

---

## Q. Render-condition behaviors

| Behavior | Design | Production | Status |
|---|---|---|---|
| Composer visible | `tab === "llm" && state !== "idle"` | Always on LLM tab regardless of state | DIVERGES P1 |
| NowStrip visible | `tab === "llm" && state !== "idle"` | Need verification | UNKNOWN |
| Auto-scroll body to bottom on state/tab change | `useEffect → bodyRef.current.scrollTop = scrollHeight` | UNKNOWN — verify | UNKNOWN P2 |
| Auto-switch to LLM tab on plan_ready | Not in design (design has manual TweakSelect) | Production now does (commit `6c05920`) | EXTRA OK |
| Auto-scroll LLM thread to latest message | Design uses bodyRef.scrollHeight | UNKNOWN | UNKNOWN P2 |

---

## R. Missing or extra components

**Missing in production:**
1. `Reason` component (think-head + bullet list of reasoning steps) — design uses it in planning state messages
2. `CardNoBrowser`
3. `CardApiKey`
4. `CardOtp` — important per spec for OTP/2FA handling
5. `CardE2EPending`
6. Composer context chips row (page URL · selected · file chip)
7. Composer paperclip attach button
8. Composer provider badge ("complete-llm · gpt-class")
9. Steps tab filter button (icon-only, next to search)
10. LlmEmpty 4th suggestion chip ("Record an Add-to-cart journey")
11. Repaired-step diff render in Recorded tab
12. Recorded screenshot strip (visual tile, not just artifact link)
13. Code tab top badge row ("1 fragile locator", "2 placeholder values", "mapped to N recorded steps")
14. Code tab "Warnings inline" section with per-line annotations
15. Code tab syntax-highlighting classes on the `<pre>` content

**Extra in production (not in design):**
1. D-105 LLM/Manual mode toggle (vs single "LLM" pill)
2. Composer's `code-save-result` chip after save (D-103)
3. Step row interactive draft inputs (intent + outcome chips + Attach Element button)
4. Step row D-101 metadata strips (locator kind, child count, blocked, precondition, navigate-to-expected)
5. Trace tab gap-category chip
6. Trace tab LLM telemetry "unavailable" honest fallback
7. Trace tab capability_gap_recorded card
8. Trace tab redaction status chip
9. Recorded tab expected/observed honest payload rows

---

## S. Architectural invariants vs design fidelity

**Conflicts identified:**

| Architectural invariant (PRD) | Design pattern (yui) | Resolution |
|---|---|---|
| Backend owns runtime truth — no fake agent state | Agents popover renders 6 mock agents with mock statuses | Keep design SHAPE (agent row layout, status pills, toggles) but feed from real `agent_settings` event; show honest empty state until backend ships event. **Currently aligned with invariant.** |
| Frontend renders only backend events; no fake LLM thread | Design `LlmThread` renders Bubble/Sys/Reason cards from STATE_META mock per state | Production renders from real `conversation` array and backend cards. Reason render component missing. |
| No fake trace/telemetry | Design TraceTab has 24 hardcoded events with mock timings/cost | Production renders from real `traceEntries` only. **Currently aligned with invariant.** |
| No static recorded steps | Design RecordedTab has 5 hardcoded recorded items | Production renders from real `recordedSteps`. **Currently aligned with invariant.** |
| No code generation in frontend | Design CodeTab has hardcoded pricing.spec.ts pre with syntax highlighting | Production renders only from `code_update` backend payload. Syntax highlighting can be applied to backend payload — **add this as P1**. |

---

## T. Highest-priority issues (proposed fix order)

If user wants to start fixing, suggested sequence (smallest blast radius first):

**P0 (visible breakage):**
1. Composer visible-only-on-non-idle render condition (`tab === "llm" && state !== "idle"`).
2. Mode toggle decision (keep D-105 vs revert to single "LLM" pill).

**P1 (PRD-noted gaps):**
3. Add `CardNoBrowser` / `CardApiKey` / `CardOtp` / `CardE2EPending` (4 state cards).
4. Add `Reason` component (think-head + bullet list) — required for planning state.
5. Composer context chips row (page URL · selected count · file chip).
6. Composer paperclip attach button.
7. Recorded tab: repair diff rendering for repaired steps + repair reason text.
8. Recorded tab: visual screenshot strip (not just artifact link).
9. Code tab: syntax highlighting on backend `code_update` payload.
10. Code tab: top badge row (fragile / placeholder / mapped counts).
11. Step row: render step ID badge (`stp_xxx` mono).
12. State-map completeness check for all 17 design states.

**P2 (polish):**
13. Steps tab filter button (icon-only secondary).
14. LlmEmpty 4th suggestion chip.
15. Composer provider badge.
16. Run-all button copy: "Run Pending Steps" → "Run all through LLM" (or leave production label).
17. Code tab "Warnings inline" section with per-line annotations.
18. CSS exact-match sweep vs design `styles.css`.
19. Visual regression test fixture (Playwright snapshot per tab × per state).

**S8 (deferred):**
20. AgentsPopover real agent rows when backend `agent_settings` ships.
21. Manual Mode foundation per `BUG-S8-MANUAL-001`.

---

## U. Files inventoried

**Design source** (`yui (1)/v4/`):
- `app.jsx` 220L — panel shell with STATE_META + TweaksPanel
- `chrome.jsx` 268L — Header / TabStrip / NowStrip / Footer / AgentsPopover / CollapsedRail
- `icons.jsx` 59L — icon set
- `llm-tab.jsx` 901L — 16 cards + Reason / Bubble / Sys / Conf / LlmEmpty / Composer / LlmThread
- `secondary-tabs.jsx` 417L — StepsTab / RecordedTab / CodeTab / TraceTab
- `styles.css` 1184L

**Production:**
- `frontend/aw-ide-panel.jsx` 485L — main panel shell
- `frontend/src/v4/chrome.jsx` 389L
- `frontend/src/v4/icons.jsx` 63L
- `frontend/src/v4/llm-cards.jsx` 1109L — 12 cards (4 missing)
- `frontend/src/v4/secondary-tabs.jsx` 1430L
- `frontend/v4.css` 1235L (now 1875L+ after my fb0b8e0 fix)

---

## V. Out of scope (this audit)

- E2E flow tests selector migration (separate ticket `BUG-S8-E2E-001`)
- `storeDispatch` typed-store wiring gap (separate ticket `BUG-S8-FRONTEND-STORE-001`)
- Backend event coverage of 17 design states (separate audit)
- PDF page-by-page interaction-spec audit (requires PDF rendering tools; pdftotext not installed)

---

**End of Phase 1 audit.** No code changed in this pass.

---

# Phase 2A — Triage Decisions

**Date:** 2026-05-14 (same session)
**Rule:** PRD/spec wins over design prototype. Production must remain backend-event/store-truth driven. Static design mocks must not become live runtime truth.

Decision codes:
- `FIX_NOW_P0` — visible breakage or PRD-mandated, apply this pass
- `KEEP_PRODUCTION` — production correct vs PRD; design prototype was a mockup
- `DEFER_SPRINT_8` — needs backend event/seam not yet emitted
- `REJECT_DESIGN_MOCK` — design renders fake runtime state; architecture invariant forbids
- `ACCEPTED_DIVERGENCE` — intentional Sprint 7 product improvement over design
- `NEEDS_USER_DECISION` — product call required

## P0 findings — triage

| # | Finding | Design behavior | PRD/spec requirement | Production behavior | Decision | Sprint | Reason |
|---|---|---|---|---|---|---|---|
| 1 | Composer hidden on idle | hide when `state === "idle"` | `03_FRONTEND_RUNTIME.md:89` — idle = "ready state, add step, load session, start recording". User MUST be able to start LLM request from idle. PRD does not require hiding composer. Frontend UI spec §10 lists "LLM chat input" as a stable hook (`frontend_ui_spec.md:855`) without idle-gating. | composer always visible on LLM tab | **KEEP_PRODUCTION** | — | Hiding composer in idle removes the start-intent UI. PRD explicitly requires starting from idle. Design prototype hid composer because state machine demo started in non-idle; not normative. |
| 2 | Mode toggle LLM/Manual vs single "LLM" pill | single read-only pill | PRD lists Manual Mode as P0 capability (`02_LLM_RUNTIME.md`, `BUG-S8-MANUAL-001`); D-105 locked classification = DISABLED_WITH_REASON | LLM/Manual segmented control; Manual disabled with Sprint 8 title | **KEEP_PRODUCTION** | — | D-105 lock holds. Single pill would hide the Manual deferral signal; segmented control surfaces it honestly. |

## P1 findings — triage

| # | Finding | Decision | Sprint | Reason |
|---|---|---|---|---|
| 3 | `CardNoBrowser` missing | **DEFER_SPRINT_8** | S8 | Backend emits no `no_browser` / `nobrowser` event. Implementing now would require frontend to invent the state (forbidden invariant). Filed under `BUG-S8-NO-BROWSER-CARD-001`. |
| 4 | `CardApiKey` missing | **DEFER_SPRINT_8** | S8 | Backend redacts API keys in error messages but emits no typed `api_key_missing` event. Implementing now → fake state. Filed under `BUG-S8-API-KEY-CARD-001`. |
| 5 | `CardOtp` missing | **DEFER_SPRINT_8** | S8 | Backend emits no `human_input_required` / `otp_required` event. Spec says "Backend redacts the value from screenshots and trace" — backend seam doesn't exist yet. Filed under `BUG-S8-OTP-CARD-001`. |
| 6 | `CardE2EPending` missing | **DEFER_SPRINT_8** | S8 | Backend emits no `e2e_pending` / `e2e_passed` event. Local-only Sprint 7 has no paid E2E scheduling. Filed under `BUG-S8-E2E-PENDING-CARD-001`. |
| 7 | `Reason` atomic component (think-head + bullet list) missing | **DEFER_SPRINT_8** | S8 | Backend emits `llm_thinking` per `02_LLM_RUNTIME.md:1583` but production reducer doesn't surface its content as bullet-list reasoning steps. Sprint 8 needs to wire `llm_thinking` payload → `Reason` JSX. Production currently shows `LlmEmpty` then plan card directly; no thinking visualization. Filed under `BUG-S8-LLM-THINKING-RENDER-001`. |
| 8 | Composer context chips row (page URL · selected · file) | **DEFER_SPRINT_8** | S8 | Need backend payload for current page URL + selected element count + attached files. `runtime.storeState.page_url` may exist; selection count may exist via picker state. Sprint 8 builds chip row from real payload only. Filed under `BUG-S8-COMPOSER-CONTEXT-CHIPS-001`. |
| 9 | Composer paperclip attach button | **DEFER_SPRINT_8** | S8 | Requires file-attach typed seam to backend. None exists today. Filed under `BUG-S8-COMPOSER-ATTACH-001`. |
| 10 | Recorded tab repair diff render + repair reason | **DEFER_SPRINT_8** | S8 | Backend emits `step_recorded` with `repair_reason` payload only when LLM repair applied (`02_LLM_RUNTIME.md::recovery`). Production renders honest expected/observed but no diff render. Sprint 8 reads `recorded_step.repair.before/after` and renders `aw-diff` lines. Filed under `BUG-S8-RECORDED-REPAIR-DIFF-001`. |
| 11 | Recorded screenshot strip (visual tile) | **DEFER_SPRINT_8** | S8 | Backend emits `artifact_attached` with screenshot path; production renders link only. Visual tile needs `<img>` from artifact URL — verify CSP allows blob/data URLs into shadow DOM. Filed under `BUG-S8-RECORDED-SCREENSHOT-TILE-001`. |
| 12 | Code tab syntax highlighting | **DEFER_SPRINT_8** | S8 | Backend payload is plain code string; frontend would need to tokenize (e.g. prism / shiki). Pure visual polish; no architecture impact. Filed under `BUG-S8-CODE-SYNTAX-HIGHLIGHT-001`. |
| 13 | State-map completeness for 17 design states | **PARTIAL — covered + DEFER** | mix | Existing production maps idle/planning/clarify/recommend/plan/diff/permit/exec/locator/recover/done/offline/schema (13 states). Remaining 4 states (nobrowser/apikey/otp/e2e) are gated by Sprint 8 backend events (findings 3-6). Production state-map is complete relative to backend events that exist today. **No fix needed this pass.** |
| 14 | Step row interactive vs design display-only | **ACCEPTED_DIVERGENCE** | — | Production adds drafting capability (intent input + outcome chips + Attach Element button + D-101 metadata strips). PRD `03_FRONTEND_RUNTIME.md:90` requires "drafting mode" with editor — production correct, design was display-only mockup. |
| 15 | Step row missing step ID badge (`stp_xxx` mono) | **FIX_NOW_P0** | — | Tiny visual addition: add `data-testid="step-id-${stepId}"` span next to title in StepRow. Helps user identify steps. Already used in design `.aw-step-title .id` CSS — class exists. Low risk. |

## P2 findings — triage

| # | Finding | Decision | Sprint |
|---|---|---|---|
| 16 | Steps tab filter icon button | **DEFER_SPRINT_8** | S8 — no real filter taxonomy yet |
| 17 | LlmEmpty 4th chip "Record an Add-to-cart journey" | **FIX_NOW_P0** | — | trivial copy add |
| 18 | Composer provider badge ("complete-llm · gpt-class") | **DEFER_SPRINT_8** | S8 — needs `model_in_use` backend event |
| 19 | Run-all button copy: "Run Pending Steps" vs design "Run all through LLM" | **KEEP_PRODUCTION** | — | Production label more accurate (covers both LLM and Manual modes when latter ships) |
| 20 | Code tab top badge row (fragile/placeholder/mapped counts) | **DEFER_SPRINT_8** | S8 — backend payload doesn't surface counts yet |
| 21 | Code tab "Warnings inline" per-line annotations | **DEFER_SPRINT_8** | S8 |
| 22 | CSS exact-match sweep vs design styles.css | **PARTIAL — covered** | — | After `fb0b8e0`, all 28 v4 classes have CSS rules. Diff showed only my mode-toggle additions differ structurally. Acceptable. |
| 23 | Visual regression test fixture (Playwright snapshot per tab × per state) | **DEFER_SPRINT_8** | S8 — new infrastructure |
| 24 | Auto-scroll body on state/tab change | **DEFER_SPRINT_8** | S8 | P2 polish, not Sprint 7 acceptance blocker. Global auto-scroll on state/tab change can disrupt Steps / Trace / Code / Recorded review (user scrolling through content gets jerked). Sprint 8 must design scoped auto-scroll (LLM tab only? new-message only?) and add jsdom coverage. Filed under `BUG-S8-AUTOSCROLL-001`. |
| 25 | NowStrip render-condition check | **PARTIAL — covered** | — | RC3 already fixed (`a5e4278`); production now reads phase correctly. |

## S — Architectural invariant tensions

| Finding | Decision | Reason |
|---|---|---|
| AgentsPopover with 6 mock agents | **REJECT_DESIGN_MOCK** | Backend `agent_settings` event not yet emitted. Production renders honest empty state. Restore design SHAPE when `BUG-S8-AGENT-001` ships. |
| TraceTab 24 mock events | **REJECT_DESIGN_MOCK** | Production renders real `traceEntries` only. |
| RecordedTab 5 mock items | **REJECT_DESIGN_MOCK** | Production renders real `recordedSteps` only. |
| CodeTab hardcoded `pricing.spec.ts` | **REJECT_DESIGN_MOCK** | Production renders only from `code_update` event. |

## P0 fixes applied this pass

Two safe-and-tiny P0 items only:

1. **Finding #15** — Add step ID badge `stp_xxx` to StepRow title for visual parity. Single span + CSS already exists.
2. **Finding #17** — Add 4th LlmEmpty chip "Record an Add-to-cart journey". Single array entry.

Everything else: classified above. No code changes for any DEFER_SPRINT_8 / KEEP_PRODUCTION / REJECT_DESIGN_MOCK / NEEDS_USER_DECISION row.

## Sprint 8 tickets to create (from this triage)

- `BUG-S8-NO-BROWSER-CARD-001`
- `BUG-S8-API-KEY-CARD-001`
- `BUG-S8-OTP-CARD-001`
- `BUG-S8-E2E-PENDING-CARD-001`
- `BUG-S8-LLM-THINKING-RENDER-001`
- `BUG-S8-COMPOSER-CONTEXT-CHIPS-001`
- `BUG-S8-COMPOSER-ATTACH-001`
- `BUG-S8-RECORDED-REPAIR-DIFF-001`
- `BUG-S8-RECORDED-SCREENSHOT-TILE-001`
- `BUG-S8-CODE-SYNTAX-HIGHLIGHT-001`

All reference this audit and the affected design source files.

---

**Phase 2A complete.** Decisions recorded. Two P0 fixes pending; everything else stays where it is.
