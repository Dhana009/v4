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

import { log as awLog, logError as awLogError } from "./src/log.js";
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
  planning: { kind: "run", state: "Analyzing", phase: "Planning", task: "Backend is drafting a plan.", primaryLabel: null, busy: true },
  awaiting_confirmation: { kind: "decide", state: "Confirm to run", phase: "Plan review", task: "Plan is ready — review before running.", primaryLabel: "Confirm Plan", busy: false },
  plan_review: { kind: "decide", state: "Confirm to run", phase: "Plan review", task: "Plan is ready — review before running.", primaryLabel: "Confirm Plan", busy: false },
  clarification: { kind: "decide", state: "Clarification", phase: "Clarification needed", task: "Answer the question to continue.", primaryLabel: "Jump to question", busy: false },
  executing: { kind: "run", state: "Executing", phase: "Executing", task: "Backend is running steps.", primaryLabel: "Pause", busy: true },
  recovery: { kind: "block", state: "Run blocked", phase: "Recovery needed", task: "Resolve the failure to continue.", primaryLabel: "Apply LLM repair", busy: false, blocker: "needs recovery" },
  completed: { kind: "ok", state: "Completed", phase: "Completed", task: "Run finished.", primaryLabel: "Replay all", busy: false },
};

// main.jsx::toPanelState emits abbreviated keys ("await", "exec", "recover",
// "done"). Without these aliases the footer falls back to "idle" forever.
const PANEL_STATE_ALIAS = {
  await: "awaiting_confirmation",
  awaiting: "awaiting_confirmation",
  exec: "executing",
  recover: "recovery",
  done: "completed",
};

function resolveStateKey(state) {
  if (!state) return "idle";
  if (PHASE_META[state]) return state;
  const alias = PANEL_STATE_ALIAS[state];
  return alias && PHASE_META[alias] ? alias : "idle";
}

