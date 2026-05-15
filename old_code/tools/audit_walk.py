"""Live audit walk against running app. Connect via CDP, screenshot
every stage, dump panel DOM. Run after `bash scripts/launch.sh` is up
with AUTOWORKBENCH_REMOTE_DEBUGGING_PORT=9222.

Usage:
    python tools/audit_walk.py STAGE [STAGE...]

Stages:
    initial      screenshot + DOM dump of just-loaded panel
    type_intent  type "click get started" into composer / intent input
    attach       click Attach Element on first pending step
    pick         click "Get started" on fixture page (uses picker)
    outcome      click navigation outcome chip
    run          click Run Pending Steps
    confirm      click Confirm Plan
    dump         re-screenshot + re-dump only
"""
from __future__ import annotations
import asyncio, json, sys, time, pathlib
from playwright.async_api import async_playwright

OUT = pathlib.Path("/tmp/aw-audit")
OUT.mkdir(exist_ok=True)
CDP = "http://127.0.0.1:9222"

async def shadow_text(page):
    return await page.evaluate("""() => {
      const host = document.getElementById('autoworkbench-root');
      if (!host || !host.shadowRoot) return {ok:false, reason:'no shadow root'};
      const sr = host.shadowRoot;
      const tabs = [...sr.querySelectorAll('[data-testid^="aw-tab-"]')].map(b=>({
        id: b.dataset.testid, label: (b.textContent||'').trim(), active: b.classList.contains('active')
      }));
      const footer = sr.querySelector('.aw-footer');
      const header = sr.querySelector('.aw-header');
      const now = sr.querySelector('.aw-now');
      const cards = [...sr.querySelectorAll('[data-testid^="card-"], .aw-card')].map(c => ({
        testid: c.dataset?.testid || null,
        title: (c.querySelector('.aw-card-title')?.textContent||'').trim(),
        state: (c.querySelector('.aw-card-state')?.textContent||'').trim(),
        body: (c.querySelector('.aw-card-body')?.textContent||'').trim().slice(0,200),
      }));
      const pendingRows = [...sr.querySelectorAll('[data-testid^="aw-step-row-"], .ide-step, .pending-step')].length;
      return {
        ok:true,
        url: location.href,
        tabs, pendingRows,
        header_text: (header?.textContent||'').trim(),
        footer_text: (footer?.textContent||'').trim(),
        now_text: (now?.textContent||'').trim(),
        cards,
      };
    }""")

async def composer_value(page):
    return await page.evaluate("""() => {
      const host = document.getElementById('autoworkbench-root');
      const sr = host?.shadowRoot;
      const ta = sr?.querySelector('textarea, [contenteditable]');
      return ta ? (ta.value ?? ta.textContent) : null;
    }""")

async def stage_initial(page):
    await page.screenshot(path=str(OUT/"01_initial.png"), full_page=True)
    snap = await shadow_text(page)
    (OUT/"01_initial.json").write_text(json.dumps(snap, indent=2))
    print(json.dumps(snap, indent=2))

async def click_tab(page, tab):
    await page.evaluate(f"""() => {{
      const sr=document.getElementById('autoworkbench-root').shadowRoot;
      sr.querySelector('[data-testid="aw-tab-{tab}"]').click();
    }}""")
    await asyncio.sleep(0.3)

async def stage_type_intent(page):
    await click_tab(page, 'steps')
    await asyncio.sleep(0.4)
    # find first intent input in steps tab
    ok = await page.evaluate("""() => {
      const sr=document.getElementById('autoworkbench-root').shadowRoot;
      const i = sr.querySelector('.ide-step-input, textarea[placeholder*="intent" i], input[placeholder*="intent" i]');
      if (!i) return false;
      i.focus();
      const setter = Object.getOwnPropertyDescriptor(i.constructor.prototype,'value')?.set;
      setter?.call(i,'click get started');
      i.dispatchEvent(new Event('input',{bubbles:true}));
      i.dispatchEvent(new Event('change',{bubbles:true}));
      return true;
    }""")
    print(f"typed intent: {ok}")
    await page.screenshot(path=str(OUT/"02_intent.png"), full_page=True)
    (OUT/"02_intent.json").write_text(json.dumps(await shadow_text(page), indent=2))

async def stage_attach(page):
    await click_tab(page, 'steps')
    await page.evaluate("""() => {
      const sr=document.getElementById('autoworkbench-root').shadowRoot;
      const btns=[...sr.querySelectorAll('button')];
      const b=btns.find(x=>/attach element/i.test(x.textContent));
      b?.click();
    }""")
    await asyncio.sleep(0.5)
    await page.screenshot(path=str(OUT/"03_attach.png"), full_page=True)
    (OUT/"03_attach.json").write_text(json.dumps(await shadow_text(page), indent=2))

