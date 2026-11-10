"""Agenda↔DB pilnīguma audits — READ-ONLY.

Atbild uz vienu jautājumu: vai katram darba kārtības balsojumam ir rinda
`saeima_votes`? Salīdzina pēc **(vote_date, vote_time)**, NEVIS pēc URL.

Kāpēc ne pēc URL: titania pārarhivē balsojumu lapas ar jauniem UNID ~nedēļu
pēc sēdes, tāpēc URL neder par atslēgu (`store_vote()` kopš 2026-11-07 dublikātu
atpazīst arī pēc datuma un laika). Šis audits neko neraksta; tas tikai
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

Kopš 2026-09-16 audits atsakās sertificēt DZĪVU (tās pašas dienas) sēdi:
kalendārs tai renderē `./DK?ReadForm&active=1`, nevis `nr={UUID}`, un līdz tam
tāda diena manifestā neiekļuva vispār — `--dates 2026-09-10` izdrukāja
„DK=0, trūkst 0", kaut sēdē bija 16 balsojumi. Tagad manifestā rinda IR (ar
`uuid=None`), diena ir redzama, un audits par to apstājas ar izejas kodu 2 —
sk. `_live_session_stop()`. Dzīvo darba kārtību nedrīkst lietot paritātei: tā
nerenderē apakšpunktu balsojumus (2026-09-10: 16 pret 21), un `active=1` rīt
rāda jau citu sēdi.

Kopš 2026-09-02 audits vispirms pārbauda MANIFESTA VECUMU (`generated_at` +
pieprasīto datumu segumu) un apstājas ar izejas kodu 2, ja manifests nevar
atbildēt par prasīto dienu — sk. `_manifest_age_stop()`. Manifests neredz
sēdes, kas notikušas pēc tā ģenerēšanas, un tāda diena bez šiem vārtiem
izskatījās tīra.

Kopš 2026-11-04 audits skaita arī `saeima_votes.url LIKE '%parentID=%'`: vēlāk šī
lapa ir tukša. Saite, kas vecāka par 7 dienām, dod izejas kodu 1 (labojums:
`scripts/fix_parentid_vote_urls.py`). Kods 2 paliek „nepilns palaidiens, atkārto",
un tas ir svarīgāks par 1.

Kopš 2026-11-10 `--tech` aizstāj rokas paritāti: katram punktam ar
`hasTechChilds` audits atver `getTechDKP` un pievieno tā balsojumus apvienībai;
dzīvajai sēdei tas nolasa `var actualXML_DkId`, pārbauda, ka `nr={DkId}` lapa ir
par prasīto datumu, un auditē `nr={DkId}` ∪ dzīvo lapu ∪ `getTechDKP`. Balsojumi
tiek skaitīti pēc (datums, laiks), jo viens balsojums var nākt divās URL formās.
Atbilde bez nevienas rindas punktam ar apakšpunktiem, `nr={DkId}` bez punktiem
vai cita datuma sēde = kļūda, izejas kods 2. Bez `--tech` dzīvā sēde joprojām
ir STOP ar kodu 2.
"""
from __future__ import annotations

import argparse
import json
import re
import sqlite3
import sys
import time
from collections import Counter
from datetime import date, timedelta
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(REPO_ROOT))

from scripts.p3_backfill_year_urllib import (  # noqa: E402
    _DRAW_DKP_ARG_RE,
    _DRAW_DKP_PR_RE,
    TechDKPError,
    _extract_vote_urls_from_agenda,
    _fetch,
    _parse_vote_page,
    collect_agenda_votes,
)
from src import db as _src_db  # noqa: E402
from src.saeima import _resolve_vote_url  # noqa: E402
from src.saeima.convocation import base_url  # noqa: E402
from src.saeima.manifest import load_manifest  # noqa: E402
from src.saeima.unloadable import is_unloadable  # noqa: E402
from src.saeima.unloadable import lookup as unloadable_lookup  # noqa: E402

MANIFEST_PATH = REPO_ROOT / "data" / "saeima_backfill_sessions.json"
# Caur `src.db`, lai testos conftest § 4 aizšķērsotais ceļš sniedzas arī līdz šejienei.
DB_PATH = str(REPO_ROOT / _src_db.DB_PATH)

