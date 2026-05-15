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
  // Live binding: subscribe to clarification_needed events from transport.
  // Falls back to the mock content (smoke/sanity/regress) when there is no
  // real event, so the standalone harness keeps working.
  const [live, setLive] = React.useState(null);
  React.useEffect(() => {
    const AW = (typeof window !== 'undefined' && window.AW) || null;
    if (!AW || typeof AW.on !== 'function') return;
    // Read the last event if it already arrived before this card mounted.
    if (AW.lastEvent && AW.lastEvent.type === 'clarification_needed') {
      const p = AW.lastEvent.payload || AW.lastEvent;
      setLive({ question: p.question, options: Array.isArray(p.options) ? p.options : [] });
    }
    return AW.on('clarification_needed', (env) => {
      const p = (env && (env.payload || env)) || {};
      setLive({ question: p.question, options: Array.isArray(p.options) ? p.options : [] });
      setPick(null);
    });
  }, []);
  const mockOptions = [
    { id: "smoke",   t: "Smoke",                  d: "5–7 assertions · ~30s · catches obvious breakage" },
    { id: "sanity",  t: "Sanity",                 d: "10–15 assertions · ~2min · core flows + visible content" },
    { id: "regress", t: "Exhaustive regression",  d: "40+ assertions · ~10min · every section, every plan" },
  ];
  const liveQuestion = live && live.question;
  const liveOptions = (live && live.options || []).filter(Boolean).map((o, i) => ({
    id: String(o), t: String(o), d: ""
  }));
  const question = liveQuestion || "Should I recommend smoke, sanity, or exhaustive regression checks for this pricing page? Each option changes scope and runtime.";
  const options = liveOptions.length > 0 ? liveOptions : mockOptions;
  return (
    <div className="aw-card clarify needs-input">
      <div className="aw-card-head">
        <span className="aw-card-icon"><I.Info/></span>
        <span className="aw-card-title">Clarification needed</span>
        <span className="aw-card-state">Decision required</span>
        <span className="aw-card-source llm"><span className="src-dot"/>{live ? 'LLM live' : 'LLM proposal'}</span>
      </div>
      <div className="aw-card-body">
        {liveQuestion
          ? <p>{liveQuestion}</p>
          : <p>Should I recommend <b>smoke</b>, <b>sanity</b>, or <b>exhaustive regression</b> checks for this pricing page? Each option changes scope and runtime.</p>}
        <div style={{display:"flex",flexDirection:"column",gap:6,marginTop:8}}>
          {options.map(o => (
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
                {o.d ? <span style={{display:"block",fontSize:11.5,color:"var(--tx-3)",marginTop:1}}>{o.d}</span> : null}
              </span>
            </label>
          ))}
        </div>
      </div>
      <div className="aw-card-foot">
        <button className="aw-btn primary"
                onClick={() => {
                  // T-8: Submit answer → typed option_selected carrying
                  // the picked radio id. Backend server.py:597 routes
                  // through normalize_frontend_command + control_queue.
                  const AW = (typeof window !== 'undefined' && window.AW) || null;
                  if (!AW || typeof AW.send !== 'function') return;
                  const value = pick || '';
                  if (!value) return;
                  AW.send({ type: 'option_selected', value: value, answer: value });
                }}
                disabled={!pick}>
          <I.Send/>Submit answer
        </button>
        <button className="aw-btn subtle"
                onClick={() => {
                  // T-8: Let LLM decide → typed correction asking the
                  // model to choose. No new command needed.
                  const AW = (typeof window !== 'undefined' && window.AW) || null;
                  if (AW && typeof AW.send === 'function') {
                    AW.send({ type: 'correction', message: 'Let the model choose the clarification answer.', auto: true });
                  }
                }}>
          Let LLM decide
        </button>
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
    <div className="aw-card plan needs-input">
      <div className="aw-card-head">
        <span className="aw-card-icon"><I.Layers/></span>
        <span className="aw-card-title">Recommended assertions</span>
        <span className="aw-card-state">Review</span>
        <span className="aw-card-source llm"><span className="src-dot"/>LLM proposal · not executable</span>
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
        <button className="aw-btn primary"
                onClick={() => {
                  // T-8: Use selected → typed option_selected with the
                  // list of currently-checked recommendation ids.
                  const AW = (typeof window !== 'undefined' && window.AW) || null;
                  if (!AW || typeof AW.send !== 'function') return;
                  const selected = items.filter(i => i.checked).map(i => i.id);
                  AW.send({ type: 'option_selected', value: selected, answer: selected });
                }}>
          <I.Check/>Use selected
        </button>
        <button className="aw-btn"
                onClick={() => {
                  // T-8: Add my own assertion → focus composer with a
                  // prefix so the user can write a custom assertion.
                  const ta = document.querySelector('textarea.aw-composer-input');
                  if (ta) { ta.focus(); ta.value = 'Add assertion: '; ta.setSelectionRange(ta.value.length, ta.value.length); }
                }}>
          <I.Plus/>Add my own assertion
        </button>
        <button className="aw-btn subtle"
                onClick={() => {
                  // T-8: Group differently → typed correction asking the
                  // model to regroup the recommended assertions.
                  const AW = (typeof window !== 'undefined' && window.AW) || null;
                  if (AW && typeof AW.send === 'function') {
                    AW.send({ type: 'correction', message: 'Group the recommended assertions differently (e.g. by page section instead of priority).' });
                  }
                }}>
          Group differently
        </button>
      </div>
    </div>
  );
}

