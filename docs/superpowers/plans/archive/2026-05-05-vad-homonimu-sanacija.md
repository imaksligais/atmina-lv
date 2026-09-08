# VAD Homonīmu Sanācijas Plāns (Phase 2)

> **Aģentu izpildei:** OBLIGĀTĀ APAKŠ-PRASME: Lieto `superpowers:subagent-driven-development` (ieteikta) vai `superpowers:executing-plans`, lai izpildītu šo plānu uzdevumu pa uzdevumam. Soļi izmanto checkbox (`- [ ]`) sintaksi izpildes uzskaitei.

**Mērķis:** Izņemt no `data/atmina.db` un publicētās analīzes 5 politiķu profilus, kuros 2026-05-03 publicētā VAD analīze ir samaisījusi datus no homonīmiem (cita cilvēka deklarācijas piesaistītas mūsu tracked politiķim) — Inese Kalniņa, Līga Kļaviņa, Jānis Skrastiņš, Gatis Liepiņš, Linda Liepiņa — un ieviest jaunu audita gate (`audit_vad_family_clusters.py`), kas tādu kontamināciju atklāj, pirms tā tiek publicēta nākamreiz.

**Arhitektūra:** Trīs slāņu darbība. (1) **Atklāšana** — jauns audita skripts, kas katram tracked politiķim salīdzina ģimenes locekļu klasterus pa deklarācijām un atzīmē 2+ disjoint klasterus kā kontaminācijas signālu (gold standard, jo vecāki/laulātais/bērni nemainās starp paralēliem amatiem). (2) **Sanācija** — par katru no 5 apstiprinātajiem gadījumiem sašaurina `tracked_politicians.keywords.vad_disambig` whitelist tikai uz patiesi piederīgo amatu, palaiž `cleanup_contaminated_vad.py --politician X --reingest` un verificē rezultātu ar audita skriptu. (3) **Atjaunina analīzi** — pārrēķina § 2 top-15, izlabo § 218 piezīmes par "paralēliem amatiem" un § 325 dedup metodiku, regenerē atmina.lv. Pēc tam plašā skenēšana ar audita skriptu visiem 152 politiķiem, lai dokumentētu pārējos atlikušos gadījumus (vēsturiski homonīmi, kas neietekmē 2024-25 ranking tabulas).

**Tehnoloģijas:** Python 3.12, SQLite, esošais Phase 1.5 sanācijas pattern (`scripts/seed_*_disambig.py` + `scripts/cleanup_contaminated_vad.py --politician --reingest` + `scripts/ingest_vad_declarations.py`), pytest, BeautifulSoup (HTML profila lapas verifikācijai).

**Worktree:** Šim plānam izveido worktree `vad-homonimu-sanacija`. Piezīme: DB raksti **nav** worktree-isolated — `data/atmina.db` ir kopīgs ar master. Worktree palīdz tikai koda izmaiņām (audita skripts, parser fix). DB cleanup darbības (`cleanup_contaminated_vad.py`) jāveic uzmanīgi — atbalsta `--dry-run` priekš pārbaudes pirms reālas izpildes.

---

## Failu struktūra

**Jauni faili:**
- `scripts/audit_vad_family_clusters.py` — atklāj 2+ disjoint immediate-family klasterus per politiķis. Exit 1 ja atrasti, 0 ja tīri. Tabular output ar opt-out flag.
- `scripts/seed_homonimu_phase2_disambig.py` — vienots curator skripts 5 politiķiem (101, 104, 107, 116, 132). Idempotents.
- `tests/test_vad_family_clusters_audit.py` — pytest priekš audita skripta klastera detekcijas loģikas (faktiski testē reizes-grupēšana + disjoint-set algoritmu).

**Modificējami faili:**
- `tracked_politicians.keywords.vad_disambig` un `tracked_politicians.negative_patterns` (DB) — caur curator skriptu, 5 pidiem.
- `vad_declarations` (DB) — DELETE caur `cleanup_contaminated_vad.py --politician`. CASCADE no FK section tabulām (`vad_income`, `vad_family`, `vad_real_estate`, `vad_companies`, `vad_savings`, `vad_vehicles`, `vad_transactions`, `vad_debts`, `vad_loans_given`, `vad_positions`).
- `content/analizes/vad-2026.md` — § 2 top-15 reranks, § 218 piezīmes pārrakstītas, § 325 metodika (82 022 EUR dedup) izlabota.
- `wiki/CHANGELOG.md` — pievienot ierakstu "2026-05-05 — VAD Phase 2: 5 papildu homonīmu sanācija".
- `~/.claude/projects/C--Users-The-User-atmina/memory/project_vad_done.md` — atjaunināt status.

**Iespējami modificējami (Phase C, atkarīgs no izmeklēšanas):**
- `src/vad/parsing.py` — ja apstiprinās intra-deklarācijas dublēto rindu parsēšanas defekts.
- `tests/test_vad_parsing.py` — papildinošs test gadījums.

---

## A FĀZE — Atklāšanas infrastruktūra

### T1 — `audit_vad_family_clusters.py` test-driven izveide

**Konteksts:** Galvenais signāls homonīmu kontaminācijai ir tas, ka vienam `opponent_id` piesaistītas deklarācijas satur **disjoint** ģimeņu klasterus (laulātais/bērni). Vienam reālam cilvēkam ģimenes kodols tam pašam dzīves periodam ir konsekvents pa visām paralēlām deklarācijām (Saeima + Tiesu adm + LNA, ja tādas tiešām būtu vienai personai). Atšķirīgi laulātie un atšķirīgi bērni starp paralēlām deklarācijām = atšķirīgi cilvēki.

**Faili:**
- Izveido: `scripts/audit_vad_family_clusters.py`
- Izveido: `tests/test_vad_family_clusters_audit.py`

- [ ] **Solis 1: Uzraksti failējošo testu klastera detekcijas loģikai**

Uzraksta `tests/test_vad_family_clusters_audit.py`:

