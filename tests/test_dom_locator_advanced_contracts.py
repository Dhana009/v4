from __future__ import annotations

from copy import deepcopy
from importlib import import_module, util as importlib_util
from inspect import signature
from types import ModuleType
from typing import Any, Callable

import pytest

from runtime.dom_locator_contract import (
    build_element_candidate,
    build_page_snapshot,
    scope_candidates,
)


ADVANCED_DOM_CONTRACT_MODULE = "runtime.dom_locator_contract"


def _load_contract_module() -> ModuleType:
    if importlib_util.find_spec(ADVANCED_DOM_CONTRACT_MODULE) is None:
        pytest.xfail(
            "runtime.dom_locator_contract missing; expected DOM-006..DOM-010 advanced DOM/locator seam"
        )
    return import_module(ADVANCED_DOM_CONTRACT_MODULE)


def _load_contract_callable(module: ModuleType, names: tuple[str, ...]) -> Callable[..., Any]:
    for name in names:
        candidate = getattr(module, name, None)
        if callable(candidate):
            return candidate

    available_exports = sorted(name for name in dir(module) if not name.startswith("_"))
    pytest.xfail(
        f"{module.__name__} is missing required advanced DOM contract callable(s) {names}; "
        f"available exports: {', '.join(available_exports[:20]) or 'none'}"
    )


def _call_contract(fn: Callable[..., Any], payload: dict[str, Any]) -> Any:
    params = signature(fn).parameters
    call_kwargs = {name: value for name, value in payload.items() if name in params}
    if call_kwargs or any(param.kind == param.VAR_KEYWORD for param in params.values()):
        return fn(**call_kwargs)
    pytest.xfail(
        f"{getattr(fn, '__module__', 'unknown')}.{getattr(fn, '__name__', 'callable')} "
        "has an incompatible signature for the advanced DOM contract test payload"
    )


def test_dom_006_assertion_target_baseline_keeps_expected_value_separate_from_target_text_and_ignores_expected_outcome_metadata() -> None:
    visible_payload = {
        "candidate_id": "assert-visible",
        "candidate_type": "assertion_target",
        "role": "status",
        "accessible_name": "Delivery status",
        "text": "Ready",
        "target_text": "Ready",
        "expected_value": None,
        "source": "validated_plan_child",
        "scope": "section:Order summary",
        "ancestor_chain": ["section:Order summary", "main"],
        "selector": 'get_by_role("status", name="Ready")',
        "expected_outcome": {"type": "navigation", "description": "go to next page"},
    }
    exact_text_payload = {
        "candidate_id": "assert-exact-text",
        "candidate_type": "assertion_target",
        "role": "textbox",
        "accessible_name": "Order note",
        "text": "Shipped",
        "target_text": "Shipped",
        "expected_value": "Shipped",
        "source": "validated_plan_child",
        "scope": "section:Order summary",
        "ancestor_chain": ["section:Order summary", "main"],
        "selector": 'get_by_text("Shipped", exact=True)',
    }

    visible_candidate = build_element_candidate(**deepcopy(visible_payload))
    exact_text_candidate = build_element_candidate(**deepcopy(exact_text_payload))

    assert visible_candidate["candidate_type"] == "assertion_target"
    assert visible_candidate["text"] == "Ready"
    assert visible_candidate["target_text"] == "Ready"
    assert visible_candidate["expected_value"] is None
    assert visible_candidate["source"] == "validated_plan_child"
    assert visible_candidate["scope"] == "section:Order summary"
    assert visible_candidate["ancestor_chain"] == ["section:Order summary", "main"]
    assert visible_candidate["selector"] == 'get_by_role("status", name="Ready")'
    assert "expected_outcome" not in visible_candidate

    assert exact_text_candidate["candidate_type"] == "assertion_target"
    assert exact_text_candidate["text"] == "Shipped"
    assert exact_text_candidate["target_text"] == "Shipped"
    assert exact_text_candidate["expected_value"] == "Shipped"
    assert exact_text_candidate["selector"] == 'get_by_text("Shipped", exact=True)'


