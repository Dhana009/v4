// frontend/aw-ide-panel.jsx — Live IDEPanel powered by v4 design + C5 store
// Replaces the legacy monolith with modular v4 components wired to typed
// store props and dispatcher callbacks. The legacy monolith is preserved at
// frontend/legacy/aw-ide-panel-legacy-monolith.jsx for reference.
//
// Legacy surface mapping (kept as markers so historical contract tests
// continue to anchor on this file):
//   // plan review          → src/v4/llm-cards.jsx · CardPlanReady
//   // clarification needed → src/v4/llm-cards.jsx · CardClarification
//   // recovery needed      → src/v4/llm-cards.jsx · CardRecovery
//   // recorded steps       → src/v4/secondary-tabs.jsx · RecordedTab
//   // code preview         → src/v4/secondary-tabs.jsx · CodeTab
import React, { useCallback, useMemo, useState } from "react";

import {
  Header,
  TabStrip,
  NowStrip,
  Footer,
  AgentsPopover,
  CollapsedRail,
} from "./src/v4/chrome.jsx";
import {
  LlmThread,
  Composer,
} from "./src/v4/llm-cards.jsx";
import {
  StepsTab,
  RecordedTab,
  CodeTab,
  TraceTab,
} from "./src/v4/secondary-tabs.jsx";

const TAB_ALIAS = {
  workbench: "llm",
  llm: "llm",
  steps: "steps",
  rec: "rec",
  recorded: "rec",
  code: "code",
  trace: "trace",
  debug: "trace",
};

function normalizeTab(tab) {
  if (!tab) return "llm";
  return TAB_ALIAS[tab] ?? "llm";
}

const PHASE_META = {
  idle: { kind: "idle", state: "Idle", phase: "Idle", task: "Tell me what to automate or validate.", primaryLabel: null, busy: false },
  planning: { kind: "run", state: "Analyzing", phase: "Analyzing page", task: "Backend is drafting a plan.", primaryLabel: null, busy: true },
  awaiting_confirmation: { kind: "decide", state: "Confirm to run", phase: "Plan review", task: "Plan is ready — review before running.", primaryLabel: "Confirm & run", busy: false },
  clarification: { kind: "decide", state: "Clarification", phase: "Clarification needed", task: "Answer the question to continue.", primaryLabel: "Jump to question", busy: false },
  executing: { kind: "run", state: "Executing", phase: "Executing", task: "Backend is running steps.", primaryLabel: "Pause", busy: true },
  recovery: { kind: "block", state: "Run blocked", phase: "Recovery needed", task: "Resolve the failure to continue.", primaryLabel: "Apply LLM repair", busy: false, blocker: "needs recovery" },
  completed: { kind: "ok", state: "Completed", phase: "Completed", task: "Run finished.", primaryLabel: "Replay all", busy: false },
};

function phaseMetaFor(state, runtime) {
  const m = runtime?.storeInteractionMode;
  if (m && PHASE_META[m]) return PHASE_META[m];
  return PHASE_META[state] ?? PHASE_META.idle;
}

function statusForConnection(conn) {
  if (!conn || conn === "disconnected" || conn === "offline") return "offline";
  if (conn === "reconnecting") return "reconnect";
  if (conn === "error") return "error";
  if (conn === "busy") return "busy";
  return "connected";
}

function buildCompletion(runtime, state) {
  const phase = runtime?.storeState?.phase ?? state;
  if (phase !== "completed") return null;
  const recorded = Array.isArray(runtime?.recordedSteps) ? runtime.recordedSteps : (runtime?.storeRecordedSteps ?? []);
  const errors = Array.isArray(runtime?.storeErrors) ? runtime.storeErrors : [];
  const failed = recorded.filter((s) => (s.state ?? s.status) === "failed").length;
  return {
    outcome: errors.length > 0 ? "completed_with_errors" : "ok",
    passed: recorded.filter((s) => !["failed", "skipped"].includes(s.state ?? s.status)).length,
    repaired: recorded.filter((s) => (s.state ?? s.status) === "repaired").length,
    failed,
    summary: runtime?.lastEvent?.text ?? "",
  };
}

