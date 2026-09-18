"""One-off backfill: re-classify existing claims into 5 new canonical topics
(Pilsētvide, Veselības aprūpe, Klimats, Korupcija un KNAB, Digitālā politika)
where the stance content matches the new bucket better than the old one.

Strategy: keyword-based suggestion. For each claim currently in a "wide"
bucket (Pašvaldības, Transports, Sociālā politika, Vide, Tieslietas,
Valsts pārvalde, Vēlēšanas), check stance text for keywords belonging to
the new specific bucket. If matched, propose reclassification.

Run with --dry-run to see suggestions; without to apply.
"""
import argparse
import sqlite3


# (target_topic, current_topics_to_search, keyword_patterns)
RULES = [
    ("Pilsētvide",
     ("Pašvaldības", "Transports"),
     ["modāl", "tranzītsatiks", "veloceļ", "veloinfra", "mikromobilitāt",
      "apkaim", "Grīziņkalnā", "Grīziņkaln", "Vārnu iela", "gājēju droš",
      "tranzīta satiksm", "betona barjer"]),
    ("Veselības aprūpe",
     ("Sociālā politika",),
     ["mediķ", "ārstniecīb", "veselīb", "farmācij", "medicīn", "RAKUS",
      "ambulanc", "neatliekam", "rehabilitācij", "garīgā veselīb",
      "medikamentu cen"]),
    ("Klimats",
     ("Vide", "Degviela un enerģētika"),
     ["klimatneitral", "klimata politik", "CO2 nodok", "ETS", "emisiju tirgus",
      "oglekļa neitr", "klimata mērķ"]),
    ("Korupcija un KNAB",
     ("Tieslietas", "Valsts pārvalde"),
     # Tightened from "KNAB" alone (too broad — many claims mention KNAB
     # incidentally without being fundamentally about corruption). Require
     # specific phrases.
     ["korupcij", "interešu konflikt", "amatpersonu dekl",
      "KNAB izmeklēšan", "KNAB pārbaud"]),
    ("Digitālā politika",
     ("Valsts pārvalde", "Vēlēšanas", "Sabiedriskie mediji"),
     ["VRAA", "EIS iepirkum", "digitāl", "kiberdroš", "valsts IT",
      "e-pārvald", "valsts digitāl", "RIX Technologies", "vēlēšanu IT"]),
]


def find_candidates(con: sqlite3.Connection) -> list[dict]:
    out = []
    for target_topic, current_topics, kws in RULES:
        placeholders = ",".join("?" * len(current_topics))
        rows = con.execute(
            f"SELECT id, opponent_id, topic, stance, source_url FROM claims "
            f"WHERE topic IN ({placeholders})",
            current_topics,
        ).fetchall()
        for r in rows:
            stance = (r["stance"] or "").lower()
            for kw in kws:
                if kw.lower() in stance:
                    out.append({
                        "claim_id": r["id"],
                        "current_topic": r["topic"],
                        "target_topic": target_topic,
                        "stance_preview": (r["stance"] or "")[:120],
                        "matched_keyword": kw,
                        "source_url": r["source_url"],
                    })
                    break
    return out


def apply_reclassifications(con: sqlite3.Connection, candidates: list[dict]) -> int:
    cur = con.cursor()
    for c in candidates:
        cur.execute(
            "UPDATE claims SET topic=? WHERE id=?",
            (c["target_topic"], c["claim_id"]),
        )
    con.commit()
    return len(candidates)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", default="data/atmina.db")
    parser.add_argument("--apply", action="store_true",
                        help="Apply reclassifications. Default is dry-run preview.")
    args = parser.parse_args()

    con = sqlite3.connect(args.db)
    con.row_factory = sqlite3.Row
    cands = find_candidates(con)

    if not cands:
        print("No reclassification candidates found.")
        con.close()
        return

    by_target: dict[str, list] = {}
    for c in cands:
        by_target.setdefault(c["target_topic"], []).append(c)

    print(f"Found {len(cands)} candidates across {len(by_target)} target topics:\n")
    for target, items in sorted(by_target.items()):
        print(f"  -> {target}: {len(items)} claims")
        for c in items[:3]:
            print(f"     #{c['claim_id']} ({c['current_topic']}): "
                  f"[{c['matched_keyword']}] {c['stance_preview']}")
        if len(items) > 3:
            print(f"     ... and {len(items) - 3} more")
        print()

    if args.apply:
        applied = apply_reclassifications(con, cands)
        print(f"Applied {applied} reclassifications.")
    else:
        print("Dry-run only. Re-run with --apply to commit.")

    con.close()


if __name__ == "__main__":
    main()
