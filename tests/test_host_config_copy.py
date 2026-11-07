"""Renderis kopē hostinga konfigurācijas failus no assets/ uz koka sakni.

_headers / _redirects / .assetsignore — tikai ja tie eksistē assets/ (īstajā
kokā — jā). .htaccess kopš 2026-10-19 netiek ģenerēts (vecais hostings vairs
nav rezervē).
"""

import src.render._orchestrator as orch


def test_copies_headers(tmp_path, monkeypatch):
    assets = tmp_path / "assets"
    assets.mkdir()
    (assets / "htaccess.template").write_text("RewriteEngine On\n", encoding="utf-8")
    (assets / "_headers").write_text("/*\n  X-Test: 1\n", encoding="utf-8")
    monkeypatch.setattr(orch, "ASSETS_DIR", assets)
    out = tmp_path / "atmina"
    out.mkdir()

    copied = orch._copy_host_config(out)

    assert copied == ["_headers"]
    assert not (out / ".htaccess").exists()
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


def test_real_assets_dir_yields_host_config(tmp_path):
    out = tmp_path / "atmina"
    out.mkdir()
    copied = orch._copy_host_config(out)
    assert sorted(copied) == [".assetsignore", "_headers", "_redirects"], copied
    assert not (out / ".htaccess").exists()
    ignored = (out / ".assetsignore").read_text(encoding="utf-8").splitlines()
    assert ".htaccess" in ignored and "assets/_headers" in ignored, ignored
