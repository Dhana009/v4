// frontend/src/v4/secondary-tabs.jsx — Live secondary tabs (Steps / Recorded / Code / Trace)
// All data sourced from runtime/storeState; never demo content; typed dispatch only.
import React, { useMemo, useState } from "react";
import { I } from "./icons.jsx";

function asArray(v) {
  return Array.isArray(v) ? v : [];
}

function pickFirst(...vals) {
  for (const v of vals) if (v != null && v !== "") return v;
  return null;
}

// — Steps tab ———————————————————————————————————————————

const EXPECTED_OUTCOME_TYPES = [
  "navigation",
  "modal",
  "dropdown",
  "new_tab",
  "toast_or_message",
  "content_change",
  "download",
  "file_picker",
  "no_visible_change",
  "not_sure",
];

function isClickLikeIntent(value) {
  const t = String(value ?? "").toLowerCase();
  return /click|tap|press|select|choose|open|navigate|submit/.test(t);
}

function PendingStepEditor({
  step,
  index,
  activePickerStepId,
  onChangeIntent,
  onChangeExpectedOutcome,
  onChangeElementTarget,
  onAttachElement,
  onDelete,
}) {
  const stepId = step.id ?? step.step_id;
  const intent = step.intent ?? step.text ?? step.description ?? "";
  const elementInfo = step.element_info ?? step.elementInfo ?? null;
  const candidates = Array.isArray(elementInfo?.candidates) ? elementInfo.candidates : [];
  const selectedIdx =
    typeof elementInfo?.selected_candidate_index === "number"
      ? elementInfo.selected_candidate_index
      : null;
  const expectedOutcome = step.expected_outcome ?? null;
  const expectedType = (expectedOutcome?.type ?? "").toLowerCase().replace(/[\s-]+/g, "_");
  const expectedDesc = expectedOutcome?.description ?? "";
  const isPicking = activePickerStepId === stepId;
  const needsOutcome = isClickLikeIntent(intent) && !expectedType;
  const ready = !!intent.trim() && (!isClickLikeIntent(intent) || expectedType);
  const status = isPicking ? "picking…" : needsOutcome ? "needs outcome" : ready ? "ready" : "draft";
  const targetSummary = elementInfo
    ? (elementInfo.text ?? elementInfo.label ?? elementInfo.tag ?? "(element)")
    : intent.trim()
    ? "No element attached."
    : "Draft step.";

  return (
    <div className="aw-step-row ide-step-card" data-testid={`step-row-${stepId}`}>
      <span className="aw-step-handle"><I.Drag/></span>
      <span className="aw-step-idx pending"
            style={{ background: ready ? "var(--grn)" : "var(--bg-card)", color: ready ? "#fff" : "var(--tx-3)" }}>
        {String(index + 1).padStart(2, "0")}
      </span>
      <div style={{ flex: 1, minWidth: 0 }}>
        <div className="ide-step-topline" style={{ display: "flex", gap: 6, alignItems: "center" }}>
          <input
            className="ide-input ide-step-input"
            data-testid={`step-input-${stepId}`}
            value={intent}
            onChange={(e) => onChangeIntent?.(stepId, e.target.value)}
            placeholder="click Get started"
            style={{ flex: 1 }}
          />
          <span className={`ide-badge ${ready ? "b-ready" : "b-await"}`} data-testid={`step-status-${stepId}`}>
            {status}
          </span>
        </div>
        <div className="ide-step-target-summary" data-testid={`step-target-${stepId}`}>
          {targetSummary}
        </div>
        {candidates.length > 1 ? (
          <select
            className="ide-input ide-step-target-select"
            data-testid="picker-candidate-select"
            aria-label="Choose locator candidate"
            value={selectedIdx == null ? "" : String(selectedIdx)}
            onChange={(e) => onChangeElementTarget?.(stepId, Number(e.target.value))}
          >
            {candidates.map((c, ci) => (
              <option key={ci} value={ci}>
                {c.label ?? c.text ?? c.tag ?? `candidate ${ci + 1}`}
              </option>
            ))}
          </select>
        ) : null}
        <div className="ide-step-outcome" data-testid={`step-outcome-${stepId}`}>
          <div className="ide-step-outcome-chips" style={{ display: "flex", gap: 4, flexWrap: "wrap" }}>
            {EXPECTED_OUTCOME_TYPES.map((type) => {
              const active = expectedType === type;
              return (
                <button
                  type="button"
                  key={type}
                  className={`ide-outcome-chip aw-btn subtle ${active ? "active" : ""}`}
                  data-testid={`step-outcome-chip-${type}-${stepId}`}
                  aria-label={type}
                  onClick={() =>
                    onChangeExpectedOutcome?.(stepId, {
                      type,
                      description: expectedDesc,
                      source: "user",
                      required: isClickLikeIntent(intent),
                    })
                  }
                >
                  {type}
                </button>
              );
            })}
          </div>
        </div>
        <div className="ide-step-actions" style={{ display: "flex", gap: 6, marginTop: 6 }}>
          <button
            type="button"
            className="aw-btn ide-btn sm"
            data-testid={`step-attach-${stepId}`}
            onClick={() => onAttachElement?.(stepId)}
          >
            {isPicking ? "Click page element…" : "Attach Element"}
          </button>
          <button
            type="button"
            className="aw-btn ide-btn sm danger"
            data-testid={`step-delete-${stepId}`}
            onClick={() => onDelete?.(stepId)}
          >
            Delete
          </button>
        </div>
      </div>
    </div>
  );
}

