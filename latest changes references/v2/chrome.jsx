// chrome.jsx — panel header, status, tab strip, footer, current-task, agents
const { useState: useStateChrome } = React;

function Header({ status, dock, setDock, collapsed, setCollapsed, tokenInfo, runState,
                  agentsOpen, setAgentsOpen, agentsSummary }) {
  const dockBtn = (kind, Icon, title) => (
    <button className={"aw-icon-btn " + (dock === kind ? "active" : "")}
            onClick={() => setDock(kind)} title={title} aria-label={title}>
      <Icon/>
    </button>
  );

  const statusMap = {
    connected: { cls: "ok",   label: "Connected",     dot: true },
    busy:      { cls: "busy", label: "Running",       dot: true },
    reconnect: { cls: "warn", label: "Reconnecting…", dot: true },
    offline:   { cls: "err",  label: "Backend unavailable", dot: true },
    error:     { cls: "err",  label: "LLM provider error", dot: true },
  };
  const s = statusMap[status] || statusMap.connected;

  return (
    <header className="aw-header">
      <div className="aw-header-main">
        <div className="aw-brand">
          <span className="aw-logo" aria-hidden="true"/>
          <span>AutoWorkbench</span>
          <span className="aw-brand-sub">/ Playwright Co-pilot</span>
        </div>
        <div className="aw-spacer"/>
        <button className="aw-icon-btn" title="History"><I.Folder/></button>
        <button className="aw-icon-btn" title="New session"><I.Plus/></button>
        {dockBtn("right", I.Dock,   "Dock right")}
        {dockBtn("left",  I.DockL,  "Dock left")}
        {dockBtn("top",   I.DockTop,"Dock top")}
        {dockBtn("float", I.Float,  "Float")}
        <button className="aw-icon-btn" onClick={() => setCollapsed(!collapsed)} title="Collapse"><I.Min/></button>
        <button className="aw-icon-btn" title="Settings"><I.Settings/></button>
      </div>
      <div className="aw-status-strip">
        <span className={"aw-status-pill " + s.cls}>
          <span className="aw-dot"/>{s.label}
        </span>
        <span className="aw-status-pill mode">
          <span className="aw-dot"/>Complete LLM Mode
        </span>
        <button className={"aw-agents-btn " + (agentsOpen ? "open" : "")}
                onClick={() => setAgentsOpen(!agentsOpen)}
                title="Agent Control Center">
          <I.Layers style={{width:11,height:11}}/>
          <span>Agents</span>
          <span className="dots">
            {agentsSummary.map((s, i) => <i key={i} className={s}/>)}
          </span>
        </button>
        <span className="aw-status-pill" title="Active page">
          <I.Globe style={{width:11,height:11,color:"var(--tx-3)"}}/>
          <span className="k">page</span>
          <span className="v">acme.dev/pricing</span>
        </span>
        <span className="aw-status-pill" title="Run id">
          <span className="k">run</span>
          <span className="v" style={{fontFamily:"var(--ff-mono)"}}>{runState}</span>
        </span>
        <span className="aw-spacer"/>
        <span className="aw-status-pill" title="Token usage this session">
          <span className="k">tok</span><span className="v">{tokenInfo.tok}</span>
          <span className="k">·</span><span className="v">${tokenInfo.cost}</span>
        </span>
      </div>
    </header>
  );
}

function TabStrip({ tab, setTab, counts }) {
  const tabs = [
    { id: "llm",   label: "LLM",      Icon: I.Spark, badge: counts.llm },
    { id: "steps", label: "Steps",    Icon: I.Steps, badge: counts.steps },
    { id: "rec",   label: "Recorded", Icon: I.Camera, badge: counts.rec },
    { id: "code",  label: "Code",     Icon: I.Code,   badge: counts.code },
    { id: "trace", label: "Trace",    Icon: I.Trace,  badge: counts.trace },
  ];
  return (
    <nav className="aw-tabs" role="tablist">
      {tabs.map(t => (
        <button key={t.id}
                role="tab"
                aria-selected={tab === t.id}
                className={"aw-tab " + (tab === t.id ? "active" : "")}
                onClick={() => setTab(t.id)}>
          <t.Icon style={{width:13, height:13}}/>
          {t.label}
          {t.badge != null && <span className="aw-badge">{t.badge}</span>}
        </button>
      ))}
    </nav>
  );
}

function NowStrip({ kind = "idle", state, task, refLabel, primaryLabel, primaryIcon: PI }) {
  return (
    <div className={"aw-now " + kind}>
      <span className="aw-now-rail"/>
      <div className="aw-now-main">
        <div className="aw-now-eyebrow">
          Current task
          <span className="aw-now-state">{state}</span>
        </div>
        <div className="aw-now-task">
          {task}
          {refLabel && <span className="ref">{refLabel}</span>}
        </div>
      </div>
      {primaryLabel && (
        <div className="aw-now-actions">
          <button className="aw-btn primary">
            {PI && <PI/>}
            {primaryLabel}
          </button>
        </div>
      )}
    </div>
  );
}

function Footer({ phase, event, blocker, nextAction, busy }) {
  return (
    <footer className="aw-footer">
      <span className="aw-footer-phase">
        {busy && <span className="aw-bar"><i/><i/><i/><i/></span>}
        {phase}
      </span>
      <span className="aw-footer-event">
        <span className="em">last:</span> {event}
        {blocker && <> · <span style={{color:"var(--red)", fontWeight:500}}>blocked: {blocker}</span></>}
      </span>
      {nextAction && (
        <span className="aw-footer-next">
          <I.CaretR style={{width:11,height:11}}/>
          {nextAction}
        </span>
      )}
    </footer>
  );
}

