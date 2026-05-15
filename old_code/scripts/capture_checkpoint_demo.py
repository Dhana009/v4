#!/usr/bin/env python3
"""
capture_checkpoint_demo.py — Playwright screenshot harness for
Complete LLM Mode UI checkpoint demo.

Boots a headless Chromium at 1440x900, loads AutoWorkbench.html,
injects canonical window.AW.lastEvent payloads for each of the
17 LLM card states + 4 secondary tabs, then screenshots the full
workbench panel.

Output: docs/superpowers/specs/2026-05-15-checkpoint-demo/<state>.png
        docs/superpowers/specs/2026-05-15-checkpoint-demo/README.md

Usage:
    python scripts/capture_checkpoint_demo.py
"""

import json
import os
import sys
import time
from pathlib import Path

# ---------------------------------------------------------------------------
# Resolve paths
# ---------------------------------------------------------------------------
REPO_ROOT = Path(__file__).resolve().parent.parent
HTML_FILE = REPO_ROOT / "AutoWorkbench.html"
OUT_DIR   = REPO_ROOT / "docs" / "superpowers" / "specs" / "2026-05-15-checkpoint-demo"

if not HTML_FILE.exists():
    print(f"ERROR: AutoWorkbench.html not found at {HTML_FILE}", file=sys.stderr)
    sys.exit(1)

OUT_DIR.mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------------------------------
# Canonical lastEvent payloads keyed by state name
# ---------------------------------------------------------------------------
# Each entry:
#   type       – AW event type string (used to set window.AW.lastEvent.type)
#   payload    – event payload (merged into lastEvent)
#   aw_set     – dict dispatched via window.dispatchEvent(new CustomEvent('aw:set', {detail: ...}))
# ---------------------------------------------------------------------------

