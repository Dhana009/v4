// app.jsx — top-level glue: stage + panel chrome + tabs + tweaks + agents + now-strip
import { useState, useEffect, useRef } from 'react';
import { I } from './icons.jsx';
import { useTweaks, TweaksPanel, TweakSection, TweakRadio, TweakSlider, TweakToggle, TweakSelect } from './tweaks-panel.jsx';
import { Website } from './website.jsx';
import { Header, TabStrip, NowStrip, Footer, AgentsPopover } from './chrome.jsx';
import { LlmThread, Composer } from './llm-tab.jsx';
import { StepsTab, RecordedTab, CodeTab, TraceTab } from './secondary-tabs.jsx';
import { DEMO_TWEAK_DEFAULTS, DEMO_STATE_META } from '../panel-v2-adapter/demo-bridge.js';

export function App() {
  const [t, setTweak] = useTweaks(DEMO_TWEAK_DEFAULTS);
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

  const meta = DEMO_STATE_META[t.state] || DEMO_STATE_META.idle;
  const statusKey = meta.conn === "offline" ? "offline"
                  : meta.conn === "error"   ? "error"
                  : meta.conn === "busy"    ? "busy"
                  : t.connection === "reconnect" ? "reconnect"
                  : "connected";

  const runId = t.state === "idle" ? "—" : "run_a91b";
  const tokenInfo = { tok: "8.4k", cost: "0.12" };
  const counts = { llm: null, steps: 5, rec: 4, code: 1, trace: 25 };

  // Agents summary dots (5 visible)
  const agentsSummary = (() => {
    const isRun = ["exec","locator","recover"].includes(t.state);
    const isPlanning = ["planning","clarify","recommend","plan","diff"].includes(t.state);
    return [
      isRun || isPlanning ? "on" : "on",       // Main Orchestrator (always at least on)
      t.state === "planning" ? "run" : "on",   // Page Intelligence
      isRun ? "run" : "on",                    // Step Runner
      t.state === "recover" ? "on" : "off",    // Debug Agent
      "off",                                    // Risk Judge
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
          <TabStrip tab={tab} setTab={setTab} counts={counts}/>
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
