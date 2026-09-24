"""NEEDS_REVIEW triāža 2026-09-23 — 69 atzīmes pēc `quote=null` griestu maiņas.

Operatora lēmums 2026-09-23 (CHANGELOG 2026-09-23 (6)): skaidrs atstāsts bez
citāta = 0.65 bez karodziņa; karodziņš tikai nosauktām šaubām. Katru atzīmi
četri `@claim-extractor` lasītāji salīdzināja ar avota dokumentu un atdeva
spriedumu (clear / ok_doubt / fix / delete); spriedumi dzīvo
`docs/audits/2026-09-23-needs-review-triage/verdicts.json`.

Lietojums (no repo saknes):
    .venv/Scripts/python.exe scripts/fix_needs_review_triage_2026-09-23.py           # sauss
    .venv/Scripts/python.exe scripts/fix_needs_review_triage_2026-09-23.py --apply   # raksta

--apply vispirms uzraksta rollback (UPDATE visām rindām + pilns INSERT dzēstajām),
tad vienā transakcijā maina DB. Pēc tam: scripts/reembed_claims.py tām rindām,
kurām mainījās stance vai topic (saraksts `.reembed.ids`).
"""
from __future__ import annotations

import json
import sqlite3
import sys
from pathlib import Path

import sqlite_vec

ROOT = Path(__file__).resolve().parent.parent
DB_PATH = ROOT / "data" / "atmina.db"
VERDICTS = ROOT / "docs" / "audits" / "2026-09-23-needs-review-triage" / "verdicts.json"
ROLLBACK = ROOT / "data" / "rollback_needs_review_triage_2026-09-23.sql"
REEMBED_IDS = ROOT / "data" / "rollback_needs_review_triage_2026-09-23.reembed.ids"

COLS = ["id", "opponent_id", "document_id", "topic", "stance", "quote", "confidence",
        "reasoning", "salience", "source_url", "stated_at", "created_at", "claim_type",
        "speaker_id", "party_id"]
CLEAR_CONF = 0.65


def sql_lit(v):
    if v is None:
        return "NULL"
    if isinstance(v, (int, float)):
        return repr(v)
    return "'" + str(v).replace("'", "''") + "'"


def resolved_reasoning(old: str, verdict: str, note: str) -> str:
    # Trigeris klasificē `needs_review`, ja marķieris ir JEBKUR tekstā, tāpēc
    # vecos marķierus aizstāj visus, nevis tikai prefiksu.
    tail = (old or "").replace("NEEDS_REVIEW:", "[bij. karodziņš]").replace(
        "NEEDS_REVIEW", "[bij. karodziņš]")
    return f"Izvērtēts 2026-09-23 (NR triāža, {verdict}): {note} | Iepriekš: {tail}"


