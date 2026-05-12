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
