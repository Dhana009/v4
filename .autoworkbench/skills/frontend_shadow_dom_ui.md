# Skill: Frontend Shadow DOM UI

## Purpose
Build the AutoWorkbench frontend as a Shadow DOM-first product UI, not as legacy overlay-specific code.

## When to use
Use for frontend React panel, Shadow DOM host, UI layout, tab model, CSS isolation, frontend E2E selectors, mount/unmount lifecycle.

## Source of truth
- Frontend/UI Spec
- Backend/UI state contract
- PRD frontend runtime guidance

## Non-negotiable rules
1. Primary target is Shadow DOM.
2. Current overlay is legacy/transitional reference only.
3. Product UI must be separated from host adapter.
4. Do not add new product logic to browser.py legacy/transitional overlay path.
5. Frontend renders typed backend state.
6. Frontend must not infer lifecycle truth.
7. Add stable data-testid hooks for important controls.
8. UI must work in constrained right-side panel.
9. Style isolation must prevent target site CSS conflicts.
10. Do not let the frontend infer runtime truth from LLM prose or legacy overlay state.

## Required UI tabs
```text
LLM
Steps
Recorded
Code
Trace
```

## Required common UI
- Global header: connection, phase, current URL, active run/plan, blocking status.
- Compact activity area.
- Common actions where relevant: new session, save/load, run/stop, permission mode.

## Required implementation behavior
- Create host adapter layer for Shadow DOM mounting.
- Keep product components host-agnostic.
- Use backend state objects as props/store.
- Preserve or migrate current IDE visual style where useful.
- Ensure event handlers send typed commands only.
- Ensure E2E can query inside Shadow DOM.

## Required tests
- Shadow host mount test
- UI tab rendering test/build check
- Command emission tests where available
- E2E helper update for Shadow DOM selectors
- Regression for key flows: LLM plan, Steps add/run, Recorded, Code, Trace

## Verification commands
```bash
npm run build
python -m pytest tests/e2e/<focused_ui_flow>.py -q -s
```

## Stop conditions
Stop if:
- required evidence is missing, unclear, or contradictory
- UI depends on page CSS
- product logic is duplicated in legacy overlay
- frontend invents lifecycle state
- selectors cannot work through Shadow DOM
- backend event needed by UI does not exist

## Reporting format
Report:
1. UI components changed
2. Host adapter behavior
3. Events/commands affected
4. data-testid hooks added
5. Build/E2E results
6. Risks
