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

// Replace the empty <style id="autoworkbench-style"></style> placeholder with
// the inlined stylesheet. Tolerate optional inner whitespace.
const PLACEHOLDER = /<style id="autoworkbench-style">\s*<\/style>/;
if (!PLACEHOLDER.test(TEMPLATE)) {
  console.error(
    "[build-preview] FAIL — preview.html template missing empty <style id=\"autoworkbench-style\"></style> placeholder.",
  );
  process.exit(1);
}
const inlined = TEMPLATE.replace(
  PLACEHOLDER,
  `<style id="autoworkbench-style">\n${CSS}\n</style>`,
);

// Sanity: confirm the resulting file actually carries the bundled stylesheet.
if (inlined.length - TEMPLATE.length < CSS.length / 2) {
  console.error("[build-preview] FAIL — inlined CSS did not grow the document.");
  process.exit(1);
}

writeFileSync(join(FRONTEND, "dist", "preview.html"), inlined);
console.log(
  `[build-preview] OK — dist/preview.html written (CSS ${CSS.length.toLocaleString()} chars inlined).`,
);
