from __future__ import annotations

from copy import deepcopy
from importlib import import_module, util as importlib_util
from inspect import signature
from types import ModuleType
from typing import Any, Callable

import pytest

from agent import AgentLoop
from runtime.recovery_manager import classify_failure

FUTURE_DOM_CONTRACT_MODULES = (
    "runtime.dom_snapshot",
    "runtime.dom_locator_contract",
    "runtime.dom_locator",
    "runtime.locator_contract",
)


def _make_agent_loop() -> AgentLoop:
    return AgentLoop.__new__(AgentLoop)


def _find_future_dom_contract_module() -> ModuleType:
    for module_name in FUTURE_DOM_CONTRACT_MODULES:
        if importlib_util.find_spec(module_name) is None:
            continue
        return import_module(module_name)

    pytest.xfail(
        "future DOM/locator seam missing; expected one of "
        + ", ".join(FUTURE_DOM_CONTRACT_MODULES)
        + " for DOM-001..DOM-005 tests-first slice"
    )


def _load_contract_callable(module: ModuleType, names: tuple[str, ...]) -> Callable[..., Any]:
    for name in names:
        candidate = getattr(module, name, None)
        if callable(candidate):
            return candidate

    available_exports = sorted(name for name in dir(module) if not name.startswith("_"))
    pytest.xfail(
        f"{module.__name__} is missing required DOM contract callable(s) {names}; "
        f"available exports: {', '.join(available_exports[:20]) or 'none'}"
    )


def _call_contract(fn: Callable[..., Any], payload: dict[str, Any]) -> Any:
    params = signature(fn).parameters
    call_kwargs = {name: value for name, value in payload.items() if name in params}
    if call_kwargs or any(param.kind == param.VAR_KEYWORD for param in params.values()):
        return fn(**call_kwargs)
    pytest.xfail(
        f"{getattr(fn, '__module__', 'unknown')}.{getattr(fn, '__name__', 'callable')} "
        "has an incompatible signature for the DOM contract test payload"
    )


def test_dom_002_selected_candidate_resolution_merges_selected_candidate_metadata_without_mutating_input() -> None:
    raw = {
        "tag": "span",
        "text": "outer text",
        "attributes": {"data-testid": "outer"},
        "candidates": [
            {
                "tag": "span",
                "text": "nested text",
                "role": "presentation",
                "ariaLabel": "nested aria",
                "selectorHint": ".nested",
                "locatorHint": 'text="nested"',
                "attributes": {
                    "id": "nested-id",
                    "class": "nested class",
                    "data-testid": "nested-testid",
                },
            },
            {
                "tag": "button",
                "cleanText": "Submit",
                "role": "button",
                "ariaLabel": "Submit form",
                "semanticType": "action_target",
                "selectorHint": "button.primary",
                "locatorHint": 'get_by_role("button", name="Submit")',
                "attributes": {
                    "id": "submit-id",
                    "class": "btn primary",
                    "data-testid": "submit-testid",
                },
            },
        ],
        "selected_candidate_index": 1,
    }
    before = deepcopy(raw)

    resolved = _make_agent_loop()._resolve_selected_element_info(raw)

    assert raw == before
    assert resolved["selected_candidate_index"] == 1
    assert resolved["tag"] == "button"
    assert resolved["id"] == "submit-id"
    assert resolved["class"] == "btn primary"
    assert resolved["className"] == "btn primary"
    assert resolved["text"] == "Submit"
    assert resolved["clean_text"] == "Submit"
    assert resolved["cleanText"] == "Submit"
    assert resolved["role"] == "button"
    assert resolved["ariaLabel"] == "Submit form"
    assert resolved["aria_label"] == "Submit form"
    assert resolved["semantic_type"] == "action_target"
    assert resolved["semanticType"] == "action_target"
    assert resolved["selector_hint"] == "button.primary"
    assert resolved["selectorHint"] == "button.primary"
    assert resolved["locator_hint"] == 'get_by_role("button", name="Submit")'
    assert resolved["locatorHint"] == 'get_by_role("button", name="Submit")'
    assert resolved["attributes"]["id"] == "submit-id"
    assert resolved["candidates"] is not raw["candidates"]
    assert len(resolved["candidates"]) == 2


def test_dom_002_selected_candidate_resolution_defaults_to_first_candidate_when_index_is_invalid() -> None:
    raw = {
        "candidates": [
            {
                "tag": "span",
                "cleanText": "nested text",
                "attributes": {"id": "nested-id"},
            },
            {
                "tag": "button",
                "cleanText": "Submit",
                "attributes": {"id": "submit-id", "class": "btn primary"},
            },
        ],
        "selected_candidate_index": "99",
    }
    before = deepcopy(raw)

    resolved = _make_agent_loop()._resolve_selected_element_info(raw)

    assert raw == before
    assert resolved["selected_candidate_index"] == 0
    assert resolved["tag"] == "span"
    assert resolved["id"] == "nested-id"
    assert resolved["text"] == "nested text"
    assert resolved["clean_text"] == "nested text"
    assert resolved["cleanText"] == "nested text"
    assert resolved["attributes"] == {"id": "nested-id"}


