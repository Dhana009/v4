/* global React, Icons */
// Variation B — Bold / Vercel-style panel (true black, high contrast, geometric)

const VRCIcons = window.Icons;

function VRCCodeLine({ tokens }) {
  return <>{tokens.map((t, i) => typeof t === "string"
    ? <span key={i}>{t}</span>
    : <span key={i} className={`tk-${t[0]}`}>{t[1]}</span>)}</>;
}

function VRCBadge({ kind, children }) {
  return <span className={`vrc-badge b-${kind}`}>{children}</span>;
}

function VRCPlanTag({ kind }) {
  const map = { click:"click", fill:"fill", assert:"assert", navigate:"nav", nav:"nav" };
  return <span className={`vrc-plan-tag t-${map[kind]||kind}`}>{kind}</span>;
}

function VRCCard({ color, title, children, footer }) {
  return (
    <div className={`vrc-card${color?" c-"+color:""}`}>
      <div className="vrc-card-hd">
        <div className="vrc-card-label">{title}</div>
        <div className="vrc-card-spacer" />
      </div>
      <div className="vrc-card-body">{children}</div>
      {footer && <div style={{ padding:"0 12px 12px", display:"flex", gap:6 }}>{footer}</div>}
    </div>
  );
}

function VRCConversation({ state }) {
  const msgs = {
    idle:     [{ w:"user",   name:"You",    t:"10:41", txt:"Open playwright.dev, assert hero text, then click Get started." }],
    planning: [
      { w:"user",  name:"You",   t:"10:41", txt:"Open playwright.dev, assert hero text, then click Get started." },
      { w:"agent", name:"Agent", t:"10:41", txt:<><span className="vrc-spinner" style={{color:"#60a5fa"}}/>Parsing task and inspecting DOM…</> },
    ],
    await: [
      { w:"user",  name:"You",   t:"10:41", txt:"Open playwright.dev, assert hero text, then click Get started." },
      { w:"agent", name:"Agent", t:"10:41", txt:"Detected 2 actions. Plan ready — confirm to run." },
    ],
    exec: [
      { w:"user",  name:"You",   t:"10:41", txt:"Open playwright.dev, assert hero text, then click Get started." },
      { w:"agent", name:"Agent", t:"10:42", txt:<><span className="vrc-spinner" style={{color:"#60a5fa"}}/>Step 2 / 2 — clicking "Get started"…</> },
    ],
    recover: [
      { w:"user",   name:"You",    t:"10:41", txt:"Open playwright.dev, assert hero text, then click Get started." },
      { w:"system", name:"System", t:"10:42", txt:"Assertion failed. Page navigated to /docs/intro before hero check." },
      { w:"agent",  name:"Agent",  t:"10:42", txt:"Suggest: go back → assert → re-click." },
    ],
    done: [
      { w:"user",  name:"You",   t:"10:41", txt:"Open playwright.dev, assert hero text, then click Get started." },
      { w:"agent", name:"Agent", t:"10:42", txt:<><b style={{color:"#4ade80"}}>2 / 2 recorded.</b> 4 lines of Playwright TS — see Code tab.</> },
    ],
  }[state] || [];
  return (
    <VRCCard color="violet" title="Conversation">
      <div style={{ marginInline:-12 }}>
        {msgs.map((m, i) => (
          <div key={i} className="vrc-msg">
            <div className={`vrc-msg-av ${m.w}`}>{m.w==="user"?"YOU":m.w==="agent"?"AI":"SYS"}</div>
            <div className="vrc-msg-body">
              <div className="vrc-msg-meta">
                <span className={`vrc-msg-name ${m.w}`}>{m.name}</span>
                <span className="vrc-msg-time">{m.t}</span>
              </div>
              <div className={`vrc-msg-text ${m.w}`}>{m.txt}</div>
            </div>
          </div>
        ))}
      </div>
    </VRCCard>
  );
}

function VRCPlan({ state }) {
  const items = [
    { type:"assert", text:'Assert hero text "Playwright enables…" is visible' },
    { type:"click",  text:'Click "Get started" link' },
  ];
  return (
    <VRCCard color="blue" title="Plan" footer={[
      <button key="c" className="vrc-btn primary" style={{ flex:1, justifyContent:"center" }}>Confirm plan</button>,
      <button key="s" className="vrc-btn" style={{ flex:1, justifyContent:"center" }}>Send correction</button>,
    ]}>
      <div style={{ display:"flex", alignItems:"center", gap:8, marginBottom:10 }}>
        <VRCBadge kind="await">Awaiting confirmation</VRCBadge>
        <span style={{ fontSize:11, color:"#444", fontFamily:"ui-monospace,monospace" }}>2 actions · ~3s</span>
      </div>
      <ul className="vrc-plan" style={{ marginBottom:10 }}>
        {items.map((it, i) => (
          <li key={i}>
            <span className="vrc-plan-n">{i+1}</span>
            <span className="vrc-plan-t">{it.text}</span>
            <VRCPlanTag kind={it.type} />
          </li>
        ))}
      </ul>
      <textarea className="vrc-input" rows={2} placeholder="Type a correction…" />
    </VRCCard>
  );
}

