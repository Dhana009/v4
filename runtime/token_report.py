from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

# Sprint 3 INT-E2E-002: parse [LLM_TELEMETRY] lines from backend stdout
# and produce a structured token-report.json artifact.

_TELEMETRY_LINE_RE = re.compile(r"\[LLM_TELEMETRY\](.+)")
_KV_RE = re.compile(r'(\w+)=("(?:[^"\\]|\\.)*"|-?\d+(?:\.\d+)?|true|false|\S+)')

# Warning thresholds (warning-only, not hard failures in Sprint 3)
WARN_CALLS_PER_TEST = 10
WARN_INPUT_TOKENS_PER_TEST = 20_000


def parse_telemetry_line(line: str) -> dict[str, Any] | None:
    """Parse a single [LLM_TELEMETRY] log line into a dict. Returns None if not a telemetry line."""
    m = _TELEMETRY_LINE_RE.search(line)
    if not m:
        return None
    record: dict[str, Any] = {}
    for key, value in _KV_RE.findall(m.group(1)):
        if value.startswith('"') and value.endswith('"'):
            record[key] = value[1:-1]
        elif value == "true":
            record[key] = True
        elif value == "false":
            record[key] = False
        else:
            try:
                record[key] = int(value)
            except ValueError:
                try:
                    record[key] = float(value)
                except ValueError:
                    record[key] = value
    return record if record else None


def parse_telemetry_lines(log_text: str) -> list[dict[str, Any]]:
    """Extract all [LLM_TELEMETRY] records from a log text blob."""
    records = []
    for line in log_text.splitlines():
        record = parse_telemetry_line(line)
        if record:
            records.append(record)
    return records


def build_token_report(
    records: list[dict[str, Any]],
    *,
    test_name: str = "unknown",
) -> dict[str, Any]:
    """Aggregate telemetry records into a per-test token report."""
    if not records:
        return {
            "test_name": test_name,
            "call_count": 0,
            "total_estimated_input_tokens": 0,
            "total_output_tokens": 0,
            "largest_call_id": None,
            "largest_call_tokens": 0,
            "top_token_source": "none",
            "skills_loaded": [],
            "purposes": [],
            "warnings": [],
            "records": [],
        }

    call_count = len(records)
    total_input = sum(int(r.get("estimated_total_input_tokens") or 0) for r in records)
    total_output = sum(int(r.get("output_tokens") or 0) for r in records)

    largest = max(records, key=lambda r: int(r.get("estimated_total_input_tokens") or 0))
    largest_id = largest.get("call_id")
    largest_tokens = int(largest.get("estimated_total_input_tokens") or 0)

    # Identify top token source across all records
    skill_total = sum(int(r.get("skill_tokens") or 0) for r in records)
    history_total = sum(int(r.get("message_history_tokens") or 0) for r in records)
    dom_total = sum(int(r.get("dom_or_tool_result_tokens") or 0) for r in records)
    system_total = sum(int(r.get("system_prompt_tokens") or 0) for r in records)
    source_map = {
        "skill": skill_total,
        "history": history_total,
        "dom_tool_result": dom_total,
        "system": system_total,
    }
    top_token_source = max(source_map, key=lambda k: source_map[k])

    purposes = list({str(r.get("purpose") or "unknown") for r in records})
    skills_loaded: list[str] = []
    for r in records:
        raw = str(r.get("skills_loaded") or "")
        if raw and raw != "unknown":
            for s in raw.split(","):
                s = s.strip()
                if s and s not in skills_loaded:
                    skills_loaded.append(s)

    warnings: list[str] = []
    if call_count > WARN_CALLS_PER_TEST:
        warnings.append(f"call_count={call_count} exceeds warning threshold {WARN_CALLS_PER_TEST}")
    if total_input > WARN_INPUT_TOKENS_PER_TEST:
        warnings.append(f"estimated_input_tokens={total_input} exceeds warning threshold {WARN_INPUT_TOKENS_PER_TEST}")

    return {
        "test_name": test_name,
        "call_count": call_count,
        "total_estimated_input_tokens": total_input,
        "total_output_tokens": total_output,
        "largest_call_id": largest_id,
        "largest_call_tokens": largest_tokens,
        "top_token_source": top_token_source,
        "token_breakdown": source_map,
        "skills_loaded": skills_loaded,
        "purposes": purposes,
        "warnings": warnings,
        "records": records,
    }


def write_token_report(artifact_dir: Path, report: dict[str, Any]) -> Path:
    """Write token-report.json into the artifact directory."""
    artifact_dir.mkdir(parents=True, exist_ok=True)
    path = artifact_dir / "token-report.json"
    path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    return path


def print_token_summary(report: dict[str, Any]) -> None:
    """Print a concise token summary table to stdout."""
    print(
        f"[TOKEN_REPORT] test={report['test_name']} "
        f"calls={report['call_count']} "
        f"input_tokens={report['total_estimated_input_tokens']} "
        f"output_tokens={report['total_output_tokens']} "
        f"largest={report['largest_call_tokens']} "
        f"top_source={report['top_token_source']}"
    )
    for warning in report.get("warnings", []):
        print(f"[TOKEN_REPORT_WARNING] {warning}")
