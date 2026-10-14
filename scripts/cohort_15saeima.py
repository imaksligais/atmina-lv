"""15. Saeimas jauno deputātu kohorta — dati, priekšskatījums, SQL.

Plāns: docs/plans/2026-10-05-15-saeimas-deputati.md. `build` lasa CVK
aprēķinu (gitignored) un raksta komitējamu data/seed/15saeima_kohorta.yaml.
DB tikai lasa. Rakstīšana — tikai `emit-sql` izvadītais fails, ko operators
apstiprina un izpilda (vārti B).
"""
from __future__ import annotations

import argparse
import json
import re
import sqlite3
import sys
import time
import unicodedata
from datetime import date
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

CALC = REPO / "data/cvk_snapshots/SV2026/ievēlētie_aprēķins_20261004_final.json"
OUT = REPO / "data/seed/15saeima_kohorta.yaml"
PREVIEW_OUT = REPO / "docs/drafts/15saeima_preview.md"

from src.matcher import (  # noqa: E402
    _INFLECTION_COMMON_WORD_BLOCKLIST,
    _caps_form,
    _latvian_surname_inflections,
    _occurrences,
)

LISTS = {  # list_nr → (short, party konvencija DB)
    7: ("AS", "Apvienotais saraksts"),
    8: ("LPV", "Latvija Pirmajā Vietā"),
    1: ("SV/AJ", "Suverēnā vara/Jaunlatvieši"),
    5: ("NA", "Nacionālā apvienība"),
    14: ("PRO", "Progresīvie"),
    9: ("JV", "Jaunā Vienotība"),
}
# Vārdabrāļi esošajos profilos (plāna tabula) — dokumentācija, ne sargs.
HOMONYMS = {"Eduards Zivtiņš": 153, "Vjačeslavs Stepaņenko": 236,
            "Nellija Kleinberga": 5, "Dana Šlesere": 3}
# Galotnes heiristika (-a/-e = sieviete) kļūdās abos virzienos; izņēmumi
# no kohortas acs pārbaudes (Step 5).
FEMALE_EXCEPTIONS: set[str] = set()  # sieviešu vārdi, kas NEbeidzas ar -a/-e
MALE_EXCEPTIONS: set[str] = set()  # vīriešu vārdi, kas beidzas ar -a/-e


def ascii_fold(s: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", s)
                   if unicodedata.category(c) != "Mn")


def is_female(first_name: str) -> bool:
    if first_name in MALE_EXCEPTIONS:
        return False
    return first_name in FEMALE_EXCEPTIONS or first_name[-1] in "ae"


def make_role(list_short: str, region: str, female: bool) -> str:
    return f"15. Saeimā {'ievēlēta' if female else 'ievēlēts'} — {list_short}, {region}"


def _forms(name: str) -> list[str]:
    surname = name.split()[-1]
    base = [name, surname]
    folded = [ascii_fold(f) for f in base if ascii_fold(f) != f]
    return base + folded


def build_cohort(calc: dict, tracked_names: set[str]) -> list[dict]:
    rows = []
    for e in calc["elected"]:
        if e["name"] in tracked_names:
            continue
        first, surname = e["name"].split()[0], e["name"].split()[-1]
        short, party = LISTS[e["list_nr"]]
        female = is_female(first)
        rows.append({
            "name": e["name"], "first": first, "surname": surname, "female": female,
            "list_nr": e["list_nr"], "list_short": short, "party": party,
            "region": e["region"], "pos": e["pos"], "score": e["score"], "rank": e["rank"],
            "name_forms": _forms(e["name"]),
            "role": make_role(short, e["region"], female),
            "x_handle": None, "x_evidence": None,
            "homonym_of": HOMONYMS.get(e["name"]), "common_word": None, "notes": None,
        })
    return rows


def _tracked_names(db_path: Path) -> set[str]:
    db = sqlite3.connect(f"file:{db_path.as_posix()}?mode=ro", uri=True)
    try:
        return {r[0] for r in db.execute("SELECT name FROM tracked_politicians")}
    finally:
        db.close()


