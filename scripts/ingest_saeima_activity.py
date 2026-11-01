"""Saeimas aktivitātes ielāde: deputātu amati, debates, jautājumi.

Plāns: docs/plans/2026-10-06-saeimas-aktivitate.md. Katram avotam viena rinda
`parsed=… stored=… skipped_existing=… empty_sessions=… failures=…`, tad
nesaskaņotie vārdi. Exit 1, ja stored + skipped_existing ≠ parsed, ja ir
failures, kas nav `unmatched_name`, vai ja deputātu sarakstā < 90 (STOP: 0 =
paterna kļūda, T8/T12). `--dry-run` ielādē, parsē un saskaņo, bet neko neraksta
(arī ne DDL).

Usage:
    .venv/Scripts/python.exe -m scripts.ingest_saeima_activity --what profiles --dry-run
    .venv/Scripts/python.exe -m scripts.ingest_saeima_activity --what all [--convocation 14] [--db PATH]
"""
from __future__ import annotations

import argparse
import sqlite3
import sys

import httpx

from src.db import get_db
from src.saeima.activity import (
    HTTP_TIMEOUT,
    MIN_DEPUTIES,
    QUESTION_VIEWS,
    ActivityResult,
    _match_rows,
    addressee_person_name,
    fetch_debates,
    fetch_deputy_list,
    fetch_deputy_positions,
    fetch_question_details,
    fetch_question_list,
    list_debate_resources,
    parse_deputy_list,
    question_links,
    store_debate_speeches,
    store_deputy_positions,
    store_questions,
)
from src.saeima.convocation import SAEIMA_CONVOCATION
from src.saeima.schema import init_saeima_tables
from src.saeima.votes import _build_name_index


def _ingest_profiles(db_path, convocation, dry_run, name_index) -> tuple[ActivityResult, list[str]]:
    """Atgriež (rezultāts, STOP iemesli)."""
    stops: list[str] = []
    with httpx.Client(timeout=HTTP_TIMEOUT, follow_redirects=True) as client:
        deputies = parse_deputy_list(fetch_deputy_list(client, convocation))
        if len(deputies) < MIN_DEPUTIES:
            stops.append(f"deputātu sarakstā {len(deputies)} < {MIN_DEPUTIES} — paterna kļūda vai tukšs sasaukums")
            return ActivityResult(), stops
        rows, fetch_failures = fetch_deputy_positions(client, deputies, convocation)
    if dry_run:
        result = ActivityResult(parsed=len(rows))
        result.failures.extend(_match_rows(rows, name_index, "deputy_name"))
        result.failures.extend({"kind": "deleted_flag", "name": r["deputy_name"],
                                "body": r["body"], "deleted": r["deleted"]}
                               for r in rows if r["deleted"])
    else:
        result = store_deputy_positions(db_path, rows, convocation, name_index)
    result.failures.extend(fetch_failures)
    print(f"deputies={len(deputies)}")
    return result, stops


# Sēde, kas jau glabāta un vecāka par šo, vairs netiek ielādēta; svaigākas avotā vēl mainās.
KNOWN_SESSION_DAYS = 30


def _known_old_sessions(db_path, convocation) -> set[str]:
    """Sēdes ar glabātām runām, kuru datums < šodiena − KNOWN_SESSION_DAYS. NULL datums → ielādē vēlreiz."""
    db = get_db(db_path)
    try:
        return {r[0] for r in db.execute(
            """SELECT session_name FROM saeima_debate_speeches WHERE convocation = ?
               GROUP BY session_name HAVING MAX(session_date) < date('now', ?)""",
            (convocation, f"-{KNOWN_SESSION_DAYS} days"))}
    except sqlite3.OperationalError:   # --dry-run DB bez tabulas = nekas nav zināms
        return set()
    finally:
        db.close()