function CardPlanDiff() {
  return (
    <div className="aw-card diff needs-input">
      <div className="aw-card-head">
        <span className="aw-card-icon"><I.Diff/></span>
        <span className="aw-card-title">Plan revision proposed</span>
        <span className="aw-card-state">Review</span>
        <span className="aw-card-source llm"><span className="src-dot"/>LLM proposal · v2 · 2 changes</span>
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
    <div className="aw-card plan needs-input">
      <div className="aw-card-head">
        <span className="aw-card-icon"><I.Layers/></span>
        <span className="aw-card-title">Plan ready · sanity check on /pricing</span>
        <span className="aw-card-state">Confirm to run</span>
        <span className="aw-card-source backend"><span className="src-dot"/>Backend event · plan_ready</span>
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
        <button className="aw-btn primary"
                onClick={() => {
                  // T-3: Confirm & run → typed `confirmed` command. Backend
                  // routes through control_queue and resumes the run.
                  const AW = (typeof window !== 'undefined' && window.AW) || null;
                  if (AW && typeof AW.send === 'function') {
                    AW.send({ type: 'confirmed' });
                  }
                }}>
          <I.Play/>Confirm &amp; run<span className="aw-kbd">⌘↵</span>
        </button>
        <button className="aw-btn"
                onClick={() => {
                  // T-3: Edit plan → focus composer so the user can type a
                  // correction. A future task may swap to a dedicated edit
                  // modal once the spec ambiguity is resolved.
                  const ta = document.querySelector('textarea.aw-composer-input');
                  if (ta) { ta.focus(); ta.value = 'Revise plan: '; ta.setSelectionRange(ta.value.length, ta.value.length); }
                }}>
          <I.Diff/>Edit plan
        </button>
        <button className="aw-btn subtle"
                onClick={() => {
                  // T-3: Run first 3 → send as a free-text correction. A
                  // typed slice payload is deferred per integration map §10
                  // (open spec ambiguity #8); this keeps the backend in
                  // charge of interpreting the partial-run intent.
                  const AW = (typeof window !== 'undefined' && window.AW) || null;
                  if (AW && typeof AW.send === 'function') {
                    AW.send({ type: 'correction', message: 'Run only the first 3 steps.' });
                  }
                }}>
          Run first 3 only
        </button>
        <span style={{flex:1}}/>
        <span style={{fontSize:11,color:"var(--tx-4)"}}>Backend will validate locators before execution</span>
      </div>
    </div>
  );
}

function CardPermission() {
  return (
    <div className="aw-card perm needs-input">
      <div className="aw-card-head">
        <span className="aw-card-icon"><I.Shield/></span>
        <span className="aw-card-title">Permission required · medium-risk action</span>
        <span className="aw-card-state" style={{background:"var(--ylw-soft)",color:"#7A5A0E",borderColor:"#ECD89A"}}>Decision required</span>
        <span className="aw-card-source backend"><span className="src-dot"/>policy · balanced</span>
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
        <button className="aw-btn primary"
                onClick={() => {
                  // T-9: Allow once → typed permission_decision with
                  // scope=once. Backend server.py:767 routes through
                  // normalize_frontend_command + control_queue.
                  const AW = (typeof window !== 'undefined' && window.AW) || null;
                  if (AW && typeof AW.send === 'function') {
                    AW.send({ type: 'permission_decision', answer: 'allow', value: 'allow', scope: 'once' });
                  }
                }}>
          <I.Check/>Allow once
        </button>
        <button className="aw-btn"
                onClick={() => {
                  // T-9: Allow for this plan → typed permission_decision
                  // with scope=run (entire current run).
                  const AW = (typeof window !== 'undefined' && window.AW) || null;
                  if (AW && typeof AW.send === 'function') {
                    AW.send({ type: 'permission_decision', answer: 'allow', value: 'allow', scope: 'run' });
                  }
                }}>
          Allow for this plan
        </button>
        <span style={{flex:1}}/>
        <button className="aw-btn subtle"><I.More/></button>
        <button className="aw-btn danger"
                onClick={() => {
                  // T-9: Deny → typed permission_decision with scope=deny.
                  // Backend pauses the run pending user action.
                  const AW = (typeof window !== 'undefined' && window.AW) || null;
                  if (AW && typeof AW.send === 'function') {
                    AW.send({ type: 'permission_decision', answer: 'deny', value: 'deny', scope: 'deny' });
                  }
                }}>
          <I.Stop style={{width:11,height:11}}/>Deny
        </button>
      </div>
    </div>
  );
}

