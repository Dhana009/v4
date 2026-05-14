// FE-VBATCH-002 Story 3 — composer parity with yui ROOT reference.
//
// Pins:
// - Context chips render only when context prop is non-empty.
// - Pick (Mouse) stays live-wired to `arm_picker`.
// - Paperclip + Camera render but stay disabled with sprint-8 reason.
// - Model badge renders when prop supplied; absent otherwise.
// - Send dispatches user_message.
import React from "react";
import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { Composer } from "../src/v4/llm-cards.jsx";

describe("FE-VBATCH-002 Composer reference port", () => {
  it("context chips render from prop with icon + label", () => {
    render(
      <Composer
        context={[
          { id: "url", icon: "Globe", label: "/pricing" },
          { id: "selection", icon: "Target", label: "2 selected" },
          { id: "doc", icon: "Doc", label: "users.csv" },
        ]}
      />,
    );
    expect(screen.getByTestId("aw-composer-chips")).toBeInTheDocument();
    expect(screen.getByTestId("aw-composer-chip-url")).toHaveTextContent("/pricing");
    expect(screen.getByTestId("aw-composer-chip-selection")).toHaveTextContent("2 selected");
    expect(screen.getByTestId("aw-composer-chip-doc")).toHaveTextContent("users.csv");
  });

  it("no chips when context prop is empty (no fake live chips)", () => {
    render(<Composer context={[]} />);
    expect(screen.queryByTestId("aw-composer-chips")).toBeNull();
  });

  it("paperclip + camera disabled with sprint-8 deferred reason (no fake live actions)", () => {
    render(<Composer />);
    const att = screen.getByTestId("aw-composer-attach");
    const cam = screen.getByTestId("aw-composer-camera");
    expect(att).toBeDisabled();
    expect(cam).toBeDisabled();
    expect(att).toHaveAttribute("data-disabled-reason", "sprint-8");
    expect(cam).toHaveAttribute("data-disabled-reason", "sprint-8");
  });

  it("Pick (Mouse) stays live-wired and dispatches arm_picker", () => {
    const onPickElement = vi.fn();
    render(<Composer onPickElement={onPickElement} />);
    fireEvent.click(screen.getByTestId("aw-composer-pick"));
    expect(onPickElement).toHaveBeenCalledWith(expect.objectContaining({ type: "arm_picker" }));
  });

  it("model badge renders only when modelBadge prop is set", () => {
    const { rerender } = render(<Composer />);
    expect(screen.queryByTestId("aw-composer-model")).toBeNull();
    rerender(<Composer modelBadge="complete-llm · gpt-class" />);
    expect(screen.getByTestId("aw-composer-model")).toHaveTextContent("complete-llm · gpt-class");
  });

  it("typing + Enter sends user_message via onSend", () => {
    const onSend = vi.fn();
    render(<Composer onSend={onSend} />);
    const ta = screen.getByTestId("aw-composer-input");
    fireEvent.change(ta, { target: { value: "hello world" } });
    fireEvent.keyDown(ta, { key: "Enter" });
    expect(onSend).toHaveBeenCalledWith(
      expect.objectContaining({ type: "user_message", message_text: "hello world" }),
    );
  });
});