```python
"""Test family-cluster audit: detect 2+ disjoint immediate-family clusters per pid."""

from scripts.audit_vad_family_clusters import (
    immediate_family_signature,
    cluster_disjoint_families,
)


def test_immediate_family_signature_excludes_extended_family():
    """Tikai laulātais + bērni veido klasteru atslēgu — māsa/brālis/vecāki var
    mainīties mantojuma vai parsēšanas variabilitātes dēļ."""
    fams = [
        ("Laulātais", "ANNA OZOLA"),
        ("Meita", "LAURA OZOLA"),
        ("Māte", "INESE OZOLA"),
        ("Brālis", "JĀNIS OZOLS"),
    ]
    sig = immediate_family_signature(fams)
    assert sig == frozenset({("Laulātais", "ANNA OZOLA"), ("Meita", "LAURA OZOLA")})


def test_signature_normalizes_whitespace_and_case():
    fams_a = [("Laulātais", "  Anna  Ozola ")]
    fams_b = [("Laulātais", "ANNA OZOLA")]
    assert immediate_family_signature(fams_a) == immediate_family_signature(fams_b)


def test_cluster_disjoint_two_unrelated_clusters():
    """Divas deklarācijas ar pilnīgi atšķirīgām ģimenēm = 2 klasteri."""
    decls_with_fams = [
        (1, frozenset({("Laulātais", "ANNA OZOLA")})),
        (2, frozenset({("Laulātais", "MARTA BĒRZIŅA")})),
    ]
    clusters = cluster_disjoint_families(decls_with_fams)
    assert len(clusters) == 2


def test_cluster_disjoint_subset_merges():
    """Ja viena deklarācija ir apakškopa otrai (piem. parsing izlaida bērnu),
    abas pieder vienam klasterim."""
    decls_with_fams = [
        (1, frozenset({("Laulātais", "ANNA OZOLA"), ("Meita", "LAURA OZOLA")})),
        (2, frozenset({("Laulātais", "ANNA OZOLA")})),
    ]
    clusters = cluster_disjoint_families(decls_with_fams)
    assert len(clusters) == 1
    assert {1, 2} == set(clusters[0]["decl_ids"])


def test_cluster_disjoint_overlap_merges():
    """Pārklāšanās vismaz 1 ģimenes loceklim = vienots klasters
    (pievienoti bērni laika gaitā)."""
    decls_with_fams = [
        (1, frozenset({("Laulātais", "ANNA OZOLA")})),
        (2, frozenset({("Laulātais", "ANNA OZOLA"), ("Dēls", "MĀRTIŅŠ OZOLS")})),
        (3, frozenset({("Dēls", "MĀRTIŅŠ OZOLS"), ("Meita", "LAURA OZOLA")})),
    ]
    clusters = cluster_disjoint_families(decls_with_fams)
    assert len(clusters) == 1


def test_empty_family_decls_form_own_cluster_or_skip():
    """Deklarācijas bez ģimenes datiem (vecas dekl < 2010) tiek izlaistas no
    klasterizācijas — nevar pierādīt piederību ne tā, ne tā."""
    decls_with_fams = [
        (1, frozenset()),
        (2, frozenset({("Laulātais", "ANNA OZOLA")})),
    ]
    clusters = cluster_disjoint_families(decls_with_fams)
    assert len(clusters) == 1  # tukšā tiek izlaista
    assert clusters[0]["decl_ids"] == [2]
```

- [ ] **Solis 2: Palaiž testus, lai pārliecinātos, ka neizdodas**

Palaiž: `pytest tests/test_vad_family_clusters_audit.py -v`

Sagaidāmais: FAIL ar `ModuleNotFoundError: No module named 'scripts.audit_vad_family_clusters'`.

- [ ] **Solis 3: Implementē audita skriptu**

Izveido `scripts/audit_vad_family_clusters.py`:

```python
"""Audit: detect 2+ disjoint immediate-family clusters per tracked politician.

VAD Phase 2 — homonīmu signāls. Reāls cilvēks paralēlām deklarācijām (Saeima +
ministrija u.tml.) saglabā konsekventu laulāto/bērnu sastāvu. Disjoint klasteri
= homonīmu kontaminācija.

Algoritms (union-find pa ģimenes locekļu signature):
  1. Katrai deklarācijai ekstraktē frozenset(("Laulātais"|"Dēls"|"Meita", normalized_name))
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

from src.db import get_db  # noqa: E402

IMMEDIATE = {"Laulātais", "Dēls", "Meita"}


def immediate_family_signature(
    fams: list[tuple[str, str]],
) -> frozenset[tuple[str, str]]:
    """Return frozenset of (relation, normalized_name) for immediate family only."""
    out = set()
    for rel, name in fams:
        if rel in IMMEDIATE:
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
    for member_indices in groups.values():
        decl_ids = sorted(member_indices)
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
    fams_by_decl: dict[int, list[tuple[str, str]]] = defaultdict(list)
    for r in db.execute(
        "SELECT declaration_id, relation, full_name FROM vad_family "
        "WHERE declaration_id IN (SELECT id FROM vad_declarations WHERE opponent_id = ?)",
        (pid,),
    ):
        fams_by_decl[r["declaration_id"]].append((r["relation"], r["full_name"]))

    decls_with_fams = [
        (d["id"], immediate_family_signature(fams_by_decl[d["id"]])) for d in decls
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
        "clusters": clusters,
    }


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    p = argparse.ArgumentParser()
    p.add_argument("--pid", type=int, help="audit tikai 1 politiķis")
    p.add_argument("--json", action="store_true")
    args = p.parse_args()

    db = get_db()
    if args.pid:
        pids = [args.pid]
    else:
        pids = [
            r["id"]
            for r in db.execute(
                "SELECT id FROM tracked_politicians "
                "WHERE relationship_type IN ('tracked') OR relationship_type IS NULL "
                "ORDER BY id"
            )
        ]

    flagged: list[dict] = []
    for pid in pids:
        result = audit_pid(db, pid)
        if result["n_clusters"] >= 2:
            flagged.append(result)

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
```

- [ ] **Solis 4: Palaiž testus, pārliecinies, ka iztur**

Palaiž: `pytest tests/test_vad_family_clusters_audit.py -v`

Sagaidāmais: 5 PASS.

- [ ] **Solis 5: Palaiž skriptu pret reālo DB, fiksē baseline**

Palaiž: `python scripts/audit_vad_family_clusters.py > .scratch_audit_baseline.txt`

Sagaidāmais: ~18 politiķi flagged. Saglabā .scratch_audit_baseline.txt repo root (negitignored, lai pēc cleanup salīdzina). Verificē, ka 5 mērķa politiķi (PID 101, 104, 107, 116, 132) **ir** sarakstā.

- [ ] **Solis 6: Commit**

```bash
git add scripts/audit_vad_family_clusters.py tests/test_vad_family_clusters_audit.py
git commit -F .git-commit-msg.tmp
```

`.git-commit-msg.tmp` saturs:

```
feat(vad): audit_vad_family_clusters.py — homonīmu detekcijas gate

Atrod 2+ disjoint immediate-family klasterus per tracked politiķis (laulātais
+ bērni signature pārklāšanās). Reāls cilvēks paralēlām deklarācijām saglabā
to pašu kodola ģimeni; disjoint klasteri = homonīmu kontaminācija.

Baseline: ~18 politiķi flagged. 5 ar tiešu ietekmi uz publicēto VAD analīzi
(Inese Kalniņa, Līga Kļaviņa, Jānis Skrastiņš, Gatis Liepiņš, Linda Liepiņa)
— tos sanē Phase 2 plānā 2026-05-05-vad-homonimu-sanacija.md.

Pārējie ~13 ir vēsturiski pre-Saeima homonīmi, kas neietekmē 2024-25
ranking tabulas, bet jādokumentē atlikušajiem audita ciklam.
```

---

## B FĀZE — Per-politiķis sanācija

Katra T2-T6 uzdevums seko vienam un tam pašam shēmam: (1) verificē klasterus, (2) izlemj patieso whitelist, (3) atjaunina DB caur `seed_homonimu_phase2_disambig.py`, (4) palaiž `cleanup_contaminated_vad.py --politician X --reingest`, (5) verificē ar audita skriptu, ka pid sanāk uz 1 klasteri.

### T2 — Inese Kalniņa (PID 101) sanācija

**Konteksts:** Trīs disjoint ģimenes klasteri: (A) Saeimas deputāte ar bērniem Kārlis/Vija/Zane Feldmane, (B) LNA Nodaļas vadītāja ar krievu ģimeni Kudrjačeva/Kudrjačovs, (C) Tiesu administrācijas direktora vietniece ar vīru Uldi un meitām Anete/Marta. Tikai A ir mūsu tracked Saeimas deputāte (JV). Pašreizējais `vad_disambig` whitelist (`scripts/seed_vad_disambig.py:24`) iekļauj visas 3 institūcijas → kļūda Phase 1.5.

