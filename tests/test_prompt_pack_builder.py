from __future__ import annotations

import pytest

from runtime.prompt_pack_builder import (
    NON_NEGOTIABLE_RUNTIME_RULES,
    REGISTERED_PROMPT_PACK_PURPOSES,
    build_prompt_pack,
    build_step_plan_normalizer_dynamic_context,
    build_step_plan_normalizer_pack,
)
from runtime.prompt_packs import PromptPack, hash_stable_prefix


def test_step_plan_normalizer_pack_identity_and_version() -> None:
    pack = build_step_plan_normalizer_pack()
    assert pack.purpose == "step_plan_normalizer"
    assert pack.prompt_pack_id == "step_plan_normalizer.v1"
    assert pack.prompt_pack_version == 1
    assert pack.prefix_hash == hash_stable_prefix(pack.stable_prefix)
    assert pack.estimated_stable_tokens is not None
    assert pack.estimated_stable_tokens > 0


def test_step_plan_normalizer_stable_prefix_contains_required_rules() -> None:
    pack = build_step_plan_normalizer_pack()
    stable_prefix = pack.stable_prefix

    for rule in NON_NEGOTIABLE_RUNTIME_RULES:
        assert rule in stable_prefix

    assert "PROMPT_PACK_ID: step_plan_normalizer.v1" in stable_prefix
    assert "PROMPT_PACK_VERSION: 1" in stable_prefix
    assert "PURPOSE: step_plan_normalizer" in stable_prefix
    assert "ROLE:" in stable_prefix
    assert "OUTPUT_EXPECTATION:" in stable_prefix
    assert "PLANNING_RULES:" in stable_prefix


def test_step_plan_normalizer_rendered_suffix_stays_separate_from_stable_prefix() -> None:
    pack = build_step_plan_normalizer_pack()
    dynamic_context = build_step_plan_normalizer_dynamic_context(
        messages=[{"role": "user", "content": "click the Get started button"}],
        metadata={
            "context_mode": "compact",
            "queued_steps": "step-1",
            "validated_locators": "[get_by_text('Get started')]",
        },
        skills_loaded=["llm_runtime_controller", "prompt_persona_skill_loading"],
        skill_levels=["core_compact", "core_compact"],
        output_schema={"schema_id": "step_plan_normalizer.v1"},
    )

    rendered_suffix = pack.render_dynamic_suffix(dynamic_context)
    rendered_prompt = pack.render_prompt(dynamic_context)

    assert "DYNAMIC_PLANNING_CONTEXT:" in rendered_suffix
    assert "click the Get started button" in rendered_suffix
    assert "click the Get started button" not in pack.stable_prefix
    assert rendered_prompt.startswith(pack.stable_prefix)
    assert rendered_suffix in rendered_prompt


def test_prefix_hash_is_deterministic_and_content_bound() -> None:
    pack_one = build_step_plan_normalizer_pack()
    pack_two = build_step_plan_normalizer_pack()
    assert pack_one.prefix_hash == pack_two.prefix_hash

    changed_pack = PromptPack(
        purpose=pack_one.purpose,
        prompt_pack_id=pack_one.prompt_pack_id,
        prompt_pack_version=pack_one.prompt_pack_version,
        stable_prefix=f"{pack_one.stable_prefix}\nEXTRA_LINE: true",
        dynamic_suffix_template=pack_one.dynamic_suffix_template,
        required_safety_rules=pack_one.required_safety_rules,
        prefix_hash=hash_stable_prefix(f"{pack_one.stable_prefix}\nEXTRA_LINE: true"),
        estimated_stable_tokens=pack_one.estimated_stable_tokens,
    )
    assert changed_pack.prefix_hash != pack_one.prefix_hash


def test_unknown_prompt_pack_purpose_raises_controlled_error() -> None:
    with pytest.raises(ValueError, match="Unsupported prompt pack purpose"):
        build_prompt_pack("unknown_purpose")


def test_step_plan_normalizer_stable_prefix_token_budget_is_small() -> None:
    pack = build_step_plan_normalizer_pack()
    assert pack.estimated_stable_tokens is not None
    assert pack.estimated_stable_tokens <= 3000


def test_registered_prompt_pack_purposes_include_step_plan_normalizer() -> None:
    assert "step_plan_normalizer" in REGISTERED_PROMPT_PACK_PURPOSES
