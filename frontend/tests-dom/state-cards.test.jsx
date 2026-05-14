// E2 (B2) — backend-driven state cards render only from real events.
//
// Pins three honest-UI invariants per card:
//   1. Card does not render when no event payload is present.
//   2. Card renders correctly from a real backend payload.
//   3. Actions either dispatch a typed command when wired or are
//      disabled with a real reason — no stub onClick.
//
// Security:
//   - No card embeds or surfaces an actual API key / OTP / password.
//   - CardOtp guards on payload.sensitive === true so a malformed
//     reducer state cannot silently drop redaction.
//   - The OTP card explicitly tells the user NOT to paste the value.
import React from "react";
import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";

import {
  CardNoBrowser,
  CardApiKey,
  CardOtp,
  CardE2EPending,
  LlmThread,
} from "../src/v4/llm-cards.jsx";
import { reducer, createInitialState } from "../src/store/reducer.js";
import { EVENT_TYPES } from "../src/store/types.js";

// --------------------------------------------------------------------------- //
// Reducer
// --------------------------------------------------------------------------- //
describe("reducer state-card slices (E2/B2)", () => {
  it("initial state has all four slices null", () => {
    const s = createInitialState();
    expect(s.no_browser_state).toBeNull();
    expect(s.api_key_required_state).toBeNull();
    expect(s.human_input_required_state).toBeNull();
    expect(s.e2e_pending_state).toBeNull();
  });

  it("no_browser event populates slice; absent reason clears", () => {
    let s = reducer(createInitialState(), {
      type: EVENT_TYPES.no_browser,
      payload: { reason: "crashed", recoverable: false, message: "x" },
    });
    expect(s.no_browser_state.reason).toBe("crashed");
    s = reducer(s, { type: EVENT_TYPES.no_browser, payload: {} });
    expect(s.no_browser_state).toBeNull();
  });

  it("api_key_required ignores payload without provider", () => {
    const s = reducer(createInitialState(), {
      type: EVENT_TYPES.api_key_required,
      payload: { reason: "missing" },
    });
    expect(s.api_key_required_state).toBeNull();
  });

  it("human_input_required REQUIRES sensitive=true; falsy guards it", () => {
    const malformed = reducer(createInitialState(), {
      type: EVENT_TYPES.human_input_required,
      payload: { input_type: "otp", prompt: "x", sensitive: false },
    });
    expect(malformed.human_input_required_state).toBeNull();

    const ok = reducer(createInitialState(), {
      type: EVENT_TYPES.human_input_required,
      payload: { input_type: "otp", prompt: "x", correlation_id: "h1", sensitive: true },
    });
    expect(ok.human_input_required_state.input_type).toBe("otp");
  });

  it("e2e_pending requires reason", () => {
    const s = reducer(createInitialState(), {
      type: EVENT_TYPES.e2e_pending,
      payload: { pending_tests: ["a"] },
    });
    expect(s.e2e_pending_state).toBeNull();
  });
});

// --------------------------------------------------------------------------- //
// CardNoBrowser
// --------------------------------------------------------------------------- //
describe("CardNoBrowser (E2/B2)", () => {
  it("renders nothing when state is null", () => {
    const { container } = render(<CardNoBrowser state={null} />);
    expect(container.firstChild).toBeNull();
  });

  it("renders message, url and disabled action when no relaunch seam", () => {
    render(
      <CardNoBrowser
        state={{
          reason: "crashed",
          recoverable: true,
          message: "Browser context crashed.",
          current_url: "https://example.com/app",
        }}
      />,
    );
    expect(screen.getByTestId("card-no-browser")).toBeInTheDocument();
    expect(screen.getByTestId("no-browser-message")).toHaveTextContent(
      "Browser context crashed.",
    );
    expect(screen.getByTestId("no-browser-url")).toHaveTextContent("example.com/app");
    expect(screen.getByTestId("no-browser-action")).toBeDisabled();
  });

  it("enables relaunch when dispatcher is provided", () => {
    const onRelaunch = vi.fn();
    render(
      <CardNoBrowser
        state={{ reason: "not_launched", recoverable: true, message: "x" }}
        onRelaunchBrowser={onRelaunch}
      />,
    );
    const btn = screen.getByTestId("no-browser-action");
    expect(btn).not.toBeDisabled();
    fireEvent.click(btn);
    expect(onRelaunch).toHaveBeenCalledWith({ type: "relaunch_browser" });
  });

  it("keeps action disabled when payload marks unrecoverable", () => {
    const onRelaunch = vi.fn();
    render(
      <CardNoBrowser
        state={{ reason: "fatal", recoverable: false, message: "x" }}
        onRelaunchBrowser={onRelaunch}
      />,
    );
    expect(screen.getByTestId("no-browser-action")).toBeDisabled();
  });
});

