// frontend/src/v4/llm-cards.jsx — Live LLM tab cards (v4 visual; backend-driven props)
// Each card returns null when its driving payload is missing. Every button
// dispatches a typed callback supplied by the parent — never mutates plan,
// recording, code, or completion state locally.
import React, { useState } from "react";
import { I } from "./icons.jsx";

function fmtTime(ts) {
  if (!ts) return "";
  if (typeof ts === "string" && ts.length <= 8) return ts;
  try {
    const d = new Date(ts);
    return d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
  } catch {
    return String(ts);
  }
}

function pickFirst(...vals) {
  for (const v of vals) {
    if (v != null && v !== "") return v;
  }
  return null;
}

function asArray(v) {
  return Array.isArray(v) ? v : [];
}

// — Conf indicator —————————————————————————————————————

export function Conf({ level }) {
  const cls = level >= 0.8 ? "high" : level >= 0.5 ? "med" : "low";
  const txt = level >= 0.8 ? "High" : level >= 0.5 ? "Medium" : "Low";
  return (
    <span style={{ display: "inline-flex", alignItems: "center", gap: 4 }}>
      <span className={"aw-conf " + cls}><i/><i/><i/></span>
      <span style={{ fontSize: 11, color: "var(--tx-3)" }}>
        {txt} · {Math.round((level ?? 0) * 100)}%
      </span>
    </span>
  );
}

// — Chat bubble / system message ————————————————————————

export function Bubble({ children, time }) {
  return (
    <div className="aw-msg-user" data-testid="aw-msg-user">
      {children}
      <div style={{ fontSize: 10.5, color: "#9A6E4A", marginTop: 4, opacity: 0.65 }}>
        {fmtTime(time)}
      </div>
    </div>
  );
}

export function Sys({ from = "AutoWorkbench", time, initials = "AW", children }) {
  return (
    <div className="aw-msg-system" data-testid="aw-msg-system">
      <div className="aw-avatar">{initials}</div>
      <div className="aw-msg-content">
        <div className="aw-msg-from">
          <b>{from}</b>
          {time ? <span className="aw-tstamp"> · {fmtTime(time)}</span> : null}
        </div>
        <div className="aw-msg-body">{children}</div>
      </div>
    </div>
  );
}

// — Clarification ———————————————————————————————————————

export function CardClarification({ clarification, onAnswer, onLetLLMDecide }) {
  const [pick, setPick] = useState(null);
  const [free, setFree] = useState("");
  if (!clarification) return null;
  const question = clarification.question ?? "";
  const options = asArray(clarification.options);
  const question_id = pickFirst(clarification.question_id, clarification.id);
  const target_step = clarification.target_step ?? null;

  const submit = (value) => {
    if (typeof onAnswer === "function") {
      onAnswer({
        type: "option_selected",
        question_id,
        target_step,
        answer: value,
      });
    }
  };

  return (
    <div className="aw-card clarify needs-input" data-testid="card-clarification">
      <div className="aw-card-head">
        <span className="aw-card-icon"><I.Info/></span>
        <span className="aw-card-title">Clarification needed</span>
        <span className="aw-card-state">Decision required</span>
        <span className="aw-card-source llm"><span className="src-dot"/>LLM proposal</span>
      </div>
      <div className="aw-card-body">
        <p>{question || "I need a bit more detail to draft this plan."}</p>
        {options.length > 0 ? (
          <div style={{ display: "flex", flexDirection: "column", gap: 6, marginTop: 8 }}
               data-testid="clarification-options">
            {options.map((o, idx) => {
              const id = pickFirst(o.id, o.value, String(o.label ?? idx));
              const label = o.label ?? o.value ?? String(o);
              const desc = o.description ?? o.detail ?? "";
              const selected = pick === id;
              return (
                <label key={id} onClick={() => setPick(id)}
                       data-testid={`clarification-option-${id}`}
                       style={{
                         display: "flex", gap: 9, padding: "9px 11px",
                         border: "1px solid " + (selected ? "var(--acc)" : "var(--br)"),
                         background: selected ? "#FFF8EE" : "var(--bg-card)",
                         borderRadius: 9, cursor: "pointer", alignItems: "flex-start",
                       }}>
                  <span style={{
                    width: 14, height: 14, borderRadius: "50%",
                    border: "1.5px solid " + (selected ? "var(--acc)" : "var(--br-strong)"),
                    background: selected ? "radial-gradient(circle, var(--acc) 40%, white 45%)" : "white",
                    flex: "0 0 14px", marginTop: 2,
                  }}/>
                  <span>
                    <span style={{ fontSize: 12.5, fontWeight: 500 }}>{label}</span>
                    {desc ? (
                      <span style={{ display: "block", fontSize: 11.5, color: "var(--tx-3)", marginTop: 1 }}>{desc}</span>
                    ) : null}
                  </span>
                </label>
              );
            })}
          </div>
        ) : (
          <div style={{ marginTop: 8 }}>
            <textarea data-testid="clarification-free-input"
                      value={free}
                      onChange={(e) => setFree(e.target.value)}
                      rows={2}
                      style={{ width: "100%", padding: 8, border: "1px solid var(--br)", borderRadius: 8 }}/>
          </div>
        )}
      </div>
      <div className="aw-card-foot">
        <button type="button" className="aw-btn primary"
                data-testid="clarification-submit"
                disabled={options.length > 0 ? !pick : !free.trim()}
                onClick={() => submit(options.length > 0 ? pick : free.trim())}>
          <I.Send/>Submit answer
        </button>
        {typeof onLetLLMDecide === "function" ? (
          <button type="button" className="aw-btn subtle"
                  data-testid="clarification-let-llm"
                  onClick={() => onLetLLMDecide({ type: "option_selected", question_id, answer: "__llm_decide__" })}>
            Let LLM decide
          </button>
        ) : null}
        <span style={{ flex: 1 }}/>
        <span style={{ fontSize: 11, color: "var(--tx-4)" }}>Pauses execution until answered</span>
      </div>
    </div>
  );
}

// — Recommendation ——————————————————————————————————————

