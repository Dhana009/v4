// website.jsx — sample pricing page that lives behind the docked panel
function Website({ highlight }) {
  return (
    <div className="aw-website">
      <style>{`
        .aw-website {
          height: 100%; overflow-y: auto;
          background: var(--bg-website);
          font-family: var(--ff);
          color: #1a1814;
        }
        .ws-bar {
          position: sticky; top: 0; z-index: 5;
          background: rgba(250,246,238,.92);
          backdrop-filter: blur(8px);
          border-bottom: 1px solid #E8DFCB;
          display: flex; align-items: center;
          padding: 9px 28px; gap: 10px;
          font-size: 12px;
        }
        .ws-bar .btn { display: inline-flex; align-items: center; gap: 6px; padding: 4px 8px; border-radius: 6px; color: #6B6259; }
        .ws-bar .btn:hover { background: rgba(0,0,0,.04); }
        .ws-bar .url {
          flex: 1; max-width: 600px;
          padding: 5px 10px;
          background: #FFFFFF;
          border: 1px solid #E8DFCB;
          border-radius: 999px;
          font-size: 12px; color: #5A5247;
          display: inline-flex; align-items: center; gap: 7px;
          margin: 0 8px;
        }
        .ws-bar .url svg { width: 12px; height: 12px; color: #5F8A6B; }
        .ws-bar .url .host { color: #221E18; font-weight: 500; }
        .ws-bar .tabs { display: flex; gap: 4px; }
        .ws-tab {
          padding: 5px 14px 7px 12px;
          border-radius: 8px 8px 0 0;
          background: #FFFFFF;
          border: 1px solid #E8DFCB;
          border-bottom: 0;
          font-size: 11.5px; color: #221E18;
          display: inline-flex; align-items: center; gap: 6px;
          margin-bottom: -1px;
          max-width: 200px;
        }
        .ws-tab .fav { width: 10px; height: 10px; border-radius: 2px; background: linear-gradient(135deg,#D97742,#BE5F2D); flex: 0 0 10px; }
        .ws-tab .tx { white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }

        .ws-topnav {
          display: flex; align-items: center; gap: 22px;
          padding: 18px 56px;
          font-size: 13px; color: #4A4239;
        }
        .ws-topnav .logo {
          font-weight: 700; font-size: 17px; letter-spacing: -0.02em; color: #1a1814;
          display: inline-flex; align-items: center; gap: 8px;
        }
        .ws-topnav .logo i {
          width: 22px; height: 22px; border-radius: 7px;
          background: linear-gradient(135deg,#D97742,#BE5F2D);
        }
        .ws-topnav a { color: #4A4239; text-decoration: none; }
        .ws-topnav a:hover { color: #1a1814; }
        .ws-topnav .right { margin-left: auto; display: flex; gap: 14px; align-items: center; white-space: nowrap; }
        .ws-topnav .cta {
          background: #1a1814; color: #FAF6EE; padding: 7px 14px;
          border-radius: 999px; font-weight: 500; font-size: 12.5px;
          white-space: nowrap;
        }

        .ws-hero {
          padding: 48px 56px 22px; max-width: 1080px;
        }
        .ws-eyebrow {
          font-size: 12.5px; color: #BE5F2D; font-weight: 600;
          letter-spacing: 0.04em; text-transform: uppercase; margin-bottom: 16px;
        }
        .ws-h1 {
          font-size: 56px; line-height: 1.04; font-weight: 600;
          letter-spacing: -0.025em; color: #1a1814;
          margin: 0 0 18px;
          max-width: 880px;
        }
        .ws-h1 em { font-style: normal; color: #BE5F2D; }
        .ws-sub {
          font-size: 17px; color: #5A5247; line-height: 1.55;
          max-width: 620px; margin: 0 0 24px;
        }
        .ws-hero-ctas { display: flex; gap: 10px; }
        .ws-hero-ctas .btn {
          padding: 11px 20px; border-radius: 999px; font-size: 14px; font-weight: 500;
          white-space: nowrap;
        }
        .ws-hero-ctas .btn.primary { background: #1a1814; color: #FAF6EE; position: relative; }
        .ws-hero-ctas .btn.ghost { background: transparent; border: 1px solid #D9CFB7; color: #1a1814; }
        .ws-hero-ctas .btn:hover { transform: translateY(-1px); }
        .ws-hero-ctas .btn.primary.highlight, .ws-hero-ctas .btn.ghost.highlight {
          outline: 3px solid rgba(217,119,66,.35); outline-offset: 3px;
        }
        .ws-hero-ctas .pulse {
          position: absolute; inset: -6px;
          border: 2px dashed #D97742;
          border-radius: 999px;
          animation: ws-pulse 1.8s ease-in-out infinite;
          pointer-events: none;
        }
        @keyframes ws-pulse {
          0%,100% { opacity: .55; transform: scale(1); }
          50% { opacity: .15; transform: scale(1.04); }
        }

        .ws-section { padding: 32px 56px; max-width: 1180px; }
        .ws-section h2 {
          font-size: 28px; font-weight: 600; letter-spacing: -0.02em;
          margin: 0 0 4px; color: #1a1814;
        }
        .ws-section .h2-sub { color: #5A5247; font-size: 14px; margin-bottom: 22px; }

        .ws-plans {
          display: grid; grid-template-columns: repeat(3, 1fr); gap: 16px;
        }
        .ws-plan {
          background: #FFFFFF;
          border: 1px solid #E8DFCB;
          border-radius: 18px;
          padding: 22px 22px 18px;
          display: flex; flex-direction: column;
          position: relative;
        }
        .ws-plan.featured {
          border-color: #BE5F2D;
          background: linear-gradient(180deg, #FFF8EE 0%, #FFFFFF 50%);
          box-shadow: 0 1px 0 rgba(0,0,0,.02), 0 10px 26px -10px rgba(190,95,45,.22);
        }
        .ws-plan-tag {
          position: absolute; top: 14px; right: 14px;
          font-size: 10.5px; font-weight: 600; letter-spacing: 0.04em;
          text-transform: uppercase; color: #BE5F2D;
          background: #FCEFE0; padding: 3px 9px; border-radius: 999px;
        }
        .ws-plan-name { font-size: 14px; font-weight: 600; color: #5A5247; }
        .ws-plan-price { font-size: 38px; font-weight: 600; letter-spacing: -0.02em; color: #1a1814; margin: 6px 0 2px; }
        .ws-plan-price small { font-size: 14px; font-weight: 500; color: #8A8275; }
        .ws-plan-desc { font-size: 13px; color: #5A5247; line-height: 1.5; margin-bottom: 14px; min-height: 38px; }
        .ws-plan-cta {
          padding: 9px 14px; border-radius: 999px;
          background: #1a1814; color: #FAF6EE; text-align: center;
          font-size: 13px; font-weight: 500; margin-bottom: 18px;
          position: relative;
        }
        .ws-plan.featured .ws-plan-cta { background: #D97742; }
        .ws-plan-cta.highlight {
          outline: 3px solid rgba(217,119,66,.35); outline-offset: 3px;
        }
        .ws-plan-feat { list-style: none; padding: 0; margin: 0; display: flex; flex-direction: column; gap: 9px; font-size: 12.5px; color: #4A4239; }
        .ws-plan-feat li { display: flex; gap: 8px; align-items: flex-start; }
        .ws-plan-feat li::before {
          content: ""; width: 14px; height: 14px; flex: 0 0 14px; margin-top: 1px;
          background-color: #5F8A6B; -webkit-mask: url("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24'><path fill='none' stroke='black' stroke-width='3' d='M5 12l5 5L20 7'/></svg>") center/contain no-repeat;
                  mask: url("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24'><path fill='none' stroke='black' stroke-width='3' d='M5 12l5 5L20 7'/></svg>") center/contain no-repeat;
        }

        .ws-faq { display: flex; flex-direction: column; gap: 10px; max-width: 760px; }
        .ws-faq-row {
          padding: 14px 18px; background: #FFFFFF;
          border: 1px solid #E8DFCB; border-radius: 14px;
          display: flex; align-items: center; justify-content: space-between;
          font-size: 14px; color: #1a1814; font-weight: 500;
        }
        .ws-faq-row .car { color: #8A8275; }

        .ws-foot {
          padding: 36px 56px 56px;
          border-top: 1px solid #E8DFCB;
          color: #5A5247;
          margin-top: 32px;
          display: flex; justify-content: space-between;
          font-size: 12.5px;
        }
        .ws-foot a { color: #5A5247; text-decoration: none; }
        .ws-foot a:hover { color: #1a1814; }

        /* highlight rings driven by panel */
        .ws-ring {
          outline: 3px solid rgba(217,119,66,.45);
          outline-offset: 4px;
          border-radius: 8px;
        }
      `}</style>

      {/* Browser-ish bar */}
      <div className="ws-bar">
        <span className="btn">‹</span>
        <span className="btn">›</span>
        <span className="btn">↻</span>
        <div className="url">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M5 11V8a7 7 0 1 1 14 0v3"/><rect x="4" y="11" width="16" height="9" rx="2"/></svg>
          <span className="host">acme.dev</span><span style={{color:"#9A8F84"}}>/pricing</span>
        </div>
        <div className="tabs">
          <span className="ws-tab"><span className="fav"/><span className="tx">Pricing — Acme</span><span style={{color:"#9A8F84"}}>×</span></span>
        </div>
      </div>

      <div className="ws-topnav">
        <span className="logo"><i/> Acme</span>
        <a>Product</a>
        <a>Solutions</a>
        <a>Docs</a>
        <a style={{color:"#1a1814", fontWeight:500}}>Pricing</a>
        <a>Changelog</a>
        <span className="right">
          <a>Sign in</a>
          <a className="cta">Get started</a>
        </span>
      </div>

      <div className="ws-hero">
        <div className="ws-eyebrow">Pricing</div>
        <h1 className="ws-h1">Plans that scale with your <em>QA team</em>, not your headcount.</h1>
        <p className="ws-sub">Start free. Add seats when you need them. Bring your own infra or run on ours — every plan includes parallel runs, full traces, and the Playwright primitives you already use.</p>
        <div className="ws-hero-ctas">
          <a className={"btn primary " + (highlight === "hero-cta" ? "highlight" : "")}>
            Get started
            {highlight === "hero-cta" && <span className="pulse"/>}
          </a>
          <a className="ghost btn">Talk to sales</a>
        </div>
      </div>

      <div className="ws-section">
        <h2>Choose a plan</h2>
        <div className="h2-sub">Monthly billing. Switch anytime.</div>
        <div className="ws-plans">
          <div className="ws-plan">
            <div className="ws-plan-name">Starter</div>
            <div className="ws-plan-price">$0<small> / mo</small></div>
            <div className="ws-plan-desc">For individuals automating their own work.</div>
            <a className="ws-plan-cta">Get started</a>
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
            <div className="ws-plan-price">$49<small> / mo</small></div>
            <div className="ws-plan-desc">For QA teams that ship every week.</div>
            <a className={"ws-plan-cta " + (highlight === "pro-cta" ? "highlight" : "")}>Start free trial</a>
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
            <div className="ws-plan-price">Custom</div>
            <div className="ws-plan-desc">SAML, audit log, dedicated infra, procurement support.</div>
            <a className="ws-plan-cta">Talk to sales</a>
            <ul className="ws-plan-feat">
              <li>Unlimited concurrent runs</li>
              <li>SAML SSO + SCIM</li>
              <li>Dedicated support engineer</li>
              <li>Custom retention &amp; regions</li>
              <li>Audit log + DPA</li>
            </ul>
          </div>
        </div>
      </div>

      <div className="ws-section">
        <h2>Frequently asked</h2>
        <div className="h2-sub">Things teams ask before they switch to Acme.</div>
        <div className="ws-faq">
          <div className="ws-faq-row">Can I bring my existing Playwright tests? <span className="car">+</span></div>
          <div className="ws-faq-row">How does parallel run pricing work? <span className="car">+</span></div>
          <div className="ws-faq-row">Do you support flaky-test auto-quarantine? <span className="car">+</span></div>
          <div className="ws-faq-row">Where is data stored? <span className="car">+</span></div>
        </div>
      </div>

      <div className="ws-foot">
        <div>© 2026 Acme Labs · Built in San Francisco</div>
        <div style={{display:"flex", gap:18}}>
          <a>Status</a><a>Docs</a><a>Privacy</a><a>Security</a>
        </div>
      </div>
    </div>
  );
}

window.Website = Website;
