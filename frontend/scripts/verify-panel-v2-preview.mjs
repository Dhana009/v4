/**
 * Smoke-checks the panel-v2 Vite dev server.
 * Usage: start `npm run dev:panel-v2` first, then run this script.
 *
 * Limitation: no Playwright available in this project, so checks are HTTP-only.
 * For full DOM/interaction verification use the vitest suite:
 *   npm run test:panel-v2
 */

const BASE = "http://127.0.0.1:5173";

async function check(label, url, predicate) {
  try {
    const res = await fetch(url);
    const text = await res.text();
    if (!res.ok) {
      console.error(`FAIL [${label}] HTTP ${res.status} for ${url}`);
      return false;
    }
    if (predicate && !predicate(text)) {
      console.error(`FAIL [${label}] content check failed for ${url}`);
      return false;
    }
    console.log(`PASS [${label}]`);
    return true;
  } catch (err) {
    console.error(`FAIL [${label}] ${err.message}`);
    return false;
  }
}

const results = await Promise.all([
  check("root /", `${BASE}/`, (t) => t.includes("panel-v2-preview.html")),
  check("panel-v2-preview.html", `${BASE}/panel-v2-preview.html`, (t) => t.includes("panel-v2")),
  check("src/panel-v2/app.jsx", `${BASE}/src/panel-v2/app.jsx`, (t) => t.includes("aw-stage")),
  check("src/panel-v2/styles.css", `${BASE}/src/panel-v2/styles.css`, (t) => t.includes(".aw-header")),
]);

const failed = results.filter((r) => !r).length;
if (failed > 0) {
  console.error(`\n${failed} check(s) failed.`);
  process.exit(1);
} else {
  console.log(`\nAll ${results.length} checks passed.`);
}
