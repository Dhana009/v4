/**
 * build.mjs — AutoWorkbench overlay bundle builder
 *
 * Produces:
 *   frontend/dist/autoworkbench.js  — React 18.3.1 UMD + transformed JSX sources
 *   frontend/dist/autoworkbench.css — verbatim copy of styles.css
 *
 * Exposes window.AutoWorkbench.mount(rootEl, config) for browser.py overlay injection.
 *
 * Usage:
 *   node build.mjs          (from frontend/ dir, or any dir — uses __dirname-equivalent)
 *   cd frontend && npm run build
 */

import { execSync } from "child_process";
import { readFileSync, writeFileSync, mkdirSync, existsSync } from "fs";
import { dirname, resolve, join } from "path";
import { fileURLToPath } from "url";
import { createRequire } from "module";

const __dirname = dirname(fileURLToPath(import.meta.url));
const ROOT = __dirname; // frontend/

const DIST = join(ROOT, "dist");
const OUT_JS = join(DIST, "autoworkbench.js");
const OUT_CSS = join(DIST, "autoworkbench.css");

// JSX files in load order (matches index.html lines 308-315)
const JSX_FILES = [
  "tweaks-panel.jsx",
  "icons.jsx",
  "website.jsx",
  "chrome.jsx",
  "llm-tab.jsx",
  "secondary-tabs.jsx",
  "transport.jsx",
  "app.jsx",
];

// React 18.3.1 UMD production CDN URLs (fetched at build time and inlined)
const REACT_UMD_URL = "https://unpkg.com/react@18.3.1/umd/react.production.min.js";
const REACT_DOM_UMD_URL = "https://unpkg.com/react-dom@18.3.1/umd/react-dom.production.min.js";

// Local cache paths so repeated builds don't re-download
const CACHE_DIR = join(ROOT, ".build-cache");
const REACT_CACHE = join(CACHE_DIR, "react.production.min.js");
const REACT_DOM_CACHE = join(CACHE_DIR, "react-dom.production.min.js");

function log(msg) {
  process.stdout.write(msg + "\n");
}

function fetchOrCache(url, cachePath) {
  if (existsSync(cachePath)) {
    log(`  cache hit: ${cachePath}`);
    return readFileSync(cachePath, "utf8");
  }
  log(`  downloading ${url} ...`);
  // Use curl (available on macOS/Linux) as Node stdlib has no built-in fetch writing to string sync
  const content = execSync(`curl -fsSL "${url}"`, { maxBuffer: 50 * 1024 * 1024 }).toString("utf8");
  mkdirSync(CACHE_DIR, { recursive: true });
  writeFileSync(cachePath, content, "utf8");
  return content;
}

function transformJsx(filePath) {
  // Use bunx esbuild to transform JSX -> React.createElement calls (no bundling, no imports)
  // esbuild is available via bunx in this project (bun 1.3.12 at /Users/apple/.bun/bin/bun)
  const bunPath = "/Users/apple/.bun/bin/bun";
  const bunExists = existsSync(bunPath);
  const esbuildCmd = bunExists
    ? `"${bunPath}" x esbuild "${filePath}" --bundle=false --jsx=transform`
    : `bunx esbuild "${filePath}" --bundle=false --jsx=transform`;

  try {
    return execSync(esbuildCmd, { maxBuffer: 20 * 1024 * 1024 }).toString("utf8");
  } catch (e) {
    // Fallback: try npx esbuild
    log(`  warn: bunx failed, trying npx esbuild`);
    return execSync(`npx --yes esbuild "${filePath}" --bundle=false --jsx=transform`, {
      maxBuffer: 20 * 1024 * 1024,
    }).toString("utf8");
  }
}

