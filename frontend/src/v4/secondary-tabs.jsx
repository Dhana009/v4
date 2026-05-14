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

// Pass 4b-1: backend-driven locator strength chip. Renders nothing unless the
// backend has classified the locator (no frontend inference). Reads:
//   step.locator_kind      = "ok" | "med" | "warn" | "unknown"
//   step.locator_strength  = "strong" | "medium" | "weak" | "unknown"
//   step.locator_reason    = short backend-generated explanation
// Falls back to the same fields on step.element_info when the step came from
// the picker rather than plan_ready.
function readLocatorMetadata(step) {
  const info = step && typeof step === "object" ? step.element_info ?? step.elementInfo ?? null : null;
  const kind = pickFirst(step?.locator_kind, info?.locator_kind);
  if (!kind) return null;
  const strength = pickFirst(step?.locator_strength, info?.locator_strength) ?? "unknown";
  const reason = pickFirst(step?.locator_reason, info?.locator_reason) ?? "";
  return { kind, strength, reason };
}

// Pass 4b-2: backend-driven step kind chip. Renders nothing unless backend
// payload provides `step.step_kind` ∈ {atomic, loop, section, unknown}.
const _VALID_STEP_KINDS = new Set(["atomic", "loop", "section", "unknown"]);
const _STEP_KIND_LABELS = {
  atomic: "Atomic",
  loop: "Loop",
  section: "Section",
  unknown: "Unknown",
};

function StepKindChip({ step, stepId }) {
  const raw = step && typeof step === "object" ? step.step_kind : null;
  if (typeof raw !== "string") return null;
  const kind = _VALID_STEP_KINDS.has(raw) ? raw : "unknown";
  const label = _STEP_KIND_LABELS[kind];
  return (
    <span
      className={`aw-badge-i ${kind === "section" ? "vio" : kind === "loop" ? "info" : kind === "unknown" ? "outline" : "outline"}`}
      data-testid={`step-kind-${stepId}`}
      data-kind={kind}
      data-raw-kind={raw}
      style={{ display: "inline-flex", alignItems: "center", gap: 4, marginTop: 4, marginLeft: 6, fontSize: 11 }}
    >
      <span className="ldot" />
      <span>{label}</span>
    </span>
  );
}

// Pass 4b-5: backend-driven precondition strip. Renders only when
// `step.precondition.status === "failed"`. Frontend never infers wrong-page
// state from text or URL comparison.
const _VALID_PRECONDITION_STATUS = new Set(["passed", "failed", "unknown"]);

function readPreconditionMetadata(step) {
  const raw = step && typeof step === "object" ? step.precondition : null;
  if (!raw || typeof raw !== "object" || Array.isArray(raw)) return null;
  const rawStatus = typeof raw.status === "string" ? raw.status : "unknown";
  const status = _VALID_PRECONDITION_STATUS.has(rawStatus) ? rawStatus : "unknown";
  return {
    status,
    rawStatus,
    expected_url: typeof raw.expected_url === "string" ? raw.expected_url : "",
    current_url: typeof raw.current_url === "string" ? raw.current_url : "",
    message: typeof raw.message === "string" ? raw.message : "",
  };
}

function StepPreconditionStrip({ step, stepId, onChangePrecondition, onNavigateToExpected }) {
  const meta = readPreconditionMetadata(step);
  if (!meta || meta.status !== "failed") return null;
  const { rawStatus, expected_url, current_url, message } = meta;

  const canChangePrec = !!stepId && typeof onChangePrecondition === "function";
  const canNavigate = !!stepId && typeof expected_url === "string" && expected_url.length > 0 && typeof onNavigateToExpected === "function";

  return (
    <div
      className="aw-info-strip aw-step-precondition"
      data-testid={`step-precondition-${stepId}`}
      data-status="failed"
      data-raw-status={rawStatus}
      role="alert"
      style={{
        background: "#FBF1D2",
        borderColor: "#ECD89A",
        color: "#7A5A0E",
        marginTop: 6,
        padding: "6px 10px",
        borderRadius: 6,
        display: "flex",
        alignItems: "center",
        gap: 6,
        flexWrap: "wrap",
        fontSize: 12,
      }}
    >
      <I.Alert style={{ width: 12, height: 12, color: "#7A5A0E" }} />
      <span>Wrong current page</span>
      {expected_url ? (
        <span
          className="scope"
          data-testid={`step-precondition-expected-${stepId}`}
          style={{ fontFamily: "var(--ff-mono)", fontSize: 11 }}
        >
          expected: {expected_url}
        </span>
      ) : null}
      {current_url ? (
        <span
          className="scope"
          data-testid={`step-precondition-current-${stepId}`}
          style={{ fontFamily: "var(--ff-mono)", fontSize: 11 }}
        >
          current: {current_url}
        </span>
      ) : null}
      {message ? <span>· {message}</span> : null}
      <button
        type="button"
        className="aw-link"
        data-testid={`step-precondition-action-${stepId}`}
        disabled={!canChangePrec}
        title={canChangePrec ? "Update the expected precondition URL for this step" : "Change precondition handler not wired"}
        style={{
          marginLeft: "auto",
          color: "#7A5A0E",
          opacity: canChangePrec ? 1 : 0.6,
          cursor: canChangePrec ? "pointer" : "not-allowed",
        }}
        onClick={canChangePrec ? () => onChangePrecondition({ type: "change_precondition", step_id: stepId, expected_url: expected_url || "" }) : undefined}
      >
        Change precondition
      </button>
      {canNavigate ? (
        <button
          type="button"
          className="aw-link"
          data-testid={`step-navigate-expected-${stepId}`}
          title={`Navigate browser to ${expected_url}`}
          style={{ color: "#7A5A0E", cursor: "pointer" }}
          onClick={() => onNavigateToExpected({ type: "navigate_to_expected", step_id: stepId, expected_url: expected_url })}
        >
          Navigate there
        </button>
      ) : null}
    </div>
  );
}

