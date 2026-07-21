"""CLI entry points: brainstorm, approve, skip, revise, resend."""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from src.db import DB_PATH, get_db
from src.social_agent.candidates import (
    fetch_pretrunas_candidates,
    fetch_stats_candidate,
    fetch_highlights_candidates,
    interest_score,
    select_top_n,
)
from src.social_agent.drafters import draft_pretrunas, draft_stats, draft_highlight
from src.social_agent.visuals import (
    render_chart, render_quote_card, render_illustration, render_pretruna_og_card,
)
from src.social_agent.storage import (
    create_draft,
    get_draft,
    mark_rejected,
    mark_posted,
    mark_failed,
    mark_revising,
    list_pending_drafts,
)
from src.social_agent.telegram import send_draft, parse_reply
from src.social_agent.publisher import publish_draft


DRAFTS_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "social" / "drafts"


def _topics_posted_last_7d(db_path: str) -> set[str]:
    db = get_db(db_path)
    rows = db.execute(
        """
        SELECT source_data_json FROM social_drafts
        WHERE status = 'posted'
          AND created_at >= datetime('now', '-7 days')
        """
    ).fetchall()
    db.close()
    out: set[str] = set()
    for r in rows:
        try:
            sd = json.loads(r["source_data_json"])
        except (TypeError, json.JSONDecodeError):
            continue
        t = sd.get("topic")
        if isinstance(t, str):
            out.add(t)
    return out


def _hours_since(ts_iso: str | None) -> float:
    if not ts_iso:
        return 9999.0
    try:
        t = datetime.fromisoformat(ts_iso.replace("T", " ").replace("Z", ""))
    except ValueError:
        return 9999.0
    # ts_iso from DB is naive (CURRENT_TIMESTAMP is UTC); treat as UTC
    t_aware = t.replace(tzinfo=timezone.utc)
    return max(0.0, (datetime.now(timezone.utc) - t_aware).total_seconds() / 3600.0)


