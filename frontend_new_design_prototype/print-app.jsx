// print-app.jsx — multi-page print layout: one PrintFrame per page
const PRINT_STATE_META = window.STATE_META;

function PrintFrame({ tab = "llm", state = "exec", dock = "right", panelWidth = 480, collapsed = false, agentsOpen = false, highlight = "pro-cta", label, caption }) {
  const meta = PRINT_STATE_META[state] || PRINT_STATE_META.idle;
  const statusKey =
    meta.conn === "offline" ? "offline" :
    meta.conn === "error"   ? "error"   :
    meta.conn === "busy"    ? "busy"    : "connected";
  const runId = state === "idle" ? "—" : "run_a91b";
  const tokenInfo = { tok: "8.4k", cost: "0.12" };
  const counts = { llm: null, steps: 5, rec: 4, code: 1, trace: 25 };

  const agentsSummary = (() => {
    const isRun = ["exec","locator","recover"].includes(state);
    const isPlanning = ["planning","clarify","recommend","plan","diff"].includes(state);
    return [
      isRun || isPlanning ? "on" : "on",
      state === "planning" ? "run" : "on",
      isRun ? "run" : "on",
      state === "recover" ? "on" : "off",
      "off",
    ];
  })();

  // Scroll body to bottom so the latest cards/rows are in view in print
  const bodyRef = React.useRef(null);
  React.useEffect(() => {
    if (bodyRef.current) bodyRef.current.scrollTop = bodyRef.current.scrollHeight;
  }, []);

  let body;
  if (tab === "llm")        body = <LlmThread state={state}/>;
  else if (tab === "steps") body = <StepsTab/>;
  else if (tab === "rec")   body = <RecordedTab/>;
  else if (tab === "code")  body = <CodeTab/>;
  else if (tab === "trace") body = <TraceTab/>;

  const showNow = tab === "llm" && state !== "idle";
  const stageCls = "aw-stage dock-" + dock + (collapsed ? " collapsed" : "");

  return (
    <div className="pf-page">
      <header className="pf-label">
        <span className="pf-lab-i">{label.i}</span>
        <span className="pf-lab-t">{label.t}</span>
        {caption && <span className="pf-lab-c">{caption}</span>}
        <span className="pf-lab-tab">{tab.toUpperCase()} TAB · DOCK {dock.toUpperCase()}</span>
      </header>
      <div className="pf-stage-wrap">
        <div className={stageCls}>
          <main className="aw-site">
            <Website highlight={highlight}/>
          </main>
          <aside className="aw-panel"
                 data-wide={(dock === "top" || panelWidth >= 620) ? "1" : "0"}
                 style={{width: dock === "top" ? "100%" : panelWidth}}>
            {!collapsed && (
              <>
                <Header
                  status={statusKey}
                  dock={dock} setDock={()=>{}}
                  collapsed={collapsed} setCollapsed={()=>{}}
                  tokenInfo={tokenInfo}
                  runState={runId}
                  agentsOpen={agentsOpen}
                  setAgentsOpen={()=>{}}
                  agentsSummary={agentsSummary}
                />
                <TabStrip tab={tab} setTab={()=>{}} counts={counts}/>
                {showNow && <NowStrip {...meta.now}/>}
                <div className="aw-panel-body" ref={bodyRef}>
                  {body}
                </div>
                {tab === "llm" && state !== "idle" && <Composer/>}
                <Footer
                  phase={meta.phase}
                  event={meta.event}
                  blocker={meta.blocker}
                  nextAction={meta.next}
                  busy={meta.busy}
                />
                {agentsOpen && <AgentsPopover state={state} onClose={()=>{}}/>}
              </>
            )}
            {collapsed && <PrintCollapsedRail tab={tab}/>}
          </aside>
        </div>
      </div>
    </div>
  );
}

