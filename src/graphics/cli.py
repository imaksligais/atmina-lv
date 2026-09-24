"""atmina image CLI — `python -m src.graphics.cli {brief,thread}`.

Replaces the per-day throwaway image scripts with two committed subcommands:

- ``brief --note-id N``   : faithful parameterization of the brief image
  pipeline (build_prompt + storage audit + budget + approval gate). Mirrors what
  the old generate_brief_image_<N>.py clones did, without a new file per day.
  Daily default since 2026-09-13: sepia + text-free (the house style the agent
  prompt has required since 2026-08-19); ``--style editorial`` (or ``--with-text``)
  brings the headline poster back. Weekly briefs keep the ink-navy ``weekly`` frame.
- ``thread --date D --prompts thread.json`` : sepia, text-free thread
  illustrations via the canonical SEPIA_STYLE (lightweight, no DB).

The @graphics-designer agent still authors metaphors/prompts; this CLI only
removes the boilerplate. See docs/superpowers/specs/2026-06-08-image-thread-cli-design.md.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from io import BytesIO
from pathlib import Path

from PIL import Image

from src.graphics.prompt import THREAD_STYLES
from src.graphics.thread import generate_thread

# Dienas pārskata attēla noklusējuma stils. Kopš 2026-08-19 (operatora lēmums,
# brief #472 precedents) aģenta prompts prasa `--style sepia --no-text` katram
# dienas pārskata attēlam (apstiprinātie #322, #323, #324 visi tā), bet CLI bez
# karogiem līdz 2026-09-13 deva `prompt.DEFAULT_STYLE` (editorial plakāts ar
# renderētu virsrakstu) — abi nesēji tagad saka vienu. `prompt.DEFAULT_STYLE`
# pats paliek editorial: tas ir `build_prompt()` plakāta noklusējums citiem
# izsaucējiem, ne šī CLI.
DAILY_BRIEF_STYLE: str = "sepia"


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(prog="python -m src.graphics.cli", description="atmina image CLI")
    sub = ap.add_subparsers(dest="cmd", required=True)

    b = sub.add_parser(
        "brief",
        help="Brief image (daily default: sepia, text-free; --style editorial for the headline poster)",
    )
    b.add_argument("--note-id", type=int, required=True, dest="note_id")
    b.add_argument("--metaphor", default=None, help="Override metaphor (else generic visual_map)")
    b.add_argument("--mood", default=None)
    b.add_argument("--accent", default=None)
    # Tri-state text flag: None → resolved from the style (sepia is text-free,
    # every other style renders the headline), an explicit flag wins. See
    # _resolve_no_text.
    text = b.add_mutually_exclusive_group()
    text.add_argument(
        "--no-text", action="store_const", const=True, dest="no_text", default=None,
        help="Text-free image: omit the rendered headline, metaphor carries it alone "
             "(default when the style is sepia)",
    )
    text.add_argument(
        "--with-text", action="store_const", const=False, dest="no_text",
        help="Render the headline in the image (default for editorial/weekly styles)",
    )
    # Default None → style is resolved from note_type (weekly_brief → "weekly",
    # daily → DAILY_BRIEF_STYLE), an explicit --style still wins. See _resolve_style.
    b.add_argument("--style", default=None)
    b.add_argument("--db", default="data/atmina.db")

    t = sub.add_parser("thread", help="Sepia text-free thread illustrations")
    t.add_argument("--date", required=True, help="YYYY-MM-DD (filename prefix)")
    t.add_argument("--prompts", required=True, help="JSON file {suffix: base_prompt}")
    t.add_argument("--out", default="output/images/threads")
    # 2026-09-07 (verdikts 47b): līdz šim `thread` pievienoja SEPIA_STYLE bez
    # nosacījuma, tāpēc gaišajam dvīnim (2026-09-06 airBaltic 2. sintēze) CLI
    # nebija lietojams un prompts palika ar roku skriptā docs/tweet_bank/.
    t.add_argument(
        "--style", default="sepia", choices=sorted(THREAD_STYLES),
        help="Pavediena attēla stils: sepia (noklusējums) vai light",
    )

    return ap


_BRIEF_DATE_RE = re.compile(r"(\d{4}-\d{2}-\d{2})")


def _brief_slug(created_at: str, note_type: str, topic: str | None = None) -> str:
    """Filename slug for a brief poster, keyed on note_type.

    weekly_brief → ``<date>-nedelas-parskats``; everything else (daily) →
    ``<date>-dienas-parskats``.

    The date is the brief's SUBJECT day, taken from ``topic``
    ('dienas analīze YYYY-MM-DD' / 'nedēļas analīze START līdz END'), not from
    ``created_at``. A routine that finishes after midnight creates the note on
    the following calendar day, so the created_at form named the 07-15 poster
    ``2026-07-16-...`` — repeatedly (07-10/11, 07-15/16); 33 stored briefs have
    a topic date that differs from their created_at date. The blog render
    already keys its URL off topic (`src/render/blog.py`, same priority chain),
    so this keeps the poster filename and the page it belongs to in agreement.

    Falls back to ``created_at[:10]`` when topic carries no date, which is the
    pre-2026-07-25 behaviour.
    """
    kind = "nedelas-parskats" if note_type == "weekly_brief" else "dienas-parskats"
    match = _BRIEF_DATE_RE.search(topic or "")
    date = match.group(1) if match else (created_at or "")[:10]
    return f"{date}-{kind}"


def _resolve_style(explicit_style: str | None, note_type: str) -> str:
    """Pick the prompt style. An explicit --style always wins; otherwise a
    weekly_brief uses the ink-navy ``weekly`` frame and daily uses
    DAILY_BRIEF_STYLE (sepia, since 2026-09-13).
    """
    if explicit_style is not None:
        return explicit_style
    return "weekly" if note_type == "weekly_brief" else DAILY_BRIEF_STYLE


def _resolve_no_text(explicit_no_text: bool | None, style_key: str) -> bool:
    """Pick the text mode. ``--no-text`` / ``--with-text`` always win; otherwise
    sepia is text-free and every other style renders the headline. The sepia
    style string itself forbids text, so a headline there is a contradiction
    (see prompt.py above ``STYLE_VARIANTS["sepia"]``) — the default keeps the
    pair consistent, an explicit ``--with-text`` is the caller's own call.
    """
    if explicit_no_text is not None:
        return explicit_no_text
    return style_key == "sepia"


def _run_thread(args) -> None:
    data = json.loads(Path(args.prompts).read_text(encoding="utf-8"))
    if not isinstance(data, dict) or not data:
        raise SystemExit("thread --prompts must be a non-empty JSON object {suffix: prompt}")
    written = generate_thread(args.date, data, args.out, style=args.style)
    print("RESULT_JSON:" + json.dumps(
        {"status": "ok", "count": len(written), "files": [str(p) for p in written]},
        ensure_ascii=False,
    ))


def _run_brief(args) -> None:
    from src.db import get_db
    from src.graphics.config import budget_check, load_gemini_key
    from src.graphics.nanobanana import generate_image
    from src.graphics.prompt import build_prompt
    from src.graphics.storage import (
        compute_filename,
        get_approved_image,
        link_audit_row,
        save_error_row,
        save_image_row,
    )
    from src.graphics.visual_map import get_visual

    db = get_db(args.db)
    row = db.execute(
        "SELECT visual_brief_json, created_at, note_type, topic FROM context_notes WHERE id=?",
        (args.note_id,),
    ).fetchone()
    if not row or not row["visual_brief_json"]:
        print("RESULT_JSON:" + json.dumps({"status": "no_visual_brief", "note_id": args.note_id}))
        return
    visual_brief = json.loads(row["visual_brief_json"])

    existing = get_approved_image(db, args.note_id)
    if existing:
        print("RESULT_JSON:" + json.dumps({"status": "already_approved", "image_path": existing}))
        return

    # House style: an explicit --metaphor overrides the generic per-topic
    # visual_map (matches metaphor_hint behavior); else fall back to visual_map.
    if args.metaphor:
        vm = {
            "metaphor": args.metaphor,
            "mood": args.mood or "purposeful, analytical",
            "accent": args.accent or "dark slate",
        }
    else:
        vm = dict(get_visual(visual_brief.get("topic", "")))
        if args.mood:
            vm["mood"] = args.mood
        if args.accent:
            vm["accent"] = args.accent

    style_key = _resolve_style(args.style, row["note_type"])
    no_text = _resolve_no_text(getattr(args, "no_text", None), style_key)
    prompt_text = build_prompt(visual_brief, vm, style_key=style_key, no_text=no_text)
    budget_check(db)
    key = load_gemini_key()
    try:
        # kind='weekly' | 'brief' — audita rinda (image_audit) top pašā
        # generate_image(); `brief_images` rinda zemāk paliek apstiprināšanas
        # darbplūsmai, izmaksas no tās vairs neskaita.
        png = generate_image(
            prompt_text, aspect_ratio="16:9",
            kind="weekly" if row["note_type"] == "weekly_brief" else "brief",
            db_path=args.db,
        )
    except Exception as e:  # noqa: BLE001 - any generation failure → audit row, no crash
        eid = save_error_row(db, args.note_id, prompt_text, key["model"], str(e))
        link_audit_row(db, brief_image_id=eid, prompt=prompt_text)
        print("RESULT_JSON:" + json.dumps({"status": "failed", "error": str(e), "row_id": eid}))
        return

    slug = _brief_slug(row["created_at"], row["note_type"], row["topic"])
    fname = compute_filename(slug, png)
    out_dir = Path("output/images/briefs")
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / fname
    out_path.write_bytes(png)

    # Izmēri no faktiskajiem baitiem — API nominālais platums (1408) nesakrīt
    # ar reāli atdoto (1376).
    png_w, png_h = Image.open(BytesIO(png)).size
    image_id = save_image_row(
        db, args.note_id, image_path=f"images/briefs/{fname}", prompt=prompt_text,
        model=key["model"], seed=None, width=png_w, height=png_h, cost=0.039, aspect="16:9",
    )
    # Zīmogo generate_image() audita rindu ar šo brief_images id — citādi
    # apply_migrations() backfill to neredz un pieliek otru (2026-09-15,
    # 13 dubultpāri septembrī; sk. storage.link_audit_row).
    link_audit_row(db, brief_image_id=image_id, prompt=prompt_text)
    print("RESULT_JSON:" + json.dumps(
        {"status": "pending_approval", "image_id": image_id,
         "path": str(out_path.resolve()), "fname": fname}, ensure_ascii=False))


def main(argv: list[str] | None = None) -> None:
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except (AttributeError, ValueError):
        pass
    args = build_parser().parse_args(argv)
    if args.cmd == "thread":
        _run_thread(args)
    elif args.cmd == "brief":
        _run_brief(args)


if __name__ == "__main__":
    main()
