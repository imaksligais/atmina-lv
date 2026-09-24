"""Ģenerē `content/analizes/vad-2026.md` skaitļus no DB (lasīšanas režīms).

Lapa ir statisks Markdown ar rokām ieliktiem skaitļiem — līdz 2026-09-20 tie
stāvēja no 2026-05-05 un četrus mēnešus dreifēja (homonīmu tīrīšanas, 288
jaunas deklarācijas, parsera labojumi). Šis skripts ir «vaicājums, kas radīja
skaitli» (CLAUDE.md § Working Conventions): katra lapas tabula te ir viena
funkcija ar to pašu metodi, ko lapa apraksta tekstā.

Metodes (nemainīt bez lapas teksta maiņas):
- ienākumi: TIKAI `declaration_kind='annual'` par fiskālo gadu, TIKAI EUR,
  atkārtojumi izslēgti pēc `(politiķis, avots, ienākuma veids, summa)` —
  paralēlu amatu deklarācijas atkārto vienu un to pašu ienākumu sarakstu;
- uzņēmumu / NĪ skaits: profila metode (`compute_section_deltas` — jaunākā
  ikgadējā deklarācija, unikālas atslēgas + iepriekšējā gada «aizgāja» rindas),
  identiski `scripts/compute_vad_profile_counts.py`;
- tikai aktīvie izsekotie (`relationship_type != 'inactive'`).

Lietošana:
    .venv/Scripts/python.exe scripts/vad_analysis_numbers.py --year 2025
"""

from __future__ import annotations

import argparse
import sys
from collections import Counter, defaultdict
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from src.db import get_db  # noqa: E402
from src.lv_text import slugify  # noqa: E402
from src.vad.diff import compute_section_deltas  # noqa: E402

PARTY_ABBREV = {
    "Zaļo un Zemnieku savienība": "ZZS",
    "Jaunā Vienotība": "JV",
    "Nacionālā apvienība": "NA",
    "Progresīvie": "PRO",
    "Apvienotais saraksts": "AS",
    "Latvija Pirmajā Vietā": "LPV",
    "Stabilitātei!": "Stab",
    "Bezpartejisks": "Bezp",
    "Mums Mēs Nepiedosim": "MMN",
    "MMN": "MMN",
    "Austošā Saule Latvijai": "ASL",
    "ASL": "ASL",
    "JKP": "JKP",
    "Kopā Latvijai": "KL",
    "Saskaņa": "Sask",
    "Suverēnā vara": "SV",
    "Latvijas attīstībai": "LA",
}


def plink(name: str) -> str:
    """Politiķa vārds kā saite uz profilu (lapa dzīvo analizes/, tāpēc ../).
    Slugs = tas pats `slugify`, ko lieto profilu renders (src/render/politicians.py)."""
    return f"[{name}](../politiki/{slugify(name)}.html)"


def short_party(p: str | None) -> str:
    return PARTY_ABBREV.get(p or "", p or "—")


def fmt(n: float) -> str:
    return f"{int(round(n)):,}".replace(",", " ")


def active_politicians(db) -> dict[int, dict]:
    return {
        r["id"]: dict(r)
        for r in db.execute(
            "SELECT id, name, party FROM tracked_politicians "
            "WHERE relationship_type != 'inactive'"
        )
    }


# ---------------------------------------------------------------- § 1
def section_dataset(db, pols):
    ids = tuple(pols)
    q = ",".join("?" * len(ids))
    n = db.execute(f"SELECT COUNT(*) FROM vad_declarations WHERE opponent_id IN ({q})", ids).fetchone()[0]
    npol = db.execute(f"SELECT COUNT(DISTINCT opponent_id) FROM vad_declarations WHERE opponent_id IN ({q})", ids).fetchone()[0]
    yrs = db.execute(f"SELECT MIN(declaration_year), MAX(declaration_year) FROM vad_declarations WHERE opponent_id IN ({q})", ids).fetchone()
    kinds = dict(db.execute(f"SELECT declaration_kind, COUNT(*) FROM vad_declarations WHERE opponent_id IN ({q}) GROUP BY 1", ids).fetchall())
    print("## § 1 Datu kopa")
    print(f"- deklarācijas: {n}; politiķi ar deklarācijām (aktīvie): {npol}; gadi {yrs[0]}–{yrs[1]} ({yrs[1]-yrs[0]+1} gadi)")
    print(f"- pa veidiem: {kinds}")
    print()


