# Locator Strategies Gap — Deterministic Waterfall vs LLM Fallback

Audit of the 8 deterministic locator-resolution strategies and the LLM fallback ordering against PRD v2.3 and the Complete LLM Mode P0 spec. Read-only. No code changes.

## 1. Spec-required 8 strategies (canonical order)

From `PRD_v2_3_Modular_Pack_v2/02_LLM_RUNTIME.md` §"Locator priority waterfall" (lines 635–696):

1. **Test attributes** — `data-testid`, `data-cy`, `data-qa`, `data-test`, `data-automation-id` (lines 642–644)
2. **Semantic / ARIA** — `aria-label`, `aria-role`, `role + name`, `aria-placeholder`, `aria-describedby` (lines 646–649)
3. **Native attributes** — `id (unique)`, `name`, `type + value` combination (lines 651–653)
4. **Text content** — exact text match, then partial text (`getByText(..., exact=false)`) (lines 655–657)
5. **Label association** — `getByLabel()` (lines 659–660)
6. **Placeholder** — `getByPlaceholder()` (lines 662–663)
7. **Alt text** — `getByAltText()` for images (lines 665–666)
8. **CSS selectors** — stable class combinations / attribute selectors; avoid dynamic classes (lines 668–671)

Then:
- **9. LLM layer** — only if all 8 fail; receives focused element snapshot + history (lines 673–679)
- **10. XPath** — last resort, only on LLM recommendation, flagged fragile (lines 681–686)
- **11. JS injection** — LLM-recommended + user confirmation (lines 688–695)

`autoworkbench_complete_llm_mode_p_0_scenarios_spec (2).md` §3.10 (lines 215–256) restates an overlapping "default semantic priority" with slightly different ordering: `role+accessible_name → label → placeholder → alt/title → stable data-testid → aria → stable scoped text → stable id → scoped CSS → XPath last`. Scenario 3 §8 (lines 759–791) repeats the same list.

**Spec ambiguous**: PRD 02 puts `data-testid` first (stability-ranked), §3.10 puts `role+name` first (semantic-ranked). The runtime policy spec §4 (lines 97–114) only says "deterministic-first" without naming the strategies. Implementer must reconcile.

## 2. Code today — per-strategy presence

Primary generator: `agent.py` `_build_locator_candidates` (lines 9731–9848), thin-wrapped by `locator/resolver.py:227-344` (note: `resolver.py` references `self._loop._*` but is not bound to a loop — appears half-extracted, see Conflicts §7). Secondary generator: `runtime/locator_intelligence.py` `_build_locator_from_attrs` (lines 188–207). Selector engine for snapshots: `runtime/dom_locator_contract.py` `_selector_for_candidate` (lines 154–174).

