#!/usr/bin/env python
"""Zelta kopa claim-extractor v4 eval (2026-09-30).

Ņem 09-30 verificētās rindas (`docs/audits/2026-09-30-stance-izlase/`) un
izveido `gold.json` (atbildes, vērtētājiem) + `packs/pNN.json` (ievade
ekstraktoriem — BEZ atbildēm, BEZ esošās stance). Tikai lasa DB.

Izvēle ir roku (stratificēta pēc kļūdu tipa `_candidates.json`); ID, ko citē
vecais prompts, izslēgti (kontaminācija). D_OK kontroles — nejauši ar seed.

    PYTHONUTF8=1 .venv/Scripts/python.exe docs/eval/stance-zelts-2026-09-30/build_gold.py
"""
from __future__ import annotations

import glob
import json
import random
import re
import sqlite3
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
AUD = REPO / "docs/audits/2026-09-30-stance-izlase"

PICK = {
    "sibling": [14348, 14503, 6898, 11302, 14486],
    "question": [14487, 6654, 548481, 14366, 7351],
    "hedge": [14475, 14532, 1530, 472, 14351],
    "tense": [7192, 14336, 14323],
    "cause": [7488, 6692, 7330],
    "scope": [11339, 6701, 10958],
    "otherwords": [689511, 403],
    "WITHDRAW": [160, 7394, 7337, 401, 7402, 1570],
}
N_DOK = 6
PACK_SIZE = 8


def load(pattern: str) -> dict[int, dict]:
    out = {}
    for f in glob.glob(str(AUD / pattern)):
        for r in json.loads(Path(f).read_text(encoding="utf-8")):
            out[r["id"]] = r
    return out


def rollback_claims() -> dict[int, dict]:
    """Atsaukto claims rindas no rollback SQL (tie DB vairs nav)."""
    out = {}
    for f in glob.glob(str(REPO / "data/rollback_stance_*2026-09-30.sql")):
        for line in Path(f).read_text(encoding="utf-8").splitlines():
            m = re.match(r"INSERT INTO claims \(([^)]*)\) VALUES \((\d+), (\d+), (\d+),", line)
            if m:
                out[int(m.group(2))] = {"opponent_id": int(m.group(3)), "document_id": int(m.group(4))}
    return out


def main() -> None:
    vin = {**load("aprilis/vin*.json"), **load("verify_in*.json")}
    vout = {**load("aprilis/vout*.json"), **load("verify_out*.json")}
    graded = {**load("aprilis/g*.json"), **load("grades*.json")}
    cited = {int(x[1:]) for x in (HERE / "_prompt_ids.txt").read_text().split()}
    rb = rollback_claims()

    db = sqlite3.connect(REPO / "data/atmina.db")
    db.row_factory = sqlite3.Row

    def claim_row(cid: int) -> dict | None:
        r = db.execute("SELECT opponent_id, document_id, topic, stance, quote FROM claims WHERE id=?", (cid,)).fetchone()
        if r:
            return dict(r)
        return rb.get(cid)

    rnd = random.Random(930)
    dok_pool = sorted(i for i, r in graded.items()
                      if r.get("grade") == "D_OK" and i not in cited and i not in vin)
    rnd.shuffle(dok_pool)
    picks = [(t, i) for t, ids in PICK.items() for i in ids]
    used_docs = set()
    items = []
    for t, cid in picks + [("D_OK", i) for i in dok_pool]:
        if t == "D_OK" and sum(1 for x in items if x["type"] == "D_OK") >= N_DOK:
            break
        assert cid not in cited, cid
        cr = claim_row(cid)
        if not cr or not cr.get("document_id"):
            if t != "D_OK":
                raise SystemExit(f"claim {cid}: nav document_id")
            continue
        d = db.execute("SELECT * FROM documents WHERE id=?", (cr["document_id"],)).fetchone()
        if d is None or d["id"] in used_docs:
            if t != "D_OK":
                raise SystemExit(f"claim {cid}: dokuments {cr['document_id']} nav/atkārtojas")
            continue
        text = ((d["title"] or "") + "\n\n" + (d["content"] or "")).strip()
        if t == "D_OK" and not (150 <= len(text) <= 6000):
            continue
        used_docs.add(d["id"])
        p = db.execute("SELECT id, name, party, role, relationship_type FROM tracked_politicians WHERE id=?",
                       (cr["opponent_id"],)).fetchone()
        fa = db.execute("SELECT feed_type, handle FROM social_accounts WHERE opponent_id=? AND platform='twitter'",
                        (cr["opponent_id"],)).fetchone()
        if t == "D_OK":
            gold_verdict, gold_stance, why = "KEEP", graded[cid].get("proposed_stance") or db.execute(
                "SELECT stance FROM claims WHERE id=?", (cid,)).fetchone()[0], graded[cid].get("why")
        else:
            v = vout[cid]
            gold_verdict = "WITHDRAW" if v["verdict"] == "WITHDRAW" else "KEEP"
            gold_stance = None if gold_verdict == "WITHDRAW" else v.get("final_stance")
            why = vin[cid].get("grader_why")
        items.append({
            # Žurnālistu/organizāciju slots kopš 2026-08-21 = relay: tukšs ir derīgs.
            "empty_ok": gold_verdict == "WITHDRAW" or p["relationship_type"] in ("journalist", "organization"),
            "relationship_type": p["relationship_type"],
            "type": t, "claim_id": cid, "doc_id": d["id"], "pid": p["id"],
            "gold_verdict": gold_verdict, "gold_stance": gold_stance, "grader_why": why,
            "old_stance": (vin.get(cid) or {}).get("current_stance") or cr.get("stance"),
            "doc": {
                "doc_id": d["id"], "pid": p["id"], "politician": p["name"], "party": p["party"],
                "role": p["role"], "relationship_type": p["relationship_type"],
                "feed_type": fa["feed_type"] if fa else None, "x_handle": fa["handle"] if fa else None,
                "platform": d["platform"], "source_url": d["source_url"], "published_at": d["published_at"],
                "word_count": d["word_count"], "title": d["title"], "content": d["content"],
            },
        })

    # Iepako 8 dokus aģentā, kā produkcijā (plan_extraction pack_docs=8).
    order = list(range(len(items)))
    rnd.shuffle(order)
    packs = [order[i:i + PACK_SIZE] for i in range(0, len(order), PACK_SIZE)]
    (HERE / "packs").mkdir(exist_ok=True)
    for n, pk in enumerate(packs, 1):
        for i in pk:
            items[i]["pack"] = n
        (HERE / f"packs/p{n:02d}.json").write_text(
            json.dumps([items[i]["doc"] for i in pk], ensure_ascii=False, indent=1), encoding="utf-8")
    gold = [{k: v for k, v in it.items() if k != "doc"} | {"doc_text": ((it["doc"]["title"] or "") + "\n\n" + (it["doc"]["content"] or "")).strip(),
             "politician": it["doc"]["politician"]} for it in items]
    (HERE / "gold.json").write_text(json.dumps(gold, ensure_ascii=False, indent=1), encoding="utf-8")
    from collections import Counter
    print(len(items), "doki;", len(packs), "komplekti;", Counter(i["type"] for i in items))


if __name__ == "__main__":
    main()