# Cik vecs manifests vēl der skrējienam BEZ `--dates`. Ar `--dates` slieksnis
# nav vajadzīgs: tur ir konkrēta diena, ar ko salīdzināt.
MANIFEST_MAX_AGE_DAYS = 14

# Cik ilgi `parentID=` saite vēl nav kļūme: titania lapas pārarhivē ap nedēļu pēc sēdes.
PARENTID_MAX_AGE_DAYS = 7


def _parentid_counts(db_path: str, today: date) -> dict | None:
    """(`parentID=` saites, kopā, vecākas par slieksni, vecākā diena); bez tīkla un manifesta.

    `None`, ja DB nav: reālā skrējienā `_db_index()` tūlīt pēc tam krīt, tāpēc
    tas nepārvēršas par zaļu iznākumu.
    """
    if not Path(db_path).exists():
        return None
    cutoff = (today - timedelta(days=PARENTID_MAX_AGE_DAYS)).isoformat()
    db = sqlite3.connect(f"{Path(db_path).resolve().as_uri()}?mode=ro", uri=True)
    try:
        total, parentid, stale, oldest = db.execute(
            """SELECT COUNT(*),
                      COALESCE(SUM(url LIKE '%parentID=%'), 0),
                      COALESCE(SUM(url LIKE '%parentID=%' AND (vote_date IS NULL OR vote_date < ?)), 0),
                      MIN(CASE WHEN url LIKE '%parentID=%' AND vote_date < ? THEN vote_date END)
               FROM saeima_votes""",
            (cutoff, cutoff),
        ).fetchone()
    finally:
        db.close()
    return {"total": total, "parentid": parentid, "stale": stale, "oldest": oldest}


def _regenerate_hint(year: int) -> str:
    """Viens teksts abiem manifesta STOP-iem — divas versijas novirzītos."""
    return (
        "  Pārģenerē manifestu:\n"
        "    1) uztver kalendāra lapu ar Playwright (sk. scripts/"
        "_p3_extract_sessions_2026-05-26.py docstring)\n"
        f"    2) .venv/Scripts/python.exe scripts/_p3_extract_sessions_2026-05-26.py "
        f"--max-year {year}"
    )


def _manifest_age_stop(generated_at: str | None, requested: list[str],
                       year: int, today: date) -> str | None:
    """STOP teksts, ja manifests ir par vecu šim skrējienam; citādi None.

    MANIFESTA VECUMA VĀRTI (2026-09-02). Manifests ir kalendāra momentuzņēmuma
    atvasinājums — tas fiziski neredz nevienu sēdi, kas notikusi PĒC
    ģenerēšanas. Vecais T8 vārts (`if not in_year:`) nostrādā tikai tad, kad
    trūkst VESELA gada, tāpēc tas nevarēja nostrādāt gadījumā, kura dēļ tas
    pastāv: 2026-09-02 manifests bija no 08-01, 2026. gads tajā BIJA, bet
    2026-08-20 sēdes divi UUID nebija. `--dates 2026-08-20` nofiltrēja sarakstu
    līdz tukšam, audits neapmeklēja nevienu darba kārtību un izdrukāja
    „trūkst 0" — kamēr DB trūka 25 balsojumu.
    """
    if not generated_at:
        return (
            f"STOP: manifestam ({MANIFEST_PATH.name}) nav lauka `generated_at` — "
            "tā vecums nav zināms.\n"
            "  Nezināms vecums nav svaigums: manifests neredz nevienu sēdi, kas "
            "notikusi pēc ģenerēšanas, un audits par tādu dienu izdrukā "
            "„trūkst 0“, nepaskatījies ne reizi (T8).\n"
            + _regenerate_hint(year)
        )
    try:
        generated = date.fromisoformat(generated_at)
    except ValueError:
        return (
            f"STOP: manifesta ({MANIFEST_PATH.name}) lauks `generated_at` nav "
            f"nolasāms datums: {generated_at!r}.\n"
            + _regenerate_hint(year)
        )

    if requested:
        newest = max(requested)
        if generated_at < newest:
            return (
                f"STOP: manifests ({MANIFEST_PATH.name}) ir vecāks par "
                "auditējamo dienu.\n"
                f"  Manifests ģenerēts: {generated_at}\n"
                f"  Jaunākais pieprasītais datums: {newest}\n"
                "  Sēde, kas notikusi pēc manifesta ģenerēšanas, tajā "
                "neeksistē — audits to neredz un izdrukā „trūkst 0“. Tas ir "
                "MANIFESTA ROBS, ne tīra diena (T8).\n"
                + _regenerate_hint(year)
            )
        return None

    age = (today - generated).days
    if age > MANIFEST_MAX_AGE_DAYS:
        return (
            f"STOP: manifests ({MANIFEST_PATH.name}) ir novecojis — ģenerēts "
            f"{generated_at}, pirms {age} dienām (slieksnis: "
            f"{MANIFEST_MAX_AGE_DAYS} dienas).\n"
            "  Katra sēde, kas notikusi pēc tam, auditam neeksistē, un tās "
            "diena skaitās tīra, jo neviens tajā nav paskatījies (T8).\n"
            + _regenerate_hint(year)
        )
    return None


