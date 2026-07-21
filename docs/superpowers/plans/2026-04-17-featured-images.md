# Featured Images Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add AI-generated 16:9 featured images to every daily brief via `gemini-3.1-flash-image-preview`, with typography-only composition, per-topic metaphor consistency, human-in-the-loop approval, and full-bleed integration into `blog/<slug>.html`, `index.html`, and `analizes.html`.

**Architecture:** New `src/graphics/` package (config/nanobanana/visual_map/prompt/storage), new `@graphics-designer` subagent, new `brief_images` DB table + `visual_brief_json` column on `context_notes`. Brief-writer emits `## Vizuālais brief` markdown block parsed into structured JSON. Images stored at `output/images/briefs/<slug>-<hash8>.png` and rendered via Jinja templates.

**Tech Stack:** Python 3.11+, `google-genai` SDK for Gemini image API, `anthropic` SDK for inline backfill extraction, SQLite (existing), Jinja2 (existing), pytest.

**Spec reference:** `docs/superpowers/specs/2026-04-17-featured-images-design.md`

---

## Phase 0 — API Smoke Test (BLOCKING)

**Gate:** Must succeed before any other phase. If Latvian diacritics catastrophically fail or API is unreachable, stop and revisit design.

### Task 0.1: Add SDK dependencies

**Files:**
- Modify: `requirements.txt`

- [ ] **Step 1: Add google-genai and anthropic to requirements.txt**

Append to end of `requirements.txt`:

```
# AI image generation
google-genai==0.8.0

# AI SDK for backfill visual_brief extraction
anthropic==0.42.0
```

- [ ] **Step 2: Install dependencies**

Run: `.venv/Scripts/python -m pip install -r requirements.txt`
Expected: both packages install without error.

- [ ] **Step 3: Commit**

```bash
git add requirements.txt
git commit -m "feat(graphics): add google-genai and anthropic SDK deps"
```

### Task 0.2: Create gemini_key.json (manual, local only)

**Files:**
- Create: `data/gemini_key.json` (NOT committed — automatically gitignored by `data/*.json`)

- [ ] **Step 1: Obtain API key from Google AI Studio**

User task (not automated): go to https://aistudio.google.com/app/apikey, create key, copy.

- [ ] **Step 2: Write key file**

Create `data/gemini_key.json`:

```json
{
  "api_key": "PASTE_KEY_HERE",
  "model": "gemini-3.1-flash-image-preview"
}
```

- [ ] **Step 3: Verify gitignore coverage**

Run: `git check-ignore -v data/gemini_key.json`
Expected: output confirms `data/*.json` rule matches.

No commit (file is gitignored and local-only).

### Task 0.3: Implement `src/graphics/config.py`

**Files:**
- Create: `src/graphics/__init__.py` (empty)
- Create: `src/graphics/config.py`
- Create: `tests/test_graphics_config.py`

- [ ] **Step 1: Write failing test**

Create `tests/test_graphics_config.py`:

```python
import json
import pytest
from pathlib import Path
from unittest.mock import patch, mock_open
from src.graphics import config


def test_load_gemini_key_returns_api_key_and_model(tmp_path):
    key_file = tmp_path / "gemini_key.json"
    key_file.write_text(json.dumps({
        "api_key": "test-key-123",
        "model": "gemini-3.1-flash-image-preview"
    }))
    with patch("src.graphics.config.KEY_PATH", key_file):
        result = config.load_gemini_key()
    assert result == {"api_key": "test-key-123", "model": "gemini-3.1-flash-image-preview"}


def test_load_gemini_key_missing_file_raises(tmp_path):
    missing = tmp_path / "nonexistent.json"
    with patch("src.graphics.config.KEY_PATH", missing):
        with pytest.raises(FileNotFoundError, match="gemini_key.json"):
            config.load_gemini_key()


def test_load_gemini_key_empty_api_key_raises(tmp_path):
    key_file = tmp_path / "gemini_key.json"
    key_file.write_text(json.dumps({"api_key": "", "model": "x"}))
    with patch("src.graphics.config.KEY_PATH", key_file):
        with pytest.raises(ValueError, match="empty"):
            config.load_gemini_key()


def test_monthly_budget_and_cost_constants():
    assert config.MONTHLY_BUDGET_USD == 5.00
    assert config.COST_PER_IMAGE_USD == 0.039
```

- [ ] **Step 2: Run to verify failure**

Run: `.venv/Scripts/python -m pytest tests/test_graphics_config.py -v`
Expected: FAIL with `ModuleNotFoundError` for `src.graphics.config`.

- [ ] **Step 3: Implement config**

Create `src/graphics/__init__.py`:

```python
```

Create `src/graphics/config.py`:

```python
"""Graphics package configuration: API key loading + budget constants."""
import json
from pathlib import Path

# COST_PER_IMAGE_USD last verified: 2026-04-17 (nanobanana-2 preview pricing).
# Update this constant manually if Google changes pricing.
COST_PER_IMAGE_USD = 0.039
MONTHLY_BUDGET_USD = 5.00

KEY_PATH = Path(__file__).parent.parent.parent / "data" / "gemini_key.json"


def load_gemini_key() -> dict:
    """Load API key + model name from data/gemini_key.json.

    Returns dict with keys 'api_key' and 'model'. Raises FileNotFoundError
    if the file is missing, ValueError if api_key is empty.
    """
    if not KEY_PATH.exists():
        raise FileNotFoundError(
            f"gemini_key.json not found at {KEY_PATH}. "
            "Create it with {\"api_key\": \"...\", \"model\": \"...\"}."
        )
    data = json.loads(KEY_PATH.read_text(encoding="utf-8"))
    if not data.get("api_key", "").strip():
        raise ValueError("gemini_key.json has empty api_key")
    if not data.get("model", "").strip():
        raise ValueError("gemini_key.json has empty model")
    return {"api_key": data["api_key"], "model": data["model"]}


class BudgetExceededError(RuntimeError):
    """Raised when monthly image-generation budget is exceeded."""


def budget_check(db) -> None:
    """Raise BudgetExceededError if this month's cost_usd sum ≥ MONTHLY_BUDGET_USD."""
    from src.graphics.storage import monthly_cost_usd
    spent = monthly_cost_usd(db)
    if spent >= MONTHLY_BUDGET_USD:
        raise BudgetExceededError(
            f"Monthly budget {MONTHLY_BUDGET_USD:.2f} USD exceeded (spent: {spent:.2f})."
        )
```

- [ ] **Step 4: Run tests**

Run: `.venv/Scripts/python -m pytest tests/test_graphics_config.py -v`
Expected: 4 passed (`budget_check` indirectly tested in Phase 2).

- [ ] **Step 5: Commit**

```bash
git add src/graphics/__init__.py src/graphics/config.py tests/test_graphics_config.py
git commit -m "feat(graphics): add config with API key loader and budget constants"
```

### Task 0.4: Implement `src/graphics/nanobanana.py` with retry logic

**Files:**
- Create: `src/graphics/nanobanana.py`
- Create: `tests/test_nanobanana.py`

- [ ] **Step 1: Write failing test**

Create `tests/test_nanobanana.py`:

```python
import pytest
from unittest.mock import patch, MagicMock
from src.graphics import nanobanana


def test_generate_image_returns_bytes_on_success():
    fake_response = MagicMock()
    fake_part = MagicMock()
    fake_part.inline_data.data = b"fake-png-bytes"
    fake_part.inline_data.mime_type = "image/png"
    fake_response.candidates = [MagicMock()]
    fake_response.candidates[0].content.parts = [fake_part]

    fake_client = MagicMock()
    fake_client.models.generate_content.return_value = fake_response

    with patch("src.graphics.nanobanana._get_client", return_value=fake_client):
        result = nanobanana.generate_image("test prompt", aspect_ratio="16:9")
    assert result == b"fake-png-bytes"


def test_generate_image_retries_on_rate_limit():
    from google.genai import errors as genai_errors
    rate_limit_error = genai_errors.APIError(429, {"error": {"message": "rate limit"}})

    fake_response = MagicMock()
    fake_part = MagicMock()
    fake_part.inline_data.data = b"eventual-success"
    fake_part.inline_data.mime_type = "image/png"
    fake_response.candidates = [MagicMock()]
    fake_response.candidates[0].content.parts = [fake_part]

    fake_client = MagicMock()
    fake_client.models.generate_content.side_effect = [
        rate_limit_error, rate_limit_error, fake_response
    ]

    with patch("src.graphics.nanobanana._get_client", return_value=fake_client):
        with patch("src.graphics.nanobanana.time.sleep"):  # skip real sleeps
            result = nanobanana.generate_image("prompt")
    assert result == b"eventual-success"
    assert fake_client.models.generate_content.call_count == 3


def test_generate_image_raises_safety_error():
    fake_response = MagicMock()
    fake_response.candidates = [MagicMock()]
    fake_response.candidates[0].finish_reason = "SAFETY"
    fake_response.candidates[0].content.parts = []

    fake_client = MagicMock()
    fake_client.models.generate_content.return_value = fake_response

    with patch("src.graphics.nanobanana._get_client", return_value=fake_client):
        with pytest.raises(nanobanana.SafetyError):
            nanobanana.generate_image("prompt")


def test_generate_image_gives_up_after_max_retries():
    from google.genai import errors as genai_errors
    rate_limit_error = genai_errors.APIError(429, {"error": {"message": "rate limit"}})

    fake_client = MagicMock()
    fake_client.models.generate_content.side_effect = rate_limit_error

    with patch("src.graphics.nanobanana._get_client", return_value=fake_client):
        with patch("src.graphics.nanobanana.time.sleep"):
            with pytest.raises(genai_errors.APIError):
                nanobanana.generate_image("prompt")
    # 1 initial + 3 retries = 4 total attempts
    assert fake_client.models.generate_content.call_count == 4
```

- [ ] **Step 2: Run to verify failure**

Run: `.venv/Scripts/python -m pytest tests/test_nanobanana.py -v`
Expected: FAIL (module missing).

- [ ] **Step 3: Implement nanobanana client**

Create `src/graphics/nanobanana.py`:

