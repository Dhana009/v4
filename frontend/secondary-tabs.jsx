// secondary-tabs.jsx — Steps / Recorded / Code / Trace

// — STEPS —————————————————————————————————————————————

function ManualBuilder() {
  const [action, setAction] = React.useState("click");
  const [assertion, setAssertion] = React.useState("visible");
  const [expected, setExpected] = React.useState("");
  const [picked, setPicked] = React.useState({
    name: "\"Start free trial\" button",
    role: "link", text: "Start free trial",
    cand: [
      { id: "c1", loc: "getByRole('link', { name: 'Start free trial' })", conf: 0.92 },
      { id: "c2", loc: ".ws-plan.featured a.ws-plan-cta", conf: 0.71 },
    ],
    chosen: "c1",
    matched: 1,
  });
  const [picking, setPicking] = React.useState(false);

  const actions = ["click","fill","press","hover","select option","check","upload file","submit","navigate"];
  const assertions = ["visible","hidden","enabled","disabled","has text","exact text","has value","checked","url matches","title matches","count equals","attribute equals"];
  const needsExpected = ["fill","press","select option","has text","exact text","has value","url matches","title matches","count equals","attribute equals"].includes(assertion) || ["fill","press","select option"].includes(action);

  return (
    <div className="aw-manual">
      <div className="aw-manual-head">
        <span className="aw-manual-eyebrow">Manual mode · deterministic</span>
        <span style={{flex:1}}/>
        <span className="aw-badge-i outline" data-tip="LLM is only used if you explicitly ask">
          <I.Shield style={{width:11,height:11,marginRight:3}}/> no LLM by default
        </span>
      </div>

      {/* Pick element */}
      <div className="aw-manual-row">
        <span className="aw-manual-label">Element</span>
        {picked ? (
          <div className="aw-manual-picked">
            <I.Target style={{width:12,height:12,color:"var(--vio)"}}/>
            <span className="aw-manual-picked-name">{picked.name}</span>
            <span className="aw-manual-picked-meta">role: <b>{picked.role}</b> · text: "{picked.text}"</span>
            <span style={{flex:1}}/>
            <button className="aw-icon-btn" title="Re-pick" data-tip="Re-pick element"
                    onClick={() => setPicking(true)}><I.Target/></button>
          </div>
        ) : (
          <button className="aw-btn primary" onClick={() => setPicking(true)}>
            <I.Mouse/>Pick an element on the page
          </button>
        )}
      </div>

      {/* Locator candidates */}
      {picked && (
        <div className="aw-manual-row">
          <span className="aw-manual-label">Locator</span>
          <div className="aw-manual-cands">
            {picked.cand.map(c => (
              <label key={c.id}
                className={"aw-manual-cand " + (picked.chosen === c.id ? "active" : "")}
                onClick={() => setPicked({...picked, chosen: c.id})}>
                <input type="radio" checked={picked.chosen === c.id} readOnly
                  style={{accentColor:"var(--acc)"}}/>
                <span className="aw-manual-cand-loc">{c.loc}</span>
                <span className={"aw-conf " + (c.conf>=0.8?"high":c.conf>=0.5?"med":"low")}>
                  <i/><i/><i/>
                </span>
              </label>
            ))}
          </div>
        </div>
      )}

      {/* Validate */}
      {picked && (
        <div className="aw-manual-row">
          <span className="aw-manual-label">Validate</span>
          <span className="aw-badge-i ok"><span className="ldot"/>matches {picked.matched} element · backend-validated</span>
          <span style={{flex:1}}/>
          <button className="aw-link" data-tip="Re-run Step Runner validation">Re-validate</button>
        </div>
      )}

      {/* Action */}
      <div className="aw-manual-row">
        <span className="aw-manual-label">Action</span>
        <select className="aw-manual-select" value={action} onChange={(e) => setAction(e.target.value)}>
          {actions.map(a => <option key={a} value={a}>{a}</option>)}
        </select>
      </div>

      {/* Assertion */}
      <div className="aw-manual-row">
        <span className="aw-manual-label">Assert</span>
        <select className="aw-manual-select" value={assertion} onChange={(e) => setAssertion(e.target.value)}>
          {assertions.map(a => <option key={a} value={a}>{a}</option>)}
        </select>
        {needsExpected && (
          <input className="aw-manual-input" placeholder="expected value…"
            value={expected} onChange={(e) => setExpected(e.target.value)}/>
        )}
      </div>

      {/* Footer */}
      <div className="aw-manual-foot">
        <button className="aw-btn primary"><I.Plus/>Add as step</button>
        <button className="aw-btn"><I.Play/>Run now</button>
        <span style={{flex:1}}/>
        <button className="aw-link" data-tip="Send this step to the LLM if you want help">
          <I.Spark style={{width:11,height:11,marginRight:3,verticalAlign:"-1px"}}/>
          Ask LLM for help
        </button>
      </div>
      <div className="aw-manual-note">
        Backend validates locator + action. Step is recorded only after successful execution. Code is emitted by backend.
      </div>
    </div>
  );
}

function StepFoot({ id, version = "v1", lastRun = "never", canDup = true }) {
  const [open, setOpen] = React.useState(false);
  return (
    <div className="aw-step-foot">
      <span className="aw-step-foot-meta">
        <span className="aw-step-foot-id" data-tip="Stable backend ID" data-tip-pos="bottom-right">{id}</span>
        <span className="aw-step-foot-sep">·</span>
        <span>{version}</span>
        <span className="aw-step-foot-sep">·</span>
        <span>last run {lastRun}</span>
      </span>
      <span className="aw-spacer"/>
      {canDup && (
        <button className="aw-icon-btn" title="Duplicate" data-tip="Duplicate step"><I.Copy/></button>
      )}
      <div className="aw-dock-wrap">
        <button className={"aw-icon-btn " + (open ? "active" : "")}
                onClick={() => setOpen(!open)} title="More options" data-tip="More options"><I.More/></button>
        {open && (
          <>
            <div className="aw-dock-scrim" onClick={() => setOpen(false)}/>
            <div className="aw-dock-menu" role="menu" style={{ minWidth: 210 }} data-tip-pos="bottom-right">
              <button className="aw-dock-opt" onClick={() => setOpen(false)}>
                <I.Play/>
                <span className="aw-dock-opt-main">
                  <span className="aw-dock-opt-t">Run this step</span>
                  <span className="aw-dock-opt-d">Send through LLM now</span>
                </span>
              </button>
              <button className="aw-dock-opt" onClick={() => setOpen(false)}>
                <I.Target/>
                <span className="aw-dock-opt-main">
                  <span className="aw-dock-opt-t">Re-pick element</span>
                  <span className="aw-dock-opt-d">Re-attach DOM target</span>
                </span>
              </button>
              <button className="aw-dock-opt" onClick={() => setOpen(false)}>
                <I.Spark/>
                <span className="aw-dock-opt-main">
                  <span className="aw-dock-opt-t">Improve locator</span>
                  <span className="aw-dock-opt-d">Ask LLM for a stronger selector</span>
                </span>
              </button>
              <div className="aw-dock-menu-sep"/>
              <button className="aw-dock-opt" onClick={() => setOpen(false)}>
                <I.Eye/>
                <span className="aw-dock-opt-main">
                  <span className="aw-dock-opt-t">View step JSON</span>
                  <span className="aw-dock-opt-d">Inspect raw step payload</span>
                </span>
              </button>
              <button className="aw-dock-opt" onClick={() => setOpen(false)}>
                <I.Skip/>
                <span className="aw-dock-opt-main">
                  <span className="aw-dock-opt-t">Skip in next run</span>
                  <span className="aw-dock-opt-d">Don't include this step</span>
                </span>
              </button>
              <button className="aw-dock-opt" onClick={() => setOpen(false)} style={{ color: "var(--red)" }}>
                <I.X/>
                <span className="aw-dock-opt-main">
                  <span className="aw-dock-opt-t">Delete step</span>
                  <span className="aw-dock-opt-d">Removes from this plan</span>
                </span>
              </button>
            </div>
          </>
        )}
      </div>
    </div>
  );
}

const STEP_STATUS = {
  ok: { label: "Ready · strong locator", count: 1 },
  weak: { label: "Weak locator", count: 1 },
  section: { label: "Section step", count: 1 },
  blocked: { label: "Blocked · missing data", count: 1 },
  wrongPage: { label: "Wrong current page", count: 1 }
};