export function CardRecommendation({ recommendations = [], onAccept, onAddOwn }) {
  const list = asArray(recommendations);
  const [picked, setPicked] = useState(() => list.filter((r) => r.checked !== false).map((r) => r.id ?? r.label));
  if (list.length === 0) return null;
  const toggle = (id) =>
    setPicked((cur) => (cur.includes(id) ? cur.filter((x) => x !== id) : [...cur, id]));

  return (
    <div className="aw-card plan needs-input" data-testid="card-recommendation">
      <div className="aw-card-head">
        <span className="aw-card-icon"><I.Layers/></span>
        <span className="aw-card-title">Recommended assertions</span>
        <span className="aw-card-state">Review</span>
        <span className="aw-card-source llm"><span className="src-dot"/>LLM proposal · not executable</span>
      </div>
      <div className="aw-card-body">
        <p style={{ color: "var(--tx-2)", fontSize: 12 }}>
          Pick the assertions to include before I draft a plan.
        </p>
        <div style={{ display: "flex", flexDirection: "column", gap: 2, marginTop: 8 }}
             data-testid="recommendation-list">
          {list.map((r, idx) => {
            const id = r.id ?? r.label ?? `rec-${idx}`;
            const text = r.label ?? r.text ?? r.summary ?? id;
            const scope = r.scope ?? r.locator ?? "";
            const checked = picked.includes(id);
            return (
              <label key={id} data-testid={`recommendation-item-${id}`}
                     style={{
                       display: "flex", gap: 9, padding: "7px 8px", borderRadius: 6,
                       background: idx % 2 ? "var(--bg-soft)" : "transparent",
                       cursor: "pointer", alignItems: "flex-start",
                     }}>
                <input type="checkbox" checked={checked} onChange={() => toggle(id)}
                       style={{ marginTop: 3, accentColor: "var(--acc)" }}/>
                <span style={{ flex: 1, minWidth: 0 }}>
                  <span style={{
                    fontSize: 12.5, color: checked ? "var(--tx)" : "var(--tx-3)",
                    textDecoration: checked ? "none" : "line-through",
                  }}>{text}</span>
                  {scope ? (
                    <span style={{ display: "block", fontSize: 10.5, color: "var(--tx-4)", fontFamily: "var(--ff-mono)", marginTop: 2 }}>{scope}</span>
                  ) : null}
                </span>
              </label>
            );
          })}
        </div>
      </div>
      <div className="aw-card-foot">
        <button type="button" className="aw-btn primary"
                data-testid="recommendation-accept"
                disabled={picked.length === 0}
                onClick={() => typeof onAccept === "function" && onAccept({
                  type: "accept_recommendations",
                  selected_recs: picked,
                })}>
          <I.Check/>Use selected ({picked.length})
        </button>
        {typeof onAddOwn === "function" ? (
          <button type="button" className="aw-btn" data-testid="recommendation-add-own"
                  onClick={() => onAddOwn({ type: "add_recommendation_request" })}>
            <I.Plus/>Add my own assertion
          </button>
        ) : null}
      </div>
    </div>
  );
}

// — Plan diff ———————————————————————————————————————————

export function CardPlanDiff({ diff, onApply, onReject, onRevert }) {
  if (!diff) return null;
  const diff_id = pickFirst(diff.diff_id, diff.id);
  const plan_id = diff.plan_id ?? null;
  const ops = asArray(diff.operations ?? diff.ops);
  const impacts = asArray(diff.impact ?? diff.impacts);

  return (
    <div className="aw-card diff needs-input" data-testid="card-plan-diff">
      <div className="aw-card-head">
        <span className="aw-card-icon"><I.Diff/></span>
        <span className="aw-card-title">Plan revision proposed</span>
        <span className="aw-card-state">Review</span>
        <span className="aw-card-source llm">
          <span className="src-dot"/>LLM proposal · {diff.version ? `v${diff.version} · ` : ""}{ops.length} changes
        </span>
      </div>
      <div className="aw-card-body">
        <div className="aw-diff" style={{ marginTop: 6, display: "flex", flexDirection: "column", gap: 1 }}
             data-testid="plan-diff-ops">
          {ops.map((op, i) => {
            const sign = op.kind === "add" ? "+" : op.kind === "remove" ? "-" : " ";
            const cls = op.kind === "add" ? "add" : op.kind === "remove" ? "rem" : "ctx";
            return (
              <div key={i} className={`aw-diff-row ${cls}`} data-testid={`plan-diff-op-${i}`}>
                <span className="aw-diff-sign">{sign}</span>
                {op.path ? <span style={{ marginRight: 8 }}>{op.path}</span> : null}
                {op.description ?? op.text ?? ""}
              </div>
            );
          })}
        </div>
        {impacts.length > 0 ? (
          <>
            <div className="aw-card-section-title">Impact</div>
            <ul className="aw-dotlist">
              {impacts.map((it, i) => (
                <li key={i} className={it.level === "ok" ? "ok" : ""}>{it.text ?? String(it)}</li>
              ))}
            </ul>
          </>
        ) : null}
      </div>
      <div className="aw-card-foot">
        <button type="button" className="aw-btn primary"
                data-testid="plan-diff-apply"
                disabled={!diff_id}
                onClick={() => typeof onApply === "function" && onApply({
                  type: "apply_plan_diff",
                  plan_id,
                  diff_id,
                  operations: ops,
                })}>
          <I.Check/>Apply changes
        </button>
        {typeof onReject === "function" ? (
          <button type="button" className="aw-btn" data-testid="plan-diff-reject"
                  disabled={!diff_id}
                  onClick={() => onReject({ type: "reject_plan_diff", plan_id, diff_id })}>
            Reject
          </button>
        ) : null}
        {typeof onRevert === "function" ? (
          <button type="button" className="aw-btn subtle" data-testid="plan-diff-revert"
                  onClick={() => onRevert({ type: "plan_revert" })}>
            <I.Retry style={{ width: 12, height: 12 }}/>Revert
          </button>
        ) : null}
      </div>
    </div>
  );
}

// — Plan ready ———————————————————————————————————————————

