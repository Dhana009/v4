# PATCH-012 FINAL-HANDOFF-v2 Execution Readiness Corrections

**Type:** Final Handoff Patch  
**Status:** Planning  
**Priority:** P0  
**Applies To:** FINAL-HANDOFF-v2 Planning Testing and Execution Readiness  
**Reason:** Codex reviewed FINAL-HANDOFF-v2 and rated it Medium confidence. It is directionally strong, but several wording and operational details must be patched so workers do not misread planning/test-matrix status as implementation readiness.  
**Decision:** Patch FINAL-HANDOFF-v2. Do not regenerate. Do not start implementation until this patch is applied.

---

## 1. Codex review result

```text
Confidence: Medium
Final decision: Patch FINAL-HANDOFF-v2
```

Codex found:

```text
The document is strong, but some wording can be misread:
- "Repo test mapping completed once" sounds too final.
- "Detailed test matrices complete after PATCH-011" sounds too final.
- Branch/parallelization rules need sharper boundaries.
- PR-0 CI/coverage/artifact gate needs more concrete outputs.
- First-slice test mapping expectation must be explicit.
- Trace/frontend/fixture work must stay blocked until the selected slice and evidence path are ready.
```

---

## 2. Executive status wording correction

Replace this wording:

```text
Detailed test matrices: complete after PATCH-011
Repo test mapping: completed once
```

With:

```text
Detailed test matrices: available, but authoritative only after PATCH-011 is applied.
Repo test mapping: one mapping pass completed; full mapping remains blocked.
```

Add:

```text
Batch 13 plus PATCH-011 is a planning/test-map source, not proof that repo tests exist.
Repo test mapping identifies what exists and what is missing; it does not authorize broad implementation.
```

---

## 3. Matrix readiness wording correction

Add this to the testing inventory/status section:

```text
PATCH-011 must be treated as part of Batch 13.
Any use of Batch 13 without PATCH-011 is incomplete.
If a matrix row lacks source-rule/invariant mapping, the worker must add mapping during repo test mapping before writing tests.
```

Accepted wording:

```text
Test matrices are ready for repo test mapping after PATCH-011.
They are not proof that repo test files exist.
They are not implementation instructions by themselves.
```

---

## 4. Repo test mapping correction

Replace:

```text
A repo test mapping was completed after Batch 12/13 patches.
```

With:

```text
One repo test mapping pass was completed after Batch 12/13 patches.
That pass found the full mapping remains blocked.
Only the backend/event contract slice is currently suitable as the first safe test-first slice after this handoff is accepted.
```

Add:

```text
Do not treat the mapping pass as permission to start any work outside the selected first slice.
Every future slice requires its own matrix-to-repo mapping before tests or implementation.
```

---

## 5. First-slice mapping expectation

Add this section near “First safe test-first slice.”

### First-slice mapping requirement

Before DEV-1 writes or updates tests for the backend/event contract slice, Codex must produce a focused slice mapping table:

| Field | Required |
|---|---:|
| Selected matrix rows | Yes |
| Source rule IDs | Yes |
| Existing test files | Yes |
| Missing tests | Yes |
| Proposed test files/functions | Yes |
| Expected failing tests | Conditional |
| Files allowed | Yes |
| Files forbidden | Yes |
| Commands to run | Yes |
| Stop conditions | Yes |

Minimum selected rows for first slice:

```text
EVENT-C-001 through EVENT-C-006
EVENT-CMD-C-001 through EVENT-CMD-C-006
EVENT-SEQ-001 through EVENT-SEQ-007
EVENT-COMP rows from PATCH-011
BE-ISO / BE-RESTART / BE-SNAP / BE-LATE / BE-PROC rows from PATCH-011 only if they fit without production changes
```

If the slice starts expanding into frontend harness, trace exporter, DOM fixtures, or broad runtime refactor, stop.

---

## 6. Branch and parallelization policy

Add this section.

### Branch discipline

Suggested branches:

