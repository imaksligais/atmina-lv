"""Partiju tests — T3 validators (tikai LASA DB).

Pārbauda `content/partiju-tests/kodejums.json` pret `jautajumi.yaml` un DB:

* katrs jautājums no yaml ir kodējumā un otrādi; `tema` ir kanoniska tēma;
* katram jautājumam ir tieši 14 startējošie saraksti (`parties.short_name`);
* `nostaja` ∈ {par, pret, klusē};
* `par`/`pret`: `claim_id` eksistē, ir `claim_type='program_promise'`, pieder
  ŠAI partijai; `citats` ir verbatim (atstarpes normalizētas) apakšvirkne
  pozīcijas dokumenta `content`; `url` == `claims.source_url`;
* `klusē`: obligāta `piezime`.

Drukā saucēju (cik šūnu pārbaudīts, par/pret/klusē pa partijām). Exit 1, ja
ir kaut viena kļūda. 0 pārbaudītu šūnu = salauzts rīks, ne tīrs rezultāts.

Lietošana:
    .venv/Scripts/python.exe scripts/partiju_tests_validate.py
        [--questions content/partiju-tests/jautajumi.yaml]
        [--coding content/partiju-tests/kodejums.json] [--db data/atmina.db]
"""

from __future__ import annotations

import argparse
import json
import re
import sqlite3
import sys
from dataclasses import dataclass, field
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from src.topic_map import get_all_group_names  # noqa: E402

SARAKSTI_PATH = Path(__file__).resolve().parent.parent / "content" / "partiju-tests" / "saraksti.yaml"


def load_saraksti(path: str | Path = SARAKSTI_PATH) -> list[dict]:
    """14 startējošo sarakstu patiesība (cvk_numurs secībā)."""
    return yaml.safe_load(Path(path).read_text(encoding="utf-8"))


STARTING = [s["short_name"] for s in load_saraksti()]
STANCES = {"par", "pret", "klusē"}


@dataclass
class Report:
    cells: int = 0
    counts: dict[str, dict[str, int]] = field(default_factory=dict)
    levels: dict[str, int] = field(default_factory=dict)
    per_party_levels: dict[str, dict[str, int]] = field(default_factory=dict)
    errors: list[str] = field(default_factory=list)


def _norm(s: str | None) -> str:
    return re.sub(r"\s+", " ", s or "").strip()


def validate(questions: list[dict], coding: dict, db_path: str,
             saraksti: list[dict] | None = None) -> Report:
    if saraksti is None:
        saraksti = load_saraksti()
    names = [s["short_name"] for s in saraksti]
    by_name = {s["short_name"]: s for s in saraksti}
    rep = Report(counts={p: {"par": 0, "pret": 0, "klusē": 0} for p in names},
                 per_party_levels={p: {} for p in names})
    for s in saraksti:
        ppu = s.get("pilna_programma_url")
        if ppu:
            mh = s.get("majaslapa")
            if not mh:
                rep.errors.append(f"{s['short_name']}: pilna_programma_url bez majaslapa")
            elif _netloc(ppu) != _netloc(mh):
                rep.errors.append(f"{s['short_name']}: pilna_programma_url domēns "
                                  f"'{_netloc(ppu)}' != majaslapa domēns '{_netloc(mh)}'")
    topics = set(get_all_group_names())
    conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)

    qids = [q["id"] for q in questions]
    for extra in sorted(set(coding) - set(qids)):
        rep.errors.append(f"{extra}: ir kodējumā, bet nav jautājumu failā")
    for q in questions:
        qid = q["id"]
        if q.get("tema") not in topics:
            rep.errors.append(f"{qid}: tema '{q.get('tema')}' nav kanoniska tēma")
        if not _norm(q.get("apgalvojums")):
            rep.errors.append(f"{qid}: tukšs apgalvojums")
        if not isinstance(q.get("quiz"), bool):
            rep.errors.append(f"{qid}: quiz nav true/false")
        cells = coding.get(qid)
        if cells is None:
            rep.errors.append(f"{qid}: trūkst kodējumā")
            continue
        for p in names:
            if p not in cells:
                rep.errors.append(f"{qid}/{p}: trūkst šūnas")
        for p in sorted(set(cells) - set(names)):
            rep.errors.append(f"{qid}/{p}: nav startējošs saraksts (atļauti tikai {', '.join(names)})")
        for p in names:
            cell = cells.get(p)
            if cell is None:
                continue
            rep.cells += 1
            _check_cell(conn, rep, qid, p, cell, by_name[p])
    conn.close()
    return rep


