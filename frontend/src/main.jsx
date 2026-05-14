import React, { useCallback, useEffect, useLayoutEffect, useMemo, useRef, useState } from "react";
import { createRoot } from "react-dom/client";

import "../styles.css";
import "../style-ide.css";
import "../v4.css";

import "../icons.jsx";
import "../aw-ide-panel.jsx";

// Cluster 4 layout modules — thin wiring
import { createHost, unmountHost, SHADOW_HOST_ID, SHADOW_MOUNT_ID } from "./host/host.jsx";
import { log as awLog, logError as awLogError, attachGlobalHandlers as awAttachGlobalHandlers } from "./log.js";
import { getDockMode, applyDock } from "./layout/dock-controller.js";
import { getPanelMode, applyMode } from "./layout/panel-modes.js";
import { applyCompensation, removeCompensation } from "./layout/compensation.js";
import { getStoredSize } from "./layout/resize-controller.js";

// Cluster 5 store — thin wiring (reducer used by useFrontendEventStore)
import { reducer, createInitialState } from "./store/reducer.js";
import { createDispatcher } from "./commands/dispatcher.js";

const VALID_TABS = new Set(["workbench", "steps", "code", "debug"]);

const DEFAULT_CONFIG = {
  state: "idle",
  tab: "workbench",
  panelWidth: 420,
  density: "compact",
};

// SHADOW_HOST_ID and SHADOW_MOUNT_ID imported from ./host/host.jsx
const SHADOW_STYLE_ID = "aw-shadow-style";
const SHADOW_STYLE_FLAG = "data-autoworkbench-shadow-style";
const AUTOWORKBENCH_STYLE_ID = "autoworkbench-style";
const FRONTEND_COMMAND_SCHEMA_VERSION = "autoworkbench.command.v1";

const RUN_STATE_ALIASES = {
  idle: "idle",
  planning: "planning",
  await: "awaiting_confirmation",
  awaiting_confirmation: "awaiting_confirmation",
  "awaiting confirmation": "awaiting_confirmation",
  confirm: "awaiting_confirmation",
  executing: "executing",
  exec: "executing",
  recovery: "recovery",
  recover: "recovery",
  "recovery needed": "recovery",
  failed: "recovery",
  done: "completed",
  completed: "completed",
};

const INTERACTION_MODE_ALIASES = {
  idle: "idle",
  planning: "planning",
  plan_review: "plan_review",
  "plan review": "plan_review",
  await: "plan_review",
  awaiting_confirmation: "plan_review",
  "awaiting confirmation": "plan_review",
  clarification: "clarification",
  "clarification needed": "clarification",
  recovery: "recovery",
  recover: "recovery",
  "recovery needed": "recovery",
  executing: "executing",
  exec: "executing",
  completed: "completed",
  done: "completed",
};

function normalizeRunState(value) {
  if (value == null || value === "") return null;
  const key = String(value).trim().toLowerCase().replace(/[\s-]+/g, "_");
  return RUN_STATE_ALIASES[key] || null;
}

function normalizeInteractionMode(value) {
  if (value == null || value === "") return null;
  const key = String(value).trim().toLowerCase().replace(/[\s-]+/g, "_");
  return INTERACTION_MODE_ALIASES[key] || null;
}

function toPanelState(runState) {
  switch (normalizeRunState(runState) || runState) {
    case "idle":
      return "idle";
    case "planning":
      return "planning";
    case "awaiting_confirmation":
      return "await";
    case "executing":
      return "exec";
    case "recovery":
      return "recover";
    case "completed":
      return "done";
    default:
      return "idle";
  }
}

function normalizeConfig(config = {}) {
  const runState = normalizeRunState(config.runState ?? config.state ?? DEFAULT_CONFIG.state) || "idle";
  const tab = VALID_TABS.has(config.tab) ? config.tab : DEFAULT_CONFIG.tab;
  const panelWidth = Number.isFinite(config.panelWidth) ? config.panelWidth : DEFAULT_CONFIG.panelWidth;
  const density = ["compact", "regular", "comfy"].includes(config.density)
    ? config.density
    : DEFAULT_CONFIG.density;
  const interactionMode = normalizeInteractionMode(config.interactionMode ?? config.mode ?? config.runState ?? config.state) || "idle";

  return {
    ...config,
    runState,
    interactionMode,
    panelState: toPanelState(runState),
    tab,
    panelWidth,
    density,
  };
}

function resolveMountNode(root) {
  if (root && root.nodeType === 1) return root;
  if (typeof root === "string") {
    const found = document.querySelector(root);
    if (found) return found;
  }

  let node = document.getElementById("autoworkbench-root");
  if (!node) {
    node = document.createElement("div");
    node.id = "autoworkbench-root";
    (document.body || document.documentElement).appendChild(node);
  }
  return node;
}

function ensureShadowHost(host) {
  if (!host || typeof host.attachShadow !== "function") {
    return null;
  }

  const shadowRoot = host.shadowRoot || host.attachShadow({ mode: "open" });
  let marker = shadowRoot.querySelector(`#${SHADOW_HOST_ID}`);
  if (!marker) {
    marker = document.createElement("div");
    marker.id = SHADOW_HOST_ID;
    marker.setAttribute("data-testid", "aw-shadow-host");
    marker.setAttribute("aria-hidden", "true");
    shadowRoot.appendChild(marker);
  }

  return shadowRoot;
}

function ensureShadowStyles(shadowRoot) {
  if (!shadowRoot) {
    return;
  }

  if (shadowRoot.querySelector(`[${SHADOW_STYLE_FLAG}="true"]`)) {
    return;
  }

  const sourceStyle = document.getElementById(AUTOWORKBENCH_STYLE_ID);
  if (!sourceStyle || !sourceStyle.textContent) {
    return;
  }

  const shadowStyle = sourceStyle.cloneNode(true);
  shadowStyle.id = SHADOW_STYLE_ID;
  shadowStyle.setAttribute(SHADOW_STYLE_FLAG, "true");
  shadowRoot.appendChild(shadowStyle);
}

function ensureShadowMount(shadowRoot) {
  let mount = shadowRoot.querySelector(`#${SHADOW_MOUNT_ID}`);
  if (!mount) {
    mount = document.createElement("div");
    mount.id = SHADOW_MOUNT_ID;
    mount.setAttribute("data-testid", "aw-shadow-mount");
    shadowRoot.appendChild(mount);
  }
  return mount;
}

function resolveWsUrl(config = {}) {
  const candidates = [
    config.wsUrl,
    config.ws_url,
    config.websocketUrl,
    config.websocket_url,
    config.socketUrl,
    config.socket_url,
  ];
  for (const candidate of candidates) {
    if (typeof candidate === "string" && candidate.trim()) {
      return candidate.trim();
    }
  }

  const wsPort = config.wsPort ?? config.ws_port ?? config.websocketPort ?? config.websocket_port;
  if (wsPort !== undefined && wsPort !== null && wsPort !== "") {
    const protocol = window.location?.protocol === "https:" ? "wss:" : "ws:";
    const host = typeof config.host === "string" && config.host.trim()
      ? config.host.trim()
      : "localhost";
    return `${protocol}//${host}:${String(wsPort).trim()}/ws`;
  }

  const loc = window.location;
  if (loc && (loc.protocol === "http:" || loc.protocol === "https:") && loc.hostname) {
    const isLocalHost = /^(localhost|127\.0\.0\.1|\[::1\]|::1)$/.test(loc.hostname);
    if (isLocalHost) {
      const protocol = loc.protocol === "https:" ? "wss:" : "ws:";
      return `${protocol}//${loc.host}/ws`;
    }
  }

  return "ws://localhost:8765/ws";
}

function normalizeBackendMessage(raw) {
  let parsed = raw;
  if (typeof raw === "string") {
    try {
      parsed = JSON.parse(raw);
    } catch {
      return {
        type: "status",
        payload: { text: raw },
        raw,
      };
    }
  }

  if (parsed && typeof parsed === "object") {
    const type = String(parsed.type || parsed.event || parsed.name || parsed.kind || "status");
    const payload =
      parsed.payload !== undefined
        ? parsed.payload
        : parsed.data !== undefined
          ? parsed.data
          : parsed;
    return { type, payload, raw: parsed };
  }

  return {
    type: "status",
    payload: { text: String(parsed ?? "") },
    raw: parsed,
  };
}

function createFrontendCommandId() {
  const randomUuid = globalThis?.crypto?.randomUUID;
  if (typeof randomUuid === "function") {
    return randomUuid.call(globalThis.crypto);
  }

  return `cmd-${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 10)}`;
}

function buildFrontendCommandEnvelope(commandType, payload = {}) {
  const normalizedPayload = payload && typeof payload === "object" ? { ...payload } : {};
  const envelope = {
    type: firstNonEmptyText(commandType),
    schema_version: FRONTEND_COMMAND_SCHEMA_VERSION,
    command_id: createFrontendCommandId(),
    source: "frontend",
    payload: normalizedPayload,
  };

  for (const [key, value] of Object.entries(normalizedPayload)) {
    if (Object.prototype.hasOwnProperty.call(envelope, key)) {
      continue;
    }
    envelope[key] = value;
  }

  return envelope;
}

function formatTimestamp(date = new Date()) {
  return date.toLocaleTimeString([], {
    hour12: false,
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  });
}

function extractText(value, keys = ["text", "message", "content", "summary", "title", "detail", "error", "reason", "label", "question"]) {
  if (value == null) return "";
  if (typeof value === "string") return value;
  if (typeof value === "number" || typeof value === "boolean") return String(value);
  if (Array.isArray(value)) {
    return value.map((entry) => extractText(entry, keys)).filter(Boolean).join("\n");
  }

  if (typeof value === "object") {
    for (const key of keys) {
      if (Object.prototype.hasOwnProperty.call(value, key) && value[key] != null && value[key] !== "") {
        const text = extractText(value[key], keys);
        if (text) return text;
      }
    }

    if (value.step && typeof value.step === "object") {
      const nested = extractText(value.step, keys);
      if (nested) return nested;
    }
  }

  return "";
}

function extractCodePreview(payload) {
  if (payload == null) return "";
  if (typeof payload === "string") return payload;
  if (typeof payload !== "object") return String(payload);

  const nestedSources = [
    payload.code,
    payload.snippet,
    payload.generatedCode,
    payload.script,
    payload.content,
    payload.text,
    payload.value,
  ];

  for (const source of nestedSources) {
    const text = extractText(source, ["code", "snippet", "content", "text", "value"]);
    if (text) return text;
  }

  if (Array.isArray(payload.lines)) {
    return payload.lines.map((line) => String(line)).join("\n");
  }

  if (Array.isArray(payload.codeLines)) {
    return payload.codeLines.map((line) => String(line)).join("\n");
  }

  return "";
}

function normalizePlanStep(step, index) {
  if (step == null) {
    return null;
  }

  const source = typeof step === "object" ? step : { text: step };
  const status = String(source.status || source.state || (source.done ? "done" : "")).toLowerCase();
  const text = extractText(source, ["text", "label", "title", "message", "content"]) || `Step ${index + 1}`;
  const normalizedStatus = ["done", "completed", "recorded", "passed", "active", "warn", "err", "ok"].includes(status)
    ? status
    : index === 0
      ? "active"
      : "ok";

  return {
    id: firstNonEmptyText(source.id, source.step_id, source.stepId) || `plan-step-${index + 1}`,
    step_id: firstNonEmptyText(source.step_id),
    stepId: firstNonEmptyText(source.stepId),
    kind: String(source.kind || source.type || source.action || source.name || "step"),
    text,
    label: firstNonEmptyText(source.label, text),
    title: firstNonEmptyText(source.title, text),
    cls: firstNonEmptyText(source.cls),
    expected_outcome: normalizeExpectedOutcome(source.expected_outcome ?? source.expectedOutcome, false),
    status: normalizedStatus,
    recorded: ["done", "completed", "recorded", "passed"].includes(normalizedStatus),
    completed: ["done", "completed", "recorded", "passed"].includes(normalizedStatus),
    raw: source,
  };
}

function normalizePlanPayload(payload) {
  if (payload == null) return null;

  const source = typeof payload === "object" && payload ? (payload.plan ?? payload) : payload;
  const summary =
    extractText(source, ["summary", "message", "text", "content", "title"]) ||
    (typeof source === "string" ? source : "Plan ready");

  const rawSteps = Array.isArray(source?.steps)
    ? source.steps
    : Array.isArray(source?.actions)
      ? source.actions
      : Array.isArray(source?.items)
        ? source.items
        : Array.isArray(payload?.steps)
          ? payload.steps
          : [];

  const steps = rawSteps.map(normalizePlanStep).filter(Boolean);

  return {
    summary,
    steps,
    raw: source,
  };
}

let pendingStepCounter = 0;
let pendingCommandSequence = 0;

function createPendingStep(intent = "", elementInfo = null, recorded = false) {
  pendingStepCounter += 1;
  return {
    id: `pending-step-${Date.now().toString(36)}-${pendingStepCounter}`,
    intent,
    element_info: elementInfo,
    expected_outcome: null,
    recorded,
    status: "draft",
  };
}

