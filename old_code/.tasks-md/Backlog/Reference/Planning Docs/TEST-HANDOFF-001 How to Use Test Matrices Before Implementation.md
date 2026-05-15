# TEST-HANDOFF-001 How to Use Test Matrices Before Implementation

**Type:** Test Planning Handoff  
**Status:** Planning  
**Priority:** P0  
**Applies To:** All implementation work  

---

## 1. Core rule

```text
No implementation starts until the relevant test matrix rows are mapped to repo test files.
```

Implementation task flow:

```text
1. Pick story/slice.
2. Read source story + doctrine + relevant test matrix.
3. Select applicable test rows.
4. Inspect repo for existing tests.
5. Add/modify tests first.
6. Confirm failing tests where fixing missing behavior.
7. Implement narrowly.
8. Run focused tests.
9. Run impacted integration/E2E.
10. Attach artifacts/evidence.
```

---

## 2. Test ID format

```text
BE = backend runtime
EVENT = typed event/command contract
LLM = LLM runtime/controller
DOM = DOM intelligence/locator
FE = frontend
E2E = cross-layer E2E
MVP = release/acceptance gate
```

Case type:

```text
P = positive
N = negative
B = boundary
E = edge
R = regression
C = contract/schema
I = integration
```

Example:

```text
BE-N-004 = backend negative case 004
LLM-R-002 = LLM regression case 002
```

---

## 3. Coverage expectation

For every implementation PR:

```text
- At least one positive test where behavior is added.
- At least one negative test for validation/rejection.
- Boundary/edge tests where state, DOM, or async behavior is involved.
- Regression test if touching a known failure area.
- 95% coverage for new/changed deterministic modules.
```

---

## 4. Merge blocker

Block merge if a selected test matrix row is marked P0 and no repo test exists for it.