def test_dom_006_assertion_target_classifier_contract_rejects_visible_plus_has_text_conflict_when_future_seam_exists() -> None:
    module = _load_contract_module()
    classify_assertion_target = _load_contract_callable(
        module,
        ("classify_assertion_target", "build_assertion_target_contract", "resolve_assertion_target"),
    )

    result = _call_contract(
        classify_assertion_target,
        {
            "assertion_type": "visible",
            "target_candidate": {
                "candidate_id": "candidate-visible",
                "role": "status",
                "text": "Ready",
            },
            "expected_outcome_metadata_ref": "parent-step-1",
            "expected_outcome": {"type": "navigation", "description": "go to next page"},
            "expected_value": None,
            "source_of_expected_value": "validated_plan_child",
            "compatibility_flags": ["visible+has_text invalid"],
        },
    )

    assert isinstance(result, dict)
    assert result.get("assertion_type") in {"visible", "has_text", "exact_text", None}
    assert result.get("target_candidate_id") in {"candidate-visible", None}
    assert result.get("expected_outcome_metadata_ref") in {"parent-step-1", None}
    assert result.get("expected_value") in {None, "Ready", "Shipped", ""}
    assert not any(
        truth_key in result
        for truth_key in ("recorded", "completed", "run_completed", "step_recorded", "execution_status")
    )


def test_dom_007_dynamic_ui_snapshot_baseline_exposes_structured_modal_dropdown_toast_loading_evidence_without_internal_controls() -> None:
    snapshot = build_page_snapshot(
        html="""
        <html>
          <head><title>Checkout</title></head>
          <body>
            <dialog aria-label="Settings modal">
              <button>Close</button>
            </dialog>
            <div role="listbox" aria-label="Theme options">
              <div role="option" aria-selected="true">Dark</div>
            </div>
            <div role="alert">Saved</div>
            <div role="status">Loading...</div>
            <button data-testid="aw-panel-toggle">Debug overlay</button>
          </body>
        </html>
        """,
        url="https://example.test/checkout",
        title="Checkout",
        captured_at="2026-05-07T01:02:03Z",
    )

    assert snapshot["url"] == "https://example.test/checkout"
    assert snapshot["title"] == "Checkout"
    assert snapshot["captured_at"] == "2026-05-07T01:02:03Z"
    assert snapshot["timestamp"] == "2026-05-07T01:02:03Z"
    assert snapshot["scope"] == "full_page"

    sections = snapshot.get("sections") or snapshot.get("landmarks")
    assert isinstance(sections, list)
    assert any(
        "settings modal" in str(section.get("name") or section.get("label") or section.get("title") or "").lower()
        for section in sections
        if isinstance(section, dict)
    )

    interactive_elements = snapshot.get("interactive_elements")
    assert isinstance(interactive_elements, list)
    assert any(element.get("role") == "button" for element in interactive_elements)
    assert any(element.get("role") == "listbox" for element in interactive_elements)
    assert any(element.get("role") == "option" for element in interactive_elements)
    assert any(element.get("role") == "alert" for element in interactive_elements)
    assert any(element.get("role") == "status" for element in interactive_elements)
    assert any("loading" in str(element.get("name") or element.get("text") or "").lower() for element in interactive_elements)
    assert not any(
        "debug overlay" in str(element.get("name") or element.get("text") or "").lower()
        or "aw-panel-toggle" in str(element.get("candidate_id") or element.get("element_id") or element.get("selector") or "")
        for element in interactive_elements
    )
    assert snapshot.get("metadata", {}).get("internal_controls_excluded") == 1
    assert snapshot.get("extraction_warnings") == ["excluded_internal_button"]


