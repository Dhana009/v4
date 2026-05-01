/* global React, Icons */
// Variation A — Editorial / IDE hybrid panel (light cream, monospace-forward)

const IDEIcons = window.Icons;

function IDECodeLine({ tokens }) {
  return (
    <>
      {tokens.map((t, i) =>
        typeof t === "string" ? (
          <span key={i}>{t}</span>
        ) : (
          <span key={i} className={`tk-${t[0]}`}>
            {t[1]}
          </span>
        )
      )}
    </>
  );
}

function IDEPlanTag({ kind }) {
  const map = { click: "click", fill: "fill", assert: "assert", navigate: "nav", nav: "nav" };
  return <span className={`ide-plan-tag t-${map[kind] || kind}`}>{kind}</span>;
}

function IDEBadge({ kind, children }) {
  return <span className={`ide-badge b-${kind}`}>{children}</span>;
}

function IDECard({ color, title, children, footer }) {
  return (
    <div className={`ide-card c-${color || "ink"}`}>
      <div className="ide-card-hd">
        <div className="ide-card-hd-label">{title}</div>
      </div>
      <div className="ide-card-body">{children}</div>
      {footer && <div style={{ padding: "0 10px 10px", display: "flex", gap: 6 }}>{footer}</div>}
    </div>
  );
}

function normalizePanelState(state) {
  const key = String(state || "idle").trim().toLowerCase().replace(/[\s-]+/g, "_");
  switch (key) {
    case "idle":
      return "idle";
    case "planning":
      return "planning";
    case "await":
    case "awaiting_confirmation":
    case "awaiting confirmation":
      return "await";
    case "exec":
    case "executing":
      return "exec";
    case "recover":
    case "recovery":
    case "recovery_needed":
    case "recovery needed":
      return "recover";
    case "done":
    case "completed":
      return "done";
    default:
      return "idle";
  }
}

function connectionLabel(status) {
  switch (String(status || "disconnected")) {
    case "connected":
      return "Connected";
    case "reconnecting":
      return "Reconnecting";
    default:
      return "Disconnected";
  }
}

function connectionStyle(status) {
  switch (String(status || "disconnected")) {
    case "connected":
      return {
        background: "#eef8f1",
        border: "1px solid #cfe9d6",
        color: "#1e7a46",
      };
    case "reconnecting":
      return {
        background: "#fbf6ea",
        border: "1px solid #ead8ac",
        color: "#8b6f1d",
      };
    default:
      return {
        background: "#f4f0ea",
        border: "1px solid #ddd3c3",
        color: "#7d7469",
      };
  }
}

function IDEConversation({ state, messages = [], live = false }) {
  const fallback = {
    idle: [{ w: "user", t: "10:41", txt: "Open playwright.dev, assert hero text exists, then click Get started." }],
    planning: [
      { w: "user", t: "10:41", txt: "Open playwright.dev, assert hero text exists, then click Get started." },
      {
        w: "agent",
        t: "10:41",
        txt: (
          <>
            <span className="ide-spinner" style={{ color: "#4a9eff" }} />Parsing task · inspecting DOM · ranking
            locators…
          </>
        ),
      },
    ],
    await: [
      { w: "user", t: "10:41", txt: "Open playwright.dev, assert hero text exists, then click Get started." },
      { w: "agent", t: "10:41", txt: "Understood. Detected 2 actions — plan ready for your review." },
    ],
    exec: [
      { w: "user", t: "10:41", txt: "Open playwright.dev, assert hero text, then click Get started." },
      {
        w: "agent",
        t: "10:42",
        txt: (
          <>
            <span className="ide-spinner" style={{ color: "#4a9eff" }} />Executing step 2 / 2 — clicking "Get started"…
          </>
        ),
      },
    ],
    recover: [
      { w: "user", t: "10:41", txt: "Open playwright.dev, assert hero text, then click Get started." },
      { w: "system", t: "10:42", txt: "Step failed: page navigated before assertion ran. Hero element no longer in DOM." },
      { w: "agent", t: "10:42", txt: "Recovery suggestion: go back → assert first → re-click." },
    ],
    done: [
      { w: "user", t: "10:41", txt: "Open playwright.dev, assert hero text exists, then click Get started." },
      {
        w: "agent",
        t: "10:42",
        txt: (
          <>
            <b style={{ color: "#1f9d6a" }}>2/2 steps recorded.</b> Generated 4 lines of Playwright TS — see Code tab.
          </>
        ),
      },
    ],
  }[state] || [];

  const rows = live
    ? messages.length > 0
      ? messages
      : [{ w: "system", t: "--:--:--", txt: "Waiting for backend messages…" }]
    : fallback;

  return (
    <IDECard color="violet" title="// conversation">
      <div style={{ marginInline: -10 }}>
        {rows.map((m, i) => {
          const who = m.role || m.w || "agent";
          const time = m.time || m.t || "--:--:--";
          const text = m.text !== undefined ? m.text : m.txt;
          return (
            <div key={i} className="ide-msg">
              <div className="ide-msg-gutter">{time}</div>
              <div className="ide-msg-body">
                <div className={`ide-msg-who w-${who}`}>{who}</div>
                <div className="ide-msg-text">{text}</div>
              </div>
            </div>
          );
        })}
      </div>
    </IDECard>
  );
}