def test_dom_004_locator_validate_invalid_remains_advisory_and_does_not_recover() -> None:
    decision = classify_failure(
        "locator_validate",
        step_id="step-1",
        result={"valid": False, "count": 0},
    )

    assert decision.outcome == "skip"
    assert decision.stop_batch is False
    assert decision.purge_step_id is None
    assert decision.clear_last_successful_action is False
    assert decision.clear_step_success_history is False
    assert decision.clear_last_action_context is False
    assert decision.next_phase is None
    assert decision.requires_replan is False
    assert decision.reason == "locator_validate invalid remains advisory in v1"


def test_dom_001_page_snapshot_contract_is_structured_and_excludes_internal_controls() -> None:
    contract_module = _find_future_dom_contract_module()
    build_page_snapshot = _load_contract_callable(
        contract_module,
        ("build_page_snapshot", "dom_snapshot", "snapshot_page", "build_dom_snapshot"),
    )

    html = """
    <html>
      <head><title>Products</title></head>
      <body>
        <div data-testid="aw-panel-toggle">Internal control</div>
        <header><h1>Products</h1></header>
        <main>
          <section aria-label="Featured products">
            <button data-testid="buy-now">Buy now</button>
            <button data-aw-internal-control="true">Debug overlay</button>
          </section>
        </main>
      </body>
    </html>
    """
    snapshot = _call_contract(
        build_page_snapshot,
        {
            "html": html,
            "url": "https://example.test/products",
            "title": "Products",
            "scope": "full_page",
            "captured_at": "2026-05-07T01:02:03Z",
        },
    )

    assert isinstance(snapshot, dict)
    assert snapshot.get("url") == "https://example.test/products"
    assert snapshot.get("title") == "Products"
    timestamp = snapshot.get("captured_at") or snapshot.get("timestamp")
    if timestamp is None and isinstance(snapshot.get("metadata"), dict):
        metadata = snapshot["metadata"]
        timestamp = metadata.get("captured_at") or metadata.get("timestamp")
    assert timestamp is not None

    sections = snapshot.get("sections") or snapshot.get("landmarks")
    assert isinstance(sections, list)
    assert sections
    assert any(
        isinstance(section, dict)
        and "featured products" in str(section.get("name") or section.get("label") or section.get("title") or "").lower()
        for section in sections
    )

    interactive_elements = snapshot.get("interactive_elements")
    assert isinstance(interactive_elements, list)
    assert interactive_elements
    assert all(isinstance(element, dict) for element in interactive_elements)
    assert any(
        (element.get("role") == "button" or element.get("tag") == "button")
        and "buy" in str(element.get("name") or element.get("text") or "").lower()
        for element in interactive_elements
    )
    assert not any(
        "debug overlay" in str(element.get("name") or element.get("text") or "").lower()
        or "aw-panel-toggle" in str(element.get("candidate_id") or element.get("element_id") or element.get("selector") or "")
        for element in interactive_elements
    )

    raw_dom = snapshot.get("raw_dom")
    assert raw_dom is None or len(str(raw_dom)) < 4096
    warnings = snapshot.get("extraction_warnings")
    assert warnings is None or isinstance(warnings, list)


