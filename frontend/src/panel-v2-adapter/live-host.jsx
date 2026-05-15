import { useMemo } from "react";
import { App } from "../panel-v2/app.jsx";
import { mapTransportToViewModel } from "./state-bridge.js";

export function PanelV2LiveHost({ transport }) {
  // Compute live view model — wiring to App props is a follow-on task
  // eslint-disable-next-line no-unused-vars
  const _vm = useMemo(
    () => mapTransportToViewModel(transport ?? {}, null),
    [transport]
  );

  return <App />;
}
