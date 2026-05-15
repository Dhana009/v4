# FE-LAYOUT-001 — Preview Dock/Stage Parity (short impl note)

**Date:** 2026-05-15
**Branch:** `s7/clusters-6-11-complete-llm-mode`
**Parent commits:** `cc3c7d9` (FE-VBATCH-001), `73d1f01` (FE-VBATCH-002), `b243961` (panel-width fix)
**References:** `AutoWorkbench.html` (visual), `yui (1)/` ROOT — `styles.css:199-260`, `app.jsx`, `website.jsx`, `tweaks-panel.jsx`.
**NOT a reference:** `yui (1)/v4/`.

## Decision

- **Preview/demo mode:** ROOT-style `.aw-stage` flex layout (website + panel as flex siblings).
- **Live runtime:** unchanged — fixed Shadow DOM host injected on real third-party page.
- **Shared:** inner `IDEPanel` markup + CSS (header / tabs / NowStrip / body / composer / footer). Both modes fill 100% of their container.

## Root causes addressed

1. Three stacked `position:fixed` layers (PreviewShell website, panel-host, inner aw-ide-panel) produce "floating card" feel + top gap.
2. `panelWidth` read once at `mount()`; slider never re-applies → website resizes, panel does not.
3. Inner panel owns its own width state, fighting the host cell.

## Contract

```
PREVIEW
  .aw-preview-shell  (100vh, overflow:hidden)
    .aw-stage.aw-stage--dock-{right|left|top|float} [.aw-stage--collapsed]
      .aw-website-region (flex:1 1 0; min-width:0; overflow:auto)
      .aw-panel-cell     (flex:0 0 panelWidth; height:100%)
        <div data-shadow-host width/height:100%>
          [shadow root]  → IDEPanel (width/height:100%, flex column)
      <TweaksPanel/>     (overlay)

LIVE
  document.body (host page untouched)
    <div data-shadow-host position:fixed; right:0; top:0; height:100vh; width:storedSize>
      IDEPanel (width/height:100%, flex column)
```

Inner panel:
```
.aw-panel  flex column, height:100%
  .aw-header        flex 0 0 auto
  .aw-tabs          flex 0 0 auto
  .aw-now-strip     flex 0 0 auto
  .aw-panel-body    flex 1 1 0; overflow-y:auto; min-height:0
  .aw-composer      flex 0 0 auto
  .aw-footer        flex 0 0 auto
```

## Width propagation

- `PreviewShell` keeps `tweaks.panelWidth` in React state.
- `.aw-panel-cell` inline `width: tweaks.panelWidth`.
- Shadow host = `width:100%; height:100%`.
- IDEPanel root strips `position:fixed`/explicit width; fills container.
- Live path keeps existing `storedSize`/`applyCompensation` (only fixed-host mode).

## Dock modes

| Mode | Stage class | Effect |
|---|---|---|
| right (default) | `aw-stage--dock-right` | flex-direction:row |
| left | `aw-stage--dock-left` | flex-direction:row-reverse |
| top | `aw-stage--dock-top` | flex-direction:column-reverse; panel height fixed |
| float | `aw-stage--dock-float` | stage display:block; panel absolute, shadow+radius reintroduced |
| collapsed | `aw-stage--collapsed` | panel-cell width forced to 44px; inner hides tabs/body/composer/footer |

## Files

Edit: `frontend/src/main.jsx`, `frontend/aw-ide-panel.jsx`, `frontend/v4.css`, `frontend/src/demo/website-preview.jsx`, `frontend/scripts/preview.html`. New: `frontend/tests-dom/layout-dock-contract.test.jsx`. Update tests as needed.

Forbidden untouched: `agent.py`, `server.py`, `runtime/**`, `tests/e2e/**`, `AutoWorkbench.html`, `yui (1)/**`.

## Tests (TDD)

`tests-dom/layout-dock-contract.test.jsx`:
1. preview renders `.aw-stage` containing website + panel-cell + tweaks
2. dock toggling swaps `aw-stage--dock-*` class
3. width slider change → `.aw-panel-cell` width updates (asserted via inline style)
4. flush: panel-cell has no top offset/margin in docked modes
5. inner IDEPanel root has no `position:fixed` and uses width/height 100%
6. live mount (no `demo:true`) → no `.aw-stage`, shadow host keeps fixed positioning, no demo fixture imports

## Out of scope

- Card-level redesign per tab (only container layout in this slice).
- Backend / event contract changes.
- Merge to main.
