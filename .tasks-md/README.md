# AutoWorkbench `.tasks-md` Board

This folder is the Jira-style project board for AutoWorkbench / Playwright Automation Co-pilot.

## Workflow folders

```text
Backlog      = future product scope and reference planning inventory
Planning     = only active Sprint 3.5 selected stories
In Progress  = actively being edited
Testing      = implementation complete, verification pending
Done         = verified completed work
Blocked      = blocked stories/features
Bugs/Open    = active bugs
Bugs/Blocked = bugs blocked by environment/dependency
Bugs/Done    = fixed and verified bugs
```

## Current active sprint

```text
Sprint 3 is complete.
Sprint 3.5 — Backend Contract Confidence, Integration Testing, and Refactor Readiness
```

Read first:

```text
Board/WORKFLOW.md
Board/SPRINT-RULES.md
Sprints/SPRINT-003-5 Backend Contract Confidence and Refactor Readiness.md
```

## Non-negotiables

```text
No undocumented work.
No test without source mapping.
No implementation without tests.
No bug fix without a bug ticket.
No Done without verification evidence.
Backend = runtime truth.
LLM = proposal only.
Frontend = typed backend-event renderer + typed command sender.
DOM intelligence = candidate/context provider only.
Trace = evidence only.
Tests = enforcement layer.
```
