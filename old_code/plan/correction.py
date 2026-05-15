from __future__ import annotations
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any
if TYPE_CHECKING:
    from agent import AgentLoop


class PlanCorrection:
    def __init__(self, loop: "AgentLoop") -> None:
        self._loop = loop

    def classify_plan_correction(self, message: Any) -> Any:
        return self._loop._classify_plan_correction(message)

    def build_plan_correction_validation_feedback(self, result: Any) -> Any:
        return self._loop._build_plan_correction_validation_feedback(result)

    def build_plan_correction_operation_context_lines(self, step: Any) -> Any:
        return self._loop._build_plan_correction_operation_context_lines(step)

    def build_plan_correction_context_message(self, correction_text: Any = None) -> Any:
        return self._loop._build_plan_correction_context_message(correction_text)

    def build_plan_diff_editor_schema_message(self) -> Any:
        return self._loop._build_plan_diff_editor_schema_message()

    def synthesize_plan_diff_editor_output(self, raw: Any) -> Any:
        return self._loop._synthesize_plan_diff_editor_output(raw)

    def build_plan_correction_clarification_message(self, reason: Any) -> Any:
        return self._loop._build_plan_correction_clarification_message(reason)

    def build_plan_correction_state(self, correction_text: Any) -> Any:
        return self._loop._build_plan_correction_state(correction_text)

    def build_plan_correction_added_child(self, op: Any) -> Any:
        return self._loop._build_plan_correction_added_child(op)

    def build_structured_plan_correction_payload_from_diff(self, diff: Any) -> Any:
        return self._loop._build_structured_plan_correction_payload_from_diff(diff)

    def patch_value(self, original: Any, patch: Any) -> Any:
        return self._loop._patch_value(original, patch)

    def normalize_step_patch(self, patch: Any) -> Any:
        return self._loop._normalize_step_patch(patch)

    def validate_structured_plan_step(self, step: Any) -> Any:
        return self._loop._validate_structured_plan_step(step)

    def validate_structured_plan_correction(self, correction: Any) -> Any:
        return self._loop._validate_structured_plan_correction(correction)

    def remember_plan_review_context(self, payload: Any) -> None:
        return self._loop._remember_plan_review_context(payload)

    def build_plan_step_context_lines(self, step: Any) -> Any:
        return self._loop._build_plan_step_context_lines(step)

    def build_plan_correction_message(self, correction_text: Any) -> Any:
        return self._loop._build_plan_correction_message(correction_text)

    def append_plan_correction_message(self, correction_text: Any) -> None:
        return self._loop._append_plan_correction_message(correction_text)

    def select_plan_correction_child_target(self, candidates: Any) -> str:
        return self._loop._select_plan_correction_child_target(candidates)

    def build_plan_correction_child_description(self, op_type: Any, target: Any) -> str:
        return self._loop._build_plan_correction_child_description(op_type, target)

    def clear_plan_review_context(self) -> None:
        return self._loop._clear_plan_review_context()

    def clear_active_plan_correction_state(self) -> None:
        return self._loop._clear_active_plan_correction_state()

    async def call_plan_diff_editor_controller(self, **kwargs: Any) -> Any:
        return await self._loop._call_plan_diff_editor_controller(**kwargs)

    async def run_plan_diff_editor_correction(self, **kwargs: Any) -> Any:
        return await self._loop._run_plan_diff_editor_correction(**kwargs)

    def sanitize_capability_gap_detail(self, value: Any) -> Any:
        if value is None or isinstance(value, (bool, int, float)):
            return value

        if isinstance(value, str):
            text = self._loop._normalize_space(value).strip()
            if len(text) > 160:
                text = f"{text[:157]}..."
            return text

        if isinstance(value, dict):
            sanitized: dict[str, Any] = {}
            for key, nested_value in value.items():
                key_text = self._loop._normalize_space(str(key or "")).strip()
                if not key_text:
                    continue
                lowered_key = key_text.lower()
                if lowered_key in {
                    "dom",
                    "html",
                    "markup",
                    "prompt",
                    "tool_args",
                    "arguments",
                    "raw_dom",
                    "raw_prompt",
                    "raw_tool_args",
                }:
                    continue
                sanitized_value = self._loop._sanitize_capability_gap_detail(nested_value)
                if sanitized_value in (None, "", [], {}):
                    continue
                sanitized[key_text] = sanitized_value
            return sanitized

        if isinstance(value, (list, tuple, set)):
            sanitized_items: list[Any] = []
            for item in value:
                sanitized_item = self._loop._sanitize_capability_gap_detail(item)
                if sanitized_item in (None, "", [], {}):
                    continue
                sanitized_items.append(sanitized_item)
                if len(sanitized_items) >= 5:
                    break
            return sanitized_items

        text = self._loop._normalize_space(str(value)).strip()
        if len(text) > 160:
            text = f"{text[:157]}..."
        return text

    def record_capability_gap(
    self,
    category: str,
    source: str,
    severity: str,
    message: str,
    **details: Any,
    ) -> dict[str, Any]:
        capability_gaps = getattr(self, "capability_gaps", None)
        if not isinstance(capability_gaps, list):
            capability_gaps = []
            self.capability_gaps = capability_gaps

        category_text = self._loop._normalize_space(str(category or "")).strip() or "unknown"
        source_text = self._loop._normalize_space(str(source or "")).strip() or "unknown"
        severity_text = self._loop._normalize_space(str(severity or "")).strip().lower()
        if severity_text not in {"warn", "error"}:
            severity_text = "warn"
        message_text = self._loop._normalize_space(str(message or "")).strip() or "unspecified capability gap"
        phase_text = self._loop._current_phase()
        step_id = str(getattr(self, "active_step_id", "") or "").strip() or None

        safe_details: dict[str, Any] = {}
        for key, value in details.items():
            key_text = self._loop._normalize_space(str(key or "")).strip()
            if not key_text:
                continue
            safe_value = self._loop._sanitize_capability_gap_detail(value)
            if safe_value in (None, "", [], {}):
                continue
            safe_details[key_text] = safe_value

        record = {
            "ordinal": len(capability_gaps) + 1,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "category": category_text,
            "source": source_text,
            "severity": severity_text,
            "message": message_text,
            "phase": phase_text,
            "step_id": step_id,
            "details": safe_details,
        }
        capability_gaps.append(record)

        log_line = (
            "[CAPABILITY_GAP] "
            f"ordinal={record['ordinal']} "
            f"category={category_text} "
            f"source={source_text} "
            f"severity={severity_text} "
            f"message={json.dumps(message_text, ensure_ascii=True)}"
        )
        if phase_text:
            log_line += f" phase={phase_text}"
        if step_id:
            log_line += f" step_id={step_id}"
        if safe_details:
            log_line += f" details={json.dumps(safe_details, ensure_ascii=True, separators=(',', ':'))}"
        print(log_line)

        return record

    def validate_plan_diff_editor_output(self, **payload: Any) -> dict[str, Any]:
        raw_output = payload.get("raw_output") or payload.get("output") or payload.get("response")
        if isinstance(raw_output, str):
            try:
                parsed_output = json.loads(raw_output)
            except json.JSONDecodeError:
                return {
                    "ok": False,
                    "validation_status": "invalid",
                    "errors": ["invalid_json"],
                    "parsed_output": None,
                }
        elif isinstance(raw_output, dict):
            parsed_output = dict(raw_output)
        elif hasattr(raw_output, "__dict__"):
            parsed_output = dict(vars(raw_output))
        else:
            return {
                "ok": False,
                "validation_status": "invalid",
                "errors": ["unsupported_output"],
                "parsed_output": None,
            }

        if not isinstance(parsed_output, dict):
            return {
                "ok": False,
                "validation_status": "invalid",
                "errors": ["invalid_output"],
                "parsed_output": None,
            }

        errors: list[str] = []
        required_text_fields = (
            "schema_id",
            "purpose",
            "correction_intent",
            "target_plan_id",
        )
        for field_name in required_text_fields:
            if str(parsed_output.get(field_name) or "").strip() == "":
                errors.append(field_name)

        target_plan_version = parsed_output.get("target_plan_version")
        if not isinstance(target_plan_version, int):
            errors.append("target_plan_version")

        if str(parsed_output.get("schema_id") or "").strip() != "plan_diff_editor.v1":
            errors.append("schema_id")
        if str(parsed_output.get("purpose") or "").strip() != "plan_diff_editor":
            errors.append("purpose")
        if not isinstance(parsed_output.get("operations"), list) or not parsed_output.get("operations"):
            errors.append("operations")
        if not isinstance(parsed_output.get("requires_user_clarification"), bool) or parsed_output.get("requires_user_clarification") is not False:
            errors.append("requires_user_clarification")

        if errors:
            return {
                "ok": False,
                "validation_status": "invalid",
                "errors": errors,
                "parsed_output": None,
            }

        return {
            "ok": True,
            "validation_status": "valid",
            "errors": [],
            "parsed_output": parsed_output,
        }
