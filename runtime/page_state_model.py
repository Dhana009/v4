"""
runtime/page_state_model.py

Page-state dependency model and wrong-page precondition flow.

Source rule: S6-0406/S6-0407 — each step has required page state.
Wrong-page precondition blocks step execution. Dependency tracked explicitly.
"""
from __future__ import annotations

import fnmatch
import re
from dataclasses import dataclass, field
from typing import Any


@dataclass
class PageStateDependency:
    step_id: str
    required_page: str
    current_page: str
    satisfied: bool


@dataclass
class PreconditionCheckResult:
    step_id: str
    blocked: bool
    reason: str | None


def check_page_precondition(step: Any, current_page: str) -> PreconditionCheckResult:
    """Check if current page satisfies the step's required page.

    Returns PreconditionCheckResult with blocked=True if wrong page.
    """
    required = getattr(step, "page_required", None)
    if required and required != current_page:
        return PreconditionCheckResult(
            step_id=step.step_id,
            blocked=True,
            reason=f"Step requires page '{required}' but current page is '{current_page}'",
        )
    return PreconditionCheckResult(
        step_id=step.step_id,
        blocked=False,
        reason=None,
    )


_PRECONDITION_TYPES = (
    "url_mismatch",
    "title_mismatch",
    "element_missing",
    "element_forbidden_present",
    "page_state_mismatch",
)


@dataclass(frozen=True)
class PageStateRequirement:
    url_glob: str | None = None
    path_regex: str | None = None
    title_regex: str | None = None
    must_contain_elements: list[str] = field(default_factory=list)
    forbidden_elements: list[str] = field(default_factory=list)


@dataclass
class PageStateObservation:
    url: str
    title: str
    present_elements: list[str] = field(default_factory=list)
    absent_elements: list[str] = field(default_factory=list)


def _extract_path(url: str) -> str:
    s = url.split("://", 1)[-1]
    i = s.find("/")
    if i < 0:
        return "/"
    p = s[i:]
    for sep in ("?", "#"):
        j = p.find(sep)
        if j >= 0:
            p = p[:j]
    return p


def evaluate_precondition(req: PageStateRequirement, obs: PageStateObservation) -> tuple[bool, list[str]]:
    """Evaluate precondition requirement against an observation."""
    reasons: list[str] = []
    if req.url_glob is not None and not fnmatch.fnmatch(obs.url, req.url_glob):
        reasons.append(f"url_glob {req.url_glob} did not match observed {obs.url}")
    if req.path_regex is not None:
        path = _extract_path(obs.url)
        if not re.search(req.path_regex, path):
            reasons.append(f"path_regex /{req.path_regex}/ did not match observed {path}")
    if req.title_regex is not None and not re.search(req.title_regex, obs.title):
        reasons.append(f"title_regex /{req.title_regex}/ did not match observed title {obs.title!r}")
    for el in req.must_contain_elements:
        if el not in obs.present_elements:
            reasons.append(f"element_missing: required element {el!r} not present")
    for el in req.forbidden_elements:
        if el in obs.present_elements:
            reasons.append(f"element_forbidden_present: forbidden element {el!r} is present")
    return (not reasons, reasons)


def evaluate_postcondition(
    req: PageStateRequirement,
    before: PageStateObservation,
    after: PageStateObservation,
) -> tuple[bool, list[str]]:
    """Evaluate postcondition: requirement holds on `after` and required deltas occurred."""
    ok_after, reasons = evaluate_precondition(req, after)
    for el in req.must_contain_elements:
        if el in before.present_elements and el in after.present_elements:
            reasons.append(f"element_missing: required element {el!r} did not transition to present (already present before)")
    for el in req.forbidden_elements:
        if el in before.present_elements and el in after.present_elements:
            reasons.append(f"element_forbidden_present: forbidden element {el!r} still present after action")
    return (not reasons, reasons)


def classify_precondition_mismatch(reasons: list[str]) -> str:
    """Classify a list of failure reasons into a single precondition mismatch type."""
    joined = " ".join(reasons).lower()
    if "url_glob" in joined or "path_regex" in joined:
        return "url_mismatch"
    if "title_regex" in joined:
        return "title_mismatch"
    if "element_forbidden_present" in joined:
        return "element_forbidden_present"
    if "element_missing" in joined:
        return "element_missing"
    return "page_state_mismatch"


def build_page_state_dependency(step_id: str, required_state: PageStateRequirement) -> dict:
    """Serialize a step's required page state into a plan-builder dependency dict."""
    return {
        "step_id": step_id,
        "required_page_state": {
            "url_glob": required_state.url_glob,
            "path_regex": required_state.path_regex,
            "title_regex": required_state.title_regex,
            "must_contain_elements": list(required_state.must_contain_elements),
            "forbidden_elements": list(required_state.forbidden_elements),
        },
    }
