// frontend/src/v4/chrome.jsx — ES module port of v4/chrome.jsx
// Header / TabStrip / NowStrip / Footer / AgentsPopover wired via props.
import React from "react";
import { I } from "./icons.jsx";

const STATUS_MAP = {
  connected: { cls: "ok", label: "Connected" },
  busy: { cls: "busy", label: "Running" },
  reconnect: { cls: "warn", label: "Reconnecting" },
  offline: { cls: "err", label: "Offline" },
  error: { cls: "err", label: "LLM error" },
};

export function Header({
  status = "connected",
  dock = "right",
  setDock = () => {},
  collapsed = false,
  setCollapsed = () => {},
  tokenInfo = { tok: "0", cost: "0.00" },
  runState = "—",
  agentsOpen = false,
  setAgentsOpen = () => {},
  agentsSummary = ["on", "on", "on", "off", "off"],
  pageUrl = "",
}) {
  const dockBtn = (kind, Icon, title) => (
    <button type="button"
      className={"aw-icon-btn " + (dock === kind ? "active" : "")}
      onClick={() => setDock(kind)}
      title={title}
      aria-label={title}
      data-testid={`aw-dock-${kind}`}
    >
      <Icon />
    </button>
  );
  const s = STATUS_MAP[status] || STATUS_MAP.connected;
  const pageLabel = pageUrl ? pageUrl.replace(/^[^/]+/, "") : "—";

  return (
    <header className="aw-header" data-testid="aw-header">
      <div className="aw-header-main">
        <div className="aw-brand">
          <span className="aw-logo" aria-hidden="true" />
          <span>AutoWorkbench</span>
        </div>
        <span className="aw-brand-divider" />
        <span
          className={"aw-status-pill " + s.cls}
          title="Backend connection"
          data-testid="aw-status-pill"
          data-status={status}
        >
          <span className="aw-dot" />
          {s.label}
        </span>
        <span
          className="aw-mode-toggle"
          role="group"
          aria-label="Interaction mode"
          data-testid="aw-mode-toggle"
        >
          <button
            type="button"
            className="aw-mode-opt active"
            aria-pressed="true"
            title="Complete LLM Mode (active)"
            data-testid="aw-mode-llm"
          >
            <span className="aw-dot" />
            LLM
          </button>
          <button
            type="button"
            className="aw-mode-opt"
            aria-pressed="false"
            aria-disabled="true"
            disabled
            tabIndex={-1}
            title="Manual Mode not available — backend seam required. Coming in Sprint 8 (D-105 / BUG-S8-MANUAL-001)."
            data-testid="aw-mode-manual"
            data-disabled-reason="sprint-8"
          >
            Manual
          </button>
        </span>
        <button type="button"
          className={"aw-agents-btn " + (agentsOpen ? "open" : "")}
          onClick={() => setAgentsOpen(!agentsOpen)}
          title="Agent Control Center"
          data-testid="aw-agents-toggle"
        >
          <I.Layers style={{ width: 11, height: 11 }} />
          <span>Agents</span>
          <span className="dots">
            {agentsSummary.map((c, i) => (
              <i key={i} className={c} />
            ))}
          </span>
        </button>
        <span
          className="aw-status-pill shrinkable"
          title={"Current page · " + (pageUrl || "—")}
        >
          <I.Globe style={{ width: 10, height: 10, color: "var(--tx-3)" }} />
          <span className="v">{pageLabel}</span>
        </span>
        <span className="aw-spacer" />
        <span
          className="aw-status-pill"
          title={`run ${runState} · ${tokenInfo.tok} tokens · $${tokenInfo.cost}`}
          data-testid="aw-run-pill"
        >
          <span className="v">{tokenInfo.tok}</span>
          <span className="k">·</span>
          <span className="v">${tokenInfo.cost}</span>
        </span>
        {dockBtn("right", I.Dock, "Dock right")}
        {dockBtn("left", I.DockL, "Dock left")}
        {dockBtn("top", I.DockTop, "Dock top")}
        {dockBtn("float", I.Float, "Float")}
        <button type="button"
          className="aw-icon-btn"
          onClick={() => setCollapsed(!collapsed)}
          title="Collapse"
          data-testid="aw-collapse"
        >
          <I.Min />
        </button>
        <button type="button" className="aw-icon-btn" title="Settings">
          <I.Settings />
        </button>
      </div>
    </header>
  );
}

