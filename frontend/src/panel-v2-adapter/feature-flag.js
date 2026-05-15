export function shouldUseV2Panel() {
  try {
    const params = new URLSearchParams(window.location.search);
    if (params.has("panel")) {
      return params.get("panel") === "v2";
    }
    return localStorage.getItem("awPanelVersion") === "v2";
  } catch {
    return false;
  }
}
