/* global React, Icons, AW */
// Workbench tab — 6 states. Pass `state` prop: idle | planning | await | exec | recover | done.

const { Icons: I3 } = window;
const { Badge, ActionTag, Card, ElementSnap, Mono, CodeLine, IconBtn } = window.AW;

// ── Conversation block ───────────────────────────────────────────
function Conversation({ state }) {
  const baseMsgs = [
    { who: "user", time: "10:41:28", text: "Open playwright.dev, assert the hero text exists, then click Get started." },
    { who: "agent", time: "10:41:30", text: <>I read the page and detected <b>2 actions</b>: an assertion on the hero heading, then a click on the “Get started” link. I'll show the plan for confirmation.</> },
  ];
  const planning = [{ who: "agent", time: "10:41:32", text: <><span className="aw-spinner" style={{verticalAlign:"-1px",marginRight:6,color:"var(--aw-warn)"}}/>Inspecting DOM and ranking locator candidates…</> }];
  const correction = [
    { who: "user", time: "10:41:55", text: "First assert the text, then click. Don't navigate yet." },
    { who: "agent", time: "10:41:57", text: "Got it — reordered the plan. Awaiting confirmation again." },
  ];
  const exec = [
    { who: "agent", time: "10:42:02", text: <><span className="aw-spinner" style={{verticalAlign:"-1px",marginRight:6,color:"var(--aw-accent)"}}/>Executing step 2 of 2 — clicking <span className="aw-mono tight" style={{padding:"0 4px"}}>Get started</span></> },
  ];
  const recover = [
    { who: "system", time: "10:42:18", text: <>Step <b>1 / Click “Get started”</b> failed: page navigated to <span style={{color:"var(--aw-fg-2)"}}>/docs/intro</span> before the assertion ran.</> },
    { who: "agent", time: "10:42:19", text: "Suggesting recovery: go back, assert the hero text first, then click." },
  ];
  const done = [
    { who: "agent", time: "10:42:31", text: <><b style={{color:"var(--aw-success)"}}>2/2 steps recorded.</b> Generated 4 lines of Playwright TS — see Code tab.</> },
  ];

  let msgs = [];
  if (state === "idle")     msgs = [{ who: "user", time: "10:41:28", text: "Open playwright.dev, assert the hero text exists, then click Get started." }];
  if (state === "planning") msgs = [...baseMsgs, ...planning];
  if (state === "await")    msgs = baseMsgs;
  if (state === "exec")     msgs = [...baseMsgs, ...exec];
  if (state === "recover")  msgs = [...baseMsgs, ...exec, ...recover];
  if (state === "done")     msgs = [...baseMsgs, ...done];

  const names = { user: "You", agent: "Agent", system: "System" };
  const initials = { user: "YOU", agent: "AGT", system: "SYS" };

  return (
    <Card title="Conversation" titleIcon={<I3.Sparkles size={12} />} dense tone="violet" link={state==="recover" ? null : null}>
      <div style={{ marginInline: -11 }}>
        {msgs.map((m, i) => (
          <div key={i} className="aw-msg">
            <div className={`aw-msg-avatar ${m.who}`}>{initials[m.who]}</div>
            <div className="aw-msg-body">
              <div>
                <span className="aw-msg-name">{names[m.who]}</span>
                <span className="aw-msg-time">{m.time}</span>
              </div>
              <div className={`aw-msg-text${m.who === "system" ? " muted" : ""}`}>{m.text}</div>
            </div>
          </div>
        ))}
      </div>
    </Card>
  );
}

// ── Plan card (Awaiting Confirmation) ────────────────────────────
function PlanCard({ revised }) {
  const items = revised
    ? [
        { type: "assert", text: "Assert hero text “Playwright enables reliable web automation” is visible" },
        { type: "click",  text: "Click “Get started” link" },
      ]
    : [
        { type: "click",  text: "Click “Get started” link" },
        { type: "assert", text: "Assert hero text is visible" },
      ];
  return (
    <Card tone="accent" title={revised ? "Revised plan" : "Current plan"} titleIcon={<I3.Wand size={12} />}>
      <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 8 }}>
        <Badge kind="await">Awaiting confirmation</Badge>
        <span style={{ fontSize: 11, color: "var(--aw-fg-3)", fontFamily: "var(--aw-mono)" }}>2 actions · ~3s</span>
      </div>
      <div style={{ fontSize: 12.5, color: "var(--aw-fg-2)", marginBottom: 8 }}>
        I understood the task as <span style={{ color: "var(--aw-fg)" }}>verify the homepage hero, then proceed to docs</span>.
      </div>
      <ol className="aw-plan-list">
        {items.map((it, i) => (
          <li key={i}>
            <div className="aw-plan-text">
              {it.text}
              <div className="aw-plan-meta">
                <ActionTag kind={it.type} />
              </div>
            </div>
          </li>
        ))}
      </ol>
      {!revised && (
        <div className="aw-warn-strip">
          <I3.Warn size={12} />
          <div><b>Order may navigate away.</b> Clicking before asserting will leave the homepage. Send a correction or reorder.</div>
        </div>
      )}
      <div style={{ marginTop: 10, display: "flex", flexDirection: "column", gap: 8 }}>
        <textarea
          className="aw-textarea"
          placeholder="Type correction, e.g. first assert the text, then click…"
          defaultValue=""
          rows={2}
        />
        <div style={{ display: "flex", gap: 6 }}>
          <button className="aw-btn primary" style={{ flex: 1, justifyContent: "center" }}>
            <I3.Check size={13} /> Confirm plan
          </button>
          <button className="aw-btn" style={{ flex: 1, justifyContent: "center" }} disabled>
            <I3.Send size={12} /> Send correction
          </button>
        </div>
      </div>
    </Card>
  );
}

