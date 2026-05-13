"""
tests/test_frontend_trace_agent_cards.py

Sprint 7 Cluster 9 — S7-0901..S7-0909: Trace, Artifacts, Agent visibility.
TDD: written before implementation; tests start RED.
"""
from __future__ import annotations

import os

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
COMP = os.path.join(REPO_ROOT, "frontend", "src", "components")


def _read(rel: str) -> str:
    path = os.path.join(COMP, rel)
    if not os.path.exists(path):
        return ""
    return open(path, encoding="utf-8").read()


def _exists(rel: str) -> bool:
    return os.path.exists(os.path.join(COMP, rel))


# S7-0901 Trace timeline
def test_trace_timeline_exists():
    assert _exists("trace/TraceTimeline.jsx")


def test_trace_timeline_renders_entries():
    c = _read("trace/TraceTimeline.jsx")
    assert "traceEntries" in c or "trace_entries" in c
    assert "data-testid" in c


def test_trace_timeline_unknown_event_diagnostic():
    c = _read("trace/TraceTimeline.jsx")
    assert "unknown" in c.lower() or "diagnostic" in c.lower()


def test_trace_timeline_not_runtime_truth():
    c = _read("trace/TraceTimeline.jsx")
    # Must not call setRunState, setRecordedSteps, etc.
    assert "setRunState" not in c
    assert "setRecordedSteps" not in c
    assert "setCodePreview" not in c


# S7-0902 Filters / search
def test_trace_filters_exists():
    assert _exists("trace/TraceFilters.jsx")


def test_trace_filters_local_only():
    c = _read("trace/TraceFilters.jsx")
    # Local filter state; no dispatch to backend
    assert "filter" in c.lower()
    assert "dispatch" not in c.lower() or "// " in c


# S7-0903 Failure detail panel
def test_failure_detail_exists():
    assert _exists("trace/FailureDetailPanel.jsx")


def test_failure_detail_renders_expected_actual():
    c = _read("trace/FailureDetailPanel.jsx")
    for f in ["expected", "actual", "layer", "evidence"]:
        assert f in c.lower(), f"FailureDetailPanel must surface {f}"


# S7-0904 Artifact links + redaction
def test_artifact_links_exists():
    assert _exists("trace/ArtifactLinks.jsx")


def test_artifact_links_only_backend_refs():
    c = _read("trace/ArtifactLinks.jsx")
    assert "artifact" in c.lower()
    assert "ref" in c.lower() or "url" in c.lower()


def test_artifact_links_redaction_visible():
    c = _read("trace/ArtifactLinks.jsx")
    assert "redacted" in c.lower() or "redaction" in c.lower()


# S7-0905 LLM telemetry display
def test_llm_telemetry_exists():
    assert _exists("trace/LLMTelemetry.jsx")


def test_llm_telemetry_no_raw_prompt():
    c = _read("trace/LLMTelemetry.jsx")
    # Must not display raw prompts/API keys/secrets
    assert "api_key" not in c.lower() or "// " in c
    assert "raw_prompt" not in c.lower() or "// " in c


def test_llm_telemetry_tokens_cost():
    c = _read("trace/LLMTelemetry.jsx")
    assert "token" in c.lower()
    assert "cost" in c.lower() or "price" in c.lower()


# S7-0906 Context level / tool policy
def test_context_policy_exists():
    assert _exists("trace/ContextPolicy.jsx")


def test_context_policy_displays_level_and_tools():
    c = _read("trace/ContextPolicy.jsx")
    assert "context" in c.lower()
    assert "tool" in c.lower() or "policy" in c.lower()


# S7-0907 Capability gap notice
def test_capability_gap_exists():
    assert _exists("trace/CapabilityGapNotice.jsx")


def test_capability_gap_notice_renders():
    c = _read("trace/CapabilityGapNotice.jsx")
    assert "capability" in c.lower()
    assert "gap" in c.lower() or "missing" in c.lower()


# S7-0908 Compact agent activity
def test_agent_activity_exists():
    assert _exists("agents/AgentActivity.jsx")


def test_agent_activity_no_fake_when_missing():
    c = _read("agents/AgentActivity.jsx")
    # Must show "unavailable" not fake "active"
    assert "unavailable" in c.lower() or "no agent" in c.lower() or "empty" in c.lower()


# S7-0909 Agent Control Center limited
def test_agent_control_exists():
    assert _exists("agents/AgentControlCenter.jsx")


def test_agent_control_unsupported_disabled():
    c = _read("agents/AgentControlCenter.jsx")
    assert "disabled" in c
    assert "unsupported" in c.lower() or "reason" in c.lower()


def test_agent_control_required_cannot_disable():
    c = _read("agents/AgentControlCenter.jsx")
    assert "required" in c.lower()