function StepsTab({ mode = "llm", setMode = () => {} }) {
  const [q, setQ] = React.useState("");
  const [filterOpen, setFilterOpen] = React.useState(false);
  const filterTriggerRef = React.useRef(null);
  const [show, setShow] = React.useState({ ok: true, weak: true, section: true, blocked: true, wrongPage: true });
  const listRef = React.useRef(null);
  const [visibleCount, setVisibleCount] = React.useState(5);
  const [extraSteps, setExtraSteps] = React.useState([]);
  const [picking, setPicking] = React.useState(false);
  const [liveSteps, setLiveSteps] = React.useState([]);
  React.useEffect(() => {
    const AW = (typeof window !== 'undefined' && window.AW) || null;
    if (!AW || typeof AW.on !== 'function') return;
    const unsubs = [];
    unsubs.push(AW.on('plan_ready', (env) => {
      const p = (env && (env.payload || env)) || {};
      const steps = Array.isArray(p.steps) ? p.steps : [];
      setLiveSteps(steps.map((s, i) => ({ id: s.id || ('stp_' + String(i + 1).padStart(3, '0')), title: s.description || s.title || String(s), status: 'pending' })));
    }));
    unsubs.push(AW.on('step_executing', (env) => {
      const p = (env && (env.payload || env)) || {};
      const sid = p.step_id || p.id;
      setLiveSteps(prev => prev.map(s => s.id === sid ? { ...s, status: 'executing' } : s).concat(prev.find(s => s.id === sid) ? [] : [{ id: sid || ('stp_live_' + Date.now()), title: p.description || p.title || sid || 'Executing…', status: 'executing' }]));
    }));
    unsubs.push(AW.on('step_recorded', (env) => {
      const p = (env && (env.payload || env)) || {};
      const sid = p.step_id || p.id;
      setLiveSteps(prev => prev.map(s => s.id === sid ? { ...s, status: 'ok', duration: p.duration_ms } : s));
    }));
    return () => unsubs.forEach(u => u && u());
  }, []);

  const fire = () => {};  // toast removed per design feedback — confirmations are inline now
  // expose so inline buttons in step rows can call it
  const link = (msg) => (e) => { e.preventDefault(); fire(msg); };

  const addStep = () => {
    const n = extraSteps.length + 6;
    const id = "stp_" + String(n).padStart(3, "0");
    setExtraSteps([...extraSteps, {
      id,
      title: "New step · describe what to assert or perform",
      status: "ok",
    }]);
    fire(`Added ${id} — describe it or pick an element`, "ok");
  };
  const togglePick = () => {
    setPicking((p) => {
      const next = !p;
      fire(next ? "Pick mode active · click an element on the page" : "Pick mode cancelled", next ? "info" : "ok");
      return next;
    });
  };

  React.useEffect(() => {
    if (!listRef.current) return;
    const rows = listRef.current.querySelectorAll(".aw-step-row");
    let visible = 0;
    rows.forEach((r) => {
      const title = (r.dataset.title || "").toLowerCase();
      const st = r.dataset.status || "";
      const matchesQ = !q || title.includes(q.toLowerCase());
      const matchesS = !!show[st];
      const showRow = matchesQ && matchesS;
      r.style.display = showRow ? "" : "none";
      if (showRow) visible++;
    });
    setVisibleCount(visible);
  }, [q, show]);

  const activeFilters = Object.values(show).filter(Boolean).length;
  const allOn = activeFilters === 5;

  if (liveSteps.length > 0) {
    return (
      <div ref={listRef}>
        {mode === "manual" && <ManualBuilder/>}
        <div className="aw-info-strip">
          <I.Info />
          <span>Live steps from backend. {liveSteps.length} step{liveSteps.length !== 1 ? 's' : ''}.</span>
        </div>
        {liveSteps.map((st, i) => {
          const statusMap = { ok: { bg: 'var(--grn)', color: '#fff', badge: 'ok', label: 'recorded' }, executing: { bg: 'var(--acc)', color: '#fff', badge: 'info', label: 'executing…' }, pending: { bg: 'var(--bg-card)', color: 'var(--tx-3)', badge: 'outline', label: 'pending' } };
          const sm = statusMap[st.status] || statusMap.pending;
          return (
            <div key={st.id} className="aw-step-row" data-title={(st.title || '').toLowerCase()} data-status={st.status}>
              <span className="aw-step-handle"><I.Drag /></span>
              <span className="aw-step-idx" style={{ background: sm.bg, color: sm.color }}>{i + 1}</span>
              <div style={{ flex: 1, minWidth: 0 }}>
                <div className="aw-step-title">{st.title}</div>
                <div className="aw-step-meta">
                  <span className={"aw-badge-i " + sm.badge}><span className="ldot" />{sm.label}</span>
                  {st.duration != null && <span>· {st.duration}ms</span>}
                </div>
                <StepFoot id={st.id} version="v1" lastRun={st.status === 'ok' ? 'just now' : 'never'} />
              </div>
            </div>
          );
        })}
      </div>
    );
  }

  return (
    <div ref={listRef}>
      {mode === "manual" && <ManualBuilder/>}
      <div className="aw-list-toolbar">
        <span style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 12 }}>
          <span style={{ color: "var(--tx-3)" }}>{visibleCount === 5 ? "5 steps" : `${visibleCount} of 5`}</span>
          <span style={{ color: "var(--tx-4)" }}>·</span>
          <span style={{ color: "var(--tx-3)" }}>2 ready</span>
          <span style={{ color: "var(--tx-4)" }}>·</span>
          <span style={{ color: "var(--tx-3)" }}>3 blocked</span>
        </span>
        <span className="aw-spacer" />
        <span className="aw-search">
          <I.Search style={{ width: 11, height: 11, color: "var(--tx-3)" }} />
          <input placeholder="Filter…" value={q} onChange={(e) => setQ(e.target.value)} />
          {q && <button className="aw-icon-btn" style={{ width: 16, height: 16, marginLeft: 2 }}
          onClick={() => setQ("")} title="Clear" data-tip="Clear"><I.X style={{ width: 9, height: 9 }} /></button>}
        </span>
        <div className="aw-dock-wrap">
          <button ref={filterTriggerRef}
          className={"aw-btn " + (filterOpen ? "" : "")}
          onClick={() => setFilterOpen(!filterOpen)}
          title="Filter by status" data-tip="Filter by status"
          style={!allOn ? { borderColor: "var(--acc)", color: "var(--acc-2)" } : {}}>
            <I.Filter />
            {!allOn && <span style={{ fontSize: 10.5, fontWeight: 600 }}>{activeFilters}</span>}
          </button>
          <PortalMenu triggerRef={filterTriggerRef} open={filterOpen} onClose={() => setFilterOpen(false)} width={220}>
            <div className="aw-dock-menu-label">Show steps with status</div>
            {Object.entries(STEP_STATUS).map(([key, info]) => (
              <label key={key} className="aw-dock-opt" style={{ cursor: "pointer" }}>
                <input type="checkbox" checked={show[key]}
                  onChange={(e) => setShow({ ...show, [key]: e.target.checked })}
                  style={{ accentColor: "var(--acc)", marginTop: 1 }} />
                <span className="aw-dock-opt-main">
                  <span className="aw-dock-opt-t">{info.label}</span>
                </span>
              </label>
            ))}
            <div className="aw-dock-menu-sep" />
            <button className="aw-dock-opt" onClick={() => setShow({ ok: true, weak: true, section: true, blocked: true, wrongPage: true })}>
              <I.Check />
              <span className="aw-dock-opt-main">
                <span className="aw-dock-opt-t">Show all</span>
              </span>
            </button>
          </PortalMenu>
        </div>
      </div>
      <div className="aw-info-strip">
        <I.Info />
        <span>Display order is cosmetic — stable IDs persist across reorders.</span>
        <span className="aw-spacer" />
        <button className="aw-btn primary" style={{ padding: "4px 10px" }}><I.Play />Run all</button>
        <button className="aw-btn" style={{ padding: "4px 10px" }}><I.Play />Run selected</button>
      </div>

      {/* step 1 */}
      <div className="aw-step-row"
      data-title="Click Most popular tag and confirm it routes to Pro signup"
      data-status="ok">
        <span className="aw-step-handle"><I.Drag /></span>
        <span className="aw-step-idx pending" style={{ background: "var(--bg-card)", border: "1px dashed var(--br-strong)", color: "var(--tx-3)" }}>1</span>
        <div style={{ flex: 1, minWidth: 0 }}>
          <div className="aw-step-title">Click "Most popular" tag and confirm it routes to Pro signup</div>
          <div className="aw-step-meta">
            <span className="aw-badge-i ok"><span className="ldot" />strong locator</span>
            <span className="aw-badge-i outline">expected: navigates to /signup?plan=pro</span>
            <span className="aw-badge-i info"><span className="ldot" />1 child op</span>
          </div>
          <div className="aw-step-attached" data-comment-anchor="50fec2b806-div-41-11">
            <I.Target style={{ width: 12, height: 12, color: "var(--vio)" }} />
            <span>attached element:</span>
            <span className="scope">.ws-plan.featured .ws-plan-tag</span>
            <span className="aw-spacer" style={{ flex: 1 }} />
            <button className="aw-icon-btn" data-comment-anchor="3e75d938bc-button-119-13" onClick={link("Pick mode active · click an element on the page")} title="Re-pick element" data-tip="Re-pick element"><I.Target/></button>
          </div>
          <StepFoot id="stp_001" version="v1" lastRun="12m ago"/>
        </div>      </div>

      {/* step 2: weak locator */}
      <div className="aw-step-row"
      data-title="Each pricing card has a CTA that contains Get started or Talk to sales"
      data-status="weak">
        <span className="aw-step-handle"><I.Drag /></span>
        <span className="aw-step-idx warn" style={{ background: "var(--ylw)", color: "#fff" }}>2</span>
        <div style={{ flex: 1, minWidth: 0 }}>
          <div className="aw-step-title">Each pricing card has a CTA that contains "Get started" or "Talk to sales"</div>
          <div className="aw-step-meta">
            <span className="aw-badge-i warn"><span className="ldot" />weak locator</span>
            <span className="aw-badge-i outline">forEach .ws-plan</span>
          </div>
          <div className="aw-step-attached" style={{ borderColor: "#ECD89A", background: "#FBF1D2" }}>
            <I.Alert style={{ width: 12, height: 12, color: "var(--ylw)" }} />
            <span style={{ color: "#7A5A0E" }}>Locator <span className="scope">div:nth-child(2)</span> is positional — will break if a card is added. </span>
            <button className="aw-link" style={{ color: "var(--ylw)" }} onClick={link("Asking LLM for a stronger selector…")}>Improve locator</button>
            <span style={{ color: "#7A5A0E" }}>·</span>
            <button className="aw-link" style={{ color: "var(--ylw)" }} onClick={link("Loading candidate locators…")}>View candidates</button>
          </div>
          <StepFoot id="stp_002" version="v3" lastRun="1h ago"/>
        </div>      </div>

      {/* step 3: selected section */}
      <div className="aw-step-row"
      data-title="Section Pricing grid 4 child operations"
      data-status="section">
        <span className="aw-step-handle"><I.Drag /></span>
        <span className="aw-step-idx" style={{ background: "var(--vio)", color: "#fff" }}>3</span>
        <div style={{ flex: 1, minWidth: 0 }} data-comment-anchor="4b60e1055b-div-162-7">
          <div className="aw-step-title">Section: Pricing grid · 4 child operations</div>
          <div className="aw-step-meta">
            <span className="aw-badge-i vio"><span className="ldot" />section step</span>
            <span className="aw-badge-i outline">scope: section.pricing</span>
          </div>
          <div className="aw-step-attached">
            <I.Layers style={{ width: 12, height: 12, color: "var(--vio)" }} />
            <span>section attached:</span>
            <span className="scope">main &gt; section[aria-label="Pricing"]</span>
          </div>
          <div style={{ marginTop: 8, borderLeft: "2px solid var(--vio-soft)", paddingLeft: 10, display: "flex", flexDirection: "column", gap: 4 }}>
            <div className="aw-step-op"><span className="op-tag" style={{ background: "var(--vio-soft)", color: "var(--vio)" }}>3.1</span> Count cards equals 3</div>
            <div className="aw-step-op"><span className="op-tag" style={{ background: "var(--vio-soft)", color: "var(--vio)" }}>3.2</span> Each card exposes name + price + cta</div>
            <div className="aw-step-op"><span className="op-tag" style={{ background: "var(--vio-soft)", color: "var(--vio)" }}>3.3</span> Pro card highlighted (badge or color)</div>
            <div className="aw-step-op"><span className="op-tag" style={{ background: "var(--vio-soft)", color: "var(--vio)" }}>3.4</span> Cards reachable by keyboard tab order</div>
          </div>
          <StepFoot id="stp_003" version="v1" lastRun="never"/>
        </div>      </div>

      {/* step 4: missing test data */}
      <div className="aw-step-row"
      data-title="Fill Salary Analyzer form with sample dataset"
      data-status="blocked">
        <span className="aw-step-handle"><I.Drag /></span>
        <span className="aw-step-idx err" style={{ background: "var(--red)", color: "#fff" }}>4</span>
        <div style={{ flex: 1, minWidth: 0 }}>
          <div className="aw-step-title">Fill Salary Analyzer form with sample dataset</div>
          <div className="aw-step-meta">
            <span className="aw-badge-i err"><span className="ldot" />blocked: missing test data</span>
            <span className="aw-badge-i outline">requires: salaries.csv</span>
          </div>
          <div className="aw-step-attached" style={{ borderColor: "#E8B9AE", background: "#FBEEEA" }}>
            <I.Doc style={{ width: 12, height: 12, color: "var(--red)" }} />
            <span style={{ color: "#8A3A2E" }}>Step references <span className="scope">salaries.csv</span> — not uploaded.</span>
            <span className="aw-spacer" style={{ flex: 1 }} />
            <button className="aw-link" style={{ color: "var(--red)" }} onClick={link("Open file picker · CSV/JSON accepted")}>Upload now</button>
          </div>
          <StepFoot id="stp_004" version="v2" lastRun="never"/>
        </div>      </div>

      {/* step 5: wrong page */}
      <div className="aw-step-row"
      data-title="Verify docs sidebar contains Quickstart"
      data-status="wrongPage">
        <span className="aw-step-handle"><I.Drag /></span>
        <span className="aw-step-idx warn" style={{ background: "var(--ylw)", color: "#fff" }}>5</span>
        <div style={{ flex: 1, minWidth: 0 }}>
          <div className="aw-step-title">Verify docs sidebar contains "Quickstart"</div>
          <div className="aw-step-meta">
            <span className="aw-badge-i warn"><span className="ldot" />wrong current page</span>
            <span className="aw-badge-i outline">expected: /docs · current: /pricing</span>
          </div>
          <div className="aw-step-attached" style={{ borderColor: "#ECD89A", background: "#FBF1D2" }}>
            <I.Globe style={{ width: 12, height: 12, color: "var(--ylw)" }} />
            <span style={{ color: "#7A5A0E" }}>I will navigate to <span className="scope">/docs</span> before running this step.</span>
            <span className="aw-spacer" style={{ flex: 1 }} />
            <button className="aw-link" style={{ color: "var(--ylw)" }} onClick={link("Edit precondition for this step")}>Change precondition</button>
          </div>
          <StepFoot id="stp_005" version="v1" lastRun="yesterday"/>
        </div>      </div>

      {/* extra steps appended via Add step — render BEFORE the Add affordance so it stays at bottom */}
      {extraSteps.map((st, i) => (
        <div key={st.id} className="aw-step-row aw-step-new"
             data-title={st.title.toLowerCase()}
             data-status={st.status}>
          <span className="aw-step-handle"><I.Drag /></span>
          <span className="aw-step-idx pending" style={{ background: "var(--bg-card)", border: "1px dashed var(--br-strong)", color: "var(--tx-3)" }}>{6 + i}</span>
          <div style={{ flex: 1, minWidth: 0 }}>
            <div className="aw-step-title">{st.title}</div>
            <div className="aw-step-meta">
              <span className="aw-badge-i ok"><span className="ldot" />new · just added</span>
              <span className="aw-badge-i outline">no locator yet</span>
            </div>
            <StepFoot id={st.id} version="draft" lastRun="never"/>
          </div>
        </div>
      ))}

      {/* Add step affordance — pinned at the bottom of the list so new steps stack downward */}
      <div className="aw-step-add">
        <button className="aw-btn primary" style={{ padding: "7px 14px" }}
                onClick={addStep}>
          <I.Plus />Add step
        </button>
        <button className={"aw-btn " + (picking ? "primary" : "")} style={{ padding: "7px 12px" }}
                onClick={togglePick}>
          <I.Mouse />{picking ? "Cancel pick" : "Pick element from page"}
        </button>
        <span className="aw-spacer" style={{ flex: 1 }} />
        {picking ? (
          <span className="aw-pick-inline">
            <span className="aw-pick-pulse"/>
            Pick mode active
          </span>
        ) : (
          <span style={{ fontSize: 11, color: "var(--tx-3)" }}>
            {extraSteps.length > 0 ? `${5 + extraSteps.length} total · new appends below` : "New steps append below"}
          </span>
        )}
      </div>
    </div>);

}