**Faili:**
- Izveido: `scripts/seed_homonimu_phase2_disambig.py` (jauns, satur konfigurāciju visiem 5 pidiem)
- Modificē: DB `tracked_politicians WHERE id=101` (`keywords`)
- DELETE: 31 `vad_declarations` rindas (id NOT IN (3408–3412))

- [ ] **Solis 1: Verificē klasterus ar audita skriptu**

Palaiž: `python scripts/audit_vad_family_clusters.py --pid 101`

Sagaidāmais output:
```
PID 101  Inese Kalniņa  (36 dekl, 2-3 klasteri)
   [1] 12 dekl: 3418, 3419, 3420, ...
       ģimene: Laulātais:ULDIS KALNIŅŠ, Meita:ANETE RUSKA, Meita:MARTA MITŅIČUKA
   [2] 5 dekl: 3408, 3409, 3410, 3411, 3412
       ģimene: Dēls:KĀRLIS KALNIŅŠ, Meita:VIJA KALNIŅA, Meita:ZANE FELDMANE
   [3] (LNA — Person B nav laulātā/bērnu, var iekrist tikai vienā klasteri ar parsing tukšumu)
```

Piezīme: Person B (LNA) ģimenes records nesatur Laulātais/Dēls/Meita (tikai māte/tēvs/brālis/māsa) — algoritmā tā signature ir tukša un tiek izlaista. Tas nozīmē, ka audita skripts atklās tikai A vs C; B identificēšana balstās uz citiem signāliem (institūcija = LNA un nav A vai C).

- [ ] **Solis 2: Sastāda jauno seed skriptu ar šaurinātu whitelist**

Izveido `scripts/seed_homonimu_phase2_disambig.py`:

```python
"""Seed Phase 2 — sašauri 5 pids whitelist pēc 2026-05-05 audita.

Atklājumi: Phase 1.5 disambig whitelist Inese Kalniņa, Līga Kļaviņa, Jānis
Skrastiņš, Gatis Liepiņš (kuram nebija nekāda whitelist), Linda Liepiņa
iekļāva institūcijas, kas faktiski pieder homonīmiem (citiem cilvēkiem ar to
pašu vārdu un uzvārdu). Ģimenes locekļu sarakstu disjoint klasteri
(scripts/audit_vad_family_clusters.py) ir gold standard pierādījums.

Idempotents.

Apstiprinātie atklājumi:
- pid 101 Inese Kalniņa: TIKAI Saeima (LNA un Tiesu adm = 2 atšķirīgi homonīmi)
- pid 104 Līga Kļaviņa:  TIKAI Saeima (FM = atšķirīgs cilvēks ar citu vīru un meitu)
- pid 107 Linda Liepiņa: TIKAI Saeima (KNAB = atšķirīgs cilvēks ar vīru Ingu)
- pid 116 Gatis Liepiņš: TIKAI Saeima (Valsts policija = atšķirīgs cilvēks)
- pid 132 Jānis Skrastiņš: TIKAI Saeima (Tieslietu ministrija/notārs = atšķ.)
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from src.db import get_db  # noqa: E402

CONFIGS: list[dict] = [
    {
        "pid": 101, "name": "Inese Kalniņa",
        "vad_disambig": ["Saeimas deputāts", "Saeimas deputāte", "Latvijas Republikas Saeima"],
        "negative_patterns": ["Tiesu administrācija", "Latvijas Nacionālais arhīvs"],
    },
    {
        "pid": 104, "name": "Līga Kļaviņa",
        "vad_disambig": ["Saeimas deputāts", "Saeimas deputāte", "Latvijas Republikas Saeima"],
        "negative_patterns": ["Finanšu ministrija", "Altum"],
    },
    {
        "pid": 107, "name": "Linda Liepiņa",
        "vad_disambig": ["Saeimas deputāts", "Saeimas deputāte", "Latvijas Republikas Saeima"],
        "negative_patterns": ["Korupcijas novēršanas un apkarošanas birojs"],
    },
    {
        "pid": 116, "name": "Gatis Liepiņš",
        "vad_disambig": ["Saeimas deputāts", "Saeimas deputāte", "Latvijas Republikas Saeima"],
        "negative_patterns": ["Valsts policija", "Ieslodzījuma vietu pārvalde"],
    },
    {
        "pid": 132, "name": "Jānis Skrastiņš",
        "vad_disambig": ["Saeimas deputāts", "Saeimas deputāte", "Latvijas Republikas Saeima"],
        "negative_patterns": ["Tieslietu ministrija", "Zvērināts notārs", "ZNB"],
    },
]


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    db = get_db()
    for cfg in CONFIGS:
        row = db.execute(
            "SELECT name, keywords, negative_patterns FROM tracked_politicians WHERE id = ?",
            (cfg["pid"],),
        ).fetchone()
        if row is None:
            print(f"[skip] pid={cfg['pid']} not found")
            continue
        if row["name"] != cfg["name"]:
            print(f"[warn] pid={cfg['pid']} name mismatch: expected {cfg['name']!r}, got {row['name']!r}")

        existing: dict | list = []
        if row["keywords"]:
            try:
                existing = json.loads(row["keywords"])
            except json.JSONDecodeError:
                existing = []
        if isinstance(existing, list):
            existing = {"tags": existing} if existing else {}
        existing["vad_disambig"] = cfg["vad_disambig"]

        db.execute(
            "UPDATE tracked_politicians SET keywords = ?, negative_patterns = ? WHERE id = ?",
            (
                json.dumps(existing, ensure_ascii=False),
                json.dumps(cfg["negative_patterns"], ensure_ascii=False),
                cfg["pid"],
            ),
        )
        print(f"[ok]  pid={cfg['pid']:>3} {row['name']:<22} "
              f"vad_disambig={cfg['vad_disambig']} neg={cfg['negative_patterns']}")
    db.commit()
    print(f"\n[done] {len(CONFIGS)} pids updated")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Solis 3: Palaiž seed skriptu (uzraksta whitelist + negative patterns DB)**

Palaiž: `python scripts/seed_homonimu_phase2_disambig.py`

Sagaidāmais output: 5 `[ok]` rindas. Verificē DB:

```bash
py -c "import sqlite3, json; con=sqlite3.connect('data/atmina.db'); print(json.loads(con.execute('SELECT keywords FROM tracked_politicians WHERE id=101').fetchone()[0]))"
```

Sagaidāmais: `{'vad_disambig': ['Saeimas deputāts', 'Saeimas deputāte', 'Latvijas Republikas Saeima'], ...}`.

- [ ] **Solis 4: Dry-run cleanup, verificē DELETE skaitļus**

Palaiž: `python scripts/cleanup_contaminated_vad.py --politician "Inese Kalniņa" --dry-run`

Sagaidāmais output: `[plan] DELETE 36 declarations from 1 pid(s)`. Tas DELETE visas 36 dekl; pēc reingest ar šaurinātu whitelist atgriežas tikai 5 (Saeimas dekl A klasteris).

- [ ] **Solis 5: Reālā cleanup + reingest**

Palaiž: `python scripts/cleanup_contaminated_vad.py --politician "Inese Kalniņa" --reingest`

Sagaidāmais output (~3-5 minūtes VID throttle dēļ):
```
[plan] single-pid mode: pid=101 Inese Kalniņa
[plan] DELETE 36 declarations from 1 pid(s)
[done] DELETE: 36 -> 0
[reingest] sweep 1 pid(s) ar disambig filter aktīvu
[1/1] pid=101 Inese Kalniņa
  ...
  exit=0 (XXX.Xs)