function CardExecution() {
  return (
    <div className="aw-card exec running">
      <div className="aw-card-head">
        <span className="aw-card-icon"><I.Play/></span>
        <span className="aw-card-title">Executing plan v2</span>
        <span className="aw-card-state">Step 3 of 6</span>
        <span className="aw-card-source backend"><span className="src-dot"/>Step Runner · live</span>
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
        <button className="aw-btn"
                onClick={() => {
                  // T-4: Pause → typed `pause` command. Backend acks +
                  // forwards through control_queue. Agent honouring is
                  // a follow-up; the wire contract lands now.
                  const AW = (typeof window !== 'undefined' && window.AW) || null;
                  if (AW && typeof AW.send === 'function') AW.send({ type: 'pause' });
                }}>
          <I.Pause style={{width:11,height:11}}/>Pause
        </button>
        <button className="aw-btn danger"
                onClick={() => {
                  // T-4: Stop run → typed `stop_run` command. Backend
                  // cancels the run_task and emits stop_run_result.
                  const AW = (typeof window !== 'undefined' && window.AW) || null;
                  if (AW && typeof AW.send === 'function') AW.send({ type: 'stop_run' });
                }}>
          <I.Stop style={{width:11,height:11}}/>Stop run
        </button>
        <span style={{flex:1}}/>
        <span style={{fontSize:11,color:"var(--tx-3)"}}>Tail traces in <button className="aw-link">Trace</button> · evidence in <button className="aw-link">Recorded</button></span>
      </div>
    </div>
  );
}

