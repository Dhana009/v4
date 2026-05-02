# 04 — Backend Event Contract

> PRD v2.3 modular pack. Existing PRD v2.2 wording is preserved where it still applies. New or corrected material is marked as v2.3 guidance.


## v2.3 contract principle

Backend Step Runner is the source of truth. Frontend renders typed events and sends explicit commands. The frontend must not infer lifecycle state from LLM text.

## Ownership

| State | Owner |
|---|---|
| local draft text before Run | frontend |
| pending/recorded/skipped/failed step truth | backend |
| plan/clarification/recovery mode | backend event stream |
| generated code | backend codegen |
| replay status | backend |
| dock position/panel size/selected tab | frontend UI preference |

## Required backend → frontend lifecycle events

| Event | Required payload | Frontend behavior |
|---|---|---|
| `ready` | `session_id`, `workspace`, `mode`, `url` | show ready state |
| `run_started` | `run_id`, `steps[]` | set executing/planning state |
| `plan_ready` | `run_id`, `plan`, `steps[]`, `summary` | enter `plan_review` |
| `clarification_needed` | `run_id`, `question`, `options?`, `step_id?` | enter `clarification` |
| `recovery_needed` | `run_id`, `step_id`, `operation_id?`, `error_summary`, `current_url`, `tried[]`, `options?` | enter `recovery` |
| `step_validating` | `step_id`, `operation_id?`, `locator?` | show validation status |
| `step_executing` | `step_id`, `operation_id?`, `action` | show executing status |
| `step_recorded` | `step` with parent/children metadata | add/update recorded output |
| `step_failed` | `step_id`, `operation_id?`, `error`, `status` | show failed/recovery pending |
| `step_skipped` | `step_id`, `reason` | mark skipped |
| `code_update` | `step_id?`, `operation_id?`, `lines[]`, `full_spec_preview`, `diagnostics[]` | update Code tab |
| `replay_started` | `run_id`, `step_ids` | show replay progress |
| `replay_result` | `step_id`, `operation_id?`, `passed`, `error?` | update replay status |
| `run_completed` | `run_id`, `summary`, `recorded_count`, `skipped_count` | enter completed |
| `session_state` | full snapshot | reconcile frontend after reconnect/load |
| `capability_gap_recorded` | `gap_id`, `needed_capability`, `path` | show non-blocking gap notice |

## Required frontend → backend commands

| Command | Required payload | Meaning |
|---|---|---|
| `run_steps` / `llm_run` | `steps[]` | submit pending LLM steps |
| `confirmed` | `run_id?` | accept current plan |
| `correction` | `message`, `run_id?`, `step_id?` | revise plan or guide recovery |
| `option_selected` | `value`, `answer?`, `run_id?` | answer clarification |
| `replay_step` | `step_id` | replay one parent step |
| `replay_operation` | `step_id`, `operation_id` | replay one child operation |
| `replay_all` | `stop_on_error` | replay full recording |
| `skip_step` | `step_id` | skip failed/current step |
| `stop_run` | `run_id` | stop current run safely |
| `save_session` | `path?`, `name?` | save session/spec |
| `load_session` | `path` | load recording/session |
| `update_locator` | `step_id`, `operation_id?`, `constraints?` | request locator replacement |

## Event validation rules

- Every event must include `type`.
- Step-related events must include `step_id`.
- Child operation events should include `operation_id` when applicable.
- `error` events must include user-friendly `message` and optional technical `detail`.
- Frontend should ignore unknown events only after logging them visibly for developers.
- Backend should reject invalid commands with typed error responses.

frontend/backend must pass expected outcome through typed payloads. This file owns commands/events like replay_all, save_session, load_session, etc.

Add fields to relevant events/payloads:

pending step / plan_ready / step_recorded / save_snapshot should allow:
expected_outcome
observed_outcome

### Expected criteria

- Frontend can render correct state using events alone, without parsing LLM prose.
- Backend can replay or reconstruct run state from event history and session state.
- Reconnect/remount can restore UI using `session_state`.
- Every UI action maps to one explicit backend command.


## Multi-agent event contract additions

When multi-model orchestration is enabled, agent activity must be visible through typed events and explicit commands.

### Frontend → Backend commands

| Command | Required payload | Expected behavior |
|---|---|---|
| `set_agent_enabled` | `{ agent, enabled }` | Toggle optional agent for active session. Required agents cannot be disabled. |
| `run_page_intelligence` | `{ scope: "current_page" | "selected_section", step_id? }` | Manually trigger Page Intelligence / Locator Agent. |
| `clear_page_intelligence_cache` | `{ url?, scope? }` | Clear cached page intelligence for current URL/section. |
| `get_agent_trace` | `{ run_id? }` | Request recent model/agent call trace. |
| `set_model_for_agent` | `{ agent, provider?, model?, base_url? }` | Optional future command to configure model per agent role. |

### Backend → Frontend events

| Event | Required payload | Expected frontend behavior |
|---|---|---|
| `agent_started` | `{ agent, reason, run_id?, step_id? }` | Show agent as running and display why it started. |
| `agent_progress` | `{ agent, stage, summary? }` | Update agent status without exposing raw prompts by default. |
| `agent_result` | `{ agent, summary, confidence?, risk?, artifacts? }` | Show concise result and attach structured artifact/page intelligence if relevant. |
| `agent_failed` | `{ agent, error, fallback_used? }` | Show failure and fallback path; core runtime should continue if possible. |
| `agent_trace` | `{ items[] }` | Display model call trace: purpose, model, tokens, cost, latency, summary. |
| `agent_settings` | `{ agents[] }` | Render current enabled/disabled/model configuration. |

