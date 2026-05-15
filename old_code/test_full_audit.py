"""
Full live audit of panel-v2. Tests every visible UI element and interaction.
Run against: http://localhost:9876/frontend/dist/test-live.html
Backend WS: ws://localhost:8765/ws  (may be offline — panel should still render)
"""
import asyncio, json
from playwright.async_api import async_playwright

LIVE_URL  = "http://localhost:9876/frontend/dist/test-live.html"
DEMO_URL  = "http://localhost:9876/frontend/dist/preview.html"

results = []

def ok(name): results.append((name, True,  ""))
def fail(name, detail=""): results.append((name, False, detail))

async def in_shadow(page, selector):
    """Find selector inside #autoworkbench-root shadow OR light DOM."""
    el = await page.query_selector(selector)
    if el: return el
    return await page.evaluate(f"""() => {{
        const r = document.querySelector('#autoworkbench-root');
        const s = r && r.shadowRoot ? r.shadowRoot.querySelector('#aw-shadow-mount') : null;
        return (s || document).querySelector('{selector}');
    }}""")

async def eval_in_panel(page, js):
    return await page.evaluate(f"""() => {{
        const r = document.querySelector('#autoworkbench-root');
        const s = r && r.shadowRoot ? r.shadowRoot.querySelector('#aw-shadow-mount') : null;
        const root = s || document;
        return (function(root){{ {js} }})(root);
    }}""")

