"""Attēlu ģenerēšanas dzinēji — viens reģistrs, viens izsaukuma punkts.

2026-10-10: Gemini projekta mēneša limits izsmelts (``429 RESOURCE_EXHAUSTED``,
2026-10-09), un Codex ceļš dzīvoja gitignorētos ``.scratch/codex_*.py``
skriptos. Tagad ``cli brief`` un ``cli thread`` izvēlas dzinēju ar
``--backend`` vai ``ATMINA_IMAGE_BACKEND``; jauns dzinējs = viena funkcija
``BACKENDS`` reģistrā.

Katrs dzinējs atstāj VIENU ``image_audit`` rindu par izsaukumu (verdikts 47b):
Gemini to dara pati ``nanobanana.generate_image()``, Codex — šeit. Auditā iet
bāzes prompts bez Codex TOOL RULES, jo ``storage.link_audit_row`` rindu atrod
pēc precīza prompta.

Pārējie ``generate_image()`` izsaucēji (vienreizējie skripti, sintēzes attēls,
``social_agent``) paliek uz Gemini tieši — šis modulis tos neaiztiek.
"""

from __future__ import annotations

import json
import logging
import os
import shutil
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from src.graphics import config, nanobanana

logger = logging.getLogger(__name__)

ENV_VAR = "ATMINA_IMAGE_BACKEND"
DEFAULT_BACKEND = "gemini"

CODEX_MODEL = "codex-gpt-image"
CODEX_TIMEOUT_SEC = 900
# Codex attēlu rīks glabā rezultātu šeit, apakšmapē ar pavediena id. Moduļa
# konstante, lai testi to var novirzīt uz pagaidu mapi.
CODEX_IMAGES_DIR = Path.home() / ".codex" / "generated_images"
# Pielaide pulksteņa noapaļošanai: fails ar mtime nedaudz pirms starta vēl ir mūsējais.
_MTIME_SLACK_SEC = 5

_CODEX_RULES = (
    "\n\nTOOL RULES: Use your image generation tool exactly once and produce exactly ONE "
    "image in wide {aspect} landscape format. Do not run any shell commands, do not edit or "
    "post-process the image, do not save it anywhere yourself. When the image is generated, "
    "reply only with the word DONE."
)


@dataclass(frozen=True)
class GeneratedImage:
    data: bytes
    model: str
    cost_usd: float


class CodexError(RuntimeError):
    """Codex nepabeidza ar attēlu (nav pavediena id vai nav PNG faila)."""


def _gemini(prompt: str, *, aspect_ratio: str, kind: str, db_path: str | None) -> GeneratedImage:
    # Caur moduļu objektiem, ne piesaistītiem vārdiem — testi aizvieto
    # `src.graphics.nanobanana.generate_image` un `src.graphics.config.load_gemini_key`.
    model = config.load_gemini_key()["model"]
    data = nanobanana.generate_image(prompt, aspect_ratio=aspect_ratio, kind=kind, db_path=db_path)
    return GeneratedImage(data=data, model=model, cost_usd=config.COST_PER_IMAGE_USD)


def _codex_run(prompt: str, aspect_ratio: str) -> bytes:
    started = time.time()
    proc = subprocess.run(
        [shutil.which("codex") or "codex", "exec", "--skip-git-repo-check", "--json",
         "-s", "read-only", "--enable", "image_generation", "-"],
        input=(prompt + _CODEX_RULES.format(aspect=aspect_ratio)).encode("utf-8"),
        capture_output=True, timeout=CODEX_TIMEOUT_SEC,
    )
    stderr_tail = (proc.stderr or b"").decode("utf-8", "replace")[-600:]
    thread_id = None
    for line in (proc.stdout or b"").decode("utf-8", "replace").splitlines():
        try:
            event = json.loads(line)
        except ValueError:
            continue
        if isinstance(event, dict) and event.get("type") == "thread.started":
            thread_id = event.get("thread_id")
    if not thread_id:
        raise CodexError(
            f"codex: nav thread.started (exit {proc.returncode}); stderr: {stderr_tail!r}"
        )
    images = sorted(
        (f for f in (CODEX_IMAGES_DIR / thread_id).glob("*.png")
         if f.stat().st_mtime >= started - _MTIME_SLACK_SEC),
        key=lambda f: f.stat().st_mtime,
    )
    if not images:
        raise CodexError(
            f"codex: nav attēla (thread {thread_id}, exit {proc.returncode}); "
            f"stderr: {stderr_tail!r}"
        )
    if len(images) > 1:
        logger.warning("codex izveidoja %d attēlus (thread %s), ņemu pēdējo", len(images), thread_id)
    return images[-1].read_bytes()


def _codex(prompt: str, *, aspect_ratio: str, kind: str, db_path: str | None) -> GeneratedImage:
    # Viens try ap visu mēģinājumu: arī FileNotFoundError (nav codex) un
    # TimeoutExpired atstāj kļūdas rindu, ne klusu iztrūkumu.
    try:
        data = _codex_run(prompt, aspect_ratio)
    except Exception as e:
        nanobanana._write_audit_row(
            kind, CODEX_MODEL, prompt, aspect_ratio, 0.0, "error",
            f"{type(e).__name__}: {e}"[:500], db_path,
        )
        raise
    nanobanana._write_audit_row(kind, CODEX_MODEL, prompt, aspect_ratio, 0.0, "ok", None, db_path)
    return GeneratedImage(data=data, model=CODEX_MODEL, cost_usd=0.0)


BACKENDS: dict[str, Callable[..., GeneratedImage]] = {
    "gemini": _gemini,
    "codex": _codex,
}

# Modeļa nosaukums `brief_images` kļūdas rindai, kad attēla (un tātad
# GeneratedImage) nav.
_MODEL_NAMES: dict[str, Callable[[], str]] = {
    "gemini": lambda: config.load_gemini_key()["model"],
    "codex": lambda: CODEX_MODEL,
}


def resolve_backend(backend: str | None = None) -> str:
    """``backend`` → env ``ATMINA_IMAGE_BACKEND`` → ``"gemini"``.

    Nezināms nosaukums → ``ValueError`` ar pieejamo sarakstu; klusa atkāpšanās
    uz Gemini būtu tieši tā klusā veiksme, ko CLAUDE.md aizliedz.
    """
    name = backend or os.environ.get(ENV_VAR) or DEFAULT_BACKEND
    if name not in BACKENDS:
        raise ValueError(
            f"Nezināms attēlu dzinējs {name!r}; pieejamie: {', '.join(sorted(BACKENDS))}"
        )
    return name


def model_name(backend: str | None = None) -> str:
    return _MODEL_NAMES[resolve_backend(backend)]()


def generate(
    prompt: str,
    *,
    aspect_ratio: str = "16:9",
    kind: str,
    backend: str | None = None,
    db_path: str | None = None,
) -> GeneratedImage:
    """Ģenerē vienu attēlu ar izvēlēto dzinēju; ``kind`` iet audita rindā."""
    fn = BACKENDS[resolve_backend(backend)]
    return fn(prompt, aspect_ratio=aspect_ratio, kind=kind, db_path=db_path)