def _netloc(url: str | None) -> str:
    host = (url or "").split("/")[2].lower() if "://" in (url or "") else ""
    return host[4:] if host.startswith("www.") else host


def _check_doc_citats(conn: sqlite3.Connection, rep: Report, where: str,
                      cell: dict) -> None:
    """2./3. līmenis: document_id → documents rinda, source_url == url, citāts verbatim."""
    did = cell.get("document_id")
    if not isinstance(did, int):
        rep.errors.append(f"{where}: document_id trūkst vai nav skaitlis")
        return
    row = conn.execute("SELECT source_url, content FROM documents WHERE id = ?", (did,)).fetchone()
    if row is None:
        rep.errors.append(f"{where}: document_id {did} DB nav")
        return
    doc_url, content = row
    if cell.get("url") != doc_url:
        rep.errors.append(f"{where}: url nesakrīt ar documents.source_url ({doc_url})")
    cit = _norm(cell.get("citats"))
    if not cit:
        rep.errors.append(f"{where}: citāts trūkst")
    elif content is None:
        rep.errors.append(f"{where}: document_id {did} bez satura — citāts nav pārbaudāms")
    elif cit not in _norm(content):
        rep.errors.append(f"{where}: citāts nav atrodams dokumenta tekstā verbatim: „{cit[:60]}…”")