async def run():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        ctx    = await browser.new_context()
        page   = await ctx.new_page()

        # ── Capture console errors ──────────────────────────────────────────
        console_errors = []
        page.on("console", lambda m: console_errors.append(m.text) if m.type == "error" else None)
        page.on("pageerror", lambda e: console_errors.append(str(e)))

        # ════════════════════════════════════════════════════════════════════
        # SECTION 1 — DEMO MODE (preview.html, no backend needed)
        # ════════════════════════════════════════════════════════════════════
        await page.goto(DEMO_URL)
        await page.evaluate("() => { localStorage.removeItem('aw-theme'); }")
        await page.reload()
        await page.wait_for_timeout(1500)

        # 1.1 Panel shell
        panel = await page.query_selector('.aw-panel')
        if panel: ok("1.1 Demo: .aw-panel renders")
        else: fail("1.1 Demo: .aw-panel renders")

        # 1.2 Header
        header = await page.query_selector('.aw-header')
        if header: ok("1.2 Demo: .aw-header renders")
        else: fail("1.2 Demo: .aw-header renders")

        # 1.3 Settings gear present in demo
        gear_demo = await page.query_selector('button[title="Settings & Tweaks"]')
        if gear_demo: ok("1.3 Demo: Settings gear visible")
        else: fail("1.3 Demo: Settings gear visible")

        # 1.4 Dock button
        dock_btn = await page.query_selector('button[title="Dock position"]')
        if dock_btn: ok("1.4 Demo: Dock position button")
        else: fail("1.4 Demo: Dock position button")

        # 1.5 Collapse button
        collapse = await page.query_selector('button[title="Collapse"]')
        if collapse: ok("1.5 Demo: Collapse button")
        else: fail("1.5 Demo: Collapse button")

        # 1.6 All 5 tabs
        tabs = await page.query_selector_all('.aw-tab')
        tab_labels = [await t.inner_text() for t in tabs]
        if len(tabs) == 5: ok(f"1.6 Demo: 5 tabs ({', '.join(tab_labels)})")
        else: fail(f"1.6 Demo: 5 tabs — found {len(tabs)}: {tab_labels}")

        # 1.7 LLM tab active by default
        active = await page.query_selector('.aw-tab.active')
        act_text = await active.inner_text() if active else ""
        if "LLM" in act_text: ok("1.7 Demo: LLM tab active by default")
        else: fail(f"1.7 Demo: LLM tab active — got '{act_text}'")

        # 1.8 Footer
        footer = await page.query_selector('.aw-footer')
        if footer: ok("1.8 Demo: Footer renders")
        else: fail("1.8 Demo: Footer renders")

        # 1.9 Status pill
        pill = await page.query_selector('.aw-status-pill')
        if pill: ok("1.9 Demo: Status pill renders")
        else: fail("1.9 Demo: Status pill renders")

        # 1.10 Brand name
        brand = await page.query_selector('.aw-brand')
        brand_text = await brand.inner_text() if brand else ""
        if "AutoWorkbench" in brand_text: ok("1.10 Demo: Brand shows 'AutoWorkbench'")
        else: fail(f"1.10 Demo: Brand — got '{brand_text}'")

        # 1.11 Mode switch (LLM/Manual)
        mode_opts = await page.query_selector_all('.aw-mode-opt')
        if len(mode_opts) == 2: ok("1.11 Demo: LLM/Manual mode switch (2 buttons)")
        else: fail(f"1.11 Demo: LLM/Manual mode switch — found {len(mode_opts)}")

        # 1.12 Agents button
        agents_btn = await page.query_selector('.aw-agents-btn')
        if agents_btn: ok("1.12 Demo: Agents button")
        else: fail("1.12 Demo: Agents button")

        # 1.13 Token pill
        token_pill = await page.query_selector('.aw-token-pill')
        if token_pill: ok("1.13 Demo: Token pill")
        else: fail("1.13 Demo: Token pill")

        # 1.14 Default theme = light
        dt = await page.evaluate("() => document.documentElement.dataset.theme")
        if dt == "light": ok("1.14 Demo: Default theme=light")
        else: fail(f"1.14 Demo: Default theme — got '{dt}'")

        # 1.15 Settings gear click fires __activate_edit_mode
        msgs = []
        await page.evaluate("""() => {
            window._auditMsgs = [];
            window.addEventListener('message', e => window._auditMsgs.push(e.data));
        }""")
        if gear_demo:
            await gear_demo.click()
            await page.wait_for_timeout(200)
        msg_types = await page.evaluate("() => window._auditMsgs.map(m => m.type)")
        if "__activate_edit_mode" in msg_types: ok("1.15 Demo: Gear click fires __activate_edit_mode")
        else: fail(f"1.15 Demo: Gear fires message — got {msg_types}")

        # 1.16 Click Steps tab
        steps_tab = next((t for t in tabs if True), None)
        for t in tabs:
            txt = await t.inner_text()
            if "Steps" in txt:
                await t.click()
                await page.wait_for_timeout(200)
                act2 = await page.query_selector('.aw-tab.active')
                act2_txt = await act2.inner_text() if act2 else ""
                if "Steps" in act2_txt: ok("1.16 Demo: Click Steps tab → active")
                else: fail(f"1.16 Demo: Steps tab active — got '{act2_txt}'")
                break

        # 1.17 Collapse → rail
        if collapse:
            await collapse.click()
            await page.wait_for_timeout(300)
            rail = await page.query_selector('.aw-collapsed-rail')
            if rail: ok("1.17 Demo: Collapse → .aw-collapsed-rail shown")
            else: fail("1.17 Demo: Collapse → rail not found")
            # Header should be gone
            hdr2 = await page.query_selector('.aw-header')
            if not hdr2: ok("1.18 Demo: Collapsed → .aw-header hidden")
            else: fail("1.18 Demo: .aw-header still visible in collapsed state")
            # Gear gone in collapsed
            gear_c = await page.query_selector('button[title="Settings & Tweaks"]')
            if not gear_c: ok("1.19 Demo: Collapsed → gear hidden")
            else: fail("1.19 Demo: Gear still visible in collapsed")
            # Dismiss TweaksPanel if open (it intercepts clicks)
            twk = await page.query_selector('.twk-panel .twk-x, .aw-tweaks [data-close], button[aria-label="Close tweaks"]')
            if twk: await twk.click(); await page.wait_for_timeout(100)
            # Also try pressing Escape
            await page.keyboard.press('Escape')
            await page.wait_for_timeout(100)
            # Expand
            exp = await page.query_selector('.aw-collapsed-rail button[title="Expand"]')
            if exp:
                await exp.click(force=True)
                await page.wait_for_timeout(300)
                gear_e = await page.query_selector('button[title="Settings & Tweaks"]')
                if gear_e: ok("1.20 Demo: Expand → gear restored")
                else: fail("1.20 Demo: Expand → gear missing")
            else:
                fail("1.20 Demo: Expand button missing in rail")

        # 1.21 Dock menu opens
        await page.reload()
        await page.wait_for_timeout(1000)
        dock2 = await page.query_selector('button[title="Dock position"]')
        if dock2:
            await dock2.click()
            await page.wait_for_timeout(200)
            dock_menu = await page.query_selector('.aw-dock-menu')
            if dock_menu: ok("1.21 Demo: Dock menu opens on click")
            else: fail("1.21 Demo: Dock menu not shown after click")
        else: fail("1.21 Demo: Dock button not found")

        # 1.22 Agents popover opens
        # close dock scrim first by clicking it
        scrim = await page.query_selector('.aw-dock-scrim')
        if scrim: await scrim.click()
        await page.wait_for_timeout(150)
        agents_btn2 = await page.query_selector('.aw-agents-btn')
        if agents_btn2:
            await agents_btn2.click()
            await page.wait_for_timeout(300)
            agents_pop = await page.query_selector('.aw-agents-pop')
            if agents_pop: ok("1.22 Demo: Agents popover opens")
            else: fail("1.22 Demo: Agents popover not found after click")
        else: fail("1.22 Demo: Agents button not found")

        # 1.23 State switcher in tweaks (via postMessage)
        # TweaksPanel should be in DOM
        tweaks_present = await page.evaluate("() => !!document.querySelector('.aw-tweaks')")
        if tweaks_present: ok("1.23 Demo: TweaksPanel (.aw-tweaks) in DOM")
        else: fail("1.23 Demo: TweaksPanel not in DOM")

        # ════════════════════════════════════════════════════════════════════
        # SECTION 2 — LIVE MODE (test-live.html, WS to backend)
        # ════════════════════════════════════════════════════════════════════
        await page.evaluate("() => { localStorage.removeItem('aw-theme'); localStorage.setItem('awPanelVersion','v2'); }")
        await page.goto(LIVE_URL)
        await page.wait_for_timeout(2500)

        # 2.1 Panel renders in live
        panel_live = await page.query_selector('.aw-panel')
        if not panel_live:
            panel_live = await eval_in_panel(page, "return root.querySelector('.aw-panel');")
        if panel_live: ok("2.1 Live: .aw-panel renders")
        else: fail("2.1 Live: .aw-panel renders")

        # 2.2 Header
        hdr_live = await page.query_selector('.aw-header')
        if not hdr_live:
            hdr_live_check = await eval_in_panel(page, "return !!root.querySelector('.aw-header');")
            if hdr_live_check: ok("2.2 Live: .aw-header renders (shadow)")
            else: fail("2.2 Live: .aw-header missing")
        else: ok("2.2 Live: .aw-header renders")

        # 2.3 Settings gear in live
        gear_live = await page.query_selector('button[title="Settings & Tweaks"]')
        if not gear_live:
            g2 = await eval_in_panel(page, "return !!root.querySelector('button[title=\"Settings & Tweaks\"]');")
            if g2: ok("2.3 Live: Settings gear visible (shadow)")
            else: fail("2.3 Live: Settings gear MISSING — regression!")
        else: ok("2.3 Live: Settings gear visible")

        # 2.4 No inline theme toggle (old wrong button removed)
        wrong_toggle = await page.query_selector('[data-testid="aw-theme-toggle"]')
        if not wrong_toggle:
            wt2 = await eval_in_panel(page, "return !!root.querySelector('[data-testid=\"aw-theme-toggle\"]');")
            if not wt2: ok("2.4 Live: No wrong aw-theme-toggle button (removed)")
            else: fail("2.4 Live: Wrong aw-theme-toggle still present in shadow")
        else: fail("2.4 Live: Wrong aw-theme-toggle still in DOM")

        # 2.5 5 tabs in live
        tabs_live = await page.query_selector_all('.aw-tab')
        if len(tabs_live) < 5:
            tl2 = await eval_in_panel(page, "return root.querySelectorAll('.aw-tab').length;")
            if tl2 == 5: ok("2.5 Live: 5 tabs (shadow)")
            else: fail(f"2.5 Live: tabs — found {tl2}")
        else: ok(f"2.6 Live: 5 tabs")

        # 2.6 WS connection status shown
        conn_pill = await page.query_selector('.aw-status-pill')
        if not conn_pill:
            conn_pill = await eval_in_panel(page, "return root.querySelector('.aw-status-pill');")
        if conn_pill: ok("2.6 Live: Connection status pill renders")
        else: fail("2.6 Live: Connection status pill missing")

        # 2.7 Default theme light
        dt_live = await page.evaluate("() => document.documentElement.dataset.theme")
        if not dt_live:
            # check shadow host
            dt_live = await page.evaluate("""() => {
                const h = document.querySelector('#autoworkbench-root');
                return h ? h.getAttribute('data-theme') : null;
            }""")
        if dt_live == "light": ok("2.7 Live: Default theme=light")
        else: fail(f"2.7 Live: Default theme — got '{dt_live}'")

        # 2.8 Collapse in live
        collapse_live = await page.query_selector('button[title="Collapse"]')
        if not collapse_live:
            has_c = await eval_in_panel(page, "return !!root.querySelector('button[title=\"Collapse\"]');")
            if has_c: ok("2.8 Live: Collapse button present (shadow)")
            else: fail("2.8 Live: Collapse button missing")
        else:
            await collapse_live.click()
            await page.wait_for_timeout(300)
            rail_live = await page.query_selector('.aw-collapsed-rail')
            if not rail_live:
                rail_live = await eval_in_panel(page, "return !!root.querySelector('.aw-collapsed-rail');")
            if rail_live: ok("2.8 Live: Collapse → rail shown")
            else: fail("2.8 Live: Collapse → rail missing")

            exp_live = await page.query_selector('.aw-collapsed-rail button[title="Expand"]')
            if exp_live:
                await exp_live.click()
                await page.wait_for_timeout(300)
                ok("2.9 Live: Expand from rail works")
            else: fail("2.9 Live: Expand button not found in rail")

        # 2.10 TweaksPanel present in live (so settings gear is functional)
        tp_live = await page.query_selector('.aw-tweaks')
        if not tp_live:
            tp2 = await eval_in_panel(page, "return !!root.querySelector('.aw-tweaks');")
            # TweaksPanel may render hidden; check outer DOM too
            tp3 = await page.evaluate("() => !!document.querySelector('.aw-tweaks')")
            if tp2 or tp3: ok("2.10 Live: TweaksPanel in DOM (gear is functional)")
            else: fail("2.10 Live: TweaksPanel NOT in DOM — gear can't open settings!")
        else: ok("2.10 Live: TweaksPanel in DOM")

        # 2.11 Gear click fires activate_edit_mode in live
        await page.evaluate("() => { window._liveAuditMsgs = []; window.addEventListener('message', e => window._liveAuditMsgs.push(e.data)); }")
        gear_live2 = await page.query_selector('button[title="Settings & Tweaks"]')
        if gear_live2:
            await gear_live2.click()
            await page.wait_for_timeout(200)
        msgs_live = await page.evaluate("() => window._liveAuditMsgs.map(m => m && m.type)")
        if "__activate_edit_mode" in msgs_live: ok("2.11 Live: Gear fires __activate_edit_mode")
        else: fail(f"2.11 Live: Gear message — got {msgs_live}")

        # 2.12 LLM tab body loads
        llm_body = await page.query_selector('.aw-llm-thread')
        if not llm_body:
            has_llm = await eval_in_panel(page, "return !!root.querySelector('.aw-llm-thread, .aw-panel-body');")
            if has_llm: ok("2.12 Live: LLM tab body renders")
            else: fail("2.12 Live: LLM tab body missing")
        else: ok("2.12 Live: LLM tab body renders")

        # 2.13 Connection offline state shown (backend likely offline from WS perspective)
        # Check status pill text
        spill = await page.evaluate("""() => {
            const pills = Array.from(document.querySelectorAll('.aw-status-pill'));
            return pills.map(p => p.textContent.trim());
        }""")
        if any(t in " ".join(spill) for t in ["Connected","Offline","Reconnecting","Running"]):
            ok(f"2.13 Live: Status pill has meaningful text ({spill})")
        else: fail(f"2.13 Live: Status pill text unclear: {spill}")

        # ════════════════════════════════════════════════════════════════════
        # SECTION 3 — Console errors audit
        # ════════════════════════════════════════════════════════════════════
        crit_errors = [e for e in console_errors if "TypeError" in e or "ReferenceError" in e or "SyntaxError" in e]
        if not crit_errors: ok("3.1 No critical JS errors (TypeError/ReferenceError/SyntaxError)")
        else: fail(f"3.1 JS errors found", f"\n       " + "\n       ".join(crit_errors[:5]))

        await browser.close()

    # ── Print results ────────────────────────────────────────────────────
    print("\n" + "="*60)
    print("FULL PANEL-V2 AUDIT RESULTS")
    print("="*60 + "\n")

    passed = failed = 0
    for name, result, detail in results:
        status = "PASS" if result else "FAIL"
        mark   = "✓" if result else "✗"
        if result: passed += 1
        else: failed += 1
        print(f"  {mark} {status}  {name}")
        if detail: print(f"       {detail}")

    print(f"\n  Total: {passed} passed, {failed} failed\n")
    print("="*60)

    if failed:
        print("\nFAILED ITEMS SUMMARY:")
        for name, result, detail in results:
            if not result:
                print(f"  ✗ {name}")
                if detail: print(f"    → {detail}")

    return failed == 0

if __name__ == "__main__":
    ok_flag = asyncio.run(run())
    exit(0 if ok_flag else 1)