def _ro(db_path: Path) -> sqlite3.Connection:
    return sqlite3.connect(f"file:{db_path.as_posix()}?mode=ro", uri=True)


# --- Task 2: sadursmju priekšskatījums ---------------------------------------

def form_family(surname: str) -> list[str]:
    return [surname, *_latvian_surname_inflections(surname)]


def matcher_forms(tp_rows) -> dict[int, list[str]]:
    """Formas, ar kurām matcher tiešām meklē katru esošo profilu.

    Spogulis funkcijai `src.matcher._load_politician_forms`: VISAS
    tracked_politicians rindas (matcher nefiltrē pēc relationship_type —
    arī 'inactive'/'neutral' tiek meklēti); journalist/organization saņem
    tikai saglabātās formas; pārējiem kailais uzvārds pēc tiem pašiem
    nosacījumiem + uzvārda locījumi bez _INFLECTION_COMMON_WORD_BLOCKLIST.
    `tp_rows` = (id, name, name_forms_json, relationship_type)."""
    out: dict[int, list[str]] = {}
    for pid, name, forms_json, rel in tp_rows:
        forms = json.loads(forms_json) if forms_json else []
        parts = name.split()
        institutional = rel in ("journalist", "organization")
        if parts:
            if not forms:
                forms = [name, parts[-1]] if len(parts) >= 2 and not institutional else [name]
            elif len(parts) >= 2 and not institutional:
                if f"{parts[0]} {parts[-1]}" in forms and parts[-1] not in forms:
                    forms = forms + [parts[-1]]
            if len(parts) >= 2 and not parts[-1].startswith("@") and not institutional:
                for f in _latvian_surname_inflections(parts[-1]):
                    if f not in forms and f.lower() not in _INFLECTION_COMMON_WORD_BLOCKLIST:
                        forms = forms + [f]
        out[pid] = forms
    return out


def _row_forms(r: dict) -> list[str]:
    return list(dict.fromkeys([*r["name_forms"], *form_family(r["surname"])]))


def _lower_word_hits(texts: list[str], form: str) -> int:
    """Dokumenti, kur forma parādās kā mazo burtu VĀRDS (sadzīves vārda
    signāls: «ābola», «dimants»). Tikai viena vārda formām."""
    if " " in form:
        return 0
    rx = re.compile(r"(?<![^\W\d_])" + re.escape(form.lower()) + r"(?![^\W\d_])")
    return sum(1 for t in texts if rx.search(t))


def preview_rows(rows, existing_forms, doc_texts, *, doc_texts_by_name=None,
                 docs_scanned=None):
    """Katra kohortas forma: trāpījumi dokumentos (_occurrences — tā pati
    vārdu robežas + ALL-CAPS semantika kā matcher), ≤4 zīmju karogs,
    esošie pid ar to pašu formu. `doc_texts_by_name` ļauj padot katram
    deputātam savu (SQL priekšfiltrētu) dokumentu kopu; `docs_scanned`
    tad ir visa loga saucējs, ne priekšfiltra izmērs."""
    owner: dict[str, list[int]] = {}
    for pid, forms in existing_forms.items():
        for f in forms:
            owner.setdefault(f, []).append(pid)
    scanned = len(doc_texts) if docs_scanned is None else docs_scanned
    out = []
    for r in rows:
        texts = doc_texts if doc_texts_by_name is None else doc_texts_by_name.get(r["name"], [])
        for f in _row_forms(r):
            out.append({
                "name": r["name"], "form": f,
                "hits": sum(1 for t in texts if _occurrences(t, f)),
                "lower_hits": _lower_word_hits(texts, f),
                "docs_scanned": scanned,
                "short": " " not in f and len(f) <= 4,
                "shared_with": sorted(set(owner.get(f, []))),
            })
    return out


def _like_terms(r: dict) -> list[str]:
    terms: set[str] = set()
    for f in _row_forms(r):
        terms.update({f, f.lower()})
        up = _caps_form(f)
        if up:
            terms.add(up)
    return sorted(terms)


# --- Task 2: SQL izvade -------------------------------------------------------