function CardLocatorAmbiguity() {
  const [pick, setPick] = useStateLlm("hero");
  const [showDiag, setShowDiag] = useStateLlm(false);
  const cands = [
    { id:"header", t:'Header CTA — "Get started"', scope:"nav.ws-topnav .cta",         conf:0.92, risk:"safe-read",
      preview:'getByRole(\'link\', { name: \'Get started\' }).first()',
      diag:'role=link · accessible name unique · stable across renders · no positional fallback',
    },
    { id:"hero",   t:'Hero CTA — "Get started"',   scope:".ws-hero a.btn.primary",     conf:0.71, risk:"medium",
      preview:'page.locator(\'.ws-hero a.btn.primary\')',
      diag:'class-based · 1 match in scope · navigates to /signup · permission required to actuate',
    },
    { id:"starter",t:'Starter plan CTA — "Get started"', scope:".ws-plan:nth(1) .ws-plan-cta", conf:0.34, risk:"medium",
      preview:'page.getByText(\'Get started\').nth(2)',
      diag:'positional nth() · breaks if a plan card is added or reordered',
    },
  ];
  const pickedIdx = cands.findIndex(c => c.id === pick);
  const picked = cands[pickedIdx];
  return (
    <div className="aw-card locator blocking">
      <div className="aw-card-head">
        <span className="aw-card-icon"><I.Target/></span>
        <span className="aw-card-title">Choose the correct "Get started" button</span>
        <span className="aw-card-state">Execution paused</span>
        <span className="aw-card-source backend"><span className="src-dot"/>Step Runner · 3 matches</span>
      </div>
      <div className="aw-card-body" style={{padding:"14px 14px 12px"}}>
        <p style={{margin:"0 0 12px", fontSize:12.5, color:"var(--tx-2)"}}>
          Three visible matches were found while resolving <span style={{fontFamily:"var(--ff-mono)",color:"var(--tx)"}}>stp_d8e2</span>.
          I won't pick on your behalf — choose one, ask me to refine the locator, or narrow the scope.
        </p>
        <div style={{display:"flex", flexDirection:"column", gap:8}}>
          {cands.map((c,i) => (
            <div key={c.id} className={"aw-cand " + (pick === c.id ? "selected" : "")} onClick={() => setPick(c.id)}>
              <span className="aw-cand-num">{i+1}</span>
              <div className="aw-cand-main">
                <div style={{display:"flex", alignItems:"center", gap:8, justifyContent:"space-between"}}>
                  <span className="aw-cand-title">{c.t}</span>
                  <Conf level={c.conf}/>
                </div>
                <div className="aw-cand-meta">
                  <span>scope: <span style={{fontFamily:"var(--ff-mono)", color:"var(--tx-2)"}}>{c.scope}</span></span>
                  <span>·</span>
                  <span>risk: <span className={"aw-badge-i " + (c.risk === "safe-read" ? "ok" : "warn")}><span className="ldot"/>{c.risk}</span></span>
                </div>
                <div className="aw-cand-loc">{c.preview}</div>
                {showDiag && (
                  <div style={{marginTop:6, fontSize:11, color:"var(--tx-3)", lineHeight:1.5}}>
                    <span style={{color:"var(--tx-4)",fontWeight:600,letterSpacing:"0.04em",fontSize:9.5,textTransform:"uppercase"}}>Diagnostics</span><br/>
                    {c.diag}
                  </div>
                )}
                <div className="aw-cand-actions">
                  <button className="aw-btn" onClick={(e) => { e.stopPropagation(); setPick(c.id); }}>
                    <I.Check/> {pick === c.id ? "Selected" : "Select"}
                  </button>
                  <button className="aw-btn subtle" onClick={(e) => {
                    // T-10: per-candidate Highlight → typed highlight_locator.
                    // Backend routes onto agent control_queue (T-10a).
                    e.stopPropagation();
                    const AW = (typeof window !== 'undefined' && window.AW) || null;
                    if (AW && typeof AW.send === 'function') {
                      AW.send({ type: 'highlight_locator', candidate_id: c.id, duration_ms: 1500 });
                    }
                  }}>
                    <I.Eye/>Highlight
                  </button>
                </div>
              </div>
            </div>
          ))}
        </div>
        <button className="aw-link" style={{marginTop:10, fontSize:11.5}}
                onClick={() => setShowDiag(!showDiag)}>
          {showDiag ? "Hide" : "Show"} per-candidate diagnostics
        </button>
      </div>
      <div className="aw-card-foot" style={{flexWrap:"wrap"}}>
        <span style={{fontSize:11.5, color:"var(--tx-3)"}}>
          Selected: <b style={{color:"var(--tx)"}}>candidate {pickedIdx+1}</b> — {picked.t}
        </span>
        <span style={{flex:1}}/>
        <button className="aw-btn"
                onClick={() => {
                  // T-10: Ask LLM for better locator → typed improve_locator.
                  const AW = (typeof window !== 'undefined' && window.AW) || null;
                  if (AW && typeof AW.send === 'function') {
                    AW.send({ type: 'improve_locator', step_id: 'stp_d8e2' });
                  }
                }}>
          <I.Spark/>Ask LLM for better locator
        </button>
        <button className="aw-btn"
                onClick={() => {
                  // T-10: Change scope → prompt for scope hint then send
                  // typed change_locator_scope. Accepted shapes per
                  // server.py:1046 are "broader" / "narrower" / free text.
                  const AW = (typeof window !== 'undefined' && window.AW) || null;
                  if (!AW || typeof AW.send !== 'function') return;
                  const scope = (typeof window !== 'undefined' && typeof window.prompt === 'function')
                    ? window.prompt('Change locator scope (broader / narrower / or free text):', 'narrower')
                    : 'narrower';
                  if (scope == null) return;
                  AW.send({ type: 'change_locator_scope', step_id: 'stp_d8e2', scope: String(scope) });
                }}>
          Change scope
        </button>
        <button className="aw-btn danger"
                onClick={() => {
                  // T-10: Stop the locator step → typed stop_run.
                  const AW = (typeof window !== 'undefined' && window.AW) || null;
                  if (AW && typeof AW.send === 'function') AW.send({ type: 'stop_run' });
                }}>
          <I.Stop style={{width:11,height:11}}/>Stop
        </button>
        <button className="aw-btn primary"
                onClick={() => {
                  // T-10: Use candidate N → typed option_selected with the
                  // picked candidate id. Backend control_queue routes it
                  // into the locator resolution path.
                  const AW = (typeof window !== 'undefined' && window.AW) || null;
                  if (AW && typeof AW.send === 'function') {
                    AW.send({ type: 'option_selected', value: pick, answer: pick, step_id: 'stp_d8e2' });
                  }
                }}>
          <I.Check/>Use candidate {pickedIdx+1}
        </button>
      </div>
    </div>
  );
}

