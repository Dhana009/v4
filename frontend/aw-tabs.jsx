/* global React, Icons, AW */
// Steps + Code + Debug tabs

const { Icons: I4 } = window;
const { Badge, ActionTag, Card, Mono, CodeLine, IconBtn } = window.AW;

// ── Steps tab ────────────────────────────────────────────────────
function StepsTab() {
  const recorded = [
    {
      n: "01", type: "assert", title: "Assert hero text exists",
      target: "Playwright hero heading",
      locator: <CodeLine tokens={[["fn","page.getByText"],"(",["str","'Playwright enables…'"],")"]} />,
      code: <CodeLine tokens={[["kw","await "],["fn","expect"],"(",["fn","page.getByText"],"(",["str","'Playwright enables reliable…'"],")).",["fn","toBeVisible"],"();"]} />,
      status: "passed",
    },
    {
      n: "02", type: "click", title: "Click “Get started”",
      target: "Get started link",
      locator: <CodeLine tokens={[["fn","page.getByText"],"(",["str","'Get started'"],", { ",["prop","exact"],": ",["kw","true"]," })"]} />,
      code: <CodeLine tokens={[["kw","await "],["fn","page.getByText"],"(",["str","'Get started'"],", { ",["prop","exact"],": ",["kw","true"]," }).",["fn","click"],"();"]} />,
      status: "recorded",
    },
  ];
  const pending = [
    {
      n: "03", type: "assert", title: "Assert docs page heading is visible",
      element: { tag: "h1", text: "Installation", cls: ".theme-doc-markdown" },
      status: "ready",
    },
    {
      n: "04", type: "fill", title: "Fill search box with “locators”",
      element: { tag: "input", text: "Search docs", cls: ".DocSearch-Button" },
      status: "draft",
    },
    {
      n: "05", type: "click", title: "Click first search result",
      element: null,
      status: "draft",
    },
  ];

  return (
    <>
      <div className="aw-section-label">
        Recorded steps <span className="count">{recorded.length}</span>
        <span style={{ marginLeft: "auto", display: "inline-flex", gap: 4 }}>
          <button className="aw-btn ghost sm"><I4.Replay size={11} /> Replay all</button>
        </span>
      </div>
      <div className="aw-card">
        {recorded.map((s, i) => (
          <div key={s.n} style={{ borderBottom: i < recorded.length - 1 ? "1px solid var(--aw-line)" : "none", padding: "10px 11px" }}>
            <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 6 }}>
              <span className="aw-step-num" style={{ marginTop: 0 }}>{s.n}</span>
              <ActionTag kind={s.type} />
              <span style={{ fontSize: 12.5, color: "var(--aw-fg)", fontWeight: 500, flex: 1, minWidth: 0, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{s.title}</span>
              <Badge kind={s.status}>{s.status === "passed" ? "Passed" : "Recorded"}</Badge>
            </div>
            <div style={{ fontSize: 11, color: "var(--aw-fg-3)", marginBottom: 4 }}>Target · {s.target}</div>
            <div style={{ display: "grid", gridTemplateColumns: "1fr", gap: 5, marginBottom: 7 }}>
              <Mono tight style={{ display: "block" }}>{s.locator}</Mono>
              <Mono tight className="code-line" style={{ display: "block" }}>{s.code}</Mono>
            </div>
            <div style={{ display: "flex", gap: 4 }}>
              <button className="aw-btn sm"><I4.Replay size={11} /> Replay</button>
              <button className="aw-btn sm"><I4.Copy size={11} /> Copy</button>
              <button className="aw-btn sm ghost"><I4.More size={11} /></button>
            </div>
          </div>
        ))}
      </div>

      <div className="aw-section-label">
        Pending steps <span className="count">{pending.length}</span>
      </div>
      <div className="aw-card">
        {pending.map((s, i) => (
          <div key={s.n} style={{ borderBottom: i < pending.length - 1 ? "1px solid var(--aw-line)" : "none", padding: "9px 11px" }}>
            <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 5 }}>
              <span className="aw-step-num" style={{ marginTop: 0 }}>{s.n}</span>
              <ActionTag kind={s.type} />
              <span style={{ fontSize: 12.5, color: "var(--aw-fg)", fontWeight: 500, flex: 1, minWidth: 0, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{s.title}</span>
              <Badge kind={s.status}>{s.status === "ready" ? "Ready" : "Draft"}</Badge>
            </div>
            {s.element ? (
              <div className="aw-elem-snap" style={{ marginTop: 4, marginBottom: 7 }}>
                <div className="ic">{s.element.tag}</div>
                <div className="info">
                  <div className="t">{s.element.text}</div>
                  <div className="l">{s.element.cls}</div>
                </div>
              </div>
            ) : (
              <div style={{ fontSize: 11.5, color: "var(--aw-fg-3)", margin: "4px 0 7px", display: "inline-flex", alignItems: "center", gap: 4 }}>
                <I4.Pin size={11} /> No element attached
              </div>
            )}
            <div style={{ display: "flex", gap: 4 }}>
              <button className="aw-btn sm"><I4.Pin size={11} /> Attach</button>
              <button className="aw-btn sm"><I4.Edit size={11} /> Edit</button>
              <button className="aw-btn sm danger"><I4.Trash size={11} /></button>
            </div>
          </div>
        ))}
      </div>

      <div className="aw-bottom-bar" style={{ position: "sticky", bottom: 0 }}>
        <button className="aw-btn"><I4.Plus size={12} /> Add step</button>
        <button className="aw-btn primary"><I4.Play size={11} /> Run pending</button>
        <button className="aw-btn ghost icon" title="Clear pending"><I4.Trash size={12} /></button>
      </div>
    </>
  );
}

