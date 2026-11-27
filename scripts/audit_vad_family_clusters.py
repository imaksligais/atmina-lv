"""Audit: detect 2+ disjoint family clusters per tracked politician.

VAD Phase 2 — homonīmu signāls. Reāls cilvēks visās deklarācijās saglabā
vismaz vienu kopīgu ģimenes locekli. Disjoint klasteri = homonīmu kontaminācija.

Paraksts = VISA deklarētā ģimene (laulātais, bērni, vecāki, brāļi, māsas), ne
tikai laulātais/bērni (mainīts 2026-11-27, mērījums uz DB kopijas ar atjaunotām
31 vārdabrāļu deklarācijām): tikai laulātais+bērni noķēra 4/5 zināmos vārdabrāļus
un deva 21 viltus karogu (laulības, vārda maiņa); visa ģimene — 5/5 un 2 karogus,
bez paraksta palika 8 dekl. (bija 558) — vecāki un brāļi/māsas desmitgadēm nemainās.

Zināma robeža: divi vārdabrāļi, kuru kādam radiniekam (piem., tēvam) ir vienāds
vārds un uzvārds, saplūst vienā klasterī — vārti tos nenoķer.

Algoritms (union-find pa ģimenes locekļu signature):
  1. Katrai deklarācijai ekstraktē frozenset((relation, normalized_name))
  2. Sasaista deklarācijas vienā klasterī, ja signatures pārklājas vismaz 1 loceklī
  3. Tukšas signatures tiek izlaistas (nepierāda piederību)
  4. Atskaite per pid: ja 2+ klasteri → flag

Usage:
    python scripts/audit_vad_family_clusters.py             # visas pids
    python scripts/audit_vad_family_clusters.py --pid 101   # tikai 1
    python scripts/audit_vad_family_clusters.py --json      # mašīnlasāms output

Exit:
    0 — visi profili ar ≤1 klasteri (tīri)
    1 — vismaz 1 profilu ar 2+ disjoint klasteriem
"""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from collections import defaultdict
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

# Viena cilvēka radniecība dažādās deklarācijās rakstīta dažādi: vecā VID forma
# (2002–2013) laulāto sauc «Sieva»/«Vīrs», jaunā «Laulātais»; to pašu brāli viena
# deklarācija sauc «Brālis», cita «Pusbrālis».
RELATION_ALIASES = {
    "Sieva": "Laulātais", "Vīrs": "Laulātais",
    "Pusbrālis": "Brālis", "Pusmāsa": "Māsa",
}
SKIP_RELATIONS = {"Nav norādīts"}


def family_signature(
    fams: list[tuple[str, str]],
) -> frozenset[tuple[str, str]]:
    """Return frozenset of (relation, normalized_name) for the declared family."""
    out = set()
    for rel, name in fams:
        rel = rel.strip()
        rel = rel[:1].upper() + rel[1:]
        rel = RELATION_ALIASES.get(rel, rel)
        if rel not in SKIP_RELATIONS:
            normalized = " ".join(name.upper().split())
            out.add((rel, normalized))
    return frozenset(out)


def cluster_disjoint_families(
    decls_with_fams: list[tuple[int, frozenset]],
) -> list[dict]:
    """Group declaration IDs into clusters by family-signature overlap.

    Pārklāšanās (vismaz 1 kopīgs (rel, name)) → vienots klasters.
    Disjoint signatures → atsevišķi klasteri.
    Tukšas signatures → izslēgtas no klasterizācijas.
    """
    nonempty = [(did, sig) for did, sig in decls_with_fams if sig]
    if not nonempty:
        return []

    # Union-find pa ģimenes locekļiem
    parent: dict[int, int] = {i: i for i in range(len(nonempty))}

    def find(x: int) -> int:
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a: int, b: int) -> None:
        parent[find(a)] = find(b)

    for i in range(len(nonempty)):
        for j in range(i + 1, len(nonempty)):
            if nonempty[i][1] & nonempty[j][1]:
                union(i, j)

    groups: dict[int, list[int]] = defaultdict(list)
    for i, (did, _sig) in enumerate(nonempty):
        groups[find(i)].append(did)

    clusters = []
    for cluster_dids in groups.values():
        decl_ids = sorted(cluster_dids)
        # Apvieno visus signatures, ko klasteris satur
        merged_sig = set()
        for did in decl_ids:
            for sig_did, sig in nonempty:
                if sig_did == did:
                    merged_sig.update(sig)
        clusters.append({"decl_ids": decl_ids, "members": sorted(merged_sig)})
    clusters.sort(key=lambda c: -len(c["decl_ids"]))
    return clusters