LLM_STATES = [
    # 1 ─ idle
    {
        "name": "idle",
        "label": "Idle / empty state",
        "purpose": "No session active. Shows the empty-state prompt with suggestion chips.",
        "aw_set": {"state": "idle", "tab": "llm"},
        "last_event": None,
    },
    # 2 ─ planning
    {
        "name": "planning",
        "label": "Planning — page analysis in progress",
        "purpose": "Backend is scanning the page. Shows the LLM reasoning bubble.",
        "aw_set": {"state": "planning", "tab": "llm"},
        "last_event": {
            "type": "dom_query",
            "payload": {"sections": 18, "url": "acme.dev/pricing"},
        },
    },
    # 3 ─ clarify
    {
        "name": "clarify",
        "label": "Clarification needed",
        "purpose": "Backend emitted clarification_needed. CardClarification shows depth options.",
        "aw_set": {"state": "clarify", "tab": "llm"},
        "last_event": {
            "type": "clarification_needed",
            "payload": {
                "question": "Should I recommend smoke, sanity, or exhaustive regression checks for this pricing page?",
                "options": ["Smoke (~30s)", "Sanity (~2min)", "Exhaustive regression (~10min)"],
            },
        },
    },
    # 4 ─ recommend
    {
        "name": "recommend",
        "label": "Recommendation review",
        "purpose": "Backend emitted recommendation_ready. CardRecommendation shows assertion checklist.",
        "aw_set": {"state": "recommend", "tab": "llm"},
        "last_event": {
            "type": "recommendation_ready",
            "payload": {
                "rationale": "Based on DOM analysis I found a hero, a 3-card pricing grid, a 4-row FAQ, and a footer.",
                "options": [
                    {"id": "rec_1", "title": "Hero heading visible and contains 'plans that scale'", "scope": "section.hero"},
                    {"id": "rec_2", "title": "Three pricing cards rendered (Starter, Pro, Enterprise)", "scope": "section.pricing"},
                    {"id": "rec_3", "title": "Pro plan shows 'Most popular' tag", "scope": "section.pricing > .featured"},
                    {"id": "rec_4", "title": "All CTA buttons are enabled and have href", "scope": "section.pricing a.cta"},
                    {"id": "rec_5", "title": "FAQ accordion expands when first row clicked", "scope": "section.faq .row[0]"},
                    {"id": "rec_6", "title": "Footer status link navigates to status.acme.dev", "scope": "footer a[href*='status']"},
                ],
            },
        },
    },
    # 5 ─ plan
    {
        "name": "plan",
        "label": "Plan ready — confirm to run",
        "purpose": "Backend emitted plan_ready. CardPlanReady shows 6 steps awaiting confirmation.",
        "aw_set": {"state": "plan", "tab": "llm"},
        "last_event": {
            "type": "plan_ready",
            "payload": {
                "run_id": "run_a91b",
                "summary": "sanity check on /pricing",
                "steps": [
                    {"step_id": "stp_a1f3", "title": "Verify hero heading", "scope": "section.hero"},
                    {"step_id": "stp_b2c9", "title": "Three pricing cards present", "scope": "section.pricing"},
                    {"step_id": "stp_c4d7", "title": "Pro card marked 'Most popular'", "scope": ".ws-plan.featured"},
                    {"step_id": "stp_d8e2", "title": "All CTA buttons enabled", "scope": "section.pricing a.cta"},
                    {"step_id": "stp_e1f4", "title": "Pro price equals '$49 / mo'", "scope": ".ws-plan.featured .ws-plan-price"},
                    {"step_id": "stp_f7a3", "title": "Footer status link points at status.acme.dev"},
                ],
            },
        },
    },
    # 6 ─ diff
    {
        "name": "diff",
        "label": "Plan revision proposed",
        "purpose": "LLM proposed a plan diff. CardPlanDiff shows +1/-1 changes awaiting acceptance.",
        "aw_set": {"state": "diff", "tab": "llm"},
        "last_event": {
            "type": "plan_diff_proposed",
            "payload": {"version": "v2", "added": 1, "removed": 1},
        },
    },
    # 7 ─ permit
    {
        "name": "permit",
        "label": "Permission required — medium-risk action",
        "purpose": "Backend emitted permission_required. CardPermission shows allow/deny for a CTA click.",
        "aw_set": {"state": "permit", "tab": "llm"},
        "last_event": {
            "type": "permission_required",
            "payload": {
                "action": "page.click(\"a.btn.primary[Get started]\")",
                "risk": "navigation",
                "scope": "stp_d8e2",
                "rationale": "Verifying enabled state requires actuating the button. The CTA may navigate to /signup.",
            },
        },
    },
    # 8 ─ exec
    {
        "name": "exec",
        "label": "Executing plan — step 3 of 6",
        "purpose": "Backend emitted step_executing. CardExecution shows live progress with pause/stop.",
        "aw_set": {"state": "exec", "tab": "llm"},
        "last_event": {
            "type": "step_executing",
            "payload": {
                "step_id": "stp_c4d7",
                "action": "Pro card marked 'Most popular'",
                "locator": ".ws-plan.featured",
                "current_index": 3,
                "total": 6,
            },
        },
    },
    # 9 ─ locator
    {
        "name": "locator",
        "label": "Locator ambiguity — 3 candidates",
        "purpose": "Backend emitted locator_candidates_ready. CardLocatorAmbiguity shows candidate picker.",
        "aw_set": {"state": "locator", "tab": "llm"},
        "last_event": {
            "type": "locator_candidates_ready",
            "payload": {
                "ambiguity_id": "amb_001",
                "current_locator": "getByText('Get started')",
                "candidates": [
                    {"id": "header", "title": "Header CTA — 'Get started'", "scope": "nav.ws-topnav .cta", "confidence": 0.92, "risk": "safe-read",
                     "preview": "getByRole('link', { name: 'Get started' }).first()", "diag": "role=link · accessible name unique"},
                    {"id": "hero",   "title": "Hero CTA — 'Get started'",   "scope": ".ws-hero a.btn.primary",     "confidence": 0.71, "risk": "medium",
                     "preview": "page.locator('.ws-hero a.btn.primary')", "diag": "class-based · 1 match in scope"},
                    {"id": "starter","title": "Starter plan CTA — 'Get started'", "scope": ".ws-plan:nth(1) .ws-plan-cta", "confidence": 0.34, "risk": "medium",
                     "preview": "page.getByText('Get started').nth(2)", "diag": "positional nth() · fragile"},
                ],
            },
        },
    },
    # 10 ─ recover
    {
        "name": "recover",
        "label": "Recovery needed — assertion mismatch",
        "purpose": "Backend emitted recovery_needed_structured. CardRecovery shows failure details + repair.",
        "aw_set": {"state": "recover", "tab": "llm"},
        "last_event": {
            "type": "recovery_needed_structured",
            "payload": {
                "failure_class": "assertion_mismatch",
                "suggestion": "Relax to toContainText('$49') — the space before /mo is inconsistent.",
                "failed_step": {"step_id": "stp_e1f4", "title": "Pro price equals '$49 / mo'"},
            },
        },
    },
    # 11 ─ done
    {
        "name": "done",
        "label": "Run completed — 6/6 recorded",
        "purpose": "Backend emitted run_completed. CardCompleted shows summary with replay/save actions.",
        "aw_set": {"state": "done", "tab": "llm"},
        "last_event": {
            "type": "run_completed",
            "payload": {
                "run_id": "run_a91b",
                "steps_completed": 6,
                "duration": "31.2s",
                "status": "completed",
            },
        },
    },
    # 12 ─ offline
    {
        "name": "offline",
        "label": "Backend disconnected — WebSocket closed",
        "purpose": "Transport lost. CardOffline shows reconnect options and held-state notice.",
        "aw_set": {"state": "offline", "tab": "llm"},
        "last_event": {
            "type": "ws_disconnected",
            "payload": {"attempt": 2, "max": 5},
        },
    },
    # 13 ─ schema
    {
        "name": "schema",
        "label": "Schema validation failed",
        "purpose": "LLM returned invalid plan JSON. CardSchemaError shows field path + repair button.",
        "aw_set": {"state": "schema", "tab": "llm"},
        "last_event": {
            "type": "schema_error",
            "payload": {
                "purpose": "plan_generation",
                "error": "$.steps[2].operations[0].kind — unknown: 'check-presence'",
                "raw": '{"steps": [{"operations": [{"kind": "check-presence"}]}]}',
            },
        },
    },
    # 14 ─ nobrowser
    {
        "name": "nobrowser",
        "label": "No browser session attached",
        "purpose": "Backend up but no Playwright context. CardNoBrowser shows launch options.",
        "aw_set": {"state": "nobrowser", "tab": "llm"},
        "last_event": {
            "type": "no_browser",
            "payload": {"reason": "No active Playwright context. Plan is ready but cannot be executed."},
        },
    },
    # 15 ─ apikey
    {
        "name": "apikey",
        "label": "LLM provider key missing",
        "purpose": "No API key in workspace. CardApiKey shows add-key and workspace-key options.",
        "aw_set": {"state": "apikey", "tab": "llm"},
        "last_event": {
            "type": "api_key_required",
            "payload": {
                "provider": "anthropic",
                "message": "ANTHROPIC_API_KEY not set — planning and repair are paused.",
            },
        },
    },
    # 16 ─ otp
    {
        "name": "otp",
        "label": "Human input required — OTP / 2FA",
        "purpose": "Step hit a 2FA prompt. CardOtp shows 6-digit code input with skip option.",
        "aw_set": {"state": "otp", "tab": "llm"},
        "last_event": {
            "type": "human_input_required",
            "payload": {"reason": "OTP prompt at acme.dev/auth/otp", "step_id": "stp_d8e2"},
        },
    },
    # 17 ─ e2e
    {
        "name": "e2e",
        "label": "Acceptance pending — paid E2E not yet run",
        "purpose": "Local run succeeded. CardCompleted + CardE2EPending shows nightly E2E gate.",
        "aw_set": {"state": "e2e", "tab": "llm"},
        "last_event": {
            "type": "run_completed",
            "payload": {
                "run_id": "run_a91b",
                "steps_completed": 6,
                "duration": "31.2s",
                "status": "completed",
            },
        },
    },
]