def brainstorm_cmd(db_path: str | None = None) -> int:
    recent = _topics_posted_last_7d(db_path)

    pool: list[dict] = []

    # Pretrunas
    for r in fetch_pretrunas_candidates(db_path=db_path):
        score = interest_score(
            salience=float(r.get("salience") or 0.5),
            severity=r.get("severity"),
            age_hours=_hours_since(r.get("detected_at")),
            candidate_topics={r.get("topic", "")} if r.get("topic") else set(),
            recent_topics=recent,
        )
        pool.append({"pillar": "pretrunas", "score": score, "payload": r})

    # Stats (single-candidate pillar) — require ≥2 politicians for a meaningful leaderboard
    stats = fetch_stats_candidate(db_path=db_path)
    if stats is not None and len(stats.get("leaderboard", [])) >= 2:
        score = interest_score(
            salience=0.6, severity=None, age_hours=0,
            candidate_topics={"aktivitāte"}, recent_topics=recent,
        )
        pool.append({"pillar": "stats", "score": score, "payload": stats})

    # Highlights
    for r in fetch_highlights_candidates(db_path=db_path):
        score = interest_score(
            salience=0.6, severity=None,
            age_hours=_hours_since(r.get("created_at")),
            candidate_topics={r.get("topic", "")} if r.get("topic") else set(),
            recent_topics=recent,
        )
        pool.append({"pillar": "highlights", "score": score, "payload": r})

    picked = select_top_n(pool, n=3, per_pillar_cap=2)
    if not picked:
        print("[social_agent] No candidates — nothing to draft.")
        return 0

    DRAFTS_DIR.mkdir(parents=True, exist_ok=True)

    for entry in picked:
        pillar = entry["pillar"]
        payload = entry["payload"]

        # Render text + visual
        if pillar == "pretrunas":
            text = draft_pretrunas(payload)
            source_data = {
                "contradiction_id": payload["contradiction_id"],
                "topic": payload["topic"],
            }
            image_out = DRAFTS_DIR / f"draft_pending_{id(payload)}.png"
            # Primary: reuse the prerendered OG card from the public site build —
            # single source of truth for styling. Fallback to live quote_card
            # render if the site hasn't been generated (e.g., tests, or if the
            # contradiction is newer than the last site build).
            try:
                render_pretruna_og_card(
                    payload["contradiction_id"], out_path=image_out,
                )
                image_path = str(image_out)
            except FileNotFoundError as e:
                print(f"[social_agent] OG card missing, falling back to quote_card: {e}",
                      file=sys.stderr)
                try:
                    render_quote_card(
                        {
                            "politician_name": payload["politician_name"],
                            "topic": payload["topic"],
                            "old_quote": payload.get("old_quote") or payload.get("old_stance") or "",
                            "old_date": (payload.get("old_stated_at") or "")[:10],
                            "new_quote": payload.get("new_quote") or payload.get("new_stance") or "",
                            "new_date": (payload.get("new_stated_at") or "")[:10],
                        },
                        out_path=image_out,
                    )
                    image_path = str(image_out)
                except Exception as e2:
                    print(f"[social_agent] quote_card fallback failed: {e2}", file=sys.stderr)
                    image_path = None
            except Exception as e:
                print(f"[social_agent] OG card copy failed: {e}", file=sys.stderr)
                image_path = None
        elif pillar == "stats":
            text = draft_stats(payload)
            source_data = {"iso_week": payload["iso_week"], "topic": "aktivitāte"}
            image_out = DRAFTS_DIR / f"draft_pending_stats_{payload['iso_week']}.png"
            try:
                render_chart(payload, out_path=image_out)
                image_path = str(image_out)
            except Exception as e:
                print(f"[social_agent] chart failed: {e}", file=sys.stderr)
                image_path = None
        else:  # highlights
            text = draft_highlight(payload)
            if payload.get("kind") == "attack":
                source_data = {
                    "kind": "attack",
                    "brief_id": payload["brief_id"],
                    "attack_index": payload["attack_index"],
                    "topic": None,
                }
            else:
                source_data = {
                    "kind": "tension",
                    "tension_id": payload["tension_id"],
                    "topic": payload.get("topic"),
                }
            # Highlights default to illustration; skip if unavailable
            image_out = DRAFTS_DIR / f"draft_pending_hl_{id(payload)}.png"
            try:
                subject = payload.get("topic") or "politiska spriedze"
                render_illustration({"subject": subject}, out_path=image_out)
                image_path = str(image_out)
            except Exception as e:
                print(f"[social_agent] illustration failed: {e}", file=sys.stderr)
                image_path = None

        # Persist + send
        draft_id = create_draft(
            pillar=pillar,
            text=text,
            image_path=image_path,
            source_data=source_data,
            score=entry["score"],
            db_path=db_path,
        )
        # Rename the pending image file to its canonical draft_<id>.png
        if image_path:
            canonical = DRAFTS_DIR / f"draft_{draft_id}.png"
            try:
                Path(image_path).replace(canonical)
                db = get_db(db_path)
                db.execute(
                    "UPDATE social_drafts SET image_path = ? WHERE id = ?",
                    (str(canonical), draft_id),
                )
                db.commit()
                db.close()
                image_path = str(canonical)
            except OSError:
                pass

        try:
            msg_id = send_draft(
                draft_id=draft_id, pillar=pillar, text=text, image_path=image_path
            )
            db = get_db(db_path)
            db.execute(
                "UPDATE social_drafts SET telegram_msg_id = ? WHERE id = ?",
                (msg_id, draft_id),
            )
            db.commit()
            db.close()
            print(f"[social_agent] Sent draft #{draft_id} ({pillar}) score={entry['score']:.2f}")
        except Exception as e:
            print(f"[social_agent] Telegram send failed for #{draft_id}: {e}", file=sys.stderr)

    return 0


def llm_rewrite(original_text: str, instruction: str) -> str:
    """Regenerate a draft using the provided free-text instruction.

    MVP: minimal heuristic fallback — if the instruction includes "īs" (shorter)
    return the first sentence; if "bez emoji" strip common emoji chars; otherwise
    just prepend the instruction marker. A proper LLM call (Claude API) can replace
    this later — keeping the interface stable.
    """
    import re

    txt = original_text
    if "īs" in instruction.lower() or "short" in instruction.lower():
        parts = re.split(r"(?<=[.!?])\s+", txt)
        if parts:
            txt = parts[0]
    if "bez emoji" in instruction.lower() or "no emoji" in instruction.lower():
        txt = re.sub(r"[\U0001F300-\U0001FAFF\U00002600-\U000027BF]", "", txt)
    return txt.strip()[:280]