export function StepsTab({
  pendingSteps = [],
  selectedStepIds = [],
  activePickerStepId = "",
  onAdd,
  onPickElement,
  onToggleSelect,
  onRunSelected,
  onRunAll,
  onReorder,
  onDuplicate,
  onDelete,
  onEdit,
  onChangeIntent,
  onChangeExpectedOutcome,
  onChangeElementTarget,
  onAttachElement,
  blocked = false,
  blockedReason = "",
}) {
  const list = asArray(pendingSteps);
  const [filter, setFilter] = useState("");
  const filtered = filter
    ? list.filter((s) =>
        ((s.description ?? "") + " " + (s.id ?? s.step_id ?? "")).toLowerCase().includes(filter.toLowerCase())
      )
    : list;

  return (
    <div data-testid="steps-tab">
      <div className="aw-list-toolbar">
        <button type="button" className="aw-btn primary"
                data-testid="steps-add"
                onClick={() => typeof onAdd === "function" && onAdd({ type: "add_step" })}>
          <I.Plus/>Add step
        </button>
        <button type="button" className="aw-btn"
                data-testid="steps-pick"
                onClick={() => typeof onPickElement === "function" && onPickElement({ type: "arm_picker" })}>
          <I.Mouse/>Pick element
        </button>
        <span className="aw-spacer"/>
        <span className="aw-search">
          <I.Search style={{ width: 11, height: 11, color: "var(--tx-3)" }}/>
          <input data-testid="steps-filter" placeholder="Filter steps…"
                 value={filter} onChange={(e) => setFilter(e.target.value)}/>
        </span>
      </div>
      <div className="aw-info-strip">
        <I.Info/>
        <span>Step display order is for your convenience. Stable IDs persist across reorders.</span>
        <span className="aw-spacer"/>
        <button type="button"
                className="aw-btn primary"
                aria-label="Run Pending Steps"
                style={{ padding: "4px 10px" }}
                data-testid="steps-run-all"
                disabled={blocked || list.length === 0}
                onClick={() => typeof onRunAll === "function" && onRunAll({
                  type: "run_steps", step_ids: list.map((s) => s.step_id ?? s.id), mode: "all",
                })}>
          <I.Play/>Run Pending Steps
        </button>
        <button type="button" className="aw-btn"
                style={{ padding: "4px 10px" }}
                data-testid="steps-run-selected"
                disabled={blocked || selectedStepIds.length === 0}
                onClick={() => typeof onRunSelected === "function" && onRunSelected({
                  type: "run_steps", step_ids: selectedStepIds, mode: "selected",
                })}>
          <I.Play/>Run selected ({selectedStepIds.length})
        </button>
      </div>
      {blocked && blockedReason ? (
        <div className="aw-info-strip" data-testid="steps-blocked"
             style={{ background: "#FBEEEA", borderColor: "#E8B9AE", color: "#8A3A2E" }}>
          <I.Alert style={{ color: "var(--red)" }}/>
          <span>{blockedReason}</span>
        </div>
      ) : null}

      {filtered.length === 0 ? (
        <div className="aw-info-strip" data-testid="steps-empty">
          <I.Info/>
          <span>No pending steps. Use Add step or Pick element to start.</span>
        </div>
      ) : (
        filtered.map((s, i) => (
          <PendingStepEditor
            key={s.id ?? s.step_id ?? i}
            step={s}
            index={i}
            activePickerStepId={activePickerStepId}
            onChangeIntent={onChangeIntent}
            onChangeExpectedOutcome={onChangeExpectedOutcome}
            onChangeElementTarget={onChangeElementTarget}
            onAttachElement={onAttachElement ?? onPickElement}
            onDelete={(stepId) =>
              typeof onDelete === "function" && onDelete({ type: "delete_step", step_id: stepId })
            }
          />
        ))
      )}
    </div>
  );
}

