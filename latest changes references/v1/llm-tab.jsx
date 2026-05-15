// llm-tab.jsx — the conversation thread with every card type
const { useState: useStateLlm } = React;

// — Atomic pieces ————————————————————————————————————————

function Bubble({ children, time = "11:42" }) {
  return (
    <div className="aw-msg-user">
      {children}
      <div style={{fontSize:10.5,color:"#9A6E4A",marginTop:4,opacity:.65}}>{time}</div>
    </div>
  );
}

function Sys({ from = "AutoWorkbench", time = "11:42", initials = "AW", children }) {
  return (
    <div className="aw-msg-system">
      <div className="aw-avatar">{initials}</div>
      <div className="aw-msg-content">
        <div className="aw-msg-from"><b>{from}</b><span className="aw-tstamp">· {time}</span></div>
        <div className="aw-msg-body">{children}</div>
      </div>
    </div>
  );
}

function Reason({ children, head = "Analyzing page" }) {
  return (
    <div className="aw-reason">
      <div className="aw-think-head">
        <I.Spark style={{width:11,height:11,color:"var(--tx-3)"}}/>
        {head}
      </div>
      <ul>{children}</ul>
    </div>
  );
}

function Conf({ level }) {
  const cls = level >= 0.8 ? "high" : level >= 0.5 ? "med" : "low";
  const txt = level >= 0.8 ? "High" : level >= 0.5 ? "Medium" : "Low";
  return (
    <span style={{display:"inline-flex",alignItems:"center",gap:4}}>
      <span className={"aw-conf " + cls}><i/><i/><i/></span>
      <span style={{fontSize:11, color:"var(--tx-3)"}}>{txt} · {Math.round(level*100)}%</span>
    </span>
  );
}

// — Cards ————————————————————————————————————————

function CardClarification() {
  const [pick, setPick] = useStateLlm(null);
  return (
    <div className="aw-card clarify">
      <div className="aw-card-head">
        <span className="aw-card-icon"><I.Info/></span>
        <span className="aw-card-title">Clarification needed</span>
        <span className="aw-card-meta">type · multi-choice</span>
      </div>
      <div className="aw-card-body">
        <p>Should I recommend <b>smoke</b>, <b>sanity</b>, or <b>exhaustive regression</b> checks for this pricing page? Each option changes scope and runtime.</p>
        <div style={{display:"flex",flexDirection:"column",gap:6,marginTop:8}}>
          {[
            { id: "smoke", t: "Smoke", d: "5–7 assertions · ~30s · catches obvious breakage" },
            { id: "sanity", t: "Sanity", d: "10–15 assertions · ~2min · core flows + visible content" },
            { id: "regress", t: "Exhaustive regression", d: "40+ assertions · ~10min · every section, every plan" },
          ].map(o => (
            <label key={o.id}
              onClick={() => setPick(o.id)}
              style={{
                display:"flex",gap:9,padding:"9px 11px",
                border:"1px solid " + (pick === o.id ? "var(--acc)" : "var(--br)"),
                background: pick === o.id ? "#FFF8EE" : "var(--bg-card)",
                borderRadius:9, cursor:"pointer", alignItems:"flex-start"
              }}>
              <span style={{
                width:14,height:14,borderRadius:"50%",
                border:"1.5px solid " + (pick === o.id ? "var(--acc)" : "var(--br-strong)"),
                background: pick === o.id ? "radial-gradient(circle, var(--acc) 40%, white 45%)" : "white",
                flex:"0 0 14px", marginTop:2
              }}/>
              <span>
                <span style={{fontSize:12.5,fontWeight:500}}>{o.t}</span>
                <span style={{display:"block",fontSize:11.5,color:"var(--tx-3)",marginTop:1}}>{o.d}</span>
              </span>
            </label>
          ))}
        </div>
      </div>
      <div className="aw-card-foot">
        <button className="aw-btn primary"><I.Send/>Submit answer</button>
        <button className="aw-btn subtle">Let LLM decide</button>
        <span style={{flex:1}}/>
        <span style={{fontSize:11,color:"var(--tx-4)"}}>Pauses execution until answered</span>
      </div>
    </div>
  );
}