def fold_name(name: str) -> str:
    return " ".join(ascii_fold(name).lower().split())


def existing_name_collisions(rows, existing_names) -> list[tuple[str, str]]:
    """(kohortas vārds, esošais vārds) pāri, kas sakrīt pēc ASCII-locīšanas,
    mazajiem burtiem un atstarpju saspiešanas. Ne-tukšs = emit-sql STOP:
    rollback dzēš pēc `name`, tātad izdzēstu jau esošu rindu."""
    by_fold: dict[str, list[str]] = {}
    for n in existing_names:
        by_fold.setdefault(fold_name(n), []).append(n)
    return [(r["name"], e) for r in rows for e in by_fold.get(fold_name(r["name"]), [])]


def _norm_handle(h: str) -> str:
    return h.strip().lstrip("@").lower()


def handle_collisions(rows, existing) -> list[str]:
    """Kohortas X kontu sadursmes, salīdzinot bez reģistra un `@`.

    `existing` = (avots, pid, handle) trijnieki no social_accounts.handle un
    tracked_politicians.x_handle. Ne-tukšs = emit-sql STOP: citādi forward
    vai nu ieliktu dublikātu (KBurane vs kburane), vai klusi izlaistu
    social_accounts rindu, kamēr tracked_politicians.x_handle tiktu ierakstīts
    — abas tabulas atšķirtos un neviens to neziņotu. Arī dublikāts pašā
    kohortā ir STOP."""
    out: list[str] = []
    seen: dict[str, str] = {}
    for r in rows:
        if not r.get("x_handle"):
            continue
        h = _norm_handle(r["x_handle"])
        if h in seen:
            out.append(f"{r['name']!r} @{r['x_handle']} ~ kohortā jau {seen[h]!r}")
        else:
            seen[h] = r["name"]
    for src, pid, handle in existing:
        if handle and _norm_handle(handle) in seen:
            out.append(f"{seen[_norm_handle(handle)]!r} ~ esošais {src} pid={pid} @{handle}")
    return out


def _q(s: str | None) -> str:
    return "NULL" if s is None else "'" + s.replace("'", "''") + "'"


def emit_sql(rows):
    fwd, rb = ["BEGIN;"], ["BEGIN;"]
    for r in rows:
        n = _q(r["name"])
        fwd.append(
            "INSERT INTO tracked_politicians (name, name_forms, relationship_type, party, role, x_handle) "
            f"SELECT {n}, {_q(json.dumps(r['name_forms'], ensure_ascii=False))}, 'tracked', "
            f"{_q(r['party'])}, {_q(r['role'])}, {_q(r['x_handle'])} "
            f"WHERE NOT EXISTS (SELECT 1 FROM tracked_politicians WHERE name = {n});")
        if r["x_handle"]:
            fwd.append(
                "INSERT INTO social_accounts (opponent_id, platform, handle, feed_type, active) "
                f"SELECT id, 'twitter', {_q(r['x_handle'])}, 'first_party', 1 FROM tracked_politicians "
                f"WHERE name = {n} AND NOT EXISTS (SELECT 1 FROM social_accounts s "
                f"WHERE lower(s.handle) = lower({_q(r['x_handle'])}));")
            rb.append("DELETE FROM social_accounts WHERE opponent_id = "
                      f"(SELECT id FROM tracked_politicians WHERE name = {n});")
    for r in rows:
        rb.append(f"DELETE FROM tracked_politicians WHERE name = {_q(r['name'])};")
    return "\n".join(fwd + ["COMMIT;"]), "\n".join(rb + ["COMMIT;"])


# --- CLI ----------------------------------------------------------------------