// Pass 4b-6: backend-driven child operation count badge. Renders only when
// `step.child_op_count` is a non-negative integer in payload (backend
// normalizer guarantees this from explicit value or len(children)).
function StepChildCountBadge({ step, stepId }) {
  if (!step || typeof step !== "object") return null;
  const raw = step.child_op_count;
  if (typeof raw !== "number" || !Number.isFinite(raw) || raw < 0 || Number.isInteger(raw) === false) {
    return null;
  }
  return (
    <span
      className="aw-badge-i info"
      data-testid={`step-child-count-${stepId}`}
      data-count={String(raw)}
      style={{ display: "inline-flex", alignItems: "center", gap: 4, marginTop: 4, marginLeft: 6, fontSize: 11 }}
    >
      <span className="ldot" />
      <span>{raw} child op{raw === 1 ? "" : "s"}</span>
    </span>
  );
}

// Pass 4b-4: backend-driven blocked-step strip. Renders only when
// `step.blocked` is a dict with a valid reason (backend normalizer guarantees
// this on plan_ready). No frontend inference of blocked state.
const _VALID_BLOCKED_REASONS = new Set([
  "missing_data",
  "wrong_page",
  "locator_unstable",
  "permission_required",
  "unknown",
]);
const _BLOCKED_REASON_LABELS = {
  missing_data: "Blocked — missing data",
  wrong_page: "Blocked — wrong current page",
  locator_unstable: "Blocked — locator unstable",
  permission_required: "Blocked — permission required",
  unknown: "Blocked",
};

function readBlockedMetadata(step) {
  const raw = step && typeof step === "object" ? step.blocked : null;
  if (!raw || typeof raw !== "object" || Array.isArray(raw)) return null;
  const rawReason = typeof raw.reason === "string" ? raw.reason : "unknown";
  const reason = _VALID_BLOCKED_REASONS.has(rawReason) ? rawReason : "unknown";
  const refs = Array.isArray(raw.refs) ? raw.refs : [];
  return {
    reason,
    rawReason,
    refs,
    message: typeof raw.message === "string" ? raw.message : "",
    action_label: typeof raw.action_label === "string" ? raw.action_label : "",
  };
}

// D-101: Map blocked reason to the underlying typed command to dispatch.
// resolve_blocked has NO standalone backend handler; the button dispatches
// existing typed commands directly per reason.
function _blockedActionCommand(reason, stepId) {
  switch (reason) {
    case "missing_data":
      return { type: "correction", step_id: stepId, message: `Provide missing data for step ${stepId}` };
    case "permission_required":
      return { type: "permission_decision", decision: "allow_once", step_id: stepId };
    case "locator_unstable":
      return { type: "improve_locator", step_id: stepId };
    case "wrong_page":
      return { type: "navigate_to_expected", step_id: stepId };
    case "unknown":
    default:
      return { type: "skip_step", step_id: stepId };
  }
}

function StepBlockedStrip({ step, stepId, onResolveBlocked }) {
  const meta = readBlockedMetadata(step);
  if (!meta) return null;
  const { reason, rawReason, refs, message, action_label } = meta;
  const palette =
    reason === "missing_data" ? { bg: "#FBEEEA", br: "#E8B9AE", tx: "#8A3A2E" } :
    reason === "wrong_page" || reason === "locator_unstable" ? { bg: "#FBF1D2", br: "#ECD89A", tx: "#7A5A0E" } :
    reason === "permission_required" ? { bg: "#EEEFFF", br: "#C6CAF5", tx: "#3F46AD" } :
    { bg: "#F4F1EC", br: "#D9D2C5", tx: "#5C5448" };

  // Determine if action can be dispatched (requires a valid stepId and a callback)
  const canDispatch = !!stepId && typeof onResolveBlocked === "function";
  const actionTitle = canDispatch
    ? `${action_label || "Resolve"} — dispatches ${_blockedActionCommand(reason, stepId).type}`
    : !stepId
    ? "Cannot resolve: step_id is missing"
    : "Resolve handler not wired";

  return (
    <div
      className="aw-info-strip aw-step-blocked"
      data-testid={`step-blocked-${stepId}`}
      data-reason={reason}
      data-raw-reason={rawReason}
      role="alert"
      style={{
        background: palette.bg,
        borderColor: palette.br,
        color: palette.tx,
        marginTop: 6,
        padding: "6px 10px",
        borderRadius: 6,
        display: "flex",
        alignItems: "center",
        gap: 6,
        fontSize: 12,
      }}
    >
      <I.Alert style={{ width: 12, height: 12, color: palette.tx }} />
      <span
        className="aw-step-blocked-reason"
        data-testid={`step-blocked-reason-${stepId}`}
      >
        {_BLOCKED_REASON_LABELS[reason]}
        {message ? `: ${message}` : ""}
      </span>
      {refs.length > 0 ? (
        <span
          className="aw-step-blocked-refs"
          data-testid={`step-blocked-refs-${stepId}`}
          style={{ marginLeft: 8, display: "inline-flex", gap: 4, flexWrap: "wrap" }}
        >
          {refs.map((r, idx) => {
            const refId = String(
              (r && typeof r === "object" ? (r.id ?? r.ref_id ?? r.name) : r) ?? `ref_${idx + 1}`
            );
            const refLabel = typeof r === "string" ? r : refId;
            return (
              <span
                key={`${idx}-${refId}`}
                className="scope"
                data-testid={`step-blocked-ref-${stepId}-${refId}`}
                style={{ fontFamily: "var(--ff-mono)", fontSize: 11 }}
              >
                {refLabel}
              </span>
            );
          })}
        </span>
      ) : null}
      {action_label ? (
        <button
          type="button"
          className="aw-link"
          data-testid={`step-blocked-action-${stepId}`}
          disabled={!canDispatch}
          title={actionTitle}
          style={{
            marginLeft: "auto",
            color: palette.tx,
            opacity: canDispatch ? 1 : 0.6,
            cursor: canDispatch ? "pointer" : "not-allowed",
          }}
          onClick={canDispatch ? () => onResolveBlocked(_blockedActionCommand(reason, stepId)) : undefined}
        >
          {action_label}
        </button>
      ) : null}
    </div>
  );
}