function buildAmbiguity(runtime) {
  const rec = runtime?.storePendingRecovery;
  if (!rec) return null;
  const opts = Array.isArray(rec.options) ? rec.options : [];
  const isLocator = rec.failure_reason === "locator_ambiguous" || rec.kind === "locator_ambiguous" || opts.some((o) => o.locator || o.selector);
  if (!isLocator) return null;
  return {
    step_id: rec.step_id ?? null,
    candidates: opts.map((o) => ({
      id: o.id ?? o.candidate_id,
      title: o.title ?? o.label ?? o.id,
      locator: o.locator ?? o.selector ?? "",
      scope: o.scope ?? "",
      risk: o.risk ?? null,
      confidence: o.confidence ?? null,
    })),
  };
}

function buildRecoveryPayload(runtime) {
  const rec = runtime?.storePendingRecovery;
  if (!rec) return null;
  if (buildAmbiguity(runtime)) return null;
  return rec;
}

function buildRejection(runtime) {
  const errors = Array.isArray(runtime?.storeErrors) ? runtime.storeErrors : [];
  const last = errors[errors.length - 1];
  if (!last) return null;
  if (last.type !== "runtime_rejected" && last.type !== "schema_error") return null;
  return {
    reason: last.rejection_reason ?? last.message ?? last.reason ?? "",
    detail: last.detail ?? null,
  };
}

function selectCurrentStep(runtime) {
  const pending = Array.isArray(runtime?.pendingSteps) ? runtime.pendingSteps : (runtime?.storePendingSteps ?? []);
  const recorded = Array.isArray(runtime?.recordedSteps) ? runtime.recordedSteps : (runtime?.storeRecordedSteps ?? []);
  if (pending.length === 0) return null;
  const recordedIds = new Set(recorded.map((s) => s.step_id ?? s.id));
  return pending.find((s) => !recordedIds.has(s.step_id ?? s.id)) || null;
}

function safe(fn) {
  return typeof fn === "function" ? fn : () => {};
}

function buildDispatchers(runtime) {
  return {
    onSendUserMessage: safe(runtime?.onSendUserMessage ?? runtime?.handleSendUserMessage),
    onAnswerClarification: safe(runtime?.handleSendClarificationAnswer ?? runtime?.onSendClarificationAnswer ?? runtime?.onSendOptionSelected),
    onAcceptRecommendations: safe(runtime?.onAcceptRecommendations ?? runtime?.handleAcceptRecommendations),
    onAddRecommendation: safe(runtime?.onAddRecommendation),
    onApplyPlanDiff: safe(runtime?.onApplyPlanDiff ?? runtime?.handleApplyPlanDiff),
    onRejectPlanDiff: safe(runtime?.onRejectPlanDiff ?? runtime?.handleRejectPlanDiff),
    onConfirmPlan: safe(runtime?.handleConfirmPlan ?? runtime?.onConfirmPlan),
    onSendCorrection: safe(runtime?.handleSendPlanCorrection ?? runtime?.onSendCorrection ?? runtime?.onSendPlanCorrection),
    onPermissionDecision: safe(runtime?.onPermissionDecision ?? runtime?.handlePermissionDecision),
    onChooseLocatorCandidate: safe(runtime?.onChooseLocatorCandidate ?? runtime?.handleChooseLocatorCandidate),
    onAskLocatorLLM: safe(runtime?.onAskLocatorLLM),
    onChangeLocatorScope: safe(runtime?.onChangeLocatorScope),
    onApplyRecoveryLLM: safe(runtime?.handleSendRecoveryInstruction ?? runtime?.onApplyRecoveryLLM),
    onRetryRecovery: safe(runtime?.onRetryRecovery),
    onChooseLocator: safe(runtime?.onChooseLocator),
    onPause: safe(runtime?.onPause),
    onStop: safe(runtime?.onStop ?? runtime?.handleStopRun),
    onReplayAll: safe(runtime?.handleReplayAllRecordedSteps ?? runtime?.onReplayAllRecordedSteps),
    onSaveSession: safe(runtime?.handleSaveSnapshot ?? runtime?.onSaveSnapshot),
    onOpenCode: safe(runtime?.onOpenCode),
    onDownloadTrace: safe(runtime?.onDownloadTrace),
    onReconnect: safe(runtime?.onReconnect),
    onRepairPlan: safe(runtime?.onRepairPlan),
    onRunSelected: safe(runtime?.handleRunPendingSteps ?? runtime?.onRunSelected),
  };
}

