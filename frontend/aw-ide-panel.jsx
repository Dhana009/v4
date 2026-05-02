import React from "react";

/* global Icons */
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
  const normalized = String(kind || "step").toLowerCase();
  const map = { click: "click", fill: "fill", assert: "assert", navigate: "nav", nav: "nav" };
  const label = normalized === "nav" ? "navigate" : normalized;
  return <span className={`ide-plan-tag t-${map[normalized] || normalized}`}>{label}</span>;
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

function getPlanStepChildren(step) {
  if (!step || typeof step !== "object") {
    return [];
  }

  if (Array.isArray(step.children)) {
    return step.children;
  }

  const raw = step.raw;
  if (raw && typeof raw === "object" && Array.isArray(raw.children)) {
    return raw.children;
  }

  return [];
}

function normalizePlanChild(child, index) {
  if (child == null) {
    return null;
  }

  const source = typeof child === "object" ? child : { text: child };
  const operationId = firstText(
    source.operation_id,
    source.operationId,
    source.op_id,
    source.opId,
    source.id,
    source.step_id,
    source.stepId
  );
  const kind = normalizeStepAction(source.type || source.kind || source.action);
  const description = pickRecordedText(
    source.description,
    source.target,
    source.text,
    source.label,
    source.title,
    source.intent,
    `Child ${index + 1}`
  );
  const locator = firstText(source.locator, source.selector, source.xpath, source.css, source.path);

  return {
    key: operationId ? `${operationId}-${index + 1}` : `plan-child-${index + 1}`,
    operationId,
    kind,
    description: description || `Child ${index + 1}`,
    locator: locator && locator.length <= 56 ? locator : "",
  };
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
  const scrollRef = React.useRef(null);
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
    plan_review: [
      { w: "user", t: "10:41", txt: "Open playwright.dev, assert hero text exists, then click Get started." },
      { w: "agent", t: "10:41", txt: "Plan ready for your review." },
    ],
    clarification: [
      { w: "user", t: "10:41", txt: "Open playwright.dev, assert hero text exists, then click Get started." },
      { w: "agent", t: "10:41", txt: "I need a clarification before I can continue." },
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
    executing: [
      { w: "user", t: "10:41", txt: "Open playwright.dev, assert hero text, then click Get started." },
      {
        w: "agent",
        t: "10:42",
        txt: (
          <>
            <span className="ide-spinner" style={{ color: "#4a9eff" }} />Executing the current step…
          </>
        ),
      },
    ],
    recover: [
      { w: "user", t: "10:41", txt: "Open playwright.dev, assert hero text, then click Get started." },
      { w: "system", t: "10:42", txt: "Step failed: page navigated before assertion ran. Hero element no longer in DOM." },
      { w: "agent", t: "10:42", txt: "Recovery suggestion: go back → assert first → re-click." },
    ],
    recovery: [
      { w: "user", t: "10:41", txt: "Open playwright.dev, assert hero text, then click Get started." },
      { w: "system", t: "10:42", txt: "Step failed: page navigated before assertion ran. Hero element no longer in DOM." },
      { w: "agent", t: "10:42", txt: "Recovery guidance needed." },
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
    completed: [
      { w: "user", t: "10:41", txt: "Open playwright.dev, assert hero text exists, then click Get started." },
      {
        w: "agent",
        t: "10:42",
        txt: (
          <>
            <b style={{ color: "#1f9d6a" }}>All steps recorded.</b> Generated 4 lines of Playwright TS — see Code tab.
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

  React.useEffect(() => {
    const node = scrollRef.current;
    if (!node) {
      return;
    }
    node.scrollTop = node.scrollHeight;
  }, [rows.length]);

  return (
    <IDECard color="violet" title="// conversation">
      <div ref={scrollRef} className="ide-scrollbox ide-scrollbox-conversation" style={{ maxHeight: 228 }}>
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
      </div>
    </IDECard>
  );
}

function IDEPlanReview({
  plan,
  live = false,
  correctionText = "",
  onCorrectionTextChange,
  onConfirmPlan,
  onSendCorrection,
}) {
  const hasRuntimePlan = live && plan && Array.isArray(plan.steps);
  const fallbackItems = [
    { type: "assert", text: "Assert hero heading is visible", cls: "" },
    { type: "click", text: 'Click "Get started" link', cls: "" },
  ];

  const items = live ? (hasRuntimePlan ? plan.steps : []) : fallbackItems;
  const planIsCompleted =
    hasRuntimePlan &&
    items.length > 0 &&
    items.every((step) => {
      const status = firstText(step.status, step.state, step.cls).toLowerCase();
      return step.recorded === true || step.completed === true || ["done", "completed", "recorded", "passed"].includes(status);
    });
  const summary = hasRuntimePlan
    ? planIsCompleted
      ? plan.summary || "All plan steps recorded"
      : plan.summary || "Plan ready"
    : live
      ? "Waiting for plan_ready…"
      : "2 actions · ~3s";
  const showPlaceholder = live && (!plan || !Array.isArray(plan.steps) || plan.steps.length === 0);
  const planBadge = planIsCompleted ? "Completed" : "Awaiting confirmation";

  return (
    <IDECard
      color="blue"
      title="// plan review"
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
        <IDEBadge kind={planIsCompleted ? "recorded" : "await"}>{planBadge}</IDEBadge>
        <span style={{ fontSize: 10.5, color: "#9e9890" }}>{summary}</span>
      </div>
      {showPlaceholder && (
        <div style={{ marginBottom: 8, fontSize: 11.5, color: "#8f8a82" }}>Waiting for plan_ready…</div>
      )}
      {items.length > 0 ? (
        <div className="ide-scrollbox ide-scrollbox-plan" style={{ maxHeight: 180 }}>
          <ol className="ide-plan">
            {items.map((it, i) => {
              const kind = it.kind || it.type || "step";
              const text = it.text || it.label || it.title || `Step ${i + 1}`;
              const status = firstText(it.status, it.state, it.cls).toLowerCase();
              const childRows = getPlanStepChildren(it).map((child, childIndex) => normalizePlanChild(child, childIndex)).filter(Boolean);
              const cls =
                it.cls ||
                (it.recorded === true || it.completed === true || ["done", "completed", "recorded", "passed"].includes(status)
                  ? "done"
                  : status === "active"
                    ? "active"
                    : "");
              return (
                <li key={i} className={cls}>
                  <div className="ide-plan-parent-row">
                    <span className="ide-plan-num">{i + 1}.</span>
                    <span className="ide-plan-text">{text}</span>
                    <IDEPlanTag kind={kind} />
                  </div>
                  {childRows.length > 0 && (
                    <div className="ide-plan-children">
                      {childRows.map((child) => (
                        <div key={child.key} className="ide-plan-child">
                          <div className="ide-plan-child-head">
                            {child.operationId && <span className="ide-plan-child-op">{child.operationId}</span>}
                            <IDEPlanTag kind={child.kind} />
                          </div>
                          <div className="ide-plan-child-desc">{child.description}</div>
                          {child.locator && <code className="ide-plan-child-locator">{child.locator}</code>}
                        </div>
                      ))}
                    </div>
                  )}
                </li>
              );
            })}
          </ol>
        </div>
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

function IDEClarificationCard({
  question = "",
  options = [],
  answerText = "",
  onAnswerTextChange,
  onSendAnswer,
}) {
  const hasOptions = Array.isArray(options) && options.length > 0;
  const text = question || "The agent needs a clarification before it can continue.";

  return (
    <IDECard
      color="violet"
      title="// clarification needed"
      footer={[
        <button
          key="s"
          className="ide-btn primary"
          type="button"
          style={{ flex: 1, justifyContent: "center" }}
          onClick={() => onSendAnswer?.()}
        >
          Send Answer
        </button>,
      ]}
    >
      <div className="ide-clarification-question">{text}</div>
      {hasOptions && (
        <div className="ide-clarification-options">
          {options.map((option, index) => {
            const label = option?.label || option?.value || String(option);
            const value = option?.value || option?.label || label;
            return (
              <button
                key={option?.id || `${index}`}
                className="ide-btn sm ide-clarification-option"
                type="button"
                onClick={() => onSendAnswer?.(value)}
              >
                {label}
              </button>
            );
          })}
        </div>
      )}
      <textarea
        className="ide-input"
        rows={3}
        placeholder="Answer clarification…"
        value={answerText}
        onChange={(event) => onAnswerTextChange?.(event.target.value)}
      />
    </IDECard>
  );
}

function IDERecovery({ message, currentUrl, recoveryText = "", onRecoveryTextChange, onSendRecoveryInstruction }) {
  const issue = message || "Action failed. The agent needs recovery guidance.";

  return (
    <IDECard
      color="red"
      title="// recovery needed"
      footer={[
        <button
          key="s"
          className="ide-btn primary"
          type="button"
          style={{ flex: 1, justifyContent: "center" }}
          onClick={() => onSendRecoveryInstruction?.()}
        >
          Send Recovery Instruction
        </button>,
      ]}
    >
      <div className="ide-err-strip" style={{ marginBottom: 10 }}>
        <IDEIcons.Warn size={12} />
        {issue}
      </div>
      {currentUrl && (
        <div className="ide-recovery-url">
          <div className="ide-recovery-url-label">Current URL</div>
          <code className="ide-recovery-url-code">{currentUrl}</code>
        </div>
      )}
      <textarea
        className="ide-input"
        rows={3}
        placeholder="Tell the agent how to recover..."
        value={recoveryText}
        onChange={(event) => onRecoveryTextChange?.(event.target.value)}
      />
    </IDECard>
  );
}

function IDETimeline({ state, events = [], live = false }) {
  const scrollRef = React.useRef(null);
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
    plan_review: [
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
    executing: [
      { d: "ok", t: "10:42:00", txt: "Action acknowledged" },
      { d: "active", t: "10:42:01", txt: "Executing the next step…" },
    ],
    recover: [
      { d: "ok", t: "10:42:00", txt: "Plan confirmed" },
      { d: "ok", t: "10:42:02", txt: "Click executed" },
      { d: "warn", t: "10:42:14", txt: "Page navigated → /docs/intro" },
      { d: "err", t: "10:42:14", txt: "Assertion failed · hero not in DOM" },
    ],
    recovery: [
      { d: "ok", t: "10:42:00", txt: "Recovery needed" },
      { d: "err", t: "10:42:14", txt: "Failure reason captured" },
    ],
    done: [
      { d: "ok", t: "10:42:00", txt: "Plan confirmed" },
      { d: "ok", t: "10:42:02", txt: "Assertion passed" },
      { d: "ok", t: "10:42:04", txt: "Click executed · /docs/intro" },
      { d: "ok", t: "10:42:05", txt: "Code generated · 4 lines" },
    ],
    completed: [
      { d: "ok", t: "10:42:00", txt: "Plan confirmed" },
      { d: "ok", t: "10:42:02", txt: "All recorded steps complete" },
      { d: "ok", t: "10:42:05", txt: "Code generated · 4 lines" },
    ],
    clarification: [
      { d: "warn", t: "10:41:32", txt: "Clarification needed" },
      { d: "active", t: "10:41:33", txt: "Waiting for user answer…" },
    ],
  }[state] || [];

  const rows = live ? events : fallback;

  React.useEffect(() => {
    const node = scrollRef.current;
    if (!node) {
      return;
    }
    node.scrollTop = node.scrollHeight;
  }, [rows.length]);

  if (!rows.length) return null;

  return (
    <IDECard color="ink" title="// execution">
      <div ref={scrollRef} className="ide-scrollbox ide-scrollbox-timeline" style={{ maxHeight: 208 }}>
        <div className="ide-tl">
          {rows.map((r, i) => (
            <div key={i} className="ide-tl-row">
              <div className={`ide-tl-dot d-${r.d || "ok"}`} />
              <div className="ide-tl-text">{r.txt !== undefined ? r.txt : r.text}</div>
              <div className="ide-tl-time">{r.t || r.time || ""}</div>
            </div>
          ))}
        </div>
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

function firstRawText(...values) {
  for (const value of values) {
    if (typeof value === "string" && value !== "") {
      return value;
    }
    if (typeof value === "number" || typeof value === "boolean") {
      return String(value);
    }
  }
  return "";
}

function isTechnicalRecordedLabel(value) {
  const text = firstText(value);
  if (!text) {
    return false;
  }

  const trimmed = text.trim();
  return (
    /^(css|xpath|text|role|id|name|label)=/i.test(trimmed) ||
    /^\/{1,2}/.test(trimmed) ||
    /[.#\[\]()>]/.test(trimmed) ||
    /^[a-z][\w-]*(?:[.#][\w-]+)+$/i.test(trimmed)
  );
}

function simplifyRecordedSubject(value) {
  const text = firstText(value);
  if (!text) {
    return "";
  }

  const lower = text.toLowerCase();
  if (/^h[1-6]$/.test(lower)) return "heading";
  if (lower === "a") return "link";
  if (lower === "button") return "button";
  if (lower === "input" || lower === "textarea" || lower === "select") return "input";
  if (lower === "img") return "image";
  if (lower === "li") return "list item";
  if (lower === "form") return "form";

  if (/^[a-z][\w-]*(?:[.#][\w-]+)+$/i.test(text)) {
    const base = text.split(/[.#\[]/, 1)[0].toLowerCase();
    if (/^h[1-6]$/.test(base)) return "heading";
    if (base === "a") return "link";
    if (base === "button") return "button";
    if (base === "input" || base === "textarea" || base === "select") return "input";
    if (base === "img") return "image";
  }

  return text;
}

function pickRecordedText(...values) {
  for (const value of values) {
    const text = firstText(value);
    if (!text) {
      continue;
    }
    if (!isTechnicalRecordedLabel(text)) {
      return text;
    }
    const simplified = simplifyRecordedSubject(text);
    if (simplified && !isTechnicalRecordedLabel(simplified)) {
      return simplified;
    }
  }

  return firstText(...values);
}

function titleFromAction(action, subject, stepNumber) {
  const fallback = Number.isFinite(stepNumber) && stepNumber > 0 ? `Step ${stepNumber}` : "Recorded step";
  const cleaned = firstText(subject);
  if (!cleaned) {
    return fallback;
  }

  switch (action) {
    case "click":
      return `Clicked ${cleaned}`;
    case "fill":
      return `Filled ${cleaned}`;
    case "assert":
      return `Asserted ${cleaned}`;
    case "navigate":
      return `Navigated ${cleaned}`;
    case "hover":
      return `Hovered ${cleaned}`;
    default:
      return `Recorded ${cleaned}`;
  }
}

function resolveRecordedStepTitle(step, action, stepNumber) {
  const elementInfo = step?.element_info && typeof step.element_info === "object" ? step.element_info : null;
  const explicitTitle = firstText(step?.display_title, step?.displayTitle, step?.title, step?.label);
  if (explicitTitle && !isTechnicalRecordedLabel(explicitTitle)) {
    if (/^(clicked|filled|asserted|navigated|hovered|recorded|step)\b/i.test(explicitTitle)) {
      return explicitTitle;
    }
    return titleFromAction(action, explicitTitle, stepNumber);
  }

  const subject = pickRecordedText(
    step?.target_label,
    step?.element_name,
    step?.elementName,
    step?.target,
    step?.name,
    elementInfo?.text,
    elementInfo?.label,
    elementInfo?.title,
    elementInfo?.name,
    simplifyRecordedSubject(firstRawText(elementInfo?.tag, elementInfo?.tagName, elementInfo?.nodeName))
  );

  if (subject) {
    return titleFromAction(action, subject, stepNumber);
  }

  const locator = pickRecordedText(step?.locator, step?.selector, step?.xpath, step?.css, step?.path);
  if (locator) {
    return titleFromAction(action, locator, stepNumber);
  }

  return Number.isFinite(stepNumber) && stepNumber > 0 ? `Step ${stepNumber}` : "Recorded step";
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

function normalizeStepAction(kind) {
  const normalized = firstText(kind).toLowerCase();
  if (!normalized) return "step";
  if (normalized === "nav") return "navigate";
  return normalized;
}

function inferActionKindFromText(...values) {
  const text = values.map((value) => firstText(value)).filter(Boolean).join(" ").toLowerCase();
  if (!text) return "step";

  if (/(^|\b)(click|tap|press|select|choose|open)\b/.test(text)) return "click";
  if (/(^|\b)(fill|type|enter|input|paste|set)\b/.test(text)) return "fill";
  if (/(^|\b)(assert|verify|check|expect|confirm|validate)\b/.test(text)) return "assert";
  if (/(^|\b)(navigate|goto|go to|go back|back|forward|reload|refresh)\b/.test(text)) return "navigate";
  if (/(^|\b)(hover)\b/.test(text)) return "hover";
  return "step";
}

function PendingChipRow({ elementInfo, intent }) {
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

  if (!elementInfo) {
    return <span style={{ color: "#8f8a82" }}>{intent.trim() ? "No element attached." : "Draft step."}</span>;
  }

  return (
    <>
      <span style={chipStyle}>{elementInfo.tag}</span>
      {elementInfo.text && <span style={chipStyle}>&quot;{shortenText(elementInfo.text)}&quot;</span>}
      {elementInfo.id && <span style={chipStyle}>#{elementInfo.id}</span>}
      {elementInfo.className && <span style={chipStyle}>.{elementInfo.className.split(/\s+/).filter(Boolean).join(".")}</span>}
    </>
  );
}

function IDERecordedStepCard({
  step,
  index = 0,
  compact = false,
  showGeneratedLine = true,
  onReplay,
  onCopy,
}) {
  const [showDetails, setShowDetails] = React.useState(false);
  const action = normalizeStepAction(step.action || step.action_label || step.kind || step.type);
  const stepNumberValue = Number.isFinite(Number(step.step_number)) && Number(step.step_number) > 0 ? Number(step.step_number) : index + 1;
  const displayTitle = resolveRecordedStepTitle(step, action, stepNumberValue);
  const target = pickRecordedText(step.target_label, step.element_name, step.target, step.label);
  const locator = firstText(step.locator);
  const status = firstText(step.status, "recorded").toLowerCase();
  const statusKind = status === "passed" ? "passed" : status === "failed" ? "failed" : "recorded";
  const codeLine = firstText(step.generated_line);

  return (
    <div className={`ide-recorded-step${compact ? " is-compact" : ""}`}>
      <div className="ide-recorded-step-main">
        <div className="ide-recorded-step-head">
          <code className="ide-step-num">{String(stepNumberValue).padStart(2, "0")}</code>
          <div className="ide-recorded-step-headcopy">
            <div className="ide-recorded-step-title">{displayTitle}</div>
            <div className="ide-recorded-step-badges">
              <IDEPlanTag kind={action} />
              <IDEBadge kind={statusKind}>{statusKind}</IDEBadge>
            </div>
          </div>
        </div>
        {target && <div className="ide-recorded-step-target">{target}</div>}
        {locator && <code className="ide-recorded-step-locator">{locator}</code>}
        {showGeneratedLine && codeLine && <pre className="ide-recorded-step-code">{codeLine}</pre>}
        {!showGeneratedLine && showDetails && codeLine && <pre className="ide-recorded-step-code ide-recorded-step-code-collapsed">{codeLine}</pre>}
        {showDetails && showGeneratedLine && <div className="ide-recorded-step-note">Technical details are in the Debug tab.</div>}
        <div className="ide-recorded-step-actions">
          <button className="ide-btn sm" type="button" onClick={() => onReplay?.(step)}>
            Replay
          </button>
          <button className="ide-btn sm" type="button" onClick={() => onCopy?.(step)}>
            Copy
          </button>
          <button className="ide-btn sm" type="button" onClick={() => setShowDetails((value) => !value)}>
            More
          </button>
        </div>
      </div>
    </div>
  );
}

function IDERecordedStepsSection({ recordedSteps = [], onReplayRecordedStep, onCopyRecordedStep }) {
  const steps = Array.isArray(recordedSteps) ? recordedSteps : [];

  return (
    <IDECard color={steps.length ? "green" : null} title="// recorded steps">
      <div className="ide-scrollbox ide-scrollbox-recorded" style={{ maxHeight: 300 }}>
        {steps.length > 0 ? (
          <div className="ide-step-list">
            {steps.map((step, i) => (
              <IDERecordedStepCard
                key={step.id || `${step.step_number || i}`}
                step={step}
                index={i}
                compact={false}
                showGeneratedLine
                onReplay={onReplayRecordedStep}
                onCopy={onCopyRecordedStep}
              />
            ))}
          </div>
        ) : (
          <div className="ide-empty-state">No recorded steps yet.</div>
        )}
      </div>
    </IDECard>
  );
}

function IDERecordedOutput({ recordedSteps = [], onReplayRecordedStep, onCopyRecordedStep }) {
  const [activeTab, setActiveTab] = React.useState("steps");
  const steps = Array.isArray(recordedSteps) ? recordedSteps : [];
  const visibleSteps = activeTab === "steps" ? steps.slice(-3).reverse() : [];
  const codeLines = steps.map((step) => firstText(step.generated_line)).filter(Boolean);
  const codeText = codeLines.join("\n");
  const recordedCount = steps.length;
  const lineCount = codeLines.length;

  return (
    <IDECard color={recordedCount > 0 ? "green" : null} title="// recorded output">
      <div className="ide-stats">
        <div className="ide-stat">
          <div className={`ide-stat-num${recordedCount > 0 ? " s-green" : ""}`}>{recordedCount}</div>
          <div className="ide-stat-lbl">Recorded steps</div>
        </div>
        <div className="ide-stat">
          <div className="ide-stat-num">{lineCount > 0 ? lineCount : "—"}</div>
          <div className="ide-stat-lbl">Code lines</div>
        </div>
      </div>
      <div className="ide-mini-tabs">
        <button
          className={`ide-mini-tab${activeTab === "steps" ? " active" : ""}`}
          type="button"
          onClick={() => setActiveTab("steps")}
        >
          Steps
        </button>
        <button
          className={`ide-mini-tab${activeTab === "code" ? " active" : ""}`}
          type="button"
          onClick={() => setActiveTab("code")}
        >
          Code
        </button>
      </div>
      {activeTab === "steps" ? (
        <div className="ide-scrollbox ide-scrollbox-recorded" style={{ maxHeight: 216 }}>
          {visibleSteps.length > 0 ? (
            <div className="ide-step-list">
              {visibleSteps.map((step, i) => (
                <IDERecordedStepCard
                  key={step.id || `${step.step_number || i}`}
                  step={step}
                  index={i}
                  compact
                  showGeneratedLine={false}
                  onReplay={onReplayRecordedStep}
                  onCopy={onCopyRecordedStep}
                />
              ))}
            </div>
          ) : (
            <div className="ide-empty-state">No recorded steps yet.</div>
          )}
          {steps.length > visibleSteps.length && (
            <div className="ide-more-note">+ {steps.length - visibleSteps.length} more in the full Steps tab.</div>
          )}
        </div>
      ) : codeText ? (
        <pre className="ide-code ide-recorded-code" style={{ marginTop: 2, whiteSpace: "pre-wrap" }}>
          {codeText}
        </pre>
      ) : (
        <div className="ide-empty-state">No recorded steps yet.</div>
      )}
    </IDECard>
  );
}

function IDEPendingStepCard({
  step,
  index = 0,
  compact = false,
  activePickerStepId = "",
  onChangeIntent,
  onAttachElement,
  onDeleteStep,
}) {
  const inputRef = React.useRef(null);
  const intent = firstRawText(step.intent, step.text, step.label);
  const trimmedIntent = intent.trim();
  const elementInfo = normalizeElementInfoForDisplay(step.element_info ?? step.elementInfo ?? null);
  const isPicking = activePickerStepId === step.id;
  const actionGuess = inferActionKindFromText(intent, elementInfo?.text, elementInfo?.tag, elementInfo?.id);
  const explicitStatus = firstText(step.status, step.state).toLowerCase();
  const statusLabel = isPicking ? "picking…" : explicitStatus === "ready" || trimmedIntent ? "ready" : "draft";
  const statusKind = isPicking ? "await" : explicitStatus === "ready" || trimmedIntent ? "ready" : "await";
  const stepNumber = String(index + 1).padStart(2, "0");

  const elementSummary = elementInfo ? (
    <PendingChipRow elementInfo={elementInfo} intent={intent} />
  ) : (
    <span style={{ color: "#8f8a82" }}>{trimmedIntent ? "No element attached." : "Draft step."}</span>
  );

  return (
    <div className={`ide-step-card${compact ? " is-compact" : ""}${isPicking ? " is-active" : ""}`}>
      <div className="ide-step-numcol">
        <code className="ide-step-num">{stepNumber}</code>
      </div>
      <div className="ide-step-card-main">
        {!compact ? (
          <div className="ide-step-topline">
            <input
              ref={inputRef}
              className="ide-input ide-step-input"
              value={intent}
              onChange={(event) => onChangeIntent?.(step.id, event.target.value)}
              placeholder="click Get started"
            />
            <IDEBadge kind={statusKind}>{statusLabel}</IDEBadge>
          </div>
        ) : (
          <div className="ide-step-summary-title">{trimmedIntent || "Draft step"}</div>
        )}
        <div className="ide-step-meta">
          <IDEPlanTag kind={actionGuess} />
          {compact ? <IDEBadge kind={statusKind}>{statusLabel}</IDEBadge> : null}
        </div>
        <div className="ide-step-elements">{elementSummary}</div>
        {!compact && (
          <div className="ide-step-actions">
            <button className="ide-btn sm" type="button" onClick={() => onAttachElement?.(step.id)}>
              {isPicking ? "Click page element…" : "Attach Element"}
            </button>
            <button
              className="ide-btn sm"
              type="button"
              onClick={() => {
                const node = inputRef.current;
                if (!node) return;
                node.focus();
                if (typeof node.select === "function") {
                  node.select();
                }
              }}
            >
              Edit
            </button>
            <button className="ide-btn sm danger" type="button" onClick={() => onDeleteStep?.(step.id)}>
              Delete
            </button>
          </div>
        )}
      </div>
    </div>
  );
}

function IDEPendingSteps({
  state = "idle",
  steps = [],
  live = false,
  compact = false,
  activePickerStepId = "",
  onChangeIntent,
  onAddStep,
  onAttachElement,
  onDeleteStep,
}) {
  const hasRuntimeSteps = live && Array.isArray(steps) && steps.length > 0;
  const fallback = ["01 · Assert hero text", "02 · Click Get started"];
  const rows = live ? (hasRuntimeSteps ? steps : []) : fallback;
  const visibleRows = compact && rows.length > 3 ? rows.slice(Math.max(0, rows.length - 3)) : rows;
  const hasMore = compact && rows.length > visibleRows.length;
  const emptyLabel =
    state === "clarification"
      ? "Waiting for clarification answer…"
      : state === "recovery"
        ? "Waiting for recovery instruction…"
        : state === "executing"
          ? "Executing…"
          : "Awaiting plan_ready…";

  return (
    <IDECard
      color="amber"
      title="// pending steps"
      footer={
        !compact && onAddStep
          ? [
              <button key="add" className="ide-btn primary" type="button" style={{ flex: 1, justifyContent: "center" }} onClick={() => onAddStep?.()}>
                + Step
              </button>,
            ]
          : null
      }
    >
      <div className={`ide-scrollbox ide-scrollbox-pending${compact ? " is-compact" : ""}`} style={{ maxHeight: compact ? 206 : 312 }}>
        {visibleRows.length > 0 ? (
          <div className="ide-step-list">
            {visibleRows.map((step, i) => {
              if (typeof step === "string") {
                return (
                  <div key={i} className="ide-step-card is-summary">
                    <div className="ide-step-numcol">
                      <code className="ide-step-num">{String(i + 1).padStart(2, "0")}</code>
                    </div>
                    <div className="ide-step-card-main">
                      <div className="ide-step-summary-title">{step}</div>
                      <div className="ide-step-meta">
                        <IDEBadge kind="ready">ready</IDEBadge>
                      </div>
                    </div>
                  </div>
                );
              }

              return (
                <IDEPendingStepCard
                  key={step.id || `${i}`}
                  step={step}
                  index={i}
                  compact={compact}
                  activePickerStepId={activePickerStepId}
                  onChangeIntent={onChangeIntent}
                  onAttachElement={onAttachElement}
                  onDeleteStep={onDeleteStep}
                />
              );
            })}
          </div>
        ) : (
          <div className="ide-empty-state">{emptyLabel}</div>
        )}
        {hasMore && <div className="ide-more-note">+ {rows.length - visibleRows.length} more in the Steps tab.</div>}
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

function IDEHeader({ state, interactionMode, connectionStatus = "disconnected" }) {
  const labels = {
    idle: "idle",
    planning: "planning…",
    plan_review: "plan review",
    clarification: "clarification needed",
    await: "awaiting confirmation",
    exec: "executing",
    executing: "executing",
    recovery: "recovery needed",
    recover: "recovery needed",
    done: "completed",
    completed: "completed",
  };

  const statusStyle = connectionStyle(connectionStatus);
  const label = labels[interactionMode] || labels[state] || state;

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
        <div className={`ide-hd-state s-${state}`}>{label}</div>
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
  const interactionMode = typeof runtime.interactionMode === "string" && runtime.interactionMode ? runtime.interactionMode : panelState;
  const connectionStatus = runtime.connectionStatus || "disconnected";
  const conversation = Array.isArray(runtime.conversation) ? runtime.conversation : [];
  const timeline = Array.isArray(runtime.timeline) ? runtime.timeline : [];
  const plan = runtime.plan || null;
  const pendingSteps = Array.isArray(runtime.pendingSteps) ? runtime.pendingSteps : [];
  const recordedSteps = Array.isArray(runtime.recordedSteps) ? runtime.recordedSteps : [];
  const planCorrectionText = typeof runtime.planCorrectionText === "string" ? runtime.planCorrectionText : "";
  const clarificationQuestion = typeof runtime.clarificationQuestion === "string" ? runtime.clarificationQuestion : "";
  const clarificationOptions = Array.isArray(runtime.clarificationOptions) ? runtime.clarificationOptions : [];
  const clarificationAnswerText = typeof runtime.clarificationAnswerText === "string" ? runtime.clarificationAnswerText : "";
  const recoveryText = typeof runtime.recoveryText === "string" ? runtime.recoveryText : "";
  const currentUrl = typeof runtime.currentUrl === "string" ? runtime.currentUrl : "";
  const codePreview = typeof runtime.codePreview === "string" ? runtime.codePreview : "";
  const lastError = typeof runtime.lastError === "string" ? runtime.lastError : "";
  const lastEvent = runtime.lastEvent || null;
  const activePickerStepId = typeof runtime.activePickerStepId === "string" ? runtime.activePickerStepId : "";
  const stepCount = pendingSteps.length + recordedSteps.length;
  const showPlanReview = interactionMode === "plan_review";
  const showClarification = interactionMode === "clarification";
  const showRecovery = interactionMode === "recovery";

  return (
    <div className="ide-panel">
      <IDEHeader state={panelState} interactionMode={interactionMode} connectionStatus={connectionStatus} />
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
            <IDEConversation state={interactionMode} messages={conversation} live={live} />
            <IDETimeline state={interactionMode} events={timeline} live={live} />
            {showPlanReview && (
              <IDEPlanReview
                plan={plan}
                live={live}
                correctionText={planCorrectionText}
                onCorrectionTextChange={runtime.onPlanCorrectionTextChange || runtime.onCorrectionTextChange}
                onConfirmPlan={runtime.onConfirmPlan}
                onSendCorrection={runtime.onSendPlanCorrection || runtime.onSendCorrection}
              />
            )}
            {showClarification && (
              <IDEClarificationCard
                question={clarificationQuestion}
                options={clarificationOptions}
                answerText={clarificationAnswerText}
                onAnswerTextChange={runtime.onClarificationAnswerTextChange}
                onSendAnswer={runtime.onSendClarificationAnswer || runtime.onSendOptionSelected}
              />
            )}
            {showRecovery && (
              <IDERecovery
                message={lastError}
                currentUrl={currentUrl}
                recoveryText={recoveryText}
                onRecoveryTextChange={runtime.onRecoveryTextChange}
                onSendRecoveryInstruction={runtime.onSendRecoveryInstruction}
              />
            )}
            <IDEPendingSteps
              state={interactionMode}
              steps={pendingSteps}
              live={live}
              compact
              activePickerStepId={activePickerStepId}
              onChangeIntent={runtime.onPendingStepIntentChange}
              onAttachElement={runtime.onAttachElement}
              onDeleteStep={runtime.onDeletePendingStep}
            />
            <IDERecordedOutput
              recordedSteps={recordedSteps}
              onReplayRecordedStep={runtime.onReplayRecordedStep}
              onCopyRecordedStep={runtime.onCopyRecordedStep}
            />
          </>
        )}
        {tab === "steps" && (
          <>
            <IDEPendingSteps
              state={interactionMode}
              steps={pendingSteps}
              live={live}
              compact={false}
              activePickerStepId={activePickerStepId}
              onChangeIntent={runtime.onPendingStepIntentChange}
              onAddStep={runtime.onAddPendingStep}
              onAttachElement={runtime.onAttachElement}
              onDeleteStep={runtime.onDeletePendingStep}
            />
            <IDERecordedStepsSection
              recordedSteps={recordedSteps}
              onReplayRecordedStep={runtime.onReplayRecordedStep}
              onCopyRecordedStep={runtime.onCopyRecordedStep}
            />
          </>
        )}
        {tab === "code" && (
          <>
            <IDECodePreview codePreview={codePreview} live={live} />
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