function IDEPlan({
  state,
  plan,
  live = false,
  correctionText = "",
  onCorrectionTextChange,
  onConfirmPlan,
  onSendCorrection,
}) {
  const hasRuntimePlan = live && plan && Array.isArray(plan.steps);
  const fallbackItems =
    state === "exec" || state === "done"
      ? [
          { type: "assert", text: "Assert hero heading is visible", cls: state === "done" ? "done" : "done" },
          { type: "click", text: 'Click "Get started" link', cls: state === "done" ? "done" : "active" },
        ]
      : [
          { type: "assert", text: "Assert hero heading is visible", cls: "" },
          { type: "click", text: 'Click "Get started" link', cls: "" },
        ];

  const items = live ? (hasRuntimePlan ? plan.steps : []) : fallbackItems;
  const summary = hasRuntimePlan
    ? plan.summary || "Plan ready"
      : live
      ? state === "recover"
        ? "Recovery needed"
        : "Waiting for plan_ready…"
      : state === "recover"
        ? "Order risk — click before assert caused navigation. Reorder steps."
        : "2 actions · ~3s";
  const showPlaceholder = live && (!plan || !Array.isArray(plan.steps) || plan.steps.length === 0);
  const isRecover = state === "recover";

  return (
    <IDECard
      color="blue"
      title="// plan"
      footer={[
        <button
          key="c"
          className="ide-btn primary"
          type="button"
          style={{ flex: 1, justifyContent: "center" }}
          onClick={() => onConfirmPlan?.()}
        >
          Confirm Plan
        </button>,
        <button
          key="s"
          className="ide-btn"
          type="button"
          style={{ flex: 1, justifyContent: "center" }}
          onClick={() => onSendCorrection?.()}
        >
          Send Correction
        </button>,
      ]}
    >
      <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 8, flexWrap: "wrap" }}>
        <IDEBadge kind="await">{hasRuntimePlan ? "Awaiting confirmation" : state === "recover" ? "Recovery needed" : "Awaiting confirmation"}</IDEBadge>
        <span style={{ fontSize: 10.5, color: "#9e9890" }}>{summary}</span>
      </div>
      {showPlaceholder && (
        <div style={{ marginBottom: 8, fontSize: 11.5, color: "#8f8a82" }}>Waiting for plan_ready…</div>
      )}
      {isRecover && (
        <div className="ide-err-strip">
          <IDEIcons.Warn size={13} /> Order risk — click before assert caused navigation. Reorder steps.
        </div>
      )}
      {items.length > 0 ? (
        <ol className="ide-plan">
          {items.map((it, i) => {
            const kind = it.kind || it.type || "step";
            const text = it.text || it.label || it.title || `Step ${i + 1}`;
            const cls = it.cls || (it.status === "done" ? "done" : it.status === "active" ? "active" : "");
            return (
              <li key={i} className={cls}>
                <span className="ide-plan-num">{i + 1}.</span>
                <span className="ide-plan-text">{text}</span>
                <IDEPlanTag kind={kind} />
              </li>
            );
          })}
        </ol>
      ) : null}
      <textarea
        className="ide-input"
        rows={2}
        style={{ marginTop: 8 }}
        placeholder="Type correction…"
        value={correctionText}
        onChange={(event) => onCorrectionTextChange?.(event.target.value)}
      />
    </IDECard>
  );
}

