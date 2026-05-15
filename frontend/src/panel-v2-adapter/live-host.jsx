import { useMemo } from "react";
import { App } from "../panel-v2/app.jsx";
import { mapTransportToViewModel } from "./state-bridge.js";

export function PanelV2LiveHost({ transport, storeState, onSendCommand }) {
  const vm = useMemo(
    () => mapTransportToViewModel(transport ?? {}, storeState ?? null),
    [transport, storeState]
  );

  const onCommand = useMemo(() => {
    if (!onSendCommand) return undefined;
    return (action, payload) => onSendCommand(action, payload);
  }, [onSendCommand]);

  return <App viewModel={vm} mode="live" onCommand={onCommand} />;
}
