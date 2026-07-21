"""Thin wrapper around google-genai SDK for image generation.

Retries on 429/5xx up to MAX_RETRIES with exponential backoff. Raises
SafetyError when model refuses content or returns no image data.
"""
import time
from google import genai
from google.genai.errors import APIError
from google.genai import types as genai_types

from src.graphics.config import load_gemini_key

MAX_RETRIES = 3
INITIAL_BACKOFF_SEC = 2.0
RETRIABLE_STATUS = {429, 500, 502, 503, 504}


class SafetyError(RuntimeError):
    """Raised when the model refuses to generate due to safety filters
    or returns no image data."""


_client = None


def _get_client():
    global _client
    if _client is None:
        key = load_gemini_key()
        _client = genai.Client(api_key=key["api_key"])
    return _client


def generate_image(prompt: str, aspect_ratio: str = "16:9") -> bytes:
    """Call Gemini image API with retry logic. Returns PNG bytes.

    Raises SafetyError if content is refused. Raises google.genai.errors.APIError
    for non-retriable errors or if API keeps failing past MAX_RETRIES.
    """
    key = load_gemini_key()
    client = _get_client()

    for attempt in range(MAX_RETRIES + 1):
        try:
            response = client.models.generate_content(
                model=key["model"],
                contents=prompt,
                config=genai_types.GenerateContentConfig(
                    response_modalities=["TEXT", "IMAGE"],
                    image_config=genai_types.ImageConfig(aspect_ratio=aspect_ratio),
                ),
            )
            return _extract_image_bytes(response)
        except APIError as e:
            if _is_retriable(e) and attempt < MAX_RETRIES:
                backoff = INITIAL_BACKOFF_SEC * (2 ** attempt)
                time.sleep(backoff)
                continue
            raise

    # Unreachable: loop either returns or raises
    raise RuntimeError("generate_image exhausted retries without raising")


def _is_retriable(err: APIError) -> bool:
    return getattr(err, "code", None) in RETRIABLE_STATUS


def _extract_image_bytes(response) -> bytes:
    """Pull PNG bytes from the first inline_data part. Raises SafetyError otherwise."""
    # Check finish_reason for safety block
    if response.candidates:
        cand = response.candidates[0]
        finish = getattr(cand, "finish_reason", None)
        # finish_reason may be an enum or string; compare by name
        finish_str = getattr(finish, "name", finish)
        if finish_str == "SAFETY":
            raise SafetyError("Content blocked by safety filter (finish_reason=SAFETY)")

    # Iterate parts — docs show response.parts as top-level accessor
    parts = getattr(response, "parts", None)
    if parts is None and response.candidates:
        parts = response.candidates[0].content.parts

    if not parts:
        raise SafetyError("No parts in response (possibly blocked)")

    for part in parts:
        inline = getattr(part, "inline_data", None)
        data = getattr(inline, "data", None) if inline else None
        if data:
            return data

    raise SafetyError("No image data in response parts")