def audit_pid(db: sqlite3.Connection, pid: int) -> dict:
    decls = db.execute(
        """
        SELECT id, declaration_year, declaration_kind, institution, position_title,
               submitted_at
        FROM vad_declarations
        WHERE opponent_id = ?
        ORDER BY id
        """,
        (pid,),
    ).fetchall()
    # Jaunā forma no `vad_family`, vecā (2002–2013) no `raw_html` — src/vad/family.py.
    from src.vad.family import declaration_families  # noqa: E402

    fams_by_decl = declaration_families(db, [pid])

    decls_with_fams = [
        (d["id"], family_signature(fams_by_decl.get(d["id"], []))) for d in decls
    ]
    clusters = cluster_disjoint_families(decls_with_fams)
    name = db.execute(
        "SELECT name FROM tracked_politicians WHERE id = ?", (pid,)
    ).fetchone()
    return {
        "pid": pid,
        "name": name["name"] if name else f"pid={pid}",
        "n_decls": len(decls),
        "n_clusters": len(clusters),
        "n_no_signature": sum(1 for _did, sig in decls_with_fams if not sig),
        "clusters": clusters,
    }


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    p = argparse.ArgumentParser()
    p.add_argument("--pid", type=int, help="audit tikai 1 politiķis")
    p.add_argument("--json", action="store_true")
    args = p.parse_args()

    from src.db import get_db  # noqa: E402  # deferred to avoid test-time simhash import

    db = get_db()
    if args.pid:
        pids = [args.pid]
    else:
        pids = [
            r["id"]
            for r in db.execute(
                "SELECT DISTINCT tp.id FROM tracked_politicians tp "
                "JOIN vad_declarations vd ON tp.id = vd.opponent_id "
                "ORDER BY tp.id"
            )
        ]

    flagged: list[dict] = []
    n_decls = n_unsigned = n_pids_unsigned = 0
    for pid in pids:
        result = audit_pid(db, pid)
        n_decls += result["n_decls"]
        n_unsigned += result["n_no_signature"]
        n_pids_unsigned += result["n_clusters"] == 0
        if result["n_clusters"] >= 2:
            flagged.append(result)

    # Saucējs: deklarācijas bez ģimenes datiem netiek salīdzinātas — tās ir
    # «nepārbaudītas», nevis «tīras».
    print(f"[saucējs] {n_decls} dekl.; bez paraksta (nav ģimenes datu) {n_unsigned}; "
          f"politiķi bez neviena paraksta {n_pids_unsigned}/{len(pids)}", file=sys.stderr)
    if args.json:
        print(json.dumps(flagged, ensure_ascii=False, indent=2))
    else:
        if not flagged:
            print(f"[ok] {len(pids)} politiķi auditēti, 0 ar disjoint family clusters")
        else:
            print(f"[FLAG] {len(flagged)}/{len(pids)} politiķi ar 2+ disjoint klasteriem:\n")
            for r in flagged:
                print(f"PID {r['pid']:>3}  {r['name']}  ({r['n_decls']} dekl, {r['n_clusters']} klasteri)")
                for i, c in enumerate(r["clusters"], 1):
                    members = ", ".join(f"{rel}:{name}" for rel, name in c["members"])
                    decl_ids = ", ".join(str(d) for d in c["decl_ids"][:5])
                    more = f" + {len(c['decl_ids']) - 5} citi" if len(c["decl_ids"]) > 5 else ""
                    print(f"   [{i}] {len(c['decl_ids'])} dekl: {decl_ids}{more}")
                    print(f"       ģimene: {members}")
                print()
    return 1 if flagged else 0


if __name__ == "__main__":
    raise SystemExit(main())