// — RECORDED —————————————————————————————————————————————

function RecActions({ id, playLabel = "Replay this step" }) {
  const [open, setOpen] = React.useState(false);
  return (
    <>
      <button className="aw-icon-btn" title={playLabel}><I.Play /></button>
      <div className="aw-dock-wrap">
        <button className={"aw-icon-btn " + (open ? "active" : "")}
        onClick={() => setOpen(!open)} title="More" data-tip="More"><I.More /></button>
        {open &&
        <>
            <div className="aw-dock-scrim" onClick={() => setOpen(false)} />
            <div className="aw-dock-menu" role="menu" style={{ minWidth: 200 }}>
              <button className="aw-dock-opt" onClick={() => setOpen(false)}>
                <I.Camera />
                <span className="aw-dock-opt-main">
                  <span className="aw-dock-opt-t">Open evidence</span>
                  <span className="aw-dock-opt-d">Screenshot · trace · artifacts</span>
                </span>
              </button>
              <button className="aw-dock-opt" onClick={() => setOpen(false)}>
                <I.Diff />
                <span className="aw-dock-opt-main">
                  <span className="aw-dock-opt-t">Compare with previous</span>
                  <span className="aw-dock-opt-d">Diff this run vs the last</span>
                </span>
              </button>
              <button className="aw-dock-opt" onClick={() => setOpen(false)}>
                <I.Code />
                <span className="aw-dock-opt-main">
                  <span className="aw-dock-opt-t">Jump to code</span>
                  <span className="aw-dock-opt-d">Show the matching line</span>
                </span>
              </button>
              <div className="aw-dock-menu-sep" />
              <button className="aw-dock-opt" onClick={() => setOpen(false)}>
                <I.Download />
                <span className="aw-dock-opt-main">
                  <span className="aw-dock-opt-t">Download trace</span>
                  <span className="aw-dock-opt-d">Playwright trace.zip</span>
                </span>
              </button>
              <button className="aw-dock-opt" onClick={() => setOpen(false)}>
                <I.Skip />
                <span className="aw-dock-opt-main">
                  <span className="aw-dock-opt-t">Skip in next run</span>
                  <span className="aw-dock-opt-d">Don't include this step</span>
                </span>
              </button>
            </div>
          </>
        }
      </div>
    </>);

}

