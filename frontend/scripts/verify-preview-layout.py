#!/usr/bin/env python
"""FE-VISUAL-QA-001 — Real-browser layout verification for dist/preview.html.

Drives every TweaksPanel control (dock, panelWidth, collapsed, tab) and
captures DOM metrics + screenshots so we can diff what actually renders
against the ROOT reference. All artifacts go to frontend/.tmp/visual-qa/
which is git-ignored.

Usage: python scripts/verify-preview-layout.py
Exit:  0 = all scenarios pass, 1 = any failure.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from playwright.sync_api import sync_playwright

FRONTEND = Path(__file__).resolve().parent.parent
PREVIEW = "file://" + str(FRONTEND / "dist" / "preview.html")
OUT = FRONTEND / ".tmp" / "visual-qa"
OUT.mkdir(parents=True, exist_ok=True)

VIEWPORT = {"width": 1480, "height": 900}


def _set_input(page, testid, value):
    page.evaluate(
        """({id, v}) => {
          const el = document.querySelector(`[data-testid="${id}"]`);
          if (!el) return;
          const proto = el.tagName === 'SELECT' ? HTMLSelectElement : HTMLInputElement;
          const setter = Object.getOwnPropertyDescriptor(proto.prototype, 'value').set;
          setter.call(el, String(v));
          el.dispatchEvent(new Event('input', { bubbles: true }));
          el.dispatchEvent(new Event('change', { bubbles: true }));
        }""",
        {"id": testid, "v": value},
    )
    page.wait_for_timeout(160)


def click(page, testid):
    page.evaluate(
        """(id) => { const el = document.querySelector(`[data-testid="${id}"]`); if (el) el.click(); }""",
        testid,
    )
    page.wait_for_timeout(160)


def click_shadow(page, host_sel, inner_sel):
    page.evaluate(
        """({h, i}) => {
          const cell = document.querySelector(h);
          const sr = cell && cell.shadowRoot;
          const el = sr && sr.querySelector(i);
          if (el) el.click();
        }""",
        {"h": host_sel, "i": inner_sel},
    )
    page.wait_for_timeout(160)


def activate_tweaks(page):
    page.evaluate("() => window.postMessage({ type: '__activate_edit_mode' }, '*')")
    page.wait_for_timeout(120)


def probe(page):
    return page.evaluate(
        """() => {
          const stage = document.querySelector('[data-testid="aw-preview-stage"]');
          const website = document.querySelector('[data-testid="aw-website-region"]');
          const cell = document.querySelector('[data-testid="aw-panel-cell"]');
          const sr = cell && cell.shadowRoot;
          const header = sr && sr.querySelector('[data-testid="aw-header"]');
          const tabs = sr && sr.querySelector('[data-testid="aw-tabs"]');
          const body = sr && sr.querySelector('[data-testid="aw-panel-body"]');
          const composer = sr && sr.querySelector('textarea');
          const footer = sr && sr.querySelector('[data-testid="aw-footer"]');
          const panel = sr && sr.querySelector('[data-testid="aw-panel"]');
          const rail = sr && sr.querySelector('[data-testid="aw-collapsed-rail"]');
          const bb = (el) => {
            if (!el) return null;
            const r = el.getBoundingClientRect();
            return { x: Math.round(r.left), y: Math.round(r.top), w: Math.round(r.width), h: Math.round(r.height) };
          };
          const comp = (el, props) => {
            if (!el) return null;
            const c = getComputedStyle(el);
            const out = {};
            for (const p of props) out[p] = c[p];
            return out;
          };
          return {
            stage: bb(stage),
            stage_class: stage && stage.className,
            website: bb(website),
            cell: bb(cell),
            panel: bb(panel),
            panel_class: panel && panel.className,
            header: bb(header),
            tabs: bb(tabs),
            body: bb(body),
            body_style: comp(body, ['overflowX', 'overflowY', 'minWidth']),
            composer: bb(composer),
            footer: bb(footer),
            rail_present: !!rail,
            rail: bb(rail),
            panel_data_collapsed: panel && panel.getAttribute('data-collapsed'),
          };
        }"""
    )


def shoot(page, name):
    path = OUT / f"{name}.png"
    page.screenshot(path=str(path))
    return str(path)


def OK(label, info=""):
    return {"label": label, "ok": True, "info": info}


def FAIL(label, msg):
    return {"label": label, "ok": False, "msg": msg}


def scenario_a(page):
    p = probe(page)
    shoot(page, "A-dock-right-normal")
    fails = []
    if not p["stage"] or p["stage"]["x"] != 0 or p["stage"]["y"] != 0:
        fails.append("stage not at 0,0")
    if not p["cell"] or p["cell"]["y"] != 0:
        fails.append(f"cell top != 0 (got {p['cell']['y'] if p['cell'] else None})")
    if not p["cell"] or abs(p["cell"]["x"] + p["cell"]["w"] - VIEWPORT["width"]) > 1:
        fails.append("cell not flush right")
    for k in ("header", "body", "footer", "composer"):
        if not p[k]:
            fails.append(f"{k} missing")
    return FAIL("A: dock-right normal", "; ".join(fails)) if fails else OK("A: dock-right normal")


def scenario_b(page, widths):
    activate_tweaks(page)
    results = []
    for w in widths:
        _set_input(page, "aw-tweaks-panelWidth", w)
        p = probe(page)
        shoot(page, f"B-narrow-{w}")
        fails = []
        if not p["cell"] or abs(p["cell"]["w"] - w) > 2:
            fails.append(f"cell width {p['cell']['w'] if p['cell'] else None}!={w}")
        # "Clipped" only counts if the children are LOST — i.e. the scroll
        # container around them has overflow:hidden so they can never be
        # reached. If overflow-x:auto and scrollWidth > clientWidth, the
        # header is scrollable and children remain reachable.
        clipped = page.evaluate(
            """() => {
              const sr = document.querySelector('[data-testid="aw-panel-cell"]').shadowRoot;
              const header = sr.querySelector('[data-testid="aw-header"]');
              if (!header) return [];
              // Find the scroll container — either the header itself or
              // any aw-header-main descendant.
              const main = sr.querySelector('.aw-header-main') || header;
              const cs = getComputedStyle(main);
              const scrollable = (cs.overflowX === 'auto' || cs.overflowX === 'scroll')
                                 && main.scrollWidth > main.clientWidth + 1;
              if (scrollable) return [];
              const hr = main.getBoundingClientRect();
              return Array.from(header.querySelectorAll('[data-testid]'))
                .filter((el) => {
                  const r = el.getBoundingClientRect();
                  return r.right > hr.right + 2 || r.left < hr.left - 2;
                })
                .map((el) => el.getAttribute('data-testid'));
            }"""
        )
        if clipped:
            fails.append("header clipped & not scrollable: " + ",".join(clipped))
        if not p["composer"]:
            fails.append("composer lost")
        if not p["footer"]:
            fails.append("footer lost")
        results.append(FAIL(f"B: narrow {w}px", "; ".join(fails)) if fails else OK(f"B: narrow {w}px"))
    return results


def scenario_c(page):
    activate_tweaks(page)
    _set_input(page, "aw-tweaks-panelWidth", 600)
    click(page, "aw-tweaks-collapsed")
    page.wait_for_timeout(200)
    p = probe(page)
    shoot(page, "C-collapsed")
    fails = []
    if not p["cell"]:
        fails.append("cell missing")
    elif p["cell"]["w"] > 80:
        fails.append(f"collapsed cell width {p['cell']['w']} not rail-sized (<=80)")
    if not p["rail_present"]:
        fails.append("no aw-collapsed-rail rendered")
    if p["body"] and p["body"]["h"] > 0 and p["body"]["w"] > 0:
        fails.append("body still visible when collapsed")
    click(page, "aw-tweaks-collapsed")
    page.wait_for_timeout(160)
    p2 = probe(page)
    shoot(page, "C-expanded-after")
    if not p2["cell"] or p2["cell"]["w"] < 200:
        fails.append("expand did not restore width")
    return FAIL("C: collapse/rail", "; ".join(fails)) if fails else OK("C: collapse/rail")


def scenario_d(page):
    activate_tweaks(page)
    _set_input(page, "aw-tweaks-panelWidth", 500)
    results = []
    for dock in ("left", "top", "float", "right"):
        click(page, f"aw-tweaks-dock-{dock}")
        page.wait_for_timeout(200)
        p = probe(page)
        shoot(page, f"D-dock-{dock}")
        fails = []
        if not p["stage_class"] or f"aw-stage--dock-{dock}" not in p["stage_class"]:
            fails.append("dock class missing")
        if not p["cell"]:
            fails.append("cell missing")
        if not p["header"]:
            fails.append("header missing")
        if dock == "left" and p["cell"] and p["cell"]["x"] != 0:
            fails.append(f"dock-left: cell.x {p['cell']['x']}!=0")
        elif dock == "right" and p["cell"] and abs(p["cell"]["x"] + p["cell"]["w"] - VIEWPORT["width"]) > 1:
            fails.append(f"dock-right: cell.right!={VIEWPORT['width']}")
        elif dock == "top" and p["cell"] and p["cell"]["y"] != 0:
            fails.append(f"dock-top: cell.y {p['cell']['y']}!=0")
        elif dock == "float" and p["cell"] and p["cell"]["x"] == 0 and p["cell"]["y"] == 0:
            fails.append("dock-float: at 0,0 (should float)")
        results.append(FAIL(f"D: dock-{dock}", "; ".join(fails)) if fails else OK(f"D: dock-{dock}"))
    return results


def scenario_e(page):
    activate_tweaks(page)
    click(page, "aw-tweaks-dock-right")
    _set_input(page, "aw-tweaks-panelWidth", 600)
    p0 = probe(page)
    if p0["cell"] and p0["cell"]["w"] < 200:
        click(page, "aw-tweaks-collapsed")
    results = []
    for t in ("llm", "steps", "rec", "code", "trace"):
        click_shadow(page, '[data-testid="aw-panel-cell"]', f'[data-testid="aw-tab-{t}"]')
        page.wait_for_timeout(180)
        p = probe(page)
        shoot(page, f"E-tab-{t}")
        fails = []
        if not p["body"] or p["body"]["h"] < 50:
            fails.append(f"body short ({p['body']['h'] if p['body'] else None})")
        if not p["footer"]:
            fails.append("footer missing")
        overflows = page.evaluate(
            """() => {
              const cell = document.querySelector('[data-testid="aw-panel-cell"]');
              const sr = cell.shadowRoot;
              const body = sr.querySelector('[data-testid="aw-panel-body"]');
              if (!body || !cell) return false;
              const cr = cell.getBoundingClientRect();
              return Array.from(body.children).some((c) => {
                const r = c.getBoundingClientRect();
                return r.right > cr.right + 2 || r.left < cr.left - 2;
              });
            }"""
        )
        if overflows:
            fails.append("body child overflows cell horizontally")
        results.append(FAIL(f"E: tab {t}", "; ".join(fails)) if fails else OK(f"E: tab {t}"))
    return results


def scenario_f(page):
    activate_tweaks(page)
    click(page, "aw-tweaks-theme-dark")
    page.wait_for_timeout(240)
    dark = page.evaluate(
        """() => {
          const sr = document.querySelector('[data-testid="aw-panel-cell"]').shadowRoot;
          const p = sr.querySelector('[data-testid="aw-panel"]');
          return getComputedStyle(p).backgroundColor;
        }"""
    )
    shoot(page, "F-theme-dark")
    click(page, "aw-tweaks-theme-light")
    page.wait_for_timeout(240)
    light = page.evaluate(
        """() => {
          const sr = document.querySelector('[data-testid="aw-panel-cell"]').shadowRoot;
          const p = sr.querySelector('[data-testid="aw-panel"]');
          return getComputedStyle(p).backgroundColor;
        }"""
    )
    shoot(page, "F-theme-light")
    fails = []
    if dark == light:
        fails.append(f"theme didn't change panel bg (both={dark})")
    return FAIL("F: theme", "; ".join(fails)) if fails else OK("F: theme")


def main():
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        page = browser.new_page(viewport=VIEWPORT)
        page.goto(PREVIEW)
        page.wait_for_timeout(1800)

        results = []
        results.append(scenario_a(page))
        results.extend(scenario_b(page, [460, 360, 300]))
        results.append(scenario_c(page))
        results.extend(scenario_d(page))
        results.extend(scenario_e(page))
        results.append(scenario_f(page))

        passed = sum(1 for r in results if r["ok"])
        failed = sum(1 for r in results if not r["ok"])

        report = {
            "viewport": VIEWPORT,
            "preview": PREVIEW,
            "pass": passed,
            "fail": failed,
            "results": results,
        }
        (OUT / "report.json").write_text(json.dumps(report, indent=2))

        print(f"\n[verify-preview-layout] {passed} passed / {failed} failed")
        for r in results:
            tag = "OK  " if r["ok"] else "FAIL"
            msg = "" if r["ok"] else "  — " + r["msg"]
            print(f"  {tag} {r['label']}{msg}")
        print(f"\nArtifacts: {OUT}")

        browser.close()
        sys.exit(0 if failed == 0 else 1)


if __name__ == "__main__":
    main()
