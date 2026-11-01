"""One-off image generator for analizes/vad-izmeklesana-2026 page.

Composes a 16:9 editorial illustration for the VAD investigation page
(60 officials' declarations swept for anomalies). Mirrors
generate_vad_2026_image.py but with a different visual metaphor:
a magnifying lens over rows of declaration documents, one sheet
standing out.
"""
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src.graphics.nanobanana import generate_image
from src.db import now_lv

PROMPT = """Editorial poster illustration for a Latvian political-transparency investigation page about public officials' financial declarations. Dark muted background — deep charcoal navy (#0d1014 to #1a1f2e gradient), subtle paper-grain texture. 16:9 aspect ratio, generous negative space, rule-of-thirds composition. Visual metaphor: a neat grid of many identical blank document sheets (declaration forms) receding in perspective toward the upper-left — rows of faint graphite-outlined rectangles with abstract grid markings, like an archive index. Above the center of the grid hovers a large, thin circular magnifying-lens rim drawn as a delicate amber-gold line; inside the lens, ONE document sheet is subtly different — its abstract grid markings form a slightly irregular, denser pattern, and the sheet glows faintly warmer. A few small geometric markers (a tiny square, a circle, a narrow bar) float out of the lens-lit sheet, connected by a faint dotted line — suggesting extracted anomalies. Light source: soft warm amber glow from the lens area only; rest of the scene cool and dim. Mood: investigative, archival, forensic, restrained. Newspaper-editorial register. Style references: Economist data-illustration, Le Monde long-form hero illustrations, archival-document hero imagery, forensic-audit aesthetics.\n\nSTRICT CONSTRAINTS — do NOT include: any text, letters, numbers, words, captions, labels, currency symbols (€, $, Ls), percentages, dates, watermarks, signatures, faces, people, hands, a literal magnifying-glass handle, photorealistic elements, cartoon style, decorative borders, national flags, recognizable individuals, coins, bank notes, maps. ZERO TYPOGRAPHY anywhere in the image — typography will be added by the page template. ZERO numerical figures. The document sheets must NOT contain any readable text, only abstract grid suggestions. Color discipline: dark navy/charcoal dominant, muted colors only; the single warm amber accent is the lens rim and the glow around the highlighted sheet."""

OUT_DIR = Path("output/images/analizes")
OUT_DIR.mkdir(parents=True, exist_ok=True)
OUT_PATH = OUT_DIR / "vad-izmeklesana-2026.png"
AUDIT_PATH = OUT_DIR / "vad-izmeklesana-2026.audit.json"

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
        print(f"[ok] vad-izmeklesana-2026.png saved ({len(png_bytes)} bytes, attempt {attempt}, {elapsed:.1f}s)")
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
audit["note"] = "One-off thematic image for analizes/vad-izmeklesana-2026 page. Not stored in brief_images table (no note_id binding). Awaiting human visual review."

AUDIT_PATH.write_text(json.dumps(audit, indent=2, ensure_ascii=False), encoding="utf-8")
print(f"audit -> {AUDIT_PATH}")
