from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.social_agent import publisher


def test_load_atmina_client_reads_cookies_path(tmp_path, monkeypatch):
    cookies = tmp_path / "cookies.json"
    cookies.write_text("[]")
    monkeypatch.setattr(publisher, "_cookies_path", lambda: str(cookies))

    fake_client = MagicMock()
    fake_client.load_cookies = MagicMock()
    with patch("src.social_agent.publisher.Client", return_value=fake_client) as ClientCls:
        c = publisher.load_atmina_client()
        ClientCls.assert_called_once_with("en-US")
        fake_client.load_cookies.assert_called_once_with(str(cookies))
        assert c is fake_client


def test_load_atmina_client_raises_when_no_cookies(monkeypatch):
    monkeypatch.setattr(publisher, "_cookies_path", lambda: "/nope/missing.json")
    with pytest.raises(FileNotFoundError):
        publisher.load_atmina_client()


def test_publish_draft_with_image(monkeypatch, tmp_path):
    img = tmp_path / "img.png"
    img.write_bytes(b"\x89PNG")

    upload_mock = AsyncMock(return_value="media-123")
    tweet_mock = MagicMock()
    tweet_mock.id = "tweet-999"
    create_mock = AsyncMock(return_value=tweet_mock)

    fake_client = MagicMock()
    fake_client.upload_media = upload_mock
    fake_client.create_tweet = create_mock

    monkeypatch.setattr(publisher, "load_atmina_client", lambda: fake_client)

    tweet_id = publisher.publish_draft(text="Hello", image_path=str(img))
    assert tweet_id == "tweet-999"
    upload_mock.assert_awaited_once_with(str(img))
    create_mock.assert_awaited_once()
    _, kwargs = create_mock.call_args
    assert kwargs["text"] == "Hello"
    assert kwargs["media_ids"] == ["media-123"]


def test_publish_draft_without_image(monkeypatch):
    tweet_mock = MagicMock()
    tweet_mock.id = "tweet-000"
    fake_client = MagicMock()
    fake_client.upload_media = AsyncMock()
    fake_client.create_tweet = AsyncMock(return_value=tweet_mock)
    monkeypatch.setattr(publisher, "load_atmina_client", lambda: fake_client)

    tweet_id = publisher.publish_draft(text="Text only", image_path=None)
    assert tweet_id == "tweet-000"
    fake_client.upload_media.assert_not_awaited()
    fake_client.create_tweet.assert_awaited_once()
    _, kwargs = fake_client.create_tweet.call_args
    assert "media_ids" not in kwargs or kwargs["media_ids"] is None


def test_publish_draft_propagates_errors(monkeypatch):
    fake_client = MagicMock()
    fake_client.create_tweet = AsyncMock(side_effect=RuntimeError("rate limit"))
    monkeypatch.setattr(publisher, "load_atmina_client", lambda: fake_client)
    with pytest.raises(RuntimeError, match="rate limit"):
        publisher.publish_draft(text="x", image_path=None)