function CardRecommendation() {
  const [items, setItems] = useStateLlm([
    { id: "rec_1", t: "Hero heading visible and contains \"plans that scale\"",  checked: true, scope: "section.hero" },
    { id: "rec_2", t: "Three pricing cards rendered (Starter, Pro, Enterprise)", checked: true, scope: "section.pricing" },
    { id: "rec_3", t: "Pro plan shows \"Most popular\" tag",                     checked: true, scope: "section.pricing > .featured" },
    { id: "rec_4", t: "All CTA buttons are enabled and have href",               checked: true, scope: "section.pricing a.cta, .hero a.btn.primary" },
    { id: "rec_5", t: "FAQ accordion expands when first row clicked",            checked: false, scope: "section.faq .row[0]" },
    { id: "rec_6", t: "Footer status link navigates to status.acme.dev",         checked: true, scope: "footer a[href*=\"status\"]" },
  ]);
  const toggle = (id) => setItems(items.map(i => i.id === id ? {...i, checked: !i.checked} : i));
  return (
    <div className="aw-card plan">
      <div className="aw-card-head">
        <span className="aw-card-icon"><I.Layers/></span>
        <span className="aw-card-title">Recommended assertions</span>
        <span className="aw-card-meta">grouped by section · {items.filter(i=>i.checked).length}/{items.length} selected</span>
      </div>
      <div className="aw-card-body">
        <p style={{color:"var(--tx-2)", fontSize:12}}>
          Based on DOM analysis I found a hero, a 3-card pricing grid, a 4-row FAQ, and a footer.
          Pick the ones to assert — you can also ask for a specific Pro plan price below.
        </p>
        <div style={{display:"flex",flexDirection:"column",gap:2,marginTop:8}}>
          {items.map((it, idx) => (
            <label key={it.id} style={{
              display:"flex", gap:9, padding:"7px 8px", borderRadius:6,
              background: idx % 2 ? "var(--bg-soft)" : "transparent",
              cursor:"pointer", alignItems:"flex-start"
            }}>
              <input type="checkbox" checked={it.checked} onChange={() => toggle(it.id)}
                     style={{marginTop:3,accentColor:"var(--acc)"}}/>
              <span style={{flex:1, minWidth:0}}>
                <span style={{fontSize:12.5, color: it.checked ? "var(--tx)" : "var(--tx-3)", textDecoration: it.checked ? "none" : "line-through"}}>
                  {it.t}
                </span>
                <span style={{display:"block",fontSize:10.5,color:"var(--tx-4)",fontFamily:"var(--ff-mono)",marginTop:2}}>{it.scope}</span>
              </span>
            </label>
          ))}
        </div>
      </div>
      <div className="aw-card-foot">
        <button className="aw-btn primary"><I.Check/>Use selected</button>
        <button className="aw-btn"><I.Plus/>Add my own assertion</button>
        <button className="aw-btn subtle">Group differently</button>
      </div>
    </div>
  );
}

function CardPlanDiff() {
  return (
    <div className="aw-card diff">
      <div className="aw-card-head">
        <span className="aw-card-icon"><I.Diff/></span>
        <span className="aw-card-title">Plan revision proposed</span>
        <span className="aw-card-meta">v2 · 2 changes</span>
      </div>
      <div className="aw-card-body">
        <p style={{color:"var(--tx-2)", fontSize:12}}>
          You asked to drop the FAQ check and assert the exact Pro plan price. Here is the proposed delta to the plan.
        </p>
        <div className="aw-diff" style={{marginTop:6, display:"flex", flexDirection:"column", gap:1}}>
          <div className="aw-diff-row ctx"><span className="aw-diff-sign"> </span>plan.steps[3]  CTA buttons enabled and have href</div>
          <div className="aw-diff-row ctx"><span className="aw-diff-sign"> </span>plan.steps[4]  Pro card shows "Most popular" tag</div>
          <div className="aw-diff-row rem"><span className="aw-diff-sign">-</span>plan.steps[5]  FAQ accordion expands when first row clicked</div>
          <div className="aw-diff-row add"><span className="aw-diff-sign">+</span>plan.steps[5]  Pro plan price equals "$49 / mo"</div>
          <div className="aw-diff-row ctx"><span className="aw-diff-sign"> </span>plan.steps[6]  Footer status link navigates to status.acme.dev</div>
        </div>
        <div className="aw-card-section-title">Impact</div>
        <ul className="aw-dotlist">
          <li className="ok">Faster: removes 1 click interaction step (~600ms saved)</li>
          <li>Adds a brittle exact-string assertion — flags as <span className="aw-badge-i warn">fragile copy</span></li>
        </ul>
      </div>
      <div className="aw-card-foot">
        <button className="aw-btn primary"><I.Check/>Apply changes</button>
        <button className="aw-btn">Keep editing</button>
        <button className="aw-btn subtle"><I.Retry style={{width:12,height:12}}/>Revert</button>
      </div>
    </div>
  );
}