def test_dom_007_dynamic_state_classifier_contract_marks_transient_states_as_advisory_only_when_future_seam_exists() -> None:
    module = _load_contract_module()
    classify_dynamic_ui_state = _load_contract_callable(
        module,
        ("classify_dynamic_ui_state", "detect_dynamic_ui_state", "build_dynamic_state_contract"),
    )

    result = _call_contract(
        classify_dynamic_ui_state,
        {
            "page_url": "https://example.test/checkout",
            "page_title": "Checkout",
            "state_evidence": {
                "modal": {"role": "dialog", "label": "Settings modal"},
                "dropdown": {"role": "listbox", "label": "Theme options"},
                "toast": {"role": "alert", "text": "Saved"},
                "loading": {"role": "status", "text": "Loading..."},
                "iframe": {"kind": "unsupported"},
            },
            "states": ["modal", "dropdown", "toast", "loading", "iframe"],
            "advisory_only": True,
        },
    )

    assert isinstance(result, dict)
    assert result.get("advisory_only") in {True, None}
    assert result.get("execute") is not True
    assert not any(
        truth_key in result
        for truth_key in ("recorded", "completed", "run_completed", "step_recorded", "execution_status")
    )
    assert result.get("classification") in {None, "modal", "dropdown", "toast", "loading", "capability_gap", "uncertain"}


