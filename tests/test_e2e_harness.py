from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

from tests.e2e import harness


NORMALIZED_EVIDENCE_ARTIFACTS = {
    "manifest": "manifest.json",
    "test_result": "test-result.json",
    "backend_log": "backend.log",
    "frontend_log": "frontend.log",
    "browser_console_log": "browser-console.log",
    "summary": "summary.md",
}
NORMALIZED_EVIDENCE_FILE_HASHES = {
    "backend.log": "sha256:backend-log",
    "frontend.log": "sha256:frontend-log",
    "browser-console.log": "sha256:browser-console-log",
    "summary.md": "sha256:summary-md",
}
NORMALIZED_EVIDENCE_NOTES = [
    "events.ndjson, commands.json, and rejections.json are deferred to a later backend event stream slice",
    "trace-summary and redaction-report are deferred to a later trace/export slice",
]
REDACTION_REPORT_ARTIFACTS = {
    "manifest": "manifest.json",
    "test_result": "test-result.json",
    "summary": "summary.md",
    "redaction_report": "redaction-report.json",
}
REDACTION_REPORT_EXPECTED_SCHEMA = {
    "redaction_passed": True,
    "redaction_version": "1.0",
    "patterns_checked": ["token", "otp", "email", "phone", "password"],
    "files_checked": ["trace.ndjson", "commands.json"],
    "findings": [],
}
REDACTION_REPORT_SECRET_VALUES = (
    "sk-test-redaction-token",
    "123456",
    "user@example.test",
    "+1-202-555-0175",
    "correct horse battery staple",
)


def _sensitive_query_url() -> str:
    fake_token, fake_otp, fake_email, fake_phone, fake_password = REDACTION_REPORT_SECRET_VALUES
    return (
        "https://example.test/trace?"
        f"token={fake_token}&"
        f"otp={fake_otp}&"
        f"email={fake_email}&"
        f"phone={fake_phone}&"
        f"password={fake_password}"
    )


def _nested_sensitive_event_evidence() -> dict[str, object]:
    fake_token, fake_otp, fake_email, fake_phone, fake_password = REDACTION_REPORT_SECRET_VALUES
    return {
        "request": {
            "url": _sensitive_query_url(),
            "headers": {
                "Authorization": f"Bearer {fake_token}",
                "X-OTP": fake_otp,
            },
            "contact": {
                "email": fake_email,
                "phone": fake_phone,
            },
            "profile": {
                "password": fake_password,
            },
        },
        "nested": [
            {"token": fake_token},
            {"otp": fake_otp},
            {"email": fake_email},
            {"phone": fake_phone},
            {"password": fake_password},
        ],
    }


def _event(event_type: str, run_id: str = "run-123", **payload: object) -> dict[str, object]:
    event: dict[str, object] = {
        "schema_version": "autoworkbench.events.v1",
        "type": event_type,
        "run_id": run_id,
    }
    event.update(payload)
    return event


def _harness_source() -> str:
    return Path(harness.__file__).read_text(encoding="utf-8")


class _FakeLocator:
    def __init__(self, text: str = "", visible: bool = False) -> None:
        self._text = text
        self._visible = visible

    @property
    def first(self) -> "_FakeLocator":
        return self

    async def is_visible(self) -> bool:
        return self._visible

    async def inner_text(self) -> str:
        return self._text


class _FakePage:
    def __init__(self, url: str = "http://example.test/agents.html") -> None:
        self.url = url

    def locator(self, selector: str) -> _FakeLocator:
        if selector == "#autoworkbench-root .ide-panel":
            return _FakeLocator(visible=False)
        if selector == ".ide-tab.active":
            return _FakeLocator(text="")
        if selector == ".ide-hd-state":
            return _FakeLocator(text="")
        return _FakeLocator()

    async def screenshot(self, path: str, full_page: bool = True) -> None:  # noqa: ARG002
        Path(path).write_text("fake screenshot", encoding="utf-8")

    async def content(self) -> str:
        return "<html><body>fake page</body></html>"


def test_harness_still_targets_legacy_overlay_path_for_transition_fallback() -> None:
    source = _harness_source()

    assert "#autoworkbench-root .ide-panel" in source
    assert "#autoworkbench-root" in source


def test_harness_is_expected_to_gain_shadow_root_aware_autoworkbench_lookup() -> None:
    source = _harness_source()

    missing = []
    if not any(marker in source for marker in ("shadow_root", "shadowRoot", "find_autoworkbench_panel", "wait_for_autoworkbench_ready")):
        missing.append("shadow-root-aware lookup helper")
    if "#autoworkbench-root .ide-panel" in source and not any(
        marker in source for marker in ("shadow_root", "shadowRoot", "find_autoworkbench_panel", "wait_for_autoworkbench_ready")
    ):
        missing.append("legacy-only overlay lookup")

    if not missing:
        assert any(marker in source for marker in ("shadow_root", "shadowRoot", "find_autoworkbench_panel", "wait_for_autoworkbench_ready"))
        assert "#autoworkbench-root .ide-panel" in source
        return

    pytest.xfail("MR-4D harness contract not implemented yet: " + ", ".join(missing))


class _TrackedTabLocator:
    def __init__(
        self,
        label: str,
        *,
        visible: bool = True,
        text: str = "",
        count_value: int = 1,
        nested: dict[str, "_TrackedTabLocator"] | None = None,
    ) -> None:
        self.label = label
        self.visible = visible
        self.text = text
        self.count_value = count_value
        self.nested = nested or {}
        self.click_count = 0
        self.wait_for_count = 0
        self.count_count = 0
        self.locator_requests: list[str] = []

    @property
    def first(self) -> "_TrackedTabLocator":
        return self

    async def count(self) -> int:
        self.count_count += 1
        return self.count_value

    async def wait_for(self, state: str, timeout: int | None = None) -> None:  # noqa: ARG002
        self.wait_for_count += 1
        if state == "visible" and not self.visible:
            raise TimeoutError(f"{self.label} is not visible")

    def locator(self, selector: str) -> "_TrackedTabLocator":
        self.locator_requests.append(selector)
        return self.nested.get(selector, _TrackedTabLocator(f"{self.label}:{selector}", visible=self.visible, count_value=0))

    async def is_visible(self) -> bool:
        return self.visible

    async def inner_text(self) -> str:
        return self.text

    async def click(self, timeout: int | None = None) -> None:  # noqa: ARG002
        self.click_count += 1


class _TrackedTabPage:
    def __init__(
        self,
        *,
        test_ids: dict[str, _TrackedTabLocator],
        roles: dict[str, _TrackedTabLocator],
        locators: dict[str, _TrackedTabLocator] | None = None,
    ) -> None:
        self.test_ids = test_ids
        self.roles = roles
        self.locators = locators or {}
        self.test_id_requests: list[str] = []
        self.role_requests: list[str] = []
        self.locator_requests: list[str] = []

    def get_by_test_id(self, test_id: str) -> _TrackedTabLocator:
        self.test_id_requests.append(test_id)
        return self.test_ids[test_id]

    def get_by_role(self, role: str, name: object) -> _TrackedTabLocator:  # noqa: ARG002
        self.role_requests.append(str(name))
        return self.roles[str(name)]

    def locator(self, selector: str) -> _TrackedTabLocator:
        self.locator_requests.append(selector)
        return self.locators.get(selector, _TrackedTabLocator(selector, visible=False, count_value=0))


def test_click_autoworkbench_tab_prefers_test_id_hooks_and_keeps_role_fallback() -> None:
    testid_steps = _TrackedTabLocator("steps-tab")
    testid_workbench = _TrackedTabLocator("llm-tab")
    role_steps = _TrackedTabLocator("steps-role")
    role_workbench = _TrackedTabLocator("workbench-role")
    page = _TrackedTabPage(
        test_ids={
            "steps-tab": testid_steps,
            "llm-tab": testid_workbench,
        },
        roles={
            "re.compile('^steps$', re.IGNORECASE)": role_steps,
            "re.compile('^(?:llm|workbench)$', re.IGNORECASE)": role_workbench,
        },
    )

    asyncio.run(harness.click_autoworkbench_tab(page, "steps"))
    asyncio.run(harness.click_autoworkbench_tab(page, "workbench"))

    assert page.test_id_requests == ["steps-tab", "llm-tab"]
    assert testid_steps.wait_for_count == 1
    assert testid_steps.click_count == 1
    assert testid_workbench.wait_for_count == 1
    assert testid_workbench.click_count == 1
    assert role_steps.wait_for_count == 0
    assert role_steps.click_count == 0
    assert role_workbench.wait_for_count == 0
    assert role_workbench.click_count == 0


def test_click_autoworkbench_tab_falls_back_to_role_names_when_test_id_missing() -> None:
    steps_role = _TrackedTabLocator("Steps", visible=True)
    workbench_role = _TrackedTabLocator("LLM", visible=True)

    class _RoleOnlyPage:
        def __init__(self) -> None:
            self.role_requests: list[str] = []
            self.call_count = 0

        def get_by_role(self, role: str, name: object) -> _TrackedTabLocator:  # noqa: ARG002
            self.call_count += 1
            self.role_requests.append(str(name))
            return steps_role if self.call_count == 1 else workbench_role

    page = _RoleOnlyPage()

    asyncio.run(harness.click_autoworkbench_tab(page, "steps"))
    asyncio.run(harness.click_autoworkbench_tab(page, "workbench"))

    assert page.role_requests == [
        "re.compile('^steps$', re.IGNORECASE)",
        "re.compile('^(?:llm|workbench)$', re.IGNORECASE)",
    ]
    assert steps_role.click_count == 1
    assert workbench_role.click_count == 1


def test_wait_for_autoworkbench_state_text_uses_shadow_root_when_present() -> None:
    shadow_state = _TrackedTabLocator("shadow-state", visible=True, text="PLAN REVIEW")
    shadow_root = _TrackedTabLocator("shadow-root", visible=True, count_value=1, nested={".ide-hd-state": shadow_state})
    fallback_state = _TrackedTabLocator("fallback-state", visible=True, text="PLAN REVIEW")
    page = _TrackedTabPage(
        test_ids={},
        roles={},
        locators={
            "#aw-root": shadow_root,
            "#autoworkbench-root .ide-panel .ide-hd-state": fallback_state,
        },
    )

    asyncio.run(harness.wait_for_autoworkbench_state_text(page, "plan review", timeout_ms=200))

    assert page.locator_requests == ["#aw-root"]
    assert shadow_root.locator_requests == [".ide-hd-state"]
    assert shadow_state.wait_for_count == 1
    assert fallback_state.wait_for_count == 0