function phaseMetaFor(state, runtime) {
  const candidates = [
    runtime?.runState,
    runtime?.interactionMode,
    runtime?.storeInteractionMode,
    state,
  ];
  for (const cand of candidates) {
    if (!cand) continue;
    if (PHASE_META[cand]) return PHASE_META[cand];
    const resolved = resolveStateKey(cand);
    if (PHASE_META[resolved] && resolved !== "idle") return PHASE_META[resolved];
  }
  return PHASE_META.idle;
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
  // E3 (B7): surface the already-redacted raw response if the backend
  // event carried one. We never lift `last.raw` or any unredacted field —
  // only `raw_response_redacted` is allowed through to the UI.
  const raw =
    typeof last.raw_response_redacted === "string"
      ? last.raw_response_redacted
      : typeof last?.detail?.raw_response_redacted === "string"
        ? last.detail.raw_response_redacted
        : null;
  return {
    reason: last.rejection_reason ?? last.message ?? last.reason ?? "",
    detail: last.detail ?? null,
    raw_response_redacted: raw,
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

function loggedDispatcher(name, fn) {
  const real = safe(fn);
  return (...args) => {
    try {
      const arg0 = args[0];
      const summary = arg0 && typeof arg0 === "object"
        ? { keys: Object.keys(arg0).slice(0, 8) }
        : { arg: typeof arg0 === "string" ? arg0.slice(0, 80) : typeof arg0 };
      awLog("COMMAND", { name, ...summary });
    } catch (_) {}
    try {
      return real(...args);
    } catch (exc) {
      awLogError("COMMAND_THROW", `dispatcher ${name} threw`, { name, error: exc });
      throw exc;
    }
  };
}

function buildDispatchers(runtime) {
  return {
    onSendUserMessage: loggedDispatcher("send_user_message", runtime?.onSendUserMessage ?? runtime?.handleSendUserMessage),
    onAnswerClarification: loggedDispatcher("answer_clarification", runtime?.handleSendClarificationAnswer ?? runtime?.onSendClarificationAnswer ?? runtime?.onSendOptionSelected),
    onAcceptRecommendations: loggedDispatcher("accept_recommendations", runtime?.onAcceptRecommendations ?? runtime?.handleAcceptRecommendations),
    onAddRecommendation: loggedDispatcher("add_recommendation", runtime?.onAddRecommendation),
    onApplyPlanDiff: loggedDispatcher("apply_plan_diff", runtime?.onApplyPlanDiff ?? runtime?.handleApplyPlanDiff),
    onRejectPlanDiff: loggedDispatcher("reject_plan_diff", runtime?.onRejectPlanDiff ?? runtime?.handleRejectPlanDiff),
    onConfirmPlan: loggedDispatcher("confirm_plan", runtime?.handleConfirmPlan ?? runtime?.onConfirmPlan),
    onSendCorrection: loggedDispatcher("send_correction", runtime?.handleSendPlanCorrection ?? runtime?.onSendCorrection ?? runtime?.onSendPlanCorrection),
    onPermissionDecision: loggedDispatcher("permission_decision", runtime?.onPermissionDecision ?? runtime?.handlePermissionDecision),
    onChooseLocatorCandidate: loggedDispatcher("choose_locator_candidate", runtime?.onChooseLocatorCandidate ?? runtime?.handleChooseLocatorCandidate),
    onAskLocatorLLM: loggedDispatcher("ask_locator_llm", runtime?.onAskLocatorLLM),
    onChangeLocatorScope: loggedDispatcher("change_locator_scope", runtime?.onChangeLocatorScope),
    onImproveLocator: loggedDispatcher("improve_locator", runtime?.onImproveLocator),
    onViewCandidates: loggedDispatcher("view_candidates", runtime?.onViewCandidates),
    onApplyRecoveryLLM: loggedDispatcher("apply_recovery_llm", runtime?.handleSendRecoveryInstruction ?? runtime?.onApplyRecoveryLLM),
    onRetryRecovery: loggedDispatcher("retry_recovery", runtime?.onRetryRecovery),
    onChooseLocator: loggedDispatcher("choose_locator", runtime?.onChooseLocator),
    onPause: loggedDispatcher("pause", runtime?.onPause),
    onStop: loggedDispatcher("stop_run", runtime?.onStop ?? runtime?.handleStopRun),
    onReplayAll: loggedDispatcher("replay_all", runtime?.handleReplayAllRecordedSteps ?? runtime?.onReplayAllRecordedSteps),
    onSaveSession: loggedDispatcher("save_session", runtime?.handleSaveSnapshot ?? runtime?.onSaveSnapshot),
    onOpenCode: loggedDispatcher("open_code", runtime?.onOpenCode),
    onDownloadTrace: loggedDispatcher("download_trace", runtime?.onDownloadTrace),
    onReconnect: loggedDispatcher("reconnect", runtime?.onReconnect),
    onRepairPlan: loggedDispatcher("repair_plan", runtime?.onRepairPlan),
    onRunSelected: loggedDispatcher("run_selected", runtime?.handleRunPendingSteps ?? runtime?.onRunSelected),
    // D-101 state-cluster commands
    onResolveBlocked: loggedDispatcher("resolve_blocked", runtime?.onResolveBlocked ?? runtime?.handleResolveBlocked),
    onChangePrecondition: loggedDispatcher("change_precondition", runtime?.onChangePrecondition ?? runtime?.handleChangePrecondition),
    onNavigateToExpected: loggedDispatcher("navigate_to_expected", runtime?.onNavigateToExpected ?? runtime?.handleNavigateToExpected),
  };
}

function IDEPanel({ state, tab, runtime = {}, onTabChange, dock: dockProp, onDockChange, onResize }) {
  const [dockLocal, setDockLocal] = useState("right");
  const dock = typeof dockProp === "string" ? dockProp : dockLocal;
  const setDock = useCallback(
    (next) => {
      if (typeof onDockChange === "function") onDockChange(next);
      else setDockLocal(next);
    },
    [onDockChange]
  );
  const [collapsed, setCollapsed] = useState(false);

  const onResizeMouseDown = useCallback(
    (e) => {
      if (typeof onResize !== "function") return;
      if (dock === "top") return; // resize handle hidden for top dock
      const panelEl = e.currentTarget.parentElement; // .aw-panel
      const wrapperEl = panelEl ? panelEl.parentElement : null; // density wrapper from main.jsx
      const startX = e.clientX;
      const startW = wrapperEl ? wrapperEl.getBoundingClientRect().width : (panelEl ? panelEl.offsetWidth : 460);
      const dir = dock === "left" ? 1 : -1; // dragging right increases width when docked-left
      const onMove = (ev) => {
        const dx = (ev.clientX - startX) * dir;
        const next = Math.max(300, Math.min(window.innerWidth * 0.8, startW + dx));
        onResize({ width: next });
      };
      const onUp = () => {
        document.removeEventListener("mousemove", onMove);
        document.removeEventListener("mouseup", onUp);
      };
      document.addEventListener("mousemove", onMove);
      document.addEventListener("mouseup", onUp);
      e.preventDefault();
    },
    [dock, onResize]
  );
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
  const codeSaveResult = runtime.codeSaveResult ?? runtime.storeState?.code_save_result ?? null;
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

  // Header agent dots derive ONLY from real backend payload. Backend does
  // not yet emit agent_settings/agent_progress (BUG-S8-AGENT-001), so this
  // is almost always []. NO fabrication based on phase — header indicator
  // must not lie about agent state. (Regression fix R2.)
  const agentsSummary = useMemo(() => {
    const list =
      runtime.storeState?.agents ??
      runtime.agents ??
      null;
    if (!Array.isArray(list)) return [];
    return list
      .map((a) => {
        const s = a?.status ?? "";
        if (s === "running") return "run";
        if (s === "active" || s === "on") return "on";
        return "off";
      });
  }, [runtime]);

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
        noBrowserState={runtime.storeState?.no_browser_state ?? null}
        apiKeyRequiredState={runtime.storeState?.api_key_required_state ?? null}
        humanInputState={runtime.storeState?.human_input_required_state ?? null}
        e2ePendingState={runtime.storeState?.e2e_pending_state ?? null}
        endpointRegistry={runtime.storeState?.endpoint_registry ?? null}
        dispatchers={{
          ...dispatchers,
          // E3 (B4) — View log routes to the Trace tab. Pure client-only.
          onViewConnectionLog:
            typeof dispatchers.onViewConnectionLog === "function"
              ? dispatchers.onViewConnectionLog
              : () => setTab("trace"),
        }}
        onSeed={(text) => dispatchers.onSendUserMessage({ type: "user_message", message_text: text })}
      />
    );
  } else if (activeTab === "steps") {
    body = (
      <StepsTab
        pendingSteps={pendingSteps}
        selectedStepIds={selectedStepIds}
        activePickerStepId={runtime.activePickerStepId ?? ""}
        onAdd={runtime.addPendingStep ?? runtime.onAddPendingStep}
        onPickElement={runtime.handleAttachElement ?? runtime.onAttachElement}
        onAttachElement={(stepId) => {
          const fn = runtime.handleAttachElement ?? runtime.onAttachElement;
          if (typeof fn === "function") fn(stepId);
        }}
        onChangeIntent={runtime.updatePendingStepIntent ?? runtime.onPendingStepIntentChange}
        onChangeExpectedOutcome={
          runtime.updatePendingStepExpectedOutcome ?? runtime.onPendingStepExpectedOutcomeChange
        }
        onChangeElementTarget={
          runtime.updatePendingStepElementTarget ?? runtime.onPendingStepElementTargetChange
        }
        onToggleSelect={handleToggleStepSelect}
        onRunSelected={dispatchers.onRunSelected}
        onRunAll={dispatchers.onRunSelected}
        onReorder={runtime.onReorderPendingStep}
        onDuplicate={runtime.onDuplicatePendingStep}
        onDelete={runtime.removePendingStep ?? runtime.onDeletePendingStep}
        onResolveBlocked={dispatchers.onResolveBlocked}
        onChangePrecondition={dispatchers.onChangePrecondition}
        onNavigateToExpected={dispatchers.onNavigateToExpected}
        blocked={!!runtime.storePendingRecovery || !!runtime.storePendingPermission}
        blockedReason={
          runtime.storePendingRecovery
            ? "Run blocked while recovery is open"
            : runtime.storePendingPermission
            ? "Run blocked while permission is pending"
            : ""
        }
        onImproveLocator={dispatchers.onImproveLocator}
        onViewCandidates={dispatchers.onViewCandidates}
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
        onCopy={runtime.handleCopyCodeToClipboard ?? runtime.onCopyCode ?? runtime.handleCopyRecordedStep}
        onSave={runtime.onExportCode ?? runtime.handleExportCode}
        codeSaveResult={codeSaveResult}
      />
    );
  } else if (activeTab === "trace") {
    body = <TraceTab traceEntries={traceEntries} />;
  }

  // v4 panel renders directly inside the docked Shadow DOM mount provided by
  // main.jsx (already position:fixed, sized, right-anchored). We do NOT use
  // the v4 .aw-stage full-viewport wrapper here — it would cover the host
  // page behind the panel. The dock/collapse state is exposed on the panel
  // element via data-* hooks for CSS variants.
  return (
    <div data-testid="aw-stage" data-dock={dock} data-state={state} data-tab={activeTab}
         style={{ width: "100%", height: "100%" }}>
      <aside
        className={`aw-panel ide-panel dock-${dock}${collapsed ? " collapsed" : ""}`}
        data-testid="aw-panel"
        data-wide={dock === "top" ? "1" : "0"}
        style={{ width: "100%", height: "100%" }}
      >
        <div
          className="aw-resize"
          data-testid="aw-resize"
          onMouseDown={onResizeMouseDown}
          role="separator"
          aria-orientation="vertical"
          aria-label="Resize panel"
        />
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
                  // Sprint 7: `state` is the panelState alias (await/exec/done…)
                  // produced by toPanelState() in main.jsx, NOT the raw runState.
                  // Accept both forms so the NowStrip's primary button works
                  // regardless of which alias the parent threads in.
                  const s = String(state || "");
                  if ((s === "awaiting_confirmation" || s === "await") && plan) {
                    dispatchers.onConfirmPlan({
                      type: "confirm_plan",
                      plan_id: plan.plan_id ?? plan.id,
                      plan_version: plan.version,
                    });
                  } else if (s === "completed" || s === "done") {
                    dispatchers.onReplayAll({ type: "replay_all" });
                  } else if (s === "executing" || s === "exec") {
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
                onPickElement={runtime.handleComposerPick ?? runtime.onComposerPick}
                disabled={status === "offline" || runtime.composerDisabled === true}
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
                controlMode={runtime.storeState?.agents_control_mode ?? "read_only"}
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
