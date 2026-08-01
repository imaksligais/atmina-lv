"""One-off image generator for analizes/vad-2026 page.

Composes a 16:9 editorial illustration for the VAD declarations analysis page,
calls Gemini image API, saves PNG + audit JSON. Mirrors the pattern used for
deklaracijas-2026.png (KNAB analysis) but with a different visual metaphor
focused on official declarations / income / assets.
"""
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.graphics.nanobanana import generate_image
from src.db import now_lv

PROMPT = """Editorial poster illustration for a Latvian political-transparency analysis page about VID public officials' financial declarations (income, real estate, business holdings). Dark muted background — deep charcoal navy (#0d1014 to #1a1f2e gradient), with subtle paper-grain texture. 16:9 aspect ratio, generous negative space, rule-of-thirds composition. Visual metaphor: a stack of layered, semi-transparent rectangular form-sheets fanning out from the bottom-left corner toward the upper-right, suggesting filed declarations stacking up over time. Each sheet outlined with a thin pale-graphite line, faint grid markings barely visible inside (suggesting form fields). Above and right of the stack, a soft constellation of small geometric markers — squares for buildings, circles for share-holdings, narrow rectangles for land plots — connected by faint dotted lines forming an abstract network. One stylized silhouette of a generic government office building at the right edge, simple geometric line-art only, not photorealistic, partly obscured by the topmost form-sheet. The stack is illuminated by a single warm-amber light source from the upper-right, casting subtle long shadows. Mood: analytical, archival, restrained, investigative, serious. Newspaper-editorial register. Style references: Economist data-illustration, Le Monde long-form hero illustrations, restrained monochromatic editorial work, archival-document hero imagery.\n\nSTRICT CONSTRAINTS — do NOT include: any text, letters, numbers, words, captions, labels, party names, party logos, currency symbols (€, $, Ls), percentages, dates, watermarks, signatures, faces, people, hands, photorealistic elements, cartoon style, decorative borders, national flags, recognizable individuals, coins, bank notes. ZERO TYPOGRAPHY anywhere in the image — typography will be added by the page template. ZERO numerical figures. The building silhouette must be a simplified geometric outline only, not photorealistic, not a recognizable real building. The form-sheets must NOT contain any readable text, only abstract grid suggestions. Color discipline: dark navy/charcoal dominant, muted colors only (no saturated reds or yellows except the single warm amber light accent)."""

OUT_DIR = Path("output/images/analizes")
OUT_DIR.mkdir(parents=True, exist_ok=True)
OUT_PATH = OUT_DIR / "vad-2026.png"
AUDIT_PATH = OUT_DIR / "vad-2026.audit.json"

audit = {
    "out_path": str(OUT_PATH).replace("/", "\\"),
    "model": "gemini-3.1-flash-image-preview",
    "aspect": "16:9",
    "prompt": PROMPT,
    "attempts": [],
}

success = False
last_err = None
for attempt in range(1, 4):
    t0 = time.time()
    try:
        png_bytes = generate_image(PROMPT, aspect_ratio="16:9")
        elapsed = time.time() - t0
        OUT_PATH.write_bytes(png_bytes)
        audit["successful_attempt"] = attempt
        audit["total_attempts"] = attempt
        audit["attempts"].append({
            "attempt": attempt,
            "status": "success",
            "bytes": len(png_bytes),
            "elapsed_sec": round(elapsed, 2),
            "timestamp_lv": now_lv(),
        })
        success = True
        print(f"[ok] vad-2026.png saved ({len(png_bytes)} bytes, attempt {attempt}, {elapsed:.1f}s)")
        break
    except Exception as e:
        elapsed = time.time() - t0
        last_err = e
        audit["attempts"].append({
            "attempt": attempt,
            "status": "error",
            "error": f"{type(e).__name__}: {e}",
            "elapsed_sec": round(elapsed, 2),
            "timestamp_lv": now_lv(),
        })
        print(f"[err] attempt {attempt}: {type(e).__name__}: {e}")

audit["result"] = "success" if success else "failure"
audit["approved"] = False
audit["note"] = "One-off thematic image for analizes/vad-2026 page. Not stored in brief_images table (no note_id binding). Awaiting human visual review."

AUDIT_PATH.write_text(json.dumps(audit, indent=2, ensure_ascii=False), encoding="utf-8")
print(f"audit -> {AUDIT_PATH}")

if not success:
    raise SystemExit(f"image generation failed after 3 attempts: {last_err}")