// — Recorded tab ————————————————————————————————————————

export function RecordedTab({ recordedSteps = [], onReplayOne, onReplayAll }) {
  const list = asArray(recordedSteps);
  return (
    <div data-testid="recorded-tab">
      <div className="aw-info-strip">
        <I.Camera/>
        <span>Backend-emitted evidence only. Skipped or unresolved steps are not shown as recorded.</span>
        <span className="aw-spacer"/>
        <button type="button" className="aw-btn" style={{ padding: "4px 10px" }}
                data-testid="recorded-replay-all"
                disabled={list.length === 0 || typeof onReplayAll !== "function"}
                onClick={() => typeof onReplayAll === "function" && onReplayAll({ type: "replay_all" })}>
          <I.Repeat/>Replay all
        </button>
      </div>
      {list.length === 0 ? (
        <div className="aw-info-strip" data-testid="recorded-empty">
          <I.Info/>
          <span>No recorded steps yet. They appear here after `step_recorded` events.</span>
        </div>
      ) : (
        list.map((s, i) => {
          const id = pickFirst(s.step_id, s.id, `r-${i}`);
          const state = (s.state ?? s.status ?? "recorded").toLowerCase();
          const repaired = state === "repaired";
          const skipped = state === "skipped";
          const failed = state === "failed";
          const passed = !skipped && !failed;
          const title = s.description ?? s.title ?? id;
          const locator = s.locator ?? s.selector ?? "";
          return (
            <div key={id} className="aw-rec-item" data-testid={`recorded-item-${id}`}
                 data-state={state}>
              <div className="aw-rec-head">
                <span className="aw-step-idx ok"
                      style={{
                        background: passed ? "var(--grn)" : repaired ? "var(--ylw)" : "var(--bg-inset)",
                        color: passed ? "#fff" : (repaired ? "#fff" : "var(--tx-3)"),
                      }}>
                  {skipped ? <I.Skip style={{ width: 11, height: 11 }}/> :
                   repaired ? <I.Sync style={{ width: 11, height: 11 }}/> :
                              <I.Check style={{ width: 11, height: 11 }}/>}
                </span>
                <div style={{ flex: 1 }}>
                  <div style={{ fontSize: 13, fontWeight: 500 }} data-testid={`recorded-title-${id}`}>
                    {title}
                    <span style={{ fontFamily: "var(--ff-mono)", fontSize: 10, color: "var(--tx-4)", marginLeft: 6 }}>
                      {id}
                    </span>
                  </div>
                  <div className="aw-step-meta" style={{ marginTop: 3 }}>
                    <span className={`aw-badge-i ${passed ? "ok" : repaired ? "warn" : "outline"}`}>
                      <span className="ldot"/>{state}
                    </span>
                    {locator ? <span>locator: <span style={{ fontFamily: "var(--ff-mono)" }}>{locator}</span></span> : null}
                    {s.duration_ms ? <span>· {s.duration_ms}ms</span> : null}
                  </div>
                </div>
                {typeof onReplayOne === "function" ? (
                  <button type="button" className="aw-icon-btn" title="Replay"
                          data-testid={`recorded-replay-${id}`}
                          onClick={() => onReplayOne({ type: "replay_one", step_id: id })}>
                    <I.Repeat/>
                  </button>
                ) : null}
              </div>
              {asArray(s.children).length > 0 ? (
                <div className="aw-step-ops"
                     style={{ borderLeft: "2px solid var(--grn-soft)", marginTop: 6, paddingLeft: 10 }}
                     data-testid={`recorded-children-${id}`}>
                  {asArray(s.children).map((child, j) => (
                    <div key={j} className="aw-step-op">
                      <span className="op-tag">{child.operation ?? child.kind ?? "op"}</span>
                      {child.description ?? child.text ?? ""}
                      {child.generated_line ? (
                        <code style={{ marginLeft: 6, fontFamily: "var(--ff-mono)", fontSize: 11, color: "var(--tx-3)" }}>
                          {child.generated_line}
                        </code>
                      ) : null}
                    </div>
                  ))}
                </div>
              ) : null}
              {repaired && (s.repaired_from || s.repaired_to) ? (
                <div className="aw-diff" style={{ marginTop: 8, display: "flex", flexDirection: "column", gap: 1 }}>
                  {s.repaired_from ? (
                    <div className="aw-diff-row rem"><span className="aw-diff-sign">-</span>{s.repaired_from}</div>
                  ) : null}
                  {s.repaired_to ? (
                    <div className="aw-diff-row add"><span className="aw-diff-sign">+</span>{s.repaired_to}</div>
                  ) : null}
                </div>
              ) : null}
            </div>
          );
        })
      )}
    </div>
  );
}