export function TabStrip({ tab, setTab, counts = {} }) {
  const tabs = [
    { id: "llm", label: "LLM", Icon: I.Spark, badge: counts.llm },
    { id: "steps", label: "Steps", Icon: I.Steps, badge: counts.steps },
    { id: "rec", label: "Recorded", Icon: I.Camera, badge: counts.rec },
    { id: "code", label: "Code", Icon: I.Code, badge: counts.code },
    { id: "trace", label: "Trace", Icon: I.Trace, badge: counts.trace },
  ];
  return (
    <nav className="aw-tabs" role="tablist" data-testid="aw-tabs">
      {tabs.map((t) => (
        <button type="button"
          key={t.id}
          role="tab"
          aria-selected={tab === t.id}
          className={"aw-tab " + (tab === t.id ? "active" : "")}
          onClick={() => setTab(t.id)}
          data-testid={`aw-tab-${t.id}`}
        >
          <t.Icon style={{ width: 13, height: 13 }} />
          {t.label}
          {t.badge != null && <span className="aw-badge">{t.badge}</span>}
        </button>
      ))}
    </nav>
  );
}

export function NowStrip({ kind = "idle", state, task, refLabel, primaryLabel, primaryIcon: PI, onPrimary }) {
  if (!state && !task) return null;
  return (
    <div className={"aw-now " + kind} data-testid="aw-now">
      <span className="aw-now-rail" />
      <div className="aw-now-main">
        <div className="aw-now-eyebrow">
          Current task
          {state ? <span className="aw-now-state">{state}</span> : null}
        </div>
        <div className="aw-now-task">
          {task}
          {refLabel ? <span className="ref">{refLabel}</span> : null}
        </div>
      </div>
      {primaryLabel ? (
        <div className="aw-now-actions">
          <button type="button"
            className="aw-btn primary"
            onClick={() => typeof onPrimary === "function" && onPrimary()}
            data-testid="aw-now-primary"
          >
            {PI ? <PI /> : null}
            {primaryLabel}
          </button>
        </div>
      ) : null}
    </div>
  );
}

export function Footer({ phase, event, blocker, nextAction, busy }) {
  return (
    <footer className="aw-footer ide-hd-state" data-testid="aw-footer">
      <span className="aw-footer-phase">
        {busy ? (
          <span className="aw-bar">
            <i />
            <i />
            <i />
            <i />
          </span>
        ) : null}
        {phase || "Idle"}
      </span>
      <span className="aw-footer-event">
        <span className="em">last:</span> {event || "—"}
        {blocker ? (
          <>
            {" · "}
            <span style={{ color: "var(--red)", fontWeight: 500 }} data-testid="aw-footer-blocker">
              blocked: {blocker}
            </span>
          </>
        ) : null}
      </span>
      {nextAction ? (
        <span className="aw-footer-next">
          <I.CaretR style={{ width: 11, height: 11 }} />
          {nextAction}
        </span>
      ) : null}
    </footer>
  );
}

const SPRINT8_DISABLED_TITLE =
  "Agent controls deferred to Sprint 8 (BUG-S8-AGENT-001)";

