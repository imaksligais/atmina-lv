"""Tests for src.graphics.config — API key loading + budget constants."""
import json
import pytest
from unittest.mock import patch
from src.graphics import config


def test_load_gemini_key_returns_api_key_and_model(tmp_path):
    key_file = tmp_path / "gemini_key.json"
    key_file.write_text(json.dumps({
        "api_key": "test-key-123",
        "model": "gemini-3.1-flash-image-preview",
    }))
    with patch("src.graphics.config.KEY_PATH", key_file):
        result = config.load_gemini_key()
    assert result == {
        "api_key": "test-key-123",
        "model": "gemini-3.1-flash-image-preview",
    }


def test_load_gemini_key_missing_file_raises(tmp_path):
    missing = tmp_path / "nonexistent.json"
    with patch("src.graphics.config.KEY_PATH", missing):
        with pytest.raises(FileNotFoundError, match="gemini_key.json"):
            config.load_gemini_key()


def test_load_gemini_key_empty_api_key_raises(tmp_path):
    key_file = tmp_path / "gemini_key.json"
    key_file.write_text(json.dumps({"api_key": "", "model": "x"}))
    with patch("src.graphics.config.KEY_PATH", key_file):
        with pytest.raises(ValueError, match="empty"):
            config.load_gemini_key()


def test_load_gemini_key_empty_model_raises(tmp_path):
    key_file = tmp_path / "gemini_key.json"
    key_file.write_text(json.dumps({"api_key": "abc", "model": ""}))
    with patch("src.graphics.config.KEY_PATH", key_file):
        with pytest.raises(ValueError, match="model"):
            config.load_gemini_key()


def test_monthly_budget_and_cost_constants():
    assert config.MONTHLY_BUDGET_USD == 5.00
    assert config.COST_PER_IMAGE_USD == 0.039


def test_budget_exceeded_error_exists():
    assert issubclass(config.BudgetExceededError, RuntimeError)
