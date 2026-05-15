"""
FE Pixel-Parity Skeleton
========================
Parametrized regression harness for the 17 FE visual states.

Each test case:
  1. Looks for  tests/fixtures/fe_states/<state>/baseline.png
  2. Looks for  tests/fixtures/fe_states/<state>/candidate.png
  3. If either is absent  →  pytest.skip (explicit reason)
  4. If PIL is not installed  →  pytest.skip
  5. Otherwise runs _diff_png and asserts total_diff <= threshold (10)

Playwright capture is NOT wired here.
See tests/fixtures/fe_states/README.md and scripts/capture_fe_baselines.py.
"""

from __future__ import annotations

import pathlib
from typing import Tuple

import pytest

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_FIXTURES_ROOT = pathlib.Path(__file__).parent / "fixtures" / "fe_states"

_FE_STATES = [
    "idle",
    "clarification",
    "planReady",
    "permission",
    "recommendation",
    "execution",
    "recovery",
    "locatorAmbiguity",
    "schemaError",
    "completed",
    "noBrowser",
    "apiKey",
    "offline",
    "tokenReport",
    "pagePicker",
    "traceTab",
    "recordedTab",
]

# Gate: summed absolute per-channel pixel delta must be <= this value.
# A value of 0 means pixel-perfect; 10 allows for negligible AA/sub-pixel noise.
_DEFAULT_THRESHOLD_SUM: int = 10


# ---------------------------------------------------------------------------
# Diff helper
# ---------------------------------------------------------------------------


def _diff_png(
    baseline_path: pathlib.Path,
    candidate_path: pathlib.Path,
    threshold_sum: int = _DEFAULT_THRESHOLD_SUM,
) -> Tuple[bool, dict]:
    """Compare two PNG files pixel-by-pixel.

    Returns
    -------
    (ok, stats)
        ok   – True when total_diff <= threshold_sum
        stats – {
            "max_per_pixel": int,   # largest single-pixel channel delta seen
            "total_diff":    int,   # sum of all per-channel absolute deltas
            "differing_pixels": int # number of pixels with any channel delta > 0
          }

    Raises pytest.skip if PIL is not available.
    """
    try:
        from PIL import Image, ImageChops  # type: ignore
    except ImportError:  # pragma: no cover
        pytest.skip("PIL not installed — pip install Pillow to enable pixel diff")

    img_base = Image.open(baseline_path).convert("RGBA")
    img_cand = Image.open(candidate_path).convert("RGBA")

    if img_base.size != img_cand.size:
        stats = {
            "max_per_pixel": -1,
            "total_diff": -1,
            "differing_pixels": -1,
        }
        return False, stats

    diff = ImageChops.difference(img_base, img_cand)
    pixels = list(diff.getdata())

    total_diff = 0
    max_per_pixel = 0
    differing_pixels = 0

    for px in pixels:
        # px is a tuple of channel values (R, G, B, A)
        px_sum = sum(px)
        if px_sum > 0:
            differing_pixels += 1
        total_diff += px_sum
        if px_sum > max_per_pixel:
            max_per_pixel = px_sum

    stats = {
        "max_per_pixel": max_per_pixel,
        "total_diff": total_diff,
        "differing_pixels": differing_pixels,
    }
    ok = total_diff <= threshold_sum
    return ok, stats


# ---------------------------------------------------------------------------
# Parametrized test
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("state", _FE_STATES)
def test_fe_pixel_parity(state: str) -> None:
    """Pixel-parity gate for FE state ``state``.

    Skips (not fails) when baseline or candidate PNG is absent so that
    ``pytest tests/test_fe_pixel_parity_skeleton.py -v`` returns 17 skips
    on a fresh checkout before the capture script has been run.
    """
    state_dir = _FIXTURES_ROOT / state
    baseline = state_dir / "baseline.png"
    candidate = state_dir / "candidate.png"

    if not baseline.exists():
        pytest.skip(
            f"baseline png missing for state '{state}' — "
            "run scripts/capture_fe_baselines.py first"
        )

    if not candidate.exists():
        pytest.skip(
            f"candidate png missing for state '{state}' — "
            "run scripts/capture_fe_baselines.py to generate candidate"
        )

    ok, stats = _diff_png(baseline, candidate, threshold_sum=_DEFAULT_THRESHOLD_SUM)

    assert ok, (
        f"Pixel-parity FAIL for state '{state}': "
        f"total_diff={stats['total_diff']} > threshold={_DEFAULT_THRESHOLD_SUM} | "
        f"max_per_pixel={stats['max_per_pixel']}, "
        f"differing_pixels={stats['differing_pixels']}"
    )
