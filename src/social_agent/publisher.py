"""twikit wrapper — posts drafts to @atmina_lv."""
from __future__ import annotations

import asyncio
from pathlib import Path

from twikit import Client

from src.credentials import get_credential


def _cookies_path() -> str:
    path = get_credential("x_atmina_cookies_path") or "data/x_cookies_atmina.json"
    return path


def load_atmina_client() -> Client:
    """Load a twikit Client authenticated with the dedicated @atmina_lv cookie file."""
    path = _cookies_path()
    if not Path(path).exists():
        raise FileNotFoundError(
            f"@atmina_lv cookies not found at {path}. "
            "Set via: python -m src.credentials set x_atmina_cookies_path"
        )
    client = Client("en-US")
    client.load_cookies(path)
    return client


def publish_draft(text: str, image_path: str | None) -> str:
    """Upload media (if any) and post a tweet. Returns the tweet id as string.

    Raises any underlying twikit exception so callers can record status='failed'.
    """
    return asyncio.run(_publish_async(text, image_path))


async def _publish_async(text: str, image_path: str | None) -> str:
    client = load_atmina_client()
    kwargs: dict = {"text": text}
    if image_path:
        media_id = await client.upload_media(image_path)
        kwargs["media_ids"] = [media_id]
    tweet = await client.create_tweet(**kwargs)
    return str(tweet.id)
