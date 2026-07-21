"""atmina image CLI — `python -m src.graphics.cli {brief,thread}`.

Replaces the per-day throwaway image scripts with two committed subcommands:

- ``brief --note-id N``   : faithful parameterization of the brief poster
  pipeline (build_prompt + storage audit + budget + approval gate). Mirrors what
  the old generate_brief_image_<N>.py clones did, without a new file per day.
- ``thread --date D --prompts thread.json`` : sepia, text-free thread
  illustrations via the canonical SEPIA_STYLE (lightweight, no DB).

The @graphics-designer agent still authors metaphors/prompts; this CLI only
removes the boilerplate. See docs/superpowers/specs/2026-06-08-image-thread-cli-design.md.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from src.graphics.prompt import DEFAULT_STYLE
from src.graphics.thread import generate_thread


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(prog="python -m src.graphics.cli", description="atmina image CLI")
    sub = ap.add_subparsers(dest="cmd", required=True)

    b = sub.add_parser("brief", help="Brief poster (Economist style, headline rendered)")
    b.add_argument("--note-id", type=int, required=True, dest="note_id")
    b.add_argument("--metaphor", default=None, help="Override metaphor (else generic visual_map)")
    b.add_argument("--mood", default=None)
    b.add_argument("--accent", default=None)
    # Default None → style is resolved from note_type (weekly_brief → "weekly"),
    # an explicit --style still wins. See _resolve_style.
    b.add_argument("--style", default=None)
    b.add_argument("--db", default="data/atmina.db")

    t = sub.add_parser("thread", help="Sepia text-free thread illustrations")
    t.add_argument("--date", required=True, help="YYYY-MM-DD (filename prefix)")
    t.add_argument("--prompts", required=True, help="JSON file {suffix: base_prompt}")
    t.add_argument("--out", default="output/images/threads")

    return ap


def _brief_slug(created_at: str, note_type: str) -> str:
    """Filename slug for a brief poster, keyed on note_type.

    weekly_brief → ``<date>-nedelas-parskats``; everything else (daily) →
    ``<date>-dienas-parskats``. The date is the first 10 chars of created_at.
    """
    kind = "nedelas-parskats" if note_type == "weekly_brief" else "dienas-parskats"
    return f"{created_at[:10]}-{kind}"


def _resolve_style(explicit_style: str | None, note_type: str) -> str:
    """Pick the prompt style. An explicit --style always wins; otherwise a
    weekly_brief uses the ink-navy ``weekly`` frame and daily uses DEFAULT_STYLE.
    """
    if explicit_style is not None:
        return explicit_style
    return "weekly" if note_type == "weekly_brief" else DEFAULT_STYLE


def _run_thread(args) -> None:
    data = json.loads(Path(args.prompts).read_text(encoding="utf-8"))
    if not isinstance(data, dict) or not data:
        raise SystemExit("thread --prompts must be a non-empty JSON object {suffix: prompt}")
    written = generate_thread(args.date, data, args.out)
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
        save_error_row,
        save_image_row,
    )
    from src.graphics.visual_map import get_visual

    db = get_db(args.db)
    row = db.execute(
        "SELECT visual_brief_json, created_at, note_type FROM context_notes WHERE id=?",
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
    prompt_text = build_prompt(visual_brief, vm, style_key=style_key)
    budget_check(db)
    key = load_gemini_key()
    try:
        png = generate_image(prompt_text, aspect_ratio="16:9")
    except Exception as e:  # noqa: BLE001 - any generation failure → audit row, no crash
        eid = save_error_row(db, args.note_id, prompt_text, key["model"], str(e))
        print("RESULT_JSON:" + json.dumps({"status": "failed", "error": str(e), "row_id": eid}))
        return

    slug = _brief_slug(row["created_at"], row["note_type"])
    fname = compute_filename(slug, png)
    out_dir = Path("output/images/briefs")
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / fname
    out_path.write_bytes(png)

    image_id = save_image_row(
        db, args.note_id, image_path=f"images/briefs/{fname}", prompt=prompt_text,
        model=key["model"], seed=None, width=1408, height=768, cost=0.039, aspect="16:9",
    )
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
