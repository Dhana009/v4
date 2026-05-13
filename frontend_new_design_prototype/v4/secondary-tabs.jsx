// secondary-tabs.jsx — Steps / Recorded / Code / Trace

// — STEPS —————————————————————————————————————————————

function StepsTab() {
  return (
    <div>
      <div className="aw-list-toolbar">
        <button className="aw-btn primary"><I.Plus/>Add step</button>
        <button className="aw-btn"><I.Mouse/>Pick element</button>
        <span className="aw-spacer"/>
        <span className="aw-search"><I.Search style={{width:11,height:11,color:"var(--tx-3)"}}/><input placeholder="Filter steps…"/></span>
        <button className="aw-btn"><I.Filter/></button>
      </div>
      <div className="aw-info-strip">
        <I.Info/>
        <span>Step display order is for your convenience. Stable IDs persist across reorders.</span>
        <span className="aw-spacer"/>
        <button className="aw-btn primary" style={{padding:"4px 10px"}}><I.Play/>Run all through LLM</button>
        <button className="aw-btn" style={{padding:"4px 10px"}}><I.Play/>Run selected</button>
      </div>

      {/* step 1 */}
      <div className="aw-step-row">
        <span className="aw-step-handle"><I.Drag/></span>
        <span className="aw-step-idx pending" style={{background:"var(--bg-card)", border:"1px dashed var(--br-strong)", color:"var(--tx-3)"}}>1</span>
        <div style={{flex:1, minWidth:0}}>
          <div className="aw-step-title">Click "Most popular" tag and confirm it routes to Pro signup
            <span className="id">stp_001</span>
          </div>
          <div className="aw-step-meta">
            <span className="aw-badge-i ok"><span className="ldot"/>strong locator</span>
            <span className="aw-badge-i outline">expected: navigates to /signup?plan=pro</span>
            <span className="aw-badge-i info"><span className="ldot"/>1 child op</span>
          </div>
          <div className="aw-step-attached">
            <I.Target style={{width:12,height:12,color:"var(--vio)"}}/>
            <span>attached element:</span>
            <span className="scope">.ws-plan.featured .ws-plan-tag</span>
            <span className="aw-spacer" style={{flex:1}}/>
            <button className="aw-link">Re-pick</button>
          </div>
        </div>
        <div className="actions">
          <button className="aw-icon-btn" title="Duplicate"><I.Copy/></button>
          <button className="aw-icon-btn" title="More"><I.More/></button>
        </div>
      </div>

      {/* step 2: weak locator */}
      <div className="aw-step-row">
        <span className="aw-step-handle"><I.Drag/></span>
        <span className="aw-step-idx warn" style={{background:"var(--ylw)", color:"#fff"}}>2</span>
        <div style={{flex:1, minWidth:0}}>
          <div className="aw-step-title">Each pricing card has a CTA that contains "Get started" or "Talk to sales"
            <span className="id">stp_002</span>
          </div>
          <div className="aw-step-meta">
            <span className="aw-badge-i warn"><span className="ldot"/>weak locator</span>
            <span className="aw-badge-i outline">forEach .ws-plan</span>
          </div>
          <div className="aw-step-attached" style={{borderColor:"#ECD89A", background:"#FBF1D2"}}>
            <I.Alert style={{width:12,height:12,color:"var(--ylw)"}}/>
            <span style={{color:"#7A5A0E"}}>Locator <span className="scope">div:nth-child(2)</span> is positional — will break if a card is added. </span>
            <button className="aw-link" style={{color:"var(--ylw)"}}>Improve locator</button>
            <span style={{color:"#7A5A0E"}}>·</span>
            <button className="aw-link" style={{color:"var(--ylw)"}}>View candidates</button>
          </div>
        </div>
        <div className="actions">
          <button className="aw-icon-btn"><I.Copy/></button>
          <button className="aw-icon-btn"><I.More/></button>
        </div>
      </div>

      {/* step 3: selected section */}
      <div className="aw-step-row">
        <span className="aw-step-handle"><I.Drag/></span>
        <span className="aw-step-idx" style={{background:"var(--vio)", color:"#fff"}}>3</span>
        <div style={{flex:1, minWidth:0}}>
          <div className="aw-step-title">Section: Pricing grid · 4 child operations
            <span className="id">stp_003</span>
          </div>
          <div className="aw-step-meta">
            <span className="aw-badge-i vio"><span className="ldot"/>section step</span>
            <span className="aw-badge-i outline">scope: section.pricing</span>
          </div>
          <div className="aw-step-attached">
            <I.Layers style={{width:12,height:12,color:"var(--vio)"}}/>
            <span>section attached:</span>
            <span className="scope">main &gt; section[aria-label="Pricing"]</span>
          </div>
          <div style={{marginTop:8, borderLeft:"2px solid var(--vio-soft)", paddingLeft:10, display:"flex", flexDirection:"column", gap:4}}>
            <div className="aw-step-op"><span className="op-tag" style={{background:"var(--vio-soft)",color:"var(--vio)"}}>3.1</span> Count cards equals 3</div>
            <div className="aw-step-op"><span className="op-tag" style={{background:"var(--vio-soft)",color:"var(--vio)"}}>3.2</span> Each card exposes name + price + cta</div>
            <div className="aw-step-op"><span className="op-tag" style={{background:"var(--vio-soft)",color:"var(--vio)"}}>3.3</span> Pro card highlighted (badge or color)</div>
            <div className="aw-step-op"><span className="op-tag" style={{background:"var(--vio-soft)",color:"var(--vio)"}}>3.4</span> Cards reachable by keyboard tab order</div>
          </div>
        </div>
        <div className="actions">
          <button className="aw-icon-btn"><I.Copy/></button>
          <button className="aw-icon-btn"><I.More/></button>
        </div>
      </div>

      {/* step 4: missing test data */}
      <div className="aw-step-row">
        <span className="aw-step-handle"><I.Drag/></span>
        <span className="aw-step-idx err" style={{background:"var(--red)", color:"#fff"}}>4</span>
        <div style={{flex:1, minWidth:0}}>
          <div className="aw-step-title">Fill Salary Analyzer form with sample dataset
            <span className="id">stp_004</span>
          </div>
          <div className="aw-step-meta">
            <span className="aw-badge-i err"><span className="ldot"/>blocked: missing test data</span>
            <span className="aw-badge-i outline">requires: salaries.csv</span>
          </div>
          <div className="aw-step-attached" style={{borderColor:"#E8B9AE", background:"#FBEEEA"}}>
            <I.Doc style={{width:12,height:12,color:"var(--red)"}}/>
            <span style={{color:"#8A3A2E"}}>Step references <span className="scope">salaries.csv</span> — not uploaded.</span>
            <span className="aw-spacer" style={{flex:1}}/>
            <button className="aw-link" style={{color:"var(--red)"}}>Upload now</button>
          </div>
        </div>
        <div className="actions">
          <button className="aw-icon-btn"><I.Copy/></button>
          <button className="aw-icon-btn"><I.More/></button>
        </div>
      </div>

      {/* step 5: wrong page */}
      <div className="aw-step-row">
        <span className="aw-step-handle"><I.Drag/></span>
        <span className="aw-step-idx warn" style={{background:"var(--ylw)", color:"#fff"}}>5</span>
        <div style={{flex:1, minWidth:0}}>
          <div className="aw-step-title">Verify docs sidebar contains "Quickstart"
            <span className="id">stp_005</span>
          </div>
          <div className="aw-step-meta">
            <span className="aw-badge-i warn"><span className="ldot"/>wrong current page</span>
            <span className="aw-badge-i outline">expected: /docs · current: /pricing</span>
          </div>
          <div className="aw-step-attached" style={{borderColor:"#ECD89A", background:"#FBF1D2"}}>
            <I.Globe style={{width:12,height:12,color:"var(--ylw)"}}/>
            <span style={{color:"#7A5A0E"}}>I will navigate to <span className="scope">/docs</span> before running this step.</span>
            <span className="aw-spacer" style={{flex:1}}/>
            <button className="aw-link" style={{color:"var(--ylw)"}}>Change precondition</button>
          </div>
        </div>
        <div className="actions">
          <button className="aw-icon-btn"><I.Copy/></button>
          <button className="aw-icon-btn"><I.More/></button>
        </div>
      </div>
    </div>
  );
}

