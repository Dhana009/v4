# BUG-S6-FINAL-002: Frontend Complete LLM UI is contract-only — no actual source implementation

**Status:** Backlog  
**Severity:** High — blocks final Complete LLM Mode acceptance claim  
**Owner:** Frontend / Cluster 10 follow-up sprint  
**Sprint:** Sprint 6 Cluster 10 gap  
**Filed:** 2026-05-13  

---

## Title

Cluster 10 marked Done but no actual `frontend/` source implementation was added; tests inspect runtime module sources, not real UI behavior

---

## Observed

- Cluster 10 (S6-1001 through S6-1012) stories were planned and contract tests were written.
- Tests in `tests/test_frontend_llm_mode_complete.py`, `tests/test_frontend_event_command_contract.py`, and related files pass.
- However, these tests verify:
  - TypedDict/dataclass schemas in runtime Python modules
  - Event contract structures
  - Command dispatcher contract data structures
  - Shadow DOM host boundary contracts
- **No actual `frontend/` directory source files were added** implementing the UI: chat panel, plan panel, steps tab, recorded tab, code tab, trace tab, recommendation review UI.
- The frontend UI is contract-only: the TypeScript/JavaScript/HTML/CSS implementation does not exist.

---

## Affected stories

- S6-1001: Shadow DOM host and product UI boundary — **contract only**
- S6-1002: Global shell (header, status, activity, footer) — **contract only**
- S6-1003: LLM tab (chat, plan, clarification, permission, recovery cards) — **contract only**
- S6-1004: Steps tab (scoped step builder and locator state) — **contract only**
- S6-1005: Recommendation review UI — **contract only**
- S6-1006: Recorded tab (immutable evidence and repair version display) — **contract only**
- S6-1007: Code tab (generated spec, warnings, export save) — **contract only**
- S6-1008: Trace tab (event timeline and diagnostics) — **contract only**
- S6-1009: Frontend typed event store completeness — **contract only**
- S6-1010: Frontend command dispatcher completeness — **contract only**
- S6-1011: Negative and edge UI states — **contract only**
- S6-1012: Cluster 10 frontend integration proof — **contract only**

---

## Expected

Actual frontend source files (`frontend/` or equivalent) implementing:
- Shadow DOM custom element host
- LLM mode chat/plan/clarification/recovery UI panels
- Steps tab UI
- Recommendation review panel
- Recorded/Code/Trace tabs
- Real TypeScript event store and command dispatcher

Tests that exercise real UI behavior (not just Python schema contracts).

---

## Source

- Frontend UI spec / Complete LLM Mode spec
- Sprint 6 Cluster 10 stories

---

## Impact

- **Complete LLM Mode cannot be claimed as fully accepted** without real frontend implementation.
- Paid browser E2E (S6-1205) cannot be validly run against a non-existent frontend.
- Final matrix (S6-1201) must mark all frontend requirements as `Partial` not `Done`.

---

## Recommendation

1. Mark all Cluster 10 frontend stories as `Partial` in the final requirement matrix (S6-1201).
2. Do not mark Complete LLM Mode as fully accepted until frontend implementation exists.
3. Schedule a dedicated frontend implementation sprint/cluster.
4. Before claiming frontend Done: add real `frontend/` source files and browser-level tests.

---

## Do not

- Do not mark Cluster 10 stories as Done without real frontend source.
- Do not claim Complete LLM Mode is fully accepted based on Python contract tests alone.
- Do not hide this gap in the handoff document.