def _session_date(session: dict) -> str:
    return f"{session['year']}-{session['month']:02d}-{session['day']:02d}"


def _live_session_stop(live: list[dict], year: int) -> str:
    """STOP teksts dzīvajai (`active=1`/`actual=1`) sēdei — 4. VĀRTI (2026-09-16).

    Kalendārs kārtējai dienai nedod `nr={UUID}`, tāpēc līdz 2026-09-16 tāda diena
    manifestā neiekļuva vispār un `--dates 2026-09-10` izdrukāja „DK=0, trūkst 0",
    kaut sēdē bija 16 balsojumi. Tagad rinda manifestā IR — bet redzama nav tas
    pats, kas auditējama, un tieši šeit gulēja otrais viltus zaļais:

      (a) `active=1` NAV piesaistīts datumam — nākamajā dienā tas pats URL rāda
          jau citu sēdi, tāpēc pēc tā rēķināta paritāte apgalvo par nepareizo dienu;
      (b) dzīvā lapa APAKŠPUNKTU balsojumus nerenderē — 2026-09-10 tā deva 16,
          bet `nr={DkId}` formā tai pašai sēdei ir 21 (backlog/saeima.md, otrā
          instance 2026-09-14: viltus zaļais slēpa 5 balsojumus, ne 0).
    """
    return (
        f"STOP: manifestā ({MANIFEST_PATH.name}) šīm dienām ir tikai DZĪVĀ sēdes "
        f"forma (`DK?ReadForm&active=1`), bez `nr={{UUID}}`: "
        f"{', '.join(sorted(_session_date(s) for s in live))}\n"
        "  Dzīvu darba kārtību audits NEATVER un ar to NEDRĪKST iziet ar 0:\n"
        "    (a) `active=1` nav piesaistīts datumam — rīt tas pats URL rāda citu sēdi;\n"
        "    (b) dzīvā lapa nerenderē APAKŠPUNKTU balsojumus (2026-09-10: 16 pret "
        "21 `nr={DkId}` formā).\n"
        "  Ko darīt: palaid ar `--tech` — audits pats nolasa dzīvās lapas "
        "`var actualXML_DkId`, atver `DK?ReadForm&nr={DkId}` un seko `getTechDKP`; "
        "ja tas neizdodas, kļūda ir nosaukta augstāk. Vai pārģenerē manifestu, kad "
        "titania sēdei ir piešķīrusi `nr={UUID}`.\n"
        + _regenerate_hint(year)
    )


def _session_dates(session: dict) -> list[str]:
    """Sēdes bāzes datums + turpinājuma dienas (`continued_on`, 2026-09-25).

    2026-09-03 sēde ir 07-23 ārkārtas sesijas sēdes turpinājums ar to pašu
    UUID; manifestā tai nav savas rindas, tikai `continued_on` īpašnieka rindā.
    Vecos manifestos atslēgas nav — tāpēc `.get(..., [])`.
    """
    return [_session_date(session), *session.get("continued_on", [])]