function RecordingVersions({ versions, onLoad }) {
  if (!versions || versions.length === 0) return null;
  return (
    <div style={{ margin: "8px 0", padding: "8px 12px", background: "var(--bg-inset)", borderRadius: 6, border: "1px solid var(--br)" }}>
      <div style={{ fontSize: 11, fontWeight: 600, color: "var(--tx-3)", marginBottom: 6, textTransform: "uppercase", letterSpacing: "0.04em" }}>Versions</div>
      <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
        {versions.map((v) => (
          <div key={v.version} style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 12 }}>
            <span style={{ fontFamily: "var(--ff-mono)", color: "var(--tx-2)", minWidth: 24 }}>v{v.version}</span>
            {v.current && <span className="aw-badge-i ok" style={{ fontSize: 10 }}><span className="ldot"/>current</span>}
            {v.note && <span style={{ color: "var(--tx-3)", flex: 1, minWidth: 0, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>({v.note})</span>}
            {!v.note && <span style={{ flex: 1 }}/>}
            <button className="aw-link" style={{ fontSize: 11, flexShrink: 0 }} onClick={() => onLoad(v)}>load</button>
          </div>
        ))}
      </div>
    </div>
  );
}

function RecordedTab() {
  const [liveRec, setLiveRec] = React.useState([]);
  const [recordingVersions, setRecordingVersions] = React.useState([]);

  const fetchVersions = React.useCallback(() => {
    const AW = (typeof window !== 'undefined' && window.AW) || null;
    if (!AW || typeof AW.send !== 'function') return;
    AW.send({ command: "list_recordings" });
  }, []);

  const handleLoadVersion = React.useCallback((v) => {
    const AW = (typeof window !== 'undefined' && window.AW) || null;
    if (!AW || typeof AW.send !== 'function') return;
    AW.send({ command: "load_recording", recording_id: v.recording_id, version: v.version });
  }, []);

  React.useEffect(() => {
    const AW = (typeof window !== 'undefined' && window.AW) || null;
    if (!AW || typeof AW.on !== 'function') return;
    const unsubs = [];
    unsubs.push(AW.on('step_recorded', (env) => {
      const p = (env && (env.payload || env)) || {};
      setLiveRec(prev => {
        const sid = p.step_id || p.id || ('rec_' + Date.now());
        if (prev.find(r => r.id === sid)) return prev;
        return [...prev, { id: sid, title: p.description || p.title || sid, duration: p.duration_ms, locator: p.locator, code: p.code_lines }];
      });
      fetchVersions();
    }));
    unsubs.push(AW.on('recordings_list_updated', (env) => {
      const p = (env && (env.payload || env)) || {};
      const list = Array.isArray(p.versions) ? p.versions : (Array.isArray(p.recordings) ? p.recordings : []);
      setRecordingVersions(list);
    }));
    unsubs.push(AW.on('list_recordings_result', (env) => {
      const p = (env && (env.payload || env)) || {};
      const list = Array.isArray(p.versions) ? p.versions : (Array.isArray(p.recordings) ? p.recordings : []);
      setRecordingVersions(list);
    }));
    fetchVersions();
    return () => unsubs.forEach(u => u && u());
  }, [fetchVersions]);

  if (liveRec.length > 0) {
    return (
      <div>
        <div className="aw-info-strip">
          <I.Camera />
          <span>Backend-emitted evidence only. {liveRec.length} step{liveRec.length !== 1 ? 's' : ''} recorded.</span>
          <span className="aw-spacer" />
          <button className="aw-btn" style={{ padding: "4px 10px" }}><I.Play />Replay all</button>
        </div>
        {liveRec.map((rec) => (
          <div key={rec.id} className="aw-rec-item">
            <div className="aw-rec-head">
              <span className="aw-step-idx ok" style={{ background: "var(--grn)", color: "#fff" }}>
                <I.Check style={{ width: 11, height: 11 }} />
              </span>
              <div style={{ flex: 1 }}>
                <div style={{ fontSize: 13, fontWeight: 500 }}>{rec.title} <span style={{ fontFamily: "var(--ff-mono)", fontSize: 10, color: "var(--tx-4)" }}>{rec.id} · v1</span></div>
                <div className="aw-step-meta" style={{ marginTop: 3 }}>
                  <span className="aw-badge-i ok"><span className="ldot" />recorded</span>
                  {rec.locator && <span>locator: <span style={{ fontFamily: "var(--ff-mono)" }}>{rec.locator}</span></span>}
                  {rec.duration != null && <span>· {rec.duration}ms</span>}
                </div>
              </div>
              <RecActions id={rec.id} />
            </div>
            {Array.isArray(rec.code) && rec.code.length > 0 && (
              <div className="aw-step-ops" style={{ borderLeft: "2px solid var(--grn-soft)", marginTop: 6, paddingLeft: 10 }}>
                {rec.code.map((line, li) => (
                  <div key={li} className="aw-step-op"><span className="op-tag">code</span>{line}</div>
                ))}
              </div>
            )}
          </div>
        ))}
        <RecordingVersions versions={recordingVersions} onLoad={handleLoadVersion} />
      </div>
    );
  }

  return (
    <div>
      <div className="aw-info-strip">
        <I.Camera />
        <span>Backend-emitted evidence only. Skipped or unresolved steps are not shown as recorded.</span>
        <span className="aw-spacer" />
        <button className="aw-btn" style={{ padding: "4px 10px" }}><I.Play />Replay all</button>
      </div>

      <div className="aw-rec-item">
        <div className="aw-rec-head">
          <span className="aw-step-idx ok" style={{ background: "var(--grn)", color: "#fff" }}>
            <I.Check style={{ width: 11, height: 11 }} />
          </span>
          <div style={{ flex: 1 }}>
            <div style={{ fontSize: 13, fontWeight: 500 }}>Verify hero heading <span style={{ fontFamily: "var(--ff-mono)", fontSize: 10, color: "var(--tx-4)" }}>rec_a1f3 · v1</span></div>
            <div className="aw-step-meta" style={{ marginTop: 3 }}>
              <span className="aw-badge-i ok"><span className="ldot" />recorded</span>
              <span>locator: <span style={{ fontFamily: "var(--ff-mono)" }}>getByRole('heading', {`{ level: 1 }`})</span></span>
              <span>· 412ms</span>
              <span>· 1 assertion</span>
            </div>
          </div>
          <RecActions id="a1f3" />
        </div>
        <div className="aw-step-ops" style={{ borderLeft: "2px solid var(--grn-soft)", marginTop: 6, paddingLeft: 10 }}>
          <div className="aw-step-op"><span className="op-tag">assert</span>visible · text contains "plans that scale" · <span className="aw-badge-i ok"><span className="ldot" />pass</span></div>
        </div>
      </div>

      <div className="aw-rec-item">
        <div className="aw-rec-head">
          <span className="aw-step-idx ok" style={{ background: "var(--grn)", color: "#fff" }}>
            <I.Check style={{ width: 11, height: 11 }} />
          </span>
          <div style={{ flex: 1 }}>
            <div style={{ fontSize: 13, fontWeight: 500 }}>Three pricing cards present <span style={{ fontFamily: "var(--ff-mono)", fontSize: 10, color: "var(--tx-4)" }}>rec_b2c9 · v1</span></div>
            <div className="aw-step-meta" style={{ marginTop: 3 }}>
              <span className="aw-badge-i ok"><span className="ldot" />recorded</span>
              <span>locator: <span style={{ fontFamily: "var(--ff-mono)" }}>locator('.ws-plan')</span></span>
              <span>· 138ms · count = 3</span>
            </div>
          </div>
          <RecActions id="b2c9" />
        </div>
        <div className="aw-rec-shot" />
      </div>

      <div className="aw-rec-item">
        <div className="aw-rec-head">
          <span className="aw-step-idx" style={{ background: "var(--ylw)", color: "#fff" }}>
            <I.Sync style={{ width: 11, height: 11 }} />
          </span>
          <div style={{ flex: 1 }}>
            <div style={{ fontSize: 13, fontWeight: 500 }}>Pro price equals "$49 / mo" <span style={{ fontFamily: "var(--ff-mono)", fontSize: 10, color: "var(--tx-4)" }}>rec_e1f4 · v2 (repaired)</span></div>
            <div className="aw-step-meta" style={{ marginTop: 3 }}>
              <span className="aw-badge-i warn"><span className="ldot" />repaired</span>
              <span>· 622ms</span>
            </div>
          </div>
          <RecActions id="e1f4" />
        </div>
        <div className="aw-diff" style={{ marginTop: 8, display: "flex", flexDirection: "column", gap: 1 }}>
          <div className="aw-diff-row rem"><span className="aw-diff-sign">-</span>expect(loc).toHaveText('$49 / mo')</div>
          <div className="aw-diff-row add"><span className="aw-diff-sign">+</span>expect(loc).toContainText('$49')</div>
        </div>
        <div className="aw-step-meta" style={{ marginTop: 8, color: "var(--tx-3)" }}>
          repair reason: actual text was <span style={{ fontFamily: "var(--ff-mono)", color: "var(--tx-2)" }}>"$49 /mo"</span> · relaxed by LLM repair with user approval
        </div>
      </div>

      <div className="aw-rec-item">
        <div className="aw-rec-head">
          <span className="aw-step-idx" style={{ background: "var(--bg-inset)", color: "var(--tx-3)", border: "1px dashed var(--br-strong)" }}>
            <I.Skip style={{ width: 10, height: 10 }} />
          </span>
          <div style={{ flex: 1 }}>
            <div style={{ fontSize: 13, fontWeight: 500, color: "var(--tx-3)" }}>FAQ accordion expands when first row clicked <span style={{ fontFamily: "var(--ff-mono)", fontSize: 10, color: "var(--tx-4)" }}>stp_faq · skipped</span></div>
            <div className="aw-step-meta" style={{ marginTop: 3 }}>
              <span className="aw-badge-i outline">skipped by user · pre-run</span>
              <span>not recorded — no evidence to show</span>
            </div>
          </div>
          <RecActions id="faq" playLabel="Include and run this step" />
        </div>
      </div>

      <div className="aw-rec-item">
        <div className="aw-rec-head">
          <span className="aw-step-idx ok" style={{ background: "var(--grn)", color: "#fff" }}>
            <I.Check style={{ width: 11, height: 11 }} />
          </span>
          <div style={{ flex: 1 }}>
            <div style={{ fontSize: 13, fontWeight: 500 }}>Footer status link points at status.acme.dev <span style={{ fontFamily: "var(--ff-mono)", fontSize: 10, color: "var(--tx-4)" }}>rec_f7a3 · v1</span></div>
            <div className="aw-step-meta" style={{ marginTop: 3 }}>
              <span className="aw-badge-i ok"><span className="ldot" />recorded</span>
              <span>locator: <span style={{ fontFamily: "var(--ff-mono)" }}>getByRole('contentinfo').getByText('Status')</span></span>
              <span>· 89ms</span>
            </div>
          </div>
          <RecActions id="f7a3" />
        </div>
      </div>
      <RecordingVersions versions={recordingVersions} onLoad={handleLoadVersion} />
    </div>);

}

