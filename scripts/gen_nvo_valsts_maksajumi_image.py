"""One-off image generator for analizes/nvo-valsts-maksajumi page (v2, 2026-08-09).

Dark + light variants, nanobanana via src.graphics.nanobanana — same pattern as
generate_vad_2026_image.py. Visual metaphor: state budget outflow concentration —
one wide channel from the left fans out into hundreds of thin streams, but nearly
all volume gathers into a small cluster of deep pools on the right; a wide shallow
field at the bottom gets only a trickle.
"""
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.graphics.nanobanana import generate_image
from src.db import now_lv

METAPHOR = (
    "Visual metaphor: one wide, calm channel of pale-gold light enters from the left edge; "
    "it fans out into hundreds of very thin graphite thread-streams spreading across the middle "
    "third, like a river delta drawn in fine line-art; but nearly all the threads bend and gather "
    "into a small cluster of a few deep, bold open-ring pools on the right third that visibly "
    "dominate the composition; across the bottom, a wide shallow field of tiny open rings receives "
    "only a sparse trickle of threads. Beneath, a faint, almost-vanishing horizontal ledger grid, "
    "barely visible. One subtle warm-amber accent glow inside the largest pool."
)
CONSTRAINTS = (
    "\n\nSTRICT CONSTRAINTS — do NOT include: any text, letters, numbers, words, captions, labels, "
    "logos, currency symbols (€, $, Ls), percentages, dates, watermarks, signatures, faces, people, "
    "hands, photorealistic elements, cartoon style, decorative borders, national flags, coins, "
    "bank notes. ZERO TYPOGRAPHY anywhere in the image — typography is added by the page template."
)
DARK = (
    "Editorial poster illustration for a Latvian political-transparency analysis page about state "
    "budget payments to NGOs and their concentration. Dark muted background — deep charcoal navy "
    "(#0d1014 to #1a1f2e gradient), with subtle paper-grain texture. 16:9 aspect ratio, generous "
    "negative space, rule-of-thirds composition. Geometric line-art style, not photorealistic, "
    "muted and restrained. " + METAPHOR + CONSTRAINTS
)
LIGHT = (
    "Editorial poster illustration for a Latvian political-transparency analysis page. LIGHT theme: "
    "warm cream paper background (#f7f3e8 with a very subtle aged-paper grain, gently darkening "
    "toward #efe8d5 at edges). All linework in dark graphite ink (#1f1b14, thin elegant lines), "
    "threads in deep-navy (#2c4270), pools' accent in muted brick red (#B71C1C). Geometric line-art "
    "style, not photorealistic, muted and restrained. 16:9 aspect ratio, generous negative space, "
    "rule-of-thirds composition. " + METAPHOR + CONSTRAINTS
)

OUT_DIR = Path("output/images/analizes")
OUT_DIR.mkdir(parents=True, exist_ok=True)

def gen(prompt, stem):
    out_path = OUT_DIR / f"{stem}.png"
    audit_path = OUT_DIR / f"{stem}.audit.json"
    audit = {"out_path": str(out_path).replace("/", "\\"), "model": "nanobanana",
             "aspect": "16:9", "prompt": prompt, "attempts": []}
    success, last_err = False, None
    for attempt in range(1, 4):
        t0 = time.time()
        try:
            png_bytes = generate_image(prompt, aspect_ratio="16:9")
            out_path.write_bytes(png_bytes)
            audit["successful_attempt"] = attempt
            audit["attempts"].append({"attempt": attempt, "status": "success",
                                      "bytes": len(png_bytes), "elapsed_sec": round(time.time() - t0, 2),
                                      "timestamp_lv": now_lv()})
            success = True
            print(f"[ok] {stem}.png ({len(png_bytes)} bytes, attempt {attempt})")
            break
        except Exception as e:
            last_err = e
            audit["attempts"].append({"attempt": attempt, "status": "error",
                                      "error": f"{type(e).__name__}: {e}",
                                      "elapsed_sec": round(time.time() - t0, 2),
                                      "timestamp_lv": now_lv()})
            print(f"[err] {stem} attempt {attempt}: {type(e).__name__}: {e}")
    audit["result"] = "success" if success else "failure"
    audit["approved"] = False
    audit["note"] = "One-off thematic image for analizes/nvo-valsts-maksajumi (v2). Awaiting human visual review."
    audit_path.write_text(json.dumps(audit, indent=2, ensure_ascii=False), encoding="utf-8")
    if not success:
        raise SystemExit(f"{stem}: failed after 3 attempts: {last_err}")

gen(DARK, "nvo-valsts-maksajumi")
gen(LIGHT, "nvo-valsts-maksajumi-light")
