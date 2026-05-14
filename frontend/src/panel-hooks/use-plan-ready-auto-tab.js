import { useEffect, useRef } from "react";

/**
 * Sprint 7 routing fix.
 *
 * When the backend dispatches `plan_ready`, the store transitions to
 * `phase === "awaiting_confirmation"` and populates `plan`. The
 * Confirm-Plan card (`CardPlanReady`) only renders inside the LLM tab,
 * so we auto-switch there so the reviewer sees the plan without
 * manual navigation.
 *
 * Fires once per null→non-null transition of `plan`, regardless of which
 * tab is currently active. It is a no-op if the user is already on the
 * LLM tab. It does NOT fire on later events (`step_recorded`,
 * `code_update`, `trace_event`, etc.), only on the plan-ready edge.
 *
 * @param {object} args
 * @param {object|null} args.plan - storeState.plan (null when no plan)
 * @param {string|null} args.phase - storeState.phase
 * @param {string} args.currentTab - currently active tab name
 * @param {(next: string) => void} args.setTab - setter for active tab
 */
export function usePlanReadyAutoTab({ plan, phase, currentTab, setTab }) {
  const lastSeenPlanRef = useRef(null);
  useEffect(() => {
    const previous = lastSeenPlanRef.current;
    lastSeenPlanRef.current = plan;
    if (!plan) return;
    if (previous) return; // already had a plan; don't re-route on updates
    if (phase !== "awaiting_confirmation") return;
    if (currentTab === "llm") return;
    setTab("llm");
  }, [plan, phase, currentTab, setTab]);
}
