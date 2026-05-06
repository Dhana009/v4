# AutoWorkbench Skills Library — Install

This zip uses a visible `skills/` folder so it will not look empty in Finder.

## Recommended install

From repo root:

```bash
mkdir -p .autoworkbench/skills
cp -R skills/*.md .autoworkbench/skills/
```

Expected final path:

```text
<repo>/.autoworkbench/skills/00_architecture_contract.md
<repo>/.autoworkbench/skills/01_prd_scope_validation.md
...
```

## Why the previous zip looked empty

It contained `.autoworkbench/skills/`. Folders starting with `.` are hidden on macOS/Finder, so the zip may look empty even though files exist.
