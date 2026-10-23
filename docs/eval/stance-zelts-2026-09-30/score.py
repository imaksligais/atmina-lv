#!/usr/bin/env python
"""Eval v4 vērtēšana (2026-09-30).

    score.py prep     # out/*.json -> grade_in/gNN.json (akli, sajaukti) + _sid_map.json
    score.py report   # grade_out/*.json -> tabula + results.json

Kritēriji fiksēti plānā pirms skrējiena (docs/plans/2026-09-30-claim-extractor-parbuve.md § 5).
"""
from __future__ import annotations

import json
import random
import sys
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "scripts"))

VARIANTS = ("vecais", "jaunais")
N_GRADERS = 3


def gold() -> dict[int, dict]:
    return {g["doc_id"]: g for g in json.loads((HERE / "gold.json").read_text(encoding="utf-8"))}


def outputs() -> dict[str, dict[int, dict]]:
    res: dict[str, dict[int, dict]] = {v: {} for v in VARIANTS}
    for f in sorted((HERE / "out").glob("*_p*.json")):
        v = f.stem.split("_")[0]
        for row in json.loads(f.read_text(encoding="utf-8")):
            res[v][int(row["doc_id"])] = row
    return res


def prep() -> None:
    G = gold()
    out = outputs()
    for v in VARIANTS:
        missing = set(G) - set(out[v])
        if missing:
            raise SystemExit(f"{v}: trūkst doki {sorted(missing)}")
    rnd = random.Random(20260930)
    sid_map = {}
    items = []
    n = 0
    for doc_id, g in G.items():
        stances = []
        for v in VARIANTS:
            for k, c in enumerate(out[v][doc_id].get("claims") or []):
                n += 1
                sid = f"s{n:03d}"
                sid_map[sid] = {"variant": v, "doc_id": doc_id, "k": k}
                stances.append({"sid": sid, "stance": c.get("stance")})
        rnd.shuffle(stances)
        items.append({
            "doc_id": doc_id, "politician": g["politician"], "doc_text": g["doc_text"],
            "reference": g["gold_stance"] if g["gold_verdict"] == "KEEP" else None,
            "stances": stances,
        })
    rnd.shuffle(items)
    (HERE / "grade_in").mkdir(exist_ok=True)
    for i in range(N_GRADERS):
        part = items[i::N_GRADERS]
        (HERE / f"grade_in/g{i + 1:02d}.json").write_text(
            json.dumps(part, ensure_ascii=False, indent=1), encoding="utf-8")
        print(f"g{i + 1:02d}: {len(part)} doki, {sum(len(x['stances']) for x in part)} stance")
    (HERE / "_sid_map.json").write_text(json.dumps(sid_map, indent=1), encoding="utf-8")