// Pass 4b-3: backend-driven section child-op list. Renders only when the
// step has a non-empty `children` array of dicts. Each child shows its
// description / type and (when present) status. No frontend invention of
// children from prose.
function StepChildrenList({ step, stepId }) {
  const raw = step && typeof step === "object" ? step.children : null;
  if (!Array.isArray(raw) || raw.length === 0) return null;
  const valid = raw.filter((c) => c && typeof c === "object");
  if (valid.length === 0) return null;
  return (
    <div
      className="aw-step-children"
      data-testid={`step-children-${stepId}`}
      data-count={String(valid.length)}
      style={{
        marginTop: 6,
        borderLeft: "2px solid var(--vio-soft)",
        paddingLeft: 10,
        display: "flex",
        flexDirection: "column",
        gap: 4,
      }}
    >
      {valid.map((child, idx) => {
        const childId = String(child.child_id ?? child.operation_id ?? child.id ?? `op_${idx + 1}`);
        const opType = typeof child.type === "string" && child.type ? child.type : "op";
        const label =
          (typeof child.description === "string" && child.description) ||
          (typeof child.text === "string" && child.text) ||
          (typeof child.label === "string" && child.label) ||
          "";
        const status =
          typeof child.status === "string" && child.status ? child.status : null;
        const opTag = `${idx + 1}`.padStart(1, "0");
        return (
          <div
            key={childId}
            className="aw-step-op"
            data-testid={`step-child-${stepId}-${childId}`}
            data-op-type={opType}
            data-op-status={status ?? ""}
            style={{ display: "flex", alignItems: "center", gap: 6, fontSize: 12 }}
          >
            <span
              className="op-tag"
              style={{
                background: "var(--vio-soft)",
                color: "var(--vio)",
                padding: "1px 6px",
                borderRadius: 4,
                fontSize: 10,
                fontFamily: "var(--ff-mono)",
              }}
            >
              {opTag}
            </span>
            <span
              className="aw-step-op-label"
              data-testid={`step-child-label-${stepId}-${childId}`}
            >
              {label || `(${opType})`}
            </span>
            {status ? (
              <span
                className={`aw-badge-i ${
                  status === "passed" || status === "recorded" || status === "ok" ? "ok" :
                  status === "failed" ? "err" :
                  status === "skipped" ? "outline" : "outline"
                }`}
                data-testid={`step-child-status-${stepId}-${childId}`}
                data-status={status}
                style={{ fontSize: 10 }}
              >
                <span className="ldot" />
                {status}
              </span>
            ) : null}
          </div>
        );
      })}
    </div>
  );
}

// Pass 4b-1 / D-101: locator improve button shown when locator is non-strong.
// Rendered as a separate block below the strength badge so the badge keeps its
// inline-badge shape. Buttons absent when no step id or no handler wired.
const _NON_STRONG_LOCATOR_KINDS = new Set(["warn", "med", "unknown"]);

