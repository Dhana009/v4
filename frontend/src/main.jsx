import React, { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { createRoot } from "react-dom/client";

import "../styles.css";
import "../style-ide.css";

import "../icons.jsx";
import "../aw-ide-panel.jsx";

const VALID_TABS = new Set(["workbench", "steps", "code", "debug"]);

const DEFAULT_CONFIG = {
  state: "planning",
  tab: "workbench",
  panelWidth: 460,
  density: "compact",
};

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

function normalizeRunState(value) {
  if (value == null || value === "") return null;
  const key = String(value).trim().toLowerCase().replace(/[\s-]+/g, "_");
  return RUN_STATE_ALIASES[key] || null;
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
      return "planning";
  }
}

function normalizeConfig(config = {}) {
  const runState = normalizeRunState(config.runState ?? config.state ?? DEFAULT_CONFIG.state) || "planning";
  const tab = VALID_TABS.has(config.tab) ? config.tab : DEFAULT_CONFIG.tab;
  const panelWidth = Number.isFinite(config.panelWidth) ? config.panelWidth : DEFAULT_CONFIG.panelWidth;
  const density = ["compact", "regular", "comfy"].includes(config.density)
    ? config.density
    : DEFAULT_CONFIG.density;

  return {
    ...config,
    runState,
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
          : parsed.message !== undefined
            ? parsed.message
            : parsed;
    return { type, payload, raw: parsed };
  }

  return {
    type: "status",
    payload: { text: String(parsed ?? "") },
    raw: parsed,
  };
}

function formatTimestamp(date = new Date()) {
  return date.toLocaleTimeString([], {
    hour12: false,
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  });
}