function CardRecovery() {
  return (
    <div className="aw-card recover blocking">
      <div className="aw-card-head">
        <span className="aw-card-icon"><I.Alert/></span>
        <span className="aw-card-title">Recovery needed · step 5</span>
        <span className="aw-card-state">Run blocked</span>
        <span className="aw-card-source backend"><span className="src-dot"/>Debug Agent · 1 attempt left</span>
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
        <button className="aw-btn primary"
                onClick={() => {
                  // T-11: Apply LLM repair → typed correction with a
                  // repair hint. Backend correction handler routes
                  // through control_queue; agent re-prompts the model.
                  const AW = (typeof window !== 'undefined' && window.AW) || null;
                  if (AW && typeof AW.send === 'function') {
                    AW.send({ type: 'correction', message: 'Apply LLM repair for the failed step.', repair: 'llm', step_id: 'stp_e1f4' });
                  }
                }}>
          <I.Spark/>Apply LLM repair
        </button>
        <button className="aw-btn"
                onClick={() => {
                  // T-11: Retry as-is → new typed cmd retry_as_is.
                  const AW = (typeof window !== 'undefined' && window.AW) || null;
                  if (AW && typeof AW.send === 'function') {
                    AW.send({ type: 'retry_as_is', step_id: 'stp_e1f4' });
                  }
                }}>
          <I.Retry style={{width:12,height:12}}/>Retry as-is
        </button>
        <button className="aw-btn"
                onClick={() => {
                  // T-11: Choose another locator → flip state so the
                  // locator-ambiguity card renders, letting the user
                  // pick a different candidate without losing context.
                  window.dispatchEvent(new CustomEvent('aw:set', { detail: { state: 'locator' } }));
                }}>
          Choose another locator
        </button>
        <span style={{flex:1}}/>
        <button className="aw-btn subtle"><I.More/></button>
        <button className="aw-btn danger"
                onClick={() => {
                  // T-11: Stop run → typed stop_run.
                  const AW = (typeof window !== 'undefined' && window.AW) || null;
                  if (AW && typeof AW.send === 'function') AW.send({ type: 'stop_run' });
                }}>
          <I.Stop style={{width:11,height:11}}/>Stop run
        </button>
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
        <span className="aw-card-state">6 / 6 recorded</span>
        <span className="aw-card-source backend"><span className="src-dot"/>Backend event · run_completed</span>
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
        <button className="aw-btn primary"
                onClick={() => {
                  // T-5: Replay all → typed replay_all command. Backend
                  // server.py:547 already handles this and streams
                  // per-step replay_result events.
                  const AW = (typeof window !== 'undefined' && window.AW) || null;
                  if (AW && typeof AW.send === 'function') AW.send({ type: 'replay_all' });
                }}>
          <I.Repeat/>Replay all
        </button>
        <button className="aw-btn"
                onClick={() => {
                  // T-5: Save as suite → prompt for a name, then typed
                  // save_session. Backend writes the spec under the
                  // workspace and emits save_result.
                  const AW = (typeof window !== 'undefined' && window.AW) || null;
                  if (!AW || typeof AW.send !== 'function') return;
                  const name = (typeof window !== 'undefined' && typeof window.prompt === 'function')
                    ? window.prompt('Save suite as:', 'autoworkbench-session')
                    : 'autoworkbench-session';
                  if (name == null) return;
                  AW.send({ type: 'save_session', name: String(name).trim() || 'autoworkbench-session' });
                }}>
          <I.Branch/>Save as suite
        </button>
        <button className="aw-btn"
                onClick={() => {
                  // T-5: Open code → switch the active tab to "code".
                  // Dispatched through aw:set so useTweaks picks it up.
                  window.dispatchEvent(new CustomEvent('aw:set', { detail: { tab: 'code' } }));
                }}>
          <I.Code/>Open code
        </button>
        <button className="aw-btn subtle"
                onClick={() => {
                  // T-5: Download trace → typed download_trace command.
                  // Backend acks only for now; bundler is a follow-up.
                  const AW = (typeof window !== 'undefined' && window.AW) || null;
                  if (AW && typeof AW.send === 'function') AW.send({ type: 'download_trace' });
                }}>
          <I.Download/>Download trace
        </button>
      </div>
    </div>
  );
}

function CardOffline() {
  return (
    <div className="aw-card recover blocking">
      <div className="aw-card-head">
        <span className="aw-card-icon"><I.Plug/></span>
        <span className="aw-card-title">Backend unavailable</span>
        <span className="aw-card-state">Holding state</span>
        <span className="aw-card-source backend"><span className="src-dot"/>ws disconnected · 14s</span>
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
        <button className="aw-btn primary"
                onClick={() => {
                  // T-6: Reconnect now → client-side WS retry. Bypasses
                  // the current backoff timer and reopens immediately.
                  const AW = (typeof window !== 'undefined' && window.AW) || null;
                  if (AW && typeof AW.reconnect === 'function') AW.reconnect();
                }}>
          <I.Sync/>Reconnect now
        </button>
        <button className="aw-btn"
                onClick={() => {
                  // T-6: View connection log → surface a quick summary
                  // pulled from window.AW. A real log viewer modal is a
                  // follow-up; this keeps the action honest by showing
                  // exactly what the transport layer holds today.
                  const AW = (typeof window !== 'undefined' && window.AW) || null;
                  const lines = [
                    'connection: ' + (AW && AW.connection),
                    'last event: ' + (AW && AW.lastEvent && AW.lastEvent.type),
                    'endpoint registry: ' + (AW && AW.endpoints && AW.endpoints.active_id),
                  ].join('\n');
                  if (typeof window !== 'undefined' && typeof window.alert === 'function') window.alert(lines);
                }}>
          View connection log
        </button>
        <button className="aw-btn subtle"
                onClick={() => {
                  // T-6: Switch endpoint → typed switch_endpoint command.
                  // Sprint 7 registry only carries the local endpoint, so
                  // the backend acks with already_active until the
                  // registry grows.
                  const AW = (typeof window !== 'undefined' && window.AW) || null;
                  if (!AW || typeof AW.send !== 'function') return;
                  const active = (AW.endpoints && AW.endpoints.active_id) || 'local';
                  AW.send({ type: 'switch_endpoint', endpoint_id: active });
                }}>
          Switch endpoint
        </button>
      </div>
    </div>
  );
}

