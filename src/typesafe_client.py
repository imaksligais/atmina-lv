"""Thin client for TypeSafe System One (Jev).

Contract: POST https://api.typesafe.ai/v1/systemone with
{"state": ..., "model": ..., "questions": {...}}; answers come back under the
same question ids. Choice answers carry `choice`, `confidence` and
`probabilities` (option -> float). Docs: https://docs.typesafe.ai/api.md

Key: env TYPESAFE_API_KEY overrides keyring politracker/typesafe_api_key.
Callers are expected to FAIL OPEN on TypeSafeUnavailable.
"""
from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request

from src.credentials import get_credential

API_URL = "https://api.typesafe.ai/v1/systemone"
DEFAULT_MODEL = "jev-latest"
# 429 + 529 are the documented back-off-and-retry codes; 5xx gateway errors
# are transient in practice.
_RETRY_CODES = {429, 500, 502, 503, 504, 529}


class TypeSafeUnavailable(RuntimeError):
    """Raised when a judgment cannot be obtained (no key, HTTP error, timeout)."""


def _api_key() -> str:
    key = os.environ.get("TYPESAFE_API_KEY") or get_credential("typesafe_api_key")
    if not key:
        raise TypeSafeUnavailable("typesafe_api_key not set (keyring politracker / env TYPESAFE_API_KEY)")
    return key


def system_one(state, questions: dict, *, model: str = DEFAULT_MODEL,
               timeout: int = 60, retries: int = 3) -> dict:
    """Evaluate `state` against `questions`; return the parsed response body."""
    key = _api_key()
    body = json.dumps({"state": state, "model": model, "questions": questions},
                      ensure_ascii=False).encode("utf-8")
    last_err: Exception | None = None
    for attempt in range(retries):
        req = urllib.request.Request(
            API_URL, data=body, method="POST",
            headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
        )
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            last_err = e
            if e.code not in _RETRY_CODES:
                raise TypeSafeUnavailable(f"HTTP {e.code}") from e
        except (urllib.error.URLError, TimeoutError, OSError) as e:
            last_err = e
        if attempt < retries - 1:
            time.sleep(1.5 * 2 ** attempt)
    raise TypeSafeUnavailable(f"exhausted {retries} attempts: {last_err}")
