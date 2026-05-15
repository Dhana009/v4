# FE Visual-State Fixtures

This directory holds per-state PNG pairs used by the pixel-parity regression
harness in `tests/test_fe_pixel_parity_skeleton.py`.

## Directory Layout

```
tests/fixtures/fe_states/
  <state>/
    baseline.png    ← golden reference image (committed or generated once)
    candidate.png   ← image produced by the current build under test
```

One sub-directory per FE state (17 total): `idle`, `clarification`,
`planReady`, `permission`, `recommendation`, `execution`, `recovery`,
`locatorAmbiguity`, `schemaError`, `completed`, `noBrowser`, `apiKey`,
`offline`, `tokenReport`, `pagePicker`, `traceTab`, `recordedTab`.

## Expected Filenames

| File            | Purpose                                          |
|-----------------|--------------------------------------------------|
| `baseline.png`  | Approved golden screenshot (checked in or saved by capture script) |
| `candidate.png` | Screenshot of the build being tested (generated fresh each CI run) |

## How a Capture Script Should Land Them

1. Start the dev server (`npm run dev` or equivalent).
2. For each state, navigate to the URL / trigger the UI transition.
3. Take a full-viewport screenshot with Playwright:
   ```python
   page.screenshot(path=f"tests/fixtures/fe_states/{state}/candidate.png",
                   full_page=False)
   ```
4. On the first run (or when re-baselining), copy `candidate.png` →
   `baseline.png` and commit.

See `scripts/capture_fe_baselines.py` (TODO — not yet implemented).

## Gate Convention

The test passes when:

```
total_diff = sum of all per-channel absolute pixel deltas across the image
total_diff <= 10
```

A threshold of `10` tolerates negligible sub-pixel antialiasing noise while
catching any meaningful layout or colour regression. Set the threshold lower
(0) for strict pixel-perfect enforcement.

## TODO

- [ ] Implement `scripts/capture_fe_baselines.py` (Playwright-based capture).
- [ ] Wire capture script into CI pipeline (run before pixel-parity tests).
- [ ] Commit initial baselines for all 17 states after UI stabilises.
- [ ] Consider per-state threshold overrides for states with dynamic content.
- [ ] Add animated-state variants (e.g. `execution_mid`) when needed.
