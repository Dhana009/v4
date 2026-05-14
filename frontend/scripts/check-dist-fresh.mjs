#!/usr/bin/env node
// FE-REF-001: dist freshness guard.
//
// Fails (exit 1) when frontend/dist/autoworkbench.{js,css} is older than any
// active build input. Build inputs are the files that the esbuild bundle entry
// (`src/main.jsx`) transitively pulls in: everything under `src/`, plus the
// root-level CSS imports and the panel root the entry imports directly.
//
// Scope is deliberately narrow per the FE-REF-001 task spec:
//   - check ONLY `dist/autoworkbench.js` and `dist/autoworkbench.css`
//   - check ONLY active build inputs (no legacy carcasses, no tests, no node_modules)
//
// If you add a new top-level source the bundle entry imports, add it to
// ROOT_SOURCE_FILES below.

import { readdirSync, statSync, existsSync } from "node:fs";
import { join, relative, dirname } from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = dirname(fileURLToPath(import.meta.url));
const FRONTEND = join(__dirname, "..");

const DIST_TARGETS = [
  "dist/autoworkbench.js",
  "dist/autoworkbench.css",
];

// Root-level files that src/main.jsx imports directly. Keep in sync with the
// top of src/main.jsx (`import "../styles.css"` etc.).
const ROOT_SOURCE_FILES = [
  "styles.css",
  "style-ide.css",
  "v4.css",
  "icons.jsx",
  "aw-ide-panel.jsx",
];

// Directory tree rooted at src/. Everything inside is a bundle input.
const SRC_DIR = "src";

const SOURCE_EXTS = new Set([".js", ".jsx", ".ts", ".tsx", ".css", ".mjs", ".cjs"]);

function walk(dir, acc) {
  const abs = join(FRONTEND, dir);
  if (!existsSync(abs)) return;
  for (const entry of readdirSync(abs, { withFileTypes: true })) {
    const childRel = join(dir, entry.name);
    if (entry.isDirectory()) {
      walk(childRel, acc);
    } else if (entry.isFile()) {
      const dot = entry.name.lastIndexOf(".");
      if (dot >= 0 && SOURCE_EXTS.has(entry.name.slice(dot))) {
        acc.push(childRel);
      }
    }
  }
}

function mtime(rel) {
  const abs = join(FRONTEND, rel);
  if (!existsSync(abs)) return null;
  return statSync(abs).mtimeMs;
}

function main() {
  const missingDist = DIST_TARGETS.filter((rel) => mtime(rel) === null);
  if (missingDist.length) {
    console.error(
      "[check:dist] FAIL — built asset missing:\n" +
        missingDist.map((p) => "  - " + p).join("\n") +
        "\nRun `npm run build`.",
    );
    process.exit(1);
  }

  const inputs = [...ROOT_SOURCE_FILES];
  walk(SRC_DIR, inputs);

  const distMin = Math.min(...DIST_TARGETS.map(mtime));
  const stale = [];
  let newestSource = 0;
  let newestSourceRel = "";
  for (const rel of inputs) {
    const m = mtime(rel);
    if (m === null) continue;
    if (m > newestSource) {
      newestSource = m;
      newestSourceRel = rel;
    }
    if (m > distMin) stale.push({ rel, m });
  }

  if (stale.length > 0) {
    stale.sort((a, b) => b.m - a.m);
    const head = stale.slice(0, 10);
    const distLines = DIST_TARGETS.map((rel) => {
      const m = mtime(rel);
      return `  - ${rel}  (${new Date(m).toISOString()})`;
    }).join("\n");
    const srcLines = head
      .map((s) => `  - ${s.rel}  (${new Date(s.m).toISOString()})`)
      .join("\n");
    const extra = stale.length > head.length ? `\n  ...and ${stale.length - head.length} more` : "";
    console.error(
      "[check:dist] FAIL — dist is stale.\n" +
        "Sources newer than the oldest dist asset:\n" +
        srcLines +
        extra +
        "\nDist assets:\n" +
        distLines +
        "\nRun `npm run build`.",
    );
    process.exit(1);
  }

  console.log(
    `[check:dist] OK — dist fresh. ${inputs.length} inputs checked; newest source: ${newestSourceRel} @ ${new Date(newestSource).toISOString()}.`,
  );
}

main();