def _ingest_debates(db_path, convocation, dry_run, name_index) -> tuple[ActivityResult, list[str]]:
    """Atgriež (rezultāts, STOP iemesli). NULL ilgums/datums/vecāks nav failure — rinda glabājas, skaita šeit.

    `parent_unresolved` = apakšpunkts (DKP_SEQUENCE ar punktu), kam pēc `resolve_parent` nav
    dokumenta numura. Izlaistie zināmie faili netiek parsēti → stored + skipped_existing == parsed.
    """
    stops: list[str] = []
    with httpx.Client(timeout=HTTP_TIMEOUT, follow_redirects=True) as client:
        resources = list_debate_resources(client, convocation)
        if not resources:
            stops.append(f"CKAN: 0 `{convocation}.Saeimas … -deb` resursu — paterna kļūda vai tukšs sasaukums")
            return ActivityResult(), stops
        known = _known_old_sessions(db_path, convocation)
        todo = [r for r in resources if r["name"][:-len("-deb")] not in known]
        rows, fetch_failures, empty = fetch_debates(client, todo)
    if dry_run:
        result = ActivityResult(parsed=len(rows))
        result.failures.extend(_match_rows(rows, name_index, "speaker_name"))
    else:
        result = store_debate_speeches(db_path, rows, convocation, name_index)
    result.empty_sessions = empty
    result.failures.extend(fetch_failures)
    print(f"deb_files={len(resources)} files_skipped_known={len(resources) - len(todo)} "
          f"speakers_distinct={len({r['speaker_name'] for r in rows})} "
          f"duration_null={sum(r['duration_sec'] is None for r in rows)} "
          f"parent_unresolved={sum(r['document_nr'] is None and '.' in (r['dkp_seq'] or '') for r in rows)} "
          f"session_date_null={sum(r['session_date'] is None for r in rows)}")
    return result, stops


def _ingest_questions(db_path, convocation, dry_run, name_index) -> tuple[ActivityResult, list[str]]:
    """Jautājumi + pieprasījumi. Jebkurš skats ar 0 ierakstiem = STOP (T8/T12)."""
    stops: list[str] = []
    items: list[dict] = []
    with httpx.Client(timeout=HTTP_TIMEOUT, follow_redirects=True) as client:
        for kind in QUESTION_VIEWS:
            listed = fetch_question_list(client, kind, convocation)
            print(f"{kind}: listed={len(listed)}")
            if not listed:
                stops.append(f"{kind} sarakstā 0 ierakstu — paterna kļūda vai tukšs sasaukums")
            items.extend(listed)
        if stops:
            return ActivityResult(), stops
        rows, fetch_failures = fetch_question_details(client, items, convocation)
    if dry_run:
        result = ActivityResult(parsed=len(rows))
        matched = {"submitter": 0, "addressee": 0}
        for row in rows:
            links, failures = question_links(row, name_index)
            result.failures.extend(failures)
            for role, _ in links:
                matched[role] += 1
        print(f"matched submitter={matched['submitter']} addressee={matched['addressee']}")
    else:
        result = store_questions(db_path, rows, convocation, name_index)
    result.failures.extend(fetch_failures)
    # Iestāžu adresāti nav kļūda, bet klasifikatoru jāvar pārbaudīt ar aci (T18).
    institutions = [a for r in rows for a in r["addressees"] if addressee_person_name(a) is None]
    print(f"institution_addressees={len(institutions)}")
    for name in sorted(set(institutions)):
        print(f"  institution: {name}")
    return result, stops


SOURCES = {"profiles": _ingest_profiles, "debates": _ingest_debates, "questions": _ingest_questions}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--what", required=True, choices=[*SOURCES, "all"])
    ap.add_argument("--convocation", type=int, default=SAEIMA_CONVOCATION)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--db", default=None, help="DB ceļš (noklusējums: src.db.DB_PATH)")
    args = ap.parse_args(argv)
    sys.stdout.reconfigure(encoding="utf-8")

    if not args.dry_run:
        init_saeima_tables(args.db)
    name_index = _build_name_index(args.db)

    exit_code = 0
    for what in (SOURCES if args.what == "all" else [args.what]):
        result, stops = SOURCES[what](args.db, args.convocation, args.dry_run, name_index)
        mode = " (dry-run)" if args.dry_run else ""
        print(f"[{what}]{mode} {result.summary_line()}")
        for reason in stops:
            print(f"  STOP: {reason}")
            exit_code = 1
        unmatched = [f["name"] for f in result.failures if f["kind"] == "unmatched_name"]
        for name in unmatched:
            print(f"  unmatched: {name}")
        for f in result.failures:
            if f["kind"] != "unmatched_name":
                print(f"  failure: {f}")
                exit_code = 1
        if not args.dry_run and result.stored + result.skipped_existing != result.parsed:
            print(f"  STOP: stored+skipped_existing={result.stored + result.skipped_existing} ≠ parsed={result.parsed}")
            exit_code = 1
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
