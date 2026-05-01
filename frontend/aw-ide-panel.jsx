/* global React, Icons */
// Variation A — Editorial / IDE hybrid panel (light cream, monospace-forward)

const IDEIcons = window.Icons;

function IDECodeLine({ tokens }) {
  return <>{tokens.map((t, i) => typeof t === "string"
    ? <span key={i}>{t}</span>
    : <span key={i} className={`tk-${t[0]}`}>{t[1]}</span>)}</>;
}

function IDEPlanTag({ kind }) {
  const map = { click:"click", fill:"fill", assert:"assert", navigate:"nav", nav:"nav" };
  return <span className={`ide-plan-tag t-${map[kind]||kind}`}>{kind}</span>;
}

function IDEBadge({ kind, children }) {
  return <span className={`ide-badge b-${kind}`}>{children}</span>;
}

function IDECard({ color, title, children, footer }) {
  return (
    <div className={`ide-card c-${color||"ink"}`}>
      <div className="ide-card-hd">
        <div className="ide-card-hd-label">{title}</div>
      </div>
      <div className="ide-card-body">{children}</div>
      {footer && <div style={{ padding: "0 10px 10px", display: "flex", gap: 6 }}>{footer}</div>}
    </div>
  );
}

function IDEConversation({ state }) {
  const msgs = {
    idle: [{ w:"user", t:"10:41", txt:"Open playwright.dev, assert hero text exists, then click Get started." }],
    planning: [
      { w:"user", t:"10:41", txt:"Open playwright.dev, assert hero text exists, then click Get started." },
      { w:"agent", t:"10:41", txt:<><span className="ide-spinner" style={{color:"#4a9eff"}}/>Parsing task · inspecting DOM · ranking locators…</> },
    ],
    await: [
      { w:"user", t:"10:41", txt:"Open playwright.dev, assert hero text exists, then click Get started." },
      { w:"agent", t:"10:41", txt:"Understood. Detected 2 actions — plan ready for your review." },
    ],
    exec: [
      { w:"user", t:"10:41", txt:"Open playwright.dev, assert hero text, then click Get started." },
      { w:"agent", t:"10:42", txt:<><span className="ide-spinner" style={{color:"#4a9eff"}}/>Executing step 2 / 2 — clicking "Get started"…</> },
    ],
    recover: [
      { w:"user", t:"10:41", txt:"Open playwright.dev, assert hero text, then click Get started." },
      { w:"system", t:"10:42", txt:"Step failed: page navigated before assertion ran. Hero element no longer in DOM." },
      { w:"agent", t:"10:42", txt:"Recovery suggestion: go back → assert first → re-click." },
    ],
    done: [
      { w:"user", t:"10:41", txt:"Open playwright.dev, assert hero text, then click Get started." },
      { w:"agent", t:"10:42", txt:<><b style={{color:"#1f9d6a"}}>2/2 steps recorded.</b> Generated 4 lines of Playwright TS — see Code tab.</> },
    ],
  }[state] || [];
  return (
    <IDECard color="violet" title="// conversation">
      <div style={{ marginInline: -10 }}>
        {msgs.map((m, i) => (
          <div key={i} className="ide-msg">
            <div className="ide-msg-gutter">{m.t}</div>
            <div className="ide-msg-body">
              <div className={`ide-msg-who w-${m.w}`}>{m.w}</div>
              <div className="ide-msg-text">{m.txt}</div>
            </div>
          </div>
        ))}
      </div>
    </IDECard>
  );
}

function IDEPlan({ state }) {
  const items = state === "exec" || state === "done"
    ? [
        { type:"assert", text:"Assert hero heading is visible", cls: state==="done"?"done":"done" },
        { type:"click",  text:'Click "Get started" link',       cls: state==="done"?"done":"active" },
      ]
    : [
        { type:"assert", text:"Assert hero heading is visible", cls:"" },
        { type:"click",  text:'Click "Get started" link',       cls:"" },
      ];
  const isRecover = state === "recover";
  return (
    <IDECard color="blue" title="// plan" footer={[
      <button key="c" className="ide-btn primary" style={{ flex:1, justifyContent:"center" }}>✓ Confirm</button>,
      <button key="s" className="ide-btn" style={{ flex:1, justifyContent:"center" }}>↩ Correct</button>,
    ]}>
      <div style={{ display:"flex", alignItems:"center", gap:8, marginBottom:8 }}>
        <IDEBadge kind="await">Awaiting confirmation</IDEBadge>
        <span style={{ fontSize:10.5, color:"#9e9890" }}>2 actions · ~3s</span>
      </div>
      {isRecover && (
        <div className="ide-err-strip">
          <IDEIcons.Warn size={13} /> Order risk — click before assert caused navigation. Reorder steps.
        </div>
      )}
      <ol className="ide-plan">
        {items.map((it, i) => (
          <li key={i} className={it.cls}>
            <span className="ide-plan-num">{i+1}.</span>
            <span className="ide-plan-text">{it.text}</span>
            <IDEPlanTag kind={it.type} />
          </li>
        ))}
      </ol>
      <textarea className="ide-input" rows={2} style={{ marginTop:8 }} placeholder="Type correction…" />
    </IDECard>
  );
}

