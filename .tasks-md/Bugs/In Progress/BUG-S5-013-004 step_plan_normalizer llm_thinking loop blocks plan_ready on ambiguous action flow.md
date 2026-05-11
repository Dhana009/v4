Status: In Progress

Sprint:
- Sprint 5

Owner:
- Codex

Source/evidence:
- Controlled paid retry artifact: `test-results/autoworkbench-e2e/llm_required_ambiguous_action_flow-20260511-141048-68814/`
- Pytest failure: `TimeoutError: Timed out waiting for plan review or clarification`
- Backend logs show repeated `send_to_overlay({"message_type": "llm_thinking"})` tool calls and no `plan_ready` or clarification event before timeout.

Problem:
- The live ambiguous planning flow keeps cycling through `llm_thinking` during `step_plan_normalizer` instead of converging to a plan review/clarification outcome.
- The run stays in `PLANNING…` until the harness times out.

Observed failure:
- `failure-context.json`:
  - `stage=llm_response_seen`
  - `reason=Timed out waiting for plan review or clarification`
- `token-report.json`:
  - `call_count=22`
  - `total_estimated_input_tokens=60326`
  - `total_output_tokens=621`
  - `top_token_source=skill`
- Backend evidence:
  - multiple `send_to_overlay({"message_type": "llm_thinking"})` tool calls
  - no `plan_ready` or clarification event

Suspected root cause:
- `step_plan_normalizer` is not converging from evidence gathering into a final plan/clarification output on the ambiguous action fixture.
- The runtime now reaches the LLM and executes tools correctly, but the planner response pattern stays stuck in a thinking loop.
- This appears distinct from the earlier raw-response, model-routing, and compaction-invariant blockers.

Scope:
- Reproduce and fix the `step_plan_normalizer` convergence problem on the ambiguous action flow.
- Keep the paid path bounded to one controlled retry per validation attempt.

Out of scope:
- Paid E2E reruns during debugging.
- Live model routing changes unrelated to the convergence issue.
- Prompt-pack rewrites unless the artifact proves the prompt is the blocker.
- Frontend changes.

Required tests:
- A focused regression that reproduces the ambiguous planning `llm_thinking` loop without paid E2E.
- Controller/runtime coverage proving the live path emits `plan_ready` or clarification for valid ambiguous-action evidence.
- Preserve existing prompt, context, telemetry, and tool-chain regressions.

Acceptance criteria:
- The ambiguous planning flow no longer times out waiting for plan review or clarification.
- The live path converges to `plan_ready` or clarification.
- A cheap regression proves the failure mode without another paid run.
- S5-013 remains blocked until the next controlled retry is explicitly approved.
