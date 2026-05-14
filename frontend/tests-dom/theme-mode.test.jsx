// FE-VBATCH-001 Story 2 — theme toggle + narrow-panel UX.
//
// Pins:
// - Header renders the theme toggle when a setTheme callback is supplied.
// - Toggle is omitted when chrome is mounted without theme plumbing
//   (backwards compat for callers that haven't opted in yet).
// - Clicking the toggle flips light <-> dark via setTheme.
// - v4.css contains the dark-theme token block scoped to the shadow host.
// - v4.css contains the L1a narrow-panel wrap fixes (toolbar wrap,
//   step-row min-width, info-strip wrap).
// - Theme toggle has aw-theme-toggle data-testid.
import React from "react";
import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import fs from "node:fs";
import path from "node:path";

import { Header } from "../src/v4/chrome.jsx";

const V4_CSS = fs.readFileSync(path.resolve(__dirname, "../v4.css"), "utf-8");

describe("FE-VBATCH-001 theme + narrow UX", () => {
  describe("Header theme toggle", () => {
    it("renders the theme toggle when setTheme is provided", () => {
      render(<Header theme="light" setTheme={() => {}} />);
      expect(screen.getByTestId("aw-theme-toggle")).toBeInTheDocument();
    });

    it("omits the theme toggle when setTheme is missing (backwards compat)", () => {
      render(<Header theme="light" />);
      expect(screen.queryByTestId("aw-theme-toggle")).toBeNull();
    });

    it("clicking the toggle calls setTheme('dark') from 'light'", () => {
      const setTheme = vi.fn();
      render(<Header theme="light" setTheme={setTheme} />);
      fireEvent.click(screen.getByTestId("aw-theme-toggle"));
      expect(setTheme).toHaveBeenCalledWith("dark");
    });

    it("clicking the toggle calls setTheme('light') from 'dark'", () => {
      const setTheme = vi.fn();
      render(<Header theme="dark" setTheme={setTheme} />);
      fireEvent.click(screen.getByTestId("aw-theme-toggle"));
      expect(setTheme).toHaveBeenCalledWith("light");
    });

    it("reflects current theme via data-theme attribute on the button", () => {
      const { rerender } = render(<Header theme="light" setTheme={() => {}} />);
      expect(screen.getByTestId("aw-theme-toggle")).toHaveAttribute("data-theme", "light");
      rerender(<Header theme="dark" setTheme={() => {}} />);
      expect(screen.getByTestId("aw-theme-toggle")).toHaveAttribute("data-theme", "dark");
    });
  });

  describe("v4.css dark-theme token block", () => {
    it("declares :host([data-theme='dark']) selector", () => {
      expect(V4_CSS).toMatch(/:host\(\[data-theme="dark"\]\)/);
    });

    it("declares #aw-shadow-host[data-theme='dark'] selector", () => {
      expect(V4_CSS).toMatch(/#aw-shadow-host\[data-theme="dark"\]/);
    });

    it("dark-theme block overrides core color tokens", () => {
      // require at least bg-page, bg-panel, tx, acc in the dark block
      const block = V4_CSS.match(
        /:host\(\[data-theme="dark"\]\)[\s\S]*?\n}/,
      );
      expect(block, "dark-theme block must exist").not.toBeNull();
      const body = block[0];
      expect(body).toMatch(/--bg-page:\s*#/);
      expect(body).toMatch(/--bg-panel:\s*#/);
      expect(body).toMatch(/--tx:\s*#/);
      expect(body).toMatch(/--acc:\s*#/);
    });
  });

  describe("v4.css narrow-panel UX (L1a)", () => {
    it("aw-list-toolbar wraps so toolbar buttons fall to next line", () => {
      expect(V4_CSS).toMatch(/\.aw-list-toolbar[\s\S]*?flex-wrap:\s*wrap/);
    });

    it("aw-search input no longer hard-pinned at 130px width", () => {
      // The fix replaces width:130px with width:100% + flexible container.
      expect(V4_CSS).toMatch(/\.aw-search input\b[^{]*\{[^}]*width:\s*100%/);
    });

    it("aw-step-row carries min-width:0 to enable child ellipsis", () => {
      expect(V4_CSS).toMatch(/\.aw-step-row\s*>\s*\*\s*\{\s*min-width:\s*0/);
    });

    it("aw-info-strip wraps to prevent vertical squeeze on narrow dock", () => {
      expect(V4_CSS).toMatch(/\.aw-info-strip[\s\S]*?flex-wrap:\s*wrap/);
    });
  });
});
