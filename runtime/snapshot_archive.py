from __future__ import annotations

"""Focused facade for snapshot/archive APIs extracted from AgentLoop seams."""

from runtime.spec_snapshot import build_spec_snapshot, load_snapshot_archive, load_spec_snapshot

__all__ = [
    "build_spec_snapshot",
    "load_snapshot_archive",
    "load_spec_snapshot",
]
