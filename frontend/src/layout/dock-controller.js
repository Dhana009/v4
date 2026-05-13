// layout/dock-controller.js — Dock mode controller
// S7-0402: Dock position (right/left/bottom/floating), CSS class application, persistence.

export const VALID_DOCK_MODES = ["dock-right", "dock-left", "dock-bottom", "floating"];
export const DEFAULT_DOCK_MODE = "dock-right";
const DOCK_STORAGE_KEY = "aw-dock-mode";

export function getDockMode() {
  try {
    const stored = localStorage.getItem(DOCK_STORAGE_KEY);
    if (stored && VALID_DOCK_MODES.includes(stored)) return stored;
  } catch (_) {}
  return DEFAULT_DOCK_MODE;
}

export function setDockMode(mode) {
  if (!VALID_DOCK_MODES.includes(mode)) return false;
  try {
    localStorage.setItem(DOCK_STORAGE_KEY, mode);
  } catch (_) {}
  return true;
}

/**
 * Applies the dock mode CSS class to the host element.
 * Ensures only one aw-dock-* class is active at a time.
 */
export function applyDock(hostElement, mode) {
  if (!hostElement) return;
  const targetMode = VALID_DOCK_MODES.includes(mode) ? mode : DEFAULT_DOCK_MODE;

  VALID_DOCK_MODES.forEach((m) => {
    hostElement.classList.remove(`aw-${m}`);
  });

  hostElement.classList.add(`aw-${targetMode}`);
  hostElement.setAttribute("data-dock-mode", targetMode);
}
