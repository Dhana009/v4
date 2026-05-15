# S6-0302 Deterministic page/section extraction completeness

**Sprint:** Sprint 6  
**Cluster:** 3 (Page Intelligence + Recommendation Mode)  
**Tier:** 1 (core)  
**Type:** Feature  
**Status:** Planning  
**Owner:** Page Extraction  
**Blocks:** S6-0303, S6-0304  
**Blocked by:** S6-0301  

---

## Purpose

Improve deterministic extraction so Page Intelligence starts with clean structured data. Extract URL/title, landmarks/sections, headings, CTAs/buttons/links, forms/inputs/labels/placeholders, tables/lists, modals/dialogs, duplicate/ambiguous target signals, and semantic quality score. No LLM, no raw screenshot interpretation.

---

## Source rules

- Runtime Policy Spec: Page Intelligence must start with deterministic structured extraction
- S5 DOM fixtures exist (test/fixtures/dom_heavy_pages.py)
- Extraction output must map cleanly into PageIntelligenceSchema
- Extraction must be bounded (no unlimited candidate lists)

---

## What it contains

```
- extract URL/title
- landmarks/sections
- headings
- CTAs/buttons/links
- forms/inputs/labels/placeholders
- tables/lists
- modals/dialogs/dynamic UI indicators
- duplicate/ambiguous target signals
- semantic quality score
- risk flags (hidden/masked targets, poor labeling, etc.)
```

---

## What it must NOT contain

```
- no LLM call
- no raw screenshot interpretation
- no browser-changing actions
- no frontend rendering
```

---

## Tests first

### Unit tests

```
- extracts headings/buttons/forms from semantic fixture
- extracts weak div/span candidates from weak fixture
- detects duplicate buttons/text
- detects table/list structure
- detects modal/dialog state
- computes semantic quality/risk flags
- handles missing alt text / labels
```

### Contract tests

```
- output maps cleanly into PageIntelligenceSchema
- extraction output is bounded (< N candidates per category)
- no hidden/non-visible noise dominates candidates
```

### Integration tests

```
- all DOM-heavy fixtures produce stable extraction outputs
```

Coverage: **95% for page_extraction.py**

---

## Out of scope

- Do not implement LLM-based refinement (defer to S6-0303)
- Do not change browser-changing tools
- Do not execute locators

---

## Allowed files

```
runtime/page_extraction.py (new)
tests/test_page_extraction.py (new)
```

---

## Forbidden files

- No changes to browser behavior
- No LLM integration

---

## Implementation notes

### Approach

1. Create `runtime/page_extraction.py` with:
   - `extract_page_structure(page_context)` → PageExtractionResult
   - Extract landmarks/sections (ARIA roles, semantic tags)
   - Extract headings (h1–h6)
   - Extract CTAs/buttons/links (visible, enabled, proper labels)
   - Extract forms (fieldsets, inputs, labels, placeholders)
   - Extract tables (th/td structure, row/col headers)
   - Extract modals/dialogs (overlay indicators, focus trap signals)
   - Detect duplicate text/ambiguous targets
   - Compute semantic quality score (0–100: based on labeling, ARIA, heading hierarchy)
   - Detect risk flags (hidden, masked, poor contrast, etc.)

2. Keep extraction bounded:
   - Top N items per category (e.g., top 20 buttons)
   - Deduplicate by text/role/aria-label
   - Remove hidden/non-visible elements

3. Return structured PageExtractionResult

### Key invariants

- No LLM call during extraction
- Output is deterministic (same input → same output)
- Quality score reflects semantic clarity, not content
- Risk flags are explicit (not silent filtering)

---

## Validation commands

```bash
python -m pytest tests/test_page_extraction.py::test_semantic_fixture -v
python -m pytest tests/test_page_extraction.py::test_weak_fixture -v
python -m pytest tests/test_page_extraction.py::test_bounded_output -v
coverage run -m pytest tests/test_page_extraction.py
coverage report --include=runtime/page_extraction.py
```

---

## Artifact/evidence requirement

- [ ] `runtime/page_extraction.py` created
- [ ] `tests/test_page_extraction.py` created
- [ ] All extraction types (landmarks, headings, CTAs, forms, tables, modals) working
- [ ] Semantic quality score computed correctly
- [ ] Risk flags identified
- [ ] Duplicate/ambiguous targets detected
- [ ] Output bounded (no candidate explosion)
- [ ] 95% coverage

---

## Stop conditions

- Extraction output doesn't map to PageIntelligenceSchema (adjust extraction logic)
- Semantic quality score unreliable (refine scoring logic)
- Fixtures not available (check S5 fixture location)

---

## Sign-off

- [x] Story is specific (improve deterministic extraction)
- [x] Scope is bounded (no LLM, no execution)
- [x] Tests are first
- [x] Depends on S6-0301 (detection logic)