// ── Pending steps summary ────────────────────────────────────────
function PendingSummary({ onOpen }) {
  return (
    <Card
      title={<>Pending steps <span style={{ color: "var(--aw-fg-3)", fontWeight: 500, marginLeft: 4 }}>2</span></>}
      titleIcon={<I3.List size={12} />}
      tone="warn"
      link="View all"
      onLink={onOpen}
      dense
    >
      <div style={{ marginInline: -11 }}>
        <div className="aw-step">
          <div className="aw-step-num">01</div>
          <div className="aw-step-main">
            <div className="aw-step-title">Assert hero text exists</div>
            <div className="aw-step-meta">
              <ActionTag kind="assert" />
              <span className="aw-elem-tag">
                <span className="ang">&lt;</span><span className="name">h1</span><span className="ang">&gt;</span>
                <span className="text">Playwright enables reliable…</span>
              </span>
            </div>
          </div>
          <div className="aw-step-actions">
            <Badge kind="ready">Ready</Badge>
          </div>
        </div>
        <div className="aw-step">
          <div className="aw-step-num">02</div>
          <div className="aw-step-main">
            <div className="aw-step-title">Click “Get started”</div>
            <div className="aw-step-meta">
              <ActionTag kind="click" />
              <span className="aw-elem-tag">
                <span className="ang">&lt;</span><span className="name">a</span><span className="ang">&gt;</span>
                <span className="text">Get started</span>
              </span>
            </div>
          </div>
          <div className="aw-step-actions">
            <Badge kind="ready">Ready</Badge>
          </div>
        </div>
      </div>
    </Card>
  );
}

