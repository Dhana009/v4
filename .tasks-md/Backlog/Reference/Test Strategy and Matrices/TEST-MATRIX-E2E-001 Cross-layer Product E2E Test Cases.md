# TEST-MATRIX-E2E-001 Cross-layer Product E2E Test Cases

**Type:** Detailed Test Matrix  
**Priority:** P0  
**Owner:** DEV-4 E2E Harness + Fixtures  
**References:** EPIC-006, EPIC-007, TEST-E2E-001  

---

## 1. E2E flow tests

| Test ID | Type | Priority | Scenario | Fixture | Steps | Expected Result | Artifacts |
|---|---|---:|---|---|---|---|---|
| E2E-P-001 | Positive | P0 | Lifecycle smoke | clean semantic | start run with mocked plan | run_started → plan_ready; UI plan visible | events, screenshots |
| E2E-P-002 | Positive | P0 | Simple click | weak/semantic | plan click, confirm | backend event + page effect + recorded click + code_update | events, recorded, code |
| E2E-P-003 | Positive | P0 | Visible assertion | docs/semantic | assert heading visible | assertion child only; toBeVisible code | events, code |
| E2E-P-004 | Positive | P0 | Exact code text assertion | docs/code | assert exact command | exact_text expected_value preserved | recorded, code |
| E2E-P-005 | Positive | P0 | Correction before confirm | weak/docs | initial plan then correction | new plan_version; old plan not executed | events, commands |
| E2E-P-006 | Positive | P0 | Clarification before planning | duplicate CTA | ambiguous prompt | clarification_needed; no plan before answer | events |
| E2E-P-007 | Positive | P0 | Locator ambiguity recovery | weak DOM | duplicate target | no execution; recovery/ask_user | events, screenshot |
| E2E-P-008 | Positive | P0 | Multi-step strict cursor | docs-style | 4-step flow | no cross-step contamination; order preserved | events, code |
| E2E-P-009 | Positive | P1 | Replay smoke | recorded archive | replay correct page | replay_result pass | replay-result |
| E2E-N-001 | Negative | P0 | Stale confirm rejected | any | send stale confirm | runtime_rejected; UI shows rejection | rejection |
| E2E-N-002 | Negative | P0 | Invalid LLM plan | any | mocked invalid planner output | no executable plan; fail closed | trace |
| E2E-N-003 | Negative | P0 | Wrong locator specialist suggestion | weak DOM | wrong section candidate | backend blocks; recovery UI | validation trace |
| E2E-N-004 | Negative | P0 | Malformed backend event | harness | emit malformed event | frontend diagnostic; no fake state | frontend log |
| E2E-N-005 | Negative | P0 | Recording failure | any | missing evidence | no code_update pretending success | diagnostics |
| E2E-E-001 | Edge | P0 | Portal dropdown | dynamic fixture | open/select dropdown | correct dynamic handling or recovery | screenshots |
| E2E-E-002 | Edge | P0 | Modal blocks target | dynamic fixture | target behind modal | recovery/correct state | events |
| E2E-E-003 | Edge | P1 | Hidden mobile/desktop duplicate | hidden fixture | click visible CTA | hidden candidate not executed | validation trace |
| E2E-E-004 | Edge | P1 | Unsupported iframe/upload | unsupported fixture | request unsupported action | capability_gap | gap payload |

---

## 2. Artifact tests

| Test ID | Type | Priority | Scenario | Expected Result |
|---|---|---:|---|---|
| E2E-ART-001 | Contract | P0 | Failed run exports required files | events/commands/logs/screenshots/summary/test-result present |
| E2E-ART-002 | Contract | P0 | Passed run exports minimum files | events/commands/summary/test-result present |
| E2E-ART-003 | Contract | P0 | Redaction report | fake secrets absent |
| E2E-ART-004 | Contract | P0 | Payload snapshots | plan_ready/recorded/code/replay payloads saved when applicable |
| E2E-ART-005 | Boundary | P1 | Missing optional artifact | manifest explains missing optional file |
