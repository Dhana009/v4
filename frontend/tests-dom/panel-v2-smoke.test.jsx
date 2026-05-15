import React from "react";
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render } from "@testing-library/react";

import { App } from "../src/panel-v2/app.jsx";
import { Header, TabStrip, Footer, NowStrip } from "../src/panel-v2/chrome.jsx";
import { LlmThread, Composer } from "../src/panel-v2/llm-tab.jsx";
import { StepsTab, RecordedTab, CodeTab, TraceTab } from "../src/panel-v2/secondary-tabs.jsx";
import { TweakSlider, TweakToggle } from "../src/panel-v2/tweaks-panel.jsx";
import { Website } from "../src/panel-v2/website.jsx";

beforeEach(() => {
  vi.spyOn(window, "postMessage").mockImplementation(() => {});
});

afterEach(() => {
  vi.restoreAllMocks();
});

const AGENT_SUMMARY = ["on", "on", "on", "off", "off"];
const TOKEN_INFO = { tok: "0", cost: "0.00" };

describe("panel-v2 smoke: App", () => {
  it("App renders without crashing", () => {
    const { container } = render(<App />);
    expect(container.firstChild).not.toBeNull();
  });

  it("App renders .aw-stage wrapper", () => {
    const { container } = render(<App />);
    expect(container.querySelector(".aw-stage")).not.toBeNull();
  });

  it("App renders .aw-panel", () => {
    const { container } = render(<App />);
    expect(container.querySelector(".aw-panel")).not.toBeNull();
  });
});

describe("panel-v2 smoke: Header", () => {
  it("Header renders without crashing", () => {
    const { container } = render(
      <Header
        status="connected"
        dock="right"
        setDock={() => {}}
        collapsed={false}
        setCollapsed={() => {}}
        tokenInfo={TOKEN_INFO}
        runState="run_a91b"
        agentsOpen={false}
        setAgentsOpen={() => {}}
        agentsSummary={AGENT_SUMMARY}
        mode="llm"
        setMode={() => {}}
      />
    );
    expect(container.querySelector(".aw-header")).not.toBeNull();
  });
});

describe("panel-v2 smoke: LLM tab", () => {
  it("LlmThread renders idle state", () => {
    const { container } = render(<LlmThread state="idle" mode="llm" />);
    expect(container.querySelector(".aw-empty")).not.toBeNull();
  });

  it("LlmThread renders planning state without crashing", () => {
    const { container } = render(<LlmThread state="planning" mode="llm" />);
    expect(container.firstChild).not.toBeNull();
  });

  it("LlmThread renders done state without crashing", () => {
    const { container } = render(<LlmThread state="done" mode="llm" />);
    expect(container.firstChild).not.toBeNull();
  });

  it("Composer renders without crashing", () => {
    const { container } = render(<Composer />);
    expect(container.querySelector(".aw-composer")).not.toBeNull();
  });
});

describe("panel-v2 smoke: secondary tabs", () => {
  it("StepsTab renders without crashing", () => {
    const { container } = render(<StepsTab mode="llm" setMode={() => {}} />);
    expect(container.firstChild).not.toBeNull();
  });

  it("RecordedTab renders without crashing", () => {
    const { container } = render(<RecordedTab />);
    expect(container.firstChild).not.toBeNull();
  });

  it("CodeTab renders without crashing", () => {
    const { container } = render(<CodeTab />);
    expect(container.firstChild).not.toBeNull();
  });

  it("TraceTab renders without crashing", () => {
    const { container } = render(<TraceTab />);
    expect(container.firstChild).not.toBeNull();
  });
});

describe("panel-v2 smoke: Website preview", () => {
  it("Website renders without crashing", () => {
    const { container } = render(<Website highlight="none" />);
    expect(container.querySelector(".aw-website")).not.toBeNull();
  });

  it("Website renders with hero-cta highlight", () => {
    const { container } = render(<Website highlight="hero-cta" />);
    expect(container.querySelector(".aw-website")).not.toBeNull();
  });
});

describe("panel-v2 smoke: TweaksPanel controls", () => {
  it("TweakSlider renders without crashing", () => {
    const { container } = render(
      <TweakSlider label="Width" value={420} min={360} max={720} step={10} unit="px" onChange={() => {}} />
    );
    expect(container.firstChild).not.toBeNull();
  });

  it("TweakToggle renders without crashing", () => {
    const { container } = render(
      <TweakToggle label="Collapsed" value={false} onChange={() => {}} />
    );
    expect(container.firstChild).not.toBeNull();
  });
});

describe("panel-v2 smoke: no old v4 involvement", () => {
  it("panel-v2/app.jsx exports App as a function", async () => {
    const mod = await import("../src/panel-v2/app.jsx");
    expect(typeof mod.App).toBe("function");
  });
});
