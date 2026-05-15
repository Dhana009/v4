from __future__ import annotations

import inspect

from runtime.correction_context import build_plan_diff_editor_context_payload
from runtime.prompt_pack_builder import (
    REGISTERED_PROMPT_PACK_PURPOSES,
    build_plan_diff_editor_pack,
    build_prompt_pack,
    build_recovery_diagnoser_pack,
    build_step_plan_normalizer_dynamic_context,
    build_step_plan_normalizer_pack,
)
from runtime.prompt_packs import PromptPack, hash_stable_prefix
from runtime.recovery_context import build_recovery_diagnoser_context_payload


def _step_plan_context(user_intent: str) -> dict[str, str]:
    return build_step_plan_normalizer_dynamic_context(
        messages=[{"role": "user", "content": user_intent}],
        metadata={
            "selected_context": "compact planning context",
            "page_summary": "fixture landing page",
            "queued_steps": "step-1",
            "validated_locators": "get_by_text('Get started')",
        },
        skills_loaded=["llm_runtime_controller", "prompt_persona_skill_loading"],
        skill_levels=["core_compact", "core_compact"],
        output_schema={"schema_id": "step_plan_normalizer.v1"},
    )


def _plan_diff_context(correction_text: str) -> dict[str, str]:
    return build_plan_diff_editor_context_payload(
        active_plan_state={
            "plan_id": "plan-1",
            "summary": "I will click Get started",
            "steps": [
                {
                    "step_id": "step-1",
                    "intent": "Click the Get started button",
                    "children": [
                        {
                            "operation_id": "op-1",
                            "type": "click",
                            "target": "Get started",
                            "locator": 'get_by_text("Get started", exact=True)',
                        }
                    ],
                }
            ],
        },
        correction_state={
            "target_step_id": "step-1",
            "correction_text": correction_text,
        },
        validation_feedback="validation feedback message",
        allowed_edit_policy="preserve existing child operations; preserve order; no split or merge unless explicit",
        validated_locators=['get_by_text("Get started", exact=True)'],
    )


def _recovery_context(failed_step_id: str) -> dict[str, str]:
    return build_recovery_diagnoser_context_payload(
        run_id="run-1",
        failed_step_state={
            "step_id": failed_step_id,
            "operation_id": "op-1",
            "last_error": "timeout while clicking",
        },
        failed_step_id=failed_step_id,
        failed_operation_id="op-1",
        error_summary="timeout while clicking",
        current_page="http://example.test/current | Fixture page",
        tried_fixes=["check visibility", "retry click"],
        failure_evidence=["timeout while clicking"],
        user_recovery_instruction="retry carefully",
        retry_attempts=[
            {"failed_step_id": failed_step_id, "status": "retrying", "summary": "retry with visibility check"},
        ],
    )


def test_step_plan_normalizer_prefix_hash_stable_across_dynamic_context() -> None:
    pack = build_step_plan_normalizer_pack()
    context_a = _step_plan_context("click the green primary CTA")
    context_b = _step_plan_context("open the account menu")

    assert pack.stable_prefix == build_step_plan_normalizer_pack().stable_prefix
    assert pack.prefix_hash == build_step_plan_normalizer_pack().prefix_hash

    rendered_suffix_a = pack.render_dynamic_suffix(context_a)
    rendered_suffix_b = pack.render_dynamic_suffix(context_b)

    assert rendered_suffix_a != rendered_suffix_b
    assert "click the green primary CTA" not in pack.stable_prefix
    assert "open the account menu" not in pack.stable_prefix
    assert "click the green primary CTA" in rendered_suffix_a
    assert "open the account menu" in rendered_suffix_b


def test_plan_diff_editor_prefix_hash_stable_across_correction_text() -> None:
    pack = build_plan_diff_editor_pack()
    context_a = _plan_diff_context("add visible assertion first")
    context_b = _plan_diff_context("move the click after the assertion")

    assert pack.stable_prefix == build_plan_diff_editor_pack().stable_prefix
    assert pack.prefix_hash == build_plan_diff_editor_pack().prefix_hash

    rendered_suffix_a = pack.render_dynamic_suffix(context_a)
    rendered_suffix_b = pack.render_dynamic_suffix(context_b)

    assert rendered_suffix_a != rendered_suffix_b
    assert "add visible assertion first" not in pack.stable_prefix
    assert "move the click after the assertion" not in pack.stable_prefix
    assert "add visible assertion first" in rendered_suffix_a
    assert "move the click after the assertion" in rendered_suffix_b


def test_recovery_diagnoser_prefix_hash_stable_across_failed_step() -> None:
    pack = build_recovery_diagnoser_pack()
    context_a = _recovery_context("step-1")
    context_b = _recovery_context("step-2")

    assert pack.stable_prefix == build_recovery_diagnoser_pack().stable_prefix
    assert pack.prefix_hash == build_recovery_diagnoser_pack().prefix_hash

    rendered_suffix_a = pack.render_dynamic_suffix(context_a)
    rendered_suffix_b = pack.render_dynamic_suffix(context_b)

    assert rendered_suffix_a != rendered_suffix_b
    assert "step-1" not in pack.stable_prefix
    assert "step-2" not in pack.stable_prefix
    assert "step-1" in rendered_suffix_a
    assert "step-2" in rendered_suffix_b


def test_prefix_hash_changes_when_stable_prefix_changes() -> None:
    pack = build_step_plan_normalizer_pack()
    original_hash = hash_stable_prefix(pack.stable_prefix)
    changed_hash = hash_stable_prefix(f"{pack.stable_prefix}\nextra stable rule")

    assert original_hash == pack.prefix_hash
    assert changed_hash != original_hash


def test_prompt_pack_identity_fields_present() -> None:
    for purpose in REGISTERED_PROMPT_PACK_PURPOSES:
        pack = build_prompt_pack(purpose)
        assert pack.prompt_pack_id
        assert pack.prompt_pack_version == 1
        assert pack.stable_prefix
        assert pack.dynamic_suffix_template
        assert pack.prefix_hash == hash_stable_prefix(pack.stable_prefix)


def test_stable_prefix_does_not_contain_dynamic_markers() -> None:
    step_plan_pack = build_step_plan_normalizer_pack()
    step_plan_context = _step_plan_context("click the green primary CTA")

    plan_diff_pack = build_plan_diff_editor_pack()
    plan_diff_context = _plan_diff_context("add visible assertion first")

    recovery_pack = build_recovery_diagnoser_pack()
    recovery_context = _recovery_context("step-99")

    cases = [
        (
            step_plan_pack,
            step_plan_context,
            ("click the green primary CTA", "fixture landing page"),
        ),
        (
            plan_diff_pack,
            plan_diff_context,
            ("add visible assertion first", "validation feedback message", "step-1"),
        ),
        (
            recovery_pack,
            recovery_context,
            ("step-99", "http://example.test/current | Fixture page"),
        ),
    ]

    for pack, context, markers in cases:
        rendered_suffix = pack.render_dynamic_suffix(context)
        for marker in markers:
            assert marker not in pack.stable_prefix
            assert marker in rendered_suffix


def test_cache_strategy_no_provider_dependency() -> None:
    pack = build_prompt_pack("step_plan_normalizer")
    context = _step_plan_context("click the green primary CTA")

    assert pack.render_dynamic_suffix(context)
    assert "client" not in inspect.signature(build_prompt_pack).parameters
    assert "client" not in inspect.signature(PromptPack.render_dynamic_suffix).parameters
    assert "openai_client" not in inspect.signature(build_prompt_pack).parameters