function IDETimeline({ state, events = [], live = false }) {
  const fallback = {
    idle: [],
    planning: [
      { d: "ok", t: "10:41:30", txt: <>Task parsed <span className="dim">· 2 actions</span></> },
      { d: "active", t: "10:41:31", txt: "Ranking locator candidates…" },
    ],
    await: [
      { d: "ok", t: "10:41:30", txt: "Task parsed · 2 actions" },
      { d: "ok", t: "10:41:31", txt: "Locators ranked · 2 / 2" },
      { d: "warn", t: "10:41:32", txt: "Plan ready · awaiting confirmation" },
    ],
    exec: [
      { d: "ok", t: "10:42:00", txt: "Plan confirmed" },
      { d: "ok", t: "10:42:01", txt: "DOM snapshot · 1.2 MB" },
      { d: "ok", t: "10:42:02", txt: "Assertion passed · hero visible" },
      { d: "active", t: "10:42:02", txt: 'Clicking "Get started"…' },
    ],
    recover: [
      { d: "ok", t: "10:42:00", txt: "Plan confirmed" },
      { d: "ok", t: "10:42:02", txt: "Click executed" },
      { d: "warn", t: "10:42:14", txt: "Page navigated → /docs/intro" },
      { d: "err", t: "10:42:14", txt: "Assertion failed · hero not in DOM" },
    ],
    done: [
      { d: "ok", t: "10:42:00", txt: "Plan confirmed" },
      { d: "ok", t: "10:42:02", txt: "Assertion passed" },
      { d: "ok", t: "10:42:04", txt: "Click executed · /docs/intro" },
      { d: "ok", t: "10:42:05", txt: "Code generated · 4 lines" },
    ],
  }[state] || [];

  const rows = live ? events : fallback;
  if (!rows.length) return null;

  return (
    <IDECard color="ink" title="// execution">
      <div className="ide-tl">
        {rows.map((r, i) => (
          <div key={i} className="ide-tl-row">
            <div className={`ide-tl-dot d-${r.d || "ok"}`} />
            <div className="ide-tl-text">{r.txt !== undefined ? r.txt : r.text}</div>
            <div className="ide-tl-time">{r.t || r.time || ""}</div>
          </div>
        ))}
      </div>
    </IDECard>
  );
}

function IDERecovery({ message, suggestion }) {
  const issue = message || "Click before assert → page navigated. Hero element missing from DOM on /docs/intro.";
  const guidance = suggestion || "Go back to playwright.dev/ · Assert hero text first · Re-attempt click";
  const steps = guidance
    .split("\n")
    .map((part) => part.trim())
    .filter(Boolean)
    .flatMap((part) => part.split("·").map((piece) => piece.trim()).filter(Boolean));

  return (
    <IDECard
      color="red"
      title="// recovery needed"
      footer={[
        <button key="s" className="ide-btn primary" type="button" style={{ flex: 1, justifyContent: "center" }}>
          Send correction
        </button>,
        <button key="k" className="ide-btn" type="button">
          Skip
        </button>,
      ]}
    >
      <div className="ide-err-strip" style={{ marginBottom: 10 }}>
        <IDEIcons.Warn size={12} />
        {issue}
      </div>
      <div style={{ marginBottom: 10, display: "grid", gridTemplateColumns: "1fr 1fr", gap: 6, fontSize: 11.5 }}>
        <div style={{ padding: "6px 8px", background: "#faf7f3", border: "1px solid #ede8e0", borderRadius: 2 }}>
          <div style={{ fontSize: 9.5, color: "#9e9890", textTransform: "uppercase", letterSpacing: ".08em", marginBottom: 2 }}>
            Was
          </div>
          <code style={{ fontSize: 11 }}>playwright.dev/</code>
        </div>
        <div style={{ padding: "6px 8px", background: "#faf7f3", border: "1px solid #ede8e0", borderRadius: 2 }}>
          <div style={{ fontSize: 9.5, color: "#9e9890", textTransform: "uppercase", letterSpacing: ".08em", marginBottom: 2 }}>
            Now
          </div>
          <code style={{ fontSize: 11 }}>/docs/intro</code>
        </div>
      </div>
      <div
        style={{
          fontSize: 11.5,
          color: "#4a4640",
          background: "#faf7f3",
          border: "1px solid #ede8e0",
          borderRadius: 2,
          padding: "8px 10px",
          marginBottom: 8,
        }}
      >
        <div
          style={{
            fontSize: 10,
            color: "#2a74d8",
            fontWeight: 700,
            textTransform: "uppercase",
            letterSpacing: ".07em",
            marginBottom: 4,
          }}
        >
          // suggestion
        </div>
        <ol style={{ margin: 0, paddingLeft: 16, lineHeight: 1.7 }}>
          {steps.length > 0 ? steps.map((step, i) => <li key={i}>{step}</li>) : <li>{guidance}</li>}
        </ol>
      </div>
      <textarea className="ide-input" rows={2} placeholder="Add guidance…" />
    </IDECard>
  );
}