def test_wait_for_autoworkbench_state_text_falls_back_when_shadow_root_missing() -> None:
    shadow_root = _TrackedTabLocator("shadow-root", visible=False, count_value=0)
    fallback_state = _TrackedTabLocator("fallback-state", visible=True, text="PLAN REVIEW")
    page = _TrackedTabPage(
        test_ids={},
        roles={},
        locators={
            "#aw-root": shadow_root,
            "#autoworkbench-root .ide-panel .ide-hd-state": fallback_state,
        },
    )

    asyncio.run(harness.wait_for_autoworkbench_state_text(page, "plan review", timeout_ms=200))

    assert page.locator_requests == ["#aw-root", "#autoworkbench-root .ide-panel .ide-hd-state"]
    assert shadow_root.locator_requests == []
    assert fallback_state.wait_for_count == 1


def test_wait_for_autoworkbench_state_text_accepts_state_families_when_state_moves_fast() -> None:
    shadow_state = _ChangingTextLocator(["PLANNING…", "COMPLETED"])
    shadow_root = _TrackedTabLocator("shadow-root", visible=True, count_value=1, nested={".ide-hd-state": shadow_state})
    page = _TrackedTabPage(
        test_ids={},
        roles={},
        locators={
            "#aw-root": shadow_root,
        },
    )

    asyncio.run(harness.wait_for_autoworkbench_state_text(page, ("executing", "completed"), timeout_ms=200))

    assert page.locator_requests == ["#aw-root"]
    assert shadow_root.locator_requests == [".ide-hd-state"]
    assert shadow_state.wait_for_count == 1
    assert shadow_state.inner_text_calls >= 2


def test_wait_for_autoworkbench_plan_ready_uses_confirm_plan_visibility_and_shadow_state() -> None:
    confirm_plan = _TrackedTabLocator("Confirm Plan", visible=True)
    shadow_state = _TrackedTabLocator("shadow-state", visible=True, text="AWAITING CONFIRMATION")
    shadow_root = _TrackedTabLocator("shadow-root", visible=True, count_value=1, nested={".ide-hd-state": shadow_state})
    fallback_state = _TrackedTabLocator("fallback-state", visible=True, text="PLAN REVIEW")
    page = _TrackedTabPage(
        test_ids={},
        roles={"Confirm Plan": confirm_plan},
        locators={
            "#aw-root": shadow_root,
            "#autoworkbench-root .ide-panel .ide-hd-state": fallback_state,
        },
    )

    asyncio.run(harness.wait_for_autoworkbench_plan_ready(page, timeout_ms=200))

    assert page.role_requests == ["Confirm Plan"]
    assert confirm_plan.wait_for_count == 1
    assert page.locator_requests == ["#aw-root"]
    assert shadow_root.locator_requests == [".ide-hd-state"]
    assert shadow_state.wait_for_count == 1
    assert fallback_state.wait_for_count == 0


def test_wait_for_autoworkbench_execution_progress_accepts_recorded_state() -> None:
    shadow_state = _TrackedTabLocator("shadow-state", visible=True, text="RECORDED")
    shadow_root = _TrackedTabLocator("shadow-root", visible=True, count_value=1, nested={".ide-hd-state": shadow_state})
    page = _TrackedTabPage(
        test_ids={},
        roles={},
        locators={
            "#aw-root": shadow_root,
        },
    )

    asyncio.run(harness.wait_for_autoworkbench_execution_progress(page, timeout_ms=200))

    assert page.locator_requests == ["#aw-root"]
    assert shadow_root.locator_requests == [".ide-hd-state"]
    assert shadow_state.wait_for_count == 1


def test_failure_artifacts_record_state_timeout_reason_backend_markers_and_artifact_path(tmp_path: Path) -> None:
    shadow_state = _TrackedTabLocator("shadow-state", visible=True, text="RECOVERY NEEDED")
    shadow_root = _TrackedTabLocator("shadow-root", visible=True, count_value=1, nested={".ide-hd-state": shadow_state})
    active_tab = _TrackedTabLocator("active-tab", visible=True, text="Workbench")
    page = _TrackedTabPage(
        test_ids={},
        roles={},
        locators={
            "#aw-root": shadow_root,
            ".ide-tab.active": active_tab,
            "#autoworkbench-root .ide-panel .ide-hd-state": _TrackedTabLocator("fallback-state", visible=True, text="LEGACY"),
        },
    )
    backend_stdout_text = (
        "[PHASE] awaiting_confirmation -> executing\n"
        "[CONFIRMED_PLAN] plan accepted\n"
        "[EXECUTION_CONTRACT] execution contract accepted\n"
    )
    session = _make_failure_session(tmp_path, page=page, backend_stdout_text=backend_stdout_text)

    with pytest.raises(TimeoutError) as excinfo:
        asyncio.run(harness.wait_for_autoworkbench_state_text(page, ("executing", "completed"), timeout_ms=200))

    context = asyncio.run(session.save_failure_artifacts(str(excinfo.value), stage="execution_started"))
    failure_text = (tmp_path / "failure.txt").read_text(encoding="utf-8")
    failure_context = json.loads((tmp_path / "failure-context.json").read_text(encoding="utf-8"))

    assert context["artifact_dir"] == str(tmp_path)
    assert "Timed out waiting for text in ['executing', 'completed']" in context["reason"]
    assert "last observed text='RECOVERY NEEDED'" in context["reason"]
    assert context["page_state"]["active_mode"] == "RECOVERY NEEDED"
    assert failure_context["page_state"]["active_mode"] == "RECOVERY NEEDED"
    assert context["backend_lifecycle_markers"]["[PHASE]"] == "[PHASE] awaiting_confirmation -> executing"
    assert context["backend_lifecycle_markers"]["[CONFIRMED_PLAN]"] == "[CONFIRMED_PLAN] plan accepted"
    assert context["backend_lifecycle_markers"]["[EXECUTION_CONTRACT]"] == "[EXECUTION_CONTRACT] execution contract accepted"
    assert "artifact_dir=" in failure_text
    assert "last observed text='RECOVERY NEEDED'" in failure_text


def test_capture_picker_arm_evidence_reports_overlay_shadow_and_selector_source() -> None:
    shadow_root = _TrackedTabLocator("aw-root", visible=True, count_value=1)
    steps_test_id = _TrackedTabLocator("steps-tab", visible=True, count_value=1)
    steps_role = _TrackedTabLocator("steps-role", visible=True, count_value=1)
    page = _TrackedTabPage(
        test_ids={"steps-tab": steps_test_id},
        roles={
            "re.compile('^steps$', re.IGNORECASE)": steps_role,
        },
        locators={
            "#aw-root": shadow_root,
            "#autoworkbench-root .ide-panel": _TrackedTabLocator("legacy-panel", visible=True, count_value=0),
        },
    )

    evidence = asyncio.run(harness.capture_picker_arm_evidence(page))

    assert evidence["overlay_loaded"] is True
    assert evidence["shadow_dom_root_found"] is True
    assert evidence["steps_tab_test_id_found"] is True
    assert evidence["steps_tab_role_found"] is True
    assert evidence["steps_tab_found"] is True
    assert evidence["steps_tab_selector_source"] == "test_id"
    assert evidence["steps_tab_clicked"] is False
    assert evidence["picker_state_changed"] is False


def test_save_failure_artifacts_persists_picker_arm_evidence_and_stage_history(tmp_path: Path) -> None:
    session = _make_failure_session(tmp_path)
    session.log_stage_ok("overlay_loaded")
    session.current_stage = "picker_armed"
    session.record_picker_arm_evidence(
        overlay_loaded=True,
        shadow_dom_root_found=True,
        steps_tab_found=True,
        steps_tab_clicked=False,
        picker_state_changed=False,
    )

    context = asyncio.run(session.save_failure_artifacts("Timed out waiting for picker arm", stage="picker_armed"))
    persisted = json.loads((tmp_path / "failure-context.json").read_text(encoding="utf-8"))

    assert context["stage_history"] == ["overlay_loaded", "picker_armed"]
    assert persisted["stage_history"] == ["overlay_loaded", "picker_armed"]
    assert context["picker_arm_evidence"] == {
        "overlay_loaded": True,
        "shadow_dom_root_found": True,
        "steps_tab_found": True,
        "steps_tab_clicked": False,
        "picker_state_changed": False,
    }
    assert persisted["picker_arm_evidence"] == context["picker_arm_evidence"]


def test_run_stage_stops_when_backend_reports_terminal_runtime_rejected(tmp_path: Path) -> None:
    rejection_marker = (
        "[RUNTIME_REJECTED] "
        "rejection_code=PLANNING_NO_PROGRESS phase=failed purpose=step_plan_normalizer "
        "recoverable=false terminal=true"
    )
    backend_stdout_text = (
        "[PHASE] from=planning to=failed reason=planning_no_progress step_id=none\n"
        f"{rejection_marker}\n"
    )
    session = _make_failure_session(tmp_path, backend_stdout_text=backend_stdout_text)
    action_started = False

    async def wait_for_plan_review() -> str:
        nonlocal action_started
        action_started = True
        await asyncio.sleep(1.0)
        return "plan_ready"

    with pytest.raises(harness.BackendTerminalRuntimeRejectionError, match="PLANNING_NO_PROGRESS"):
        asyncio.run(session.run_stage("llm_response_seen", 5.0, wait_for_plan_review))

    failure_context = json.loads((tmp_path / "failure-context.json").read_text(encoding="utf-8"))
    assert failure_context["reason"].startswith(rejection_marker)
    assert failure_context["observed_event_types"] == ["runtime_rejected"]
    assert failure_context["event_evidence"]["observed_event_types"] == ["runtime_rejected"]
    assert failure_context["event_evidence"]["runtime_rejected_marker"] == rejection_marker
    assert failure_context["backend_lifecycle_markers"]["[RUNTIME_REJECTED]"] == rejection_marker
    assert failure_context["backend_lifecycle_markers"]["[PHASE]"] == "[PHASE] from=planning to=failed reason=planning_no_progress step_id=none"


class _ChangingTextLocator:
    def __init__(self, texts: list[str], *, visible: bool = True) -> None:
        self.texts = texts
        self.visible = visible
        self.wait_for_count = 0
        self.inner_text_calls = 0

    @property
    def first(self) -> "_ChangingTextLocator":
        return self

    async def wait_for(self, state: str, timeout: int | None = None) -> None:  # noqa: ARG002
        self.wait_for_count += 1
        if state == "visible" and not self.visible:
            raise TimeoutError("locator is not visible")

    async def inner_text(self) -> str:
        index = min(self.inner_text_calls, len(self.texts) - 1)
        self.inner_text_calls += 1
        return self.texts[index]


class _ChangingCountLocator:
    def __init__(self, counts: list[int]) -> None:
        self.counts = counts
        self.count_calls = 0

    @property
    def first(self) -> "_ChangingCountLocator":
        return self

    async def count(self) -> int:
        index = min(self.count_calls, len(self.counts) - 1)
        self.count_calls += 1
        return self.counts[index]