SECONDARY_TABS = [
    {
        "name": "tab_steps",
        "label": "Steps tab",
        "purpose": "Steps tab with 5 pending steps showing locator status and intent.",
        "aw_set": {"tab": "steps", "state": "plan"},
        "last_event": None,
    },
    {
        "name": "tab_recorded",
        "label": "Recorded tab",
        "purpose": "Recorded tab with 4 parent steps and child operations/evidence.",
        "aw_set": {"tab": "recorded", "state": "done"},
        "last_event": {
            "type": "session_state",
            "payload": {
                "recorded_steps": [
                    {"step_id": "stp_a1f3", "title": "Verify hero heading", "status": "passed"},
                    {"step_id": "stp_b2c9", "title": "Three pricing cards present", "status": "passed"},
                    {"step_id": "stp_c4d7", "title": "Pro card 'Most popular'", "status": "passed"},
                    {"step_id": "stp_d8e2", "title": "All CTA buttons enabled", "status": "repaired"},
                ],
            },
        },
    },
    {
        "name": "tab_code",
        "label": "Code tab",
        "purpose": "Code tab showing generated Playwright spec with copy/export actions.",
        "aw_set": {"tab": "code", "state": "done"},
        "last_event": {
            "type": "code_update",
            "payload": {
                "file": "tests/pricing.spec.ts",
                "lines_added": 47,
                "preview": (
                    "import { test, expect } from '@playwright/test';\n\n"
                    "test('pricing page sanity', async ({ page }) => {\n"
                    "  await page.goto('https://acme.dev/pricing');\n"
                    "  await expect(page.getByRole('heading', { level: 1 }))\n"
                    "    .toContainText('plans that scale');\n"
                    "  const cards = page.locator('.ws-plan');\n"
                    "  await expect(cards).toHaveCount(3);\n"
                    "  await expect(page.locator('.ws-plan.featured')).toContainText('Most popular');\n"
                    "});\n"
                ),
            },
        },
    },
    {
        "name": "tab_trace",
        "label": "Trace tab",
        "purpose": "Trace tab with event timeline, LLM calls, locator decisions and failure details.",
        "aw_set": {"tab": "trace", "state": "done"},
        "last_event": {
            "type": "trace_event",
            "payload": {
                "events": [
                    {"t": "11:42:01", "kind": "dom_query",          "msg": "18 sections discovered on /pricing"},
                    {"t": "11:42:03", "kind": "llm_call",           "msg": "journey_classifier → sanity"},
                    {"t": "11:43:12", "kind": "plan_ready",         "msg": "plan_ready · 6 steps · run_a91b"},
                    {"t": "11:44:08", "kind": "step_executing",     "msg": "stp_a1f3 hero heading · passed 412ms"},
                    {"t": "11:44:10", "kind": "step_executing",     "msg": "stp_b2c9 pricing cards · passed 138ms"},
                    {"t": "11:44:13", "kind": "locator_ambiguity",  "msg": "stp_d8e2 3 matches for 'Get started'"},
                    {"t": "11:45:02", "kind": "recovery_needed",    "msg": "stp_e1f4 assertion_mismatch '$49 /mo'"},
                    {"t": "11:46:18", "kind": "run_completed",      "msg": "run_completed · 6/6 · 31.2s"},
                ],
            },
        },
    },
]


