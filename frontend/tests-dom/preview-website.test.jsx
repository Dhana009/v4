// FE-VBATCH-002 Story 5 — Website-behind preview (demo-only).
//
// Pins:
// - Hero CTA + Pro CTA both render.
// - `highlight="hero-cta"` accents the hero button, not the pro.
// - `highlight="pro-cta"` accents the pro button, not the hero.
// - All key ws-* sections present (topnav, hero, plans, faq, foot).
// - Module lives under src/demo/ and is not imported by production runtime.
import React from "react";
import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import fs from "node:fs";
import path from "node:path";

import { WebsitePreview } from "../src/demo/website-preview.jsx";

describe("FE-VBATCH-002 WebsitePreview (demo-only)", () => {
  it("renders the ROOT-derived sections", () => {
    const { container } = render(<WebsitePreview highlight="hero-cta" />);
    expect(screen.getByTestId("aw-website-preview")).toBeInTheDocument();
    expect(screen.getByTestId("aw-website-url")).toHaveTextContent("acme.dev/pricing");
    expect(screen.getByTestId("aw-website-hero-cta")).toHaveTextContent("Get started");
    expect(screen.getByTestId("aw-website-pro-cta")).toHaveTextContent("Start free trial");
    // ws-* landmarks
    for (const klass of [
      ".ws-bar",
      ".ws-topnav",
      ".ws-hero",
      ".ws-plans",
      ".ws-plan.featured",
      ".ws-faq",
      ".ws-foot",
    ]) {
      expect(container.querySelector(klass), `missing ${klass}`).not.toBeNull();
    }
  });

  it("highlight='hero-cta' accents hero CTA only", () => {
    render(<WebsitePreview highlight="hero-cta" />);
    expect(screen.getByTestId("aw-website-hero-cta").className).toMatch(/highlight/);
    expect(screen.getByTestId("aw-website-pro-cta").className).not.toMatch(/highlight/);
  });

  it("highlight='pro-cta' accents pro CTA only", () => {
    render(<WebsitePreview highlight="pro-cta" />);
    expect(screen.getByTestId("aw-website-pro-cta").className).toMatch(/highlight/);
    expect(screen.getByTestId("aw-website-hero-cta").className).not.toMatch(/highlight/);
  });

  it("highlight='none' accents nothing", () => {
    render(<WebsitePreview highlight="none" />);
    expect(screen.getByTestId("aw-website-hero-cta").className).not.toMatch(/highlight/);
    expect(screen.getByTestId("aw-website-pro-cta").className).not.toMatch(/highlight/);
  });

  it("source file is quarantined under src/demo/", () => {
    const filePath = path.resolve(__dirname, "../src/demo/website-preview.jsx");
    expect(fs.existsSync(filePath)).toBe(true);
  });

  it("no production runtime source imports website-preview.jsx", () => {
    const PRODUCTION_SOURCES = [
      "aw-ide-panel.jsx",
      "src/v4/chrome.jsx",
      "src/v4/llm-cards.jsx",
      "src/v4/secondary-tabs.jsx",
      "src/store/reducer.js",
      "src/commands/dispatcher.js",
    ];
    for (const rel of PRODUCTION_SOURCES) {
      const src = fs.readFileSync(path.resolve(__dirname, "..", rel), "utf-8");
      const codeOnly = src
        .split("\n")
        .map((line) => line.replace(/\/\/.*$/, ""))
        .join("\n")
        .replace(/\/\*[\s\S]*?\*\//g, "");
      expect(codeOnly, `${rel} must not import website-preview`).not.toMatch(/website-preview/);
    }
  });
});
