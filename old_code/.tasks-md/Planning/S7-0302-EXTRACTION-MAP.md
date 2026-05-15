# S7-0302 Frontend New Design Prototype Extraction Map

**Sprint:** Sprint 7  
**Cluster:** 3  
**Story:** S7-0302  
**Date:** 2026-05-13  

---

## Extraction Rules

1. **Extract visual tokens, not state logic** — CSS vars go to tokens.css; static STATE_META does not go to production.
2. **Extract component structure, not hardcoded data** — Component shape/props go to components/; demo data stays in prototype.
3. **No prototype state as runtime truth** — Prototype uses in-memory tweak panel; production uses backend events.

---

## 1. Design Token Extraction (→ tokens.css)

Source: `frontend_new_design_prototype/styles.css`

### Background tokens
| CSS var | Value | Production token name |
|---------|-------|----------------------|
| `--bg` | `#FDFAF5` | `--aw-bg` |
| `--bg-card` | `#FFFFFF` | `--aw-bg-card` |
| `--bg-tray` | `#F4F0EA` | `--aw-bg-tray` |
| `--bg-code` | `#1C1A17` | `--aw-bg-code` |

### Text tokens
| CSS var | Value | Production token name |
|---------|-------|----------------------|
| `--ink` | `#2C2219` | `--aw-ink` |
| `--tx-2` | `#5C4B38` | `--aw-tx-2` |
| `--tx-3` | `#9A7B62` | `--aw-tx-3` |
| `--tx-4` | `#B8A696` | `--aw-tx-4` |

### Accent tokens
| CSS var | Value | Production token name |
|---------|-------|----------------------|
| `--acc` | `#C17A35` | `--aw-acc` |
| `--acc-2` | `#E09040` | `--aw-acc-2` |

### Status tokens
| CSS var | Value | Production token name |
|---------|-------|----------------------|
| `--grn` | `#4F8A5B` | `--aw-grn` |
| `--red` | `#B84040` | `--aw-red` |
| `--yel` | `#C89A30` | `--aw-yel` |
| `--blu` | `#3A7AA8` | `--aw-blu` |

### Border tokens
| CSS var | Value | Production token name |
|---------|-------|----------------------|
| `--br` | `rgba(0,0,0,.08)` | `--aw-br` |
| `--br-strong` | `rgba(0,0,0,.15)` | `--aw-br-strong` |

### Shape tokens
| CSS var | Value | Production token name |
|---------|-------|----------------------|
| `--r` | `8px` | `--aw-r` |
| `--r-lg` | `12px` | `--aw-r-lg` |

### Typography tokens
| CSS var | Value | Production token name |
|---------|-------|----------------------|
| `--font-mono` | `"JetBrains Mono", "Fira Code", monospace` | `--aw-font-mono` |

### Spacing tokens (derived from prototype patterns)
| Name | Value | Production token name |
|------|-------|----------------------|
| `--space-1` | `4px` | `--aw-space-1` |
| `--space-2` | `8px` | `--aw-space-2` |
| `--space-3` | `12px` | `--aw-space-3` |
| `--space-4` | `16px` | `--aw-space-4` |

---

## 2. Component Pattern Extraction (→ components/)

### Shell components (→ components/shell/)

| Prototype component | Production component | Props to extract | Do NOT copy |
|--------------------|---------------------|-----------------|-------------|
| `Header` (chrome.jsx) | `Header.jsx` | `status`, `dock`, `setDock`, `collapsed`, `setCollapsed`, `tokenInfo`, `mode`, `setMode` | `agentsSummary` (prototype-specific), `dockMenu` local state |
| `TabStrip` (chrome.jsx) | `TabBar.jsx` | `tab`, `setTab`, `counts` | Static counts object |
| `Footer` (chrome.jsx) | No direct production equiv yet | `phase`, `event`, `blocker`, `nextAction` | — |
| `NowStrip` (chrome.jsx) | — (Cluster 6) | — | Prototype state |
| `CollapsedRail` (app.jsx) | — (Cluster 4) | — | — |

### LLM tab components (→ components/llm/)