// — CODE —————————————————————————————————————————————

function CodeReviewSummary({ review, collapsed, onToggle }) {
  if (!review) return null;
  const score = review.score != null ? review.score : null;
  const errors = review.errors != null ? review.errors : (Array.isArray(review.issues) ? review.issues.filter(i => i.severity === 'error').length : 0);
  const warns = review.warnings != null ? review.warnings : (Array.isArray(review.issues) ? review.issues.filter(i => i.severity === 'warning' || i.severity === 'warn').length : 0);
  const infos = review.infos != null ? review.infos : (Array.isArray(review.issues) ? review.issues.filter(i => i.severity === 'info').length : 0);
  const issues = Array.isArray(review.issues) ? review.issues : [];
  const scoreColor = score == null ? "var(--tx-3)" : score >= 80 ? "var(--grn)" : score >= 70 ? "var(--ylw)" : "var(--red)";
  return (
    <div style={{ margin: "8px 12px", padding: "8px 10px", background: "var(--bg-inset)", borderRadius: 6, border: "1px solid var(--br)" }}>
      <div style={{ display: "flex", alignItems: "center", gap: 6, cursor: "pointer" }} onClick={onToggle}>
        <I.Check style={{ width: 11, height: 11, color: scoreColor }} />
        <span style={{ fontSize: 12, fontWeight: 600, color: scoreColor }}>
          {score != null ? ("Score: " + score + "/100") : "Code Review"}
        </span>
        <span style={{ fontSize: 12, color: "var(--tx-3)", flex: 1 }}>
          {" — "}{errors} error{errors !== 1 ? "s" : ""}, {warns} warn{warns !== 1 ? "s" : ""}, {infos} info
        </span>
        {issues.length > 0 && (
          <span style={{ fontSize: 10, color: "var(--tx-3)" }}>{collapsed ? "▸" : "▾"}</span>
        )}
      </div>
      {!collapsed && issues.length > 0 && (
        <ul style={{ margin: "6px 0 0 0", padding: 0, listStyle: "none", display: "flex", flexDirection: "column", gap: 3 }}>
          {issues.map((iss, i) => {
            const sevColor = iss.severity === 'error' ? "var(--red)" : iss.severity === 'warning' || iss.severity === 'warn' ? "var(--ylw)" : "var(--blu)";
            return (
              <li key={i} style={{ fontSize: 11, display: "flex", gap: 5, alignItems: "flex-start" }}>
                <span style={{ color: sevColor, flexShrink: 0, fontWeight: 600 }}>{(iss.severity || "info").slice(0, 1).toUpperCase()}</span>
                {iss.line && <span style={{ fontFamily: "var(--ff-mono)", color: "var(--tx-3)", flexShrink: 0 }}>L{iss.line}</span>}
                <span style={{ color: "var(--tx-2)" }}>{iss.message || iss.text || String(iss)}</span>
              </li>
            );
          })}
        </ul>
      )}
    </div>
  );
}