def _select_sessions(in_year: list[dict], requested: list[str],
                     today: str) -> tuple[list[dict], list[dict]]:
    """(auditējamās, nākotnes) — tīra funkcija, lai atlasi var testēt bez tīkla.

    Nākotnes filtrs iet pēc BĀZES datuma: sēde, kas jau sākusies, nav nākotne.
    `--dates` filtrs iet pēc JEBKURA sēdes datuma, citādi turpinājuma diena
    (2026-09-03) netiek atlasīta un audits ziņo zaļu, kamēr DB trūkst balsojumu.
    """
    future = [s for s in in_year if _session_date(s) > today]
    sessions = [s for s in in_year if _session_date(s) <= today]
    if requested:
        want = set(requested)
        sessions = [s for s in sessions if want.intersection(_session_dates(s))]
    return sessions, future


def _uncovered_dates(in_year: list[dict], requested: list[str]) -> list[str]:
    """Pieprasītie datumi, kuriem manifestā nav NEVIENAS sēdes rindas
    (ieskaitot turpinājuma dienas)."""
    have = {d for s in in_year for d in _session_dates(s)}
    return [d for d in requested if d not in have]


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


def _db_url_moments() -> dict[str, tuple[str, str]]:
    """{url: (vote_date, vote_time)} — tikai `--tech` ceļam, tikai lasa.

    Vajadzīgs, lai viens balsojums divās URL formās (`/0/{HEX}` no `nr=` lapas un
    `parentID=` no dzīvās lapas) netiktu skaitīts divreiz: `store_vote()` kopš
    2026-11-07 to pašu (datums, laiks ar sekundēm) uzskata par vienu balsojumu.
    """
    db = sqlite3.connect(f"{Path(DB_PATH).resolve().as_uri()}?mode=ro", uri=True)
    try:
        return {r[0]: (r[1], r[2]) for r in db.execute(
            "SELECT url, vote_date, vote_time FROM saeima_votes") if r[0] and r[1] and r[2]}
    finally:
        db.close()


_DKID_RE = re.compile(r'actualXML_DkId\s*=\s*"([0-9A-Fa-f]{32})"')
_DRAW_DKP_DT_ARG = 14  # 34-arg forma: punkta datums «DD.MM.YYYY» (`nr=` lapā)


def _dashed(hex32: str) -> str:
    """`actualXML_DkId` nāk bez domuzīmēm; `nr=` bez tām atdod TUKŠU darba kārtību
    (mērīts 2026-11-10: 0 `drawDKP_*` izsaukumu), tāpēc GUID jāsaliek atpakaļ."""
    h = hex32.lower()
    return f"{h[:8]}-{h[8:12]}-{h[12:16]}-{h[16:20]}-{h[20:]}"


def _live_pages(session: dict, base: str) -> list[tuple[str, str]]:
    """Dzīvās sēdes lapas `--tech` ceļam: [(avots, html)] — `nr={DkId}` un dzīvā.

    Kļūme (`RuntimeError`) = automātiskais ceļš nevar strādāt → sēde paliek
    nepārbaudīta, izejas kods 2. Datuma pārbaude sargā no (a): `active=1`
    nākamajā dienā rāda jau citu sēdi.
    """
    live_url = session.get("url") or f"{base}/DK?ReadForm&actual=1"
    live_html = _fetch(live_url)
    m = _DKID_RE.search(live_html)
    if not m:
        raise RuntimeError(f"dzīvajā lapā nav `var actualXML_DkId` ({live_url})")
    nr_url = f"{base}/DK?ReadForm&nr={_dashed(m.group(1))}"
    nr_html = _fetch(nr_url)
    calls = [_DRAW_DKP_ARG_RE.findall(c.group(1)) for c in _DRAW_DKP_PR_RE.finditer(nr_html)]
    if not calls:
        raise RuntimeError(f"`nr={{DkId}}` darba kārtībā 0 punktu — formāta robs (T12): {nr_url}")
    want = {f"{d[8:10]}.{d[5:7]}.{d[:4]}" for d in _session_dates(session)}
    seen = {a[_DRAW_DKP_DT_ARG] for a in calls if len(a) > _DRAW_DKP_DT_ARG and a[_DRAW_DKP_DT_ARG]}
    if not want & seen:
        raise RuntimeError(
            f"dzīvā lapa rāda citu sēdi: `nr={{DkId}}` punktu datumi "
            f"{', '.join(sorted(seen)) or '—'}, gaidīts {', '.join(sorted(want))}")
    return [("nr={DkId}", nr_html), ("dzīvā", live_html)]