function VRCTimeline({ state }) {
  const rows = ({
    planning: [
      { k:"ok",     t:"10:41:30", txt:<><b>Task parsed</b> · 2 actions</> },
      { k:"active", t:"10:41:31", txt:"Ranking locator candidates…" },
    ],
    await: [
      { k:"ok",   t:"10:41:30", txt:<><b>Task parsed</b> · 2 actions</> },
      { k:"ok",   t:"10:41:31", txt:"Locators ranked · 2 / 2" },
      { k:"warn", t:"10:41:32", txt:"Plan ready · awaiting confirmation" },
    ],
    exec: [
      { k:"ok",     t:"10:42:00", txt:<><b>Plan confirmed</b></> },
      { k:"ok",     t:"10:42:01", txt:"DOM snapshot captured" },
      { k:"ok",     t:"10:42:02", txt:"Assertion passed — hero visible" },
      { k:"active", t:"10:42:02", txt:'Clicking "Get started"…' },
    ],
    recover: [
      { k:"ok",  t:"10:42:00", txt:<><b>Plan confirmed</b></> },
      { k:"ok",  t:"10:42:02", txt:"Click executed" },
      { k:"warn",t:"10:42:14", txt:"Navigation detected → /docs/intro" },
      { k:"err", t:"10:42:14", txt:<><b>Assertion failed</b> — hero not in DOM</> },
    ],
    done: [
      { k:"ok", t:"10:42:00", txt:<><b>Plan confirmed</b></> },
      { k:"ok", t:"10:42:02", txt:"Assertion passed" },
      { k:"ok", t:"10:42:04", txt:"Click executed" },
      { k:"ok", t:"10:42:05", txt:<><b>Code generated</b> · 4 lines</> },
    ],
  })[state] || [];
  if (!rows.length) return null;
  return (
    <VRCCard title="Execution">
      <div className="vrc-tl">
        {rows.map((r, i) => (
          <div key={i} className="vrc-tl-row">
            <div className={`vrc-tl-icon ${r.k}`}>
              {r.k==="ok" && "✓"}
              {r.k==="active" && "·"}
              {r.k==="warn" && "!"}
              {r.k==="err" && "✕"}
            </div>
            <div className="vrc-tl-text">{r.txt}</div>
            <div className="vrc-tl-time">{r.t}</div>
          </div>
        ))}
      </div>
    </VRCCard>
  );
}

function VRCRecovery() {
  return (
    <VRCCard color="red" title="Recovery needed" footer={[
      <button key="s" className="vrc-btn primary" style={{ flex:1, justifyContent:"center" }}>Send correction</button>,
      <button key="k" className="vrc-btn">Skip</button>,
    ]}>
      <div className="vrc-err">
        <VRCIcons.Warn size={14} />
        <div>Click before assert caused navigation. Hero element missing on <code style={{color:"#f87171"}}>/docs/intro</code>.</div>
      </div>
      <div style={{ display:"grid", gridTemplateColumns:"1fr 1fr", gap:8, marginBottom:10, fontFamily:"ui-monospace,monospace", fontSize:11.5 }}>
        <div style={{ padding:"8px 10px", background:"#0f0f0f", border:"1px solid #1a1a1a", borderRadius:4 }}>
          <div style={{ fontSize:9.5, color:"#444", textTransform:"uppercase", letterSpacing:".09em", marginBottom:3 }}>Was</div>
          playwright.dev/
        </div>
        <div style={{ padding:"8px 10px", background:"#0f0f0f", border:"1px solid #1a1a1a", borderRadius:4 }}>
          <div style={{ fontSize:9.5, color:"#444", textTransform:"uppercase", letterSpacing:".09em", marginBottom:3 }}>Now</div>
          /docs/intro
        </div>
      </div>
      <div style={{ fontSize:12, color:"#888", background:"#0f0f0f", border:"1px solid #1a1a1a", borderRadius:4, padding:"10px 12px", marginBottom:10 }}>
        <div style={{ fontSize:10, color:"#60a5fa", fontWeight:700, textTransform:"uppercase", letterSpacing:".09em", marginBottom:6 }}>Suggested recovery</div>
        <ol style={{ margin:0, paddingLeft:18, color:"#aaa", lineHeight:1.7 }}>
          <li>Go back to <code style={{color:"#ededed"}}>playwright.dev/</code></li>
          <li>Assert hero text first</li>
          <li>Re-attempt the click</li>
        </ol>
      </div>
      <textarea className="vrc-input" rows={2} placeholder="Add guidance…" />
    </VRCCard>
  );
}

