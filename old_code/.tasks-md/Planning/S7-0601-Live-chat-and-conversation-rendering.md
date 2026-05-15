# S7-0601 — Live Chat and Conversation Rendering

**Sprint:** Sprint 7  
**Cluster:** 6  
**Tier:** 1  
**Type:** Feature  
**Status:** Done  
**Owner:** Frontend  
**Blocks:** S7-0602, S7-0603, S7-0604, S7-0605, S7-0606, S7-0607, S7-0608, S7-0609, S7-0610  
**Blocked by:** Cluster 2 (Cluster 2 must emit live events)

---

## Objective

Replace static demo message stream in LLM tab with live-rendered messages from backend/transport state. Frontend must render user intent, assistant summaries, LLM thinking, and runtime errors as they arrive via typed backend events.

Today: Frontend renders static mock conversation.
After S7-0601: Frontend renders real message stream from backend events, displays empty state when no messages exist, handles reconnect/session restore correctly.

---

## Source Rules

1. **PRD-03-FE-001:** Frontend renders typed backend events only; no inference.
2. **PRD-04-BE-001:** Backend emits run_started, step_executing, step_recorded, runtime_rejected lifecycle events.
3. **PRD-03-FE-002:** Message stream is a sequence of typed events; unknown message types logged and ignored safely.
4. **PRD-03-FE-003:** Empty first-run state shown when no messages exist; no placeholder demo content in live mode.
5. **GOV-S7-C0-001:** Test-first protocol; tests written before implementation.
6. **GOV-S7-C0-012:** Modularization rule; message rendering logic in focused component, not monolithic main.jsx.
7. **GOV-S7-C0-008:** No source rule → no test; no test → no implementation.

---

## Current Known Context

### What exists in the repo

- `frontend_new_design_prototype/llm-tab.jsx` — Reference UI with message display layout (47KB; design only)
- Transport layer: WebSocket event queue exists; events reach frontend
- `runtime/event_contracts.py` — Backend event type definitions from Sprint 6
- Frontend store initial implementation but not fully wired to IDEPanel props
- No dedicated message reducer or component yet

### What gaps exist

- No message reducer (event stream → message state)
- No message display component wired to backend events
- No empty state handling for first run
- Static demo messages appear in live mode instead of empty state
- Message types from backend not fully enumerated (user_intent, assistant_summary, llm_thinking, runtime_rejected)
- Timestamps and correlation IDs for messages not tracked
- Session restore/reconnect message deduplication logic missing

### Current test status

- No tests exist for message rendering
- Existing test suite does not cover message stream behavior
- Frontend component tests not present (will be new)

---

## Tests First

### Unit Tests

```
test_message_reducer_receives_user_intent_event()        # PRD-03-FE-001
test_message_reducer_receives_assistant_summary_event()  # PRD-03-FE-001
test_message_reducer_handles_llm_thinking_event()        # PRD-03-FE-001
test_message_reducer_handles_runtime_rejected_event()    # PRD-03-FE-001
test_message_reducer_handles_timestamp_and_correlation() # PRD-03-FE-003
test_message_reducer_restores_messages_from_session_state() # PRD-04-BE-001
```

File: `tests/test_frontend_message_reducer.py`

### Contract Tests

```
test_run_started_event_payload_includes_run_id()         # PRD-04-BE-001
test_user_intent_message_has_intent_text_and_timestamp() # PRD-03-FE-001
test_assistant_summary_message_has_summary_and_model()   # PRD-03-FE-001
test_llm_thinking_message_has_reasoning()                # PRD-03-FE-001
test_runtime_rejected_message_has_error_and_reason()     # PRD-03-FE-001
test_malformed_event_payload_rejected()                  # GOV-S7-C0-009
```

File: `tests/test_frontend_message_contract.py`

### Component Render Tests

```
test_message_list_renders_empty_when_no_messages()       # PRD-03-FE-003
test_message_list_renders_user_intent_message()          # PRD-03-FE-001
test_message_list_renders_assistant_summary_message()    # PRD-03-FE-001
test_message_list_renders_llm_thinking_in_collapse()     # PRD-03-FE-001
test_message_list_renders_runtime_rejected_as_error()    # PRD-03-FE-001
test_message_timestamp_displayed()                       # PRD-03-FE-003
test_no_static_demo_content_in_live_mode()               # PRD-03-FE-003
```

File: `tests/test_frontend_message_component.py`

### Integration Tests

```
test_run_started_event_triggers_message_reducer()        # PRD-03-FE-001
test_event_sequence_produces_correct_message_order()     # PRD-03-FE-003
test_reconnect_restores_message_list_without_dups()      # PRD-04-BE-001
test_session_state_event_reconciles_messages()           # PRD-04-BE-001
```

File: `tests/test_frontend_message_integration.py`

### Negative Tests

```
test_null_message_text_handled_safely()                  # GOV-S7-C0-009
test_empty_message_text_shows_empty_state()              # GOV-S7-C0-009
test_unknown_message_type_logged_not_rendered()          # GOV-S7-C0-009
test_message_id_mismatch_in_reconnect_detected()         # GOV-S7-C0-009
test_duplicate_message_id_not_rendered_twice()           # GOV-S7-C0-009
test_missing_timestamp_safe()                            # GOV-S7-C0-009
```

File: `tests/test_frontend_message_negative.py`

### Regression Tests