function CardSchemaError() {
  return (
    <div className="aw-card warn blocking">
      <div className="aw-card-head">
        <span className="aw-card-icon"><I.Alert/></span>
        <span className="aw-card-title">Schema validation failed</span>
        <span className="aw-card-state">Nothing executed</span>
        <span className="aw-card-source llm"><span className="src-dot"/>llm_response_invalid</span>
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
        <button className="aw-btn primary"
                onClick={() => {
                  // T-7: Ask LLM to repair → typed correction with a
                  // repair hint. Backend correction handler routes
                  // through control_queue; the agent re-prompts the
                  // model when it sees the repair flag.
                  const AW = (typeof window !== 'undefined' && window.AW) || null;
                  if (AW && typeof AW.send === 'function') {
                    AW.send({ type: 'correction', message: 'Repair the plan: schema validation failed.', repair: 'schema' });
                  }
                }}>
          <I.Sync/>Ask LLM to repair plan
        </button>
        <button className="aw-btn"
                onClick={() => {
                  // T-7: Edit plan manually → focus the composer with a
                  // prefix so the user can hand-edit the plan.
                  const ta = document.querySelector('textarea.aw-composer-input');
                  if (ta) { ta.focus(); ta.value = 'Repair plan: '; ta.setSelectionRange(ta.value.length, ta.value.length); }
                }}>
          Edit plan manually
        </button>
        <button className="aw-btn subtle"
                onClick={() => {
                  // T-7: Open raw response → surface the last typed
                  // envelope the transport saw. A dedicated viewer is a
                  // follow-up; this keeps the action honest.
                  const AW = (typeof window !== 'undefined' && window.AW) || null;
                  const last = (AW && AW.lastEvent) || null;
                  const text = last ? JSON.stringify(last, null, 2) : '(no event captured yet)';
                  if (typeof window !== 'undefined' && typeof window.alert === 'function') window.alert(text);
                }}>
          Open raw response
        </button>
      </div>
    </div>
  );
}

// — Additional state cards: no browser, api key missing, OTP, paid E2E pending ——

function CardNoBrowser() {
  return (
    <div className="aw-card recover blocking">
      <div className="aw-card-head">
        <span className="aw-card-icon"><I.Globe/></span>
        <span className="aw-card-title">No browser session attached</span>
        <span className="aw-card-state">Cannot start run</span>
        <span className="aw-card-source backend"><span className="src-dot"/>Step Runner · idle</span>
      </div>
      <div className="aw-card-body">
        <p style={{margin:"0 0 6px"}}>Backend is connected, but there is no Playwright browser context to drive. Plan was drafted but cannot be executed.</p>
        <ul className="aw-dotlist">
          <li className="no">no active context · <span style={{fontFamily:"var(--ff-mono)"}}>browserType: chromium</span> requested</li>
          <li>page intelligence cache available · 14s old</li>
          <li>safe actions: launch new context, attach existing, or keep plan as draft</li>
        </ul>
      </div>
      <div className="aw-card-foot">
        <button className="aw-btn primary"
                onClick={() => {
                  // T-12: Launch chromium → typed cmd. Backend calls
                  // browser.launch_browser and emits browser_ready or
                  // BROWSER_LAUNCH_FAILED.
                  const AW = (typeof window !== 'undefined' && window.AW) || null;
                  if (AW && typeof AW.send === 'function') AW.send({ type: 'launch_chromium' });
                }}>
          <I.Play/>Launch chromium
        </button>
        <button className="aw-btn"
                onClick={() => {
                  // T-12: Attach existing tab → prompt for URL then
                  // send typed attach_existing_tab. Backend acks only.
                  const AW = (typeof window !== 'undefined' && window.AW) || null;
                  if (!AW || typeof AW.send !== 'function') return;
                  const url = (typeof window !== 'undefined' && typeof window.prompt === 'function')
                    ? window.prompt('URL of the tab to attach:', 'https://acme.dev/pricing')
                    : '';
                  if (url == null) return;
                  AW.send({ type: 'attach_existing_tab', url: String(url) });
                }}>
          Attach existing tab…
        </button>
        <button className="aw-btn subtle"
                onClick={() => {
                  // T-12: Keep plan as draft → typed defer cmd.
                  const AW = (typeof window !== 'undefined' && window.AW) || null;
                  if (AW && typeof AW.send === 'function') AW.send({ type: 'keep_plan_as_draft' });
                }}>
          Keep plan as draft
        </button>
      </div>
    </div>
  );
}

