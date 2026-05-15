"""
runtime/recommendation_contracts.py

Schema contracts for page validation recommendations.

Source rule: S6-0304 — recommendations grouped by section, stable IDs,
priority classification, capability status, no execution.

Modularization rule: policy logic in focused runtime/ modules, not agent.py.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class ValidationRecommendation:
    id: str
    recommendation_type: str          # "assertion" | "action" | "check"
    assertion_type: Optional[str]     # "text_content" | "visibility" | "attribute" | etc.
    action_type: Optional[str]        # "click" | "fill" | "submit" | etc.
    section_id: str
    description: str
    locator_hint: str                 # advisory only, not final
    expected_value: Optional[str]
    priority: str                     # "critical" | "useful" | "optional"
    confidence: float                 # 0–1
    capability_status: str            # "supported" | "capability_gap" | "warning"


@dataclass
class ValidationRecommendationGroup:
    section_id: str
    section_name: str
    recommendations: list[ValidationRecommendation] = field(default_factory=list)
    ambiguities: list[Any] = field(default_factory=list)


@dataclass
class PageValidationRecommenderOutput:
    groups: list[ValidationRecommendationGroup]
    total_recommendations: int
    critical_count: int
    capability_gaps: list[Any]
    warnings: list[Any]