```

- [ ] **Solis 6: Verificē klastera saplūšanu uz 1**

Palaiž: `python scripts/audit_vad_family_clusters.py --pid 101`

Sagaidāmais: `[ok] 1 politiķi auditēti, 0 ar disjoint family clusters`. Ja vēl 2+ klasteri — `negative_patterns` nepilnīgs. Atgriežas Solis 2 pielāgojumam.

- [ ] **Solis 7: Verificē, ka deklarāciju skaits = 5 (Saeima A klasteris)**

```bash
py -c "import sqlite3; con=sqlite3.connect('data/atmina.db'); print(con.execute('SELECT COUNT(*), GROUP_CONCAT(declaration_year), GROUP_CONCAT(institution) FROM vad_declarations WHERE opponent_id=101').fetchone())"
```

Sagaidāmais: `(5, '2025,2024,2023,2022,(start)', 'Latvijas Republikas Saeima,...')`.

- [ ] **Solis 8: Commit**

```bash
git add scripts/seed_homonimu_phase2_disambig.py
git commit -F .git-commit-msg.tmp
```

`.git-commit-msg.tmp`:

```
fix(vad): pid 101 Inese Kalniņa — sašaurināts whitelist Saeima only

3 disjoint family clusters apstiprināti audita gaitā: (A) Saeimas deputāte
JV ar bērniem Kārlis/Vija/Zane Feldmane, (B) LNA Nodaļas vadītāja ar krievu
ģimeni Kudrjačeva/Kudrjačovs, (C) Tiesu administrācijas direktora vietniece
ar vīru Uldi un meitām Anete/Marta. Phase 1.5 whitelist iekļāva visas 3
institūcijas pieņemot, ka tas ir viens cilvēks ar 3 paralēliem amatiem —
nepatiess pieņēmums, ko atklāja ģimenes locekļu krustpārbaude.

Sanācija: vad_disambig sašaurināts uz Saeima only, negative_patterns
nobloķē Tiesu adm un LNA. Cleanup + reingest atstāj 5 dekl (4 Saeima
ikgadējās 2022-2025 + 1 start 2022-11-30).

Skat. plānu docs/superpowers/plans/2026-05-05-vad-homonimu-sanacija.md T2.
```

### T3 — Līga Kļaviņa (PID 104) sanācija

**Konteksts:** Analīzes #1 ar 239 664 EUR. Saeimas deputātes ģimene (vīrs Vilnis Kļaviņš, meita Ilze, tēvs Elmārs Dzērve) vs FM valsts sekretāra vietnieces ģimene (vīrs Andžejs Kļaviņš, meita Emīlija, brāļi/māsa Vanagi). Atšķirīgi vīri = atšķirīgi cilvēki. Pirms cleanup obligāti **manuāli verificē**, vai ZZS Saeimas deputāte Līga Kļaviņa nav strādājusi FM kā paralēlais amats — publiskie avoti norāda, ka viņa ir bijusi finanšu nozares sieviete, bet paralēla deputāte + valsts sekretāra vietniece ir reglamentēti aizliegta kombinācija.

**Faili:**
- Modificē: DB `tracked_politicians WHERE id=104` (caur seed skriptu, jau definēts T2 Solis 2)
- DELETE: ~22 `vad_declarations` rindas (id 3458-3471 atskaitot 3469-3471 + 2025 ikgadējo 3472)

- [ ] **Solis 1: Manuāla identitātes apstiprināšana publiskajos avotos**

Atver Wikipedia Latvijas un titanic.lv ZZS deputātu sarakstu. Pārbauda, ka Līga Kļaviņa ir 14. Saeimas deputāte, kāda ir viņas iepriekšējā darba vieta (publiski jābūt informācijai). Salīdzina ar pirms-Saeima Finanšu ministrijas valsts sekretāra vietniece "Līga Kļaviņa" — Wikipedia rāda 1972. dzimšanas gadu un ir atsevišķa persona.

Tāpat verificē izglītības profilu (vēsturiska izglītība): ZZS deputāte ir publiskots dzīvesgājuma profils — ja izglītība un karjera nesakrīt ar FM valsts sekretāra vietnieces karjeru, homonīms apstiprināts.

- [ ] **Solis 2: Verificē klasterus**

Palaiž: `python scripts/audit_vad_family_clusters.py --pid 104`

Sagaidāmais: 2 klasteri.

- [ ] **Solis 3: Palaiž seed skriptu (jau izpildīts T2 Solis 3 vienlaicīgi visiem 5 pidiem)**

Tā kā `seed_homonimu_phase2_disambig.py` apstrādā visus 5 pidiem, T2 Solis 3 šo jau ir izdarījis.

Verificē: `py -c "import sqlite3, json; con=sqlite3.connect('data/atmina.db'); print(json.loads(con.execute('SELECT keywords FROM tracked_politicians WHERE id=104').fetchone()[0])['vad_disambig'])"`

Sagaidāmais: `['Saeimas deputāts', 'Saeimas deputāte', 'Latvijas Republikas Saeima']`.

- [ ] **Solis 4: Dry-run + cleanup + reingest**

Palaiž:
```bash
python scripts/cleanup_contaminated_vad.py --politician "Līga Kļaviņa" --dry-run
python scripts/cleanup_contaminated_vad.py --politician "Līga Kļaviņa" --reingest
```

Sagaidāmais: dry-run rāda 14 dekl, pēc reingest atstāj ~4 (2022-2025 Saeima ikgadējās).

- [ ] **Solis 5: Verificē audit**

Palaiž: `python scripts/audit_vad_family_clusters.py --pid 104`

Sagaidāmais: tīri (1 klasteris vai 0).

- [ ] **Solis 6: Verificē final dekl skaitu un institūcijas**

Sagaidāmais: 4 dekl, visas Saeima.

- [ ] **Solis 7: Commit**

```bash
git commit -F .git-commit-msg.tmp -- --allow-empty
```

`.git-commit-msg.tmp`:

```
fix(vad): pid 104 Līga Kļaviņa — sašaurināts whitelist Saeima only

2 disjoint family clusters: (A) ZZS Saeimas deputāte ar vīru Vilni
Kļaviņu, meitu Ilzi, tēvu Elmāru Dzērvi; (B) FM valsts sekretāra
vietniece ar vīru Andžeju Kļaviņu, meitu Emīliju, brāļiem Vanagiem.

Atšķirīgi vīri = atšķirīgi cilvēki, paralēla deputāte + valsts sekretāra
vietniece reglamentēti aizliegta kombinācija. Phase 1.5 whitelist iekļāva
"Finanšu ministrija" — kļūda; izņemts.

