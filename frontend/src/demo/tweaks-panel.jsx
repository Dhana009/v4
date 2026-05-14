// FE-VBATCH-002 Story 4 — Tweaks side panel (demo-only).
//
// Ports the yui ROOT tweaks panel as a demo/preview side overlay that
// mutates preview-local UI state through a single `onChange(edits)`
// callback. The host page activates it by posting `__activate_edit_mode`
// on `window`, dismisses with `__deactivate_edit_mode`, and the panel
// also posts a same-window `tweakchange` CustomEvent so non-React demo
// hosts can react.
//
// HARD CONSTRAINT: this module never touches backend lifecycle truth.
// It is imported only by demo entries (e.g. `dist/preview.html`). The
// live runtime (`main.jsx` → `aw-ide-panel.jsx`) does NOT import it.

import React, { useEffect, useRef, useState } from "react";

const SECTIONS = [
  {
    id: "panel",
    label: "Panel",
    fields: [
      {
        kind: "radio",
        key: "dock",
        label: "Dock",
        options: ["right", "left", "top", "float"],
      },
      {
        kind: "slider",
        key: "panelWidth",
        label: "Panel width",
        min: 300,
        max: 720,
        step: 10,
        unit: "px",
      },
      { kind: "toggle", key: "collapsed", label: "Collapsed" },
      { kind: "toggle", key: "showWebsite", label: "Show website behind" },
    ],
  },
  {
    id: "active",
    label: "Active tab",
    fields: [
      {
        kind: "radio",
        key: "tab",
        label: "Tab",
        options: ["llm", "steps", "rec", "code", "trace"],
      },
    ],
  },
  {
    id: "lifecycle",
    label: "Lifecycle state (LLM tab)",
    fields: [
      {
        kind: "select",
        key: "state",
        label: "State",
        options: [
          "idle",
          "planning",
          "clarify",
          "recommend",
          "plan",
          "diff",
          "permit",
          "exec",
          "locator",
          "recover",
          "done",
          "offline",
          "schema",
          "nobrowser",
          "apikey",
          "otp",
          "e2e",
        ],
      },
    ],
  },
  {
    id: "theme",
    label: "Theme",
    fields: [{ kind: "radio", key: "theme", label: "Theme", options: ["light", "dark"] }],
  },
  {
    id: "mode",
    label: "Interaction mode",
    fields: [{ kind: "radio", key: "mode", label: "Mode", options: ["llm", "manual"] }],
  },
  {
    id: "overlays",
    label: "Overlays",
    fields: [{ kind: "toggle", key: "agentsOpen", label: "Agent Control Center" }],
  },
  {
    id: "highlight",
    label: "Page highlight",
    fields: [
      {
        kind: "radio",
        key: "highlight",
        label: "Highlight CTA",
        options: ["none", "hero-cta", "pro-cta"],
      },
    ],
  },
];

export const DEFAULT_TWEAKS = {
  dock: "right",
  panelWidth: 600,
  collapsed: false,
  showWebsite: true,
  tab: "llm",
  state: "locator",
  theme: "light",
  mode: "llm",
  agentsOpen: false,
  highlight: "hero-cta",
};

function broadcast(edits) {
  try {
    window.dispatchEvent(new CustomEvent("tweakchange", { detail: edits }));
  } catch (_) {}
}

function Toggle({ value, onChange, testid }) {
  return (
    <button
      type="button"
      className={"twk-toggle" + (value ? " on" : "")}
      data-testid={testid}
      aria-pressed={value ? "true" : "false"}
      onClick={() => onChange(!value)}
    >
      <span className="twk-thumb" />
    </button>
  );
}

function Radio({ value, options, onChange, testid }) {
  return (
    <span className="twk-seg" role="group" data-testid={testid}>
      {options.map((opt) => (
        <button
          type="button"
          key={opt}
          className={"twk-seg-opt" + (value === opt ? " active" : "")}
          data-testid={`${testid}-${opt}`}
          aria-pressed={value === opt ? "true" : "false"}
          onClick={() => onChange(opt)}
        >
          {opt}
        </button>
      ))}
    </span>
  );
}

function Slider({ value, min, max, step, unit, onChange, testid }) {
  return (
    <span className="twk-slider">
      <input
        type="range"
        min={min}
        max={max}
        step={step}
        value={value}
        data-testid={testid}
        onChange={(e) => onChange(Number(e.target.value))}
      />
      <span className="twk-num">
        {value}
        {unit}
      </span>
    </span>
  );
}

function Select({ value, options, onChange, testid }) {
  return (
    <select
      className="twk-select"
      value={value}
      data-testid={testid}
      onChange={(e) => onChange(e.target.value)}
    >
      {options.map((opt) => (
        <option key={opt} value={opt}>
          {opt}
        </option>
      ))}
    </select>
  );
}

export function TweaksPanel({
  value = DEFAULT_TWEAKS,
  onChange = () => {},
  defaultOpen = false,
}) {
  const [open, setOpen] = useState(defaultOpen);
  const panelRef = useRef(null);

  useEffect(() => {
    function onMessage(ev) {
      if (!ev || !ev.data || typeof ev.data.type !== "string") return;
      if (ev.data.type === "__activate_edit_mode") setOpen(true);
      else if (ev.data.type === "__deactivate_edit_mode") setOpen(false);
    }
    window.addEventListener("message", onMessage);
    return () => window.removeEventListener("message", onMessage);
  }, []);

  const setKey = (key, next) => {
    const edits = { [key]: next };
    onChange({ ...value, ...edits });
    broadcast(edits);
  };

  if (!open) return null;

  return (
    <aside
      ref={panelRef}
      className="twk-panel"
      role="dialog"
      aria-label="Tweaks panel"
      data-testid="aw-tweaks-panel"
    >
      <header className="twk-hd">
        <span className="twk-title">Tweaks</span>
        <button
          type="button"
          className="twk-x"
          data-testid="aw-tweaks-close"
          onClick={() => setOpen(false)}
          aria-label="Close tweaks"
        >
          ×
        </button>
      </header>
      <div className="twk-body">
        {SECTIONS.map((sec) => (
          <section key={sec.id} className="twk-sect" data-testid={`aw-tweaks-section-${sec.id}`}>
            <div className="twk-sect-label">{sec.label}</div>
            {sec.fields.map((f) => (
              <div key={f.key} className="twk-row">
                <span className="twk-lbl">{f.label}</span>
                <span className="twk-val">
                  {f.kind === "toggle" ? (
                    <Toggle
                      value={!!value[f.key]}
                      onChange={(v) => setKey(f.key, v)}
                      testid={`aw-tweaks-${f.key}`}
                    />
                  ) : f.kind === "radio" ? (
                    <Radio
                      value={value[f.key]}
                      options={f.options}
                      onChange={(v) => setKey(f.key, v)}
                      testid={`aw-tweaks-${f.key}`}
                    />
                  ) : f.kind === "slider" ? (
                    <Slider
                      value={Number(value[f.key])}
                      min={f.min}
                      max={f.max}
                      step={f.step}
                      unit={f.unit}
                      onChange={(v) => setKey(f.key, v)}
                      testid={`aw-tweaks-${f.key}`}
                    />
                  ) : f.kind === "select" ? (
                    <Select
                      value={value[f.key]}
                      options={f.options}
                      onChange={(v) => setKey(f.key, v)}
                      testid={`aw-tweaks-${f.key}`}
                    />
                  ) : null}
                </span>
              </div>
            ))}
          </section>
        ))}
      </div>
    </aside>
  );
}

export default TweaksPanel;
