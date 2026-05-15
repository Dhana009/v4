// app.jsx — top-level glue: stage + panel chrome + active tab + tweaks
const { useState, useEffect } = React;

const TWEAK_DEFAULTS = /*EDITMODE-BEGIN*/{
  "tab": "llm",
  "state": "exec",
  "dock": "right",
  "panelWidth": 480,
  "collapsed": false,
  "connection": "connected",
  "showWebsite": true,
  "highlight": "pro-cta"
}/*EDITMODE-END*/;

// Map "state" tweak → footer / header status / phase strings
const STATE_META = {
  idle:      { phase: "Idle",                  event: "session ready · waiting on user", next: "Describe a flow",        conn: "connected", busy: false },
  planning:  { phase: "Analyzing page",        event: "dom_query · 814 nodes scanned",   next: "Awaiting plan",          conn: "connected", busy: true },
  clarify:   { phase: "Clarification needed",  event: "asked about test depth",          next: "Answer to continue",     conn: "connected", busy: false },
  recommend: { phase: "Recommendation review", event: "rendered 6 candidate assertions", next: "Use selected",           conn: "connected", busy: false },
  plan:      { phase: "Plan review",           event: "plan_ready · 6 steps · ~28s",     next: "Confirm & run",          conn: "connected", busy: false },
  diff:      { phase: "Plan revision",         event: "plan_v2 · +1 / -1",               next: "Apply changes",          conn: "connected", busy: false },
  permit:    { phase: "Permission required",   event: "medium-risk click on a.btn.primary", next: "Allow or deny",       conn: "connected", busy: false },
  exec:      { phase: "Executing",             event: "stp_c4d7 · resolving locator…",   next: "Wait or pause",          conn: "busy",      busy: true },
  locator:   { phase: "Locator ambiguity",     event: "3 matches for \"Get started\"",   next: "Choose candidate",       conn: "connected", busy: false, blocker: "ambiguous locator" },
  recover:   { phase: "Recovery needed",       event: "stp_e1f4 · assertion mismatch",   next: "Apply LLM repair",       conn: "connected", busy: false, blocker: "1 failed step" },
  done:      { phase: "Completed",             event: "run_completed · 5/6 + 1 repaired", next: "Replay or save suite", conn: "connected", busy: false },
  offline:   { phase: "Disconnected",          event: "ws closed · attempt 2 of 5",      next: "Reconnect",              conn: "offline",   busy: false, blocker: "backend unreachable" },
  schema:    { phase: "Schema invalid",        event: "llm response failed plan.v3",     next: "Ask LLM to repair",      conn: "error",     busy: false, blocker: "invalid plan payload" },
};

function App() {
  const [t, setTweak] = useTweaks(TWEAK_DEFAULTS);
  const [tab, setTabLocal] = useState(t.tab);
  // keep local tab in sync with tweak when changed via panel
  useEffect(() => { setTabLocal(t.tab); }, [t.tab]);

  const setTab = (id) => { setTabLocal(id); setTweak("tab", id); };
  const setDock = (d) => setTweak("dock", d);
  const setCollapsed = (v) => setTweak("collapsed", v);

  const meta = STATE_META[t.state] || STATE_META.idle;
  const statusKey = meta.conn === "offline" ? "offline"
                  : meta.conn === "error"   ? "error"
                  : meta.conn === "busy"    ? "busy"
                  : t.connection === "reconnect" ? "reconnect"
                  : "connected";

  const runId = t.state === "idle" ? "—" : "run_a91b";
  const tokenInfo = { tok: "8.4k", cost: "0.12" };

  const counts = {
    llm: null,
    steps: 5,
    rec: 4,
    code: 1,
    trace: 25,
  };

  const stageCls = "aw-stage dock-" + t.dock + (t.collapsed ? " collapsed" : "");

  // Auto-scroll body to bottom on state/tab change so latest content is in view
  const bodyRef = React.useRef(null);
  useEffect(() => {
    if (bodyRef.current) bodyRef.current.scrollTop = bodyRef.current.scrollHeight;
  }, [t.state, tab]);

  // tab body
  let body;
  if (tab === "llm")        body = <LlmThread state={t.state}/>;
  else if (tab === "steps") body = <StepsTab/>;
  else if (tab === "rec")   body = <RecordedTab/>;
  else if (tab === "code")  body = <CodeTab/>;
  else if (tab === "trace") body = <TraceTab/>;

  // ----- panel render -----
  const panel = (
    <aside className="aw-panel" style={{width: t.dock === "top" ? "100%" : t.panelWidth}}>
      <div className="aw-resize"/>
      {!t.collapsed && (
        <>
          <Header
            status={statusKey}
            dock={t.dock} setDock={setDock}
            collapsed={t.collapsed} setCollapsed={setCollapsed}
            tokenInfo={tokenInfo}
            runState={runId}
          />
          <TabStrip tab={tab} setTab={setTab} counts={counts}/>
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
                       "offline","schema"
                     ]}
                     onChange={(v) => setTweak("state", v)}/>

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
