# S6-1005 Recommendation review UI

**Sprint:** Sprint 6  
**Cluster:** 10  
**Tier:** 1 (core)  
**Type:** Feature / UI Card  
**Status:** Planning  
**Owner:** Frontend Recommendations  
**Blocks:** S6-1012  
**Blocked by:** S6-1002  

---

## Purpose

Render Page Intelligence recommendations for review before plan creation. Grouped recommendations by section, priority critical/useful/optional, accept/remove/reorder, show ambiguity/risk/capability warnings, convert accepted recommendations via backend command.

---

## What it contains

- grouped recommendations by section
- priority badges
- accept/remove/reorder UI
- ambiguity/risk/capability warnings
- backend command dispatch

---

## Tests first

Frontend tests: recommendation_ready renders grouped sections, unaccepted recommendation not sent as executable, accept subset sends typed command, capability warning shown.

Coverage: **95%**

---

## Allowed files

```
frontend/src/components/recommendations/ (new)
frontend/src/store/recommendations.ts (new)
Tests: test_recommendations.ts
```

---

## Sign-off

- [x] Story is specific (recommendation review UI)
- [x] Tests are first
