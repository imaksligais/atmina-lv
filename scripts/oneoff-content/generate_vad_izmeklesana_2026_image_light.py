"""One-off light-theme image generator for analizes/vad-izmeklesana-2026.

Light twin of generate_vad_izmeklesana_2026_image.py — same metaphor
(archive grid + amber lens ring over one anomalous declaration sheet),
re-graded for the light page theme (paper background, ink lines,
red accent), output as <slug>-light.png master.
"""
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src.graphics.nanobanana import generate_image
from src.db import now_lv

PROMPT = """Editorial poster illustration for a Latvian political-transparency investigation page about public officials' financial declarations — LIGHT THEME version. Background: warm cream paper (#f7f3e8 to #f1ead6 gradient), subtle paper-grain texture. 16:9 aspect ratio, generous negative space, rule-of-thirds composition. Visual metaphor: a neat grid of many identical blank document sheets (declaration forms) receding in perspective toward the upper-left — rows of fine ink-gray outlined rectangles with abstract grid markings, like an archive index printed on paper. Above the center of the grid hovers a large, thin circular magnifying-lens rim drawn as a delicate deep-blue (#1f2d4d) line; inside the lens, ONE document sheet is subtly different — its abstract grid markings form a slightly irregular, denser pattern, and a restrained brick-red (#B71C1C) wash marks that single sheet. A few small geometric markers (a tiny square, a circle, a narrow bar) float out of the lens-lit sheet, connected by a faint dotted line — suggesting extracted anomalies. Lighting: flat daylight, minimal shadows, calm print-editorial feel. Mood: investigative, archival, forensic, restrained. Style references: Economist data-illustration (light background variants), Le Monde long-form hero illustrations, archival-document hero imagery, forensic-audit aesthetics, flat print editorial.\n\nSTRICT CONSTRAINTS — do NOT include: any text, letters, numbers, words, captions, labels, currency symbols (€, $, Ls), percentages, dates, watermarks, signatures, faces, people, hands, a literal magnifying-glass handle, photorealistic elements, cartoon style, decorative borders, national flags, recognizable individuals, coins, bank notes, maps. ZERO TYPOGRAPHY anywhere in the image — typography will be added by the page template. ZERO numerical figures. The document sheets must NOT contain any readable text, only abstract grid suggestions. Color discipline: cream/paper background dominant; lines in ink-gray and deep navy; the ONLY saturated accent is the single brick-red marked sheet. No dark-mode glow, no neon, no heavy shadows."""

OUT_DIR = Path("output/images/analizes")
OUT_DIR.mkdir(parents=True, exist_ok=True)
OUT_PATH = OUT_DIR / "vad-izmeklesana-2026-light.png"
AUDIT_PATH = OUT_DIR / "vad-izmeklesana-2026-light.audit.json"

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
        print(f"[ok] vad-izmeklesana-2026-light.png saved ({len(png_bytes)} bytes, attempt {attempt}, {elapsed:.1f}s)")
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
audit["note"] = "One-off LIGHT-theme thematic image for analizes/vad-izmeklesana-2026 page. Not stored in brief_images table (no note_id binding). Awaiting human visual review."

AUDIT_PATH.write_text(json.dumps(audit, indent=2, ensure_ascii=False), encoding="utf-8")
print(f"audit -> {AUDIT_PATH}")