function CardPlanReady({ status = "ready" }) {
  return (
    <div className="aw-card plan">
      <div className="aw-card-head">
        <span className="aw-card-icon"><I.Layers/></span>
        <span className="aw-card-title">Plan ready · sanity check on /pricing</span>
        <span className="aw-card-meta">
          <span className="aw-badge-i acc"><span className="ldot"/>plan_ready</span>
        </span>
      </div>
      <div className="aw-card-body" style={{paddingBottom:6}}>
        <div style={{display:"grid", gridTemplateColumns:"1fr 1fr 1fr", gap:8, marginBottom:8}}>
          <div className="aw-status-pill" style={{justifySelf:"start"}}><span className="aw-dot" style={{background:"var(--blu)"}}/><span className="k">steps</span><span className="v">6</span></div>
          <div className="aw-status-pill" style={{justifySelf:"start"}}><span className="aw-dot" style={{background:"var(--vio)"}}/><span className="k">ops</span><span className="v">11</span></div>
          <div className="aw-status-pill" style={{justifySelf:"start"}}><span className="aw-dot" style={{background:"var(--grn)"}}/><span className="k">est</span><span className="v">~28s</span></div>
        </div>
        <div className="aw-step pending">
          <span className="aw-step-idx">1</span>
          <div className="aw-step-main">
            <div className="aw-step-title">Verify hero heading <span className="id">stp_a1f3</span></div>
            <div className="aw-step-meta">
              <span className="aw-badge-i ok"><span className="ldot"/>strong locator</span>
              <span>scope: <span className="mono">section.hero</span></span>
            </div>
            <div className="aw-step-ops">
              <div className="aw-step-op"><span className="op-tag">assert</span>visible · text contains "plans that scale"</div>
            </div>
          </div>
        </div>
        <div className="aw-step pending">
          <span className="aw-step-idx">2</span>
          <div className="aw-step-main">
            <div className="aw-step-title">Three pricing cards present <span className="id">stp_b2c9</span></div>
            <div className="aw-step-meta">
              <span className="aw-badge-i ok"><span className="ldot"/>strong locator</span>
              <span>scope: <span className="mono">section.pricing</span></span>
            </div>
            <div className="aw-step-ops">
              <div className="aw-step-op"><span className="op-tag">count</span>.ws-plan count === 3</div>
              <div className="aw-step-op"><span className="op-tag">assert</span>each card has name + price + cta</div>
            </div>
          </div>
        </div>
        <div className="aw-step pending">
          <span className="aw-step-idx">3</span>
          <div className="aw-step-main">
            <div className="aw-step-title">Pro card marked "Most popular" <span className="id">stp_c4d7</span></div>
            <div className="aw-step-meta">
              <span className="aw-badge-i ok"><span className="ldot"/>strong locator</span>
              <span>scope: <span className="mono">.ws-plan.featured</span></span>
            </div>
          </div>
        </div>
        <div className="aw-step pending">
          <span className="aw-step-idx">4</span>
          <div className="aw-step-main">
            <div className="aw-step-title">All CTA buttons enabled <span className="id">stp_d8e2</span></div>
            <div className="aw-step-meta">
              <span className="aw-badge-i warn"><span className="ldot"/>ambiguous locator</span>
              <span>4 candidates</span>
            </div>
            <div className="aw-step-ops">
              <div className="aw-step-op"><span className="op-tag">forEach</span>a.btn.primary, a.ws-plan-cta</div>
              <div className="aw-step-op"><span className="op-tag">assert</span>enabled · has href</div>
            </div>
          </div>
        </div>
        <div className="aw-step pending">
          <span className="aw-step-idx">5</span>
          <div className="aw-step-main">
            <div className="aw-step-title">Pro price equals "$49 / mo" <span className="id">stp_e1f4</span></div>
            <div className="aw-step-meta">
              <span className="aw-badge-i warn"><span className="ldot"/>fragile copy</span>
              <span>scope: <span className="mono">.ws-plan.featured .ws-plan-price</span></span>
            </div>
          </div>
        </div>
        <div className="aw-step pending">
          <span className="aw-step-idx">6</span>
          <div className="aw-step-main">
            <div className="aw-step-title">Footer status link points at status.acme.dev <span className="id">stp_f7a3</span></div>
            <div className="aw-step-meta">
              <span className="aw-badge-i ok"><span className="ldot"/>strong locator</span>
            </div>
          </div>
        </div>
      </div>
      <div className="aw-card-foot">
        <button className="aw-btn primary"><I.Play/>Confirm &amp; run<span className="aw-kbd">⌘↵</span></button>
        <button className="aw-btn"><I.Diff/>Edit plan</button>
        <button className="aw-btn subtle">Run first 3 only</button>
        <span style={{flex:1}}/>
        <span style={{fontSize:11,color:"var(--tx-4)"}}>Backend will validate locators before execution</span>
      </div>
    </div>
  );
}