function StepLocatorChip({ step, stepId, onImproveLocator, onViewCandidates }) {
  const meta = readLocatorMetadata(step);
  if (!meta) return null;
  const { kind, strength, reason } = meta;
  const label =
    strength === "strong" ? "strong locator" :
    strength === "medium" ? "medium locator" :
    strength === "weak" ? "weak locator" :
    "locator unknown";
  const showActions = !!stepId && _NON_STRONG_LOCATOR_KINDS.has(kind);
  return (
    <div style={{ display: "inline-flex", flexWrap: "wrap", alignItems: "center", gap: 4, marginTop: 4 }}>
      <div
        className={`aw-badge-i ${kind === "warn" ? "warn" : kind === "med" ? "outline" : kind === "ok" ? "ok" : "outline"}`}
        data-testid={`step-locator-${stepId}`}
        data-kind={kind}
        data-strength={strength}
        title={reason || label}
        style={{ display: "inline-flex", alignItems: "center", gap: 4, fontSize: 11 }}
      >
        <span className="ldot" />
        <span>{label}</span>
        {reason ? <span style={{ color: "var(--tx-3)" }}>· {reason}</span> : null}
      </div>
      {showActions ? (
        <>
          <button
            type="button"
            className="aw-btn subtle"
            data-testid={`step-improve-locator-${stepId}`}
            disabled={typeof onImproveLocator !== "function"}
            title={
              typeof onImproveLocator === "function"
                ? "Ask LLM to improve this locator"
                : "Improve locator — runtime not connected"
            }
            style={{ fontSize: 10, padding: "1px 6px" }}
            onClick={() =>
              typeof onImproveLocator === "function" &&
              onImproveLocator({ type: "improve_locator", step_id: stepId })
            }
          >
            Improve locator
          </button>
          <button
            type="button"
            className="aw-btn subtle"
            data-testid={`step-view-candidates-${stepId}`}
            disabled={typeof onViewCandidates !== "function"}
            title={
              typeof onViewCandidates === "function"
                ? "View locator candidates for this step"
                : "View candidates — runtime not connected"
            }
            style={{ fontSize: 10, padding: "1px 6px" }}
            onClick={() =>
              typeof onViewCandidates === "function" &&
              onViewCandidates({ type: "view_candidates", step_id: stepId })
            }
          >
            View candidates
          </button>
        </>
      ) : null}
    </div>
  );
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
  onImproveLocator,
  onViewCandidates,
  onResolveBlocked,
  onChangePrecondition,
  onNavigateToExpected,
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
  const blockedMeta = readBlockedMetadata(step);
  const ready =
    !blockedMeta && !!intent.trim() && (!isClickLikeIntent(intent) || expectedType);
  const status = blockedMeta
    ? "blocked"
    : isPicking ? "picking…" : needsOutcome ? "needs outcome" : ready ? "ready" : "draft";
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
          {stepId ? (
            <span
              className="id"
              data-testid={`step-id-${stepId}`}
              style={{ fontFamily: "var(--ff-mono)", fontSize: 10, color: "var(--tx-4)", flexShrink: 0 }}
              title={`step id: ${stepId}`}
            >
              {stepId}
            </span>
          ) : null}
        </div>
        <div className="ide-step-target-summary" data-testid={`step-target-${stepId}`}>
          {targetSummary}
        </div>
        <StepLocatorChip step={step} stepId={stepId} onImproveLocator={onImproveLocator} onViewCandidates={onViewCandidates} />
        <StepKindChip step={step} stepId={stepId} />
        <StepChildCountBadge step={step} stepId={stepId} />
        <StepBlockedStrip step={step} stepId={stepId} onResolveBlocked={onResolveBlocked} />
        <StepPreconditionStrip step={step} stepId={stepId} onChangePrecondition={onChangePrecondition} onNavigateToExpected={onNavigateToExpected} />
        <StepChildrenList step={step} stepId={stepId} />
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
  onImproveLocator,
  onViewCandidates,
  onResolveBlocked,
  onChangePrecondition,
  onNavigateToExpected,
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
                onClick={() => typeof onRunAll === "function" && onRunAll()}>
          <I.Play/>Run Pending Steps
        </button>
        <button type="button" className="aw-btn"
                style={{ padding: "4px 10px" }}
                data-testid="steps-run-selected"
                disabled={blocked || selectedStepIds.length === 0}
                onClick={() => typeof onRunSelected === "function" && onRunSelected()}>
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
            onImproveLocator={onImproveLocator}
            onViewCandidates={onViewCandidates}
            onResolveBlocked={onResolveBlocked}
            onChangePrecondition={onChangePrecondition}
            onNavigateToExpected={onNavigateToExpected}
          />
        ))
      )}
    </div>
  );
}

// — Recorded tab ————————————————————————————————————————

// Pass 5 (D-102): backend evidence read helpers. Frontend never invents
// recorded state — it surfaces what the backend's step_recorded /
// recorded_steps payload contains.
function readRecordedStatus(s) {
  const raw = s && typeof s === "object" ? (s.state ?? s.status) : null;
  if (typeof raw !== "string") return "unknown";
  return raw.toLowerCase();
}

function readRecordedOutcome(s, kind) {
  if (!s || typeof s !== "object") return null;
  const field = kind === "expected" ? "expected_outcome" : "observed_outcome";
  const obj = s[field];
  if (obj && typeof obj === "object" && !Array.isArray(obj)) {
    const text = typeof obj.description === "string" ? obj.description :
                 typeof obj.text === "string" ? obj.text :
                 typeof obj.value === "string" ? obj.value : "";
    const type = typeof obj.type === "string" ? obj.type : "";
    if (!text && !type) return null;
    return { type, text };
  }
  // Fallback: plain string field (some backends emit "observed_text").
  const fallback = kind === "expected" ? s.expected_text : s.observed_text;
  if (typeof fallback === "string" && fallback) return { type: "", text: fallback };
  return null;
}

