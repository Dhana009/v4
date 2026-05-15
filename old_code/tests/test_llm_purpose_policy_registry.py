"""
S6-0102: Typed purpose policy registry — unit and contract tests.

Tests-first policy: all tests written before implementation.
Source rule: Runtime Policy Spec — every LLM call must declare purpose_id.
Unknown purpose must fail closed (no fallback LLM call).
Every purpose must have complete policy fields.
95% coverage required for new modules.
"""
from __future__ import annotations

import copy
import json
import pytest

from runtime.llm_purpose_policy import (
    REQUIRED_PURPOSE_IDS,
    LLMPurposePolicy,
    get_purpose_policy,
    list_purposes,
    is_known_purpose,
)
from runtime.llm_policy_registry import (
    LLMPolicyRegistry,
    build_default_registry,
    POLICY_REGISTRY,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def registry() -> LLMPolicyRegistry:
    return build_default_registry()


# ---------------------------------------------------------------------------
# 1. All 14 purposes present
# ---------------------------------------------------------------------------

EXPECTED_PURPOSES = {
    "intent_classifier",
    "clarification_generator",
    "page_intelligence_summarizer",
    "page_validation_recommender",
    "journey_planner",
    "step_plan_normalizer",
    "plan_diff_editor",
    "locator_specialist",
    "custom_assertion_planner",
    "execution_driver",
    "recovery_diagnoser",
    "replay_repair_specialist",
    "user_response_writer",
    "trace_summarizer",
}


def test_required_purpose_ids_count():
    assert len(REQUIRED_PURPOSE_IDS) == 14


def test_required_purpose_ids_names():
    assert set(REQUIRED_PURPOSE_IDS) == EXPECTED_PURPOSES


def test_registry_has_all_14_purposes(registry):
    purposes = set(registry.list_purposes())
    assert purposes == EXPECTED_PURPOSES


def test_module_list_purposes_returns_all():
    purposes = set(list_purposes())
    assert purposes == EXPECTED_PURPOSES


# ---------------------------------------------------------------------------
# 2. Unknown purpose fails closed
# ---------------------------------------------------------------------------

def test_unknown_purpose_raises_from_registry(registry):
    with pytest.raises((ValueError, KeyError)):
        registry.get("unknown_purpose_xyz")


def test_empty_purpose_raises(registry):
    with pytest.raises((ValueError, KeyError, TypeError)):
        registry.get("")


def test_none_purpose_raises(registry):
    with pytest.raises((ValueError, KeyError, TypeError)):
        registry.get(None)  # type: ignore[arg-type]


def test_unknown_purpose_raises_from_module():
    with pytest.raises((ValueError, KeyError)):
        get_purpose_policy("not_a_real_purpose")


def test_is_known_purpose_true_for_valid():
    for p in EXPECTED_PURPOSES:
        assert is_known_purpose(p) is True


def test_is_known_purpose_false_for_unknown():
    assert is_known_purpose("nonexistent_purpose") is False
    assert is_known_purpose("") is False
    assert is_known_purpose("main_orchestrator") is False


# ---------------------------------------------------------------------------
# 3. Every purpose has required policy fields
# ---------------------------------------------------------------------------

REQUIRED_FIELDS = [
    "purpose_id",
    "model_class",
    "context_policy",
    "skill_policy",
    "tool_policy",
    "schema_id",
    "validator_id",
    "fallback_policy",
    "retry_policy",
    "telemetry_fields",
]


@pytest.mark.parametrize("purpose", sorted(EXPECTED_PURPOSES))
def test_purpose_has_all_required_fields(purpose, registry):
    policy = registry.get(purpose)
    for field in REQUIRED_FIELDS:
        assert field in policy, f"Purpose {purpose!r} missing field {field!r}"


@pytest.mark.parametrize("purpose", sorted(EXPECTED_PURPOSES))
def test_purpose_has_no_empty_model_class(purpose, registry):
    policy = registry.get(purpose)
    model_class = policy["model_class"]
    assert model_class, f"Purpose {purpose!r} has empty model_class"
    assert model_class in {"cheap", "main", "debug"}, (
        f"Purpose {purpose!r} model_class {model_class!r} not in cheap/main/debug"
    )


@pytest.mark.parametrize("purpose", sorted(EXPECTED_PURPOSES))
def test_purpose_has_context_policy(purpose, registry):
    policy = registry.get(purpose)
    cp = policy["context_policy"]
    assert isinstance(cp, dict), f"Purpose {purpose!r} context_policy must be dict"
    assert cp, f"Purpose {purpose!r} context_policy is empty"


@pytest.mark.parametrize("purpose", sorted(EXPECTED_PURPOSES))
def test_purpose_has_skill_policy(purpose, registry):
    policy = registry.get(purpose)
    sp = policy["skill_policy"]
    assert isinstance(sp, dict), f"Purpose {purpose!r} skill_policy must be dict"
    assert sp, f"Purpose {purpose!r} skill_policy is empty"


@pytest.mark.parametrize("purpose", sorted(EXPECTED_PURPOSES))
def test_purpose_has_tool_policy(purpose, registry):
    policy = registry.get(purpose)
    tp = policy["tool_policy"]
    assert isinstance(tp, dict), f"Purpose {purpose!r} tool_policy must be dict"


@pytest.mark.parametrize("purpose", sorted(EXPECTED_PURPOSES))
def test_purpose_has_schema_id(purpose, registry):
    policy = registry.get(purpose)
    schema_id = policy["schema_id"]
    assert schema_id, f"Purpose {purpose!r} has empty schema_id"
    assert isinstance(schema_id, str)


@pytest.mark.parametrize("purpose", sorted(EXPECTED_PURPOSES))
def test_purpose_has_validator_id(purpose, registry):
    policy = registry.get(purpose)
    validator_id = policy["validator_id"]
    assert validator_id, f"Purpose {purpose!r} has empty validator_id"
    assert isinstance(validator_id, str)


@pytest.mark.parametrize("purpose", sorted(EXPECTED_PURPOSES))
def test_purpose_has_fallback_policy(purpose, registry):
    policy = registry.get(purpose)
    fallback = policy["fallback_policy"]
    assert fallback, f"Purpose {purpose!r} has empty fallback_policy"
    assert fallback in {"ask_user", "fail_closed", "retry"}, (
        f"Purpose {purpose!r} fallback_policy {fallback!r} not in allowed set"
    )


@pytest.mark.parametrize("purpose", sorted(EXPECTED_PURPOSES))
def test_purpose_has_retry_policy(purpose, registry):
    policy = registry.get(purpose)
    rp = policy["retry_policy"]
    assert isinstance(rp, dict), f"Purpose {purpose!r} retry_policy must be dict"
    assert rp, f"Purpose {purpose!r} retry_policy is empty"


@pytest.mark.parametrize("purpose", sorted(EXPECTED_PURPOSES))
def test_purpose_has_telemetry_fields(purpose, registry):
    policy = registry.get(purpose)
    tf = policy["telemetry_fields"]
    assert isinstance(tf, (dict, list)), f"Purpose {purpose!r} telemetry_fields must be dict or list"
    assert tf, f"Purpose {purpose!r} telemetry_fields is empty"


# ---------------------------------------------------------------------------
# 4. Policy immutability / safe copy
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("purpose", sorted(EXPECTED_PURPOSES))
def test_registry_returns_safe_copy(purpose, registry):
    """Mutating a returned policy must not corrupt the registry."""
    policy1 = registry.get(purpose)
    policy1["__injected_mutation__"] = "corrupted"
    policy2 = registry.get(purpose)
    assert "__injected_mutation__" not in policy2, (
        f"Registry returned a live reference for {purpose!r}; must return a copy"
    )


# ---------------------------------------------------------------------------
# 5. Serialisability
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("purpose", sorted(EXPECTED_PURPOSES))
def test_purpose_policy_is_json_serializable(purpose, registry):
    policy = registry.get(purpose)
    try:
        encoded = json.dumps(policy)
    except (TypeError, ValueError) as exc:
        pytest.fail(f"Purpose {purpose!r} policy is not JSON-serializable: {exc}")
    decoded = json.loads(encoded)
    assert decoded["purpose_id"] == purpose


# ---------------------------------------------------------------------------
# 6. LLMPurposePolicy TypedDict / dataclass sanity
# ---------------------------------------------------------------------------

def test_llm_purpose_policy_has_required_attributes():
    """LLMPurposePolicy must expose all required fields via annotation or attribute."""
    import inspect
    annotations = getattr(LLMPurposePolicy, "__annotations__", {})
    for field in REQUIRED_FIELDS:
        assert field in annotations, f"LLMPurposePolicy missing annotation for {field!r}"


# ---------------------------------------------------------------------------
# 7. Module-level get_purpose_policy convenience
# ---------------------------------------------------------------------------

def test_get_purpose_policy_returns_dict():
    policy = get_purpose_policy("intent_classifier")
    assert isinstance(policy, dict)
    assert policy["purpose_id"] == "intent_classifier"


def test_get_purpose_policy_unknown_raises():
    with pytest.raises((ValueError, KeyError)):
        get_purpose_policy("bad_purpose")


# ---------------------------------------------------------------------------
# 8. POLICY_REGISTRY singleton is consistent
# ---------------------------------------------------------------------------

def test_policy_registry_singleton_all_purposes():
    purposes = set(POLICY_REGISTRY.list_purposes())
    assert purposes == EXPECTED_PURPOSES


def test_policy_registry_singleton_fail_closed():
    with pytest.raises((ValueError, KeyError)):
        POLICY_REGISTRY.get("unknown_xyz")


# ---------------------------------------------------------------------------
# 9. Purpose ID matches key
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("purpose", sorted(EXPECTED_PURPOSES))
def test_purpose_id_matches_key(purpose, registry):
    policy = registry.get(purpose)
    assert policy["purpose_id"] == purpose, (
        f"Purpose {purpose!r}: policy['purpose_id'] = {policy['purpose_id']!r}, expected {purpose!r}"
    )