| # | Strategy | Status | Evidence |
|---|---|---|---|
| 1 | Test attributes | **partial** | `agent.py:9758-9774` reads `data-testid`, `data-test-id`, `data-test`, `data-qa`, `data-cy`. **Missing** `data-automation-id`. `locator_intelligence.py:190` only checks `data-testid`, `data-cy`. |
| 2 | Semantic/ARIA | **partial** | `aria-label` at `agent.py:9776-9785`; `role+name` at `agent.py:9816-9825`. **Missing** `aria-placeholder`, `aria-describedby`. Pure-`role` (no name) absent. |
| 3 | Native attributes | **partial** | `id` at `agent.py:9787-9789`. **`name` attribute not emitted as a candidate** (no `[name=...]` generation in `_build_locator_candidates`; only `locator_intelligence.py:197-198` builds `[name=…]` but that pipeline is not chained into the find loop). **`type + value` combination absent.** |
| 4 | Text content | **present** | exact `agent.py:9800-9806`, partial `9808-9814` (truncated to 50 chars — may differ from PRD's `exact:false` semantics). |
| 5 | Label association | **partial** | `aria-label` is emitted as `get_by_label(...)` at `agent.py:9783`, which conflates ARIA label with HTML `<label for=>` association. **True `<label>`-for-input association not extracted.** `dom_locator_contract.py:177-185` reads `label` attribute, not associated `<label>` element. |
| 6 | Placeholder | **present** | `agent.py:9791-9798` |
| 7 | **Alt text** | **ABSENT** | No `get_by_alt_text` / `getByAltText` / alt-attribute candidate anywhere. `grep -n "get_by_alt\|alt_text" agent.py locator/*` returns nothing. `dom_locator_contract.py:413-415` stores `alt` on records but never emits an alt-text locator candidate. |
| 8 | CSS selectors | **present, fragile** | `agent.py:9827-9829` via `LocatorResolver.build_locator_from_strategy("css", …)` at `locator/resolver.py:113-129`. No filter for dynamic/generated class names beyond `risk_flags` annotation in `dom_locator_contract.py:230-266`. |

Additional emitted candidates outside the spec: `locator_hint` (`agent.py:9749-9756`), `relative_xpath` (9831-9837), `absolute_xpath` (9839-9846). XPath being a "Last Resort #10" per PRD is **emitted proactively** today, contrary to spec lines 681–686 ("Never proactively generated").

Resolver dispatch (`locator/resolver.py:205-225` and mirror in `agent.py:7408-7443`) recognises 5 tool forms: `get_by_test_id`, `get_by_label`, `get_by_placeholder`, `get_by_text`, `get_by_role`. **No `get_by_alt_text` resolver case.** Falls through to `page.locator(...)` for anything unknown.

## 3. LLM fallback gating

Spec (PRD 02 line 673; §3.10 lines 239–241; Scenario 3 lines 793–802): LLM fallback is triggered only after **all 8 programmatic strategies fail** OR when (a) candidates are ambiguous, (b) result is low-confidence/fragile (<60), (c) user explicitly asks, (d) repair after failure, (e) semantic interpretation on weak DOM.

Code today (`runtime/agent_locator_handlers.py:62-119` `tool_locator_find`): iterates candidates produced by `_build_locator_candidates` until one returns `count == 1`; on miss it calls `scope_candidates(...)` (line 109) and returns `found: False` with `scope_suggestions`. **No LLM-escalation call site triggers from this handler.** `runtime/dom_locator_contract.py:941-1030` defines `build_locator_escalation_request(...)` (purpose `locator_specialist`) but `grep -rn "build_locator_escalation_request\|locator_specialist" --include=*.py` shows it is constructed only by dom contracts and consumed by tests — no agent.py call path invokes it after the 8-strategy loop fails.

**Gap**: there is no enforced "all 8 exhausted → escalate" sequencer. The current loop simply returns `found: False`; what happens next is decided by the LLM-driven plan layer (free-form), not by a deterministic gate. The §10.5 Locator-Specialist gate (`autoworkbench_complete_llm_mode_runtime_policy_spec.md:449-461`) requires `candidate locators tried` in the escalation packet — `tried[]` is built (`agent_locator_handlers.py:80-107`) but is not wired into an escalation event.

## 4. Event surface

Spec references:
- `04_BACKEND_EVENT_CONTRACT.md:57` defines a frontend command `update_locator { step_id, operation_id?, constraints? }`. **The doc does not specify a `locator_update_request` server event schema** — that name comes from `scenarios_spec §21.2` (line 1814). **Spec ambiguous**: PRD 04 names the action `update_locator` (command) whereas scenarios spec names it `locator_update_request` (server event). `locator_candidates_ready` does not appear in PRD 04 at all (scenarios spec uses `locator_candidates_generated` at line 869 and `view_candidates` action at line 1804).

Code:
- `runtime/event_contracts.py:1121-1171` `build_locator_update_request_event` — payload: `run_id`, `step_id`, `ambiguity_id`, `current_locator`, `trigger`, optional `operation_id`. Adds 1024-char DOM-injection guard.
- `runtime/event_contracts.py:2059-2088` `build_locator_candidates_ready_event` — payload: `ambiguity_id`, `candidates[]`; strips `raw_dom`.
- **Builders exist but no production emitter calls them.** `grep -rn 'build_locator_update_request_event\|build_locator_candidates_ready_event' --include='*.py'` outside `tests/` returns only the definitions in `event_contracts.py`. `agent.py`, `runtime/locator_update.py`, `runtime/agent_locator_handlers.py` never emit.
- `runtime/locator_update.py:46-85` implements precondition + history append in-memory; does **not** emit `precondition_failed_for_locator_update` (scenarios §21.3 line 1844). No event-bus hook.
- Schema mismatches vs scenarios §21.2 (line 1814) which expects `(step_id, operation_id, requested_action, user_hint?)`. Code's `build_locator_update_request_event` uses `trigger`, `ambiguity_id`, `current_locator` — semantically different. **Spec ambiguous**, but the divergence is real.

## 5. Gap matrix

| # | Strategy | Status | Gap | Fix sketch |
|---|---|---|---|---|
| 1 | data-testid family | partial | `data-automation-id` missing | Add to attribute fallback chain in `_build_locator_candidates` |
| 2 | ARIA | partial | No `aria-placeholder`, `aria-describedby`, role-only | Extend candidate builder; add resolver case if needed |
| 3 | Native attrs | partial | `name`, `type+value` not emitted | Add `[name=…]` / `input[type=… ][value=…]` candidates |
| 4 | Text | present | Partial-text truncation at 50 chars may misfire on long headings (test #2) | Make truncation configurable / send full normalised text |
| 5 | Label | partial | True `<label for=>` association not derived | Walk DOM in Page Intelligence to bind labels to inputs |
| 6 | Placeholder | present | none material | — |
| 7 | Alt text | absent | No alt-text candidate emitted; resolver lacks `get_by_alt_text` | Emit candidate; add resolver dispatch case |
| 8 | CSS | present | Generated/dynamic-class detection coarse (only via risk_flags in snapshot path) | Score-down generated classes in candidate ranker |
| 9 | LLM fallback | unwired | No sequencer enforces "after all 8 fail → emit escalation request" | Add gate at `tool_locator_find` return point feeding `build_locator_escalation_request` then LLM purpose `locator_specialist` |
| 10 | XPath | wrong order | Emitted proactively as candidate (`agent.py:9831-9846`) instead of LLM-recommended-only | Strip from `_build_locator_candidates`; only attach after LLM proposes |
| 11 | JS injection | absent | No path; no user-confirm flow | Out of scope until #9 lands |
| — | Events | unemitted | `locator_update_request`, `locator_candidates_ready`, `precondition_failed_for_locator_update` never sent | Wire emitters into `locator_update.py` and handlers in `agent.py` |

## 6. Test mapping — PRD 06 Phase 2 test #2

`PRD_v2_3_Modular_Pack_v2/06_BUILD_ROADMAP_AND_ACCEPTANCE.md:169`:
> Pick one heading → has_text assertion with `&nbsp;` → recorded → code line.

Path used: text strategy (#4). `locator/resolver.py:28-39` `normalize_assertion_text` strips `&nbsp;` and similar whitespace; `agent.py` `has_text` plumbing at lines 2948–3101 calls it. **The text normaliser works.**

What blocks the test:
1. **Partial-text truncation to 50 chars at `agent.py:9746` and 9808-9814** — long headings get truncated, causing `count == 0` on exact match if the full normalised text was needed downstream.
2. **No `getByRole("heading", name=…)` candidate when the heading carries no role attribute** — `_infer_role` (`locator/resolver.py:135-159`) returns "" for `<h1..h6>` tags. So strategy #2 (role+name) silently degrades to strategy #4 only.
3. Resolver path for `get_by_text` (`locator/resolver.py:219-220`) escapes quotes but does not normalise `&nbsp;` in the input — caller must pre-normalise. If caller forwards raw element text, locator misses.

Primary blocker: gap on strategy #2 (role inference for heading tags missing) plus the truncation behaviour on strategy #4. Either alone may pass test #2 in isolation; both together cause flakiness.

## 7. Conflict notes

Files an implementer will touch and shared-state risk against `agent.py`:

- `/Users/apple/personal/agent v4/agent.py:9731-9848` — primary `_build_locator_candidates`. Holds method-level state via `self._resolve_selected_element_info`, `self._infer_role`. Largest blast radius.
- `/Users/apple/personal/agent v4/locator/resolver.py:227-344` — `build_locator_candidates` is a near-duplicate that references `self._loop._*` but the class has no `_loop` attribute and no `__init__` wiring it. **Looks like an incomplete extraction.** Editing here without also editing `agent.py` will leave drift; binding `self._loop` is itself a refactor.
- `/Users/apple/personal/agent v4/locator.py:16-63` `find_best_locator` — older single-string selector helper still importable. Third source of truth; check call sites before deletion.
- `/Users/apple/personal/agent v4/runtime/locator_intelligence.py:188-207` `_build_locator_from_attrs` — fourth generator with its own ranking. Used by the plan-step annotation flow (`annotate_plan_steps_with_locator_kind`, line 131).
- `/Users/apple/personal/agent v4/runtime/dom_locator_contract.py:154-174` — fifth selector emitter, used during snapshot parsing.
- `/Users/apple/personal/agent v4/runtime/agent_locator_handlers.py:62-119` — `tool_locator_find` is the only iteration loop. Event-bus wiring for #9 lands here.
- `/Users/apple/personal/agent v4/runtime/locator_update.py:46-85` — needs event-emit hook (today returns dataclass result; nothing on the bus).
- `/Users/apple/personal/agent v4/runtime/event_contracts.py:1121, 2059` — emitter builders are stable; only callers need wiring.

Shared-state hazards with `agent.py`:
- `self._build_locator_candidates`, `self._resolve_locator`, `self._is_stable_locator_strategy`, `self._infer_role`, `self._tool_string_escape`, `self._css_escape`, `self._xpath_literal`, `self._normalize_space` are all instance methods proxied through `_locator_resolver` (`agent.py:9850-9890`). Touching any one is safe; renaming any means updating `locator/resolver.py` and the resolver module simultaneously.
- The duplicate `build_locator_candidates` in `locator/resolver.py:228` will raise `AttributeError` on `self._loop` if ever called. Any consolidation work must either delete it or bind `_loop`.
- There are **five** independent locator-string generators (`agent.py`, `locator/resolver.py`, `locator.py`, `runtime/locator_intelligence.py`, `runtime/dom_locator_contract.py`) — unification is a prerequisite to closing #1, #2, #3 without drift.

End of audit.
