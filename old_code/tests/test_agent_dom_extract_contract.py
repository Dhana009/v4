from __future__ import annotations

import asyncio
import types
from unittest.mock import AsyncMock, patch


_HTML = """
<html>
  <body>
    <main>
      <h1>Welcome</h1>
      <p>Intro text</p>
      <form>
        <input type="email" name="email" />
        <button data-testid="submit">Submit</button>
      </form>
    </main>
  </body>
</html>
"""


def _make_stub_page():
    page = types.SimpleNamespace()
    page.url = "http://fixture/page"
    page.content = AsyncMock(return_value=_HTML)
    page.title = AsyncMock(return_value="Fixture Page")
    page.evaluate = AsyncMock(return_value="<section><h2>Scoped</h2><button>Continue</button></section>")
    return page


def test_tool_dom_extract_returns_compact_summary_and_structured_page_intelligence() -> None:
    import agent as agent_module

    page = _make_stub_page()
    with patch.object(agent_module, "get_page", return_value=page):
        stub = types.SimpleNamespace()
        real_cls = agent_module.AgentLoop
        stub._tool_dom_extract = real_cls._tool_dom_extract.__get__(stub, type(stub))
        stub._clean_markup = real_cls._clean_markup.__get__(stub, type(stub))

        result = asyncio.run(stub._tool_dom_extract({"scope": "page"}))

    assert "page:" in result["elements"]
    assert "headings:" in result["elements"]
    assert "ctas:" in result["elements"]
    assert result["url"] == "http://fixture/page"
    assert "<html>" not in result["elements"]

    page_intelligence = result["page_intelligence"]
    assert "Welcome" in page_intelligence["headings"][0]
    assert any("Submit" in cta for cta in page_intelligence["ctas"])
    assert page_intelligence["forms_count"] == 1
    assert page_intelligence["semantic_quality"] == "good"
    assert result["_raw_elements"]


def test_tool_dom_extract_scoped_extract_uses_evaluate_and_keeps_raw_backend_side() -> None:
    import agent as agent_module

    page = _make_stub_page()
    with patch.object(agent_module, "get_page", return_value=page):
        stub = types.SimpleNamespace()
        real_cls = agent_module.AgentLoop
        stub._tool_dom_extract = real_cls._tool_dom_extract.__get__(stub, type(stub))
        stub._clean_markup = real_cls._clean_markup.__get__(stub, type(stub))

        result = asyncio.run(stub._tool_dom_extract({"scope": "section.hero"}))

    page.evaluate.assert_awaited()
    assert result["page_intelligence"]["headings"][0] == "Scoped"
    assert any("Continue" in cta for cta in result["page_intelligence"]["ctas"])
    assert "<section>" not in result["elements"]
    assert result["_raw_elements"]