export function CardPlanReady({ plan, onConfirm, onEdit, onPartialRun }) {
  if (!plan) return null;
  const plan_id = pickFirst(plan.plan_id, plan.id);
  const plan_version = pickFirst(plan.version, plan.plan_version);
  const steps = asArray(plan.steps);
  const totalOps = steps.reduce((acc, s) => acc + (asArray(s.operations).length || 1), 0);

  return (
    <div className="aw-card plan needs-input" data-testid="card-plan-ready">
      <div className="aw-card-head">
        <span className="aw-card-icon"><I.Layers/></span>
        <span className="aw-card-title">{plan.title ? `Plan ready · ${plan.title}` : "Plan ready"}</span>
        <span className="aw-card-state">Confirm to run</span>
        <span className="aw-card-source backend">
          <span className="src-dot"/>Backend event · plan_ready
        </span>
      </div>
      <div className="aw-card-body" style={{ paddingBottom: 6 }}>
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 8, marginBottom: 8 }}>
          <div className="aw-status-pill" style={{ justifySelf: "start" }}>
            <span className="aw-dot" style={{ background: "var(--blu)" }}/>
            <span className="k">steps</span><span className="v" data-testid="plan-step-count">{steps.length}</span>
          </div>
          <div className="aw-status-pill" style={{ justifySelf: "start" }}>
            <span className="aw-dot" style={{ background: "var(--vio)" }}/>
            <span className="k">ops</span><span className="v">{totalOps}</span>
          </div>
          {plan.estimate ? (
            <div className="aw-status-pill" style={{ justifySelf: "start" }}>
              <span className="aw-dot" style={{ background: "var(--grn)" }}/>
              <span className="k">est</span><span className="v">{plan.estimate}</span>
            </div>
          ) : null}
        </div>
        <div data-testid="plan-steps">
          {steps.map((s, i) => {
            const stepId = pickFirst(s.step_id, s.id, `step-${i}`);
            const title = s.description ?? s.title ?? s.action ?? `Step ${i + 1}`;
            const ops = asArray(s.operations);
            const locatorKind = s.locator_kind ?? (s.weak_locator ? "warn" : "ok");
            return (
              <div key={stepId} className="aw-step pending" data-testid={`plan-step-${stepId}`}>
                <span className="aw-step-idx">{i + 1}</span>
                <div className="aw-step-main">
                  <div className="aw-step-title">
                    {title}
                    <span className="id">{stepId}</span>
                  </div>
                  <div className="aw-step-meta">
                    <span className={`aw-badge-i ${locatorKind === "warn" ? "warn" : "ok"}`}>
                      <span className="ldot"/>{locatorKind === "warn" ? "weak locator" : "strong locator"}
                    </span>
                    {s.scope ? (
                      <span>scope: <span className="mono">{s.scope}</span></span>
                    ) : null}
                  </div>
                  {ops.length > 0 ? (
                    <div className="aw-step-ops">
                      {ops.map((op, j) => (
                        <div key={j} className="aw-step-op">
                          <span className="op-tag">{op.kind ?? op.type ?? "op"}</span>
                          {op.description ?? op.text ?? ""}
                        </div>
                      ))}
                    </div>
                  ) : null}
                </div>
              </div>
            );
          })}
        </div>
      </div>
      <div className="aw-card-foot">
        <button type="button" className="aw-btn primary"
                data-testid="plan-confirm"
                aria-label="Confirm Plan"
                disabled={!plan_id}
                onClick={() => typeof onConfirm === "function" && onConfirm({
                  type: "confirm_plan",
                  plan_id,
                  plan_version,
                })}>
          <I.Play/>Confirm Plan<span className="aw-kbd">⌘↵</span>
        </button>
        {typeof onEdit === "function" ? (
          <button type="button" className="aw-btn" data-testid="plan-edit"
                  onClick={() => onEdit({ type: "correction", plan_id, plan_version })}>
            <I.Diff/>Edit plan
          </button>
        ) : null}
        {typeof onPartialRun === "function" && steps.length > 3 ? (
          <button type="button" className="aw-btn subtle" data-testid="plan-partial-run"
                  onClick={() => onPartialRun({
                    type: "run_steps",
                    step_ids: steps.slice(0, 3).map((s) => s.step_id ?? s.id),
                  })}>
            Run first 3 only
          </button>
        ) : null}
        <span style={{ flex: 1 }}/>
        <span style={{ fontSize: 11, color: "var(--tx-4)" }}>
          Backend will validate locators before execution
        </span>
      </div>
    </div>
  );
}

// — Permission ——————————————————————————————————————————

export function CardPermission({ permission, onDecision }) {
  if (!permission) return null;
  const operation = permission.operation ?? permission.action ?? "operation";
  const step_id = permission.step_id ?? null;
  const risk = permission.risk_level ?? permission.risk ?? "unknown";
  const reason = permission.reason ?? permission.message ?? "";

  const decide = (decision, scope = "once") => {
    if (typeof onDecision === "function") {
      onDecision({
        type: "permission_decision",
        operation,
        step_id,
        decision,
        scope,
      });
    }
  };

  return (
    <div className="aw-card perm needs-input" data-testid="card-permission">
      <div className="aw-card-head">
        <span className="aw-card-icon"><I.Shield/></span>
        <span className="aw-card-title">Permission required · {risk}-risk action</span>
        <span className="aw-card-state" style={{ background: "var(--ylw-soft)", color: "#7A5A0E", borderColor: "#ECD89A" }}>
          Decision required
        </span>
      </div>
      <div className="aw-card-body">
        <div className="aw-fail-grid">
          <div className="k">operation</div><div className="v mono">{operation}</div>
          {step_id ? (<><div className="k">on step</div><div className="v">{step_id}</div></>) : null}
          <div className="k">risk</div><div className="v">
            <span className="aw-badge-i warn"><span className="ldot"/>{risk}</span>
          </div>
          {reason ? (<><div className="k">why</div><div className="v">{reason}</div></>) : null}
        </div>
      </div>
      <div className="aw-card-foot" style={{ flexWrap: "wrap" }}>
        <button type="button" className="aw-btn primary" data-testid="permission-allow-once"
                onClick={() => decide("allow", "once")}>
          <I.Check/>Allow once
        </button>
        <button type="button" className="aw-btn" data-testid="permission-allow-plan"
                onClick={() => decide("allow", "plan")}>
          Allow for this plan
        </button>
        <span style={{ flex: 1 }}/>
        <button type="button" className="aw-btn danger" data-testid="permission-deny"
                onClick={() => decide("deny")}>
          <I.Stop style={{ width: 11, height: 11 }}/>Deny
        </button>
      </div>
    </div>
  );
}

// — Execution ———————————————————————————————————————————

