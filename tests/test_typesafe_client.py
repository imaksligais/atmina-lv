import io
import json
from unittest.mock import patch

import pytest

from src import typesafe_client as tc


class _Resp(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


def _fake_urlopen(payload: dict):
    body = json.dumps(payload).encode("utf-8")

    def _open(req, timeout=0):
        _open.last_request = req
        return _Resp(body)

    return _open


def test_system_one_posts_and_parses(monkeypatch):
    monkeypatch.setenv("TYPESAFE_API_KEY", "k-test")
    fake = _fake_urlopen({"model": "jev-1.13.0",
                          "answers": {"q": {"type": "noul", "noul": 0.93}}})
    with patch("src.typesafe_client.urllib.request.urlopen", fake):
        resp = tc.system_one({"t": "x"}, {"q": {"type": "noul", "instructions": "?"}})
    assert resp["answers"]["q"]["noul"] == 0.93
    req = fake.last_request
    assert req.get_header("Authorization") == "Bearer k-test"
    sent = json.loads(req.data.decode("utf-8"))
    assert sent["model"] == "jev-latest"
    assert sent["questions"]["q"]["type"] == "noul"


def test_missing_key_raises(monkeypatch):
    monkeypatch.delenv("TYPESAFE_API_KEY", raising=False)
    with patch("src.typesafe_client.get_credential", lambda name: None):
        with pytest.raises(tc.TypeSafeUnavailable):
            tc.system_one({"t": "x"}, {"q": {"type": "noul", "instructions": "?"}})


def test_http_error_raises_after_retries(monkeypatch):
    import urllib.error
    monkeypatch.setenv("TYPESAFE_API_KEY", "k-test")
    calls = {"n": 0}

    def _boom(req, timeout=0):
        calls["n"] += 1
        raise urllib.error.HTTPError(req.full_url, 503, "down", {}, io.BytesIO(b""))

    with patch("src.typesafe_client.urllib.request.urlopen", _boom), \
         patch("src.typesafe_client.time.sleep", lambda s: None):
        with pytest.raises(tc.TypeSafeUnavailable):
            tc.system_one({"t": "x"}, {"q": {"type": "noul", "instructions": "?"}}, retries=2)
    assert calls["n"] == 2


def test_overloaded_529_is_retried(monkeypatch):
    """Docs list 529 Overloaded next to 429 as back-off-and-retry."""
    import urllib.error
    monkeypatch.setenv("TYPESAFE_API_KEY", "k-test")
    calls = {"n": 0}
    ok = _fake_urlopen({"model": "jev", "answers": {"q": {"type": "noul", "noul": 0.5}}})

    def _flaky(req, timeout=0):
        calls["n"] += 1
        if calls["n"] == 1:
            raise urllib.error.HTTPError(req.full_url, 529, "overloaded", {}, io.BytesIO(b""))
        return ok(req, timeout)

    with patch("src.typesafe_client.urllib.request.urlopen", _flaky), \
         patch("src.typesafe_client.time.sleep", lambda s: None):
        resp = tc.system_one({"t": "x"}, {"q": {"type": "noul", "instructions": "?"}}, retries=3)
    assert resp["answers"]["q"]["noul"] == 0.5 and calls["n"] == 2
