# PATCH-004 Batch 05 DOM and Locator Strategy Corrections

**Type:** Planning Patch  
**Status:** Planning  
**Priority:** P0  
**Applies To:** EPIC-004 and DOM-001 through DOM-010  
**Reason:** Codex Batch 05 review found the DOM/locator architecture boundary strong enough for repo inspection, but identified missing source evidence depth, missing four-developer coordination sections, dependency-arrow gaps, and contract details around scoping, ambiguity routing, assertion taxonomy, dynamic state, update_locator history, and fixtures.  
**Decision:** Patch Batch 05. Do not regenerate. Do not start implementation from Batch 05 until this patch is applied.  

---

## 1. Codex review result

Codex reviewed EPIC-004 and DOM-001 through DOM-010 using only Tasks.md planning files.

Result:

```text
Confidence: Medium
All DOM-001 through DOM-010 are ready for repo inspection.
No DOM story is ready for immediate implementation.
Final decision: Patch Batch 05.
```

Reason:

```text
The conceptual shape is clear and usable,
and the plan is strong at preventing LLM-owned locator truth,
but the batch needs source-evidence, dependency, coordination, and schema-detail patches before freezing.
```

---

## 2. Patch goal

Patch objectives:

1. Add explicit source evidence requirement to DOM-002 through DOM-010.
2. Add four-developer coordination blocks to every DOM story.
3. Fix DOM-003 / DOM-005 dependency wiring.
4. Mark DOM-005, DOM-007, DOM-008, and DOM-009 as core P0 work.
5. Clarify shadow root and iframe serialization expectations in DOM-001.
6. Clarify ancestor_chain typing and candidate scoring metadata in DOM-002.
7. Add ranking tie-breakers and scoring guidance in DOM-003.
8. Add ambiguity routing in DOM-004.
9. Add ancestor precedence in DOM-005.
10. Add assertion taxonomy and target/value rules in DOM-006.
11. Add dynamic-state event/evidence consumption rules in DOM-007.
12. Add specialist escalation split in DOM-008.
13. Add update_locator version/history/retry behavior in DOM-009.
14. Expand fixture coverage in DOM-010.

---

## 3. EPIC-004 dependency correction

Apply this to EPIC-004.

### Corrected direct blockers

Replace the direct blocker list with:

```text
DOM-001 Page snapshot and DOM extraction contract
DOM-002 Element identity and candidate model
DOM-003 Semantic locator ranking policy
DOM-004 Locator validation and ambiguity classification
DOM-005 Section/container scoping and ancestor candidates
DOM-006 Assertion target classification
DOM-007 Dynamic UI state detection baseline
DOM-008 Locator specialist escalation contract
DOM-009 update_locator command flow
DOM-010 Real-world DOM fixture requirements
```

### Core P0 note

Add:

```markdown
## Core P0 note

DOM-005, DOM-007, DOM-008, and DOM-009 are core P0 planning work.

Some implementation can proceed in parallel with mocks, but the contracts must be planned now because:
- DOM-005 prevents weak-DOM/nested-span target bugs.
- DOM-007 provides baseline dynamic-state evidence for modals, dropdowns, loading, toast, and wrong-page cases.
- DOM-008 defines when LLM locator specialist can be used without owning locator truth.
- DOM-009 defines the safe backend-validated update_locator command flow used by recovery and future replay repair.
```

---

## 4. Source evidence table requirement for DOM stories

Apply this to DOM-002 through DOM-010.

Each DOM story must include a source evidence table using this format:

| Source | Extracted rule | Planning interpretation | Story impact |
|---|---|---|---|
| SOURCE-001 | Deterministic evidence first; LLM suggests only; backend validates. | Locator work must not be LLM-owned. | Story must preserve backend/browser validation boundary. |
| EPIC-003 / LLM-008 | Locator specialist is advisory-only. | LLM can suggest candidates/rationale. | Story must prevent LLM final locator truth. |
| EPIC-001 / BE-006 | Backend validates execution contract. | Locator must validate before execution. | Story must output validation-compatible data. |
| PLAN-005 | Realistic fixtures required. | DOM strategy must be tested against weak/semantic pages. | Story must define fixture-backed tests. |
| Handoff | expected_outcome is metadata only. | Assertions must separate target/value/metadata. | Applies directly to DOM-006. |

Story-specific source rows should be added where relevant:
- DOM-005: picker may capture nested spans/token text instead of useful ancestor.
- DOM-006: expected_outcome is parent metadata only.
- DOM-010: real-world fixtures must not be toy-only.

