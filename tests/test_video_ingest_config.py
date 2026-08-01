import json
from pathlib import Path
from unittest.mock import patch

import pytest

from src.video_ingest.config import (
    load_hf_token, video_workspace_dir, slug_from_metadata, VIDEO_ROOT,
)


def test_load_hf_token_from_file(tmp_path, monkeypatch):
    key_file = tmp_path / "hf_token.json"
    key_file.write_text(json.dumps({"token": "hf_abcd1234"}), encoding="utf-8")
    monkeypatch.setattr("src.video_ingest.config.HF_TOKEN_PATH", key_file)
    monkeypatch.delenv("HUGGINGFACE_TOKEN", raising=False)
    assert load_hf_token() == "hf_abcd1234"


def test_load_hf_token_from_env(tmp_path, monkeypatch):
    nonexistent = tmp_path / "missing.json"
    monkeypatch.setattr("src.video_ingest.config.HF_TOKEN_PATH", nonexistent)
    monkeypatch.setenv("HUGGINGFACE_TOKEN", "hf_envtoken")
    assert load_hf_token() == "hf_envtoken"


def test_load_hf_token_missing_raises(tmp_path, monkeypatch):
    monkeypatch.setattr("src.video_ingest.config.HF_TOKEN_PATH", tmp_path / "nope.json")
    monkeypatch.delenv("HUGGINGFACE_TOKEN", raising=False)
    with pytest.raises(FileNotFoundError) as exc:
        load_hf_token()
    assert "huggingface" in str(exc.value).lower()


def test_video_workspace_dir_creates(tmp_path, monkeypatch):
    monkeypatch.setattr("src.video_ingest.config.VIDEO_ROOT", tmp_path / "videos")
    p = video_workspace_dir("2026-04-15-test-slug")
    assert p.exists()
    assert p.name == "2026-04-15-test-slug"


def test_slug_from_metadata_basic():
    slug = slug_from_metadata(
        published_at="2026-04-15",
        title="Kas Notiek Latvijā #345 — vēlēšanas",
    )
    assert slug.startswith("2026-04-15-")
    assert "kas-notiek-latvija" in slug.lower() or "knl" in slug.lower()
    assert len(slug) <= 60


def test_slug_from_metadata_diacritics_stripped():
    slug = slug_from_metadata(published_at="2026-04-15", title="Šlesera intervija")
    assert "š" not in slug
    assert slug.isascii()
