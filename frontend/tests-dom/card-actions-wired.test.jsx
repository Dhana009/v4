// E3 — wired LLM card actions. No clickable no-ops left.
//
// Pins the contract for the 5 controls cleared in this batch:
//   1. CardLocatorAmbiguity → Highlight candidate dispatches `highlight_locator`.
//   2. CardOffline         → View log routes to Trace tab.
//   3. CardOffline         → Switch endpoint disabled with reason when only
//                           the current endpoint is registered.
//   4. CardSchemaError     → Edit plan manually opens a textarea, submit
//                           dispatches the existing `correction` command.
//   5. CardSchemaError     → Open raw response toggles a redacted <pre>;
//                           disabled-with-reason when payload has no raw.
import React from "react";
import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";

import {
  CardLocatorAmbiguity,
  CardOffline,
  CardSchemaError,
} from "../src/v4/llm-cards.jsx";
import { reducer, createInitialState } from "../src/store/reducer.js";
import { EVENT_TYPES } from "../src/store/types.js";

// --------------------------------------------------------------------------- //
// CardLocatorAmbiguity → Highlight
// --------------------------------------------------------------------------- //
describe("CardLocatorAmbiguity Highlight (E3/B3)", () => {
  const ambiguity = {
    step_id: "step-1",
    candidates: [
      { id: "cand-a", title: "first match", locator: "[data-x]" },
      { id: "cand-b", title: "second match", locator: "[data-y]" },
    ],
  };

  it("renders one highlight button per candidate with stable testids", () => {
    render(<CardLocatorAmbiguity ambiguity={ambiguity} />);
    expect(screen.getByTestId("locator-highlight-cand-a")).toBeInTheDocument();
    expect(screen.getByTestId("locator-highlight-cand-b")).toBeInTheDocument();
  });

  it("highlight button is disabled (with reason) when no onHighlight dispatcher", () => {
    render(<CardLocatorAmbiguity ambiguity={ambiguity} />);
    const btn = screen.getByTestId("locator-highlight-cand-a");
    expect(btn).toBeDisabled();
    expect(btn.getAttribute("title") || "").toMatch(/not wired/i);
  });

  it("dispatches typed highlight_locator with candidate_id + step_id", () => {
    const onHighlight = vi.fn();
    render(<CardLocatorAmbiguity ambiguity={ambiguity} onHighlight={onHighlight} />);
    fireEvent.click(screen.getByTestId("locator-highlight-cand-b"));
    expect(onHighlight).toHaveBeenCalledWith({
      type: "highlight_locator",
      candidate_id: "cand-b",
      step_id: "step-1",
    });
  });

  it("highlight click does not also select the candidate (event isolated)", () => {
    const onChoose = vi.fn();
    const onHighlight = vi.fn();
    render(
      <CardLocatorAmbiguity
        ambiguity={ambiguity}
        onChoose={onChoose}
        onHighlight={onHighlight}
      />,
    );
    fireEvent.click(screen.getByTestId("locator-highlight-cand-a"));
    // onChoose dispatches via the "Use candidate" button, not Highlight.
    expect(onChoose).not.toHaveBeenCalled();
  });
});

// --------------------------------------------------------------------------- //
// CardOffline → View log + Switch endpoint
// --------------------------------------------------------------------------- //
describe("CardOffline action wiring (E3/B4 + B5)", () => {
  const connection = { connected: false, last_event: "step_executing" };

  it("view-log button is disabled with reason when no dispatcher", () => {
    render(<CardOffline connection={connection} />);
    const btn = screen.getByTestId("offline-view-log");
    expect(btn).toBeDisabled();
    expect(btn.getAttribute("title") || "").toMatch(/Trace tab routing/i);
  });

  it("view-log dispatches view_connection_log when wired", () => {
    const onViewLog = vi.fn();
    render(<CardOffline connection={connection} onViewLog={onViewLog} />);
    fireEvent.click(screen.getByTestId("offline-view-log"));
    expect(onViewLog).toHaveBeenCalledWith({ type: "view_connection_log" });
  });

  it("switch-endpoint disabled with reason when only the active endpoint exists", () => {
    const onSwitch = vi.fn();
    render(
      <CardOffline
        connection={connection}
        onSwitchEndpoint={onSwitch}
        endpointRegistry={{
          active_id: "local",
          entries: [{ id: "local", label: "Local", base_url: "ws://x", kind: "local" }],
        }}
      />,
    );
    const btn = screen.getByTestId("offline-switch-endpoint");
    expect(btn).toBeDisabled();
    expect(btn.getAttribute("title") || "").toMatch(/Only the local endpoint/i);
    fireEvent.click(btn);
    expect(onSwitch).not.toHaveBeenCalled();
  });

  it("switch-endpoint enabled only when an alternate endpoint exists; dispatch sends id only (no URL)", () => {
    const onSwitch = vi.fn();
    render(
      <CardOffline
        connection={connection}
        onSwitchEndpoint={onSwitch}
        endpointRegistry={{
          active_id: "local",
          entries: [
            { id: "local", label: "Local", base_url: "ws://x", kind: "local" },
            { id: "staging", label: "Staging", base_url: "ws://y", kind: "staging" },
          ],
        }}
      />,
    );
    const btn = screen.getByTestId("offline-switch-endpoint");
    expect(btn).not.toBeDisabled();
    fireEvent.click(btn);
    expect(onSwitch).toHaveBeenCalledWith({
      type: "switch_endpoint",
      endpoint_id: "staging",
    });
    // Sanity: dispatched payload must NOT carry a raw URL (SSRF guard).
    expect(onSwitch.mock.calls[0][0]).not.toHaveProperty("base_url");
    expect(onSwitch.mock.calls[0][0]).not.toHaveProperty("url");
  });
});

