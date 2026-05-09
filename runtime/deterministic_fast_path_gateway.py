from __future__ import annotations

from typing import Any, Awaitable, Callable

from runtime.deterministic_fast_path import build_deterministic_plan, classify_fast_path


async def attempt_deterministic_fast_path(
    loop: Any,
    steps: list[dict[str, Any]],
    *,
    get_page: Callable[[], Any],
) -> bool:
    """Run the deterministic fast-path gateway without changing execution semantics.

    This extracts only the qualification, deterministic plan construction, and
    confirmation/correction routing seam. Confirmed execution remains on AgentLoop.
    """
    if len(steps) != 1:
        print("[FAST_PATH] skip: multi-step run")
        return False

    step = steps[0]
    intent = loop._normalize_space(str(step.get("intent") or "")).strip()
    step_id = str(step.get("id") or step.get("stepId") or "").strip() or None

    locator = loop._normalize_space(str(step.get("locator") or "")).strip()
    if not locator:
        locator = loop._derive_locator_from_step_context(step)
    if not locator:
        print("[FAST_PATH] skip: no locator derivable from step")
        return False

    locator_count = 0
    locator_validated = False
    try:
        page = get_page()
        locator_count = await loop._resolve_locator(page, locator).count()
        locator_validated = locator_count == 1
    except Exception as exc:  # noqa: BLE001
        print(f"[FAST_PATH] skip: locator validation error: {exc}")
        return False

    qualifies, reason = classify_fast_path(
        user_message=intent,
        locator_validated=locator_validated,
        locator_count=locator_count,
    )
    if not qualifies:
        print(f"[FAST_PATH] skip: {reason}")
        return False

    action_verb = reason.split(":")[-1] if ":" in reason else reason
    fill_value = str(step.get("fill_value") or step.get("value") or "").strip() or None
    expected_text = str(step.get("expected_text") or step.get("expectedText") or "").strip() or None
    selected_element_info = loop._resolve_selected_element_info(step.get("element_info") or {})
    target_label = loop._best_fast_path_target_label(step, action_verb) or None
    if not expected_text and action_verb == "assert_text":
        expected_text = loop._selected_element_text(selected_element_info) or None
    if target_label and loop._should_replace_fast_path_locator_with_text(action_verb, locator):
        locator = f'get_by_text("{loop._tool_string_escape(target_label)}", exact=True)'

    plan_payload = build_deterministic_plan(
        user_message=intent,
        locator=locator,
        action_verb=action_verb,
        step_id=step_id,
        target_label=target_label,
        fill_value=fill_value,
        expected_text=expected_text,
    )
    print(f"[FAST_PATH] qualified: {reason}, locator={locator}")

    confirmation = await loop._send_plan_ready_after_confirmation(plan_payload)
    if confirmation.get("confirmed"):
        print("[FAST_PATH] confirmed; executing through confirmed execution contract")
        loop.last_plan_ready_payload = plan_payload
        await loop._execute_deterministic_fast_path_confirmed_plan()
        return True

    correction = str(confirmation.get("correction") or "").strip()
    print(f"[FAST_PATH] correction requested, falling through to LLM loop: {correction!r}")
    if correction:
        loop._append_plan_correction_message(
            correction,
            plan_id=str(confirmation.get("plan_id") or plan_payload.get("plan_id") or "").strip() or None,
            target_step_id=str(
                confirmation.get("target_step_id") or plan_payload.get("target_step_id") or step_id or ""
            ).strip()
            or None,
        )
    return False