---

## 5. Four-developer coordination block to add to every DOM story

Add this standard section to each DOM story, with story-specific notes.

```markdown
## Four-developer coordination

| Developer | Relationship to this story |
|---|---|
| DEV-1 Backend | Validates final locator/target before execution and stores evidence. Must reject ambiguous or invalid locator truth. |
| DEV-2 LLM/DOM | Owns DOM extraction/ranking/escalation policy. LLM may suggest candidates only. |
| DEV-3 Frontend | Displays picker/candidate/context UI but must not decide final locator truth. |
| DEV-4 E2E | Builds and runs realistic fixture scenarios that prove the contract. |

Story-specific coordination:
- DEV-1: <backend validation/evidence responsibility>
- DEV-2: <DOM/LLM policy responsibility>
- DEV-3: <UI display/input responsibility>
- DEV-4: <fixture/E2E assertion responsibility>
```

### Story-specific notes

#### DOM-001

```text
DEV-1 consumes snapshot evidence for validation; DEV-4 verifies snapshot output across fixtures.
```

#### DOM-002

```text
DEV-3 may display candidate/ancestor lists; DEV-1 validates candidate identity before execution.
```

#### DOM-003

```text
DEV-2 owns deterministic ranking policy; DEV-4 tests ranking order across duplicate/semantic fixtures.
```

#### DOM-004

```text
DEV-1 owns browser validation result; DEV-3 renders ambiguity/recovery choices; DEV-4 tests no execution on ambiguous locator.
```

#### DOM-005

```text
DEV-3 picker must show ancestor target levels; DEV-4 must test nested span, card, row, form, dialog, and code block ancestor cases.
```

#### DOM-006

```text
DEV-1 rejects invalid assertion target/value combinations; DEV-3 must not turn expected_outcome into assertion text.
```

#### DOM-007

```text
DEV-1 consumes dynamic-state evidence before execution/recovery; DEV-4 tests portal dropdowns, transient toasts, loading, and page-change cases.
```

#### DOM-008

```text
DEV-2 owns specialist escalation policy; DEV-1/browser validation remains final truth.
```

#### DOM-009

```text
DEV-3 sends update_locator command only; DEV-1 validates and versions locator history.
```

#### DOM-010

```text
DEV-4 owns fixture completeness; DEV-1/2/3 consume fixtures for contract validation.
```

---

## 6. DOM-001 shadow root and iframe serialization patch

Apply this to DOM-001.

### Shadow root extraction

P0 expectation:

| Case | P0 behavior |
|---|---|
| open shadow root | serialize accessible/interactive descendants where possible |
| closed shadow root | mark unsupported/opaque with warning |
| nested shadow root | serialize with scope path if open |
| host element | include host identity and shadow availability |
| frontend Shadow DOM overlay | exclude product overlay from target page extraction unless explicitly inspecting product UI |

### Iframe extraction

P0 expectation:

| Case | P0 behavior |
|---|---|
| same-origin iframe | mark iframe boundary; optionally extract if current repo supports safely |
| cross-origin iframe | mark unsupported/capability gap |
| iframe target requested | route to capability gap or future specialized story unless supported |
| iframe present but irrelevant | include warning/context only |

### Tests to add

```markdown
| DOM001-U-005 | Unit | open shadow root | serializes host and accessible descendants |
| DOM001-U-006 | Unit | closed shadow root | warning/opaque boundary |
| DOM001-U-007 | Unit | cross-origin iframe | unsupported/capability flag |
| DOM001-U-008 | Unit | product overlay present | overlay excluded from target page extraction |
```

---

## 7. DOM-002 ancestor_chain and scoring metadata patch

Apply this to DOM-002.

### Ancestor chain type

`ancestor_chain` entries must be typed candidate references, not raw unsorted DOM refs.

Minimum ancestor entry:

| Field | Required | Meaning |
|---|---|---|
| ancestor_candidate_id | Yes | stable ancestor candidate id |
| element_ref | Yes | backend/browser reference |
| ancestor_type | Yes | interactive_parent/card/row/form/dialog/section/code_block/landmark/page |
| role | Optional | semantic role |
| accessible_name | Optional | name |
| text_summary | Optional | compact text |
| distance_from_selected | Yes | DOM distance |
| scope_strength | Yes | low/medium/high |
| risk_flags | Optional | duplicate/hidden/too_broad |

