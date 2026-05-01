/* global React, Icons, AW */
// Panel header + tabs

const { Icons: I2 } = window;
const { IconBtn } = window.AW;

function PanelHeader({ stateKind, stateLabel }) {
  const stateClass = ({
    idle: "",
    planning: "s-planning",
    await: "s-await",
    exec: "s-exec",
    recover: "s-recover",
    done: "s-done",
  })[stateKind] || "";
  const dotClass = ({
    idle: "aw-dot-idle",
    planning: "aw-dot-warn",
    await: "aw-dot-warn",
    exec: "aw-dot-accent",
    recover: "aw-dot-danger",
    done: "",
  })[stateKind] || "";
  return (
    <div className="aw-hd">
      <div className="aw-hd-row1">
        <div className="aw-logo" />
        <div>
          <div className="aw-title">AutoWorkbench</div>
          <div className="aw-sub">PLAYWRIGHT CO-PILOT · v1.0</div>
        </div>
        <div className="aw-hd-ctl">
          <IconBtn icon={<I2.Settings size={13} />} title="Settings" />
          <IconBtn icon={<I2.Collapse size={13} />} title="Collapse panel" />
          <IconBtn icon={<I2.X size={13} />} title="Close" />
        </div>
      </div>
      <div className="aw-hd-row2">
        <span className="aw-conn">
          <span className={`aw-dot ${dotClass}`} />
          <span className={`aw-state-pill ${stateClass}`}>{stateLabel}</span>
        </span>
        <div className="aw-url" title="https://playwright.dev/">
          <I2.Globe size={11} />
          <span>playwright.dev/</span>
        </div>
      </div>
    </div>
  );
}

function Tabs({ active, counts, onChange }) {
  const tabs = [
    { id: "workbench", label: "Workbench" },
    { id: "steps", label: "Steps", count: counts?.steps },
    { id: "code", label: "Code" },
    { id: "debug", label: "Debug" },
  ];
  return (
    <div className="aw-tabs" role="tablist">
      {tabs.map((t) => (
        <button
          key={t.id}
          role="tab"
          className={`aw-tab${active === t.id ? " active" : ""}`}
          onClick={() => onChange?.(t.id)}
        >
          {t.label}
          {t.count != null && <span className="aw-tab-count">{t.count}</span>}
        </button>
      ))}
    </div>
  );
}

window.AW.PanelHeader = PanelHeader;
window.AW.Tabs = Tabs;
