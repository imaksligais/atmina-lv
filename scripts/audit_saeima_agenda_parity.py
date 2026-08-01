"""Agenda↔DB pilnīguma audits — READ-ONLY.

Atbild uz vienu jautājumu: vai katram darba kārtības balsojumam ir rinda
`saeima_votes`? Salīdzina pēc **(vote_date, vote_time)**, NEVIS pēc URL.

Kāpēc ne pēc URL: titania pārarhivē balsojumu lapas ar jauniem UNID ~nedēļu
pēc sēdes, tāpēc `store_vote()` URL-dedup (src/saeima/votes.py:413) kļūst akls —
tas pats balsojums ar jaunu URL izskatās kā jauns. Akls bulk-backfill tāpēc
ražo dublikātus, nevis aizpilda robus. Šis audits neko neraksta; tas tikai
nosauc, kas tiešām trūkst, lai ielāde būtu mērķēta.

Atklāts 2026-07-25: `Par iekļaušanu ... darba kārtībā` klases balsojumi 2025.
gadā DB bija 0 (2024. gadā 12), lai gan tādi notikuši — piem. 692/Lm14
(2025-04-10 09:25:00) un 877/Lm14 (2025-12-11 16:29:57). 10.04. gadījums ir
robs klases, nevis dienas, līmenī: DB ir 09:14:56 un 09:28:37 balsojumi, bet
trūkstošais ir tieši pa vidu.

Lietošana:
    python scripts/audit_saeima_agenda_parity.py --year 2025
    python scripts/audit_saeima_agenda_parity.py --year 2025 --dates 2025-04-10,2025-12-11
    python scripts/audit_saeima_agenda_parity.py --year 2025 --out data/parity_2025.json

Izvade: rinda uz sēdi (darba kārtības balsojumi / DB / trūkst) + JSON ar
trūkstošo balsojumu sarakstu (URL, datums, laiks, motīvs), ko padot ielādei.

Kopš 2026-08-04 auditē arī `jautajumi` tipa sēdes: līdz tam tās izlaida pēc
pieņēmuma "bez balsojumiem", bet 2025-10-30 jautājumu sēdei DB ir 2 balsojumi —
pieņēmums bija nepatiess, un tāda diena no audita pazuda pilnībā.
"""
from __future__ import annotations

import argparse
import json
import sqlite3
import sys
import time
from collections import Counter
from datetime import date
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(REPO_ROOT))

from scripts.p3_backfill_year_urllib import (  # noqa: E402
    _extract_vote_urls_from_agenda,
    _fetch,
    _parse_vote_page,
    SAEIMA_BASE,
)
from src.saeima import _resolve_vote_url  # noqa: E402
from src.saeima.unloadable import is_unloadable  # noqa: E402
from src.saeima.unloadable import lookup as unloadable_lookup  # noqa: E402

MANIFEST_PATH = REPO_ROOT / "data" / "saeima_backfill_sessions.json"
DB_PATH = str(REPO_ROOT / "data" / "atmina.db")


def _db_index() -> tuple[set[tuple[str, str]], set[str]]:
    """Return ({(vote_date, vote_time)}, {url}) for the whole table."""
    db = sqlite3.connect(DB_PATH)
    dt = {
        (r[0], r[1])
        for r in db.execute("SELECT vote_date, vote_time FROM saeima_votes")
        if r[0] and r[1]
    }
    urls = {r[0] for r in db.execute("SELECT url FROM saeima_votes") if r[0]}
    db.close()
    return dt, urls


def _iso(parsed: dict) -> tuple[str | None, str | None]:
    if not parsed.get("date"):
        return None, parsed.get("time")
    try:
        dd, mm, yyyy = parsed["date"].split(".")
        return f"{yyyy}-{mm}-{dd}", parsed.get("time")
    except ValueError:
        return None, parsed.get("time")