export function RecordedTab({ recordedSteps = [], onReplayOne, onReplayAll }) {
  // Filter malformed entries up front so the frontend never invents a
  // "recorded item" row for non-objects (per D-102 honesty rule).
  const list = asArray(recordedSteps).filter((s) => s && typeof s === "object");
  const replayAllEnabled = list.length > 0 && typeof onReplayAll === "function";
  return (
    <div data-testid="recorded-tab">
      <div className="aw-info-strip">
        <I.Camera/>
        <span>Backend-emitted evidence only. Skipped or unresolved steps are not shown as recorded.</span>
        <span className="aw-spacer"/>
        <span className="ide-stat" data-testid="recorded-count">
          recorded: <span className="ide-stat-num">{list.filter((s) => readRecordedStatus(s) !== "skipped" && readRecordedStatus(s) !== "unresolved").length}</span>
        </span>
        <button type="button" className="aw-btn" style={{ padding: "4px 10px" }}
                data-testid="recorded-replay-all"
                disabled={!replayAllEnabled}
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
          // Stable id only when backend provided one. Synthetic `r-${i}`
          // marks "no backend id" — frontend must not pretend to replay it.
          const backendId = s.step_id ?? s.id;
          const hasBackendId = typeof backendId === "string" && backendId.trim() !== "";
          const id = hasBackendId ? backendId : `r-${i}`;
          const state = readRecordedStatus(s);
          const repaired = state === "repaired";
          const skipped = state === "skipped";
          const failed = state === "failed";
          const unresolved = state === "unresolved";
          const passed = !skipped && !failed && !unresolved && state !== "unknown";
          const title = s.description ?? s.title ?? id;
          const locator = s.locator ?? s.selector ?? "";
          const locatorKind = s.locator_kind ?? null;
          const expected = readRecordedOutcome(s, "expected");
          const observed = readRecordedOutcome(s, "observed");
          const children = asArray(s.children);
          const artifacts = asArray(s.artifacts);
          const durationMs = s.duration_ms;
          return (
            <div key={id}
                 className="aw-rec-item ide-recorded-step"
                 data-testid={`recorded-item-${id}`}
                 data-state={state}
                 data-has-backend-id={hasBackendId ? "1" : "0"}>
              <div className="aw-rec-head">
                <span className="aw-step-idx ok"
                      data-testid={`recorded-row-${id}`}
                      style={{
                        background: passed ? "var(--grn)" : repaired ? "var(--ylw)" : failed ? "var(--red)" : "var(--bg-inset)",
                        color: passed || repaired || failed ? "#fff" : "var(--tx-3)",
                      }}>
                  {skipped ? <I.Skip style={{ width: 11, height: 11 }}/> :
                   repaired ? <I.Sync style={{ width: 11, height: 11 }}/> :
                   failed ? <I.Alert style={{ width: 11, height: 11 }}/> :
                              <I.Check style={{ width: 11, height: 11 }}/>}
                </span>
                <div style={{ flex: 1 }}>
                  <div className="ide-recorded-step-title" style={{ fontSize: 13, fontWeight: 500 }} data-testid={`recorded-title-${id}`}>
                    {title}
                    <span style={{ fontFamily: "var(--ff-mono)", fontSize: 10, color: "var(--tx-4)", marginLeft: 6 }}>
                      {id}
                    </span>
                  </div>
                  <div className="aw-step-meta" style={{ marginTop: 3 }}>
                    <span
                      className={`aw-badge-i ${passed ? "ok" : repaired ? "warn" : failed ? "err" : "outline"}`}
                      data-testid={`recorded-status-${id}`}
                      data-status={state}
                    >
                      <span className="ldot"/>{state}
                    </span>
                    {locator ? (
                      <span
                        data-testid={`recorded-locator-${id}`}
                        data-locator-kind={locatorKind ?? ""}
                      >
                        locator: <span style={{ fontFamily: "var(--ff-mono)" }}>{locator}</span>
                      </span>
                    ) : null}
                    {typeof durationMs === "number" ? <span>· {durationMs}ms</span> : null}
                  </div>
                  {expected ? (
                    <div
                      className="aw-rec-expected"
                      data-testid={`recorded-expected-${id}`}
                      data-expected-type={expected.type}
                      style={{ marginTop: 3, fontSize: 11.5, color: "var(--tx-3)" }}
                    >
                      expected: {expected.type ? <b>{expected.type}</b> : null} {expected.text}
                    </div>
                  ) : null}
                  {observed ? (
                    <div
                      className="aw-rec-observed"
                      data-testid={`recorded-observed-${id}`}
                      data-observed-type={observed.type}
                      style={{ marginTop: 2, fontSize: 11.5, color: passed ? "var(--tx-3)" : "var(--red)" }}
                    >
                      observed: {observed.type ? <b>{observed.type}</b> : null} {observed.text}
                    </div>
                  ) : null}
                </div>
                <button
                  type="button"
                  className="aw-icon-btn"
                  title={hasBackendId
                    ? (typeof onReplayOne === "function" ? "Replay" : "Replay command not yet wired")
                    : "No backend step id"
                  }
                  data-testid={`recorded-replay-${id}`}
                  disabled={!hasBackendId || typeof onReplayOne !== "function"}
                  onClick={() => {
                    if (hasBackendId && typeof onReplayOne === "function") {
                      onReplayOne({ type: "replay_one", step_id: id });
                    }
                  }}
                >
                  <I.Repeat/>
                </button>
              </div>
              {children.length > 0 ? (
                <div className="aw-step-ops"
                     style={{ borderLeft: "2px solid var(--grn-soft)", marginTop: 6, paddingLeft: 10 }}
                     data-testid={`recorded-child-list-${id}`}
                     data-count={String(children.filter((c) => c && typeof c === "object").length)}>
                  {children.map((child, j) => {
                    if (!child || typeof child !== "object") return null;
                    const childId = String(child.child_id ?? child.operation_id ?? child.id ?? `op_${j + 1}`);
                    const op = child.operation ?? child.kind ?? child.type ?? "op";
                    const desc = child.description ?? child.text ?? "";
                    const childStatus = typeof child.status === "string" ? child.status : null;
                    return (
                      <div
                        key={childId}
                        className="aw-step-op"
                        data-testid={`recorded-child-${id}-${childId}`}
                        data-op-type={op}
                        data-op-status={childStatus ?? ""}
                      >
                        <span className="op-tag">{op}</span>
                        <span className="ide-plan-child-desc">{desc}</span>
                        {child.generated_line ? (
                          <code style={{ marginLeft: 6, fontFamily: "var(--ff-mono)", fontSize: 11, color: "var(--tx-3)" }}>
                            {child.generated_line}
                          </code>
                        ) : null}
                        {childStatus ? (
                          <span
                            className={`aw-badge-i ${
                              childStatus === "passed" || childStatus === "recorded" || childStatus === "ok" ? "ok" :
                              childStatus === "failed" ? "err" :
                              childStatus === "skipped" ? "outline" : "outline"
                            }`}
                            style={{ marginLeft: 6, fontSize: 10 }}
                            data-status={childStatus}
                          >
                            <span className="ldot"/>{childStatus}
                          </span>
                        ) : null}
                      </div>
                    );
                  })}
                </div>
              ) : null}
              {artifacts.length > 0 ? (
                <div
                  className="aw-rec-artifacts"
                  data-testid={`recorded-artifact-list-${id}`}
                  style={{ marginTop: 6, display: "flex", gap: 6, flexWrap: "wrap" }}
                >
                  {artifacts.map((a, j) => {
                    if (!a) return null;
                    const isStr = typeof a === "string";
                    const artifactId = String(
                      isStr ? a : (a.id ?? a.artifact_id ?? a.name ?? `art_${j + 1}`)
                    );
                    const href = isStr ? a : (typeof a === "object" ? (a.url ?? a.href ?? a.path ?? "") : "");
                    const label = isStr ? a : (typeof a === "object" ? (a.label ?? a.name ?? artifactId) : String(a));
                    return (
                      <a
                        key={artifactId}
                        href={href || undefined}
                        target={href ? "_blank" : undefined}
                        rel={href ? "noreferrer" : undefined}
                        className="aw-link"
                        data-testid={`recorded-artifact-${id}-${artifactId}`}
                        data-artifact-href={href}
                        style={{ fontSize: 11 }}
                      >
                        <I.Camera style={{ width: 10, height: 10 }} /> {label}
                      </a>
                    );
                  })}
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

export function CodeTab({ codePreview, codeDiagnostics = [], onCopy, onSave, codeSaveResult }) {
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

      {codeSaveResult ? (
        codeSaveResult.ok ? (
          <div
            className="aw-info-strip"
            data-testid="code-save-result"
            data-status="ok"
            data-path={codeSaveResult.path ?? ""}
            style={{ background: "var(--grn-tint,#f0faf3)", borderColor: "#b2dfcc" }}
          >
            <I.Check style={{ color: "var(--grn,#22863a)" }}/>
            <span>Saved to <span style={{ fontFamily: "var(--ff-mono)" }}>{codeSaveResult.path}</span></span>
          </div>
        ) : (
          <div
            className="aw-info-strip"
            data-testid="code-save-result"
            data-status="error"
            data-error={codeSaveResult.error ?? ""}
            style={{ background: "var(--red-tint,#fff0f0)", borderColor: "#ffb3b3" }}
          >
            <I.Info style={{ color: "var(--red,#d73a49)" }}/>
            <span>Save failed: {codeSaveResult.error}</span>
          </div>
        )
      ) : null}

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
  "capability_gap_recorded",
]);

// Filter predicate — gap uses exact match; all others use startsWith
function matchesKind(type, kind) {
  if (kind === "all") return true;
  if (kind === "gap") return type === "capability_gap_recorded";
  return type.startsWith(kind);
}

// D-104 §4: Failure detail panel — renders only fields the step_failed payload provides.
// Fields: step_id, error, status, operation_id (optional). No fabricated fields.
function TraceFailureDetail({ entry, rowIndex }) {
  const payload = entry?.raw?.payload ?? entry?.raw ?? {};
  const stepId = payload.step_id ?? null;
  const error = entry.summary ?? payload.error ?? null;
  const status = payload.status ?? null;
  const operationId = payload.operation_id ?? null;
  return (
    <div
      className="aw-trace-detail"
      data-testid={`trace-failure-detail-${rowIndex}`}
      style={{ marginTop: 6, padding: "8px 10px", background: "var(--bg-inset)", borderRadius: 6, fontSize: 12 }}
    >
      {stepId != null && (
        <div data-testid={`trace-failure-step-${rowIndex}`} style={{ marginBottom: 4 }}>
          <span style={{ color: "var(--tx-3)" }}>step_id: </span>
          <span style={{ fontFamily: "var(--ff-mono)" }}>{String(stepId)}</span>
        </div>
      )}
      {error != null && (
        <div data-testid={`trace-failure-error-${rowIndex}`} style={{ marginBottom: 4 }}>
          <span style={{ color: "var(--tx-3)" }}>error: </span>
          <span style={{ color: "var(--red)" }}>{String(error)}</span>
        </div>
      )}
      {status != null && (
        <div data-testid={`trace-failure-status-${rowIndex}`} style={{ marginBottom: 4 }}>
          <span style={{ color: "var(--tx-3)" }}>status: </span>
          <span
            className={`aw-badge-i ${status === "failed" ? "err" : "outline"}`}
            style={{ display: "inline-flex", gap: 4 }}
          >
            <span className="ldot"/>{String(status)}
          </span>
        </div>
      )}
      {operationId != null && (
        <div data-testid={`trace-failure-op-${rowIndex}`} style={{ marginBottom: 4 }}>
          <span style={{ color: "var(--tx-3)" }}>operation_id: </span>
          <span style={{ fontFamily: "var(--ff-mono)" }}>{String(operationId)}</span>
        </div>
      )}
      <div style={{ marginTop: 4, color: "var(--tx-3)", fontStyle: "italic", fontSize: 11 }}>
        Recovery entered — see Recovery card
      </div>
    </div>
  );
}

// D-104 §5: LLM telemetry section — renders fields when present; honest unavailable when absent.
const LLM_TYPES = new Set(["llm_thinking", "llm_result", "agent_trace"]);

function TraceLlmTelemetry({ entry, rowIndex }) {
  const isLlmType = LLM_TYPES.has(entry.type ?? "") || (entry.type ?? "").startsWith("llm");
  if (!isLlmType) return null;
  const payload = entry?.raw?.payload ?? entry?.raw ?? {};
  const model = payload.model ?? null;
  const inputTokens = payload.input_tokens ?? payload.total_input_tokens ?? null;
  const outputTokens = payload.output_tokens ?? null;
  const estimatedCost = payload.estimated_cost ?? null;
  const latencyMs = payload.latency_ms ?? null;
  const hasAnyTelemetry = model != null || inputTokens != null || outputTokens != null || estimatedCost != null || latencyMs != null;
  if (!hasAnyTelemetry) {
    return (
      <div
        data-testid={`trace-llm-unavailable-${rowIndex}`}
        style={{ marginTop: 6, fontSize: 11, color: "var(--tx-3)", fontStyle: "italic" }}
      >
        LLM telemetry not in this event payload
      </div>
    );
  }
  return (
    <div
      data-testid={`trace-llm-telemetry-${rowIndex}`}
      style={{ marginTop: 6, fontSize: 11, display: "flex", flexWrap: "wrap", gap: 6 }}
    >
      {model != null && (
        <span data-testid={`trace-llm-model-${rowIndex}`}>
          model: <b>{String(model)}</b>
        </span>
      )}
      {inputTokens != null && (
        <span data-testid={`trace-llm-input-tokens-${rowIndex}`}>
          in: <b>{String(inputTokens)}</b>
        </span>
      )}
      {outputTokens != null && (
        <span data-testid={`trace-llm-output-tokens-${rowIndex}`}>
          out: <b>{String(outputTokens)}</b>
        </span>
      )}
      {estimatedCost != null && (
        <span data-testid={`trace-llm-cost-${rowIndex}`}>
          cost: <b>${String(estimatedCost)}</b>
        </span>
      )}
      {latencyMs != null && (
        <span data-testid={`trace-llm-latency-${rowIndex}`}>
          latency: <b>{String(latencyMs)}ms</b>
        </span>
      )}
    </div>
  );
}

// D-104 §6: Artifact list — renders for entries with artifacts[].
// Each item carries data-artifact-href only when backend provides a path.
function TraceArtifactList({ entry, rowIndex }) {
  const artifacts = Array.isArray(entry.artifacts) ? entry.artifacts : [];
  if (artifacts.length === 0) return null;
  return (
    <div
      data-testid={`trace-artifact-list-${rowIndex}`}
      style={{ marginTop: 6, display: "flex", flexWrap: "wrap", gap: 6 }}
    >
      {artifacts.map((a) => {
        if (!a) return null;
        const key = a.key ?? a.kind ?? a.name ?? "artifact";
        const label = a.label ?? a.title ?? key;
        const path = a.path ?? null;
        return (
          <span
            key={key}
            data-testid={`trace-artifact-${rowIndex}-${key}`}
            {...(path != null ? { "data-artifact-href": path } : {})}
            style={{ fontSize: 11, display: "inline-flex", alignItems: "center", gap: 3 }}
          >
            {path != null ? (
              <a href={path} target="_blank" rel="noreferrer" style={{ color: "var(--blu)" }}>
                {label}
              </a>
            ) : (
              <span style={{ color: "var(--tx-3)" }}>{label}</span>
            )}
            {a.status != null && (
              <span
                data-testid={`trace-artifact-status-${rowIndex}-${key}`}
                data-status={a.status}
                className={`aw-badge-i ${a.status === "err" ? "err" : "outline"}`}
                style={{ fontSize: 10 }}
              >
                <span className="ldot"/>{a.status}
              </span>
            )}
          </span>
        );
      })}
    </div>
  );
}

// D-104 §7: Capability-gap card — renders when type === "capability_gap_recorded" and expanded.
function TraceGapCard({ entry, rowIndex }) {
  const payload = entry?.raw?.payload ?? entry?.raw ?? {};
  const gapId = payload.gap_id ?? null;
  const neededCapability = payload.needed_capability ?? null;
  const path = payload.path ?? null;
  return (
    <div
      data-testid={`trace-gap-card-${rowIndex}`}
      style={{ marginTop: 6, padding: "8px 10px", background: "var(--bg-inset)", borderRadius: 6, fontSize: 12 }}
    >
      <div style={{ fontWeight: 600, marginBottom: 4, color: "var(--tx-2)" }}>
        Capability gap logged — non-blocking
      </div>
      {gapId != null && (
        <div data-testid={`trace-gap-id-${rowIndex}`} style={{ marginBottom: 3 }}>
          <span style={{ color: "var(--tx-3)" }}>gap_id: </span>
          <span style={{ fontFamily: "var(--ff-mono)" }}>{String(gapId)}</span>
        </div>
      )}
      {neededCapability != null && (
        <div data-testid={`trace-gap-capability-${rowIndex}`} style={{ marginBottom: 3 }}>
          <span style={{ color: "var(--tx-3)" }}>needed: </span>
          <span>{String(neededCapability)}</span>
        </div>
      )}
      {path != null && (
        <div data-testid={`trace-gap-path-${rowIndex}`}>
          <span style={{ color: "var(--tx-3)" }}>path: </span>
          <span style={{ fontFamily: "var(--ff-mono)" }}>{String(path)}</span>
        </div>
      )}
    </div>
  );
}

export function TraceTab({ traceEntries = [] }) {
  const [filter, setFilter] = useState("");
  const [kind, setKind] = useState("all");
  const [expandedRows, setExpandedRows] = useState(() => new Set());
  const list = asArray(traceEntries);
  const filtered = list.filter((row) => {
    const type = row.type ?? "";
    if (!matchesKind(type, kind)) return false;
    if (filter) {
      const searchable = (
        (row.summary ?? row.text ?? row.description ?? row.message ?? "") + " " + type
      ).toLowerCase();
      if (!searchable.includes(filter.toLowerCase())) return false;
    }
    return true;
  });

  const toggleRow = (i) => {
    setExpandedRows((prev) => {
      const next = new Set(prev);
      if (next.has(i)) {
        next.delete(i);
      } else {
        next.add(i);
      }
      return next;
    });
  };

  return (
    <div data-testid="trace-tab">
      <div className="aw-list-toolbar">
        <span className="aw-search" style={{ flex: 1, maxWidth: 240 }}>
          <I.Search style={{ width: 11, height: 11, color: "var(--tx-3)" }}/>
          <input data-testid="trace-filter" placeholder="Filter events…"
                 value={filter} onChange={(e) => setFilter(e.target.value)}/>
        </span>
        <span style={{ display: "flex", gap: 4 }}>
          {["all", "llm", "step", "permission", "error", "code", "gap"].map((k) => (
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
          const isExpanded = expandedRows.has(i);
          const isStepFailed = type === "step_failed";
          const isLlmType = LLM_TYPES.has(type) || type.startsWith("llm");
          const isGap = type === "capability_gap_recorded";
          const hasArtifacts = Array.isArray(r.artifacts) && r.artifacts.length > 0;
          const hasRedaction = typeof r.redactionStatus === "string" && r.redactionStatus !== "";
          return (
            <div key={r.id ?? i}
                 className={"aw-trace-row " + cls}
                 data-testid={`trace-row-${i}`}
                 data-type={type}
                 data-known={known ? "1" : "0"}
                 style={{ cursor: isStepFailed || isLlmType || isGap ? "pointer" : "default" }}
                 onClick={() => {
                   if (isStepFailed || isLlmType || isGap) toggleRow(i);
                 }}>
              <span className="t">{r.timestamp ?? r.t ?? ""}</span>
              <span className="aw-trace-icon"><I.Info style={{ width: 10, height: 10 }}/></span>
              <span className="type">{type}</span>
              <span className="desc">
                {r.summary ?? r.text ?? r.description ?? r.message ?? ""}
                {!known ? <span style={{ marginLeft: 8, color: "var(--tx-4)" }}>(unknown event · diagnostic only)</span> : null}
              </span>
              {hasRedaction && (
                <span
                  className={`aw-badge-i ${r.redactionStatus === "warn" || r.redactionStatus === "redacted" ? "warn" : "ok"}`}
                  data-testid={`trace-redaction-chip-${i}`}
                  data-status={r.redactionStatus}
                  style={{ marginLeft: 6, fontSize: 10 }}
                >
                  <span className="ldot"/>{r.redactionStatus}
                </span>
              )}
              {r.redactionWarning && (
                <span
                  data-testid={`trace-redaction-warning-${i}`}
                  style={{ marginLeft: 6, fontSize: 11, color: "var(--ylw)" }}
                >
                  {r.redactionWarning}
                </span>
              )}
              {hasArtifacts && <TraceArtifactList entry={r} rowIndex={i} />}
              {isExpanded && isStepFailed && <TraceFailureDetail entry={r} rowIndex={i} />}
              {isExpanded && isLlmType && <TraceLlmTelemetry entry={r} rowIndex={i} />}
              {isExpanded && isGap && <TraceGapCard entry={r} rowIndex={i} />}
            </div>
          );
        })
      )}
    </div>
  );
}

export default { StepsTab, RecordedTab, CodeTab, TraceTab };