# ---------------------------------------------------------------- ienākumi
def income_rows(db, pols, year):
    """Unikālie EUR ienākumu ieraksti par fiskālo gadu (ikgadējās deklarācijas)."""
    q = ",".join("?" * len(pols))
    rows = db.execute(
        f"""SELECT d.opponent_id pid, i.source, i.income_type, i.amount, i.currency
            FROM vad_income i JOIN vad_declarations d ON d.id = i.declaration_id
            WHERE d.declaration_kind = 'annual' AND d.declaration_year = ?
              AND d.opponent_id IN ({q})""",
        (year, *pols),
    ).fetchall()
    seen = set()
    eur, non_eur = [], Counter()
    for r in rows:
        key = (r["pid"], (r["source"] or "").strip().upper(), (r["income_type"] or "").strip(), round(float(r["amount"] or 0), 2), r["currency"])
        if key in seen:
            continue
        seen.add(key)
        if r["currency"] == "EUR":
            eur.append(key)
        else:
            non_eur[r["currency"]] += 1
    return eur, non_eur


def income_by_pol(eur):
    tot = defaultdict(float)
    for pid, _src, _typ, amt, _cur in eur:
        tot[pid] += amt
    return tot


def section_income_top(db, pols, year, n=15):
    eur, non_eur = income_rows(db, pols, year)
    tot = income_by_pol(eur)
    top = sorted(tot.items(), key=lambda kv: -kv[1])[:n]
    print(f"## § 2 Lielākie kopējā ienākuma deklarētāji {year}. gadā (top {n})")
    print("| # | Politiķis | Partija | Ienākums (EUR) |")
    print("|---|-----------|---------|----------------|")
    for i, (pid, s) in enumerate(top, 1):
        print(f"| {i} | {plink(pols[pid]['name'])} | {short_party(pols[pid]['party'])} | {fmt(s)} |")
    print()
    # amatu līnija top-N (kontekstam)
    q = ",".join("?" * len(top))
    for pid, s in top:
        pos = db.execute(
            "SELECT DISTINCT institution, position_title FROM vad_declarations WHERE opponent_id=? AND declaration_kind='annual' AND declaration_year=?",
            (pid, year),
        ).fetchall()
        srcs = Counter()
        for p2, src, typ, amt, _ in eur:
            if p2 == pid:
                srcs[src[:45]] += amt
        print(f"  - {pols[pid]['name']}: {[(p['institution'][:35], p['position_title'][:30]) for p in pos]} | avoti: {[(k, fmt(v)) for k, v in srcs.most_common(4)]}")
    print()
    return eur, non_eur, tot


def section_income_types(eur, non_eur, year, tot):
    by_type = defaultdict(lambda: [0, 0.0])
    for _pid, _src, typ, amt, _cur in eur:
        by_type[typ][0] += 1
        by_type[typ][1] += amt
    total = sum(v[1] for v in by_type.values())
    print(f"## § 3 Ienākumu sastāvs {year}. gadā (pa veidiem)")
    print("| Veids | Unikāli ieraksti | Kopā EUR |")
    print("|-------|------------------|----------|")
    for typ, (c, s) in sorted(by_type.items(), key=lambda kv: -kv[1][1]):
        print(f"| {typ} | {c} | {fmt(s)} |")
    print(f"\n**Kopā:** {fmt(total)} EUR no {len(eur)} unikāliem EUR ierakstiem {len(tot)} politiķiem.")
    top3 = sorted(by_type.items(), key=lambda kv: -kv[1][1])[:3]
    print("  procenti:", [(t, f"{s/total*100:.1f}%") for t, (c, s) in top3])
    print(f"  ne-EUR rindas: {dict(non_eur)}")
    print()


