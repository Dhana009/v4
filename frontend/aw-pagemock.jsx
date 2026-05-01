/* global React */
// Playwright-style homepage mock — LIGHT theme so the dark docked panel pops.
// Original recreation; generic dev-tool aesthetic.

function PlaywrightMock() {
  return (
    <div style={{
      width: "100%", height: "100%",
      background: "#eef0f3",
      color: "#1a1f2b",
      fontFamily: '-apple-system, "Inter", "Segoe UI", system-ui, sans-serif',
      overflow: "hidden",
      position: "relative",
      display: "flex",
      flexDirection: "column",
    }}>
      {/* Browser chrome */}
      <div style={{
        display: "flex", alignItems: "center", gap: 10, padding: "9px 14px",
        background: "#e2e5ea", borderBottom: "1px solid rgba(0,0,0,0.08)",
        fontSize: 12, color: "#5a6473", flex: "0 0 auto",
      }}>
        <div style={{ display: "flex", gap: 6 }}>
          <span style={{ width: 11, height: 11, borderRadius: "50%", background: "#ff5f57" }} />
          <span style={{ width: 11, height: 11, borderRadius: "50%", background: "#febc2e" }} />
          <span style={{ width: 11, height: 11, borderRadius: "50%", background: "#28c840" }} />
        </div>
        <div style={{ display: "flex", gap: 6, color: "#9aa1ad", fontSize: 14 }}>
          <span>‹</span><span>›</span><span style={{ marginLeft: 4 }}>↻</span>
        </div>
        <div style={{
          flex: 1, background: "#fff", border: "1px solid rgba(0,0,0,0.06)",
          padding: "6px 13px", borderRadius: 6, fontFamily: "ui-monospace, monospace",
          fontSize: 12.5, display: "flex", alignItems: "center", gap: 6, maxWidth: 520,
          color: "#1a1f2b",
        }}>
          <span style={{ color: "#1f9d6a" }}>🔒</span>
          <span style={{ color: "#9aa1ad" }}>https://</span>
          <span>playwright.dev</span>
          <span style={{ color: "#9aa1ad" }}>/</span>
        </div>
      </div>

      {/* Site header */}
      <div style={{
        display: "flex", alignItems: "center", padding: "16px 36px",
        borderBottom: "1px solid rgba(0,0,0,0.06)", flex: "0 0 auto",
        background: "#fff",
      }}>
        <div style={{ display: "flex", alignItems: "center", gap: 10, fontWeight: 700, fontSize: 17, letterSpacing: -0.2 }}>
          <div style={{
            width: 24, height: 24, borderRadius: 6,
            background: "linear-gradient(135deg, #2eb086, #1f7a5f)",
            display: "grid", placeItems: "center", color: "#fff", fontSize: 13,
          }}>▶</div>
          <span>Playwright</span>
        </div>
        <div style={{ display: "flex", gap: 28, marginLeft: 36, fontSize: 14, color: "#3a4150", fontWeight: 500 }}>
          <span>Docs</span>
          <span>API</span>
          <span>Node.js</span>
          <span>Community</span>
        </div>
        <div style={{ marginLeft: "auto", display: "flex", gap: 14, alignItems: "center", fontSize: 13 }}>
          <span style={{
            background: "#e6e8ec", border: "1px solid rgba(0,0,0,0.06)",
            padding: "6px 12px", borderRadius: 7, color: "#5a6473", fontSize: 12.5,
            display: "inline-flex", alignItems: "center", gap: 8, minWidth: 220,
          }}>
            🔍 Search docs
            <span style={{ marginLeft: "auto", fontFamily: "monospace", fontSize: 11, opacity: 0.5 }}>⌘K</span>
          </span>
          <span style={{ color: "#3a4150", fontWeight: 500 }}>GitHub</span>
        </div>
      </div>

      {/* Hero */}
      <div style={{
        flex: 1,
        display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center",
        padding: "44px 40px",
        textAlign: "center",
        background: "radial-gradient(ellipse at top, rgba(46,176,134,0.08), transparent 65%)",
      }}>
        <div style={{ fontSize: 13, color: "#1f9d6a", fontFamily: "ui-monospace, monospace", marginBottom: 14, letterSpacing: 0.06, fontWeight: 600 }}>
          BROWSER AUTOMATION FOR THE MODERN WEB
        </div>
        <h1 style={{
          fontSize: 52, fontWeight: 800, margin: 0, letterSpacing: -1.1,
          lineHeight: 1.05, maxWidth: 880, color: "#0c1322",
        }}>
          Playwright enables reliable web automation
          <br />
          <span style={{ color: "#5a6473" }}>for testing, scripting, and AI agents.</span>
        </h1>
        <p style={{
          fontSize: 17, color: "#3a4150", maxWidth: 600, margin: "20px 0 26px",
          lineHeight: 1.55,
        }}>
          Cross-browser. Cross-platform. Cross-language. One API to drive Chromium,
          Firefox, and WebKit with auto-waiting and trace viewing.
        </p>
        <div style={{ display: "flex", gap: 10 }}>
          <a style={{
            background: "#1a1f2b", color: "#fff", padding: "12px 22px", borderRadius: 7,
            fontWeight: 600, fontSize: 14.5, display: "inline-flex", alignItems: "center", gap: 8,
            textDecoration: "none",
            boxShadow: "0 1px 0 rgba(255,255,255,0.12) inset, 0 6px 16px rgba(0,0,0,0.18)",
          }}>
            Get started →
          </a>
          <a style={{
            background: "#fff", border: "1px solid rgba(0,0,0,0.1)",
            color: "#1a1f2b", padding: "11px 20px", borderRadius: 7, fontWeight: 500,
            fontSize: 14.5, textDecoration: "none",
          }}>
            View on GitHub
          </a>
        </div>

        {/* Code preview */}
        <div style={{
          marginTop: 36, width: "min(680px, 92%)",
          background: "#0e1014", borderRadius: 9, border: "1px solid rgba(0,0,0,0.1)",
          fontFamily: "ui-monospace, monospace", fontSize: 12.5, textAlign: "left",
          boxShadow: "0 18px 50px rgba(20,24,40,0.18)",
        }}>
          <div style={{
            padding: "8px 14px", borderBottom: "1px solid rgba(255,255,255,0.06)",
            display: "flex", alignItems: "center", gap: 10, color: "#a8adb8", fontSize: 11.5,
          }}>
            <span style={{ width: 9, height: 9, borderRadius: "50%", background: "#3a3f48" }} />
            <span style={{ width: 9, height: 9, borderRadius: "50%", background: "#3a3f48" }} />
            <span style={{ width: 9, height: 9, borderRadius: "50%", background: "#3a3f48" }} />
            <span style={{ marginLeft: 6 }}>example.spec.ts</span>
          </div>
          <pre style={{ margin: 0, padding: "16px 18px", lineHeight: 1.7, color: "#a8adb8" }}>
{`import { test, expect } from '@playwright/test';

test('homepage has title', async ({ page }) => {
  await page.goto('https://playwright.dev/');
  await expect(page).toHaveTitle(/Playwright/);
});`}
          </pre>
        </div>
      </div>

      {/* Feature row */}
      <div style={{
        padding: "20px 40px 24px", display: "flex", gap: 28, flex: "0 0 auto",
        borderTop: "1px solid rgba(0,0,0,0.06)", background: "#fff",
      }}>
        {[
          ["Any browser · any platform", "Test on Chromium, WebKit, and Firefox locally or in CI."],
          ["Resilient · no flaky tests", "Auto-wait removes the need for sleeps. Web-first assertions retry."],
          ["Powerful tooling", "Codegen, trace viewer, and Playwright inspector for debugging."],
        ].map(([h, b]) => (
          <div key={h} style={{ flex: 1 }}>
            <div style={{ fontSize: 14, fontWeight: 600, marginBottom: 5, color: "#0c1322" }}>{h}</div>
            <div style={{ fontSize: 12.5, color: "#5a6473", lineHeight: 1.55 }}>{b}</div>
          </div>
        ))}
      </div>
    </div>
  );
}

window.PlaywrightMock = PlaywrightMock;