function CardPermission() {
  return (
    <div className="aw-card perm">
      <div className="aw-card-head">
        <span className="aw-card-icon"><I.Shield/></span>
        <span className="aw-card-title">Permission required · medium-risk action</span>
        <span className="aw-card-meta">
          <span className="aw-badge-i warn"><span className="ldot"/>policy: balanced</span>
        </span>
      </div>
      <div className="aw-card-body">
        <div className="aw-fail-grid">
          <div className="k">operation</div><div className="v mono">page.click("a.btn.primary[Get started]")</div>
          <div className="k">on step</div><div className="v">stp_d8e2 · CTA buttons enabled</div>
          <div className="k">risk</div><div className="v"><span className="aw-badge-i warn"><span className="ldot"/>navigation</span> · may leave /pricing</div>
          <div className="k">why</div><div className="v">Verifying enabled state requires actuating the button. The CTA may navigate to /signup.</div>
        </div>
      </div>
      <div className="aw-card-foot" style={{flexWrap:"wrap"}}>
        <button className="aw-btn primary"><I.Check/>Allow once</button>
        <button className="aw-btn">Allow for this plan</button>
        <button className="aw-btn">Edit plan to skip click</button>
        <button className="aw-btn danger"><I.Stop style={{width:11,height:11}}/>Deny &amp; stop</button>
      </div>
    </div>
  );
}

function CardExecution() {
  return (
    <div className="aw-card exec">
      <div className="aw-card-head">
        <span className="aw-card-icon"><I.Play/></span>
        <span className="aw-card-title">Executing plan v2</span>
        <span className="aw-card-meta">
          <span className="aw-badge-i info"><span className="ldot"/>step 3 of 6</span>
        </span>
      </div>
      <div className="aw-card-body">
        <div className="aw-prog" style={{marginBottom:10}}/>
        <div className="aw-step ok">
          <span className="aw-step-idx"><I.Check style={{width:11,height:11}}/></span>
          <div className="aw-step-main">
            <div className="aw-step-title">Verify hero heading</div>
            <div className="aw-step-meta">
              <span className="aw-badge-i ok"><span className="ldot"/>recorded</span>
              <span>locator <span className="mono">role=heading[level=1]</span></span>
              <span>· 412ms</span>
            </div>
          </div>
        </div>
        <div className="aw-step ok">
          <span className="aw-step-idx"><I.Check style={{width:11,height:11}}/></span>
          <div className="aw-step-main">
            <div className="aw-step-title">Three pricing cards present</div>
            <div className="aw-step-meta">
              <span className="aw-badge-i ok"><span className="ldot"/>recorded</span>
              <span>count = 3 · 138ms</span>
              <span>· <button className="aw-link">code_update</button></span>
            </div>
          </div>
        </div>
        <div className="aw-step run">
          <span className="aw-step-idx">3</span>
          <div className="aw-step-main">
            <div className="aw-step-title">Pro card marked "Most popular" <span className="id">stp_c4d7</span></div>
            <div className="aw-step-meta">
              <span className="aw-badge-i info"><span className="ldot"/>resolving locator…</span>
              <span>scope <span className="mono">.ws-plan.featured</span></span>
            </div>
            <div className="aw-step-ops">
              <div className="aw-step-op"><span className="op-tag">wait</span>locator stable · 2 candidates collapsing to 1</div>
            </div>
          </div>
        </div>
        <div className="aw-step pending">
          <span className="aw-step-idx">4</span>
          <div className="aw-step-main">
            <div className="aw-step-title">All CTA buttons enabled</div>
            <div className="aw-step-meta"><span className="aw-badge-i outline">queued</span></div>
          </div>
        </div>
      </div>
      <div className="aw-card-foot">
        <button className="aw-btn"><I.Pause style={{width:11,height:11}}/>Pause</button>
        <button className="aw-btn danger"><I.Stop style={{width:11,height:11}}/>Stop run</button>
        <span style={{flex:1}}/>
        <span style={{fontSize:11,color:"var(--tx-3)"}}>Tail traces in <button className="aw-link">Trace</button> · evidence in <button className="aw-link">Recorded</button></span>
      </div>
    </div>
  );
}

