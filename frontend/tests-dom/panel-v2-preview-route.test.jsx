import { describe, it, expect } from "vitest";
import { readFileSync, existsSync } from "fs";
import { join } from "path";
import React from "react";
import { render, fireEvent } from "@testing-library/react";
import { App } from "../src/panel-v2/app.jsx";

const FRONTEND_ROOT = join(import.meta.dirname, "..");

describe("panel-v2 root route: index.html exists", () => {
  it("frontend/index.html exists", () => {
    expect(existsSync(join(FRONTEND_ROOT, "index.html"))).toBe(true);
  });

  it("frontend/index.html references panel-v2-preview.html", () => {
    const html = readFileSync(join(FRONTEND_ROOT, "index.html"), "utf-8");
    expect(html).toMatch(/panel-v2-preview\.html/);
  });

  it("frontend/index.html does not render old v4 app directly", () => {
    const html = readFileSync(join(FRONTEND_ROOT, "index.html"), "utf-8");
    expect(html).not.toMatch(/src\/v4\//);
    expect(html).not.toMatch(/autoworkbench\.js/);
  });
});

describe("panel-v2 root route: panel-v2 preview still renders", () => {
  it("App renders without crashing", () => {
    const { container } = render(<App />);
    expect(container.firstChild).not.toBeNull();
  });

  it("all 5 tabs are present", () => {
    const { container } = render(<App />);
    expect(container.querySelectorAll(".aw-tab").length).toBe(5);
  });

  it("LLM tab is active by default", () => {
    const { container } = render(<App />);
    const active = container.querySelector(".aw-tab.active");
    expect(active).not.toBeNull();
    expect(active.textContent).toMatch(/LLM/i);
  });

  it("clicking Steps tab activates it", () => {
    const { container } = render(<App />);
    const tabs = container.querySelectorAll(".aw-tab");
    const steps = Array.from(tabs).find((t) => t.textContent.includes("Steps"));
    fireEvent.click(steps);
    expect(steps.classList.contains("active")).toBe(true);
  });

  it("switching tabs deactivates LLM", () => {
    const { container } = render(<App />);
    const tabs = container.querySelectorAll(".aw-tab");
    const llm = Array.from(tabs).find((t) => t.textContent.includes("LLM"));
    const rec = Array.from(tabs).find((t) => t.textContent.includes("Recorded"));
    fireEvent.click(rec);
    expect(llm.classList.contains("active")).toBe(false);
  });
});
