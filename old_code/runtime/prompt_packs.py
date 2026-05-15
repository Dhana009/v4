from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
import hashlib
from typing import Any

from runtime.telemetry import estimate_messages_tokens, estimate_text_tokens


class _SafeTemplateDict(dict[str, str]):
    def __missing__(self, key: str) -> str:  # pragma: no cover - defensive helper
        return ""


def _stringify_context_value(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, Mapping):
        items = [
            f"{str(key).strip()}={_stringify_context_value(item)}"
            for key, item in value.items()
            if str(key).strip()
        ]
        return ", ".join(item for item in items if item)
    if isinstance(value, Sequence) and not isinstance(value, (bytes, bytearray)):
        parts = [_stringify_context_value(item) for item in value]
        return ", ".join(part for part in parts if part)
    return str(value).strip()


def _normalize_context(dynamic_context: Mapping[str, Any] | None) -> dict[str, str]:
    if not dynamic_context:
        return {}
    normalized: dict[str, str] = {}
    for key, value in dynamic_context.items():
        normalized[str(key).strip()] = _stringify_context_value(value)
    return normalized


def hash_stable_prefix(stable_prefix: str) -> str:
    return hashlib.sha256(str(stable_prefix or "").encode("utf-8")).hexdigest()[:16]


def count_system_prompt_tokens(messages: Sequence[Mapping[str, Any]] | None) -> int:
    total = 0
    for message in messages or []:
        if not isinstance(message, Mapping):
            continue
        if str(message.get("role") or "").strip().lower() != "system":
            continue
        content = message.get("content")
        if content is None:
            continue
        total += estimate_text_tokens(str(content))
    return total


@dataclass(frozen=True, slots=True)
class PromptPack:
    purpose: str
    prompt_pack_id: str
    prompt_pack_version: int
    stable_prefix: str
    dynamic_suffix_template: str
    required_safety_rules: tuple[str, ...]
    prefix_hash: str
    estimated_stable_tokens: int | None = None

    def render_dynamic_suffix(self, dynamic_context: Mapping[str, Any] | None = None) -> str:
        template = str(self.dynamic_suffix_template or "").strip()
        if not template:
            return ""
        try:
            rendered = template.format_map(_SafeTemplateDict(_normalize_context(dynamic_context)))
        except Exception:  # noqa: BLE001
            rendered = template
        return str(rendered or "").strip()

    def render_prompt(self, dynamic_context: Mapping[str, Any] | None = None) -> str:
        stable_prefix = str(self.stable_prefix or "").strip()
        rendered_suffix = self.render_dynamic_suffix(dynamic_context)
        if rendered_suffix:
            return f"{stable_prefix}\n\n{rendered_suffix}".strip()
        return stable_prefix

    def metadata(self, dynamic_context: Mapping[str, Any] | None = None) -> dict[str, Any]:
        rendered_suffix = self.render_dynamic_suffix(dynamic_context)
        rendered_prompt = self.stable_prefix.strip()
        if rendered_suffix:
            rendered_prompt = f"{rendered_prompt}\n\n{rendered_suffix}".strip()
        return {
            "purpose": self.purpose,
            "prompt_pack_id": self.prompt_pack_id,
            "prompt_pack_version": self.prompt_pack_version,
            "prefix_hash": self.prefix_hash,
            "estimated_stable_tokens": self.estimated_stable_tokens,
            "rendered_prompt": rendered_prompt,
            "rendered_suffix": rendered_suffix,
            "rendered_prompt_tokens": estimate_text_tokens(rendered_prompt),
        }


def apply_prompt_pack_to_messages(
    messages: Sequence[Mapping[str, Any]] | None,
    prompt_pack: PromptPack,
    *,
    dynamic_context: Mapping[str, Any] | None = None,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    copied_messages = [
        dict(message) if isinstance(message, Mapping) else message
        for message in (messages or [])
    ]
    rendered_prompt = prompt_pack.render_prompt(dynamic_context)

    existing_system_index: int | None = None
    for index, message in enumerate(copied_messages):
        if isinstance(message, dict) and str(message.get("role") or "").strip().lower() == "system":
            existing_system_index = index
            break

    if existing_system_index is None:
        copied_messages.insert(0, {"role": "system", "content": rendered_prompt})
    else:
        existing_content = str(copied_messages[existing_system_index].get("content") or "").strip()
        if existing_content.startswith(rendered_prompt) or (
            existing_content.startswith(prompt_pack.stable_prefix.strip())
            and prompt_pack.prompt_pack_id in existing_content
        ):
            rendered_prompt = existing_content
        elif existing_content:
            copied_messages[existing_system_index]["content"] = f"{rendered_prompt}\n\n{existing_content}".strip()
        else:
            copied_messages[existing_system_index]["content"] = rendered_prompt

    system_prompt_tokens = count_system_prompt_tokens(copied_messages)
    metadata = prompt_pack.metadata(dynamic_context)
    metadata.update(
        {
            "prompt_pack_applied": True,
            "system_prompt_tokens": system_prompt_tokens,
            "estimated_message_tokens": estimate_messages_tokens(list(copied_messages)),
        }
    )
    return copied_messages, metadata
