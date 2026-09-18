"""Thin wrapper around google-genai SDK for image generation.

Retries on 429/5xx up to MAX_RETRIES with exponential backoff. Raises
SafetyError when model refuses content or returns no image data.

Katrs izsaukums raksta VIENU ``image_audit`` rindu (verdikts 47b, 2026-09-07),
tāpēc mēneša budžetam (5,00 USD) ir viens saucējs neatkarīgi no tā, vai izsaucējs
ir ``cli brief``, ``cli thread`` vai vienreizējs skripts. Rinda top gan
veiksmīgam izsaukumam (``status='ok'``, 0,039 USD), gan galīgai kļūdai
(``status='error'``, 0,0 USD) — pārtraukts izsaukums, kas neizmaksāja neko,
budžetu neuzpūš, bet paliek redzams.
"""
import logging
import time

from google import genai
from google.genai.errors import APIError
from google.genai import types as genai_types

from src.graphics.config import COST_PER_IMAGE_USD, load_gemini_key

logger = logging.getLogger(__name__)

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


def _write_audit_row(
    kind: str, model: str, prompt: str, aspect: str,
    cost: float, status: str, error_message: str | None,
    db_path: str | None,
) -> None:
    """Ieraksta vienu ``image_audit`` rindu; kļūdu SKAĻI logo, bet nepārmet.

    Audita rinda ir uzskaite, attēls ir produkts — nogāzt jau saņemtu attēlu
    tāpēc, ka neizdevās ieraksts, būtu dārgāka kļūda. Toties klusa neizdošanās
    ir tieši tas defektu klase, ko CLAUDE.md § „Silent success" aizliedz, tāpēc
    neizdošanās iet ERROR līmenī ar visu, kas rindā būtu bijis.
    """
    try:
        from src.db import get_db
        from src.graphics.storage import save_audit_row

        db = get_db(db_path)
        save_audit_row(
            db, kind=kind, model=model, prompt=prompt, aspect=aspect,
            cost=cost, status=status, error_message=error_message,
        )
    except Exception as audit_err:  # pragma: no cover — aizsargs, ne ceļš
        logger.error(
            "image_audit rinda NETIKA ierakstīta (%s): kind=%s model=%s "
            "aspect=%s cost=%.3f status=%s prompt[:80]=%r",
            audit_err, kind, model, aspect, cost, status, prompt[:80],
        )


def generate_image(
    prompt: str,
    aspect_ratio: str = "16:9",
    *,
    kind: str = "direct",
    db_path: str | None = None,
) -> bytes:
    """Call Gemini image API with retry logic. Returns PNG bytes.

    Raises SafetyError if content is refused. Raises google.genai.errors.APIError
    for non-retriable errors or if API keeps failing past MAX_RETRIES.

    ``kind`` marķē ceļu audita rindā ('brief' | 'weekly' | 'synthesis' |
    'thread' | 'direct'); noklusējums 'direct' sedz vienreizējos skriptus, kas
    par audita tabulu neko nezina. ``db_path`` ir tikai testiem — ražošanā tiek
    izmantota noklusējuma bāze.
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
            png = _extract_image_bytes(response)
        except APIError as e:
            if _is_retriable(e) and attempt < MAX_RETRIES:
                backoff = INITIAL_BACKOFF_SEC * (2 ** attempt)
                time.sleep(backoff)
                continue
            _write_audit_row(
                kind, key["model"], prompt, aspect_ratio, 0.0, "error",
                f"{type(e).__name__}: {e}"[:500], db_path,
            )
            raise
        except SafetyError as e:
            _write_audit_row(
                kind, key["model"], prompt, aspect_ratio, 0.0, "error",
                f"{type(e).__name__}: {e}"[:500], db_path,
            )
            raise
        else:
            _write_audit_row(
                kind, key["model"], prompt, aspect_ratio,
                COST_PER_IMAGE_USD, "ok", None, db_path,
            )
            return png

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