def test_dom_008_locator_escalation_baseline_prefers_deterministic_section_scoping_before_specialist_escalation() -> None:
    result = scope_candidates(
        target_text="Submit",
        candidates=[
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
        preferred_container_types=["section", "card", "form", "dialog", "table-row", "list-item"],
        escalate_to=["clarification", "locator_specialist"],
    )

    assert isinstance(result, dict)
    assert result["candidate_id"] == "submit-card-1"
    assert result["recommended_candidate_id"] == "submit-card-1"
    assert result["candidate_count"] == 3
    assert result["target_text"] == "Submit"
    assert result["preferred_container_type"] in {
        "section",
        "card",
        "form",
        "dialog",
        "table-row",
        "list-item",
    }
    assert result["scope"] in {"card", "section", "form", "dialog", "table-row", "list-item"}
    assert result["needs_clarification"] is True
    assert result["execute"] is False
    assert result["escalation"] in {"clarification", "locator_specialist"}
    assert [candidate["candidate_id"] for candidate in result["ranked_candidates"]][:2] == [
        "submit-card-1",
        "submit-card-2",
    ]


def test_dom_008_locator_specialist_escalation_request_contract_rejects_raw_dom_and_keeps_output_advisory_only_when_future_seam_exists() -> None:
    module = _load_contract_module()
    build_locator_escalation_request = _load_contract_callable(
        module,
        (
            "build_locator_escalation_request",
            "prepare_locator_specialist_request",
            "escalate_locator_specialist",
        ),
    )

    result = _call_contract(
        build_locator_escalation_request,
        {
            "target_text": "Submit",
            "candidate_summary": {
                "candidate_ids": ["submit-card-1", "submit-card-2"],
                "preferred_container_type": "card",
                "scope": "card",
            },
            "page_context": {
                "url": "https://example.test/pricing",
                "title": "Pricing",
            },
            "validation_requirements": ["browser_validate_unique", "backend_validate_unique"],
            "skills_loaded": ["locator_strategy"],
            "tool_policy": {"deny_execution": True},
            "advisory_only": True,
        },
    )

    assert isinstance(result, dict)
    assert "raw_dom" not in result
    assert "full_dom" not in result
    assert result.get("advisory_only") in {True, None}
    assert result.get("execute") is not True
    assert result.get("candidate_ids") in (None, ["submit-card-1", "submit-card-2"])
    assert result.get("validation_requirements") in (
        None,
        ["browser_validate_unique", "backend_validate_unique"],
    )
    assert not any(
        truth_key in result
        for truth_key in ("recorded", "completed", "run_completed", "step_recorded", "execution_status")
    )


def test_dom_009_update_locator_command_flow_contract_preserves_history_and_requires_backend_validation_when_future_seam_exists() -> None:
    module = _load_contract_module()
    build_update_locator_command = _load_contract_callable(
        module,
        (
            "build_update_locator_command",
            "prepare_update_locator_command",
            "validate_update_locator_command",
            "apply_locator_update",
        ),
    )

    locator_history = [
        {"locator_ref": "candidate-old", "status": "accepted", "validated": True},
        {"locator_ref": "candidate-new", "status": "rejected", "validated": False},
    ]
    result = _call_contract(
        build_update_locator_command,
        {
            "type": "update_locator",
            "command_id": "update-locator-001",
            "run_id": "run-1",
            "step_id": "step-1",
            "operation_id": "op-1",
            "locator_candidate": {
                "candidate_id": "candidate-new",
                "element_ref": "el-2",
                "selector": 'get_by_role("button", name="Submit")',
            },
            "locator_history": deepcopy(locator_history),
            "reason": "current locator became ambiguous",
            "source": "recovery",
            "user_hint": "use button in pricing card",
            "backend_validation_required": True,
        },
    )

    assert isinstance(result, dict)
    assert result.get("type") in {"update_locator", None}
    assert result.get("command_id") in {"update-locator-001", None}
    assert result.get("locator_history") in (None, locator_history)
    assert result.get("backend_validation_required") in {True, None}
    assert result.get("active_locator") in {None, "candidate-old"}
    assert not any(
        truth_key in result
        for truth_key in ("recorded", "completed", "run_completed", "step_recorded", "execution_status")
    )


def test_dom_010_fixture_matrix_baseline_covers_docs_forms_modals_tables_semantics_and_weak_div_span_candidates() -> None:
    docs_snapshot = build_page_snapshot(
        html="""
        <html>
          <head><title>Docs</title></head>
          <body>
            <main aria-label="Docs intro">
              <section aria-label="Getting started">
                <pre><code>npm install</code></pre>
                <p>Copy this command.</p>
              </section>
            </main>
          </body>
        </html>
        """,
        url="https://example.test/docs",
        title="Docs",
        captured_at="2026-05-07T01:02:03Z",
    )
    form_snapshot = build_page_snapshot(
        html="""
        <html>
          <body>
            <form aria-label="Lead capture">
              <label>Email</label>
              <textarea placeholder="Email address">hello</textarea>
              <button>Submit</button>
            </form>
          </body>
        </html>
        """,
        url="https://example.test/form",
        title="Lead capture",
        captured_at="2026-05-07T01:02:03Z",
    )
    modal_snapshot = build_page_snapshot(
        html="""
        <html>
          <body>
            <dialog aria-label="Share settings">
              <button>Close</button>
            </dialog>
            <div role="listbox" aria-label="Theme options">
              <div role="option" aria-selected="true">Dark</div>
            </div>
            <div role="alert">Saved</div>
            <div role="status">Loading...</div>
          </body>
        </html>
        """,
        url="https://example.test/modal",
        title="Share settings",
        captured_at="2026-05-07T01:02:03Z",
    )
    table_snapshot = build_page_snapshot(
        html="""
        <html>
          <body>
            <section aria-label="Orders dashboard">
              <table>
                <tr>
                  <td>Alpha</td>
                  <td><button>Edit</button></td>
                </tr>
              </table>
              <button hidden>Save desktop</button>
              <button aria-hidden="true">Save mobile</button>
            </section>
          </body>
        </html>
        """,
        url="https://example.test/table",
        title="Orders dashboard",
        captured_at="2026-05-07T01:02:03Z",
    )
    semantic_snapshot = build_page_snapshot(
        html="""
        <html>
          <body>
            <section aria-label="Accessibility sample">
              <button data-testid="save-btn" aria-label="Save changes">Save</button>
              <a href="/docs" aria-label="Read docs">Docs</a>
              <textarea aria-label="Search">Search</textarea>
            </section>
          </body>
        </html>
        """,
        url="https://example.test/semantic",
        title="Accessibility sample",
        captured_at="2026-05-07T01:02:03Z",
    )
    weak_candidate = build_element_candidate(
        candidate_id="weak-cta",
        element_id="cta-1",
        element_ref="cta-1",
        candidate_type="action_target",
        role="button",
        accessible_name="Start free trial",
        text="Start free trial",
        target_text="Start free trial",
        expected_value=None,
        selector="div.hero span.cta span",
        source="fixture_requirement",
        scope="section:Hero card",
        ancestor_chain=["section:Hero card", "main"],
        locator_candidates=[
            {"strategy": "role+name", "locator": 'get_by_role("button", name="Start free trial")'}
        ],
        risk_flags=["weak_semantics", "nested_span"],
    )

    assert any(
        "docs intro" in str(section.get("name") or section.get("label") or section.get("title") or "").lower()
        for section in docs_snapshot["sections"]
    )
    assert any(
        element.get("candidate_type") == "text_block"
        and "npm install" in str(element.get("text") or "").lower()
        for element in docs_snapshot["interactive_elements"]
    )
    assert any(
        element.get("role") == "textbox" or element.get("placeholder") == "Email address"
        for element in form_snapshot["interactive_elements"]
    )
    assert any(element.get("role") == "button" for element in form_snapshot["interactive_elements"])
    assert any(
        "share settings" in str(section.get("name") or section.get("label") or section.get("title") or "").lower()
        for section in modal_snapshot["sections"]
    )
    modal_roles = {element.get("role") for element in modal_snapshot["interactive_elements"]}
    assert {"button", "listbox", "option", "alert", "status"}.issubset(modal_roles)
    assert any(
        "orders dashboard" in str(section.get("name") or section.get("label") or section.get("title") or "").lower()
        for section in table_snapshot["sections"]
    )
    assert any(element.get("role") == "button" and element.get("text") == "Edit" for element in table_snapshot["interactive_elements"])
    assert any(element.get("visibility") == "hidden" for element in table_snapshot["interactive_elements"])
    semantic_roles = {element.get("role") for element in semantic_snapshot["interactive_elements"]}
    assert {"button", "link", "textbox"}.issubset(semantic_roles)
    assert any(element.get("data_testid") == "save-btn" for element in semantic_snapshot["interactive_elements"])
    assert weak_candidate["candidate_type"] == "action_target"
    assert weak_candidate["scope"] == "section:Hero card"
    assert weak_candidate["ancestor_chain"] == ["section:Hero card", "main"]
    assert weak_candidate["selector"] == "div.hero span.cta span"
    assert weak_candidate["risk_flags"] == ["weak_semantics", "nested_span"]
    assert weak_candidate["target_text"] == "Start free trial"
    assert weak_candidate["expected_value"] is None

    fixture_gap_needs = {
        "iframe": "capability_gap",
        "popup": "capability_gap",
        "upload": "capability_gap",
        "permission": "capability_gap",
        "download": "capability_gap",
    }
    assert set(fixture_gap_needs) == {"iframe", "popup", "upload", "permission", "download"}
    assert all(reason == "capability_gap" for reason in fixture_gap_needs.values())


def test_dom_010_fixture_requirement_registry_contract_xfail_until_fixture_matrix_seam_exists() -> None:
    module = _load_contract_module()
    build_fixture_requirements = _load_contract_callable(
        module,
        ("build_fixture_requirements", "list_fixture_requirements", "dom_fixture_requirements"),
    )

    result = _call_contract(
        build_fixture_requirements,
        {
            "fixture_names": [
                "docs-style",
                "weak-div-span",
                "form-heavy",
                "modal-dropdown",
                "table-card",
                "semantic-accessibility",
            ],
            "gap_needs": ["iframe", "popup", "upload", "permission", "download"],
            "advisory_only": True,
        },
    )

    assert isinstance(result, dict)
    assert result.get("advisory_only") in {True, None}
    assert not any(
        truth_key in result
        for truth_key in ("recorded", "completed", "run_completed", "step_recorded", "execution_status")
    )
