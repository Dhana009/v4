// layout/panel-modes.js — Panel mode controller
// S7-0403: collapsed/expanded/floating modes. floating does NOT apply page compensation.

export const PANEL_MODES = {
  collapsed: "collapsed",
  expanded: "expanded",
  floating: "floating",
};

export const DEFAULT_PANEL_MODE = PANEL_MODES.expanded;

// Mode metadata: floating has noCompensation = true (no page style changes)
const MODE_META = {
  collapsed: { noCompensation: false, label: "Collapsed" },
  expanded:  { noCompensation: false, label: "Expanded" },
  floating:  { noCompensation: true,  label: "Floating" },
};

export function getModeMetadata(mode) {
  return MODE_META[mode] ?? MODE_META[PANEL_MODES.expanded];
}

const MODES_STORAGE_KEY = "aw-panel-mode";

export function getPanelMode() {
  try {
    const stored = localStorage.getItem(MODES_STORAGE_KEY);
    if (stored && Object.values(PANEL_MODES).includes(stored)) return stored;
  } catch (_) {}
  return DEFAULT_PANEL_MODE;
}

export function setPanelMode(mode) {
  if (!Object.values(PANEL_MODES).includes(mode)) return false;
  try {
    localStorage.setItem(MODES_STORAGE_KEY, mode);
  } catch (_) {}
  return true;
}

/**
 * Applies the panel mode CSS class to the host element.
 * Ensures only one aw-panel-* class is active at a time.
 */
export function applyMode(hostElement, mode) {
  if (!hostElement) return;
  const targetMode = Object.values(PANEL_MODES).includes(mode) ? mode : DEFAULT_PANEL_MODE;

  Object.values(PANEL_MODES).forEach((m) => {
    hostElement.classList.remove(`aw-panel-${m}`);
  });

  hostElement.classList.add(`aw-panel-${targetMode}`);
  hostElement.setAttribute("data-panel-mode", targetMode);
}