def report() -> None:
    from eval_claim_extractor_score import norm
    from src.quality import validate_lv_diacritics

    G = gold()
    out = outputs()
    sid_map = json.loads((HERE / "_sid_map.json").read_text(encoding="utf-8"))
    grades = {}
    for f in sorted((HERE / "grade_out").glob("g*.json")):
        for r in json.loads(f.read_text(encoding="utf-8")):
            grades[r["sid"]] = r
    missing = set(sid_map) - set(grades)
    if missing:
        raise SystemExit(f"nenovērtēti stance: {sorted(missing)}")

    per = {v: defaultdict(list) for v in VARIANTS}  # variant -> doc -> [grade rows]
    for sid, m in sid_map.items():
        per[m["variant"]][m["doc_id"]].append(grades[sid] | {"sid": sid, "k": m["k"]})

    res = {}
    for v in VARIANTS:
        gc = Counter(r["grade"] for rows in per[v].values() for r in rows)
        n = sum(gc.values())
        ab = gc["A_WITHDRAW"] + gc["B_REWRITE"]
        keep_docs = [d for d, g in G.items() if g["gold_verdict"] == "KEEP"]
        found = 0
        for d in keep_docs:
            ok = any(r["matches_reference"] in ("yes", "partial") and r["grade"] in ("D_OK", "C_LANGUAGE")
                     for r in per[v][d])
            if ok or (G[d]["empty_ok"] and not out[v][d].get("claims")):
                found += 1
        wd_docs = [d for d, g in G.items() if g["gold_verdict"] == "WITHDRAW"]
        wd_false = sum(1 for d in wd_docs if any(r["grade"] in ("A_WITHDRAW", "B_REWRITE") for r in per[v][d]))
        sup_total = sup_ok = 0
        lv_fail = []
        for d, row in out[v].items():
            text = norm(G[d]["doc_text"])
            for c in row.get("claims") or []:
                for fld in ("stance", "reasoning"):
                    ok, why = validate_lv_diacritics(c.get(fld)) if c.get(fld) else (True, "")
                    if not ok:
                        lv_fail.append((d, fld, why))
                if v == "jaunais":
                    sup_total += 1
                    frags = c.get("support") or []
                    if isinstance(frags, str):
                        frags = [frags]
                    if frags and all(len(norm(s)) >= 10 and norm(s) in text for s in frags):
                        sup_ok += 1
        by_type = defaultdict(Counter)
        for d, rows in per[v].items():
            for r in rows:
                by_type[G[d]["type"]][r["grade"]] += 1
        res[v] = {
            "stances": n, "grades": dict(gc), "ab_share": round(ab / n, 3) if n else None,
            "recall": f"{found}/{len(keep_docs)}", "recall_n": found,
            "withdraw_false": f"{wd_false}/{len(wd_docs)}", "withdraw_false_n": wd_false,
            "support_pass": f"{sup_ok}/{sup_total}" if v == "jaunais" else None,
            "support_rate": round(sup_ok / sup_total, 3) if (v == "jaunais" and sup_total) else None,
            "lv_fail": lv_fail, "by_type": {k: dict(c) for k, c in by_type.items()},
            "empty_docs": sum(1 for r in out[v].values() if not r.get("claims")),
        }
    o, j = res["vecais"], res["jaunais"]
    crit = {
        "1 A+B ≤ vecais − 5 pp": j["ab_share"] <= o["ab_share"] - 0.05,
        "2 recall ≥ vecais − 1": j["recall_n"] >= o["recall_n"] - 1,
        "3 WITHDRAW viltus ≤ vecais": j["withdraw_false_n"] <= o["withdraw_false_n"],
        "4 support ≥ 95 %": (j["support_rate"] or 0) >= 0.95,
        "5 0 garumzīmju kļūdu": not j["lv_fail"],
    }
    res["criteria"] = crit
    (HERE / "results.json").write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
    for v in VARIANTS:
        r = res[v]
        print(f"{v:8} stance={r['stances']:3} A+B={r['ab_share']} grades={r['grades']} recall={r['recall']} "
              f"withdraw_false={r['withdraw_false']} empty_docs={r['empty_docs']} support={r['support_pass']} lv_fail={len(r['lv_fail'])}")
    for k, ok in crit.items():
        print(("PASS " if ok else "FAIL ") + k)


def calib() -> None:
    """Vērtētāja jutības pārbaude: 32 zināmi kļūdaini (09-30 verificēti A/B) +
    10 jau D_OK novērtēti eval stance, akli sajaukti. Jutīgs vērtētājs ≥20/32
    kļūdainos atzīmē A/B."""
    G = gold()
    out = outputs()
    rnd = random.Random(777)
    rows, key = [], {}
    bad = [g for g in G.values() if g["type"] not in ("D_OK",)]
    for g in bad:
        rows.append((g["doc_id"], g["old_stance"], "known_bad"))
    pool = [(d, c["stance"]) for v in VARIANTS for d, r in out[v].items() for c in (r.get("claims") or [])]
    for d, st in rnd.sample(pool, 10):
        rows.append((d, st, "eval_ok"))
    rnd.shuffle(rows)
    docs: dict[int, dict] = {}
    for n, (d, st, kind) in enumerate(rows, 1):
        sid = f"c{n:03d}"
        key[sid] = {"doc_id": d, "kind": kind}
        docs.setdefault(d, {"doc_id": d, "politician": G[d]["politician"], "doc_text": G[d]["doc_text"],
                            "reference": None, "stances": []})["stances"].append({"sid": sid, "stance": st})
    items = list(docs.values())
    rnd.shuffle(items)
    (HERE / "grade_in/calib.json").write_text(json.dumps(items, ensure_ascii=False, indent=1), encoding="utf-8")
    (HERE / "_calib_key.json").write_text(json.dumps(key, indent=1), encoding="utf-8")
    print(len(items), "doki,", len(rows), "stance")


def calib_report() -> None:
    key = json.loads((HERE / "_calib_key.json").read_text(encoding="utf-8"))
    gr = {r["sid"]: r for r in json.loads((HERE / "grade_out/calib.json").read_text(encoding="utf-8"))}
    c = defaultdict(Counter)
    for sid, k in key.items():
        c[k["kind"]][gr[sid]["grade"]] += 1
    for kind, cnt in c.items():
        print(kind, dict(cnt))


if __name__ == "__main__":
    {"prep": prep, "report": report, "calib": calib, "calib_report": calib_report}[sys.argv[1]]()
