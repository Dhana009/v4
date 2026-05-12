# S6-1204: Real LLM Contract Probes

## Objective

Use real LLM contract probes (no browser) to validate high-risk LLM purposes before paid E2E.

## Acceptance Criteria

- [ ] Cheap regression passes (S6-1202)
- [ ] Cheap local E2E passes (S6-1203)
- [ ] Contract probe inputs are deterministic/redacted
- [ ] Artifact writer enabled for all probes
- [ ] Token budget configured
- [ ] Expected terminal behavior documented
- [ ] Real LLM outputs valid schema
- [ ] Backend validators accept or safely reject
- [ ] Token report captured

## Candidate Contract Probes

intent_classifier, page_intelligence_summarizer, page_validation_recommender, journey_planner, plan_diff_editor, locator_specialist, custom_assertion_planner, recovery_diagnoser, replay_repair_specialist, user_response_writer

## Hard Stops

- LLM claims execution success → Fail
- LLM generates secrets → Fail
- LLM modifies runtime state → Fail

## Notes

Contract probes are cheap and deterministic. Results inform whether paid E2E can proceed.
