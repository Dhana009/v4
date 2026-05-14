// E1 (B1) — AgentsPopover renders from backend agent_settings payload only.
// Plan ref: .tasks-md/Planning/S7-CROSS-LAYER-COMPLETION-PLAN.md
// Companion spec: autoworkbench_complete_llm_mode_runtime_policy_spec.md
//
// These tests pin three honest-UI invariants:
//   1. The reducer treats agent_settings as the only source of truth for
//      `state.agents`. No DEFAULT_AGENTS fallback may exist anywhere.
//   2. Stale (lower-version) payloads are ignored — optimistic concurrency.
//   3. The popover toggle is disabled in read_only control_mode and
//      enabled in writable control_mode. No fake activity ever.
import React from "react";
import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";

import { reducer, createInitialState } from "../src/store/reducer.js";
import { EVENT_TYPES } from "../src/store/types.js";
import { AgentsPopover } from "../src/v4/chrome.jsx";

const SAMPLE_PAYLOAD = {
  version: 1,
  control_mode: "read_only",
  agents: [
    {
      key: "orchestrator",
      name: "Main Orchestrator",
      required: true,
      enabled: true,
      model_class: "live",
      status: "active",
      last_activity_at: null,
    },
    {
      key: "page_intelligence",
      name: "Page Intelligence",
      required: false,
      enabled: true,
      model_class: "live",
      status: "standby",
      last_activity_at: null,
    },
  ],
};

describe("reducer agent_settings (E1/B1)", () => {
  it("initial state has no fabricated agents", () => {
    const s = createInitialState();
    expect(s.agents).toBeNull();
    expect(s.agents_version).toBe(0);
    expect(s.agents_control_mode).toBe("read_only");
  });

  it("agent_settings replaces state.agents from payload", () => {
    const s = reducer(createInitialState(), {
      type: EVENT_TYPES.agent_settings,
      payload: SAMPLE_PAYLOAD,
    });
    expect(Array.isArray(s.agents)).toBe(true);
    expect(s.agents).toHaveLength(2);
    expect(s.agents_version).toBe(1);
    expect(s.agents_control_mode).toBe("read_only");
  });

  it("stale lower-version agent_settings is ignored", () => {
    let s = reducer(createInitialState(), {
      type: EVENT_TYPES.agent_settings,
      payload: { ...SAMPLE_PAYLOAD, version: 5 },
    });
    const before = s.agents;
    s = reducer(s, {
      type: EVENT_TYPES.agent_settings,
      payload: { ...SAMPLE_PAYLOAD, version: 2 },
    });
    expect(s.agents).toBe(before);
    expect(s.agents_version).toBe(5);
  });

  it("equal-version agent_settings does NOT regress state (idempotent)", () => {
    let s = reducer(createInitialState(), {
      type: EVENT_TYPES.agent_settings,
      payload: SAMPLE_PAYLOAD,
    });
    s = reducer(s, {
      type: EVENT_TYPES.agent_settings,
      payload: SAMPLE_PAYLOAD,
    });
    expect(s.agents).toHaveLength(2);
    expect(s.agents_version).toBe(1);
  });
});

describe("AgentsPopover with backend payload (E1/B1)", () => {
  it("renders rows from payload with no fabricated extras", () => {
    render(<AgentsPopover agents={SAMPLE_PAYLOAD.agents} controlMode="read_only" />);
    expect(screen.getByTestId("aw-agent-row-orchestrator")).toBeInTheDocument();
    expect(screen.getByTestId("aw-agent-row-page_intelligence")).toBeInTheDocument();
    // No leaked mock/default keys
    expect(screen.queryByTestId("aw-agent-row-orch")).toBeNull();
    expect(screen.queryByTestId("aw-agent-row-sr")).toBeNull();
    expect(screen.queryByTestId("aw-agent-row-dbg")).toBeNull();
  });

  it("required agent toggle is locked regardless of control_mode", () => {
    render(<AgentsPopover agents={SAMPLE_PAYLOAD.agents} controlMode="writable" />);
    // required-row uses a locked-on visual; we just assert the writable
    // toggle test-id is missing for the orchestrator (it gets the locked button instead).
    expect(screen.queryByTestId("aw-agent-toggle-orchestrator")).toBeNull();
  });

  it("non-required agent toggle is disabled when control_mode is read_only", () => {
    render(<AgentsPopover agents={SAMPLE_PAYLOAD.agents} controlMode="read_only" />);
    expect(screen.getByTestId("aw-agent-toggle-page_intelligence")).toBeDisabled();
  });

  it("non-required agent toggle is enabled when control_mode is writable", () => {
    render(<AgentsPopover agents={SAMPLE_PAYLOAD.agents} controlMode="writable" />);
    expect(screen.getByTestId("aw-agent-toggle-page_intelligence")).not.toBeDisabled();
  });

  it("empty payload still renders honest empty state", () => {
    render(<AgentsPopover agents={[]} controlMode="read_only" />);
    expect(screen.getByTestId("aw-agents-empty")).toBeInTheDocument();
  });
});
