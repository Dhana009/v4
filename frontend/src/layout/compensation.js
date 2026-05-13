// layout/compensation.js — Page content compensation
// S7-0405: Adjusts page size when panel docked to prevent content overlap.
//          Saves original style values for clean restore on unmount.

const SAVED_ATTR_PREFIX = "data-aw-original-";

function saveOriginalStyle(el, prop) {
  const attr = `${SAVED_ATTR_PREFIX}${prop}`;
  if (!el.hasAttribute(attr)) {
    el.setAttribute(attr, el.style[prop] ?? "");
  }
}

function restoreOriginalStyle(el, prop) {
  const attr = `${SAVED_ATTR_PREFIX}${prop}`;
  if (el.hasAttribute(attr)) {
    el.style[prop] = el.getAttribute(attr);
    el.removeAttribute(attr);
  }
}

/**
 * Apply page body/html compensation for the given dock mode and panel size.
 * floating mode: no compensation (returns immediately).
 */
export function applyCompensation(dockMode, panelSize) {
  if (dockMode === "floating") return;

  const body = document.body;
  const html = document.documentElement;
  if (!body || !html) return;

  if (dockMode === "dock-right") {
    const width = panelSize?.width ?? 380;
    saveOriginalStyle(body, "width");
    saveOriginalStyle(body, "maxWidth");
    saveOriginalStyle(html, "width");
    saveOriginalStyle(html, "maxWidth");
    body.style.width = `calc(100vw - ${width}px)`;
    body.style.maxWidth = `calc(100vw - ${width}px)`;
  } else if (dockMode === "dock-left") {
    const width = panelSize?.width ?? 380;
    saveOriginalStyle(body, "marginLeft");
    body.style.marginLeft = `${width}px`;
  } else if (dockMode === "dock-bottom") {
    const height = panelSize?.height ?? 300;
    saveOriginalStyle(body, "height");
    saveOriginalStyle(body, "maxHeight");
    body.style.height = `calc(100vh - ${height}px)`;
    body.style.maxHeight = `calc(100vh - ${height}px)`;
  }
}

/**
 * Remove all compensation and restore original page styles.
 */
export function removeCompensation() {
  const body = document.body;
  const html = document.documentElement;
  if (!body || !html) return;

  const props = ["width", "maxWidth", "height", "maxHeight", "marginLeft", "paddingRight"];
  props.forEach((prop) => {
    restoreOriginalStyle(body, prop);
    restoreOriginalStyle(html, prop);
  });
}

/**
 * Re-apply compensation with updated panel size (called on resize).
 */
export function updateCompensation(dockMode, panelSize) {
  removeCompensation();
  applyCompensation(dockMode, panelSize);
}
