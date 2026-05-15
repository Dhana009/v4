# gstack

Use the `/browse` skill from gstack for all web browsing. Never use `mcp__claude-in-chrome__*` tools.

## Available skills

`/office-hours`, `/plan-ceo-review`, `/plan-eng-review`, `/plan-design-review`, `/design-consultation`, `/design-shotgun`, `/design-html`, `/review`, `/ship`, `/land-and-deploy`, `/canary`, `/benchmark`, `/browse`, `/connect-chrome`, `/qa`, `/qa-only`, `/design-review`, `/setup-browser-cookies`, `/setup-deploy`, `/setup-gbrain`, `/retro`, `/investigate`, `/document-release`, `/document-generate`, `/codex`, `/cso`, `/autoplan`, `/plan-devex-review`, `/devex-review`, `/careful`, `/freeze`, `/guard`, `/unfreeze`, `/gstack-upgrade`, `/learn`

# Project: AutoWorkbench Complete LLM Mode

## Branch
Active: `s7/clusters-6-11-complete-llm-mode`. Tip: `de14aee`.

## Tests
- `PYTHONPATH=. pytest tests/test_p0_acceptance.py tests/test_fe_pixel_parity_skeleton.py tests/test_e2e_ws_envelope_chain.py` — 26 pass.

## Manual test entry
```bash
export OPENAI_API_KEY=sk-...
PYTHONPATH=. python server.py
# open frontend/index.html
```

## Source-of-truth specs
- `autoworkbench_complete_llm_mode_p_0_scenarios_spec (2).md`
- `autoworkbench_complete_llm_mode_runtime_policy_spec.md`
- `autoworkbench_complete_llm_mode_frontend_ui_spec.md`
- `PRD_v2_3_Modular_Pack_v2/*.md`

## Sub-agent rules
- Opus = orchestrator only. Never as sub-agent.
- Sonnet for all sub-agent dev work.
- File-disjoint partition required to prevent agent.py race.
- agent.py (~9000 LOC) is serial-only — never 2+ agents on it simultaneously.