def _check_cell(conn: sqlite3.Connection, rep: Report, qid: str, party: str,
                cell: dict, saraksts: dict) -> None:
    where = f"{qid}/{party}"
    st = cell.get("nostaja")
    if st not in STANCES:
        rep.errors.append(f"{where}: nostaja '{st}' nav viena no par/pret/klusē")
        return
    rep.counts[party][st] += 1
    if st == "klusē":
        rep.levels["klusē"] = rep.levels.get("klusē", 0) + 1
        rep.per_party_levels[party]["klusē"] = rep.per_party_levels[party].get("klusē", 0) + 1
        piez = _norm(cell.get("piezime"))
        if not piez:
            rep.errors.append(f"{where}: 'klusē' bez piezime — kāpēc programma neizsakās?")
        else:
            low = piez.lower()
            if "nav pārbaudīta" in low:
                rep.errors.append(f"{where}: piezime satur 'nav pārbaudīta' — U4 prasa pilnās programmas rezultātu")
            elif "cvk" not in low or not any(
                    t in low for t in ("pilnā programma", "pilna programma",
                                       "nav publicējusi", "nav pieejama")):
                rep.errors.append(f"{where}: piezime neapliecina, ka meklēta CVK programmā un pilnajā programmā")
        return
    avots = cell.get("avots")
    if avots not in ("cvk", "pilna_programma", "izteikums"):
        rep.errors.append(f"{where}: avots '{avots}' nav viens no cvk/pilna_programma/izteikums")
        return
    rep.levels[avots] = rep.levels.get(avots, 0) + 1
    rep.per_party_levels[party][avots] = rep.per_party_levels[party].get(avots, 0) + 1
    if avots == "cvk":
        if cell.get("document_id") is not None and cell.get("claim_id") is None:
            rep.errors.append(f"{where}: document_id bez claim_id — cvk šūnai pierādījums ir claim_id")
            return
        cid = cell.get("claim_id")
        if not isinstance(cid, int):
            rep.errors.append(f"{where}: claim_id trūkst vai nav skaitlis")
            return
        row = conn.execute(
            """SELECT c.claim_type, p.short_name, c.source_url, d.content
               FROM claims c LEFT JOIN parties p ON p.id = c.party_id
               LEFT JOIN documents d ON d.id = c.document_id WHERE c.id = ?""",
            (cid,),
        ).fetchone()
        if row is None:
            rep.errors.append(f"{where}: claim_id {cid} DB nav")
            return
        claim_type, short_name, source_url, content = row
        if claim_type != "program_promise":
            rep.errors.append(f"{where}: claim_id {cid} ir '{claim_type}', ne program_promise")
        if short_name != party:
            rep.errors.append(f"{where}: claim_id {cid} pieder partijai '{short_name}', ne {party} (partija nesakrīt)")
        if cell.get("url") != source_url:
            rep.errors.append(f"{where}: url nesakrīt ar claims.source_url ({source_url})")
        cit = _norm(cell.get("citats"))
        if not cit:
            rep.errors.append(f"{where}: citāts trūkst")
        elif content is None:
            rep.errors.append(f"{where}: claim_id {cid} bez dokumenta — citāts nav pārbaudāms")
        elif cit not in _norm(content):
            rep.errors.append(f"{where}: citāts nav atrodams programmas tekstā verbatim: „{cit[:60]}…”")
    elif avots == "pilna_programma":
        majaslapa = saraksts.get("majaslapa")
        if not majaslapa:
            rep.errors.append(f"{where}: majaslapa nav saraksti.yaml — domēnu nevar pārbaudīt")
        elif _netloc(cell.get("url")) != _netloc(majaslapa):
            rep.errors.append(f"{where}: url domēns '{_netloc(cell.get('url'))}' != majaslapa domēns '{_netloc(majaslapa)}'")
        _check_doc_citats(conn, rep, where, cell)
    else:  # izteikums
        lideris = saraksts.get("lideris_id")
        if lideris is None:
            rep.errors.append(f"{where}: lideris_id nav saraksti.yaml — runātāju nevar pārbaudīt")
        elif cell.get("runatajs") != lideris:
            rep.errors.append(f"{where}: runatajs {cell.get('runatajs')} != saraksta lideris_id {lideris}")
        if not re.fullmatch(r"2026-\d{2}-\d{2}", str(cell.get("datums") or "")):
            rep.errors.append(f"{where}: datums '{cell.get('datums')}' nav formā 2026-MM-DD")
        _check_doc_citats(conn, rep, where, cell)


QUIZ_MIN_READABLE = 8   # § 3.3: nolasāmas ≥ 8
QUIZ_MIN_MINORITY = 3   # § 3.3: mazākums ≥ 3
QUIZ_MIN_QUESTIONS = 8  # § 3.3: mērķis ≥ 8 quiz: true jautājumi
QUIZ_MAX_BALANCE = 0.60  # § 3.3: virziena balanss ≤ 60/40 (par : pret)


def question_gate(questions: list[dict], coding: dict, saraksti: list[dict],
                  min_readable: int = QUIZ_MIN_READABLE,
                  min_minority: int = QUIZ_MIN_MINORITY) -> list[dict]:
    rows = []
    names = [s["short_name"] for s in saraksti]
    for q in questions:
        cells = coding.get(q["id"], {})
        n_par = sum(1 for p in names if cells.get(p, {}).get("nostaja") == "par")
        n_pret = sum(1 for p in names if cells.get(p, {}).get("nostaja") == "pret")
        readable = n_par + n_pret
        minority = min(n_par, n_pret)
        rows.append({"id": q["id"], "apgalvojums": q.get("apgalvojums", ""), "par": n_par,
                     "pret": n_pret, "readable": readable, "minority": minority,
                     "ok": readable >= min_readable and minority >= min_minority})
    return rows


