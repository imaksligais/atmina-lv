"""Regenerate featured image for note_id=172 (weekly brief 2026-04-20..04-26).

Operator wants a more visually striking, editorial-poster variant for the
primary slot. Image #43 (shield with concentric ripples) stays in DB as
backup (approved=0). This script inserts a NEW brief_images row, also
approved=0, awaiting operator approval.

Metaphor direction (chosen): crossfire vectors converging on a single
painted target — multiple gestural arrows / streams of paint / light
beams meeting at one point on a richly textured surface. Captures the
week's "7 paralleli triecieni from 4+ attackers" narrative without
showing people. Painterly, hand-made feel; New Yorker / Politico cover
energy rather than infographic.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

# Force UTF-8 for stdout (Windows cp1252 chokes on Latvian diacritics).
sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]

from src.db import get_db
from src.graphics.config import budget_check, load_gemini_key
from src.graphics.nanobanana import SafetyError, generate_image
from src.graphics.prompt import NEGATIVE_CONSTRAINTS
from src.graphics.storage import (
    compute_filename,
    save_error_row,
    save_image_row,
)

NOTE_ID = 172


# Custom editorial-poster prompt — bypasses build_prompt() because the
# operator asked for a hand-tuned painterly variant, not the standard
# editorial template. Style block, metaphor block, headline block, and
# the existing NEGATIVE_CONSTRAINTS + STRICT TEXT RULE OVERRIDE are all
# kept consistent with the system contract.
STYLE_BLOCK = (
    "Editorial magazine cover style — New Yorker / Politico front-page energy. "
    "Painterly, hand-made aesthetic with visible brush texture, gestural strokes, "
    "and rich pigment saturation; NOT vector-flat, NOT stock-photo, NOT corporate "
    "AI-illustration. Textured surface (think gesso on canvas or thick cold-press "
    "paper) with subtle grain. Dramatic chiaroscuro lighting; deep shadows meeting "
    "warm highlights. Composition is dynamic and asymmetric, leaning into diagonal "
    "tension rather than centered symmetry. 16:9 aspect ratio. "
    "Mood: charged, urgent, editorial — converging pressure made visible."
)

METAPHOR_BLOCK = (
    "Topic: Aizsardzība un drošība\n"
    "Visual Metaphor: crossfire vectors converging on a single point — multiple "
    "gestural streams (painted arrows, raking light beams, ribbons of pigment) "
    "shooting in from different angles on the canvas, all meeting at one painted "
    "focal mark. The convergence point is where the eye lands; the streams are "
    "kinetic, irregular, brush-driven, NOT geometric. Use 6 to 8 distinct "
    "vectors of varying weight to suggest plural sources. The struck surface at "
    "the center can crack, ripple, or absorb the impact in a painterly way. "
    "Negative space around the streams, so the convergence reads instantly.\n"
    "Emotional Mood: charged, vigilant, under-pressure but composed\n"
    "Accent Color: deep navy as primary, with one warm accent (ochre or burnt "
    "sienna) carrying the brightest vectors against a muted, off-white / "
    "bone-colored painted background"
)

# Headline preserved verbatim with diacritics — but the OVERRIDE block at
# the end forces the final image to be text-free anyway. The headline is
# kept in the prompt only for thematic anchoring (model uses it as
# conceptual context even when not rendering it).
HEADLINE = "Sprūdam septiņas paralēlas spriedzes pēc AM atlūguma"
HEADLINE_BLOCK = (
    f'Headline text (render exactly as shown, preserve Latvian diacritics): '
    f'"{HEADLINE}"'
)

OVERRIDE_BLOCK = (
    "OVERRIDE — TEXT-FREE IMAGE: ignore all earlier instructions to render the "
    "headline. The final image MUST be a pure visual metaphor with ZERO text, "
    "ZERO letters, ZERO numbers, ZERO glyphs, ZERO captions, ZERO labels of any "
    "kind. No fake-runes, no fake-Latvian-words, no decorative pseudo-script. "
    "Convey the topic through composition, color, brush gesture, and abstract "
    "form alone."
)


def build_custom_prompt() -> str:
    return "\n\n".join(
        [
            STYLE_BLOCK,
            METAPHOR_BLOCK,
            HEADLINE_BLOCK,
            NEGATIVE_CONSTRAINTS,
            OVERRIDE_BLOCK,
        ]
    )


def main() -> dict:
    db = get_db("data/atmina.db")

    row = db.execute(
        "SELECT created_at, note_type, visual_brief_json "
        "FROM context_notes WHERE id=?",
        (NOTE_ID,),
    ).fetchone()
    if row is None:
        return {"status": "failed", "error": "note_id not found"}

    created_at, note_type, vb_json = row
    visual_brief = json.loads(vb_json)

    # Sanity: headline must match what we baked into the prompt.
    if visual_brief["headline"] != HEADLINE:
        return {
            "status": "failed",
            "error": (
                f"headline mismatch: brief='{visual_brief['headline']}' "
                f"vs script='{HEADLINE}'"
            ),
        }

    prompt_text = build_custom_prompt()

    # Budget check — propagates BudgetExceededError per agent contract.
    budget_check(db)
    key = load_gemini_key()

    try:
        png_bytes = generate_image(prompt_text, aspect_ratio="16:9")
    except SafetyError as exc:
        eid = save_error_row(
            db, NOTE_ID, prompt_text, key["model"], f"SAFETY: {exc}"
        )
        return {
            "status": "failed",
            "error": "safety_blocked",
            "row_id": eid,
        }
    except Exception as exc:  # noqa: BLE001
        eid = save_error_row(
            db, NOTE_ID, prompt_text, key["model"], str(exc)
        )
        return {"status": "failed", "error": str(exc), "row_id": eid}

    # File slug — same scheme as routine.py / agent contract.
    slug = f"{created_at[:10]}-nedelas-parskats"
    fname = compute_filename(slug, png_bytes)
    out_dir = Path("output/images/briefs")
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / fname
    out_path.write_bytes(png_bytes)

    # Responsive variants (non-fatal).
    try:
        from src.image_variants import make_variants

        make_variants(out_path)
    except Exception as exc:  # noqa: BLE001
        print(f"[warn] variant generation failed: {exc}")

    image_id = save_image_row(
        db,
        NOTE_ID,
        image_path=f"images/briefs/{fname}",
        prompt=prompt_text,
        model=key["model"],
        seed=None,
        width=1408,
        height=768,
        cost=0.039,
        aspect="16:9",
    )

    return {
        "status": "pending_approval",
        "image_id": image_id,
        "image_path": str(out_path),
        "metaphor": "crossfire vectors converging on single painted target",
    }


if __name__ == "__main__":
    result = main()
    print(json.dumps(result, ensure_ascii=False, indent=2))