// --------------------------------------------------------------------------- //
// CardSchemaError → Edit plan manually + Open raw
// --------------------------------------------------------------------------- //
describe("CardSchemaError action wiring (E3/B6 + B7)", () => {
  it("edit-plan disabled with reason when no correction dispatcher", () => {
    render(<CardSchemaError rejection={{ reason: "schema_invalid" }} />);
    const btn = screen.getByTestId("schema-error-edit-plan");
    expect(btn).toBeDisabled();
    expect(btn.getAttribute("title") || "").toMatch(/not wired/i);
  });

  it("edit-plan opens a textarea and submit dispatches the existing correction command", () => {
    const onEdit = vi.fn();
    render(
      <CardSchemaError
        rejection={{ reason: "schema_invalid" }}
        onEditPlan={onEdit}
      />,
    );
    fireEvent.click(screen.getByTestId("schema-error-edit-plan"));
    const ta = screen.getByTestId("schema-error-edit-input");
    fireEvent.change(ta, { target: { value: "Drop the extra clarify step" } });
    fireEvent.click(screen.getByTestId("schema-error-edit-submit"));
    expect(onEdit).toHaveBeenCalledWith({
      type: "correction",
      message: "Drop the extra clarify step",
      source: "manual_edit",
    });
  });

  it("edit-plan submit is disabled until the textarea has non-empty text", () => {
    render(
      <CardSchemaError
        rejection={{ reason: "schema_invalid" }}
        onEditPlan={() => {}}
      />,
    );
    fireEvent.click(screen.getByTestId("schema-error-edit-plan"));
    expect(screen.getByTestId("schema-error-edit-submit")).toBeDisabled();
  });

  it("open-raw disabled (with reason) when payload has no raw_response_redacted", () => {
    render(<CardSchemaError rejection={{ reason: "schema_invalid" }} />);
    const btn = screen.getByTestId("schema-error-open-raw");
    expect(btn).toBeDisabled();
    expect(btn.getAttribute("title") || "").toMatch(/did not retain/i);
  });

  it("open-raw toggles a redacted <pre> when payload carries raw_response_redacted", () => {
    render(
      <CardSchemaError
        rejection={{
          reason: "schema_invalid",
          raw_response_redacted: "{\"tool\":\"foo\",\"api_key\":\"[REDACTED]\"}",
        }}
      />,
    );
    expect(screen.queryByTestId("schema-error-raw-viewer")).toBeNull();
    fireEvent.click(screen.getByTestId("schema-error-open-raw"));
    const viewer = screen.getByTestId("schema-error-raw-viewer");
    expect(viewer).toBeInTheDocument();
    // Body must not contain any sk-* literal.
    expect(viewer.textContent || "").not.toMatch(/sk-[A-Za-z0-9]{8,}/);
  });
});

// --------------------------------------------------------------------------- //
// Reducer: endpoint_registry slice
// --------------------------------------------------------------------------- //
describe("reducer endpoint_registry slice (E3/B5)", () => {
  it("initial state is null", () => {
    expect(createInitialState().endpoint_registry).toBeNull();
  });

  it("ignores payload without entries[] or active_id", () => {
    const s = reducer(createInitialState(), {
      type: EVENT_TYPES.endpoint_registry,
      payload: {},
    });
    expect(s.endpoint_registry).toBeNull();
  });

  it("stores active_id + entries from real payload", () => {
    const s = reducer(createInitialState(), {
      type: EVENT_TYPES.endpoint_registry,
      payload: {
        active_id: "local",
        entries: [{ id: "local", label: "Local", base_url: "ws://x" }],
      },
    });
    expect(s.endpoint_registry.active_id).toBe("local");
    expect(s.endpoint_registry.entries).toHaveLength(1);
  });
});
