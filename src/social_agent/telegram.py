"""Telegram Bot API wrapper (httpx, no MCP dependency)."""
from __future__ import annotations

import re

import httpx

from src.credentials import get_credential


BASE = "https://api.telegram.org/bot"


def _bot_token() -> str:
    t = get_credential("telegram_bot_token")
    if not t:
        raise RuntimeError(
            "telegram_bot_token not set. Configure via: "
            "python -m src.credentials set telegram_bot_token"
        )
    return t


def _operator_chat_id() -> str:
    c = get_credential("telegram_operator_chat_id")
    if not c:
        raise RuntimeError(
            "telegram_operator_chat_id not set. Configure via: "
            "python -m src.credentials set telegram_operator_chat_id"
        )
    return c


def _caption(draft_id: int, pillar: str, text: str) -> str:
    return (
        f"Draft #{draft_id} · {pillar}\n\n"
        f"{text}\n\n—\n"
        f"Approve: `ok {draft_id}` · Skip: `skip {draft_id}` · "
        f"Revise: `{draft_id} <instruction>`"
    )


def send_draft(
    draft_id: int, pillar: str, text: str, image_path: str | None
) -> str:
    """Send a draft preview to the operator's Telegram chat.

    Returns the Telegram message_id as string so it can be stored in social_drafts.
    """
    token = _bot_token()
    chat_id = _operator_chat_id()
    caption = _caption(draft_id, pillar, text)

    if image_path:
        url = f"{BASE}{token}/sendPhoto"
        with open(image_path, "rb") as f:
            files = {"photo": f}
            data = {"chat_id": chat_id, "caption": caption, "parse_mode": "Markdown"}
            resp = httpx.post(url, data=data, files=files, timeout=30.0)
    else:
        url = f"{BASE}{token}/sendMessage"
        data = {"chat_id": chat_id, "text": caption, "parse_mode": "Markdown"}
        resp = httpx.post(url, data=data, timeout=30.0)

    resp.raise_for_status()
    return str(resp.json()["result"]["message_id"])


_CMD_PREFIX_RE = re.compile(r"^\s*(ok|skip)\s+(\d+)\s*$", re.IGNORECASE)
_CMD_REVISE_RE = re.compile(r"^\s*(\d+)\s+(\S.*\S|\S)\s*$")


def parse_reply(text: str) -> dict | None:
    """Parse an operator reply into a command dict or None if unrecognized.

    Forms:
      - "ok <id>"              → {"action": "ok", "draft_id": N, "instruction": None}
      - "skip <id>"            → {"action": "skip", ...}
      - "<id> <freetext>"      → {"action": "revise", "instruction": "<freetext>"}
    """
    if not text:
        return None
    m = _CMD_PREFIX_RE.match(text)
    if m:
        return {"action": m.group(1).lower(), "draft_id": int(m.group(2)), "instruction": None}
    m = _CMD_REVISE_RE.match(text)
    if m:
        instruction = m.group(2).strip()
        return {"action": "revise", "draft_id": int(m.group(1)), "instruction": instruction}
    return None
