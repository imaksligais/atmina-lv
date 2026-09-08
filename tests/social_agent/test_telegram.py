from unittest.mock import MagicMock, patch

from src.social_agent import telegram as tg


def test_send_draft_with_image_calls_sendphoto(monkeypatch, tmp_path):
    img = tmp_path / "card.png"
    img.write_bytes(b"\x89PNG")
    monkeypatch.setattr(tg, "_bot_token", lambda: "BOT-TOKEN")
    monkeypatch.setattr(tg, "_operator_chat_id", lambda: "12345")

    fake_response = MagicMock()
    fake_response.json.return_value = {"ok": True, "result": {"message_id": 42}}
    fake_response.raise_for_status = MagicMock()

    with patch("src.social_agent.telegram.httpx.post", return_value=fake_response) as post:
        msg_id = tg.send_draft(
            draft_id=7,
            pillar="pretrunas",
            text="Sample text",
            image_path=str(img),
        )
    assert msg_id == "42"
    url, kwargs = post.call_args[0], post.call_args[1]
    assert "sendPhoto" in url[0]
    assert "BOT-TOKEN" in url[0]
    assert kwargs["data"]["chat_id"] == "12345"
    assert "Draft #7" in kwargs["data"]["caption"]
    assert "pretrunas" in kwargs["data"]["caption"]


def test_send_draft_without_image_calls_sendmessage(monkeypatch):
    monkeypatch.setattr(tg, "_bot_token", lambda: "T")
    monkeypatch.setattr(tg, "_operator_chat_id", lambda: "1")
    fake_response = MagicMock()
    fake_response.json.return_value = {"ok": True, "result": {"message_id": 7}}
    fake_response.raise_for_status = MagicMock()
    with patch("src.social_agent.telegram.httpx.post", return_value=fake_response) as post:
        msg_id = tg.send_draft(draft_id=3, pillar="stats", text="x", image_path=None)
    assert msg_id == "7"
    assert "sendMessage" in post.call_args[0][0]
    assert "Draft #3" in post.call_args[1]["data"]["text"]


def test_parse_ok_command():
    cmd = tg.parse_reply("ok 42")
    assert cmd == {"action": "ok", "draft_id": 42, "instruction": None}


def test_parse_skip_command():
    cmd = tg.parse_reply("skip 42")
    assert cmd == {"action": "skip", "draft_id": 42, "instruction": None}


def test_parse_revise_command():
    cmd = tg.parse_reply("42 pārraksti īsāk un bez emoji")
    assert cmd == {
        "action": "revise",
        "draft_id": 42,
        "instruction": "pārraksti īsāk un bez emoji",
    }


def test_parse_with_extra_whitespace():
    assert tg.parse_reply("  ok   42  ") == {
        "action": "ok", "draft_id": 42, "instruction": None
    }


def test_parse_returns_none_on_garbage():
    assert tg.parse_reply("hello there") is None
    assert tg.parse_reply("") is None
    assert tg.parse_reply("42") is None  # id without instruction is ambiguous