# ---------------------------------------------------------------------------
# JS helper injected into page before capturing each state
# ---------------------------------------------------------------------------

SETUP_AW_JS = """
(function(eventType, payload, awSet) {
  // 1. Ensure window.AW exists with a minimal on/send/reconnect API
  if (!window.AW) {
    var _handlers = {};
    window.AW = {
      lastEvent: null,
      connection: 'connected',
      send: function(cmd) { return true; },
      reconnect: function() {},
      on: function(type, fn) {
        if (!_handlers[type]) _handlers[type] = [];
        _handlers[type].push(fn);
        return function() {
          _handlers[type] = (_handlers[type] || []).filter(function(h) { return h !== fn; });
        };
      },
      _emit: function(type, env) {
        var hs = _handlers[type] || [];
        for (var i = 0; i < hs.length; i++) { try { hs[i](env); } catch(e) {} }
        var hs2 = _handlers['*'] || [];
        for (var i = 0; i < hs2.length; i++) { try { hs2[i](env); } catch(e) {} }
      }
    };
  }

  // 2. Set lastEvent if provided
  if (eventType) {
    var env = { type: eventType, payload: payload || {} };
    Object.assign(env, payload || {});
    window.AW.lastEvent = env;
  }

  // 3. Dispatch aw:set to flip the tweaks/state
  if (awSet) {
    window.dispatchEvent(new CustomEvent('aw:set', { detail: awSet }));
  }

  // 4. If there was a live event, emit it so card useEffect hooks pick it up
  if (eventType && window.AW._emit) {
    var env2 = { type: eventType, payload: payload || {} };
    Object.assign(env2, payload || {});
    window.AW._emit(eventType, env2);
  }
})(%s, %s, %s);
"""