function normalizePendingCommandStatus(status) {
  const value = firstNonEmptyText(status).toLowerCase();
  if (["pending", "acknowledged", "rejected"].includes(value)) {
    return value;
  }
  return "pending";
}

function normalizePendingCommand(command, index = 0) {
  if (!command || typeof command !== "object") {
    return null;
  }

  const commandId = firstNonEmptyText(command.command_id, command.commandId, command.id);
  const commandType = firstNonEmptyText(command.command_type, command.commandType, command.type);
  if (!commandId || !commandType) {
    return null;
  }

  const createdSequence = Number(command.created_sequence ?? command.createdSequence);

  return {
    ...command,
    command_id: commandId,
    command_type: commandType,
    created_at: firstNonEmptyText(command.created_at, command.createdAt) || new Date().toISOString(),
    created_sequence: Number.isFinite(createdSequence) ? createdSequence : index + 1,
    status: normalizePendingCommandStatus(command.status),
    source: firstNonEmptyText(command.source) || "frontend",
  };
}

function normalizePendingCommands(commands) {
  if (Array.isArray(commands) && commands.length > 0) {
    return commands.map((command, index) => normalizePendingCommand(command, index)).filter(Boolean);
  }

  return [];
}

function normalizeCodeDiagnostics(diagnostics) {
  if (!Array.isArray(diagnostics) || diagnostics.length === 0) {
    return [];
  }

  return diagnostics.map((entry) => (entry && typeof entry === "object" ? { ...entry } : entry)).filter((entry) => entry != null);
}

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
  const text = firstNonEmptyText(value).toLowerCase();
  return /(^|\b)(click|tap|press|open)\b/.test(text);
}

function normalizeExpectedOutcome(expectedOutcome, required = false) {
  if (!expectedOutcome || typeof expectedOutcome !== "object") {
    return null;
  }

  const type = firstNonEmptyText(expectedOutcome.type)
    .toLowerCase()
    .replace(/[\s-]+/g, "_");
  if (!type || !EXPECTED_OUTCOME_TYPES.includes(type)) {
    return null;
  }

  const description = firstRawText(expectedOutcome.description);
  return {
    type,
    ...(description ? { description } : {}),
    source: "user",
    required: Boolean(required || expectedOutcome.required === true),
  };
}

function resolveSelectedCandidateIndex(value, candidateCount) {
  const index = Number(value);
  if (Number.isInteger(index) && index >= 0 && index < candidateCount) {
    return index;
  }
  return candidateCount > 0 ? 0 : null;
}

function normalizeElementCandidate(candidate, fallbackLevel = 0) {
  if (!candidate || typeof candidate !== "object") {
    return null;
  }

  const attributes = candidate.attributes && typeof candidate.attributes === "object" ? candidate.attributes : {};
  let classValue = firstNonEmptyText(candidate.className, candidate.class, attributes.class, attributes.className);
  if (!classValue && Array.isArray(candidate.classes)) {
    classValue = candidate.classes
      .filter(Boolean)
      .map((value) => String(value).trim())
      .filter(Boolean)
      .join(" ");
  }

  const textValue = firstNonEmptyText(
    candidate.cleanText,
    candidate.clean_text,
    candidate.text,
    candidate.innerText,
    candidate.content,
    candidate.title,
    candidate.label,
    candidate.value
  );
  const semanticTypeValue = firstNonEmptyText(
    candidate.semanticType,
    candidate.semantic_type,
    candidate.category
  );
  const roleValue = firstNonEmptyText(candidate.role, attributes.role);
  const ariaLabelValue = firstNonEmptyText(candidate.ariaLabel, candidate.aria_label, attributes["aria-label"]);

  return {
    ...candidate,
    level: Number.isFinite(Number(candidate.level)) ? Number(candidate.level) : fallbackLevel,
    tag: firstNonEmptyText(candidate.tag, candidate.tagName, candidate.nodeName).toLowerCase(),
    role: roleValue,
    ariaLabel: ariaLabelValue,
    text: textValue,
    cleanText: textValue,
    clean_text: textValue,
    id: firstNonEmptyText(candidate.id, attributes.id),
    className: classValue,
    class: classValue,
    selectorHint: firstNonEmptyText(candidate.selectorHint, candidate.selector_hint),
    selector_hint: firstNonEmptyText(candidate.selector_hint, candidate.selectorHint),
    locatorHint: firstNonEmptyText(candidate.locatorHint, candidate.locator_hint),
    locator_hint: firstNonEmptyText(candidate.locator_hint, candidate.locatorHint),
    semanticType: semanticTypeValue,
    semantic_type: semanticTypeValue,
    reason: firstNonEmptyText(candidate.reason),
    category: firstNonEmptyText(candidate.category),
    attributes,
  };
}

function formatExpectedOutcomeSummary(expectedOutcome) {
  if (!expectedOutcome || typeof expectedOutcome !== "object") {
    return "";
  }

  const type = firstNonEmptyText(expectedOutcome.type).toLowerCase().replace(/[\s-]+/g, "_");
  if (!type) {
    return "";
  }

  const description = firstRawText(expectedOutcome.description);
  const summary = description ? `${type} · ${description}` : type;
  return summary.length > 80 ? `${summary.slice(0, 79)}…` : summary;
}

function resolvePendingStepStatus(step) {
  if (!step || typeof step !== "object") {
    return "draft";
  }

  if (step.recorded === true) {
    return "recorded";
  }

  const intent = firstNonEmptyText(step.intent, step.text, step.label);
  if (!intent) {
    return "draft";
  }

  const expectedOutcome = normalizeExpectedOutcome(step.expected_outcome ?? step.expectedOutcome, isClickLikeIntent(intent));
  if (isClickLikeIntent(intent) && (!expectedOutcome || !expectedOutcome.type)) {
    return "needs_outcome";
  }

  return "ready";
}

function isPendingStepReady(step) {
  return resolvePendingStepStatus(step) === "ready";
}