// — RECORDED —————————————————————————————————————————————

function RecordedTab() {
  return (
    <div>
      <div className="aw-info-strip">
        <I.Camera/>
        <span>Backend-emitted evidence only. Skipped or unresolved steps are not shown as recorded.</span>
        <span className="aw-spacer"/>
        <button className="aw-btn" style={{padding:"4px 10px"}}><I.Repeat/>Replay all</button>
      </div>

      <div className="aw-rec-item">
        <div className="aw-rec-head">
          <span className="aw-step-idx ok" style={{background:"var(--grn)", color:"#fff"}}>
            <I.Check style={{width:11,height:11}}/>
          </span>
          <div style={{flex:1}}>
            <div style={{fontSize:13, fontWeight:500}}>Verify hero heading <span style={{fontFamily:"var(--ff-mono)",fontSize:10,color:"var(--tx-4)"}}>rec_a1f3 · v1</span></div>
            <div className="aw-step-meta" style={{marginTop:3}}>
              <span className="aw-badge-i ok"><span className="ldot"/>recorded</span>
              <span>locator: <span style={{fontFamily:"var(--ff-mono)"}}>getByRole('heading', {`{ level: 1 }`})</span></span>
              <span>· 412ms</span>
              <span>· 1 assertion</span>
            </div>
          </div>
          <button className="aw-icon-btn"><I.Repeat/></button>
          <button className="aw-icon-btn"><I.More/></button>
        </div>
        <div className="aw-step-ops" style={{borderLeft:"2px solid var(--grn-soft)", marginTop:6, paddingLeft:10}}>
          <div className="aw-step-op"><span className="op-tag">assert</span>visible · text contains "plans that scale" · <span className="aw-badge-i ok"><span className="ldot"/>pass</span></div>
        </div>
      </div>

      <div className="aw-rec-item">
        <div className="aw-rec-head">
          <span className="aw-step-idx ok" style={{background:"var(--grn)", color:"#fff"}}>
            <I.Check style={{width:11,height:11}}/>
          </span>
          <div style={{flex:1}}>
            <div style={{fontSize:13, fontWeight:500}}>Three pricing cards present <span style={{fontFamily:"var(--ff-mono)",fontSize:10,color:"var(--tx-4)"}}>rec_b2c9 · v1</span></div>
            <div className="aw-step-meta" style={{marginTop:3}}>
              <span className="aw-badge-i ok"><span className="ldot"/>recorded</span>
              <span>locator: <span style={{fontFamily:"var(--ff-mono)"}}>locator('.ws-plan')</span></span>
              <span>· 138ms · count = 3</span>
            </div>
          </div>
          <button className="aw-icon-btn"><I.Repeat/></button>
          <button className="aw-icon-btn"><I.More/></button>
        </div>
        <div className="aw-rec-shot"/>
      </div>

      <div className="aw-rec-item">
        <div className="aw-rec-head">
          <span className="aw-step-idx" style={{background:"var(--ylw)", color:"#fff"}}>
            <I.Sync style={{width:11,height:11}}/>
          </span>
          <div style={{flex:1}}>
            <div style={{fontSize:13, fontWeight:500}}>Pro price equals "$49 / mo" <span style={{fontFamily:"var(--ff-mono)",fontSize:10,color:"var(--tx-4)"}}>rec_e1f4 · v2 (repaired)</span></div>
            <div className="aw-step-meta" style={{marginTop:3}}>
              <span className="aw-badge-i warn"><span className="ldot"/>repaired</span>
              <span>· 622ms</span>
            </div>
          </div>
          <button className="aw-icon-btn"><I.Repeat/></button>
          <button className="aw-icon-btn"><I.More/></button>
        </div>
        <div className="aw-diff" style={{marginTop:8, display:"flex", flexDirection:"column", gap:1}}>
          <div className="aw-diff-row rem"><span className="aw-diff-sign">-</span>expect(loc).toHaveText('$49 / mo')</div>
          <div className="aw-diff-row add"><span className="aw-diff-sign">+</span>expect(loc).toContainText('$49')</div>
        </div>
        <div className="aw-step-meta" style={{marginTop:8, color:"var(--tx-3)"}}>
          repair reason: actual text was <span style={{fontFamily:"var(--ff-mono)",color:"var(--tx-2)"}}>"$49 /mo"</span> · relaxed by LLM repair with user approval
        </div>
      </div>

      <div className="aw-rec-item">
        <div className="aw-rec-head">
          <span className="aw-step-idx" style={{background:"var(--bg-inset)", color:"var(--tx-3)", border:"1px dashed var(--br-strong)"}}>
            <I.Skip style={{width:10,height:10}}/>
          </span>
          <div style={{flex:1}}>
            <div style={{fontSize:13, fontWeight:500, color:"var(--tx-3)"}}>FAQ accordion expands when first row clicked <span style={{fontFamily:"var(--ff-mono)",fontSize:10,color:"var(--tx-4)"}}>stp_faq · skipped</span></div>
            <div className="aw-step-meta" style={{marginTop:3}}>
              <span className="aw-badge-i outline">skipped by user · pre-run</span>
              <span>not recorded — no evidence to show</span>
            </div>
          </div>
        </div>
      </div>

      <div className="aw-rec-item">
        <div className="aw-rec-head">
          <span className="aw-step-idx ok" style={{background:"var(--grn)", color:"#fff"}}>
            <I.Check style={{width:11,height:11}}/>
          </span>
          <div style={{flex:1}}>
            <div style={{fontSize:13, fontWeight:500}}>Footer status link points at status.acme.dev <span style={{fontFamily:"var(--ff-mono)",fontSize:10,color:"var(--tx-4)"}}>rec_f7a3 · v1</span></div>
            <div className="aw-step-meta" style={{marginTop:3}}>
              <span className="aw-badge-i ok"><span className="ldot"/>recorded</span>
              <span>locator: <span style={{fontFamily:"var(--ff-mono)"}}>getByRole('contentinfo').getByText('Status')</span></span>
              <span>· 89ms</span>
            </div>
          </div>
          <button className="aw-icon-btn"><I.Repeat/></button>
        </div>
      </div>
    </div>
  );
}