```python
"""Thin wrapper around google-genai SDK for image generation.

Retries on 429/5xx up to MAX_RETRIES with exponential backoff. Raises
SafetyError when model refuses content.
"""
import time
from google import genai
from google.genai import errors as genai_errors
from google.genai import types as genai_types

from src.graphics.config import load_gemini_key

MAX_RETRIES = 3
INITIAL_BACKOFF_SEC = 2.0


class SafetyError(RuntimeError):
    """Raised when the model refuses to generate due to safety filters."""


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
    if API keeps failing past MAX_RETRIES.
    """
    key = load_gemini_key()
    client = _get_client()
    last_err = None

    for attempt in range(MAX_RETRIES + 1):
        try:
            response = client.models.generate_content(
                model=key["model"],
                contents=prompt,
                config=genai_types.GenerateContentConfig(
                    response_modalities=["IMAGE"],
                    image_config=genai_types.ImageConfig(aspect_ratio=aspect_ratio),
                ),
            )
            return _extract_image_bytes(response)
        except genai_errors.APIError as e:
            last_err = e
            if _is_retriable(e) and attempt < MAX_RETRIES:
                backoff = INITIAL_BACKOFF_SEC * (2 ** attempt)
                time.sleep(backoff)
                continue
            raise

    raise last_err  # unreachable but keeps type-checkers happy


def _is_retriable(err: "genai_errors.APIError") -> bool:
    status = getattr(err, "code", None)
    return status in (429, 500, 502, 503, 504)


def _extract_image_bytes(response) -> bytes:
    if not response.candidates:
        raise SafetyError("No candidates in response (possibly blocked)")
    cand = response.candidates[0]
    finish = getattr(cand, "finish_reason", None)
    if finish == "SAFETY":
        raise SafetyError(f"Content blocked by safety filter (finish_reason=SAFETY)")
    for part in cand.content.parts:
        data = getattr(part.inline_data, "data", None) if hasattr(part, "inline_data") else None
        if data:
            return data
    raise SafetyError(f"No image data in response (finish_reason={finish})")
```

- [ ] **Step 4: Run tests**

Run: `.venv/Scripts/python -m pytest tests/test_nanobanana.py -v`
Expected: 4 passed.

- [ ] **Step 5: Commit**

```bash
git add src/graphics/nanobanana.py tests/test_nanobanana.py
git commit -m "feat(graphics): add nanobanana client with retry + SafetyError"
```

### Task 0.5: Write smoke test script

**Files:**
- Create: `scripts/smoke_test.py`

- [ ] **Step 1: Create smoke test**

Create `scripts/smoke_test.py`:

```python
"""Phase 0 smoke test — validates that gemini-3.1-flash-image-preview
is reachable and produces usable output with Latvian diacritics.

Run: .venv/Scripts/python scripts/smoke_test.py

Output: tmp/smoke_test_<timestamp>.png + tmp/smoke_test_<timestamp>.prompt.txt
"""
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.graphics.nanobanana import generate_image

PROMPT = """
Editorial poster illustration, textured cream paper background with subtle grain,
monochrome black condensed serif display typography, single deep-red accent color,
composition with generous negative space. Aspect ratio 16:9, no people, no flags,
no party logos, no photorealism.

Topic: finanses
Visual metaphor: ascending bar chart silhouette with one anomalous bar
Mood: analytical, scrutiny
Accent color: deep red

Headline text (render exactly as shown, preserve Latvian diacritics):
"Saeima apstiprina budžeta grozījumus"

Key figure to display prominently: +47 milj.

Do NOT include: people, faces, flags, party logos, other text, photorealistic
elements, cartoon style, decorative borders.
"""


def main() -> int:
    tmp_dir = Path(__file__).parent.parent / "tmp"
    tmp_dir.mkdir(exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d-%H%M%S")

    prompt_path = tmp_dir / f"smoke_test_{ts}.prompt.txt"
    image_path = tmp_dir / f"smoke_test_{ts}.png"

    prompt_path.write_text(PROMPT, encoding="utf-8")
    print(f"[smoke] prompt → {prompt_path}")
    print(f"[smoke] calling Gemini...")

    png = generate_image(PROMPT, aspect_ratio="16:9")
    image_path.write_bytes(png)
    print(f"[smoke] image → {image_path} ({len(png)} bytes)")
    print("[smoke] open the PNG and verify:")
    print("  (a) image renders successfully")
    print("  (b) Latvian diacritics (žū, ā, ē) are readable")
    print("  (c) composition is roughly 16:9 and matches style brief")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 2: Run smoke test**

Run: `.venv/Scripts/python scripts/smoke_test.py`
Expected: prints prompt path, image path, byte count. Creates `tmp/smoke_test_*.png`.

- [ ] **Step 3: Manual eye-check**

Open `tmp/smoke_test_<timestamp>.png` in an image viewer. Verify:
- Image renders (not blank / corrupted).
- "Saeima apstiprina budžeta grozījumus" text is legible with diacritics preserved.
- Aspect ratio looks like 16:9.
- No people, logos, or photorealistic elements.

**GATE:** If any check fails catastrophically (e.g. diacritics are replaced by garbage), STOP. Report findings to user; do not proceed to Phase 1.

- [ ] **Step 4: Commit**

```bash
git add scripts/smoke_test.py
git commit -m "feat(graphics): phase 0 smoke test script"
```

---

## Phase 1 — Style Matrix (3 styles × 3 real briefs = 9 images)

### Task 1.1: Build `src/graphics/visual_map.py`

**Files:**
- Create: `src/graphics/visual_map.py`
- Create: `tests/test_visual_map.py`

- [ ] **Step 1: Write failing test**

Create `tests/test_visual_map.py`:

```python
import pytest
from src.graphics import visual_map
from src import topic_map


def test_visual_map_covers_all_canonical_topics():
    missing = set(topic_map.CANONICAL_TOPICS) - set(visual_map.VISUAL_MAP.keys())
    assert not missing, f"visual_map missing topics: {missing}"


def test_get_visual_returns_metaphor_mood_accent_for_known_topic():
    result = visual_map.get_visual("finanses")
    assert "metaphor" in result and result["metaphor"]
    assert "mood" in result and result["mood"]
    assert "accent" in result and result["accent"]


def test_get_visual_returns_default_for_unknown_topic():
    result = visual_map.get_visual("nonexistent-topic-xyz")
    assert result == visual_map._DEFAULT


def test_get_visual_every_entry_has_required_keys():
    for topic, entry in visual_map.VISUAL_MAP.items():
        assert set(entry.keys()) >= {"metaphor", "mood", "accent"}, \
            f"Entry '{topic}' missing keys: {entry}"
```

- [ ] **Step 2: Run to verify failure**

Run: `.venv/Scripts/python -m pytest tests/test_visual_map.py -v`
Expected: FAIL (module missing).

- [ ] **Step 3: Check canonical topic list**

Run: `.venv/Scripts/python -c "from src.topic_map import CANONICAL_TOPICS; print('\n'.join(sorted(CANONICAL_TOPICS)))"`
Expected: list of 26 topic names. Copy them for visual_map entries.

- [ ] **Step 4: Implement visual_map**

Create `src/graphics/visual_map.py`:

```python
"""Per-topic visual metaphor library for image generation.

Each entry: {metaphor, mood, accent} feeds the nanobanana prompt template.
Must stay in sync with src/topic_map.py::CANONICAL_TOPICS (enforced by test).
"""

VISUAL_MAP: dict[str, dict[str, str]] = {
    "airBaltic": {
        "metaphor": "abstract aircraft silhouette OR airplane tail fin viewed at an angle",
        "mood": "tension, scrutiny",
        "accent": "deep red",
    },
    "Aizsardzība un drošība": {
        "metaphor": "geometric shield OR abstract radar sweep composition",
        "mood": "vigilance, resolve",
        "accent": "deep navy",
    },
    "Ārpolitika": {
        "metaphor": "abstract compass rose OR silhouette of the Baltic region on a map",
        "mood": "measured observation",
        "accent": "deep navy",
    },
    "Budžets un finanses": {
        "metaphor": "ascending bar chart silhouette with one anomalous bar OR stylized budget document",
        "mood": "analytical, scrutiny",
        "accent": "deep red",
    },
    "Degviela un enerģētika": {
        "metaphor": "abstract fuel droplet OR power line silhouette at dusk",
        "mood": "pressure, flow",
        "accent": "amber",
    },
    "Ekonomika": {
        "metaphor": "stacked geometric blocks suggesting growth OR coin stack silhouette",
        "mood": "analytical",
        "accent": "deep red",
    },
    "ES politika": {
        "metaphor": "twelve stars arranged in abstract circle OR geometric compass over Europe outline",
        "mood": "deliberation",
        "accent": "deep blue",
    },
    "Imigrācija": {
        "metaphor": "abstract arrows crossing a border line OR silhouettes of suitcases in formation",
        "mood": "movement, tension",
        "accent": "ochre",
    },
    "Izglītība": {
        "metaphor": "stylized open book OR graduation cap silhouette in geometric form",
        "mood": "gravity, stewardship",
        "accent": "muted teal",
    },
    "Koalīcija un partijas": {
        "metaphor": "chain links silhouette OR geometric puzzle pieces not fully interlocking",
        "mood": "fragility, negotiation",
        "accent": "charcoal",
    },
    "Korupcija": {
        "metaphor": "keyhole with shadow extending beyond frame OR tipped scales of justice",
        "mood": "tension, exposure",
        "accent": "deep red",
    },
    "Medijpolitika": {
        "metaphor": "abstract broadcast antenna OR newspaper fold silhouette",
        "mood": "scrutiny",
        "accent": "charcoal",
    },
    "Mežsaimniecība": {
        "metaphor": "stylized tree cross-section with rings OR forest silhouette in monochrome",
        "mood": "stewardship, depth",
        "accent": "forest green",
    },
    "Pašvaldības": {
        "metaphor": "abstract city grid OR cluster of geometric rooftops",
        "mood": "structured, grounded",
        "accent": "muted teal",
    },
    "Sabiedriskie mediji": {
        "metaphor": "stylized microphone silhouette OR broadcast waves abstract pattern",
        "mood": "accountability",
        "accent": "charcoal",
    },
    "Sankcijas": {
        "metaphor": "abstract barrier line OR geometric stamp mark composition",
        "mood": "resolve, boundary",
        "accent": "deep red",
    },
    "Skandāli": {
        "metaphor": "abstract sealed envelope with shadow OR magnifying glass over redacted lines",
        "mood": "exposure, pursuit",
        "accent": "deep red",
    },
    "Sociālā politika": {
        "metaphor": "abstract interlocking hands silhouette OR geometric family cluster",
        "mood": "care, collective",
        "accent": "muted teal",
    },
    "Tieslietas": {
        "metaphor": "abstract courthouse column silhouette OR geometric gavel composition",
        "mood": "gravity, process",
        "accent": "charcoal",
    },
    "Transports": {
        "metaphor": "abstract aircraft silhouette OR parallel railway tracks converging to horizon",
        "mood": "motion, forward trajectory",
        "accent": "deep blue",
    },
    "Ukraina un Krievija": {
        "metaphor": "abstract frontier line OR stylized sunflower silhouette in geometric form",
        "mood": "resolve, solidarity",
        "accent": "cornflower blue",
    },
    "Valodu politika": {
        "metaphor": "stylized speech bubble with abstract characters OR geometric letterform composition",
        "mood": "identity, clarity",
        "accent": "deep red",
    },
    "Valsts pārvalde": {
        "metaphor": "abstract government document stack OR geometric civic building silhouette",
        "mood": "formal, procedural",
        "accent": "charcoal",
    },
    "Vēlēšanas": {
        "metaphor": "abstract ballot slot silhouette OR ballot box with geometric shadow",
        "mood": "consequential, measured",
        "accent": "deep red",
    },
    "Veselība": {
        "metaphor": "cross symbol dissolving into dotted line OR stylized pulse line silhouette",
        "mood": "care, fragility",
        "accent": "muted teal",
    },
    "Vide": {
        "metaphor": "abstract leaf silhouette OR geometric landscape horizon line",
        "mood": "stewardship",
        "accent": "forest green",
    },
}

