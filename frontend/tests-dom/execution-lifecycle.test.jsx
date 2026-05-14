// E4 (B8/B9/B10) — execution lifecycle events feed the store and surface in the Trace tab.
//
// Pins three invariants:
//   1. Reducer stores backend-truth events into typed slices; malformed
//      payloads do NOT corrupt state (silent fail-closed).
//   2. Frontend NEVER infers an applied locator update from a click —
//      only the typed `locator_update_applied` event populates the slice.
//   3. Trace tab renders execution lifecycle events when traceEntries are
//      threaded through (kind filter "all").
import React from "react";
import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";

import { reducer, createInitialState } from "../src/store/reducer.js";
import { EVENT_TYPES } from "../src/store/types.js";
import { TraceTab } from "../src/v4/secondary-tabs.jsx";

const ev = (type, payload) => ({ type, payload });

// --------------------------------------------------------------------------- //
// Reducer
// --------------------------------------------------------------------------- //
describe("reducer execution lifecycle slices (E4)", () => {
  it("initial state slots are null", () => {
    const s = createInitialState();
    expect(s.execution_started_state).toBeNull();
    expect(s.last_operation_event).toBeNull();
    expect(s.pending_precondition).toBeNull();
    expect(s.last_locator_update).toBeNull();
  });

  it("execution_started populates state only with run_id", () => {
    let s = reducer(
      createInitialState(),
      ev(EVENT_TYPES.execution_started, { run_id: "r1", step_count: 3, source: "confirmed_plan" }),
    );
    expect(s.execution_started_state.run_id).toBe("r1");

    // Malformed payload ignored.
    s = reducer(s, ev(EVENT_TYPES.execution_started, {}));
    expect(s.execution_started_state.run_id).toBe("r1");
  });

  it("operation_executed and operation_failed both update last_operation_event with type", () => {
    let s = reducer(
      createInitialState(),
      ev(EVENT_TYPES.operation_executed, {
        run_id: "r1",
        step_id: "s1",
        operation_id: "op_0",
        action: "click",
      }),
    );
    expect(s.last_operation_event.type).toBe("operation_executed");
    s = reducer(
      s,
      ev(EVENT_TYPES.operation_failed, {
        run_id: "r1",
        step_id: "s1",
        operation_id: "op_1",
        action: "fill",
        error_summary: "x",
      }),
    );
    expect(s.last_operation_event.type).toBe("operation_failed");
    expect(s.last_operation_event.operation_id).toBe("op_1");
  });

  it("operation_executed without operation_id is dropped (B8 root-cause guard)", () => {
    const s = reducer(
      createInitialState(),
      ev(EVENT_TYPES.operation_executed, { run_id: "r", step_id: "s", action: "x" }),
    );
    expect(s.last_operation_event).toBeNull();
  });

  it("precondition_failed payload requires step_id + precondition_type", () => {
    let s = reducer(
      createInitialState(),
      ev(EVENT_TYPES.precondition_failed, {
        run_id: "r1",
        step_id: "s1",
        precondition_type: "page_url",
        expected: "a",
        actual: "b",
      }),
    );
    expect(s.pending_precondition.precondition_type).toBe("page_url");

    // Missing precondition_type → ignored.
    s = reducer(s, ev(EVENT_TYPES.precondition_failed, { run_id: "r1", step_id: "s1" }));
    expect(s.pending_precondition.precondition_type).toBe("page_url");
  });

  it("locator_update_applied requires ambiguity_id; frontend never infers applied", () => {
    let s = reducer(
      createInitialState(),
      ev(EVENT_TYPES.locator_update_applied, {
        run_id: "r1",
        step_id: "s1",
        ambiguity_id: "amb",
        old_locator: "[a]",
        new_locator: "[b]",
        strategy: "user_pick",
        confidence: 0.9,
      }),
    );
    expect(s.last_locator_update.type).toBe("locator_update_applied");
    expect(s.last_locator_update.new_locator).toBe("[b]");

    // Missing ambiguity_id is dropped — no fake "applied" state.
    s = reducer(
      s,
      ev(EVENT_TYPES.locator_update_applied, {
        run_id: "r1",
        step_id: "s1",
        new_locator: "[c]",
      }),
    );
    expect(s.last_locator_update.new_locator).toBe("[b]");
  });
});

// --------------------------------------------------------------------------- //
// Trace tab rendering
// --------------------------------------------------------------------------- //
describe("Trace tab renders execution lifecycle events (E4)", () => {
  it("renders one row per lifecycle event when fed via traceEntries", () => {
    const entries = [
      { type: "execution_started", summary: "run started", payload: { run_id: "r1" } },
      { type: "operation_executed", summary: "click ok", payload: { operation_id: "op_0" } },
      { type: "operation_failed", summary: "timeout", payload: { operation_id: "op_1" } },
      { type: "precondition_failed", summary: "wrong page", payload: { step_id: "s1" } },
      { type: "locator_update_request", summary: "ask for better locator", payload: { ambiguity_id: "amb" } },
      { type: "locator_update_applied", summary: "new locator validated", payload: { ambiguity_id: "amb" } },
    ];
    render(<TraceTab traceEntries={entries} />);
    expect(screen.queryByTestId("trace-empty")).toBeNull();
    // Every row appears in the default "all" kind filter — none are
    // swallowed by the existing chip set.
    const rows = screen.getAllByTestId(/^trace-row-/);
    expect(rows.length).toBe(entries.length);
  });

  it("malformed entries do not crash the renderer", () => {
    expect(() => {
      render(<TraceTab traceEntries={[{ type: "execution_started" }, null]} />);
    }).not.toThrow();
  });
});
