"""
runtime/recommendation_events.py

Typed events for recommendation review lifecycle.

Source rule: S6-0305 — page_analysis_requested, page_summary_ready,
validation_recommendations_ready, accept/remove/reorder commands,
review_completed. Events are immutable records.

Modularization rule: policy logic in focused runtime/ modules, not agent.py.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass(frozen=True)
class PageAnalysisRequested:
    request_id: str
    page_url: str
    selected_section: Optional[str] = None


@dataclass(frozen=True)
class PageSummaryReady:
    request_id: str
    page_intelligence_summary: Any  # dict
    timestamp: str


@dataclass(frozen=True)
class RecommendationReady:
    request_id: str
    recommendations: Any  # PageValidationRecommenderOutput
    timestamp: str


# Alias
ValidationRecommendationsReady = RecommendationReady


@dataclass(frozen=True)
class AcceptRecommendationCommand:
    request_id: str
    recommendation_ids: tuple[str, ...] | list[str]


@dataclass(frozen=True)
class RemoveRecommendationCommand:
    request_id: str
    recommendation_ids: tuple[str, ...] | list[str]


@dataclass(frozen=True)
class ReorderRecommendationCommand:
    request_id: str
    recommendation_ids: tuple[str, ...] | list[str]


@dataclass(frozen=True)
class RecommendationReviewCompleted:
    request_id: str
    accepted_recommendation_ids: tuple[str, ...] | list[str]
    timestamp: str