// ── Execution timeline ───────────────────────────────────────────
function ExecutionTimeline({ state }) {
  // tailored per state
  let rows = [];
  if (state === "exec") {
    rows = [
      { t: "10:42:00", k: "success", icon: <I3.Check size={9} />, text: <>Plan confirmed · <span className="dim">2 actions</span></> },
      { t: "10:42:01", k: "success", icon: <I3.Camera size={9} />, text: <>DOM snapshot captured · <span className="dim">1.2 MB</span></> },
      { t: "10:42:01", k: "success", icon: <I3.Search size={9} />, text: <>Locator <span className="dim">getByText</span> found · <span className="dim">count=1</span></> },
      { t: "10:42:02", k: "success", icon: <I3.Check size={9} />, text: <>Assertion passed · <span className="dim">hero visible</span></> },
      { t: "10:42:02", k: "active",  icon: <I3.Mouse size={9} />, text: <>Clicking <span className="dim">Get started</span>…</> },
    ];
  } else if (state === "recover") {
    rows = [
      { t: "10:42:00", k: "success", icon: <I3.Check size={9} />, text: <>Plan confirmed</> },
      { t: "10:42:01", k: "success", icon: <I3.Search size={9} />, text: <>Locator found · <span className="dim">getByText “Get started”</span></> },
      { t: "10:42:02", k: "success", icon: <I3.Mouse size={9} />, text: <>Click executed</> },
      { t: "10:42:14", k: "warn",    icon: <I3.Globe size={9} />, text: <>Page navigated · <span className="dim">/docs/intro</span></> },
      { t: "10:42:14", k: "danger",  icon: <I3.X size={9} />,    text: <>Assertion failed · <span className="dim">hero not in DOM</span></> },
      { t: "10:42:18", k: "danger",  icon: <I3.Warn size={9} />, text: <>Recovery needed</> },
    ];
  } else if (state === "done") {
    rows = [
      { t: "10:42:00", k: "success", icon: <I3.Check size={9} />, text: <>Plan confirmed</> },
      { t: "10:42:02", k: "success", icon: <I3.Check size={9} />, text: <>Assertion passed</> },
      { t: "10:42:04", k: "success", icon: <I3.Mouse size={9} />, text: <>Click executed · <span className="dim">/docs/intro</span></> },
      { t: "10:42:05", k: "success", icon: <I3.Camera size={9} />, text: <>Screenshot captured</> },
      { t: "10:42:05", k: "success", icon: <I3.Code size={9} />, text: <>Code generated · <span className="dim">4 lines</span></> },
    ];
  } else if (state === "planning") {
    rows = [
      { t: "10:41:30", k: "success", icon: <I3.Check size={9} />, text: <>Task understood · <span className="dim">2 actions detected</span></> },
      { t: "10:41:31", k: "active",  icon: <I3.Search size={9} />, text: <>Ranking locator candidates…</> },
    ];
  } else if (state === "await") {
    rows = [
      { t: "10:41:30", k: "success", icon: <I3.Check size={9} />, text: <>Task understood · 2 actions</> },
      { t: "10:41:31", k: "success", icon: <I3.Search size={9} />, text: <>Locators ranked · <span className="dim">2 / 2</span></> },
      { t: "10:41:32", k: "warn",    icon: <I3.Eye size={9} />, text: <>Plan ready · awaiting your confirmation</> },
    ];
  } else {
    rows = [{ t: "—", k: null, icon: <I3.Bolt size={9} />, text: <span className="dim">No execution yet. Add steps and run, or chat with the agent.</span> }];
  }

  return (
    <Card title="Execution timeline" titleIcon={<I3.Bolt size={12} />} dense tone="elevated">
      <div className="aw-timeline" style={{ marginInline: -11 }}>
        {rows.map((r, i) => (
          <div key={i} className="aw-tl-row">
            <div className={`aw-tl-icon ${r.k ? "s-" + r.k : ""}`}>{r.icon}</div>
            <div className="aw-tl-text">{r.text}</div>
            <div className="aw-tl-time">{r.t}</div>
          </div>
        ))}
      </div>
    </Card>
  );
}

// ── Recovery card ────────────────────────────────────────────────
function RecoveryCard() {
  return (
    <Card title="Recovery needed" titleIcon={<I3.Warn size={12} />} tone="danger">
      <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 8 }}>
        <Badge kind="recover">Recovery needed</Badge>
        <span style={{ fontSize: 11, color: "var(--aw-fg-3)", fontFamily: "var(--aw-mono)" }}>step 2 of 2</span>
      </div>
      <div style={{ fontSize: 12.5, color: "var(--aw-fg-2)", marginBottom: 8, lineHeight: 1.5 }}>
        <div style={{ color: "var(--aw-fg)", fontWeight: 500, marginBottom: 4 }}>Assert hero text exists</div>
        <div>
          The agent clicked <span style={{ color: "var(--aw-fg)" }}>Get started</span> before asserting. The page navigated and the hero element is no longer in the DOM.
        </div>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 6, marginBottom: 10 }}>
        <Mono tight>
          <div style={{ fontSize: 9.5, color: "var(--aw-fg-4)", textTransform: "uppercase", letterSpacing: ".08em", marginBottom: 2 }}>Was</div>
          playwright.dev/
        </Mono>
        <Mono tight>
          <div style={{ fontSize: 9.5, color: "var(--aw-fg-4)", textTransform: "uppercase", letterSpacing: ".08em", marginBottom: 2 }}>Now</div>
          /docs/intro
        </Mono>
      </div>

      <div style={{
        background: "var(--aw-bg-2)", border: "1px solid var(--aw-line)", borderRadius: 5,
        padding: "8px 10px", fontSize: 12, color: "var(--aw-fg-2)", lineHeight: 1.5, marginBottom: 10,
      }}>
        <div style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 10.5, color: "var(--aw-accent)", textTransform: "uppercase", letterSpacing: ".07em", fontWeight: 600, marginBottom: 4 }}>
          <I3.Sparkles size={10} /> Suggested recovery
        </div>
        <ol style={{ margin: 0, paddingLeft: 18, color: "var(--aw-fg)" }}>
          <li>Go back to <span className="aw-mono tight" style={{ padding: "0 4px" }}>playwright.dev/</span></li>
          <li>Assert the hero text first</li>
          <li>Re-attempt the click</li>
        </ol>
      </div>

      <div className="aw-thumb" style={{ marginBottom: 10, height: 70 }}>
        <div style={{ position: "absolute", inset: 8, border: "1px dashed var(--aw-line-strong)", borderRadius: 4, display: "grid", placeItems: "center" }}>
          <I3.Camera size={14} />
          <span style={{ marginTop: 4 }}>screenshot · failure-step-02.png</span>
        </div>
      </div>

      <textarea className="aw-textarea" placeholder="Add guidance, e.g. go back and assert before clicking…" rows={2} />
      <div style={{ display: "flex", gap: 6, marginTop: 8 }}>
        <button className="aw-btn primary" style={{ flex: 1, justifyContent: "center" }}>
          <I3.Send size={12} /> Send correction
        </button>
        <button className="aw-btn" title="Skip step">Skip step</button>
      </div>
    </Card>
  );
}