function IDERecorded({ done, recordedCount, codePreview }) {
  const count = Number.isFinite(recordedCount) && recordedCount > 0 ? recordedCount : done ? 2 : 0;
  const codeText = typeof codePreview === "string" && codePreview.trim()
    ? codePreview.trim()
    : done
      ? "await page.getByText('Get started', { exact: true }).click();"
      : "";
  const showCode = Boolean(codeText);

  return (
    <IDECard color={done ? "green" : null} title="// recorded output">
      <div className="ide-stats">
        <div className="ide-stat">
          <div className={`ide-stat-num${done ? " s-green" : ""}`}>{count}</div>
          <div className="ide-stat-lbl">Recorded steps</div>
        </div>
        <div className="ide-stat">
          <div className="ide-stat-num">{showCode ? Math.max(1, codeText.split(/\r?\n/).length) : "—"}</div>
          <div className="ide-stat-lbl">Lines of code</div>
        </div>
      </div>
      {showCode && (
        <pre className="ide-code" style={{ marginTop: 8, whiteSpace: "pre-wrap" }}>
          {done && !codePreview ? (
            <IDECodeLine tokens={[["kw", "await "], ["fn", "page.getByText"], "(", ["str", "'Get started'"], ", { ", ["prop", "exact"], ": ", ["kw", "true"], " }).", ["fn", "click"], "();"]} />
          ) : (
            codeText
          )}
        </pre>
      )}
      <div style={{ display: "flex", gap: 6, marginTop: 10 }}>
        <button className="ide-btn sm" type="button" style={{ flex: 1, justifyContent: "center" }}>
          Steps
        </button>
        <button className="ide-btn sm" type="button" style={{ flex: 1, justifyContent: "center" }}>
          Code
        </button>
      </div>
    </IDECard>
  );
}

function firstText(...values) {
  for (const value of values) {
    if (typeof value === "string" && value.trim()) {
      return value.trim();
    }
    if ((typeof value === "number" || typeof value === "boolean") && value !== "") {
      return String(value);
    }
  }
  return "";
}

function normalizeElementInfoForDisplay(info) {
  if (!info || typeof info !== "object") {
    return null;
  }

  const attributes = info.attributes && typeof info.attributes === "object" ? info.attributes : {};
  let className = firstText(info.className, info.class, attributes.className, attributes.class);
  if (!className && Array.isArray(info.classes)) {
    className = info.classes.filter(Boolean).map((value) => String(value).trim()).filter(Boolean).join(" ");
  }

  return {
    tag: firstText(info.tag, info.tagName, info.nodeName).toLowerCase() || "element",
    text: firstText(info.text, info.innerText, info.content, info.title, info.label, info.value),
    id: firstText(info.id, attributes.id),
    className,
  };
}

function shortenText(text, maxLength = 48) {
  const value = firstText(text);
  if (!value) {
    return "";
  }
  return value.length > maxLength ? `${value.slice(0, maxLength - 1)}…` : value;
}

