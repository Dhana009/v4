import { describe, it, expect, beforeEach, afterEach } from "vitest";

import { shouldUseV2Panel } from "../src/panel-v2-adapter/feature-flag.js";

function setSearch(search) {
  Object.defineProperty(window, "location", {
    writable: true,
    configurable: true,
    value: { ...window.location, search },
  });
}

describe("004C feature-flag: URL param", () => {
  afterEach(() => {
    setSearch("");
    localStorage.clear();
  });

  it("?panel=v2 returns true", () => {
    setSearch("?panel=v2");
    expect(shouldUseV2Panel()).toBe(true);
  });

  it("?panel=v1 returns false", () => {
    setSearch("?panel=v1");
    expect(shouldUseV2Panel()).toBe(false);
  });

  it("no param returns false by default", () => {
    setSearch("");
    expect(shouldUseV2Panel()).toBe(false);
  });
});

describe("004C feature-flag: localStorage override", () => {
  beforeEach(() => {
    localStorage.clear();
    setSearch("");
  });

  afterEach(() => {
    localStorage.clear();
    setSearch("");
  });

  it("localStorage.awPanelVersion=v2 returns true", () => {
    localStorage.setItem("awPanelVersion", "v2");
    expect(shouldUseV2Panel()).toBe(true);
  });

  it("localStorage.awPanelVersion=v1 returns false", () => {
    localStorage.setItem("awPanelVersion", "v1");
    expect(shouldUseV2Panel()).toBe(false);
  });

  it("URL param ?panel=v2 takes precedence over localStorage v1", () => {
    localStorage.setItem("awPanelVersion", "v1");
    setSearch("?panel=v2");
    expect(shouldUseV2Panel()).toBe(true);
  });
});

describe("004C feature-flag: source file audit", () => {
  it("feature-flag.js does not import from panel-v2 or panel-v2-adapter", async () => {
    const { readFileSync } = await import("fs");
    const { join } = await import("path");
    const src = readFileSync(
      join(import.meta.dirname, "../src/panel-v2-adapter/feature-flag.js"),
      "utf-8"
    );
    expect(src).not.toMatch(/from.*panel-v2\//);
    expect(src).not.toMatch(/from.*panel-v2-adapter\//);
  });
});