### Candidate scoring metadata

Add:

| Field | Required | Meaning |
|---|---|---|
| score | Optional before DOM-003 | ranking score if computed |
| score_reasons | Optional | list of ranked signals |
| uniqueness_evidence | Optional | match count / scope uniqueness |
| stability_risk | Optional | low/medium/high |
| validation_needed | Yes | always true before DOM-004 |

### Tests to add

```markdown
| DOM002-U-006 | Unit | ancestor_chain typed | entries have ancestor_type and distance |
| DOM002-U-007 | Unit | scoring metadata present | score_reasons available when ranked |
| DOM002-U-008 | Unit | raw ancestor refs only | rejected or normalized |
```

---

## 8. DOM-003 dependency and ranking patch

Apply this to DOM-003.

### Dependency correction

Change dependencies to include DOM-005:

```text
Dependencies: SOURCE-001, EPIC-004, DOM-001, DOM-002, DOM-005
```

Reason:

```text
DOM-003 ranking uses section/container-scoped locators, and DOM-005 defines those ancestor/container candidates.
```

### Ranking tie-breakers

When multiple locator candidates have similar primary rank, use this order:

| Tie-breaker | Prefer |
|---|---|
| uniqueness | one visible match over many |
| semantic strength | role/name or label over raw text |
| scope precision | section/card/row-scoped over page-wide if target is scoped |
| stability | testid/stable role over generated class/id |
| actionability | visible/enabled over hidden/disabled |
| user intent alignment | candidate text/role matches requested action/assertion |
| ancestor quality | interactive/container ancestor over leaf span |
| brittleness risk | avoid XPath/dynamic CSS unless no alternative |

### Scoring guidance

P0 can use a rule-table, but every ranked candidate must include:

```text
rank
score or rank_bucket
score_reasons
risk_flags
validation_needed=true
```

### Tests to add

```markdown
| DOM003-U-006 | Unit | role/name vs raw text | role/name wins |
| DOM003-U-007 | Unit | scoped duplicate CTA | scoped card/section wins |
| DOM003-U-008 | Unit | visible/enabled vs hidden | visible/enabled wins |
| DOM003-U-009 | Unit | leaf span vs button ancestor | button ancestor wins |
```

---

## 9. DOM-004 ambiguity routing patch

Apply this to DOM-004.

### Validation thresholds

| Status | Threshold |
|---|---|
| unique | exactly one valid, visible/actionable match for operation type |
| multiple | more than one plausible visible/actionable match |
| none | zero matches |
| stale | candidate ref/locator no longer resolves after page/state change |
| hidden | match exists but not visible |
| disabled | match exists but not actionable |
| wrong_page | URL/title/precondition mismatch |
| unsupported | iframe/popup/file/permission/closed shadow or unsupported target |
| unstable | page/loading/dynamic state prevents reliable validation |

### Routing rules

| Validation status | Route |
|---|---|
| unique | allow BE-006 execution contract to continue |
| multiple | ask user selection or route DOM-008 specialist if evidence insufficient |
| none | route recovery or DOM-008 specialist depending context |
| stale | recovery/update_locator |
| hidden/disabled | recovery or wait/state handling |
| wrong_page | recovery/precondition failure |
| unsupported | capability_gap |
| unstable | wait/retry policy or recovery |

### Tests to add

```markdown
| DOM004-U-006 | Unit | multiple matches | route ask_user_or_specialist |
| DOM004-U-007 | Unit | none after prior valid | route recovery/update_locator |
| DOM004-U-008 | Unit | unsupported iframe target | capability_gap |
| DOM004-U-009 | Unit | unstable loading state | wait_or_recovery |
```

---

## 10. DOM-005 ancestor precedence patch

Apply this to DOM-005.

### Ancestor precedence

When several ancestors qualify, present candidates in this order unless operation type changes priority:

| Priority | Ancestor type | Use when |
|---:|---|---|
| 1 | interactive ancestor | clicked leaf/icon/span inside button/link/control |
| 2 | form control group | label/input/select context |
| 3 | table/list row | row-level action/assertion |
| 4 | card/list item | repeated card scoped CTA/content |
| 5 | dialog/modal | modal-contained interactions |
| 6 | code/pre/text block | exact text/code assertions |
| 7 | section/container | scoped section assertions/actions |
| 8 | page landmark | nav/main/footer-level scope |

### Operation-specific override