// ── Code tab ─────────────────────────────────────────────────────
function CodeTab() {
  // 4 + import block = 9 lines
  const lines = [
    [["kw","import"]," { ",["fn","test"],", ",["fn","expect"]," } ",["kw","from"]," ",["str","'@playwright/test'"],";"],
    [],
    [["fn","test"],"(",["str","'generated flow'"],", ",["kw","async"]," ({ ",["prop","page"]," }) => {"],
    ["  ",["kw","await "],["fn","page.goto"],"(",["str","'https://playwright.dev/'"],");"],
    ["  ",["kw","await "],["fn","expect"],"(",["fn","page.getByText"],"(",["str","'Playwright enables reliable web automation'"],")).",["fn","toBeVisible"],"();"],
    ["  ",["kw","await "],["fn","page.getByText"],"(",["str","'Get started'"],", { ",["prop","exact"],": ",["kw","true"]," }).",["fn","click"],"();"],
    ["});"],
  ];
  const hl = 5; // "Get started" line — latest

  return (
    <>
      <div style={{ display: "flex", alignItems: "center", gap: 8, padding: "10px 12px 4px" }}>
        <span style={{ fontFamily: "var(--aw-mono)", fontSize: 11.5, color: "var(--aw-fg-2)" }}>generated.spec.ts</span>
        <Badge kind="recorded">Auto-generated</Badge>
        <span style={{ flex: 1 }} />
        <button className="aw-btn sm"><I4.Copy size={11} /> Copy</button>
        <button className="aw-btn sm primary"><I4.Code size={11} /> Export .spec.ts</button>
      </div>
      <div className="aw-code">
        <div className="aw-code-lines">
          {lines.map((_, i) => <div key={i}>{i + 1}</div>)}
        </div>
        <div className="aw-code-body">
          <pre>
            {lines.map((toks, i) => (
              <div key={i} className={`aw-code-line${i === hl ? " hl-new" : ""}`}>
                {toks.length ? <CodeLine tokens={toks} /> : "\u00a0"}
              </div>
            ))}
          </pre>
        </div>
      </div>
      <div style={{ padding: "0 12px", fontSize: 11, color: "var(--aw-fg-3)", display: "flex", alignItems: "center", gap: 6 }}>
        <I4.Spark size={11} style={{ color: "var(--aw-accent)" }} />
        Updated · 4s ago · highlighted line was just recorded
      </div>
      <div className="aw-bottom-bar">
        <button className="aw-btn"><I4.Wand size={11} /> Format</button>
        <button className="aw-btn"><I4.Copy size={11} /> Copy code</button>
        <button className="aw-btn primary" style={{ flex: 1, justifyContent: "center" }}>
          <I4.Code size={11} /> Export .spec.ts
        </button>
      </div>
    </>
  );
}

