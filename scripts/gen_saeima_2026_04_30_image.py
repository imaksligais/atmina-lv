"""One-shot image generator for synthesis saeima-2026-04-30-balsojumi.

Mirrors scripts/generate_synthesis_image.py pattern (off-routine companion to
@graphics-designer). Audit row in context_notes + DB row in brief_images +
PNG at output/atmina/images/synthesis/<slug>.png + responsive variants via
src.image_variants.make_variants. Stable filename, NOT hash-suffixed.
"""
from __future__ import annotations

import json
from pathlib import Path

from src.db import get_db, now_lv
from src.graphics.config import budget_check, load_gemini_key
from src.graphics.nanobanana import generate_image, SafetyError
from src.graphics.storage import save_error_row, save_image_row


SYNTHESIS_SLUG = "saeima-2026-04-30-balsojumi"
OUT_PATH = Path("output/atmina/images/synthesis") / f"{SYNTHESIS_SLUG}.png"
SYNTHESIS_MD = f"wiki/synthesis/{SYNTHESIS_SLUG}.md"


PROMPT = """Editorial poster illustration in the calm documentary political
tradition. Near-black background (#0d1014), textured paper overlay with very
fine grain, generous negative space, rule-of-thirds composition, 16:9 aspect
ratio.

Central visual metaphor: a stylized abstract semicircle (parliamentary
hemicycle seen from above), rendered in muted metallic gray as a pattern of
small horizontal seat-bars arranged in concentric arcs. One sector of the
arc — about a sixth of the semicircle, positioned slightly right-of-center —
sits clearly out of alignment with the rest: its seat-bars are tilted at a
different angle and slightly offset, with a narrow gap of empty space
separating it from its neighbors. A thin warm amber line traces along that
gap, marking the separation as a quiet editorial accent.

The misaligned sector is the single focal subject. The other arcs remain
intact and orderly.

Accent color: warm amber / ochre (#eab308), used SPARINGLY — the narrow
amber line along the gap, plus a single soft amber ray falling diagonally
across one orderly section of the hemicycle. The amber must be present as
a clear graphic element, not merely as ambient haze.

Surface treatment: aged editorial poster paper grain, small print-registration
marks faintly visible in one corner, like a scanned 1970s political weekly.
Lighting is directional and low, casting soft long shadows. Style reference:
The Economist / New York Review of Books cover illustrations meet
Eastern-European political documentary photography.

Mood: restrained, analytical, politically sober, weight of consequence — the
quiet moment when a vote tally reveals an unspoken difference of position.
Not sensational, not dramatic, not cinematic — editorial.

STRICT TEXT RULE: render ABSOLUTELY ZERO text, letters, numbers, or
typography of any kind anywhere in the image. No headline, no title, no
caption, no subtitle, no date, no label on any graphic element, no logo,
no watermark, no signature, no serial number, no registration code, no
party name, no percentage, no figure, no year, no roman numeral. If the
model is tempted to render any character, letter, digit, or punctuation
mark, it must refuse and produce only the visual.

Avoid: people, faces, hands, body parts, silhouettes of individuals,
party logos, national flags, the actual Saeima building exterior or
recognizable interior, photorealistic elements, cartoon or illustration-
book style, decorative borders, voting machines, ballot boxes, or any
recognizable real-world individuals or corporate identities."""


def main():
    db = get_db("data/atmina.db")
    key = load_gemini_key()

    budget_check(db)

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)

    audit_content = json.dumps({
        "kind": "synthesis_featured_image",
        "synthesis_path": SYNTHESIS_MD,
        "slug": SYNTHESIS_SLUG,
        "title": "Saeimas 30. aprīļa sēde: koalīcijas plaisas un pensiju mozaīka",
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

    OUT_PATH.write_bytes(png_bytes)
    print(f"[png] wrote {len(png_bytes)} bytes to {OUT_PATH}")

    try:
        from src.image_variants import make_variants
        make_variants(OUT_PATH)
        print(f"[variants] hero/card/thumb webp + og.jpg generated")
    except Exception as exc:
        import logging
        logging.getLogger(__name__).warning(
            "variant generation failed for %s: %s", OUT_PATH.name, exc
        )

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
