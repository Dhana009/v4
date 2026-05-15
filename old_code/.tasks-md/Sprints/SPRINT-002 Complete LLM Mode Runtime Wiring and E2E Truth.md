# SPRINT-002 Complete LLM Mode Runtime Wiring and E2E Truth

Status: Done  
Sprint: Sprint 2  
Type: Sprint Plan  
Owner: Project  
Priority: P0  
Main commit before: b5d475d  
Main commit after: 5a43872  

## Sprint goal

Make the existing LLM/DOM architecture active in the live product path and stabilize current E2E truth.

## Sprint background

Claude Code audits found that foundation modules exist but the live product path still bypasses important architecture:

```text
LLMRuntimeController exists but agent.py still uses a monolithic main_orchestrator call path.
dom_locator_contract.py exists but agent.py does not use rank_locator_candidates / validate_locator_candidate / scope_candidates.
Current E2E truth is inconsistent across handoffs and must be verified/fixed.
```

## Selected Sprint 2 items

### Bugs

```text
Bugs/Open/BUG-E2E-001 Visible assertion and correction E2E instability.md
```

### Stories in Planning

```text
Planning/INT-LLM-001 Wire plan diff editor through LLMRuntimeController.md
Planning/INT-DOM-001 Wire deterministic locator handlers into live agent path.md
Planning/INT-MVP-001 Add Complete LLM Mode lifecycle E2E skeleton.md
```

## Sprint 2 acceptance

```text
1. Current E2E truth is verified and BUG-E2E-001 is fixed or reclassified with evidence.
2. plan_diff_editor correction path uses LLMRuntimeController.
3. locator_find / locator_validate return deterministic-ranked and classified locator evidence.
4. MVP-001 lifecycle E2E skeleton exists and documents required event order.
5. .tasks-md state remains clean and Jira-like.
```

## Out of scope for Sprint 2

```text
full agent.py rewrite
full multi-model routing
frontend tab rename / Recorded tab implementation
full trace export pipeline
permission/autonomy mode
full replay repair/versioning
broad UI redesign
```

## Sprint 2 execution report

### Task-board changes

```text
BUG-E2E-001  Bugs/In Progress -> Bugs/Done
INT-LLM-001  Planning         -> Done
INT-DOM-001  Planning         -> Done
INT-MVP-001  Planning         -> Done
```

### Commits created

```text
83e4cbf  docs: sync sprint 2 completed task status
fafec66  feat: wire deterministic locator handlers into agent path
5a43872  test: add mvp lifecycle e2e skeleton
```

### Tests added

```text
tests/test_agent_locator_handler_contract.py  5 tests covering ranked_candidates, classification/status/match_count, scope_suggestions on multiple match, and unique-match no-ambiguity
tests/e2e/test_mvp_001_lifecycle_smoke.py     6-checkpoint lifecycle smoke: overlay -> plan_ready -> confirmed -> execution_started -> step_recorded -> code_update
```

### Results

```text
Unit/contract tests   137  PASS
Frontend build        —    PASS (1.2mb)
E2E tests             5    PASS
```

### E2E truth

```text
basic_click                    PASS
exact_text_assertion           PASS
visible_assertion              PASS
correction_assert_then_click   PASS
MVP-001 lifecycle              PASS
```

### What changed

```text
agent.py: added `from runtime.dom_locator_contract import rank_locator_candidates, validate_locator_candidate, scope_candidates`; enriched _tool_locator_find with ranked_candidates + scope_suggestions; enriched _tool_locator_validate with classification, status, match_count.
```

### What remains

```text
Nothing in Sprint 2. All 4 items are Done.
Bugs opened: none.
Blockers: none.
Ready for next sprint planning: yes.
```