function IDEPendingSteps({
  state,
  steps = [],
  live = false,
  activePickerStepId = "",
  onChangeIntent,
  onAddStep,
  onAttachElement,
}) {
  const hasRuntimeSteps = live && Array.isArray(steps) && steps.length > 0;
  const fallback = ["01 · Assert hero text", "02 · Click Get started"];
  const rows = live ? (hasRuntimeSteps ? steps : []) : fallback;
  const chipStyle = {
    display: "inline-flex",
    alignItems: "center",
    gap: 4,
    padding: "2px 6px",
    background: "#f4f0ea",
    border: "1px solid #ddd8d0",
    borderRadius: 2,
    fontSize: 10.5,
    color: "#4a4640",
    whiteSpace: "nowrap",
  };

  return (
    <IDECard color="amber" title="// pending steps">
      <div style={{ display: "flex", flexDirection: "column", gap: 5 }}>
        {rows.length > 0 ? (
          rows.map((step, i) => {
            if (typeof step === "string") {
              return (
                <div
                  key={i}
                  style={{
                    display: "flex",
                    gap: 8,
                    alignItems: "center",
                    padding: "6px 8px",
                    background: "#faf7f3",
                    border: "1px solid #ede8e0",
                    borderRadius: 2,
                    fontSize: 12,
                  }}
                >
                  <code style={{ fontSize: 10, color: "#9e9890" }}>{String(i + 1).padStart(2, "0")}</code>
                  <span style={{ flex: 1 }}>{step}</span>
                  <IDEBadge kind="ready">ready</IDEBadge>
                </div>
              );
            }

            const intent = step.intent ?? step.text ?? step.label ?? "";
            const elementInfo = normalizeElementInfoForDisplay(step.element_info ?? step.elementInfo ?? null);
            const isPicking = activePickerStepId === step.id;
            const badgeLabel = step.recorded === true
              ? "recorded"
              : isPicking
                ? "picking…"
                : intent.trim()
                  ? "ready"
                  : "draft";
            const badgeKind = step.recorded === true
              ? "recorded"
              : isPicking
                ? "await"
                : intent.trim()
                  ? "ready"
                  : "await";
            const cls = step.recorded === true ? "p-done" : isPicking ? "p-active" : intent.trim() ? "p-active" : "";
            return (
              <li
                key={i}
                className={cls}
              >
                <code style={{ fontSize: 10, color: "#9e9890" }}>{String(i + 1).padStart(2, "0")}</code>
                <div style={{ flex: 1, minWidth: 0 }}>
                  <div style={{ display: "flex", gap: 6, alignItems: "center", flexWrap: "wrap" }}>
                    <input
                      className="ide-input"
                      style={{ flex: 1, minWidth: 0, width: "auto", padding: "6px 8px" }}
                      value={intent}
                      onChange={(event) => onChangeIntent?.(step.id, event.target.value)}
                      placeholder="click Get started"
                    />
                    <IDEBadge kind={badgeKind}>{badgeLabel}</IDEBadge>
                    <button
                      className="ide-btn sm"
                      type="button"
                      onClick={() => onAttachElement?.(step.id)}
                    >
                      {isPicking ? "Click page element…" : "Attach Element"}
                    </button>
                  </div>
                  <div
                    style={{
                      marginTop: 6,
                      display: "flex",
                      flexWrap: "wrap",
                      gap: 6,
                      alignItems: "center",
                      fontSize: 10.5,
                      color: "#4a4640",
                    }}
                  >
                    {elementInfo ? (
                      <>
                        <span style={chipStyle}>{elementInfo.tag}</span>
                        {elementInfo.text && <span style={chipStyle}>&quot;{shortenText(elementInfo.text)}&quot;</span>}
                        {elementInfo.id && <span style={chipStyle}>#{elementInfo.id}</span>}
                        {elementInfo.className && (
                          <span style={chipStyle}>.{elementInfo.className.split(/\s+/).filter(Boolean).join(".")}</span>
                        )}
                      </>
                    ) : (
                      <span style={{ color: "#8f8a82" }}>{intent.trim() ? "No element attached." : "Draft step."}</span>
                    )}
                  </div>
                </div>
              </li>
            );
          })
        ) : (
          <div style={{ padding: "6px 2px", color: "#8f8a82", fontSize: 11.5 }}>Awaiting plan_ready…</div>
        )}
      </div>
    </IDECard>
  );
}

function IDECodePreview({ codePreview, live = false }) {
  const text = typeof codePreview === "string" && codePreview.trim()
    ? codePreview.trim()
    : live
      ? "Awaiting code_update…"
      : "Generated Playwright code will appear here.";

  return (
    <IDECard color="ink" title="// code preview">
      <pre className="ide-code" style={{ marginTop: 0, whiteSpace: "pre-wrap" }}>
        {text}
      </pre>
    </IDECard>
  );
}

function IDEDebugPane({ connectionStatus, lastEvent, lastError }) {
  return (
    <>
      <IDECard color="red" title="// transport">
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 6, fontSize: 11.5 }}>
          <div style={{ padding: "6px 8px", background: "#faf7f3", border: "1px solid #ede8e0", borderRadius: 2 }}>
            <div style={{ fontSize: 9.5, color: "#9e9890", textTransform: "uppercase", letterSpacing: ".08em", marginBottom: 2 }}>
              Connection
            </div>
            <div style={{ fontWeight: 700 }}>{connectionLabel(connectionStatus)}</div>
          </div>
          <div style={{ padding: "6px 8px", background: "#faf7f3", border: "1px solid #ede8e0", borderRadius: 2 }}>
            <div style={{ fontSize: 9.5, color: "#9e9890", textTransform: "uppercase", letterSpacing: ".08em", marginBottom: 2 }}>
              Last event
            </div>
            <div style={{ fontWeight: 700 }}>{lastEvent ? `${lastEvent.type}` : "—"}</div>
          </div>
        </div>
        {lastEvent?.txt && (
          <div style={{ marginTop: 8, fontSize: 11.5, color: "#4a4640", background: "#faf7f3", border: "1px solid #ede8e0", borderRadius: 2, padding: "8px 10px" }}>
            {lastEvent.txt}
          </div>
        )}
        {lastError && (
          <div className="ide-err-strip" style={{ marginTop: 10 }}>
            <IDEIcons.Warn size={12} />
            {lastError}
          </div>
        )}
      </IDECard>
      {lastError && (
        <IDECard color="ink" title="// log snapshot">
          <div style={{ fontSize: 11.5, color: "#4a4640", lineHeight: 1.6 }}>{lastError}</div>
        </IDECard>
      )}
    </>
  );
}