export function AgentsPopover({ onClose, agents }) {
  // Backend does not emit agent_settings / agent_progress / agent_result /
  // agent_failed / agent_trace today. Until BUG-S8-AGENT-001 wires the
  // backend agent registry, the popover renders an honest disabled state
  // when no payload is present. We never fall back to a hardcoded mock list
  // (no DEFAULT_AGENTS in production path).
  const list = Array.isArray(agents) ? agents : [];
  const hasPayload = list.length > 0;
  return (
    <div className="aw-agents-pop" role="dialog" aria-label="Agent Control Center" data-testid="aw-agents-popover">
      <div className="aw-agents-head">
        <span
          className="aw-card-icon"
          style={{
            width: 22,
            height: 22,
            borderRadius: 6,
            background: "var(--acc-tint)",
            color: "var(--acc-2)",
          }}
        >
          <I.Layers style={{ width: 12, height: 12 }} />
        </span>
        <div>
          <div className="t">Agent Control Center</div>
        </div>
        <span
          className="aw-agents-sprint8-badge"
          data-testid="aw-agents-sprint8-badge"
          title={SPRINT8_DISABLED_TITLE}
        >
          Read-only — Sprint 8
        </span>
        <span className="x" onClick={onClose} data-testid="aw-agents-close">
          <I.X style={{ width: 13, height: 13 }} />
        </span>
      </div>
      {!hasPayload ? (
        <div
          className="aw-agents-empty"
          data-testid="aw-agents-empty"
          role="status"
        >
          <I.Info style={{ width: 11, height: 11 }} />
          <span>
            No agent registry available. Backend does not yet emit{" "}
            <code>agent_settings</code>; wired in Sprint 8 (BUG-S8-AGENT-001).
          </span>
        </div>
      ) : (
        list.map((a) => {
          const status = a.status || "standby";
          const cls =
            status === "running"
              ? "running"
              : status === "active"
              ? "active"
              : status === "disabled"
              ? "disabled"
              : "standby";
          return (
            <div key={a.key} className={"aw-agent-row " + cls} data-testid={`aw-agent-row-${a.key}`}>
              <span className="aw-agent-av">{a.initials}</span>
              <div>
                <div className="aw-agent-name">
                  {a.name}
                  {a.required ? <span className="aw-pin-required">Required</span> : null}
                </div>
                <div className="aw-agent-model">{a.model}</div>
                <div className="aw-agent-last">
                  <span className="em">last:</span> {a.last ?? "—"}
                </div>
              </div>
              <div className="aw-agent-ctrl">
                <span className={"aw-agent-status " + cls}>
                  <span className="ldot" />
                  {status === "queued" ? "queued" : status}
                </span>
                {a.required ? (
                  <button
                    type="button"
                    className="aw-toggle on locked"
                    aria-label="locked on"
                    title="Required — always on"
                    disabled
                  />
                ) : (
                  <button
                    type="button"
                    className={"aw-toggle " + (status === "disabled" ? "" : "on")}
                    data-testid={`aw-agent-toggle-${a.key}`}
                    title={SPRINT8_DISABLED_TITLE}
                    disabled
                  />
                )}
              </div>
            </div>
          );
        })
      )}
      <div className="aw-agents-foot">
        <I.Info style={{ width: 11, height: 11 }} />
        <span>
          Agent enable/disable commands land in Sprint 8 (BUG-S8-AGENT-001).
          Controls are read-only until backend emits the agent registry.
        </span>
        <span style={{ flex: 1 }} />
      </div>
    </div>
  );
}

export function CollapsedRail({ tab, setTab, setCollapsed }) {
  const items = [
    { id: "llm", Icon: I.Spark },
    { id: "steps", Icon: I.Steps },
    { id: "rec", Icon: I.Camera },
    { id: "code", Icon: I.Code },
    { id: "trace", Icon: I.Trace },
  ];
  return (
    <div className="aw-collapsed-rail" data-testid="aw-collapsed-rail">
      <button type="button" className="aw-icon-btn" onClick={() => setCollapsed(false)} title="Expand">
        <I.CaretR style={{ transform: "rotate(180deg)" }} />
      </button>
      <div className="aw-rail-sep" />
      {items.map((it) => (
        <button type="button"
          key={it.id}
          className={"aw-icon-btn " + (tab === it.id ? "active" : "")}
          onClick={() => setTab(it.id)}
          data-testid={`aw-rail-tab-${it.id}`}
        >
          <it.Icon />
        </button>
      ))}
    </div>
  );
}

export default { Header, TabStrip, NowStrip, Footer, AgentsPopover, CollapsedRail };