def section_yoy(db, pols, year, prev_eur_tot, cur_tot, n=10, threshold=5000):
    rows = []
    for pid, cur in cur_tot.items():
        prev = prev_eur_tot.get(pid, 0.0)
        if prev < threshold:
            continue
        rows.append((pid, prev, cur, cur - prev, (cur - prev) / prev * 100))
    rows.sort(key=lambda r: -r[4])
    print(f"## § 4 Lielākie ienākuma pieaugumi {year-1} → {year} (top {n}, {year-1}. gadā ≥ {threshold} EUR)")
    print(f"| Politiķis | Partija | {year-1} EUR | {year} EUR | Izmaiņa EUR | Izmaiņa % |")
    print("|-----------|---------|----------|----------|-------------|-----------|")
    for pid, prev, cur, d, pct in rows[:n]:
        print(f"| {plink(pols[pid]['name'])} | {short_party(pols[pid]['party'])} | {fmt(prev)} | {fmt(cur)} | {'+' if d >= 0 else ''}{fmt(d)} | {'+' if pct >= 0 else ''}{pct:.0f}% |")
    print()
    print("  amatu maiņa top-N (deklarāciju iestāde/amats prev → cur):")
    for pid, prev, cur, d, pct in rows[:n]:
        a = db.execute("SELECT DISTINCT institution, position_title FROM vad_declarations WHERE opponent_id=? AND declaration_kind='annual' AND declaration_year=?", (pid, year - 1)).fetchall()
        b = db.execute("SELECT DISTINCT institution, position_title FROM vad_declarations WHERE opponent_id=? AND declaration_kind='annual' AND declaration_year=?", (pid, year)).fetchall()
        print(f"  - {pols[pid]['name']}: {[(x['institution'][:30], x['position_title'][:28]) for x in a]} → {[(x['institution'][:30], x['position_title'][:28]) for x in b]}")
    print()
    # pilns saraksts arī zem sliekšņa — lai varētu minēt konkrētus cilvēkus
    print("  atsauces (visi ar abiem gadiem, pct):")
    allrows = []
    for pid, cur in cur_tot.items():
        prev = prev_eur_tot.get(pid, 0.0)
        if prev > 0:
            allrows.append((pols[pid]["name"], round(prev), round(cur), round((cur - prev) / prev * 100)))
    for r in sorted(allrows, key=lambda r: -r[2])[:20]:
        print("   ", r)
    print()


# ---------------------------------------------------------------- profila skaiti (§ 5/§ 6)
def profile_counts(db, pols):
    out = defaultdict(list)  # section -> [(pid, year, count)]
    for pid in pols:
        decls = db.execute(
            "SELECT id, declaration_year, declaration_kind FROM vad_declarations WHERE opponent_id=? "
            "ORDER BY COALESCE(declaration_year,0) DESC, published_at DESC",
            (pid,),
        ).fetchall()
        if not decls:
            continue
        ids = [d["id"] for d in decls]
        q = ",".join("?" * len(ids))
        rows = {"real_estate": defaultdict(list), "companies": defaultdict(list)}
        for sec, tbl in (("real_estate", "vad_real_estate"), ("companies", "vad_companies")):
            for r in db.execute(f"SELECT * FROM {tbl} WHERE declaration_id IN ({q})", ids):
                d = dict(r)
                rows[sec][d["declaration_id"]].append(d)
        for i, decl in enumerate(decls):
            if decl["declaration_kind"] != "annual":
                continue
            prev_id = decls[i + 1]["id"] if i + 1 < len(decls) else None
            for sec in rows:
                deltas = compute_section_deltas(sec, rows[sec].get(prev_id, []) if prev_id else [], rows[sec].get(decl["id"], []))
                cur = sum(1 for x in deltas if x.delta != "removed")
                rem = len(deltas) - cur
                prev_year = decls[i + 1]["declaration_year"] if i + 1 < len(decls) else None
                out[sec].append((pid, decl["declaration_year"], cur, rem, len(deltas), prev_year))
            break
    return out


def section_profile_top(pols, counts, sec, title, n, label):
    """Kārto pēc PAŠREIZĒJO unikālo ierakstu skaita jaunākajā ikgadējā deklarācijā
    (tas, ko virsraksts sola); profila skaitlis (pašreizējie + iepriekšējā gadā
    «aizgājušie») paliek atsevišķā kolonnā — to pret profilu pārbauda
    scripts/audit_vad_profile_match.py."""
    rows = sorted(counts[sec], key=lambda r: (-r[2], -r[4], pols[r[0]]["name"].split()[-1]))
    print(f"## {title} (top {n}, pēc pašreizējiem)")
    print(f"| # | Politiķis | Partija | Gads | Pašreizējie | Aizgāja | {label} |")
    print("|---|-----------|---------|------|-------------|---------|--------|")
    for i, (pid, y, cur, rem, tot, py) in enumerate(rows[:n], 1):
        print(f"| {i} | {plink(pols[pid]['name'])} | {short_party(pols[pid]['party'])} | {y} | {cur} | {rem}{f' (pret {py})' if py and py != y - 1 else ''} | {tot} |")
    print()
    return rows[:n]


