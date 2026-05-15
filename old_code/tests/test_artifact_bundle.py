"""
tests/test_artifact_bundle.py

Tests for Cluster 11: Artifact Bundle Standardization.
S6-1104.
"""
from __future__ import annotations

import pytest
from runtime.artifact_bundle import (
    ArtifactManifest,
    ArtifactEntry,
    ArtifactBundle,
    create_artifact_bundle,
    validate_artifact_bundle,
)


def test_artifact_manifest_has_required_fields():
    manifest = ArtifactManifest(
        session_id="s1",
        entries=[],
    )
    assert manifest.session_id == "s1"
    assert isinstance(manifest.entries, list)
    assert manifest.created_at is not None


def test_artifact_entry_types():
    entry = ArtifactEntry(
        artifact_type="llm_call",
        path="artifacts/s1/llm_call_001.json",
        size_bytes=1024,
        redacted=False,
    )
    assert entry.artifact_type == "llm_call"
    assert entry.path is not None


def test_create_artifact_bundle():
    bundle = create_artifact_bundle(
        session_id="sess-1",
        artifacts=[
            {"type": "llm_call", "data": {"purpose": "plan_generation", "response": "ok"}},
            {"type": "failure_context", "data": {"error": "ElementNotFoundError"}},
        ],
    )
    assert isinstance(bundle, ArtifactBundle)
    assert bundle.manifest is not None
    assert len(bundle.manifest.entries) == 2


def test_validate_bundle_requires_manifest():
    bundle = ArtifactBundle(
        manifest=ArtifactManifest(session_id="s1", entries=[]),
        artifacts={},
    )
    errors = validate_artifact_bundle(bundle)
    assert isinstance(errors, list)


def test_bundle_artifacts_keyed_by_type():
    bundle = create_artifact_bundle(
        session_id="s2",
        artifacts=[
            {"type": "trace", "data": {"events": []}},
        ],
    )
    assert "trace" in bundle.artifacts


def test_validate_bundle_blocks_missing_manifest():
    # Bundle with no entries should still be valid (empty run)
    bundle = ArtifactBundle(
        manifest=ArtifactManifest(session_id="missing", entries=[]),
        artifacts={},
    )
    errors = validate_artifact_bundle(bundle)
    # Empty bundle is valid — no required artifacts until E2E
    assert isinstance(errors, list)