async def stage_pick(page):
    # click in light DOM (host page) — fixture "Get started"
    await page.evaluate("""() => {
      const b = document.querySelector('#get-started, [data-testid="get-started"]');
      b?.click();
    }""")
    await asyncio.sleep(0.8)
    await page.screenshot(path=str(OUT/"04_pick.png"), full_page=True)
    (OUT/"04_pick.json").write_text(json.dumps({**await shadow_text(page), "page_url": page.url}, indent=2))

async def stage_outcome(page):
    await click_tab(page, 'steps')
    await page.evaluate("""() => {
      const sr=document.getElementById('autoworkbench-root').shadowRoot;
      const btns=[...sr.querySelectorAll('button')];
      const b=btns.find(x=>/^navigation$/i.test((x.textContent||'').trim()));
      b?.click();
    }""")
    await asyncio.sleep(0.3)
    await page.screenshot(path=str(OUT/"05_outcome.png"), full_page=True)
    (OUT/"05_outcome.json").write_text(json.dumps(await shadow_text(page), indent=2))

async def stage_run(page):
    await click_tab(page, 'steps')
    await asyncio.sleep(0.3)
    clicked = await page.evaluate("""() => {
      const sr=document.getElementById('autoworkbench-root').shadowRoot;
      const btns=[...sr.querySelectorAll('button')];
      const b=btns.find(x=>/run pending steps/i.test(x.textContent));
      if (!b) return false;
      b.click();
      return true;
    }""")
    print(f"run clicked: {clicked}")
    await click_tab(page, 'llm')
    await asyncio.sleep(2.0)
    await page.screenshot(path=str(OUT/"06_run.png"), full_page=True)
    (OUT/"06_run.json").write_text(json.dumps(await shadow_text(page), indent=2))

async def stage_confirm(page):
    await asyncio.sleep(8.0)  # wait for plan_ready from LLM
    await page.screenshot(path=str(OUT/"07_plan_ready.png"), full_page=True)
    (OUT/"07_plan_ready.json").write_text(json.dumps(await shadow_text(page), indent=2))
    await page.evaluate("""() => {
      const sr=document.getElementById('autoworkbench-root').shadowRoot;
      const btns=[...sr.querySelectorAll('button')];
      const b=btns.find(x=>/confirm plan/i.test(x.textContent));
      b?.click();
    }""")
    await asyncio.sleep(3.0)
    await page.screenshot(path=str(OUT/"08_confirmed.png"), full_page=True)
    (OUT/"08_confirmed.json").write_text(json.dumps(await shadow_text(page), indent=2))

async def stage_dump(page):
    t = int(time.time())
    await page.screenshot(path=str(OUT/f"dump_{t}.png"), full_page=True)
    snap = await shadow_text(page)
    (OUT/f"dump_{t}.json").write_text(json.dumps(snap, indent=2))
    print(json.dumps(snap, indent=2))

async def stage_walk_tabs(page):
    for i, tab in enumerate(["llm", "steps", "rec", "code", "trace", "llm"], 1):
        await click_tab(page, tab)
        await asyncio.sleep(0.4)
        snap = await shadow_text(page)
        suffix = f"tab_{i:02d}_{tab}"
        await page.screenshot(path=str(OUT/f"{suffix}.png"), full_page=False)
        (OUT/f"{suffix}.json").write_text(json.dumps(snap, indent=2))
        print(f"=== {suffix} ok={snap.get('ok')} cards={len(snap.get('cards',[]))} ===")


STAGES = {
    "initial": stage_initial,
    "type_intent": stage_type_intent,
    "attach": stage_attach,
    "pick": stage_pick,
    "outcome": stage_outcome,
    "run": stage_run,
    "confirm": stage_confirm,
    "dump": stage_dump,
    "walk_tabs": stage_walk_tabs,
}

async def main(stages):
    async with async_playwright() as p:
        browser = await p.chromium.connect_over_cdp(CDP)
        ctx = browser.contexts[0]
        page = None
        for cand in ctx.pages:
            url = cand.url or ""
            if url.startswith("http://127.0.0.1:8000") or url.startswith("http://localhost:8000"):
                page = cand; break
        if page is None:
            # fall back to first non-chrome:// page
            for cand in ctx.pages:
                if not cand.url.startswith("chrome"):
                    page = cand; break
        if page is None:
            page = ctx.pages[0]
        await page.bring_to_front()
        for s in stages:
            fn = STAGES.get(s)
            if not fn:
                print(f"unknown stage: {s}", file=sys.stderr); continue
            print(f"=== {s} ===")
            await fn(page)
        await browser.close()  # detaches, doesn't kill backend

if __name__ == "__main__":
    asyncio.run(main(sys.argv[1:] or ["initial"]))
