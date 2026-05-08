from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Sequence

from runtime.deterministic_fast_path import classify_fast_path
from runtime.tool_registry import PLANNING_SAFE_TOOL_NAMES, RECORDING_WAIT_SAFE_TOOL_NAMES


@dataclass(slots=True)
class LLMPolicyDecision:
    model_needed: bool
    purpose: str
    phase: str
    allowed_tools: tuple[str, ...]
    context_level: str
    schema_id: str | None
    budget: int
    deterministic_candidate_allowed: bool
    fallback: str
    requires_confirmation: bool


class LLMPolicyGateway:
    def __init__(self, purpose_registry: Mapping[str, dict[str, Any]] | None = None) -> None:
        self.purpose_registry = dict(purpose_registry or {})

    def decide(
        self,
        *,
        phase: str,
        steps: Sequence[Mapping[str, Any]] | None = None,
        correction_mode: Mapping[str, Any] | None = None,
        awaiting_step_record: bool = False,
        plan_confirmed: bool = False,
        locator_validated: bool | None = None,
        locator_count: int | None = None,
    ) -> LLMPolicyDecision:
        normalized_phase = str(phase or "").strip().lower() or "planning"
        step_list = list(steps or [])
        correction_state = correction_mode if isinstance(correction_mode, Mapping) else None

        if self._is_deterministic_candidate(
            normalized_phase=normalized_phase,
            step_list=step_list,
            locator_validated=locator_validated,
            locator_count=locator_count,
            correction_state=correction_state,
        ):
            return LLMPolicyDecision(
                model_needed=False,
                purpose="deterministic_fast_path",
                phase=normalized_phase,
                allowed_tools=(),
                context_level="compact",
                schema_id=None,
                budget=0,
                deterministic_candidate_allowed=True,
                fallback="main_orchestrator",
                requires_confirmation=True,
            )

        if correction_state and normalized_phase in {"planning", "awaiting_confirmation"}:
            return self._decision_from_registry("plan_diff_editor", normalized_phase)

        if normalized_phase in {"planning", "awaiting_confirmation"}:
            return self._decision_from_registry("step_plan_normalizer", normalized_phase)

        if normalized_phase in {"executing", "recording"} and plan_confirmed:
            return self._decision_from_registry("execution_driver", normalized_phase)

        if normalized_phase in {"recovery", "recovering"}:
            return self._decision_from_registry("recovery_diagnoser", normalized_phase)

        if normalized_phase == "recording" and awaiting_step_record:
            return LLMPolicyDecision(
                model_needed=True,
                purpose="main_orchestrator",
                phase=normalized_phase,
                allowed_tools=tuple(sorted(RECORDING_WAIT_SAFE_TOOL_NAMES)),
                context_level="compact",
                schema_id=None,
                budget=2400,
                deterministic_candidate_allowed=False,
                fallback="main_orchestrator",
                requires_confirmation=True,
            )

        return LLMPolicyDecision(
            model_needed=True,
            purpose="main_orchestrator",
            phase=normalized_phase,
            allowed_tools=tuple(sorted(self._default_allowed_tools(normalized_phase))),
            context_level="compact",
            schema_id=None,
            budget=2400,
            deterministic_candidate_allowed=False,
            fallback="main_orchestrator",
            requires_confirmation=True,
        )

    def _decision_from_registry(self, purpose: str, phase: str) -> LLMPolicyDecision:
        entry = self.purpose_registry.get(purpose) or {}
        context_policy = entry.get("context_policy") if isinstance(entry.get("context_policy"), Mapping) else {}
        output_schema = entry.get("output_schema") if isinstance(entry.get("output_schema"), Mapping) else {}
        tool_policy = entry.get("tool_policy") if isinstance(entry.get("tool_policy"), Mapping) else {}
        allowed_by_phase = (
            tool_policy.get("allowed_tools_by_phase")
            if isinstance(tool_policy.get("allowed_tools_by_phase"), Mapping)
            else {}
        )
        allowed_tools = allowed_by_phase.get(phase) or ()

        return LLMPolicyDecision(
            model_needed=True,
            purpose=purpose,
            phase=phase,
            allowed_tools=tuple(str(tool).strip() for tool in allowed_tools if str(tool).strip()),
            context_level=str(context_policy.get("context_level") or "compact"),
            schema_id=str(output_schema.get("schema_id") or "").strip() or None,
            budget=int(entry.get("token_budget") or 2400),
            deterministic_candidate_allowed=False,
            fallback=str(entry.get("fallback") or "fail_closed"),
            requires_confirmation=True,
        )

    def _is_deterministic_candidate(
        self,
        *,
        normalized_phase: str,
        step_list: list[Mapping[str, Any]],
        locator_validated: bool | None,
        locator_count: int | None,
        correction_state: Mapping[str, Any] | None,
    ) -> bool:
        if normalized_phase not in {"planning", "awaiting_confirmation"}:
            return False
        if correction_state:
            return False
        if len(step_list) != 1:
            return False
        if locator_validated is None or locator_count is None:
            return False

        step = step_list[0]
        intent = str(step.get("intent") or step.get("text") or "").strip()
        qualifies, _reason = classify_fast_path(
            user_message=intent,
            locator_validated=locator_validated,
            locator_count=locator_count,
        )
        return qualifies

    def _default_allowed_tools(self, phase: str) -> set[str]:
        if phase in {"planning", "awaiting_confirmation"}:
            return set(PLANNING_SAFE_TOOL_NAMES)
        if phase == "recording":
            return set(RECORDING_WAIT_SAFE_TOOL_NAMES)
        return set()