// — Code tab ————————————————————————————————————————————

export function CodeTab({ codePreview, codeDiagnostics = [], onCopy, onSave }) {
  const text = useMemo(() => {
    if (!codePreview) return "";
    if (typeof codePreview === "string") return codePreview;
    return codePreview.code ?? codePreview.content ?? "";
  }, [codePreview]);
  const fileLabel = useMemo(() => {
    if (!codePreview) return "";
    if (typeof codePreview === "object") {
      return codePreview.file ?? codePreview.path ?? "";
    }
    return "";
  }, [codePreview]);
  const diagnostics = asArray(codeDiagnostics).filter(Boolean);
  const hasCode = !!text;

  return (
    <div data-testid="code-tab">
      <div className="aw-info-strip" style={{ background: "var(--blu-tint)", borderColor: "#D8E3F2" }}>
        <I.Info style={{ color: "var(--blu)" }}/>
        <span>
          Code is rendered from <span style={{ fontFamily: "var(--ff-mono)" }}>code_update</span> events.
          Frontend does not generate code.
        </span>
      </div>
      <div className="aw-list-toolbar" style={{ position: "sticky" }}>
        <span style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 12.5 }}>
          <I.Doc style={{ width: 13, height: 13, color: "var(--tx-2)" }}/>
          <span style={{ fontFamily: "var(--ff-mono)", color: "var(--tx)" }} data-testid="code-file-label">
            {fileLabel || (hasCode ? "generated.spec.ts" : "—")}
          </span>
        </span>
        <span className="aw-spacer"/>
        <button type="button" className="aw-btn"
                data-testid="code-copy"
                disabled={!hasCode}
                onClick={() => typeof onCopy === "function" && onCopy({ type: "copy_code", code: text })}>
          <I.Copy/>Copy
        </button>
        <button type="button" className="aw-btn"
                data-testid="code-save"
                disabled={!hasCode}
                onClick={() => typeof onSave === "function" && onSave({ type: "export_code", code: text })}>
          <I.Download/>Save
        </button>
      </div>

      {!hasCode ? (
        <div className="aw-info-strip" data-testid="code-empty">
          <I.Info/>
          <span>Awaiting code_update event. No code rendered yet.</span>
        </div>
      ) : (
        <div style={{ padding: "10px 14px" }}>
          <pre className="aw-code" data-testid="code-preview">{text}</pre>
          {diagnostics.length > 0 ? (
            <>
              <div className="aw-card-section-title">Diagnostics</div>
              <ul className="aw-dotlist" data-testid="code-diagnostics">
                {diagnostics.map((d, i) => {
                  const level = (d.level ?? d.severity ?? d.kind ?? "info").toLowerCase();
                  const cls = level === "warning" || level === "warn" || level === "error" ? "no" : "";
                  const message = d.message ?? d.text ?? d.reason ?? "";
                  return (
                    <li key={i} className={cls} data-testid={`code-diagnostic-${i}`}>
                      <span className="sec">{level}</span>{message}
                    </li>
                  );
                })}
              </ul>
            </>
          ) : null}
        </div>
      )}
    </div>
  );
}

