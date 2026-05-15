# 00 — Master Index

> PRD v2.3 modular pack. Existing PRD v2.2 wording is preserved where it still applies. New or corrected material is marked as v2.3 guidance. This revision adds `07_MULTI_MODEL_ORCHESTRATION.md` for optional/stabilized multi-model architecture.


## Source of truth

This modular PRD pack replaces the single-file daily working reference for PRD v2.2. The original v2.2 file remains the archival base. These files reorganize v2.2 content and add v2.3 clarifications without changing the core product direction.

## Strategic intent

Human tells what to test. The system figures out how to test it, validates everything in the real browser, recovers without restarting, records reliable steps, saves/replays those recordings, repairs broken replay flows with the LLM, and generates clean runnable Playwright TypeScript.

## Non-negotiable decisions

| Area | Decision |
|---|---|
| Primary build focus | LLM Mode first. It is the brain used by record, replay, repair, and eventually manual mode failure repair. |
| Runtime truth | Backend Step Runner owns lifecycle, finality, recording, and replay truth. |
| LLM role | LLM reasons, decomposes, plans, explains, and repairs. It does not decide whether work is complete. |
| Frontend role | AutoWorkbench UI renders backend state and collects user input. It must not infer lifecycle state from LLM text. |
| Contract | Backend/frontend communicate through typed WebSocket events and commands. |
| UI direction | Current injected AutoWorkbench UI remains; stabilized target is Shadow DOM + DevTools-like docked/resizable layout host. |
| Recording model | Parent recorded step with child operations/checks. |
| Storage | User-facing output saves under the active workspace by default, not hardcoded `.hermes`. Internal metadata may use a hidden workspace folder. |
| Context | LLM receives full relevant state, not raw full history. |
| Multi-model orchestration | Optional/stabilized architecture: cheap/nano models prepare page intelligence; Main Orchestrator reasons; Step Runner validates truth. |
| Quality | Token optimization must never reduce correctness. |

## Documents

| File | Purpose | Read when |
|---|---|---|
| `00_MASTER_INDEX.md` | Orientation and document map | Always |
| `01_PRODUCT_WORKFLOWS.md` | Product flows and daily use cases | Planning features, UX, recording/replay behavior |
| `02_LLM_RUNTIME.md` | LLM runtime, context, DOM, skills, recovery, tool safety | LLM/agent/backend work |
| `03_FRONTEND_RUNTIME.md` | AutoWorkbench UI, docking, interaction modes, UX | UI/frontend work |
| `04_BACKEND_EVENT_CONTRACT.md` | WebSocket commands/events and payload rules | Any UI/backend integration task |
| `05_CODEGEN_REPLAY_PERSISTENCE.md` | Codegen, save/load, replay, repair, locator update | Output, replay, persistence work |
| `06_BUILD_ROADMAP_AND_ACCEPTANCE.md` | Phases, expected criteria, test matrix | Planning Codex tasks and validating progress |

## Current MVP boundary

MVP should prove this loop end-to-end:

```text
pick/select target or section
→ describe intent
→ LLM decomposes if needed
→ plan review
→ confirm/correct
→ execute with live validation
→ recover if needed
→ record parent step + child operations
→ emit code_update
→ save session/spec
→ replay and repair if broken
```

## Expected criteria

- A new agent can read this master index and know which focused PRD file to read next.
- Build tasks reference the smallest relevant PRD documents, not the full 3000-line archive by default.
- All implementation decisions preserve the non-negotiable decisions above.
- Contradictions between older v2.2 sections and v2.3 guidance are resolved in favor of v2.3 guidance.
- Multi-model decisions are read from `07_MULTI_MODEL_ORCHESTRATION.md`; do not scatter agent role definitions across implementation files.

---

> **Preserved v2.2 reference only.** If this section conflicts with v2.3 guidance above, v2.3 wins.

## Preserved v2.2 strategic section

This project is being built around **LLM Mode first**. Manual Mode is important, but the core product value is the LLM layer: the system should understand tester intent, ground that intent against the live browser, validate locators/actions, recover from failures, and produce clean Playwright TypeScript.

### Primary product intent

```text
Human tells what to test.
System figures out how to test it.
System validates everything in the real browser.
System recovers without restarting.
System records reliable steps and generates runnable Playwright code.
```

### Current strategic decisions

| Decision | Current direction | Why |
|---|---|---|
| Build focus | LLM Mode first | This is the brain and differentiator of the product. |
| Runtime ownership | Backend Step Runner owns lifecycle | The LLM may reason, but it must not decide whether work is complete. |
| Context ownership | Context Manager owns prompt/context | The LLM needs full relevant state, not raw full history. |
| Skills | Progressive skill loading | Avoid loading every full skill file for every call. |
| DOM strategy | Mode-based DOM context | Normal/explore/debug/full-DOM modes balance quality and token cost. |
| UI delivery | Direct injected overlay for MVP | Fastest reliable way to pick elements and control the live page. |
| Future UI isolation | Shadow DOM overlay | Better CSS/layout isolation without iframe restrictions. |
| Recording | Backend-owned | A step is recorded only after confirmed successful execution. |
| Code output | Clean Playwright TypeScript | Output must run without manual cleanup. |

### Non-negotiable quality principle

Token optimization must never reduce correctness. The system should reduce irrelevant context, not useful context. When reliability requires more context, the Context Manager must escalate deliberately and log why.