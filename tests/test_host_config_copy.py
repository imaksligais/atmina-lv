"""Renderis kopē hostinga konfigurācijas failus no assets/ uz koka sakni.

Kamēr vecais hostings ir rezervē: .htaccess (no htaccess.template) UN _headers.
_redirects / .assetsignore — tikai ja tie eksistē assets/ (īstajā kokā — jā).
"""

import src.render._orchestrator as orch


def test_copies_htaccess_and_headers(tmp_path, monkeypatch):
    assets = tmp_path / "assets"
    assets.mkdir()
    (assets / "htaccess.template").write_text("RewriteEngine On\n", encoding="utf-8")
    (assets / "_headers").write_text("/*\n  X-Test: 1\n", encoding="utf-8")
    monkeypatch.setattr(orch, "ASSETS_DIR", assets)
    out = tmp_path / "atmina"
    out.mkdir()

    copied = orch._copy_host_config(out)

    assert sorted(copied) == [".htaccess", "_headers"]
    assert (out / ".htaccess").read_text(encoding="utf-8") == "RewriteEngine On\n"
    assert (out / "_headers").read_text(encoding="utf-8") == "/*\n  X-Test: 1\n"
    assert not (out / "_redirects").exists()


def test_copies_redirects_when_present(tmp_path, monkeypatch):
    assets = tmp_path / "assets"
    assets.mkdir()
    (assets / "_redirects").write_text("/vecais /jaunais.html 301\n", encoding="utf-8")
    monkeypatch.setattr(orch, "ASSETS_DIR", assets)
    out = tmp_path / "atmina"
    out.mkdir()

    assert orch._copy_host_config(out) == ["_redirects"]
    assert (out / "_redirects").exists()


def test_real_assets_dir_yields_both_files(tmp_path):
    out = tmp_path / "atmina"
    out.mkdir()
    copied = orch._copy_host_config(out)
    assert sorted(copied) == [".assetsignore", ".htaccess", "_headers", "_redirects"], copied
    ignored = (out / ".assetsignore").read_text(encoding="utf-8").splitlines()
    assert ".htaccess" in ignored and "assets/_headers" in ignored, ignored