def quiz_gate(questions: list[dict], coding: dict, saraksti: list[dict]) -> list[str]:
    """§ 3.3 vārts `quiz: true` kopai; atgriež kļūdu sarakstu (tukšs = zaļš)."""
    errors: list[str] = []
    quiz_qs = [q for q in questions if q.get("quiz") is True]
    rows = {r["id"]: r for r in question_gate(quiz_qs, coding, saraksti)}
    for r in rows.values():
        if r["readable"] < QUIZ_MIN_READABLE or r["minority"] < QUIZ_MIN_MINORITY:
            errors.append(f"{r['id']}: quiz: true, bet nolasāmas {r['readable']} "
                          f"(< {QUIZ_MIN_READABLE}) vai mazākums {r['minority']} (< {QUIZ_MIN_MINORITY})")
    if len(quiz_qs) < QUIZ_MIN_QUESTIONS:
        errors.append(f"quiz: true skaits {len(quiz_qs)} < {QUIZ_MIN_QUESTIONS}")
    if quiz_qs:
        n_par = n_pret = 0
        for q in quiz_qs:
            for s in saraksti:
                v = coding.get(q["id"], {}).get(s["short_name"], {}).get("nostaja")
                n_par += v == "par"
                n_pret += v == "pret"
        total = n_par + n_pret
        if total == 0:
            print("quiz-gate: par+pret šūnu nav — balansa pārbaude izlaista")
        elif max(n_par, n_pret) / total > QUIZ_MAX_BALANCE:
            errors.append(f"balanss par={n_par} pret={n_pret} pārsniedz "
                          f"{QUIZ_MAX_BALANCE:.0%}/{1 - QUIZ_MAX_BALANCE:.0%}")
    return errors


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--questions", default="content/partiju-tests/jautajumi.yaml")
    ap.add_argument("--coding", default="content/partiju-tests/kodejums.json")
    ap.add_argument("--db", default="data/atmina.db")
    ap.add_argument("--saraksti", default=str(SARAKSTI_PATH))
    ap.add_argument("--quiz-gate", action="store_true",
                    help="pārbauda quiz: true kopu pret § 3.3 sliekšņiem")
    a = ap.parse_args(argv)
    questions = yaml.safe_load(Path(a.questions).read_text(encoding="utf-8")) or []
    coding = json.loads(Path(a.coding).read_text(encoding="utf-8"))
    saraksti = load_saraksti(a.saraksti)
    rep = validate(questions, coding, a.db, saraksti=saraksti)
    names = [s["short_name"] for s in saraksti]

    print(f"Pārbaudītas {rep.cells} šūnas ({len(questions)} jautājumi × {len(names)} saraksti)")
    for p in names:
        c = rep.counts[p]
        print(f"  {p:6s} par {c['par']:2d}  pret {c['pret']:2d}  klusē {c['klusē']:2d}")
    if rep.levels:
        print("Līmeņi: " + "  ".join(f"{k} {v}" for k, v in sorted(rep.levels.items())))
    if rep.cells == 0:
        print("KĻŪDA: 0 pārbaudītu šūnu — rīks vai faili ir salauzti", file=sys.stderr)
        return 1
    if rep.errors:
        print(f"\n{len(rep.errors)} kļūdas:", file=sys.stderr)
        for e in rep.errors:
            print("  - " + e, file=sys.stderr)
        return 1
    if a.quiz_gate:
        gate_errors = quiz_gate(questions, coding, saraksti)
        if gate_errors:
            print(f"\nquiz-gate: {len(gate_errors)} kļūdas:", file=sys.stderr)
            for e in gate_errors:
                print("  - " + e, file=sys.stderr)
            return 1
        print("quiz-gate OK")
    print("OK — kļūdu nav")
    return 0


if __name__ == "__main__":
    sys.exit(main())