function IDEIdleComposer() {
  return (
    <IDECard color="blue" title="// new task">
      <textarea
        className="ide-input"
        rows={3}
        placeholder="// describe the task, e.g. open playwright.dev, assert hero text, then click Get started…"
      />
      <div style={{ display: "flex", gap: 6, marginTop: 8, justifyContent: "flex-end" }}>
        <button className="ide-btn primary" type="button">
          ▶ Plan task
        </button>
      </div>
    </IDECard>
  );
}

function IDEHeader({ state, connectionStatus = "disconnected" }) {
  const labels = {
    idle: "idle",
    planning: "planning…",
    await: "awaiting confirmation",
    exec: "executing",
    recover: "recovery needed",
    done: "completed",
  };

  const statusStyle = connectionStyle(connectionStatus);

  return (
    <div className="ide-hd" style={{ gap: 8 }}>
      <div className="ide-hd-logo">AW</div>
      <div>
        <div className="ide-hd-title">AutoWorkbench</div>
        <div className="ide-hd-sub">playwright co-pilot</div>
      </div>
      <div
        style={{
          marginLeft: "auto",
          display: "flex",
          alignItems: "center",
          gap: 6,
          flexWrap: "wrap",
          justifyContent: "flex-end",
        }}
      >
        <div className={`ide-hd-state s-${state}`}>{labels[state] || state}</div>
        <div
          style={{
            ...statusStyle,
            padding: "5px 8px",
            borderRadius: 999,
            fontSize: 10.5,
            fontWeight: 700,
            letterSpacing: ".04em",
            textTransform: "uppercase",
            lineHeight: 1,
          }}
        >
          {connectionLabel(connectionStatus)}
        </div>
      </div>
    </div>
  );
}