// — Trace tab ————————————————————————————————————————————

const KNOWN_TYPES = new Set([
  "run_started", "plan_ready", "clarification_needed", "recommendation_ready",
  "permission_required", "locator_ambiguous", "recovery_needed",
  "step_validating", "step_executing", "step_failed", "step_skipped", "step_recorded",
  "code_update", "replay_started", "replay_result",
  "run_completed", "runtime_rejected", "session_state", "schema_error", "error",
]);

export function TraceTab({ traceEntries = [] }) {
  const [filter, setFilter] = useState("");
  const [kind, setKind] = useState("all");
  const list = asArray(traceEntries);
  const filtered = list.filter((row) => {
    const type = row.type ?? "";
    if (kind !== "all" && !type.startsWith(kind)) return false;
    if (filter && !((row.text ?? row.description ?? "") + type).toLowerCase().includes(filter.toLowerCase())) {
      return false;
    }
    return true;
  });

  return (
    <div data-testid="trace-tab">
      <div className="aw-list-toolbar">
        <span className="aw-search" style={{ flex: 1, maxWidth: 240 }}>
          <I.Search style={{ width: 11, height: 11, color: "var(--tx-3)" }}/>
          <input data-testid="trace-filter" placeholder="Filter events…"
                 value={filter} onChange={(e) => setFilter(e.target.value)}/>
        </span>
        <span style={{ display: "flex", gap: 4 }}>
          {["all", "llm", "step", "permission", "error", "code"].map((k) => (
            <span key={k}
                  className={"aw-badge-i " + (kind === k ? "info" : "outline")}
                  style={{ cursor: "pointer" }}
                  data-testid={`trace-filter-${k}`}
                  onClick={() => setKind(k)}>
              {kind === k ? <span className="ldot"/> : null}{k}
            </span>
          ))}
        </span>
      </div>
      {filtered.length === 0 ? (
        <div className="aw-info-strip" data-testid="trace-empty">
          <I.Info/>
          <span>No trace events yet.</span>
        </div>
      ) : (
        filtered.map((r, i) => {
          const type = r.type ?? "unknown";
          const known = KNOWN_TYPES.has(type) || ["session", "plan", "step", "llm", "code", "permission", "locator", "recover", "redact", "page", "e2e", "run"].some((p) => type.startsWith(p));
          const cls = r.severity === "err" || r.severity === "error" ? "err"
                    : r.severity === "warn" ? "warn"
                    : type.includes("ok") || type === "step.recorded" || type === "run_completed" ? "ok"
                    : known ? "" : "unknown";
          return (
            <div key={r.id ?? i}
                 className={"aw-trace-row " + cls}
                 data-testid={`trace-row-${i}`}
                 data-type={type}
                 data-known={known ? "1" : "0"}>
              <span className="t">{r.timestamp ?? r.t ?? ""}</span>
              <span className="aw-trace-icon"><I.Info style={{ width: 10, height: 10 }}/></span>
              <span className="type">{type}</span>
              <span className="desc">
                {r.text ?? r.description ?? r.message ?? ""}
                {!known ? <span style={{ marginLeft: 8, color: "var(--tx-4)" }}>(unknown event · diagnostic only)</span> : null}
              </span>
            </div>
          );
        })
      )}
    </div>
  );
}

export default { StepsTab, RecordedTab, CodeTab, TraceTab };
