// app.jsx — top-level glue: stage + panel chrome + tabs + tweaks + agents + now-strip
const { useState, useEffect, useRef } = React;

const TWEAK_DEFAULTS = /*EDITMODE-BEGIN*/{
  "tab": "llm",
  "state": "locator",
  "dock": "right",
  "panelWidth": 420,
  "collapsed": false,
  "connection": "connected",
  "showWebsite": true,
  "highlight": "hero-cta",
  "agentsOpen": false,
  "theme": "light",
  "mode": "llm"
}/*EDITMODE-END*/;

// Map "state" tweak → footer / header status / phase strings + current-task strip
const STATE_META = {
  idle:      { phase: "Idle",                  event: "session ready · waiting on user",  next: "Describe a flow",        conn: "connected", busy: false,
               now: { kind: "idle",   state: "Idle",                task: "Tell me what to automate or validate. I'll plan a flow before running anything.", primaryLabel: null } },
  planning:  { phase: "Analyzing page",        event: "dom_query · 814 nodes scanned",   next: "Awaiting plan",          conn: "connected", busy: true,
               now: { kind: "run",    state: "Analyzing",            task: "Page Intelligence is scanning acme.dev/pricing — 18 sections found so far.", primaryLabel: null } },
  clarify:   { phase: "Clarification needed",  event: "asked about test depth",          next: "Answer to continue",     conn: "connected", busy: false,
               now: { kind: "decide", state: "Clarification",        task: "Choose how deep this run should go — smoke, sanity, or regression.", refLabel: "step 0 of 0", primaryLabel: "Jump to question" } },
  recommend: { phase: "Recommendation review", event: "rendered 6 candidate assertions", next: "Use selected",           conn: "connected", busy: false,
               now: { kind: "decide", state: "Review",                task: "Pick which assertions to include before I draft a plan.", primaryLabel: "Use selected (5)" } },
  plan:      { phase: "Plan review",           event: "plan_ready · 6 steps · ~28s",     next: "Confirm & run",          conn: "connected", busy: false,
               now: { kind: "decide", state: "Confirm to run",        task: "Plan v2 is ready — 6 steps, ~28s, one fragile copy assertion flagged.", primaryLabel: "Confirm & run" } },
  diff:      { phase: "Plan revision",         event: "plan_v2 · +1 / -1",               next: "Apply changes",          conn: "connected", busy: false,
               now: { kind: "decide", state: "Plan diff",             task: "I drafted plan v2 with your edits — accept the changes to continue.", primaryLabel: "Apply changes" } },
  permit:    { phase: "Permission required",   event: "medium-risk click on a.btn.primary", next: "Allow or deny",       conn: "connected", busy: false,
               now: { kind: "decide", state: "Permission",            task: "Need permission for one medium-risk click before step 4 can run.", refLabel: "stp_d8e2", primaryLabel: "Allow once" } },
  exec:      { phase: "Executing",             event: "stp_c4d7 · resolving locator…",   next: "Wait or pause",          conn: "busy",      busy: true,
               now: { kind: "run",    state: "Step 3 of 6",           task: "Resolving locator for the \"Most popular\" tag in the Pro card.", refLabel: "stp_c4d7", primaryLabel: "Pause" } },
  locator:   { phase: "Locator ambiguity",     event: "3 matches for \"Get started\"",   next: "Choose candidate",       conn: "connected", busy: false, blocker: "ambiguous locator",
               now: { kind: "block",  state: "Execution paused",      task: "Three visible \"Get started\" links — pick a candidate or let me find a unique one.", refLabel: "stp_d8e2", primaryLabel: "Choose candidate" } },
  recover:   { phase: "Recovery needed",       event: "stp_e1f4 · assertion mismatch",   next: "Apply LLM repair",       conn: "connected", busy: false, blocker: "1 failed step",
               now: { kind: "block",  state: "Run blocked",           task: "Assertion failed — actual text was \"$49 /mo\". Repair, retry, or skip.", refLabel: "stp_e1f4", primaryLabel: "Apply LLM repair" } },
  done:      { phase: "Completed",             event: "run_completed · 5/6 + 1 repaired", next: "Replay or save suite", conn: "connected", busy: false,
               now: { kind: "ok",     state: "Completed",             task: "6 of 6 recorded · 1 repaired · 31.2s · paid E2E still pending.", primaryLabel: "Replay all" } },
  offline:   { phase: "Disconnected",          event: "ws closed · attempt 2 of 5",      next: "Reconnect",              conn: "offline",   busy: false, blocker: "backend unreachable",
               now: { kind: "block",  state: "Disconnected",          task: "Lost the websocket mid-step. I won't infer success or failure on my own.", primaryLabel: "Reconnect now" } },
  schema:    { phase: "Schema invalid",        event: "llm response failed plan.v3",     next: "Ask LLM to repair",      conn: "error",     busy: false, blocker: "invalid plan payload",
               now: { kind: "block",  state: "Schema invalid",        task: "Model returned an unknown operation kind. Nothing executed.", primaryLabel: "Ask LLM to repair" } },
  nobrowser: { phase: "Waiting on browser",    event: "no Playwright context attached",  next: "Launch chromium",        conn: "connected", busy: false, blocker: "no browser context",
               now: { kind: "block",  state: "Cannot start",          task: "Backend is up but there's no browser to drive. Launch one or attach an existing tab.", primaryLabel: "Launch chromium" } },
  apikey:    { phase: "Auth required",         event: "no provider key in workspace",    next: "Add API key",            conn: "connected", busy: false, blocker: "missing API key",
               now: { kind: "block",  state: "No model key",          task: "Main Orchestrator can't call the model — workspace has no key configured.", primaryLabel: "Add key" } },
  otp:       { phase: "Human input required",  event: "OTP prompt at /auth/otp",         next: "Submit code",            conn: "connected", busy: false, blocker: "awaiting OTP",
               now: { kind: "decide", state: "Awaiting OTP",          task: "Step 4 hit a 2FA prompt — type the 6-digit code from your authenticator.", refLabel: "stp_d8e2", primaryLabel: "Submit code" } },
  e2e:       { phase: "Acceptance pending",    event: "local run done · E2E queued",     next: "Wait for E2E or trigger now", conn: "connected", busy: false,
               now: { kind: "ok",     state: "Local done · E2E pending", task: "Local run is recorded, but the paid E2E suite hasn't run for this commit yet.", primaryLabel: "Trigger E2E now" } },
};