def section_company_values(db, pols, year, n=10):
    q = ",".join("?" * len(pols))
    rows = db.execute(
        f"""SELECT d.opponent_id pid, c.company_name, c.total_value, c.currency
            FROM vad_companies c JOIN vad_declarations d ON d.id=c.declaration_id
            WHERE d.declaration_kind='annual' AND d.declaration_year=? AND d.opponent_id IN ({q})
              AND c.total_value IS NOT NULL AND c.total_value > 0""",
        (year, *pols),
    ).fetchall()
    seen = set()
    eur, other = [], defaultdict(list)
    for r in rows:
        key = (r["pid"], (r["company_name"] or "").strip().upper(), r["currency"], round(float(r["total_value"]), 2))
        if key in seen:
            continue
        seen.add(key)
        if r["currency"] == "EUR":
            eur.append((r["pid"], r["company_name"], float(r["total_value"])))
        else:
            other[(r["pid"], r["currency"])].append((r["company_name"], float(r["total_value"])))
    eur.sort(key=lambda r: -r[2])
    print(f"## § 5b Lielākās individuālās kapitāldaļas pēc EUR vērtības ({year}) (top {n})")
    print("| # | Politiķis | Partija | Uzņēmums | Vērtība EUR |")
    print("|---|-----------|---------|----------|-------------|")
    for i, (pid, name, v) in enumerate(eur[:n], 1):
        print(f"| {i} | {plink(pols[pid]['name'])} | {short_party(pols[pid]['party'])} | {name} | {fmt(v)} |")
    print()
    print(f"## § 5c USD/GBP kapitāldaļas ({year})")
    print("| Politiķis | Partija | Paketes | Kopvērtība | Galvenās pozīcijas |")
    print("|-----------|---------|---------|------------|---------------------|")
    for (pid, cur), items in sorted(other.items(), key=lambda kv: -sum(v for _, v in kv[1])):
        items.sort(key=lambda t: -t[1])
        print(f"| {plink(pols[pid]['name'])} | {short_party(pols[pid]['party'])} | {len(items)} | {cur} {fmt(sum(v for _, v in items))} | {', '.join(nm[:28] for nm, _ in items[:5])} |")
    print()


def section_dombrava_history(db, pols):
    r = db.execute("SELECT id FROM tracked_politicians WHERE name LIKE 'Jānis Dombrava%'").fetchone()
    if not r:
        return
    pid = r[0]
    hist = db.execute("SELECT COUNT(*), COUNT(DISTINCT d.declaration_year) FROM vad_companies c JOIN vad_declarations d ON d.id=c.declaration_id WHERE d.opponent_id=?", (pid,)).fetchone()
    print(f"  Dombrava: kumulatīvi {hist[0]} uzņēmumu ieraksti {hist[1]} gados")
    names = db.execute("SELECT c.company_name, c.total_value, c.currency FROM vad_companies c JOIN vad_declarations d ON d.id=c.declaration_id WHERE d.opponent_id=? AND d.declaration_kind='annual' AND d.declaration_year=(SELECT MAX(declaration_year) FROM vad_declarations WHERE opponent_id=? AND declaration_kind='annual')", (pid, pid)).fetchall()
    print("  Dombrava jaunākā ikgadējā:", [(n[0][:28], n[1], n[2]) for n in names])
    print()