function IDETimeline({ state }) {
  const rows = ({
    idle: [],
    planning: [
      { d:"ok",     t:"10:41:30", txt:<>Task parsed <span className="dim">· 2 actions</span></> },
      { d:"active", t:"10:41:31", txt:"Ranking locator candidates…" },
    ],
    await: [
      { d:"ok",   t:"10:41:30", txt:"Task parsed · 2 actions" },
      { d:"ok",   t:"10:41:31", txt:"Locators ranked · 2 / 2" },
      { d:"warn", t:"10:41:32", txt:"Plan ready · awaiting confirmation" },
    ],
    exec: [
      { d:"ok",     t:"10:42:00", txt:"Plan confirmed" },
      { d:"ok",     t:"10:42:01", txt:"DOM snapshot · 1.2 MB" },
      { d:"ok",     t:"10:42:02", txt:"Assertion passed · hero visible" },
      { d:"active", t:"10:42:02", txt:'Clicking "Get started"…' },
    ],
    recover: [
      { d:"ok",  t:"10:42:00", txt:"Plan confirmed" },
      { d:"ok",  t:"10:42:02", txt:"Click executed" },
      { d:"warn",t:"10:42:14", txt:"Page navigated → /docs/intro" },
      { d:"err", t:"10:42:14", txt:"Assertion failed · hero not in DOM" },
    ],
    done: [
      { d:"ok", t:"10:42:00", txt:"Plan confirmed" },
      { d:"ok", t:"10:42:02", txt:"Assertion passed" },
      { d:"ok", t:"10:42:04", txt:"Click executed · /docs/intro" },
      { d:"ok", t:"10:42:05", txt:"Code generated · 4 lines" },
    ],
  })[state] || [];
  if (!rows.length) return null;
  return (
    <IDECard color="ink" title="// execution">
      <div className="ide-tl">
        {rows.map((r, i) => (
          <div key={i} className="ide-tl-row">
            <div className={`ide-tl-dot d-${r.d}`} />
            <div className="ide-tl-text">{r.txt}</div>
            <div className="ide-tl-time">{r.t}</div>
          </div>
        ))}
      </div>
    </IDECard>
  );
}

function IDERecovery() {
  return (
    <IDECard color="red" title="// recovery needed" footer={[
      <button key="s" className="ide-btn primary" style={{ flex:1, justifyContent:"center" }}>Send correction</button>,
      <button key="k" className="ide-btn">Skip</button>,
    ]}>
      <div className="ide-err-strip" style={{ marginBottom:10 }}>
        <IDEIcons.Warn size={12} />
        Click before assert → page navigated. Hero element missing from DOM on /docs/intro.
      </div>
      <div style={{ marginBottom:10, display:"grid", gridTemplateColumns:"1fr 1fr", gap:6, fontSize:11.5 }}>
        <div style={{ padding:"6px 8px", background:"#faf7f3", border:"1px solid #ede8e0", borderRadius:2 }}>
          <div style={{ fontSize:9.5, color:"#9e9890", textTransform:"uppercase", letterSpacing:".08em", marginBottom:2 }}>Was</div>
          <code style={{ fontSize:11 }}>playwright.dev/</code>
        </div>
        <div style={{ padding:"6px 8px", background:"#faf7f3", border:"1px solid #ede8e0", borderRadius:2 }}>
          <div style={{ fontSize:9.5, color:"#9e9890", textTransform:"uppercase", letterSpacing:".08em", marginBottom:2 }}>Now</div>
          <code style={{ fontSize:11 }}>/docs/intro</code>
        </div>
      </div>
      <div style={{ fontSize:11.5, color:"#4a4640", background:"#faf7f3", border:"1px solid #ede8e0", borderRadius:2, padding:"8px 10px", marginBottom:8 }}>
        <div style={{ fontSize:10, color:"#2a74d8", fontWeight:700, textTransform:"uppercase", letterSpacing:".07em", marginBottom:4 }}>// suggestion</div>
        <ol style={{ margin:0, paddingLeft:16, lineHeight:1.7 }}>
          <li>Go back to playwright.dev/</li><li>Assert hero text first</li><li>Re-attempt click</li>
        </ol>
      </div>
      <textarea className="ide-input" rows={2} placeholder="Add guidance…" />
    </IDECard>
  );
}

