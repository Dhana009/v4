// chrome.jsx — panel header, status, tab strip, footer
const { useState } = React;

function Header({ status, dock, setDock, collapsed, setCollapsed, onFloat, tokenInfo, runUrl, runState }) {
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

window.Header = Header;
window.TabStrip = TabStrip;
window.Footer = Footer;