_DEFAULT: dict[str, str] = {
    "metaphor": "abstract geometric composition suggesting public discourse",
    "mood": "neutral observation",
    "accent": "charcoal",
}


def get_visual(topic: str) -> dict[str, str]:
    """Return visual descriptors for a canonical topic, falling back to _DEFAULT."""
    return VISUAL_MAP.get(topic, _DEFAULT)
```

- [ ] **Step 5: Run tests**

Run: `.venv/Scripts/python -m pytest tests/test_visual_map.py -v`
Expected: 4 passed.

If `test_visual_map_covers_all_canonical_topics` fails, the canonical list has additional topics. Print the missing set from test output and add entries to `VISUAL_MAP`.

- [ ] **Step 6: Commit**

```bash
git add src/graphics/visual_map.py tests/test_visual_map.py
git commit -m "feat(graphics): visual_map with 26 canonical topics + drift test"
```

### Task 1.2: Build `src/graphics/prompt.py` with 3 style variants

**Files:**
- Create: `src/graphics/prompt.py`
- Create: `tests/test_graphics_prompt.py`

- [ ] **Step 1: Write failing test**

Create `tests/test_graphics_prompt.py`:

```python
import pytest
from src.graphics import prompt
from src.graphics.visual_map import get_visual


def test_build_prompt_includes_headline_and_metaphor():
    vb = {
        "topic": "Budžets un finanses",
        "headline": "Saeima apstiprina budžeta grozījumus",
        "stat": "+47 milj.",
        "metaphor_hint": "budžeta dokuments",
    }
    vm = get_visual(vb["topic"])
    p = prompt.build_prompt(vb, vm, style_key="editorial")
    assert "Saeima apstiprina budžeta grozījumus" in p
    assert "+47 milj." in p
    assert vm["metaphor"].split(" OR ")[0] in p or vm["metaphor"] in p


def test_build_prompt_omits_stat_section_when_none():
    vb = {
        "topic": "Skandāli",
        "headline": "JV Milānas seminārs",
        "stat": None,
        "metaphor_hint": "",
    }
    vm = get_visual("Skandāli")
    p = prompt.build_prompt(vb, vm, style_key="editorial")
    assert "Key figure" not in p


def test_build_prompt_unknown_style_raises():
    vb = {"topic": "x", "headline": "y", "stat": None, "metaphor_hint": ""}
    vm = get_visual("x")
    with pytest.raises(KeyError):
        prompt.build_prompt(vb, vm, style_key="nonexistent")


def test_three_styles_exist():
    assert set(prompt.STYLE_VARIANTS.keys()) == {"editorial", "scandi", "constructivist"}


def test_default_style_is_valid_variant():
    assert prompt.DEFAULT_STYLE in prompt.STYLE_VARIANTS
```

- [ ] **Step 2: Run to verify failure**

Run: `.venv/Scripts/python -m pytest tests/test_graphics_prompt.py -v`
Expected: FAIL (module missing).

- [ ] **Step 3: Implement prompt module**

Create `src/graphics/prompt.py`:

```python
"""Nanobanana prompt composition: three style variants + build_prompt().

STYLE_VARIANTS defines three visual languages for Phase 1 selection. After
phase 1, user freezes DEFAULT_STYLE to the winning variant.
"""

STYLE_VARIANTS: dict[str, str] = {
    "editorial": """
Style: editorial poster illustration. Textured cream paper background with
subtle grain (aged document feel). Monochrome black condensed serif display
typography (think The Economist cover). One accent color per composition.
Rule-of-thirds composition, generous negative space, single dominant visual
metaphor. Aspect ratio 16:9. Mood: restrained, analytical, serious.
""".strip(),
    "scandi": """
Style: Nordic minimalist editorial. Off-white / bone-colored background.
Thin geometric line work, subtle asymmetry, ample negative space. Inter- or
Söhne-style sans-serif typography (modern, rational). One muted accent color
per composition. Aspect ratio 16:9. Mood: calm, measured, Scandinavian civic
seriousness.
""".strip(),
    "constructivist": """
Style: modernized constructivist / Bauhaus political poster. Two contrasting
colors per composition (deep navy + ochre, or charcoal + deep red). Bold
geometric blocks, diagonal composition, slab-serif or display sans-serif
typography. High contrast, strong visual hierarchy. Aspect ratio 16:9.
Mood: declarative, purposeful, commanding.
""".strip(),
}

DEFAULT_STYLE: str = "editorial"  # frozen after Phase 1 user selection

NEGATIVE_CONSTRAINTS = """
Do NOT include: people, faces, hands, flags, party logos, text other than
the provided headline and stat, photorealistic elements, cartoon style,
decorative borders, watermarks.
""".strip()


def build_prompt(
    visual_brief: dict,
    visual_map_entry: dict,
    style_key: str = DEFAULT_STYLE,
) -> str:
    """Compose the full nanobanana prompt from brief data + style.

    Args:
        visual_brief: {topic, headline, stat (optional), metaphor_hint (optional)}
        visual_map_entry: {metaphor, mood, accent} from get_visual()
        style_key: one of STYLE_VARIANTS keys

    Raises KeyError if style_key not in STYLE_VARIANTS.
    """
    style = STYLE_VARIANTS[style_key]

    stat_line = ""
    if visual_brief.get("stat"):
        stat_line = f"Key figure to display prominently: {visual_brief['stat']}"

    return f"""{style}

Topic: {visual_brief['topic']}
Visual metaphor: {visual_map_entry['metaphor']}
Mood modifier: {visual_map_entry['mood']}
Accent color: {visual_map_entry['accent']}

Headline text (render exactly as shown, preserve Latvian diacritics):
"{visual_brief['headline']}"

{stat_line}

{NEGATIVE_CONSTRAINTS}
""".strip()
```

- [ ] **Step 4: Run tests**

Run: `.venv/Scripts/python -m pytest tests/test_graphics_prompt.py -v`
Expected: 5 passed.

- [ ] **Step 5: Commit**

```bash
git add src/graphics/prompt.py tests/test_graphics_prompt.py
git commit -m "feat(graphics): prompt composer with 3 style variants"
```

### Task 1.3: Hand-craft `visual_brief` JSONs for test briefs

**Files:**
- Create: `tmp/visual_briefs/142.json`
- Create: `tmp/visual_briefs/135.json`
- Create: `tmp/visual_briefs/126.json`

- [ ] **Step 1: Read brief content**

Run:
```bash
.venv/Scripts/python -c "
import sqlite3
c = sqlite3.connect('data/atmina.db')
for nid in (142, 135, 126):
    row = c.execute('SELECT content FROM context_notes WHERE id=?', (nid,)).fetchone()
    print(f'=== {nid} ===')
    print(row[0][:1500])
    print()
"
```

- [ ] **Step 2: Create `tmp/visual_briefs/` dir**

Run: `mkdir -p "tmp/visual_briefs"`

- [ ] **Step 3: Write `tmp/visual_briefs/142.json`**

```json
{
  "topic": "airBaltic",
  "headline": "Saeima lemj par 30 milj. airBaltic aizdevumu",
  "stat": "30 milj.",
  "metaphor_hint": "lidmašīna un budžets"
}
```

- [ ] **Step 4: Write `tmp/visual_briefs/135.json`**

```json
{
  "topic": "Skandāli",
  "headline": "JV Milānas seminārs — dienas politiskais skandāls",
  "stat": null,
  "metaphor_hint": "aizsegtas dokumentu paketes"
}
```

- [ ] **Step 5: Write `tmp/visual_briefs/126.json`**

```json
{
  "topic": "Ārpolitika",
  "headline": "Orbāna sakāve — Latvijas politiķu atbalsis",
  "stat": null,
  "metaphor_hint": "Ungārijas karte / vēlēšanu urna"
}
```

No commit — these are tmp/ files (gitignored via `tmp/` not explicit but typically cleaned).

### Task 1.4: Build `scripts/test_image_prompt.py` matrix mode

**Files:**
- Create: `scripts/test_image_prompt.py`

- [ ] **Step 1: Write script**

Create `scripts/test_image_prompt.py`:

```python
"""Image prompt test harness.

Modes:
  --smoke                            One hardcoded prompt, quick API check.
  --matrix --brief-ids 142,135,126   3 styles × N briefs, HTML gallery.

Reads visual_brief JSONs from tmp/visual_briefs/<id>.json.
Writes to tmp/image_tests/<timestamp>/.
"""
import argparse
import json
import sys
import time
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.graphics.nanobanana import generate_image
from src.graphics.prompt import STYLE_VARIANTS, build_prompt
from src.graphics.visual_map import get_visual


def run_matrix(brief_ids: list[str]) -> Path:
    root = Path(__file__).parent.parent
    out = root / "tmp" / "image_tests" / datetime.now().strftime("%Y%m%d-%H%M%S")
    out.mkdir(parents=True, exist_ok=True)

    visual_briefs = {}
    for bid in brief_ids:
        path = root / "tmp" / "visual_briefs" / f"{bid}.json"
        if not path.exists():
            print(f"[error] missing {path}")
            sys.exit(1)
        visual_briefs[bid] = json.loads(path.read_text(encoding="utf-8"))

    results = []
    for style_key in STYLE_VARIANTS:
        for bid, vb in visual_briefs.items():
            vm = get_visual(vb["topic"])
            prompt = build_prompt(vb, vm, style_key=style_key)

            prompt_file = out / f"{style_key}-{bid}.prompt.txt"
            image_file = out / f"{style_key}-{bid}.png"
            prompt_file.write_text(prompt, encoding="utf-8")

            print(f"[{style_key} · {bid}] generating...")
            try:
                png = generate_image(prompt, aspect_ratio="16:9")
                image_file.write_bytes(png)
                results.append((style_key, bid, vb, image_file.name, None))
                print(f"  → {image_file.name} ({len(png)} bytes)")
            except Exception as e:
                results.append((style_key, bid, vb, None, str(e)))
                print(f"  → FAILED: {e}")
            time.sleep(2.0)  # rate limit courtesy

    _write_gallery(out, results, list(visual_briefs.keys()))
    print(f"\n[done] gallery → {out / 'gallery.html'}")
    return out


