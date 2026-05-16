from pathlib import Path


def test_popup_uses_script_injection_fallback_before_capture():
    popup_source = Path("extension/popup.js").read_text(encoding="utf-8")

    assert "chrome.scripting.executeScript" in popup_source
    assert "files: [\"content.js\"]" in popup_source
    assert "capture-page" in popup_source
    assert "chrome.tabs.captureVisibleTab" in popup_source
    assert "/api/import-visual-page" in popup_source
    assert "scroll-to-capture-target" in popup_source
    assert "screenshots.push" in popup_source
    assert "text_excerpt" in popup_source