function App() {
  const [t, setTweak] = useTweaks(TWEAK_DEFAULTS);
  const [tab, setTabLocal] = useState(t.tab);
  useEffect(() => { setTabLocal(t.tab); }, [t.tab]);

  const setTab = (id) => { setTabLocal(id); setTweak("tab", id); };
  const setDock = (d) => setTweak("dock", d);
  const setCollapsed = (v) => setTweak("collapsed", v);
  const setAgentsOpen = (v) => setTweak("agentsOpen", v);

  // Apply theme to the panel scope so the website behind stays light
  useEffect(() => {
    document.documentElement.dataset.theme = t.theme || "light";
  }, [t.theme]);

  const meta = STATE_META[t.state] || STATE_META.idle;
  const statusKey = meta.conn === "offline" ? "offline"
                  : meta.conn === "error"   ? "error"
                  : meta.conn === "busy"    ? "busy"
                  : t.connection === "reconnect" ? "reconnect"
                  : "connected";

  const runId = t.state === "idle" ? "—" : "run_a91b";

  const [liveCounts, setLiveCounts] = React.useState(null);
  React.useEffect(() => {
    const AW = (typeof window !== 'undefined' && window.AW) || null;
    if (!AW || typeof AW.on !== 'function') return;
    if (AW.lastEvent && AW.lastEvent.type === 'session_state') {
      const p = AW.lastEvent.payload || AW.lastEvent;
      setLiveCounts({ llm: null, steps: (p.steps || []).length, rec: (p.recorded_steps || []).length, code: p.code_preview ? 1 : 0, trace: 0 });
    }
    return AW.on('session_state', (env) => {
      const p = (env && (env.payload || env)) || {};
      setLiveCounts({ llm: null, steps: (p.steps || []).length, rec: (p.recorded_steps || []).length, code: p.code_preview ? 1 : 0, trace: 0 });
    });
  }, []);
  const counts = liveCounts || { llm: null, steps: 5, rec: 4, code: 1, trace: 25 };

  const [liveTokenInfo, setLiveTokenInfo] = React.useState(null);
  React.useEffect(() => {
    const AW = (typeof window !== 'undefined' && window.AW) || null;
    if (!AW || typeof AW.on !== 'function') return;
    if (AW.lastEvent && AW.lastEvent.type === 'token_report') {
      const p = AW.lastEvent.payload || AW.lastEvent;
      setLiveTokenInfo({ tok: ((((p.input_tokens || 0) + (p.output_tokens || 0)) / 1000).toFixed(1)) + "k", cost: (p.estimated_cost || 0).toFixed(2) });
    }
    return AW.on('token_report', (env) => {
      const p = (env && (env.payload || env)) || {};
      setLiveTokenInfo({ tok: ((((p.input_tokens || 0) + (p.output_tokens || 0)) / 1000).toFixed(1)) + "k", cost: (p.estimated_cost || 0).toFixed(2) });
    });
  }, []);
  const tokenInfo = liveTokenInfo || { tok: "8.4k", cost: "0.12" };

  const [liveAgentMap, setLiveAgentMap] = React.useState(null);
  React.useEffect(() => {
    const AW = (typeof window !== 'undefined' && window.AW) || null;
    if (!AW || typeof AW.on !== 'function') return;
    const applyAgentStatus = (p) => {
      const invId = (p && (p.invocation_id || p.agent_id || p.agent_name || "unknown")) + "";
      const role = (p && (p.role || p.agent_name || p.purpose || "")) + "";
      const purpose = (p && (p.purpose || p.description || "")) + "";
      const status = (p && (p.status || p.state || "")) + "";
      setLiveAgentMap((prev) => {
        const next = new Map(prev || []);
        next.set(invId, { role, purpose, status });
        return next;
      });
    };
    const off1 = AW.on('agent_status', (env) => applyAgentStatus((env && (env.payload || env)) || {}));
    const off2 = AW.on('agent_running', (env) => applyAgentStatus((env && (env.payload || env)) || {}));
    const off3 = AW.on('agent_complete', (env) => applyAgentStatus((env && (env.payload || env)) || {}));
    return () => { off1 && off1(); off2 && off2(); off3 && off3(); };
  }, []);

  const liveAgents = React.useMemo(() => {
    if (!liveAgentMap || liveAgentMap.size === 0) return null;
    const ROLE_SLOTS = [
      { slot: 0, pattern: /main_orchestrator|orchestrat/i },
      { slot: 1, pattern: /page_intelligence|page.intel|locator/i },
      { slot: 2, pattern: /step_runner|step.run|executor/i },
      { slot: 3, pattern: /debug_agent|debug/i },
      { slot: 4, pattern: /codegen_reviewer|risk/i },
    ];
    const slots = ["on","on","on","off","off"];
    liveAgentMap.forEach(({ role, status }) => {
      const isRun = status === "running";
      for (const { slot, pattern } of ROLE_SLOTS) {
        if (pattern.test(role)) {
          slots[slot] = isRun ? "run" : "on";
          break;
        }
      }
    });
    return slots;
  }, [liveAgentMap]);

  const [liveDebugReport, setLiveDebugReport] = React.useState(null);
  React.useEffect(() => {
    const AW = (typeof window !== 'undefined' && window.AW) || null;
    if (!AW || typeof AW.on !== 'function') return;
    const off = AW.on('debug_report', (env) => {
      const p = (env && (env.payload || env)) || {};
      setLiveDebugReport(p);
    });
    return () => off && off();
  }, []);

  const [liveCodeReview, setLiveCodeReview] = React.useState(null);
  React.useEffect(() => {
    const AW = (typeof window !== 'undefined' && window.AW) || null;
    if (!AW || typeof AW.on !== 'function') return;
    const off = AW.on('code_review', (env) => {
      const p = (env && (env.payload || env)) || {};
      setLiveCodeReview(p);
    });
    return () => off && off();
  }, []);

  // run_rejected toast — shown for 3 s when server rejects a new llm_run while one is active
  const [runRejectedMsg, setRunRejectedMsg] = React.useState(null);
  const runRejectedTimer = React.useRef(null);
  React.useEffect(() => {
    const AW = (typeof window !== 'undefined' && window.AW) || null;
    if (!AW || typeof AW.on !== 'function') return;
    const off = AW.on('run_rejected', (env) => {
      const p = (env && (env.payload || env)) || {};
      const text = p.message || "A run is already in progress.";
      console.warn('[run_rejected]', p);
      setRunRejectedMsg(text);
      clearTimeout(runRejectedTimer.current);
      runRejectedTimer.current = setTimeout(() => setRunRejectedMsg(null), 3000);
    });
    return () => { off && off(); clearTimeout(runRejectedTimer.current); };
  }, []);

  const agentsSummary = liveAgents || (() => {
    const isRun = ["exec","locator","recover"].includes(t.state);
    const isPlanning = ["planning","clarify","recommend","plan","diff"].includes(t.state);
    return [
      isRun || isPlanning ? "on" : "on",
      t.state === "planning" ? "run" : "on",
      isRun ? "run" : "on",
      t.state === "recover" ? "on" : "off",
      "off",
    ];
  })();

  const stageCls = "aw-stage dock-" + t.dock + (t.collapsed ? " collapsed" : "");

  // Auto-scroll body to bottom on state/tab change
  const bodyRef = useRef(null);
  useEffect(() => {
    if (bodyRef.current) bodyRef.current.scrollTop = bodyRef.current.scrollHeight;
  }, [t.state, tab]);

  // tab body
  let body;
  if (tab === "llm")        body = <LlmThread state={t.state} mode={t.mode}/>;
  else if (tab === "steps") body = <StepsTab mode={t.mode} setMode={(v) => setTweak("mode", v)}/>;
  else if (tab === "rec")   body = <RecordedTab/>;
  else if (tab === "code")  body = <CodeTab/>;
  else if (tab === "trace") body = <TraceTab/>;

  const showNow = tab === "llm" && t.state !== "idle";

  const panel = (
    <aside className="aw-panel"
           data-wide={(t.dock === "top" || t.panelWidth >= 620) ? "1" : "0"}
           style={{width: t.dock === "top" ? "100%" : t.panelWidth}}>
      <div className="aw-resize"/>
      {!t.collapsed && (
        <>
          <Header
            status={statusKey}
            dock={t.dock} setDock={setDock}
            collapsed={t.collapsed} setCollapsed={setCollapsed}
            tokenInfo={tokenInfo}
            runState={runId}
            agentsOpen={t.agentsOpen}
            setAgentsOpen={setAgentsOpen}
            agentsSummary={agentsSummary}
            mode={t.mode}
            setMode={(v) => setTweak("mode", v)}
          />
          {liveDebugReport && liveDebugReport.hypothesis && (
            <div style={{ display: "flex", alignItems: "center", gap: 6, padding: "4px 12px", background: "var(--ylw-tint, #FBF1D2)", borderBottom: "1px solid #ECD89A", fontSize: 11, color: "#7A5A0E", flexShrink: 0 }}>
              <I.Alert style={{ width: 11, height: 11, color: "var(--ylw)", flexShrink: 0 }} />
              <span style={{ flex: 1, minWidth: 0, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                debug: {liveDebugReport.hypothesis}
              </span>
              <button className="aw-btn" style={{ padding: "2px 8px", fontSize: 11, flexShrink: 0 }} onClick={() => setTab("trace")}>Trace</button>
            </div>
          )}
          {runRejectedMsg && (
            <div className="aw-toast" style={{ display: "flex", alignItems: "center", gap: 6, padding: "5px 12px", background: "var(--red-tint, #FDECEA)", borderBottom: "1px solid #F5C6C2", fontSize: 11, color: "#8B1A14", flexShrink: 0 }}>
              <span style={{ flex: 1, minWidth: 0 }}>{runRejectedMsg}</span>
              <button style={{ background: "none", border: "none", cursor: "pointer", fontSize: 13, lineHeight: 1, color: "#8B1A14", padding: "0 2px", flexShrink: 0 }} onClick={() => setRunRejectedMsg(null)} aria-label="Dismiss">&times;</button>
            </div>
          )}
          <div style={{ position: "relative" }}>
            <TabStrip tab={tab} setTab={setTab} counts={counts}/>
            {liveCodeReview && liveCodeReview.score != null && liveCodeReview.score < 70 && (
              <span style={{ position: "absolute", top: 6, right: 8, width: 7, height: 7, borderRadius: "50%", background: "var(--red)", boxShadow: "0 0 0 2px var(--bg-panel, #fff)", pointerEvents: "none" }} title={"Code review score: " + liveCodeReview.score + "/100"} />
            )}
          </div>
          {showNow && <NowStrip {...meta.now}/>}
          <div className="aw-panel-body" ref={bodyRef}>
            {body}
          </div>
          {tab === "llm" && t.state !== "idle" && <Composer/>}
          <Footer
            phase={meta.phase}
            event={meta.event}
            blocker={meta.blocker}
            nextAction={meta.next}
            busy={meta.busy}
          />
          {t.agentsOpen && <AgentsPopover state={t.state} onClose={() => setAgentsOpen(false)}/>}
        </>
      )}
      {t.collapsed && <CollapsedRail tab={tab} setTab={(id)=>{ setTab(id); setCollapsed(false); }} setCollapsed={setCollapsed}/>}
    </aside>
  );

  return (
    <>
      <div className={stageCls}>
        <main className="aw-site">
          {t.showWebsite && <Website highlight={t.highlight}/>}
        </main>
        {panel}
      </div>

      <TweaksPanel>
        <TweakSection label="Panel"/>
        <TweakRadio  label="Dock"      value={t.dock}
                     options={["right","left","top","float"]}
                     onChange={(v) => setTweak("dock", v)}/>
        <TweakSlider label="Panel width" value={t.panelWidth} min={360} max={720} step={10} unit="px"
                     onChange={(v) => setTweak("panelWidth", v)}/>
        <TweakToggle label="Collapsed"  value={t.collapsed}  onChange={(v)=>setTweak("collapsed", v)}/>
        <TweakToggle label="Show website behind" value={t.showWebsite} onChange={(v)=>setTweak("showWebsite", v)}/>

        <TweakSection label="Active tab"/>
        <TweakRadio label="Tab" value={tab}
                    options={["llm","steps","rec","code","trace"]}
                    onChange={(v) => setTab(v)}/>

        <TweakSection label="Lifecycle state (LLM tab)"/>
        <TweakSelect label="State" value={t.state}
                     options={[
                       "idle","planning","clarify","recommend","plan","diff",
                       "permit","exec","locator","recover","done",
                       "offline","schema","nobrowser","apikey","otp","e2e"
                     ]}
                     onChange={(v) => setTweak("state", v)}/>

        <TweakSection label="Theme"/>
        <TweakRadio label="Theme" value={t.theme}
                    options={["light","dark"]}
                    onChange={(v) => setTweak("theme", v)}/>

        <TweakSection label="Interaction mode"/>
        <TweakRadio label="Mode" value={t.mode}
                    options={["llm","manual"]}
                    onChange={(v) => setTweak("mode", v)}/>

        <TweakSection label="Overlays"/>
        <TweakToggle label="Agent Control Center" value={t.agentsOpen}
                     onChange={(v) => setTweak("agentsOpen", v)}/>

        <TweakSection label="Page highlight"/>
        <TweakRadio label="Highlight CTA" value={t.highlight}
                    options={["none","hero-cta","pro-cta"]}
                    onChange={(v) => setTweak("highlight", v)}/>
      </TweaksPanel>
    </>
  );
}

// — Collapsed rail —————————————————————————————————————

function CollapsedRail({ tab, setTab, setCollapsed }) {
  const items = [
    { id: "llm",   Icon: I.Spark },
    { id: "steps", Icon: I.Steps },
    { id: "rec",   Icon: I.Camera },
    { id: "code",  Icon: I.Code },
    { id: "trace", Icon: I.Trace },
  ];
  return (
    <div className="aw-collapsed-rail">
      <button className="aw-icon-btn" onClick={() => setCollapsed(false)} title="Expand">
        <I.CaretR style={{transform:"rotate(180deg)"}}/>
      </button>
      <div className="aw-rail-sep"/>
      {items.map(i => (
        <button key={i.id}
                className={"aw-icon-btn " + (tab === i.id ? "active" : "")}
                onClick={() => setTab(i.id)}>
          <i.Icon/>
        </button>
      ))}
      <div className="aw-rail-sep"/>
      <button className="aw-icon-btn" title="Status">
        <span style={{width:8,height:8,borderRadius:"50%",background:"var(--grn)",boxShadow:"0 0 0 2px rgba(79,138,91,.18)"}}/>
      </button>
    </div>
  );
}

ReactDOM.createRoot(document.getElementById("root")).render(<App/>);