Cleanup atstāj 4 dekl (2022-2025 Saeima ikgadējās). Skat. plānu T3.
```

### T4 — Linda Liepiņa (PID 107) sanācija

**Konteksts:** Saeimas deputāte (māte Edīte, māsa Baiba, dēls Toms Francis Provejs) vs KNAB Vecākais inspektors (vīrs Ingus Liepiņš, tēvs Aivis Nusbergs, māte Ilze Cielava). Phase 1.5 whitelist iekļāva "Korupcijas novēršanas un apkarošanas birojs" pieņemot, ka KNAB ir Lindas Liepiņas pirms-Saeima darba vieta — patiesībā tas ir atšķirīgs cilvēks ar to pašu vārdu un uzvārdu.

**Faili:**
- Modificē: DB `tracked_politicians WHERE id=107` (caur seed skriptu, jau definēts T2 Solis 2)
- DELETE: ~16 `vad_declarations` rindas (KNAB klasteris)

- [ ] **Solis 1: Manuāla LPV deputātes Lindas Liepiņas identitātes apstiprināšana**

Atver Wikipedia LPV deputātu sarakstu vai LPV oficiālo lapu. Pārbauda Lindas Liepiņas publisko CV — vai viņa kādreiz bijusi KNAB Vecākais inspektors? KNAB Vecākais inspektors ir specifisks dienesta amats; ja LPV deputātes biogrāfijā tas neparādās, homonīms apstiprināts.

- [ ] **Solis 2: Verificē klasterus**

Palaiž: `python scripts/audit_vad_family_clusters.py --pid 107`

Sagaidāmais: 2 klasteri (Saeima ar dēlu Toms Francis vs KNAB ar vīru Ingu).

- [ ] **Solis 3: Verificē, ka seed skripts ir piemērots (jau veikts T2 Solis 3 visiem 5 pidiem reizē)**

Verificē DB:
```bash
py -c "import sqlite3, json; con=sqlite3.connect('data/atmina.db'); print(json.loads(con.execute('SELECT keywords FROM tracked_politicians WHERE id=107').fetchone()[0])['vad_disambig']); print(json.loads(con.execute('SELECT negative_patterns FROM tracked_politicians WHERE id=107').fetchone()[0]))"
```

Sagaidāmais: `['Saeimas deputāts', 'Saeimas deputāte', 'Latvijas Republikas Saeima']` un `['Korupcijas novēršanas un apkarošanas birojs']`.

- [ ] **Solis 4: Dry-run cleanup**

Palaiž: `python scripts/cleanup_contaminated_vad.py --politician "Linda Liepiņa" --dry-run`

Sagaidāmais: rāda esošo dekl skaitu (~16).

- [ ] **Solis 5: Reālā cleanup + reingest**

Palaiž: `python scripts/cleanup_contaminated_vad.py --politician "Linda Liepiņa" --reingest`

VID throttle (10s) → izpilde aptuveni 2-4 min.

- [ ] **Solis 6: Verificē klastera saplūšanu uz 1**

Palaiž: `python scripts/audit_vad_family_clusters.py --pid 107`

Sagaidāmais: tīri (1 klasteris). Ja vēl 2+ — pielāgo `negative_patterns` (atgriežas T2 seed skriptā).

- [ ] **Solis 7: Verificē final dekl skaitu un institūcijas**

```bash
py -c "import sqlite3; con=sqlite3.connect('data/atmina.db'); print(con.execute('SELECT COUNT(*), GROUP_CONCAT(DISTINCT institution) FROM vad_declarations WHERE opponent_id=107').fetchone())"
```

Sagaidāmais: ~5 dekl (Saeima ikgadējās + iespējamais start), institūcija = "Latvijas Republikas Saeima".

- [ ] **Solis 8: Commit**

```bash
git commit -F .git-commit-msg.tmp --allow-empty
```

`.git-commit-msg.tmp`:

```
fix(vad): pid 107 Linda Liepiņa — sašaurināts whitelist Saeima only

KNAB Vecākais inspektors ar atšķirīgu ģimeni (vīrs Ingus Liepiņš, tēvs
Aivis Nusbergs, māte Ilze Cielava) ir homonīms, ne Lindas Liepiņas
pirms-Saeima darba vieta. Phase 1.5 whitelist iekļāva KNAB pieņemot
paralēlu darbu — kļūda; izņemts.

Cleanup atstāj N dekl (visas Saeima). Skat. plānu T4.
```

### T5 — Gatis Liepiņš (PID 116) sanācija

**Konteksts:** Phase 1.5 NEBIJA disambig sarakstā (whitelist tukš → trust full-name search). Tāpēc visas Valsts policijas Jaunākā inspektora deklarācijas (atšķirīgs cilvēks ar meitu Anete Liepiņa, vecākiem Anda + Valdis) tika piesaistītas Saeimas deputātam (sieva Justīne, brālis Ralfs Litaunieks). Tagad **pievienojam** whitelist pirmo reizi.

**Faili:**
- Modificē: DB `tracked_politicians WHERE id=116` (caur seed skriptu, jau definēts T2 Solis 2)
- DELETE: ~9 `vad_declarations` rindas (Valsts policija + Ieslodzījuma vietu pārvalde klasteris)

- [ ] **Solis 1: Manuāla JV deputāta Gata Liepiņa identitātes apstiprināšana**

Atver Wikipedia JV deputātu sarakstu vai Saeimas oficiālo deputāta profilu (saeima.lv/14/deputati). Pārbauda Gata Liepiņa publisko CV — vai bijis Valsts policijas inspektors vai Ieslodzījuma vietu pārvaldes amats? Ja nē → homonīms apstiprināts.

- [ ] **Solis 2: Verificē klasterus**

Palaiž: `python scripts/audit_vad_family_clusters.py --pid 116`

Sagaidāmais: 2 klasteri (Saeima ar sievu Justīne vs Valsts policija ar meitu Anete Liepiņa).

- [ ] **Solis 3: Verificē seed skripts piemērots**

```bash
py -c "import sqlite3, json; con=sqlite3.connect('data/atmina.db'); print(json.loads(con.execute('SELECT keywords FROM tracked_politicians WHERE id=116').fetchone()[0])['vad_disambig']); print(json.loads(con.execute('SELECT negative_patterns FROM tracked_politicians WHERE id=116').fetchone()[0]))"
```

Sagaidāmais: `['Saeimas deputāts', ...]` un `['Valsts policija', 'Ieslodzījuma vietu pārvalde']`.

- [ ] **Solis 4: Dry-run cleanup**

Palaiž: `python scripts/cleanup_contaminated_vad.py --politician "Gatis Liepiņš" --dry-run`

- [ ] **Solis 5: Reālā cleanup + reingest**

Palaiž: `python scripts/cleanup_contaminated_vad.py --politician "Gatis Liepiņš" --reingest`

- [ ] **Solis 6: Verificē klastera saplūšana uz 1**

Palaiž: `python scripts/audit_vad_family_clusters.py --pid 116`

Sagaidāmais: tīri.

- [ ] **Solis 7: Verificē final dekl skaitu**

```bash
py -c "import sqlite3; con=sqlite3.connect('data/atmina.db'); print(con.execute('SELECT COUNT(*), GROUP_CONCAT(DISTINCT institution) FROM vad_declarations WHERE opponent_id=116').fetchone())"
```

Sagaidāmais: 4 dekl (2022-2025 Saeima ikgadējās), institūcija = "Latvijas Republikas Saeima".

- [ ] **Solis 8: Commit**

```bash
git commit -F .git-commit-msg.tmp --allow-empty
```

`.git-commit-msg.tmp`:

```
fix(vad): pid 116 Gatis Liepiņš — pievienots Saeima-only whitelist