### Expected criteria

- UI does not infer agent activity from text logs.
- Every optional agent call emits start and result/failure events.
- Agent toggles are session-scoped and visible in UI.
- Model call telemetry is available for debugging cost/latency.
- Optional agent failure never corrupts Step Runner state.


---

> **Preserved v2.2 reference only.** If this section conflicts with v2.3 guidance above, v2.3 wins.

## Preserved v2.2 WebSocket Protocol section

All messages are JSON. Direction: → = Panel to Backend, ← = Backend to Panel.

### Panel → Backend

| Message | Payload | Description |
|---|---|---|
| `pick_start` | `{}` | Start element pick mode |
| `pick_cancel` | `{}` | Cancel pick mode |
| `append_step` | `{ action, locator, params, mode }` | Add step to session |
| `validate_step` | `{ action, locator, params, stepId? }` | Validate one step live |
| `run_step` | `{ stepId }` | Run single step |
| `replay` | `{ startIndex?, stopOnError? }` | Replay all/partial steps |
| `pause_replay` | `{}` | Pause after current action |
| `resume` | `{ overrideLocator?, overrideParams? }` | Resume from pause |
| `stop_replay` | `{}` | Hard stop |
| `skip_step` | `{ stepId }` | Skip current/specified step |
| `llm_run` | `{ steps[], mode }` | Submit steps to LLM agent |
| `llm_cancel` | `{}` | Cancel running LLM agent |
| `force_fix` | `{ stepId }` | Trigger repair cascade for step |
| `llm_assist` | `{ stepId, maxIterations? }` | LLM repair for step |
| `delete_step` | `{ stepId }` | Delete step |
| `edit_step` | `{ stepId, action, locator, params }` | Edit step |
| `insert_step` | `{ index, action, locator?, params? }` | Insert step at position |
| `reorder_step` | `{ stepId, newIndex }` | Reorder step |
| `save_version` | `{ name, stepIds? }` | Save named version |
| `load_version` | `{ name }` | Load named version |
| `list_versions` | `{}` | List all saved versions |
| `delete_version` | `{ name }` | Delete named version |
| `start_recording` | `{}` | Start auto-recording mode |
| `stop_recording` | `{}` | Stop auto-recording mode |
| `get_code` | `{ format? }` | Request generated TypeScript |
| `save_to_file` | `{ path? }` | Save session JSON to default location |
| `save_as_file` | `{ path, name }` | Save session JSON to custom path/name |
| `save_copy` | `{ path, name }` | Save a copy, continue on original |
| `load_from_file` | `{ path? }` | Load session JSON (recent list or browse) |
| `load_from_path` | `{ path }` | Load session from specific filesystem path |
| `set_mode` | `{ mode: "manual"\|"llm" }` | Switch mode |
| `set_llm_config` | `{ provider, model, api_key, base_url }` | Configure LLM |

### Backend → Panel

| Message | Payload | Description |
|---|---|---|
| `ready` | `{ runId, mode, llmStatus, domain }` | Session ready |
| `pick_result` | `{ locator, candidates[], element, framePath? }` | Element picked + locators ranked |
| `pick_cancelled` | `{}` | Pick cancelled |
| `step_list` | `{ steps[] }` | Full current step list |
| `step_status` | `{ stepId, status, error? }` | Single step status update |
| `validate_result` | `{ passed, error?, friendlyError?, durationMs }` | Validation result |
| `replay_status` | `{ running, currentIndex?, paused?, error? }` | Replay progress |
| `llm_thinking` | `{ message }` | LLM working — show to user |
| `llm_tool_call` | `{ tool, args }` | LLM called a tool — show progress |
| `llm_result` | `{ success, summary, stepsUpdated[] }` | LLM run complete |
| `force_fix_progress` | `{ stage, detail?, attempts? }` | Repair in progress |
| `force_fix_result` | `{ success, locator?, reason?, attempts[] }` | Repair complete |
| `llm_assist_progress` | `{ iteration, attempt, strategy }` | LLM repair progress |
| `llm_assist_result` | `{ success, patch?, attempts[] }` | LLM repair complete |
| `highlight_element` | `{ boundingBox, state }` | Draw highlight at coords |
| `clear_highlight` | `{}` | Remove all highlights |
| `code_result` | `{ content, format }` | Generated TypeScript code |
| `step_recorded` | `{ step }` | New step confirmed and saved |
| `session_saved` | `{ path, name }` | Session file saved — shows path to user |
| `session_loaded` | `{ stepCount, path, name }` | Session file loaded |
| `version_saved` | `{ name }` | Version snapshot saved |
| `version_loaded` | `{ name, stepCount }` | Version loaded |
| `versions_list` | `{ versions[] }` | List of saved versions |
| `network_capture` | `{ calls[] }` | Network calls captured |
| `suggestion` | `{ message, actions[] }` | Smart suggestion from agent |
| `error` | `{ message, detail?, code? }` | Error with typed code |

---