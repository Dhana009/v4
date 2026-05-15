# Skill: Codegen

## Purpose
Generate deterministic, runnable Playwright TypeScript from validated recorded evidence.

## When to use
Use when touching code_update, generated lines, code preview, code export, recorded child operation code, locator code conversion, capability code templates.

## Source of truth
- PRD codegen/replay persistence guidance
- Recorded step model
- Capability framework

## Non-negotiable rules
1. Codegen is backend-owned and deterministic-first.
2. Generate code from recorded evidence, not LLM prose.
3. Preserve parent/child operation order.
4. If recording payload is wrong, do not hide it in codegen.
5. Unsupported capability should produce warning/gap, not fake code.
6. Locator formatting must match validated locator strategy.
7. Code tab should show warnings for fragile/incomplete code.

## Required implementation behavior
- Use recorded_step_detail children[] as source.
- Generate code_lines per child operation.
- Update code_state with source_recorded_step_ids.
- Include fragile locator warnings.
- Include incomplete capability warnings.
- Keep code_update events typed.

## Required tests
- single action codegen
- assertion codegen
- multi-child order codegen
- locator formatting
- capability template tests
- incomplete/unsupported warning tests
- code_update event tests

## Verification commands
```bash
python -m pytest tests/test_code_update.py tests/test_*codegen* -q
```

## Stop conditions
Stop if:
- code is generated from unvalidated LLM text
- operation order is ambiguous
- unsupported capability lacks warning
- locator not validated
- code_update event shape is unclear

## Reporting format
Report:
1. Codegen behavior changed
2. Source evidence used
3. Tests/results
4. Warnings/gaps