function CardLocatorAmbiguity() {
  const [pick, setPick] = useStateLlm("hero");
  const cands = [
    { id:"header", t:'Header CTA — "Get started"', scope:"nav.ws-topnav .cta", conf:0.92, risk:"safe-read",  preview:'getByRole(\'link\', { name: \'Get started\' }).first()' },
    { id:"hero",   t:'Hero CTA — "Get started"',   scope:".ws-hero .btn.primary", conf:0.71, risk:"medium",  preview:'page.locator(\'.ws-hero a.btn.primary\')' },
    { id:"starter",t:'Starter plan CTA — "Get started"', scope:".ws-plan:nth(1) .ws-plan-cta", conf:0.34, risk:"medium", preview:'page.getByText(\'Get started\').nth(2)' },
  ];
  return (
    <div className="aw-card locator">
      <div className="aw-card-head">
        <span className="aw-card-icon"><I.Target/></span>
        <span className="aw-card-title">Locator ambiguity — choose a candidate</span>
        <span className="aw-card-meta">
          <span className="aw-badge-i vio"><span className="ldot"/>3 matches</span>
        </span>
      </div>
      <div className="aw-card-body">
        <p style={{color:"var(--tx-2)", fontSize:12, marginBottom:8}}>
          I found <b>3 visible "Get started" links</b> on /pricing. Execution is paused until you pick one or I find a unique candidate.
        </p>
        {cands.map((c,i) => (
          <div key={c.id} className={"aw-cand " + (pick === c.id ? "selected" : "")} onClick={() => setPick(c.id)}>
            <span className="aw-cand-num">{i+1}</span>
            <div className="aw-cand-main">
              <div style={{display:"flex", alignItems:"center", gap:8, justifyContent:"space-between"}}>
                <span className="aw-cand-title">{c.t}</span>
                <Conf level={c.conf}/>
              </div>
              <div className="aw-cand-loc">{c.preview}</div>
              <div className="aw-cand-meta">
                <span>scope: <span style={{fontFamily:"var(--ff-mono)", color:"var(--tx-2)"}}>{c.scope}</span></span>
                <span>·</span>
                <span>risk: <span className={"aw-badge-i " + (c.risk === "safe-read" ? "ok" : "warn")}><span className="ldot"/>{c.risk}</span></span>
              </div>
              <div className="aw-cand-actions">
                <button className="aw-btn" onClick={(e) => { e.stopPropagation(); setPick(c.id); }}>
                  <I.Check/> Select
                </button>
                <button className="aw-btn subtle" onClick={(e) => e.stopPropagation()}>
                  <I.Eye/>Highlight in page
                </button>
              </div>
            </div>
          </div>
        ))}
      </div>
      <div className="aw-card-foot" style={{flexWrap:"wrap"}}>
        <button className="aw-btn primary"><I.Check/>Use candidate {cands.findIndex(c => c.id === pick)+1}</button>
        <button className="aw-btn"><I.Spark/>Ask LLM for better locator</button>
        <button className="aw-btn">Change scope</button>
        <button className="aw-btn subtle"><I.Stop style={{width:11,height:11}}/>Stop run</button>
      </div>
    </div>
  );
}