// — Agent Control Center —————————————————————————

function AgentsPopover({ onClose, state }) {
  // state lets us flex agent statuses to match the current run state
  const isRunning = ["exec","locator","recover"].includes(state);
  const isDone = state === "done";
  const orchestratorStatus = state === "idle" ? "standby"
                           : (state === "planning" || state === "diff" || state === "plan" || state === "recommend") ? "active"
                           : isRunning ? "running"
                           : "active";
  const stepRunnerStatus  = isRunning ? "running" : (isDone ? "standby" : "standby");
  const debugStatus       = state === "recover" ? "active" : "standby";
  const codegenStatus     = (isRunning || isDone) ? "queued" : "standby";

  const agents = [
    {
      key: "orch", name: "Main Orchestrator", initials: "MO",
      model: "gpt-4-class · 200k ctx", status: orchestratorStatus,
      last: state === "exec"   ? "Watching step 3 · stp_c4d7"
          : state === "locator"? "Pausing run · 3 candidates"
          : state === "recover"? "Coordinating LLM repair proposal"
          : state === "plan"   ? "Drafted plan v2 · 6 steps"
          : state === "done"   ? "Run completed · 31.2s"
          :                      "Waiting on user input",
      required: true,
    },
    {
      key: "pi", name: "Page Intelligence", initials: "PI",
      model: "claude-haiku-class · DOM tool",
      status: state === "planning" ? "running" : "standby",
      last: <>Cached <span style={{fontFamily:"var(--ff-mono)",color:"var(--tx-2)"}}>acme.dev/pricing</span> · 18 sections · 14s ago</>,
      required: false, toggle: true, ctrl: ["Run now","Clear cache"],
    },
    {
      key: "sr", name: "Step Runner", initials: "SR",
      model: "internal · Playwright runtime",
      status: stepRunnerStatus,
      last: isRunning ? "Validating locator stp_c4d7 (resolve)" : "Idle · awaiting plan confirmation",
      required: true,
    },
    {
      key: "dbg", name: "Debug Agent", initials: "DA",
      model: "gpt-4-class · trace-aware",
      status: debugStatus,
      last: state === "recover" ? "Proposed: relax toHaveText → toContainText(\"$49\")"
                                : "Auto-activates on any step failure",
      required: false, toggle: true,
    },
    {
      key: "cg", name: "Codegen Reviewer", initials: "CR",
      model: "gpt-4-class · style + locator linter",
      status: codegenStatus,
      last: isDone ? "Reviewed +47 lines · 1 fragile locator flagged"
                   : "Runs after each recorded step",
      required: false, toggle: true,
    },
    {
      key: "judge", name: "Risk Judge (opt-in)", initials: "RJ",
      model: "claude-class · policy-grader",
      status: "disabled",
      last: "Off · enable to grade high-risk operations before execution",
      required: false, toggle: false,
    },
  ];

  return (
    <div className="aw-agents-pop" role="dialog" aria-label="Agent Control Center">
      <div className="aw-agents-head">
        <span className="aw-card-icon" style={{width:22,height:22,borderRadius:6,background:"var(--acc-tint)",color:"var(--acc-2)"}}>
          <I.Layers style={{width:12,height:12}}/>
        </span>
        <div>
          <div className="t">Agent Control Center</div>
        </div>
        <span className="sub">5 active · 1 off</span>
        <span className="x" onClick={onClose}><I.X style={{width:13,height:13}}/></span>
      </div>
      {agents.map(a => {
        const cls = (a.status === "running") ? "running"
                 : (a.status === "active")  ? "active"
                 : (a.status === "disabled")? "disabled"
                 : "standby";
        return (
          <div key={a.key} className={"aw-agent-row " + cls}>
            <span className="aw-agent-av">{a.initials}</span>
            <div>
              <div className="aw-agent-name">
                {a.name}
                {a.required && <span className="aw-pin-required">Required</span>}
              </div>
              <div className="aw-agent-model">{a.model}</div>
              <div className="aw-agent-last">
                <span className="em">last:</span> {a.last}
              </div>
              {a.ctrl && (
                <div style={{display:"flex",gap:6,marginTop:7}}>
                  {a.ctrl.map(c => (
                    <button key={c} className="aw-btn" style={{padding:"3px 8px",fontSize:11}}>{c}</button>
                  ))}
                </div>
              )}
            </div>
            <div className="aw-agent-ctrl">
              <span className={"aw-agent-status " + cls}>
                <span className="ldot"/>
                {a.status === "queued" ? "queued" : a.status}
              </span>
              {a.toggle != null && (
                a.required
                  ? <button className="aw-toggle on locked" aria-label="locked on" disabled/>
                  : <button className={"aw-toggle " + (a.status === "disabled" ? "" : "on")}/>
              )}
            </div>
          </div>
        );
      })}
      <div className="aw-agents-foot">
        <I.Info style={{width:11,height:11}}/>
        <span>Main Orchestrator and Step Runner cannot be disabled while LLM Mode is running.</span>
        <span style={{flex:1}}/>
        <button className="aw-link"><I.Trace style={{width:11,height:11,display:"inline",verticalAlign:"-1px",marginRight:3}}/>Open agent trace</button>
      </div>
    </div>
  );
}

window.Header = Header;
window.TabStrip = TabStrip;
window.Footer = Footer;
window.NowStrip = NowStrip;
window.AgentsPopover = AgentsPopover;