function CodeTab() {
  const [moreOpen, setMoreOpen] = React.useState(false);
  const [liveCode, setLiveCode] = React.useState([]);
  const [liveCodeReview, setLiveCodeReview] = React.useState(null);
  const [reviewCollapsed, setReviewCollapsed] = React.useState(false);
  React.useEffect(() => {
    const AW = (typeof window !== 'undefined' && window.AW) || null;
    if (!AW || typeof AW.on !== 'function') return;
    const unsubs = [];
    unsubs.push(AW.on('code_update', (env) => {
      const p = (env && (env.payload || env)) || {};
      const lines = Array.isArray(p.lines) ? p.lines : (typeof p.code === 'string' ? p.code.split('\n') : []);
      const file = p.file || p.filename || 'generated.spec.ts';
      setLiveCode(prev => {
        const existing = prev.find(c => c.file === file);
        if (existing) return prev.map(c => c.file === file ? { ...c, lines, ts: Date.now() } : c);
        return [...prev, { file, lines, ts: Date.now() }];
      });
    }));
    unsubs.push(AW.on('code_review', (env) => {
      const p = (env && (env.payload || env)) || {};
      setLiveCodeReview(p);
    }));
    return () => unsubs.forEach(u => u && u());
  }, []);

  if (liveCode.length > 0) {
    return (
      <div>
        <CodeReviewSummary review={liveCodeReview} collapsed={reviewCollapsed} onToggle={() => setReviewCollapsed(c => !c)} />
        <div className="aw-info-strip" style={{ background: "var(--blu-tint)", borderColor: "#D8E3F2" }}>
          <I.Info style={{ color: "var(--blu)" }} />
          <span>Rendered from <span style={{ fontFamily: "var(--ff-mono)" }}>code_update</span> events — frontend does not generate code.</span>
        </div>
        {liveCode.map((c) => (
          <div key={c.file} style={{ padding: "8px 12px 12px" }}>
            <div className="aw-list-toolbar" style={{ position: "sticky" }}>
              <span style={{ display: "flex", alignItems: "center", gap: 5, fontSize: 12, minWidth: 0, overflow: "hidden" }}>
                <I.Doc style={{ width: 12, height: 12, color: "var(--tx-2)", flex: "0 0 12px" }} />
                <span style={{ fontFamily: "var(--ff-mono)", color: "var(--tx)", whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>{c.file}</span>
                <span className="aw-badge-i info" style={{ marginLeft: 2, flexShrink: 0 }}><span className="ldot" />live</span>
              </span>
              <span className="aw-spacer" />
              <button className="aw-btn" onClick={() => { try { navigator.clipboard.writeText(c.lines.join('\n')); } catch(e) {} }}><I.Copy />Copy</button>
            </div>
            <pre className="aw-code">{c.lines.join('\n')}</pre>
          </div>
        ))}
      </div>
    );
  }

  return (
    <div>
      <CodeReviewSummary review={liveCodeReview} collapsed={reviewCollapsed} onToggle={() => setReviewCollapsed(c => !c)} />
      <div className="aw-info-strip" style={{ background: "var(--blu-tint)", borderColor: "#D8E3F2" }}>
        <I.Info style={{ color: "var(--blu)" }} />
        <span>Rendered from <span style={{ fontFamily: "var(--ff-mono)" }}>code_update</span> events — frontend does not generate code.</span>
      </div>
      <div className="aw-list-toolbar" style={{ position: "sticky" }}>
        <span style={{ display: "flex", alignItems: "center", gap: 5, fontSize: 12, minWidth: 0, overflow: "hidden" }}>
          <I.Doc style={{ width: 12, height: 12, color: "var(--tx-2)", flex: "0 0 12px" }} />
          <span style={{ fontFamily: "var(--ff-mono)", color: "var(--tx)", whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>tests/pricing.spec.ts</span>
          <span className="aw-badge-i info" style={{ marginLeft: 2, flexShrink: 0 }}><span className="ldot" />4s ago</span>
        </span>
        <span className="aw-spacer" />
        <button className="aw-btn"><I.Copy />Copy</button>
        <div className="aw-dock-wrap">
          <button className={"aw-icon-btn " + (moreOpen ? "active" : "")}
          onClick={() => setMoreOpen(!moreOpen)} title="More options" data-tip="More options"><I.More /></button>
          {moreOpen &&
          <>
              <div className="aw-dock-scrim" onClick={() => setMoreOpen(false)} />
              <div className="aw-dock-menu" role="menu" style={{ minWidth: 200 }}>
                <button className="aw-dock-opt" onClick={() => setMoreOpen(false)}>
                  <I.Download />
                  <span className="aw-dock-opt-main">
                    <span className="aw-dock-opt-t">Save to disk</span>
                    <span className="aw-dock-opt-d">Write the spec file locally</span>
                  </span>
                </button>
                <button className="aw-dock-opt" onClick={() => setMoreOpen(false)}>
                  <I.Eye />
                  <span className="aw-dock-opt-main">
                    <span className="aw-dock-opt-t">View raw</span>
                    <span className="aw-dock-opt-d">Open the source as plain text</span>
                  </span>
                </button>
                <button className="aw-dock-opt" onClick={() => setMoreOpen(false)}>
                  <I.Branch />
                  <span className="aw-dock-opt-main">
                    <span className="aw-dock-opt-t">Open in editor</span>
                    <span className="aw-dock-opt-d">Hand off to your IDE</span>
                  </span>
                </button>
                <div className="aw-dock-menu-sep" />
                <button className="aw-dock-opt" onClick={() => setMoreOpen(false)}>
                  <I.Sync />
                  <span className="aw-dock-opt-main">
                    <span className="aw-dock-opt-t">Re-generate from recordings</span>
                    <span className="aw-dock-opt-d">Rebuild from latest evidence</span>
                  </span>
                </button>
              </div>
            </>
          }
        </div>
      </div>

      <div style={{ padding: "8px 12px 12px" }}>
        <div style={{ display: "flex", gap: 4, marginBottom: 8, flexWrap: "wrap" }}>
          <span className="aw-badge-i warn"><span className="ldot" />1 fragile locator</span>
          <span className="aw-badge-i outline">2 placeholders</span>
          <span className="aw-badge-i info"><span className="ldot" />5 recorded</span>
        </div>

        <pre className="aw-code"><span className="com">// generated by AutoWorkbench · do not edit manually</span>{"\n"}
<span className="kw">import</span> <span className="pun">{"{"}</span> <span className="var">test</span><span className="pun">,</span> <span className="var">expect</span> <span className="pun">{"}"}</span> <span className="kw">from</span> <span className="str">'@playwright/test'</span><span className="pun">;</span>{"\n"}
{"\n"}
<span className="fn">test</span><span className="pun">(</span><span className="str">'pricing page · sanity'</span><span className="pun">,</span> <span className="kw">async</span> <span className="pun">({"{"}</span> <span className="var">page</span> <span className="pun">{"}"})</span> <span className="pun">=&gt; {"{"}</span>{"\n"}
{"  "}<span className="kw">await</span> <span className="var">page</span><span className="pun">.</span><span className="fn">goto</span><span className="pun">(</span><span className="str">'https://acme.dev/pricing'</span><span className="pun">);</span>{"\n"}
{"\n"}
{"  "}<span className="com">// rec_a1f3 · hero heading</span>{"\n"}
{"  "}<span className="kw">await</span> <span className="fn">expect</span><span className="pun">(</span><span className="var">page</span><span className="pun">.</span><span className="fn">getByRole</span><span className="pun">(</span><span className="str">'heading'</span><span className="pun">, {"{"} level: </span><span className="num">1</span> <span className="pun">{"}"})).</span><span className="fn">toContainText</span><span className="pun">(</span><span className="str">'plans that scale'</span><span className="pun">);</span>{"\n"}
{"\n"}
{"  "}<span className="com">// rec_b2c9 · three pricing cards</span>{"\n"}
{"  "}<span className="kw">const</span> <span className="var">cards</span> <span className="pun">=</span> <span className="var">page</span><span className="pun">.</span><span className="fn">locator</span><span className="pun">(</span><span className="str">'.ws-plan'</span><span className="pun">);</span>{"\n"}
{"  "}<span className="kw">await</span> <span className="fn">expect</span><span className="pun">(</span><span className="var">cards</span><span className="pun">).</span><span className="fn">toHaveCount</span><span className="pun">(</span><span className="num">3</span><span className="pun">);</span>{"\n"}
{"\n"}
{"  "}<span className="com">// rec_c4d7 · pro card flagged</span>{"\n"}
{"  "}<span className="kw">await</span> <span className="fn">expect</span><span className="pun">(</span><span className="var">page</span><span className="pun">.</span><span className="fn">locator</span><span className="pun">(</span><span className="str">'.ws-plan.featured'</span><span className="pun">)).</span><span className="fn">toContainText</span><span className="pun">(</span><span className="str">'Most popular'</span><span className="pun">);</span>{"\n"}
{"\n"}
{"  "}<span className="com">// rec_d8e2 · ctas — !! fragile: ambiguous selector resolved by index</span>{"\n"}
{"  "}<span className="kw">for</span> <span className="pun">(</span><span className="kw">const</span> <span className="var">cta</span> <span className="kw">of</span> <span className="kw">await</span> <span className="var">page</span><span className="pun">.</span><span className="fn">locator</span><span className="pun">(</span><span className="str">'a.ws-plan-cta'</span><span className="pun">).</span><span className="fn">all</span><span className="pun">()) {"{"}</span>{"\n"}
{"    "}<span className="kw">await</span> <span className="fn">expect</span><span className="pun">(</span><span className="var">cta</span><span className="pun">).</span><span className="fn">toBeEnabled</span><span className="pun">();</span>{"\n"}
{"    "}<span className="kw">await</span> <span className="fn">expect</span><span className="pun">(</span><span className="var">cta</span><span className="pun">).</span><span className="fn">toHaveAttribute</span><span className="pun">(</span><span className="str">'href'</span><span className="pun">, </span><span className="fn">expect</span><span className="pun">.</span><span className="fn">stringMatching</span><span className="pun">(/^https?:|^\//));</span>{"\n"}
{"  "}<span className="pun">{"}"}</span>{"\n"}
{"\n"}
{"  "}<span className="com">// rec_e1f4 · pro price (repaired: exact → contains)</span>{"\n"}
{"  "}<span className="kw">await</span> <span className="fn">expect</span><span className="pun">(</span><span className="var">page</span><span className="pun">.</span><span className="fn">locator</span><span className="pun">(</span><span className="str">'.ws-plan.featured .ws-plan-price'</span><span className="pun">)).</span><span className="fn">toContainText</span><span className="pun">(</span><span className="str">'$49'</span><span className="pun">);</span>{"\n"}
{"\n"}
{"  "}<span className="com">// rec_f7a3 · footer status link</span>{"\n"}
{"  "}<span className="kw">const</span> <span className="var">statusLink</span> <span className="pun">=</span> <span className="var">page</span><span className="pun">.</span><span className="fn">getByRole</span><span className="pun">(</span><span className="str">'contentinfo'</span><span className="pun">).</span><span className="fn">getByText</span><span className="pun">(</span><span className="str">'Status'</span><span className="pun">);</span>{"\n"}
{"  "}<span className="kw">await</span> <span className="fn">expect</span><span className="pun">(</span><span className="var">statusLink</span><span className="pun">).</span><span className="fn">toHaveAttribute</span><span className="pun">(</span><span className="str">'href'</span><span className="pun">, </span><span className="str">'https://status.acme.dev'</span><span className="pun">);</span>{"\n"}
<span className="pun">{"}"});</span>{"\n"}</pre>

        <div className="aw-card-section-title">Warnings inline</div>
        <ul className="aw-dotlist">
          <li className="no"><span className="sec">L18</span>fragile selector <span style={{ fontFamily: "var(--ff-mono)" }}>a.ws-plan-cta</span> — three matches at runtime, indexed by order. Consider role + accessible name.</li>
          <li><span className="sec">L24</span>repaired assertion uses <span style={{ fontFamily: "var(--ff-mono)" }}>toContainText</span>; original exact match preserved in <button className="aw-link">replay history</button>.</li>
          <li className="no"><span className="sec">code_gen</span>FAQ accordion step skipped by user — no code emitted (would have been a click + visibility assertion).</li>
        </ul>
      </div>
    </div>);

}

// — TRACE —————————————————————————————————————————————

function TraceTab() {
  const [liveRows, setLiveRows] = React.useState([]);
  React.useEffect(() => {
    const AW = (typeof window !== 'undefined' && window.AW) || null;
    if (!AW || typeof AW.on !== 'function') return;
    const TRACE_EVENTS = ['step_executing', 'step_recorded', 'plan_ready', 'code_update', 'clarification_needed', 'llm_request', 'llm_response', 'permission_request', 'session_start', 'run_completed'];
    const unsubs = [];
    const addRow = (type, extraCls, extraIcon) => (env) => {
      const p = (env && (env.payload || env)) || {};
      const ts = new Date().toLocaleTimeString('en-US', { hour12: false, hour: '2-digit', minute: '2-digit', second: '2-digit' });
      const summary = p.description || p.title || p.step_id || p.message || p.hypothesis || type;
      const icon = extraIcon || I.Info;
      const cls = extraCls || '';
      setLiveRows(prev => [{ t: ts, icon, type, desc: String(summary), cls, live: true }, ...prev]);
    };
    if (typeof AW.on === 'function') {
      const tryWild = AW.on('*', (env) => {
        const type = (env && env.type) || 'event';
        if (type === 'debug_report' || type === 'code_review') return;
        addRow(type)(env);
      });
      if (tryWild && typeof tryWild === 'function') {
        unsubs.push(tryWild);
      } else {
        TRACE_EVENTS.forEach(evt => unsubs.push(AW.on(evt, addRow(evt))));
      }
    }
    unsubs.push(AW.on('debug_report', (env) => {
      const p = (env && (env.payload || env)) || {};
      const ts = new Date().toLocaleTimeString('en-US', { hour12: false, hour: '2-digit', minute: '2-digit', second: '2-digit' });
      const hypothesis = p.hypothesis || p.message || 'debug report';
      const agent = p.agent || p.agent_id || '';
      const desc = agent ? (hypothesis + " · " + agent) : hypothesis;
      setLiveRows(prev => [{ t: ts, icon: I.Alert, type: 'debug.report', desc, cls: 'debug-report', live: true }, ...prev]);
    }));
    unsubs.push(AW.on('code_review', (env) => {
      const p = (env && (env.payload || env)) || {};
      const ts = new Date().toLocaleTimeString('en-US', { hour12: false, hour: '2-digit', minute: '2-digit', second: '2-digit' });
      const score = p.score != null ? ("score " + p.score + "/100") : "code review";
      const errors = p.errors != null ? (p.errors + " err") : "";
      const warns = p.warnings != null ? (p.warnings + " warn") : "";
      const parts = [score, errors, warns].filter(Boolean).join(" · ");
      setLiveRows(prev => [{ t: ts, icon: I.Code, type: 'code.review', desc: parts, cls: 'code-review', live: true }, ...prev]);
    }));
    return () => unsubs.forEach(u => u && u());
  }, []);

  const mockRows = [
  { t: "11:42:01", icon: I.Spark, type: "session.start", desc: <><b>session_a91</b> · workspace <span style={{ fontFamily: "var(--ff-mono)" }}>acme-qa</span> · policy <span className="aw-badge-i warn"><span className="ldot" />balanced</span></>, cls: "" },
  { t: "11:42:02", icon: I.Globe, type: "page.attach", desc: <>attached to <span style={{ fontFamily: "var(--ff-mono)" }}>https://acme.dev/pricing</span> · dom 814 nodes</>, cls: "io" },
  { t: "11:42:03", icon: I.Spark, type: "llm.request", desc: <>plan-draft · ctx <span className="aw-badge-i acc"><span className="ldot" />section-summaries</span> · tools <span style={{ fontFamily: "var(--ff-mono)" }}>[dom_query, screenshot]</span> · ~1.2k tok</>, cls: "llm" },
  { t: "11:42:06", icon: I.Spark, type: "llm.response", desc: <>plan-v1 · 6 steps · validated against schema · cost <span style={{ fontFamily: "var(--ff-mono)" }}>$0.012</span></>, cls: "llm" },
  { t: "11:42:06", icon: I.Info, type: "plan.proposed", desc: <><b>plan_proposed</b> · awaiting user review</>, cls: "" },
  { t: "11:43:42", icon: I.Diff, type: "plan.revised", desc: <>user requested change · plan-v2 emitted · 1 add, 1 remove</>, cls: "" },
  { t: "11:43:42", icon: I.Check, type: "plan.confirmed", desc: <><b>plan_confirmed</b> · 6 steps queued</>, cls: "ok" },
  { t: "11:43:42", icon: I.Shield, type: "permission.req", desc: <>medium risk · <span style={{ fontFamily: "var(--ff-mono)" }}>page.click("a.btn.primary[Get started]")</span></>, cls: "warn" },
  { t: "11:43:46", icon: I.Check, type: "permission.allow", desc: <>user allowed once · scope <span style={{ fontFamily: "var(--ff-mono)" }}>plan_v2</span></>, cls: "ok" },
  { t: "11:43:47", icon: I.Play, type: "step.start", desc: <><b>stp_a1f3</b> · verify hero heading</>, cls: "" },
  { t: "11:43:47", icon: I.Target, type: "locator.resolved", desc: <>unique · <span style={{ fontFamily: "var(--ff-mono)" }}>role=heading[level=1]</span></>, cls: "ok" },
  { t: "11:43:47", icon: I.Check, type: "step.recorded", desc: <><b>stp_a1f3</b> recorded · 412ms · code_update emitted</>, cls: "ok" },
  { t: "11:43:47", icon: I.Play, type: "step.start", desc: <><b>stp_b2c9</b> · 3 pricing cards present</>, cls: "" },
  { t: "11:43:47", icon: I.Check, type: "step.recorded", desc: <><b>stp_b2c9</b> recorded · 138ms · count=3</>, cls: "ok" },
  { t: "11:43:47", icon: I.Target, type: "locator.ambig", desc: <>step <b>stp_c4d7</b> · 3 candidates for "Get started" — pausing run</>, cls: "warn" },
  { t: "11:43:54", icon: I.Check, type: "locator.chosen", desc: <>user selected candidate #2 · <span style={{ fontFamily: "var(--ff-mono)" }}>.ws-hero a.btn.primary</span></>, cls: "ok" },
  { t: "11:43:56", icon: I.Alert, type: "step.failed", desc: <><b>stp_e1f4</b> · assertion mismatch · evidence saved</>, cls: "err" },
  { t: "11:43:57", icon: I.Sync, type: "recover.attempt", desc: <>deterministic retry × 2 · same result · escalating to LLM</>, cls: "warn" },
  { t: "11:43:59", icon: I.Spark, type: "llm.repair", desc: <>proposed: relax <span style={{ fontFamily: "var(--ff-mono)" }}>toHaveText</span> → <span style={{ fontFamily: "var(--ff-mono)" }}>toContainText("$49")</span></>, cls: "llm" },
  { t: "11:44:03", icon: I.Check, type: "recover.applied", desc: <>user approved repair · re-running stp_e1f4</>, cls: "ok" },
  { t: "11:44:03", icon: I.Check, type: "step.recorded", desc: <><b>stp_e1f4</b> recorded · 622ms · v2 (repaired)</>, cls: "ok" },
  { t: "11:44:04", icon: I.Code, type: "code.update", desc: <><span style={{ fontFamily: "var(--ff-mono)" }}>tests/pricing.spec.ts</span> +47 lines · checksum <span style={{ fontFamily: "var(--ff-mono)" }}>c1f8a…</span></>, cls: "" },
  { t: "11:44:04", icon: I.Lock, type: "redact.scan", desc: <>screenshot redacted · 0 PII matches · all clear</>, cls: "" },
  { t: "11:44:04", icon: I.Check, type: "run.completed", desc: <><b>run_completed</b> · 5 passed · 1 repaired · 0 failed · 31.2s</>, cls: "ok" },
  { t: "11:44:04", icon: I.Info, type: "e2e.pending", desc: <>frontend cannot mark acceptance · paid E2E run scheduled <span style={{ fontFamily: "var(--ff-mono)" }}>02:00 UTC</span></>, cls: "" }];

  const rows = liveRows.length > 0 ? [...liveRows, ...mockRows] : mockRows;

  const [q, setQ] = React.useState("");
  const [scope, setScope] = React.useState("all");

  const matchScope = (r) => {
    if (scope === "all") return true;
    if (scope === "llm") return r.type.startsWith("llm.") || r.cls === "llm";
    if (scope === "step") return r.type.startsWith("step.") || r.type.startsWith("locator.");
    if (scope === "permission") return r.type.startsWith("permission.");
    if (scope === "error") return r.cls === "err" || r.type.includes("fail") || r.type.includes("recover.");
    if (scope === "debug") return r.cls === "debug-report" || r.cls === "code-review" || r.type === "debug.report" || r.type === "code.review";
    return true;
  };
  const matchQ = (r) => {
    if (!q) return true;
    const needle = q.toLowerCase();
    if (r.type.toLowerCase().includes(needle)) return true;
    if (r.t.includes(needle)) return true;
    const text = (typeof r.desc === "string" ? r.desc : JSON.stringify(r.desc)).toLowerCase();
    return text.includes(needle);
  };
  const visible = rows.filter((r) => matchScope(r) && matchQ(r));

  const scopes = [
  { id: "all", label: "All", count: rows.length },
  { id: "llm", label: "LLM", count: rows.filter((r) => r.type.startsWith("llm.") || r.cls === "llm").length },
  { id: "step", label: "Step", count: rows.filter((r) => r.type.startsWith("step.") || r.type.startsWith("locator.")).length },
  { id: "permission", label: "Permission", count: rows.filter((r) => r.type.startsWith("permission.")).length },
  { id: "error", label: "Error", count: rows.filter((r) => r.cls === "err" || r.type.includes("fail") || r.type.includes("recover.")).length },
  { id: "debug", label: "Debug/Review", count: rows.filter((r) => r.cls === "debug-report" || r.cls === "code-review" || r.type === "debug.report" || r.type === "code.review").length }];


  return (
    <div>
      <div className="aw-list-toolbar">
        <span className="aw-search" style={{ flex: 1, minWidth: 0, maxWidth: 220 }}>
          <I.Search style={{ width: 11, height: 11, color: "var(--tx-3)" }} />
          <input placeholder="Filter events…" value={q} onChange={(e) => setQ(e.target.value)} style={{ flex: 1, minWidth: 0 }} />
          {q && <button className="aw-icon-btn" style={{ width: 16, height: 16 }}
          onClick={() => setQ("")} title="Clear" data-tip="Clear search"><I.X style={{ width: 9, height: 9 }} /></button>}
        </span>
        <span className="aw-spacer" />
        <span style={{ fontSize: 11, color: "var(--tx-3)" }}>{visible.length} / {rows.length}</span>
        <button className="aw-btn" title="Download trace" data-tip="Download trace.zip"><I.Download /></button>
      </div>

      {/* Functional scope chips — exactly one active */}
      <div className="aw-trace-scopes">
        {scopes.map((sc) =>
        <button key={sc.id}
        className={"aw-trace-scope " + (scope === sc.id ? "active" : "")}
        onClick={() => setScope(sc.id)}>
            {sc.label}
            <span className="aw-trace-scope-n">{sc.count}</span>
          </button>
        )}
      </div>

      <div className="aw-info-strip" style={{ background: "#FBEEEA", borderColor: "#E8B9AE", color: "#8A3A2E" }}>
        <I.Alert style={{ color: "var(--red)" }} />
        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{ fontWeight: 600, color: "#8A3A2E" }}>Failure detail · stp_e1f4 · resolved by repair</div>
          <div style={{ display: "grid", gridTemplateColumns: "68px 1fr", gap: "2px 8px", marginTop: 4, fontFamily: "var(--ff-mono)", fontSize: 11, color: "var(--tx)" }}>
            <span style={{ color: "var(--tx-3)" }}>expected</span><span>"$49 / mo"</span>
            <span style={{ color: "var(--tx-3)" }}>actual</span><span>"$49 /mo"</span>
            <span style={{ color: "var(--tx-3)" }}>layer</span><span>assertion (locator matched 1)</span>
            <span style={{ color: "var(--tx-3)" }}>next</span><span>retry · select candidate · repair · skip · stop</span>
          </div>
        </div>
      </div>

      {visible.length === 0 &&
      <div style={{ padding: "32px 14px", textAlign: "center", color: "var(--tx-3)", fontSize: 12 }}>
          No events match your filter.
          <button className="aw-link" style={{ marginLeft: 6 }} onClick={() => {setQ("");setScope("all");}}>Reset</button>
        </div>
      }

      {visible.map((r, i) => {
        const isDebugReport = r.cls === "debug-report" || r.type === "debug.report";
        const isCodeReview = r.cls === "code-review" || r.type === "code.review";
        const rowStyle = isDebugReport
          ? { background: "rgba(234,179,8,0.08)", borderLeft: "2px solid var(--ylw)" }
          : isCodeReview
          ? { background: "rgba(59,130,246,0.07)", borderLeft: "2px solid var(--blu, #3B82F6)" }
          : {};
        const iconColor = isDebugReport ? "var(--ylw)" : isCodeReview ? "var(--blu, #3B82F6)" : undefined;
        return (
          <div key={i} className={"aw-trace-row " + (r.cls || "")} style={rowStyle}>
            <span className="t">{r.t}</span>
            <span className="aw-trace-icon"><r.icon style={{ width: 10, height: 10, color: iconColor }} /></span>
            <span className="type" style={isDebugReport || isCodeReview ? { fontWeight: 600 } : {}}>{r.type}</span>
            <span className="desc">{r.desc}</span>
          </div>
        );
      })}
    </div>);

}

window.StepsTab = StepsTab;
window.RecordedTab = RecordedTab;
window.CodeTab = CodeTab;
window.TraceTab = TraceTab;