from pathlib import Path

from src.social_agent import visuals


def test_render_illustration_delegates_to_nanobanana(monkeypatch, tmp_path):
    called = {}

    def fake_generate_bytes(prompt, **kwargs):
        called["prompt"] = prompt
        called["kwargs"] = kwargs
        return b"\x89PNG\r\n\x1a\nfake"

    monkeypatch.setattr(visuals, "_nanobanana_bytes", fake_generate_bytes)
    out = tmp_path / "illus.png"
    result = visuals.render_illustration(
        {"subject": "ideoloģiju sadursme", "style_hint": "editorial"},
        out_path=out,
    )
    assert result == out
    assert out.exists()
    assert out.read_bytes().startswith(b"\x89PNG")
    assert "ideoloģiju sadursme" in called["prompt"]
    assert "atmina" in called["prompt"].lower()
    # Brand must enforce no-text rule (per feedback_nanobanana_text_rule memory)
    assert "no text" in called["prompt"].lower()
    # Aspect ratio must be 16:9 for X optimal
    assert called["kwargs"].get("aspect_ratio") == "16:9"