# Plāna (Step 5) sadzīves vārdu kandidāti ar skaidrojumu; papildu kandidātus
# atklāj mazo burtu trāpījumu kolonna (lower_hits).
COMMON_WORD_CANDIDATES = {
    "Dimants": "«dimants» — dārgakmens",
    "Putniņš": "«putniņš» — mazs putns",
    "Ābola": "«ābola» — vārda «ābols» ģenitīvs",
    "Āboliņš": "«āboliņš» — auga nosaukums",
    "Dārznieks": "«dārznieks» — profesija",
    "Ozoliņš": "«ozoliņš» — mazs ozols",
    "Lazdiņš": "«lazdiņa» — maza lazda (sakrīt ar ģenitīvu)",
    "Caunītis": "«caunīte» — maza cauna (sakrīt akuzatīvs «caunīti»)",
    "Kārkliņš": "«kārkliņš» — mazs kārkls",
    "Apine": "«apini» — vārda «apinis» akuzatīvs (augs)",
    "Kraps": "plānā minēts kandidāts; sk. mazo burtu trāpījumus",
}


def _md_table(header: list[str], rows: list[list]) -> list[str]:
    out = ["| " + " | ".join(header) + " |", "|" + "---|" * len(header)]
    out += ["| " + " | ".join(str(c) for c in r) + " |" for r in rows]
    return out


def render_preview(cohort, out, names: dict[int, str], docs_scanned: int,
                   runtime_s: float) -> str:
    def owners(pids):
        return ", ".join(f"{names.get(p, '?')} ({p})" for p in pids)

    surname_of = {r["name"]: r["surname"] for r in cohort}
    lines = [
        "# 15. Saeimas jaunie deputāti — sadursmju priekšskatījums",
        "",
        f"Ģenerēts {date.today().isoformat()} ar `scripts/cohort_15saeima.py preview` "
        f"(DB tikai lasīta). Kohorta: {len(cohort)} deputāti, {len(out)} formas. "
        f"Dokumenti: `documents.content`, pēdējās 90 dienas — **docs_scanned = "
        f"{docs_scanned}** (katrā rindā tas pats saucējs; trāpījumi skaitīti ar "
        f"matcher `_occurrences` SQL priekšfiltra atlasītajos dokumentos). "
        f"Izpildes laiks: {runtime_s:.1f} s.",
        "",
        "`hits` = dokumenti, kur forma atrasta kā vārds (arī ALL-CAPS); "
        "`lower_hits` = dokumenti, kur tā pati forma ir ar mazo burtu (sadzīves vārda "
        "signāls). Esošo profilu formas = saglabātās `name_forms` + matcher automātiskie "
        "locījumi VISIEM profiliem (matcher nefiltrē pēc `relationship_type`).",
        "",
        "Šis fails neko neizlemj. Operators katrai formai izvēlas: atstāt / tikai "
        "pilnais vārds / `_COMMON_WORD_FORMS`. Lēmumus ieraksta YAML `common_word`/`notes`.",
        "",
        "## 1. Formas, kas jau pieder esošam profilam (`shared_with`)",
        "",
    ]
    shared = [o for o in out if o["shared_with"]]
    lines += _md_table(["Deputāts", "Forma", "Pieder arī", "hits", "docs_scanned"],
                       [[o["name"], o["form"], owners(o["shared_with"]), o["hits"],
                         o["docs_scanned"]] for o in shared]) if shared else ["Nav."]
    def hits_of(form):
        return next((o["hits"] for o in out if o["form"] == form), "—")

    lines += [
        "",
        f"Piezīmes. `Kleinberga` ({hits_of('Kleinberga')} dok.) — tieši tā kailā "
        "ģenitīva atpazīšana, ko Kleinbergs (5) zaudēs pēc Task 3 (koplietoto formu "
        f"noteikums). `Šleseri` ({hits_of('Šleseri')} dok.) šajā tabulā NAV: Šlesera "
        "automātiskie locījumi ir Šlesera/Šleseram/Šleseru, ne «Šleseri». Tomēr "
        "Danas Šleseres akuzatīvs «Šleseri» sakrīt ar daudzskaitli («Šleseri» = "
        "Šleseru ģimene), tāpēc arī šo formu operatoram jāizlemj.",
        "",
        "## 2. Īsās formas (≤4 zīmes, viens vārds)",
        "",
    ]
    short = [o for o in out if o["short"]]
    lines += _md_table(["Deputāts", "Forma", "hits", "lower_hits", "Pieder arī",
                        "docs_scanned"],
                       [[o["name"], o["form"], o["hits"], o["lower_hits"],
                         owners(o["shared_with"]) or "—", o["docs_scanned"]]
                        for o in short]) if short else ["Nav."]
    lines += ["", "## 3. Sadzīves vārdu kandidāti (formas ar `hits` > 0)", ""]
    listed = [r for r in cohort if r["surname"] in COMMON_WORD_CANDIDATES]
    rows3 = [[r["name"], COMMON_WORD_CANDIDATES[r["surname"]], o["form"], o["hits"],
              o["lower_hits"], o["docs_scanned"]]
             for r in listed for o in out
             if o["name"] == r["name"] and " " not in o["form"] and o["hits"] > 0]
    lines += _md_table(["Deputāts", "Kāpēc kandidāts", "Forma", "hits", "lower_hits",
                        "docs_scanned"], rows3) if rows3 else ["Nav."]
    zero = [r["name"] for r in listed
            if not any(o["name"] == r["name"] and o["hits"] > 0 for o in out)]
    if zero:
        lines += ["", "Kandidāti bez neviena trāpījuma: " + ", ".join(zero) + "."]
    missing = sorted(set(COMMON_WORD_CANDIDATES) - {r["surname"] for r in cohort})
    if missing:
        lines += ["", "Plāna kandidāti, kuru NAV kohortā: " + ", ".join(missing) + "."]
    lines += ["", "### Papildu kandidāti — citi uzvārdi ar mazo burtu trāpījumiem "
              "(`lower_hits` > 0)", ""]
    extra = [o for o in out if o["lower_hits"] > 0
             and surname_of[o["name"]] not in COMMON_WORD_CANDIDATES]
    lines += _md_table(["Deputāts", "Forma", "hits", "lower_hits", "docs_scanned"],
                       [[o["name"], o["form"], o["hits"], o["lower_hits"], o["docs_scanned"]]
                        for o in extra]) if extra else ["Nav."]
    lines += [
        "",
        "Apakšvirknes vārda iekšienē (piem., «Kolu» → «Kolumbija») šeit netiek skaitītas: "
        "matcher viena vārda formas meklē tikai pie vārda robežām.",
        "",
        "## 4. Visas formas",
        "",
    ]
    lines += _md_table(["Deputāts", "Forma", "hits", "lower_hits", "≤4", "Pieder arī",
                        "docs_scanned"],
                       [[o["name"], o["form"], o["hits"], o["lower_hits"],
                         "jā" if o["short"] else "", owners(o["shared_with"]) or "—",
                         o["docs_scanned"]] for o in out])
    return "\n".join(lines) + "\n"


