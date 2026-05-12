"""
runtime/capability_registry.py

Capability registry framework for action/assertion baseline.

Source rule: S6-0703/0704 — capability registry, action/assertion baseline,
capability_gap for unsupported operations.
"""
from __future__ import annotations

import enum
from dataclasses import dataclass, field


class CapabilityStatus(enum.Enum):
    SUPPORTED = "supported"
    CAPABILITY_GAP = "capability_gap"
    WARNING = "warning"


BASELINE_CAPABILITIES: frozenset[str] = frozenset({
    # Actions
    "click", "fill", "select", "hover", "scroll", "navigate",
    "upload_file", "submit", "clear",
    # Assertions
    "assert_text", "assert_visibility", "assert_attribute", "assert_count",
    "assert_url", "assert_title", "assert_enabled", "assert_checked",
    "assert_value",
    # Special
    "screenshot", "wait_for_element", "wait_for_navigation",
})


@dataclass
class CapabilityRegistry:
    capabilities: frozenset[str] = field(default_factory=lambda: BASELINE_CAPABILITIES)

    def is_supported(self, capability: str) -> bool:
        return capability.lower() in self.capabilities


_DEFAULT_REGISTRY = CapabilityRegistry()


def get_capability_status(capability: str) -> CapabilityStatus:
    """Return capability status for *capability*."""
    if _DEFAULT_REGISTRY.is_supported(capability):
        return CapabilityStatus.SUPPORTED
    return CapabilityStatus.CAPABILITY_GAP
