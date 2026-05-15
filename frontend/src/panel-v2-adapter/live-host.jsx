import { useMemo } from "react";
import { App } from "../panel-v2/app.jsx";
import { mapTransportToViewModel } from "./state-bridge.js";
import { buildPanelV2Command } from "./command-bridge.js";

export function PanelV2LiveHost({ transport, storeState, onSendCommand }) {
  const vm = useMemo(
    () => mapTransportToViewModel(transport ?? {}, storeState ?? null),
    [transport, storeState]
  );

  const onCommand = useMemo(() => {
    if (!onSendCommand) return undefined;
    return (action, payload) => {
      const runId = payload?.run_id ?? vm.runtime?.runId ?? null;
      const result = buildPanelV2Command(action, payload, runId);
      if (result.supported && result.command) {
        onSendCommand(result.command);
      }
    };
  }, [onSendCommand, vm]);

  return <App viewModel={vm} mode="live" onCommand={onCommand} />;
}
