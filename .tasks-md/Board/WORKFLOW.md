# Board Workflow

## Folder meanings

| Folder | Meaning |
|---|---|
| Backlog | Full remaining product roadmap and non-active planning/reference inventory. Completed work must not stay here. |
| Planning | Active sprint stories only. If it is not selected for the active sprint, it must not be here. |
| In Progress | Work currently being changed. A story enters here only when implementation/test work starts. |
| Testing | Code implemented, verification pending. |
| Done | Verified complete with tests/evidence and sprint tag. |
| Blocked | Story cannot proceed due to explicit blocker. |
| Bugs/Open | Active bug, not fixed yet. |
| Bugs/Blocked | Bug is real but cannot proceed due to blocker. |
| Bugs/Done | Fixed and verified bug with root cause, tests, and commit evidence. |

## Required story metadata

Every story must include:

```text
Status:
Sprint:
Type:
Owner:
Priority:
Source docs:
Problem / Goal:
Scope:
Out of scope:
Required tests:
Acceptance criteria:
Evidence:
```

## Required bug metadata

Every bug must include:

```text
Status:
Sprint:
Type: Bug
Severity:
Owner:
Source / Contract violated:
Expected:
Actual:
Evidence:
Required tests:
Fix plan:
Acceptance criteria:
Root cause:
Fix summary:
Verification:
Commit:
```

## Movement rules

```text
Backlog -> Planning: selected for active sprint.
Planning -> In Progress: implementation/test work starts.
In Progress -> Testing: implementation done, verification pending.
Testing -> Done: verification passed and evidence added.
Any state -> Blocked: explicit blocker recorded.
Bugs/Open -> Bugs/Done: root cause, fix, tests, and verification recorded.
```

## Done rule

A story is Done only when:

```text
1. source rule is identified,
2. implementation is complete for that story scope,
3. positive and required negative tests exist,
4. verification commands are recorded,
5. no boundary rule is violated,
6. sprint tag is present.
```
