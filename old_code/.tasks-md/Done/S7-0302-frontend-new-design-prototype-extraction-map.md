# S7-0302 frontend_new_design_prototype Extraction Map

**Sprint:** Sprint 7  
**Cluster:** 3  
**Story:** S7-0302  
**Status:** Done  
**Date:** 2026-05-13  

---

## Objective

Map design prototype files to production component modules. Identify which prototype patterns are reusable, which are design-only, and which need to be rewritten for backend-event-driven architecture.

---

## Audit Scope

- **Prototype files** — llm-tab.jsx, secondary-tabs.jsx, chrome.jsx, etc.
- **Component patterns** — Reusable visual patterns
- **Demo data** — Static state that must be replaced
- **Tab structure** — LLM, Steps, Recorded, Code, Trace
- **Card types** — Clarification, Recommendation, Recovery, etc.
- **Interaction** — Buttons, inputs, menus

---

## Tests First

### Mapping Tests (no implementation; mapping document needed)

**Test: File inventory**
- List all .jsx files in `frontend_new_design_prototype/`.
- For each file, identify purpose and target production location.
- Report: file → production module mapping.

**Test: Component patterns**
- Extract visual component patterns (buttons, cards, tabs, etc.).
- Identify which are design-only vs. reusable.
- Report: pattern list with reusability assessment.

**Test: Demo vs. live data**
- Identify static data structures in prototype.
- Map to Cluster 2 event schemas.
- Report: demo data → event field mapping.

**Test: Tab structure**
- Verify prototype has LLM, Steps, Recorded, Code, Trace tabs.
- Map to production tab structure.
- Report: tab → component module mapping.

---

## Implementation Boundaries

**Mapping only; no code changes.**

---

## Acceptance Criteria

✅ **Extraction map created** with:
- Prototype file → production location mapping
- Component pattern reusability assessment
- Demo data → event schema mapping
- Tab structure and component mapping
- Identified design-only vs. reusable content

✅ **Map stored** as `.tasks-md/Planning/S7-0302-EXTRACTION-MAP.md`

---

## Evidence Checklist

- [x] File inventory complete
- [x] Component patterns identified
- [x] Demo data mapped to events
- [x] Tab structure documented
- [x] Reusability assessment provided
- [x] Extraction map created and submitted

---

## Evidence Recorded

**Implementation commit:** `6486771`  
**Extraction map:** `.tasks-md/Planning/S7-0302-EXTRACTION-MAP.md`  
**Prototype files read:** app.jsx, chrome.jsx, llm-tab.jsx, icons.jsx, styles.css  
**Tokens mapped:** 20+ CSS custom properties extracted  
**Components mapped:** 10 primitive patterns → production components  
**Exclusion list:** 8 prototype-only artifacts documented