// --------------------------------------------------------------------------- //
// CardApiKey
// --------------------------------------------------------------------------- //
describe("CardApiKey (E2/B2)", () => {
  it("renders nothing without state", () => {
    const { container } = render(<CardApiKey state={null} />);
    expect(container.firstChild).toBeNull();
  });

  it("surfaces provider name and missing env vars only (never the key)", () => {
    render(
      <CardApiKey
        state={{
          provider: "openai",
          reason: "missing",
          message: "Provider 'openai' requires an API key.",
          missing_config_keys: ["OPENAI_API_KEY"],
          setup_hint: { url: "https://platform.openai.com/keys" },
        }}
      />,
    );
    expect(screen.getByTestId("api-key-provider")).toHaveTextContent("openai");
    expect(screen.getByTestId("api-key-missing-keys")).toHaveTextContent(
      "OPENAI_API_KEY",
    );
    // The entire card body must NEVER contain a literal sk-* secret.
    const card = screen.getByTestId("card-api-key");
    expect(card.textContent || "").not.toMatch(/sk-[A-Za-z0-9]{8,}/);
  });

  it("action disabled when no recheck dispatcher", () => {
    render(
      <CardApiKey state={{ provider: "openai", reason: "missing", message: "x" }} />,
    );
    expect(screen.getByTestId("api-key-recheck")).toBeDisabled();
  });

  it("action dispatches recheck when wired", () => {
    const onRecheck = vi.fn();
    render(
      <CardApiKey
        state={{ provider: "openai", reason: "invalid", message: "x" }}
        onRecheckConfig={onRecheck}
      />,
    );
    fireEvent.click(screen.getByTestId("api-key-recheck"));
    expect(onRecheck).toHaveBeenCalledWith({ type: "recheck_config" });
  });
});

// --------------------------------------------------------------------------- //
// CardOtp / human-input
// --------------------------------------------------------------------------- //
describe("CardOtp (E2/B2)", () => {
  it("renders nothing without sensitive=true (refuses to drop redaction)", () => {
    const { container } = render(
      <CardOtp state={{ input_type: "otp", prompt: "x", sensitive: false }} />,
    );
    expect(container.firstChild).toBeNull();
  });

  it("renders the prompt and a safety note telling the user NOT to paste here", () => {
    render(
      <CardOtp
        state={{
          input_type: "otp",
          prompt: "Enter the 6-digit code in the auth tab.",
          correlation_id: "hin-1",
          sensitive: true,
          redaction_required: true,
          origin: "https://login.example.com",
        }}
      />,
    );
    expect(screen.getByTestId("otp-prompt")).toHaveTextContent("Enter the 6-digit");
    expect(screen.getByTestId("otp-origin")).toHaveTextContent("login.example.com");
    expect(screen.getByTestId("otp-safety-note").textContent || "").toMatch(
      /Do not paste the code/i,
    );
  });

  it("never accepts an input element for the secret value", () => {
    render(
      <CardOtp
        state={{
          input_type: "otp",
          prompt: "x",
          correlation_id: "hin-2",
          sensitive: true,
        }}
      />,
    );
    const card = screen.getByTestId("card-otp");
    expect(card.querySelector("input")).toBeNull();
    expect(card.querySelector("textarea")).toBeNull();
  });

  it("continue action passes correlation_id without any secret", () => {
    const onContinue = vi.fn();
    render(
      <CardOtp
        state={{
          input_type: "otp",
          prompt: "x",
          correlation_id: "hin-9",
          sensitive: true,
        }}
        onContinue={onContinue}
      />,
    );
    fireEvent.click(screen.getByTestId("otp-continue"));
    expect(onContinue).toHaveBeenCalledWith({
      type: "human_input_completed",
      correlation_id: "hin-9",
    });
  });
});

// --------------------------------------------------------------------------- //
// CardE2EPending
// --------------------------------------------------------------------------- //
describe("CardE2EPending (E2/B2)", () => {
  it("renders nothing without reason", () => {
    const { container } = render(<CardE2EPending state={null} />);
    expect(container.firstChild).toBeNull();
  });

  it("renders pending tests, status, and command hint", () => {
    render(
      <CardE2EPending
        state={{
          reason: "acceptance_gate",
          pending_tests: ["test_a", "test_b"],
          last_result_summary: "2 / 2 passed",
          command_hint: "python -m pytest tests/e2e -q",
        }}
      />,
    );
    expect(screen.getByTestId("card-e2e-pending")).toBeInTheDocument();
    expect(screen.getByTestId("e2e-pending-status")).toHaveTextContent("2 / 2 passed");
    expect(screen.getByTestId("e2e-pending-hint")).toHaveTextContent("pytest");
    // The card has no action button — it is advisory only.
    expect(
      screen.getByTestId("card-e2e-pending").querySelector("button"),
    ).toBeNull();
  });
});

// --------------------------------------------------------------------------- //
// LlmThread integration: cards do not appear when state is empty
// --------------------------------------------------------------------------- //
describe("LlmThread state-card gating (E2/B2)", () => {
  it("does not render any state card when idle store is fed", () => {
    render(<LlmThread />);
    expect(screen.queryByTestId("card-no-browser")).toBeNull();
    expect(screen.queryByTestId("card-api-key")).toBeNull();
    expect(screen.queryByTestId("card-otp")).toBeNull();
    expect(screen.queryByTestId("card-e2e-pending")).toBeNull();
  });

  it("renders no_browser card when slice is populated", () => {
    render(
      <LlmThread
        noBrowserState={{ reason: "crashed", recoverable: false, message: "x" }}
      />,
    );
    expect(screen.getByTestId("card-no-browser")).toBeInTheDocument();
  });

  it("rendering a state card overrides the empty welcome", () => {
    render(
      <LlmThread
        e2ePendingState={{
          reason: "browser_warming",
          pending_tests: [],
          last_result_summary: null,
        }}
      />,
    );
    expect(screen.queryByTestId("aw-llm-empty")).toBeNull();
    expect(screen.getByTestId("card-e2e-pending")).toBeInTheDocument();
  });
});
