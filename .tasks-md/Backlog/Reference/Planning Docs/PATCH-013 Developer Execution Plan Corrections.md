# PATCH-013 Developer Execution Plan Corrections

**Type:** Developer Execution Plan Patch  
**Status:** Planning  
**Priority:** P0  
**Applies To:** DEVELOPER-EXECUTION-PLAN-001 Four Developer Branch Checkpoint and Merge Plan  
**Reason:** Codex reviewed the developer execution plan and rated it High confidence, but required final operational tightening: mapping branches must be explicitly read-only, branch/MR dependencies must be clearer, DEV-4 allowlists must be concrete, and parallelization/blocked-area rules must be stronger.  
**Decision:** Patch DEVELOPER-EXECUTION-PLAN-001. Do not regenerate. Do not start implementation until this patch is applied.

---

## 1. Codex review result

```text
Confidence: High
Final decision: Patch DEVELOPER-EXECUTION-PLAN-001
```

Codex found the plan structurally strong, but recommended tightening:

```text
mapping branches are read-only
one active branch per slice
stale branches are not reused
DEV-4 allowlists are concrete
parallelization table is explicit
MR dependencies are direct
mapping-only MRs cannot include tests or production code
blocked-area rule is restated near branch/merge sections
```

---

## 2. Branch discipline correction

Add this to the branch discipline section.

### Mapping branch hard rule

```text
Mapping branches are read-only.
They must not create tests.
They must not modify production code.
They must not modify task files.
They must produce a mapping report only.
```

Allowed mapping output:

```text
plain report in terminal / MR description
mapping table
recommended next slice
blocked rows list
allowed/forbidden file proposal
commands discovered/proposed
```

Forbidden in mapping branches:

```text
new tests
modified tests
production code changes
fixture changes
config changes
task file changes
```

### One active branch per slice

```text
One slice may have one active mapping branch and one follow-up test branch.
Do not keep stale branches alive after their slice is merged or rejected.
After merge, create a fresh branch from main for the next slice.
```

### Stale branch rule

```text
If a branch is older than the latest merged contract/evidence change, rebase or recreate it before continuing.
If rebase changes selected matrix rows or expected contracts, stop and update the mapping report before writing tests/code.
```

---

## 3. Parallelization policy

Add this section after developer ownership.

| Stream | Can run now after this plan is accepted? | Allowed mode | Blocked mode |
|---|---:|---|---|
| DEV-1 Backend/Event | Yes | first-slice mapping → tests → narrow implementation after approval | broad runtime refactor |
| DEV-4 Test Infra/Evidence | Yes | PR-0A discovery/mapping only; PR-0B minimal infra only after approval | full trace exporter / broad fixture suite |
| DEV-2 LLM/DOM | Yes | mapping only | implementation, prompt changes, locator refactor |
| DEV-3 Frontend | Yes | mapping only | Shadow DOM implementation, UI rewrite, local lifecycle state |

### Parallelization rule

```text
DEV-2 and DEV-3 may begin mapping in parallel.
DEV-2 and DEV-3 must not begin implementation until backend/event contracts and relevant harness decisions are stable enough.
DEV-4 may do discovery in parallel, but must not implement trace/export/fixture breadth until its own approved slice.
```

### Shared contract coordination

```text
DEV-1 owns backend event/command truth.
DEV-3 consumes frontend command/event shape.
DEV-4 verifies artifacts and E2E evidence.
If DEV-1 changes an event/command contract, DEV-3 and DEV-4 must re-check affected mappings before continuing.
```

---

## 4. DEV-4 allowlist correction

Replace vague `repo config files` wording with this concrete mapping-only allowlist.

### DEV-4 mapping/discovery branch read-only allowlist

```text
.tasks-md/**
tests/**
tests/e2e/**
tests/e2e/fixtures/**
frontend/package.json
package.json if present
pytest.ini if present
pyproject.toml if present
setup.cfg if present
tox.ini if present
.coveragerc if present
.github/workflows/** if present
.gitlab-ci.yml if present
Makefile if present
scripts/** if present
```

