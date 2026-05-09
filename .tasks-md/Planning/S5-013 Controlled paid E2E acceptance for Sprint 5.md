# S5-013 Controlled paid E2E acceptance for Sprint 5

Status: Planning
Sprint: Sprint 5
Type: Story
Owner:
Priority: P0
Source docs: PRD v2.3 01_PRODUCT_WORKFLOWS.md, AGENTS.md token baseline

## Problem / Goal

**Problem:** Fake-model suite proves architecture works; real LLM behavior needs verification. Must balance token efficiency (S5 goal) with correctness (non-negotiable).

**Goal:** Run controlled paid E2E on 2–3 representative flows. Measure tokens vs baseline. Verify correctness unchanged. Gate Sprint 5 acceptance on token reduction + correctness.

## Scope

- Run E2E on: ambiguous planning flow, plan correction flow, one DOM-heavy page flow (if page intelligence implemented)
- Measure: input tokens, output tokens, call count, cost
- Compare vs Sprint 3 baseline (AGENTS.md)
- Verify: correctness (all steps pass), no quality loss
- Document: which flows tested, token results, cost

Out of scope:
- Repeated paid runs during development (only S5 acceptance)
- All 5 flows (2–3 representative flows sufficient)
- Real nano model testing (fake model sufficient for this sprint)

## Required unit tests

None (purely E2E).

## Required contract tests

- `test_e2e_token_baseline_comparison.py`:
  - Baseline tokens from AGENTS.md
  - S5 tokens are ≤110% of baseline (allow 10% variance)
  - Token reduction is measurable

## Required integration tests

- `test_e2e_ambiguous_planning.py`:
  - Ambiguous user intent → planning → correction → confirmation
  - All steps execute correctly
  - Token count recorded
- `test_e2e_plan_correction.py`:
  - Valid plan → user correction → corrected plan → confirmation
  - Correction applied correctly
  - Token count recorded
- `test_e2e_dom_heavy_page_intelligence.py` (if S5-010 done):
  - Weak DOM page → page intelligence → planning → validation
  - All steps correct
  - Token count recorded

## Fixture/page needs

- Fixture pages from S5-011
- Public test pages (e.g., playwright-docs, Airbnb signup)

## Paid E2E requirement

**Yes. This story requires real LLM calls.**

- Ambiguous planning: ~1–2 runs, ~5–10k tokens
- Correction: ~1–2 runs, ~5–10k tokens
- DOM-heavy (if done): ~1 run, ~8–12k tokens
- **Total estimate: 2–3 runs, ~15–30k tokens, cost ~$0.30–$0.60**

## Acceptance criteria

- [ ] 2–3 E2E flows run with real LLM
- [ ] Token count measured and compared vs baseline
- [ ] All flows pass without correctness loss
- [ ] Token reduction is achievable (≤110% of baseline)
- [ ] Cost estimate is reasonable (commit approved before run)
- [ ] Results documented in token_report.json
- [ ] Baseline comparison shows S5 changes are working

## Evidence

Will include:
- E2E test output (pass/fail)
- token_report.json with detailed breakdown
- Comparison table: baseline vs S5 results
- Cost receipt
- Commit message recording results

## Verification commands/results

```bash
# Before running, check approval:
echo "Running controlled E2E. Cost estimate: $0.50. Approved? (yes/no)"

# Run E2E (if approved):
pytest tests/e2e/test_e2e_ambiguous_planning.py -v --tb=short
pytest tests/e2e/test_e2e_plan_correction.py -v --tb=short
pytest tests/e2e/test_e2e_dom_heavy_page_intelligence.py -v --tb=short

# Extract token results
python scripts/compare_token_baselines.py \
  --baseline AGENTS.md \
  --current tests/e2e/artifacts/token_report.json \
  --output comparison.md

# Show cost
grep -E "estimated_cost|total_cost" tests/e2e/artifacts/token_report.json
```

## Risk

- **Medium:** Real LLM may behave differently than fake model (expected, S5 goal is to handle it)
- **Low:** Token reduction may be marginal (acceptable if correctness preserved)
- **Low:** Cost may exceed estimate (gate with pre-approval)

## Mitigation

- Pre-approval for cost before running
- Fake-model suite (S5-012) prepares for real behavior
- Token baseline (AGENTS.md) provides comparison baseline
- Acceptance criteria allow 10% variance (realistic)