function CardApiKey() {
  return (
    <div className="aw-card warn blocking">
      <div className="aw-card-head">
        <span className="aw-card-icon"><I.Key/></span>
        <span className="aw-card-title">LLM provider key missing</span>
        <span className="aw-card-state">No model calls possible</span>
        <span className="aw-card-source backend"><span className="src-dot"/>config · auth</span>
      </div>
      <div className="aw-card-body">
        <p style={{margin:"0 0 6px"}}>The Main Orchestrator agent needs a model provider key to draft plans or repairs. Backend lifecycle continues to flow but no new LLM calls can be made.</p>
        <div className="aw-fail-grid">
          <div className="k">missing</div> <div className="v mono">ANTHROPIC_API_KEY <span style={{color:"var(--tx-3)"}}>or</span> OPENAI_API_KEY</div>
          <div className="k">policy</div>  <div className="v">workspace · Acme QA · keys not in env</div>
          <div className="k">impact</div>  <div className="v">planning, clarification, repair, codegen reviewer all paused</div>
        </div>
      </div>
      <div className="aw-card-foot">
        <button className="aw-btn primary"
                onClick={() => {
                  // T-13: Add key → prompt for the OpenAI key, then
                  // typed add_api_key. Backend writes to process env
                  // and flips _BOOT_STATE.api_key_ok. The key never
                  // appears on the wire beyond this single outbound
                  // send (backend never echoes it back).
                  const AW = (typeof window !== 'undefined' && window.AW) || null;
                  if (!AW || typeof AW.send !== 'function') return;
                  const key = (typeof window !== 'undefined' && typeof window.prompt === 'function')
                    ? window.prompt('Paste OpenAI API key (starts with sk-):', '')
                    : '';
                  if (!key) return;
                  AW.send({ type: 'add_api_key', provider: 'openai', key: String(key).trim() });
                }}>
          <I.Key/>Add key…
        </button>
        <button className="aw-link" style={{marginLeft:4}}
                onClick={() => {
                  // T-13: Use shared workspace key → typed cmd.
                  const AW = (typeof window !== 'undefined' && window.AW) || null;
                  if (AW && typeof AW.send === 'function') AW.send({ type: 'use_workspace_key' });
                }}>
          Use shared workspace key
        </button>
        <span style={{flex:1}}/>
        <span className="aw-card-foot-hint"><I.Lock style={{width:11,height:11}}/>Keys are stored encrypted per workspace</span>
      </div>
    </div>
  );
}

function CardOtp() {
  return (
    <div className="aw-card perm needs-input">
      <div className="aw-card-head">
        <span className="aw-card-icon"><I.Key/></span>
        <span className="aw-card-title">Human input required · OTP / 2FA</span>
        <span className="aw-card-state" style={{background:"var(--ylw-soft)",color:"#7A5A0E",borderColor:"#ECD89A"}}>Awaiting you</span>
        <span className="aw-card-source backend"><span className="src-dot"/>Step Runner · human_input</span>
      </div>
      <div className="aw-card-body">
        <p style={{margin:"0 0 8px"}}>Step 4 ran into a one-time code prompt at <span style={{fontFamily:"var(--ff-mono)"}}>acme.dev/auth/otp</span>. Backend will not type values it cannot derive from your test data. Provide the code or skip the step.</p>
        <div style={{display:"flex",gap:8,alignItems:"center"}}>
          <input type="text" placeholder="6-digit code"
                 style={{flex:1,maxWidth:180,padding:"7px 10px",fontFamily:"var(--ff-mono)",fontSize:14,
                         letterSpacing:"0.2em",border:"1px solid var(--br)",borderRadius:8,
                         background:"var(--bg-card)",outline:"none"}}/>
          <span style={{fontSize:11.5,color:"var(--tx-3)"}}>received via Authenticator app</span>
        </div>
        <div style={{marginTop:10,fontSize:11.5,color:"var(--tx-3)"}}>Backend redacts the value from screenshots and trace. <button className="aw-link">View redaction policy</button></div>
      </div>
      <div className="aw-card-foot">
        <button className="aw-btn primary"><I.Send/>Submit code</button>
        <button className="aw-btn"><I.Skip style={{width:11,height:11}}/>Skip this step</button>
        <button className="aw-btn subtle">Pause run for manual login</button>
      </div>
    </div>
  );
}