def test_dom_002_element_candidate_contract_distinguishes_target_text_from_expected_value_and_keeps_scope_metadata() -> None:
    contract_module = _find_future_dom_contract_module()
    build_element_candidate = _load_contract_callable(
        contract_module,
        ("build_element_candidate", "make_element_candidate", "normalize_candidate", "extract_element_candidate"),
    )

    action_candidate = _call_contract(
        build_element_candidate,
        {
            "candidate_id": "candidate-buy-now",
            "element_id": "submit-id",
            "element_ref": "frame-1#submit-id",
            "candidate_type": "action_target",
            "role": "button",
            "accessible_name": "Buy now",
            "text": "Buy now",
            "target_text": "Buy now",
            "expected_value": None,
            "label": None,
            "placeholder": None,
            "alt": None,
            "title": None,
            "data_testid": "buy-now",
            "selector": "get_by_role('button', name='Buy now')",
            "source": "picker",
            "scope": "section:Featured products",
            "ancestor_chain": ["section:Featured products", "main"],
            "locator_candidates": [
                {"strategy": "role+name", "locator": "get_by_role('button', name='Buy now')"}
            ],
            "risk_flags": ["duplicate_in_page"],
        },
    )

    assertion_candidate = _call_contract(
        build_element_candidate,
        {
            "candidate_id": "candidate-status-ready",
            "element_id": "status-id",
            "element_ref": "main#status-id",
            "candidate_type": "assertion_target",
            "role": "status",
            "accessible_name": "Delivery status",
            "text": "Ready",
            "target_text": "Ready",
            "expected_value": "Delivered",
            "label": None,
            "placeholder": None,
            "alt": None,
            "title": None,
            "data_testid": "delivery-status",
            "selector": "get_by_text('Ready', exact=True)",
            "source": "dom_snapshot",
            "scope": "section:Order summary",
            "ancestor_chain": ["section:Order summary", "main"],
            "locator_candidates": [
                {"strategy": "scoped_text", "locator": "text='Ready'"},
            ],
            "risk_flags": ["assertion_value_separate_from_target_text"],
        },
    )

    assert action_candidate["candidate_id"] == "candidate-buy-now"
    assert action_candidate["element_id"] == "submit-id"
    assert action_candidate["element_ref"] == "frame-1#submit-id"
    assert action_candidate["candidate_type"] == "action_target"
    assert action_candidate["role"] == "button"
    assert action_candidate["accessible_name"] == "Buy now"
    assert action_candidate["text"] == "Buy now"
    assert action_candidate["target_text"] == "Buy now"
    assert action_candidate["expected_value"] is None
    assert action_candidate["data_testid"] == "buy-now"
    assert action_candidate["selector"] == "get_by_role('button', name='Buy now')"
    assert action_candidate["source"] == "picker"
    assert action_candidate["scope"] == "section:Featured products"
    assert action_candidate["ancestor_chain"] == ["section:Featured products", "main"]
    assert isinstance(action_candidate["locator_candidates"], list)
    assert action_candidate["locator_candidates"][0]["strategy"] == "role+name"
    assert "duplicate_in_page" in action_candidate["risk_flags"]

    assert assertion_candidate["candidate_id"] == "candidate-status-ready"
    assert assertion_candidate["candidate_type"] == "assertion_target"
    assert assertion_candidate["text"] == "Ready"
    assert assertion_candidate["target_text"] == "Ready"
    assert assertion_candidate["expected_value"] == "Delivered"
    assert assertion_candidate["scope"] == "section:Order summary"
    assert assertion_candidate["ancestor_chain"] == ["section:Order summary", "main"]
    assert "assertion_value_separate_from_target_text" in assertion_candidate["risk_flags"]


def test_dom_003_locator_ranking_contract_prefers_semantic_candidates_before_css_xpath_and_fragile_nth_locators() -> None:
    contract_module = _find_future_dom_contract_module()
    rank_locator_candidates = _load_contract_callable(
        contract_module,
        ("rank_locator_candidates", "rank_candidates", "sort_locator_candidates", "order_locator_candidates"),
    )

    candidates = [
        {"candidate_id": "testid", "strategy": "data-testid", "risk_flags": ["stable"]},
        {"candidate_id": "role", "strategy": "role+name", "risk_flags": ["stable"]},
        {"candidate_id": "label", "strategy": "label", "risk_flags": ["stable"]},
        {"candidate_id": "placeholder", "strategy": "placeholder", "risk_flags": ["fallback"]},
        {"candidate_id": "alt-title", "strategy": "alt/title", "risk_flags": ["fallback"]},
        {"candidate_id": "scoped-text", "strategy": "scoped_text", "risk_flags": ["duplicate_safe"]},
        {"candidate_id": "section", "strategy": "section_scope", "risk_flags": ["section_scoped"]},
        {"candidate_id": "id", "strategy": "stable_id", "risk_flags": ["stable"]},
        {"candidate_id": "css", "strategy": "scoped_css", "risk_flags": ["brittle_but_acceptable"]},
        {"candidate_id": "generated-class", "strategy": "css", "risk_flags": ["generated_class"]},
        {"candidate_id": "xpath", "strategy": "xpath", "risk_flags": ["last_resort"]},
        {"candidate_id": "nth", "strategy": "nth", "risk_flags": ["fragile_last_resort"]},
    ]
    ranked = _call_contract(rank_locator_candidates, {"candidates": candidates, "target_text": "Submit"})

    assert isinstance(ranked, list)
    ranked_ids = [candidate["candidate_id"] for candidate in ranked]
    assert ranked_ids[0] == "testid"
    assert ranked_ids.index("role") < ranked_ids.index("css")
    assert ranked_ids.index("label") < ranked_ids.index("css")
    assert ranked_ids.index("placeholder") < ranked_ids.index("css")
    assert ranked_ids.index("alt-title") < ranked_ids.index("css")
    assert ranked_ids.index("scoped-text") < ranked_ids.index("css")
    assert ranked_ids.index("section") < ranked_ids.index("css")
    assert ranked_ids.index("id") < ranked_ids.index("css")
    assert ranked_ids.index("generated-class") > ranked_ids.index("css")
    assert ranked_ids.index("xpath") > ranked_ids.index("generated-class")
    assert ranked_ids[-1] == "nth"