For mapping/discovery, DEV-4 must not modify these files. Read only.

### DEV-4 later PR-0B allowed files

Only after PR-0A is reviewed and PR-0B is explicitly approved:

```text
test command scripts/config
coverage config
E2E harness artifact output
artifact directory conventions
CI config if in scope
```

PR-0B must still avoid product runtime behavior changes.

---

## 5. DEV-2 and DEV-3 mapping boundary correction

Add to DEV-2:

```text
DEV-2 mapping branch may inspect runtime/context_manager.py, runtime/model_router.py, tool registry, locator-related tests, and existing DOM/LLM test files only to map coverage.
It must not modify prompts, model routing, DOM extraction, locator ranking, browser.py, locator.py, or agent.py.
```

Add to DEV-3:

```text
DEV-3 mapping branch may inspect frontend/src/**, frontend/package.json, and E2E tests only to map frontend testability.
It must not modify frontend source, implement Shadow DOM, patch legacy overlay, or add local lifecycle state.
```

---

## 6. MR dependency clarification

Add this dependency chain.

```text
MR-0A can run in parallel with MR-1A.
MR-1B depends on MR-1A acceptance.
MR-1C depends on MR-1B tests being reviewed.
MR-2A can run after MR-0A discovery is available.
MR-2B depends on MR-2A acceptance.
MR-3A and MR-4A are mapping-only and may run in parallel after this plan is accepted.
MR-3B/DEV-2 implementation depends on backend/event contract stability and fixture/harness readiness.
MR-4B/DEV-3 implementation depends on backend/event command contract stability and frontend harness decision.
MR-5+ MVP slices depend on relevant backend/event, harness, LLM/DOM, frontend, and artifact prerequisites.
```

### Sequence override rule

```text
The first safe implementation slice remains backend/event contract.
The MR list does not authorize later implementation streams early.
Later streams may map only until their blockers are cleared.
```

---

## 7. Mapping-only MR checkpoint correction

Add this checkpoint to every mapping-only MR.

A mapping-only MR is accepted only if:

```text
no tests created
no production code changed
no task files modified
selected matrix rows listed
source rule IDs listed
existing tests identified
missing tests identified
proposed test files/functions listed
allowed/forbidden files listed
commands to run listed
blocked rows listed
recommended next branch stated
```

Stop if a mapping branch starts creating tests or implementation.

---

## 8. Future-file list clarification

Add this rule to sections that list “likely future files.”

```text
Likely future files are examples for planning only.
They are not authorization to create those files.
A future file may be created only after:
1. mapping identifies it as needed,
2. the relevant slice is approved,
3. allowed files are listed in the task,
4. tests are created before implementation.
```

---

## 9. Blocked-area rule restatement

Add this near branch/MR sections.

```text
Trace exporter, frontend Shadow DOM implementation, broad fixture suite, replay repair, session restore, and DOM/locator refactor remain blocked.
They can be mapped, but not implemented, until their own slice is approved.
```

Specific stop triggers:

```text
DEV-1 branch touches frontend/DOM/trace exporter.
DEV-2 branch changes prompts/locator implementation before mapping approval.
DEV-3 branch implements Shadow DOM before frontend harness/contract readiness.
DEV-4 branch implements broad trace/export or fixture suite before PR-0 scope approval.
Any branch modifies task files.
Any mapping branch creates tests or code.
```

---

## 10. Patch acceptance criteria

DEVELOPER-EXECUTION-PLAN-001 is accepted after:

```text
1. Mapping branches are explicitly read-only.
2. One-active-branch-per-slice and stale-branch rules are added.
3. Parallelization table is added.
4. DEV-4 allowlist is concrete.
5. DEV-2 and DEV-3 mapping boundaries are explicit.
6. MR dependencies are clear.
7. Mapping-only MR acceptance criteria are added.
8. Future-file lists are clarified as examples, not authorization.
9. Blocked-area rule is restated near branch/MR sections.
```

After this patch:

```text
DEVELOPER-EXECUTION-PLAN-001 = accepted for final new-chat handoff
Implementation still blocked until the next chat starts with the approved first mapping slice.
```