// ── Debug tab ────────────────────────────────────────────────────
function DebugTab() {
  const calls = [
    { name: "locator_find",     arrow: "→", res: "found:true",    ok: true,  args: "role=heading" },
    { name: "locator_validate", arrow: "→", res: "count:1",       ok: true,  args: "" },
    { name: "action_click",     arrow: "→", res: "success:true",  ok: true,  args: "" },
    { name: "page_snapshot",    arrow: "→", res: "1.2 MB",        ok: true,  args: "" },
    { name: "locator_validate", arrow: "→", res: "count:0",       ok: false, args: "h1.hero__title" },
  ];
  const logs = [
    "[10:42:01] DOM snapshot captured (1248 nodes)",
    "[10:42:02] Locator validated count=1",
    "[10:42:02] Click executed at (640, 412)",
    "[10:42:14] Navigation observed → /docs/intro",
    "[10:42:14] Assertion failed: hero element not in DOM",
    "[10:42:14] WS event: ws://127.0.0.1:9223/devtools/page/A1B2",
  ];
  const locators = [
    { kind: "getByRole", val: <CodeLine tokens={[["fn","getByRole"],"(",["str","'heading'"],", { ",["prop","level"],": ",["num","1"]," })"]} />, ok: true,  count: 1 },
    { kind: "getByText", val: <CodeLine tokens={[["fn","getByText"],"(",["str","'Playwright enables…'"],")"]} />, ok: true,  count: 1 },
    { kind: "css",       val: <CodeLine tokens={[["str","'h1.hero__title'"]]} />, ok: false, count: 0 },
    { kind: "xpath",     val: <CodeLine tokens={[["str","'//main//h1[1]'"]]} />, ok: true,  count: 1 },
  ];

  return (
    <>
      <Card title="Tool calls" titleIcon={<I4.Beaker size={11} />} dense link={`${calls.length}`}>
        <div style={{ marginInline: -11 }}>
          {calls.map((c, i) => (
            <div key={i} className={`aw-toolcall ${c.ok ? "ok" : "fail"}`}>
              <span className="name">{c.name}</span>
              {c.args && <span style={{ color: "var(--aw-fg-3)" }}>({c.args})</span>}
              <span className="arrow">{c.arrow}</span>
              <span className="res">{c.res}</span>
            </div>
          ))}
        </div>
      </Card>

      <Card title="Locator candidates" titleIcon={<I4.Search size={11} />} dense>
        <div style={{ marginInline: -11 }}>
          {locators.map((l, i) => (
            <div key={i} className="aw-locator-row">
              <span className="aw-loc-kind">{l.kind}</span>
              <span className="aw-loc-val">{l.val}</span>
              <span style={{ display: "inline-flex", alignItems: "center", gap: 5, fontFamily: "var(--aw-mono)", fontSize: 10.5, color: l.ok ? "var(--aw-success)" : "var(--aw-danger)" }}>
                {l.ok ? <I4.Check size={10} /> : <I4.X size={10} />}
                count={l.count}
              </span>
            </div>
          ))}
        </div>
      </Card>

      <Card title="Raw logs" titleIcon={<I4.List size={11} />} dense>
        <div style={{ fontFamily: "var(--aw-mono)", fontSize: 11, lineHeight: 1.55, color: "var(--aw-fg-2)", maxHeight: 160, overflow: "auto" }}>
          {logs.map((l, i) => <div key={i} style={{ whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>{l}</div>)}
        </div>
      </Card>

      <Card title="Screenshots" titleIcon={<I4.Camera size={11} />} dense>
        <div className="aw-thumb-grid">
          {["hero-pre.png", "hero-post.png", "fail-step-02.png", "click-target.png"].map((n) => (
            <div key={n} className="aw-thumb" style={{ height: 64 }}>
              <I4.Camera size={14} />
              <div style={{ position: "absolute", bottom: 4, left: 6, right: 6, fontSize: 10, color: "var(--aw-fg-3)", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{n}</div>
            </div>
          ))}
        </div>
      </Card>
    </>
  );
}

window.AW.StepsTab = StepsTab;
window.AW.CodeTab = CodeTab;
window.AW.DebugTab = DebugTab;
