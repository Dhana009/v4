from __future__ import annotations

import asyncio
import hashlib
import json
import os
import re
import subprocess
import sys
import time
from datetime import datetime, timezone
import urllib.error
import urllib.request
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, AsyncIterator, Awaitable, Callable, Mapping, Sequence, TypeVar
from urllib.parse import parse_qsl, quote, urlsplit, urlunsplit

from dotenv import dotenv_values


REPO_ROOT = Path(__file__).resolve().parents[2]
RESULTS_ROOT = REPO_ROOT / "test-results" / "autoworkbench-e2e"
E2E_LLM_MARKERS = ["[MODEL_ROUTER]", "[LLM_TELEMETRY]", "[CONTEXT_MANAGER]"]
E2E_LIFECYCLE_MARKERS = [
    "[PHASE]",
    "[CONFIRMED_PLAN]",
    "[EXECUTION_CONTRACT]",
    "[RECORDING_TARGET]",
    "[CODE_UPDATE]",
]
E2E_ARTIFACT_SCHEMA_VERSION = "autoworkbench.e2e.artifacts.v1"
DEFAULT_E2E_STATIC_SERVER_PORT = 8000
DEFAULT_E2E_BACKEND_PORT = 8765
DEFAULT_E2E_REMOTE_DEBUGGING_PORT = 9222
DEFAULT_E2E_ARTIFACT_PATHS: dict[str, str] = {
    "manifest": "manifest.json",
    "test_result": "test-result.json",
    "events": "events.ndjson",
    "commands": "commands.json",
    "rejections": "rejections.json",
    "redaction_report": "redaction-report.json",
    "backend_log": "backend.log",
    "frontend_log": "frontend.log",
    "browser_console_log": "browser-console.log",
    "summary": "summary.md",
    "backend_stdout": "backend.stdout.log",
    "backend_stderr": "backend.stderr.log",
    "static_server_stdout": "static-server.stdout.log",
    "static_server_stderr": "static-server.stderr.log",
    "frontend_console": "frontend.console.log",
    "backend_tail": "backend.tail.log",
    "frontend_console_tail": "frontend.console.tail.log",
    "failure": "failure.txt",
    "failure_context": "failure-context.json",
    "failure_screenshot": "failure.png",
    "page_html": "page.html",
}
DEFAULT_E2E_OPTIONAL_ABSENCE_NOTES: list[str] = [
    "events.ndjson, commands.json, and rejections.json are deferred to a later backend event stream slice",
    "trace-summary and redaction-report are deferred to a later trace/export slice",
]
REDACTION_REPORT_VERSION = "1.0"
REDACTION_REPORT_PATTERNS = ["token", "otp", "email", "phone", "password"]
REDACTION_REPORT_FILES_CHECKED = ["trace.ndjson", "commands.json"]
REDACTION_REPORT_PLACEHOLDERS = {
    "token": "[REDACTED_TOKEN]",
    "otp": "[REDACTED_OTP]",
    "email": "[REDACTED_EMAIL]",
    "phone": "[REDACTED_PHONE]",
    "password": "[REDACTED_PASSWORD]",
    "auth": "[REDACTED_AUTH]",
    "session": "[REDACTED_SESSION]",
    "session_id": "[REDACTED_SESSION]",
    "sessionid": "[REDACTED_SESSION]",
    "session_token": "[REDACTED_SESSION]",
    "access_token": "[REDACTED_TOKEN]",
    "auth_token": "[REDACTED_TOKEN]",
    "id_token": "[REDACTED_TOKEN]",
    "api_key": "[REDACTED_TOKEN]",
    "apikey": "[REDACTED_TOKEN]",
    "secret": "[REDACTED_SECRET]",
    "csrf": "[REDACTED_SECRET]",
    "xsrf": "[REDACTED_SECRET]",
}
_REDACTION_SENSITIVE_QUERY_PARAMS: dict[str, tuple[str, str]] = {
    "token": ("token", "[REDACTED_TOKEN]"),
    "access_token": ("token", "[REDACTED_TOKEN]"),
    "auth_token": ("token", "[REDACTED_TOKEN]"),
    "id_token": ("token", "[REDACTED_TOKEN]"),
    "api_key": ("token", "[REDACTED_TOKEN]"),
    "apikey": ("token", "[REDACTED_TOKEN]"),
    "otp": ("otp", "[REDACTED_OTP]"),
    "email": ("email", "[REDACTED_EMAIL]"),
    "phone": ("phone", "[REDACTED_PHONE]"),
    "password": ("password", "[REDACTED_PASSWORD]"),
    "pass": ("password", "[REDACTED_PASSWORD]"),
    "pwd": ("password", "[REDACTED_PASSWORD]"),
    "auth": ("auth", "[REDACTED_AUTH]"),
    "session": ("auth", "[REDACTED_SESSION]"),
    "session_id": ("auth", "[REDACTED_SESSION]"),
    "sessionid": ("auth", "[REDACTED_SESSION]"),
    "session_token": ("auth", "[REDACTED_SESSION]"),
    "sid": ("auth", "[REDACTED_SESSION]"),
    "secret": ("auth", "[REDACTED_SECRET]"),
    "csrf": ("auth", "[REDACTED_SECRET]"),
    "xsrf": ("auth", "[REDACTED_SECRET]"),
}
_REDACTION_EXACT_TEXT_RULES: list[tuple[str, str, str]] = [
    ("token", "sk-test-redaction-token", "[REDACTED_TOKEN]"),
    ("otp", "123456", "[REDACTED_OTP]"),
    ("email", "user@example.test", "[REDACTED_EMAIL]"),
    ("phone", "+1-202-555-0175", "[REDACTED_PHONE]"),
    ("password", "correct horse battery staple", "[REDACTED_PASSWORD]"),
]
_REDACTION_REGEX_RULES: list[tuple[str, re.Pattern[str], str]] = [
    ("token", re.compile(r"\bsk-[A-Za-z0-9-]+\b"), "[REDACTED_TOKEN]"),
    ("otp", re.compile(r"\b\d{6}\b"), "[REDACTED_OTP]"),
    ("email", re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"), "[REDACTED_EMAIL]"),
    ("phone", re.compile(r"\+?\d[\d\s().-]{7,}\d"), "[REDACTED_PHONE]"),
]
_REDACTION_URL_PATTERN = re.compile(r"https?://[^\s<>\"]+")
T = TypeVar("T")


def resolve_e2e_port(port: int | None, *, env_name: str, default: int) -> int:
    if port is not None:
        return port
    raw_port = os.getenv(env_name, "").strip()
    if raw_port:
        try:
            return int(raw_port)
        except ValueError as exc:
            raise RuntimeError(f"{env_name} must be an integer, got {raw_port!r}") from exc
    return default


def ensure_directory(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def tail_text(path: Path, line_count: int = 80) -> str:
    if not path.exists():
        return ""
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    if not lines:
        return ""
    return "\n".join(lines[-line_count:])


def tail_lines_text(text: str, line_count: int = 30) -> str:
    lines = text.splitlines()
    if not lines:
        return ""
    return "\n".join(lines[-line_count:])


def _compact_reason(exc: BaseException) -> str:
    text = " ".join(str(exc).split())
    if not text:
        return "timeout"
    return text[:160] if len(text) > 160 else text


def _detect_marker_line(lines: list[str], markers: list[str]) -> str | None:
    for line in reversed(lines):
        if any(marker in line for marker in markers):
            return line
    return None


def wait_for_process_log_markers(process: "ManagedProcess", markers: list[str], timeout_s: float = 30.0) -> str:
    deadline = time.monotonic() + timeout_s
    last_text = ""
    while time.monotonic() < deadline:
        last_text = process.stdout_path.read_text(encoding="utf-8", errors="replace")
        last_text = f"{last_text}\n{process.stderr_path.read_text(encoding='utf-8', errors='replace')}"
        if all(marker in last_text for marker in markers):
            return last_text
        if process.poll() is not None:
            raise RuntimeError(
                f"{process.name} exited early with code {process.returncode}\n"
                f"stdout:\n{tail_text(process.stdout_path)}\n"
                f"stderr:\n{tail_text(process.stderr_path)}"
            )
        time.sleep(0.25)
    missing = [marker for marker in markers if marker not in last_text]
    raise TimeoutError(f"Timed out waiting for log markers {missing!r} in {process.name}")


async def wait_for_process_log_markers_async(process: "ManagedProcess", markers: list[str], timeout_s: float = 30.0) -> str:
    deadline = time.monotonic() + timeout_s
    last_text = ""
    while time.monotonic() < deadline:
        last_text = process.stdout_path.read_text(encoding="utf-8", errors="replace")
        last_text = f"{last_text}\n{process.stderr_path.read_text(encoding='utf-8', errors='replace')}"
        if all(marker in last_text for marker in markers):
            return last_text
        if process.poll() is not None:
            raise RuntimeError(
                f"{process.name} exited early with code {process.returncode}\n"
                f"stdout:\n{tail_text(process.stdout_path)}\n"
                f"stderr:\n{tail_text(process.stderr_path)}"
            )
        await asyncio.sleep(0.25)
    missing = [marker for marker in markers if marker not in last_text]
    raise TimeoutError(f"Timed out waiting for log markers {missing!r} in {process.name}")


def wait_for_http_url(url: str, *, label: str, process: "ManagedProcess | None" = None, timeout_s: float = 60.0) -> None:
    deadline = time.monotonic() + timeout_s
    last_error: Exception | None = None

    while time.monotonic() < deadline:
        if process is not None and process.poll() is not None:
            stdout_text = tail_text(process.stdout_path)
            stderr_text = tail_text(process.stderr_path)
            if "PermissionError" in stderr_text and "Operation not permitted" in stderr_text:
                raise RuntimeError(
                    f"{label} could not start because local socket allocation is blocked in this environment.\n"
                    f"Requested URL: {url}\n"
                    f"stdout:\n{stdout_text}\n"
                    f"stderr:\n{stderr_text}"
                )
            raise RuntimeError(
                f"{label} exited early with code {process.returncode}\n"
                f"stdout:\n{stdout_text}\n"
                f"stderr:\n{stderr_text}"
            )

        try:
            with urllib.request.urlopen(url, timeout=2) as response:
                if 200 <= response.status < 300:
                    return
        except Exception as exc:  # noqa: BLE001
            last_error = exc
        time.sleep(0.25)

    raise TimeoutError(f"Timed out waiting for {label} at {url}: {last_error}")


def create_run_artifact_dir(test_name: str) -> Path:
    ensure_directory(RESULTS_ROOT)
    stamp = time.strftime("%Y%m%d-%H%M%S")
    run_dir = RESULTS_ROOT / f"{test_name}-{stamp}-{os.getpid()}"
    ensure_directory(run_dir)
    return run_dir


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _normalize_artifact_paths(artifacts: Mapping[str, str | Path] | None) -> dict[str, str]:
    if artifacts is None:
        return dict(DEFAULT_E2E_ARTIFACT_PATHS)
    normalized: dict[str, str] = {}
    for name, path in artifacts.items():
        normalized[name] = str(path)
    return normalized


def _normalize_file_hashes(file_hashes: Mapping[str, str] | None) -> dict[str, str]:
    if file_hashes is None:
        return {}
    normalized: dict[str, str] = {}
    for name, digest in file_hashes.items():
        normalized[name] = str(digest)
    return normalized


def _normalize_optional_absence_notes(optional_absence_notes: Sequence[str] | None) -> list[str]:
    if optional_absence_notes is None:
        return list(DEFAULT_E2E_OPTIONAL_ABSENCE_NOTES)
    return [str(note) for note in optional_absence_notes]


def _dedupe_finding_tuples(findings: Sequence[tuple[str, str]]) -> list[tuple[str, str]]:
    unique: list[tuple[str, str]] = []
    seen: set[tuple[str, str]] = set()
    for finding in findings:
        if finding in seen:
            continue
        seen.add(finding)
        unique.append(finding)
    return unique


def _format_finding_tuples(findings: Sequence[tuple[str, str]]) -> list[dict[str, str]]:
    return [{"pattern": pattern, "location": location} for pattern, location in findings]


def _normalize_query_key(key: str) -> str:
    return re.sub(r"[-\s]+", "_", key.strip().lower())


def _redact_url_substrings(text: str, *, location: str) -> tuple[str, list[tuple[str, str]]]:
    if "://" not in text and "?" not in text and "&" not in text:
        return text, []

    redacted_text = text
    findings: list[tuple[str, str]] = []
    matches = list(_REDACTION_URL_PATTERN.finditer(text))
    if not matches:
        return text, []

    for match in reversed(matches):
        url_text = match.group(0)
        parsed = urlsplit(url_text)
        if not parsed.scheme or not parsed.netloc:
            continue
        query_pairs = parse_qsl(parsed.query, keep_blank_values=True)
        if not query_pairs:
            continue
        redacted_pairs: list[tuple[str, str]] = []
        url_changed = False
        for key, value in query_pairs:
            normalized_key = _normalize_query_key(key)
            rule = _REDACTION_SENSITIVE_QUERY_PARAMS.get(normalized_key)
            if rule is None:
                redacted_pairs.append((key, value))
                continue
            pattern_name, replacement = rule
            redacted_pairs.append((key, replacement))
            findings.append((pattern_name, location))
            url_changed = True
        if not url_changed:
            continue
        redacted_query = "&".join(
            f"{quote(key, safe='')}={quote(value, safe='[]_')}"
            for key, value in redacted_pairs
        )
        redacted_url = urlunsplit((parsed.scheme, parsed.netloc, parsed.path, redacted_query, parsed.fragment))
        redacted_text = f"{redacted_text[:match.start()]}{redacted_url}{redacted_text[match.end():]}"
    return redacted_text, _dedupe_finding_tuples(findings)


def _redact_text_value(text: str, *, location: str) -> tuple[str, list[tuple[str, str]]]:
    redacted = text
    findings: list[tuple[str, str]] = []
    redacted, url_findings = _redact_url_substrings(redacted, location=location)
    findings.extend(url_findings)
    for pattern_name, raw_value, replacement in _REDACTION_EXACT_TEXT_RULES:
        if raw_value in redacted:
            redacted = redacted.replace(raw_value, replacement)
            findings.append((pattern_name, location))
    for pattern_name, regex, replacement in _REDACTION_REGEX_RULES:
        if regex.search(redacted):
            redacted = regex.sub(replacement, redacted)
            findings.append((pattern_name, location))
    return redacted, _dedupe_finding_tuples(findings)


def _redact_sensitive_value(value: Any, *, location: str) -> tuple[Any, list[tuple[str, str]]]:
    if isinstance(value, Mapping):
        redacted_mapping: dict[str, Any] = {}
        findings: list[tuple[str, str]] = []
        for key, inner_value in value.items():
            normalized_key = str(key)
            child_location = f"{location}.{normalized_key}" if location else normalized_key
            if normalized_key in REDACTION_REPORT_PLACEHOLDERS:
                redacted_mapping[normalized_key] = REDACTION_REPORT_PLACEHOLDERS[normalized_key]
                findings.append((normalized_key, child_location))
                continue
            redacted_inner, child_findings = _redact_sensitive_value(inner_value, location=child_location)
            redacted_mapping[normalized_key] = redacted_inner
            findings.extend(child_findings)
        return redacted_mapping, _dedupe_finding_tuples(findings)
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        redacted_list: list[Any] = []
        findings: list[tuple[str, str]] = []
        for index, item in enumerate(value):
            child_location = f"{location}[{index}]"
            redacted_item, child_findings = _redact_sensitive_value(item, location=child_location)
            redacted_list.append(redacted_item)
            findings.extend(child_findings)
        return redacted_list, _dedupe_finding_tuples(findings)
    if isinstance(value, str):
        return _redact_text_value(value, location=location)
    return value, []


def _normalize_redaction_findings(findings: Sequence[tuple[str, str]] | Sequence[Mapping[str, Any]] | None) -> list[dict[str, Any]]:
    if findings is None:
        return []
    normalized: list[tuple[str, str]] = []
    for finding in findings:
        if isinstance(finding, Mapping):
            pattern = str(finding.get("pattern", "unknown"))
            location = str(finding.get("location", "unknown"))
            normalized.append((pattern, location))
        else:
            pattern, location = finding
            normalized.append((str(pattern), str(location)))
    return _format_finding_tuples(_dedupe_finding_tuples(normalized))


def _build_redaction_report(
    *,
    findings: Sequence[tuple[str, str]] | None = None,
    redaction_report: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    if redaction_report is not None:
        provided_findings = _normalize_redaction_findings(redaction_report.get("findings"))
        additional_findings = _normalize_redaction_findings(findings)
        merged_findings = _format_finding_tuples(
            _dedupe_finding_tuples(
                [
                    *( (entry["pattern"], entry["location"]) for entry in provided_findings ),
                    *( (entry["pattern"], entry["location"]) for entry in additional_findings ),
                ]
            )
        )
        payload = {
            "redaction_passed": bool(redaction_report.get("redaction_passed", True)),
            "redaction_version": str(redaction_report.get("redaction_version", REDACTION_REPORT_VERSION)),
            "patterns_checked": [str(pattern) for pattern in redaction_report.get("patterns_checked", REDACTION_REPORT_PATTERNS)],
            "files_checked": [str(file_name) for file_name in redaction_report.get("files_checked", REDACTION_REPORT_FILES_CHECKED)],
            "findings": merged_findings,
        }
        return payload
    return {
        "redaction_passed": True,
        "redaction_version": REDACTION_REPORT_VERSION,
        "patterns_checked": list(REDACTION_REPORT_PATTERNS),
        "files_checked": list(REDACTION_REPORT_FILES_CHECKED),
        "findings": _normalize_redaction_findings(findings),
    }


def _rewrite_trace_export_optional_absence_notes(
    optional_absence_notes: Sequence[str] | None,
    *,
    redaction_report_written: bool = False,
) -> list[str]:
    base_notes = _normalize_optional_absence_notes(optional_absence_notes)
    default_trace_export_note = DEFAULT_E2E_OPTIONAL_ABSENCE_NOTES[1]
    rewritten_notes: list[str] = []
    for note in base_notes:
        if note == default_trace_export_note:
            if redaction_report_written:
                rewritten_notes.append("trace-summary is deferred to a later trace/export slice")
            else:
                rewritten_notes.append(note)
            continue
        rewritten_notes.append(note)
    return rewritten_notes


def _resolve_artifact_file_name(name: str) -> str:
    return DEFAULT_E2E_ARTIFACT_PATHS.get(name, name)


def _format_event_stream_absence_note(missing_artifacts: Sequence[str]) -> str:
    missing = [str(artifact) for artifact in missing_artifacts]
    if not missing:
        return ""
    if len(missing) == 1:
        return f"{missing[0]} is deferred to a later backend event stream slice"
    if len(missing) == 2:
        return f"{missing[0]} and {missing[1]} are deferred to a later backend event stream slice"
    if len(missing) == 3:
        return f"{missing[0]}, {missing[1]}, and {missing[2]} are deferred to a later backend event stream slice"
    return f"{', '.join(missing[:-1])}, and {missing[-1]} are deferred to a later backend event stream slice"


def _rewrite_event_stream_optional_absence_notes(
    optional_absence_notes: Sequence[str] | None,
    *,
    events_written: bool = False,
    commands_written: bool = False,
    rejections_written: bool = False,
) -> list[str]:
    base_notes = _normalize_optional_absence_notes(optional_absence_notes)
    default_event_stream_note = DEFAULT_E2E_OPTIONAL_ABSENCE_NOTES[0]
    missing_artifacts: list[str] = []
    if not events_written:
        missing_artifacts.append("events.ndjson")
    if not commands_written:
        missing_artifacts.append("commands.json")
    if not rejections_written:
        missing_artifacts.append("rejections.json")

    rewritten_notes: list[str] = []
    for note in base_notes:
        if note == default_event_stream_note:
            if missing_artifacts:
                rewritten_notes.append(_format_event_stream_absence_note(missing_artifacts))
            continue
        rewritten_notes.append(note)
    return rewritten_notes


def _serialize_ndjson_records(records: Sequence[Any]) -> str:
    lines: list[str] = []
    for record in records:
        if isinstance(record, Mapping):
            payload: Any = dict(record)
        else:
            payload = record
        lines.append(json.dumps(payload, sort_keys=True))
    if not lines:
        return ""
    return "\n".join(lines) + "\n"


def _write_ndjson_artifact(artifact_dir: Path, name: str, records: Sequence[Any] | None) -> tuple[str, str] | None:
    if records is None:
        return None
    file_name = _resolve_artifact_file_name(name)
    path = artifact_dir / file_name
    ensure_directory(path.parent)
    text = _serialize_ndjson_records(records)
    path.write_text(text, encoding="utf-8")
    return file_name, text


def _serialize_json_array_records(records: Sequence[Any]) -> str:
    payload: list[Any] = []
    for record in records:
        if isinstance(record, Mapping):
            payload.append(dict(record))
        else:
            payload.append(record)
    return json.dumps(payload, indent=2, sort_keys=True)


def _write_json_array_artifact(artifact_dir: Path, name: str, records: Sequence[Any] | None) -> tuple[str, str] | None:
    if records is None:
        return None
    file_name = _resolve_artifact_file_name(name)
    path = artifact_dir / file_name
    ensure_directory(path.parent)
    text = _serialize_json_array_records(records)
    path.write_text(text, encoding="utf-8")
    return file_name, text


def _event_record_type(event: Any) -> str | None:
    if isinstance(event, Mapping):
        for key in ("type", "event"):
            value = event.get(key)
            if value is not None:
                return str(value)
        return None
    for key in ("type", "event"):
        value = getattr(event, key, None)
        if value is not None:
            return str(value)
    return None


def _normalize_event_evidence(event_evidence: Mapping[str, Any] | None) -> dict[str, Any]:
    if event_evidence is None:
        return {}
    normalized, _findings = _redact_sensitive_value(event_evidence, location="event_evidence")
    if isinstance(normalized, Mapping):
        return {str(key): value for key, value in normalized.items()}
    return {}


def _append_event_evidence_summary(summary_text: str, event_evidence: Mapping[str, Any]) -> str:
    evidence_json = json.dumps(_normalize_event_evidence(event_evidence), indent=2, sort_keys=True)
    summary_prefix = summary_text.rstrip()
    if summary_prefix:
        summary_prefix += "\n\n"
    return f"{summary_prefix}## Event evidence\n\n```json\n{evidence_json}\n```\n"


def _build_failure_event_evidence(
    event_evidence: Mapping[str, Any] | None,
    expected_event_type: str | None,
    observed_event_types: Sequence[str] | None,
) -> dict[str, Any] | None:
    normalized_event_evidence = _normalize_event_evidence(event_evidence)
    normalized_observed_event_types = [str(event_type) for event_type in observed_event_types] if observed_event_types is not None else []

    if normalized_event_evidence:
        return normalized_event_evidence

    if expected_event_type is None and not normalized_observed_event_types:
        return None

    built_event_evidence: dict[str, Any] = {}
    if expected_event_type is not None:
        built_event_evidence["expected_event_type"] = str(expected_event_type)
    if normalized_observed_event_types:
        built_event_evidence["observed_event_types"] = normalized_observed_event_types
    return built_event_evidence


def collect_events(source: Any, event_type: str | None = None) -> list[Any]:
    events: list[Any]
    if isinstance(source, Sequence) and not isinstance(source, (str, bytes, bytearray, Path)):
        events = list(source)
    elif isinstance(source, Mapping):
        events = [dict(source)]
    else:
        source_path = Path(source)
        if source_path.exists():
            event_path = source_path if source_path.is_file() else source_path / "events.ndjson"
        else:
            event_path = RESULTS_ROOT / str(source) / "events.ndjson"
        if not event_path.exists():
            events = []
        else:
            events = []
            for line in event_path.read_text(encoding="utf-8", errors="replace").splitlines():
                if not line.strip():
                    continue
                payload = json.loads(line)
                if isinstance(payload, Mapping):
                    events.append(dict(payload))
                else:
                    events.append(payload)
    if event_type is None:
        return events
    return [event for event in events if _event_record_type(event) == event_type]


def wait_for_event(source: Any, event_type: str, event_filter: Mapping[str, Any] | None = None) -> Any:
    events = collect_events(source)
    for event in events:
        if _event_record_type(event) != event_type:
            continue
        if event_filter is not None:
            if isinstance(event, Mapping):
                matches = all(event.get(key) == value for key, value in event_filter.items())
            else:
                matches = all(getattr(event, key, None) == value for key, value in event_filter.items())
            if not matches:
                continue
        return event

    available_types = [record_type for record_type in (_event_record_type(event) for event in events) if record_type is not None]
    filter_text = f" matching {dict(event_filter)!r}" if event_filter else ""
    raise AssertionError(
        f"Expected event {event_type!r}{filter_text} was not found. Available events: {available_types!r}"
    )


def assert_sequence(source: Any, expected_types: Sequence[str]) -> None:
    events = collect_events(source)
    actual_types = [record_type for record_type in (_event_record_type(event) for event in events) if record_type is not None]
    expected_type_list = [str(event_type) for event_type in expected_types]
    if not expected_type_list:
        return

    cursor = 0
    for expected_type in expected_type_list:
        while cursor < len(actual_types) and actual_types[cursor] != expected_type:
            cursor += 1
        if cursor >= len(actual_types):
            raise AssertionError(
                f"Expected event sequence {expected_type_list!r} was not found in order. "
                f"Missing {expected_type!r} after actual events {actual_types!r}"
            )
        cursor += 1


def assert_no_event(source: Any, forbidden_type: str) -> None:
    events = collect_events(source)
    matching_events = [event for event in events if _event_record_type(event) == forbidden_type]
    if matching_events:
        raise AssertionError(f"Forbidden event {forbidden_type!r} was present: {matching_events!r}")


def _hash_text_value(text: str) -> str:
    return f"sha256:{hashlib.sha256(text.encode('utf-8')).hexdigest()}"


def _write_text_artifacts(artifact_dir: Path, artifact_texts: Mapping[str, str] | None) -> dict[str, str]:
    if not artifact_texts:
        return {}
    written: dict[str, str] = {}
    for name, text in artifact_texts.items():
        file_name = _resolve_artifact_file_name(name)
        path = artifact_dir / file_name
        ensure_directory(path.parent)
        path.write_text(text, encoding="utf-8")
        written[file_name] = text
    return written


def _hash_artifact_texts(artifact_texts: Mapping[str, str] | None) -> dict[str, str]:
    if not artifact_texts:
        return {}
    file_hashes: dict[str, str] = {}
    for name, text in artifact_texts.items():
        file_name = _resolve_artifact_file_name(name)
        file_hashes[file_name] = _hash_text_value(text)
    return file_hashes


def write_json_artifact(path: Path, payload: dict[str, Any]) -> dict[str, Any]:
    ensure_directory(path.parent)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    return payload


def build_artifact_manifest(
    *,
    artifact_dir: Path,
    test_name: str,
    status: str = "running",
    created_at: str | None = None,
    artifacts: Mapping[str, str | Path] | None = None,
    file_hashes: Mapping[str, str] | None = None,
    optional_absence_notes: Sequence[str] | None = None,
    event_evidence: Mapping[str, Any] | None = None,
    run_id: str | None = None,
) -> dict[str, Any]:
    return {
        "schema_version": E2E_ARTIFACT_SCHEMA_VERSION,
        "test_name": test_name,
        "run_id": run_id or artifact_dir.name,
        "created_at": created_at or _utc_now_iso(),
        "artifact_dir": str(artifact_dir),
        "status": status,
        "artifacts": _normalize_artifact_paths(artifacts),
        "file_hashes": _normalize_file_hashes(file_hashes),
        "optional_absence_notes": _normalize_optional_absence_notes(optional_absence_notes),
        **({"event_evidence": _normalize_event_evidence(event_evidence)} if event_evidence is not None else {}),
    }


def write_artifact_manifest(
    *,
    artifact_dir: Path,
    test_name: str,
    status: str = "running",
    created_at: str | None = None,
    artifacts: Mapping[str, str | Path] | None = None,
    file_hashes: Mapping[str, str] | None = None,
    optional_absence_notes: Sequence[str] | None = None,
    event_evidence: Mapping[str, Any] | None = None,
    run_id: str | None = None,
) -> dict[str, Any]:
    manifest = build_artifact_manifest(
        artifact_dir=artifact_dir,
        test_name=test_name,
        status=status,
        created_at=created_at,
        artifacts=artifacts,
        file_hashes=file_hashes,
        optional_absence_notes=optional_absence_notes,
        event_evidence=event_evidence,
        run_id=run_id,
    )
    return write_json_artifact(artifact_dir / "manifest.json", manifest)


def build_test_result(
    *,
    artifact_dir: Path,
    test_name: str,
    status: str = "unknown",
    error_summary: str | None = None,
    event_evidence: Mapping[str, Any] | None = None,
    run_id: str | None = None,
) -> dict[str, Any]:
    sanitized_error_summary = error_summary
    if sanitized_error_summary is not None:
        sanitized_error_summary, _error_findings = _redact_text_value(sanitized_error_summary, location="error_summary")
    payload: dict[str, Any] = {
        "schema_version": E2E_ARTIFACT_SCHEMA_VERSION,
        "test_name": test_name,
        "run_id": run_id or artifact_dir.name,
        "artifact_dir": str(artifact_dir),
        "status": status,
    }
    if sanitized_error_summary:
        payload["error_summary"] = sanitized_error_summary
    if event_evidence is not None:
        payload["event_evidence"] = _normalize_event_evidence(event_evidence)
    return payload


def write_test_result(
    *,
    artifact_dir: Path,
    test_name: str,
    status: str = "unknown",
    error_summary: str | None = None,
    event_evidence: Mapping[str, Any] | None = None,
    run_id: str | None = None,
) -> dict[str, Any]:
    result = build_test_result(
        artifact_dir=artifact_dir,
        test_name=test_name,
        status=status,
        error_summary=error_summary,
        event_evidence=event_evidence,
        run_id=run_id,
    )
    return write_json_artifact(artifact_dir / "test-result.json", result)


def finalize_test_result(
    *,
    artifact_dir: Path,
    test_name: str,
    status: str,
    error_summary: str | None = None,
    created_at: str | None = None,
    artifacts: Mapping[str, str | Path] | None = None,
    artifact_texts: Mapping[str, str] | None = None,
    event_records: Sequence[Any] | None = None,
    command_records: Sequence[Any] | None = None,
    rejection_records: Sequence[Any] | None = None,
    file_hashes: Mapping[str, str] | None = None,
    optional_absence_notes: Sequence[str] | None = None,
    event_evidence: Mapping[str, Any] | None = None,
    redaction_report: Mapping[str, Any] | None = None,
    run_id: str | None = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    effective_artifact_texts: Mapping[str, str] | None = artifact_texts
    redaction_findings: list[tuple[str, str]] = []
    if event_evidence is not None and artifact_texts:
        effective_artifact_texts = dict(artifact_texts)
        summary_key = next((key for key in ("summary.md", "summary") if key in effective_artifact_texts), None)
        if summary_key is not None:
            effective_artifact_texts[summary_key] = _append_event_evidence_summary(
                effective_artifact_texts[summary_key],
                event_evidence,
            )
    if effective_artifact_texts:
        sanitized_artifact_texts: dict[str, str] = {}
        for artifact_name, artifact_text in effective_artifact_texts.items():
            file_name = _resolve_artifact_file_name(artifact_name)
            sanitized_text, findings = _redact_text_value(artifact_text, location=file_name)
            sanitized_artifact_texts[artifact_name] = sanitized_text
            redaction_findings.extend(findings)
        effective_artifact_texts = sanitized_artifact_texts

    sanitized_error_summary = error_summary
    if sanitized_error_summary is not None:
        sanitized_error_summary, findings = _redact_text_value(sanitized_error_summary, location="error_summary")
        redaction_findings.extend(findings)

    sanitized_event_evidence = event_evidence
    if sanitized_event_evidence is not None:
        normalized_event_evidence, findings = _redact_sensitive_value(sanitized_event_evidence, location="event_evidence")
        sanitized_event_evidence = normalized_event_evidence if isinstance(normalized_event_evidence, Mapping) else {}
        redaction_findings.extend(findings)

    effective_artifacts = artifacts
    event_artifact: tuple[str, str] | None = None
    if event_records is not None:
        event_artifact = _write_ndjson_artifact(artifact_dir, "events", event_records)
        if effective_artifacts is not None and "events" not in effective_artifacts:
            effective_artifacts = dict(effective_artifacts)
            effective_artifacts["events"] = _resolve_artifact_file_name("events")

    command_artifact: tuple[str, str] | None = None
    if command_records is not None:
        command_artifact = _write_json_array_artifact(artifact_dir, "commands", command_records)
        if effective_artifacts is not None and "commands" not in effective_artifacts:
            effective_artifacts = dict(effective_artifacts)
            effective_artifacts["commands"] = _resolve_artifact_file_name("commands")

    rejection_artifact: tuple[str, str] | None = None
    if rejection_records is not None:
        rejection_artifact = _write_json_array_artifact(artifact_dir, "rejections", rejection_records)
        if effective_artifacts is not None and "rejections" not in effective_artifacts:
            effective_artifacts = dict(effective_artifacts)
            effective_artifacts["rejections"] = _resolve_artifact_file_name("rejections")

    _write_text_artifacts(artifact_dir, effective_artifact_texts)

    redaction_report_written = False
    redaction_report_artifact: tuple[str, str] | None = None
    redaction_report_requested = redaction_report is not None or artifacts is None or (
        effective_artifacts is not None and "redaction_report" in effective_artifacts
    )
    if redaction_report_requested:
        redaction_report_file_name = _resolve_artifact_file_name("redaction_report")
        if effective_artifacts is not None and "redaction_report" in effective_artifacts:
            redaction_report_file_name = str(effective_artifacts["redaction_report"])
        redaction_report_payload = _build_redaction_report(
            findings=redaction_findings,
            redaction_report=redaction_report,
        )
        redaction_report_path = artifact_dir / redaction_report_file_name
        write_json_artifact(redaction_report_path, redaction_report_payload)
        redaction_report_text = redaction_report_path.read_text(encoding="utf-8")
        redaction_report_artifact = (redaction_report_file_name, redaction_report_text)
        redaction_report_written = True
        if effective_artifacts is not None and "redaction_report" not in effective_artifacts:
            effective_artifacts = dict(effective_artifacts)
            effective_artifacts["redaction_report"] = redaction_report_file_name

    resolved_file_hashes = _normalize_file_hashes(file_hashes)
    if not resolved_file_hashes and effective_artifact_texts:
        resolved_file_hashes = _hash_artifact_texts(effective_artifact_texts)
    if event_artifact is not None:
        event_file_name, event_text = event_artifact
        if event_file_name not in resolved_file_hashes:
            resolved_file_hashes[event_file_name] = _hash_text_value(event_text)
    if command_artifact is not None:
        command_file_name, command_text = command_artifact
        if command_file_name not in resolved_file_hashes:
            resolved_file_hashes[command_file_name] = _hash_text_value(command_text)
    if rejection_artifact is not None:
        rejection_file_name, rejection_text = rejection_artifact
        if rejection_file_name not in resolved_file_hashes:
            resolved_file_hashes[rejection_file_name] = _hash_text_value(rejection_text)
    if redaction_report_artifact is not None:
        redaction_report_file_name, redaction_report_text = redaction_report_artifact
        if redaction_report_file_name not in resolved_file_hashes:
            resolved_file_hashes[redaction_report_file_name] = _hash_text_value(redaction_report_text)

    effective_status = status
    if not redaction_report_written:
        missing_redaction_report = False
        if sanitized_event_evidence is not None:
            missing_values = sanitized_event_evidence.get("missing")
            if isinstance(missing_values, Sequence) and not isinstance(missing_values, (str, bytes, bytearray)):
                missing_redaction_report = any(
                    str(value) in {"redaction-report.json", "redaction_report"} for value in missing_values
                )
        if not missing_redaction_report and sanitized_error_summary is not None:
            missing_redaction_report = "redaction-report.json missing" in sanitized_error_summary
        if missing_redaction_report:
            effective_status = "failed"
    elif redaction_report is not None:
        if not bool(redaction_report.get("redaction_passed", True)):
            effective_status = "failed"
    effective_optional_absence_notes = optional_absence_notes
    if event_records is not None or command_records is not None or rejection_records is not None:
        effective_optional_absence_notes = _rewrite_event_stream_optional_absence_notes(
            optional_absence_notes,
            events_written=event_records is not None,
            commands_written=command_records is not None,
            rejections_written=rejection_records is not None,
        )
    if redaction_report_written:
        effective_optional_absence_notes = _rewrite_trace_export_optional_absence_notes(
            effective_optional_absence_notes,
            redaction_report_written=True,
        )
    manifest = write_artifact_manifest(
        artifact_dir=artifact_dir,
        test_name=test_name,
        status=effective_status,
        created_at=created_at,
        artifacts=effective_artifacts,
        file_hashes=resolved_file_hashes,
        optional_absence_notes=effective_optional_absence_notes,
        event_evidence=sanitized_event_evidence,
        run_id=run_id,
    )
    result = write_test_result(
        artifact_dir=artifact_dir,
        test_name=test_name,
        status=effective_status,
        error_summary=sanitized_error_summary,
        event_evidence=sanitized_event_evidence,
        run_id=run_id,
    )
    return manifest, result


def _load_repo_env_values() -> dict[str, str]:
    env_path = REPO_ROOT / ".env"
    raw_values = dotenv_values(env_path)
    repo_env = {key: value for key, value in raw_values.items() if key and value is not None}
    openai_key = str(repo_env.get("OPENAI_API_KEY", "")).strip()
    if not openai_key or not openai_key.startswith("sk-"):
        raise RuntimeError("Repo .env missing valid OPENAI_API_KEY")
    return {key: str(value) for key, value in repo_env.items()}


def _backend_launch_command() -> list[str]:
    return [
        sys.executable,
        "-c",
        "import dotenv; dotenv.load_dotenv = lambda *args, **kwargs: None; "
        "import runpy; runpy.run_module('server', run_name='__main__')",
    ]


@dataclass
class ManagedProcess:
    name: str
    process: subprocess.Popen[str]
    stdout_path: Path
    stderr_path: Path
    stdout_handle: Any
    stderr_handle: Any
    port: int
    base_url: str

    def poll(self) -> int | None:
        return self.process.poll()

    @property
    def returncode(self) -> int | None:
        return self.process.returncode

    def stop(self, timeout_s: float = 10.0) -> None:
        if self.poll() is None:
            self.process.terminate()
            try:
                self.process.wait(timeout=timeout_s)
            except subprocess.TimeoutExpired:
                self.process.kill()
                self.process.wait(timeout=timeout_s)
        for handle in (self.stdout_handle, self.stderr_handle):
            try:
                handle.flush()
            except Exception:
                pass
            try:
                handle.close()
            except Exception:
                pass


def start_managed_process(
    *,
    name: str,
    command: list[str],
    cwd: Path,
    artifact_dir: Path,
    stdout_name: str,
    stderr_name: str,
    env: dict[str, str],
    port: int,
) -> ManagedProcess:
    ensure_directory(artifact_dir)
    stdout_path = artifact_dir / stdout_name
    stderr_path = artifact_dir / stderr_name
    stdout_handle = stdout_path.open("w", encoding="utf-8", buffering=1)
    stderr_handle = stderr_path.open("w", encoding="utf-8", buffering=1)
    process = subprocess.Popen(
        command,
        cwd=str(cwd),
        env=env,
        stdout=stdout_handle,
        stderr=stderr_handle,
        text=True,
    )
    return ManagedProcess(
        name=name,
        process=process,
        stdout_path=stdout_path,
        stderr_path=stderr_path,
        stdout_handle=stdout_handle,
        stderr_handle=stderr_handle,
        port=port,
        base_url=f"http://127.0.0.1:{port}",
    )


def start_static_server(app_root: Path, artifact_dir: Path, port: int | None = None) -> ManagedProcess:
    server_port = resolve_e2e_port(
        port,
        env_name="AUTOWORKBENCH_E2E_STATIC_SERVER_PORT",
        default=DEFAULT_E2E_STATIC_SERVER_PORT,
    )
    env = os.environ.copy()
    env["PYTHONUNBUFFERED"] = "1"
    process = start_managed_process(
        name="static-server",
        command=[sys.executable, "-m", "http.server", str(server_port), "--bind", "127.0.0.1"],
        cwd=app_root,
        artifact_dir=artifact_dir,
        stdout_name="static-server.stdout.log",
        stderr_name="static-server.stderr.log",
        env=env,
        port=server_port,
    )
    wait_for_http_url(f"{process.base_url}/index.html", label="static server", process=process, timeout_s=10.0)
    return process


def start_autoworkbench_backend(
    start_url: str,
    artifact_dir: Path,
    port: int | None = None,
    remote_debugging_port: int | None = None,
) -> ManagedProcess:
    backend_port = resolve_e2e_port(
        port,
        env_name="AUTOWORKBENCH_E2E_BACKEND_PORT",
        default=DEFAULT_E2E_BACKEND_PORT,
    )
    debugging_port = resolve_e2e_port(
        remote_debugging_port,
        env_name="AUTOWORKBENCH_E2E_REMOTE_DEBUGGING_PORT",
        default=DEFAULT_E2E_REMOTE_DEBUGGING_PORT,
    )
    env = os.environ.copy()
    env.update(_load_repo_env_values())
    env["PYTHONUNBUFFERED"] = "1"
    env["PORT"] = str(backend_port)
    env["START_URL"] = start_url
    env["AUTOWORKBENCH_REMOTE_DEBUGGING_PORT"] = str(debugging_port)
    assert env["OPENAI_API_KEY"].startswith("sk-")
    assert env["PORT"] == str(backend_port)
    assert env["AUTOWORKBENCH_REMOTE_DEBUGGING_PORT"] == str(debugging_port)
    process = start_managed_process(
        name="autoworkbench-backend",
        command=_backend_launch_command(),
        cwd=REPO_ROOT,
        artifact_dir=artifact_dir,
        stdout_name="backend.stdout.log",
        stderr_name="backend.stderr.log",
        env=env,
        port=backend_port,
    )
    assert process.port == backend_port
    assert process.base_url == f"http://127.0.0.1:{backend_port}"
    wait_for_http_url(f"{process.base_url}/docs", label="AutoWorkbench backend", process=process, timeout_s=20.0)
    return process


async def _import_playwright_async_api() -> Any:
    try:
        from playwright.async_api import async_playwright
    except ImportError as exc:  # pragma: no cover - skip path is exercised by runtime environment
        raise RuntimeError("playwright.async_api is required for the E2E harness") from exc
    return async_playwright


async def _wait_for_page(context: Any, target_url: str, timeout_ms: int) -> Any:
    deadline = time.monotonic() + timeout_ms / 1000
    last_seen_urls: list[str] = []
    while time.monotonic() < deadline:
        pages = list(getattr(context, "pages", []))
        for page in pages:
            current_url = getattr(page, "url", "")
            if current_url:
                last_seen_urls.append(current_url)
            if current_url.startswith(target_url):
                try:
                    await page.wait_for_load_state("domcontentloaded", timeout=5000)
                except Exception:
                    pass
                return page
        await asyncio.sleep(0.25)
    seen = ", ".join(last_seen_urls[-5:]) if last_seen_urls else "<no pages>"
    raise TimeoutError(f"Timed out waiting for browser page {target_url}. Seen: {seen}")


async def _wait_for_locator_text(locator: Any, expected_text: str, timeout_ms: int = 120000) -> str:
    deadline = time.monotonic() + timeout_ms / 1000
    last_text = ""
    while time.monotonic() < deadline:
        try:
            last_text = await locator.inner_text()
        except Exception as exc:  # noqa: BLE001
            last_text = f"<error: {exc}>"
        if expected_text in last_text:
            return last_text
        await asyncio.sleep(0.25)
    raise TimeoutError(f"Timed out waiting for text {expected_text!r}. Last text: {last_text!r}")


@dataclass
class E2ESession:
    artifact_dir: Path
    test_name: str
    run_id: str
    created_at: str
    static_server: ManagedProcess
    backend: ManagedProcess
    playwright: Any
    browser: Any
    context: Any
    page: Any
    console_entries: list[str]
    current_stage: str = "initialized"
    stage_history: list[str] = field(default_factory=list)
    failure_artifacts_captured: bool = False
    result_status: str = "unknown"
    result_error_summary: str | None = None
    failure_expected_event_type: str | None = None
    failure_observed_event_types: list[str] = field(default_factory=list)
    failure_event_evidence: dict[str, Any] | None = None
    failure_redaction_report: dict[str, Any] | None = None

    def log_stage_ok(self, stage: str) -> None:
        self.current_stage = stage
        self.stage_history.append(stage)
        print(f"[E2E_STAGE] {stage} ok")

    def _backend_log_text(self) -> str:
        return f"{self.backend.stdout_path.read_text(encoding='utf-8', errors='replace')}\n{self.backend.stderr_path.read_text(encoding='utf-8', errors='replace')}"

    def _backend_log_lines(self) -> list[str]:
        return self._backend_log_text().splitlines()

    def _backend_marker_lines(self, markers: list[str]) -> dict[str, str | None]:
        lines = self._backend_log_lines()
        return {marker: _detect_marker_line(lines, [marker]) for marker in markers}

    def _llm_activity(self) -> tuple[bool, str | None]:
        lines = self._backend_log_lines()
        marker_line = _detect_marker_line(lines, E2E_LLM_MARKERS)
        return marker_line is not None, marker_line

    async def find_autoworkbench_panel(self) -> Any:
        shadow_panel = self.page.locator("#aw-root").first
        try:
            if await shadow_panel.count() > 0:
                return shadow_panel
        except Exception:
            pass
        return self.page.locator("#autoworkbench-root .ide-panel").first

    async def _page_state(self) -> dict[str, Any]:
        current_url = getattr(self.page, "url", "")
        overlay_visible = False
        active_tab = ""
        active_mode = ""
        try:
            overlay_visible = bool(await (await self.find_autoworkbench_panel()).is_visible())
        except Exception:
            overlay_visible = False
        try:
            active_tab = (await self.page.locator(".ide-tab.active").first.inner_text()).strip()
        except Exception:
            active_tab = ""
        try:
            active_mode = (await self.page.locator(".ide-hd-state").first.inner_text()).strip()
        except Exception:
            active_mode = ""
        return {
            "current_url": current_url,
            "overlay_visible": overlay_visible,
            "active_tab": active_tab or None,
            "active_mode": active_mode or None,
        }

    async def save_failure_artifacts(
        self,
        reason: str,
        stage: str | None = None,
        *,
        expected_event_type: str | None = None,
        observed_event_types: Sequence[str] | None = None,
        event_evidence: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        if self.failure_artifacts_captured:
            return {}
        self.failure_artifacts_captured = True
        self.result_status = "failed"
        self.result_error_summary = reason
        stage_name = stage or self.current_stage
        normalized_observed_event_types = [str(event_type) for event_type in observed_event_types] if observed_event_types is not None else []
        stored_event_evidence = _build_failure_event_evidence(event_evidence, expected_event_type, normalized_observed_event_types)
        self.failure_expected_event_type = expected_event_type
        self.failure_observed_event_types = normalized_observed_event_types
        self.failure_event_evidence = stored_event_evidence
        ensure_directory(self.artifact_dir)
        backend_log_text = self._backend_log_text()
        backend_tail = tail_lines_text(backend_log_text, 30)
        frontend_tail = "\n".join(self.console_entries[-30:])
        llm_triggered, last_llm_marker = self._llm_activity()
        lifecycle_markers = self._backend_marker_lines(E2E_LIFECYCLE_MARKERS)
        page_state: dict[str, Any] = {}
        page_error: str | None = None
        try:
            page_state = await self._page_state()
        except Exception as exc:  # noqa: BLE001
            page_error = str(exc)
            page_state = {
                "current_url": getattr(self.page, "url", ""),
                "overlay_visible": False,
                "active_tab": None,
                "active_mode": None,
            }
        sanitized_page_state, page_state_findings = _redact_sensitive_value(page_state, location="page_state")
        sanitized_page_error = page_error
        page_error_findings: list[tuple[str, str]] = []
        if sanitized_page_error is not None:
            sanitized_page_error, page_error_findings = _redact_text_value(sanitized_page_error, location="page_error")
        sanitized_reason, _reason_findings = _redact_text_value(reason, location="failure_reason")
        failure_redaction_findings = []
        failure_redaction_findings.extend(_reason_findings)
        failure_redaction_findings.extend(page_state_findings)
        failure_redaction_findings.extend(page_error_findings)
        self.failure_redaction_report = _build_redaction_report(findings=failure_redaction_findings)
        context = {
            "artifact_dir": str(self.artifact_dir),
            "screenshot_path": str(self.artifact_dir / "failure.png"),
            "page_html_path": str(self.artifact_dir / "page.html"),
            "backend_tail_path": str(self.artifact_dir / "backend.tail.log"),
            "frontend_console_tail_path": str(self.artifact_dir / "frontend.console.tail.log"),
            "stage": stage_name,
            "reason": sanitized_reason,
            "expected_event_type": expected_event_type,
            "observed_event_types": normalized_observed_event_types,
            "event_evidence": stored_event_evidence,
            "page_state": sanitized_page_state,
            "page_error": sanitized_page_error,
            "llm_triggered": llm_triggered,
            "last_llm_marker": last_llm_marker,
            "backend_lifecycle_markers": lifecycle_markers,
            "stage_history": self.stage_history + [stage_name],
        }
        failure_text_lines = [
            f"stage={stage_name}",
            f"reason={sanitized_reason}",
            f"artifact_dir={self.artifact_dir}",
        ]
        if expected_event_type is not None:
            failure_text_lines.append(f"expected_event_type={expected_event_type}")
        if normalized_observed_event_types:
            failure_text_lines.append(f"observed_event_types={normalized_observed_event_types!r}")
        if stored_event_evidence is not None:
            failure_text_lines.append("event_evidence=")
            failure_text_lines.append(json.dumps(stored_event_evidence, indent=2, sort_keys=True))
        (self.artifact_dir / "failure.txt").write_text(
            "\n".join(failure_text_lines) + "\n",
            encoding="utf-8",
        )
        (self.artifact_dir / "failure-context.json").write_text(
            json.dumps(context, indent=2, sort_keys=True),
            encoding="utf-8",
        )
        (self.artifact_dir / "backend.tail.log").write_text(backend_tail, encoding="utf-8")
        (self.artifact_dir / "frontend.console.tail.log").write_text(frontend_tail, encoding="utf-8")
        try:
            await self.page.screenshot(path=str(self.artifact_dir / "failure.png"), full_page=True)
        except Exception as exc:  # noqa: BLE001
            (self.artifact_dir / "failure-screenshot-error.txt").write_text(str(exc), encoding="utf-8")
        try:
            page_html = await self.page.content()
            (self.artifact_dir / "page.html").write_text(page_html, encoding="utf-8")
        except Exception as exc:  # noqa: BLE001
            (self.artifact_dir / "page-html-error.txt").write_text(str(exc), encoding="utf-8")
        return context

    async def run_stage(self, stage: str, timeout_s: float, action: Callable[[], Awaitable[T]]) -> T:
        self.current_stage = stage
        try:
            result = await asyncio.wait_for(action(), timeout=timeout_s)
        except Exception as exc:  # noqa: BLE001
            context = await self.save_failure_artifacts(_compact_reason(exc), stage=stage)
            llm_triggered = str(context.get("llm_triggered", False)).lower()
            last_llm_marker = context.get("last_llm_marker") or "none"
            print(
                f"[E2E_STAGE] {stage} failed reason={_compact_reason(exc)} "
                f"llm_triggered={llm_triggered} last_llm_marker={last_llm_marker} artifact_dir={self.artifact_dir}"
            )
            raise
        else:
            self.log_stage_ok(stage)
            return result

    def write_console_log(self) -> None:
        ensure_directory(self.artifact_dir)
        (self.artifact_dir / "frontend.console.log").write_text(
            "\n".join(self.console_entries),
            encoding="utf-8",
        )

    def backend_logs(self) -> str:
        return f"{self.backend.stdout_path.read_text(encoding='utf-8', errors='replace')}\n{self.backend.stderr_path.read_text(encoding='utf-8', errors='replace')}"

    def _build_summary_markdown(self) -> str:
        stage_history = ", ".join(self.stage_history) if self.stage_history else "none"
        return (
            f"# {self.test_name}\n\n"
            f"- status: {self.result_status}\n"
            f"- artifact_dir: {self.artifact_dir}\n"
            f"- run_id: {self.run_id}\n"
            f"- created_at: {self.created_at}\n"
            f"- stage_history: {stage_history}\n"
        )

    async def close(self) -> None:
        self.write_console_log()
        self.backend.stop()
        self.static_server.stop()
        try:
            await self.browser.close()
        except Exception:
            pass
        try:
            await self.playwright.stop()
        except Exception:
            pass
        artifact_texts = {
            "backend.log": self.backend_logs(),
            "frontend.log": "\n".join(self.console_entries),
            "browser-console.log": "\n".join(self.console_entries),
            "summary.md": self._build_summary_markdown(),
        }
        finalize_test_result(
            artifact_dir=self.artifact_dir,
            test_name=self.test_name,
            status=self.result_status,
            error_summary=self.result_error_summary,
            created_at=self.created_at,
            artifact_texts=artifact_texts,
            optional_absence_notes=DEFAULT_E2E_OPTIONAL_ABSENCE_NOTES,
            event_evidence=self.failure_event_evidence,
            redaction_report=self.failure_redaction_report,
            run_id=self.run_id,
        )


def _capture_console(console_entries: list[str], page: Any) -> None:
    def on_console(message: Any) -> None:
        try:
            text = message.text
        except Exception:
            text = str(message)
        try:
            entry_type = message.type
        except Exception:
            entry_type = "log"
        console_entries.append(f"[console:{entry_type}] {text}")

    def on_page_error(error: Any) -> None:
        console_entries.append(f"[pageerror] {error}")

    def on_request_failed(request: Any) -> None:
        try:
            url = request.url
        except Exception:
            url = "<unknown>"
        try:
            failure = request.failure.error_text
        except Exception:
            failure = "request failed"
        console_entries.append(f"[requestfailed] {url} :: {failure}")

    page.on("console", on_console)
    page.on("pageerror", on_page_error)
    page.on("requestfailed", on_request_failed)


async def _connect_browser_page(remote_debugging_port: int, target_url: str) -> tuple[Any, Any, Any, Any]:
    async_playwright = await _import_playwright_async_api()
    playwright = await async_playwright().start()
    endpoint_url = f"http://127.0.0.1:{remote_debugging_port}"
    deadline = time.monotonic() + 20.0
    last_error: Exception | None = None
    while time.monotonic() < deadline:
        try:
            browser = await playwright.chromium.connect_over_cdp(endpoint_url)
            break
        except Exception as exc:  # noqa: BLE001
            last_error = exc
            await asyncio.sleep(0.25)
    else:
        await playwright.stop()
        raise RuntimeError(f"Timed out connecting to backend browser at {endpoint_url}: {last_error}")

    contexts = list(getattr(browser, "contexts", []))
    if not contexts:
        await browser.close()
        await playwright.stop()
        raise RuntimeError("No browser context available after CDP connection")

    context = contexts[0]
    page = await _wait_for_page(context, target_url, timeout_ms=15000)
    return playwright, browser, context, page


@asynccontextmanager
async def start_e2e_session(*, test_name: str, app_root: Path) -> AsyncIterator[E2ESession]:
    artifact_dir = create_run_artifact_dir(test_name)
    created_at = _utc_now_iso()
    run_id = artifact_dir.name
    write_artifact_manifest(
        artifact_dir=artifact_dir,
        test_name=test_name,
        status="running",
        created_at=created_at,
        optional_absence_notes=DEFAULT_E2E_OPTIONAL_ABSENCE_NOTES,
        run_id=run_id,
    )
    write_test_result(
        artifact_dir=artifact_dir,
        test_name=test_name,
        status="unknown",
        run_id=run_id,
    )
    static_server: ManagedProcess | None = None
    backend: ManagedProcess | None = None
    playwright: Any | None = None
    browser: Any | None = None
    context: Any | None = None
    page: Any | None = None
    session: E2ESession | None = None
    try:
        static_server = start_static_server(app_root, artifact_dir)
        start_url = f"{static_server.base_url}/index.html"
        backend_remote_debugging_port = resolve_e2e_port(
            None,
            env_name="AUTOWORKBENCH_E2E_REMOTE_DEBUGGING_PORT",
            default=DEFAULT_E2E_REMOTE_DEBUGGING_PORT,
        )
        backend = start_autoworkbench_backend(
            start_url=start_url,
            artifact_dir=artifact_dir,
            remote_debugging_port=backend_remote_debugging_port,
        )
        console_entries: list[str] = []
        playwright, browser, context, page = await _connect_browser_page(backend_remote_debugging_port, start_url)
        _capture_console(console_entries, page)
        session = E2ESession(
            artifact_dir=artifact_dir,
            test_name=test_name,
            run_id=run_id,
            created_at=created_at,
            static_server=static_server,
            backend=backend,
            playwright=playwright,
            browser=browser,
            context=context,
            page=page,
            console_entries=console_entries,
        )
        session.log_stage_ok("backend_started")
        session.log_stage_ok("websocket_connected")
        yield session
        session.result_status = "passed"
    except Exception as exc:
        if session is not None and not session.failure_artifacts_captured:
            await session.save_failure_artifacts(str(exc), stage=session.current_stage)
        elif session is None:
            finalize_test_result(
                artifact_dir=artifact_dir,
                test_name=test_name,
                status="failed",
                error_summary=_compact_reason(exc),
                created_at=created_at,
                run_id=run_id,
            )
        raise
    finally:
        if session is not None:
            await session.close()
        else:
            if browser is not None:
                try:
                    await browser.close()
                except Exception:
                    pass
            if playwright is not None:
                try:
                    await playwright.stop()
                except Exception:
                    pass
            if backend is not None:
                backend.stop()
            if static_server is not None:
                static_server.stop()


async def wait_for_overlay_ready(page: Any, timeout_ms: int = 10000) -> None:
    await wait_for_autoworkbench_ready(page, timeout_ms=timeout_ms)


_AUTOWORKBENCH_TAB_TEST_IDS = {
    "workbench": "llm-tab",
    "steps": "steps-tab",
    "code": "code-tab",
    "debug": "trace-tab",
}
_AUTOWORKBENCH_TAB_ROLE_NAMES = {
    "workbench": re.compile(r"^(?:llm|workbench)$", re.IGNORECASE),
    "steps": re.compile(r"^steps$", re.IGNORECASE),
    "code": re.compile(r"^code$", re.IGNORECASE),
    "debug": re.compile(r"^(?:trace|debug)$", re.IGNORECASE),
}
_AUTOWORKBENCH_TAB_ALIASES = {
    "llm": "workbench",
    "trace": "debug",
}


def _normalize_autoworkbench_tab_name(tab_name: str) -> str:
    normalized = str(tab_name).strip().lower()
    normalized = _AUTOWORKBENCH_TAB_ALIASES.get(normalized, normalized)
    if normalized not in _AUTOWORKBENCH_TAB_TEST_IDS:
        raise ValueError(f"Unknown AutoWorkbench tab {tab_name!r}")
    return normalized


async def click_autoworkbench_tab(page: Any, tab_name: str, timeout_ms: int = 10000) -> None:
    normalized = _normalize_autoworkbench_tab_name(tab_name)
    test_id = _AUTOWORKBENCH_TAB_TEST_IDS[normalized]
    role_name = _AUTOWORKBENCH_TAB_ROLE_NAMES[normalized]

    candidates: list[Any] = []
    get_by_test_id = getattr(page, "get_by_test_id", None)
    if callable(get_by_test_id):
        candidates.append(get_by_test_id(test_id).first)
    get_by_role = getattr(page, "get_by_role", None)
    if callable(get_by_role):
        candidates.append(get_by_role("button", name=role_name).first)

    last_error: Exception | None = None
    for candidate in candidates:
        try:
            await candidate.wait_for(state="visible", timeout=timeout_ms)
            await candidate.click(timeout=timeout_ms)
            return
        except Exception as exc:  # noqa: BLE001
            last_error = exc

    raise TimeoutError(f"Timed out waiting to click AutoWorkbench tab {tab_name!r}") from last_error


async def wait_for_locator_text(locator: Any, expected_text: str, timeout_ms: int = 10000) -> None:
    await locator.wait_for(state="visible", timeout=timeout_ms)
    expected = expected_text.lower()
    deadline = asyncio.get_running_loop().time() + timeout_ms / 1000
    while True:
        current = (await locator.inner_text()).strip().lower()
        if expected in current:
            return
        if asyncio.get_running_loop().time() >= deadline:
            raise TimeoutError(f"Timed out waiting for text {expected_text!r}")
        await asyncio.sleep(0.1)


async def wait_for_autoworkbench_ready(page: Any, timeout_ms: int = 10000) -> None:
    await page.locator("#autoworkbench-root").wait_for(state="attached", timeout=timeout_ms)
    panel = page.locator("#aw-root").first
    try:
        if await panel.count() > 0:
            await panel.wait_for(state="visible", timeout=timeout_ms)
        else:
            await page.locator("#autoworkbench-root .ide-panel").first.wait_for(state="visible", timeout=timeout_ms)
    except Exception:
        await page.locator("#autoworkbench-root .ide-panel").first.wait_for(state="visible", timeout=timeout_ms)
    await page.get_by_role("button", name="Run Pending Steps").first.wait_for(state="visible", timeout=timeout_ms)


async def wait_for_agents_page(page: Any, timeout_ms: int = 15000) -> None:
    await page.wait_for_url("**/agents.html", timeout=timeout_ms)
    await page.get_by_role("heading", name="Playwright Test Agents").wait_for(state="visible", timeout=timeout_ms)