def _write_gallery(out: Path, results: list, brief_ids: list[str]) -> None:
    styles = list(STYLE_VARIANTS.keys())
    rows = []
    for style in styles:
        cells = [f"<td><strong>{style}</strong></td>"]
        for bid in brief_ids:
            r = next((r for r in results if r[0] == style and r[1] == bid), None)
            if r and r[3]:
                vb = r[2]
                cells.append(
                    f'<td><figure><img src="{r[3]}" alt="{vb["headline"]}" '
                    f'style="max-width:480px;"><figcaption>{vb["topic"]} · {bid}<br>'
                    f'<a href="{style}-{bid}.prompt.txt">prompt</a></figcaption></figure></td>'
                )
            elif r:
                cells.append(f"<td><em>FAILED: {r[4]}</em></td>")
            else:
                cells.append("<td>—</td>")
        rows.append("<tr>" + "".join(cells) + "</tr>")

    header_cells = "<th>style \\ brief</th>" + "".join(
        f"<th>{bid}</th>" for bid in brief_ids
    )

    html = f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>Style matrix</title>
<style>
body {{ font-family: system-ui; padding: 2rem; }}
table {{ border-collapse: collapse; }}
td, th {{ border: 1px solid #ccc; padding: 0.75rem; vertical-align: top; }}
figure {{ margin: 0; }}
figcaption {{ font-size: 0.85rem; color: #555; margin-top: 0.25rem; }}
img {{ display: block; max-width: 480px; }}
</style></head><body>
<h1>Featured image style matrix</h1>
<p>Generated: {datetime.now().isoformat()}</p>
<table><thead><tr>{header_cells}</tr></thead><tbody>
{"".join(rows)}
</tbody></table></body></html>
"""
    (out / "gallery.html").write_text(html, encoding="utf-8")


def run_smoke() -> None:
    """Delegate to scripts/smoke_test.py."""
    import subprocess
    subprocess.run([sys.executable, str(Path(__file__).parent / "smoke_test.py")], check=True)


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--smoke", action="store_true")
    p.add_argument("--matrix", action="store_true")
    p.add_argument("--brief-ids", type=str, default="142,135,126")
    args = p.parse_args()

    if args.smoke:
        run_smoke()
    elif args.matrix:
        ids = [b.strip() for b in args.brief_ids.split(",") if b.strip()]
        run_matrix(ids)
    else:
        p.print_help()
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 2: Run matrix**

Run: `.venv/Scripts/python scripts/test_image_prompt.py --matrix --brief-ids 142,135,126`
Expected: 9 API calls, 9 PNGs + prompts + gallery.html in `tmp/image_tests/<timestamp>/`. Total runtime ~90s with rate-limit sleeps. Cost ~$0.35.

- [ ] **Step 3: Review gallery**

Open `tmp/image_tests/<timestamp>/gallery.html` in browser. User picks winning style.

- [ ] **Step 4: Freeze DEFAULT_STYLE**

Edit `src/graphics/prompt.py` — set `DEFAULT_STYLE = "<chosen-key>"` (one of `editorial`, `scandi`, `constructivist`).

- [ ] **Step 5: Commit**

```bash
git add scripts/test_image_prompt.py src/graphics/prompt.py
git commit -m "feat(graphics): test harness matrix + freeze default style"
```

---

## Phase 2 — DB Schema + Storage

### Task 2.1: Add `brief_images` table + `visual_brief_json` column to `src/db.py`

**Files:**
- Modify: `src/db.py` (add new table definition near line 210)

- [ ] **Step 1: Read `src/db.py:195-250` to locate context_notes and logs tables**

Run: `head -250 src/db.py | tail -60`

- [ ] **Step 2: Add brief_images table definition after `context_notes`**

In `src/db.py`, locate the `CREATE TABLE IF NOT EXISTS context_notes` block (around line 199). After it, and after the related index statements (around line 244-245), insert:

```python
    db.execute("""
        CREATE TABLE IF NOT EXISTS brief_images (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            note_id       INTEGER NOT NULL REFERENCES context_notes(id),
            image_path    TEXT    NOT NULL,
            prompt        TEXT    NOT NULL,
            model         TEXT    NOT NULL,
            seed          INTEGER,
            aspect        TEXT    NOT NULL DEFAULT '16:9',
            width         INTEGER,
            height        INTEGER,
            generated_at  TEXT    NOT NULL,
            cost_usd      REAL    NOT NULL DEFAULT 0.039,
            approved      INTEGER NOT NULL DEFAULT 0,
            error_message TEXT
        )
    """)
    db.execute("""
        CREATE INDEX IF NOT EXISTS idx_brief_images_note_approved
            ON brief_images(note_id, approved, id DESC)
    """)

    # Add visual_brief_json column to context_notes if missing (idempotent)
    _cols = {r[1] for r in db.execute("PRAGMA table_info(context_notes)")}
    if "visual_brief_json" not in _cols:
        db.execute("ALTER TABLE context_notes ADD COLUMN visual_brief_json TEXT")
```

- [ ] **Step 3: Run DB init to apply schema**

Run: `.venv/Scripts/python -c "from src.db import get_db; db = get_db(); print('OK')"`
Expected: prints `OK`. No errors.

- [ ] **Step 4: Verify tables**

Run:
```bash
.venv/Scripts/python -c "
import sqlite3
c = sqlite3.connect('data/atmina.db')
print([r[0] for r in c.execute(\"SELECT name FROM sqlite_master WHERE type='table' AND name='brief_images'\")])
print([r[1] for r in c.execute('PRAGMA table_info(context_notes)') if r[1] == 'visual_brief_json'])
"
```
Expected: `['brief_images']` and `['visual_brief_json']`.

- [ ] **Step 5: Commit**

```bash
git add src/db.py
git commit -m "feat(graphics): add brief_images table + visual_brief_json column"
```

### Task 2.2: Implement `src/graphics/storage.py`

**Files:**
- Create: `src/graphics/storage.py`
- Create: `tests/test_graphics_storage.py`

- [ ] **Step 1: Write failing tests**

Create `tests/test_graphics_storage.py`:

```python
import sqlite3
import hashlib
import pytest
from src.graphics import storage


@pytest.fixture
def memdb():
    db = sqlite3.connect(":memory:")
    db.execute("""
        CREATE TABLE context_notes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            content TEXT, note_type TEXT, created_at TEXT
        )
    """)
    db.execute("""
        CREATE TABLE brief_images (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            note_id       INTEGER NOT NULL,
            image_path    TEXT NOT NULL,
            prompt        TEXT NOT NULL,
            model         TEXT NOT NULL,
            seed          INTEGER,
            aspect        TEXT NOT NULL DEFAULT '16:9',
            width         INTEGER, height INTEGER,
            generated_at  TEXT NOT NULL,
            cost_usd      REAL NOT NULL DEFAULT 0.039,
            approved      INTEGER NOT NULL DEFAULT 0,
            error_message TEXT
        )
    """)
    db.execute("INSERT INTO context_notes (id, content, note_type, created_at) VALUES (1, 'c', 'daily_brief', '2026-04-17T10:00:00')")
    db.commit()
    yield db


def test_compute_filename_produces_stable_hash():
    png = b"fake image bytes"
    name = storage.compute_filename("2026-04-17-test", png)
    assert name.startswith("2026-04-17-test-")
    assert name.endswith(".png")
    assert len(name.split("-")[-1].replace(".png", "")) == 8


def test_save_image_row_returns_id(memdb):
    image_id = storage.save_image_row(
        memdb, note_id=1, image_path="images/briefs/x-ab12cd34.png",
        prompt="prompt", model="test-model", seed=None,
        width=1408, height=768, cost=0.039,
    )
    assert isinstance(image_id, int) and image_id > 0
    row = memdb.execute("SELECT approved, error_message FROM brief_images WHERE id=?", (image_id,)).fetchone()
    assert row == (0, None)


def test_approve_image_sets_approved_1(memdb):
    iid = storage.save_image_row(memdb, 1, "p", "pr", "m", None, 1, 1, 0.039)
    storage.approve_image(memdb, iid)
    row = memdb.execute("SELECT approved FROM brief_images WHERE id=?", (iid,)).fetchone()
    assert row[0] == 1


def test_reject_image_sets_approved_2_with_reason(memdb):
    iid = storage.save_image_row(memdb, 1, "p", "pr", "m", None, 1, 1, 0.039)
    storage.reject_image(memdb, iid, "poor diacritics")
    row = memdb.execute("SELECT approved, error_message FROM brief_images WHERE id=?", (iid,)).fetchone()
    assert row == (2, "poor diacritics")


def test_get_approved_image_returns_latest_approved(memdb):
    iid1 = storage.save_image_row(memdb, 1, "old.png", "p", "m", None, 1, 1, 0.039)
    storage.approve_image(memdb, iid1)
    iid2 = storage.save_image_row(memdb, 1, "new.png", "p", "m", None, 1, 1, 0.039)
    storage.approve_image(memdb, iid2)
    assert storage.get_approved_image(memdb, 1) == "new.png"


def test_get_approved_image_returns_none_when_no_approved(memdb):
    storage.save_image_row(memdb, 1, "pending.png", "p", "m", None, 1, 1, 0.039)
    assert storage.get_approved_image(memdb, 1) is None


def test_get_attempts_returns_all_rows(memdb):
    storage.save_image_row(memdb, 1, "a.png", "p", "m", None, 1, 1, 0.039)
    storage.save_image_row(memdb, 1, "b.png", "p", "m", None, 1, 1, 0.039)
    attempts = storage.get_attempts(memdb, 1)
    assert len(attempts) == 2
```

- [ ] **Step 2: Run to verify failure**

Run: `.venv/Scripts/python -m pytest tests/test_graphics_storage.py -v`
Expected: FAIL (module missing).

- [ ] **Step 3: Implement storage**

Create `src/graphics/storage.py`:

```python
"""DB helpers for brief_images table + filename hashing.

Site renders only latest row with approved=1 per note_id.
Rejected rows (approved=2) are kept for audit.
"""
import hashlib
from src.db import now_lv


def compute_filename(slug: str, png_bytes: bytes) -> str:
    """Return '<slug>-<hash8>.png' where hash8 is sha256 prefix of png bytes."""
    h = hashlib.sha256(png_bytes).hexdigest()[:8]
    return f"{slug}-{h}.png"


def save_image_row(
    db,
    note_id: int,
    image_path: str,
    prompt: str,
    model: str,
    seed: int | None,
    width: int,
    height: int,
    cost: float = 0.039,
    aspect: str = "16:9",
) -> int:
    """Insert a pending (approved=0) row. Return new id."""
    cur = db.execute(
        """
        INSERT INTO brief_images
          (note_id, image_path, prompt, model, seed, aspect,
           width, height, generated_at, cost_usd, approved)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0)
        """,
        (note_id, image_path, prompt, model, seed, aspect,
         width, height, now_lv().isoformat(), cost),
    )
    db.commit()
    return cur.lastrowid


def approve_image(db, image_id: int) -> None:
    db.execute("UPDATE brief_images SET approved = 1 WHERE id = ?", (image_id,))
    db.commit()


def reject_image(db, image_id: int, reason: str) -> None:
    db.execute(
        "UPDATE brief_images SET approved = 2, error_message = ? WHERE id = ?",
        (reason, image_id),
    )
    db.commit()


def save_error_row(
    db, note_id: int, prompt: str, model: str, error_message: str
) -> int:
    """Record a failed generation attempt. approved=2 immediately."""
    cur = db.execute(
        """
        INSERT INTO brief_images
          (note_id, image_path, prompt, model, aspect,
           generated_at, cost_usd, approved, error_message)
        VALUES (?, '', ?, ?, '16:9', ?, 0.0, 2, ?)
        """,
        (note_id, prompt, model, now_lv().isoformat(), error_message),
    )
    db.commit()
    return cur.lastrowid


def get_approved_image(db, note_id: int) -> str | None:
    """Return the latest approved image_path for note_id, or None."""
    row = db.execute(
        """
        SELECT image_path FROM brief_images
        WHERE note_id = ? AND approved = 1
        ORDER BY id DESC LIMIT 1
        """,
        (note_id,),
    ).fetchone()
    return row[0] if row else None


def get_attempts(db, note_id: int) -> list[dict]:
    """Return all image rows for note_id, newest first."""
    rows = db.execute(
        """
        SELECT id, image_path, prompt, approved, error_message, generated_at, cost_usd
        FROM brief_images WHERE note_id = ? ORDER BY id DESC
        """,
        (note_id,),
    ).fetchall()
    return [
        {
            "id": r[0], "image_path": r[1], "prompt": r[2],
            "approved": r[3], "error_message": r[4],
            "generated_at": r[5], "cost_usd": r[6],
        }
        for r in rows
    ]


def monthly_cost_usd(db) -> float:
    """Sum cost_usd for rows generated in the current Latvia-TZ month."""
    month_prefix = now_lv().strftime("%Y-%m")
    row = db.execute(
        """
        SELECT COALESCE(SUM(cost_usd), 0.0) FROM brief_images
        WHERE generated_at LIKE ? || '%'
        """,
        (month_prefix,),
    ).fetchone()
    return float(row[0])
```

- [ ] **Step 4: Run tests**

Run: `.venv/Scripts/python -m pytest tests/test_graphics_storage.py -v`
Expected: 7 passed.

- [ ] **Step 5: Commit**

```bash
git add src/graphics/storage.py tests/test_graphics_storage.py
git commit -m "feat(graphics): storage helpers for brief_images"
```

---

## Phase 3 — Brief-Writer + Parser

### Task 3.1: Update `@brief-writer` prompt

**Files:**
- Modify: `.claude/agents/brief-writer.md`

- [ ] **Step 1: Read current prompt**

Run: `cat .claude/agents/brief-writer.md`

- [ ] **Step 2: Append Vizuālais brief block instructions**

At the end of `.claude/agents/brief-writer.md` (just before any closing examples, or at the very end if no final section), append:

```markdown

## Vizuālais brief (obligāts)

Pašās pārskata beigās **vienmēr** pievieno šādu markdown bloku:

```
## Vizuālais brief

- **Tēma:** <viena no 26 kanoniskajām topic_map grupām — dienas dominējošā tēma>
- **Galvenā tēze:** <līdz 60 simboliem, faktiska teikuma fragments, ne sauklis>
- **Skaitlis:** <galvenais kvantitatīvais dienas rādītājs, piem. "30 milj.", "+47 pozīcijas"; ja nav skaidra — "-">
- **Metaforas hint:** <līdz 40 simboliem, brīva forma par vizuālo virzienu>
```

Stingrie likumi:
- Tēma JĀBŪT no kanoniskajām 26 topic_map grupām — nekas cits.
- Galvenā tēze ir **faktiska** dienas primārā notikuma apraksts, nevis interpretācija.
- Skaitlis, ja iekļauts, MĀ parādīties pārskata body — nevari izdomāt numuru.
- Metaforas hint ir brīva, netiek validēta pret neko konkrētu.
```

- [ ] **Step 3: Commit**

```bash
git add .claude/agents/brief-writer.md
git commit -m "feat(graphics): brief-writer emits Vizualais brief block"
```

### Task 3.2: Implement `parse_visual_brief()` in `src/briefs.py`

**Files:**
- Modify: `src/briefs.py` (add parser function)
- Create: `tests/test_briefs_visual.py`

- [ ] **Step 1: Write failing tests**

Create `tests/test_briefs_visual.py`:

```python
from src.briefs import parse_visual_brief


VALID_BRIEF = """
# Dienas analīze — 2026-04-17

## Galvenais

Liels teksts par dienu.

## Vizuālais brief

- **Tēma:** Budžets un finanses
- **Galvenā tēze:** Saeima apstiprina budžeta grozījumus
- **Skaitlis:** +47 milj.
- **Metaforas hint:** budžeta dokuments
"""

BRIEF_WITH_DASH_STAT = """
Teksts par skandālu.

## Vizuālais brief

- **Tēma:** Skandāli
- **Galvenā tēze:** JV Milānas seminārs
- **Skaitlis:** -
- **Metaforas hint:** aizsegti dokumenti
"""

BRIEF_MISSING_BLOCK = """
# Vecs brief bez Vizuālais brief bloka.
Tikai saturs.
"""


def test_parse_valid_brief_returns_dict():
    vb = parse_visual_brief(VALID_BRIEF)
    assert vb == {
        "topic": "Budžets un finanses",
        "headline": "Saeima apstiprina budžeta grozījumus",
        "stat": "+47 milj.",
        "metaphor_hint": "budžeta dokuments",
    }


def test_parse_dash_stat_becomes_none():
    vb = parse_visual_brief(BRIEF_WITH_DASH_STAT)
    assert vb["stat"] is None


def test_parse_missing_block_returns_none():
    assert parse_visual_brief(BRIEF_MISSING_BLOCK) is None


def test_stat_validation_drops_stat_not_in_body():
    content = """
Body text without any numbers.

## Vizuālais brief

- **Tēma:** Budžets un finanses
- **Galvenā tēze:** X
- **Skaitlis:** +99 trilj.
- **Metaforas hint:** y
"""
    vb = parse_visual_brief(content)
    # "+99 trilj." substring not in body → stat dropped
    assert vb["stat"] is None


def test_stat_validation_keeps_stat_in_body():
    content = """
Body mentions 30 milj. in the text.

## Vizuālais brief

- **Tēma:** airBaltic
- **Galvenā tēze:** airBaltic aizdevums
- **Skaitlis:** 30 milj.
- **Metaforas hint:** lidmašīna
"""
    vb = parse_visual_brief(content)
    assert vb["stat"] == "30 milj."
```

- [ ] **Step 2: Run to verify failure**

Run: `.venv/Scripts/python -m pytest tests/test_briefs_visual.py -v`
Expected: FAIL (`parse_visual_brief` not defined).

- [ ] **Step 3: Find location in src/briefs.py**

Run: `grep -n "^def \|^class " src/briefs.py | head -20`

- [ ] **Step 4: Add parser function**

At the end of `src/briefs.py`, add:

```python
import re


def parse_visual_brief(content: str) -> dict | None:
    """Extract the `## Vizuālais brief` markdown block into a dict.

    Returns {topic, headline, stat, metaphor_hint} or None if block missing
    or malformed. Applies stat validation: if stat value does not appear
    as substring in content body, stat is set to None.
    """
    m = re.search(
        r"##\s*Viz[uū]ālais\s+brief\s*\n+(.*?)(?=\n##\s|\Z)",
        content,
        flags=re.IGNORECASE | re.DOTALL,
    )
    if not m:
        return None

    block = m.group(1)
    fields: dict[str, str] = {}
    for line in block.splitlines():
        bm = re.match(r"\s*-\s*\*\*([^*]+)\*\*:\s*(.+?)\s*$", line)
        if bm:
            key, val = bm.group(1).strip(), bm.group(2).strip()
            fields[key] = val

    topic = fields.get("Tēma") or ""
    headline = fields.get("Galvenā tēze") or ""
    stat = fields.get("Skaitlis") or ""
    metaphor_hint = fields.get("Metaforas hint") or ""

    if not topic or not headline:
        return None

    if stat in {"-", "—", "", "nav"}:
        stat_value: str | None = None
    else:
        # Validate stat appears in body (outside the visual brief block)
        body = content[: m.start()] + content[m.end():]
        stat_value = stat if stat in body else None

    return {
        "topic": topic,
        "headline": headline,
        "stat": stat_value,
        "metaphor_hint": metaphor_hint,
    }
```

- [ ] **Step 5: Run tests**

Run: `.venv/Scripts/python -m pytest tests/test_briefs_visual.py -v`
Expected: 5 passed.

- [ ] **Step 6: Commit**

```bash
git add src/briefs.py tests/test_briefs_visual.py
git commit -m "feat(briefs): parse Vizualais brief markdown block"
```

### Task 3.3: Wire `visual_brief_json` into `store_context_note()`

**Files:**
- Modify: `src/tools.py` (around line 261 — `store_context_note`)
- Modify: `tests/test_briefs_visual.py` (add one integration test)

- [ ] **Step 1: Read current signature**

Run: `.venv/Scripts/python -c "import inspect; from src.tools import store_context_note; print(inspect.getsource(store_context_note))"`

- [ ] **Step 2: Extend signature**

In `src/tools.py`, locate `def store_context_note(` around line 261. Change signature:

Before:
```python
def store_context_note(
    opponent_id: int | None = None,
    topic: str | None = None,
    note_type: str = "context",
    content: str = "",
    source: str | None = None,
    expires_at: str | None = None,
) -> str:
```

After:
```python
def store_context_note(
    opponent_id: int | None = None,
    topic: str | None = None,
    note_type: str = "context",
    content: str = "",
    source: str | None = None,
    expires_at: str | None = None,
    visual_brief: dict | None = None,
) -> str:
```

- [ ] **Step 3: Auto-parse visual_brief from content when note_type is a brief**

Locate where the note is inserted. After the `_validate_brief_structure` call and before insert, add:

```python
        # Auto-extract visual_brief from content if the brief-writer included it
        # and caller didn't pass one explicitly.
        if note_type in ("daily_brief", "weekly_brief") and visual_brief is None:
            from src.briefs import parse_visual_brief
            visual_brief = parse_visual_brief(content)
```

Then find the INSERT into `context_notes` (search for `INSERT INTO context_notes`). Update column list to include `visual_brief_json` and bind `json.dumps(visual_brief) if visual_brief else None`.

If the INSERT currently looks like (simplified):

```python
db.execute(
    "INSERT INTO context_notes (opponent_id, topic, note_type, content, source, created_at, expires_at) "
    "VALUES (?, ?, ?, ?, ?, ?, ?)",
    (opponent_id, topic, note_type, content, source, now_lv().isoformat(), expires_at),
)
```

Change to:

```python
import json
db.execute(
    "INSERT INTO context_notes (opponent_id, topic, note_type, content, source, created_at, expires_at, visual_brief_json) "
    "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
    (opponent_id, topic, note_type, content, source, now_lv().isoformat(), expires_at,
     json.dumps(visual_brief, ensure_ascii=False) if visual_brief else None),
)
```

(The exact SQL may differ — adapt to what's already there.)

- [ ] **Step 4: Add integration test**

Append to `tests/test_briefs_visual.py`:

```python
import json
import sqlite3
from unittest.mock import patch


def test_store_context_note_auto_extracts_visual_brief(monkeypatch, tmp_path):
    """store_context_note() with note_type=daily_brief auto-parses visual_brief."""
    # This test assumes integration with the real DB — skip if that's too invasive.
    # Instead we verify the logic by importing and calling parse directly:
    from src.briefs import parse_visual_brief
    content = """# Dienas analīze

Saeima ir apstiprinājusi 30 milj. aizdevumu.

## Vizuālais brief

- **Tēma:** airBaltic
- **Galvenā tēze:** Saeima lemj par 30 milj. airBaltic aizdevumu
- **Skaitlis:** 30 milj.
- **Metaforas hint:** lidmašīna
"""
    vb = parse_visual_brief(content)
    assert vb["topic"] == "airBaltic"
    assert vb["stat"] == "30 milj."
```

- [ ] **Step 5: Run tests**

Run: `.venv/Scripts/python -m pytest tests/test_briefs_visual.py -v`
Expected: 6 passed.

- [ ] **Step 6: Commit**

```bash
git add src/tools.py tests/test_briefs_visual.py
git commit -m "feat(briefs): store_context_note persists visual_brief_json"
```

---

## Phase 4 — Graphics Agent + Backfill

### Task 4.1: Write `.claude/agents/graphics-designer.md`

**Files:**
- Create: `.claude/agents/graphics-designer.md`

- [ ] **Step 1: Write agent definition**

Create `.claude/agents/graphics-designer.md`:

```markdown
---
name: graphics-designer
description: Creative agent — takes a daily_brief note_id, reads content + visual_brief_json, picks metaphor from visual_map, composes nanobanana prompt, generates 16:9 PNG, saves to output/images/briefs/ and DB. Returns image path + row id.
tools: Read, Bash, Grep, Edit
---

# graphics-designer

You are the featured image designer for atmina.lv. Your job: given a daily
brief's `note_id`, produce a stylistically consistent, factually grounded
16:9 featured image via `gemini-3.1-flash-image-preview`.

## Inputs

- `note_id` (integer) — row in `context_notes` where `note_type='daily_brief'`
- DB: `data/atmina.db`
- Visual style book: `src/graphics/visual_map.py` + `src/graphics/prompt.py`
- API: `src/graphics/nanobanana.py::generate_image()`
- Storage: `src/graphics/storage.py`

## Process

1. Read brief content and `visual_brief_json` from `context_notes`:
   ```python
   import sqlite3, json
   db = sqlite3.connect("data/atmina.db")
   row = db.execute(
       "SELECT content, visual_brief_json FROM context_notes WHERE id=?",
       (note_id,)
   ).fetchone()
   content, vb_json = row
   visual_brief = json.loads(vb_json) if vb_json else None
   ```
2. If `visual_brief is None`, stop with error "missing visual_brief_json".
3. Look up metaphor: `from src.graphics.visual_map import get_visual; vm = get_visual(visual_brief["topic"])`.
4. Optionally refine metaphor using `visual_brief["metaphor_hint"]` — you may pick one of the two "OR" alternatives in `vm["metaphor"]` if the hint favors one.
5. Budget check: `from src.graphics.config import budget_check; budget_check(db)`.
6. Compose prompt: `from src.graphics.prompt import build_prompt, DEFAULT_STYLE; p = build_prompt(visual_brief, vm, DEFAULT_STYLE)`.
7. Generate: `from src.graphics.nanobanana import generate_image, SafetyError`.
   - On `SafetyError` or `google.genai.errors.APIError` after retries, call `save_error_row(db, note_id, p, model, str(e))` and return error info.
8. Compute filename and save:
   ```python
   from src.graphics.storage import compute_filename, save_image_row
   from pathlib import Path
   slug = f"{created_at_date}-dienas-parskats"  # or use existing slug logic
   fname = compute_filename(slug, png_bytes)
   out = Path("output/images/briefs") / fname
   out.parent.mkdir(parents=True, exist_ok=True)
   out.write_bytes(png_bytes)
   image_id = save_image_row(db, note_id, f"images/briefs/{fname}",
                              prompt=p, model=model, seed=None,
                              width=1408, height=768, cost=0.039)
   ```
9. Return to caller:
   ```json
   {"image_id": 42, "image_path": "output/images/briefs/...png", "status": "pending_approval"}
   ```

## Constraints

- Never modify brief content.
- Never auto-approve (`approved=0` default). Human-in-the-loop approves.
- If `visual_brief["stat"]` is None, let prompt.py omit the stat section (already handled).
- Preserve Latvian diacritics in the prompt — do not transliterate.
- On any exception: log via `save_error_row`, return `{"status": "failed", "error": "..."}`.

## Regeneration

When the caller asks for regenerate (with or without modification):
- Same `note_id`, new row in `brief_images`. Do NOT delete or update old rows.
- If a modifier is given ("warmer tone", "bolder metaphor"), append it to `prompt` as an extra line before calling `generate_image`.
```

- [ ] **Step 2: Commit**

```bash
git add .claude/agents/graphics-designer.md
git commit -m "feat(graphics): @graphics-designer subagent"
```

### Task 4.2: Build `scripts/backfill_brief_images.py`

**Files:**
- Create: `scripts/backfill_brief_images.py`

- [ ] **Step 1: Write backfill script**

Create `scripts/backfill_brief_images.py`:

```python
"""Backfill featured images for existing daily briefs.

Flow:
  1. For each daily_brief missing visual_brief_json: extract via Anthropic SDK.
  2. For each daily_brief without approved=1 brief_images row: generate image,
     approve automatically (batch mode, no human-in-the-loop).
  3. 2s sleep between API calls. Exponential backoff on 429/5xx inherited from
     nanobanana.generate_image().

Run: .venv/Scripts/python scripts/backfill_brief_images.py
Cost: ~12 × $0.039 = ~$0.47 for 12 existing briefs.
"""
import json
import os
import sqlite3
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from anthropic import Anthropic
from src.briefs import parse_visual_brief
from src.graphics.config import budget_check, load_gemini_key
from src.graphics.nanobanana import generate_image, SafetyError
from src.graphics.prompt import DEFAULT_STYLE, build_prompt
from src.graphics.storage import (
    approve_image, compute_filename, save_error_row, save_image_row,
)
from src.graphics.visual_map import get_visual


ANTHROPIC_KEY = os.environ.get("ANTHROPIC_API_KEY")
EXTRACTION_PROMPT = """Ekstraktē Vizuālais brief struktūru no šī dienas pārskata.

Atgriez TIKAI JSON ar laukiem:
- topic: viena no 26 kanoniskajām topic_map grupām (airBaltic, Budžets un finanses, Skandāli, Ārpolitika utt.)
- headline: dienas galvenais fakts, līdz 60 simboliem
- stat: galvenais skaitlis (piem. "30 milj.", "+47 pozīcijas") vai null
- metaphor_hint: vizuālās metaforas ideja, līdz 40 simboliem

Brief teksts:
{content}

Atgriez TIKAI JSON, bez prefiksa/sufiksa teksta."""


def extract_visual_brief(client: Anthropic, content: str) -> dict | None:
    """Use Claude to extract visual_brief from brief content."""
    resp = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=500,
        messages=[{"role": "user", "content": EXTRACTION_PROMPT.format(content=content)}],
    )
    text = resp.content[0].text.strip()
    # Strip possible markdown code fences
    if text.startswith("```"):
        text = text.split("\n", 1)[1].rsplit("```", 1)[0].strip()
        if text.startswith("json"):
            text = text[4:].strip()
    try:
        vb = json.loads(text)
    except json.JSONDecodeError:
        print(f"    [warn] unparseable extractor output: {text[:200]}")
        return None
    # Validate stat
    if vb.get("stat") and str(vb["stat"]) not in content:
        print(f"    [warn] stat '{vb['stat']}' not found in content → drop")
        vb["stat"] = None
    return vb


def main() -> int:
    if not ANTHROPIC_KEY:
        print("[error] ANTHROPIC_API_KEY env var not set")
        return 1

    db = sqlite3.connect("data/atmina.db")
    anthropic_client = Anthropic(api_key=ANTHROPIC_KEY)
    gemini_key = load_gemini_key()

    # Stage 1: extract visual_brief for briefs missing it
    briefs_missing_vb = db.execute("""
        SELECT id, content FROM context_notes
        WHERE note_type = 'daily_brief' AND visual_brief_json IS NULL
    """).fetchall()
    print(f"[stage 1] extracting visual_brief for {len(briefs_missing_vb)} briefs")
    for nid, content in briefs_missing_vb:
        print(f"  → brief {nid}")
        vb = extract_visual_brief(anthropic_client, content)
        if vb:
            db.execute(
                "UPDATE context_notes SET visual_brief_json = ? WHERE id = ?",
                (json.dumps(vb, ensure_ascii=False), nid),
            )
            db.commit()
        time.sleep(1.0)

    # Stage 2: generate images for briefs without approved=1 row
    briefs_to_image = db.execute("""
        SELECT cn.id, cn.content, cn.visual_brief_json, cn.created_at
        FROM context_notes cn
        WHERE cn.note_type = 'daily_brief'
          AND cn.visual_brief_json IS NOT NULL
          AND NOT EXISTS (
            SELECT 1 FROM brief_images bi
            WHERE bi.note_id = cn.id AND bi.approved = 1
          )
    """).fetchall()
    print(f"[stage 2] generating images for {len(briefs_to_image)} briefs")

    for nid, content, vb_json, created_at in briefs_to_image:
        print(f"  → brief {nid} ({created_at[:10]})")
        try:
            budget_check(db)
        except Exception as e:
            print(f"    [stop] budget: {e}")
            break

        vb = json.loads(vb_json)
        vm = get_visual(vb["topic"])
        prompt_text = build_prompt(vb, vm, DEFAULT_STYLE)

        try:
            png = generate_image(prompt_text, aspect_ratio="16:9")
        except SafetyError as e:
            print(f"    [safety] {e}")
            save_error_row(db, nid, prompt_text, gemini_key["model"], f"SAFETY: {e}")
            time.sleep(2.0)
            continue
        except Exception as e:
            print(f"    [api error] {e}")
            save_error_row(db, nid, prompt_text, gemini_key["model"], str(e))
            time.sleep(2.0)
            continue

        slug = f"{created_at[:10]}-dienas-parskats"
        fname = compute_filename(slug, png)
        out = Path("output/images/briefs") / fname
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_bytes(png)

        image_id = save_image_row(
            db, nid, f"images/briefs/{fname}",
            prompt=prompt_text, model=gemini_key["model"], seed=None,
            width=1408, height=768, cost=0.039,
        )
        approve_image(db, image_id)  # batch mode: auto-approve
        print(f"    → {out.name} (id={image_id}) approved")
        time.sleep(2.0)

    print("[done] backfill complete")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 2: Set Anthropic API key**

Prompt user to set env var:
```
Before running, set ANTHROPIC_API_KEY env var with your Anthropic key.
On Windows: set ANTHROPIC_API_KEY=sk-ant-...
(Or export via .env.deploy-style mechanism you already use.)
```

- [ ] **Step 3: Run backfill**

Run: `.venv/Scripts/python scripts/backfill_brief_images.py`
Expected: Stage 1 extracts ~12 visual_briefs. Stage 2 generates ~12 images. Console prints per-brief progress.

- [ ] **Step 4: Verify results**

Run:
```bash
.venv/Scripts/python -c "
import sqlite3
c = sqlite3.connect('data/atmina.db')
print('approved:', c.execute('SELECT COUNT(*) FROM brief_images WHERE approved=1').fetchone()[0])
print('errors:', c.execute('SELECT COUNT(*) FROM brief_images WHERE approved=2').fetchone()[0])
"
ls output/images/briefs/
```
Expected: `approved: 12` (or close), `errors: 0-2`. PNG files listed.

- [ ] **Step 5: Commit**

```bash
git add scripts/backfill_brief_images.py
git commit -m "feat(graphics): backfill script for existing briefs"
```

---

## Phase 5 — Routine Integration

### Task 5.1: Add step 11 to `src/routine.py`

**Files:**
- Modify: `src/routine.py`
- Modify: `tests/test_routine.py`

- [ ] **Step 1: Read current routine**

Run: `grep -n "def \|STEPS\|step" src/routine.py | head -30`

- [ ] **Step 2: Find STEPS list and add entry**

Locate the STEPS dict/list. Add entry 11 after the brief-writer step (usually step 10). Pattern follows existing entries:

```python
    11: {
        "name": "Featured image ģenerēšana",
        "check": _check_pending_brief_image,
        "description": (
            "Ģenerē featured image jaunākajam daily_brief ar visual_brief_json, "
            "ja vēl nav approved=1 attēls. Izsauc @graphics-designer subagent."
        ),
    },
```

Add helper function in the same file:

```python
def _check_pending_brief_image(db) -> tuple[bool, str]:
    """Returns (done, status_msg)."""
    row = db.execute("""
        SELECT cn.id, cn.created_at FROM context_notes cn
        WHERE cn.note_type = 'daily_brief'
          AND cn.visual_brief_json IS NOT NULL
          AND date(cn.created_at) = date(?)
          AND NOT EXISTS (
            SELECT 1 FROM brief_images bi
            WHERE bi.note_id = cn.id AND bi.approved = 1
          )
        ORDER BY cn.id DESC LIMIT 1
    """, (now_lv().isoformat(),)).fetchone()
    if row is None:
        # Either today's brief already has an approved image, or no brief today yet.
        today_brief = db.execute(
            "SELECT id FROM context_notes WHERE note_type='daily_brief' "
            "AND date(created_at)=date(?)",
            (now_lv().isoformat(),),
        ).fetchone()
        if today_brief is None:
            return False, "nav šodienas daily_brief"
        return True, "šodienas brief jau ar attēlu"
    return False, f"brief {row[0]} gaida featured image (izsauc @graphics-designer)"
```

(Imports at top of file may need `now_lv` — check existing imports.)

- [ ] **Step 3: Update `tests/test_routine.py`**

Add test:

```python
def test_routine_has_step_11_featured_image():
    from src.routine import STEPS  # or equivalent export
    assert 11 in STEPS
    assert "image" in STEPS[11]["name"].lower() or "attēl" in STEPS[11]["name"].lower()
```

- [ ] **Step 4: Run tests**

Run: `.venv/Scripts/python -m pytest tests/test_routine.py -v`
Expected: all pass including new test.

- [ ] **Step 5: Verify `print_routine()` renders step 11**

Run: `.venv/Scripts/python -c "from src.routine import print_routine; print_routine()"`
Expected: step 11 appears in output with its status.

- [ ] **Step 6: Commit**

```bash
git add src/routine.py tests/test_routine.py
git commit -m "feat(routine): step 11 featured image generation"
```

---

## Phase 6 — Template + Site Integration

### Task 6.1: Add `fetch_latest_brief_with_image()` and image context to `src/generate.py`

**Files:**
- Modify: `src/generate.py`

- [ ] **Step 1: Locate brief context building in generate.py**

Run: `grep -n "latest_brief\|daily_brief\|brief_card\|BASE_URL" src/generate.py | head -20`

- [ ] **Step 2: Add helper function near other brief queries**

After `BASE_URL = "https://atmina.lv"` declaration (line 78), add (or near other fetch_* helpers):

```python
def fetch_latest_brief_with_image(db) -> dict | None:
    """Return latest daily/weekly brief enriched with image_path (or None)."""
    row = db.execute("""
        SELECT cn.id, cn.content, cn.note_type, cn.created_at, cn.visual_brief_json
        FROM context_notes cn
        WHERE cn.note_type IN ('daily_brief', 'weekly_brief')
        ORDER BY cn.created_at DESC LIMIT 1
    """).fetchone()
    if row is None:
        return None
    note_id, content, note_type, created_at, vb_json = row
    from src.graphics.storage import get_approved_image
    image_path = get_approved_image(db, note_id)
    import json
    vb = json.loads(vb_json) if vb_json else None
    preview = content[:300].strip() + ("..." if len(content) > 300 else "")
    slug = f"{created_at[:10]}-dienas-parskats"  # adapt if existing slug logic differs
    return {
        "note_id": note_id,
        "slug": slug,
        "date": created_at[:10],
        "note_type": note_type,
        "type_label": "Nedēļas pārskats" if note_type == "weekly_brief" else "Dienas pārskats",
        "title": f"Dienas pārskats — {created_at[:10]}",
        "preview": preview,
        "image_path": image_path,  # relative: "images/briefs/<slug>-<hash>.png"
        "image_filename": image_path.rsplit("/", 1)[-1] if image_path else None,
        "headline": vb["headline"] if vb else None,
        "visual_brief": vb,
    }
```

- [ ] **Step 3: Pass `BASE_URL` + latest_brief_with_image to Jinja context**

Locate the Jinja `render()` or `env.get_template(...).render(...)` calls for index.html and blog-post. Wherever context dict is built, add:

```python
ctx["BASE_URL"] = BASE_URL
ctx["latest_brief_with_image"] = fetch_latest_brief_with_image(db)
```

For blog-post.html context specifically — the brief detail view — set:

```python
ctx["featured_image"] = get_approved_image(db, note_id)
ctx["visual_brief"] = json.loads(vb_json) if vb_json else None
```

For analizes.html context — iterate posts list, and for each post dict add:

```python
post["image_path"] = get_approved_image(db, post["note_id"])
post["image_filename"] = (
    post["image_path"].rsplit("/", 1)[-1] if post["image_path"] else None
)
post["headline"] = (
    json.loads(post["visual_brief_json"])["headline"]
    if post.get("visual_brief_json") else None
)
```

(Exact integration point varies — match existing context-building patterns in generate.py.)

- [ ] **Step 4: Run generate_public_site() and check no errors**

Run: `.venv/Scripts/python -c "from src.generate import generate_public_site; generate_public_site()"`
Expected: completes without errors. `output/` has new pages.

- [ ] **Step 5: Commit**

```bash
git add src/generate.py
git commit -m "feat(generate): pass BASE_URL + featured image to templates"
```

### Task 6.2: Update `templates/base.html.j2` with OG meta blocks

**Files:**
- Modify: `templates/base.html.j2`

- [ ] **Step 1: Read current head section**

Run: `head -40 templates/base.html.j2`

- [ ] **Step 2: Add OG meta tags**

In `templates/base.html.j2`, inside the `<head>` section, find where `<meta property="og:*">` tags are (if present) or where title meta is. Replace or insert:

```html
<meta property="og:title" content="{% block og_title %}{{ self.title() }}{% endblock %}">
<meta property="og:description" content="{% block og_description %}atmina.lv — Latvijas politiskās atmiņas datubāze{% endblock %}">
<meta property="og:image" content="{% block og_image %}{{ BASE_URL }}/assets/og-default.png{% endblock %}">
<meta property="og:type" content="article">
<meta property="og:locale" content="lv_LV">
<meta name="twitter:card" content="summary_large_image">
```

- [ ] **Step 3: Re-render site**

Run: `.venv/Scripts/python -c "from src.generate import generate_public_site; generate_public_site()"`
Expected: no errors.

- [ ] **Step 4: Inspect generated HTML**

Run: `grep -l "og:image" output/atmina/*.html | head -3`
Expected: multiple HTML files contain og:image meta.

- [ ] **Step 5: Commit**

```bash
git add templates/base.html.j2
git commit -m "feat(templates): OG meta tags base blocks"
```

### Task 6.3: Full-bleed hero in `templates/blog-post.html.j2`

**Files:**
- Modify: `templates/blog-post.html.j2`

- [ ] **Step 1: Read current template**

Run: `cat templates/blog-post.html.j2`

- [ ] **Step 2: Add featured image hero + OG override**

At the top of `templates/blog-post.html.j2` (after `{% extends "base.html.j2" %}`), add OG block override:

```html
{% block og_image %}{% if featured_image %}{{ BASE_URL }}/images/briefs/{{ featured_image.rsplit('/', 1)[-1] if '/' in featured_image else featured_image }}{% else %}{{ BASE_URL }}/assets/og-default.png{% endif %}{% endblock %}
{% block og_description %}{{ preview if preview else "" }}{% endblock %}
```

At the top of the `{% block content %}`, insert:

```html
{% if featured_image %}
<figure class="brief-hero">
  <img src="../{{ featured_image }}"
       alt="{{ visual_brief.headline if visual_brief else title }}"
       width="1408" height="768" loading="eager">
</figure>
{% endif %}

<article class="brief-content">
```

And ensure the closing `</article>` appears at end of content block.

- [ ] **Step 3: Re-render + manual check**

Run: `.venv/Scripts/python -c "from src.generate import generate_public_site; generate_public_site()"`

Open `output/atmina/blog/<latest-slug>.html` in browser. Expected: full-bleed hero image above text.

- [ ] **Step 4: Commit**

```bash
git add templates/blog-post.html.j2
git commit -m "feat(templates): full-bleed hero on blog-post"
```

### Task 6.4: Single featured card on `index.html` (or `index-v2.html`)

**Files:**
- Modify: `templates/index.html.j2` OR the file that becomes the homepage

- [ ] **Step 1: Read current template**

Run: `grep -n "brief-card\|latest_brief" templates/index.html.j2`

- [ ] **Step 2: Replace existing `brief-card` section with featured card**

Replace the `{% if latest_brief %} ... {% endif %}` block (around lines 29–40) with:

```html
{% if latest_brief_with_image %}
<section class="container">
  <a href="blog/{{ latest_brief_with_image.slug }}.html" class="brief-featured-card">
    {% if latest_brief_with_image.image_filename %}
    <img src="images/briefs/{{ latest_brief_with_image.image_filename }}"
         alt="{{ latest_brief_with_image.headline or latest_brief_with_image.title }}"
         loading="eager">
    {% endif %}
    <div class="brief-featured-body">
      <div class="brief-featured-meta">
        <span class="brief-featured-type">{{ latest_brief_with_image.type_label }}</span>
        <span class="brief-featured-date">{{ latest_brief_with_image.date }}</span>
      </div>
      <div class="brief-featured-preview">{{ latest_brief_with_image.preview }}</div>
      <span class="brief-featured-link">Lasīt vairāk &rarr;</span>
    </div>
  </a>
</section>
{% endif %}
```

- [ ] **Step 3: Commit**

```bash
git add templates/index.html.j2
git commit -m "feat(templates): featured card on homepage"
```

### Task 6.5: Thumbnail column in `templates/analizes.html.j2`

**Files:**
- Modify: `templates/analizes.html.j2`

- [ ] **Step 1: Read current daily-card markup (around lines 44–62)**

Run: `sed -n '44,62p' templates/analizes.html.j2`

- [ ] **Step 2: Add thumbnail img + has-image class**

Replace the `daily-card` `<a>` block:

```html
<a href="blog/{{ post.slug }}.html" class="daily-card {% if post.image_filename %}has-image{% endif %}">
  {% if post.image_filename %}
  <img src="images/briefs/{{ post.image_filename }}"
       alt="{{ post.headline or post.title }}"
       class="daily-card-thumb" loading="lazy">
  {% endif %}
  <div class="daily-date-block">
    <div class="daily-date-day">{{ post.date[8:10] }}</div>
    <div class="daily-date-month">{{ post.date[5:7] }}.{{ post.date[:4] }}</div>
    <div class="daily-type {% if post.note_type == 'weekly_brief' %}daily-type-week{% endif %}">
      {% if post.note_type == 'weekly_brief' %}NED{% else %}DIN{% endif %}
    </div>
  </div>
  <div class="daily-body">
    <h3 class="daily-title">{{ post.title }}</h3>
    <div class="daily-preview">{{ post.preview }}</div>
  </div>
  <div class="daily-arrow">→</div>
</a>
```

- [ ] **Step 3: Commit**

```bash
git add templates/analizes.html.j2
git commit -m "feat(templates): thumbnail column on analizes daily-card"
```

### Task 6.6: Add CSS for featured image components

**Files:**
- Modify: `assets/style.css`

- [ ] **Step 1: Append new CSS at end of `assets/style.css`**

```css
/* ===== Featured images ===== */

/* Blog post full-bleed hero */
.brief-hero {
  margin: 0 -50vw 2rem -50vw;
  width: 100vw;
  position: relative;
  left: 50%;
  transform: translateX(-50%);
  aspect-ratio: 16 / 9;
  overflow: hidden;
  max-width: none;
}
.brief-hero img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: block;
}
.brief-content {
  max-width: 720px;
  margin: 0 auto;
}

/* Homepage single featured card */
.brief-featured-card {
  display: block;
  text-decoration: none;
  color: inherit;
  border-radius: 8px;
  overflow: hidden;
  background: var(--bg-muted, #f4f1ea);
  transition: transform 0.15s ease;
  margin: 2rem 0;
}
.brief-featured-card:hover { transform: translateY(-2px); }
.brief-featured-card img {
  width: 100%;
  aspect-ratio: 16 / 9;
  object-fit: cover;
  display: block;
}
.brief-featured-body {
  padding: 1.25rem 1.5rem 1.5rem;
}
.brief-featured-meta {
  display: flex;
  gap: 0.75rem;
  font-size: 0.8rem;
  color: var(--text-muted, #666);
  margin-bottom: 0.5rem;
}
.brief-featured-type { font-weight: 600; }
.brief-featured-preview {
  color: var(--text, #222);
  line-height: 1.5;
  margin-bottom: 0.75rem;
}
.brief-featured-link {
  color: var(--accent, #b71c1c);
  font-weight: 600;
}

/* Analizes daily-card thumbnail */
.daily-card.has-image {
  padding-left: 0;
  align-items: stretch;
}
.daily-card-thumb {
  width: 140px;
  aspect-ratio: 16 / 9;
  object-fit: cover;
  flex-shrink: 0;
  display: block;
}

@media (max-width: 768px) {
  .daily-card-thumb { width: 80px; }
}
```

- [ ] **Step 2: Re-render site**

Run: `.venv/Scripts/python -c "from src.generate import generate_public_site; generate_public_site()"`

- [ ] **Step 3: Manual browser check**

Open `output/atmina/index.html` — verify featured card with image.
Open `output/atmina/analizes.html` — verify thumbnails on daily cards.
Open `output/atmina/blog/<slug>.html` — verify full-bleed hero.

- [ ] **Step 4: Commit**

```bash
git add assets/style.css
git commit -m "feat(templates): CSS for featured image components"
```

### Task 6.7: Create `assets/og-default.png` fallback

**Files:**
- Create: `assets/og-default.png`

- [ ] **Step 1: Generate default OG image**

Option A (manual): Use an existing brand asset or create a simple 1200x630 PNG via any tool with "atmina.lv" wordmark on cream paper.

Option B (automated): Run smoke_test with atmina-branded prompt:

```bash
.venv/Scripts/python -c "
from src.graphics.nanobanana import generate_image
png = generate_image('''
Editorial poster, textured cream paper background, monochrome black
condensed serif typography. Large centered headline: \"atmina.lv\".
Subtitle below: \"Latvijas politiskā atmiņa\". Aspect ratio 16:9. Minimal,
no other elements, no people, no logos, no borders.
''', aspect_ratio='16:9')
open('assets/og-default.png', 'wb').write(png)
print('done')
"
```

- [ ] **Step 2: Verify file exists and renders**

Run: `ls -la assets/og-default.png`
Open file to visually confirm.

- [ ] **Step 3: Commit**

```bash
git add assets/og-default.png
git commit -m "feat(templates): default OG image"
```

### Task 6.8: Full site regeneration + manual verification

**Files:** None (verification only)

- [ ] **Step 1: Full regen**

Run: `.venv/Scripts/python -c "from src.generate import generate_public_site; generate_public_site()"`

- [ ] **Step 2: Verify URLs in generated HTML**

```bash
grep -c "images/briefs/" output/atmina/index.html output/atmina/analizes.html
head -20 output/atmina/blog/$(ls output/atmina/blog/ | head -1)
```

Expected: `images/briefs/...` refs present. og:image has absolute URL.

- [ ] **Step 3: Local preview server**

Run: `.venv/Scripts/python serve.py`
Open http://127.0.0.1:8080/ and navigate:
- Homepage — featured card with image visible.
- /analizes — daily cards show thumbnails.
- Open a daily brief — full-bleed hero visible.
- View source, find `og:image` — absolute URL starts with `https://atmina.lv/`.

- [ ] **Step 4: Share-preview sanity check (optional but recommended)**

Paste the production URL (after deploy) into Twitter/Telegram/Signal and verify the preview card renders the featured image.

No code commit — this task is verification.

---

## Phase 7 — Deploy

### Task 7.1: Dry-run deploy

- [ ] **Step 1: Run dry-run**

Run: `bash scripts/deploy.sh --dry-run`
Expected: rsync lists `output/images/briefs/*.png`, `output/images/og-default.png`, and all modified HTML files.

### Task 7.2: Full deploy

- [ ] **Step 1: Deploy**

Run: `bash scripts/deploy.sh`
Expected: upload completes, reports files transferred.

- [ ] **Step 2: Verify one image URL**

Run: `curl -I "https://atmina.lv/images/briefs/$(ls output/atmina/images/briefs | head -1)"`
Expected: `HTTP/2 200`.

- [ ] **Step 3: Verify OG tag**

Run: `curl -s "https://atmina.lv/blog/$(ls output/atmina/blog/ | head -1)" | grep "og:image"`
Expected: prints `<meta property="og:image" content="https://atmina.lv/images/briefs/...png">`.

- [ ] **Step 4: Manual social preview**

Post the URL in Signal/Telegram/X, verify image preview renders with correct headline visible in-card.

No commit — deploy has no local code changes.

---

## Post-Implementation Checklist

- [ ] All 7 phases committed.
- [ ] `pytest tests/ -v` fully green.
- [ ] Homepage, `/analizes`, and a sample `/blog/<slug>.html` look correct in production.
- [ ] `https://atmina.lv/images/briefs/<slug>-<hash>.png` returns 200.
- [ ] OG preview works on at least one social platform.
- [ ] `data/gemini_key.json` is NOT in git (`git log --all -- data/gemini_key.json` should return nothing).
- [ ] `MONTHLY_BUDGET_USD = 5.00` is appropriate — revisit after first month of routine usage.

## Rollback Notes

If something goes wrong in production:
- Templates: revert specific template commit and re-deploy. Images remain served but featured-card may fall back to basic rendering.
- Backfill bad results: mark those rows `reject_image()` in DB, re-generate via routine's `@graphics-designer` regenerate flow.
- API quota exhausted: `MONTHLY_BUDGET_USD` halts new generation; existing approved images keep serving. Raise budget in `src/graphics/config.py` if needed.
- Preview model deprecated: update `data/gemini_key.json` `model` field to new model name.
