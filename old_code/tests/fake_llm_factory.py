"""S5-012: Reusable fake LLM client for Sprint 5 testing.

Provides FakeLLMClient — an async OpenAI-compatible fake that returns
schema-valid stub responses per LLM purpose without calling a real model.

Usage:
    client = FakeLLMClient()
    # or with custom responses:
    client = FakeLLMClient(purpose_responses={"step_plan_normalizer": {...}})
    response = await client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[...],
    )

The client also exposes .calls to inspect all captured call payloads.
"""
from __future__ import annotations

import json
from types import SimpleNamespace
from typing import Any


# ---------------------------------------------------------------------------
# Default schema-valid stub responses per purpose
# These match the shapes expected by LLMRuntimeController schema validation.
# ---------------------------------------------------------------------------

DEFAULT_STEP_PLAN_NORMALIZER_RESPONSE: dict[str, Any] = {
    "purpose": "step_plan_normalizer",
    "steps": [
        {
            "step_id": "pending-step-1",
            "intent": "click the Get started button",
            "children": [
                {
                    "operation_id": "op_1",
                    "type": "click",
                    "target": "Get started",
                    "locator": 'get_by_text("Get started", exact=True)',
                }
            ],
        }
    ],
    "plan_ready": True,
    "requires_confirmation": True,
}

DEFAULT_PLAN_DIFF_EDITOR_RESPONSE: dict[str, Any] = {
    "purpose": "plan_diff_editor",
    "corrected_steps": [
        {
            "step_id": "pending-step-1",
            "intent": "assert the heading then click Get started",
            "children": [
                {
                    "operation_id": "op_1",
                    "type": "assert_visible",
                    "target": "Welcome heading",
                    "locator": 'get_by_role("heading", name="Welcome")',
                },
                {
                    "operation_id": "op_2",
                    "type": "click",
                    "target": "Get started",
                    "locator": 'get_by_text("Get started", exact=True)',
                },
            ],
        }
    ],
    "correction_applied": True,
    "correction_type": "reorder_operations",
    "requires_confirmation": True,
}

DEFAULT_RECOVERY_DIAGNOSER_RESPONSE: dict[str, Any] = {
    "purpose": "recovery_diagnoser",
    "recovery_action": "retry",
    "reason": "Element may not have been visible yet; retry with a short wait.",
    "proposed_locator": 'get_by_text("Get started", exact=True)',
    "confidence": "medium",
    "requires_user_confirmation": False,
}

DEFAULT_PAGE_INTELLIGENCE_RESPONSE: dict[str, Any] = {
    "purpose": "page_intelligence_summarizer",
    "page_or_section_summary": "Landing page with hero section and CTA buttons",
    "semantic_quality": "mixed",
    "elements": [
        {
            "semantic_name": "Get started button",
            "element_type_guess": "button-like div",
            "section": "hero",
            "visible_text": "Get started",
            "signals_used": ["visible_text", "cursor_pointer"],
            "confidence": 0.8,
            "risk": "medium",
        }
    ],
    "ambiguities": ["Two elements with similar text in hero and nav sections"],
    "risk_flags": ["No data-testid or aria-label on primary CTA"],
}

DEFAULT_LOCATOR_SPECIALIST_RESPONSE: dict[str, Any] = {
    "purpose": "locator_specialist",
    "candidates": [
        {
            "locator": 'get_by_text("Get started", exact=True)',
            "strategy": "visible_text",
            "confidence": "high",
            "risk": "low",
        }
    ],
    "recommended": 'get_by_text("Get started", exact=True)',
    "requires_validation": True,
}

# Malformed response for negative tests
MALFORMED_RESPONSE: dict[str, Any] = {
    "error": "unexpected output",
    "missing_required_fields": True,
}

_DEFAULT_PURPOSE_RESPONSES: dict[str, dict[str, Any]] = {
    "step_plan_normalizer": DEFAULT_STEP_PLAN_NORMALIZER_RESPONSE,
    "plan_diff_editor": DEFAULT_PLAN_DIFF_EDITOR_RESPONSE,
    "recovery_diagnoser": DEFAULT_RECOVERY_DIAGNOSER_RESPONSE,
    "page_intelligence_summarizer": DEFAULT_PAGE_INTELLIGENCE_RESPONSE,
    "locator_specialist": DEFAULT_LOCATOR_SPECIALIST_RESPONSE,
}


