# AutoWorkbench Frontend — Authoritative Reference Source

This file locks the visual/design reference for the AutoWorkbench frontend so
that future ports do not repeat the earlier mistake of using the older
`yui (1)/v4/` checkpoint.

## Authoritative references

- **Visual reference (rendered):** `AutoWorkbench.html` at the repository root.
  Self-extracting standalone demo. Open in a browser to see the target UI.
- **Source reference (JSX/CSS):** `yui (1)/` **ROOT** files (newer revision).
  Files: `index.html`, `app.jsx`, `chrome.jsx`, `icons.jsx`, `llm-tab.jsx`,
  `secondary-tabs.jsx`, `tweaks-panel.jsx`, `website.jsx`, `styles.css`.

`AutoWorkbench.html` was built from these ROOT files (with auto-injected
`data-comment-anchor` review tags). They are byte-equivalent for the
unannotated modules.

## NOT the design source

`yui (1)/v4/` is an **older checkpoint**. It is **NOT** authoritative and
**NOT** the design source. The earlier refactor pass mistakenly ported from
this subdirectory; that drift is the root cause of the current visual gap.

Do not use `yui (1)/v4/` as a target. Use `yui (1)/` ROOT.

## Live-mode rules (unchanged)

- Backend remains runtime truth.
- Frontend renders backend events and sends typed commands only.
- Frontend must not infer lifecycle truth from LLM prose, CSS state, or local
  assumptions.
- Mock/demo data from `AutoWorkbench.html` or `yui (1)/` ROOT may be used
  only in an isolated demo/fixture mode. It must never contaminate live
  backend-driven rendering.

## Build freshness guard

`npm run check:dist` (script: `scripts/check-dist-fresh.mjs`) fails if
`dist/autoworkbench.js` or `dist/autoworkbench.css` is older than any active
build input under `src/`, `aw-ide-panel.jsx`, `icons.jsx`, `styles.css`,
`style-ide.css`, or `v4.css`.

Run after every edit to a source file; CI may run it as a gate.

## Static guard

`tests-dom/static-audit.test.jsx` (block `FE-REF-001 …`) enforces the above:
- both references exist,
- `REFERENCE_SOURCE.md` declares ROOT authoritative,
- no production source claims `v4` as the visual target,
- `check:dist` script + check-dist-fresh.mjs exist and are scoped narrowly.