Phase 1.5 šis pid nebija disambig sarakstā, tāpēc Valsts policijas
Jaunākais inspektors (atšķirīgs cilvēks ar meitu Anete Liepiņa, vecākiem
Anda+Valdis) tika piesaistīts Saeimas deputātam (sieva Justīne, brālis
Ralfs Litaunieks). Pievienota whitelist Saeima only + Valsts policija
+ Ieslodzījuma vietu pārvalde negative_patterns.

Cleanup atstāj 4 dekl (2022-2025 Saeima). Skat. plānu T5.
```

### T6 — Jānis Skrastiņš (PID 132) sanācija

**Konteksts:** Analīzes #8 ar 157 767 EUR. Saeimas deputāts (sieva Ilze, dēli Artūrs+Elvis, māsas Elita+Rasma) vs Zvērināts notārs Tieslietu ministrijā ZNB SIA (meita Monta, tēvs Ivars). Phase 1.5 whitelist iekļāva "Tieslietu ministrija" pieņemot paralēlu darbu — patiesībā homonīms. Notariāta likuma 4. panta 1. daļā noteikts, ka zvērināts notārs nedrīkst būt deputāts.

**Faili:**
- Modificē: DB `tracked_politicians WHERE id=132` (caur seed skriptu, jau definēts T2 Solis 2)
- DELETE: ~10 `vad_declarations` rindas (Tieslietu ministrija + ZNB klasteris)

- [ ] **Solis 1: Manuāla JV deputāta Jāņa Skrastiņa identitātes apstiprināšana**

Atver Saeimas oficiālo deputāta profilu (saeima.lv/14/deputati). Pārbauda, vai bijis vai ir zvērināts notārs paralēli ar deputāta amatu. Notariāta likums to liedz; tāpēc paralēla "Tieslietu ministrija — Zvērināts notārs" deklarācija = homonīms.

- [ ] **Solis 2: Verificē klasterus**

Palaiž: `python scripts/audit_vad_family_clusters.py --pid 132`

Sagaidāmais: 2-3 klasteri.

- [ ] **Solis 3: Verificē seed skripts piemērots**

```bash
py -c "import sqlite3, json; con=sqlite3.connect('data/atmina.db'); print(json.loads(con.execute('SELECT keywords FROM tracked_politicians WHERE id=132').fetchone()[0])['vad_disambig']); print(json.loads(con.execute('SELECT negative_patterns FROM tracked_politicians WHERE id=132').fetchone()[0]))"
```

Sagaidāmais: `['Saeimas deputāts', ...]` un `['Tieslietu ministrija', 'Zvērināts notārs', 'ZNB']`.

- [ ] **Solis 4: Dry-run cleanup**

Palaiž: `python scripts/cleanup_contaminated_vad.py --politician "Jānis Skrastiņš" --dry-run`

- [ ] **Solis 5: Reālā cleanup + reingest**

Palaiž: `python scripts/cleanup_contaminated_vad.py --politician "Jānis Skrastiņš" --reingest`

- [ ] **Solis 6: Verificē klastera saplūšana uz 1**

Palaiž: `python scripts/audit_vad_family_clusters.py --pid 132`

Sagaidāmais: tīri.

- [ ] **Solis 7: Verificē final dekl skaitu**

```bash
py -c "import sqlite3; con=sqlite3.connect('data/atmina.db'); print(con.execute('SELECT COUNT(*), GROUP_CONCAT(DISTINCT institution) FROM vad_declarations WHERE opponent_id=132').fetchone())"
```

Sagaidāmais: 4 dekl (2022-2025 Saeima ikgadējās), institūcija = "Latvijas Republikas Saeima".

- [ ] **Solis 8: Commit**

```bash
git commit -F .git-commit-msg.tmp --allow-empty
```

`.git-commit-msg.tmp`:

```
fix(vad): pid 132 Jānis Skrastiņš — sašaurināts whitelist Saeima only

Zvērināts notārs Tieslietu ministrijā ZNB SIA ar atšķirīgu ģimeni (meita
Monta, tēvs Ivars) ir homonīms, ne JV deputāta paralēlais amats.
Notariāta likuma 4. panta 1. daļa liedz notāra praksi paralēli deputāta
amatam. Phase 1.5 whitelist iekļāva "Tieslietu ministrija" — kļūda;
izņemts.

Cleanup atstāj 4 dekl (2022-2025 Saeima). Skat. plānu T6.
```

---

## C FĀZE — Parsēšanas defekta izmeklēšana

### T7 — Atklāj un fixē intra-deklarācijas dublēto ienākumu rindu defektu

**Konteksts:** Pirms cleanup, pid=101 decl 3429 (Tiesu administrācijas 2024 ikgadējā Person C) saturēja 4 ienākumu rindas, kur Tiesu adm alga 57 704 EUR un VSAA pensija 24 318 EUR bija dublētas. Pēc cleanup šī decl ir izdzēsta, bet defekts var pastāvēt arī citās deklarācijās. Šī fāze atklāj un, ja apstiprināms, fixē parsēšanas loģiku.

**Faili:**
- Izveido: `scripts/audit_vad_intra_decl_dups.py` (vienreizējs)
- Iespējami modificē: `src/vad/parsing.py`
- Iespējami papildina: `tests/test_vad_parsing.py`

- [ ] **Solis 1: Uzraksta scratch skripts, kas pārbauda ALL `vad_income` uz dubultām (decl_id, source, source_reg_number, income_type, amount, currency) tuples**

```python
# scripts/audit_vad_intra_decl_dups.py
import sqlite3, sys
con = sqlite3.connect('data/atmina.db')
cur = con.cursor()
cur.execute("""
    SELECT declaration_id, source, source_reg_number, income_type, amount, currency,
           COUNT(*) AS n
    FROM vad_income
    GROUP BY declaration_id, source, source_reg_number, income_type, amount, currency
    HAVING n > 1
    ORDER BY n DESC, declaration_id
    LIMIT 50
""")
rows = cur.fetchall()
print(f"Atrasti {len(rows)} dubulti tuple")
for r in rows:
    print(r)
