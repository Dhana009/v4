# S6-1003 LLM tab: chat, plan, clarification, permission, recovery cards

**Sprint:** Sprint 6  
**Cluster:** 10  
**Tier:** 1 (core)  
**Type:** Feature / UI Tab  
**Status:** Planning  
**Owner:** Frontend LLM Tab  
**Blocks:** S6-1012  
**Blocked by:** S6-1002  

---

## Purpose

Complete the main agent workspace. Conversation history, active plan card, recommendation card, clarification card, permission card, recovery card, chat input, plan revision discussion.

---

## What it contains

- conversation history from conversation_state
- active plan card
- recommendation card
- clarification card
- permission card
- recovery card
- chat input
- plan revision discussion/actions

---

## Tests first

Frontend tests: clarification_needed renders exact question/options, permission_required renders risk/choices, recovery_needed renders failed stage/evidence/next actions, plan_ready renders plan_id/version/children, plan discussion doesn't mutate local plan.

Coverage: **95%**

---

## Allowed files

```
frontend/src/components/llm/ (new)
frontend/src/store/conversation.ts (new)
Tests: test_llm_tab.ts
```

---

## Sign-off

- [x] Story is specific (LLM tab cards)
- [x] Tests are first
- [x] Blocks integration proof
