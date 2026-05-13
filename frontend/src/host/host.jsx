// host/host.jsx — Shadow DOM host lifecycle module
// S7-0401: Idempotent mount/unmount, full cleanup contract.

export const SHADOW_HOST_ID = "aw-shadow-host";
export const SHADOW_MOUNT_ID = "aw-shadow-mount";
const CONTAINER_ID = "autoworkbench-root";

// Attribute applied to all AutoWorkbench DOM nodes for picker exclusion (S7-0408)
const HOST_ATTR = "data-autoworkbench";

/**
 * Returns the root container element (#autoworkbench-root) if it exists in the page.
 */
export function getHostContainer() {
  if (typeof document === "undefined") return null;
  return document.getElementById(CONTAINER_ID) ?? null;
}

/**
 * Returns the open ShadowRoot for the given container, or null if not mounted.
 */
export function getHostRoot(container) {
  const el = container ?? getHostContainer();
  if (!el) return null;
  return el.shadowRoot ?? null;
}

/**
 * Attaches Shadow DOM to container (idempotent) and ensures the host marker div exists.
 * Returns { shadowRoot, hostElement } or null if container is not a valid element.
 */
export function createHost(container) {
  if (!container || typeof container.attachShadow !== "function") return null;

  const shadowRoot = container.shadowRoot ?? container.attachShadow({ mode: "open" });

  let hostEl = shadowRoot.querySelector(`#${SHADOW_HOST_ID}`);
  if (!hostEl) {
    hostEl = document.createElement("div");
    hostEl.id = SHADOW_HOST_ID;
    hostEl.setAttribute("data-testid", "aw-shadow-host");
    hostEl.setAttribute(HOST_ATTR, "true");
    shadowRoot.appendChild(hostEl);
  }

  return { shadowRoot, hostElement: hostEl };
}

/**
 * Mounts the AutoWorkbench host into the page. Creates container if missing.
 * Idempotent — calling multiple times is safe.
 * Returns { shadowRoot, mount, container } or null on failure.
 */
export function mountHost() {
  if (typeof document === "undefined") return null;

  let container = document.getElementById(CONTAINER_ID);
  if (!container) {
    container = document.createElement("div");
    container.id = CONTAINER_ID;
    container.setAttribute(HOST_ATTR, "true");
    container.setAttribute("data-testid", "aw-host-container");
    (document.body ?? document.documentElement).appendChild(container);
  }

  const result = createHost(container);
  if (!result) return null;

  const { shadowRoot } = result;

  let mount = shadowRoot.querySelector(`#${SHADOW_MOUNT_ID}`);
  if (!mount) {
    mount = document.createElement("div");
    mount.id = SHADOW_MOUNT_ID;
    mount.setAttribute("data-testid", "aw-shadow-mount");
    mount.setAttribute(HOST_ATTR, "true");
    shadowRoot.appendChild(mount);
  }

  return { shadowRoot, mount, container };
}

/**
 * Unmounts and removes all AutoWorkbench DOM nodes from the page.
 * Clears Shadow DOM and removes the root container.
 * Idempotent — safe to call when not mounted.
 */
export function unmountHost() {
  if (typeof document === "undefined") return;

  const container = document.getElementById(CONTAINER_ID);
  if (!container) return;

  const shadowRoot = container.shadowRoot;
  if (shadowRoot) {
    while (shadowRoot.firstChild) {
      shadowRoot.removeChild(shadowRoot.firstChild);
    }
  }

  if (container.parentNode) {
    container.parentNode.removeChild(container);
  }
}