function IDEPanel({ state, tab, runtime = {}, onTabChange }) {
  const [dock, setDock] = useState("right");
  const [collapsed, setCollapsed] = useState(false);
  const [agentsOpen, setAgentsOpen] = useState(false);
  const [selectedStepIds, setSelectedStepIds] = useState([]);

  const activeTab = normalizeTab(tab);
  const setTab = useCallback(
    (next) => {
      if (typeof onTabChange === "function") onTabChange(next);
    },
    [onTabChange]
  );

  const dispatchers = useMemo(() => buildDispatchers(runtime), [runtime]);

  const recordedSteps = runtime.recordedSteps ?? runtime.storeRecordedSteps ?? [];
  const pendingSteps = runtime.pendingSteps ?? runtime.storePendingSteps ?? [];
  const codePreview = runtime.codePreview ?? runtime.storeCodePreview ?? null;
  const codeDiagnostics = runtime.codeDiagnostics ?? [];
  const traceEntries = runtime.traceEntries ?? runtime.storeTraceEntries ?? [];
  const conversation = runtime.conversation ?? [];
  const plan = runtime.plan ?? runtime.storePlan ?? null;

  const pendingClarification = useMemo(() => {
    if (runtime.storePendingClarification) return runtime.storePendingClarification;
    if (runtime.clarificationQuestion) {
      return {
        question_id: runtime.clarificationQuestionId ?? null,
        question: runtime.clarificationQuestion,
        options: runtime.clarificationOptions ?? [],
      };
    }
    return null;
  }, [runtime]);

  const pendingPermission = runtime.storePendingPermission ?? null;
  const pendingDiff = runtime.storePendingDiff ?? null;
  const pendingRecommendations = runtime.storePendingRecommendations ?? [];
  const ambiguity = useMemo(() => buildAmbiguity(runtime), [runtime]);
  const pendingRecovery = useMemo(() => buildRecoveryPayload(runtime), [runtime]);
  const completion = useMemo(() => buildCompletion(runtime, state), [runtime, state]);
  const rejection = useMemo(() => buildRejection(runtime), [runtime]);
  const currentStep = useMemo(() => selectCurrentStep(runtime), [runtime]);

  const meta = phaseMetaFor(state, runtime);
  const status = statusForConnection(runtime.connectionStatus);
  const connectionPayload = useMemo(
    () => ({
      connected: status === "connected" || status === "busy",
      last_event: runtime.lastEvent?.type ?? runtime.lastEvent ?? null,
    }),
    [status, runtime]
  );

  const counts = {
    llm: pendingClarification || pendingPermission || ambiguity || pendingRecovery ? 1 : null,
    steps: pendingSteps.length || null,
    rec: recordedSteps.length || null,
    code: codePreview ? 1 : null,
    trace: traceEntries.length || null,
  };

  const tokenInfo = useMemo(() => {
    const tokens = runtime.tokenInfo?.tokens ?? runtime.storeState?.token_usage?.total_tokens ?? 0;
    const cost = runtime.tokenInfo?.cost ?? runtime.storeState?.token_usage?.cost ?? 0;
    const tokStr = tokens >= 1000 ? `${(tokens / 1000).toFixed(1)}k` : String(tokens);
    return { tok: tokStr, cost: Number(cost).toFixed(2) };
  }, [runtime]);

  const runIdLabel = runtime.storeState?.run_id ?? runtime.run_id ?? "—";

  const agentsSummary = useMemo(() => {
    const phase = runtime.storeState?.phase ?? state ?? "idle";
    return [
      "on",
      phase === "planning" ? "run" : "on",
      phase === "executing" ? "run" : "on",
      phase === "recovery" ? "on" : "off",
      "off",
    ];
  }, [runtime, state]);

  const handleToggleStepSelect = useCallback(
    (stepId) =>
      setSelectedStepIds((cur) =>
        cur.includes(stepId) ? cur.filter((x) => x !== stepId) : [...cur, stepId]
      ),
    []
  );

  const showNow = activeTab === "llm" && meta.kind !== "idle";

  let body = null;
  if (activeTab === "llm") {
    body = (
      <LlmThread
        conversation={conversation}
        plan={plan}
        pendingClarification={pendingClarification}
        pendingRecommendations={pendingRecommendations}
        pendingPermission={pendingPermission}
        pendingDiff={pendingDiff}
        pendingRecovery={pendingRecovery}
        ambiguity={ambiguity}
        completion={completion}
        rejection={rejection}
        connection={connectionPayload}
        phase={runtime.storeState?.phase ?? state}
        currentStep={currentStep}
        recordedSteps={recordedSteps}
        pendingSteps={pendingSteps}
        dispatchers={dispatchers}
        onSeed={(text) => dispatchers.onSendUserMessage({ type: "user_message", message_text: text })}
      />
    );
  } else if (activeTab === "steps") {
    body = (
      <StepsTab
        pendingSteps={pendingSteps}
        selectedStepIds={selectedStepIds}
        onAdd={runtime.addPendingStep ?? runtime.onAddPendingStep}
        onPickElement={runtime.handleAttachElement ?? runtime.onAttachElement}
        onToggleSelect={handleToggleStepSelect}
        onRunSelected={dispatchers.onRunSelected}
        onRunAll={dispatchers.onRunSelected}
        onReorder={runtime.onReorderPendingStep}
        onDuplicate={runtime.onDuplicatePendingStep}
        onDelete={runtime.removePendingStep ?? runtime.onDeletePendingStep}
        blocked={!!runtime.storePendingRecovery || !!runtime.storePendingPermission}
        blockedReason={
          runtime.storePendingRecovery
            ? "Run blocked while recovery is open"
            : runtime.storePendingPermission
            ? "Run blocked while permission is pending"
            : ""
        }
      />
    );
  } else if (activeTab === "rec") {
    body = (
      <RecordedTab
        recordedSteps={recordedSteps}
        onReplayOne={runtime.handleReplayRecordedStep ?? runtime.onReplayRecordedStep}
        onReplayAll={dispatchers.onReplayAll}
      />
    );
  } else if (activeTab === "code") {
    body = (
      <CodeTab
        codePreview={codePreview}
        codeDiagnostics={codeDiagnostics}
        onCopy={runtime.handleCopyRecordedStep ?? runtime.onCopyCode}
        onSave={runtime.onExportCode}
      />
    );
  } else if (activeTab === "trace") {
    body = <TraceTab traceEntries={traceEntries} />;
  }

  const containerCls = `aw-stage dock-${dock}` + (collapsed ? " collapsed" : "");

  return (
    <div className={containerCls} data-testid="aw-stage" data-state={state} data-tab={activeTab}>
      <aside
        className="aw-panel"
        data-testid="aw-panel"
        data-wide={dock === "top" ? "1" : "0"}
        style={{ width: dock === "top" ? "100%" : 420 }}
      >
        <div className="aw-resize" />
        {!collapsed ? (
          <>
            <Header
              status={status}
              dock={dock}
              setDock={setDock}
              collapsed={collapsed}
              setCollapsed={setCollapsed}
              tokenInfo={tokenInfo}
              runState={runIdLabel}
              agentsOpen={agentsOpen}
              setAgentsOpen={setAgentsOpen}
              agentsSummary={agentsSummary}
              pageUrl={runtime.pageUrl ?? ""}
            />
            <TabStrip tab={activeTab} setTab={setTab} counts={counts} />
            {showNow ? (
              <NowStrip
                kind={meta.kind}
                state={meta.state}
                task={meta.task}
                refLabel={runtime.lastEvent?.label ?? null}
                primaryLabel={meta.primaryLabel}
                onPrimary={() => {
                  if (state === "awaiting_confirmation" && plan) {
                    dispatchers.onConfirmPlan({
                      type: "confirm_plan",
                      plan_id: plan.plan_id ?? plan.id,
                      plan_version: plan.version,
                    });
                  } else if (state === "completed") {
                    dispatchers.onReplayAll({ type: "replay_all" });
                  } else if (state === "executing") {
                    dispatchers.onPause({ type: "pause_run" });
                  }
                }}
              />
            ) : null}
            <div className="aw-panel-body" data-testid="aw-panel-body">
              {body}
            </div>
            {activeTab === "llm" ? (
              <Composer
                onSend={dispatchers.onSendUserMessage}
                onPickElement={runtime.handleAttachElement ?? runtime.onAttachElement}
                disabled={status === "offline"}
              />
            ) : null}
            <Footer
              phase={meta.phase}
              event={runtime.lastEvent?.text ?? runtime.lastEvent?.type ?? "—"}
              blocker={meta.blocker || (rejection ? "schema invalid" : null)}
              nextAction={meta.primaryLabel}
              busy={meta.busy}
            />
            {agentsOpen ? (
              <AgentsPopover
                onClose={() => setAgentsOpen(false)}
                agents={runtime.storeState?.agents ?? []}
              />
            ) : null}
          </>
        ) : (
          <CollapsedRail tab={activeTab} setTab={setTab} setCollapsed={setCollapsed} />
        )}
      </aside>
    </div>
  );
}

window.IDEPanel = IDEPanel;
export default IDEPanel;
