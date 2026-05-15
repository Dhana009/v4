from __future__ import annotations

import browser


def test_autoworkbench_injection_script_includes_backend_websocket_config(monkeypatch) -> None:
    monkeypatch.setattr(browser, "_read_frontend_asset", lambda relative_path: "body{}")
    monkeypatch.setattr(browser, "_read_port", lambda: 4789)

    script = browser._build_autoworkbench_injection_script()

    assert '"wsUrl": "ws://127.0.0.1:4789/ws"' in script
    assert '"wsPort": 4789' in script
