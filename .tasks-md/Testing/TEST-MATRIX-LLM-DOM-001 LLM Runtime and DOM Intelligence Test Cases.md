# TEST-MATRIX-LLM-DOM-001 LLM Runtime and DOM Intelligence Test Cases

**Type:** Detailed Test Matrix  
**Priority:** P0  
**Owner:** DEV-2 LLM Runtime + DOM/Locator, DEV-4 Fixtures/E2E  
**References:** EPIC-003, EPIC-004, TEST-LLM-DOM-001  

---

## 1. LLM Runtime Controller tests

| Test ID | Type | Priority | Scenario | Preconditions | Steps | Expected Result |
|---|---|---:|---|---|---|---|
| LLM-C-001 | Contract | P0 | Known purpose loads schema/tools | purpose=journey_planner | prepare LLM call | correct schema/tools/context |
| LLM-C-002 | Contract | P0 | Unknown purpose rejected | purpose invalid | prepare call | fail closed; no LLM call |
| LLM-C-003 | Contract | P0 | Runtime-impacting purpose has backend validator | journey_planner/correction | inspect config | validator present |
| LLM-C-004 | Contract | P0 | Minimal skills loaded | purpose-specific call | prepare context | only mandatory + needed skills |
| LLM-C-005 | Contract | P0 | Tool phase gating | planning phase | expose tools | no execution/recording/completion tools |
| LLM-N-001 | Negative | P0 | Invalid schema once retries | bad first response, valid second | run controller | retry_count=1; accepted after validation |
| LLM-N-002 | Negative | P0 | Invalid schema twice fails closed | two bad responses | run controller | no runtime mutation; fail-closed diagnostic |
| LLM-N-003 | Negative | P0 | Schema-valid but backend-invalid rejected | stale plan_id output | validate | backend_rejected |
| LLM-R-001 | Regression | P0 | LLM step_recorded rejected | model output includes step_recorded | validate | rejected/ignored |
| LLM-R-002 | Regression | P0 | LLM run_completed rejected | model output says run_completed | validate | rejected/ignored |
| LLM-B-001 | Boundary | P0 | Token budget exceeded | huge context | prepare call | compress/ask more context/fail safely |
| LLM-B-002 | Boundary | P1 | Telemetry missing token estimate | local model route | run call | telemetry has diagnostic, not crash |

---

## 2. Planner / correction / recovery tests

| Test ID | Type | Priority | Scenario | Input | Expected Result |
|---|---|---:|---|---|---|
| LLM-P-001 | Positive | P0 | Simple click | "click Get started" | click operation plan |
| LLM-P-002 | Positive | P0 | Visible assertion | "verify heading is visible" | assertion visible, not click |
| LLM-P-003 | Positive | P0 | Exact text assertion | "verify exact command..." | exact_text + expected_value |
| LLM-P-004 | Positive | P0 | Multi-step flow | 4-step instruction | ordered stable steps/operations |
| LLM-N-004 | Negative | P0 | Ambiguous target | "click the button" with duplicates | clarification_needed/ask_user |
| LLM-N-005 | Negative | P0 | Unsupported upload | upload unsupported fixture | capability_gap/ask_user, no fake support |
| LLM-R-003 | Regression | P0 | Assertion intent becomes click | assertion prompt | rejected if click generated |
| LLM-R-004 | Regression | P0 | exact_text missing expected_value | exact prompt | schema/backend rejection |
| LLM-P-005 | Positive | P0 | Correction add assertion before click | correction text | structured diff add/reorder |
| LLM-N-006 | Negative | P0 | Correction silently drops child | bad diff | rejected |
| LLM-N-007 | Negative | P0 | Correction stale plan_version | stale version | backend rejection |
| LLM-P-006 | Positive | P0 | Recovery multiple matches | locator ambiguity | ask_user with candidates |
| LLM-N-008 | Negative | P0 | Recovery says success | failed action | ignored/rejected; recovery remains |

---

## 3. DOM extraction / compression tests

| Test ID | Type | Priority | Fixture | Scenario | Expected Result |
|---|---|---:|---|---|---|
| DOM-P-001 | Positive | P0 | clean semantic | extract roles/labels | candidates have roles/names |
| DOM-P-002 | Positive | P0 | form-heavy | extract labels/placeholders/required | form candidates complete |
| DOM-P-003 | Positive | P0 | docs/code | extract code/pre block | code block candidate preserved |
| DOM-P-004 | Positive | P0 | cards/table | extract row/card ancestors | scoped candidates available |
| DOM-N-001 | Negative | P0 | weak div/span | nested span CTA | clickable ancestor exposed |
| DOM-N-002 | Negative | P0 | hidden variants | hidden duplicate CTA | visibility metadata prevents blind selection |
| DOM-N-003 | Negative | P0 | duplicate CTA | same text in sections | ambiguity/section context |
| DOM-B-001 | Boundary | P0 | huge page | 1000+ nodes | compressed under budget |
| DOM-B-002 | Boundary | P0 | summary omits target | target missing | ask_more_context or specialist route |
| DOM-E-001 | Edge | P0 | portal dropdown | option outside parent | dynamic relation captured or recovery |
| DOM-E-002 | Edge | P1 | modal | modal blocks target | dynamic state/recovery |
| DOM-E-003 | Edge | P1 | toast | transient toast | detection or typed limitation |
| DOM-E-004 | Edge | P1 | unsupported iframe | iframe target | capability_gap |
| DOM-R-001 | Regression | P0 | weak DOM | selected nested span | useful ancestor selected/candidate shown |

---

## 4. Main LLM vs locator specialist handoff tests

| Test ID | Type | Priority | Scenario | Expected Result |
|---|---|---:|---|---|
| HANDOFF-P-001 | Positive | P0 | specialist receives scoped DOM only | no unrelated full DOM/history |
| HANDOFF-P-002 | Positive | P0 | specialist returns candidate IDs/confidence | schema valid |
| HANDOFF-N-001 | Negative | P0 | specialist suggests wrong section | backend validation/ambiguity blocks execution |
| HANDOFF-N-002 | Negative | P0 | specialist low confidence | ask_user/recovery |
| HANDOFF-N-003 | Negative | P0 | main LLM trusts specialist blindly | test fails; backend validation required |
| HANDOFF-B-001 | Boundary | P1 | specialist disagreement | deterministic/backend policy decides |