| Operation type | Preferred ancestor |
|---|---|
| click | interactive ancestor first |
| fill/select | form control/group |
| row/card action | row/card before page-wide CTA |
| exact text assertion | text/code/pre block before broad section |
| visible section assertion | section/container |
| modal assertion/action | dialog/modal scope |

### Tests to add

```markdown
| DOM005-U-005 | Unit | several ancestors qualify | precedence order applied |
| DOM005-U-006 | Unit | exact text in code block | code/pre preferred |
| DOM005-U-007 | Unit | click icon inside button | interactive ancestor preferred |
```

---

## 11. DOM-006 assertion taxonomy patch

Apply this to DOM-006.

### Assertion taxonomy

| Assertion family | Target required | Expected value required | Notes |
|---|---|---|---|
| visible | yes | no | target-only |
| present/attached | yes | no | target-only |
| hidden | yes | no | target-only |
| enabled/disabled | yes | no | target-only |
| checked/unchecked | yes | no | input/control target |
| has_text/contains_text | yes | yes | text source required |
| exact_text/text_equals | yes | yes | whitespace policy required |
| has_value | yes | yes | input value |
| count | yes/container | yes number | list/table/card assertions |
| url/title | page target | yes | page-level assertion |

### Expected value source rules

| Source | Allowed? | Notes |
|---|---|---|
| explicit user text | yes | preferred for text/value assertions |
| confirmed plan operation expected_value | yes | backend-validated |
| DOM observed text | only as target evidence, not expected truth unless user requested |
| expected_outcome metadata | no | never hidden target/value source |
| LLM-inferred text | no unless backend/user validates |

### Code-block mapping

For code/pre/text assertions:

```text
target = text_block/code/pre candidate
expected_value = explicit user/plan assertion value
normalization = exact/contains/regex policy must be explicit
```

### Tests to add

```markdown
| DOM006-U-006 | Unit | present assertion | target only; no expected value |
| DOM006-U-007 | Unit | exact_text from user command | expected_value set from user |
| DOM006-U-008 | Unit | expected_outcome used as value | rejected |
| DOM006-U-009 | Unit | code block exact assertion | text_block target + explicit value |
| DOM006-U-010 | Unit | URL/title assertion | page-level target |
```

---

## 12. DOM-007 dynamic-state evidence patch

Apply this to DOM-007.

### Dynamic-state evidence shape

| Field | Required | Meaning |
|---|---|---|
| state_id | Yes | dynamic state id |
| state_type | Yes | modal/dropdown/toast/loading/navigation/page_change/iframe/popup/permission |
| status | Yes | active/inactive/unknown/unsupported |
| related_element_ref | Optional | trigger or container |
| visible_text | Optional | message/options/title |
| scope | Optional | page/section/dialog |
| confidence | Yes | high/medium/low |
| evidence_ref | Optional | DOM/screenshot/log reference |
| expires_quickly | Optional | transient toast/spinner |

### Event/consumer rule

Dynamic-state evidence is not necessarily its own canonical event in P0. It may be included in:

```text
step_failed
recovery_needed
locator validation result
observed_outcome
trace evidence
```

If a new event is introduced, it must follow EPIC-002 event envelope.

### Tests to add

```markdown
| DOM007-U-006 | Unit | portal dropdown | dropdown state detected outside parent container |
| DOM007-U-007 | Unit | transient toast | expires_quickly true |
| DOM007-U-008 | Unit | navigation invalidates context | page_change evidence |
| DOM007-U-009 | Unit | permission prompt | permission/capability state |
```

---

## 13. DOM-008 escalation split patch

Apply this to DOM-008.

### Ask-user vs ask-specialist vs capability-gap split

| Situation | Route |
|---|---|
| deterministic unique candidate exists | no specialist; validate |
| multiple candidates with user-meaningful options | ask user selection |
| multiple candidates but technical ambiguity | locator specialist may rank/explain |
| no candidate but sufficient DOM context | locator specialist may suggest candidates |
| no candidate and insufficient DOM context | request more DOM/snapshot/context |
| unsupported iframe/popup/upload/permission target | capability_gap or specialized future story |
| low confidence specialist output | ask user or block; no execution |
| stale locator after prior success | recovery/update_locator |

### Tests to add

```markdown
| DOM008-U-005 | Unit | user-meaningful ambiguity | ask_user |
| DOM008-U-006 | Unit | technical ambiguity | ask_specialist |
| DOM008-U-007 | Unit | insufficient DOM | request_more_context |
| DOM008-U-008 | Unit | unsupported upload target | capability_gap |
```

