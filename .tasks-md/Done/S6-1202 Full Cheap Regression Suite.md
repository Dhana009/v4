# S6-1202: Full Cheap Regression Suite

## Objective

Run complete cheap/local regression suite to verify no regressions from Sprint 5.

## Acceptance Criteria

- [ ] All cheap/local tests pass or failures explicitly classified
- [ ] Backend event/command contracts pass
- [ ] LLM purpose registry tests pass
- [ ] Context/tool/schema/token policy tests pass
- [ ] Page Intelligence cheap tests pass
- [ ] Journey/steps planning cheap tests pass
- [ ] Recovery tests pass
- [ ] Replay/save/load/versioning tests pass
- [ ] Frontend event/command store tests pass
- [ ] Trace/artifacts/redaction tests pass
- [ ] No paid LLM used
- [ ] No paid browser E2E used
- [ ] No hidden xfail/skip to pass

## Constraints

- No paid LLM calls
- No paid browser E2E
- All failures must be understood and classified
- xfail tests must have dated reason

## Notes

This is the gate story. Cheap regression must be green before paid E2E.


---

## Implementation evidence

- **Validation command:** `python -m pytest -q`
- **Result:** 1689 passed, 1 skipped, 12 pre-existing failures (tracked in BUG-S6-FINAL-001)
- **12 failures:** Pre-existing model-class contract mismatch (cheap vs gpt-4o-mini); NOT new regressions
- **Local fixture E2E:** `python -m pytest tests/e2e/ -q` → 6 passed
- **Sprint 5 regression:** No S5 tests broken
- **Status:** Suite runs; 12 known failures tracked; not hiding them; bug ticket filed