function VRCPendingSteps() {
  return (
    <VRCCard color="amber" title="Pending steps">
      <div style={{ display:"flex", flexDirection:"column", gap:4 }}>
        {[
          { n:"01", label:"Assert hero text exists",      type:"assert", status:"ready"  },
          { n:"02", label:'Click "Get started"',          type:"click",  status:"ready"  },
        ].map((s) => (
          <div key={s.n} style={{ display:"flex", gap:8, alignItems:"center", padding:"8px 10px", background:"#0f0f0f", border:"1px solid #1a1a1a", borderRadius:4, fontSize:12.5 }}>
            <code style={{ fontSize:10.5, color:"#444", fontFamily:"ui-monospace,monospace" }}>{s.n}</code>
            <span style={{ flex:1, color:"#ededed" }}>{s.label}</span>
            <VRCPlanTag kind={s.type} />
            <VRCBadge kind={s.status}>ready</VRCBadge>
          </div>
        ))}
      </div>
    </VRCCard>
  );
}

function VRCRecorded({ done }) {
  return (
    <VRCCard color={done?"green":undefined} title="Recorded output">
      <div className="vrc-stats" style={{ marginBottom: done?10:0 }}>
        <div className="vrc-stat"><div className={`vrc-stat-num${done?" green":""}`}>{done?"2":"0"}</div><div className="vrc-stat-lbl">Recorded steps</div></div>
        <div className="vrc-stat"><div className="vrc-stat-num">{done?"4":"—"}</div><div className="vrc-stat-lbl">Lines of code</div></div>
      </div>
      {done && (
        <pre className="vrc-code">
          <VRCCodeLine tokens={[["kw","await "],["fn","page.getByText"],"(",["str","'Get started'"],", { ",["prop","exact"],": ",["kw","true"]," }).",["fn","click"],"();"]} />
        </pre>
      )}
      {!done && <div style={{ fontSize:12.5, color:"#444", marginTop:8 }}>Successful steps and generated code appear here.</div>}
      <div style={{ display:"flex", gap:6, marginTop:10 }}>
        <button className="vrc-btn sm" style={{ flex:1, justifyContent:"center" }}>Steps</button>
        <button className="vrc-btn sm" style={{ flex:1, justifyContent:"center" }}>Code</button>
      </div>
    </VRCCard>
  );
}

function VRCIdleComposer() {
  return (
    <VRCCard color="blue" title="New task">
      <textarea className="vrc-input" rows={3} placeholder="Describe what to test — e.g. open playwright.dev, assert hero text exists, click Get started…" />
      <div style={{ display:"flex", gap:6, marginTop:8, justifyContent:"flex-end" }}>
        <button className="vrc-btn primary">Plan task →</button>
      </div>
    </VRCCard>
  );
}

function VRCHeader({ state }) {
  const labels = { idle:"Idle", planning:"Planning", await:"Awaiting confirmation", exec:"Executing", recover:"Recovery needed", done:"Completed" };
  return (
    <div className="vrc-hd">
      <div className="vrc-hd-top">
        <div className="vrc-logo">
          <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
            <path d="M2 2h4v4H2zM8 2h4v4H8zM2 8h4v4H2z" fill="#000"/>
          </svg>
        </div>
        <div>
          <div className="vrc-product">AutoWorkbench</div>
          <div className="vrc-product-sub">Playwright Co-pilot</div>
        </div>
      </div>
      <div className={`vrc-state-block s-${state}`}>
        <div className={`vrc-state-dot s-${state}`} />
        <div className={`vrc-state-label s-${state}`}>{labels[state]}</div>
        <div className="vrc-state-url">playwright.dev/</div>
      </div>
    </div>
  );
}

function VRCPanel({ state, tab }) {
  const stepCount = ["planning","await","exec","recover","done"].includes(state) ? 2 : 0;
  return (
    <div className="vrc-panel">
      <VRCHeader state={state} />
      <div className="vrc-tabs">
        {[["workbench","Workbench"],["steps","Steps"],["code","Code"],["debug","Debug"]].map(([id,label]) => (
          <button key={id} className={`vrc-tab${tab===id?" active":""}`}>
            {label}{id==="steps" && stepCount>0 && <span className="vrc-tab-ct">{stepCount}</span>}
          </button>
        ))}
      </div>
      <div className="vrc-body">
        {tab==="workbench" && <>
          {state==="idle" && <VRCIdleComposer />}
          <VRCConversation state={state} />
          <VRCTimeline state={state} />
          {state==="await" && <VRCPlan state={state} />}
          {state==="recover" && <VRCRecovery />}
          <VRCPendingSteps />
          {["exec","done"].includes(state) && <VRCRecorded done={state==="done"} />}
          {state==="idle" && <VRCRecorded done={false} />}
        </>}
      </div>
      <div className="vrc-bottom">
        <button className="vrc-btn">+ Step</button>
        <button className="vrc-btn primary" style={{ flex:1, justifyContent:"center" }}>Run →</button>
      </div>
    </div>
  );
}

window.VRCPanel = VRCPanel;