function IDEPanel({ state, tab, runtime = {}, onTabChange }) {
  const live = runtime.live !== false;
  const panelState = normalizePanelState(state);
  const connectionStatus = runtime.connectionStatus || "disconnected";
  const conversation = Array.isArray(runtime.conversation) ? runtime.conversation : [];
  const timeline = Array.isArray(runtime.timeline) ? runtime.timeline : [];
  const plan = runtime.plan || null;
  const pendingSteps = Array.isArray(runtime.pendingSteps) ? runtime.pendingSteps : [];
  const correctionText = typeof runtime.correctionText === "string" ? runtime.correctionText : "";
  const recordedCount = runtime.recordedCount ?? 0;
  const codePreview = typeof runtime.codePreview === "string" ? runtime.codePreview : "";
  const lastError = typeof runtime.lastError === "string" ? runtime.lastError : "";
  const lastEvent = runtime.lastEvent || null;
  const activePickerStepId = typeof runtime.activePickerStepId === "string" ? runtime.activePickerStepId : "";
  const planSteps = Array.isArray(plan?.steps) ? plan.steps : [];
  const stepCount = pendingSteps.length || planSteps.length || (["planning", "await", "exec", "recover", "done"].includes(panelState) ? 2 : 0);
  const showPlan = panelState === "await" || live || Boolean(plan);
  const showRecovery = panelState === "recover";

  return (
    <div className="ide-panel">
      <IDEHeader state={panelState} connectionStatus={connectionStatus} />
      <div className="ide-tabs">
        {[
          ["workbench", "workbench"],
          ["steps", "steps"],
          ["code", "code"],
          ["debug", "debug"],
        ].map(([id, label]) => (
          <button
            key={id}
            className={`ide-tab${tab === id ? " active" : ""}`}
            type="button"
            onClick={() => onTabChange?.(id)}
          >
            {label}
            {id === "steps" && stepCount > 0 && <span className="ide-tab-badge">{stepCount}</span>}
          </button>
        ))}
      </div>
      <div className="ide-body">
        {tab === "workbench" && (
          <>
            {panelState === "idle" && <IDEIdleComposer />}
            <IDEConversation state={panelState} messages={conversation} live={live} />
            <IDETimeline state={panelState} events={timeline} live={live} />
            {showPlan && (
              <IDEPlan
                state={panelState}
                plan={plan}
                live={live}
                correctionText={correctionText}
                onCorrectionTextChange={runtime.onCorrectionTextChange}
                onConfirmPlan={runtime.onConfirmPlan}
                onSendCorrection={runtime.onSendCorrection}
              />
            )}
            {showRecovery && <IDERecovery message={lastError} />}
            <IDEPendingSteps
              state={panelState}
              steps={pendingSteps.length > 0 ? pendingSteps : planSteps}
              live={live}
              activePickerStepId={activePickerStepId}
              onChangeIntent={runtime.onPendingStepIntentChange}
              onAddStep={runtime.onAddPendingStep}
              onAttachElement={runtime.onAttachElement}
            />
            <IDERecorded done={panelState === "done"} recordedCount={recordedCount} codePreview={codePreview} />
          </>
        )}
        {tab === "steps" && (
          <>
            <IDEPlan
              state={panelState}
              plan={plan}
              live={live}
              correctionText={correctionText}
              onCorrectionTextChange={runtime.onCorrectionTextChange}
              onConfirmPlan={runtime.onConfirmPlan}
              onSendCorrection={runtime.onSendCorrection}
            />
            <IDEPendingSteps
              state={panelState}
              steps={pendingSteps.length > 0 ? pendingSteps : planSteps}
              live={live}
              activePickerStepId={activePickerStepId}
              onChangeIntent={runtime.onPendingStepIntentChange}
              onAddStep={runtime.onAddPendingStep}
              onAttachElement={runtime.onAttachElement}
            />
            <IDERecorded done={panelState === "done"} recordedCount={recordedCount} codePreview={codePreview} />
          </>
        )}
        {tab === "code" && (
          <>
            <IDECodePreview codePreview={codePreview} live={live} />
            <IDERecorded done={panelState === "done"} recordedCount={recordedCount} codePreview={codePreview} />
          </>
        )}
        {tab === "debug" && (
          <>
            <IDEDebugPane connectionStatus={connectionStatus} lastEvent={lastEvent} lastError={lastError} />
            <IDETimeline state={panelState} events={timeline} live={live} />
          </>
        )}
      </div>
      {tab === "workbench" && (
        <div className="ide-bottom">
          <button className="ide-btn" type="button" onClick={() => runtime.onAddPendingStep?.()}>
            + Step
          </button>
          <button
            className="ide-btn primary"
            type="button"
            style={{ flex: 1, justifyContent: "center" }}
            onClick={() => runtime.onRunPendingSteps?.()}
          >
            Run Pending Steps
          </button>
        </div>
      )}
    </div>
  );
}

window.IDEPanel = IDEPanel;