function extractText(value, keys = ["text", "message", "content", "summary", "title", "detail", "error", "reason", "label"]) {
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

  if (typeof step === "string") {
    return {
      kind: "step",
      text: step,
      status: index === 0 ? "active" : "ok",
    };
  }

  if (typeof step !== "object") {
    return {
      kind: "step",
      text: String(step),
      status: index === 0 ? "active" : "ok",
    };
  }

  const status = String(step.status || step.state || (step.done ? "done" : "")).toLowerCase();
  return {
    kind: String(step.kind || step.type || step.action || step.name || "step"),
    text: extractText(step, ["text", "label", "title", "message", "content"]) || `Step ${index + 1}`,
    status: ["done", "active", "warn", "err", "ok"].includes(status) ? status : index === 0 ? "active" : "ok",
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

function createPendingStep(intent = "", elementInfo = null, recorded = false) {
  pendingStepCounter += 1;
  return {
    id: `pending-step-${Date.now().toString(36)}-${pendingStepCounter}`,
    intent,
    element_info: elementInfo,
    recorded,
  };
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

function normalizeElementInfo(info) {
  if (!info || typeof info !== "object") {
    return null;
  }

  const attributes = info.attributes && typeof info.attributes === "object" ? info.attributes : {};
  let classValue = firstNonEmptyText(info.class, info.className, attributes.class, attributes.className);
  if (!classValue && Array.isArray(info.classes)) {
    classValue = info.classes.filter(Boolean).map((value) => String(value).trim()).filter(Boolean).join(" ");
  }

  return {
    ...info,
    tag: firstNonEmptyText(info.tag, info.tagName, info.nodeName).toLowerCase() || "element",
    text: firstNonEmptyText(info.text, info.innerText, info.content, info.title, info.value, info.label),
    id: firstNonEmptyText(info.id, attributes.id),
    className: classValue,
    attributes,
  };
}

function normalizePickedElementMessage(message) {
  const payload = message?.payload && typeof message.payload === "object" ? message.payload : message;
  const stepId = firstNonEmptyText(
    payload?.step_id,
    payload?.stepId,
    payload?.step?.id,
    message?.step_id,
    message?.stepId,
    message?.step?.id
  );

  const rawElementInfo =
    payload?.element_info ??
    payload?.elementInfo ??
    payload?.element ??
    payload?.info ??
    payload?.descriptor ??
    payload?.payload ??
    payload;

  return {
    stepId,
    elementInfo: normalizeElementInfo(rawElementInfo),
  };
}

function normalizePendingStep(step) {
  if (!step || typeof step !== "object") {
    return createPendingStep(typeof step === "string" ? step : "");
  }

  return {
    id: typeof step.id === "string" && step.id.trim() ? step.id : createPendingStep().id,
    intent: typeof step.intent === "string" ? step.intent : "",
    element_info: step.element_info ?? null,
    recorded: step.recorded === true,
  };
}

function normalizePendingSteps(steps) {
  if (Array.isArray(steps) && steps.length > 0) {
    return steps.map(normalizePendingStep);
  }

  return [createPendingStep("")];
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
  const [runState, setRunState] = useState(() => normalizeRunState(config.runState ?? config.state) || "planning");
  const [conversation, setConversation] = useState([]);
  const [timeline, setTimeline] = useState([]);
  const [plan, setPlan] = useState(null);
  const [recordedCount, setRecordedCount] = useState(0);
  const [codePreview, setCodePreview] = useState("");
  const [lastError, setLastError] = useState("");
  const [lastEvent, setLastEvent] = useState(null);
  const [pendingSteps, setPendingSteps] = useState(() => normalizePendingSteps(config.pendingSteps));
  const [correctionText, setCorrectionText] = useState("");
  const [activePickerStepId, setActivePickerStepId] = useState("");

  const socketRef = useRef(null);
  const retryRef = useRef(null);
  const attemptRef = useRef(0);
  const mountedRef = useRef(true);
  const activePickerStepIdRef = useRef("");

  useEffect(() => {
    activePickerStepIdRef.current = activePickerStepId;
  }, [activePickerStepId]);

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
      if (!isSocketOpen(socket)) {
        appendTimeline(offlineMessage, "warn");
        return false;
      }

      try {
        socket.send(JSON.stringify(payload));
        return true;
      } catch (error) {
        setConnectionStatus("reconnecting");
        appendTimeline(offlineMessage, "warn");
        if (error instanceof Error && error.message) {
          setLastError(error.message);
        }
        return false;
      }
    },
    [appendTimeline]
  );

  const updatePendingStepIntent = useCallback((stepId, intent) => {
    setPendingSteps((current) =>
      current.map((step) => (step.id === stepId ? { ...step, intent, recorded: false, element_info: step.element_info ?? null } : step))
    );
  }, []);

  const addPendingStep = useCallback(() => {
    setPendingSteps((current) => [...current, createPendingStep("")]);
    appendTimeline("Step added.", "ok");
  }, [appendTimeline]);

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

  const handleRunPendingSteps = useCallback(() => {
    const readySteps = pendingSteps
      .filter((step) => typeof step.intent === "string" && step.intent.trim() && step.recorded !== true)
      .map((step) => ({
        id: step.id,
        intent: step.intent.trim(),
        element_info: step.element_info ?? null,
      }));

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

  const handleConfirmPlan = useCallback(() => {
    const sent = sendPayload(
      {
        type: "confirmed",
      },
      "WebSocket not connected."
    );

    if (sent) {
      appendTimeline("Confirmation sent.", "ok");
    }
  }, [appendTimeline, sendPayload]);

  const handleSendCorrection = useCallback(() => {
    const correction = correctionText.trim();
    if (!correction) {
      appendTimeline("Correction is empty.", "warn");
      return;
    }

    const sent = sendPayload(
      {
        type: "correction",
        message: correction,
      },
      "WebSocket not connected."
    );

    if (sent) {
      setCorrectionText("");
      appendTimeline("Correction sent.", "ok");
    }
  }, [appendTimeline, correctionText, sendPayload]);

  const handleBackendMessage = useCallback(
    (message) => {
      const type = String(message?.type || "status").toLowerCase();
      const payload = message?.payload;
      const text = extractText(payload) || extractText(message?.raw) || type.replace(/_/g, " ");

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
          }
          appendTimeline(text || "Status update", "ok");
          break;
        }
        case "llm_thinking":
          setRunState("planning");
          appendTimeline(text || "LLM thinking", "active");
          appendConversation("agent", text || "Thinking…");
          break;
        case "plan_ready": {
          setRunState("awaiting_confirmation");
          const nextPlan = normalizePlanPayload(payload);
          setPlan(nextPlan);
          appendTimeline(nextPlan?.summary ? `Plan ready · ${nextPlan.summary}` : "Plan ready", "warn");
          if (nextPlan?.summary) {
            appendConversation("agent", nextPlan.summary);
          }
          break;
        }
        case "clarification_needed":
          setRunState("awaiting_confirmation");
          appendConversation("system", text || "Clarification needed");
          appendTimeline(text || "Clarification needed", "warn");
          break;
        case "error":
          setRunState("recovery");
          setLastError(text || "Unknown error");
          appendConversation("system", text || "Error");
          appendTimeline(text || "Error", "err");
          break;
        case "llm_result":
          appendConversation("agent", text || "LLM result received");
          appendTimeline(text || "LLM result received", "ok");
          {
            const nextCode = extractCodePreview(payload);
            if (nextCode) {
              setCodePreview(nextCode);
            }
          }
          break;
        case "step_recorded": {
          const recordedStepId = firstNonEmptyText(
            payload && typeof payload === "object" ? payload.step_id : "",
            payload && typeof payload === "object" ? payload.stepId : "",
            payload && typeof payload === "object" ? payload.id : ""
          );
          const recordedStepNumber = Number(
            payload && typeof payload === "object"
              ? payload.step_number ?? payload.stepNumber ?? payload.number ?? payload.index
              : Number.NaN
          );
          if (recordedStepId || Number.isFinite(recordedStepNumber)) {
            setPendingSteps((current) =>
              current.map((step, index) => {
                const matchesId = recordedStepId && step.id === recordedStepId;
                const matchesNumber = Number.isFinite(recordedStepNumber) && recordedStepNumber > 0 && index === recordedStepNumber - 1;
                if (!matchesId && !matchesNumber) {
                  return step;
                }
                return {
                  ...step,
                  recorded: true,
                  element_info: step.element_info ?? normalizeElementInfo(payload?.element_info ?? payload?.elementInfo ?? null),
                };
              })
            );
          }
          const countFromPayload = Number(
            payload && typeof payload === "object"
              ? payload.recordedCount ?? payload.count ?? payload.total ?? payload.stepCount
              : Number.NaN
          );
          if (Number.isFinite(countFromPayload)) {
            setRecordedCount(countFromPayload);
          } else {
            setRecordedCount((current) => current + 1);
          }
          setRunState((current) => (current === "completed" ? current : "executing"));
          appendTimeline(text || "Step recorded", "ok");
          break;
        }
        case "code_update": {
          const nextCode = extractCodePreview(payload);
          if (nextCode) {
            setCodePreview(nextCode);
          }
          appendTimeline(text || "Code updated", "ok");
          break;
        }
        case "element_picked": {
          const { stepId, elementInfo } = normalizePickedElementMessage(message);
          const resolvedStepId = stepId || activePickerStepIdRef.current;
          if (resolvedStepId) {
            let matched = false;
            setPendingSteps((current) =>
              current.map((step) => {
                if (step.id !== resolvedStepId) {
                  return step;
                }
                matched = true;
                return {
                  ...step,
                  element_info: elementInfo,
                  recorded: false,
                };
              })
            );
            setActivePickerStepId("");
            if (matched) {
              appendTimeline(`Element attached to step ${resolvedStepId}`, "ok");
            } else {
              appendTimeline(`Element picked but no matching step found for ${resolvedStepId}`, "warn");
            }
          } else {
            setActivePickerStepId("");
            appendTimeline(text || "Element picked", "ok");
          }
          break;
        }
        default:
          appendTimeline(text || type, "ok");
          break;
      }
    },
    [appendConversation, appendTimeline]
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
      };

      socket.onmessage = (event) => {
        if (cancelled) return;
        handleBackendMessage(normalizeBackendMessage(event.data));
      };

      socket.onerror = () => {
        if (cancelled) return;
        setConnectionStatus("reconnecting");
        appendTimeline("WebSocket error", "err");
      };

      socket.onclose = () => {
        if (cancelled) return;
        socketRef.current = null;
        setConnectionStatus("reconnecting");
        appendTimeline("Disconnected", "warn");
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
    conversation,
    timeline,
    plan,
    pendingSteps,
    correctionText,
    recordedCount,
    codePreview,
    lastError,
    lastEvent,
    wsUrl,
    activePickerStepId,
    onCorrectionTextChange: setCorrectionText,
    onPendingStepIntentChange: updatePendingStepIntent,
    onAddPendingStep: addPendingStep,
    onAttachElement: handleAttachElement,
    onRunPendingSteps: handleRunPendingSteps,
    onConfirmPlan: handleConfirmPlan,
    onSendCorrection: handleSendCorrection,
    setCorrectionText,
    setPendingSteps,
    updatePendingStepIntent,
    addPendingStep,
    handleRunPendingSteps,
    handleConfirmPlan,
    handleSendCorrection,
  };
}

function AutoWorkbenchRuntime({ config }) {
  const normalized = normalizeConfig(config);
  const transport = useAutoWorkbenchTransport(config);
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
            }}
            onTabChange={setTab}
          />
        ) : null}
      </div>
    </div>
  );
}

let currentRoot = null;
let currentNode = null;

function renderInto(node, config) {
  if (currentRoot && currentNode !== node) {
    currentRoot.unmount();
    currentRoot = null;
  }

  if (!currentRoot) {
    currentRoot = createRoot(node);
    currentNode = node;
  }

  currentRoot.render(<AutoWorkbenchRuntime config={config} />);
}

function mount(root, config = {}) {
  const node = resolveMountNode(root);
  renderInto(node, config);
  return node;
}

function unmount() {
  if (currentRoot) {
    currentRoot.unmount();
    currentRoot = null;
    currentNode = null;
  }
}

window.AutoWorkbench = {
  mount,
  unmount,
};
