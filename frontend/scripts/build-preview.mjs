#!/usr/bin/env node
// Build the standalone demo preview entry by inlining dist/autoworkbench.css
// into scripts/preview.html (template) → dist/preview.html.
//
// Inlining is required because the ShadowRoot adapter in src/main.jsx
// (ensureShadowStyles) clones from a `<style id="autoworkbench-style">`
// in the document. `<link rel="stylesheet">` does not satisfy this; the
// shadow tree would be unstyled. See FE-VBATCH-001 Story 3.

import { readFileSync, writeFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = dirname(fileURLToPath(import.meta.url));
const FRONTEND = join(__dirname, "..");

const TEMPLATE = readFileSync(join(__dirname, "preview.html"), "utf-8");
const CSS = readFileSync(join(FRONTEND, "dist", "autoworkbench.css"), "utf-8");

// Replace the empty <style id="autoworkbench-style"></style> tag (and any
// adjacent loader <script>) with the inlined stylesheet.
const inlined = TEMPLATE.replace(
  /<!--[\s\S]*?-->\s*<style id="autoworkbench-style"><\/style>\s*<script>[\s\S]*?<\/script>/,
  `<style id="autoworkbench-style">\n${CSS}\n</style>`,
);

if (!inlined.includes("autoworkbench-style")) {
  console.error("[build-preview] FAIL — could not inline autoworkbench.css into preview.html.");
  process.exit(1);
}

writeFileSync(join(FRONTEND, "dist", "preview.html"), inlined);
console.log(
  `[build-preview] OK — dist/preview.html written (CSS ${CSS.length.toLocaleString()} chars inlined).`,
);