async function main() {
  log("AutoWorkbench overlay bundle builder");
  log("=====================================");

  mkdirSync(DIST, { recursive: true });

  // 1. Fetch / cache React UMD builds
  log("\n[1/4] Fetching React 18.3.1 UMD production builds...");
  const reactUmd = fetchOrCache(REACT_UMD_URL, REACT_CACHE);
  const reactDomUmd = fetchOrCache(REACT_DOM_UMD_URL, REACT_DOM_CACHE);
  log(`  react.js: ${reactUmd.length} bytes, react-dom.js: ${reactDomUmd.length} bytes`);

  // 2. Transform each JSX file
  log("\n[2/4] Transforming JSX files...");
  const transformedChunks = [];
  for (const file of JSX_FILES) {
    const filePath = join(ROOT, file);
    log(`  ${file}`);
    let code = transformJsx(filePath);

    // Replace the app.jsx mount line:
    //   ReactDOM.createRoot(document.getElementById("root")).render(<App/>);
    // with a window.AutoWorkbench.mount(rootEl, config) exposure.
    // We do this substitution on the last file (app.jsx) only.
    if (file === "app.jsx") {
      // Remove the hard-wired mount line
      code = code.replace(
        /ReactDOM\.createRoot\s*\(\s*document\.getElementById\s*\(\s*["']root["']\s*\)\s*\)\.render\s*\(\s*\/\*.*?\*\/\s*React\.createElement\s*\(\s*App[^)]*\)\s*\)\s*;?/,
        ""
      );
      // Also handle the non-pure-annotation variant
      code = code.replace(
        /ReactDOM\.createRoot\s*\(\s*document\.getElementById\s*\(\s*["']root["']\s*\)\s*\)\.render\s*\(\s*React\.createElement\s*\(\s*App[^)]*\)\s*\)\s*;?/,
        ""
      );
    }

    transformedChunks.push(`\n// ---- ${file} ----\n${code}`);
  }

  // 3. Assemble the bundle
  log("\n[3/4] Assembling bundle...");

  const mountApi = `
// ---- AutoWorkbench overlay mount API ----
// Exposed as window.AutoWorkbench.mount(rootEl, config) for browser.py injection.
// browser.py bootstrap calls: window.AutoWorkbench.mount(rootEl, CONFIG)
// where CONFIG = { wsUrl, wsPort, state, tab, panelWidth, density, ... }
(function () {
  "use strict";
  var _mountedRoot = null;

  window.AutoWorkbench = window.AutoWorkbench || {};

  window.AutoWorkbench.mount = function (rootEl, config) {
    if (_mountedRoot) {
      try { _mountedRoot.unmount(); } catch (e) {}
    }
    // Apply config to window.AW so transport.jsx picks up wsUrl etc.
    if (config) {
      window.AW = window.AW || {};
      if (config.wsUrl) { window.AW.wsUrl = config.wsUrl; }
      if (config.wsPort) { window.AW.wsPort = config.wsPort; }
      // Seed tweaks with matching keys
      var TWEAK_KEYS = ["state", "tab", "panelWidth", "density", "collapsed", "connection",
                        "showWebsite", "agentsOpen", "theme", "mode", "dock"];
      var initEvent = {};
      TWEAK_KEYS.forEach(function (k) {
        if (config[k] !== undefined) { initEvent[k] = config[k]; }
      });
      if (Object.keys(initEvent).length) {
        window.dispatchEvent(new CustomEvent("aw:set", { detail: initEvent }));
      }
    }
    _mountedRoot = ReactDOM.createRoot(rootEl);
    _mountedRoot.render(React.createElement(App));
    return _mountedRoot;
  };

  window.AutoWorkbench.unmount = function () {
    if (_mountedRoot) {
      try { _mountedRoot.unmount(); } catch (e) {}
      _mountedRoot = null;
    }
  };
})();
`;

  const bundle = [
    "// AutoWorkbench overlay bundle — generated by build.mjs",
    "// React 18.3.1 + ReactDOM 18.3.1 UMD (inlined) + AutoWorkbench app JSX",
    "// DO NOT EDIT — regenerate with: cd frontend && npm run build",
    "",
    "// ---- react.production.min.js ----",
    reactUmd,
    "",
    "// ---- react-dom.production.min.js ----",
    reactDomUmd,
    "",
    ...transformedChunks,
    "",
    mountApi,
  ].join("\n");

  writeFileSync(OUT_JS, bundle, "utf8");
  log(`  wrote ${OUT_JS} (${bundle.length} bytes)`);

  // 4. Copy CSS verbatim
  log("\n[4/4] Copying styles.css -> dist/autoworkbench.css...");
  const css = readFileSync(join(ROOT, "styles.css"), "utf8");
  writeFileSync(OUT_CSS, css, "utf8");
  log(`  wrote ${OUT_CSS} (${css.length} bytes)`);

  log("\nBuild complete.");
  log(`  dist/autoworkbench.js  : ${bundle.length.toLocaleString()} bytes`);
  log(`  dist/autoworkbench.css : ${css.length.toLocaleString()} bytes`);

  // Quick smoke test
  if (!bundle.includes("React")) {
    log("ERROR: bundle does not contain 'React' — build may be broken!");
    process.exit(1);
  }
  if (!bundle.includes("AutoWorkbench")) {
    log("ERROR: bundle does not expose AutoWorkbench — build may be broken!");
    process.exit(1);
  }
  log("  smoke check: OK (React + AutoWorkbench present)");
}

main().catch((err) => {
  console.error("Build failed:", err);
  process.exit(1);
});