def _make_usage(
    prompt_tokens: int = 100,
    completion_tokens: int = 20,
    cached_tokens: int = 0,
) -> Any:
    return SimpleNamespace(
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        total_tokens=prompt_tokens + completion_tokens,
        prompt_tokens_details=SimpleNamespace(cached_tokens=cached_tokens),
    )


def _make_response(content: str, prompt_tokens: int = 100, cached_tokens: int = 0) -> Any:
    return SimpleNamespace(
        choices=[
            SimpleNamespace(
                message=SimpleNamespace(
                    content=content,
                    tool_calls=None,
                    role="assistant",
                )
            )
        ],
        usage=_make_usage(
            prompt_tokens=prompt_tokens,
            completion_tokens=max(1, len(content) // 4),
            cached_tokens=cached_tokens,
        ),
    )


def _infer_purpose_from_messages(messages: list[dict[str, Any]]) -> str | None:
    """Try to infer the LLM purpose from message content (for routing in tests)."""
    for message in reversed(messages):
        content = str(message.get("content") or "")
        if "step_plan_normalizer" in content or "plan_ready" in content:
            return "step_plan_normalizer"
        if "plan_diff_editor" in content or "corrected_steps" in content:
            return "plan_diff_editor"
        if "recovery_diagnoser" in content or "recovery_action" in content:
            return "recovery_diagnoser"
        if "page_intelligence" in content:
            return "page_intelligence_summarizer"
        if "locator_specialist" in content:
            return "locator_specialist"
    return None


class FakeLLMClient:
    """Async OpenAI-compatible fake LLM client for Sprint 5 testing.

    Captures call payloads in .calls and returns configured stub responses.
    Does not call any real LLM.

    Args:
        purpose_responses: Override stub responses per purpose name.
            Unmapped purposes fall back to _DEFAULT_PURPOSE_RESPONSES.
        default_purpose: If purpose cannot be inferred from messages, use this.
        prompt_tokens: Simulated prompt token count in usage.
        cached_tokens: Simulated cached token count (for S5-007 attribution).
        force_malformed: If True, always return MALFORMED_RESPONSE (for negative tests).
    """

    def __init__(
        self,
        purpose_responses: dict[str, dict[str, Any]] | None = None,
        *,
        default_purpose: str = "step_plan_normalizer",
        prompt_tokens: int = 100,
        cached_tokens: int = 0,
        force_malformed: bool = False,
    ) -> None:
        self._responses: dict[str, dict[str, Any]] = {
            **_DEFAULT_PURPOSE_RESPONSES,
            **(purpose_responses or {}),
        }
        self._default_purpose = default_purpose
        self._prompt_tokens = prompt_tokens
        self._cached_tokens = cached_tokens
        self._force_malformed = force_malformed
        self.calls: list[dict[str, Any]] = []
        self.chat = SimpleNamespace(
            completions=SimpleNamespace(create=self._create)
        )

    async def _create(self, **payload: Any) -> Any:
        self.calls.append(dict(payload))

        if self._force_malformed:
            return _make_response(
                json.dumps(MALFORMED_RESPONSE),
                prompt_tokens=self._prompt_tokens,
                cached_tokens=self._cached_tokens,
            )

        messages = payload.get("messages") or []
        purpose = _infer_purpose_from_messages(messages) or self._default_purpose
        response_data = self._responses.get(purpose, DEFAULT_STEP_PLAN_NORMALIZER_RESPONSE)

        return _make_response(
            json.dumps(response_data),
            prompt_tokens=self._prompt_tokens,
            cached_tokens=self._cached_tokens,
        )

    def get_call_count(self) -> int:
        return len(self.calls)

    def get_last_call(self) -> dict[str, Any] | None:
        return self.calls[-1] if self.calls else None

    def get_messages_for_call(self, index: int = -1) -> list[dict[str, Any]]:
        if not self.calls:
            return []
        call = self.calls[index]
        return list(call.get("messages") or [])