function firstNonEmptyText(...values) {
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

const KNOWN_TRACE_EVENT_TYPES = new Set([
  "browser_ready",
  "status",
  "llm_thinking",
  "plan_ready",
  "clarification_needed",
  "recovery_needed",
  "error",
  "runtime_rejected",
  "llm_result",
  "step_recorded",
  "code_update",
  "export_code_result",
  "replay_started",
  "replay_result",
  "capability_gap_recorded",
  "trace_summary",
  "save_snapshot",
  "saved_snapshot",
  "snapshot_saved",
  "element_attached",
  "command_accepted",
  "command_rejected",
]);

const TRACE_ARTIFACT_LABELS = {
  manifest: "manifest.json",
  test_result: "test-result.json",
  summary: "summary.md",
  events: "events.ndjson",
  commands: "commands.json",
  rejections: "rejections.json",
  redaction_report: "redaction-report.json",
};

function normalizeTraceArtifact(artifact, index = 0) {
  if (artifact == null) {
    return null;
  }

  const source = typeof artifact === "object" ? artifact : { path: artifact };
  const kind = firstNonEmptyText(source.key, source.kind, source.name, source.type, `artifact-${index + 1}`)
    .toLowerCase()
    .replace(/[\s-]+/g, "_");
  const label = firstNonEmptyText(
    source.label,
    source.title,
    TRACE_ARTIFACT_LABELS[kind],
    kind.replace(/_/g, "-"),
    kind
  );
  const path = firstNonEmptyText(source.path, source.file_path, source.filePath, source.href, source.url, source.value);
  const status = firstNonEmptyText(source.status, source.state, source.redaction_status, source.redactionStatus)
    .toLowerCase()
    .replace(/[\s-]+/g, "_");
  const note = firstNonEmptyText(source.note, source.summary, source.message, source.warning, source.redaction_warning, source.redactionWarning);

  return {
    key: kind,
    label,
    ...(path ? { path } : {}),
    ...(status ? { status } : {}),
    ...(note ? { note } : {}),
  };
}

function normalizeTraceArtifacts(artifacts) {
  if (Array.isArray(artifacts)) {
    return artifacts.map((artifact, index) => normalizeTraceArtifact(artifact, index)).filter(Boolean);
  }

  if (artifacts && typeof artifacts === "object") {
    return Object.entries(artifacts)
      .map(([key, value], index) => {
        if (value && typeof value === "object") {
          return normalizeTraceArtifact({ key, ...value }, index);
        }
        return normalizeTraceArtifact({ key, value, path: value }, index);
      })
      .filter(Boolean);
  }

  return [];
}

function normalizeTraceEntry(entry, index = 0) {
  if (!entry || typeof entry !== "object") {
    return null;
  }

  const payload = entry.payload && typeof entry.payload === "object" ? entry.payload : {};
  const raw = entry.raw && typeof entry.raw === "object" ? entry.raw : entry;
  const type = firstNonEmptyText(entry.type, entry.event, entry.name, entry.kind, payload.type, raw.type, "trace")
    .toLowerCase()
    .replace(/[\s-]+/g, "_");
  const category = firstNonEmptyText(entry.category, entry.source_type, entry.sourceType, entry.kind, payload.category, payload.kind, raw.category, raw.kind);
  const timestamp = firstNonEmptyText(
    entry.timestamp,
    entry.created_at,
    entry.createdAt,
    payload.timestamp,
    payload.created_at,
    payload.createdAt,
    raw.timestamp,
    raw.created_at,
    raw.createdAt
  );
  const source = firstNonEmptyText(entry.source, entry.owner, entry.origin, payload.source, payload.owner, payload.origin, payload.actor, raw.source, raw.owner);
  const summary = firstNonEmptyText(
    entry.summary,
    payload.summary,
    payload.message,
    payload.text,
    payload.detail,
    raw.summary,
    raw.message,
    raw.text,
    raw.detail,
    extractText(payload),
    extractText(raw),
    type.replace(/_/g, " ")
  );
  const evidenceRef = firstNonEmptyText(
    entry.evidenceRef,
    entry.evidence_ref,
    payload.evidence_ref,
    payload.evidenceRef,
    payload.artifact_path,
    payload.artifactPath,
    payload.path,
    raw.evidence_ref,
    raw.evidenceRef,
    raw.artifact_path,
    raw.artifactPath,
    raw.path
  );
  const redactionStatus = firstNonEmptyText(
    entry.redactionStatus,
    entry.redaction_status,
    payload.redaction_status,
    payload.redactionStatus,
    payload.redaction_report,
    payload.redactionReport,
    raw.redaction_status,
    raw.redactionStatus,
    raw.redaction_report,
    raw.redactionReport
  );
  const redactionWarning = firstNonEmptyText(
    entry.redactionWarning,
    entry.redaction_warning,
    payload.redaction_warning,
    payload.redactionWarning,
    payload.redaction_message,
    payload.redactionMessage,
    raw.redaction_warning,
    raw.redactionWarning
  );
  const rejectionReason = type === "runtime_rejected"
    ? firstNonEmptyText(
        entry.rejectionReason,
        entry.rejection_reason,
        payload.rejection_reason,
        payload.rejectionReason,
        payload.message,
        payload.detail,
        raw.rejection_reason,
        raw.rejectionReason,
        raw.message,
        raw.detail,
        summary
      )
    : "";
  const currentState = type === "runtime_rejected"
    ? entry.currentState ?? entry.current_state ?? payload.current_state ?? payload.currentState ?? raw.current_state ?? raw.currentState ?? null
    : null;
  const currentStateLabel = currentState && typeof currentState === "object"
    ? [
        firstNonEmptyText(currentState.phase, currentState.state),
        firstNonEmptyText(currentState.run_id, currentState.runId, currentState.plan_id, currentState.planId),
      ]
        .filter(Boolean)
        .join(" · ")
    : "";
  const artifacts = normalizeTraceArtifacts(entry.artifacts ?? payload.artifacts ?? payload.artifact_bundle ?? payload.artifactBundle ?? raw.artifacts);
  const requiresEvidence = Boolean(
    evidenceRef ||
      redactionStatus ||
      redactionWarning ||
      rejectionReason ||
      currentStateLabel ||
      artifacts.length > 0 ||
      ["runtime_rejected", "replay_result", "step_recorded", "code_update", "capability_gap_recorded", "trace_summary"].includes(type)
  );
  const knownType = KNOWN_TRACE_EVENT_TYPES.has(type);
  const diagnostic = !knownType
    ? `Unknown trace event: ${type}`
    : requiresEvidence && !evidenceRef
      ? "Evidence ref missing"
      : "";
  const severity = !knownType
    ? "warn"
    : rejectionReason || redactionWarning
      ? "err"
      : diagnostic
        ? "warn"
        : "ok";

  return {
    id: firstNonEmptyText(entry.id, raw.id, payload.id, payload.trace_id, payload.traceId, `${type}-${index + 1}`),
    type,
    category,
    timestamp,
    source,
    summary,
    evidenceRef,
    redactionStatus,
    redactionWarning,
    rejectionReason,
    currentState,
    currentStateLabel,
    artifacts,
    diagnostic,
    severity,
    raw,
  };
}

function normalizeTraceEntries(entries) {
  if (!Array.isArray(entries) || entries.length === 0) {
    return [];
  }

  return entries.map((entry, index) => normalizeTraceEntry(entry, index)).filter(Boolean);
}

function mergeTraceEntryList(current, nextEntry, limit = 120) {
  if (!nextEntry) {
    return Array.isArray(current) ? current : [];
  }

  const nextId = firstNonEmptyText(nextEntry.id);
  const next = Array.isArray(current) ? current.filter((entry) => firstNonEmptyText(entry?.id) !== nextId) : [];
  next.unshift(nextEntry);
  return next.slice(0, limit);
}

function buildTraceEntryFromBackendMessage(message) {
  return normalizeTraceEntry(message);
}

function collectStepReferenceValues(...sources) {
  const values = [];
  const seen = new Set();
  const push = (value) => {
    const text = firstNonEmptyText(value);
    if (!text || seen.has(text)) {
      return;
    }
    seen.add(text);
    values.push(text);
  };

  for (const source of sources) {
    if (source == null) {
      continue;
    }

    if (Array.isArray(source)) {
      source.forEach(push);
      continue;
    }

    if (typeof source === "object") {
      push(source.step_id);
      push(source.stepId);
      push(source.id);
      push(source.step?.id);
      push(source.step?.step_id);
      push(source.step?.stepId);
      continue;
    }

    push(source);
  }

  return values;
}

function normalizeMatchText(value) {
  return firstNonEmptyText(value).replace(/\s+/g, " ").trim().toLowerCase();
}

function isTechnicalRecordedLabel(value) {
  const text = firstNonEmptyText(value);
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

function pickFriendlyText(...values) {
  for (const value of values) {
    const text = firstNonEmptyText(value);
    if (text && !isTechnicalRecordedLabel(text)) {
      return text;
    }
  }
  return firstNonEmptyText(...values);
}

function describeElementSubject(info) {
  if (!info || typeof info !== "object") {
    return "";
  }

  const friendlyText = pickFriendlyText(info.text, info.innerText, info.content, info.title, info.label, info.value, info.name);
  if (friendlyText) {
    return friendlyText;
  }

  const tag = firstNonEmptyText(info.tag, info.tagName, info.nodeName).toLowerCase();
  switch (tag) {
    case "h1":
    case "h2":
    case "h3":
    case "h4":
    case "h5":
    case "h6":
      return "heading";
    case "a":
      return "link";
    case "button":
      return "button";
    case "input":
    case "textarea":
    case "select":
      return "input";
    case "img":
      return "image";
    case "li":
      return "list item";
    case "form":
      return "form";
    default:
      return tag || "";
  }
}

function normalizeElementInfo(info) {
  if (!info || typeof info !== "object") {
    return null;
  }

  const attributes = info.attributes && typeof info.attributes === "object" ? info.attributes : {};
  const rawCandidates = Array.isArray(info.candidates) ? info.candidates : [];
  const candidates = rawCandidates.map((candidate, index) => normalizeElementCandidate(candidate, index)).filter(Boolean);
  const selectedIndex = resolveSelectedCandidateIndex(info.selected_candidate_index ?? info.selectedCandidateIndex, candidates.length);
  const selectedCandidate = selectedIndex === null ? normalizeElementCandidate(info, 0) : candidates[selectedIndex] || normalizeElementCandidate(info, 0);
  const selectedAttributes = selectedCandidate && selectedCandidate.attributes && typeof selectedCandidate.attributes === "object" ? selectedCandidate.attributes : attributes;
  let classValue = firstNonEmptyText(
    selectedCandidate?.className,
    selectedCandidate?.class,
    info.class,
    info.className,
    selectedAttributes.class,
    selectedAttributes.className
  );
  if (!classValue && Array.isArray(info.classes)) {
    classValue = info.classes.filter(Boolean).map((value) => String(value).trim()).filter(Boolean).join(" ");
  }

  const selectedText = firstNonEmptyText(
    selectedCandidate?.cleanText,
    selectedCandidate?.clean_text,
    selectedCandidate?.text,
    info.clean_text,
    info.cleanText,
    info.text,
    info.innerText,
    info.content,
    info.title,
    info.value,
    info.label
  );
  const selectedSemanticType = firstNonEmptyText(
    selectedCandidate?.semanticType,
    selectedCandidate?.semantic_type,
    selectedCandidate?.category,
    info.semantic_type,
    info.semanticType
  );
  const selectedSelectorHint = firstNonEmptyText(
    selectedCandidate?.selectorHint,
    selectedCandidate?.selector_hint,
    info.selector_hint,
    info.selectorHint
  );
  const selectedLocatorHint = firstNonEmptyText(
    selectedCandidate?.locatorHint,
    selectedCandidate?.locator_hint,
    info.locator_hint,
    info.locatorHint
  );
  const selectedRole = firstNonEmptyText(selectedCandidate?.role, info.role, selectedAttributes.role);
  const selectedAriaLabel = firstNonEmptyText(
    selectedCandidate?.ariaLabel,
    selectedCandidate?.aria_label,
    info.ariaLabel,
    info.aria_label,
    selectedAttributes["aria-label"]
  );

  return {
    ...info,
    tag: firstNonEmptyText(selectedCandidate?.tag, info.tag, info.tagName, info.nodeName).toLowerCase() || "element",
    text: selectedText,
    clean_text: selectedText,
    cleanText: selectedText,
    id: firstNonEmptyText(selectedCandidate?.id, info.id, selectedAttributes.id),
    role: selectedRole,
    ariaLabel: selectedAriaLabel,
    aria_label: selectedAriaLabel,
    semantic_type: selectedSemanticType,
    semanticType: selectedSemanticType,
    selector_hint: selectedSelectorHint,
    selectorHint: selectedSelectorHint,
    locator_hint: selectedLocatorHint,
    locatorHint: selectedLocatorHint,
    selected_candidate_index: selectedIndex,
    candidates,
    className: classValue,
    class: classValue,
    attributes: selectedAttributes,
  };
}

function selectElementInfoCandidate(info, selectedCandidateIndex) {
  if (!info || typeof info !== "object") {
    return info;
  }

  const candidates = Array.isArray(info.candidates) ? info.candidates : [];
  if (!candidates.length) {
    return info;
  }

  const selectedIndex = resolveSelectedCandidateIndex(selectedCandidateIndex, candidates.length);
  if (selectedIndex === null) {
    return info;
  }

  const selectedCandidate = normalizeElementCandidate(candidates[selectedIndex], selectedIndex);
  if (!selectedCandidate) {
    return info;
  }

  const attributes = selectedCandidate.attributes && typeof selectedCandidate.attributes === "object" ? selectedCandidate.attributes : {};
  const selectedText = firstNonEmptyText(selectedCandidate.cleanText, selectedCandidate.text, info.text, info.clean_text, info.cleanText);
  const selectedSemanticType = firstNonEmptyText(selectedCandidate.semanticType, selectedCandidate.semantic_type, selectedCandidate.category, info.semantic_type, info.semanticType);
  const selectedSelectorHint = firstNonEmptyText(selectedCandidate.selectorHint, selectedCandidate.selector_hint, info.selector_hint, info.selectorHint);
  const selectedLocatorHint = firstNonEmptyText(selectedCandidate.locatorHint, selectedCandidate.locator_hint, info.locator_hint, info.locatorHint);
  const selectedRole = firstNonEmptyText(selectedCandidate.role, info.role, attributes.role);
  const selectedAriaLabel = firstNonEmptyText(selectedCandidate.ariaLabel, selectedCandidate.aria_label, info.ariaLabel, info.aria_label, attributes["aria-label"]);
  const classValue = firstNonEmptyText(selectedCandidate.className, selectedCandidate.class, info.class, info.className, attributes.class, attributes.className);

  return {
    ...info,
    ...selectedCandidate,
    text: selectedText,
    clean_text: selectedText,
    cleanText: selectedText,
    semantic_type: selectedSemanticType,
    semanticType: selectedSemanticType,
    selector_hint: selectedSelectorHint,
    selectorHint: selectedSelectorHint,
    locator_hint: selectedLocatorHint,
    locatorHint: selectedLocatorHint,
    role: selectedRole,
    ariaLabel: selectedAriaLabel,
    aria_label: selectedAriaLabel,
    id: firstNonEmptyText(selectedCandidate.id, info.id, attributes.id),
    class: classValue,
    className: classValue,
    attributes,
    selected_candidate_index: selectedIndex,
    candidates,
  };
}

function normalizePickedElementMessage(message) {
  const payload = message?.payload && typeof message.payload === "object" ? message.payload : message;
  const stepIds = collectStepReferenceValues(payload, message);

  const rawElementInfo =
    payload?.element_info ??
    payload?.elementInfo ??
    payload?.element ??
    payload?.info ??
    payload?.descriptor ??
    payload?.payload ??
    payload;

  return {
    stepId: stepIds[0] || "",
    stepIds,
    elementInfo: normalizeElementInfo(rawElementInfo),
  };
}

function normalizePendingStep(step) {
  if (!step || typeof step !== "object") {
    return createPendingStep(typeof step === "string" ? step : "");
  }

  const nextIntent =
    typeof step.intent === "string"
      ? step.intent
      : typeof step.text === "string"
        ? step.text
        : typeof step.label === "string"
          ? step.label
          : "";
  const normalizedStep = {
    ...step,
    id: typeof step.id === "string" && step.id.trim() ? step.id : createPendingStep().id,
    intent: nextIntent,
    element_info: step.element_info ?? step.elementInfo ?? null,
    elementInfo: step.elementInfo ?? step.element_info ?? null,
    expected_outcome: normalizeExpectedOutcome(step.expected_outcome ?? step.expectedOutcome, isClickLikeIntent(nextIntent)),
    recorded: step.recorded === true,
  };
  const status = typeof step.status === "string" ? step.status.trim().toLowerCase() : "";

  return {
    ...normalizedStep,
    status:
      ["recorded", "done", "completed", "passed", "failed", "skipped"].includes(status)
        ? status
        : resolvePendingStepStatus(normalizedStep),
  };
}

function normalizePendingSteps(steps) {
  if (Array.isArray(steps) && steps.length > 0) {
    return steps.map(normalizePendingStep);
  }

  return [createPendingStep("")];
}

function resolveFiniteNumber(value) {
  const number = Number(value);
  return Number.isFinite(number) ? number : null;
}

function inferActionKindFromText(...values) {
  const text = values.map((value) => firstNonEmptyText(value)).filter(Boolean).join(" ").toLowerCase();
  if (!text) return "step";

  if (/(^|\b)(click|tap|press|select|choose|open)\b/.test(text)) return "click";
  if (/(^|\b)(fill|type|enter|input|paste|set)\b/.test(text)) return "fill";
  if (/(^|\b)(assert|verify|check|expect|confirm|validate)\b/.test(text)) return "assert";
  if (/(^|\b)(navigate|goto|go to|go back|back|forward|reload|refresh)\b/.test(text)) return "navigate";
  if (/(^|\b)(hover)\b/.test(text)) return "hover";
  return "step";
}

function stripActionPrefix(text, action) {
  const value = firstNonEmptyText(text);
  if (!value) return "";

  const map = {
    click: /^(click|tap|press|select|choose|open)\s+/i,
    fill: /^(fill|type|enter|input|paste|set)\s+/i,
    assert: /^(assert|verify|check|expect|confirm|validate)\s+/i,
    navigate: /^(navigate|go to|goto|go back|back|forward|reload|refresh)\s+/i,
    hover: /^(hover)\s+/i,
  };

  const stripped = value.replace(map[action] || /^recorded\s+/i, "").trim();
  return stripped || value;
}

function summarizeElementName(info) {
  if (!info || typeof info !== "object") {
    return "";
  }

  return pickFriendlyText(
    info.text,
    info.label,
    info.title,
    info.name,
    describeElementSubject(info),
    info.id ? `#${info.id}` : "",
    info.tag
  );
}

function summarizeLocator(source, matchedStep) {
  const raw = firstNonEmptyText(
    source?.locator,
    source?.selector,
    source?.css,
    source?.xpath,
    source?.path,
    source?.target,
    matchedStep?.locator,
    matchedStep?.element_info?.locator
  );
  if (raw) return raw;

  const elementInfo = matchedStep?.element_info;
  if (!elementInfo) return "";
  if (elementInfo.id) return `#${elementInfo.id}`;
  if (elementInfo.className) {
    const classes = elementInfo.className.split(/\s+/).filter(Boolean);
    if (classes.length) {
      return `.${classes.join(".")}`;
    }
  }
  if (elementInfo.tag) return elementInfo.tag;
  return "";
}

function buildRecordedDisplayTitle(action, elementName, stepNumber) {
  const target = stripActionPrefix(elementName, action);
  const fallback = Number.isFinite(stepNumber) && stepNumber > 0 ? `Step ${stepNumber}` : "Recorded step";

  switch (action) {
    case "click":
      return target ? `Clicked ${target}` : fallback;
    case "fill":
      return target ? `Filled ${target}` : fallback;
    case "assert":
      return target ? `Asserted ${target}` : fallback;
    case "navigate":
      return target ? `Navigated ${target}` : "Navigated";
    case "hover":
      return target ? `Hovered ${target}` : fallback;
    case "step":
    default:
      return target ? `Recorded ${target}` : fallback;
  }
}

function normalizeRecordedStep(step, index) {
  if (!step || typeof step !== "object") {
    const rawText = firstNonEmptyText(step) || `Recorded step ${index + 1}`;
    const action = inferActionKindFromText(rawText);
    const target = stripActionPrefix(rawText, action);
    return {
      id: `recorded-step-${Date.now().toString(36)}-${index + 1}`,
      step_number: index + 1,
      action,
      element_name: target || rawText,
      locator: "",
      generated_line: "",
      status: "recorded",
      display_title: buildRecordedDisplayTitle(action, target || rawText, index + 1),
      action_label: action,
      target_label: target || rawText,
    };
  }

  const action = inferActionKindFromText(
    step.action,
    step.action_label,
    step.kind,
    step.type,
    step.intent,
    step.display_title,
    step.title,
    step.element_name,
    step.locator
  );
  const stepNumberValue = resolveFiniteNumber(step.step_number ?? step.stepNumber ?? step.number ?? step.index);
  const stepNumber = Number.isFinite(stepNumberValue) ? (stepNumberValue > 0 ? stepNumberValue : stepNumberValue + 1) : index + 1;
  const matchedElementInfo = step.element_info && typeof step.element_info === "object" ? step.element_info : null;
  const elementName = stripActionPrefix(
    pickFriendlyText(
      step.element_name,
      step.elementName,
      step.target_name,
      step.targetName,
      step.target,
      step.name,
      step.label,
      step.intent,
      summarizeElementName(matchedElementInfo),
      describeElementSubject(matchedElementInfo)
    ),
    action
  );
  const status = firstNonEmptyText(step.status, step.result, step.state, step.outcome).toLowerCase();
  const normalizedStatus = status === "passed" || status === "failed" ? status : "recorded";
  const displayTitle =
    pickFriendlyText(step.display_title, step.displayTitle, step.title, step.label, buildRecordedDisplayTitle(action, elementName, stepNumber)) ||
    buildRecordedDisplayTitle(action, elementName, stepNumber);

  return {
    ...step,
    id: firstNonEmptyText(step.id, step.step_id, step.stepId) || `recorded-step-${Date.now().toString(36)}-${index + 1}`,
    step_number: stepNumber,
    action,
    element_name: elementName || firstNonEmptyText(step.element_name, step.target, step.label) || `Step ${stepNumber}`,
    locator: firstNonEmptyText(step.locator, step.selector, step.xpath, step.css, step.path) || "",
    generated_line: firstNonEmptyText(step.generated_line, step.generatedLine, step.code_line, step.codeLine, step.line, step.code, step.snippet) || "",
    expected_outcome:
      step.expected_outcome ??
      step.expectedOutcome ??
      (step.raw && typeof step.raw === "object"
        ? step.raw.expected_outcome ?? step.raw.expectedOutcome
        : null),
    status: normalizedStatus,
    display_title: displayTitle,
    action_label: action,
    target_label: elementName || firstNonEmptyText(step.target, step.label) || "",
  };
}

function sortRecordedSteps(steps) {
  if (!Array.isArray(steps) || steps.length === 0) {
    return [];
  }

  const nextSteps = [...steps];
  nextSteps.sort((left, right) => {
    const leftNumber = resolveFiniteNumber(left?.step_number ?? left?.stepNumber ?? left?.number ?? left?.index);
    const rightNumber = resolveFiniteNumber(right?.step_number ?? right?.stepNumber ?? right?.number ?? right?.index);
    const leftSortNumber = Number.isFinite(leftNumber) ? leftNumber : Number.POSITIVE_INFINITY;
    const rightSortNumber = Number.isFinite(rightNumber) ? rightNumber : Number.POSITIVE_INFINITY;
    if (leftSortNumber !== rightSortNumber) {
      return leftSortNumber - rightSortNumber;
    }

    const leftId = firstNonEmptyText(left?.id, left?.step_id, left?.stepId);
    const rightId = firstNonEmptyText(right?.id, right?.step_id, right?.stepId);
    if (leftId && rightId && leftId !== rightId) {
      return leftId.localeCompare(rightId);
    }
    if (leftId && !rightId) {
      return -1;
    }
    if (!leftId && rightId) {
      return 1;
    }
    return 0;
  });
  return nextSteps;
}

function normalizeRecordedSteps(steps) {
  if (!Array.isArray(steps) || steps.length === 0) {
    return [];
  }

  return sortRecordedSteps(steps.map(normalizeRecordedStep).filter(Boolean));
}

function findPendingStepMatch(steps, stepIds, recordedStepNumber, recordedStepIndex) {
  if (!Array.isArray(steps) || steps.length === 0) {
    return { index: -1, step: null, reason: "empty" };
  }

  const candidateIds = collectStepReferenceValues(stepIds);
  if (candidateIds.length > 0) {
    const index = steps.findIndex((step) =>
      candidateIds.some((candidateId) => {
        const stepCandidateIds = collectStepReferenceValues(step);
        return stepCandidateIds.includes(candidateId);
      })
    );
    if (index !== -1) {
      return { index, step: steps[index], reason: "id" };
    }
  }

  if (Number.isFinite(recordedStepNumber) && recordedStepNumber > 0) {
    const index = recordedStepNumber - 1;
    if (index >= 0 && index < steps.length) {
      return { index, step: steps[index], reason: "number" };
    }
  }

  if (Number.isFinite(recordedStepIndex) && recordedStepIndex >= 0 && recordedStepIndex < steps.length) {
    return { index: recordedStepIndex, step: steps[recordedStepIndex], reason: "index" };
  }

  if (steps.length === 1) {
    return { index: 0, step: steps[0], reason: "single" };
  }

  return { index: -1, step: null, reason: "unmatched" };
}

function buildRecordedStepFromPayload(payload, matchedStep, matchIndex, recordedStepId, recordedStepNumber, recordedStepIndex) {
  const source = payload && typeof payload === "object" ? payload : {};
  const action = inferActionKindFromText(
    source.action,
    source.step_action,
    source.kind,
    source.type,
    source.intent,
    matchedStep?.intent,
    source.generated_line,
    source.locator,
    matchedStep?.element_info?.text
  );
  const stepNumber = Number.isFinite(recordedStepNumber)
    ? recordedStepNumber
    : Number.isFinite(recordedStepIndex)
      ? recordedStepIndex + 1
      : matchIndex >= 0
        ? matchIndex + 1
        : resolveFiniteNumber(source.step_number ?? source.stepNumber ?? source.number ?? source.index) ?? null;
  const matchedElementName = matchedStep?.element_info ? summarizeElementName(matchedStep.element_info) : "";
  const elementName = stripActionPrefix(
    pickFriendlyText(
      source.element_name,
      source.elementName,
      source.target_name,
      source.targetName,
      source.target,
      source.name,
      source.label,
      matchedElementName,
      matchedStep?.intent,
      matchedStep?.element_info?.text,
      describeElementSubject(matchedStep?.element_info),
      stepNumber ? `Step ${stepNumber}` : ""
    ),
    action
  );
  const locator = summarizeLocator(source, matchedStep);
  const generatedLine = firstNonEmptyText(
    source.generated_line,
    source.generatedLine,
    source.code_line,
    source.codeLine,
    source.line,
    source.script,
    source.code,
    source.snippet
  );
  const rawStatus = firstNonEmptyText(source.status, source.result, source.state, source.outcome).toLowerCase();
  const status = rawStatus === "passed" || rawStatus === "failed" ? rawStatus : "recorded";
  const friendlyTitle = pickFriendlyText(
    source.display_title,
    source.displayTitle,
    source.title,
    source.label,
    buildRecordedDisplayTitle(action, elementName || matchedElementName, stepNumber ?? undefined)
  );
  const fallbackTitle = buildRecordedDisplayTitle(action, elementName || matchedElementName, stepNumber ?? undefined);

  return normalizeRecordedStep(
    {
      id: firstNonEmptyText(source.id, source.step_id, source.stepId, recordedStepId),
      step_number: stepNumber,
      action,
      intent: firstNonEmptyText(source.intent, source.raw?.intent, matchedStep?.intent),
      element_name: elementName || matchedElementName || (stepNumber ? `Step ${stepNumber}` : "Recorded step"),
      locator,
      generated_line: generatedLine,
      status,
      display_title: friendlyTitle || fallbackTitle,
      action_label: action,
      target_label: elementName || matchedElementName || "",
      raw: source,
      ...(Array.isArray(source.children)
        ? {
            children: source.children.map((child) => (child && typeof child === "object" ? { ...child } : child)),
          }
        : {}),
    },
    Number.isFinite(matchIndex) && matchIndex >= 0 ? matchIndex : 0
  );
}

function isPlanStepCompleted(step) {
  if (!step || typeof step !== "object") {
    return false;
  }

  const status = firstNonEmptyText(step.status, step.state, step.cls).toLowerCase();
  return step.recorded === true || step.completed === true || ["done", "completed", "recorded", "passed"].includes(status);
}

function updatePlanAfterRecordedStep(currentPlan, matchInfo, nextRecordedStep) {
  if (!currentPlan || typeof currentPlan !== "object") {
    return currentPlan;
  }

  const currentSteps = Array.isArray(currentPlan.steps) ? currentPlan.steps : [];
  if (!currentSteps.length) {
    return currentPlan;
  }

  const { stepIds = [], recordedStepNumber, recordedStepIndex, matchedStep, matchIndex } = matchInfo || {};
  const candidateIds = collectStepReferenceValues(stepIds, nextRecordedStep?.id, matchedStep?.id);
  const resolvedMatch = findPendingStepMatch(
    currentSteps,
    candidateIds,
    Number.isFinite(recordedStepNumber) ? recordedStepNumber : Number.NaN,
    Number.isFinite(recordedStepIndex) ? recordedStepIndex : Number.isNaN(matchIndex) ? Number.NaN : matchIndex
  );

  if (resolvedMatch.index < 0) {
    return currentPlan;
  }

  const nextSteps = currentSteps.slice();
  const existingStep = nextSteps[resolvedMatch.index] || {};
  nextSteps[resolvedMatch.index] = {
    ...existingStep,
    status: "done",
    state: "done",
    recorded: true,
    completed: true,
    cls: "done",
  };

  const allDone = nextSteps.length > 0 && nextSteps.every(isPlanStepCompleted);
  const nextPlan = {
    ...currentPlan,
    steps: nextSteps,
  };

  if (allDone) {
    nextPlan.summary = "All plan steps recorded";
    nextPlan.status = "completed";
    nextPlan.state = "completed";
    nextPlan.completed = true;
  }

  return nextPlan;
}

function mergeRecordedStepList(current, nextStep) {
  const list = Array.isArray(current) ? current : [];
  const nextStepId = firstNonEmptyText(nextStep?.id, nextStep?.step_id, nextStep?.stepId);
  const nextStepNumber = resolveFiniteNumber(nextStep?.step_number ?? nextStep?.stepNumber ?? nextStep?.number ?? nextStep?.index);
  const index = list.findIndex((step) => {
    const stepId = firstNonEmptyText(step?.id, step?.step_id, step?.stepId);
    if (stepId && nextStepId) {
      return stepId === nextStepId;
    }
    if (stepId || nextStepId) {
      return false;
    }
    const stepNumber = resolveFiniteNumber(step?.step_number ?? step?.stepNumber ?? step?.number ?? step?.index);
    if (Number.isFinite(stepNumber) && Number.isFinite(nextStepNumber) && stepNumber === nextStepNumber) {
      return true;
    }
    return false;
  });

  if (index === -1) {
    return sortRecordedSteps([...list, nextStep]);
  }

  const next = list.slice();
  next[index] = {
    ...next[index],
    ...nextStep,
  };
  return sortRecordedSteps(next);
}

function isSocketOpen(socket) {
  return Boolean(socket && socket.readyState === WebSocket.OPEN);
}

function normalizeTimelineEntry(label, level = "ok") {
  return {
    d: level,
    t: formatTimestamp(),
    txt: label,
  };
}

function resolveReplayPreconditionFeedback(payload) {
  if (!payload || typeof payload !== "object") {
    return null;
  }

  const reason = firstNonEmptyText(payload.reason).toLowerCase();
  if (reason !== "replay_precondition_failed") {
    return null;
  }

  const stepId = firstNonEmptyText(payload.step_id, payload.stepId);
  const failureType = firstNonEmptyText(payload.failure_type, payload.failureType).toLowerCase().replace(/[\s-]+/g, "_");
  const expected = payload.expected && typeof payload.expected === "object" ? payload.expected : null;
  const actual = payload.actual && typeof payload.actual === "object" ? payload.actual : null;
  const message = firstNonEmptyText(payload.message, payload.error);
  const wrongStartPage = failureType === "wrong_start_page" || Boolean(expected?.before_url && actual?.url);
  const locatorMissing = failureType === "locator_missing";
  const timelineDetail = wrongStartPage
    ? "Wrong page"
    : locatorMissing
      ? "Element not found"
      : message && message !== "Replay blocked"
        ? message
        : "";
  const cardDetail = wrongStartPage ? "Wrong page" : locatorMissing ? "Element missing" : "";

  return {
    stepId,
    timelineLabel: timelineDetail ? `Replay blocked · ${timelineDetail}` : "Replay blocked",
    cardDetail,
    message: timelineDetail || message || "Replay blocked",
  };
}

function normalizeClarificationOption(option, index) {
  if (option == null) {
    return null;
  }

  if (typeof option === "string" || typeof option === "number" || typeof option === "boolean") {
    const text = firstNonEmptyText(option);
    if (!text) {
      return null;
    }

    return {
      id: `clarification-option-${index + 1}`,
      label: text,
      value: text,
      raw: option,
    };
  }

  if (typeof option !== "object") {
    return null;
  }

  const label = firstNonEmptyText(option.label, option.text, option.message, option.title, option.option, option.answer, option.value, option.name);
  const value = firstNonEmptyText(option.value, option.answer, option.option, option.text, option.label, option.message, option.title, option.name);
  const resolvedLabel = label || value;
  const resolvedValue = value || resolvedLabel;

  if (!resolvedLabel && !resolvedValue) {
    return null;
  }

  return {
    id: firstNonEmptyText(option.id, option.key, option.value, option.answer) || `clarification-option-${index + 1}`,
    label: resolvedLabel || resolvedValue,
    value: resolvedValue || resolvedLabel,
    raw: option,
  };
}

function normalizeClarificationOptions(options) {
  const list = Array.isArray(options) ? options : options != null ? [options] : [];
  return list.map((option, index) => normalizeClarificationOption(option, index)).filter(Boolean);
}

function normalizeClarificationMessage(message) {
  const raw = message && typeof message.raw === "object" ? message.raw : {};
  const payload = message && typeof message.payload === "object" ? message.payload : {};
  const question = firstNonEmptyText(
    payload.question,
    payload.prompt,
    payload.message,
    payload.text,
    raw.question,
    raw.prompt,
    raw.message,
    raw.text,
    extractText(payload),
    extractText(raw),
    "Clarification needed"
  );
  const options = normalizeClarificationOptions(
    payload.options ?? raw.options ?? payload.choices ?? raw.choices ?? payload.suggestions ?? raw.suggestions ?? []
  );

  return {
    question,
    options,
  };
}

function normalizeConversationEntry(role, text) {
  return {
    w: role,
    t: formatTimestamp(),
    txt: text,
  };
}

function useAutoWorkbenchTransport(config) {
  const wsUrl = useMemo(
    () => resolveWsUrl(config),
    [
      config?.wsUrl,
      config?.ws_url,
      config?.websocketUrl,
      config?.websocket_url,
      config?.socketUrl,
      config?.socket_url,
      config?.wsPort,
      config?.ws_port,
      config?.websocketPort,
      config?.websocket_port,
      config?.host,
    ]
  );

  const [connectionStatus, setConnectionStatus] = useState("disconnected");
  const [runState, setRunStateRaw] = useState(() => normalizeRunState(config.runState ?? config.state) || "idle");
  const setRunState = useCallback((next) => {
    setRunStateRaw((prev) => {
      const nv = typeof next === "function" ? next(prev) : next;
      if (nv !== prev) awLog("STATE", { field: "runState", from: prev, to: nv });
      return nv;
    });
  }, []);
  const [conversation, setConversation] = useState([]);
  const [timeline, setTimeline] = useState([]);
  const [traceEntries, setTraceEntries] = useState(() => normalizeTraceEntries(config.traceEntries));
  const [plan, setPlan] = useState(null);
  const [codePreview, setCodePreview] = useState("");
  const [lastError, setLastError] = useState("");
  const [lastEvent, setLastEvent] = useState(null);
  const [lastSavedSnapshot, setLastSavedSnapshot] = useState(null);
  const [pendingCommands, setPendingCommands] = useState(() => normalizePendingCommands(config.pendingCommands));
  const [pendingSteps, setPendingSteps] = useState(() => normalizePendingSteps(config.pendingSteps));
  const [recordedSteps, setRecordedSteps] = useState(() => normalizeRecordedSteps(config.recordedSteps));
  const [lastReplayByStepId, setLastReplayByStepId] = useState({});
  const [codeDiagnostics, setCodeDiagnostics] = useState(() => normalizeCodeDiagnostics(config.codeDiagnostics));
  const [codeSaveResult, setCodeSaveResult] = useState(null);
  const [interactionMode, setInteractionModeRaw] = useState(
    () => normalizeInteractionMode(config.interactionMode ?? config.mode ?? config.runState ?? config.state) || "idle"
  );
  const setInteractionMode = useCallback((next) => {
    setInteractionModeRaw((prev) => {
      const nv = typeof next === "function" ? next(prev) : next;
      if (nv !== prev) awLog("STATE", { field: "interactionMode", from: prev, to: nv });
      return nv;
    });
  }, []);
  const [planCorrectionText, setPlanCorrectionText] = useState("");
  const [clarificationQuestion, setClarificationQuestion] = useState("");
  const [clarificationOptions, setClarificationOptions] = useState([]);
  const [clarificationAnswerText, setClarificationAnswerText] = useState("");
  const [recoveryText, setRecoveryText] = useState("");
  const [activePickerStepId, setActivePickerStepId] = useState("");

  const socketRef = useRef(null);
  const retryRef = useRef(null);
  const attemptRef = useRef(0);
  const mountedRef = useRef(true);
  const planRef = useRef(null);
  const pendingCommandsRef = useRef([]);
  const activePickerStepIdRef = useRef("");
  const pendingStepsRef = useRef([]);

  useLayoutEffect(() => {
    pendingCommandsRef.current = pendingCommands;
  }, [pendingCommands]);

  useLayoutEffect(() => {
    activePickerStepIdRef.current = activePickerStepId;
  }, [activePickerStepId]);

  useLayoutEffect(() => {
    pendingStepsRef.current = pendingSteps;
  }, [pendingSteps]);

  useLayoutEffect(() => {
    planRef.current = plan;
  }, [plan]);

  const updatePendingSteps = useCallback((updater) => {
    setPendingSteps((current) => {
      const next = typeof updater === "function" ? updater(current) : updater;
      pendingStepsRef.current = next;
      return next;
    });
  }, []);

  const updatePendingCommands = useCallback((updater) => {
    setPendingCommands((current) => {
      const next = typeof updater === "function" ? updater(current) : updater;
      pendingCommandsRef.current = next;
      return next;
    });
  }, []);

  const recordTraceEntry = useCallback((traceEntry) => {
    if (!traceEntry || typeof traceEntry !== "object") {
      return;
    }

    setTraceEntries((current) => mergeTraceEntryList(current, traceEntry));
  }, []);

  const recordPendingCommand = useCallback(
    (commandEnvelope, metadata = {}) => {
      const commandId = firstNonEmptyText(commandEnvelope?.command_id, commandEnvelope?.commandId);
      const commandType = firstNonEmptyText(commandEnvelope?.type);
      if (!commandId || !commandType) {
        return;
      }

      const pendingCommand = {
        command_id: commandId,
        command_type: commandType,
        created_at: new Date().toISOString(),
        created_sequence: pendingCommandSequence += 1,
        status: "pending",
        source: "frontend",
        ...metadata,
      };

      updatePendingCommands((current) => [...current, pendingCommand].slice(-20));
    },
    [updatePendingCommands]
  );

  const acknowledgePendingCommands = useCallback(
    (eventType, metadata = {}) => {
      updatePendingCommands((current) => {
        const index = current.findIndex((command) => command && command.status === "pending");
        if (index === -1) {
          return current;
        }

        const next = current.slice();
        next[index] = {
          ...next[index],
          status: "acknowledged",
          acknowledged_at: new Date().toISOString(),
          acknowledged_by: eventType,
          ...metadata,
        };
        return next;
      });
    },
    [updatePendingCommands]
  );

  const rejectPendingCommand = useCallback(
    (commandId, metadata = {}) => {
      const rejectionId = firstNonEmptyText(commandId);
      if (!rejectionId) {
        return false;
      }

      let matched = false;
      updatePendingCommands((current) => {
        const index = current.findIndex((command) => firstNonEmptyText(command?.command_id) === rejectionId);
        if (index === -1) {
          return current;
        }

        matched = true;
        const next = current.slice();
        next[index] = {
          ...next[index],
          status: "rejected",
          rejected_at: new Date().toISOString(),
          ...metadata,
        };
        return next;
      });

      return matched;
    },
    [updatePendingCommands]
  );

  const updateLastReplayByStepId = useCallback((stepId, replayStatus) => {
    const replayStepId = firstNonEmptyText(stepId);
    if (!replayStepId) {
      return;
    }

    setLastReplayByStepId((current) => ({
      ...current,
      [replayStepId]: replayStatus,
    }));
  }, []);

  const appendTimeline = useCallback((label, level = "ok") => {
    const entry = normalizeTimelineEntry(label, level);
    setTimeline((current) => [...current.slice(-39), entry]);
    setLastEvent({ type: "timeline", ...entry });
  }, []);

  const appendConversation = useCallback((role, text) => {
    const entry = normalizeConversationEntry(role, text);
    setConversation((current) => [...current.slice(-29), entry]);
    setLastEvent({ type: "conversation", ...entry });
  }, []);

  const sendPayload = useCallback(
    (payload, offlineMessage = "WebSocket not connected.") => {
      const socket = socketRef.current;
      const t = payload?.type ?? "?";
      if (!isSocketOpen(socket)) {
        appendTimeline(offlineMessage, "warn");
        awLogError("WS_SEND_OFFLINE", offlineMessage, { type: t });
        return false;
      }

      try {
        socket.send(JSON.stringify(payload));
        awLog("WS_SEND", { type: t, keys: Object.keys(payload || {}).slice(0, 10) });
        return true;
      } catch (error) {
        setConnectionStatus("reconnecting");
        appendTimeline(offlineMessage, "warn");
        if (error instanceof Error && error.message) {
          setLastError(error.message);
        }
        awLogError("WS_SEND", "send failed", { type: t, error });
        return false;
      }
    },
    [appendTimeline]
  );

  const updatePendingStepIntent = useCallback((stepId, intent) => {
    updatePendingSteps((current) =>
      current.map((step) => {
        if (step.id !== stepId) {
          return step;
        }

        const nextIntent = typeof intent === "string" ? intent : "";
        const nextStep = {
          ...step,
          intent: nextIntent,
          recorded: false,
          element_info: step.element_info ?? step.elementInfo ?? null,
        };
        return {
          ...nextStep,
          expected_outcome: normalizeExpectedOutcome(
            step.expected_outcome ?? step.expectedOutcome,
            isClickLikeIntent(nextIntent)
          ),
          status: resolvePendingStepStatus(nextStep),
        };
      })
    );
  }, [updatePendingSteps]);

  const updatePendingStepExpectedOutcome = useCallback((stepId, expectedOutcome) => {
    updatePendingSteps((current) =>
      current.map((step) => {
        if (step.id !== stepId) {
          return step;
        }

        const nextIntent = typeof step.intent === "string" ? step.intent : "";
        const nextStep = {
          ...step,
          intent: nextIntent,
          recorded: false,
          element_info: step.element_info ?? step.elementInfo ?? null,
          expected_outcome: normalizeExpectedOutcome(expectedOutcome, isClickLikeIntent(nextIntent)),
        };

        return {
          ...nextStep,
          status: resolvePendingStepStatus(nextStep),
        };
      })
    );
  }, [updatePendingSteps]);

  const updatePendingStepElementTarget = useCallback((stepId, selectedCandidateIndex) => {
    updatePendingSteps((current) =>
      current.map((step) => {
        if (step.id !== stepId) {
          return step;
        }

        const nextElementInfo = selectElementInfoCandidate(step.element_info ?? step.elementInfo ?? null, selectedCandidateIndex);
        if (!nextElementInfo) {
          return step;
        }

        const nextIntent = typeof step.intent === "string" ? step.intent : "";
        const nextStep = {
          ...step,
          intent: nextIntent,
          recorded: false,
          element_info: nextElementInfo,
          elementInfo: nextElementInfo,
        };
        return {
          ...nextStep,
          status: resolvePendingStepStatus(nextStep),
        };
      })
    );
  }, [updatePendingSteps]);

  const removePendingStep = useCallback(
    (stepId) => {
      if (!stepId) {
        return;
      }

      const currentSteps = pendingStepsRef.current;
      const removedStep = currentSteps.find((step) => step.id === stepId) || null;
      updatePendingSteps((current) => current.filter((step) => step.id !== stepId));

      if (activePickerStepIdRef.current === stepId) {
        setActivePickerStepId("");
      }

      if (removedStep) {
        const stepLabel = firstNonEmptyText(removedStep.intent, removedStep.element_info?.text, removedStep.element_info?.id, `step ${stepId}`);
        appendTimeline(`Removed pending step ${stepLabel}`, "ok");
      } else {
        appendTimeline("Pending step removed.", "ok");
      }
    },
    [appendTimeline, updatePendingSteps]
  );

  const addPendingStep = useCallback(() => {
    updatePendingSteps((current) => [...current, createPendingStep("")]);
    appendTimeline("Step added.", "ok");
  }, [appendTimeline, updatePendingSteps]);

  const handleReplayRecordedStep = useCallback(
    (step) => {
      const stepId = firstNonEmptyText(step?.id, step?.step_id, step?.stepId);
      const title = firstNonEmptyText(step?.display_title, step?.element_name, step?.action, stepId, "Recorded step");
      if (!stepId) {
        appendTimeline("Replay unavailable for this step.", "warn");
        return;
      }

      const sent = sendPayload(
        {
          type: "replay_one",
          step_id: stepId,
        },
        "WebSocket not connected."
      );

      if (sent) {
        appendTimeline(`Replay requested for ${title}`, "active");
      }
    },
    [appendTimeline, sendPayload]
  );

  const handleReplayAllRecordedSteps = useCallback(() => {
    const sent = sendPayload(
      {
        type: "replay_all",
        stop_on_error: true,
      },
      "WebSocket not connected."
    );

    if (sent) {
      appendTimeline("Replay all requested.", "active");
    }
  }, [appendTimeline, sendPayload]);

  const handleCopyRecordedStep = useCallback(
    (step) => {
      const line = firstNonEmptyText(step?.generated_line);
      if (!line) {
        appendTimeline("No generated line to copy.", "warn");
        return;
      }

      if (navigator?.clipboard?.writeText) {
        navigator.clipboard
          .writeText(line)
          .then(() => appendTimeline("Copied generated line.", "ok"))
          .catch(() => appendTimeline("Copy not available.", "warn"));
        return;
      }

      appendTimeline("Copy not available.", "warn");
    },
    [appendTimeline]
  );

  const handleExportCode = useCallback(
    ({ code, path } = {}) => {
      const codeStr = typeof code === "string" ? code : "";
      if (!codeStr) {
        appendTimeline("Export code: no code to save.", "warn");
        return;
      }
      const payload = { type: "export_code", code: codeStr };
      if (path) payload.path = path;
      const sent = sendPayload(payload, "WebSocket not connected — cannot save code.");
      if (sent) {
        appendTimeline("Exporting code to workspace…", "active");
      }
    },
    [appendTimeline, sendPayload]
  );

  const handleCopyCodeToClipboard = useCallback(
    ({ code } = {}) => {
      const codeStr = typeof code === "string" ? code : codePreview;
      const text = typeof codeStr === "string" ? codeStr : "";
      if (!text) {
        appendTimeline("No code to copy.", "warn");
        return;
      }
      if (navigator?.clipboard?.writeText) {
        navigator.clipboard
          .writeText(text)
          .then(() => appendTimeline("Code copied to clipboard.", "ok"))
          .catch(() => appendTimeline("Clipboard copy not available.", "warn"));
        return;
      }
      appendTimeline("Clipboard copy not available.", "warn");
    },
    [appendTimeline, codePreview]
  );

  const handleAttachElement = useCallback(
    (stepId) => {
      if (!stepId) {
        return;
      }

      setActivePickerStepId(stepId);
      const sent = sendPayload(
        {
          type: "arm_picker",
          step_id: stepId,
        },
        "Picker failed"
      );

      if (sent) {
        appendTimeline(`Picker armed for step ${stepId}`, "active");
        return;
      }

      setActivePickerStepId("");
    },
    [appendTimeline, sendPayload]
  );

  // D-107: Composer pick — auto-creates a blank pending step, then arms the
  // picker with its id so the backend can attach element context to it.
  // On dispatch failure the draft step is removed so no orphan pending row
  // remains.
  const handleComposerPick = useCallback(() => {
    const newStep = createPendingStep("");
    updatePendingSteps((current) => [...current, newStep]);
    setActivePickerStepId(newStep.id);
    const sent = sendPayload(
      {
        type: "arm_picker",
        step_id: newStep.id,
      },
      "Picker failed"
    );
    if (sent) {
      appendTimeline(`Composer pick: picker armed for step ${newStep.id}`, "active");
    } else {
      setActivePickerStepId("");
      updatePendingSteps((current) =>
        current.filter((s) => s && s.id !== newStep.id)
      );
    }
  }, [appendTimeline, sendPayload, updatePendingSteps]);

  const handleRunPendingSteps = useCallback(() => {
    const readySteps = [];
    for (const step of pendingSteps) {
      if (!step || typeof step !== "object" || step.recorded === true) {
        continue;
      }

      const intent = firstNonEmptyText(step.intent, step.text, step.label);
      if (!intent) {
        continue;
      }

      const normalizedOutcome = normalizeExpectedOutcome(
        step.expected_outcome ?? step.expectedOutcome,
        isClickLikeIntent(intent)
      );
      if (isClickLikeIntent(intent) && (!normalizedOutcome || !normalizedOutcome.type)) {
        appendTimeline(`Select an expected outcome for "${intent}" before running.`, "warn");
        return;
      }

      readySteps.push({
        id: step.id,
        intent,
        element_info: step.element_info ?? step.elementInfo ?? null,
        expected_outcome: normalizedOutcome,
      });
    }

    if (!readySteps.length) {
      appendTimeline("Add at least one step before running.", "warn");
      return;
    }

    sendPayload(
      {
        type: "run_steps",
        steps: readySteps,
      },
      "WebSocket not connected."
    );
  }, [appendTimeline, pendingSteps, sendPayload]);

  const handleSaveSnapshot = useCallback(() => {
    sendPayload(
      {
        type: "save_snapshot",
      },
      "WebSocket not connected."
    );
  }, [sendPayload]);

  const handleConfirmPlan = useCallback(() => {
    const currentPlan = planRef.current && typeof planRef.current === "object" ? planRef.current : null;
    const rawPlan = currentPlan && typeof currentPlan.raw === "object" ? currentPlan.raw : {};
    const commandPayload = {};
    const planId = firstNonEmptyText(rawPlan.plan_id, rawPlan.planId, rawPlan.id);
    const planVersion = firstNonEmptyText(rawPlan.plan_version, rawPlan.planVersion);
    const runId = firstNonEmptyText(rawPlan.run_id, rawPlan.runId);
    if (planId) {
      commandPayload.plan_id = planId;
    }
    if (planVersion) {
      commandPayload.plan_version = planVersion;
    }
    if (runId) {
      commandPayload.run_id = runId;
    }

    const commandEnvelope = buildFrontendCommandEnvelope("confirmed", commandPayload);
    const sent = sendPayload(commandEnvelope, "WebSocket not connected.");

    if (sent) {
      appendConversation("user", "Confirmed.");
      recordPendingCommand(commandEnvelope, {
        ui_label: "Confirm Plan",
      });
      setPlanCorrectionText("");
      appendTimeline("Confirmation sent.", "ok");
    }
  }, [appendConversation, appendTimeline, recordPendingCommand, sendPayload]);

  const handleSendPlanCorrection = useCallback(() => {
    const correction = planCorrectionText.trim();
    if (!correction) {
      appendTimeline("Correction is empty.", "warn");
      return;
    }
    const currentPlan = planRef.current && typeof planRef.current === "object" ? planRef.current : null;
    const rawPlan = currentPlan && typeof currentPlan.raw === "object" ? currentPlan.raw : {};
    const planId = firstNonEmptyText(rawPlan.plan_id, rawPlan.planId, rawPlan.id);
    const planVersion = firstNonEmptyText(rawPlan.plan_version, rawPlan.planVersion);
    const targetStepId = firstNonEmptyText(
      rawPlan.target_step_id,
      rawPlan.targetStepId,
      currentPlan?.steps?.[0]?.step_id,
      currentPlan?.steps?.[0]?.stepId
    );

    const commandEnvelope = buildFrontendCommandEnvelope("correction", {
      message: correction,
      ...(planId ? { plan_id: planId } : {}),
      ...(planVersion ? { plan_version: planVersion } : {}),
      ...(targetStepId ? { step_id: targetStepId } : {}),
    });
    const sent = sendPayload(commandEnvelope, "WebSocket not connected.");

    if (sent) {
      appendConversation("user", correction);
      recordPendingCommand(commandEnvelope, {
        ui_label: "Plan correction",
      });
      setPlanCorrectionText("");
      appendTimeline("Correction sent.", "ok");
    }
  }, [appendConversation, appendTimeline, plan, planCorrectionText, recordPendingCommand, sendPayload]);

  const handleSendClarificationAnswer = useCallback(
    (answerOverride = "") => {
      const answer = firstNonEmptyText(answerOverride, clarificationAnswerText).trim();
      if (!answer) {
        appendTimeline("Clarification answer is empty.", "warn");
        return;
      }
      const currentPlan = planRef.current && typeof planRef.current === "object" ? planRef.current : null;
      const rawPlan = currentPlan && typeof currentPlan.raw === "object" ? currentPlan.raw : {};
      const planId = firstNonEmptyText(rawPlan.plan_id, rawPlan.planId, rawPlan.id);
      const planVersion = firstNonEmptyText(rawPlan.plan_version, rawPlan.planVersion);

      const commandEnvelope = buildFrontendCommandEnvelope("option_selected", {
        value: answer,
        answer,
        message: answer,
        ...(planId ? { plan_id: planId } : {}),
        ...(planVersion ? { plan_version: planVersion } : {}),
      });
      const sent = sendPayload(commandEnvelope, "WebSocket not connected.");

      if (sent) {
        appendConversation("user", answer);
        recordPendingCommand(commandEnvelope, {
          ui_label: "Clarification answer",
        });
        appendTimeline("Clarification answer sent.", "ok");
        setClarificationAnswerText("");
      }
    },
    [appendConversation, appendTimeline, clarificationAnswerText, recordPendingCommand, sendPayload]
  );

  const handleSendRecoveryInstruction = useCallback(() => {
    const instruction = recoveryText.trim();
    if (!instruction) {
      appendTimeline("Recovery instruction is empty.", "warn");
      return;
    }
    const currentPlan = planRef.current && typeof planRef.current === "object" ? planRef.current : null;
    const rawPlan = currentPlan && typeof currentPlan.raw === "object" ? currentPlan.raw : {};
    const planId = firstNonEmptyText(rawPlan.plan_id, rawPlan.planId, rawPlan.id);
    const planVersion = firstNonEmptyText(rawPlan.plan_version, rawPlan.planVersion);

    const commandEnvelope = buildFrontendCommandEnvelope("correction", {
      message: instruction,
      ...(planId ? { plan_id: planId } : {}),
      ...(planVersion ? { plan_version: planVersion } : {}),
    });
    const sent = sendPayload(commandEnvelope, "WebSocket not connected.");

    if (sent) {
      appendConversation("user", instruction);
      recordPendingCommand(commandEnvelope, {
        ui_label: "Recovery instruction",
      });
      appendTimeline("Recovery instruction sent.", "ok");
      setRecoveryText("");
    }
  }, [appendConversation, appendTimeline, recordPendingCommand, recoveryText, sendPayload]);

  const handleBackendMessage = useCallback(
    (message) => {
      const type = String(message?.type || "status").toLowerCase();
      const payload = message?.payload;
      const text = extractText(payload) || extractText(message?.raw) || type.replace(/_/g, " ");
      const traceEntry = buildTraceEntryFromBackendMessage(message);
      if (traceEntry) {
        recordTraceEntry(traceEntry);
      }

      switch (type) {
        case "browser_ready":
          appendTimeline(text || "Browser ready", "ok");
          break;
        case "status": {
          const nextState = normalizeRunState(
            typeof payload === "string"
              ? payload
              : payload && typeof payload === "object"
                ? payload.runState ?? payload.state ?? payload.phase ?? payload.status
                : null
          );
          if (nextState) {
            setRunState(nextState);
            if (nextState === "idle" || nextState === "planning" || nextState === "executing" || nextState === "recovery" || nextState === "completed") {
              setInteractionMode(nextState);
            }
          }
          acknowledgePendingCommands(type, {
            backend_event: type,
            backend_state: nextState || "",
          });
          appendTimeline(text || "Status update", "ok");
          break;
        }
        case "llm_thinking":
          setRunState("planning");
          setInteractionMode("planning");
          acknowledgePendingCommands(type, {
            backend_event: type,
          });
          appendTimeline(text || "LLM thinking", "active");
          appendConversation("agent", text || "Thinking…");
          break;
        case "plan_ready": {
          setRunState("awaiting_confirmation");
          setInteractionMode("plan_review");
          setPlanCorrectionText("");
          setClarificationQuestion("");
          setClarificationOptions([]);
          setClarificationAnswerText("");
          setRecoveryText("");
          const nextPlan = normalizePlanPayload(payload);
          setPlan(nextPlan);
          acknowledgePendingCommands(type, {
            backend_event: type,
            plan_id: firstNonEmptyText(nextPlan?.raw?.plan_id, nextPlan?.raw?.planId, nextPlan?.raw?.id),
          });
          appendTimeline(nextPlan?.summary ? `Plan ready · ${nextPlan.summary}` : "Plan ready", "warn");
          if (nextPlan?.summary) {
            appendConversation("agent", nextPlan.summary);
          }
          break;
        }
        case "clarification_needed": {
          const clarification = normalizeClarificationMessage(message);
          setRunState("awaiting_confirmation");
          setInteractionMode("clarification");
          setClarificationQuestion(clarification.question);
          setClarificationOptions(clarification.options);
          setClarificationAnswerText("");
          setPlanCorrectionText("");
          setRecoveryText("");
          acknowledgePendingCommands(type, {
            backend_event: type,
          });
          appendConversation("agent", clarification.question || "Clarification needed");
          appendTimeline("Clarification needed", "warn");
          break;
        }
        case "recovery_needed": {
          const recoveryReason = firstNonEmptyText(
            payload && typeof payload === "object" ? payload.error_summary : "",
            payload && typeof payload === "object" ? payload.message : "",
            payload && typeof payload === "object" ? payload.detail : "",
            text,
            "Recovery needed"
          );
          setRunState("recovery");
          setInteractionMode("recovery");
          setLastError(recoveryReason);
          setPlanCorrectionText("");
          setClarificationQuestion("");
          setClarificationOptions([]);
          setClarificationAnswerText("");
          setRecoveryText("");
          acknowledgePendingCommands(type, {
            backend_event: type,
          });
          appendConversation("system", recoveryReason);
          appendTimeline(recoveryReason, "err");
          break;
        }
        case "error":
          setRunState("recovery");
          setInteractionMode("recovery");
          setLastError(text || "Unknown error");
          setClarificationQuestion("");
          setClarificationOptions([]);
          setClarificationAnswerText("");
          setPlanCorrectionText("");
          setRecoveryText("");
          acknowledgePendingCommands(type, {
            backend_event: type,
          });
          appendConversation("system", text || "Error");
          appendTimeline(text || "Error", "err");
          break;
        case "runtime_rejected": {
          const rejectionCommandId = firstNonEmptyText(
            payload && typeof payload === "object" ? payload.command_id : "",
            payload && typeof payload === "object" ? payload.commandId : "",
            message && typeof message === "object" ? message.command_id : "",
            message && typeof message === "object" ? message.commandId : ""
          );
          const rejectionCode = firstNonEmptyText(
            payload && typeof payload === "object" ? payload.rejection_code : "",
            payload && typeof payload === "object" ? payload.rejectionCode : ""
          );
          const rejectionReason = firstNonEmptyText(
            payload && typeof payload === "object" ? payload.message : "",
            payload && typeof payload === "object" ? payload.detail : "",
            text,
            "Command rejected"
          );
          const currentState = payload && typeof payload === "object" ? payload.current_state : null;
          const currentStateSummary =
            currentState && typeof currentState === "object"
              ? [
                  firstNonEmptyText(currentState.phase, currentState.state),
                  firstNonEmptyText(currentState.run_id, currentState.plan_id),
                ]
                  .filter(Boolean)
                  .join(" · ")
              : "";

          if (rejectionCommandId) {
            rejectPendingCommand(rejectionCommandId, {
              rejection_code: rejectionCode,
              rejection_reason: rejectionReason,
              current_state: currentState,
            });
          }
          setLastError(rejectionReason);
          appendTimeline([rejectionCode, rejectionReason, currentStateSummary].filter(Boolean).join(" · "), "err");
          break;
        }
        case "llm_result": {
          const resultSuccess = message?.success;
          const resultMessage = message?.message;
          if (resultSuccess === false || resultSuccess === 0) {
            const failText = resultMessage || text || "Failed";
            appendConversation("system", failText);
            appendTimeline(failText, "err");
            if (String(failText).includes("Correction failed")) {
              setRunState("planning");
              setInteractionMode("planning");
              setPlanCorrectionText("");
              setClarificationQuestion("");
              setClarificationOptions([]);
              setClarificationAnswerText("");
            }
          } else {
            appendConversation("agent", text || "LLM result received");
            appendTimeline(text || "LLM result received", "ok");
          }
          acknowledgePendingCommands(type, {
            backend_event: type,
            success: Boolean(resultSuccess),
          });
          {
            const nextCode = extractCodePreview(payload);
            if (nextCode) {
              setCodePreview(nextCode);
            }
          }
          break;
        }
        case "step_recorded": {
          const recordedStepIds = collectStepReferenceValues(payload);
          const recordedStepNumber = resolveFiniteNumber(
            payload && typeof payload === "object"
              ? payload.step_number ?? payload.stepNumber ?? payload.number
              : Number.NaN
          );
          const recordedStepIndex = resolveFiniteNumber(
            payload && typeof payload === "object"
              ? payload.index ?? payload.step_index ?? payload.stepIndex
              : Number.NaN
          );
          const { index: matchedIndex, step: matchedStep } = findPendingStepMatch(
            pendingStepsRef.current,
            recordedStepIds,
            recordedStepNumber,
            recordedStepIndex
          );
          const nextRecordedStep = buildRecordedStepFromPayload(
            payload,
            matchedStep,
            matchedIndex,
            recordedStepIds[0] || "",
            recordedStepNumber,
            recordedStepIndex
          );

          if (matchedStep || Number.isFinite(recordedStepNumber) || Number.isFinite(recordedStepIndex)) {
            const removalIds = matchedStep ? collectStepReferenceValues(matchedStep) : [];
            updatePendingSteps((current) =>
              current.filter((step, index) => {
                if (removalIds.length > 0) {
                  const stepIds = collectStepReferenceValues(step);
                  if (stepIds.some((stepId) => removalIds.includes(stepId))) {
                    return false;
                  }
                }

                if (removalIds.length === 0 && matchedIndex >= 0 && index === matchedIndex) {
                  return false;
                }

                return true;
              })
            );
          }

          const nextPlan = updatePlanAfterRecordedStep(planRef.current, {
            stepIds: recordedStepIds,
            recordedStepNumber,
            recordedStepIndex,
            matchedStep,
            matchIndex: matchedIndex,
          }, nextRecordedStep);
          if (nextPlan && nextPlan !== planRef.current) {
            setPlan(nextPlan);
          }

          setRecordedSteps((current) => mergeRecordedStepList(current, nextRecordedStep));
          const planCompleted = Boolean(nextPlan && Array.isArray(nextPlan.steps) && nextPlan.steps.length > 0 && nextPlan.steps.every(isPlanStepCompleted));
          setRunState((current) => (current === "completed" ? current : planCompleted ? "completed" : "executing"));
          setInteractionMode(planCompleted ? "completed" : "executing");
          acknowledgePendingCommands(type, {
            backend_event: type,
            recorded_step_id: firstNonEmptyText(nextRecordedStep.id, nextRecordedStep.step_id),
          });
          appendTimeline(
            `Recorded: ${firstNonEmptyText(nextRecordedStep.action, "recorded")} — ${firstNonEmptyText(
              nextRecordedStep.element_name,
              nextRecordedStep.display_title,
              "step"
            )}`,
            "ok"
          );
          break;
        }
        case "code_update": {
          const nextCode = extractCodePreview(payload);
          if (nextCode) {
            setCodePreview(nextCode);
          }
          setCodeDiagnostics(
            normalizeCodeDiagnostics(payload && typeof payload === "object" ? payload.diagnostics : [])
          );
          // Clear prior save result when a new code_update arrives
          setCodeSaveResult(null);
          acknowledgePendingCommands(type, {
            backend_event: type,
          });
          appendTimeline(text || "Code updated", "ok");
          break;
        }
        case "replay_started": {
          const scope = firstNonEmptyText(payload && typeof payload === "object" ? payload.scope : "");
          const stepCount = resolveFiniteNumber(
            payload && typeof payload === "object" ? payload.step_count ?? payload.stepCount : Number.NaN
          );
          const scopeLabel = scope === "all" ? "Replay all started" : "Replay started";
          appendTimeline(
            Number.isFinite(stepCount) ? `${scopeLabel} · ${stepCount} steps` : scopeLabel,
            "active"
          );
          break;
        }
        case "replay_result": {
          const replayStepId = firstNonEmptyText(
            payload && typeof payload === "object" ? payload.step_id : "",
            payload && typeof payload === "object" ? payload.stepId : ""
          );
          const isOk = payload && typeof payload === "object" && payload.ok === true;
          const operationCount = resolveFiniteNumber(
            payload && typeof payload === "object" ? payload.operation_count ?? payload.operationCount : Number.NaN
          );
          if (isOk) {
            updateLastReplayByStepId(replayStepId, {
              status: "passed",
              short_reason: "Replay passed",
            });
            appendTimeline(
              `Replay step succeeded for ${replayStepId || "step"}${
                Number.isFinite(operationCount) ? ` · ${operationCount} operations` : ""
              }`,
              "ok"
            );
          } else {
            const replayFeedback = resolveReplayPreconditionFeedback(payload);
            if (replayFeedback) {
              updateLastReplayByStepId(replayStepId, {
                status: "blocked",
                short_reason: replayFeedback.cardDetail,
              });
              setLastError(replayFeedback.message);
              appendTimeline(replayFeedback.timelineLabel, "err");
            } else {
              const failedOperationId = firstNonEmptyText(
                payload && typeof payload === "object" ? payload.failed_operation_id : "",
                payload && typeof payload === "object" ? payload.failedOperationId : ""
              );
              const errorText = firstNonEmptyText(
                payload && typeof payload === "object" ? payload.error : "",
                "Replay failed"
              );
              updateLastReplayByStepId(replayStepId, {
                status: "failed",
                short_reason: "",
              });
              setLastError(errorText);
              appendTimeline(
                `Replay step failed for ${replayStepId || "step"}${
                  failedOperationId ? ` · ${failedOperationId}` : ""
                } · ${errorText}`,
                "err"
              );
            }
          }
          break;
        }
        case "replay_all_result": {
          const isOk = payload && typeof payload === "object" && payload.ok === true;
          const passedCount = resolveFiniteNumber(
            payload && typeof payload === "object" ? payload.passed_count ?? payload.passedCount : Number.NaN
          );
          const failedCount = resolveFiniteNumber(
            payload && typeof payload === "object" ? payload.failed_count ?? payload.failedCount : Number.NaN
          );
          const errorText = firstNonEmptyText(
            payload && typeof payload === "object" ? payload.error : "",
            "Replay all failed"
          );
          if (isOk) {
            const passedLabel = Number.isFinite(passedCount) ? `${passedCount} passed` : "";
            appendTimeline(["Replay all completed", passedLabel].filter(Boolean).join(" · "), "ok");
          } else {
            setLastError(errorText);
            const stoppedLabel =
              payload && typeof payload === "object" && payload.stop_on_error === true
                ? "Replay all stopped"
                : "Replay all completed";
            const passedLabel = Number.isFinite(passedCount) ? `${passedCount} passed` : "";
            const failedLabel = Number.isFinite(failedCount) ? `${failedCount} failed` : "";
            appendTimeline([stoppedLabel, passedLabel, failedLabel].filter(Boolean).join(" · "), "err");
          }
          break;
        }
        case "replay_one_result": {
          const replayStepId = firstNonEmptyText(
            payload && typeof payload === "object" ? payload.step_id : "",
            payload && typeof payload === "object" ? payload.stepId : ""
          );
          const isOk = payload && typeof payload === "object" && payload.ok === true;
          if (isOk) {
            updateLastReplayByStepId(replayStepId, {
              status: "passed",
              short_reason: "Replay passed",
            });
            const operationCount = resolveFiniteNumber(
              payload && typeof payload === "object" ? payload.operation_count ?? payload.operationCount : Number.NaN
            );
            appendTimeline(
              `Replay succeeded for ${replayStepId || "step"}${
                Number.isFinite(operationCount) ? ` · ${operationCount} operations` : ""
              }`,
              "ok"
            );
          } else {
            const replayFeedback = resolveReplayPreconditionFeedback(payload);
            if (replayFeedback) {
              updateLastReplayByStepId(replayStepId, {
                status: "blocked",
                short_reason: replayFeedback.cardDetail,
              });
              setLastError(replayFeedback.message);
              appendTimeline(replayFeedback.timelineLabel, "err");
            } else {
              const failedOperationId = firstNonEmptyText(
                payload && typeof payload === "object" ? payload.failed_operation_id : "",
                payload && typeof payload === "object" ? payload.failedOperationId : ""
              );
              const errorText = firstNonEmptyText(
                payload && typeof payload === "object" ? payload.error : "",
                "Replay failed"
              );
              updateLastReplayByStepId(replayStepId, {
                status: "failed",
                short_reason: "",
              });
              setLastError(errorText);
              appendTimeline(
                `Replay failed for ${replayStepId || "step"}${failedOperationId ? ` · ${failedOperationId}` : ""} · ${errorText}`,
                "err"
              );
            }
          }
          break;
        }
        case "export_code_result": {
          const isOk = payload && typeof payload === "object" && payload.ok === true;
          if (isOk) {
            const savedPath = firstNonEmptyText(
              payload && typeof payload === "object" ? payload.path : "",
              "workspace"
            );
            setCodeSaveResult({ ok: true, path: payload.path ?? null });
            appendTimeline(`Code saved to ${savedPath}`, "ok");
          } else {
            const errorText = firstNonEmptyText(
              payload && typeof payload === "object" ? payload.error : "",
              "Code save failed"
            );
            setCodeSaveResult({ ok: false, error: errorText });
            appendTimeline(errorText, "err");
          }
          break;
        }
        case "save_snapshot_result": {
          const isOk = payload && typeof payload === "object" && payload.ok === true;
          if (isOk) {
            const nextSnapshot = payload.snapshot && typeof payload.snapshot === "object" ? payload.snapshot : null;
            setLastSavedSnapshot(nextSnapshot);
            appendTimeline("Snapshot saved", "ok");
          } else {
            const errorText = firstNonEmptyText(
              payload && typeof payload === "object" ? payload.error : "",
              "Snapshot save failed"
            );
            setLastError(errorText);
            appendTimeline(errorText, "err");
          }
          break;
        }
        case "element_picked": {
          const { stepId, stepIds, elementInfo } = normalizePickedElementMessage(message);
          const referenceIds = collectStepReferenceValues(stepIds, stepId, activePickerStepIdRef.current);
          const match = findPendingStepMatch(pendingStepsRef.current, referenceIds, Number.NaN, Number.NaN);
          if (match.step) {
            updatePendingSteps((current) =>
              current.map((step, index) => {
                if (index !== match.index) {
                  return step;
                }

                const nextIntent = typeof step.intent === "string" ? step.intent : "";
                const nextElementInfo = selectElementInfoCandidate(elementInfo, elementInfo?.selected_candidate_index);
                const nextStep = {
                  ...step,
                  element_info: nextElementInfo,
                  elementInfo: nextElementInfo,
                  recorded: false,
                  status: nextIntent.trim() ? "ready" : "draft",
                };

                return {
                  ...nextStep,
                  expected_outcome: normalizeExpectedOutcome(
                    step.expected_outcome ?? step.expectedOutcome,
                    isClickLikeIntent(nextIntent)
                  ),
                  status: resolvePendingStepStatus(nextStep),
                };
              })
            );
            setActivePickerStepId("");
            const stepNumber = resolveFiniteNumber(match.step.step_number ?? match.step.stepNumber ?? match.step.number ?? match.index + 1);
            const stepLabel = Number.isFinite(stepNumber) && stepNumber > 0 ? `step ${stepNumber}` : `step ${match.step.id || match.index + 1}`;
            appendTimeline(`Element attached to ${stepLabel}`, "ok");
          } else {
            const availableIds = pendingStepsRef.current.map((step) => step.id).filter(Boolean);
            setActivePickerStepId("");
            appendTimeline(
              `Element picked but no matching step found for ${referenceIds.join(", ") || "unknown"}${
                availableIds.length > 0 ? ` · pending: ${availableIds.join(", ")}` : ""
              }`,
              "warn"
            );
          }
          break;
        }
        default:
          appendTimeline(text || type, "ok");
          break;
      }
    },
    [acknowledgePendingCommands, appendConversation, appendTimeline, rejectPendingCommand]
  );

  useEffect(() => {
    mountedRef.current = true;
    return () => {
      mountedRef.current = false;
      if (retryRef.current) {
        clearTimeout(retryRef.current);
        retryRef.current = null;
      }
      if (socketRef.current) {
        try {
          socketRef.current.close();
        } catch {
          // ignore close errors during unmount
        }
        socketRef.current = null;
      }
    };
  }, []);

  useEffect(() => {
    let cancelled = false;

    const clearRetry = () => {
      if (retryRef.current) {
        clearTimeout(retryRef.current);
        retryRef.current = null;
      }
    };

    const scheduleReconnect = () => {
      if (cancelled || !mountedRef.current) return;
      clearRetry();
      const attempt = attemptRef.current;
      const delay = Math.min(1000 * 2 ** Math.min(attempt, 4), 5000);
      attemptRef.current = Math.min(attempt + 1, 6);
      setConnectionStatus("reconnecting");
      retryRef.current = window.setTimeout(connect, delay);
    };

    function connect() {
      if (cancelled || !mountedRef.current) return;
      clearRetry();

      if (socketRef.current) {
        try {
          socketRef.current.close();
        } catch {
          // ignore stale socket close errors
        }
      }

      let socket;
      try {
        socket = new WebSocket(wsUrl);
      } catch (error) {
        setConnectionStatus("reconnecting");
        appendTimeline("WebSocket connection failed", "err");
        setLastError(error instanceof Error ? error.message : "WebSocket connection failed");
        scheduleReconnect();
        return;
      }

      socketRef.current = socket;
      setConnectionStatus("reconnecting");

      socket.onopen = () => {
        if (cancelled) return;
        attemptRef.current = 0;
        setConnectionStatus("connected");
        appendTimeline("Connected", "ok");
        awLog("WS_OPEN", { url: wsUrl });
      };

      socket.onmessage = (event) => {
        if (cancelled) return;
        const normalized = normalizeBackendMessage(event.data);
        const evType = normalized?.type ?? "?";
        awLog("WS_RECV", { type: evType, keys: Object.keys(normalized || {}).slice(0, 10) });
        try {
          window.__awLastWsFrame__ = normalized;
          window.__awWsFrames__ = window.__awWsFrames__ || [];
          window.__awWsFrames__.push({ at: Date.now(), type: evType, payload: normalized });
          if (window.__awWsFrames__.length > 200) window.__awWsFrames__.shift();
        } catch (_) {}
        try {
          handleBackendMessage(normalized);
        } catch (exc) {
          awLogError("WS_RECV_HANDLER", "handleBackendMessage threw", { type: evType, error: exc });
        }
      };

      socket.onerror = () => {
        if (cancelled) return;
        setConnectionStatus("reconnecting");
        appendTimeline("WebSocket error", "err");
        awLogError("WS_ERROR", "websocket onerror", { url: wsUrl });
      };

      socket.onclose = (e) => {
        if (cancelled) return;
        socketRef.current = null;
        setConnectionStatus("reconnecting");
        appendTimeline("Disconnected", "warn");
        awLog("WS_CLOSE", { code: e?.code, reason: e?.reason, wasClean: e?.wasClean });
        scheduleReconnect();
      };
    }

    connect();

    return () => {
      cancelled = true;
      clearRetry();
      if (socketRef.current) {
        try {
          socketRef.current.close();
        } catch {
          // ignore close errors during reconnect teardown
        }
        socketRef.current = null;
      }
    };
  }, [appendTimeline, handleBackendMessage, wsUrl]);

  return {
    connectionStatus,
    runState,
    interactionMode,
    conversation,
    timeline,
    traceEntries,
    plan,
    pendingSteps,
    pendingCommands,
    recordedSteps,
    lastReplayByStepId,
    codeDiagnostics,
    codeSaveResult,
    planCorrectionText,
    clarificationQuestion,
    clarificationOptions,
    clarificationAnswerText,
    recoveryText,
    recordedCount: recordedSteps.length,
    codePreview,
    lastError,
    lastEvent,
    lastSavedSnapshot,
    wsUrl,
    activePickerStepId,
    onCorrectionTextChange: setPlanCorrectionText,
    onPlanCorrectionTextChange: setPlanCorrectionText,
    onClarificationAnswerTextChange: setClarificationAnswerText,
    onRecoveryTextChange: setRecoveryText,
    onPendingStepIntentChange: updatePendingStepIntent,
    onPendingStepExpectedOutcomeChange: updatePendingStepExpectedOutcome,
    onPendingStepElementTargetChange: updatePendingStepElementTarget,
    onAddPendingStep: addPendingStep,
    onDeletePendingStep: removePendingStep,
    onAttachElement: handleAttachElement,
    handleComposerPick,
    onComposerPick: handleComposerPick,
    onRunPendingSteps: handleRunPendingSteps,
    onSaveSnapshot: handleSaveSnapshot,
    onConfirmPlan: handleConfirmPlan,
    onSendCorrection: handleSendPlanCorrection,
    onSendPlanCorrection: handleSendPlanCorrection,
    onSendClarificationAnswer: handleSendClarificationAnswer,
    onSendOptionSelected: handleSendClarificationAnswer,
    onSendRecoveryInstruction: handleSendRecoveryInstruction,
    onReplayRecordedStep: handleReplayRecordedStep,
    onReplayAllRecordedSteps: handleReplayAllRecordedSteps,
    onCopyRecordedStep: handleCopyRecordedStep,
    onExportCode: handleExportCode,
    handleExportCode,
    onCopyCode: handleCopyCodeToClipboard,
    handleCopyCodeToClipboard,
    setPlanCorrectionText,
    setClarificationQuestion,
    setClarificationOptions,
    setClarificationAnswerText,
    setRecoveryText,
    setPendingSteps,
    setPendingCommands,
    setTraceEntries,
    setRecordedSteps,
    setCodeDiagnostics,
    updatePendingStepIntent,
    addPendingStep,
    removePendingStep,
    updatePendingStepElementTarget,
    handleRunPendingSteps,
    handleSaveSnapshot,
    handleConfirmPlan,
    handleSendPlanCorrection,
    handleSendClarificationAnswer,
    handleSendRecoveryInstruction,
    handleReplayRecordedStep,
    handleReplayAllRecordedSteps,
    handleCopyRecordedStep,
    handleExportCode,
    handleCopyCodeToClipboard,
    handleComposerPick,
  };
}

function AutoWorkbenchRuntime({ config }) {
  const normalized = normalizeConfig(config);
  const transport = useFrontendEventStore(config);
  const [tab, setTab] = useState(normalized.tab);

  useEffect(() => {
    setTab(normalized.tab);
  }, [normalized.tab]);

  const panelState = toPanelState(transport.runState || normalized.panelState);
  const IDEPanel = window.IDEPanel;

  return (
    <div
      style={{
        position: "fixed",
        inset: 0,
        zIndex: 2147483647,
        display: "flex",
        justifyContent: "flex-end",
        padding: 16,
        boxSizing: "border-box",
        pointerEvents: "none",
      }}
    >
      <div
        className={`aw-density-${normalized.density}`}
        style={{
          width: normalized.panelWidth,
          height: "100%",
          pointerEvents: "auto",
          boxShadow: "-12px 0 36px rgba(0,0,0,0.28)",
        }}
      >
        {IDEPanel ? (
          <IDEPanel
            state={panelState}
            tab={tab}
            runtime={{
              live: true,
              ...transport,
              storeState: transport.storeState,
              connected: transport.storeState?.connected ?? false,
              run_id: transport.storeState?.run_id ?? null,
              phase: transport.storeState?.phase ?? "idle",
              storePlan: transport.storeState?.plan ?? null,
              storePendingSteps: transport.storeState?.pending_steps ?? [],
              storeRecordedSteps: transport.storeState?.recorded_steps ?? [],
              storeCodePreview: transport.storeState?.code_preview ?? null,
              storeCodeSaveResult: transport.storeState?.code_save_result ?? null,
              storeTraceEntries: transport.storeState?.trace_entries ?? [],
              storeErrors: transport.storeState?.errors ?? [],
              storeLastError: transport.storeState?.last_error ?? null,
              storeInteractionMode: transport.storeState?.interaction_mode ?? "idle",
              storePendingClarification: transport.storeState?.pending_clarification ?? null,
              storePendingPermission: transport.storeState?.pending_permission ?? null,
              storePendingRecovery: transport.storeState?.pending_recovery ?? null,
              storePendingRecommendations: transport.storeState?.pending_recommendations ?? [],
            }}
            onTabChange={setTab}
          />
        ) : null}
      </div>
    </div>
  );
}

function useFrontendEventStore(config) {
  const [storeState, storeDispatch] = React.useReducer(reducer, null, createInitialState);
  const transport = useAutoWorkbenchTransport(config);
  return { ...transport, storeState, storeDispatch };
}

let currentRoot = null;
let currentHostNode = null;
let currentMountNode = null;

function renderInto(node, config) {
  // Derive backend base URL from the wsUrl so frontend log POSTs land at /api/log.
  try {
    const wsUrl = config?.wsUrl || config?.ws_url || "";
    if (wsUrl && typeof window !== "undefined") {
      const httpUrl = wsUrl.replace(/^ws/i, "http").replace(/\/ws$/, "");
      window.__awBackendBaseUrl__ = httpUrl;
    }
  } catch (_) {}
  awAttachGlobalHandlers();
  awLog("PANEL", { event: "renderInto" });
  // Use host module for Shadow DOM lifecycle (S7-0401)
  const hostResult = createHost(node);
  const shadowRoot = hostResult ? hostResult.shadowRoot : null;
  const mountNode = shadowRoot ? ensureShadowMount(shadowRoot) : node;

  if (shadowRoot) {
    ensureShadowStyles(shadowRoot);
  }

  if (currentRoot && (currentHostNode !== node || currentMountNode !== mountNode)) {
    currentRoot.unmount();
    currentRoot = null;
    currentHostNode = null;
    currentMountNode = null;
  }

  if (!currentRoot) {
    currentRoot = createRoot(mountNode);
    currentHostNode = node;
    currentMountNode = mountNode;
  }

  currentRoot.render(<AutoWorkbenchRuntime config={config} />);
}

function mount(root, config = {}) {
  const node = resolveMountNode(root);

  // Wire layout modules — S7-0402, S7-0403, S7-0405
  const dockMode = getDockMode();
  const panelMode = getPanelMode();
  applyDock(node, dockMode);
  applyMode(node, panelMode);
  const storedSize = getStoredSize();
  const panelWidth = storedSize?.width ?? config.panelWidth ?? 460;
  applyCompensation(dockMode, { width: panelWidth });

  renderInto(node, config);
  return node;
}

function unmount() {
  // Restore page styles and remove DOM nodes — S7-0405, S7-0406
  removeCompensation();
  if (currentRoot) {
    currentRoot.unmount();
    currentRoot = null;
    currentHostNode = null;
    currentMountNode = null;
  }
  unmountHost();
}

window.AutoWorkbench = {
  mount,
  unmount,
};
