// FE-VBATCH-002 Story 5 — Website-behind preview (demo-only).
//
// Ports the yui ROOT `website.jsx` mock acme.dev/pricing page so the
// preview entry has a real page behind the panel for visual parity with
// AutoWorkbench.html. Self-contained: bundles its own styles via a
// `<style>` tag scoped to the `.aw-website` root so it cannot leak into
// the live host page.
//
// HARD CONSTRAINT: demo-only. Live runtime never imports or renders this
// module. The host page in production is the real site under test.

import React from "react";

export function WebsitePreview({ highlight = "hero-cta" }) {
  return (
    <div className="aw-website" data-testid="aw-website-preview">
      <style>{WEBSITE_CSS}</style>
      <div className="ws-bar">
        <span className="btn">←</span>
        <span className="btn">→</span>
        <span className="btn">⟳</span>
        <span className="url" data-testid="aw-website-url">acme.dev/pricing</span>
        <div className="tabs">
          <span className="ws-tab">Pricing — Acme</span>
        </div>
      </div>

      <nav className="ws-topnav">
        <span className="logo">Acme</span>
        <span className="topnav-links">
          <a>Product</a>
          <a>Solutions</a>
          <a>Docs</a>
          <a className="active">Pricing</a>
          <a>Changelog</a>
        </span>
        <span className="right">
          <a className="signin">Sign in</a>
          <a className={"cta" + (highlight === "hero-cta" ? "" : "")} data-testid="aw-website-signin-cta">
            Get started
          </a>
        </span>
      </nav>

      <section className="ws-hero">
        <span className="ws-eyebrow">PRICING</span>
        <h1 className="ws-h1">
          Plans that scale with your <em>QA team</em>, not your headcount.
        </h1>
        <p className="ws-sub">
          Start free. Add seats when you need them. Cancel anytime — no card required.
        </p>
        <div className="ws-hero-ctas">
          <a
            className={"btn primary" + (highlight === "hero-cta" ? " highlight" : "")}
            data-testid="aw-website-hero-cta"
          >
            Get started
            {highlight === "hero-cta" ? <span className="pulse" /> : null}
          </a>
          <a className="btn ghost">Talk to sales</a>
        </div>
      </section>

      <section className="ws-section">
        <h2>Choose a plan</h2>
        <p className="h2-sub">Monthly billing. Switch anytime.</p>
        <div className="ws-plans">
          <div className="ws-plan">
            <div className="ws-plan-name">Starter</div>
            <div className="ws-plan-price">
              $0<span className="per">/mo</span>
            </div>
            <div className="ws-plan-desc">For individuals automating their own work.</div>
            <a className="btn ws-plan-cta">Get started</a>
            <ul className="ws-plan-feat">
              <li>1 workspace</li>
              <li>1 concurrent run</li>
              <li>Community support</li>
              <li>7-day trace retention</li>
            </ul>
          </div>
          <div className="ws-plan featured">
            <div className="ws-plan-tag">Most popular</div>
            <div className="ws-plan-name">Pro</div>
            <div className="ws-plan-price">
              $49<span className="per">/mo</span>
            </div>
            <div className="ws-plan-desc">For QA teams that ship every week.</div>
            <a
              className={"btn primary ws-plan-cta" + (highlight === "pro-cta" ? " highlight" : "")}
              data-testid="aw-website-pro-cta"
            >
              Start free trial
              {highlight === "pro-cta" ? <span className="pulse" /> : null}
            </a>
            <ul className="ws-plan-feat">
              <li>Unlimited workspaces</li>
              <li>10 concurrent runs</li>
              <li>Email support, 24h SLA</li>
              <li>90-day trace retention</li>
              <li>SSO via Google &amp; Microsoft</li>
            </ul>
          </div>
          <div className="ws-plan">
            <div className="ws-plan-name">Enterprise</div>
            <div className="ws-plan-price">
              Custom<span className="per"></span>
            </div>
            <div className="ws-plan-desc">SAML, audit log, dedicated capacity.</div>
            <a className="btn ws-plan-cta">Talk to sales</a>
            <ul className="ws-plan-feat">
              <li>Everything in Pro</li>
              <li>SAML SSO + SCIM</li>
              <li>Audit log + DPA</li>
              <li>Dedicated capacity</li>
            </ul>
          </div>
        </div>
      </section>

      <section className="ws-section">
        <h2>Frequently asked</h2>
        <div className="ws-faq">
          <div className="ws-faq-row">
            <span className="car">+</span>Can I bring my existing Playwright tests?
          </div>
          <div className="ws-faq-row">
            <span className="car">+</span>How does parallel run pricing work?
          </div>
          <div className="ws-faq-row">
            <span className="car">+</span>Do you support flaky-test auto-quarantine?
          </div>
          <div className="ws-faq-row">
            <span className="car">+</span>Where is data stored?
          </div>
        </div>
      </section>

      <footer className="ws-foot">
        © 2026 Acme Labs · Built in San Francisco
        <span className="ws-foot-links">
          <a>Status</a>
          <a>Docs</a>
          <a>Privacy</a>
          <a>Security</a>
        </span>
      </footer>
    </div>
  );
}

