#!/usr/bin/env python3
"""Salīdzina kodejuma failu ar priekšlikuma failu (tikai lasīšana).

Lietojums:
    python scripts/partiju_tests_diff.py --a kodejums.json --b kodejums_u3_priekslikums.json
"""
import argparse
import json
from pathlib import Path


def _nostaja(cell: dict) -> str:
    return cell.get("nostaja", "?")


def _citats(cell: dict) -> str:
    c = cell.get("citats") or cell.get("piezime") or ""
    return c[:90]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--a", required=True, help="esošais kodejums.json")
    ap.add_argument("--b", required=True, help="priekšlikuma fails")
    args = ap.parse_args()

    a = json.loads(Path(args.a).read_text(encoding="utf-8"))
    b = json.loads(Path(args.b).read_text(encoding="utf-8"))

    rows = []
    agree = 0
    total = 0
    claim_changed = []
    for qid in sorted(b):
        for lst, new_cell in b[qid].items():
            old_cell = a.get(qid, {}).get(lst, {})
            old_n, new_n = _nostaja(old_cell), _nostaja(new_cell)
            total += 1
            if old_n == new_n:
                agree += 1
            rows.append(
                f"| {qid} | {lst} | {old_n} | {new_n} | {_citats(new_cell)} | {_citats(old_cell)} |"
            )
            if old_n in ("par", "pret") and new_n in ("par", "pret"):
                if old_cell.get("claim_id") != new_cell.get("claim_id"):
                    claim_changed.append((qid, lst, old_cell.get("claim_id"), new_cell.get("claim_id")))

    print("| jautājums | saraksts | bija | piedāvāts | piedāvātais citāts | bijušais citāts |")
    print("|---|---|---|---|---|---|")
    for r in rows:
        print(r)
    print(f"\nsakrīt {agree} no {total}")
    if claim_changed:
        print("\nclaim_id izmaiņas (abas šūnas par/pret):")
        for qid, lst, old_c, new_c in claim_changed:
            print(f"  {qid} {lst}: {old_c} -> {new_c}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