def run_preview(db_path: Path, cohort: list[dict], out_path: Path) -> list[dict]:
    t0 = time.perf_counter()
    db = _ro(db_path)
    try:
        tp = db.execute("SELECT id, name, name_forms, relationship_type "
                        "FROM tracked_politicians").fetchall()
        existing = matcher_forms(tp)
        names = {r[0]: r[1] for r in tp}
        window = "scraped_at >= date('now','-90 day')"
        docs_scanned = db.execute(f"SELECT COUNT(*) FROM documents WHERE {window}").fetchone()[0]
        by_name: dict[str, list[str]] = {}
        for r in cohort:
            terms = _like_terms(r)
            where = " OR ".join("content LIKE ?" for _ in terms)
            by_name[r["name"]] = [t for (t,) in db.execute(
                f"SELECT content FROM documents WHERE {window} AND content IS NOT NULL "
                f"AND ({where})", [f"%{t}%" for t in terms])]
    finally:
        db.close()
    out = preview_rows(cohort, existing, [], doc_texts_by_name=by_name,
                       docs_scanned=docs_scanned)
    runtime = time.perf_counter() - t0
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(render_preview(cohort, out, names, docs_scanned, runtime),
                        encoding="utf-8")
    print(f"preview: {len(cohort)} deputāti, {len(out)} formas, docs_scanned={docs_scanned}, "
          f"priekšfiltrs {sum(len(v) for v in by_name.values())} dok., {runtime:.1f} s "
          f"→ {out_path}")
    return out