export function CardExecution({ phase, currentStep, recordedSteps = [], pendingSteps = [], onPause, onStop }) {
  // Render only while the backend is actually executing. A pending step
  // alone (idle planning state) must NOT trigger the executing card.
  if (phase !== "executing") return null;
  const recorded = asArray(recordedSteps);
  const pending = asArray(pendingSteps);

  return (
    <div className="aw-card exec running" data-testid="card-execution">
      <div className="aw-card-head">
        <span className="aw-card-icon"><I.Play/></span>
        <span className="aw-card-title">Executing plan</span>
        {currentStep ? (
          <span className="aw-card-state" data-testid="exec-current-step">
            {currentStep.label ?? currentStep.step_id ?? ""}
          </span>
        ) : null}
        <span className="aw-card-source backend"><span className="src-dot"/>Step Runner · live</span>
      </div>
      <div className="aw-card-body">
        <div className="aw-prog" style={{ marginBottom: 10 }}/>
        {recorded.map((s, i) => {
          const id = pickFirst(s.step_id, s.id, `r-${i}`);
          const title = s.description ?? s.title ?? id;
          return (
            <div key={id} className="aw-step ok" data-testid={`exec-recorded-${id}`}>
              <span className="aw-step-idx"><I.Check style={{ width: 11, height: 11 }}/></span>
              <div className="aw-step-main">
                <div className="aw-step-title">{title}</div>
                <div className="aw-step-meta">
                  <span className="aw-badge-i ok"><span className="ldot"/>recorded</span>
                  {s.duration_ms ? <span>· {s.duration_ms}ms</span> : null}
                </div>
              </div>
            </div>
          );
        })}
        {currentStep ? (
          <div className="aw-step run" data-testid="exec-current">
            <span className="aw-step-idx">{recorded.length + 1}</span>
            <div className="aw-step-main">
              <div className="aw-step-title">
                {currentStep.description ?? currentStep.title ?? currentStep.step_id}
                {currentStep.step_id ? <span className="id">{currentStep.step_id}</span> : null}
              </div>
              <div className="aw-step-meta">
                <span className="aw-badge-i info"><span className="ldot"/>{currentStep.status ?? "running"}</span>
                {currentStep.scope ? <span>scope <span className="mono">{currentStep.scope}</span></span> : null}
              </div>
            </div>
          </div>
        ) : null}
        {pending.map((s, i) => {
          const id = pickFirst(s.step_id, s.id, `p-${i}`);
          const title = s.description ?? s.title ?? id;
          return (
            <div key={id} className="aw-step pending" data-testid={`exec-pending-${id}`}>
              <span className="aw-step-idx">{recorded.length + 1 + (currentStep ? 1 : 0) + i}</span>
              <div className="aw-step-main">
                <div className="aw-step-title">{title}</div>
                <div className="aw-step-meta">
                  <span className="aw-badge-i outline">queued</span>
                </div>
              </div>
            </div>
          );
        })}
      </div>
      <div className="aw-card-foot">
        {typeof onPause === "function" ? (
          <button type="button" className="aw-btn" data-testid="exec-pause"
                  onClick={() => onPause({ type: "pause_run" })}>
            <I.Pause style={{ width: 11, height: 11 }}/>Pause
          </button>
        ) : null}
        <button type="button" className="aw-btn danger" data-testid="exec-stop"
                onClick={() => typeof onStop === "function" && onStop({ type: "stop_run" })}>
          <I.Stop style={{ width: 11, height: 11 }}/>Stop run
        </button>
      </div>
    </div>
  );
}

// — Locator ambiguity ——————————————————————————————————