---

## 14. DOM-009 update_locator history and retry patch

Apply this to DOM-009.

### Locator update behavior

Decision:

```text
update_locator appends a new validated locator version/history entry.
It does not silently overwrite old locator evidence.
```

### Locator history entry

| Field | Required | Meaning |
|---|---|---|
| locator_version_id | Yes | new locator version |
| previous_locator_ref | Yes where exists | old locator |
| new_locator_ref | Yes | accepted locator |
| run_id/step_id/operation_id | Yes | scope |
| reason | Yes | why changed |
| source | Yes | user/recovery/specialist/system |
| validation_result | Yes | DOM-004 result |
| accepted_at | Yes if accepted | timestamp |
| evidence_ref | Optional | trace/screenshot |

### Retry behavior after accepted update

| Situation | Behavior |
|---|---|
| update accepted during recovery | backend may allow retry of failed operation |
| update accepted during replay | replay may retry target if replay policy allows |
| update rejected | remain in recovery/rejected state |
| update accepted but execution fails | open new recovery with both locator histories |
| stale step/operation | reject |

### Tests to add

```markdown
| DOM009-U-004 | Unit | accepted update appends history | old locator preserved |
| DOM009-U-005 | Unit | rejected update | no history mutation except rejection trace |
| DOM009-U-006 | Unit | accepted update enables retry | recovery retry allowed |
| DOM009-U-007 | Unit | accepted but retry fails | new recovery with history |
```

---

## 15. DOM-010 fixture expansion patch

Apply this to DOM-010.

### Additional required fixture coverage

Add these fixture cases:

| Fixture case | Required scenario |
|---|---|
| shadow DOM open host | open shadow root with button/input/text |
| shadow DOM closed host | unsupported/opaque boundary |
| iframe boundary | same-origin optional, cross-origin unsupported/gap |
| popup/new tab boundary | unsupported or capability gap baseline |
| file upload / permission prompt | capability-gap path |
| navigation-invalidates-context | locator valid before navigation, stale after |
| portal dropdown | options rendered outside parent container |
| transient toast/spinner | short-lived dynamic state |
| nested icon/span button | ancestor selection |
| repeated cards/table rows | scoped locator ranking |
| code block exact assertion | text_block/code/pre target |

### Fixture metadata

Every fixture should include:

| Field | Required |
|---|---|
| fixture_id | Yes |
| fixture_path | Yes |
| purpose | Yes |
| DOM features covered | Yes |
| expected candidates | Yes |
| expected ambiguity cases | Optional |
| expected validation statuses | Yes |
| related stories | Yes |
| negative cases | Yes |

### Tests to add

```markdown
| DOM010-F-006 | Fixture | open shadow root | extraction expected |
| DOM010-F-007 | Fixture | cross-origin iframe | capability gap expected |
| DOM010-F-008 | Fixture | portal dropdown | dynamic state expected |
| DOM010-F-009 | Fixture | transient toast/spinner | dynamic state evidence |
| DOM010-F-010 | Fixture | navigation invalidates context | stale/wrong_page validation |
```

---

## 16. Batch 05 patch acceptance criteria

Batch 05 is accepted after:

- EPIC-004 direct blocker list includes DOM-001 through DOM-010.
- DOM-002 through DOM-010 include explicit source evidence tables.
- Every DOM story includes four-developer coordination.
- DOM-003 explicitly depends on DOM-005 or its dependency language is corrected.
- DOM-001 includes shadow root and iframe serialization expectations.
- DOM-002 defines typed ancestor_chain and scoring metadata.
- DOM-003 includes ranking tie-breakers and scoring output.
- DOM-004 includes validation thresholds and routing rules.
- DOM-005 includes ancestor precedence.
- DOM-006 includes assertion taxonomy and expected-value source rules.
- DOM-007 includes dynamic-state evidence shape and consumer rules.
- DOM-008 includes ask-user vs specialist vs capability-gap routing.
- DOM-009 defines locator version/history and retry behavior.
- DOM-010 includes shadow DOM, iframe/popup, capability gap, portal dropdown, transient toast/spinner, and navigation-invalidates-context fixtures.

After this patch:

```text
EPIC-004 = planning-ready.
DOM-001 through DOM-010 = ready for repo inspection.
DOM-001 through DOM-010 = not ready for immediate implementation.
```
