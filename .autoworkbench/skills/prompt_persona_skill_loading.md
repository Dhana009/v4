# Skill: Prompt, Persona, and Skill Loading

## Purpose
Keep prompts compact, purpose-specific, and skill loading controlled.

## When to use
Use when editing prompts, personas, system messages, skills, skill loader, context manager, LLM purpose policies, user-loaded personas.

## Source of truth
- LLM Runtime Policy Spec
- PRD progressive skill loading guidance
- Memory/Human Feedback skill

## Non-negotiable rules
1. Do not use one giant universal system prompt for every call.
2. Keep common core prompt compact.
3. Persona is purpose-specific.
4. User-loaded persona cannot override backend truth/safety/schema/tool policy.
5. Skills load by purpose/capability/failure, not broad phase alone.
6. Full skill loads only with reason and budget.
7. Every call logs skills loaded and token impact.
8. Schema requirements must be explicit.
9. Do not widen skill packs from intuition.

## Skill levels
```text
none
core_compact
skill_summary
full_skill
debug_skill
capability_skill
```

## Required implementation behavior
- Define prompt policy per LLM purpose.
- Use compact core + purpose persona + relevant skill summary.
- Avoid repeating large rules in every call.
- Provide skill index/lazy loading.
- Track skill_count, skill_names, estimated_skill_tokens.
- Add schema reminders only on retry.

## Required tests
- skill selection by purpose
- no broad default skill load
- user persona boundaries
- prompt token estimates
- schema retry behavior

## Verification commands
```bash
python -m pytest tests/test_context_manager.py tests/test_*skill* tests/test_*prompt* -q
```

## Stop conditions
Stop if:
- required evidence is missing, unclear, or contradictory
- system prompt grows unnecessarily
- skills are loaded by default without relevance
- user persona can bypass safety
- prompt lacks required schema
- token budget is not logged

## Reporting format
Report:
1. Prompt/persona changed
2. Skills loaded/removed
3. Token impact
4. Tests/results
5. Drift risks