| Prototype component | Production component | Props shape | Do NOT copy |
|--------------------|---------------------|------------|-------------|
| `CardClarification` (llm-tab.jsx) | `ClarificationCard.jsx` | `question`, `options`, `onAnswer` | Hardcoded option list |
| `CardPlanReady` (llm-tab.jsx) | `PlanCard.jsx` | `plan`, `onAccept`, `onCorrect` | Demo plan object |
| `CardRecommendation` (llm-tab.jsx) | `RecommendationCard.jsx` | `recommendations[]`, `onUse` | Hardcoded rec list |
| `CardDiff` (llm-tab.jsx) | — (Cluster 6) | — | — |
| `CardPermit` (llm-tab.jsx) | — (Cluster 6) | — | — |
| `CardLocator` (llm-tab.jsx) | — (Cluster 6) | — | — |
| `CardRecovery` (llm-tab.jsx) | — (Cluster 6) | — | — |
| `Bubble`, `Sys` (llm-tab.jsx) | ChatMessage components (Cluster 6) | — | Hardcoded timestamps |

### Primitive extraction (→ components/primitives/)

| Prototype pattern | Production primitive | Key props |
|------------------|---------------------|-----------|
| `<button className="aw-btn primary">` | `Button.jsx` | `variant`, `disabled`, `onClick`, `ariaLabel` |
| `<div className="ide-card c-{color}">` | `Card.jsx` | `color`, `title`, `children`, `footer` |
| `<span className="aw-card-state">` | `Badge.jsx` | `variant`, `children` |
| `<span className="aw-status-pill">` | `StatusPill.jsx` | `status` (completed/running/failed) |
| No explicit empty state in prototype | `EmptyState.jsx` | `message`, `icon?` |
| Inline error spans | `InlineAlert.jsx` | `variant` (error/warning/info), `message` |
| `<div>` with multiple buttons | `ActionRow.jsx` | `children` |
| `<pre>` code display | `CodeBlock.jsx` | `code`, `language?` |
| Timeline row spans | `TimelineRow.jsx` | `event`, `timestamp`, `severity` |
| Locator candidate cards | `CandidateCard.jsx` | `candidate`, `onSelect` |

---

## 3. CSS Class Mapping (prototype → tokens)

| Prototype class | Meaning | Production approach |
|----------------|---------|-------------------|
| `.aw-card.c-ink` | Dark ink card | Use `--aw-ink` token |
| `.aw-card.c-grn` | Green success card | Use `--aw-grn` token |
| `.aw-card.c-red` | Red error card | Use `--aw-red` token |
| `.aw-btn.primary` | Primary action | Button variant="primary" |
| `.aw-btn.subtle` | Secondary action | Button variant="secondary" |
| `.aw-conf.high/.med/.low` | Confidence indicator | Use `--aw-grn`/`--aw-yel`/`--aw-red` |

---

## 4. What to NOT Extract

| Prototype artifact | Reason to exclude |
|-------------------|------------------|
| `TWEAK_DEFAULTS` constant | Design tool only; not runtime state |
| `STATE_META` object | Static demo state; production gets state from backend events |
| `TweaksPanel`, `TweakRadio`, `TweakSlider` | Design tool UI only |
| `Website` component | Simulated page behind panel |
| `useTweaks()` hook | Design tool state management |
| Hardcoded timestamps ("11:42") | Demo data; production uses real event timestamps |
| Hardcoded agent names/states in `agentsSummary` | Demo; production from backend events |
| Hardcoded step/plan arrays | Demo; production from `plan_ready` events |

---

## 5. Tab Structure Mapping

| Prototype tab ID | Production tab ID | Component |
|-----------------|-------------------|-----------|
| `"llm"` | `"workbench"` (current) | LLM thread (Cluster 6) |
| `"steps"` | `"steps"` | Steps panel (Cluster 7) |
| `"rec"` | `"recorded"` | Recorded tab (Cluster 8) |
| `"code"` | `"code"` | Code tab (Cluster 8) |
| `"trace"` | `"debug"` | Trace tab (Cluster 9) |

---

## Evidence

- Prototype files read: app.jsx, chrome.jsx, llm-tab.jsx, icons.jsx, styles.css
- CSS var extraction: 20+ design tokens mapped
- Component pattern: 10 prototype components → production primitives
- Exclusion list: 8 prototype artifacts explicitly excluded from production
