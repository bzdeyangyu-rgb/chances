from frontend.app import (
    build_app_header_html,
    build_app_styles,
    build_summary_strip_html,
)


def test_build_app_styles_exposes_workspace_design_tokens():
    styles = build_app_styles()

    assert "--brand-ink" in styles
    assert "--surface-panel" in styles
    assert "--status-focus" in styles
    assert '[data-testid="stHeader"]' in styles
    assert ".stTextArea textarea:disabled" in styles
    assert ".ops-hero" in styles
    assert ".command-tile" in styles


def test_build_app_styles_avoids_decorative_marketing_treatment():
    styles = build_app_styles()

    assert "radial-gradient" not in styles
    assert "border-radius: 22px" not in styles
    assert "border-radius: 26px" not in styles


def test_build_summary_strip_html_does_not_create_markdown_code_blocks():
    html = build_summary_strip_html([("目标方向", "AI 产品"), ("工作城市", "南京")])

    assert html.startswith('<div class="summary-strip">')
    assert "\n        <div" not in html
    assert html.count('class="summary-item"') == 2


def test_app_header_reports_real_api_connection_state_in_chinese():
    connected = build_app_header_html("岗位池", api_connected=True)
    disconnected = build_app_header_html("岗位池", api_connected=False)

    assert "接口已连接" in connected
    assert "接口未连接" in disconnected
    assert "API http" not in connected