```

Palaiž; ja 0 dubulti → defekts atsevišķs Person C decl 3429 gadījumam (jau dzēsts), nav nepieciešams parser fix. Ja >0 → turpina ar Solis 2.

- [ ] **Solis 2: Atrod sākotnējo HTML un reproducē parser bug (ja 0 dubulti — izlaiž)**

Atrod `vad_declarations.raw_html` ailē sākotnējo HTML duplikātu deklarācijai. Pārbauda vai tabulā tiešām ir 4 rindas un parser kļūdaini sadala vai dublē. Iespējami iemesli: BeautifulSoup `find_all("tr")` iekļauj header rinas; `<tbody>` iebūvēts divreiz HTML pļuras dēļ; CSS-display none rindas tiek skaitītas.

- [ ] **Solis 3: Uzraksta failējošo testu ar tieši reproducējamo HTML fragmentu (ja parser fix nepieciešams)**

Pievieno `tests/test_vad_parsing.py` jaunu test_case ar īsu HTML inline parauga rindu.

- [ ] **Solis 4: Implementē fix**

Pielāgo `src/vad/parsing.py` deduplicēt rindas pirms `vad_income` insert (iekšējais dedup uz to pašu tuple kā audita skriptā).

- [ ] **Solis 5: Palaiž testus + commits**

Palaiž `pytest tests/test_vad_parsing.py -v` un `bash scripts/check.sh`. Commits.

---

## D FĀZE — Analīzes pārrakstīšana + render

### T8 — Pārrēķina § 2 top-15 ranking

**Konteksts:** Pēc 5 pidu cleanup, kopējais 2024 ienākumu top-15 saraksts mainās. Iepriekšējā #1 (Kļaviņa 239k) un #2 (Kalniņa 184k) nu zaudē mākslīgos pārklājumus, atstājot tikai patiesos Saeimas + LU ienākumus. Top-15 tagad jāpārrēķina no DB.

**Faili:**
- Lasa: `data/atmina.db`
- Modificē: `content/analizes/vad-2026.md` (§ 2 tabula)

- [ ] **Solis 1: Uzraksta scratch skriptu vai SQL, kas atkārto top-15 aggregation queriju**

Atrod analīzes generatora vietu — varbūt `scripts/_aggregate_vad_2026.py` vai inline SQL `content/analizes/vad-2026.md` priekšā. Ja nav esoša scripta, uzraksta minimal scriptu, kas:
- Apvieno `vad_income.amount` per (opponent_id, year), DISTINCT uz (source, source_reg_number, income_type, amount) četrinieku (dedup).
- Izlasa visus opponent_id ar `relationship_type IN ('tracked')` un kuram ir 2024 dekl.
- Sakārto pēc summas DESC, izlasa top 20.

```python
# scratch_recompute_top15.py
import sqlite3
con = sqlite3.connect('data/atmina.db')
cur = con.cursor()
cur.execute("""
SELECT p.id, p.name, p.party,
       SUM(amount) AS total
FROM (
    SELECT DISTINCT d.opponent_id, i.source, i.source_reg_number, i.income_type, i.amount
    FROM vad_income i
    JOIN vad_declarations d ON d.id = i.declaration_id
    WHERE d.declaration_year = 2024 AND i.currency = 'EUR'
) AS dedup
JOIN tracked_politicians p ON p.id = dedup.opponent_id
WHERE p.relationship_type = 'tracked' OR p.relationship_type IS NULL
GROUP BY p.id, p.name, p.party
ORDER BY total DESC
LIMIT 20
""")
for r in cur.fetchall():
    print(r)
```

Sagaidāmais: jaunā kārtība bez Kalniņas un Kļaviņas (varbūt arī bez Skrastiņa) augšā.

- [ ] **Solis 2: Modificē `content/analizes/vad-2026.md` § 2 tabulu ar jaunajiem skaitļiem**

Lasi tabulu rindas 124-214 (15 ieraksti). Atjauni #1, #2, #8, ja nepieciešams arī #11, un papildini saraksta beigas ar nu jaunpienākušo #15 vietā nokļuvušo politiķi.

- [ ] **Solis 3: Modificē § 218 piezīmes**

Iepriekšējā piezīme par "Inese Kalniņa strādā trīs paralēlos amatos" ir izdzēšama. Pēc cleanup viņa arī nav top-15.

Iepriekšējā piezīme par "Līga Kļaviņa Saeimas deputāte un vienlaikus FM valsts sekretāra vietniece" arī izdzēšama, ja Kļaviņa nepaliek #1; vai pārrakstāma, ja apstiprinās, ka analīzē norādītā Saeimas deputāte tiešām bija FM valsts sekretāra vietniece.

Pievieno jaunu piezīmi: "2026-05-05 sanācija — 5 papildu profili tīri (Kalniņa, Kļaviņa, Skrastiņš, Gatis Liepiņš, Linda Liepiņa); ģimenes locekļu klasteri pierādīja, ka Phase 1.5 atstāja kontamināciju ar institūcijām, kas pieder homonīmiem".

- [ ] **Solis 4: Modificē § 325 metodikas paragrafu**

Patreizējā formulējumā: "dedup noņem 2 atkārtotus ierakstus / 82 022 EUR (abi Ineses Kalniņas Tiesu administrācijas un LU algas, kas parādījās divās viņas paralēlās deklarācijās)".

Pārraksta uz: "dedup noņem N atkārtotus ierakstus / X EUR (intra-deklarācijas parsēšanas dublikāti — atsevišķs problēmas atzars, kas bija sakrišanā ar Phase 2 sanāciju). Skat. § 9 par sanāciju". Konkrēti skaitļi N un X tiek pārrēķināti pēc cleanup; iespējami pat tikt uz 0, ja Person C 3429 deklarācija (kur dublikāti bija) ir izdzēsta un nav citu intra-decl dublikātu (T7 atklāj).

- [ ] **Solis 5: Atjaunina § 9 (sanācijas hronika) ar Phase 2 ierakstu**

Pievieno apakšsekciju: "**2026-05-05 audita Phase 2** — papildu 5 homonīmu sanācija (Inese Kalniņa, Līga Kļaviņa, Jānis Skrastiņš, Gatis Liepiņš, Linda Liepiņa). Atklāts ar `scripts/audit_vad_family_clusters.py` ģimenes locekļu disjoint klastera signālu. Kopā Phase 1.5 + audita T1-T11 + Phase 2 = 20 sanēti pidi. Total 2262 - X dekl. Profila lapas atjauninātas, top-15 pārrēķināts."

- [ ] **Solis 6: Commit**

```bash
git add content/analizes/vad-2026.md
git commit -F .git-commit-msg.tmp
```

`.git-commit-msg.tmp`:

```
docs(vad): § 2 + § 218 + § 325 atjaunoti pēc Phase 2 sanācijas

5 homonīmu pidu cleanup (T2-T6) maina 2024 top-15 ranking — Inese
Kalniņa un Līga Kļaviņa zaudē mākslīgos pārklājumus, izkrīt no top-15.
§ 218 piezīmes par "paralēliem amatiem" izdzēstas (faktoloģiski
nepatiesi). § 325 metodikas paragrafs precizēts, jo iepriekš minētā
"Tiesu administrācijas un LU algas" dedup faktiski bija intra-deklarācijas
parsēšanas dublikātu fix (atsevišķs problēmas atzars, T7).