// — CODE —————————————————————————————————————————————

function CodeTab() {
  return (
    <div>
      <div className="aw-info-strip" style={{background:"var(--blu-tint)", borderColor:"#D8E3F2"}}>
        <I.Info style={{color:"var(--blu)"}}/>
        <span>Code is rendered from <span style={{fontFamily:"var(--ff-mono)"}}>code_update</span> events emitted by the backend after successful recording. Frontend does not generate code.</span>
      </div>
      <div className="aw-list-toolbar" style={{position:"sticky"}}>
        <span style={{display:"flex", alignItems:"center", gap:6, fontSize:12.5}}>
          <I.Doc style={{width:13, height:13, color:"var(--tx-2)"}}/>
          <span style={{fontFamily:"var(--ff-mono)", color:"var(--tx)"}}>tests/pricing.spec.ts</span>
          <span className="aw-badge-i info" style={{marginLeft:4}}><span className="ldot"/>updated 4s ago</span>
        </span>
        <span className="aw-spacer"/>
        <button className="aw-btn"><I.Copy/>Copy</button>
        <button className="aw-btn"><I.Download/>Save</button>
        <button className="aw-btn"><I.More/></button>
      </div>

      <div style={{padding:"10px 14px"}}>
        <div style={{display:"flex", gap:4, marginBottom:10, flexWrap:"wrap"}}>
          <span className="aw-badge-i warn"><span className="ldot"/>1 fragile locator</span>
          <span className="aw-badge-i outline">2 placeholder values</span>
          <span className="aw-badge-i info"><span className="ldot"/>mapped to 5 recorded steps</span>
        </div>

        <pre className="aw-code"><span className="com">// generated by AutoWorkbench · do not edit manually</span>{"\n"}
<span className="kw">import</span> <span className="pun">{"{"}</span> <span className="var">test</span><span className="pun">,</span> <span className="var">expect</span> <span className="pun">{"}"}</span> <span className="kw">from</span> <span className="str">'@playwright/test'</span><span className="pun">;</span>{"\n"}
{"\n"}
<span className="fn">test</span><span className="pun">(</span><span className="str">'pricing page · sanity'</span><span className="pun">,</span> <span className="kw">async</span> <span className="pun">({"{"}</span> <span className="var">page</span> <span className="pun">{"}"})</span> <span className="pun">=&gt; {"{"}</span>{"\n"}
{"  "}<span className="kw">await</span> <span className="var">page</span><span className="pun">.</span><span className="fn">goto</span><span className="pun">(</span><span className="str">'https://acme.dev/pricing'</span><span className="pun">);</span>{"\n"}
{"\n"}
{"  "}<span className="com">// rec_a1f3 · hero heading</span>{"\n"}
{"  "}<span className="kw">await</span> <span className="fn">expect</span><span className="pun">(</span><span className="var">page</span><span className="pun">.</span><span className="fn">getByRole</span><span className="pun">(</span><span className="str">'heading'</span><span className="pun">, {"{"} level: </span><span className="num">1</span> <span className="pun">{"}"})).</span><span className="fn">toContainText</span><span className="pun">(</span><span className="str">'plans that scale'</span><span className="pun">);</span>{"\n"}
{"\n"}
{"  "}<span className="com">// rec_b2c9 · three pricing cards</span>{"\n"}
{"  "}<span className="kw">const</span> <span className="var">cards</span> <span className="pun">=</span> <span className="var">page</span><span className="pun">.</span><span className="fn">locator</span><span className="pun">(</span><span className="str">'.ws-plan'</span><span className="pun">);</span>{"\n"}
{"  "}<span className="kw">await</span> <span className="fn">expect</span><span className="pun">(</span><span className="var">cards</span><span className="pun">).</span><span className="fn">toHaveCount</span><span className="pun">(</span><span className="num">3</span><span className="pun">);</span>{"\n"}
{"\n"}
{"  "}<span className="com">// rec_c4d7 · pro card flagged</span>{"\n"}
{"  "}<span className="kw">await</span> <span className="fn">expect</span><span className="pun">(</span><span className="var">page</span><span className="pun">.</span><span className="fn">locator</span><span className="pun">(</span><span className="str">'.ws-plan.featured'</span><span className="pun">)).</span><span className="fn">toContainText</span><span className="pun">(</span><span className="str">'Most popular'</span><span className="pun">);</span>{"\n"}
{"\n"}
{"  "}<span className="com">// rec_d8e2 · ctas — !! fragile: ambiguous selector resolved by index</span>{"\n"}
{"  "}<span className="kw">for</span> <span className="pun">(</span><span className="kw">const</span> <span className="var">cta</span> <span className="kw">of</span> <span className="kw">await</span> <span className="var">page</span><span className="pun">.</span><span className="fn">locator</span><span className="pun">(</span><span className="str">'a.ws-plan-cta'</span><span className="pun">).</span><span className="fn">all</span><span className="pun">()) {"{"}</span>{"\n"}
{"    "}<span className="kw">await</span> <span className="fn">expect</span><span className="pun">(</span><span className="var">cta</span><span className="pun">).</span><span className="fn">toBeEnabled</span><span className="pun">();</span>{"\n"}
{"    "}<span className="kw">await</span> <span className="fn">expect</span><span className="pun">(</span><span className="var">cta</span><span className="pun">).</span><span className="fn">toHaveAttribute</span><span className="pun">(</span><span className="str">'href'</span><span className="pun">, </span><span className="fn">expect</span><span className="pun">.</span><span className="fn">stringMatching</span><span className="pun">(/^https?:|^\//));</span>{"\n"}
{"  "}<span className="pun">{"}"}</span>{"\n"}
{"\n"}
{"  "}<span className="com">// rec_e1f4 · pro price (repaired: exact → contains)</span>{"\n"}
{"  "}<span className="kw">await</span> <span className="fn">expect</span><span className="pun">(</span><span className="var">page</span><span className="pun">.</span><span className="fn">locator</span><span className="pun">(</span><span className="str">'.ws-plan.featured .ws-plan-price'</span><span className="pun">)).</span><span className="fn">toContainText</span><span className="pun">(</span><span className="str">'$49'</span><span className="pun">);</span>{"\n"}
{"\n"}
{"  "}<span className="com">// rec_f7a3 · footer status link</span>{"\n"}
{"  "}<span className="kw">const</span> <span className="var">statusLink</span> <span className="pun">=</span> <span className="var">page</span><span className="pun">.</span><span className="fn">getByRole</span><span className="pun">(</span><span className="str">'contentinfo'</span><span className="pun">).</span><span className="fn">getByText</span><span className="pun">(</span><span className="str">'Status'</span><span className="pun">);</span>{"\n"}
{"  "}<span className="kw">await</span> <span className="fn">expect</span><span className="pun">(</span><span className="var">statusLink</span><span className="pun">).</span><span className="fn">toHaveAttribute</span><span className="pun">(</span><span className="str">'href'</span><span className="pun">, </span><span className="str">'https://status.acme.dev'</span><span className="pun">);</span>{"\n"}
<span className="pun">{"}"});</span>{"\n"}</pre>

        <div className="aw-card-section-title">Warnings inline</div>
        <ul className="aw-dotlist">
          <li className="no"><span className="sec">L18</span>fragile selector <span style={{fontFamily:"var(--ff-mono)"}}>a.ws-plan-cta</span> — three matches at runtime, indexed by order. Consider role + accessible name.</li>
          <li><span className="sec">L24</span>repaired assertion uses <span style={{fontFamily:"var(--ff-mono)"}}>toContainText</span>; original exact match preserved in <button className="aw-link">replay history</button>.</li>
          <li className="no"><span className="sec">code_gen</span>FAQ accordion step skipped by user — no code emitted (would have been a click + visibility assertion).</li>
        </ul>
      </div>
    </div>
  );
}

// — TRACE —————————————————————————————————————————————

function TraceTab() {
  const rows = [
    { t:"11:42:01.118", icon:I.Spark, type:"session.start",   desc:<><b>session_a91</b> · workspace <span style={{fontFamily:"var(--ff-mono)"}}>acme-qa</span> · policy <span className="aw-badge-i warn"><span className="ldot"/>balanced</span></>, cls:"" },
    { t:"11:42:02.401", icon:I.Globe, type:"page.attach",     desc:<>attached to <span style={{fontFamily:"var(--ff-mono)"}}>https://acme.dev/pricing</span> · dom 814 nodes</>, cls:"io" },
    { t:"11:42:03.992", icon:I.Spark, type:"llm.request",     desc:<>plan-draft · ctx <span className="aw-badge-i acc"><span className="ldot"/>section-summaries</span> · tools <span style={{fontFamily:"var(--ff-mono)"}}>[dom_query, screenshot]</span> · ~1.2k tok</>, cls:"llm" },
    { t:"11:42:06.118", icon:I.Spark, type:"llm.response",    desc:<>plan-v1 · 6 steps · validated against schema · cost <span style={{fontFamily:"var(--ff-mono)"}}>$0.012</span></>, cls:"llm" },
    { t:"11:42:06.200", icon:I.Info,  type:"plan.proposed",   desc:<><b>plan_proposed</b> · awaiting user review</>, cls:"" },
    { t:"11:43:42.001", icon:I.Diff,  type:"plan.revised",    desc:<>user requested change · plan-v2 emitted · 1 add, 1 remove</>, cls:"" },
    { t:"11:43:42.402", icon:I.Check, type:"plan.confirmed",  desc:<><b>plan_confirmed</b> · 6 steps queued</>, cls:"ok" },
    { t:"11:43:42.602", icon:I.Shield,type:"permission.req",  desc:<>medium risk · <span style={{fontFamily:"var(--ff-mono)"}}>page.click("a.btn.primary[Get started]")</span></>, cls:"warn" },
    { t:"11:43:46.811", icon:I.Check, type:"permission.allow",desc:<>user allowed once · scope <span style={{fontFamily:"var(--ff-mono)"}}>plan_v2</span></>, cls:"ok" },
    { t:"11:43:47.011", icon:I.Play,  type:"step.start",      desc:<><b>stp_a1f3</b> · verify hero heading</>, cls:"" },
    { t:"11:43:47.122", icon:I.Target,type:"locator.resolved",desc:<>unique · <span style={{fontFamily:"var(--ff-mono)"}}>role=heading[level=1]</span></>, cls:"ok" },
    { t:"11:43:47.423", icon:I.Check, type:"step.recorded",   desc:<><b>stp_a1f3</b> recorded · 412ms · code_update emitted</>, cls:"ok" },
    { t:"11:43:47.512", icon:I.Play,  type:"step.start",      desc:<><b>stp_b2c9</b> · 3 pricing cards present</>, cls:"" },
    { t:"11:43:47.650", icon:I.Check, type:"step.recorded",   desc:<><b>stp_b2c9</b> recorded · 138ms · count=3</>, cls:"ok" },
    { t:"11:43:47.700", icon:I.Target,type:"locator.ambig",   desc:<>step <b>stp_c4d7</b> · 3 candidates for "Get started" — pausing run</>, cls:"warn" },
    { t:"11:43:54.220", icon:I.Check, type:"locator.chosen",  desc:<>user selected candidate #2 · <span style={{fontFamily:"var(--ff-mono)"}}>.ws-hero a.btn.primary</span></>, cls:"ok" },
    { t:"11:43:56.812", icon:I.Alert, type:"step.failed",     desc:<><b>stp_e1f4</b> · assertion mismatch · evidence saved</>, cls:"err" },
    { t:"11:43:57.001", icon:I.Sync,  type:"recover.attempt", desc:<>deterministic retry × 2 · same result · escalating to LLM</>, cls:"warn" },
    { t:"11:43:59.115", icon:I.Spark, type:"llm.repair",      desc:<>proposed: relax <span style={{fontFamily:"var(--ff-mono)"}}>toHaveText</span> → <span style={{fontFamily:"var(--ff-mono)"}}>toContainText("$49")</span></>, cls:"llm" },
    { t:"11:44:03.420", icon:I.Check, type:"recover.applied", desc:<>user approved repair · re-running stp_e1f4</>, cls:"ok" },
    { t:"11:44:03.992", icon:I.Check, type:"step.recorded",   desc:<><b>stp_e1f4</b> recorded · 622ms · v2 (repaired)</>, cls:"ok" },
    { t:"11:44:04.118", icon:I.Code,  type:"code.update",     desc:<><span style={{fontFamily:"var(--ff-mono)"}}>tests/pricing.spec.ts</span> +47 lines · checksum <span style={{fontFamily:"var(--ff-mono)"}}>c1f8a…</span></>, cls:"" },
    { t:"11:44:04.221", icon:I.Lock,  type:"redact.scan",     desc:<>screenshot redacted · 0 PII matches · all clear</>, cls:"" },
    { t:"11:44:04.301", icon:I.Check, type:"run.completed",   desc:<><b>run_completed</b> · 5 passed · 1 repaired · 0 failed · 31.2s</>, cls:"ok" },
    { t:"11:44:04.450", icon:I.Info,  type:"e2e.pending",     desc:<>frontend cannot mark acceptance · paid E2E run scheduled <span style={{fontFamily:"var(--ff-mono)"}}>02:00 UTC</span></>, cls:"" },
  ];

  return (
    <div>
      <div className="aw-list-toolbar">
        <span className="aw-search" style={{flex:1, maxWidth:240}}>
          <I.Search style={{width:11,height:11,color:"var(--tx-3)"}}/>
          <input placeholder="Filter events…" style={{flex:1}}/>
        </span>
        <span style={{display:"flex", gap:4}}>
          <span className="aw-badge-i info" style={{cursor:"pointer"}}><span className="ldot"/>all</span>
          <span className="aw-badge-i outline" style={{cursor:"pointer"}}>llm</span>
          <span className="aw-badge-i outline" style={{cursor:"pointer"}}>step</span>
          <span className="aw-badge-i outline" style={{cursor:"pointer"}}>permission</span>
          <span className="aw-badge-i outline" style={{cursor:"pointer"}}>error</span>
        </span>
        <span className="aw-spacer"/>
        <button className="aw-btn"><I.Download/></button>
      </div>

      <div className="aw-info-strip" style={{background:"#FBEEEA", borderColor:"#E8B9AE", color:"#8A3A2E"}}>
        <I.Alert style={{color:"var(--red)"}}/>
        <div style={{flex:1, minWidth:0}}>
          <div style={{fontWeight:600, color:"#8A3A2E"}}>Failure detail · stp_e1f4 · resolved by repair</div>
          <div style={{display:"grid", gridTemplateColumns:"68px 1fr", gap:"2px 8px", marginTop:4, fontFamily:"var(--ff-mono)", fontSize:11, color:"var(--tx)"}}>
            <span style={{color:"var(--tx-3)"}}>expected</span><span>"$49 / mo"</span>
            <span style={{color:"var(--tx-3)"}}>actual</span><span>"$49 /mo"</span>
            <span style={{color:"var(--tx-3)"}}>layer</span><span>assertion (locator matched 1)</span>
            <span style={{color:"var(--tx-3)"}}>next</span><span>retry · select candidate · repair · skip · stop</span>
          </div>
        </div>
      </div>

      {rows.map((r, i) => (
        <div key={i} className={"aw-trace-row " + r.cls}>
          <span className="t">{r.t}</span>
          <span className="aw-trace-icon"><r.icon style={{width:10,height:10}}/></span>
          <span className="type">{r.type}</span>
          <span className="desc">{r.desc}</span>
        </div>
      ))}
    </div>
  );
}

window.StepsTab = StepsTab;
window.RecordedTab = RecordedTab;
window.CodeTab = CodeTab;
window.TraceTab = TraceTab;