function CardRecovery() {
  return (
    <div className="aw-card recover">
      <div className="aw-card-head">
        <span className="aw-card-icon"><I.Alert/></span>
        <span className="aw-card-title">Recovery needed · step 5</span>
        <span className="aw-card-meta">
          <span className="aw-badge-i err"><span className="ldot"/>assertion failed</span>
        </span>
      </div>
      <div className="aw-card-body">
        <div className="aw-fail-grid">
          <div className="k">step</div><div className="v">stp_e1f4 · Pro price equals "$49 / mo"</div>
          <div className="k">operation</div><div className="v mono">expect(locator).toHaveText('$49 / mo')</div>
          <div className="k">expected</div><div className="v mono" style={{color:"#2F6B3D"}}>"$49 / mo"</div>
          <div className="k">actual</div><div className="v mono" style={{color:"#8A3A2E"}}>"$49 /mo"  <span style={{color:"var(--tx-3)"}}>(missing space)</span></div>
          <div className="k">failed at</div><div className="v">assertion layer · locator matched 1 element</div>
          <div className="k">evidence</div><div className="v" style={{display:"flex", gap:8, flexWrap:"wrap"}}>
            <button className="aw-link"><I.Camera style={{width:11,height:11,display:"inline",marginRight:3,verticalAlign:"-1px"}}/>screenshot</button>
            <button className="aw-link"><I.Doc style={{width:11,height:11,display:"inline",marginRight:3,verticalAlign:"-1px"}}/>trace.zip</button>
            <button className="aw-link"><I.Trace style={{width:11,height:11,display:"inline",marginRight:3,verticalAlign:"-1px"}}/>open trace</button>
          </div>
        </div>

        <div className="aw-card-section-title">Recovery attempts</div>
        <ul className="aw-dotlist">
          <li className="no">deterministic retry × 2 — same text returned</li>
          <li className="no">whitespace normalization — heuristic disabled by policy</li>
          <li className="ok">LLM repair available: relax to <span style={{fontFamily:"var(--ff-mono)",color:"var(--tx)"}}>toContainText("$49")</span></li>
        </ul>
      </div>
      <div className="aw-card-foot" style={{flexWrap:"wrap"}}>
        <button className="aw-btn primary"><I.Spark/>Apply LLM repair</button>
        <button className="aw-btn"><I.Retry style={{width:12,height:12}}/>Retry as-is</button>
        <button className="aw-btn">Choose another locator</button>
        <button className="aw-btn">Provide instruction…</button>
        <button className="aw-btn"><I.Skip style={{width:11,height:11}}/>Skip step</button>
        <button className="aw-btn danger"><I.Stop style={{width:11,height:11}}/>Stop run</button>
      </div>
    </div>
  );
}

function CardCompleted() {
  return (
    <div className="aw-card done">
      <div className="aw-card-head">
        <span className="aw-card-icon"><I.Check/></span>
        <span className="aw-card-title">Run completed</span>
        <span className="aw-card-meta">
          <span className="aw-badge-i ok"><span className="ldot"/>6 / 6 recorded</span>
        </span>
      </div>
      <div className="aw-card-body">
        <div style={{display:"grid", gridTemplateColumns:"repeat(4, 1fr)", gap:8, marginBottom:10}}>
          <div className="aw-status-pill" style={{justifySelf:"start"}}><span className="aw-dot" style={{background:"var(--grn)"}}/><span className="k">passed</span><span className="v">5</span></div>
          <div className="aw-status-pill" style={{justifySelf:"start"}}><span className="aw-dot" style={{background:"var(--ylw)"}}/><span className="k">repaired</span><span className="v">1</span></div>
          <div className="aw-status-pill" style={{justifySelf:"start"}}><span className="aw-dot" style={{background:"var(--red)"}}/><span className="k">failed</span><span className="v">0</span></div>
          <div className="aw-status-pill" style={{justifySelf:"start"}}><span className="aw-dot" style={{background:"var(--blu)"}}/><span className="k">elapsed</span><span className="v">31.2s</span></div>
        </div>
        <ul className="aw-dotlist">
          <li className="ok"><span className="sec">Recorded</span>6 parent steps · 11 child operations</li>
          <li className="ok"><span className="sec">Code</span>updated <span style={{fontFamily:"var(--ff-mono)"}}>tests/pricing.spec.ts</span> · +47 lines</li>
          <li className="ok"><span className="sec">Trace</span>artifacts saved · <button className="aw-link">view</button></li>
        </ul>
        <div className="aw-card-section-title">Acceptance gate</div>
        <p style={{margin:0, fontSize:12, color:"var(--tx-2)"}}>
          Paid E2E suite has not been run yet — frontend cannot mark this fully accepted. Backend will surface a <span className="aw-badge-i acc"><span className="ldot"/>e2e_pending</span> event when the nightly run finishes.
        </p>
      </div>
      <div className="aw-card-foot">
        <button className="aw-btn primary"><I.Repeat/>Replay all</button>
        <button className="aw-btn"><I.Branch/>Save as suite</button>
        <button className="aw-btn"><I.Code/>Open code</button>
        <button className="aw-btn subtle"><I.Download/>Download trace</button>
      </div>
    </div>
  );
}

