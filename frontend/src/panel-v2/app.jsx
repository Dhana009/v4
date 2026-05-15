// app.jsx — top-level glue: stage + panel chrome + tabs + tweaks + agents + now-strip
import './styles.css';
import { useState, useEffect, useRef, useMemo } from 'react';
import { I } from './icons.jsx';
import { useTweaks, TweaksPanel, TweakSection, TweakRadio, TweakSlider, TweakToggle, TweakSelect } from './tweaks-panel.jsx';
import { Website } from './website.jsx';
import { Header, TabStrip, NowStrip, Footer, AgentsPopover } from './chrome.jsx';
import { LlmThread, Composer } from './llm-tab.jsx';
import { StepsTab, RecordedTab, CodeTab, TraceTab } from './secondary-tabs.jsx';
import { DEMO_TWEAK_DEFAULTS, DEMO_STATE_META } from '../panel-v2-adapter/demo-bridge.js';

export function App({ viewModel, onCommand, mode, onCollapseChange, onDockChange } = {}) {
  const isLive = mode === "live" && viewModel != null;

  const tweakDefaults = useMemo(() => {
    try {
      const saved = localStorage.getItem("aw-theme");
      if (saved === "dark" || saved === "light") return { ...DEMO_TWEAK_DEFAULTS, theme: saved };
    } catch {}
    return DEMO_TWEAK_DEFAULTS;
  }, []);
  const [t, setTweak] = useTweaks(tweakDefaults);
  const [tab, setTabLocal] = useState(isLive ? "llm" : t.tab);
  useEffect(() => { if (!isLive) setTabLocal(t.tab); }, [t.tab, isLive]);

  const setTab = (id) => { setTabLocal(id); if (!isLive) setTweak("tab", id); };
  const setDock = (d) => {
    setTweak("dock", d);
    if (isLive && typeof onDockChange === "function") onDockChange(d);
  };
  const setCollapsed = (v) => setTweak("collapsed", v);
  const setAgentsOpen = (v) => setTweak("agentsOpen", v);

  // Notify outer host of collapse state changes (live only).
  useEffect(() => {
    if (isLive && typeof onCollapseChange === "function") {
      onCollapseChange(!!t.collapsed);
    }
  }, [t.collapsed, isLive, onCollapseChange]);

  // Apply theme. In live mode, write to the shadow host element when mounted
  // inside a ShadowRoot so :host([data-theme]) tokens apply. Fall back to
  // documentElement when no shadow root (preview/iframe/standalone).
  const panelRef = useRef(null);
  useEffect(() => {
    const theme = t.theme || "light";
    try { localStorage.setItem("aw-theme", theme); } catch {}
    if (isLive) {
      const node = panelRef.current;
      const rootNode = node && typeof node.getRootNode === "function" ? node.getRootNode() : null;
      const hostEl =
        rootNode && typeof rootNode === "object" && "host" in rootNode ? rootNode.host : null;
      if (hostEl && typeof hostEl.setAttribute === "function") {
        hostEl.setAttribute("data-theme", theme);
        return;
      }
    }
    document.documentElement.dataset.theme = theme;
  }, [t.theme, isLive]);

  // — Live mode derived values ——————————————————————————
  const livePhase = isLive ? (viewModel.runtime?.phase ?? "idle") : null;
  const liveRunId = isLive ? (viewModel.runtime?.runId ?? null) : null;
  const liveCounts = isLive ? (viewModel.counts ?? { steps: 0, rec: 0, code: 0, trace: 0 }) : null;
  const liveConnection = isLive ? (viewModel.runtime?.connection ?? "connected") : null;
  const liveAgents = isLive ? (Array.isArray(viewModel.agents) ? viewModel.agents : null) : null;

  // — Demo mode derived values ——————————————————————————
  const meta = DEMO_STATE_META[t.state] || DEMO_STATE_META.idle;

  const statusKey = isLive
    ? (liveConnection === "offline" ? "offline" : liveConnection === "busy" ? "busy" : "connected")
    : (meta.conn === "offline" ? "offline"
     : meta.conn === "error"   ? "error"
     : meta.conn === "busy"    ? "busy"
     : t.connection === "reconnect" ? "reconnect"
     : "connected");

  const runId = isLive ? liveRunId : (t.state === "idle" ? "—" : "run_a91b");
  const tokenInfo = { tok: "8.4k", cost: "0.12" };
  const counts = isLive ? liveCounts : { llm: null, steps: 5, rec: 4, code: 1, trace: 25 };

  const activeState = isLive ? livePhase : t.state;

  // Agents summary dots (5 visible)
  const agentsSummary = (() => {
    const isRun = ["exec","locator","recover"].includes(activeState);
    const isPlanning = ["planning","clarify","recommend","plan","diff"].includes(activeState);
    return [
      isRun || isPlanning ? "on" : "on",
      activeState === "planning" ? "run" : "on",
      isRun ? "run" : "on",
      activeState === "recover" ? "on" : "off",
      "off",
    ];
  })();

  const stageCls = "aw-stage dock-" + t.dock + (t.collapsed ? " collapsed" : "");

  // Auto-scroll body to bottom on state/tab change
  const bodyRef = useRef(null);
  useEffect(() => {
    if (bodyRef.current) bodyRef.current.scrollTop = bodyRef.current.scrollHeight;
  }, [activeState, tab]);

  // tab body
  let body;
  if (tab === "llm")        body = <LlmThread state={activeState} mode={t.mode} onCommand={isLive ? onCommand : undefined} runId={isLive ? runId : undefined}/>;
  else if (tab === "steps") body = <StepsTab mode={t.mode} setMode={(v) => setTweak("mode", v)}/>;
  else if (tab === "rec")   body = <RecordedTab/>;
  else if (tab === "code")  body = <CodeTab/>;
  else if (tab === "trace") body = <TraceTab/>;

  const showNow = tab === "llm" && activeState !== "idle";

  const panelStyle = isLive
    ? { width: "100%", height: "100%" }
    : { width: t.dock === "top" ? "100%" : t.panelWidth };

  const wide = isLive || t.dock === "top" || t.panelWidth >= 620 ? "1" : "0";

  const panel = (
    <aside ref={panelRef} className="aw-panel"
           data-wide={wide}
           style={panelStyle}>
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
            isLive={isLive}
          />
          <TabStrip tab={tab} setTab={setTab} counts={counts}/>
          {showNow && <NowStrip {...(isLive ? {} : meta.now)}/>}
          <div className="aw-panel-body" ref={bodyRef}>
            {body}
          </div>
          {tab === "llm" && activeState !== "idle" && (
            <Composer
              onCommand={isLive ? onCommand : undefined}
              runId={isLive ? runId : undefined}
            />
          )}
          <Footer
            phase={isLive ? livePhase : meta.phase}
            event={isLive ? undefined : meta.event}
            blocker={isLive ? undefined : meta.blocker}
            nextAction={isLive ? undefined : meta.next}
            busy={isLive ? undefined : meta.busy}
          />
          {t.agentsOpen && (
            <AgentsPopover
              state={activeState}
              onClose={() => setAgentsOpen(false)}
              isLive={isLive}
              agents={liveAgents}
            />
          )}
        </>
      )}
      {t.collapsed && <CollapsedRail tab={tab} setTab={(id)=>{ setTab(id); setCollapsed(false); }} setCollapsed={setCollapsed}/>}
    </aside>
  );

  if (isLive) {
    return (
      <>
        {panel}
        <TweaksPanel>
          <TweakSection label="Theme"/>
          <TweakRadio label="Theme" value={t.theme}
                      options={["light","dark"]}
                      onChange={(v) => setTweak("theme", v)}/>
          <TweakSection label="Interaction mode"/>
          <TweakRadio label="Mode" value={t.mode}
                      options={["llm","manual"]}
                      onChange={(v) => setTweak("mode", v)}/>
        </TweaksPanel>
      </>
    );
  }

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

export function CollapsedRail({ tab, setTab, setCollapsed }) {
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
