"""
Live browser test: panel-v2 theme toggle and header controls.
Verifies the FE-PANELV2-007B fix works end-to-end in a real browser.
"""
import asyncio
from playwright.async_api import async_playwright

APP_URL = "http://localhost:9876/frontend/dist/test-live.html"

async def run():
    results = []

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        ctx = await browser.new_context()
        page = await ctx.new_page()

        # ── Load live test page (mounts v2 live panel) ──────────────────
        # Pre-set localStorage before first load so init reads clean state
        await page.goto(APP_URL)
        await page.evaluate("() => { localStorage.removeItem('aw-theme'); }")
        await page.reload()
        await page.wait_for_timeout(2000)  # let React mount + WS attempt

        # ── 1: Panel renders ─────────────────────────────────────────────
        panel = await page.query_selector(".aw-panel")
        ok = panel is not None
        results.append(("1. .aw-panel renders", ok))

        # ── 2: Default theme is light ────────────────────────────────────
        dt = await page.evaluate("() => document.documentElement.dataset.theme")
        # Also check shadow host if panel is in shadow
        shadow_dt = await page.evaluate("""() => {
            const h = document.querySelector('#autoworkbench-root');
            if (!h) return null;
            const sr = h.shadowRoot;
            if (!sr) return null;
            const host = sr.host;
            return host ? host.getAttribute('data-theme') : null;
        }""")
        effective = shadow_dt if shadow_dt else dt
        results.append(("2. Default theme is light", effective == "light"))

        # ── 3: Theme toggle button visible ───────────────────────────────
        # Panel-v2 may be inside a shadow DOM; try both
        toggle = await page.query_selector('[data-testid="aw-theme-toggle"]')
        if not toggle:
            # Try inside shadow root
            toggle_in_shadow = await page.evaluate("""() => {
                const root = document.querySelector('#autoworkbench-root');
                if (!root || !root.shadowRoot) return false;
                const mount = root.shadowRoot.querySelector('#aw-shadow-mount');
                if (!mount) return false;
                return !!mount.querySelector('[data-testid="aw-theme-toggle"]');
            }""")
            results.append(("3. Theme toggle button visible", toggle_in_shadow))
        else:
            results.append(("3. Theme toggle button visible", True))

        # ── 4: Click toggle → dark ───────────────────────────────────────
        clicked = await page.evaluate("""() => {
            // Try light DOM first, then shadow DOM
            let btn = document.querySelector('[data-testid="aw-theme-toggle"]');
            if (!btn) {
                const root = document.querySelector('#autoworkbench-root');
                if (root && root.shadowRoot) {
                    const mount = root.shadowRoot.querySelector('#aw-shadow-mount');
                    if (mount) btn = mount.querySelector('[data-testid="aw-theme-toggle"]');
                }
            }
            if (!btn) return false;
            btn.click();
            return true;
        }""")
        await page.wait_for_timeout(300)
        dt_after = await page.evaluate("() => document.documentElement.dataset.theme")
        shadow_dt_after = await page.evaluate("""() => {
            const h = document.querySelector('#autoworkbench-root');
            if (!h || !h.shadowRoot) return null;
            return h.shadowRoot.host.getAttribute('data-theme');
        }""")
        effective_after = shadow_dt_after if shadow_dt_after else dt_after
        results.append(("4. Click toggle → theme becomes dark", effective_after == "dark"))

        # ── 5: localStorage persists dark ────────────────────────────────
        stored = await page.evaluate("() => localStorage.getItem('aw-theme')")
        results.append(("5. localStorage aw-theme=dark after toggle", stored == "dark"))

        # ── 6: Reload → stays dark ───────────────────────────────────────
        await page.reload()
        await page.wait_for_timeout(1500)
        dt_reload = await page.evaluate("() => document.documentElement.dataset.theme")
        shadow_dt_reload = await page.evaluate("""() => {
            const h = document.querySelector('#autoworkbench-root');
            if (!h || !h.shadowRoot) return null;
            return h.shadowRoot.host.getAttribute('data-theme');
        }""")
        effective_reload = shadow_dt_reload if shadow_dt_reload else dt_reload
        results.append(("6. Reload → still dark (persisted)", effective_reload == "dark"))

        # ── 7: Click toggle again → light ────────────────────────────────
        await page.evaluate("""() => {
            let btn = document.querySelector('[data-testid="aw-theme-toggle"]');
            if (!btn) {
                const root = document.querySelector('#autoworkbench-root');
                if (root && root.shadowRoot) {
                    const mount = root.shadowRoot.querySelector('#aw-shadow-mount');
                    if (mount) btn = mount.querySelector('[data-testid="aw-theme-toggle"]');
                }
            }
            if (btn) btn.click();
        }""")
        await page.wait_for_timeout(300)
        dt_light = await page.evaluate("() => document.documentElement.dataset.theme")
        shadow_dt_light = await page.evaluate("""() => {
            const h = document.querySelector('#autoworkbench-root');
            if (!h || !h.shadowRoot) return null;
            return h.shadowRoot.host.getAttribute('data-theme');
        }""")
        effective_light = shadow_dt_light if shadow_dt_light else dt_light
        results.append(("7. Click toggle again → back to light", effective_light == "light"))
        stored_light = await page.evaluate("() => localStorage.getItem('aw-theme')")
        results.append(("8. localStorage aw-theme=light after second toggle", stored_light == "light"))

        # ── 9: Collapse → header hides ───────────────────────────────────
        collapse_clicked = await page.evaluate("""() => {
            let btn = document.querySelector('button[title="Collapse"]');
            if (!btn) {
                const root = document.querySelector('#autoworkbench-root');
                if (root && root.shadowRoot) {
                    const mount = root.shadowRoot.querySelector('#aw-shadow-mount');
                    if (mount) btn = mount.querySelector('button[title="Collapse"]');
                }
            }
            if (!btn) return false;
            btn.click();
            return true;
        }""")
        await page.wait_for_timeout(300)
        rail_visible = await page.evaluate("""() => {
            let rail = document.querySelector('.aw-collapsed-rail');
            if (!rail) {
                const root = document.querySelector('#autoworkbench-root');
                if (root && root.shadowRoot) {
                    const mount = root.shadowRoot.querySelector('#aw-shadow-mount');
                    if (mount) rail = mount.querySelector('.aw-collapsed-rail');
                }
            }
            return !!rail;
        }""")
        toggle_in_rail = await page.evaluate("""() => {
            const root = document.querySelector('#autoworkbench-root');
            const searchIn = (root && root.shadowRoot)
                ? root.shadowRoot.querySelector('#aw-shadow-mount')
                : document;
            if (!searchIn) return false;
            return !!searchIn.querySelector('[data-testid="aw-theme-toggle"]');
        }""")
        results.append(("9. Collapse → rail shows", rail_visible))
        results.append(("10. Collapsed rail → theme toggle gone (header hidden)", not toggle_in_rail))

        # ── 11: Expand → header + toggle restore ─────────────────────────
        await page.evaluate("""() => {
            let btn = document.querySelector('.aw-collapsed-rail button[title="Expand"]');
            if (!btn) {
                const root = document.querySelector('#autoworkbench-root');
                if (root && root.shadowRoot) {
                    const mount = root.shadowRoot.querySelector('#aw-shadow-mount');
                    if (mount) btn = mount.querySelector('.aw-collapsed-rail button[title="Expand"]');
                }
            }
            if (btn) btn.click();
        }""")
        await page.wait_for_timeout(300)
        toggle_after_expand = await page.evaluate("""() => {
            const root = document.querySelector('#autoworkbench-root');
            const searchIn = (root && root.shadowRoot)
                ? root.shadowRoot.querySelector('#aw-shadow-mount')
                : document;
            if (!searchIn) return false;
            return !!searchIn.querySelector('[data-testid="aw-theme-toggle"]');
        }""")
        results.append(("11. Expand → theme toggle restored", toggle_after_expand))

        # ── 12: Dump DOM context for debug ───────────────────────────────
        dom_info = await page.evaluate("""() => {
            const root = document.querySelector('#autoworkbench-root');
            return {
                has_root: !!root,
                has_shadow: root ? !!root.shadowRoot : false,
                shadow_mount: root && root.shadowRoot ? !!root.shadowRoot.querySelector('#aw-shadow-mount') : false,
                light_dom_panel: !!document.querySelector('.aw-panel'),
                panel_v2_flag: localStorage.getItem('awPanelVersion'),
                aw_theme: localStorage.getItem('aw-theme'),
            };
        }""")

        await browser.close()

    # ── Print results ─────────────────────────────────────────────────
    passed = 0
    failed = 0
    print("\n=== PANEL-V2 LIVE THEME TEST RESULTS ===\n")
    for name, result in results:
        status = "PASS" if result else "FAIL"
        mark = "✓" if result else "✗"
        if result:
            passed += 1
        else:
            failed += 1
        print(f"  {mark} {status}  {name}")

    print(f"\n  DOM context: {dom_info}")
    print(f"\n  Total: {passed} passed, {failed} failed\n")
    return failed == 0

if __name__ == "__main__":
    ok = asyncio.run(run())
    exit(0 if ok else 1)
