import { PANEL_V2_VIEW_MODEL_VERSION } from "./types.js";

export const DEMO_TWEAK_DEFAULTS = {
  "tab": "llm",
  "state": "locator",
  "dock": "right",
  "panelWidth": 420,
  "collapsed": false,
  "connection": "connected",
  "showWebsite": true,
  "highlight": "hero-cta",
  "agentsOpen": false,
  "theme": "light",
  "mode": "llm",
};

export const DEMO_STATE_META = {
  idle:      { phase: "Idle",                  event: "session ready · waiting on user",  next: "Describe a flow",        conn: "connected", busy: false,
               now: { kind: "idle",   state: "Idle",                task: "Tell me what to automate or validate. I'll plan a flow before running anything.", primaryLabel: null } },
  planning:  { phase: "Analyzing page",        event: "dom_query · 814 nodes scanned",   next: "Awaiting plan",          conn: "connected", busy: true,
               now: { kind: "run",    state: "Analyzing",            task: "Page Intelligence is scanning acme.dev/pricing — 18 sections found so far.", primaryLabel: null } },
  clarify:   { phase: "Clarification needed",  event: "asked about test depth",          next: "Answer to continue",     conn: "connected", busy: false,
               now: { kind: "decide", state: "Clarification",        task: "Choose how deep this run should go — smoke, sanity, or regression.", refLabel: "step 0 of 0", primaryLabel: "Jump to question" } },
  recommend: { phase: "Recommendation review", event: "rendered 6 candidate assertions", next: "Use selected",           conn: "connected", busy: false,
               now: { kind: "decide", state: "Review",                task: "Pick which assertions to include before I draft a plan.", primaryLabel: "Use selected (5)" } },
  plan:      { phase: "Plan review",           event: "plan_ready · 6 steps · ~28s",     next: "Confirm & run",          conn: "connected", busy: false,
               now: { kind: "decide", state: "Confirm to run",        task: "Plan v2 is ready — 6 steps, ~28s, one fragile copy assertion flagged.", primaryLabel: "Confirm & run" } },
  diff:      { phase: "Plan revision",         event: "plan_v2 · +1 / -1",               next: "Apply changes",          conn: "connected", busy: false,
               now: { kind: "decide", state: "Plan diff",             task: "I drafted plan v2 with your edits — accept the changes to continue.", primaryLabel: "Apply changes" } },
  permit:    { phase: "Permission required",   event: "medium-risk click on a.btn.primary", next: "Allow or deny",       conn: "connected", busy: false,
               now: { kind: "decide", state: "Permission",            task: "Need permission for one medium-risk click before step 4 can run.", refLabel: "stp_d8e2", primaryLabel: "Allow once" } },
  exec:      { phase: "Executing",             event: "stp_c4d7 · resolving locator…",   next: "Wait or pause",          conn: "busy",      busy: true,
               now: { kind: "run",    state: "Step 3 of 6",           task: "Resolving locator for the \"Most popular\" tag in the Pro card.", refLabel: "stp_c4d7", primaryLabel: "Pause" } },
  locator:   { phase: "Locator ambiguity",     event: "3 matches for \"Get started\"",   next: "Choose candidate",       conn: "connected", busy: false, blocker: "ambiguous locator",
               now: { kind: "block",  state: "Execution paused",      task: "Three visible \"Get started\" links — pick a candidate or let me find a unique one.", refLabel: "stp_d8e2", primaryLabel: "Choose candidate" } },
  recover:   { phase: "Recovery needed",       event: "stp_e1f4 · assertion mismatch",   next: "Apply LLM repair",       conn: "connected", busy: false, blocker: "1 failed step",
               now: { kind: "block",  state: "Run blocked",           task: "Assertion failed — actual text was \"$49 /mo\". Repair, retry, or skip.", refLabel: "stp_e1f4", primaryLabel: "Apply LLM repair" } },
  done:      { phase: "Completed",             event: "run_completed · 5/6 + 1 repaired", next: "Replay or save suite", conn: "connected", busy: false,
               now: { kind: "ok",     state: "Completed",             task: "6 of 6 recorded · 1 repaired · 31.2s · paid E2E still pending.", primaryLabel: "Replay all" } },
  offline:   { phase: "Disconnected",          event: "ws closed · attempt 2 of 5",      next: "Reconnect",              conn: "offline",   busy: false, blocker: "backend unreachable",
               now: { kind: "block",  state: "Disconnected",          task: "Lost the websocket mid-step. I won't infer success or failure on my own.", primaryLabel: "Reconnect now" } },
  schema:    { phase: "Schema invalid",        event: "llm response failed plan.v3",     next: "Ask LLM to repair",      conn: "error",     busy: false, blocker: "invalid plan payload",
               now: { kind: "block",  state: "Schema invalid",        task: "Model returned an unknown operation kind. Nothing executed.", primaryLabel: "Ask LLM to repair" } },
  nobrowser: { phase: "Waiting on browser",    event: "no Playwright context attached",  next: "Launch chromium",        conn: "connected", busy: false, blocker: "no browser context",
               now: { kind: "block",  state: "Cannot start",          task: "Backend is up but there's no browser to drive. Launch one or attach an existing tab.", primaryLabel: "Launch chromium" } },
  apikey:    { phase: "Auth required",         event: "no provider key in workspace",    next: "Add API key",            conn: "connected", busy: false, blocker: "missing API key",
               now: { kind: "block",  state: "No model key",          task: "Main Orchestrator can't call the model — workspace has no key configured.", primaryLabel: "Add key" } },
  otp:       { phase: "Human input required",  event: "OTP prompt at /auth/otp",         next: "Submit code",            conn: "connected", busy: false, blocker: "awaiting OTP",
               now: { kind: "decide", state: "Awaiting OTP",          task: "Step 4 hit a 2FA prompt — type the 6-digit code from your authenticator.", refLabel: "stp_d8e2", primaryLabel: "Submit code" } },
  e2e:       { phase: "Acceptance pending",    event: "local run done · E2E queued",     next: "Wait for E2E or trigger now", conn: "connected", busy: false,
               now: { kind: "ok",     state: "Local done · E2E pending", task: "Local run is recorded, but the paid E2E suite hasn't run for this commit yet.", primaryLabel: "Trigger E2E now" } },
};

export function getDemoViewModel(tweaks) {
  const state = tweaks?.state ?? DEMO_TWEAK_DEFAULTS.state;
  const meta = DEMO_STATE_META[state] ?? DEMO_STATE_META.idle;

  return {
    _version: PANEL_V2_VIEW_MODEL_VERSION,
    mode: "demo",
    runtime: {
      phase: state,
      connection: meta.conn ?? "connected",
      runId: null,
      pageUrl: "acme.dev/pricing",
    },
    counts: {
      steps: 6,
      rec: 3,
      code: 1,
      trace: 12,
    },
    llm: {
      messages: [],
    },
    steps: [],
    recorded: [],
    code: null,
    trace: [],
  };
}
