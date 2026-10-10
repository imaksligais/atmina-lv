"""Generate dark/light featured images for the education-reform synthesis.

One-shot, off-routine generator. Images remain pending approval in brief_images.
"""
from __future__ import annotations

import json
from pathlib import Path

from src.db import get_db, now_lv
from src.graphics.config import budget_check, load_gemini_key
from src.graphics.nanobanana import SafetyError, generate_image
from src.graphics.storage import save_error_row, save_image_row

SLUG = "izglitibas-reforma-pirms-1-septembra"
OUT_DIR = Path("output/images/synthesis")
SYNTHESIS_MD = f"wiki/synthesis/{SLUG}.md"

COMPOSITION = """Wide 16:9 editorial illustration, straight-on view into an empty modern public-school classroom. The composition is symmetrical and calm. In the foreground, one large plain school desk anchors the image. On it lie exactly three symbolic objects: a completely blank exam sheet with empty geometric answer boxes, a small architectural model of a regional school building, and a simple brass balance scale with a few unmarked coin-shaped discs on one side. In the middle distance, three narrow floor paths leave the desk: one leads to a blank blackboard, one to a classroom door, and one to a softly lit window. The paths meet at the desk but diverge beyond it, expressing one political debate made of three different decisions: assessment, school access, and funding.

No people, children, faces, hands, politicians, flags, party colors, logos, national symbols, maps, readable documents, screens, charts, decorative borders or photo frames. The room must look Latvian/Northern European but contain no identifiable institution. Restrained, factual, neutral editorial mood; not dystopian, not triumphant, not sentimental. Fine paper grain and subtle print texture.

STRICT TEXT RULE: render absolutely no text, letters, numbers, equations, handwriting, labels, logos, watermarks, signatures or pseudo-text anywhere. Blackboard fully blank. Exam sheet fully blank except simple empty circles and squares. Coin-shaped discs fully blank. Full-bleed edge-to-edge composition, no border, no frame, no paper margins."""

DARK_PROMPT = COMPOSITION + """

DARK THEME VERSION: near-black navy and charcoal classroom, deep blue-gray shadows, warm amber light entering from the side and touching only the desk, the brass scale and the three diverging floor paths. Off-white blank paper. High contrast but readable, sober investigative-journalism cover aesthetic, etched photographic realism, atmina.lv dark visual language. Avoid pure black crushing; preserve detail in the classroom."""

LIGHT_PROMPT = COMPOSITION + """

LIGHT THEME VERSION: warm ivory and pale stone classroom, soft natural daylight, muted slate-blue shadows, restrained terracotta and ochre accents on the desk edges and the three diverging floor paths. Dark graphite linework, airy negative space, elegant European newspaper illustration, atmina.lv light visual language. Avoid washed-out whites; preserve clear object separation and readable contrast."""


def _generate_one(db, note_id: int, key: dict, suffix: str, prompt: str) -> dict:
    budget_check(db)
    out_path = OUT_DIR / f"{SLUG}{suffix}.png"
    try:
        png_bytes = generate_image(prompt, aspect_ratio="16:9")
    except SafetyError as exc:
        row_id = save_error_row(db, note_id, prompt, key["model"], f"SAFETY: {exc}")
        return {"status": "failed", "row_id": row_id, "error": str(exc)}
    except Exception as exc:
        row_id = save_error_row(db, note_id, prompt, key["model"], str(exc))
        return {"status": "failed", "row_id": row_id, "error": str(exc)}

    out_path.write_bytes(png_bytes)
    image_id = save_image_row(
        db,
        note_id,
        image_path=f"images/synthesis/{out_path.name}",
        prompt=prompt,
        model=key["model"],
        seed=None,
        width=1792,
        height=1024,
        cost=0.039,
        aspect="16:9",
    )
    return {
        "status": "pending_approval",
        "image_id": image_id,
        "path": str(out_path.resolve()),
        "bytes": len(png_bytes),
    }


def main() -> dict:
    db = get_db("data/atmina.db")
    key = load_gemini_key()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    audit = json.dumps(
        {
            "kind": "synthesis_featured_image_pair",
            "synthesis_path": SYNTHESIS_MD,
            "slug": SLUG,
            "title": "Reforma pirms 1. septembra: kur saduras eksāmeni, finansēšana un valdības atbildība",
            "variants": ["dark", "light"],
        },
        ensure_ascii=False,
    )
    cur = db.execute(
        """INSERT INTO context_notes (opponent_id, note_type, content, created_at)
           VALUES (NULL, 'context', ?, ?)""",
        (audit, now_lv()),
    )
    db.commit()
    note_id = cur.lastrowid
    result = {
        "note_id": note_id,
        "dark": _generate_one(db, note_id, key, "", DARK_PROMPT),
        "light": _generate_one(db, note_id, key, "-light", LIGHT_PROMPT),
    }
    return result


if __name__ == "__main__":
    print(json.dumps(main(), ensure_ascii=False, indent=2))