§ 9 papildināts ar Phase 2 hronikas ierakstu.
```

### T9 — Audita skripts + render + deploy

**Faili:**
- Lasa: `data/atmina.db`
- Izveido: `output/atmina/**` (caur generate_public_site)

- [ ] **Solis 1: Palaiž profila-match audit**

Palaiž: `python scripts/audit_vad_profile_match.py`

Sagaidāmais: PASS (analīzes top-N skaitļi 1:1 sakrīt ar profila lapām).

- [ ] **Solis 2: Palaiž family-cluster audit pret visiem 152**

Palaiž: `python scripts/audit_vad_family_clusters.py > .scratch_audit_post_phase2.txt`

Salīdzini ar T1 Solis 5 baseline (`.scratch_audit_baseline.txt`). Sagaidāmais: 5 mērķa pidi vairs nav flagged. Atlikušie ~13 vēsturiski homonīmi (pre-Saeima) — dokumentē atsevišķi T11.

- [ ] **Solis 3: Render full site**

Palaiž: `bash scripts/check.sh` (lai pārliecinās ruff + pytest + render smoke iztur).

Pēc tam: `python -c "from src.render import generate_public_site; generate_public_site()"`.

- [ ] **Solis 4: Verificē `output/atmina/analizes/vad-2026.html` un atskaitās politiķu profila lapās (Kalniņa, Kļaviņa, Skrastiņš, Gatis Liepiņš, Linda Liepiņa)**

Pārbauda HTML ar Grep'u, ka:
- `output/atmina/politiki/inese-kalnina.html` vairs neminē "KUDRJAČEVS" vai "ANETE RUSKA".
- `output/atmina/politiki/liga-klavina.html` vairs neminē "ANDŽEJS KĻAVIŅŠ" vai "EMĪLIJA KĻAVIŅA".
- analīzē § 2 tabulas pirmā rinda ir jaunā #1 politiķis.

- [ ] **Solis 5: Commit + deploy**

```bash
git add output/  # vai pārvieto uz `git checkout master && rebase`, atkarībā no deploy konvencijas
git commit -F .git-commit-msg.tmp
```

Deploy plūsma: skat. `wiki/operations/operacijas.md`.

---

## E FĀZE — Plašā skenēšana + memory

### T10 — Visu 152 politiķu klastera audit triāža

**Konteksts:** T1 Solis 5 baseline norāda ~18 flagged politiķus. 5 sanēti Phase B. Atlikušie ~13 jāklasificē trijās kategorijās: (a) **homonīms** (atšķirīgs cilvēks, jāsanē), (b) **legitīma izmaiņa** (laulības/šķiršanās — vārda maiņa, bērnu pievienošana), (c) **parsēšanas vai whitespace artefakts** (tas pats cilvēks, divas variantas).

**Faili:**
- Lasa: `.scratch_audit_post_phase2.txt`
- Izveido: `docs/audits/2026-05-05-vad-residual-clusters.md` (atsevišķs)

- [ ] **Solis 1: Manuāli izlasi katru atlikušo flagged pid'u**

Sagaidāmie kandidāti (no T1 Solis 5 baseline): Ināra Mūrniece (73), Oļegs Burovs (74), Ingrīda Circene (78), Aiva Vīksna (141), Jānis Dombrava (6), Andris Sprūds (16), Edgars Tāvars (52), Artūrs Butāns (82), Ligita Gintere (93), Dace Melbārde (155), Reinis Uzulnieks (159), Mārtiņš Štāls (173), Jānis Zalāns (186).

- [ ] **Solis 2: Klasificē katru un raksti audita ziņojumu**

Izveido `docs/audits/2026-05-05-vad-residual-clusters.md` ar tabulu (pid, vārds, klasteru skaits, klasifikācija, ietekme uz analīzi 2024-25, plānotā darbība).

- [ ] **Solis 3: Sanē "homonīms" kategorijas pidus, kas ietekmē 2024-25**

Ja nav 2024-25 ietekmes — atstāj tos atkļūdošanai nākamajā ciklā ar piezīmi audita ziņojumā.

- [ ] **Solis 4: Commit audita ziņojumu**

### T11 — CHANGELOG + memory atjaunošana

**Faili:**
- Modificē: `wiki/CHANGELOG.md`
- Modificē: `~/.claude/projects/C--Users-The-User-atmina/memory/project_vad_done.md`

- [ ] **Solis 1: Pievieno CHANGELOG ierakstu**

```markdown
### 2026-05-05 — VAD Phase 2: 5 papildu homonīmu sanācija

Audita gaitā ar jauno `scripts/audit_vad_family_clusters.py` skriptu atklāti 5
papildu pidi ar disjoint immediate-family klasteriem starp paralēlām
deklarācijām — pierādījums, ka Phase 1.5 whitelist bija par plašs un
iekļāva institūcijas, kas pieder homonīmiem (citiem cilvēkiem ar to pašu
vārdu+uzvārdu):

- pid 101 Inese Kalniņa — atstājusi 5 dekl no 36
- pid 104 Līga Kļaviņa — atstājusi 4 dekl no 14
- pid 107 Linda Liepiņa — atstājusi N dekl no M
- pid 116 Gatis Liepiņš — atstājusi 4 dekl no N (pirmoreiz pievienots whitelist)
- pid 132 Jānis Skrastiņš — atstājusi 4 dekl no N

§ 2 top-15, § 218 piezīmes un § 325 metodika atjaunotas. § 9 sanācijas
hronikā pievienots Phase 2 ieraksts. Family-cluster audita skripts ir
turpmāks pre-publish gate.
```

- [ ] **Solis 2: Atjaunina memory**

Modificē `project_vad_done.md`:
- Atjaunini description ar Phase 2 datumu
- Pievieno sadaļu "**Phase 2 sanācija (2026-05-05)**" ar 5 sanētiem pidiem un norādi uz audita skriptu
- Atjaunini total dekl skaitu

- [ ] **Solis 3: Commit**

```bash
git add wiki/CHANGELOG.md
git commit -F .git-commit-msg.tmp
```

`.git-commit-msg.tmp`:

```
docs(wiki): CHANGELOG 2026-05-05 — VAD Phase 2 homonīmu sanācija

5 papildu pidi sanēti pēc 2026-05-03 publicēšanas: Kalniņa, Kļaviņa,
Skrastiņš, Gatis Liepiņš, Linda Liepiņa. Family-cluster audita skripts
ir turpmāks pre-publish gate.
```

---

## Risku reģistrs

- **VID portāla rate-limit (10s/search)** var padarīt 5 reingest sekvenču izpildi par ~3-5 minūtēm katrai. Plānot izpildi vakarā, kad VID nav peak load.
- **Manuālas identitātes apstiprināšanas solis** (T3-T6 Solis 1) prasa VID portāla atvēršanu pārlūkā un publisko avotu pārbaudi. Ja konkrētam politiķim publiski nav pierādīta CV, var atstāt whitelist plašāku, bet nepublicēt ranking analīzē.
- **Render skripts var norādīt iepriekšējā cache** uz vecajām profila lapām. Pirms commit pārliecinies, ka `output/atmina/politiki/<5-slug>.html` ir reģenerēti (modification time pēc cleanup).
- **DB cleanup nav rollback'iable** bez backup. Pirms T2 cleanup paņem snapshot: `cp data/atmina.db data/atmina.db.pre-vad-phase2-$(date +%Y%m%d-%H%M%S)`.
- **Phase 1.5 disambig saraksts** (`scripts/seed_vad_disambig.py`) saturēs novecojušas konfigurācijas pēc Phase 2 — atstāj kā vēsturisku, bet pievieno komentāru pirms `HINTS = [...]`, kas norāda uz Phase 2 kā oficiālo avotu 5 izlabotajiem pidiem.

---

## Atkarību grafiks

```
T1 (audita skripts + testi)
  ↓
T2-T6 (5 politiķu cleanup; var izpildīt paralēli, bet jāizpilda secīgi, jo `cleanup_contaminated_vad.py` viens pid vienlaikus, un VID throttle)
  ↓
T7 (parsing dup izmeklēšana — paralēli ar T8/T9)
  ↓
T8 (analīzes pārrakstīšana)
  ↓
T9 (audit + render + deploy)
  ↓
T10 (plašā triāža)
  ↓
T11 (CHANGELOG + memory)
```
