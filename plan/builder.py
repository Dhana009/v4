from __future__ import annotations
from typing import TYPE_CHECKING, Any
if TYPE_CHECKING:
    from agent import AgentLoop


class PlanBuilder:
    def __init__(self, loop: "AgentLoop") -> None:
        self._loop = loop

    def normalize_steps(self, steps: Any) -> Any:
        return self._loop._normalize_steps(steps)

    def format_steps(self, steps: Any) -> Any:
        return self._loop._format_steps(steps)

    def validate_recording_steps(self, steps: Any) -> Any:
        return self._loop._validate_recording_steps(steps)

    def infer_operation_type(self, intent: Any) -> str:
        return self._loop._infer_operation_type(intent)

    def infer_planned_operation_sequence(self, intent: Any) -> list[str]:
        return self._loop._infer_planned_operation_sequence(intent)

    def build_planned_child_description(self, operation_type: Any, target: Any, intent: Any) -> str:
        return self._loop._build_planned_child_description(operation_type, target, intent)

    def build_planned_children(self, step: Any) -> list[dict[str, Any]]:
        return self._loop._build_planned_children(step)

    def build_plan_ready_parent_step(self, step: Any) -> dict[str, Any]:
        return self._loop._build_plan_ready_parent_step(step)

    def build_recorded_child_description(self, child: Any) -> str:
        return self._loop._build_recorded_child_description(child)

    def is_technical_recorded_label_text(self, value: Any) -> bool:
        return self._loop._is_technical_recorded_label_text(value)

    def build_recorded_children(self, step: Any) -> list[dict[str, Any]]:
        return self._loop._build_recorded_children(step)

    def build_plan_ready_payload(self, steps: Any) -> dict[str, Any]:
        return self._loop._build_plan_ready_payload(steps)

    def is_outcome_like_label(self, value: Any) -> bool:
        normalized_value = self._loop._normalize_space(str(value or "")).strip().lower()
        if not normalized_value:
            return False

        compact_value = re.sub(r"[\s-]+", "_", normalized_value)
        if compact_value in EXPECTED_OUTCOME_TYPES:
            return True

        if compact_value.startswith("expected_outcome"):
            return True

        if normalized_value == "expected outcome":
            return True

        if normalized_value == "picker" or normalized_value.startswith("picker:") or normalized_value.startswith("picker -"):
            return True

        for outcome_label in EXPECTED_OUTCOME_TYPES:
            for separator in (" ·", ":", " -", " —"):
                if normalized_value.startswith(f"{outcome_label}{separator}"):
                    return True

        return False

    def extract_assertion_expected_value(self, value: Any) -> str:
        candidate_text = self._loop._normalize_space(str(value or "")).strip()
        if not candidate_text or self._loop._is_outcome_like_label(candidate_text):
            return ""

        quoted_match = re.search(r'["“”`](.+?)["“”`]', candidate_text)
        if quoted_match:
            quoted_text = self._loop._normalize_space(quoted_match.group(1)).strip()
            if quoted_text and not self._loop._is_outcome_like_label(quoted_text):
                return quoted_text

        lowered_text = candidate_text.lower()
        markers = (
            "exact text equal to",
            "exact text equals",
            "text equal to",
            "text equals",
            "exactly match",
            "exactly matches",
            "match exactly",
            "equal to",
            "equals",
            "contains text",
            "has text",
            "includes text",
            "includes",
            "include",
        )
        for marker in markers:
            marker_index = lowered_text.find(marker)
            if marker_index < 0:
                continue
            extracted_text = self._loop._normalize_space(
                candidate_text[marker_index + len(marker) :]
            ).strip(" :,-–—")
            if extracted_text and not self._loop._is_outcome_like_label(extracted_text):
                return extracted_text

        return ""

    def canonicalize_assertion_operation(
    self,
    operation_spec: dict[str, Any],
    source_step: dict[str, Any] | None = None,
    anchor_child: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        operation_data = operation_spec if isinstance(operation_spec, dict) else {}
        source_step_data = source_step if isinstance(source_step, dict) else {}
        anchor_child_data = anchor_child if isinstance(anchor_child, dict) else {}

        operation_type = self._loop._normalize_space(
            str(operation_data.get("type") or operation_data.get("action") or "")
        ).strip().lower()
        if operation_type != "assert":
            return {}

        source_element_info = self._loop._resolve_selected_element_info(
            source_step_data.get("element_info") if isinstance(source_step_data.get("element_info"), dict) else {}
        )
        source_element_text = self._loop._selected_element_text(source_element_info)

        hint_text_parts = [
            str(operation_data.get("description") or "").strip(),
            str(operation_data.get("text") or "").strip(),
            str(operation_data.get("target") or "").strip(),
            str(operation_data.get("value") or operation_data.get("expected_value") or operation_data.get("expected_text") or "").strip(),
            str(anchor_child_data.get("description") or "").strip(),
            str(anchor_child_data.get("target") or "").strip(),
            str(source_step_data.get("intent") or "").strip(),
            str(source_step_data.get("element_name") or "").strip(),
            source_element_text,
        ]
        hint_text = self._loop._normalize_space(" ".join(part for part in hint_text_parts if part)).strip().lower()

        explicit_assertion = self._loop._normalize_space(
            str(operation_data.get("assertion") or anchor_child_data.get("assertion") or "")
        ).strip().lower()
        assertion_aliases = {
            "exact_text": "has_text",
            "text_equal": "has_text",
            "text_equals": "has_text",
            "contains_text": "has_text",
            "includes_text": "has_text",
        }
        assertion = assertion_aliases.get(explicit_assertion, explicit_assertion)

        exact_text_mode = any(
            marker in hint_text
            for marker in (
                "exact text equal to",
                "exact text equals",
                "text equal to",
                "text equals",
                "exactly match",
                "exactly matches",
                "match exactly",
                "equal to",
                "equals",
            )
        )
        contains_text_mode = any(
            marker in hint_text
            for marker in (
                "contains text",
                "has text",
                "includes text",
                "includes",
                "include",
            )
        )
        visible_mode = any(
            marker in hint_text
            for marker in (
                " visible",
                "visible",
                "present",
                "on screen",
                "displayed",
            )
        )
        if exact_text_mode or contains_text_mode:
            assertion = "has_text"
        elif not assertion:
            if visible_mode:
                assertion = "visible"
            elif self._loop._normalize_space(str(operation_data.get("value") or operation_data.get("expected_value") or "")).strip():
                assertion = "has_text"
            else:
                assertion = "visible"

        if assertion not in {"visible", "hidden", "enabled", "disabled", "checked", "has_text", "has_value"}:
            assertion = "has_text" if exact_text_mode or contains_text_mode else "visible"

        expected_value = ""
        direct_value_candidates = [
            operation_data.get("expected_value"),
            operation_data.get("expected_text"),
            operation_data.get("value"),
            operation_data.get("text"),
            anchor_child_data.get("expected_value"),
            anchor_child_data.get("expected_text"),
            anchor_child_data.get("value"),
            anchor_child_data.get("text"),
        ]
        for candidate in direct_value_candidates:
            candidate_text = self._loop._normalize_space(str(candidate or "")).strip()
            if candidate_text and not self._loop._is_outcome_like_label(candidate_text):
                expected_value = candidate_text
                break

        if not expected_value:
            parsed_value_candidates = [
                operation_data.get("description"),
                operation_data.get("target"),
                operation_data.get("element_name"),
                operation_data.get("intent"),
                anchor_child_data.get("description"),
                anchor_child_data.get("target"),
                source_step_data.get("intent"),
                source_step_data.get("element_name"),
                source_element_text,
            ]
            for candidate in parsed_value_candidates:
                parsed_value = self._loop._extract_assertion_expected_value(candidate)
                if parsed_value:
                    expected_value = parsed_value
                    break

        if not expected_value and (exact_text_mode or contains_text_mode or assertion == "has_text"):
            for candidate in (
                operation_data.get("target"),
                operation_data.get("element_name"),
                anchor_child_data.get("target"),
                anchor_child_data.get("element_name"),
                source_step_data.get("element_name"),
                source_element_text,
            ):
                candidate_text = self._loop._normalize_space(str(candidate or "")).strip()
                if candidate_text and not self._loop._is_outcome_like_label(candidate_text):
                    expected_value = candidate_text
                    break

        locator = self._loop._normalize_space(
            str(
                operation_data.get("locator")
                or anchor_child_data.get("locator")
                or source_step_data.get("locator")
                or self._loop._derive_locator_from_step_context(source_step_data)
                or ""
            )
        ).strip()
        if locator in {"*", 'page.locator("")'}:
            locator = ""
        target = self._loop._select_plan_correction_child_target(
            [
                ("operation.target", operation_data.get("target")),
                ("operation.element_name", operation_data.get("element_name")),
                ("anchor.target", anchor_child_data.get("target")),
                ("anchor.description", anchor_child_data.get("description")),
                ("source.element_name", source_step_data.get("element_name")),
                ("source.intent", source_step_data.get("intent")),
            ]
        )
        target_text = self._loop._normalize_space(str(target or "")).strip()
        source_intent_text = self._loop._normalize_space(str(source_step_data.get("intent") or "")).strip()
        operation_description_text = self._loop._normalize_space(
            str(operation_data.get("description") or anchor_child_data.get("description") or "")
        ).strip()
        if assertion == "has_text" and expected_value:
            if (
                not target_text
                or self._loop._is_outcome_like_label(target_text)
                or target_text == source_intent_text
                or target_text == operation_description_text
                or expected_value in target_text
                or target_text in expected_value
            ):
                target = expected_value

        visible_target_text = target_text
        if assertion == "visible" and expected_value:
            if (
                not visible_target_text
                or self._loop._is_outcome_like_label(visible_target_text)
                or visible_target_text.lower() in {"main", "page", "body", "document"}
                or expected_value in visible_target_text
                or visible_target_text in expected_value
                or "heading" in visible_target_text.lower()
            ):
                visible_target_text = expected_value

        if assertion in {"visible", "has_text"} and source_element_text:
            if (
                not visible_target_text
                or self._loop._is_outcome_like_label(visible_target_text)
                or visible_target_text.lower() in {"main", "page", "body", "document"}
                or "heading" in visible_target_text.lower()
            ):
                visible_target_text = source_element_text

        locator_label_text = self._loop._locator_label_hint(locator)
        source_locator = self._loop._normalize_space(str(source_step_data.get("locator") or "")).strip()
        source_locator_label = self._loop._locator_label_hint(source_locator)
        preferred_visible_label = locator_label_text
        if source_locator_label:
            if not preferred_visible_label:
                preferred_visible_label = source_locator_label
            elif source_locator_label in preferred_visible_label and len(source_locator_label) < len(preferred_visible_label):
                preferred_visible_label = source_locator_label

        if assertion == "visible" and preferred_visible_label:
            if (
                not visible_target_text
                or self._loop._is_outcome_like_label(visible_target_text)
                or visible_target_text.lower() in {"main", "page", "body", "document"}
                or "heading" in visible_target_text.lower()
                or preferred_visible_label in visible_target_text
            ):
                visible_target_text = preferred_visible_label

        if (
            assertion == "visible"
            and source_locator
            and source_locator_label
            and preferred_visible_label == source_locator_label
            and source_locator != locator
            and source_locator_label in visible_target_text
        ):
            locator = source_locator

        if assertion == "visible":
            if visible_target_text:
                target = visible_target_text
                target_text = visible_target_text
            locator_value_text = expected_value or target_text or source_element_text
            normalized_locator = self._loop._normalize_space(locator).strip().lower()
            if locator_value_text and normalized_locator in {"main", 'page.locator("main")', "page.locator('main')"}:
                locator = f'get_by_text("{self._loop._tool_string_escape(locator_value_text)}", exact=True)'

        if not locator and assertion == "has_text" and expected_value:
            locator = f'get_by_text("{self._loop._tool_string_escape(expected_value)}", exact=True)'

        description = self._loop._build_plan_correction_child_description(
            "assert",
            target,
            assertion,
            expected_value,
            str(operation_data.get("description") or anchor_child_data.get("description") or "").strip(),
            str(source_step_data.get("intent") or target or "").strip(),
        )

        normalized_child: dict[str, Any] = {
            "assertion": assertion,
            "target": target,
            "locator": locator,
            "description": description,
        }
        if expected_value:
            normalized_child["value"] = expected_value
            normalized_child["expected_value"] = expected_value
        return normalized_child

    def normalize_expected_outcome(
    self,
    expected_outcome: Any,
    required: bool = False,
    ) -> dict[str, Any] | None:
        if not isinstance(expected_outcome, dict):
            return None

        type_text = self._loop._normalize_space(str(expected_outcome.get("type") or "")).lower()
        type_text = re.sub(r"[\s-]+", "_", type_text)
        if not type_text or type_text not in EXPECTED_OUTCOME_TYPES:
            return None

        description_text = self._loop._normalize_space(str(expected_outcome.get("description") or "")).strip()
        normalized_outcome: dict[str, Any] = {
            "type": type_text,
            "source": "user",
            "required": bool(required or expected_outcome.get("required") is True),
        }
        if description_text:
            normalized_outcome["description"] = description_text
        return normalized_outcome

    def expected_outcome_summary(self, expected_outcome: Any) -> str:
        if not isinstance(expected_outcome, dict):
            return ""

        type_text = self._loop._normalize_space(str(expected_outcome.get("type") or "")).lower()
        type_text = re.sub(r"[\s-]+", "_", type_text)
        if not type_text or type_text not in EXPECTED_OUTCOME_TYPES:
            return ""

        description_text = self._loop._normalize_space(str(expected_outcome.get("description") or "")).strip()
        summary = f"{type_text} · {description_text}" if description_text else type_text
        if len(summary) > 80:
            return f"{summary[:79]}..."
        return summary

    def resolve_selected_element_info(self, element_info: dict[str, Any]) -> dict[str, Any]:
        if not isinstance(element_info, dict):
            return {}

        candidates = element_info.get("candidates")
        if not isinstance(candidates, list) or not candidates:
            return element_info

        selected_candidate_index = element_info.get("selected_candidate_index")
        selected_index: int | None = None
        if isinstance(selected_candidate_index, int):
            selected_index = selected_candidate_index
        else:
            try:
                selected_index = int(str(selected_candidate_index or "").strip())
            except (TypeError, ValueError):
                selected_index = None
        if selected_index is None or selected_index < 0 or selected_index >= len(candidates):
            selected_index = 0

        selected_candidate = candidates[selected_index]
        if not isinstance(selected_candidate, dict):
            return element_info

        selected_attributes = selected_candidate.get("attributes") if isinstance(selected_candidate.get("attributes"), dict) else {}
        merged = dict(element_info)
        merged["selected_candidate_index"] = selected_index
        merged["candidates"] = deepcopy(candidates)
        merged["tag"] = self._loop._normalize_space(str(selected_candidate.get("tag") or merged.get("tag") or "")).strip().lower()
        merged["id"] = self._loop._normalize_space(
            str(selected_candidate.get("id") or merged.get("id") or selected_attributes.get("id") or "")
        ).strip()
        merged["class"] = self._loop._normalize_space(
            str(
                selected_candidate.get("className")
                or selected_candidate.get("class")
                or merged.get("className")
                or merged.get("class")
                or selected_attributes.get("className")
                or selected_attributes.get("class")
                or ""
            )
        ).strip()
        merged["className"] = merged["class"]

        selected_text = self._loop._normalize_space(
            str(
                selected_candidate.get("cleanText")
                or selected_candidate.get("clean_text")
                or selected_candidate.get("text")
                or merged.get("clean_text")
                or merged.get("cleanText")
                or merged.get("text")
                or ""
            )
        ).strip()
        merged["text"] = selected_text
        merged["clean_text"] = selected_text
        merged["cleanText"] = selected_text

        role_value = self._loop._normalize_space(
            str(selected_candidate.get("role") or merged.get("role") or selected_attributes.get("role") or "")
        ).strip()
        if role_value:
            merged["role"] = role_value

        aria_label_value = self._loop._normalize_space(
            str(
                selected_candidate.get("ariaLabel")
                or selected_candidate.get("aria_label")
                or merged.get("ariaLabel")
                or merged.get("aria_label")
                or selected_attributes.get("aria-label")
                or ""
            )
        ).strip()
        if aria_label_value:
            merged["ariaLabel"] = aria_label_value
            merged["aria_label"] = aria_label_value

        semantic_value = self._loop._normalize_space(
            str(
                selected_candidate.get("semanticType")
                or selected_candidate.get("semantic_type")
                or selected_candidate.get("category")
                or merged.get("semantic_type")
                or merged.get("semanticType")
                or ""
            )
        ).strip()
        if semantic_value:
            merged["semantic_type"] = semantic_value
            merged["semanticType"] = semantic_value

        selector_value = self._loop._normalize_space(
            str(
                selected_candidate.get("selectorHint")
                or selected_candidate.get("selector_hint")
                or merged.get("selector_hint")
                or merged.get("selectorHint")
                or ""
            )
        ).strip()
        if selector_value:
            merged["selector_hint"] = selector_value
            merged["selectorHint"] = selector_value

        locator_value = self._loop._normalize_space(
            str(
                selected_candidate.get("locatorHint")
                or selected_candidate.get("locator_hint")
                or merged.get("locator_hint")
                or merged.get("locatorHint")
                or ""
            )
        ).strip()
        if locator_value:
            merged["locator_hint"] = locator_value
            merged["locatorHint"] = locator_value

        merged["attributes"] = deepcopy(
            selected_attributes or (merged.get("attributes") if isinstance(merged.get("attributes"), dict) else {})
        )
        return merged

    def selected_element_text(self, element_info: dict[str, Any]) -> str:
        selected_element_info = self._loop._resolve_selected_element_info(element_info)
        attributes = selected_element_info.get("attributes") if isinstance(selected_element_info.get("attributes"), dict) else {}
        candidates = [
            selected_element_info.get("clean_text"),
            selected_element_info.get("cleanText"),
            selected_element_info.get("text"),
            attributes.get("aria-label"),
            selected_element_info.get("ariaLabel"),
            selected_element_info.get("aria_label"),
            attributes.get("placeholder"),
            attributes.get("data-testid"),
            selected_element_info.get("id"),
        ]
        for candidate in candidates:
            candidate_text = self._loop._normalize_space(str(candidate or "")).strip()
            if candidate_text:
                return candidate_text
        return ""

    def element_candidate_display_text(self, element_info: dict[str, Any]) -> str:
        if not isinstance(element_info, dict):
            return ""
        attributes = element_info.get("attributes") if isinstance(element_info.get("attributes"), dict) else {}
        candidates = [
            element_info.get("clean_text"),
            element_info.get("cleanText"),
            element_info.get("text"),
            attributes.get("aria-label"),
            element_info.get("ariaLabel"),
            element_info.get("aria_label"),
            attributes.get("placeholder"),
            attributes.get("data-testid"),
            element_info.get("id"),
        ]
        for candidate in candidates:
            candidate_text = self._loop._normalize_space(str(candidate or "")).strip()
            if candidate_text:
                return candidate_text
        return ""

    def best_fast_path_target_label(self, step: dict[str, Any], action_verb: str) -> str:
        step_data = step if isinstance(step, dict) else {}
        max_label_length = 80
        preferred_roles = {"heading", "link", "button", "textbox", "text"}
        explicit_name = self._loop._normalize_space(str(step_data.get("element_name") or "")).strip()
        if explicit_name and len(explicit_name) <= max_label_length and explicit_name.lower() not in {"main", "page", "body", "document"}:
            return explicit_name

        element_info = step_data.get("element_info") if isinstance(step_data.get("element_info"), dict) else {}
        raw_candidates = element_info.get("candidates") if isinstance(element_info.get("candidates"), list) else []
        fallback_label = ""
        for raw_candidate in raw_candidates:
            if not isinstance(raw_candidate, dict):
                continue
            candidate_text = self._loop._normalize_space(self._loop._element_candidate_display_text(raw_candidate)).strip()
            if (
                not candidate_text
                or len(candidate_text) > max_label_length
                or candidate_text.lower() in {"main", "page", "body", "document"}
            ):
                continue
            candidate_role = self._loop._normalize_space(
                str(
                    raw_candidate.get("role")
                    or raw_candidate.get("semanticType")
                    or raw_candidate.get("semantic_type")
                    or raw_candidate.get("category")
                    or raw_candidate.get("tag")
                    or ""
                )
            ).strip().lower()
            if action_verb in {"assert_visible", "assert_text"} and candidate_role in preferred_roles:
                return candidate_text
            if not fallback_label:
                fallback_label = candidate_text
        selected_text = self._loop._normalize_space(self._loop._selected_element_text(element_info)).strip()
        if selected_text and len(selected_text) <= max_label_length and selected_text.lower() not in {"main", "page", "body", "document"}:
            return selected_text
        return fallback_label

    def should_replace_fast_path_locator_with_text(self, action_verb: str, locator: str) -> bool:
        if action_verb not in {"assert_visible", "assert_text"}:
            return False
        normalized_locator = self._loop._normalize_space(str(locator or "")).strip().lower()
        return normalized_locator in {"main", "body", "page", 'page.locator("main")', "page.locator('main')"}

    def compact_step_element_summary(self, step: dict[str, Any]) -> str:
        element_info = self._loop._resolve_selected_element_info(step.get("element_info") or {})
        if not isinstance(element_info, dict):
            return ""

        attributes = element_info.get("attributes") if isinstance(element_info.get("attributes"), dict) else {}
        candidates = [
            self._loop._selected_element_text(element_info),
            self._loop._normalize_space(str(attributes.get("aria-label") or "")).strip(),
            self._loop._normalize_space(str(attributes.get("placeholder") or "")).strip(),
            self._loop._normalize_space(str(element_info.get("id") or "")).strip(),
            self._loop._normalize_space(str(element_info.get("tag") or "")).strip(),
        ]
        parts = [part for part in candidates if part]
        return " · ".join(parts[:3])