function CardE2EPending() {
  return (
    <div className="aw-card warn">
      <div className="aw-card-head">
        <span className="aw-card-icon"><I.Branch/></span>
        <span className="aw-card-title">Paid E2E suite pending final acceptance</span>
        <span className="aw-card-state" style={{background:"var(--blu-soft)",color:"var(--blu)",borderColor:"#D8E3F2"}}>Not run yet</span>
        <span className="aw-card-source backend"><span className="src-dot"/>scheduled · nightly</span>
      </div>
      <div className="aw-card-body">
        <p style={{margin:"0 0 6px"}}>
          The local plan recorded cleanly, but the paid end-to-end suite (real card, real signup, real Stripe) has not been run for this commit.
          <b> Frontend will not mark this work accepted</b> — that gate is owned by the backend after the nightly E2E run.
        </p>
        <ul className="aw-dotlist">
          <li>scheduled <span style={{fontFamily:"var(--ff-mono)"}}>02:00 UTC</span> · ~3h 22m from now</li>
          <li>cost cap <span style={{fontFamily:"var(--ff-mono)"}}>$4.20</span> per run · uses real Stripe test cards</li>
          <li>completion will arrive as <span style={{fontFamily:"var(--ff-mono)"}}>e2e_pending → e2e_passed</span> events</li>
        </ul>
      </div>
      <div className="aw-card-foot">
        <button className="aw-btn"><I.Bolt/>Trigger E2E now ($4.20)</button>
        <button className="aw-btn subtle">Notify me when E2E completes</button>
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
  const [sending, setSending] = React.useState(false);
  const [sent, setSent] = React.useState(false);
  const [error, setError] = React.useState(null);
  const inputRef = React.useRef(null);
  // T-2: real send through window.AW (set up by transport.jsx). Falls back to
  // the original mock animation when the backend is not reachable so the
  // standalone harness keeps working.
  const onSend = () => {
    if (sending) return;
    const ta = inputRef.current;
    const text = ((ta && ta.value) || "").trim();
    if (!text) return;
    setSending(true);
    setError(null);
    const finish = (ok) => {
      setSending(false);
      if (ok) {
        if (ta) ta.value = "";
        setSent(true);
        setTimeout(() => setSent(false), 1200);
      }
    };
    const AW = (typeof window !== "undefined" && window.AW) || null;
    if (AW && typeof AW.send === "function") {
      // PRD 05 §498-887 (Expected Outcome Capture v1) requires click-like
      // intents to carry an expected_outcome.type. We do not know what
      // the user wants in advance so we ship "not_sure" which the agent
      // treats as a valid placeholder per the spec's enum list.
      const ok = AW.send({
        type: "llm_run",
        steps: [{ intent: text, expected_outcome: { type: "not_sure" } }],
      });
      if (ok) {
        setTimeout(() => finish(true), 350);
      } else {
        setError("Not connected. Reconnecting…");
        setTimeout(() => finish(false), 350);
      }
    } else {
      // No transport (offline / static fixture). Keep the original mock UX.
      setTimeout(() => finish(true), 450);
    }
  };
  const onKey = (e) => {
    if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); onSend(); }
  };
  return (
    <div className="aw-composer">
      <div className="aw-composer-box">
        <div className="aw-composer-actions">
          <span className="aw-context-chip"><I.Globe/> /pricing</span>
          <span className="aw-context-chip"><I.Target/> 2 selected</span>
          <span className="aw-context-chip"><I.Doc/> users.csv</span>
          <button className="aw-btn subtle" style={{padding:"2px 5px",fontSize:10.5,height:18}}>
            <I.Plus/>Add
          </button>
        </div>
        <textarea ref={inputRef} className="aw-composer-input" rows={1}
                  placeholder="Reply, refine the plan, or paste a step…"
                  defaultValue=""
                  onKeyDown={onKey}></textarea>
        <div className="aw-composer-actions" style={{justifyContent:"space-between"}}>
          <div style={{display:"flex", gap:2, alignItems:"center"}}>
            <button className="aw-icon-btn" title="Attach" data-tip="Attach"><I.Paperclip/></button>
            <button className="aw-icon-btn" title="Pick element" data-tip="Pick element"><I.Mouse/></button>
            <button className="aw-icon-btn" title="Attach screenshot" data-tip="Attach screenshot"><I.Camera/></button>
            <span style={{fontSize:10.5, color:"var(--tx-4)", marginLeft:6}}>complete-llm · gpt-class</span>
          </div>
          <button className={"aw-btn primary aw-send " + (sending ? "sending " : "") + (sent ? "sent" : "")}
                  style={{padding:"5px 10px",fontSize:11.5,height:24,minWidth:74,justifyContent:"center"}}
                  onClick={onSend}
                  disabled={sending}>
            {sending ? (<><span className="aw-send-spin"/>Sending</>)
             : sent ? (<><I.Check/>Sent</>)
             : (<><I.Send/>Send<span className="aw-kbd">↵</span></>)}
          </button>
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

      {state === "nobrowser" && (<>
        <Sys time="11:42">
          <p>I have your plan ready, but I can't find a browser to run it against.</p>
        </Sys>
        <CardNoBrowser/>
      </>)}

      {state === "apikey" && (<>
        <Sys time="11:42">
          <p>I can't reach a model provider — the workspace has no key configured.</p>
        </Sys>
        <CardApiKey/>
      </>)}

      {state === "otp" && (<>
        <Sys time="11:46">
          <p>Step 4 navigated to a login flow that asks for a 2FA code.</p>
        </Sys>
        <CardOtp/>
      </>)}

      {state === "e2e" && (<>
        <Bubble time="11:49">Apply the repair.</Bubble>
        <Sys time="11:49"><p>Repair applied, step recorded, code updated. Local run finished — the paid E2E suite is still pending.</p></Sys>
        <CardCompleted/>
        <CardE2EPending/>
      </>)}
    </div>
  );
}

window.LlmThread = LlmThread;
window.Composer = Composer;