def build_js(entry):
    last = entry.get("last_event")
    if last:
        evt_type = json.dumps(last["type"])
        evt_payload = json.dumps(last.get("payload", {}))
    else:
        evt_type = "null"
        evt_payload = "null"
    aw_set = json.dumps(entry["aw_set"])
    return SETUP_AW_JS % (evt_type, evt_payload, aw_set)


# ---------------------------------------------------------------------------
# Capture
# ---------------------------------------------------------------------------

def capture_all():
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("playwright not installed. Run: pip install playwright && playwright install chromium")
        sys.exit(1)

    url = HTML_FILE.as_uri()
    all_states = LLM_STATES + SECONDARY_TABS

    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        context = browser.new_context(
            viewport={"width": 1440, "height": 900},
            device_scale_factor=1,
        )
        page = context.new_page()

        # ── Initial load ──────────────────────────────────────────────────
        print(f"Loading {url} …")
        page.goto(url, wait_until="networkidle", timeout=60_000)

        # Wait for AutoWorkbench React app to mount. The bundler swaps the
        # document root, so we wait for the .aw-panel sentinel.
        try:
            page.wait_for_selector(".aw-panel, #aw-root, .aw-chrome", timeout=20_000)
        except Exception:
            # Fallback: just give it more time to render
            page.wait_for_timeout(5_000)

        # Extra settle time for fonts/styles
        page.wait_for_timeout(1_500)

        captured = []
        failed = []

        for entry in all_states:
            name = entry["name"]
            out_path = OUT_DIR / f"{name}.png"
            print(f"  [{name}] injecting state … ", end="", flush=True)

            try:
                js = build_js(entry)
                page.evaluate(js)
                # Let React re-render
                page.wait_for_timeout(800)

                # Screenshot the full page (captures whatever is visible at 1440×900)
                page.screenshot(path=str(out_path), full_page=False, type="png")

                size = out_path.stat().st_size
                print(f"OK  ({size // 1024} KB)  → {out_path.name}")
                captured.append({"name": name, "path": out_path, "size": size, "entry": entry})
            except Exception as exc:
                print(f"FAILED: {exc}")
                failed.append(name)

        browser.close()

    return captured, failed