def run_emit_sql(db_path: Path, cohort: list[dict], out_dir: Path, day: str) -> int:
    db = _ro(db_path)
    try:
        existing = [r[0] for r in db.execute("SELECT name FROM tracked_politicians")]
        handles = [("social_accounts.handle", pid, h) for pid, h in
                   db.execute("SELECT opponent_id, handle FROM social_accounts")]
        tp_cols = {r[1] for r in db.execute("PRAGMA table_info(tracked_politicians)")}
        if "x_handle" in tp_cols:
            handles += [("tracked_politicians.x_handle", pid, h) for pid, h in
                        db.execute("SELECT id, x_handle FROM tracked_politicians")]
    finally:
        db.close()
    hits = existing_name_collisions(cohort, existing)
    if hits:
        print("STOP: kohortas vārdi jau ir tracked_politicians (rollback dzēstu esošas rindas):",
              file=sys.stderr)
        for c, e in hits:
            print(f"  {c!r} ~ esošais {e!r}", file=sys.stderr)
        return 1
    h_hits = handle_collisions(cohort, handles)
    if h_hits:
        print("STOP: kohortas X konti sakrīt (bez reģistra) ar esošiem vai savā starpā:",
              file=sys.stderr)
        for line in h_hits:
            print(f"  {line}", file=sys.stderr)
        return 1
    fwd, rb = emit_sql(cohort)
    head = (f"-- 15. Saeimas jaunie deputāti: {len(cohort)} tracked_politicians rindas "
            f"(relationship_type='tracked') + social_accounts tiem, kam ir x_handle.\n"
            f"-- Avots: data/seed/15saeima_kohorta.yaml; ģenerēts {day} ar "
            f"scripts/cohort_15saeima.py emit-sql.\n")
    fp = out_dir / f"seed_15saeima_{day}.sql"
    rp = out_dir / f"rollback_seed_15saeima_{day}.sql"
    out_dir.mkdir(parents=True, exist_ok=True)
    fp.write_text(f"-- FORWARD ({day})\n{head}{fwd}\n", encoding="utf-8")
    rp.write_text(f"-- ROLLBACK ({day}) forward failam {fp.name}\n{head}"
                  "-- Dzēš pēc name. Vārdu sargs darbojās emit-sql brīdī (neviens kohortas "
                  f"vārds tad nebija DB); izpildes brīža pārbaude ir Task 6 Step 3 «+{len(cohort)} tieši».\n"
                  "-- Derīgs TIKAI pirms jebkura rescan vai saišu veidošanas šiem pid: "
                  "document_politicians rindas šis fails NEdzēš.\n"
                  f"{rb}\n", encoding="utf-8")
    print(f"emit-sql: {len(cohort)} rindas → {fp}, {rp}")
    return 0


def _load_cohort() -> list[dict]:
    return yaml.safe_load(OUT.read_text(encoding="utf-8"))


def main() -> int:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    b = sub.add_parser("build")
    b.add_argument("--calc", type=Path, default=CALC)
    p = sub.add_parser("preview")
    p.add_argument("--out", type=Path, default=PREVIEW_OUT)
    e = sub.add_parser("emit-sql")
    e.add_argument("--out-dir", type=Path, default=REPO / "data")
    e.add_argument("--date", default=date.today().isoformat())
    args = ap.parse_args()
    from src.db import PRODUCTION_DB_PATH
    db_path = REPO / PRODUCTION_DB_PATH
    if args.cmd == "build":
        calc = json.loads(args.calc.read_text(encoding="utf-8"))
        rows = build_cohort(calc, _tracked_names(db_path))
        OUT.parent.mkdir(parents=True, exist_ok=True)
        OUT.write_text(yaml.safe_dump(rows, allow_unicode=True, sort_keys=False), encoding="utf-8")
        print(f"kohorta: {len(rows)} rindas → {OUT.relative_to(REPO)}")
    elif args.cmd == "preview":
        run_preview(db_path, _load_cohort(), args.out)
    elif args.cmd == "emit-sql":
        return run_emit_sql(db_path, _load_cohort(), args.out_dir, args.date)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
