"""Ad-hoc synthesis featured-image generator.

Off-routine companion to @graphics-designer for wiki/synthesis/ articles.
Builds an audit context_notes row + brief_images row, writes the PNG to the
SOURCE folder ``output/images/synthesis/`` under a stable filename (NOT
hash-based), and leaves the DB row with approved=0 awaiting operator review.
``generate_public_site()`` copies the source dir into the deploy tree
(``output/atmina/images/synthesis/``), so the image survives a clean rebuild.

One-shot. Not part of automated routine.
"""
from __future__ import annotations

import json
from pathlib import Path

from src.db import get_db, now_lv
from src.graphics.config import budget_check, load_gemini_key
from src.graphics.nanobanana import generate_image, SafetyError
from src.graphics.storage import save_error_row, save_image_row


SYNTHESIS_SLUG = "partiju-programmas-2026-solijumu-karte"
OUT_PATH = Path("output/images/synthesis") / f"{SYNTHESIS_SLUG}.png"
SYNTHESIS_MD = f"wiki/synthesis/{SYNTHESIS_SLUG}.md"


# Hand-composed prompt — not via build_prompt() because synthesis articles
# have no canonical topic/headline/stat triad and we want ZERO rendered text.
# Editorial poster base, adapted to atmina.lv dark brand (noir doc mood).
# Metaphor mirrors the synthesis structure: a cartographic chart of routes —
# some converging on shared landmarks (consensus themes), some running to
# opposite edges (polarization axes), with blank uncharted regions (silence).
PROMPT = """Editorial poster illustration in the noir-documentary political tradition.
Near-black background (#0d1014), textured paper overlay with very fine grain,
generous negative space, rule-of-thirds composition, 16:9 aspect ratio.

Central visual metaphor: an abstract vintage cartographic chart, drawn as
thin engraved lines on dark aged paper. Across the chart run many distinct
route lines — slender pale-gray paths like shipping lanes on an old nautical
map. Several of the routes converge and briefly bundle together at two or
three small shared waypoints near the center (drawn as tiny circular
survey marks), then split apart again. Two groups of routes pull hard
toward opposite edges of the chart, diverging like magnetic field lines,
never to meet. One corner region of the chart is conspicuously empty —
uncharted, blank dark paper with only the faintest unfinished grid,
a region the routes avoid entirely.

Supporting elements: a faint compass rose, incomplete and partly worn away,
in the lower third; hairline latitude and longitude rulings receding into
the dark; subtle contour-line topography barely perceptible under the
routes. All linework is fine, restrained, engraver-precise — no thick
strokes.

Accent color: warm amber / ochre (#eab308), used SPARINGLY — exactly one
route line rendered in amber, tracing its full path across the chart
through a shared waypoint and out toward an edge. The amber route is the
single editorial signal element; everything else stays gray and off-white.

Surface treatment: aged editorial poster paper grain, small print-registration
marks faintly visible in one corner, like a scanned 1970s political weekly.
Lighting is directional and low, casting deep shadows. Style reference:
The Economist / New York Review of Books cover illustrations meet
Eastern-European political documentary photography.

Mood: restrained, analytical, politically sober — a map of promises made,
routes declared but not yet traveled. Not sensational, not dramatic,
not cinematic — editorial.

STRICT TEXT RULE: render ABSOLUTELY ZERO text, letters, numbers, or
typography of any kind anywhere in the image. No headline, no title,
no caption, no subtitle, no date, no label on any graphic element, no
place names, no compass letters (no N, S, E, W on the compass rose),
no coordinates, no logo, no watermark, no signature, no serial number,
no registration code, no party name or abbreviation (NOT "atmina.lv",
NOT any organization name), no percentage, no figure, no year.
If the model is tempted to render any character, letter, digit, or
punctuation mark, it must refuse and produce only the visual.

Do NOT include: people, faces, hands, body parts, silhouettes of
individuals, party logos, national flags, recognizable country or
region outlines (the chart must NOT depict Latvia or any real
geography), photorealistic elements, cartoon or illustration-book
style, decorative borders, or any recognizable real-world individuals
or corporate identities."""


def main():
    db = get_db("data/atmina.db")
    key = load_gemini_key()

    # Budget gate
    budget_check(db)

    # Ensure output directory exists
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)

    # Create audit context_notes row so brief_images.note_id FK resolves.
    # note_type='context' (existing type) with a marker in content.
    audit_content = json.dumps({
        "kind": "synthesis_featured_image",
        "synthesis_path": SYNTHESIS_MD,
        "slug": SYNTHESIS_SLUG,
        "title": "Partiju programmas 2026: solījumu karte",
    }, ensure_ascii=False)
    cur = db.execute(
        """
        INSERT INTO context_notes (opponent_id, note_type, content, created_at)
        VALUES (NULL, 'context', ?, ?)
        """,
        (audit_content, now_lv()),
    )
    db.commit()
    note_id = cur.lastrowid
    print(f"[audit] context_notes row id={note_id}")

    # Generate
    try:
        png_bytes = generate_image(PROMPT, aspect_ratio="16:9")
    except SafetyError as e:
        eid = save_error_row(db, note_id, PROMPT, key["model"], f"SAFETY: {e}")
        print(f"[error] safety_blocked, row_id={eid}")
        return {"status": "failed", "error": "safety_blocked", "row_id": eid}
    except Exception as e:
        eid = save_error_row(db, note_id, PROMPT, key["model"], str(e))
        print(f"[error] {e}, row_id={eid}")
        return {"status": "failed", "error": str(e), "row_id": eid}

    # Persist PNG at user-specified stable filename (NOT hash-suffixed,
    # because the user gave an explicit public URL path)
    OUT_PATH.write_bytes(png_bytes)
    print(f"[png] wrote {len(png_bytes)} bytes to {OUT_PATH}")

    # Keep same relative-path style as briefs images: path recorded in DB
    # is under output/atmina/ to match deploy structure.
    image_id = save_image_row(
        db,
        note_id,
        image_path=f"atmina/images/synthesis/{SYNTHESIS_SLUG}.png",
        prompt=PROMPT,
        model=key["model"],
        seed=None,
        width=1792,
        height=1024,
        cost=0.039,
        aspect="16:9",
    )
    print(f"[db] brief_images.id={image_id} approved=0 (pending review)")

    return {
        "status": "pending_approval",
        "image_id": image_id,
        "image_path": str(OUT_PATH.resolve()),
        "note_id": note_id,
    }


if __name__ == "__main__":
    result = main()
    print("---RESULT---")
    print(json.dumps(result, ensure_ascii=False, indent=2))