def main(apply: bool) -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    verdicts = json.loads(VERDICTS.read_text(encoding="utf-8"))
    by_id = {v["id"]: v for v in verdicts}
    if len(by_id) != len(verdicts):
        raise SystemExit("STOP: dublēti id spriedumos")

    db = sqlite3.connect(DB_PATH)
    db.enable_load_extension(True)
    sqlite_vec.load(db)
    flagged = {r[0] for r in db.execute("SELECT id FROM claims WHERE review_status='needs_review'")}
    ids = sorted(by_id)
    rows = {r[0]: r for r in db.execute(
        f"SELECT {', '.join(COLS)} FROM claims WHERE id IN ({','.join('?' * len(ids))})", ids)}
    missing = [i for i in ids if i not in rows]
    not_flagged = [i for i in ids if i not in flagged]
    if missing or not_flagged:
        raise SystemExit(f"STOP: trūkst {missing}, nav karogoti {not_flagged}")

    delete = [i for i in ids if by_id[i]["verdict"] == "delete"]
    refs = db.execute(
        f"SELECT COUNT(*) FROM contradictions WHERE claim_old_id IN ({','.join('?' * len(delete))})"
        f" OR claim_new_id IN ({','.join('?' * len(delete))})", delete + delete).fetchone()[0] if delete else 0
    if refs:
        raise SystemExit(f"STOP: {refs} pretrunas atsaucas uz dzēšamajām rindām")

    updates: dict[int, dict] = {}
    reembed: list[int] = []
    for i in ids:
        v = by_id[i]
        if v["verdict"] == "delete":
            continue
        r = dict(zip(COLS, rows[i]))
        ch = {"reasoning": resolved_reasoning(r["reasoning"], v["verdict"], v["note"])}
        if v["verdict"] == "clear":
            ch["confidence"] = max(CLEAR_CONF, r["confidence"] or 0) if r["quote"] else CLEAR_CONF
        if v.get("new_confidence") is not None:
            ch["confidence"] = v["new_confidence"]
        if v["verdict"] == "fix":
            if v.get("new_stance"):
                ch["stance"] = v["new_stance"]
            if v.get("new_quote") is not None:
                ch["quote"] = v["new_quote"] or None
            if v.get("new_topic"):
                ch["topic"] = v["new_topic"]
        if ("quote" not in ch and not r["quote"] or "quote" in ch and ch["quote"] is None) \
                and ch.get("confidence", r["confidence"]) > CLEAR_CONF:
            raise SystemExit(f"STOP: #{i} quote=null, bet confidence > {CLEAR_CONF}")
        if "stance" in ch or "topic" in ch:
            reembed.append(i)
        updates[i] = ch

    # Idempotences atslēga (opponent_id, source_url, topic) — tēmas maiņa nedrīkst radīt dublikātu.
    for i, ch in updates.items():
        if "topic" in ch:
            r = dict(zip(COLS, rows[i]))
            hit = db.execute("SELECT id FROM claims WHERE opponent_id=? AND source_url=? AND topic=? AND id<>?",
                             (r["opponent_id"], r["source_url"], ch["topic"], i)).fetchone()
            if hit:
                raise SystemExit(f"STOP: #{i} tēmas maiņa sadurtos ar #{hit[0]}")

    from collections import Counter
    print(f"examined={len(ids)} (karogoti DB: {len(flagged)}) spriedumi={dict(Counter(v['verdict'] for v in verdicts))}")
    for i in delete:
        print(f"  DEL #{i}: {by_id[i]['note']}")
    for i, ch in updates.items():
        if by_id[i]["verdict"] == "fix":
            print(f"  FIX #{i}: {', '.join(k for k in ch if k != 'reasoning')}")
    if not apply:
        print("sauss skrējiens — nekas nav rakstīts")
        return

    lines = [
        "-- Rollback: scripts/fix_needs_review_triage_2026-09-23.py (piemērots 2026-09-23)",
        f"-- Atjauno {len(updates)} izvērtēto rindu topic/stance/quote/confidence/reasoning un {len(delete)} dzēstās rindas.",
        "-- PĒC TAM: .venv/Scripts/python.exe scripts/reembed_claims.py --ids-from "
        "data/rollback_needs_review_triage_2026-09-23.reembed.ids (+ dzēsto id, ja atjauno).",
        "BEGIN;",
    ]
    for i in delete:
        lines.append(f"INSERT INTO claims ({', '.join(COLS)}) VALUES ({', '.join(sql_lit(x) for x in rows[i])});")
    for i in updates:
        r = dict(zip(COLS, rows[i]))
        lines.append(
            f"UPDATE claims SET topic={sql_lit(r['topic'])}, stance={sql_lit(r['stance'])}, "
            f"quote={sql_lit(r['quote'])}, confidence={sql_lit(r['confidence'])}, "
            f"reasoning={sql_lit(r['reasoning'])} WHERE id={i};")
    lines.append("COMMIT;")
    ROLLBACK.write_text("\n".join(lines) + "\n", encoding="utf-8")
    REEMBED_IDS.write_text("\n".join(str(i) for i in reembed + delete) + "\n", encoding="utf-8")
    print(f"rollback -> {ROLLBACK.relative_to(ROOT)}; reembed ids: {len(reembed)}")

    with db:
        for i in delete:
            db.execute("DELETE FROM claim_vectors WHERE claim_id = ?", (i,))
            db.execute("DELETE FROM claims WHERE id = ?", (i,))
        for i, ch in updates.items():
            sets = ", ".join(f"{k} = ?" for k in ch)
            db.execute(f"UPDATE claims SET {sets} WHERE id = ?", (*ch.values(), i))

    left = db.execute(f"SELECT COUNT(*) FROM claims WHERE id IN ({','.join('?' * len(ids))}) "
                      "AND review_status = 'needs_review'", ids).fetchone()[0]
    gone = db.execute(f"SELECT COUNT(*) FROM claims WHERE id IN ({','.join('?' * len(delete))})",
                      delete).fetchone()[0] if delete else 0
    reviewed = db.execute(f"SELECT COUNT(*) FROM claims WHERE id IN ({','.join('?' * len(ids))}) "
                          "AND review_status = 'reviewed'", ids).fetchone()[0]
    print(f"needs_review palika={left} (jābūt 0), dzēstās palika={gone} (jābūt 0), "
          f"reviewed={reviewed}/{len(updates)}")
    if left or gone or reviewed != len(updates):
        raise SystemExit("verifikācija neizdevās")


if __name__ == "__main__":
    main("--apply" in sys.argv)