def _iso(parsed: dict) -> tuple[str | None, str | None]:
    if not parsed.get("date"):
        return None, parsed.get("time")
    try:
        dd, mm, yyyy = parsed["date"].split(".")
        return f"{yyyy}-{mm}-{dd}", parsed.get("time")
    except ValueError:
        return None, parsed.get("time")


def _tech_union(pages: list[tuple[str, str]], base: str, out: dict, actual: bool,
                delay: float) -> list[str]:
    """`--tech`: katras lapas balsojumi ∪ tās `getTechDKP` apakšpunkti; skaitļi → `out`."""
    def fetch(url: str) -> str:
        html = _fetch(url)
        if delay:
            time.sleep(delay)
        return html

    union: list[str] = []
    have: set[str] = set()
    page_votes: set[str] = set()
    tech_votes: set[str] = set()
    for source, html in pages:
        r = collect_agenda_votes(html, base, fetch=fetch, actual=actual)
        out["sources"][source] = len(r["agenda"])
        page_votes.update(r["agenda"])
        tech_votes.update(r["tech"])
        out["tech_points"] += r["tech_points"]
        out["tech_fetched"] += r["tech_fetched"]
        for u in r["union"]:
            if u not in have:
                have.add(u)
                union.append(u)
    out["sources"]["getTechDKP"] = len(tech_votes)
    out["tech_only"] = len(tech_votes - page_votes)
    return union