function IDERecorded({ done }) {
  return (
    <IDECard color={done?"green":null} title="// recorded output">
      <div className="ide-stats">
        <div className="ide-stat"><div className={`ide-stat-num${done?" s-green":""}`}>{done?"2":"0"}</div><div className="ide-stat-lbl">Recorded steps</div></div>
        <div className="ide-stat"><div className="ide-stat-num">{done?"4":"—"}</div><div className="ide-stat-lbl">Lines of code</div></div>
      </div>
      {done && (
        <pre className="ide-code" style={{ marginTop:8 }}>
          <IDECodeLine tokens={[["kw","await "],["fn","page.getByText"],"(",["str","'Get started'"],", { ",["prop","exact"],": ",["kw","true"]," }).",["fn","click"],"();"]} />
        </pre>
      )}
      <div style={{ display:"flex", gap:6, marginTop:10 }}>
        <button className="ide-btn sm" style={{ flex:1, justifyContent:"center" }}>Steps</button>
        <button className="ide-btn sm" style={{ flex:1, justifyContent:"center" }}>Code</button>
      </div>
    </IDECard>
  );
}

function IDEIdleComposer() {
  return (
    <IDECard color="blue" title="// new task">
      <textarea className="ide-input" rows={3} placeholder="// describe the task, e.g. open playwright.dev, assert hero text, then click Get started…" />
      <div style={{ display:"flex", gap:6, marginTop:8, justifyContent:"flex-end" }}>
        <button className="ide-btn primary">▶ Plan task</button>
      </div>
    </IDECard>
  );
}

function IDEHeader({ state }) {
  const labels = { idle:"idle", planning:"planning…", await:"awaiting confirmation", exec:"executing", recover:"recovery needed", done:"completed" };
  return (
    <div className="ide-hd">
      <div className="ide-hd-logo">AW</div>
      <div>
        <div className="ide-hd-title">AutoWorkbench</div>
        <div className="ide-hd-sub">playwright co-pilot</div>
      </div>
      <div className={`ide-hd-state s-${state}`}>{labels[state]}</div>
    </div>
  );
}

function IDEPanel({ state, tab }) {
  const stepCount = ["planning","await","exec","recover","done"].includes(state) ? 2 : 0;
  return (
    <div className="ide-panel">
      <IDEHeader state={state} />
      <div className="ide-tabs">
        {[["workbench","workbench"],["steps","steps"],["code","code"],["debug","debug"]].map(([id,label]) => (
          <button key={id} className={`ide-tab${tab===id?" active":""}`}>
            {label}{id==="steps" && stepCount>0 && <span className="ide-tab-badge">{stepCount}</span>}
          </button>
        ))}
      </div>
      <div className="ide-body">
        {tab === "workbench" && <>
          {state==="idle" && <IDEIdleComposer />}
          <IDEConversation state={state} />
          {["planning","await","exec","recover","done"].includes(state) && <IDETimeline state={state} />}
          {state==="await" && <IDEPlan state={state} />}
          {state==="recover" && <IDERecovery />}
          <IDECard color="amber" title="// pending steps">
            <div style={{ display:"flex", flexDirection:"column", gap:5 }}>
              {["01 · Assert hero text","02 · Click Get started"].map((s,i) => (
                <div key={i} style={{ display:"flex", gap:8, alignItems:"center", padding:"6px 8px", background:"#faf7f3", border:"1px solid #ede8e0", borderRadius:2, fontSize:12 }}>
                  <code style={{ fontSize:10, color:"#9e9890" }}>0{i+1}</code>
                  <span style={{ flex:1 }}>{s}</span>
                  <IDEBadge kind="ready">ready</IDEBadge>
                </div>
              ))}
            </div>
          </IDECard>
          {["exec","done"].includes(state) && <IDERecorded done={state==="done"} />}
          {state==="idle" && <IDERecorded done={false} />}
        </>}
      </div>
      {tab==="workbench" && (
        <div className="ide-bottom">
          <button className="ide-btn">+ Step</button>
          <button className="ide-btn primary" style={{ flex:1, justifyContent:"center" }}>▶ Run</button>
        </div>
      )}
    </div>
  );
}

window.IDEPanel = IDEPanel;
