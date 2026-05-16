import json
from pathlib import Path


def test_extension_manifest_declares_capture_permissions():
    manifest_path = Path("extension/manifest.json")

    assert manifest_path.exists()

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    assert manifest["manifest_version"] == 3
    assert manifest["action"]["default_popup"] == "popup.html"
    assert "activeTab" in manifest["permissions"]
    assert "scripting" in manifest["permissions"]
    assert "http://127.0.0.1:8000/*" in manifest["host_permissions"]
    assert "https://www.zhipin.com/*" in manifest["host_permissions"]
    assert "https://www.liepin.com/*" in manifest["host_permissions"]
    assert Path("extension/popup.js").exists()
    assert Path("extension/content.js").exists()