def audit_session(session: dict, db_dt: set, db_urls: set, delay: float, *,
                  tech: bool = False, url_moments: dict | None = None) -> dict:
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
    if tech:
        out.update({"sources": {}, "tech_points": 0, "tech_fetched": 0,
                    "tech_only": 0, "same_moment": 0})

    # Sēdes SAVA sasaukuma bāze: pēc pārslēgšanas uz 15. Saeimu 14. sasaukuma
    # darba kārtības dzīvo LIVS14. Rinda bez atslēgas = 14 (vecie manifesti).
    base = base_url(session.get("convocation", 14))
    try:
        if session.get("uuid"):
            pages = [("nr=", _fetch(f"{base}/DK?ReadForm&nr={session['uuid']}"))]
        else:  # dzīvā sēde — šeit nonāk tikai ar `--tech`
            pages = _live_pages(session, base)
    except Exception as e:  # noqa: BLE001
        out["error"] = f"agenda fetch: {e}"
        return out

    if tech:
        try:
            vote_urls = _tech_union(pages, base, out, actual=not session.get("uuid"),
                                    delay=delay)
        except TechDKPError as e:
            out["error"] = f"getTechDKP: {e}"
            return out
        except Exception as e:  # noqa: BLE001
            out["error"] = f"getTechDKP fetch: {e}"
            return out
    else:
        vote_urls = _extract_vote_urls_from_agenda(pages[0][1], base=base)
    out["agenda_votes"] = len(vote_urls)

    # `--tech`: viens balsojums var nākt divās URL formās — skaita pēc (datums, laiks).
    seen_moments: set[tuple[str, str]] = set()

    def _dup(moment: tuple[str, str] | None) -> bool:
        if not tech or not moment:
            return False
        if moment in seen_moments:
            out["same_moment"] += 1
            return True
        seen_moments.add(moment)
        return False

    for url in vote_urls:
        full = _resolve_vote_url(url)
        if full in db_urls:
            if _dup((url_moments or {}).get(full)):
                continue
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
        if _dup((iso_date, vtime)):
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
    ap.add_argument("--tech", action="store_true",
                    help="seko getTechDKP katram punktam ar apakšpunktiem; dzīvajai "
                         "sēdei nolasa actualXML_DkId un auditē nr={DkId} formu")
    args = ap.parse_args()

    manifest, generated_at = load_manifest(MANIFEST_PATH)
    manifest_years = {s["year"] for s in manifest}
    in_year = [s for s in manifest if s["year"] == args.year]
    requested = [d.strip() for d in args.dates.split(",") if d.strip()] if args.dates else []

    # Pirms visiem STOP: šim skaitam nevajag ne tīklu, ne manifestu.
    parentid = _parentid_counts(DB_PATH, date.today())
    if parentid:
        print(f"parentID= saites: {parentid['parentid']} no {parentid['total']} balsojumiem; "
              f"vecākas par {PARENTID_MAX_AGE_DAYS} dienām: {parentid['stale']}")
    else:
        print(f"parentID= saites: NAV PĀRBAUDĪTAS, DB nav atrasta ({DB_PATH})")

    # 1. VĀRTI — manifesta vecums. Iet PIRMS gada vārtiem: „šis manifests
    # nevar atbildēt par šo dienu" ir pamatīgāks fakts nekā „šajā gadā nav
    # sēžu", un abu remonts ir viens un tas pats.
    age_stop = _manifest_age_stop(generated_at, requested, args.year, date.today())
    if age_stop:
        print(age_stop, file=sys.stderr)
        return 2

    # 2. VĀRTI — T8 PAŠA RĪKA LĪMENĪ. Līdz 2026-08-01 manifestā bija tikai 2022.–2025. gads,
    # tāpēc `--year 2026` filtrēja līdz TUKŠAM sarakstam un rīks mierīgi
    # izdrukāja „KOPĀ: darba kārtībā 0, trūkst 0" — tīrs pārskats par gadu, kurā
    # tas nebija paskatījies ne reizi. 0 sēžu iekšā NAV tīrs gads; tas ir
    # manifesta robs, un rīkam par to jāapstājas, ne jāziņo zaļš.
    if not in_year:
        print(
            f"STOP: manifestā ({MANIFEST_PATH.name}) nav nevienas {args.year}. gada "
            f"sēdes.\n"
            f"  Manifestā ir gadi: {', '.join(str(y) for y in sorted(manifest_years))}\n"
            "  Tas ir MANIFESTA ROBS, ne tīrs gads (T8).\n"
            + _regenerate_hint(args.year),
            file=sys.stderr,
        )
        return 2

    # 3. VĀRTI — pieprasīta diena, kurai manifestā nav nevienas rindas. Gada
    # vārti to nepamana (gads manifestā ir), un `--dates` filtrs to klusi
    # nogriež līdz tukšam sarakstam. Tieši šeit 2026-08-20 sēdes 25 balsojumi
    # pārvērtās par „trūkst 0".
    uncovered = _uncovered_dates(in_year, requested)
    if uncovered:
        print(
            f"STOP: manifestā ({MANIFEST_PATH.name}) nav nevienas {args.year}. gada "
            f"sēdes šajos pieprasītajos datumos: {', '.join(sorted(uncovered))}\n"
            "  Datums bez manifesta rindas nav tīra diena — audits tam neatver "
            "nevienu darba kārtību un izdrukā „trūkst 0“ (T8).\n"
            + _regenerate_hint(args.year),
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
    #
    # Nākotnes sēde nevar būt robs. Kalendārs uzskaita visu gadu uz priekšu,
    # tāpēc bez šī filtra vēl nenotikusi sēde atgrieztu 0 darba kārtības
    # balsojumu un izskatītos pēc tukšas dienas. `--dates` atlasa pēc JEBKURA
    # sēdes datuma, ieskaitot turpinājumus — sk. `_select_sessions()`.
    today = date.today().isoformat()
    sessions, future = _select_sessions(in_year, requested, today)
    sessions.sort(key=lambda s: (s["month"], s["day"]))

    # 4. VĀRTI — DZĪVĀ sēde (2026-09-16). Šķirtne ir `not s.get("uuid")`, nevis
    # jaunā `live` atslēga: vecos manifestos tās nav, un vārti, kas paļaujas uz
    # jauno lauku, klusi izlaistu tieši veco failu.
    # Ar `--tech` dzīvā sēde IR auditējama (nr={DkId} ∪ getTechDKP); ja tas
    # neizdodas, tās rinda iet kļūdas ceļā — tas pats izejas kods 2.
    live = [s for s in sessions if not s.get("uuid")]
    if not args.tech:
        sessions = [s for s in sessions if s.get("uuid")]

    if args.limit:
        sessions = sessions[: args.limit]

    db_dt, db_urls = _db_index()
    url_moments = _db_url_moments() if args.tech else None
    print(f"DB: {len(db_dt)} unikāli (datums, laiks); {len(db_urls)} URL")
    print(f"Manifests ģenerēts: {generated_at}")
    print(f"Manifestā {args.year}. gadā: {len(in_year)} sēdes "
          f"({', '.join(f'{t}={n}' for t, n in sorted(Counter(s['session_type'] for s in in_year).items()))})")
    if future:
        print(f"Izlaistas (vēl nav notikušas, > {today}): {len(future)} — "
              + ", ".join(f"{s['year']}-{s['month']:02d}-{s['day']:02d}" for s in future))
    if live:
        print("DZĪVĀS SĒDES (kalendārā `active=1`/`actual=1`, bez `nr={UUID}`) — "
              + ("auditē caur nr={DkId} ∪ getTechDKP" if args.tech else "NEAUDITĒJAMAS")
              + f": {len(live)} — "
              + ", ".join(sorted(_session_date(s) for s in live)))
    print(f"Auditējamas sēdes: {len(sessions)}\n")
    if not sessions:
        if live and not args.tech:
            print(_live_session_stop(live, args.year), file=sys.stderr)
            return 2
        print("STOP: pēc filtriem nepalika neviena auditējama sēde — sk. augšējās "
              "rindas. Tas nav tīrs gads.", file=sys.stderr)
        return 2
    print(f"{'datums':<12} {'tips':<10} {'DK':>4} {'URL✓':>5} {'DT✓':>5} {'TRŪKST':>7} {'?':>3}")
    print("-" * 52)

    results = []
    for s in sessions:
        r = audit_session(s, db_dt, db_urls, args.delay, tech=args.tech,
                          url_moments=url_moments)
        results.append(r)
        flag = "  ERR" if r["error"] else ""
        # Turpinājuma sēdei viena darba kārtība sedz vairākas dienas — to
        # nosauc blakus bāzes datumam, citādi 2026-09-03 trūkstošie balsojumi
        # izskatītos piederīgi 07-23 rindai bez paskaidrojuma.
        cont = s.get("continued_on", [])
        cont_note = f"  (turpinājums: {', '.join(cont)})" if cont else ""
        print(f'{r["date"]:<12} {r["session_type"]:<10} {r["agenda_votes"]:>4} '
              f'{r["present_by_url"]:>5} {r["present_by_datetime"]:>5} '
              f'{len(r["missing"]):>7} {len(r["unreadable"]):>3}{flag}{cont_note}')
        if r["error"]:
            print(f'    {r["error"]}')
        elif args.tech:
            # Saucējs pa avotiem: cik deva katra lapa, cik getTechDKP, cik no tiem
            # nebija nevienā lapā, un cik unikālu balsojumu pēc (datums, laiks).
            src = ", ".join(f"{k} {v}" for k, v in r["sources"].items())
            print(f'    avoti: {src}; punkti ar apakšpunktiem {r["tech_points"]}, '
                  f'getTechDKP atbildes {r["tech_fetched"]}, tikai getTechDKP '
                  f'{r["tech_only"]}; apvienība {r["agenda_votes"]} URL = '
                  f'{r["agenda_votes"] - r["same_moment"]} balsojumi; DB '
                  f'{r["present_by_url"] + r["present_by_datetime"]}')

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
        live_failed = [s for s in live if any(r["date"] == _session_date(s) for r in errored)]
        if live_failed:
            print("\n" + _live_session_stop(live_failed, args.year), file=sys.stderr)
        return 2
    # Dzīvā sēde STOP-o TIKAI BEIGĀS, tāpat kā fetch kļūmes: gada skrējiens
    # apstaigā visu, ko var, un tikai tad atsakās no zaļā.
    if live and not args.tech:
        print("\n" + _live_session_stop(live, args.year), file=sys.stderr)
        return 2
    if parentid and parentid["stale"]:
        print(f"\nKĻŪME: {parentid['stale']} balsojumiem saite `parentID=` vecāka par "
              f"{PARENTID_MAX_AGE_DAYS} dienām (vecākā {parentid['oldest']}); šīs lapas drīz būs tukšas. "
              "Palaid: .venv/Scripts/python.exe scripts/fix_parentid_vote_urls.py",
              file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