function CardOffline() {
  return (
    <div className="aw-card recover">
      <div className="aw-card-head">
        <span className="aw-card-icon"><I.Plug/></span>
        <span className="aw-card-title">Backend unavailable</span>
        <span className="aw-card-meta">
          <span className="aw-badge-i err"><span className="ldot"/>ws disconnected</span>
        </span>
      </div>
      <div className="aw-card-body">
        <p style={{margin:"0 0 6px"}}>The frontend lost its websocket to <span style={{fontFamily:"var(--ff-mono)"}}>autoworkbench-runner</span> 14s ago. <b>I will not infer success or failure of in-flight steps.</b></p>
        <ul className="aw-dotlist">
          <li className="no">last event: <span style={{fontFamily:"var(--ff-mono)"}}>step.running stp_c4d7</span></li>
          <li>auto-reconnect in <span style={{fontFamily:"var(--ff-mono)"}}>3s…</span> (attempt 2 of 5)</li>
          <li>any in-flight code_update / recorded events will replay on reconnect</li>
        </ul>
      </div>
      <div className="aw-card-foot">
        <button className="aw-btn primary"><I.Sync/>Reconnect now</button>
        <button className="aw-btn">View connection log</button>
        <button className="aw-btn subtle">Switch endpoint</button>
      </div>
    </div>
  );
}

function CardSchemaError() {
  return (
    <div className="aw-card warn">
      <div className="aw-card-head">
        <span className="aw-card-icon"><I.Alert/></span>
        <span className="aw-card-title">Schema validation failed</span>
        <span className="aw-card-meta">
          <span className="aw-badge-i warn"><span className="ldot"/>llm_response_invalid</span>
        </span>
      </div>
      <div className="aw-card-body">
        <p style={{margin:"0 0 6px", fontSize:12.5}}>The LLM returned a plan that does not match <span style={{fontFamily:"var(--ff-mono)"}}>plan.v3.schema.json</span>. Nothing was executed.</p>
        <div className="aw-fail-grid">
          <div className="k">at</div>          <div className="v mono">$.steps[2].operations[0].kind</div>
          <div className="k">expected</div>    <div className="v mono">one of: assert | click | fill | navigate | wait</div>
          <div className="k">received</div>    <div className="v mono">"check-presence"  <span style={{color:"var(--tx-3)"}}>(unknown)</span></div>
        </div>
      </div>
      <div className="aw-card-foot">
        <button className="aw-btn primary"><I.Sync/>Ask LLM to repair plan</button>
        <button className="aw-btn">Edit plan manually</button>
        <button className="aw-btn subtle">Open raw response</button>
      </div>
    </div>
  );
}

// — Empty state ————————————————————————————————————————

function LlmEmpty({ onSeed }) {
  return (
    <div className="aw-empty">
      <div className="ic"><I.Spark/></div>
      <h3>Describe what you want to automate or validate.</h3>
      <p>Tell me about a page, attach a selection from the page, or paste a Playwright snippet. I'll plan a flow, ask before running, and record evidence on the way.</p>
      <div className="aw-suggestions">
        <span className="aw-chip" onClick={onSeed}>Validate this pricing page</span>
        <span className="aw-chip">Smoke test the login flow</span>
        <span className="aw-chip">Repair my flaky checkout spec</span>
        <span className="aw-chip">Record an Add-to-cart journey</span>
      </div>
    </div>
  );
}

// — Composer (sticky at bottom of LLM tab) ————————————————————————————————————————

function Composer() {
  return (
    <div className="aw-composer">
      <div className="aw-composer-box">
        <div className="aw-composer-actions" style={{marginBottom:2}}>
          <span className="aw-context-chip"><I.Globe/> /pricing</span>
          <span className="aw-context-chip"><I.Target/> 2 selected elements</span>
          <span className="aw-context-chip"><I.Doc/> users.csv</span>
          <button className="aw-btn subtle" style={{padding:"3px 7px",fontSize:11}}>
            <I.Plus/>Add context
          </button>
        </div>
        <textarea className="aw-composer-input" rows={2}
                  placeholder="Reply, refine the plan, or paste a step…"
                  defaultValue=""></textarea>
        <div className="aw-composer-actions">
          <button className="aw-icon-btn" title="Attach"><I.Paperclip/></button>
          <button className="aw-icon-btn" title="Pick element"><I.Mouse/></button>
          <button className="aw-icon-btn" title="Attach screenshot"><I.Camera/></button>
          <span className="aw-spacer" style={{flex:1}}/>
          <span style={{fontSize:11, color:"var(--tx-4)"}}>complete-llm · gpt-class · plan-aware</span>
          <button className="aw-btn primary"><I.Send/>Send<span className="aw-kbd">↵</span></button>
        </div>
      </div>
    </div>
  );
}