def test_dom_004_validation_contract_classifies_common_locator_failures_without_emitting_runtime_truth() -> None:
    contract_module = _find_future_dom_contract_module()
    validate_locator_candidate = _load_contract_callable(
        contract_module,
        ("validate_locator_candidate", "validate_locator", "browser_validate_locator", "classify_locator_validation"),
    )

    cases = [
        (
            {
                "locator_ref": "candidate-not-found",
                "matches": [],
                "visible_matches": [],
                "page_url": "https://example.test/products",
            },
            "locator_not_found",
            "none",
            0,
        ),
        (
            {
                "locator_ref": "candidate-multiple",
                "matches": [{"element_ref": "el-1"}, {"element_ref": "el-2"}],
                "visible_matches": [{"element_ref": "el-1"}, {"element_ref": "el-2"}],
                "page_url": "https://example.test/products",
            },
            "locator_matches_multiple",
            "multiple",
            2,
        ),
        (
            {
                "locator_ref": "candidate-hidden",
                "matches": [{"element_ref": "el-3", "visible": False}],
                "visible_matches": [],
                "page_url": "https://example.test/products",
            },
            "locator_hidden",
            "hidden",
            1,
        ),
        (
            {
                "locator_ref": "candidate-text-mismatch",
                "matches": [{"element_ref": "el-4", "text": "Submit"}],
                "visible_matches": [{"element_ref": "el-4", "text": "Submit"}],
                "expected_value": "Save",
                "page_url": "https://example.test/products",
            },
            "locator_text_mismatch",
            "unique",
            1,
        ),
        (
            {
                "locator_ref": "candidate-unique",
                "matches": [{"element_ref": "el-5", "visible": True}],
                "visible_matches": [{"element_ref": "el-5", "visible": True}],
                "page_url": "https://example.test/products",
                "expected_value": "Ready",
            },
            "locator_unique",
            "unique",
            1,
        ),
    ]

    for payload, classification, status, match_count in cases:
        result = _call_contract(validate_locator_candidate, payload)

        assert isinstance(result, dict)
        assert result.get("locator_ref") == payload["locator_ref"]
        assert result.get("classification") == classification
        assert result.get("status") == status
        assert result.get("match_count") == match_count
        assert result.get("backend_validation_needed") is True or result.get("backend_validated") is True
        assert not any(
            truth_key in result
            for truth_key in ("recorded", "completed", "execution_status", "step_recorded", "run_completed")
        )


def test_dom_005_section_scoping_contract_prefers_meaningful_container_before_locator_escalation() -> None:
    contract_module = _find_future_dom_contract_module()
    scope_candidates = _load_contract_callable(
        contract_module,
        ("scope_candidates", "select_scoped_candidates", "build_section_scope", "rank_scoped_candidates"),
    )

    result = _call_contract(
        scope_candidates,
        {
            "target_text": "Submit",
            "candidates": [
                {
                    "candidate_id": "submit-card-1",
                    "text": "Submit",
                    "candidate_type": "action_target",
                    "section_ref": "pricing-card",
                    "scope": "card",
                    "ancestor_chain": ["card", "main"],
                },
                {
                    "candidate_id": "submit-card-2",
                    "text": "Submit",
                    "candidate_type": "action_target",
                    "section_ref": "pricing-card-2",
                    "scope": "card",
                    "ancestor_chain": ["card", "main"],
                },
                {
                    "candidate_id": "submit-global",
                    "text": "Submit",
                    "candidate_type": "action_target",
                    "section_ref": None,
                    "scope": "page",
                    "ancestor_chain": ["main"],
                },
            ],
            "preferred_container_types": ["section", "card", "form", "dialog", "table-row", "list-item"],
            "escalate_to": ["clarification", "locator_specialist"],
        },
    )

    assert isinstance(result, dict)
    assert result.get("candidate_id") == "submit-card-1"
    assert result.get("preferred_container_type") in {
        "section",
        "card",
        "form",
        "dialog",
        "table-row",
        "list-item",
    }
    assert result.get("scope") in {"card", "section", "form", "dialog", "table-row", "list-item"}
    assert result.get("escalation") in {"clarification", "locator_specialist", None}
    assert result.get("needs_clarification") in {True, False}
    assert result.get("execute") is not True
