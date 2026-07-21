"""One-shot synthesis featured-image generator for the Kulbergs-government
formation synthesis. Mirrors scripts/generate_synthesis_image.py:

Writes the PNG to the SOURCE folder ``output/images/synthesis/`` under the
stable slug filename, inserts an audit context_notes row + brief_images row
(approved=0 awaiting operator review). ``generate_public_site()`` copies the
source dir into the deploy tree so the image survives a clean rebuild.
"""
from __future__ import annotations

import json
from pathlib import Path

from src.db import get_db, now_lv
from src.graphics.config import budget_check, load_gemini_key
from src.graphics.nanobanana import generate_image, SafetyError
from src.graphics.storage import save_error_row, save_image_row


SYNTHESIS_SLUG = "kulberga-valdibas-izveide-2026-05"
OUT_PATH = Path("output/images/synthesis") / f"{SYNTHESIS_SLUG}.png"
SYNTHESIS_MD = f"wiki/synthesis/{SYNTHESIS_SLUG}.md"
TITLE = "No vakuuma līdz Kulberga valdībai: kā četrpadsmit dienās izpildvaru pārņēma opozīcija"

# Hand-composed prompt — synthesis articles have no canonical headline/stat
# triad and we want ZERO rendered text. Editorial noir-doc poster on atmina.lv
# dark brand. Metaphor: four separate metallic arcs converging to form a single
# ring (a four-partner coalition assembling into one government), with a small
# unclosed gap (incomplete internal unity) and a restrained amber editorial seam
# at the convergence point.
PROMPT = """Editorial poster illustration in the noir-documentary political tradition.
Near-black background (#0d1014), textured paper overlay with very fine grain,
generous negative space, rule-of-thirds composition, 16:9 aspect ratio.

Central visual metaphor: four separate curved arc segments rendered in muted
metallic gray, each sweeping inward from a different direction, converging so
their ends almost meet to form a single large ring near the center of the
frame. The ring is ALMOST closed — one small gap remains where two arc-ends do
not quite touch, leaving a deliberate break in the circle. The four converging
arcs are the single focal subject: separate pieces assembling into one whole.

At the point where the arcs converge, a thin restrained seam of warm amber /
ochre light (#eab308) glows along the inner edge of the ring — the editorial
signal color, present as a clear narrow graphic element, not ambient haze. The
small unclosed gap is touched by a faint, cooler oxidized accent, hinting at
incompleteness.

Behind and beneath the ring, faint architectural rhythm suggesting a formal
institutional chamber: thin vertical columnar lines or receding parallel
rulings, extremely subtle, barely perceptible — hints of a parliamentary
interior without ever depicting recognizable rooms or figures.

Surface treatment: aged editorial poster paper grain with soft, even uneven
vignetting that gently darkens the four corners. The corners are CLEAN — empty
dark paper only, with no marks, dots, crosses, codes, symbols, or signatures of
any kind. Lighting is directional and low, casting deep shadows. Style reference:
The Economist / New York Review of Books cover illustrations meet
Eastern-European political documentary photography.

Mood: restrained, analytical, politically sober, the weight of reassembly and
unfinished consensus. Not sensational, not dramatic, not cinematic — editorial.

STRICT TEXT RULE: render ABSOLUTELY ZERO text, letters, numbers, or
typography of any kind anywhere in the image. No headline, no title,
no caption, no subtitle, no date, no label on any graphic element, no
logo, no watermark, no signature, no serial number, no registration
code, no party name, no abbreviation (NOT "atmina.lv", NOT any party
or company name), no percentage, no figure, no year. If the model is
tempted to render any character, letter, digit, or punctuation mark,
it must refuse and produce only the visual.

Do NOT include: people, faces, hands, body parts, silhouettes of
individuals, party logos, national flags, ballot boxes, photorealistic
elements, cartoon or illustration-book style, decorative borders, or any
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
        "title": TITLE,
    }, ensure_ascii=False)
    cur = db.execute(
        "INSERT INTO context_notes (opponent_id, note_type, content, created_at) "
        "VALUES (NULL, 'context', ?, ?)",
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

    image_id = save_image_row(
        db, note_id,
        image_path=f"atmina/images/synthesis/{SYNTHESIS_SLUG}.png",
        prompt=PROMPT, model=key["model"], seed=None,
        width=1792, height=1024, cost=0.039, aspect="16:9",
    )
    print(f"[db] brief_images.id={image_id} approved=0 (pending review)")
    return {"status": "pending_approval", "image_id": image_id,
            "image_path": str(OUT_PATH.resolve()), "note_id": note_id}


if __name__ == "__main__":
    result = main()
    print("---RESULT---")
    print(json.dumps(result, ensure_ascii=False, indent=2))
