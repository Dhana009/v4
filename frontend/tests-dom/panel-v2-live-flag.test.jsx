import { describe, it, expect } from "vitest";

describe("S5 main.jsx source audit", () => {
  it("main.jsx imports shouldUseV2Panel", async () => {
    const { readFileSync } = await import("fs");
    const { join } = await import("path");
    const src = readFileSync(
      join(import.meta.dirname, "../src/main.jsx"),
      "utf-8"
    );
    expect(src).toMatch(/shouldUseV2Panel/);
  });

  it("main.jsx imports PanelV2LiveHost", async () => {
    const { readFileSync } = await import("fs");
    const { join } = await import("path");
    const src = readFileSync(
      join(import.meta.dirname, "../src/main.jsx"),
      "utf-8"
    );
    expect(src).toMatch(/PanelV2LiveHost/);
  });

  it("main.jsx calls shouldUseV2Panel() (invoked, not just imported)", async () => {
    const { readFileSync } = await import("fs");
    const { join } = await import("path");
    const src = readFileSync(
      join(import.meta.dirname, "../src/main.jsx"),
      "utf-8"
    );
    expect(src).toMatch(/shouldUseV2Panel\(\)/);
  });

  it("main.jsx conditionally renders PanelV2LiveHost", async () => {
    const { readFileSync } = await import("fs");
    const { join } = await import("path");
    const src = readFileSync(
      join(import.meta.dirname, "../src/main.jsx"),
      "utf-8"
    );
    expect(src).toMatch(/<PanelV2LiveHost/);
  });
});

describe("S5 live-host.jsx source audit", () => {
  it("live-host.jsx does not import demo-bridge", async () => {
    const { readFileSync } = await import("fs");
    const { join } = await import("path");
    const src = readFileSync(
      join(import.meta.dirname, "../src/panel-v2-adapter/live-host.jsx"),
      "utf-8"
    );
    expect(src).not.toMatch(/demo-bridge/);
  });

  it("live-host.jsx passes viewModel prop to App", async () => {
    const { readFileSync } = await import("fs");
    const { join } = await import("path");
    const src = readFileSync(
      join(import.meta.dirname, "../src/panel-v2-adapter/live-host.jsx"),
      "utf-8"
    );
    expect(src).toMatch(/viewModel/);
  });

  it("live-host.jsx passes mode='live' to App", async () => {
    const { readFileSync } = await import("fs");
    const { join } = await import("path");
    const src = readFileSync(
      join(import.meta.dirname, "../src/panel-v2-adapter/live-host.jsx"),
      "utf-8"
    );
    expect(src).toMatch(/mode=.live/);
  });

  it("live-host.jsx passes onCommand prop to App", async () => {
    const { readFileSync } = await import("fs");
    const { join } = await import("path");
    const src = readFileSync(
      join(import.meta.dirname, "../src/panel-v2-adapter/live-host.jsx"),
      "utf-8"
    );
    expect(src).toMatch(/onCommand/);
  });
});