// ── Recorded summary ─────────────────────────────────────────────
function RecordedSummary({ done }) {
  return (
    <Card title="Recorded output" titleIcon={<I3.Check size={12} />} tone={done ? "success" : null}>
      <div className="aw-stat-row">
        <div className="aw-stat">
          <div className={`aw-stat-num ${done ? "s-success" : ""}`}>{done ? "2" : "0"}</div>
          <div className="aw-stat-lbl">Recorded steps</div>
        </div>
        <div className="aw-stat">
          <div className="aw-stat-num">{done ? "4" : "—"}</div>
          <div className="aw-stat-lbl">Lines of code</div>
        </div>
      </div>
      {done ? (
        <>
          <div style={{ fontSize: 11, color: "var(--aw-fg-3)", textTransform: "uppercase", letterSpacing: ".07em", fontWeight: 600, marginBottom: 5 }}>
            Last recorded
          </div>
          <Mono tight className="code-line" style={{ display: "block" }}>
            <CodeLine tokens={[
              ["kw", "await "], ["fn", "page.getByText"], "(", ["str", "'Get started'"], ", { ",
              ["prop", "exact"], ": ", ["kw", "true"], " }).", ["fn", "click"], "();"
            ]} />
          </Mono>
        </>
      ) : (
        <div style={{ fontSize: 12, color: "var(--aw-fg-3)", lineHeight: 1.5 }}>
          Successful steps and their generated Playwright code will appear here.
        </div>
      )}
      <div style={{ display: "flex", gap: 6, marginTop: 10 }}>
        <button className="aw-btn" style={{ flex: 1, justifyContent: "center" }}>
          <I3.List size={12} /> Open Steps
        </button>
        <button className="aw-btn" style={{ flex: 1, justifyContent: "center" }}>
          <I3.Code size={12} /> Open Code
        </button>
      </div>
    </Card>
  );
}

// ── Idle prompt composer ─────────────────────────────────────────
function IdleComposer() {
  return (
    <Card title="Start a task" titleIcon={<I3.Sparkles size={12} />} tone="accent">
      <textarea
        className="aw-textarea"
        rows={3}
        placeholder="Describe what to test, e.g. open playwright.dev, assert the hero text exists, then click Get started…"
        defaultValue=""
      />
      <div style={{ display: "flex", gap: 6, marginTop: 8, alignItems: "center" }}>
        <button className="aw-btn ghost sm">
          <I3.Paperclip size={11} /> Attach element
        </button>
        <span style={{ flex: 1 }} />
        <button className="aw-btn primary">
          <I3.Wand size={12} /> Plan task
        </button>
      </div>
    </Card>
  );
}

// ── Workbench composer ───────────────────────────────────────────
function WorkbenchTab({ state }) {
  return (
    <>
      {state === "idle" && <IdleComposer />}
      <Conversation state={state} />
      {state === "await" && <PlanCard />}
      {(state === "exec" || state === "recover" || state === "done" || state === "await" || state === "planning") && (
        <ExecutionTimeline state={state} />
      )}
      {state === "recover" && <RecoveryCard />}
      <PendingSummary />
      {(state === "done" || state === "exec") && <RecordedSummary done={state === "done"} />}
      {state === "idle" && <RecordedSummary done={false} />}
    </>
  );
}

window.AW.WorkbenchTab = WorkbenchTab;
