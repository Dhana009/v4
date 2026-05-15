from __future__ import annotations

from dataclasses import asdict, dataclass
import json
from typing import Any, Iterable

from runtime.telemetry import estimate_text_tokens


@dataclass(slots=True)
class SkillDiagnostics:
    loaded_skill_names: list[str]
    skill_count: int
    estimated_total_skill_tokens: int
    per_skill_estimated_tokens: dict[str, int]
    largest_skill_name: str
    largest_skill_tokens: int
    suggested_future_policy: str

    def to_summary_dict(self) -> dict[str, Any]:
        return asdict(self)


class SkillManager:
    def analyze(
        self,
        skills: Any,
        *,
        loaded_skill_names: list[str] | None = None,
    ) -> SkillDiagnostics:
        normalized_skills = self._normalize_skills(skills, loaded_skill_names=loaded_skill_names)

        loaded_names = [name for name, _ in normalized_skills]
        per_skill_estimated_tokens: dict[str, int] = {}
        estimated_total_skill_tokens = 0
        largest_skill_name = "none"
        largest_skill_tokens = 0

        for name, content in normalized_skills:
            skill_name = name or "unknown"
            token_count = estimate_text_tokens(content)
            per_skill_estimated_tokens[skill_name] = token_count
            estimated_total_skill_tokens += token_count
            if token_count > largest_skill_tokens:
                largest_skill_name = skill_name
                largest_skill_tokens = token_count

        suggested_future_policy = self._suggested_future_policy(estimated_total_skill_tokens)

        return SkillDiagnostics(
            loaded_skill_names=loaded_names,
            skill_count=len(loaded_names),
            estimated_total_skill_tokens=estimated_total_skill_tokens,
            per_skill_estimated_tokens=per_skill_estimated_tokens,
            largest_skill_name=largest_skill_name,
            largest_skill_tokens=largest_skill_tokens,
            suggested_future_policy=suggested_future_policy,
        )

    def _normalize_skills(
        self,
        skills: Any,
        *,
        loaded_skill_names: list[str] | None = None,
    ) -> list[tuple[str, str]]:
        if isinstance(skills, dict):
            return [
                (self._coerce_name(name, index), self._coerce_content(value))
                for index, (name, value) in enumerate(skills.items())
            ]

        if isinstance(skills, (list, tuple)):
            return self._normalize_sequence(skills, loaded_skill_names=loaded_skill_names)

        if isinstance(skills, str):
            return self._normalize_text(skills, loaded_skill_names=loaded_skill_names)

        fallback_name = self._coerce_name(
            loaded_skill_names[0] if loaded_skill_names else "combined_skill_text",
            0,
        )
        return [(fallback_name, self._coerce_content(skills))]

    def _normalize_sequence(
        self,
        skills: Iterable[Any],
        *,
        loaded_skill_names: list[str] | None = None,
    ) -> list[tuple[str, str]]:
        normalized: list[tuple[str, str]] = []
        skill_list = list(skills)
        names = list(loaded_skill_names or [])

        for index, item in enumerate(skill_list):
            if isinstance(item, dict):
                name = item.get("name") or item.get("skill_name") or item.get("id")
                content = item.get("content")
                if content is None:
                    content = item.get("text")
                if content is None:
                    content = item.get("body")
                if name is None and index < len(names):
                    name = names[index]
                normalized.append((self._coerce_name(name, index), self._coerce_content(content)))
                continue

            if isinstance(item, (list, tuple)) and len(item) >= 2:
                normalized.append(
                    (
                        self._coerce_name(item[0], index),
                        self._coerce_content(item[1]),
                    )
                )
                continue

            if isinstance(item, str):
                if index < len(names):
                    normalized.append((self._coerce_name(names[index], index), item))
                    continue

                if self._looks_like_content(item):
                    normalized.append((self._coerce_name(None, index), item))
                else:
                    normalized.append((self._coerce_name(item, index), ""))
                continue

            if index < len(names):
                normalized.append((self._coerce_name(names[index], index), self._coerce_content(item)))
                continue

            normalized.append((self._coerce_name(item, index), self._coerce_content("")))

        return normalized

    def _normalize_text(
        self,
        text: str,
        *,
        loaded_skill_names: list[str] | None = None,
    ) -> list[tuple[str, str]]:
        names = [self._coerce_name(name, index) for index, name in enumerate(loaded_skill_names or [])]
        if not names:
            return [("combined_skill_text", text)]

        if len(names) == 1:
            return [(names[0], text)]

        total_tokens = estimate_text_tokens(text)
        base_tokens = total_tokens // len(names)
        remainder = total_tokens % len(names)
        normalized: list[tuple[str, str]] = []
        cursor = 0

        for index, name in enumerate(names):
            chunk_tokens = base_tokens + (1 if index < remainder else 0)
            if chunk_tokens <= 0:
                normalized.append((name, ""))
                continue

            chunk_text = self._slice_text_by_estimated_tokens(text, cursor, chunk_tokens)
            normalized.append((name, chunk_text))
            cursor += len(chunk_text)

        return normalized

    def _slice_text_by_estimated_tokens(self, text: str, start_index: int, estimated_tokens: int) -> str:
        if estimated_tokens <= 0 or start_index >= len(text):
            return ""

        target_chars = max(1, estimated_tokens * 4)
        end_index = min(len(text), start_index + target_chars)
        return text[start_index:end_index]

    def _coerce_name(self, value: Any, index: int) -> str:
        text = str(value or "").strip()
        if text:
            return text
        return f"skill_{index + 1}"

    def _coerce_content(self, value: Any) -> str:
        if value is None:
            return ""
        if isinstance(value, str):
            return value
        if isinstance(value, (list, tuple, dict)):
            try:
                return json.dumps(value, ensure_ascii=True, separators=(",", ":"))
            except Exception:  # noqa: BLE001
                return str(value)
        return str(value)

    def _looks_like_content(self, value: str) -> bool:
        text = str(value or "").strip()
        if not text:
            return False
        return "\n" in text or len(text) > 80 or text.startswith("---") or text.startswith("#")

    def _suggested_future_policy(self, estimated_total_skill_tokens: int) -> str:
        if estimated_total_skill_tokens > 6000:
            return "needs_progressive_loading"
        if estimated_total_skill_tokens >= 2500:
            return "consider_compact_core"
        return "ok_current"