def approve_cmd(draft_id: int, db_path: str | None = None) -> int:
    draft = get_draft(draft_id, db_path=db_path)
    if draft is None:
        print(f"[social_agent] No draft #{draft_id}", file=sys.stderr)
        return 2
    if draft["status"] != "pending":
        print(f"[social_agent] Draft #{draft_id} is {draft['status']}, not pending",
              file=sys.stderr)
        return 3
    try:
        tweet_id = publish_draft(text=draft["text"], image_path=draft["image_path"])
    except Exception as e:
        mark_failed(draft_id, error_message=str(e), db_path=db_path)
        print(f"[social_agent] Publish failed: {e}", file=sys.stderr)
        return 1
    mark_posted(draft_id, tweet_id=tweet_id, db_path=db_path)
    print(f"[social_agent] Posted draft #{draft_id} → tweet {tweet_id}")
    return 0


def skip_cmd(draft_id: int, db_path: str | None = None) -> int:
    draft = get_draft(draft_id, db_path=db_path)
    if draft is None:
        print(f"[social_agent] No draft #{draft_id}", file=sys.stderr)
        return 2
    mark_rejected(draft_id, db_path=db_path)
    print(f"[social_agent] Skipped draft #{draft_id}")
    return 0


def revise_cmd(draft_id: int, instruction: str, db_path: str | None = None) -> int:
    draft = get_draft(draft_id, db_path=db_path)
    if draft is None:
        print(f"[social_agent] No draft #{draft_id}", file=sys.stderr)
        return 2
    new_text = llm_rewrite(draft["text"], instruction)
    child_id = mark_revising(draft_id, new_text=new_text, db_path=db_path)
    child = get_draft(child_id, db_path=db_path)
    try:
        msg_id = send_draft(
            draft_id=child_id, pillar=child["pillar"],
            text=child["text"], image_path=child["image_path"],
        )
        db = get_db(db_path)
        db.execute(
            "UPDATE social_drafts SET telegram_msg_id = ? WHERE id = ?",
            (msg_id, child_id),
        )
        db.commit()
        db.close()
    except Exception as e:
        print(f"[social_agent] Telegram send of revised draft failed: {e}",
              file=sys.stderr)
        return 1
    print(f"[social_agent] Revised draft #{draft_id} → new draft #{child_id}")
    return 0


def resend_cmd(draft_id: int, db_path: str | None = None) -> int:
    draft = get_draft(draft_id, db_path=db_path)
    if draft is None:
        print(f"[social_agent] No draft #{draft_id}", file=sys.stderr)
        return 2
    try:
        msg_id = send_draft(
            draft_id=draft_id, pillar=draft["pillar"],
            text=draft["text"], image_path=draft["image_path"],
        )
    except Exception as e:
        print(f"[social_agent] Resend failed: {e}", file=sys.stderr)
        return 1
    db = get_db(db_path)
    db.execute(
        "UPDATE social_drafts SET telegram_msg_id = ? WHERE id = ?",
        (msg_id, draft_id),
    )
    db.commit()
    db.close()
    print(f"[social_agent] Resent draft #{draft_id} (msg {msg_id})")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="social_agent", description="X posting agent")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("brainstorm", help="Select top-3 candidates and send drafts to Telegram")

    p_approve = sub.add_parser("approve", help="Post an approved draft to X")
    p_approve.add_argument("draft_id", type=int)

    p_skip = sub.add_parser("skip", help="Reject a draft without posting")
    p_skip.add_argument("draft_id", type=int)

    p_rev = sub.add_parser("revise", help="Regenerate a draft with an instruction")
    p_rev.add_argument("draft_id", type=int)
    p_rev.add_argument("instruction", nargs="+")

    p_rs = sub.add_parser("resend", help="Re-send an existing draft to Telegram")
    p_rs.add_argument("draft_id", type=int)

    args = parser.parse_args(argv)

    if args.command == "brainstorm":
        return brainstorm_cmd()
    if args.command == "approve":
        return approve_cmd(args.draft_id)
    if args.command == "skip":
        return skip_cmd(args.draft_id)
    if args.command == "revise":
        return revise_cmd(args.draft_id, instruction=" ".join(args.instruction))
    if args.command == "resend":
        return resend_cmd(args.draft_id)
    return 2