export function CardLocatorAmbiguity({ ambiguity, onChoose, onAskLLM, onChangeScope, onStop }) {
  const [pick, setPick] = useState(null);
  if (!ambiguity) return null;
  const candidates = asArray(ambiguity.candidates);
  const step_id = pickFirst(ambiguity.step_id, ambiguity.target_step);
  const pickedIdx = candidates.findIndex((c) => (c.id ?? c.candidate_id) === pick);
  const picked = pickedIdx >= 0 ? candidates[pickedIdx] : null;

  return (
    <div className="aw-card locator blocking" data-testid="card-locator-ambiguity">
      <div className="aw-card-head">
        <span className="aw-card-icon"><I.Target/></span>
        <span className="aw-card-title">Choose the correct candidate</span>
        <span className="aw-card-state">Execution paused</span>
        <span className="aw-card-source backend">
          <span className="src-dot"/>Step Runner · {candidates.length} matches
        </span>
      </div>
      <div className="aw-card-body" style={{ padding: "14px 14px 12px" }}>
        <p style={{ margin: "0 0 12px", fontSize: 12.5, color: "var(--tx-2)" }}>
          {step_id ? <>Multiple matches were found while resolving <span style={{ fontFamily: "var(--ff-mono)", color: "var(--tx)" }}>{step_id}</span>. </> : null}
          I won't pick on your behalf — choose one, ask me to refine the locator, or narrow the scope.
        </p>
        <div style={{ display: "flex", flexDirection: "column", gap: 8 }}
             data-testid="locator-candidates">
          {candidates.map((c, i) => {
            const id = pickFirst(c.id, c.candidate_id, `cand-${i}`);
            const selected = pick === id;
            return (
              <div key={id}
                   className={"aw-cand " + (selected ? "selected" : "")}
                   onClick={() => setPick(id)}
                   data-testid={`locator-candidate-${id}`}>
                <span className="aw-cand-num">{i + 1}</span>
                <div className="aw-cand-main">
                  <div style={{ display: "flex", alignItems: "center", gap: 8, justifyContent: "space-between" }}>
                    <span className="aw-cand-title">{c.title ?? c.description ?? id}</span>
                    {c.confidence != null ? <Conf level={c.confidence}/> : null}
                  </div>
                  <div className="aw-cand-meta">
                    {c.scope ? <span>scope: <span style={{ fontFamily: "var(--ff-mono)", color: "var(--tx-2)" }}>{c.scope}</span></span> : null}
                    {c.risk ? <><span>·</span><span>risk: <span className={"aw-badge-i " + (c.risk === "safe-read" ? "ok" : "warn")}><span className="ldot"/>{c.risk}</span></span></> : null}
                  </div>
                  {c.locator ? <div className="aw-cand-loc">{c.locator}</div> : null}
                  <div className="aw-cand-actions">
                    <button type="button" className="aw-btn" onClick={(e) => { e.stopPropagation(); setPick(id); }}
                            data-testid={`locator-select-${id}`}>
                      <I.Check/> {selected ? "Selected" : "Select"}
                    </button>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      </div>
      <div className="aw-card-foot" style={{ flexWrap: "wrap" }}>
        <span style={{ fontSize: 11.5, color: "var(--tx-3)" }}>
          {picked ? <>Selected: <b style={{ color: "var(--tx)" }}>candidate {pickedIdx + 1}</b></> : "No candidate selected"}
        </span>
        <span style={{ flex: 1 }}/>
        {typeof onAskLLM === "function" ? (
          <button type="button" className="aw-btn" data-testid="locator-ask-llm"
                  onClick={() => onAskLLM({ type: "improve_locator", step_id })}>
            <I.Spark/>Ask LLM for better locator
          </button>
        ) : null}
        {typeof onChangeScope === "function" ? (
          <button type="button" className="aw-btn" data-testid="locator-change-scope"
                  onClick={() => onChangeScope({ type: "change_locator_scope", step_id })}>
            Change scope
          </button>
        ) : null}
        <button type="button" className="aw-btn danger" data-testid="locator-stop"
                disabled={typeof onStop !== "function"}
                onClick={() => typeof onStop === "function" && onStop({ type: "stop_run" })}>
          <I.Stop style={{ width: 11, height: 11 }}/>Stop
        </button>
        <button type="button" className="aw-btn primary" data-testid="locator-confirm"
                disabled={!picked}
                onClick={() => typeof onChoose === "function" && onChoose({
                  type: "choose_locator_candidate",
                  step_id,
                  candidate_id: pick,
                })}>
          <I.Check/>Use candidate {picked ? pickedIdx + 1 : ""}
        </button>
      </div>
    </div>
  );
}

// — Recovery ———————————————————————————————————————————

export function CardRecovery({ recovery, onApplyRepair, onRetry, onChooseLocator, onStop }) {
  if (!recovery) return null;
  const step_id = recovery.step_id ?? null;
  const reason = recovery.failure_reason ?? recovery.reason ?? recovery.message ?? "";
  const expected = recovery.expected ?? null;
  const actual = recovery.actual ?? null;
  const evidence = asArray(recovery.evidence);
  const attempts = asArray(recovery.attempts);

  return (
    <div className="aw-card recover blocking" data-testid="card-recovery">
      <div className="aw-card-head">
        <span className="aw-card-icon"><I.Alert/></span>
        <span className="aw-card-title">
          Recovery needed{step_id ? ` · ${step_id}` : ""}
        </span>
        <span className="aw-card-state">Run blocked</span>
      </div>
      <div className="aw-card-body">
        <div className="aw-fail-grid">
          {reason ? (<><div className="k">reason</div><div className="v">{reason}</div></>) : null}
          {expected != null ? (<><div className="k">expected</div><div className="v mono">{String(expected)}</div></>) : null}
          {actual != null ? (<><div className="k">actual</div><div className="v mono">{String(actual)}</div></>) : null}
          {evidence.length > 0 ? (
            <>
              <div className="k">evidence</div>
              <div className="v" style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
                {evidence.map((e, i) => (
                  <span key={i} data-testid={`recovery-evidence-${i}`}>
                    {typeof e === "string" ? e : (e.label ?? e.url ?? e.kind ?? "evidence")}
                  </span>
                ))}
              </div>
            </>
          ) : null}
        </div>
        {attempts.length > 0 ? (
          <>
            <div className="aw-card-section-title">Recovery attempts</div>
            <ul className="aw-dotlist" data-testid="recovery-attempts">
              {attempts.map((a, i) => (
                <li key={i} className={a.outcome === "ok" ? "ok" : "no"}>{a.text ?? a.reason ?? String(a)}</li>
              ))}
            </ul>
          </>
        ) : null}
      </div>
      <div className="aw-card-foot" style={{ flexWrap: "wrap" }}>
        {typeof onApplyRepair === "function" ? (
          <button type="button" className="aw-btn primary" data-testid="recovery-apply-llm"
                  onClick={() => onApplyRepair({ type: "retry_recovery", step_id, recovery_action: "llm_repair" })}>
            <I.Spark/>Apply LLM repair
          </button>
        ) : null}
        <button type="button" className="aw-btn" data-testid="recovery-retry"
                onClick={() => typeof onRetry === "function" && onRetry({
                  type: "retry_recovery", step_id, recovery_action: "retry_as_is",
                })}>
          <I.Retry style={{ width: 12, height: 12 }}/>Retry as-is
        </button>
        {typeof onChooseLocator === "function" ? (
          <button type="button" className="aw-btn" data-testid="recovery-choose-locator"
                  onClick={() => onChooseLocator({ type: "choose_locator", step_id })}>
            Choose another locator
          </button>
        ) : null}
        <span style={{ flex: 1 }}/>
        <button type="button" className="aw-btn danger" data-testid="recovery-stop"
                onClick={() => typeof onStop === "function" && onStop({ type: "stop_run" })}>
          <I.Stop style={{ width: 11, height: 11 }}/>Stop run
        </button>
      </div>
    </div>
  );
}

// — Completed ———————————————————————————————————————————

export function CardCompleted({ completion, onReplayAll, onSaveSession, onOpenCode, onDownloadTrace }) {
  if (!completion) return null;
  const passed = completion.passed ?? completion.success_count ?? null;
  const repaired = completion.repaired ?? null;
  const failed = completion.failed ?? completion.failure_count ?? null;
  const elapsed = completion.elapsed ?? completion.duration ?? null;
  const summary = completion.summary ?? "";

  return (
    <div className="aw-card done" data-testid="card-completed">
      <div className="aw-card-head">
        <span className="aw-card-icon"><I.Check/></span>
        <span className="aw-card-title">Run completed</span>
        <span className="aw-card-state" data-testid="completed-state">
          {completion.outcome ?? "ok"}
        </span>
        <span className="aw-card-source backend">
          <span className="src-dot"/>Backend event · run_completed
        </span>
      </div>
      <div className="aw-card-body">
        <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 8, marginBottom: 10 }}
             data-testid="completed-summary-grid">
          {passed != null ? (
            <div className="aw-status-pill" style={{ justifySelf: "start" }}>
              <span className="aw-dot" style={{ background: "var(--grn)" }}/>
              <span className="k">passed</span><span className="v">{passed}</span>
            </div>
          ) : null}
          {repaired != null ? (
            <div className="aw-status-pill" style={{ justifySelf: "start" }}>
              <span className="aw-dot" style={{ background: "var(--ylw)" }}/>
              <span className="k">repaired</span><span className="v">{repaired}</span>
            </div>
          ) : null}
          {failed != null ? (
            <div className="aw-status-pill" style={{ justifySelf: "start" }}>
              <span className="aw-dot" style={{ background: "var(--red)" }}/>
              <span className="k">failed</span><span className="v">{failed}</span>
            </div>
          ) : null}
          {elapsed != null ? (
            <div className="aw-status-pill" style={{ justifySelf: "start" }}>
              <span className="aw-dot" style={{ background: "var(--blu)" }}/>
              <span className="k">elapsed</span><span className="v">{elapsed}</span>
            </div>
          ) : null}
        </div>
        {summary ? (
          <p style={{ margin: 0, fontSize: 12, color: "var(--tx-2)" }} data-testid="completed-summary-text">
            {summary}
          </p>
        ) : null}
      </div>
      <div className="aw-card-foot">
        {typeof onReplayAll === "function" ? (
          <button type="button" className="aw-btn primary" data-testid="completed-replay-all"
                  onClick={() => onReplayAll({ type: "replay_all" })}>
            <I.Repeat/>Replay all
          </button>
        ) : null}
        {typeof onSaveSession === "function" ? (
          <button type="button" className="aw-btn" data-testid="completed-save"
                  onClick={() => onSaveSession({ type: "save_session" })}>
            <I.Branch/>Save as suite
          </button>
        ) : null}
        {typeof onOpenCode === "function" ? (
          <button type="button" className="aw-btn" data-testid="completed-open-code"
                  onClick={() => onOpenCode({ type: "open_code" })}>
            <I.Code/>Open code
          </button>
        ) : null}
        {typeof onDownloadTrace === "function" ? (
          <button type="button" className="aw-btn subtle" data-testid="completed-download-trace"
                  onClick={() => onDownloadTrace({ type: "download_trace" })}>
            <I.Download/>Download trace
          </button>
        ) : null}
      </div>
    </div>
  );
}

// — Offline / connection lost —————————————————————————

export function CardOffline({ connection, onReconnect }) {
  if (!connection || connection.connected) return null;
  return (
    <div className="aw-card recover blocking" data-testid="card-offline">
      <div className="aw-card-head">
        <span className="aw-card-icon"><I.Plug/></span>
        <span className="aw-card-title">Backend unavailable</span>
        <span className="aw-card-state">Holding state</span>
      </div>
      <div className="aw-card-body">
        <p style={{ margin: "0 0 6px" }}>
          The frontend lost its websocket. <b>I will not infer success or failure of in-flight steps.</b>
        </p>
        {connection.last_event ? (
          <ul className="aw-dotlist">
            <li className="no">last event: <span style={{ fontFamily: "var(--ff-mono)" }}>{connection.last_event}</span></li>
          </ul>
        ) : null}
      </div>
      <div className="aw-card-foot">
        <button type="button" className="aw-btn primary" data-testid="offline-reconnect"
                onClick={() => typeof onReconnect === "function" && onReconnect({ type: "reconnect" })}>
          <I.Sync/>Reconnect now
        </button>
      </div>
    </div>
  );
}

// — E2 (B2) backend-driven state cards ——————————————————

// CardNoBrowser: renders only when reducer holds a no_browser payload.
// Sprint 7 does not collect a relaunch command yet (no safe WS seam
// exists); the action is disabled with a real reason instead of a
// fake button. Pass dispatchers.onRelaunchBrowser to enable wiring
// in a later batch.
export function CardNoBrowser({ state, onRelaunchBrowser }) {
  if (!state || !state.reason) return null;
  const canRelaunch = typeof onRelaunchBrowser === "function";
  return (
    <div className="aw-card warn blocking" data-testid="card-no-browser">
      <div className="aw-card-head">
        <span className="aw-card-icon"><I.Plug /></span>
        <span className="aw-card-title">No browser context</span>
        <span className="aw-card-state">{state.recoverable === false ? "Unrecoverable" : "Recoverable"}</span>
      </div>
      <div className="aw-card-body">
        <p style={{ margin: "0 0 6px" }} data-testid="no-browser-message">
          {state.message}
        </p>
        {state.current_url ? (
          <ul className="aw-dotlist">
            <li className="no" data-testid="no-browser-url">
              last url: <span style={{ fontFamily: "var(--ff-mono)" }}>{state.current_url}</span>
            </li>
          </ul>
        ) : null}
      </div>
      <div className="aw-card-foot">
        <button
          type="button"
          className="aw-btn primary"
          data-testid="no-browser-action"
          disabled={!canRelaunch || state.recoverable === false}
          title={
            canRelaunch
              ? "Request the backend to relaunch the browser"
              : "Relaunch command is not yet exposed; restart the backend service to recover"
          }
          onClick={() => canRelaunch && onRelaunchBrowser({ type: "relaunch_browser" })}
        >
          <I.Sync />Relaunch browser
        </button>
      </div>
    </div>
  );
}

// CardApiKey: renders only when api_key_required event is in store.
// Sprint 7 deliberately does NOT collect the key in the frontend — no
// secure storage policy exists. The card surfaces config metadata
// (provider, missing env var NAMES, setup hint URLs) and a disabled
// "Re-check config" action stub; an existing safe seam would replace
// the disabled state with a real dispatch.
export function CardApiKey({ state, onRecheckConfig }) {
  if (!state || !state.provider) return null;
  const canRecheck = typeof onRecheckConfig === "function";
  return (
    <div className="aw-card warn blocking" data-testid="card-api-key">
      <div className="aw-card-head">
        <span className="aw-card-icon"><I.Alert /></span>
        <span className="aw-card-title">Provider key required</span>
        <span className="aw-card-state">{state.reason}</span>
      </div>
      <div className="aw-card-body">
        <p style={{ margin: "0 0 6px" }} data-testid="api-key-message">
          {state.message}
        </p>
        <ul className="aw-dotlist">
          <li className="no">
            provider: <span style={{ fontFamily: "var(--ff-mono)" }} data-testid="api-key-provider">{state.provider}</span>
          </li>
          {Array.isArray(state.missing_config_keys) && state.missing_config_keys.length ? (
            <li className="no" data-testid="api-key-missing-keys">
              missing env: {state.missing_config_keys.join(", ")}
            </li>
          ) : null}
          {state.setup_hint && state.setup_hint.url ? (
            <li className="no" data-testid="api-key-setup-hint">
              setup: <a href={state.setup_hint.url} target="_blank" rel="noopener noreferrer">{state.setup_hint.url}</a>
            </li>
          ) : null}
        </ul>
      </div>
      <div className="aw-card-foot">
        <button
          type="button"
          className="aw-btn primary"
          data-testid="api-key-recheck"
          disabled={!canRecheck}
          title={
            canRecheck
              ? "Ask the backend to re-read its configured providers"
              : "Re-check command is not yet exposed; update the env and restart the backend"
          }
          onClick={() => canRecheck && onRecheckConfig({ type: "recheck_config" })}
        >
          <I.Sync />Re-check config
        </button>
      </div>
    </div>
  );
}

// CardOtp / CardHumanInput: covers otp / password / browser_prompt /
// file_picker. Sprint 7 does NOT collect the value in the frontend —
// no secure store exists. The card instructs the user to complete the
// step in the browser and a "Continue" button only dispatches when a
// safe seam is provided.
export function CardOtp({ state, onContinue }) {
  if (!state || !state.input_type || state.sensitive !== true) return null;
  const canContinue = typeof onContinue === "function";
  return (
    <div className="aw-card warn blocking" data-testid="card-otp">
      <div className="aw-card-head">
        <span className="aw-card-icon"><I.Key /></span>
        <span className="aw-card-title">
          {state.input_type === "otp" ? "One-time code required" : "Human input required"}
        </span>
        <span className="aw-card-state">{state.input_type}</span>
      </div>
      <div className="aw-card-body">
        <p style={{ margin: "0 0 6px" }} data-testid="otp-prompt">{state.prompt}</p>
        <ul className="aw-dotlist">
          {state.origin ? (
            <li className="no" data-testid="otp-origin">
              origin: <span style={{ fontFamily: "var(--ff-mono)" }}>{state.origin}</span>
            </li>
          ) : null}
          {state.expires_at ? (
            <li className="no" data-testid="otp-expires">expires: {state.expires_at}</li>
          ) : null}
          <li className="no" data-testid="otp-safety-note">
            Complete this step in the browser. <b>Do not paste the code here.</b>
          </li>
        </ul>
      </div>
      <div className="aw-card-foot">
        <button
          type="button"
          className="aw-btn primary"
          data-testid="otp-continue"
          disabled={!canContinue}
          title={
            canContinue
              ? "Notify the backend that the step was completed in the browser"
              : "Continue command is not yet exposed; resume execution from the panel"
          }
          onClick={() =>
            canContinue && onContinue({ type: "human_input_completed", correlation_id: state.correlation_id })
          }
        >
          <I.Check />I completed it in the browser
        </button>
      </div>
    </div>
  );
}

// CardE2EPending: pure advisory; no command path. Will not claim
// acceptance status that the backend has not produced.
export function CardE2EPending({ state }) {
  if (!state || !state.reason) return null;
  return (
    <div className="aw-card info" data-testid="card-e2e-pending">
      <div className="aw-card-head">
        <span className="aw-card-icon"><I.Info /></span>
        <span className="aw-card-title">Acceptance pending</span>
        <span className="aw-card-state">{state.reason}</span>
      </div>
      <div className="aw-card-body">
        {Array.isArray(state.pending_tests) && state.pending_tests.length ? (
          <ul className="aw-dotlist" data-testid="e2e-pending-list">
            {state.pending_tests.map((tid) => (
              <li key={tid} className="no">
                <span style={{ fontFamily: "var(--ff-mono)" }}>{tid}</span>
              </li>
            ))}
          </ul>
        ) : null}
        {state.last_result_summary ? (
          <p style={{ margin: "6px 0 0" }} data-testid="e2e-pending-status">
            last: {state.last_result_summary}
          </p>
        ) : null}
        {state.command_hint ? (
          <p style={{ margin: "4px 0 0" }} data-testid="e2e-pending-hint">
            <span style={{ fontFamily: "var(--ff-mono)" }}>{state.command_hint}</span>
          </p>
        ) : null}
      </div>
    </div>
  );
}

// — Schema / runtime rejected ——————————————————————————

export function CardSchemaError({ rejection, onAskRepair }) {
  if (!rejection) return null;
  return (
    <div className="aw-card warn blocking" data-testid="card-schema-error">
      <div className="aw-card-head">
        <span className="aw-card-icon"><I.Alert/></span>
        <span className="aw-card-title">Schema validation failed</span>
        <span className="aw-card-state">Nothing executed</span>
      </div>
      <div className="aw-card-body">
        <p style={{ margin: "0 0 6px", fontSize: 12.5 }}>
          {rejection.reason ?? rejection.message ?? "The LLM response did not validate."}
        </p>
        {rejection.detail ? (
          <div className="aw-fail-grid">
            {Object.entries(rejection.detail).map(([k, v]) => (
              <React.Fragment key={k}>
                <div className="k">{k}</div><div className="v mono">{String(v)}</div>
              </React.Fragment>
            ))}
          </div>
        ) : null}
      </div>
      <div className="aw-card-foot">
        {typeof onAskRepair === "function" ? (
          <button type="button" className="aw-btn primary" data-testid="schema-repair"
                  onClick={() => onAskRepair({ type: "repair_plan" })}>
            <I.Sync/>Ask LLM to repair plan
          </button>
        ) : null}
      </div>
    </div>
  );
}

// — LLM tab empty state ————————————————————————————————

export function LlmEmpty({ onSeed }) {
  return (
    <div className="aw-empty" data-testid="llm-empty">
      <div className="ic"><I.Spark/></div>
      <h3>Describe what you want to automate or validate.</h3>
      <p>
        Tell me about a page, attach a selection from the page, or paste a Playwright snippet.
        I'll plan a flow, ask before running, and record evidence on the way.
      </p>
      <div className="aw-suggestions">
        {["Validate this pricing page", "Smoke test the login flow", "Repair my flaky checkout spec", "Record an Add-to-cart journey"].map((c) => (
          <span key={c} className="aw-chip" data-testid={`llm-seed-${c.split(" ")[0].toLowerCase()}`}
                onClick={() => typeof onSeed === "function" && onSeed(c)}>
            {c}
          </span>
        ))}
      </div>
    </div>
  );
}

// — Composer ————————————————————————————————————————————

export function Composer({ onSend, onPickElement, disabled = false }) {
  const [text, setText] = useState("");
  const send = () => {
    if (!text.trim()) return;
    if (typeof onSend === "function") onSend({ type: "user_message", message_text: text.trim() });
    setText("");
  };
  return (
    <div className="aw-composer" data-testid="aw-composer">
      <div className="aw-composer-box">
        <textarea className="aw-composer-input" rows={1}
                  data-testid="aw-composer-input"
                  placeholder="Reply, refine the plan, or paste a step…"
                  value={text}
                  onChange={(e) => setText(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === "Enter" && !e.shiftKey) {
                      e.preventDefault();
                      send();
                    }
                  }}/>
        <div className="aw-composer-actions" style={{ justifyContent: "space-between" }}>
          <div style={{ display: "flex", gap: 2, alignItems: "center" }}>
            <button type="button" className="aw-icon-btn" title="Pick a page element to attach to your task"
                    data-testid="aw-composer-pick"
                    disabled={disabled}
                    onClick={() => typeof onPickElement === "function" && onPickElement({ type: "arm_picker" })}>
              <I.Mouse/>
            </button>
          </div>
          <button type="button" className="aw-btn primary"
                  style={{ padding: "5px 10px", fontSize: 11.5, height: 24 }}
                  data-testid="aw-composer-send"
                  disabled={disabled || !text.trim()}
                  onClick={send}>
            <I.Send/>Send<span className="aw-kbd">↵</span>
          </button>
        </div>
      </div>
    </div>
  );
}

// — LlmThread — assembles live conversation from store —————————————

export function LlmThread({
  conversation = [],
  plan,
  pendingClarification,
  pendingRecommendations = [],
  pendingPermission,
  pendingDiff,
  pendingRecovery,
  ambiguity,
  completion,
  rejection,
  connection,
  phase,
  currentStep,
  recordedSteps = [],
  pendingSteps = [],
  // E2 (B2) — backend-driven state cards. Each is null until the
  // matching event arrives; LlmThread renders the card only then.
  noBrowserState = null,
  apiKeyRequiredState = null,
  humanInputState = null,
  e2ePendingState = null,
  dispatchers = {},
  onSeed,
}) {
  const has = (v) => v != null && (Array.isArray(v) ? v.length > 0 : true);
  // currentStep deliberately NOT in the empty gate: a draft pending step on
  // the Steps tab must not suppress the LLM welcome card. currentStep is
  // still passed through to CardExecution which renders only when phase ===
  // "executing"; the executing phase short-circuits the empty gate below.
  const empty =
    phase !== "executing" &&
    !has(conversation) &&
    !has(plan) &&
    !has(pendingClarification) &&
    !has(pendingRecommendations) &&
    !has(pendingPermission) &&
    !has(pendingDiff) &&
    !has(pendingRecovery) &&
    !has(ambiguity) &&
    !has(completion) &&
    !has(rejection) &&
    // E2 (B2) — state cards keep the thread non-empty when active.
    !noBrowserState &&
    !apiKeyRequiredState &&
    !humanInputState &&
    !e2ePendingState;
  if (empty) return <LlmEmpty onSeed={onSeed}/>;

  return (
    <div className="aw-thread" data-testid="aw-thread">
      {asArray(conversation).map((m, i) => {
        const isUser = m.role === "user";
        if (isUser) {
          return <Bubble key={m.id ?? `m-${i}`} time={m.timestamp ?? m.time}>{m.text ?? ""}</Bubble>;
        }
        return (
          <Sys key={m.id ?? `s-${i}`} time={m.timestamp ?? m.time}>{m.text ?? ""}</Sys>
        );
      })}

      {connection && !connection.connected ? (
        <CardOffline connection={connection} onReconnect={dispatchers.onReconnect}/>
      ) : null}

      {/* E2 (B2) — state cards render only from real backend events. */}
      {noBrowserState ? (
        <CardNoBrowser state={noBrowserState} onRelaunchBrowser={dispatchers.onRelaunchBrowser} />
      ) : null}
      {apiKeyRequiredState ? (
        <CardApiKey state={apiKeyRequiredState} onRecheckConfig={dispatchers.onRecheckConfig} />
      ) : null}
      {humanInputState ? (
        <CardOtp state={humanInputState} onContinue={dispatchers.onHumanInputCompleted} />
      ) : null}
      {e2ePendingState ? (
        <CardE2EPending state={e2ePendingState} />
      ) : null}

      {pendingClarification ? (
        <CardClarification
          clarification={pendingClarification}
          onAnswer={dispatchers.onAnswerClarification}
          onLetLLMDecide={dispatchers.onAnswerClarification}
        />
      ) : null}

      {has(pendingRecommendations) ? (
        <CardRecommendation
          recommendations={pendingRecommendations}
          onAccept={dispatchers.onAcceptRecommendations}
          onAddOwn={dispatchers.onAddRecommendation}
        />
      ) : null}

      {pendingDiff ? (
        <CardPlanDiff
          diff={pendingDiff}
          onApply={dispatchers.onApplyPlanDiff}
          onReject={dispatchers.onRejectPlanDiff}
        />
      ) : null}

      {plan ? (
        <CardPlanReady
          plan={plan}
          onConfirm={dispatchers.onConfirmPlan}
          onEdit={dispatchers.onSendCorrection}
          onPartialRun={dispatchers.onRunSelected}
        />
      ) : null}

      {pendingPermission ? (
        <CardPermission
          permission={pendingPermission}
          onDecision={dispatchers.onPermissionDecision}
        />
      ) : null}

      {phase === "executing" ? (
        <CardExecution
          phase={phase}
          currentStep={currentStep}
          recordedSteps={recordedSteps}
          pendingSteps={pendingSteps}
          onPause={dispatchers.onPause}
          onStop={dispatchers.onStop}
        />
      ) : null}

      {ambiguity ? (
        <CardLocatorAmbiguity
          ambiguity={ambiguity}
          onChoose={dispatchers.onChooseLocatorCandidate}
          onAskLLM={dispatchers.onAskLocatorLLM}
          onChangeScope={dispatchers.onChangeLocatorScope}
          onStop={dispatchers.onStop}
        />
      ) : null}

      {pendingRecovery ? (
        <CardRecovery
          recovery={pendingRecovery}
          onApplyRepair={dispatchers.onApplyRecoveryLLM}
          onRetry={dispatchers.onRetryRecovery}
          onChooseLocator={dispatchers.onChooseLocator}
          onStop={dispatchers.onStop}
        />
      ) : null}

      {rejection ? (
        <CardSchemaError rejection={rejection} onAskRepair={dispatchers.onRepairPlan}/>
      ) : null}

      {completion ? (
        <CardCompleted
          completion={completion}
          onReplayAll={dispatchers.onReplayAll}
          onSaveSession={dispatchers.onSaveSession}
          onOpenCode={dispatchers.onOpenCode}
          onDownloadTrace={dispatchers.onDownloadTrace}
        />
      ) : null}
    </div>
  );
}

export default LlmThread;