const WEBSITE_CSS = `
.aw-website {
  background: var(--bg-website, #FAF5EB);
  color: #1A1C16;
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
  width: 100%; height: 100%;
  overflow: auto;
}
.aw-website .ws-bar {
  display: flex; align-items: center; gap: 8px;
  padding: 8px 14px;
  background: #EDE5D2;
  border-bottom: 1px solid #DCDECF;
  font-size: 12.5px; color: #66695C;
}
.aw-website .ws-bar .btn {
  display: inline-flex; align-items: center; justify-content: center;
  width: 22px; height: 22px; border-radius: 6px;
  background: rgba(255,255,255,0.6); color: #66695C; border: 1px solid #DCDECF;
}
.aw-website .ws-bar .url {
  padding: 4px 10px; border-radius: 999px; background: white; border: 1px solid #DCDECF;
  font-family: ui-monospace, "SF Mono", monospace;
}
.aw-website .ws-tab {
  padding: 4px 10px; border-radius: 6px;
  background: rgba(255,255,255,0.45); border: 1px solid #DCDECF;
}
.aw-website .ws-topnav {
  display: flex; align-items: center; gap: 16px;
  padding: 16px 40px;
  border-bottom: 1px solid #ECE3CE;
  font-size: 13px;
}
.aw-website .ws-topnav .logo { font-weight: 700; font-size: 16px; color: #1A1C16; }
.aw-website .ws-topnav .topnav-links { display: flex; gap: 14px; margin-left: 12px; flex: 1; }
.aw-website .ws-topnav .topnav-links a { color: #66695C; cursor: pointer; }
.aw-website .ws-topnav .topnav-links a.active { color: #1A1C16; font-weight: 500; }
.aw-website .ws-topnav .right { display: flex; align-items: center; gap: 12px; }
.aw-website .ws-topnav .signin { color: #66695C; cursor: pointer; }
.aw-website .ws-topnav .cta {
  background: #1A1C16; color: white;
  padding: 6px 14px; border-radius: 999px;
  cursor: pointer; font-weight: 500;
}
.aw-website .ws-hero {
  padding: 56px 40px 32px;
  max-width: 920px;
}
.aw-website .ws-eyebrow {
  display: inline-block; font-size: 11.5px; font-weight: 600;
  text-transform: uppercase; letter-spacing: 0.12em;
  color: #D87740; margin-bottom: 14px;
}
.aw-website .ws-h1 {
  font-size: 44px; line-height: 1.1; font-weight: 800; margin: 0 0 14px;
}
.aw-website .ws-h1 em { color: #D87740; font-style: normal; }
.aw-website .ws-sub {
  font-size: 16px; line-height: 1.5; color: #66695C; max-width: 60ch;
  margin: 0 0 22px;
}
.aw-website .ws-hero-ctas { display: flex; gap: 10px; }
.aw-website .btn {
  display: inline-flex; align-items: center; gap: 6px;
  padding: 10px 18px; border-radius: 999px;
  font-size: 14px; font-weight: 600; cursor: pointer;
  border: 1px solid transparent; position: relative;
}
.aw-website .btn.primary { background: #1A1C16; color: white; }
.aw-website .btn.ghost { background: white; border-color: #DCDECF; color: #1A1C16; }
.aw-website .btn.highlight {
  box-shadow: 0 0 0 3px rgba(216,119,64,0.35), 0 0 0 7px rgba(216,119,64,0.15);
}
.aw-website .pulse {
  position: absolute; inset: -10px; border-radius: 999px;
  border: 2px dashed #D87740;
  animation: aw-website-pulse 1.6s ease-in-out infinite;
}
@keyframes aw-website-pulse {
  0%,100% { opacity: 0.45; transform: scale(1); }
  50%     { opacity: 1; transform: scale(1.04); }
}
.aw-website .ws-section { padding: 40px 40px; }
.aw-website .ws-section h2 { font-size: 24px; margin: 0 0 4px; }
.aw-website .h2-sub { color: #66695C; margin: 0 0 22px; font-size: 13.5px; }
.aw-website .ws-plans { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 14px; }
.aw-website .ws-plan {
  background: white; border-radius: 12px; padding: 22px 18px;
  border: 1px solid #ECE3CE; display: flex; flex-direction: column;
  position: relative;
}
.aw-website .ws-plan.featured { border-color: #D87740; box-shadow: 0 14px 30px -18px rgba(216,119,64,0.45); }
.aw-website .ws-plan-tag {
  position: absolute; top: -10px; left: 18px;
  background: #D87740; color: white; padding: 3px 10px;
  border-radius: 999px; font-size: 10.5px; font-weight: 700; letter-spacing: 0.05em;
  text-transform: uppercase;
}
.aw-website .ws-plan-name { font-weight: 600; font-size: 14px; color: #66695C; }
.aw-website .ws-plan-price { font-size: 32px; font-weight: 800; margin: 6px 0 10px; }
.aw-website .ws-plan-price .per { font-size: 13px; font-weight: 500; color: #66695C; margin-left: 4px; }
.aw-website .ws-plan-desc { color: #66695C; font-size: 13px; margin-bottom: 14px; }
.aw-website .ws-plan-cta { align-self: stretch; justify-content: center; margin-bottom: 14px; }
.aw-website .ws-plan-feat { list-style: none; padding: 0; margin: 0; display: flex; flex-direction: column; gap: 6px; font-size: 12.5px; color: #1A1C16; }
.aw-website .ws-plan-feat li::before { content: "✓ "; color: #D87740; font-weight: 700; margin-right: 4px; }
.aw-website .ws-faq { display: flex; flex-direction: column; gap: 8px; max-width: 720px; }
.aw-website .ws-faq-row {
  background: white; padding: 14px 18px; border-radius: 10px;
  border: 1px solid #ECE3CE; font-size: 13.5px;
  display: flex; gap: 10px; align-items: center;
}
.aw-website .ws-faq-row .car { color: #D87740; font-weight: 700; }
.aw-website .ws-foot {
  padding: 22px 40px;
  border-top: 1px solid #ECE3CE;
  color: #82867A; font-size: 12.5px;
  display: flex; align-items: center; justify-content: space-between;
}
.aw-website .ws-foot .ws-foot-links { display: flex; gap: 14px; }
.aw-website .ws-foot .ws-foot-links a { color: #82867A; cursor: pointer; }
`;

export default WebsitePreview;
