"""fastText language identification (lid.176) — the leaf `src.ingest` used to carry.

Carved out of ``src/ingest.py`` on 2026-09-05 (plan
docs/plans/2026-09-05-strukturas-tirisanas-plans.md § 5.4). Pure move: no
behaviour, no comment and no name changed. ``src.ingest`` re-exports every
name below under its original spelling, because ``src/quality.py``,
``scripts/ingest_vestnesis.py`` and ``tests/test_quality.py`` all reach these
through ``from src.ingest import ...`` / ``monkeypatch.setattr(src.ingest,
"_detect_language", ...)``. New callers should import from here.

Note the module-level ``_ft_model`` cache: it is per-MODULE, so patching the
ingest re-export swaps the function, not this cache — that is the same
behaviour as before the move.
"""

import os
import time

import numpy as np

# --- Language detection (fasttext) ---

_ft_model = None

# Vendored language-ID model (fasttext lid.176, compressed ~917 KB `.ftz`),
# committed at tests/calibration_results/lid.176.ftz so the diacritic
# write-gate in src/quality.py never depends on a network fetch or an HF
# token at runtime (CHANGELOG arhīvs 2026-08-19 «Vārtu vilnis 2», fasttext lid-modelis).
# The download path below is a fallback only — e.g. an archive checkout that
# strips binaries.
_FT_MODEL_URL = "https://dl.fbaipublicfiles.com/fasttext/supervised-models/lid.176.ftz"
_FT_MODEL_RETRIES = 3


def _ft_model_path() -> str:
    """Repo-relative path to the vendored lid.176 model, CWD-independent.

    Resolving against ``__file__`` (not the process CWD) is the point: a run
    from a foreign directory must still find the committed file instead of
    silently falling back to a network download, which is what degrades the
    diacritic gate open when the fetch fails (src/quality.py candidate #3).
    """
    repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(repo_root, "tests", "calibration_results", "lid.176.ftz")


def _download_ft_model(model_path: str) -> None:
    """Fetch lid.176 with retry, written atomically.

    ``os.replace`` after a completed download ensures a partial transfer can
    never leave a corrupt file behind — a corrupt cache makes
    ``fasttext.load_model`` fail forever and wedges the gate as permanently
    unavailable (worse than a one-off fetch failure).
    """
    import urllib.request

    os.makedirs(os.path.dirname(model_path), exist_ok=True)
    tmp_path = model_path + ".part"
    last_exc: Exception | None = None
    for attempt in range(_FT_MODEL_RETRIES):
        try:
            urllib.request.urlretrieve(_FT_MODEL_URL, tmp_path)
            os.replace(tmp_path, model_path)
            return
        except Exception as exc:  # noqa: BLE001 — network fetch: retry, then raise
            last_exc = exc
            time.sleep(2 ** attempt)
    if last_exc is not None:
        raise last_exc
    raise RuntimeError("fasttext lid.176 download failed")  # pragma: no cover


def _get_ft_model():
    global _ft_model
    if _ft_model is None:
        import fasttext
        import warnings
        warnings.filterwarnings("ignore", category=UserWarning, module="fasttext")
        model_path = _ft_model_path()
        if not os.path.exists(model_path):
            _download_ft_model(model_path)
        _ft_model = fasttext.load_model(model_path)
    return _ft_model


def _detect_language(text: str) -> tuple[str, float]:
    model = _get_ft_model()
    # Limit to first 2000 chars for detection (fasttext chokes on huge texts)
    clean = text[:2000].replace("\n", " ").strip()
    _orig_array = np.array
    def _compat_array(*args, **kwargs):
        kwargs.pop("copy", None)
        return _orig_array(*args, **kwargs)
    np.array = _compat_array
    try:
        predictions = model.predict(clean, k=3)
    finally:
        np.array = _orig_array
    labels, scores = predictions
    lang = labels[0].replace("__label__", "")
    return lang, float(scores[0])