function PrintCollapsedRail({ tab }) {
  const items = [
    { id: "llm",   Icon: I.Spark },
    { id: "steps", Icon: I.Steps },
    { id: "rec",   Icon: I.Camera },
    { id: "code",  Icon: I.Code },
    { id: "trace", Icon: I.Trace },
  ];
  return (
    <div className="aw-collapsed-rail">
      <button className="aw-icon-btn"><I.CaretR style={{transform:"rotate(180deg)"}}/></button>
      <div className="aw-rail-sep"/>
      {items.map(i => (
        <button key={i.id} className={"aw-icon-btn " + (tab === i.id ? "active" : "")}>
          <i.Icon/>
        </button>
      ))}
      <div className="aw-rail-sep"/>
      <button className="aw-icon-btn">
        <span style={{width:8,height:8,borderRadius:"50%",background:"var(--grn)",boxShadow:"0 0 0 2px rgba(79,138,91,.18)"}}/>
      </button>
    </div>
  );
}

const PRINT_PAGES = [
  // --- LLM tab lifecycle ---
  { label: { i: "01", t: "Plan review" },
    caption: "Plan v2 is drafted. The Current Task strip pins the next decision, the card carries a Decision Required badge, and the source tag credits the backend event plan_ready.",
    tab: "llm", state: "plan", highlight: "none" },

  { label: { i: "02", t: "Executing · with agents" },
    caption: "Step 3 of 6 is running. Agent Control Center is open to show which agents are active (Orchestrator, Step Runner) and which are standby.",
    tab: "llm", state: "exec", highlight: "pro-cta", agentsOpen: true },

  { label: { i: "03", t: "Locator ambiguity — blocking" },
    caption: "Three visible \"Get started\" links. The card carries a red left rail and \"Execution paused\" badge so the blocker is unmissable.",
    tab: "llm", state: "locator", highlight: "hero-cta" },

  { label: { i: "04", t: "Recovery & repair" },
    caption: "Assertion failed; deterministic retries exhausted. Debug Agent has surfaced an LLM repair proposal — only applies with user consent.",
    tab: "llm", state: "recover", highlight: "pro-cta" },

  { label: { i: "05", t: "Run completed · E2E pending" },
    caption: "Local run recorded cleanly. Frontend explicitly does not infer acceptance — paid E2E suite has its own gate.",
    tab: "llm", state: "e2e", highlight: "none" },

  // --- Other tabs ---
  { label: { i: "06", t: "Steps — user-guided plan" },
    caption: "Stable step IDs, weak-locator warning, missing test-data block, wrong-page precondition, and a section step with child operations.",
    tab: "steps", state: "exec", highlight: "none" },

  { label: { i: "07", t: "Recorded — backend evidence" },
    caption: "Backend-emitted recordings only. Repaired step shows old → new locator diff; skipped steps appear but never counted as recorded.",
    tab: "rec", state: "done", highlight: "none" },

  { label: { i: "08", t: "Code — emitted by backend" },
    caption: "Playwright spec rendered from code_update events, mapped to recorded step IDs. Inline warnings flag fragile locators and skipped operations.",
    tab: "code", state: "done", highlight: "none" },

  { label: { i: "09", t: "Trace — debugging timeline" },
    caption: "Structured event log with type-tagged rows, filters, and a sticky failure-detail panel showing expected/actual/layer/next legal actions.",
    tab: "trace", state: "done", highlight: "none" },

  // --- Docking modes ---
  { label: { i: "10", t: "Dock left" },
    caption: "Panel docks to the left of the website. Same five-tab interface; website resizes beside the panel rather than being covered.",
    tab: "llm", state: "plan", dock: "left", highlight: "none" },

  { label: { i: "11", t: "Dock top" },
    caption: "Panel docks above the website with a wider 1-column conversation layout. Useful for ultra-wide monitors or pair-debugging sessions.",
    tab: "llm", state: "exec", dock: "top", panelWidth: 1400, highlight: "pro-cta" },

  { label: { i: "12", t: "Collapsed rail" },
    caption: "Slim rail that surfaces the five tabs and connection status without covering content. Click any icon to expand the panel into that tab.",
    tab: "llm", state: "exec", collapsed: true, highlight: "pro-cta" },

  { label: { i: "13", t: "Floating panel" },
    caption: "Panel detaches from the dock and floats over the page. Marked explicitly so users know it may cover content while floating.",
    tab: "llm", state: "plan", dock: "float", highlight: "none" },

  // --- Edge cases ---
  { label: { i: "14", t: "Edge — backend / schema / API key" },
    caption: "Backend unavailable: frontend holds state, never invents lifecycle. Connection log + reconnect controls live in the panel, not toasts.",
    tab: "llm", state: "offline", highlight: "none" },

  { label: { i: "15", t: "Edge — no browser, OTP / human input" },
    caption: "Backend is connected but there is no Playwright context to drive. The plan can be drafted but execution is blocked until a browser is attached.",
    tab: "llm", state: "nobrowser", highlight: "none" },

  { label: { i: "16", t: "Edge — OTP / 2FA · human input" },
    caption: "Step Runner emits a human_input event when it can't progress alone. Submit the code, skip the step, or pause the run for manual login.",
    tab: "llm", state: "otp", highlight: "none" },
];