def audit_session(session: dict, db_dt: set, db_urls: set, delay: float) -> dict:
    date_str = f"{session['year']}-{session['month']:02d}-{session['day']:02d}"
    out = {
        "date": date_str,
        "uuid": session["uuid"],
        "session_type": session["session_type"],
        "agenda_votes": 0,
        "present_by_url": 0,
        "present_by_datetime": 0,
        "missing": [],
        "known_unloadable": [],
        "unreadable": [],
        "error": None,
    }

    agenda_url = f"{SAEIMA_BASE}/DK?ReadForm&nr={session['uuid']}"
    try:
        agenda_html = _fetch(agenda_url)
    except Exception as e:  # noqa: BLE001
        out["error"] = f"agenda fetch: {e}"
        return out

    vote_urls = _extract_vote_urls_from_agenda(agenda_html)
    out["agenda_votes"] = len(vote_urls)

    for url in vote_urls:
        full = _resolve_vote_url(url)
        if full in db_urls:
            out["present_by_url"] += 1
            continue
        # Unknown URL — could be a re-archived UNID of a vote we already have.
        # Only a (date, time) check can tell; that needs the page itself.
        try:
            parsed = _parse_vote_page(_fetch(url))
        except Exception as e:  # noqa: BLE001
            out["unreadable"].append({"url": full, "err": str(e)})
            continue
        if delay:
            time.sleep(delay)
        iso_date, vtime = _iso(parsed)
        if not iso_date or not vtime:
            out["unreadable"].append({"url": full, "err": "no date/time on page"})
            continue
        if (iso_date, vtime) in db_dt:
            out["present_by_datetime"] += 1
            continue
        # Aizklātā balsošana: roll-call neeksistē pēc dizaina, tāpēc tas nav
        # robs, ko ielādēt. Bez šī katrs skrējiens skaitītu tos pašus 16 par
        # trūkstošiem, un katra nākamā sesija izmeklētu to pašu no jauna.
        if is_unloadable(iso_date, vtime):
            known = unloadable_lookup(iso_date, vtime) or {}
            out["known_unloadable"].append({
                "url": full,
                "vote_date": iso_date,
                "vote_time": vtime,
                "motif": parsed.get("motif", "")[:200],
                "kind": known.get("kind"),
            })
            continue
        out["missing"].append({
            "url": full,
            "vote_date": iso_date,
            "vote_time": vtime,
            "motif": parsed.get("motif", "")[:200],
            "par": parsed.get("par"),
            "pret": parsed.get("pret"),
            "atturas": parsed.get("atturas"),
            "deputies": len(parsed.get("deputies") or []),
        })
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--year", type=int, required=True)
    ap.add_argument("--dates", type=str, default=None,
                    help="komatatdalīti ISO datumi; ierobežo auditu tikai tiem")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--delay", type=float, default=0.3)
    ap.add_argument("--out", type=str, default=None)
    args = ap.parse_args()

    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    manifest_years = {s["year"] for s in manifest}
    in_year = [s for s in manifest if s["year"] == args.year]

    # T8 PAŠA RĪKA LĪMENĪ. Līdz 2026-08-01 manifestā bija tikai 2022.–2025. gads,
    # tāpēc `--year 2026` filtrēja līdz TUKŠAM sarakstam un rīks mierīgi
    # izdrukāja „KOPĀ: darba kārtībā 0, trūkst 0" — tīrs pārskats par gadu, kurā
    # tas nebija paskatījies ne reizi. 0 sēžu iekšā NAV tīrs gads; tas ir
    # manifesta robs, un rīkam par to jāapstājas, ne jāziņo zaļš.
    if not in_year:
        print(
            f"STOP: manifestā ({MANIFEST_PATH.name}) nav nevienas {args.year}. gada "
            f"sēdes.\n"
            f"  Manifestā ir gadi: {', '.join(str(y) for y in sorted(manifest_years))}\n"
            "  Tas ir MANIFESTA ROBS, ne tīrs gads (T8). Pārģenerē manifestu:\n"
            "    1) uztver kalendāra lapu ar Playwright (sk. scripts/"
            "_p3_extract_sessions_2026-05-26.py docstring)\n"
            f"    2) .venv/Scripts/python.exe scripts/_p3_extract_sessions_2026-05-26.py "
            f"--max-year {args.year}",
            file=sys.stderr,
        )
        return 2

    # Filtri ir SKAIDRI un uzskaitīti — kluss filtrs šeit nozīmētu, ka sēde
    # pazūd no audita un neviens to nezina.
    #
    # `jautajumi` sēdes kopš 2026-08-04 TIEK auditētas. Līdz tam tās izlaida
    # pēc pieņēmuma "bez balsojumiem", bet 2025-10-30 ir jautājumu sēde ar
    # 2 balsojumiem DB — pieņēmums nepatiess, un tās dienas darba kārtību
    # audits neredzēja nekad. Tukša jautājumu sēde tagad godīgi rāda DK=0.
    sessions = list(in_year)

    # Nākotnes sēde nevar būt robs. Kalendārs uzskaita visu gadu uz priekšu,
    # tāpēc bez šī filtra vēl nenotikusi sēde atgrieztu 0 darba kārtības
    # balsojumu un izskatītos pēc tukšas dienas.
    today = date.today().isoformat()
    future = [s for s in sessions
              if f"{s['year']}-{s['month']:02d}-{s['day']:02d}" > today]
    sessions = [s for s in sessions
                if f"{s['year']}-{s['month']:02d}-{s['day']:02d}" <= today]

    if args.dates:
        want = {d.strip() for d in args.dates.split(",")}
        sessions = [
            s for s in sessions
            if f"{s['year']}-{s['month']:02d}-{s['day']:02d}" in want
        ]
    sessions.sort(key=lambda s: (s["month"], s["day"]))
    if args.limit:
        sessions = sessions[: args.limit]

    db_dt, db_urls = _db_index()
    print(f"DB: {len(db_dt)} unikāli (datums, laiks); {len(db_urls)} URL")
    print(f"Manifestā {args.year}. gadā: {len(in_year)} sēdes "
          f"({', '.join(f'{t}={n}' for t, n in sorted(Counter(s['session_type'] for s in in_year).items()))})")
    if future:
        print(f"Izlaistas (vēl nav notikušas, > {today}): {len(future)} — "
              + ", ".join(f"{s['year']}-{s['month']:02d}-{s['day']:02d}" for s in future))
    print(f"Auditējamas sēdes: {len(sessions)}\n")
    if not sessions:
        print("STOP: pēc filtriem nepalika neviena auditējama sēde — sk. augšējās "
              "rindas. Tas nav tīrs gads.", file=sys.stderr)
        return 2
    print(f"{'datums':<12} {'tips':<10} {'DK':>4} {'URL✓':>5} {'DT✓':>5} {'TRŪKST':>7} {'?':>3}")
    print("-" * 52)

    results = []
    for s in sessions:
        r = audit_session(s, db_dt, db_urls, args.delay)
        results.append(r)
        flag = "  ERR" if r["error"] else ""
        print(f'{r["date"]:<12} {r["session_type"]:<10} {r["agenda_votes"]:>4} '
              f'{r["present_by_url"]:>5} {r["present_by_datetime"]:>5} '
              f'{len(r["missing"]):>7} {len(r["unreadable"]):>3}{flag}')
        if r["error"]:
            print(f'    {r["error"]}')

    # SEGUMS PIRMS KOPSAVILKUMA (2026-08-09). Bez šīs rindas neizdevies fetch
    # ir aritmētiski neatšķirams no tukšas sēdes: `audit_session` kļūmes ceļā
    # atgriežas ar `agenda_votes: 0, missing: []`, tāpēc tāda sēde dod nulli
    # visiem trim kopskaitļiem, un apakšā stāv „trūkst 0". Bīstamais gadījums
    # nav pilnā avārija (visas rindas ar ERR), bet daļējā: 3 no 79 sēdēm krīt,
    # ERR karogi jau aizritējuši ekrānā, un skaitlis aizceļo BACKLOG-ā.
    #
    # Otrs skaitlis (DK=0) ir vienīgais falsificējamais signāls pret T12: kad
    # formāts mainās, `_fetch` IZDODAS, urlu ekstrakcija atdod [], `error`
    # paliek None un ERR karoga nav vispār — tikai DK=0 sēžu skaits palecas.
    # Tas nav kļūda pats par sevi: svinīgās un `jautajumi` sēdes leģitīmi rāda
    # 0. Tāpēc to ziņo kā saucēju, ne kā vārtus.
    errored = [r for r in results if r["error"]]
    zero_dk = [r for r in results if not r["error"] and r["agenda_votes"] == 0]
    print("-" * 52)
    print(f"SEGUMS: nolasītas {len(results) - len(errored)}/{len(results)} sēdes; "
          f"ar kļūdu {len(errored)}; no nolasītajām DK=0: {len(zero_dk)} "
          f"({', '.join(sorted({r['session_type'] for r in zero_dk})) or '—'})")

    total_missing = sum(len(r["missing"]) for r in results)
    total_agenda = sum(r["agenda_votes"] for r in results)
    total_unreadable = sum(len(r["unreadable"]) for r in results)
    total_unloadable = sum(len(r["known_unloadable"]) for r in results)
    print("-" * 52)
    print(f"KOPĀ: darba kārtībā {total_agenda}, trūkst {total_missing}, "
          f"nenolasāmi {total_unreadable}")
    if total_unloadable:
        print(f"Zināmi neielādējami (aizklātā balsošana — roll-call neeksistē): "
              f"{total_unloadable}")

    if total_missing:
        print("\nTrūkstošie balsojumi:")
        for r in results:
            for m in r["missing"]:
                print(f'  {m["vote_date"]} {m["vote_time"]}  '
                      f'{m["par"]}/{m["pret"]}/{m["atturas"]}  {m["motif"][:90]}')

    if args.out:
        path = REPO_ROOT / args.out
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(results, ensure_ascii=False, indent=2),
                        encoding="utf-8")
        print(f"\nJSON: {path}")

    # STOP TIKAI BEIGĀS, ne pie pirmās kļūmes: `_fetch` ir kails `urlopen` bez
    # atkārtojuma, tāpēc pārtraukums trešajā sēdē noslēptu pārējo 76 stāvokli.
    # Izejas kods 2 = „nepilns palaidiens, atkārto nosauktos datumus", NEVIS
    # „atrasti robi" (robi iet ar 0 + `Trūkstošie balsojumi` sarakstu).
    if errored:
        print(f"\nSTOP: {len(errored)} sēdes nav nolasītas — šis audits NAV "
              f"pilnīgs, un tā JSON ir apcirpts darba uzdevums:", file=sys.stderr)
        for r in errored:
            print(f'  {r["date"]} ({r["session_type"]}): {r["error"]}', file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
