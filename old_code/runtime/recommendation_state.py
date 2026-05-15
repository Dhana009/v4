"""
runtime/recommendation_state.py

Recommendation review state machine.

Source rule: S6-0305 — state transitions: requested → summary_ready →
recommendations_ready → reviewing → completed.
Unaccepted recommendations never execute. IDs stable across reorder.

Modularization rule: policy logic in focused runtime/ modules, not agent.py.
"""
from __future__ import annotations

import enum
from typing import Any


class RecommendationStatus(enum.IntEnum):
    REQUESTED = 0
    SUMMARY_READY = 1
    RECOMMENDATIONS_READY = 2
    REVIEWING = 3
    COMPLETED = 4


class RecommendationReviewState:
    """Mutable state for one recommendation review session."""

    def __init__(self, request_id: str, page_url: str) -> None:
        self.request_id = request_id
        self.page_url = page_url
        self.page_summary: Any = None
        self.all_recommendations: Any = None
        self.accepted_ids: set[str] = set()
        self.removed_ids: set[str] = set()
        self.current_order: list[str] = []
        self.status = RecommendationStatus.REQUESTED

    def set_summary(self, page_summary: Any) -> None:
        self.page_summary = page_summary
        self.status = RecommendationStatus.SUMMARY_READY

    def set_recommendations(self, recommendations: Any) -> None:
        self.all_recommendations = recommendations
        # Build initial order from all recs
        from runtime.recommendation_contracts import PageValidationRecommenderOutput
        if isinstance(recommendations, PageValidationRecommenderOutput):
            self.current_order = [
                r.id
                for g in recommendations.groups
                for r in g.recommendations
            ]
        self.status = RecommendationStatus.RECOMMENDATIONS_READY

    def accept(self, ids: list[str]) -> None:
        self.accepted_ids.update(ids)
        if self.status in (RecommendationStatus.RECOMMENDATIONS_READY, RecommendationStatus.REVIEWING):
            self.status = RecommendationStatus.REVIEWING

    def remove(self, ids: list[str]) -> None:
        self.removed_ids.update(ids)
        self.accepted_ids -= set(ids)

    def reorder(self, new_order: list[str]) -> None:
        """Reorder recommendations — IDs are stable, only order changes."""
        self.current_order = list(new_order)

    def complete(self) -> None:
        self.status = RecommendationStatus.COMPLETED

    def get_accepted_ids(self) -> list[str]:
        return [rid for rid in self.current_order if rid in self.accepted_ids]