Must stay green:
- `python -m pytest tests/test_frontend_*.py -q` (existing frontend tests)
- `python -m pytest tests/test_event_contracts.py -q` (backend event contracts)
- `python -m pytest -q --ignore=tests/e2e` (full cheap regression gate)

---

## Implementation Boundaries

### Allowed Files

- **New:** `frontend/src/components/messages/MessageList.jsx` — Main message list component
- **New:** `frontend/src/components/messages/Message.jsx` — Individual message component
- **New:** `frontend/src/store/message_reducer.js` — Reducer for message events
- **New:** `frontend/src/store/messages.js` — Message store slice with action creators
- **New:** `frontend/src/styles/messages.css` — Message styling
- **New:** `tests/test_frontend_message_*.py` — All tests listed above
- **Modify:** `frontend/src/aw-ide-panel.jsx` — Thread message state and dispatch into props (thin wiring only; ≤10 lines)
- **Modify:** `frontend/src/main.jsx` — Mount message reducer into store (thin wiring only)
- **Modify:** `frontend/src/transport/event_handlers.js` — Route backend message events to message reducer

### Forbidden Files

- No `runtime/` changes
- No `agent.py` changes
- No `server.py` or `ws/` changes
- No direct `browser.py` modifications
- No legacy overlay wiring
- No monolith expansion (main.jsx, aw-ide-panel.jsx beyond thin seams)

---

## Implementation Notes

### Approach

1. Define message types in TypeScript/JavaScript:
   - `{ type: "user_intent", run_id, intent_text, timestamp }`
   - `{ type: "assistant_summary", run_id, summary, model_used, timestamp }`
   - `{ type: "llm_thinking", step_id, reasoning, timestamp, collapsed: true }`
   - `{ type: "runtime_rejected", error, reason, timestamp }`

2. Create message reducer:
   - Action: `ADD_MESSAGE(message)` → append to messages[]
   - Action: `RESTORE_MESSAGES(messages[])` → replace on session_state event
   - Action: `CLEAR_MESSAGES()` → reset on new run

3. Create MessageList component:
   - Accept messages[] prop from store
   - Map to individual Message components
   - Show empty state if messages.length === 0 && run started
   - No demo content

4. Create Message component:
   - Render message content based on type
   - Handle llm_thinking collapse
   - Display timestamp
   - Safe render of null/empty fields

5. Wire message reducer into transport event handler:
   - On `user_intent` event → dispatch ADD_MESSAGE
   - On `assistant_summary` event → dispatch ADD_MESSAGE
   - On `session_state` event → dispatch RESTORE_MESSAGES
   - On unknown event → log and ignore

6. Thread into IDEPanel:
   - Pass messages prop
   - Pass dispatch callback if needed for future interactions

### Key Invariants

- Empty state appears when run_started received but no messages yet
- No demo content appears in live mode (assert in tests)
- Message order matches backend event sequence
- Reconnect does not duplicate messages
- Unknown message types are logged, not rendered

### Known Risks

- Message reducer state and IDEPanel state can get out of sync if not wired correctly → test integration
- Timestamp parsing inconsistency → enforce ISO format in contract tests
- LLM thinking text could be very long → test component handles long text safely
- Session restore could send duplicate message IDs → test deduplication logic

---

## Coverage Requirement

Minimum 95% line coverage for new modules.

```bash
python -m pytest tests/test_frontend_message_*.py --cov=frontend/src/components/messages --cov=frontend/src/store/message_reducer --cov-fail-under=95
```

---

## Validation Commands

```bash
# All message tests
python -m pytest tests/test_frontend_message_*.py -v

# Regression guard
python -m pytest -q --ignore=tests/e2e 2>&1 | tail -5

# Coverage
python -m pytest tests/test_frontend_message_*.py --cov=frontend/src/components/messages --cov=frontend/src/store/message_reducer --cov-fail-under=95
```

---

## Acceptance Criteria

- [ ] All message reducer tests pass (unit + contract + integration + negative)
- [ ] All message component tests pass
- [ ] Empty state appears when no messages (no demo content)
- [ ] No new failures in regression guard
- [ ] Coverage ≥ 95% for new modules
- [ ] MessageList + Message components wired to IDEPanel
- [ ] Session restore deduplicates messages correctly
- [ ] Unknown message events logged safely

---

## Evidence Required

- [ ] `frontend/src/components/messages/MessageList.jsx` exists
- [ ] `frontend/src/components/messages/Message.jsx` exists
- [ ] `frontend/src/store/message_reducer.js` exists
- [ ] `tests/test_frontend_message_*.py` files exist and pass
- [ ] All tests green — output pasted
- [ ] Regression guard passes
- [ ] Coverage ≥ 95%
- [ ] Story status updated to Done with commit hash

---

## Stop Conditions

- Cannot write message reducer tests without defining exact event payload shapes from backend
- Backend events missing from Cluster 2 (user_intent, assistant_summary)
- Component render requires inferring state from LLM text
- Transport layer requires broad refactor
- Coverage falls below 95%
- New regression test failures appear


---

## Evidence Recorded

- **Commit:** a84bf22 — Cluster 6 LLM card extraction
- **File:** `frontend/src/components/llm/` — ConversationView.jsx — renders messages from store; empty state; no demo
- **Test:** tests/test_frontend_llm_cards.py (36 tests verify typed commands, empty states, no demo, no local lifecycle mutation)
- **Build:** dist/autoworkbench.js 1.3mb (clean)
- **Regression:** 2383 passed / 1 skipped / 0 failed
