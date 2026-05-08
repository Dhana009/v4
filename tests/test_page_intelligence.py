from __future__ import annotations

from runtime.page_intelligence import build_page_intelligence_packet, PageIntelligencePacket

_SAMPLE_HTML = """
<html>
<head><title>Test Page</title></head>
<body>
  <h1>Welcome to the site</h1>
  <h2>Features</h2>
  <p>This is a feature description paragraph.</p>
  <form action="/submit">
    <input type="text" name="username" placeholder="Username">
    <input type="password" name="password" placeholder="Password">
    <button type="submit">Login</button>
    <a href="/register">Register</a>
  </form>
</body>
</html>
"""

_WEAK_HTML = """
<html>
<body>
  <div id="1234" class="a">
    <div id="5678" class="b">
      <span>text</span>
    </div>
  </div>
</body>
</html>
"""


def test_packet_includes_headings():
    packet = build_page_intelligence_packet(html=_SAMPLE_HTML, url="http://test/", title="Test Page")
    assert len(packet.headings) >= 1
    assert any("Welcome" in h for h in packet.headings)


def test_packet_includes_ctas():
    packet = build_page_intelligence_packet(html=_SAMPLE_HTML, url="http://test/")
    assert len(packet.ctas) >= 1
    assert any("Login" in cta or "Register" in cta for cta in packet.ctas)


def test_packet_includes_inputs():
    packet = build_page_intelligence_packet(html=_SAMPLE_HTML, url="http://test/")
    input_names = [i["name"] for i in packet.inputs]
    assert "username" in input_names
    assert "password" in input_names


def test_packet_includes_forms_count():
    packet = build_page_intelligence_packet(html=_SAMPLE_HTML, url="http://test/")
    assert packet.forms_count == 1


def test_packet_includes_text_blocks():
    packet = build_page_intelligence_packet(html=_SAMPLE_HTML, url="http://test/")
    assert len(packet.text_blocks) >= 1


def test_weak_dom_produces_semantic_quality_weak():
    packet = build_page_intelligence_packet(html=_WEAK_HTML, url="http://weak/")
    assert packet.semantic_quality == "weak"
    assert "weak_semantic_dom" in packet.risk_flags


def test_good_dom_produces_semantic_quality_good():
    packet = build_page_intelligence_packet(html=_SAMPLE_HTML, url="http://test/")
    assert packet.semantic_quality == "good"


def test_packet_has_token_estimate():
    packet = build_page_intelligence_packet(html=_SAMPLE_HTML, url="http://test/")
    assert packet.token_estimate > 0


def test_compact_summary_does_not_include_raw_dom():
    packet = build_page_intelligence_packet(html=_SAMPLE_HTML, url="http://test/", title="Test")
    summary = packet.to_compact_summary()
    assert "<html>" not in summary
    assert "<body>" not in summary
    assert "<input" not in summary
    assert "semantic_quality" in summary


def test_raw_dom_excluded_by_default():
    """build_page_intelligence_packet returns a compact packet, not the raw HTML."""
    raw_html = "<html>" + "<div>content</div>" * 200 + "</html>"
    packet = build_page_intelligence_packet(html=raw_html, url="http://test/")
    summary = packet.to_compact_summary()
    # summary must be far smaller than raw HTML
    assert len(summary) < len(raw_html) // 5


def test_escalation_false_returns_packet():
    packet = build_page_intelligence_packet(
        html=_SAMPLE_HTML, url="http://test/", escalation=False
    )
    assert isinstance(packet, PageIntelligencePacket)


def test_empty_html_produces_unknown_quality():
    packet = build_page_intelligence_packet(html="", url="http://empty/")
    assert packet.semantic_quality == "unknown"
    assert "empty_dom" in packet.ambiguities
    assert "no_content" in packet.risk_flags


def test_candidate_locator_groups_included():
    locators = ["button[data-testid='login']", "input[name='username']"]
    packet = build_page_intelligence_packet(
        html=_SAMPLE_HTML, url="http://test/", candidate_locators=locators
    )
    assert packet.candidate_locator_groups == locators


def test_sections_derived_from_headings():
    packet = build_page_intelligence_packet(html=_SAMPLE_HTML, url="http://test/")
    assert len(packet.sections) >= 1