def test_wait_for_locator_text_polls_locator_text_until_expected_value_appears() -> None:
    locator = _ChangingTextLocator(["PLANNING…", "PLAN REVIEW"])

    asyncio.run(harness.wait_for_locator_text(locator, "plan review", timeout_ms=200))

    assert locator.wait_for_count == 1
    assert locator.inner_text_calls >= 2


def test_wait_for_locator_count_polls_until_expected_count_appears() -> None:
    locator = _ChangingCountLocator([1, 2])

    asyncio.run(harness.wait_for_locator_count(locator, 2, timeout_ms=200))

    assert locator.count_calls >= 2


def test_extract_latest_recording_step_payload_prefers_final_structured_payload() -> None:
    assert_line = 'await expect(page.getByTestId("get-started")).toBeVisible();'
    click_line = 'await page.getByTestId("get-started").click();'
    click_only_payload = {
        "step_id": "step-1",
        "step_number": 1,
        "action": "click",
        "generated_line": click_line,
        "children": [
            {
                "operation_id": "op_1",
                "type": "click",
                "code_lines": [click_line],
                "status": "success",
            }
        ],
    }
    final_payload = {
        "step_id": "step-1",
        "step_number": 1,
        "action": "click",
        "generated_line": click_line,
        "children": [
            {
                "operation_id": "op_2",
                "type": "assert",
                "code_lines": [assert_line],
                "status": "success",
            },
            {
                "operation_id": "op_1",
                "type": "click",
                "code_lines": [click_line],
                "status": "success",
            },
        ],
    }
    backend_logs = "\n".join(
        [
            "[PHASE] from=awaiting_confirmation to=planning reason=correction step_id=step-1",
            f"[AGENT] recording step: {json.dumps(click_only_payload, sort_keys=True)}",
            "[CODE_UPDATE] step_id=step-1 operation_id=op_1 lines=1",
            f"[AGENT] recording step: {json.dumps(final_payload, sort_keys=True)}",
            "[CODE_UPDATE] step_id=step-1 operation_id=op_2 lines=2",
        ]
    )

    payload = harness.extract_latest_recording_step_payload(backend_logs)
    assert payload is not None
    assert payload["step_id"] == "step-1"
    assert [child["type"] for child in payload["children"]] == ["assert", "click"]
    assert harness.recording_step_code_lines(payload) == [assert_line, click_line]

    click_only_lines = harness.recording_step_code_lines(click_only_payload)
    assert click_only_lines == [click_line]
    with pytest.raises(AssertionError):
        assert click_only_lines == [assert_line, click_line]


class _LeakyFailurePage(_FakePage):
    def __init__(self, url: str, error_message: str) -> None:
        super().__init__(url=url)
        self._error_message = error_message

    def locator(self, selector: str) -> _FakeLocator:
        raise RuntimeError(self._error_message)


class _FakeBrowser:
    async def close(self) -> None:
        return None


class _FakePlaywright:
    async def stop(self) -> None:
        return None


def _make_failure_session(
    tmp_path: Path,
    page: object | None = None,
    *,
    backend_stdout_text: str = "[PLAN_READY] backend ready\n",
) -> harness.E2ESession:
    stdout_path = tmp_path / "backend.stdout.log"
    stderr_path = tmp_path / "backend.stderr.log"
    stdout_path.write_text(backend_stdout_text, encoding="utf-8")
    stderr_path.write_text("", encoding="utf-8")
    backend = SimpleNamespace(
        name="autoworkbench-backend",
        stdout_path=stdout_path,
        stderr_path=stderr_path,
        stop=lambda: None,
        poll=lambda: None,
        returncode=None,
    )
    static_server = SimpleNamespace(stop=lambda: None)
    return harness.E2ESession(
        artifact_dir=tmp_path,
        test_name="failure_artifacts",
        run_id="run-123",
        created_at="2026-05-07T00:00:00Z",
        static_server=static_server,
        backend=backend,
        playwright=_FakePlaywright(),
        browser=_FakeBrowser(),
        context=SimpleNamespace(),
        page=page if page is not None else _FakePage(),
        console_entries=[],
    )


def _make_static_server_process(tmp_path: Path, port: int, stop_calls: list[int] | None = None) -> SimpleNamespace:
    def stop(timeout_s: float = 10.0) -> None:  # noqa: ARG001
        if stop_calls is not None:
            stop_calls.append(port)

    return SimpleNamespace(
        port=port,
        base_url=f"http://127.0.0.1:{port}",
        stdout_path=tmp_path / f"static-server-{port}.stdout.log",
        stderr_path=tmp_path / f"static-server-{port}.stderr.log",
        stop=stop,
        poll=lambda: None,
        returncode=None,
    )


def test_resolve_e2e_port_prefers_explicit_value_then_env(monkeypatch) -> None:
    monkeypatch.setenv("AUTOWORKBENCH_E2E_BACKEND_PORT", "53101")

    assert (
        harness.resolve_e2e_port(
            53100,
            env_name="AUTOWORKBENCH_E2E_BACKEND_PORT",
            default=8765,
        )
        == 53100
    )
    assert (
        harness.resolve_e2e_port(
            None,
            env_name="AUTOWORKBENCH_E2E_BACKEND_PORT",
            default=8765,
        )
        == 53101
    )


def test_resolve_e2e_port_rejects_invalid_env_value(monkeypatch) -> None:
    monkeypatch.setenv("AUTOWORKBENCH_E2E_BACKEND_PORT", "not-a-number")

    with pytest.raises(RuntimeError, match="must be an integer"):
        harness.resolve_e2e_port(
            None,
            env_name="AUTOWORKBENCH_E2E_BACKEND_PORT",
            default=8765,
        )


def test_start_static_server_respects_configured_port_env(monkeypatch, tmp_path: Path) -> None:
    captured: dict[str, object] = {}

    monkeypatch.setenv("AUTOWORKBENCH_E2E_PORT", "53123")

    def fake_reserve_tcp_port(host: str, port: int) -> int:
        captured.setdefault("reserve_calls", []).append((host, port))
        return port

    def fake_start_managed_process(**kwargs):
        captured["port"] = kwargs["port"]
        captured["command"] = kwargs["command"]
        return _make_static_server_process(tmp_path, kwargs["port"])

    def fake_wait_for_http_url(url: str, *, label: str, process=None, timeout_s: float = 0.0) -> None:
        captured["wait_url"] = url
        captured["wait_label"] = label
        captured["wait_port"] = getattr(process, "port", None)
        captured["wait_timeout_s"] = timeout_s

    monkeypatch.setattr(harness, "_reserve_tcp_port", fake_reserve_tcp_port)
    monkeypatch.setattr(harness, "start_managed_process", fake_start_managed_process)
    monkeypatch.setattr(harness, "wait_for_http_url", fake_wait_for_http_url)

    process = harness.start_static_server(tmp_path, tmp_path)

    assert process.port == 53123
    assert process.base_url == "http://127.0.0.1:53123"
    assert captured["reserve_calls"] == [("127.0.0.1", 53123)]
    assert captured["port"] == 53123
    assert captured["wait_url"] == "http://127.0.0.1:53123/index.html"
    assert captured["wait_label"] == "static server"
    assert captured["wait_port"] == 53123


def test_start_static_server_falls_back_to_dynamic_port_when_default_is_blocked(
    monkeypatch,
    tmp_path: Path,
) -> None:
    captured: dict[str, object] = {}
    stop_calls: list[int] = []

    def fake_reserve_tcp_port(host: str, port: int) -> int:
        captured.setdefault("reserve_calls", []).append((host, port))
        if port == 0:
            return 54321
        return port

    def fake_start_managed_process(**kwargs):
        captured.setdefault("start_ports", []).append(kwargs["port"])
        return _make_static_server_process(tmp_path, kwargs["port"], stop_calls=stop_calls)

    def fake_wait_for_http_url(url: str, *, label: str, process=None, timeout_s: float = 0.0) -> None:
        captured.setdefault("wait_calls", []).append((url, label, getattr(process, "port", None), timeout_s))
        if getattr(process, "port", None) == harness.DEFAULT_E2E_STATIC_SERVER_PORT:
            raise harness.E2EStartupBlockedError("default bind blocked")

    monkeypatch.setattr(harness, "_reserve_tcp_port", fake_reserve_tcp_port)
    monkeypatch.setattr(harness, "start_managed_process", fake_start_managed_process)
    monkeypatch.setattr(harness, "wait_for_http_url", fake_wait_for_http_url)

    process = harness.start_static_server(tmp_path, tmp_path)

    assert captured["reserve_calls"] == [("127.0.0.1", harness.DEFAULT_E2E_STATIC_SERVER_PORT), ("127.0.0.1", 0)]
    assert captured["start_ports"] == [harness.DEFAULT_E2E_STATIC_SERVER_PORT, 54321]
    assert stop_calls == [harness.DEFAULT_E2E_STATIC_SERVER_PORT]
    assert process.port == 54321
    assert process.base_url == "http://127.0.0.1:54321"
    assert captured["wait_calls"] == [
        ("http://127.0.0.1:8000/index.html", "static server", 8000, 10.0),
        ("http://127.0.0.1:54321/index.html", "static server", 54321, 10.0),
    ]


def test_start_static_server_raises_typed_blocker_when_all_local_binds_fail(monkeypatch, tmp_path: Path) -> None:
    captured: dict[str, object] = {}

    def fake_reserve_tcp_port(host: str, port: int) -> int:
        captured.setdefault("reserve_calls", []).append((host, port))
        raise OSError("bind blocked")

    monkeypatch.setattr(harness, "_reserve_tcp_port", fake_reserve_tcp_port)

    with pytest.raises(harness.E2EStartupBlockedError, match=r"127\.0\.0\.1:8000 or a dynamic local port"):
        harness.start_static_server(tmp_path, tmp_path)

    assert captured["reserve_calls"] == [("127.0.0.1", harness.DEFAULT_E2E_STATIC_SERVER_PORT), ("127.0.0.1", 0)]


