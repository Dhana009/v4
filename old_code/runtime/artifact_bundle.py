"""
runtime/artifact_bundle.py

Artifact bundle standardization.

Source rule: S6-1104.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


@dataclass
class ArtifactEntry:
    artifact_type: str
    path: str
    size_bytes: int = 0
    redacted: bool = False


@dataclass
class ArtifactManifest:
    session_id: str
    entries: list[ArtifactEntry] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


@dataclass
class ArtifactBundle:
    manifest: ArtifactManifest
    artifacts: dict[str, Any] = field(default_factory=dict)


def create_artifact_bundle(
    session_id: str,
    artifacts: list[dict[str, Any]],
) -> ArtifactBundle:
    entries: list[ArtifactEntry] = []
    artifact_map: dict[str, Any] = {}

    for item in artifacts:
        art_type = item.get("type", "unknown")
        data = item.get("data", {})
        path = f"artifacts/{session_id}/{art_type}.json"
        entries.append(ArtifactEntry(artifact_type=art_type, path=path))
        artifact_map[art_type] = data

    manifest = ArtifactManifest(session_id=session_id, entries=entries)
    return ArtifactBundle(manifest=manifest, artifacts=artifact_map)


def validate_artifact_bundle(bundle: ArtifactBundle) -> list[str]:
    """Return list of validation errors (empty = valid)."""
    errors: list[str] = []
    if bundle.manifest is None:
        errors.append("missing manifest")
    return errors