```text
dev4/test-infra-artifact-readiness
dev1/backend-event-contract-tests
dev1/backend-event-contract-implementation
dev2/llm-dom-test-mapping
dev3/frontend-harness-test-mapping
```

Rules:

```text
1. One branch = one small slice.
2. Test-only PRs should be allowed before implementation PRs.
3. No branch should mix backend contracts, frontend UI, DOM fixtures, and trace exporters in one PR.
4. Every branch must list selected matrix rows.
5. Every branch must list files allowed and files forbidden.
6. Every branch must stop if it touches out-of-scope layers.
```

### Parallelization boundaries

Allowed in parallel after this handoff is accepted:

| Stream | Allowed parallel work | Must not do yet |
|---|---|---|
| DEV-1 | Backend/event focused test mapping and tests | broad implementation/refactor |
| DEV-4 | Test command/coverage/artifact discovery and PR-0 planning | full trace exporter implementation before scope accepted |
| DEV-2 | LLM/DOM repo test mapping only | DOM implementation or prompt changes |
| DEV-3 | Frontend harness approach mapping only | Shadow DOM migration implementation |

Shared contract coordination required:

```text
DEV-1 and DEV-3 must coordinate event/command envelope expectations.
DEV-1 and DEV-4 must coordinate event artifacts and test harness output.
DEV-2 and DEV-4 must coordinate DOM fixture requirements before DOM tests.
DEV-3 and DEV-4 must coordinate frontend E2E hooks before UI tests.
```

---

## 7. PR-0 CI / coverage / artifact gate specificity

Replace vague PR-0 wording with this.

### PR-0 concrete outputs

PR-0 is not product implementation. It must produce a repo readiness report and, if approved, minimal test infrastructure changes.

Required PR-0 outputs:

```text
1. Canonical test command list:
   - backend unit/contract
   - integration
   - frontend if available
   - E2E
   - coverage if available

2. Coverage decision:
   - existing tool/config if present
   - proposed tool/config if absent
   - excluded/generated files policy
   - where coverage report is written

3. Artifact output plan:
   - artifact root directory
   - naming convention using test_id/run_id/artifact_bundle_id
   - minimum failed-run artifacts
   - minimum pass-run artifacts
   - manifest/hash/redaction plan

4. CI tier plan:
   - local focused command
   - PR required command
   - impacted E2E command
   - nightly/full command
```

If repo lacks coverage/CI support, PR-0 may be split:

```text
PR-0A: discovery/report only
PR-0B: minimal test command/coverage/artifact config
```

Do not mix PR-0 with product behavior changes.

---

## 8. Blocked-area stop rule

Add this to stop conditions.

```text
Stop if the first backend/event slice starts expanding into:
- trace/export/redaction harness implementation
- frontend Shadow DOM migration
- frontend dedicated harness implementation
- DOM fixture creation
- locator/picker refactor
- replay repair
- session restore
- broad agent.py refactor
```

These areas remain blocked until their own slice is mapped and approved.

---

## 9. “What not to do” addition

Add:

```text
Do not treat one repo mapping pass as permission for broad implementation.
Do not treat Batch 13 matrices as implemented tests.
Do not start frontend/trace/fixture work only because it appears in the matrix.
Do not let DEV-2/DEV-3 implement ahead of backend/event contract stabilization unless the slice is mapping-only.
```

---

## 10. Patch acceptance criteria

FINAL-HANDOFF-v2 is accepted after:

```text
1. Executive status says matrices are authoritative only after PATCH-011 is applied.
2. Repo mapping status says one mapping pass was completed but full mapping remains blocked.
3. First-slice mapping requirement is explicit.
4. Branch/parallelization policy is added.
5. PR-0 concrete outputs are defined.
6. Blocked-area stop rule is added.
7. What-not-to-do rules include no broad implementation from one mapping pass.
```

After this patch:

```text
FINAL-HANDOFF-v2 = execution-readiness handoff ready
Next step = accept handoff, then perform focused first-slice mapping for backend/event contract tests
Implementation still does not start until selected tests are written/reviewed.
```