def test_start_autoworkbench_backend_uses_selected_port_for_env_and_readiness(monkeypatch, tmp_path: Path) -> None:
    captured: dict[str, object] = {}
    expected_repo_key = "sk-repo-key"

    monkeypatch.setenv("OPENAI_API_KEY", "sk-stale-shell-key")
    monkeypatch.setattr(
        harness,
        "_load_repo_env_values",
        lambda: {
            "OPENAI_API_KEY": expected_repo_key,
            "REPO_ONLY_FLAG": "enabled",
        },
    )

    def fake_start_managed_process(**kwargs):
        captured["command"] = kwargs["command"]
        captured["env"] = kwargs["env"]
        captured["port"] = kwargs["port"]
        return SimpleNamespace(
            port=kwargs["port"],
            base_url=f"http://127.0.0.1:{kwargs['port']}",
            stdout_path=tmp_path / "backend.stdout.log",
            stderr_path=tmp_path / "backend.stderr.log",
            poll=lambda: None,
            returncode=None,
        )

    def fake_wait_for_http_url(url: str, *, label: str, process=None, timeout_s: float = 0.0) -> None:
        captured["wait_url"] = url
        captured["wait_label"] = label
        captured["wait_process_port"] = getattr(process, "port", None)
        captured["wait_timeout_s"] = timeout_s

    monkeypatch.setattr(harness, "start_managed_process", fake_start_managed_process)
    monkeypatch.setattr(harness, "wait_for_http_url", fake_wait_for_http_url)

    process = harness.start_autoworkbench_backend(
        start_url="http://127.0.0.1:9999/index.html",
        artifact_dir=tmp_path,
        port=53211,
        remote_debugging_port=53212,
    )

    assert process.port == 53211
    assert captured["port"] == 53211
    assert captured["env"]["OPENAI_API_KEY"] == expected_repo_key
    assert captured["env"]["REPO_ONLY_FLAG"] == "enabled"
    assert captured["env"]["PORT"] == "53211"
    assert captured["env"]["START_URL"] == "http://127.0.0.1:9999/index.html"
    assert captured["env"]["AUTOWORKBENCH_REMOTE_DEBUGGING_PORT"] == "53212"
    assert captured["wait_url"] == "http://127.0.0.1:53211/docs"
    assert captured["wait_label"] == "AutoWorkbench backend"
    assert captured["wait_process_port"] == 53211

    command = captured["command"]
    assert command[:2] == [sys.executable, "-c"]
    assert "dotenv.load_dotenv = lambda *args, **kwargs: None" in command[2]
    assert "runpy.run_module('server', run_name='__main__')" in command[2]


def test_wait_for_http_url_classifies_permission_error(tmp_path: Path) -> None:
    stdout_path = tmp_path / "stdout.log"
    stderr_path = tmp_path / "stderr.log"
    stdout_path.write_text("", encoding="utf-8")
    stderr_path.write_text("PermissionError [Errno 1] Operation not permitted\n", encoding="utf-8")

    process = SimpleNamespace(
        name="autoworkbench-backend",
        stdout_path=stdout_path,
        stderr_path=stderr_path,
        poll=lambda: 1,
        returncode=1,
    )

    with pytest.raises(harness.E2EStartupBlockedError, match="local socket allocation is blocked"):
        harness.wait_for_http_url(
            "http://127.0.0.1:8765/docs",
            label="AutoWorkbench backend",
            process=process,
            timeout_s=0.01,
        )


def test_default_artifact_paths_include_normalized_evidence_files() -> None:
    assert harness.DEFAULT_E2E_ARTIFACT_PATHS["backend_log"] == "backend.log"
    assert harness.DEFAULT_E2E_ARTIFACT_PATHS["frontend_log"] == "frontend.log"
    assert harness.DEFAULT_E2E_ARTIFACT_PATHS["browser_console_log"] == "browser-console.log"
    assert harness.DEFAULT_E2E_ARTIFACT_PATHS["summary"] == "summary.md"


def test_write_artifact_manifest_creates_required_keys_and_status(tmp_path: Path) -> None:
    manifest = harness.write_artifact_manifest(
        artifact_dir=tmp_path,
        test_name="fresh_artifact_baseline",
        created_at="2026-05-07T00:00:00Z",
        status="running",
        artifacts={
            "manifest": "manifest.json",
            "test_result": "test-result.json",
            "backend_stdout": "backend.stdout.log",
        },
    )

    manifest_path = tmp_path / "manifest.json"
    assert manifest_path.exists()

    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert payload == manifest
    assert payload["schema_version"] == harness.E2E_ARTIFACT_SCHEMA_VERSION
    assert payload["test_name"] == "fresh_artifact_baseline"
    assert payload["run_id"] == tmp_path.name
    assert payload["artifact_dir"] == str(tmp_path)
    assert payload["created_at"] == "2026-05-07T00:00:00Z"
    assert payload["status"] == "running"
    assert payload["artifacts"]["backend_stdout"] == "backend.stdout.log"
    assert payload["artifacts"]["test_result"] == "test-result.json"


def test_write_artifact_manifest_records_normalized_evidence_metadata(tmp_path: Path) -> None:
    manifest = harness.write_artifact_manifest(
        artifact_dir=tmp_path,
        test_name="fresh_artifact_baseline",
        created_at="2026-05-07T00:00:00Z",
        status="running",
        artifacts=NORMALIZED_EVIDENCE_ARTIFACTS,
        file_hashes=NORMALIZED_EVIDENCE_FILE_HASHES,
        optional_absence_notes=NORMALIZED_EVIDENCE_NOTES,
    )

    payload = json.loads((tmp_path / "manifest.json").read_text(encoding="utf-8"))
    assert payload == manifest
    assert payload["artifacts"] == NORMALIZED_EVIDENCE_ARTIFACTS
    assert payload["file_hashes"] == NORMALIZED_EVIDENCE_FILE_HASHES
    assert payload["optional_absence_notes"] == NORMALIZED_EVIDENCE_NOTES


def test_write_test_result_creates_failed_result_with_error_summary(tmp_path: Path) -> None:
    result = harness.write_test_result(
        artifact_dir=tmp_path,
        test_name="fresh_artifact_baseline",
        status="failed",
        error_summary="Timeout waiting for overlay ready",
    )

    result_path = tmp_path / "test-result.json"
    assert result_path.exists()

    payload = json.loads(result_path.read_text(encoding="utf-8"))
    assert payload == result
    assert payload["schema_version"] == harness.E2E_ARTIFACT_SCHEMA_VERSION
    assert payload["test_name"] == "fresh_artifact_baseline"
    assert payload["run_id"] == tmp_path.name
    assert payload["artifact_dir"] == str(tmp_path)
    assert payload["status"] == "failed"
    assert payload["error_summary"] == "Timeout waiting for overlay ready"


def test_finalize_test_result_writes_normalized_evidence_files(tmp_path: Path) -> None:
    artifact_texts = {
        "backend.log": "backend stdout\nbackend stderr\n",
        "frontend.log": "frontend console\n",
        "browser-console.log": "[console:log] browser ready\n",
        "summary.md": "# Summary\n\nNormalized evidence baseline.\n",
    }

    manifest, result = harness.finalize_test_result(
        artifact_dir=tmp_path,
        test_name="fresh_artifact_baseline",
        created_at="2026-05-07T00:00:00Z",
        status="unknown",
        error_summary=None,
        artifacts=NORMALIZED_EVIDENCE_ARTIFACTS,
        artifact_texts=artifact_texts,
        file_hashes=NORMALIZED_EVIDENCE_FILE_HASHES,
        optional_absence_notes=NORMALIZED_EVIDENCE_NOTES,
    )

    manifest_path = tmp_path / "manifest.json"
    result_path = tmp_path / "test-result.json"
    assert manifest_path.exists()
    assert result_path.exists()
    assert (tmp_path / "backend.log").exists()
    assert (tmp_path / "frontend.log").exists()
    assert (tmp_path / "browser-console.log").exists()
    assert (tmp_path / "summary.md").exists()
    assert (tmp_path / "backend.log").read_text(encoding="utf-8") == artifact_texts["backend.log"]
    assert (tmp_path / "frontend.log").read_text(encoding="utf-8") == artifact_texts["frontend.log"]
    assert (tmp_path / "browser-console.log").read_text(encoding="utf-8") == artifact_texts["browser-console.log"]
    assert (tmp_path / "summary.md").read_text(encoding="utf-8") == artifact_texts["summary.md"]

    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    result_payload = json.loads(result_path.read_text(encoding="utf-8"))
    assert payload == manifest
    assert result_payload == result
    assert payload["artifacts"] == NORMALIZED_EVIDENCE_ARTIFACTS
    assert payload["file_hashes"] == NORMALIZED_EVIDENCE_FILE_HASHES
    assert payload["optional_absence_notes"] == NORMALIZED_EVIDENCE_NOTES
    assert payload["status"] == "unknown"
    assert result_payload["status"] == "unknown"


def test_artifact_writers_do_not_require_live_runtime_dependencies(
    monkeypatch,
    tmp_path: Path,
) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    manifest, result = harness.finalize_test_result(
        artifact_dir=tmp_path,
        test_name="fresh_artifact_baseline",
        status="unknown",
        error_summary=None,
        created_at="2026-05-07T00:00:00Z",
        artifacts=NORMALIZED_EVIDENCE_ARTIFACTS,
        artifact_texts={
            "backend.log": "backend stdout\n",
            "frontend.log": "frontend console\n",
            "browser-console.log": "browser console\n",
            "summary.md": "# Summary\n\nNormalized evidence baseline.\n",
        },
        file_hashes=NORMALIZED_EVIDENCE_FILE_HASHES,
        optional_absence_notes=NORMALIZED_EVIDENCE_NOTES,
    )

    assert (tmp_path / "manifest.json").exists()
    assert (tmp_path / "test-result.json").exists()
    assert (tmp_path / "backend.log").exists()
    assert (tmp_path / "frontend.log").exists()
    assert (tmp_path / "browser-console.log").exists()
    assert (tmp_path / "summary.md").exists()
    assert (tmp_path / "backend.log").read_text(encoding="utf-8") == "backend stdout\n"
    assert (tmp_path / "frontend.log").read_text(encoding="utf-8") == "frontend console\n"
    assert (tmp_path / "browser-console.log").read_text(encoding="utf-8") == "browser console\n"
    assert (tmp_path / "summary.md").read_text(encoding="utf-8") == "# Summary\n\nNormalized evidence baseline.\n"
    assert manifest["artifacts"] == NORMALIZED_EVIDENCE_ARTIFACTS
    assert manifest["file_hashes"] == NORMALIZED_EVIDENCE_FILE_HASHES
    assert manifest["optional_absence_notes"] == NORMALIZED_EVIDENCE_NOTES
    assert manifest["status"] == "unknown"
    assert result["status"] == "unknown"


def test_wait_for_event_filters_captured_events_by_type() -> None:
    events = [
        _event("run_started"),
        _event("plan_ready", plan={"steps": 1}),
        _event("step_recorded", step_id="step-1"),
    ]

    matched = harness.wait_for_event(events, "plan_ready")

    assert matched["type"] == "plan_ready"
    assert matched["run_id"] == "run-123"
    assert matched["plan"] == {"steps": 1}


def test_assert_sequence_enforces_required_event_order() -> None:
    events = [
        _event("run_started"),
        _event("plan_ready"),
        _event("step_recorded"),
    ]

    harness.assert_sequence(events, ["run_started", "plan_ready", "step_recorded"])