function PrintApp() {
  return (
    <div className="pf-deck">
      <div className="pf-cover pf-page">
        <div className="pf-cover-inner">
          <div className="pf-cover-logo">
            <span className="aw-logo" style={{width:38,height:38,borderRadius:10}}/>
          </div>
          <div className="pf-cover-eyebrow">AutoWorkbench / Playwright Co-pilot · v2</div>
          <h1 className="pf-cover-title">Complete LLM Mode — frontend reference</h1>
          <p className="pf-cover-sub">
            A docked Shadow-DOM panel that lets a QA engineer plan, run, record,
            debug, and repair Playwright flows. Backend events drive lifecycle truth;
            the frontend renders typed cards and routes typed commands. v2 adds a
            Current Task strip, an Agent Control Center, sharper active-state visuals,
            and explicit dock / float / collapsed proofs.
          </p>
          <div className="pf-toc">
            {PRINT_PAGES.map(p => (
              <div key={p.label.i} className="pf-toc-row">
                <span className="pf-toc-i">{p.label.i}</span>
                <span className="pf-toc-t">{p.label.t}</span>
                <span className="pf-toc-tab">{p.tab.toUpperCase()}</span>
              </div>
            ))}
          </div>
          <div className="pf-cover-foot">
            <span>{PRINT_PAGES.length} frames · landscape · {new Date().toLocaleDateString("en-US", { year:"numeric", month:"long", day:"numeric" })}</span>
            <span>generated for print from index.html</span>
          </div>
        </div>
      </div>
      {PRINT_PAGES.map((p, i) => <PrintFrame key={i} {...p}/>)}
    </div>
  );
}

ReactDOM.createRoot(document.getElementById("root")).render(<PrintApp/>);

// — Auto-print after fonts + transforms + scrolls settle ——————————
(async function autoPrint() {
  if (window.__noPrint) return;
  try { if (document.fonts && document.fonts.ready) await document.fonts.ready; } catch(e) {}
  for (let i = 0; i < 60; i++) {
    if (document.querySelectorAll(".pf-page").length >= PRINT_PAGES.length + 1) break;
    await new Promise(r => setTimeout(r, 100));
  }
  // Scroll each panel-body to bottom after another tick
  document.querySelectorAll(".aw-panel-body").forEach(el => el.scrollTop = el.scrollHeight);
  await new Promise(r => setTimeout(r, 600));
  document.querySelectorAll(".aw-panel-body").forEach(el => el.scrollTop = el.scrollHeight);
  await new Promise(r => setTimeout(r, 400));
  window.print();
})();