// — Master assembly ————————————————————————————————————————

function LlmThread({ state }) {
  // state values: idle | planning | clarify | recommend | plan | diff | permit |
  //               exec | locator | recover | done | offline | schema
  if (state === "idle") return <LlmEmpty onSeed={() => {}}/>;

  // Build progressive thread — each later state shows everything from prior states.
  const order = ["planning","clarify","recommend","plan","diff","permit","exec","locator","recover","done"];
  const show = (k) => order.indexOf(state) >= order.indexOf(k);

  return (
    <div className="aw-thread">
      <div className="aw-day-sep">Session started · today, 11:42 AM</div>

      <Bubble time="11:42">
        Validate this pricing page. Use the design system tokens we agreed on and make sure the Pro plan price is exactly what marketing approved.
      </Bubble>

      {show("planning") && (
        <Sys time="11:42">
          <p>On it. Scanning <b>acme.dev/pricing</b> with the page-intelligence tool — I'll group what I see, then ask before running anything.</p>
          <Reason head="Page analysis">
            <li>DOM ready · 18 sections discovered</li>
            <li>Detected: hero, 3-card pricing grid, FAQ accordion, footer</li>
            <li>Found <b>3 visible</b> "Get started" links — flag for locator review</li>
            <li>No <span style={{fontFamily:"var(--ff-mono)"}}>data-testid</span> attributes — relying on role + text</li>
          </Reason>
        </Sys>
      )}

      {show("clarify") && (
        <Sys time="11:43">
          <p>Before I draft a plan — what depth do you want?</p>
        </Sys>
      )}
      {show("clarify") && <CardClarification/>}

      {show("recommend") && (
        <>
          <Bubble time="11:44">Sanity is fine for now.</Bubble>
          <Sys time="11:44">
            <p>Good. Here are the assertions I'd run — uncheck anything that isn't valuable yet.</p>
          </Sys>
          <CardRecommendation/>
        </>
      )}

      {show("plan") && (
        <>
          <Bubble time="11:45">Drop the FAQ check, and add an exact assertion that the Pro plan price equals "$49 / mo".</Bubble>
          <Sys time="11:45">
            <p>Got it. Drafting plan v2 with those changes.</p>
          </Sys>
        </>
      )}

      {show("diff") && <CardPlanDiff/>}
      {show("plan") && <CardPlanReady/>}

      {show("permit") && (
        <Sys time="11:46">
          <p>Before I touch a CTA, I need permission for one medium-risk action.</p>
        </Sys>
      )}
      {show("permit") && <CardPermission/>}

      {show("exec") && (
        <>
          <Bubble time="11:46">Allow once. Run the plan.</Bubble>
          <Sys time="11:46">
            <p>Running plan v2. I'll record evidence after each successful operation; <button className="aw-link">Trace</button> tails live.</p>
          </Sys>
          <CardExecution/>
        </>
      )}

      {show("locator") && (
        <Sys time="11:47">
          <p>Step 4 hit a snag — three "Get started" links and I can't tell which one you mean. Stopping execution until you choose or the backend confirms a unique candidate.</p>
        </Sys>
      )}
      {show("locator") && <CardLocatorAmbiguity/>}

      {show("recover") && (
        <Sys time="11:48">
          <p>Step 5 failed the assertion — the Pro card renders the price without a space between number and unit. Deterministic recovery didn't help; the LLM has a suggested repair.</p>
        </Sys>
      )}
      {show("recover") && <CardRecovery/>}

      {show("done") && (
        <>
          <Bubble time="11:49">Apply the repair.</Bubble>
          <Sys time="11:49">
            <p>Repair applied, step recorded, code updated. Run finished.</p>
          </Sys>
          <CardCompleted/>
        </>
      )}

      {state === "offline" && (<>
        <Sys time="11:46">
          <p>Lost connection mid-step. Holding state.</p>
        </Sys>
        <CardOffline/>
      </>)}

      {state === "schema" && (<>
        <Sys time="11:47">
          <p>The model returned something I can't safely execute.</p>
        </Sys>
        <CardSchemaError/>
      </>)}
    </div>
  );
}

window.LlmThread = LlmThread;
window.Composer = Composer;