# ---------------------------------------------------------------------------
# README generator
# ---------------------------------------------------------------------------

README_HEADER = """\
# Checkpoint Demo — Complete LLM Mode UI

**Date:** 2026-05-15
**Branch:** `s7/clusters-6-11-complete-llm-mode`
**Captured via:** `scripts/capture_checkpoint_demo.py` (Playwright + Chromium headless 1440×900)
**Source surface:** `AutoWorkbench.html` (canonical mock / smoke harness)

---

## Purpose

Manual-test checkpoint screenshots demonstrating every reachable UI state of
the Complete LLM Mode panel.  Each PNG was captured with a canonical
`window.AW.lastEvent` payload injected into the live React app so the card
renders its live-binding branch, not just the static mock fallback.

---

## Screenshot grid

### LLM tab — 17 card states

| # | State | Screenshot | What it demonstrates |
|---|-------|------------|----------------------|
"""

README_FOOTER = """
---

## Checklist

- [ ] All 17 LLM card states render without blank areas or JS errors
- [ ] Live-binding branch activates (card header shows "live" badge) for: clarify, recommend, plan, permit, exec, locator, recover, done, offline, schema, nobrowser, apikey
- [ ] Composer is visible and usable in every LLM state
- [ ] Steps tab shows step cards with locator status badges
- [ ] Recorded tab shows parent steps with child operations
- [ ] Code tab shows generated spec with copy/export actions
- [ ] Trace tab shows event timeline with filter controls
- [ ] No `console.error` or unhandled React warnings in any state
- [ ] Screenshots are 1440×900, panel occupies right third of viewport

---

_Generated by `scripts/capture_checkpoint_demo.py` — do not edit by hand._
"""


def write_readme(captured):
    llm_rows = []
    tab_rows = []

    for i, c in enumerate(captured):
        entry = c["entry"]
        name  = entry["name"]
        label = entry["label"]
        purpose = entry["purpose"]
        img   = f"![](./{name}.png)"

        if name.startswith("tab_"):
            tab_rows.append((name, label, img, purpose))
        else:
            llm_rows.append((i + 1, name, label, img, purpose))

    lines = [README_HEADER]

    for (idx, name, label, img, purpose) in llm_rows:
        lines.append(f"| {idx} | `{name}` | {img} | {purpose} |")

    lines.append("")
    lines.append("### Secondary tabs — 4 tabs")
    lines.append("")
    lines.append("| # | Tab | Screenshot | What it demonstrates |")
    lines.append("|---|-----|------------|----------------------|")

    for i, (name, label, img, purpose) in enumerate(tab_rows, 1):
        lines.append(f"| {i} | `{name}` | {img} | {purpose} |")

    lines.append(README_FOOTER)

    readme_path = OUT_DIR / "README.md"
    readme_path.write_text("\n".join(lines), encoding="utf-8")
    return readme_path


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print(f"\nAutoWorkbench LLM Mode — Checkpoint Demo Capture")
    print(f"  Output dir : {OUT_DIR}")
    print(f"  States     : {len(LLM_STATES)} LLM card states + {len(SECONDARY_TABS)} secondary tabs")
    print()

    captured, failed = capture_all()

    # Write README
    readme_path = write_readme(captured)

    total_bytes = sum(c["size"] for c in captured)
    png_count   = len(captured)

    print()
    print("─" * 60)
    print(f"  PNGs captured : {png_count}")
    print(f"  Total bytes   : {total_bytes:,}  ({total_bytes // 1024 // 1024} MB approx)")
    print(f"  README        : {readme_path}")
    if failed:
        print(f"  FAILED states : {', '.join(failed)}")
    print("─" * 60)

    if png_count < 21:
        print(f"\nWARNING: expected ≥21 PNGs, got {png_count}", file=sys.stderr)
        sys.exit(1)

    print("\nDone.")