# ---------------------------------------------------------------- § 6 NĪ
def section_real_estate_stats(db, pols, year):
    q = ",".join("?" * len(pols))
    rows = db.execute(
        f"""SELECT r.property_type, r.location, r.ownership_status
            FROM vad_real_estate r JOIN vad_declarations d ON d.id=r.declaration_id
            WHERE d.declaration_kind='annual' AND d.declaration_year=? AND d.opponent_id IN ({q})""",
        (year, *pols),
    ).fetchall()
    types = Counter((r["property_type"] or "-").strip() for r in rows)
    statuses = Counter((r["ownership_status"] or "-").strip().capitalize() for r in rows)
    locs = Counter()
    for r in rows:
        loc = (r["location"] or "").strip()
        parts = [p.strip() for p in loc.split(",")]
        if len(parts) >= 2 and parts[0] == "Latvija":
            locs[parts[1]] += 1
        elif loc:
            locs[loc] += 1
    print(f"## § 6b NĪ tipi ({year}. gada ikgadējo deklarāciju ieraksti, n={len(rows)})")
    for k, v in types.most_common(8):
        print(f"| {k} | {v} |")
    print("\n## § 6c Īpašumtiesību veidi")
    for k, v in statuses.most_common(8):
        print(f"| {k} | {v} |")
    print("\n## § 6d Atrašanās vieta (top 12)")
    for k, v in locs.most_common(12):
        print(f"{k} — {v}")
    print()
    # ārvalstu īpašumi visā kopā
    frows = db.execute(
        f"""SELECT tp.name, r.location, r.property_type, d.declaration_year
            FROM vad_real_estate r JOIN vad_declarations d ON d.id=r.declaration_id
            JOIN tracked_politicians tp ON tp.id=d.opponent_id
            WHERE d.opponent_id IN ({q}) AND r.location IS NOT NULL AND r.location != ''
              AND r.location NOT LIKE 'Latvija%'""",
        pols and tuple(pols),
    ).fetchall()
    by = defaultdict(lambda: {"n": 0, "types": Counter(), "years": set(), "loc": Counter()})
    for r in frows:
        b = by[r["name"]]
        b["n"] += 1
        b["types"][(r["property_type"] or "-")] += 1
        b["years"].add(r["declaration_year"])
        b["loc"][r["location"][:40]] += 1
    print(f"## § 6e Ārvalstu īpašumi (visi gadi): {len(frows)} ieraksti, {len(by)} politiķi")
    for name, b in sorted(by.items(), key=lambda kv: -kv[1]["n"]):
        yrs = sorted(y for y in b["years"] if y)
        print(f"- {name}: {b['n']} ieraksti, {dict(b['types'])}, gadi {yrs[0] if yrs else '?'}–{yrs[-1] if yrs else '?'}, {dict(b['loc'])}")
    print()


# ---------------------------------------------------------------- § 7 ģimene
def section_family(db, pols):
    q = ",".join("?" * len(pols))
    rows = db.execute(
        f"""SELECT f.relation, COUNT(*) n, COUNT(DISTINCT d.opponent_id || '|' || UPPER(TRIM(f.full_name))) u
            FROM vad_family f JOIN vad_declarations d ON d.id=f.declaration_id
            WHERE d.opponent_id IN ({q}) GROUP BY f.relation ORDER BY n DESC""",
        tuple(pols),
    ).fetchall()
    print("## § 7 Ģimenes locekļi (visi gadi)")
    print("| Saistība | Ieraksti | Unikāli cilvēki |")
    print("|----------|----------|-----------------|")
    for r in rows:
        print(f"| {r['relation']} | {r['n']} | {r['u']} |")
    print()


def section_berzina(db):
    r = db.execute("SELECT id FROM tracked_politicians WHERE name LIKE 'Inga Bērziņa%'").fetchone()
    if r:
        rows = db.execute("SELECT declaration_year, declaration_kind, institution FROM vad_declarations WHERE opponent_id=? ORDER BY declaration_year", (r[0],)).fetchall()
        print("## § 9 Inga Bērziņa:", [(x[0], x[1], (x[2] or "")[:25]) for x in rows])
        print()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--year", type=int, default=2025)
    args = ap.parse_args()
    year = args.year
    db = get_db()
    pols = active_politicians(db)
    section_dataset(db, pols)
    eur, non_eur, tot = section_income_top(db, pols, year)
    section_income_types(eur, non_eur, year, tot)
    prev_eur, _, prev_tot = income_rows(db, pols, year - 1), None, None
    prev_tot = income_by_pol(prev_eur[0])
    section_yoy(db, pols, year, prev_tot, tot)
    counts = profile_counts(db, pols)
    section_profile_top(pols, counts, "companies", "§ 5 Lielākie uzņēmumu deklarētāji (jaunākā ikgadējā)", 10, "Uzņēmumi")
    section_dombrava_history(db, pols)
    section_company_values(db, pols, year)
    section_profile_top(pols, counts, "real_estate", "§ 6 Lielākie NĪ deklarētāji (jaunākā ikgadējā)", 15, "NĪ")
    section_real_estate_stats(db, pols, year)
    section_family(db, pols)
    section_berzina(db)


if __name__ == "__main__":
    main()
