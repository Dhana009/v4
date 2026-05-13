// layout/resize-controller.js — Panel resize controller
// S7-0404: Drag-to-resize with min/max constraints and size persistence.

export const MIN_PANEL_WIDTH = 300;
export const MAX_PANEL_WIDTH_PERCENT = 80;
export const MIN_PANEL_HEIGHT = 200;
export const MAX_PANEL_HEIGHT_PERCENT = 70;
export const SIZE_STORAGE_KEY = "aw-panel-size";

export function getStoredSize() {
  try {
    const raw = localStorage.getItem(SIZE_STORAGE_KEY);
    if (raw) return JSON.parse(raw);
  } catch (_) {}
  return null;
}

export function saveSize(size) {
  try {
    localStorage.setItem(SIZE_STORAGE_KEY, JSON.stringify(size));
  } catch (_) {}
}

export function clampWidth(width) {
  const vw = typeof window !== "undefined" ? (window.innerWidth ?? 1280) : 1280;
  const maxPx = vw * (MAX_PANEL_WIDTH_PERCENT / 100);
  return Math.max(MIN_PANEL_WIDTH, Math.min(maxPx, width));
}

export function clampHeight(height) {
  const vh = typeof window !== "undefined" ? (window.innerHeight ?? 800) : 800;
  const maxPx = vh * (MAX_PANEL_HEIGHT_PERCENT / 100);
  return Math.max(MIN_PANEL_HEIGHT, Math.min(maxPx, height));
}

function debounce(fn, delay) {
  let timer;
  return function (...args) {
    clearTimeout(timer);
    timer = setTimeout(() => fn.apply(this, args), delay);
  };
}

export function createResizeController(hostElement, onResize) {
  if (!hostElement) return null;

  let active = false;
  let startX = 0;
  let startWidth = 0;

  const debouncedSave = debounce((size) => saveSize(size), 200);

  function onMouseMove(e) {
    if (!active) return;
    const dx = startX - e.clientX;
    const newWidth = clampWidth(startWidth + dx);
    hostElement.style.width = `${newWidth}px`;
    debouncedSave({ width: newWidth });
    if (onResize) onResize({ width: newWidth });
  }

  function onMouseUp() {
    active = false;
    document.removeEventListener("mousemove", onMouseMove);
    document.removeEventListener("mouseup", onMouseUp);
  }

  function onMouseDown(e) {
    active = true;
    startX = e.clientX;
    startWidth = hostElement.offsetWidth;
    document.addEventListener("mousemove", onMouseMove);
    document.addEventListener("mouseup", onMouseUp);
    e.preventDefault();
  }

  return { onMouseDown, cleanup: onMouseUp };
}

export function attachResize(handle, hostElement, onResize) {
  if (!handle || !hostElement) return () => {};
  const controller = createResizeController(hostElement, onResize);
  if (!controller) return () => {};
  handle.addEventListener("mousedown", controller.onMouseDown);
  return function detachResize() {
    handle.removeEventListener("mousedown", controller.onMouseDown);
    document.removeEventListener("mousemove", controller.onMouseDown);
    document.removeEventListener("mouseup", controller.cleanup);
  };
}