def test_assert_no_event_passes_when_forbidden_event_absent() -> None:
    events = [
        _event("run_started"),
        _event("plan_ready"),
        _event("step_recorded"),
    ]

    harness.assert_no_event(events, "recovery_needed")


def test_assert_no_event_fails_with_clear_message_when_forbidden_event_present() -> None:
    events = [
        _event("run_started"),
        _event("plan_ready"),
        _event("recovery_needed", error_summary="missing required evidence"),
    ]

    with pytest.raises(AssertionError, match="recovery_needed"):
        harness.assert_no_event(events, "recovery_needed")


def test_wait_for_event_fails_with_clear_message_when_expected_event_missing() -> None:
    events = [
        _event("run_started"),
        _event("step_recorded"),
    ]

    with pytest.raises(AssertionError, match="plan_ready"):
        harness.wait_for_event(events, "plan_ready")


def test_collect_events_can_model_capture_before_action_without_browser_server(
    monkeypatch,
    tmp_path: Path,
) -> None:
    run_id = "run-123"
    run_dir = tmp_path / run_id
    run_dir.mkdir()
    (run_dir / "events.ndjson").write_text(
        "\n".join(
            [
                json.dumps(_event("plan_ready", captured_at="before_action")),
                json.dumps(_event("step_recorded", captured_at="after_action")),
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    monkeypatch.setattr(harness, "RESULTS_ROOT", tmp_path)

    events = harness.collect_events(run_id)

    assert [event["type"] for event in events] == ["plan_ready", "step_recorded"]
    assert events[0]["captured_at"] == "before_action"
    assert events[1]["captured_at"] == "after_action"


def test_finalize_test_result_can_record_event_evidence_presence_and_absence_metadata(
    tmp_path: Path,
) -> None:
    event_evidence = {
        "present": ["events.ndjson", "commands.json"],
        "missing": ["rejections.json"],
    }

    manifest, result = harness.finalize_test_result(
        artifact_dir=tmp_path,
        test_name="fresh_artifact_baseline",
        status="failed",
        error_summary="expected event missing",
        artifacts=NORMALIZED_EVIDENCE_ARTIFACTS,
        artifact_texts={
            "summary.md": "# Summary\n\nEvent evidence metadata baseline.\n",
        },
        event_evidence=event_evidence,
    )

    assert manifest["event_evidence"] == event_evidence
    assert result["event_evidence"] == event_evidence


def test_finalize_test_result_writes_events_ndjson_and_lists_it_in_manifest(
    tmp_path: Path,
) -> None:
    event_records = [
        _event("run_started"),
        _event("plan_ready", plan={"steps": 1}),
    ]

    manifest, result = harness.finalize_test_result(
        artifact_dir=tmp_path,
        test_name="events_artifact_baseline",
        status="unknown",
        error_summary=None,
        artifacts={
            "manifest": "manifest.json",
            "test_result": "test-result.json",
            "summary": "summary.md",
            "events": "events.ndjson",
        },
        artifact_texts={
            "summary.md": "# Summary\n\nEvents emission baseline.\n",
        },
        event_records=event_records,
        event_evidence={
            "events": "events.ndjson",
            "event_count": len(event_records),
        },
    )

    events_path = tmp_path / "events.ndjson"
    assert events_path.exists()
    lines = events_path.read_text(encoding="utf-8").splitlines()
    assert [json.loads(line)["type"] for line in lines] == ["run_started", "plan_ready"]
    assert len(lines) == 2
    assert "events.ndjson" in manifest["artifacts"].values()
    assert manifest["file_hashes"]["events.ndjson"].startswith("sha256:")
    assert manifest["event_evidence"]["events"] == "events.ndjson"
    assert result["event_evidence"]["events"] == "events.ndjson"
    assert "events.ndjson" in (tmp_path / "summary.md").read_text(encoding="utf-8")


def test_finalize_test_result_omits_deferred_events_note_when_events_ndjson_is_written(
    tmp_path: Path,
) -> None:
    event_records = [
        _event("run_started"),
        _event("plan_ready"),
    ]

    manifest, result = harness.finalize_test_result(
        artifact_dir=tmp_path,
        test_name="events_artifact_baseline",
        status="unknown",
        error_summary=None,
        artifacts={
            "manifest": "manifest.json",
            "test_result": "test-result.json",
            "summary": "summary.md",
            "events": "events.ndjson",
        },
        artifact_texts={
            "summary.md": "# Summary\n\nEvents emission baseline.\n",
        },
        event_records=event_records,
        event_evidence={
            "events": "events.ndjson",
        },
    )

    summary = (tmp_path / "summary.md").read_text(encoding="utf-8")

    assert all("events.ndjson" not in note for note in manifest["optional_absence_notes"])
    assert result["event_evidence"]["events"] == "events.ndjson"
    assert "events.ndjson" in summary


def test_finalize_test_result_writes_commands_json_and_lists_it_in_manifest(
    tmp_path: Path,
) -> None:
    command_records = [
        {"type": "run_started", "run_id": "run-123"},
        {"type": "plan_ready", "run_id": "run-123", "plan_id": "plan-1"},
    ]

    manifest, result = harness.finalize_test_result(
        artifact_dir=tmp_path,
        test_name="commands_artifact_baseline",
        status="unknown",
        error_summary=None,
        artifacts={
            "manifest": "manifest.json",
            "test_result": "test-result.json",
            "summary": "summary.md",
            "commands": "commands.json",
        },
        artifact_texts={
            "summary.md": "# Summary\n\nCommands emission baseline.\n",
        },
        command_records=command_records,
        event_evidence={
            "commands": "commands.json",
            "command_count": len(command_records),
        },
    )

    commands_path = tmp_path / "commands.json"
    assert commands_path.exists()
    payload = json.loads(commands_path.read_text(encoding="utf-8"))
    assert isinstance(payload, list)
    assert [record["type"] for record in payload] == ["run_started", "plan_ready"]
    assert manifest["artifacts"]["commands"] == "commands.json"
    assert manifest["file_hashes"]["commands.json"].startswith("sha256:")
    assert manifest["event_evidence"]["commands"] == "commands.json"
    assert result["event_evidence"]["commands"] == "commands.json"


def test_finalize_test_result_omits_deferred_commands_note_when_commands_json_is_written(
    tmp_path: Path,
) -> None:
    command_records = [
        {"type": "run_started", "run_id": "run-123"},
    ]

    manifest, result = harness.finalize_test_result(
        artifact_dir=tmp_path,
        test_name="commands_artifact_baseline",
        status="unknown",
        error_summary=None,
        artifacts={
            "manifest": "manifest.json",
            "test_result": "test-result.json",
            "summary": "summary.md",
            "commands": "commands.json",
        },
        artifact_texts={
            "summary.md": "# Summary\n\nCommands emission baseline.\n",
        },
        command_records=command_records,
        event_evidence={
            "commands": "commands.json",
        },
    )

    summary = (tmp_path / "summary.md").read_text(encoding="utf-8")

    assert all("commands.json" not in note for note in manifest["optional_absence_notes"])
    assert result["event_evidence"]["commands"] == "commands.json"
    assert "commands.json" in summary


def test_finalize_test_result_keeps_events_behavior_when_commands_json_is_written(
    tmp_path: Path,
) -> None:
    event_records = [
        _event("run_started"),
        _event("plan_ready"),
    ]
    command_records = [
        {"type": "run_started", "run_id": "run-123"},
        {"type": "plan_ready", "run_id": "run-123", "plan_id": "plan-1"},
    ]

    manifest, result = harness.finalize_test_result(
        artifact_dir=tmp_path,
        test_name="events_and_commands_artifact_baseline",
        status="unknown",
        error_summary=None,
        artifacts={
            "manifest": "manifest.json",
            "test_result": "test-result.json",
            "summary": "summary.md",
            "events": "events.ndjson",
            "commands": "commands.json",
        },
        artifact_texts={
            "summary.md": "# Summary\n\nEvents and commands emission baseline.\n",
        },
        event_records=event_records,
        command_records=command_records,
        event_evidence={
            "events": "events.ndjson",
            "commands": "commands.json",
        },
    )

    events_path = tmp_path / "events.ndjson"
    commands_path = tmp_path / "commands.json"

    assert [json.loads(line)["type"] for line in events_path.read_text(encoding="utf-8").splitlines()] == [
        "run_started",
        "plan_ready",
    ]
    assert isinstance(json.loads(commands_path.read_text(encoding="utf-8")), list)
    assert manifest["artifacts"]["events"] == "events.ndjson"
    assert manifest["artifacts"]["commands"] == "commands.json"
    assert result["event_evidence"]["events"] == "events.ndjson"
    assert result["event_evidence"]["commands"] == "commands.json"


def test_finalize_test_result_writes_rejections_json_and_lists_it_in_manifest(
    tmp_path: Path,
) -> None:
    rejection_records = [
        {"type": "plan_rejected", "run_id": "run-123", "reason": "missing clarification"},
        {"type": "step_rejected", "run_id": "run-123", "reason": "invalid locator"},
    ]

    manifest, result = harness.finalize_test_result(
        artifact_dir=tmp_path,
        test_name="rejections_artifact_baseline",
        status="unknown",
        error_summary=None,
        artifacts={
            "manifest": "manifest.json",
            "test_result": "test-result.json",
            "summary": "summary.md",
            "rejections": "rejections.json",
        },
        artifact_texts={
            "summary.md": "# Summary\n\nRejections emission baseline.\n",
        },
        rejection_records=rejection_records,
        event_evidence={
            "rejections": "rejections.json",
            "rejection_count": len(rejection_records),
        },
    )

    rejections_path = tmp_path / "rejections.json"
    assert rejections_path.exists()
    payload = json.loads(rejections_path.read_text(encoding="utf-8"))
    assert isinstance(payload, list)
    assert [record["type"] for record in payload] == ["plan_rejected", "step_rejected"]
    assert manifest["artifacts"]["rejections"] == "rejections.json"
    assert manifest["file_hashes"]["rejections.json"].startswith("sha256:")
    assert manifest["event_evidence"]["rejections"] == "rejections.json"
    assert result["event_evidence"]["rejections"] == "rejections.json"


def test_finalize_test_result_writes_redaction_report_json_and_lists_it_in_manifest(
    tmp_path: Path,
) -> None:
    manifest, result = harness.finalize_test_result(
        artifact_dir=tmp_path,
        test_name="redaction_report_artifact_baseline",
        status="unknown",
        error_summary=None,
        artifacts=REDACTION_REPORT_ARTIFACTS,
        artifact_texts={
            "summary.md": "# Summary\n\nRedaction report baseline.\n",
        },
    )

    report_path = tmp_path / "redaction-report.json"

    assert report_path.exists()
    payload = json.loads(report_path.read_text(encoding="utf-8"))
    assert payload["redaction_passed"] is True
    assert payload["redaction_version"] == "1.0"
    assert payload["patterns_checked"] == ["token", "otp", "email", "phone", "password"]
    assert payload["files_checked"] == ["trace.ndjson", "commands.json"]
    assert payload["findings"] == []
    assert manifest["artifacts"]["redaction_report"] == "redaction-report.json"
    assert manifest["file_hashes"]["redaction-report.json"].startswith("sha256:")


def test_redaction_report_json_schema_includes_expected_fields(tmp_path: Path) -> None:
    harness.finalize_test_result(
        artifact_dir=tmp_path,
        test_name="redaction_report_schema_baseline",
        status="unknown",
        error_summary=None,
        artifacts=REDACTION_REPORT_ARTIFACTS,
        artifact_texts={
            "summary.md": "# Summary\n\nRedaction report baseline.\n",
        },
    )

    report_path = tmp_path / "redaction-report.json"

    assert report_path.exists()
    payload = json.loads(report_path.read_text(encoding="utf-8"))
    assert set(REDACTION_REPORT_EXPECTED_SCHEMA).issubset(payload)
    assert payload["redaction_passed"] is True
    assert payload["redaction_version"] == "1.0"
    assert payload["patterns_checked"] == ["token", "otp", "email", "phone", "password"]
    assert payload["files_checked"] == ["trace.ndjson", "commands.json"]
    assert payload["findings"] == []


def test_finalize_test_result_redacts_sensitive_strings_from_summary_and_artifact_metadata(
    tmp_path: Path,
) -> None:
    fake_token, fake_otp, fake_email, fake_phone, fake_password = REDACTION_REPORT_SECRET_VALUES

    manifest, result = harness.finalize_test_result(
        artifact_dir=tmp_path,
        test_name="redaction_sensitive_metadata_baseline",
        status="failed",
        error_summary=f"leaked {fake_token}",
        artifacts=REDACTION_REPORT_ARTIFACTS,
        artifact_texts={
            "summary.md": (
                "# Summary\n\n"
                f"token={fake_token}\n"
                f"otp={fake_otp}\n"
                f"email={fake_email}\n"
                f"phone={fake_phone}\n"
                f"password={fake_password}\n"
            ),
        },
        event_evidence={
            "token": fake_token,
            "otp": fake_otp,
            "email": fake_email,
            "phone": fake_phone,
            "password": fake_password,
        },
    )

    summary = (tmp_path / "summary.md").read_text(encoding="utf-8")
    manifest_blob = json.dumps(manifest, sort_keys=True)
    result_blob = json.dumps(result, sort_keys=True)

    for secret in REDACTION_REPORT_SECRET_VALUES:
        assert secret not in summary
        assert secret not in manifest_blob
        assert secret not in result_blob


def test_finalize_test_result_records_redaction_parse_diagnostics_for_already_redacted_placeholders(
    tmp_path: Path,
) -> None:
    already_redacted_url = "https://[REDACTED_PHONE]/trace?phone=[REDACTED_PHONE]"

    manifest, result = harness.finalize_test_result(
        artifact_dir=tmp_path,
        test_name="redaction_placeholder_parse_diagnostic",
        status="failed",
        error_summary=f"cleanup saw {already_redacted_url}",
        artifacts=REDACTION_REPORT_ARTIFACTS,
        artifact_texts={
            "summary.md": f"# Summary\n\ncleanup saw {already_redacted_url}\n",
        },
    )

    report_path = tmp_path / "redaction-report.json"
    report = json.loads(report_path.read_text(encoding="utf-8"))

    assert manifest["status"] == "failed"
    assert result["status"] == "failed"
    assert any(
        finding["pattern"] == "redaction_parse_error" and finding["location"] in {"error_summary", "summary.md"}
        for finding in report["findings"]
    )
    assert "[REDACTED_PHONE]" in (tmp_path / "summary.md").read_text(encoding="utf-8")


def test_finalize_test_result_omits_deferred_redaction_report_note_when_redaction_report_json_is_written(
    tmp_path: Path,
) -> None:
    manifest, _result = harness.finalize_test_result(
        artifact_dir=tmp_path,
        test_name="redaction_report_notes_baseline",
        status="unknown",
        error_summary=None,
        artifacts=REDACTION_REPORT_ARTIFACTS,
        artifact_texts={
            "summary.md": "# Summary\n\nRedaction report baseline.\n",
        },
    )

    assert manifest["artifacts"]["redaction_report"] == "redaction-report.json"
    assert all("redaction-report" not in note for note in manifest["optional_absence_notes"])


def test_finalize_test_result_marks_missing_redaction_report_as_failed_evidence_gate(
    tmp_path: Path,
) -> None:
    manifest, result = harness.finalize_test_result(
        artifact_dir=tmp_path,
        test_name="redaction_report_missing_gate",
        status="unknown",
        error_summary="redaction-report.json missing",
        artifacts={
            "manifest": "manifest.json",
            "test_result": "test-result.json",
            "summary": "summary.md",
        },
        artifact_texts={
            "summary.md": "# Summary\n\nRedaction report gate baseline.\n",
        },
        event_evidence={
            "present": ["manifest.json", "test-result.json", "summary.md"],
            "missing": ["redaction-report.json"],
        },
    )

    assert manifest["status"] == "failed"
    assert result["status"] == "failed"


def test_save_failure_artifacts_redacts_sensitive_query_params_in_failure_context_and_summary(
    tmp_path: Path,
) -> None:
    fake_token, fake_otp, fake_email, fake_phone, fake_password = REDACTION_REPORT_SECRET_VALUES
    sensitive_url = _sensitive_query_url()
    session = _make_failure_session(
        tmp_path,
        page=_LeakyFailurePage(
            url=sensitive_url,
            error_message=f"page-state leak token={fake_token} otp={fake_otp}",
        ),
    )

    asyncio.run(
        session.save_failure_artifacts(
            f"request url {sensitive_url}",
            stage="awaiting_plan_ready",
            expected_event_type="plan_ready",
            observed_event_types=["run_started"],
            event_evidence={
                "request": {
                    "url": sensitive_url,
                },
            },
        )
    )
    asyncio.run(session.close())

    summary = (tmp_path / "summary.md").read_text(encoding="utf-8")
    failure_text = (tmp_path / "failure.txt").read_text(encoding="utf-8")
    failure_context_blob = (tmp_path / "failure-context.json").read_text(encoding="utf-8")

    for secret in (fake_token, fake_otp, fake_email, fake_phone, fake_password):
        assert secret not in summary
        assert secret not in failure_text
        assert secret not in failure_context_blob


def test_nested_event_evidence_payload_values_are_redacted_recursively_in_failure_context(
    tmp_path: Path,
) -> None:
    sensitive_url = _sensitive_query_url()
    session = _make_failure_session(
        tmp_path,
        page=_LeakyFailurePage(
            url=sensitive_url,
            error_message=f"page-state leak token={REDACTION_REPORT_SECRET_VALUES[0]}",
        ),
    )

    asyncio.run(
        session.save_failure_artifacts(
            "missing plan_ready event",
            stage="awaiting_plan_ready",
            expected_event_type="plan_ready",
            observed_event_types=["run_started"],
            event_evidence=_nested_sensitive_event_evidence(),
        )
    )
    asyncio.run(session.close())

    failure_context = json.loads((tmp_path / "failure-context.json").read_text(encoding="utf-8"))
    nested_evidence = failure_context["event_evidence"]

    assert nested_evidence["request"]["headers"]["Authorization"] == "Bearer [REDACTED_TOKEN]"
    assert nested_evidence["request"]["headers"]["X-OTP"] == "[REDACTED_OTP]"
    assert nested_evidence["request"]["contact"]["email"] == "[REDACTED_EMAIL]"
    assert nested_evidence["request"]["contact"]["phone"] == "[REDACTED_PHONE]"
    assert nested_evidence["request"]["profile"]["password"] == "[REDACTED_PASSWORD]"
    assert nested_evidence["nested"][0]["token"] == "[REDACTED_TOKEN]"
    assert nested_evidence["nested"][1]["otp"] == "[REDACTED_OTP]"
    assert nested_evidence["nested"][2]["email"] == "[REDACTED_EMAIL]"
    assert nested_evidence["nested"][3]["phone"] == "[REDACTED_PHONE]"
    assert nested_evidence["nested"][4]["password"] == "[REDACTED_PASSWORD]"
    assert sensitive_url not in json.dumps(failure_context, sort_keys=True)


def test_redaction_report_records_findings_for_redacted_fields_without_raw_secrets(
    tmp_path: Path,
) -> None:
    session = _make_failure_session(
        tmp_path,
        page=_LeakyFailurePage(
            url=_sensitive_query_url(),
            error_message=f"page-state leak token={REDACTION_REPORT_SECRET_VALUES[0]}",
        ),
    )

    asyncio.run(
        session.save_failure_artifacts(
            "missing plan_ready event",
            stage="awaiting_plan_ready",
            expected_event_type="plan_ready",
            observed_event_types=["run_started"],
            event_evidence=_nested_sensitive_event_evidence(),
        )
    )
    asyncio.run(session.close())

    report_path = tmp_path / "redaction-report.json"
    report = json.loads(report_path.read_text(encoding="utf-8"))
    report_blob = json.dumps(report, sort_keys=True)

    assert report["redaction_passed"] is True
    assert any(finding["location"].startswith("event_evidence.") for finding in report["findings"])
    assert any(finding["location"] == "page_state.current_url" for finding in report["findings"])
    for secret in REDACTION_REPORT_SECRET_VALUES:
        assert secret not in report_blob


def test_clean_artifacts_produce_redaction_passed_true_and_empty_findings(tmp_path: Path) -> None:
    manifest, result = harness.finalize_test_result(
        artifact_dir=tmp_path,
        test_name="redaction_report_clean_artifacts_baseline",
        status="unknown",
        error_summary=None,
        artifacts=REDACTION_REPORT_ARTIFACTS,
        artifact_texts={
            "summary.md": "# Summary\n\nClean redaction baseline.\n",
        },
    )

    report_path = tmp_path / "redaction-report.json"
    report = json.loads(report_path.read_text(encoding="utf-8"))

    assert report_path.exists()
    assert report["redaction_passed"] is True
    assert report["findings"] == []
    assert manifest["artifacts"]["redaction_report"] == "redaction-report.json"
    assert manifest["file_hashes"]["redaction-report.json"].startswith("sha256:")
    assert result["status"] == "unknown"


def test_finalize_test_result_omits_deferred_rejections_note_when_rejections_json_is_written(
    tmp_path: Path,
) -> None:
    rejection_records = [
        {"type": "plan_rejected", "run_id": "run-123", "reason": "missing clarification"},
    ]

    manifest, result = harness.finalize_test_result(
        artifact_dir=tmp_path,
        test_name="rejections_artifact_baseline",
        status="unknown",
        error_summary=None,
        artifacts={
            "manifest": "manifest.json",
            "test_result": "test-result.json",
            "summary": "summary.md",
            "rejections": "rejections.json",
        },
        artifact_texts={
            "summary.md": "# Summary\n\nRejections emission baseline.\n",
        },
        rejection_records=rejection_records,
        event_evidence={
            "rejections": "rejections.json",
        },
    )

    summary = (tmp_path / "summary.md").read_text(encoding="utf-8")

    assert all("rejections.json" not in note for note in manifest["optional_absence_notes"])
    assert result["event_evidence"]["rejections"] == "rejections.json"
    assert "rejections.json" in summary


def test_finalize_test_result_keeps_events_and_commands_behavior_when_rejections_json_is_written(
    tmp_path: Path,
) -> None:
    event_records = [
        _event("run_started"),
        _event("plan_ready"),
    ]
    command_records = [
        {"type": "run_started", "run_id": "run-123"},
        {"type": "plan_ready", "run_id": "run-123", "plan_id": "plan-1"},
    ]
    rejection_records = [
        {"type": "plan_rejected", "run_id": "run-123", "reason": "missing clarification"},
    ]

    manifest, result = harness.finalize_test_result(
        artifact_dir=tmp_path,
        test_name="events_commands_rejections_artifact_baseline",
        status="unknown",
        error_summary=None,
        artifacts={
            "manifest": "manifest.json",
            "test_result": "test-result.json",
            "summary": "summary.md",
            "events": "events.ndjson",
            "commands": "commands.json",
            "rejections": "rejections.json",
        },
        artifact_texts={
            "summary.md": "# Summary\n\nEvents, commands, and rejections emission baseline.\n",
        },
        event_records=event_records,
        command_records=command_records,
        rejection_records=rejection_records,
        event_evidence={
            "events": "events.ndjson",
            "commands": "commands.json",
            "rejections": "rejections.json",
        },
    )

    events_path = tmp_path / "events.ndjson"
    commands_path = tmp_path / "commands.json"
    rejections_path = tmp_path / "rejections.json"

    assert [json.loads(line)["type"] for line in events_path.read_text(encoding="utf-8").splitlines()] == [
        "run_started",
        "plan_ready",
    ]
    assert isinstance(json.loads(commands_path.read_text(encoding="utf-8")), list)
    assert isinstance(json.loads(rejections_path.read_text(encoding="utf-8")), list)
    assert manifest["artifacts"]["events"] == "events.ndjson"
    assert manifest["artifacts"]["commands"] == "commands.json"
    assert manifest["artifacts"]["rejections"] == "rejections.json"
    assert result["event_evidence"]["events"] == "events.ndjson"
    assert result["event_evidence"]["commands"] == "commands.json"
    assert result["event_evidence"]["rejections"] == "rejections.json"


def test_finalize_test_result_writes_events_commands_and_rejections_together(
    tmp_path: Path,
) -> None:
    event_records = [
        _event("run_started"),
        _event("plan_ready"),
    ]
    command_records = [
        {"type": "run_started", "run_id": "run-123"},
        {"type": "plan_ready", "run_id": "run-123", "plan_id": "plan-1"},
    ]
    rejection_records = [
        {"type": "plan_rejected", "run_id": "run-123", "reason": "missing clarification"},
        {"type": "step_rejected", "run_id": "run-123", "reason": "invalid locator"},
    ]

    manifest, result = harness.finalize_test_result(
        artifact_dir=tmp_path,
        test_name="all_artifacts_baseline",
        status="unknown",
        error_summary=None,
        artifacts={
            "manifest": "manifest.json",
            "test_result": "test-result.json",
            "summary": "summary.md",
            "events": "events.ndjson",
            "commands": "commands.json",
            "rejections": "rejections.json",
        },
        artifact_texts={
            "summary.md": "# Summary\n\nAll artifact emission baseline.\n",
        },
        event_records=event_records,
        command_records=command_records,
        rejection_records=rejection_records,
        event_evidence={
            "events": "events.ndjson",
            "commands": "commands.json",
            "rejections": "rejections.json",
            "event_count": len(event_records),
            "command_count": len(command_records),
            "rejection_count": len(rejection_records),
        },
    )

    events_path = tmp_path / "events.ndjson"
    commands_path = tmp_path / "commands.json"
    rejections_path = tmp_path / "rejections.json"
    summary = (tmp_path / "summary.md").read_text(encoding="utf-8")

    assert [json.loads(line)["type"] for line in events_path.read_text(encoding="utf-8").splitlines()] == [
        "run_started",
        "plan_ready",
    ]
    assert [record["type"] for record in json.loads(commands_path.read_text(encoding="utf-8"))] == [
        "run_started",
        "plan_ready",
    ]
    assert [record["type"] for record in json.loads(rejections_path.read_text(encoding="utf-8"))] == [
        "plan_rejected",
        "step_rejected",
    ]
    assert manifest["artifacts"]["events"] == "events.ndjson"
    assert manifest["artifacts"]["commands"] == "commands.json"
    assert manifest["artifacts"]["rejections"] == "rejections.json"
    assert manifest["file_hashes"]["events.ndjson"].startswith("sha256:")
    assert manifest["file_hashes"]["commands.json"].startswith("sha256:")
    assert manifest["file_hashes"]["rejections.json"].startswith("sha256:")
    assert manifest["event_evidence"]["events"] == "events.ndjson"
    assert manifest["event_evidence"]["commands"] == "commands.json"
    assert manifest["event_evidence"]["rejections"] == "rejections.json"
    assert result["event_evidence"]["events"] == "events.ndjson"
    assert result["event_evidence"]["commands"] == "commands.json"
    assert result["event_evidence"]["rejections"] == "rejections.json"
    assert '"events": "events.ndjson"' in summary
    assert '"commands": "commands.json"' in summary
    assert '"rejections": "rejections.json"' in summary
    assert "deferred" not in summary.lower()


def test_finalize_test_result_without_records_keeps_default_absence_notes_and_no_artifacts(
    tmp_path: Path,
) -> None:
    manifest, result = harness.finalize_test_result(
        artifact_dir=tmp_path,
        test_name="no_artifacts_baseline",
        status="unknown",
        error_summary=None,
        artifacts={
            "manifest": "manifest.json",
            "test_result": "test-result.json",
            "summary": "summary.md",
        },
        artifact_texts={
            "summary.md": "# Summary\n\nNo artifact emission baseline.\n",
        },
        optional_absence_notes=NORMALIZED_EVIDENCE_NOTES,
        event_evidence={
            "present": [],
            "missing": ["events.ndjson", "commands.json", "rejections.json"],
        },
    )

    summary = (tmp_path / "summary.md").read_text(encoding="utf-8")

    assert manifest["optional_absence_notes"] == NORMALIZED_EVIDENCE_NOTES
    assert manifest["artifacts"] == {
        "manifest": "manifest.json",
        "test_result": "test-result.json",
        "summary": "summary.md",
    }
    assert result["event_evidence"]["missing"] == ["events.ndjson", "commands.json", "rejections.json"]
    assert "## Event evidence" in summary
    assert "events.ndjson" in summary
    assert "commands.json" in summary
    assert "rejections.json" in summary
    assert not (tmp_path / "events.ndjson").exists()
    assert not (tmp_path / "commands.json").exists()
    assert not (tmp_path / "rejections.json").exists()


def test_failure_artifacts_record_expected_and_observed_event_metadata(tmp_path: Path) -> None:
    session = _make_failure_session(tmp_path)
    captured_before_action = harness.collect_events(
        [
            _event("run_started"),
        ]
    )
    observed_events = [
        _event("run_started"),
        _event("step_executing"),
    ]
    event_evidence = {
        "captured_before_action": [event["type"] for event in captured_before_action],
        "expected_event_type": "plan_ready",
        "observed_event_types": [event["type"] for event in observed_events],
    }

    context = asyncio.run(
        session.save_failure_artifacts(
            "missing plan_ready event",
            stage="awaiting_plan_ready",
            expected_event_type="plan_ready",
            observed_event_types=[event["type"] for event in observed_events],
            event_evidence=event_evidence,
        )
    )

    failure_text = (tmp_path / "failure.txt").read_text(encoding="utf-8")
    failure_context = json.loads((tmp_path / "failure-context.json").read_text(encoding="utf-8"))

    assert context["expected_event_type"] == "plan_ready"
    assert context["observed_event_types"] == ["run_started", "step_executing"]
    assert context["event_evidence"] == event_evidence
    assert failure_context["expected_event_type"] == "plan_ready"
    assert failure_context["observed_event_types"] == ["run_started", "step_executing"]
    assert failure_context["event_evidence"] == event_evidence
    assert "expected_event_type=plan_ready" in failure_text
    assert "observed_event_types=['run_started', 'step_executing']" in failure_text
    assert "captured_before_action" in failure_text


def test_failure_artifacts_will_persist_event_evidence_through_close(tmp_path: Path) -> None:
    session = _make_failure_session(tmp_path)
    event_evidence = {
        "captured_before_action": ["run_started"],
        "expected_event_type": "plan_ready",
        "observed_event_types": ["run_started", "step_executing"],
        "present": ["backend.log", "summary.md"],
    }

    asyncio.run(
        session.save_failure_artifacts(
            "missing plan_ready event",
            stage="awaiting_plan_ready",
            expected_event_type="plan_ready",
            observed_event_types=["run_started", "step_executing"],
            event_evidence=event_evidence,
        )
    )
    asyncio.run(session.close())

    manifest = json.loads((tmp_path / "manifest.json").read_text(encoding="utf-8"))
    result = json.loads((tmp_path / "test-result.json").read_text(encoding="utf-8"))
    summary = (tmp_path / "summary.md").read_text(encoding="utf-8")

    assert manifest["optional_absence_notes"] == [
        "events.ndjson, commands.json, and rejections.json are deferred to a later backend event stream slice",
        "trace-summary is deferred to a later trace/export slice",
    ]
    assert not (tmp_path / "events.ndjson").exists()
    assert not (tmp_path / "commands.json").exists()
    assert not (tmp_path / "rejections.json").exists()
    assert manifest["event_evidence"] == event_evidence
    assert result["event_evidence"] == event_evidence
    assert "## Event evidence" in summary
    assert '"expected_event_type": "plan_ready"' in summary
    assert '"observed_event_types": [' in summary


def test_session_close_writes_token_report_from_backend_stdout_telemetry(tmp_path: Path) -> None:
    telemetry_line = (
        "[LLM_TELEMETRY] call_id=llm_001 purpose=main_orchestrator "
        "estimated_total_input_tokens=1500 output_tokens=180 "
        "system_prompt_tokens=200 skill_tokens=300 tool_schema_tokens=900 "
        "message_history_tokens=50 dom_or_tool_result_tokens=25 "
        'skills_loaded="core,locator"'
    )
    session = _make_failure_session(tmp_path, backend_stdout_text=f"{telemetry_line}\n")

    asyncio.run(session.close())

    report = json.loads((tmp_path / "token-report.json").read_text(encoding="utf-8"))
    assert report["test_name"] == "failure_artifacts"
    assert report["call_count"] == 1
    assert report["total_estimated_input_tokens"] == 1500
    assert report["largest_call_id"] == "llm_001"
    assert report["largest_call_tokens"] == 1500
    assert report["top_token_source"] == "tool_schema"
    assert report["token_breakdown"]["tool_schema"] == 900
    assert report["skills_loaded"] == ["core", "locator"]


def test_session_close_writes_empty_token_report_when_telemetry_is_missing(tmp_path: Path) -> None:
    session = _make_failure_session(tmp_path, backend_stdout_text="[PHASE] run started\n")

    asyncio.run(session.close())

    report = json.loads((tmp_path / "token-report.json").read_text(encoding="utf-8"))
    assert report["test_name"] == "failure_artifacts"
    assert report["call_count"] == 0
    assert report["total_estimated_input_tokens"] == 0
    assert report["largest_call_id"] is None
    assert report["top_token_source"] == "none"
    llm_calls = json.loads((tmp_path / "llm-calls.json").read_text(encoding="utf-8"))
    assert llm_calls == []


def test_failure_summary_mentions_expected_and_observed_event_types(tmp_path: Path) -> None:
    session = _make_failure_session(tmp_path)
    event_evidence = {
        "captured_before_action": ["run_started"],
        "expected_event_type": "plan_ready",
        "observed_event_types": ["run_started"],
    }

    asyncio.run(
        session.save_failure_artifacts(
            "missing plan_ready event",
            stage="awaiting_plan_ready",
            expected_event_type="plan_ready",
            observed_event_types=["run_started"],
            event_evidence=event_evidence,
        )
    )

    failure_text = (tmp_path / "failure.txt").read_text(encoding="utf-8")

    assert "expected_event_type=plan_ready" in failure_text
    assert "observed_event_types=['run_started']" in failure_text
    assert "missing plan_ready event" in failure_text


# ---------------------------------------------------------------------------
# BUG-S5-013-007: LLM call payload capture tests
# ---------------------------------------------------------------------------

def test_paid_artifact_captures_assistant_text_for_content_only_turns(tmp_path: Path) -> None:
    """build_llm_calls_artifact must record assistant_text for content-only turns."""
    calls = [
        {
            "call_id": "llm_001",
            "purpose": "step_plan_normalizer",
            "tool_names": ["send_to_overlay", "ask_user", "dom_extract"],
            "assistant_text": None,
            "tool_calls": [{"name": "send_to_overlay", "args_summary": "message_type=llm_thinking"}],
            "finish_reason": "tool_calls",
            "token_usage": {"prompt_tokens": 100, "completion_tokens": 14},
        },
        {
            "call_id": "llm_002",
            "purpose": "step_plan_normalizer",
            "tool_names": ["send_to_overlay", "ask_user", "dom_extract"],
            "assistant_text": (
                "The page has Profile Settings, Billing Profile, and Shipping Profile. "
                "It is ambiguous which one to save."
            ),
            "tool_calls": [],
            "finish_reason": "stop",
            "token_usage": {"prompt_tokens": 150, "completion_tokens": 75},
        },
    ]
    artifact = harness.build_llm_calls_artifact(calls)

    assert len(artifact) == 2

    # Tool-call turn: assistant_text is None
    assert artifact[0]["call_id"] == "llm_001"
    assert artifact[0]["assistant_text"] is None
    assert artifact[0]["tool_calls"]

    # Content-only turn: assistant_text captured
    assert artifact[1]["call_id"] == "llm_002"
    assert artifact[1]["assistant_text"] is not None
    assert "ambiguous" in artifact[1]["assistant_text"]
    assert artifact[1]["tool_calls"] == []
    assert artifact[1]["finish_reason"] == "stop"
    assert artifact[1]["token_usage"]["completion_tokens"] == 75


def test_paid_artifact_captures_tool_schema_names_exposed(tmp_path: Path) -> None:
    """Each LLM call record must include the tool_names exposed to the model."""
    calls = [
        {
            "call_id": "llm_001",
            "purpose": "step_plan_normalizer",
            "tool_names": ["send_to_overlay", "ask_user", "dom_extract", "browser_get_state",
                           "locator_find", "locator_validate"],
            "assistant_text": None,
            "tool_calls": [],
            "finish_reason": "stop",
            "token_usage": {"prompt_tokens": 100, "completion_tokens": 10},
        },
    ]
    artifact = harness.build_llm_calls_artifact(calls)

    assert artifact[0]["tool_names"] == [
        "send_to_overlay", "ask_user", "dom_extract", "browser_get_state",
        "locator_find", "locator_validate",
    ]


def test_payload_capture_does_not_expose_raw_secrets(tmp_path: Path) -> None:
    """build_llm_calls_artifact must redact secret-looking values from assistant text."""
    calls = [
        {
            "call_id": "llm_001",
            "purpose": "step_plan_normalizer",
            "tool_names": ["send_to_overlay"],
            "assistant_text": "The API key is sk-test-secret-1234567890 and token Bearer abc123xyz",
            "tool_calls": [],
            "finish_reason": "stop",
            "token_usage": {"prompt_tokens": 50, "completion_tokens": 20},
        },
    ]
    artifact = harness.build_llm_calls_artifact(calls)

    captured_text = artifact[0]["assistant_text"] or ""
    assert "sk-test-secret-1234567890" not in captured_text, (
        "Raw sk- API key must be redacted from captured assistant text"
    )
    assert "Bearer abc123xyz" not in captured_text, (
        "Bearer token must be redacted from captured assistant text"
    )


def test_payload_capture_redacts_tool_call_args_summary() -> None:
    calls = [
        {
            "call_id": "llm_001",
            "purpose": "step_plan_normalizer",
            "tool_names": ["ask_user"],
            "assistant_text": None,
            "tool_calls": [
                {
                    "name": "ask_user",
                    "args_summary": '{"question":"Use Bearer abc123xyz?","token":"sk-test-secret-1234567890"}',
                }
            ],
            "finish_reason": "tool_calls",
            "token_usage": {"prompt_tokens": 50, "completion_tokens": 20},
        },
    ]
    artifact = harness.build_llm_calls_artifact(calls)

    args_summary = artifact[0]["tool_calls"][0]["args_summary"] or ""
    assert "Bearer abc123xyz" not in args_summary
    assert "sk-test-secret-1234567890" not in args_summary


def test_paid_artifact_captures_tool_schema_summary_fields() -> None:
    calls = [
        {
            "call_id": "llm_001",
            "purpose": "step_plan_normalizer",
            "model": "gpt-4o-mini",
            "model_class": "main",
            "prompt_pack_id": "step_plan_normalizer.v1",
            "prefix_hash": "deadbeefdeadbeef",
            "tool_names": ["ask_user", "dom_extract"],
            "tool_schema": {
                "tool_count": 2,
                "tools": [
                    {"name": "ask_user", "description": "Ask the user", "params": ["question", "options"]},
                    {"name": "dom_extract", "description": "Read page DOM", "params": ["scope"]},
                ],
            },
            "assistant_text": None,
            "tool_calls": [],
            "finish_reason": "stop",
            "token_usage": {"prompt_tokens": 80, "completion_tokens": 25},
        },
    ]
    artifact = harness.build_llm_calls_artifact(calls)

    assert artifact[0]["model"] == "gpt-4o-mini"
    assert artifact[0]["model_class"] == "main"
    assert artifact[0]["prompt_pack_id"] == "step_plan_normalizer.v1"
    assert artifact[0]["prefix_hash"] == "deadbeefdeadbeef"
    assert artifact[0]["tool_schema"]["tool_count"] == 2
    assert artifact[0]["tool_schema"]["tools"][0]["name"] == "ask_user"


def test_session_close_writes_llm_calls_artifact_on_failure_before_plan_ready(tmp_path: Path) -> None:
    backend_stdout = "\n".join([
        '[LLM_CALL] {"assistant_text":"The token is sk-test-secret-1234567890","call_id":"llm_001","error":{},"finish_reason":"stop","model":"gpt-4o-mini","model_class":"main","prefix_hash":"deadbeefdeadbeef","prompt_pack_id":"step_plan_normalizer.v1","purpose":"step_plan_normalizer","token_usage":{"completion_tokens":12,"prompt_tokens":34},"tool_calls":[{"args_summary":"{\\"auth\\": \\"Bearer abc123xyz\\"}","name":"ask_user"}],"tool_names":["ask_user"],"tool_schema":{"tool_count":1,"tools":[{"description":"Ask the user","name":"ask_user","params":["question","options"]}]}}',
        "[PHASE] from=planning to=failed reason=planning_no_progress step_id=none",
        "",
    ])
    session = _make_failure_session(tmp_path, backend_stdout_text=backend_stdout)

    asyncio.run(session.close())

    artifact_path = tmp_path / "llm-calls.json"
    assert artifact_path.exists()
    records = json.loads(artifact_path.read_text(encoding="utf-8"))
    assert len(records) == 1
    assert records[0]["call_id"] == "llm_001"
    assert "sk-test-secret-1234567890" not in (records[0]["assistant_text"] or "")
    assert "[REDACTED_TOKEN]" in (records[0]["assistant_text"] or "")
    assert records[0]["tool_calls"][0]["name"] == "ask_user"
    assert "Bearer abc123xyz" not in (records[0]["tool_calls"][0]["args_summary"] or "")


def test_write_llm_calls_artifact_produces_json_file(tmp_path: Path) -> None:
    """write_llm_calls_artifact must write llm-calls.json to the artifact dir."""
    calls = [
        {
            "call_id": "llm_001",
            "purpose": "step_plan_normalizer",
            "tool_names": ["send_to_overlay"],
            "assistant_text": "Some reasoning text",
            "tool_calls": [],
            "finish_reason": "stop",
            "token_usage": {"prompt_tokens": 80, "completion_tokens": 25},
        },
    ]
    harness.write_llm_calls_artifact(tmp_path, calls)

    artifact_path = tmp_path / "llm-calls.json"
    assert artifact_path.exists(), "llm-calls.json must be written to artifact_dir"

    records = json.loads(artifact_path.read_text(encoding="utf-8"))
    assert isinstance(records, list)
    assert len(records) == 1
    assert records[0]["call_id"] == "llm_001"
