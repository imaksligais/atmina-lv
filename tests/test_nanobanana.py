"""Tests for src.graphics.nanobanana — Gemini image client with retry + SafetyError."""
import pytest
from unittest.mock import patch, MagicMock
from google.genai.errors import APIError
from src.graphics import nanobanana


def _make_image_response(data: bytes):
    """Build a mock response with one inline_data part."""
    resp = MagicMock()
    part = MagicMock()
    part.inline_data.data = data
    part.inline_data.mime_type = "image/png"
    resp.parts = [part]
    cand = MagicMock()
    cand.finish_reason = "STOP"
    cand.content.parts = [part]
    resp.candidates = [cand]
    return resp


def _make_safety_response():
    resp = MagicMock()
    resp.parts = []
    cand = MagicMock()
    cand.finish_reason = "SAFETY"
    cand.content.parts = []
    resp.candidates = [cand]
    return resp


def test_generate_image_returns_bytes_on_success():
    fake_client = MagicMock()
    fake_client.models.generate_content.return_value = _make_image_response(b"fake-png-bytes")

    with patch("src.graphics.nanobanana._get_client", return_value=fake_client):
        with patch("src.graphics.nanobanana.load_gemini_key",
                   return_value={"api_key": "k", "model": "m"}):
            result = nanobanana.generate_image("test prompt", aspect_ratio="16:9")
    assert result == b"fake-png-bytes"


def test_generate_image_retries_on_rate_limit():
    rate_limit = APIError(429, {"error": {"message": "rate limit"}})
    success = _make_image_response(b"eventual-success")

    fake_client = MagicMock()
    fake_client.models.generate_content.side_effect = [rate_limit, rate_limit, success]

    with patch("src.graphics.nanobanana._get_client", return_value=fake_client):
        with patch("src.graphics.nanobanana.load_gemini_key",
                   return_value={"api_key": "k", "model": "m"}):
            with patch("src.graphics.nanobanana.time.sleep"):
                result = nanobanana.generate_image("prompt")
    assert result == b"eventual-success"
    assert fake_client.models.generate_content.call_count == 3


def test_generate_image_raises_safety_error():
    fake_client = MagicMock()
    fake_client.models.generate_content.return_value = _make_safety_response()

    with patch("src.graphics.nanobanana._get_client", return_value=fake_client):
        with patch("src.graphics.nanobanana.load_gemini_key",
                   return_value={"api_key": "k", "model": "m"}):
            with pytest.raises(nanobanana.SafetyError):
                nanobanana.generate_image("prompt")


def test_generate_image_gives_up_after_max_retries():
    rate_limit = APIError(429, {"error": {"message": "rate limit"}})

    fake_client = MagicMock()
    fake_client.models.generate_content.side_effect = rate_limit

    with patch("src.graphics.nanobanana._get_client", return_value=fake_client):
        with patch("src.graphics.nanobanana.load_gemini_key",
                   return_value={"api_key": "k", "model": "m"}):
            with patch("src.graphics.nanobanana.time.sleep"):
                with pytest.raises(APIError):
                    nanobanana.generate_image("prompt")
    # 1 initial + 3 retries = 4 total attempts
    assert fake_client.models.generate_content.call_count == 4


def test_non_retriable_error_raises_immediately():
    auth_error = APIError(401, {"error": {"message": "unauthorized"}})

    fake_client = MagicMock()
    fake_client.models.generate_content.side_effect = auth_error

    with patch("src.graphics.nanobanana._get_client", return_value=fake_client):
        with patch("src.graphics.nanobanana.load_gemini_key",
                   return_value={"api_key": "k", "model": "m"}):
            with patch("src.graphics.nanobanana.time.sleep"):
                with pytest.raises(APIError):
                    nanobanana.generate_image("prompt")
    assert fake_client.models.generate_content.call_count == 1
