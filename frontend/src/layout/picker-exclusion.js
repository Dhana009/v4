// layout/picker-exclusion.js — Picker exclusion for AutoWorkbench UI
// S7-0408: Element picker targets only page content, not panel UI elements.

export const PICKER_EXCLUSION_SELECTOR = [
  "#autoworkbench-root",
  "#aw-shadow-host",
  "[data-autoworkbench]",
  "[data-aw-ui]",
].join(", ");

/**
 * Returns true if the element is part of AutoWorkbench UI and must be excluded from picker.
 * Checks element itself and all ancestors.
 */
export function isExcluded(element) {
  if (!element) return false;

  // Direct match against exclusion selectors
  if (typeof element.matches === "function") {
    try {
      if (element.matches(PICKER_EXCLUSION_SELECTOR)) return true;
    } catch (_) {}
  }

  // Check if element is inside an AutoWorkbench ancestor
  if (typeof element.closest === "function") {
    const ancestor = element.closest("[data-autoworkbench], #autoworkbench-root");
    if (ancestor) return true;
  } else {
    // Fallback: walk parentNode chain
    let node = element.parentNode;
    while (node) {
      if (
        node.id === "autoworkbench-root"
        || (node.hasAttribute && node.hasAttribute("data-autoworkbench"))
      ) return true;
      node = node.parentNode;
    }
  }

  // Direct attribute check
  if (
    typeof element.hasAttribute === "function"
    && (element.hasAttribute("data-autoworkbench") || element.hasAttribute("data-aw-ui"))
  ) return true;

  return false;
}

/**
 * Returns a filter function that passes only non-AutoWorkbench elements.
 * Use with element picker: candidates.filter(getExclusionFilter()).
 */
export function getExclusionFilter() {
  return (element) => !isExcluded(element);
}
