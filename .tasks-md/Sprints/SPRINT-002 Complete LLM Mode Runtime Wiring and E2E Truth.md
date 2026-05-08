# SPRINT-002 Complete LLM Mode Runtime Wiring and E2E Truth

Status: Planning  
Sprint: Sprint 2  
Type: Sprint Plan  
Owner: Project  
Priority: P0  

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
