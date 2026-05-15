# S7-0904 — Artifact Links and Redaction Status

**Sprint:** Sprint 7
**Cluster:** 9
**Tier:** 2 (supporting)
**Type:** Feature
**Status:** Done
**Blocks:** []
**Blocked by:** [S7-0901]

---

## Objective

Render artifact references and redaction status in Trace or Failure Detail. Show artifact bundle links, summary/failure-context paths, screenshots if available, llm-calls/token-report references. Display redaction status. Unavailable artifacts show clear state. No secret values displayed raw.

After S7-0904:
- Artifact links render from backend-provided references
- Missing artifact shows unavailable state
- Redaction status badge visible
- No secrets displayed raw
- Clicking link is safe

---

## Source Rules

- PRD-06-TRACE-004: Artifact references in trace and failure context
- PRD-06-REDACTION-001: Redaction status visibility and secret protection
- GOV-S7-C0-009: No raw secrets in frontend

---

## Tests First

### Component Tests

```python
test_artifact_link_renders()  # PRD-06-TRACE-004
test_artifact_unavailable_state()  # PRD-06-TRACE-004
test_redaction_status_visible()  # PRD-06-REDACTION-001
test_screenshot_artifact_renders()  # PRD-06-TRACE-004
test_llm_calls_artifact_renders()  # PRD-06-TRACE-004
```

### Negative Tests

```python
test_malformed_artifact_ref_safe()  # GOV-S7-C0-009
test_no_raw_secrets_in_artifact_display()  # GOV-S7-C0-009
```

---

## Implementation Boundaries

### Allowed Files

```
- frontend/src/components/trace/ArtifactLinks.jsx (new)
- frontend/src/components/trace/RedactionStatus.jsx (new)
- tests/test_frontend_artifacts.py (new)
```

### Forbidden Files

```
- agent.py
- runtime/artifact_bundle.py (read-only)
- runtime/redaction_policy.py (read-only)
- frontend_new_design_prototype/
```

---

## Stop Conditions

Stop if:

- Artifact bundle schema incomplete
- Redaction policy cannot be integrated
- Coverage below 95%


---

## Evidence Recorded

- **Commit:** 7e0ab27 — Cluster 9 trace/agents components
- **Tests:** tests/test_frontend_trace_agent_cards.py (23 tests)
- **Build:** dist/autoworkbench.js 1.3mb (clean)
- **Regression:** 2467 passed / 1 skipped / 0 failed
