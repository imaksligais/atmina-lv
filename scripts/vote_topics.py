"""Saeimas balsojumu tēmu partiju dzinējs (spec 2026-10-21-saeimas-balsojumu-temas).

Vienīgais ceļš, kā mainīt `saeima_votes.topic` / `claims.topic` (saeima_vote):
lēmums dokumentam → iesaldēta partija (snapshot) → komitēts rollback fails →
piemērošana vienā transakcijā. Loģika dzīvo `src/saeima/topics.py`.

Lietošana:
    .venv/Scripts/python.exe scripts/vote_topics.py status
    .venv/Scripts/python.exe scripts/vote_topics.py decide 412/Lp14 Tieslietas
    .venv/Scripts/python.exe scripts/vote_topics.py freeze b01 --keys-file keys.txt
    git add data/rollback_vote_topics_b01.sql && git commit ...   # eskalācija 8
    .venv/Scripts/python.exe scripts/vote_topics.py apply b01
    .venv/Scripts/python.exe scripts/vote_topics.py rollback b01
    .venv/Scripts/python.exe scripts/vote_topics.py abandon b01   # tikai nepiemērotai
    .venv/Scripts/python.exe scripts/vote_topics.py plan --size 300   # partiju saraksts (tikai lasa)
    .venv/Scripts/python.exe scripts/vote_topics.py classify b01      # 9. uzd. 1. solis (Jev)
    .venv/Scripts/python.exe scripts/vote_topics.py review-list b01   # 9. uzd. 2. solis → CSV
    .venv/Scripts/python.exe scripts/vote_topics.py bills-sync s01 --keys-file keys.txt
    git add data/rollback_bill_topics_s01.sql && git commit ...   # eskalācija 8
    .venv/Scripts/python.exe scripts/vote_topics.py bills-apply s01
    .venv/Scripts/python.exe scripts/vote_topics.py bills-rollback s01

`--db` pēc noklusējuma ir ražošanas DB (`src.db.PRODUCTION_DB_PATH` pret repo sakni).
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from collections import Counter
from pathlib import Path

_REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_REPO))

from src.db import PRODUCTION_DB_PATH, get_db  # noqa: E402
from src.saeima.schema import init_saeima_tables  # noqa: E402
from src.saeima.topics import (  # noqa: E402
    abandon_batch,
    apply_batch,
    apply_bill_sync,
    current_decision,
    document_key,
    freeze_batch,
    plan_batches,
    record_decision,
    rollback_batch,
    rollback_bill_sync,
    sync_bill_topics,
    write_rollback_sql,
)
from src.saeima.topics import (  # noqa: E402
    BATCH_CONFIDENCE_THRESHOLD,
    JEV_CHUNK_SIZE,
    JEV_MODEL,
    _keyword_topic,
    current_vote_topic,
    document_title,
    rule_topic,
)
from src.topic_map import TOPIC_GROUPS  # noqa: E402

GOLD_DIR = _REPO / "data" / "saeima_topic_gold"
# Plāna 9. uzd. 2. solis: pārskata arī AUTOMĀTISKOS lēmumus, kas maina tēmu un kuru
# pārliecība < 0,9 (plāna burtiskais skaitlis; ne INGEST_CONFIDENCE_THRESHOLD — var atšķirties).
REVIEW_CONFIDENCE_CUTOFF = 0.9
REVIEW_COLUMNS = ["document_key", "current_topic", "jev_topic", "confidence", "reason",
                  "title", "url"]


def _err(msg: str) -> int:
    print(f"KĻŪDA: {msg}", file=sys.stderr)
    return 1


def cmd_status(db, args) -> int:
    print("Partijas pa statusiem:")
    for status, n in db.execute("SELECT status, count(*) FROM vote_topic_batches"
                                " GROUP BY status ORDER BY status"):
        print(f"  {status}: {n}")
    for bid, status, applied in db.execute("SELECT batch_id, status, applied_at FROM"
                                           " vote_topic_batches ORDER BY created_at, batch_id"):
        print(f"  - {bid}: {status}" + (f" ({applied})" if applied else ""))
    keys: Counter = Counter()
    unresolved = 0
    for nr, motif in db.execute("SELECT document_nr, motif FROM saeima_votes"):
        k, _ = document_key(nr, motif)
        if k is None:
            unresolved += 1
        else:
            keys[k] += 1
    decided = pending = 0
    for k in keys:
        d = current_decision(db, k)
        if d is not None:
            decided += 1
            pending += d["review_status"] == "pending"
    print(f"Dokumenti: {len(keys)} (ar lēmumu {decided}, bez lēmuma {len(keys) - decided},"
          f" pending {pending})")
    print(f"Balsojumi ar neatrisinātu kailu numuru (bez atslēgas): {unresolved}")
    return 0


def cmd_decide(db, args) -> int:
    if args.topic not in TOPIC_GROUPS:
        return _err(f"nekanoniska tēma {args.topic!r}; derīgās: {', '.join(TOPIC_GROUPS)}")
    n = sum(1 for nr, motif in db.execute("SELECT document_nr, motif FROM saeima_votes")
            if document_key(nr, motif)[0] == args.key)
    if n == 0:
        return _err(f"atslēgai {args.key!r} nav neviena balsojuma")
    rid = record_decision(db, args.key, args.topic, method="human", model=None,
                          confidence=1.0, input_hash="manual", review_status="confirmed")
    print(f"Lēmums #{rid}: {args.key} → {args.topic} ({n} balsojumi)")
    return 0


def _read_keys(path) -> list[str]:
    return [ln.strip() for ln in Path(path).read_text(encoding="utf-8").splitlines()
            if ln.strip() and not ln.lstrip().startswith("#")]


def cmd_freeze(db, args) -> int:
    keys = _read_keys(args.keys_file)
    try:
        out = freeze_batch(db, args.batch_id, keys, allow_pending=args.allow_pending)
    except (ValueError, RuntimeError) as e:
        return _err(str(e))
    print(json.dumps(out, ensure_ascii=False))
    if out["pending"]:
        print(f"BRĪDINĀJUMS: {out['pending']} atslēgām lēmums ir 'pending' (--allow-pending)",
              file=sys.stderr)
    try:
        path = write_rollback_sql(
            db, args.batch_id, Path(args.rollback_dir) / f"rollback_vote_topics_{args.batch_id}.sql")
    except (OSError, ValueError, RuntimeError) as e:
        return _err(f"partija {args.batch_id} iesaldēta, bet rollback failu uzrakstīt neizdevās:"
                    f" {e}\nTā bloķē pārklājošās partijas. Pamet to un iesaldē no jauna ar"
                    f" citu batch_id:\n  scripts/vote_topics.py abandon {args.batch_id}")
    print(f"Rollback fails: {path}")
    print("Pirms `apply` komitē rollback failu (eskalācija 8).")
    return 0


def cmd_apply(db, args) -> int:
    if not args.require_tracked:
        print("BRĪDINĀJUMS: --no-require-tracked — rollback faila komitēšanu NEPĀRBAUDA "
              "(eskalācija 8). Tikai DB kopijām un testiem!", file=sys.stderr)
    try:
        report = apply_batch(db, args.batch_id, require_tracked=args.require_tracked)
    except (ValueError, RuntimeError) as e:
        return _err(str(e))
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if report["parity_mismatch_global"]:
        print(f"BRĪDINĀJUMS: parity_mismatch_global={report['parity_mismatch_global']} "
              "(visā DB, ne tikai šajā partijā)", file=sys.stderr)
    if report["parity_mismatch"]:
        return _err(f"parity_mismatch={report['parity_mismatch']} (šajā partijā)")
    return 0


def cmd_rollback(db, args) -> int:
    try:
        out = rollback_batch(db, args.batch_id)
    except (ValueError, RuntimeError) as e:
        return _err(str(e))
    print(json.dumps(out, ensure_ascii=False))
    return 0


def cmd_abandon(db, args) -> int:
    try:
        abandon_batch(db, args.batch_id)
    except (ValueError, RuntimeError) as e:
        return _err(str(e))
    print(f"Partija {args.batch_id} pamesta (snapshot rindas paliek).")
    return 0


def cmd_plan(db, args) -> int:
    try:
        rows, info = plan_batches(db, args.size)
    except ValueError as e:
        return _err(str(e))
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh, lineterminator="\n")
        w.writerow(["batch_id", "document_key"])
        w.writerows(rows)
    docs = Counter(b for b, _ in rows)
    print(f"Dokumenti ar atslēgu: {info['documents']}; plānā {info['planned']};"
          f" partijas {len(docs)} → {out}")
    for bid in sorted(docs):
        print(f"  {bid}: {docs[bid]} dokumenti, {info['votes_per_batch'][bid]} balsojumi")
    ex = info["excluded_budget"]
    print(f"Izslēgti budžeta likumi (backlog/saeima.md, operatora noklusējums): {len(ex)},"
          f" {sum(ex.values())} balsojumi: " + ", ".join(f"{k} ({n})" for k, n in ex.items()))
    print(f"`multi` atslēgas plānā (lēmums tikai ar roku): {info['multi_keys']};"
          f" balsojumi bez atslēgas (plānā nav): {info['unresolved_votes']}")
    return 0


def _batch_keys(path, batch_id) -> list[str]:
    with open(path, encoding="utf-8", newline="") as fh:
        return [r["document_key"] for r in csv.DictReader(fh) if r["batch_id"] == batch_id]


def _key_votes(db, keys) -> dict[str, dict]:
    """Katrai atslēgai: balsojumi [(id, topic)], pirmā balsojuma motīvs/URL, vai `multi`."""
    wanted = set(keys)
    out: dict[str, dict] = {}
    for vid, nr, motif, topic, url in db.execute(
            "SELECT id, document_nr, motif, topic, url FROM saeima_votes ORDER BY id"):
        k, reason = document_key(nr, motif or "")
        if k not in wanted:
            continue
        d = out.setdefault(k, {"votes": [], "motif": motif or "", "url": url,
                               "multi": False, "motifs": set()})
        d["votes"].append((vid, topic))
        d["multi"] |= reason == "multi"
        d["motifs"].add((motif or "").strip())
    return out


def cmd_classify(db, args) -> int:
    """9. uzd. 1. solis: Jev partijas dokumentiem bez lēmuma (viens dokuments pieprasījumā, `JEV_CHUNK_SIZE`)."""
    from scripts.vote_topic_gold_sample import build_doc, load
    from src.jev_filter import JevStats
    from src.saeima import topic_classifiers as tc

    keys = _batch_keys(args.batches, args.batch_id)
    if not keys:
        return _err(f"partijai {args.batch_id!r} failā {args.batches} nav atslēgu")
    info = _key_votes(db, keys)
    missing = [k for k in keys if k not in info]
    if missing:
        return _err(f"{len(missing)} atslēgām DB nav balsojumu: {', '.join(missing[:10])}")
    todo = [k for k in keys if current_decision(db, k) is None]
    votes, _, _, bills_by_nr, bills_by_id = load(db)
    rows, multi, ruled = [], [], []
    for k in todo:
        topics = {rule_topic(m) for m in info[k]["motifs"]}
        if info[k]["multi"]:
            multi.append(k)
        elif len(topics) == 1 and None not in topics:  # visiem motīviem tas pats noteikums
            ruled.append((k, topics.pop()))
        else:
            # Tā pati `input_text` forma kā zelta izlasei (slieksnis mērīts uz tās).
            rows.append(build_doc(k, votes[k], bills_by_nr, bills_by_id))
    stats = JevStats()
    preds = tc.classify_jev([{"input_text": r["input_text"], "input_hash": r["input_hash"]}
                             for r in rows], model=JEV_MODEL, batch_size=JEV_CHUNK_SIZE,
                            stats=stats) if rows else []
    n = {"auto": 0, "low": 0, "none": 0, "changed": 0, "changed_lt": 0}
    for r, pred in zip(rows, preds, strict=True):
        k = r["document_key"]
        if pred is not None and pred.confidence is not None \
                and pred.confidence >= args.threshold:
            record_decision(db, k, pred.topic, method="jev", model=pred.model,
                            confidence=pred.confidence, input_hash=r["input_hash"])
            n["auto"] += 1
            if pred.topic != current_vote_topic(info[k]["votes"]):
                n["changed"] += 1
                n["changed_lt"] += pred.confidence < REVIEW_CONFIDENCE_CUTOFF
        else:
            # Kā ielādē (plāna 8. uzd., spec § Lēmumi 6): tēma no atslēgvārdiem, `pending`;
            # Jev ieteikums paliek kešā — `review-list` to nolasa pēc `input_hash`.
            n["low" if pred is not None else "none"] += 1
            record_decision(db, k, _keyword_topic(r["input_text"], info[k]["motif"]),
                            method="keyword", model=None, confidence=None,
                            input_hash=r["input_hash"], review_status="pending")
    for k in multi:  # klasifikatoru nesauc — lēmums tikai ar roku
        record_decision(db, k, _keyword_topic("", info[k]["motif"]), method="keyword",
                        model=None, confidence=None, input_hash="multi",
                        review_status="pending")
    for k, topic in ruled:  # tas pats noteikums kā topic_for_new_vote
        record_decision(db, k, topic, method="keyword", model=None,
                        confidence=None, input_hash="rule")
    decided = len(rows) + len(multi) + len(ruled)
    pending = n["low"] + n["none"] + len(multi)
    print(f"Partija {args.batch_id}: {len(keys)} dokumenti, jau ar lēmumu {len(keys) - len(todo)},"
          f" jauni lēmumi {decided} (slieksnis {args.threshold}, modelis {JEV_MODEL})")
    print(f"  auto (Jev ≥ {args.threshold}): {n['auto']}; no tiem tēma ≠ pašreizējā"
          f" {n['changed']}, no tiem pārliecība < {REVIEW_CONFIDENCE_CUTOFF}: {n['changed_lt']}")
    print(f"  pending: {pending} (zem sliekšņa {n['low']}, bez Jev atbildes {n['none']},"
          f" multi {len(multi)})")
    print(f"  noteikums (klātbūtnes reģistrācija, kārtības rullis; auto, bez zvana): {len(ruled)}")
    print(f"  {stats.summary()}")
    return 0


def select_review_rows(docs: list[dict], cutoff: float = REVIEW_CONFIDENCE_CUTOFF) -> list[dict]:
    """Plāna 9. uzd. 2. solis: ko izlasīt ar roku (tīrā loģika).

    Katrai `docs` vārdnīcai: document_key, current_topic, topic (lēmuma), review_status,
    confidence, multi. Atlasa `multi`, jebkuru `pending` un automātisku Jev lēmumu, kura
    tēma ≠ pašreizējā UN pārliecība < `cutoff`. Nekad: cilvēka `confirmed` un noteikuma
    lēmumu bez pārliecības (`rule_topic`: klātbūtnes reģistrācija, kārtības rullis).
    """
    out = []
    for d in docs:
        if d["review_status"] == "confirmed":
            continue
        if d["multi"]:
            reason = "multi: vairāki dokumentu numuri"
        elif d["review_status"] == "pending":
            reason = "pending"
        elif (d["topic"] != d["current_topic"] and d["confidence"] is not None
              and d["confidence"] < cutoff):
            reason = f"mainīta tēma, pārliecība < {cutoff}"
        else:
            continue
        out.append({**d, "reason": reason})
    return out


def cmd_review_list(db, args) -> int:
    from src.saeima import topic_classifiers as tc

    keys = _batch_keys(args.batches, args.batch_id)
    if not keys:
        return _err(f"partijai {args.batch_id!r} failā {args.batches} nav atslēgu")
    info = _key_votes(db, keys)
    docs, undecided = [], 0
    for k in keys:
        dec = current_decision(db, k)
        if dec is None or k not in info:
            undecided += 1
            continue
        jev = None
        if dec["method"] == "jev":
            jev = (dec["topic"], dec["confidence"])
        elif dec["review_status"] == "pending" and not info[k]["multi"]:
            p = tc.cached_prediction(dec["input_hash"], JEV_MODEL, JEV_CHUNK_SIZE)
            jev = (p.topic, p.confidence) if p else None
        docs.append({"document_key": k, "current_topic": current_vote_topic(info[k]["votes"]),
                     "topic": dec["topic"], "review_status": dec["review_status"],
                     "confidence": dec["confidence"], "multi": info[k]["multi"], "jev": jev,
                     "title": document_title(info[k]["motif"], k), "url": info[k]["url"]})
    picked = select_review_rows(docs)
    out = Path(args.out or GOLD_DIR / f"review_{args.batch_id}.csv")
    out.parent.mkdir(parents=True, exist_ok=True)
    no_hint = 0
    with open(out, "w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh, lineterminator="\n")
        w.writerow(REVIEW_COLUMNS)
        for d in picked:
            no_hint += d["jev"] is None and not d["multi"]
            jt, jc = d["jev"] or ("", None)
            w.writerow([d["document_key"], d["current_topic"], jt,
                        "" if jc is None else f"{jc:.3f}", d["reason"], d["title"], d["url"]])
    print(f"Partija {args.batch_id}: {len(keys)} dokumenti, ar lēmumu {len(docs)},"
          f" bez lēmuma {undecided}; pārskatāmi {len(picked)} → {out}")
    for reason, c in sorted(Counter(d["reason"] for d in picked).items()):
        print(f"  {reason}: {c}")
    if no_hint:
        print(f"BRĪDINĀJUMS: {no_hint} rindām nav Jev ieteikuma (kešā nav / Jev neatbildēja)",
              file=sys.stderr)
    return 0


def cmd_bills_sync(db, args) -> int:
    keys = _read_keys(args.keys_file) if args.keys_file else None
    try:
        out = sync_bill_topics(db, args.sync_id, keys=keys, rollback_dir=args.rollback_dir)
    except (OSError, ValueError, RuntimeError) as e:
        return _err(str(e))
    print(json.dumps(out, ensure_ascii=False))
    if out["changed"]:
        print("Pirms `bills-apply` komitē rollback failu (eskalācija 8).")
    return 0


def cmd_bills_apply(db, args) -> int:
    if not args.require_tracked:
        print("BRĪDINĀJUMS: --no-require-tracked — rollback faila komitēšanu NEPĀRBAUDA "
              "(eskalācija 8). Tikai DB kopijām un testiem!", file=sys.stderr)
    try:
        out = apply_bill_sync(db, args.sync_id, require_tracked=args.require_tracked)
    except (ValueError, RuntimeError) as e:
        return _err(str(e))
    print(json.dumps(out, ensure_ascii=False))
    return 0


def cmd_bills_rollback(db, args) -> int:
    try:
        out = rollback_bill_sync(db, args.sync_id)
    except (ValueError, RuntimeError) as e:
        return _err(str(e))
    print(json.dumps(out, ensure_ascii=False))
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--db", default=str(_REPO / PRODUCTION_DB_PATH))
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("status")
    p = sub.add_parser("decide", help="cilvēka lēmums dokumentam (method=human)")
    p.add_argument("key")
    p.add_argument("topic")
    p = sub.add_parser("freeze")
    p.add_argument("batch_id")
    p.add_argument("--keys-file", required=True)
    p.add_argument("--rollback-dir", default=str(_REPO / "data"))
    p.add_argument("--allow-pending", action="store_true",
                   help="atļaut lēmumus ar review_status='pending' (zema pārliecība)")
    p = sub.add_parser("apply")
    p.add_argument("batch_id")
    p.add_argument("--no-require-tracked", dest="require_tracked", action="store_false")
    p = sub.add_parser("rollback")
    p.add_argument("batch_id")
    p = sub.add_parser("abandon", help="pamest iesaldētu, nepiemērotu partiju")
    p.add_argument("batch_id")
    p = sub.add_parser("plan", help="partiju saraksts → CSV (tikai lasa DB)")
    p.add_argument("--size", type=int, default=300)
    p.add_argument("--out", default=str(_REPO / "data" / "saeima_topic_gold" / "batches.csv"))
    p = sub.add_parser("classify", help="9. uzd. 1. solis: Jev partijas dokumentiem bez lēmuma")
    p.add_argument("batch_id")
    p.add_argument("--threshold", type=float, default=BATCH_CONFIDENCE_THRESHOLD)
    p.add_argument("--batches", default=str(GOLD_DIR / "batches.csv"))
    p = sub.add_parser("review-list", help="9. uzd. 2. solis: pārskatāmo dokumentu CSV")
    p.add_argument("batch_id")
    p.add_argument("--batches", default=str(GOLD_DIR / "batches.csv"))
    p.add_argument("--out", help="CSV (noklusējums data/saeima_topic_gold/review_<batch>.csv)")
    p = sub.add_parser("bills-sync", help="saeima_bills.topic no lēmumiem: snapshot + rollback fails")
    p.add_argument("sync_id")
    p.add_argument("--keys-file", help="tikai šo dokumentu likumi (citādi visi)")
    p.add_argument("--rollback-dir", default=str(_REPO / "data"))
    p = sub.add_parser("bills-apply")
    p.add_argument("sync_id")
    p.add_argument("--no-require-tracked", dest="require_tracked", action="store_false")
    p = sub.add_parser("bills-rollback")
    p.add_argument("sync_id")
    args = ap.parse_args(argv)
    if not Path(args.db).exists():
        return _err(f"DB nav atrasta: {args.db}")
    init_saeima_tables(args.db)  # tikai CREATE IF NOT EXISTS: jaunās tabulas pirms pirmās ielādes
    db = get_db(args.db)
    try:
        return {"status": cmd_status, "decide": cmd_decide, "freeze": cmd_freeze,
                "apply": cmd_apply, "rollback": cmd_rollback, "abandon": cmd_abandon,
                "plan": cmd_plan, "classify": cmd_classify, "review-list": cmd_review_list,
                "bills-sync": cmd_bills_sync, "bills-apply": cmd_bills_apply,
                "bills-rollback": cmd_bills_rollback}[args.cmd](db, args)
    finally:
        db.close()


if __name__ == "__main__":
    sys.exit(main())
