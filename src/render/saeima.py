"""Render saeima.html — 15. Saeimas pusloks (sēdvietu karte ar četrām lēcām).

Spec: docs/superpowers/specs/2026-10-08-saeimas-pusloks-design.md.

Sastāvs = SĒDOŠIE: ievēlēto saraksta fails (CVK oficiālais, apstiprināts 2026-10-16)
mīnus ministri, kas nolikuši mandātu, plus viņu aizstājēji (``mandates`` amatu YAML); saraksta
nosaukums un krāsa = CVK rezultātu fails + ``parties``. Sasaiste ar profilu —
TIKAI precīzs pilnais ``tracked_politicians.name`` (T1: nekādu apakšvirkņu) un
tikai tiem, kam profila lapa tiešām tiek renderēta (tas pats WHERE kā
``_fetch_politicians``), lai sēdvieta nekad nevestu uz 404.

Visas lēcu vērtības aprēķina šeit; lapa bez JS rāda «Saraksta» lēcu un strādā.
``assets/slv1.js`` tikai pārslēdz ``data-lens`` un atver kartīti.

Amati (Prezidijs, frakciju vadība, komisiju sastāvs) — no kurētā
``data/saeima15_amati.yaml`` (spec: 2026-11-11-saeimas-lapa-amati-design.md),
NE no ``tracked_politicians.role`` (brīvs teksts, T6). Neatbilstība → KRĪT.

Lēcas «Koalīcija» un «Uzticības balsojums» (2026-11-18) rāda tikai tad, kad
jaunākā ``coalition_periods`` rinda ir ŠĪ sasaukuma uzticības balsojums:
koalīcija = ``parties.coalition_status`` (caur ``get_coalition_map``, nekad
``relationship_type``), balss = tā paša balsojuma ``saeima_individual_votes``
rinda pēc precīzā vārda ``politician_id``. Rindas nav → «nav ieraksta», nekad «pret».
"""

from __future__ import annotations

import datetime as _dt
import math
import sqlite3
from pathlib import Path
from typing import Any, NoReturn

import yaml
from jinja2 import Environment

from src.render._common import (
    lv_date,
    ASSETS_DIR,
    _lv_number,
    _lv_plural,
    _render_page,
    _slugify,
    trailing_days_cutoff,
)
from src.render._common.constants import PROJECT_ROOT
from src.coalition import get_coalition_map
from src.render._common.cvk import read_elected, read_election_results
from src.saeima.convocation import SAEIMA_CONVOCATION, base_url
from src.render.valdiba import VALDIBA_PUBLISHED, fetch_cabinet
from src.scope import not_attendance_sql

# Testi (test_render_chars, test_render_saeima) visus trīs pārsien uz fixture kopijām.
ELECTED_PATH = PROJECT_ROOT / "data" / "cvk_sv2026_ievēlētie.yaml"
RESULTS_PATH = PROJECT_ROOT / "data" / "cvk_sv2026_rezultati.yaml"
AMATI_PATH = PROJECT_ROOT / "data" / "saeima15_amati.yaml"

PRESIDIUM_SIZE = 5
# Atļautie amatu teksti (saeima.lv formas abām dzimtēm). Cits teksts → KRĪT:
# drukas kļūda YAML nedrīkst klusi nonākt lapā.
_PRESIDIUM_OFFICES = {
    "Saeimas priekšsēdētājs", "Saeimas priekšsēdētāja",
    "Saeimas priekšsēdētāja biedrs", "Saeimas priekšsēdētāja biedre",
    "Saeimas priekšsēdētājas biedrs", "Saeimas priekšsēdētājas biedre",
    "Saeimas sekretārs", "Saeimas sekretāre",
    "Saeimas sekretāra biedrs", "Saeimas sekretāra biedre",
    "Saeimas sekretāres biedrs", "Saeimas sekretāres biedre",
}
_FACTION_TITLES = {
    "chair": {"Priekšsēdētājs", "Priekšsēdētāja"},
    "deputy": {
        "Priekšsēdētāja vietnieks", "Priekšsēdētāja vietniece",
        "Priekšsēdētājas vietnieks", "Priekšsēdētājas vietniece",
    },
}

# Komisijas amats (verbatim no saeima.lv) → loma. Cits teksts → KRĪT.
_COMMITTEE_TITLES = {
    "chair": {"Priekšsēdētājs", "Priekšsēdētāja"},
    "deputy": {
        "Priekšsēdētāja biedrs", "Priekšsēdētāja biedre",
        "Priekšsēdētājas biedrs", "Priekšsēdētājas biedre",
    },
    "secretary": {"Sekretārs", "Sekretāre"},
    "member": {"Deputāts", "Deputāte"},
}
_COMMITTEE_ROLE = {t: role for role, titles in _COMMITTEE_TITLES.items() for t in titles}
# 15. Saeimas pastāvīgās komisijas (saeima.lv, 25.11.). Mazāk ierakstu YAML = izkritusi komisija.
COMMITTEES_TOTAL = 16
# 25.11. katrs no 100 sēdošajiem ir tieši divās komisijās. Neviena = izkritis loceklis
# (vai sēdošo sarakstā kāds, kas nesēž); trīs = dublikāts starp komisijām.
_COMMITTEES_PER_DEPUTY = (1, 2)

SEATS_TOTAL = 100
POSITIONS_WINDOW_DAYS = 90

# coalition_status → lēcas vērtība un teksts; cits statuss (not_in_saeima,
# other, saraksts bez partijas) = «nav datu», nekad kāda no abām pusēm.
_GOV_STATUS = {"coalition": "koalicija", "opposition": "opozicija"}
_GOV_TEXT = {"koalicija": "koalīcija", "opozicija": "opozīcija", "nav": "nav datu"}
# Balsojuma vērtība → lēcas vērtība un teksts. Cita vērtība (Reģistrējies…)
# uzticības balsojumā → KRĪT: tā nav balss, un minēt to nedrīkst.
_CAST = {"Par": "par", "Pret": "pret", "Atturas": "atturas", "Nebalsoja": "nebalsoja"}
_CAST_TEXT = {
    "par": "balsoja par", "pret": "balsoja pret", "atturas": "atturējās",
    "nebalsoja": "nebalsoja", "nav": "nav ieraksta",
}

# Pusloka ģeometrija: 6 rindas, iekšējais rādiuss 0,36 no ārējā. Sēdvietas
# rindā ∝ rindas rādiusam, tāpēc attālumi starp apļiem visās rindās ~vienādi
# (min ~0,128 vienības; redzamais aplis 0,05, trāpījuma aplis 0,064).
_ROWS = 6
_R_INNER = 0.36
_SCALE = 200  # SVG vienības uz rādiusu 1
_DOT_R = 0.05
_HIT_R = 0.064
# Amatpersonas gredzens: rādiuss + puse līnijas < pusei min. attāluma (0,064),
# lai divu blakus amatpersonu gredzeni nesaskaras.
_RING_R = 0.06


def _arc_positions(n: int) -> list[tuple[float, float]]:
    """n sēdvietu (x, y) SVG koordinātās, sakārtotas no kreisās uz labo.

    Kārtošana pēc leņķa (π → 0) visās rindās kopā dod saraksta «ķīli» no
    centra uz āru — tāpat kā parlamenta diagrammās.
    """
    radii = [_R_INNER + (1 - _R_INNER) * i / (_ROWS - 1) for i in range(_ROWS)]
    total_r = sum(radii)
    raw = [n * r / total_r for r in radii]
    counts = [math.floor(x) for x in raw]
    for i in sorted(range(_ROWS), key=lambda i: -(raw[i] - counts[i]))[: n - sum(counts)]:
        counts[i] += 1
    seats: list[tuple[float, int, float, float]] = []
    for row, (r, k) in enumerate(zip(radii, counts, strict=True)):
        for j in range(k):
            theta = math.pi * (1 - j / (k - 1)) if k > 1 else math.pi / 2
            seats.append((theta, row, r * math.cos(theta), r * math.sin(theta)))
    seats.sort(key=lambda s: (-round(s[0], 9), s[1]))
    return [(round(x * _SCALE, 2), round(-y * _SCALE, 2)) for _, _, x, y in seats]


def _pos_bucket(n: int | None) -> str:
    if n is None:
        return "nav"
    if n == 0:
        return "0"
    if n < 5:
        return "1"
    if n < 20:
        return "5"
    return "20"


def _ctr_bucket(n: int | None) -> str:
    if n is None:
        return "nav"
    return "0" if n == 0 else ("1" if n == 1 else "2")


def _seats_text(n: int) -> str:
    return f"{n} {_lv_plural(n, 'vieta', 'vietas')}"


def _load_composition(
    elected_path: Path, results_path: Path
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Ievēlētie + rezultātu dokuments. Nepilns vai nesaskanīgs sastāvs → KRĪT."""
    elected = read_elected(elected_path)
    if len(elected) != SEATS_TOTAL:
        raise ValueError(
            f"saeima: sastāva failā {elected_path.name} ir {len(elected)} ieraksti, "
            f"jābūt {SEATS_TOTAL}"
        )
    results = read_election_results(results_path)
    if results is None:
        raise ValueError(f"saeima: nav CVK rezultātu faila {results_path}")
    known = {x["list_nr"] for x in results["lists"]}
    missing = sorted({e["list_nr"] for e in elected} - known)
    if missing:
        raise ValueError(f"saeima: saraksta nr. {missing} nav rezultātu failā")
    slugs = [_slugify(e["name"]) for e in elected]
    if len(set(slugs)) != len(slugs):
        raise ValueError("saeima: divi deputāti ar vienādu slug — #dep- enkuri sadurtos")
    return elected, results


def _short_date(d: Any) -> str:
    """YAML datums (datetime.date vai 'YYYY-MM-DD') → '11.11.'."""
    if isinstance(d, str):
        d = _dt.date.fromisoformat(d)
    return f"{d.day:02d}.{d.month:02d}." if isinstance(d, _dt.date) else ""


def _apply_mandates(
    mandates: dict[str, Any], elected: list[dict[str, Any]], fail: Any
) -> list[dict[str, Any]]:
    """Ievēlētie − mandātu nolikušie ministri + deputāti viņu vietā = sēdošie.

    Aizstājējs nāk no tā paša saraksta, tāpēc katram sarakstam abu skaitam jāsakrīt;
    aizstājējs stāv sava saraksta beigās (pārus — kurš kura vietā — neglabājam).
    """
    if not mandates:
        return list(elected)
    list_of = {e["name"]: e["list_nr"] for e in elected}
    short_of = {e["list_nr"]: e.get("list_short") for e in elected}
    out = mandates.get("suspended") or []
    subs = mandates.get("substitutes") or []
    if len(set(out)) != len(out):
        fail("mandates.suspended — vārds divreiz")
    delta: dict[int, int] = {}
    for name in out:
        if name not in list_of:
            fail(f"mandates.suspended — {name!r} nav ievēlēto sarakstā")
        delta[list_of[name]] = delta.get(list_of[name], 0) - 1
    seen: set[str] = set()
    for s in subs:
        if s["name"] in list_of:
            fail(f"mandates.substitutes — {s['name']!r} jau ir ievēlēto sarakstā")
        if s["name"] in seen:
            fail(f"mandates.substitutes — {s['name']!r} divreiz")
        if s.get("list_nr") not in short_of:
            fail(f"mandates.substitutes — {s['name']!r}: saraksts {s.get('list_nr')!r} nav ievēlēto vidū")
        seen.add(s["name"])
        delta[s["list_nr"]] = delta.get(s["list_nr"], 0) + 1
    uneven = sorted(nr for nr, d in delta.items() if d)
    if uneven:
        fail(f"mandates — sarakstam(-iem) {uneven} nolikto un aizstājēju skaits nesakrīt")
    gone = set(out)
    sitting = [e for e in elected if e["name"] not in gone]
    for nr in dict.fromkeys(e["list_nr"] for e in elected):
        sitting += [
            {"name": s["name"], "list_nr": nr, "list_short": short_of[nr], "region": "", "substitute": True}
            for s in subs if s["list_nr"] == nr
        ]
    return sitting


def _check_committees(committees: dict[str, Any], list_of: dict[str, int], fail: Any) -> None:
    """16 komisijas; katrā tieši viens priekšsēdētājs, biedrs un sekretārs; locekļi = sēdošie."""
    if committees.get("status") != "elected":
        fail(f"komisiju statuss {committees.get('status')!r} nav atbalstīts")
    items = committees.get("items") or []
    if len(items) != COMMITTEES_TOTAL:
        fail(f"komisiju ir {len(items)}, jābūt {COMMITTEES_TOTAL}")
    if len({c.get("name") for c in items}) != len(items):
        fail("komisijas nosaukums divreiz")
    seats: dict[str, int] = {}
    for c in items:
        cname = c.get("name")
        members = c.get("members") or []
        roles: dict[str, int] = {}
        names: set[str] = set()
        for m in members:
            name, title = m.get("name"), m.get("title")
            if name not in list_of:
                fail(f"{cname} — {name!r} nav sēdošo deputātu sarakstā")
            if title not in _COMMITTEE_ROLE:
                fail(f"{cname} — {name!r}: nezināms amats {title!r}")
            if name in names:
                fail(f"{cname} — {name!r} divreiz")
            names.add(name)
            roles[_COMMITTEE_ROLE[title]] = roles.get(_COMMITTEE_ROLE[title], 0) + 1
            seats[name] = seats.get(name, 0) + 1
        for role in ("chair", "deputy", "secretary"):
            if roles.get(role, 0) != 1:
                fail(f"{cname} — lomai {role!r} {roles.get(role, 0)} cilvēki, jābūt tieši vienam")
    lo, hi = _COMMITTEES_PER_DEPUTY
    odd = sorted(n for n in list_of if not lo <= seats.get(n, 0) <= hi)
    if odd:
        fail(f"{len(odd)} deputāti nav {lo}–{hi} komisijās: {odd[:5]}")


def _load_offices(path: Path, elected: list[dict[str, Any]]) -> dict[str, Any]:
    """Amatu YAML → pārbaudīts dict ar ``sitting`` (sēdošie 100). Neatbilstība → ValueError."""
    doc = yaml.safe_load(path.read_text(encoding="utf-8")) or {}

    def _fail(msg: str) -> NoReturn:
        raise ValueError(f"saeima: {path.name}: {msg}")

    sitting = _apply_mandates(doc.get("mandates") or {}, elected, _fail)
    if len(sitting) != SEATS_TOTAL:
        _fail(f"sēdošo ir {len(sitting)}, jābūt {SEATS_TOTAL}")
    slugs = [_slugify(e["name"]) for e in sitting]
    if len(set(slugs)) != len(slugs):
        _fail("divi sēdošie ar vienādu slug — #dep- enkuri sadurtos")
    doc["sitting"] = sitting
    list_of = {e["name"]: e["list_nr"] for e in sitting}

    presidium = (doc.get("presidium") or {}).get("members") or []
    if len(presidium) != PRESIDIUM_SIZE:
        _fail(f"Prezidijā {len(presidium)} locekļi, jābūt {PRESIDIUM_SIZE}")
    seen: set[str] = set()
    for m in presidium:
        if m["name"] not in list_of:
            _fail(f"Prezidijs — {m['name']!r} nav ievēlēto sarakstā")
        if m.get("office") not in _PRESIDIUM_OFFICES:
            _fail(f"Prezidijs — nezināms amats {m.get('office')!r}")
        if m["name"] in seen:
            _fail(f"Prezidijs — {m['name']!r} divreiz")
        seen.add(m["name"])

    seen_lists: set[int] = set()
    seen_leaders: set[str] = set()
    for f in (doc.get("factions") or {}).get("items") or []:
        nr = f.get("list_nr")
        if nr in seen_lists:
            _fail(f"frakcija list_nr={nr} divreiz")
        seen_lists.add(nr)
        leaders = f.get("leaders") or []
        if sum(1 for ld in leaders if ld.get("role") == "chair") != 1:
            _fail(f"frakcijai list_nr={nr} jābūt tieši vienam priekšsēdētājam")
        for ld in leaders:
            name = ld["name"]
            if name not in list_of:
                _fail(f"frakcija list_nr={nr} — {name!r} nav ievēlēto sarakstā")
            if list_of[name] != nr:
                _fail(f"{name!r} vada frakciju list_nr={nr}, bet ievēlēts no saraksta {list_of[name]}")
            if ld.get("title") not in _FACTION_TITLES.get(ld.get("role"), set()):
                _fail(f"{name!r} — amats {ld.get('title')!r} neder lomai {ld.get('role')!r}")
            if name in seen_leaders:
                _fail(f"frakciju vadībā {name!r} divreiz")
            seen_leaders.add(name)

    missing = sorted(set(list_of.values()) - seen_lists)
    if missing:
        # Citādi saraksts klusi paliktu bez vadības rindas.
        _fail(f"nav frakcijas ieraksta sarakstam(-iem) {missing}")

    _check_committees(doc.get("committees") or {}, list_of, _fail)
    return doc


def _fetch_people(db: sqlite3.Connection, names: list[str]) -> dict[str, dict[str, Any]]:
    """name → lēcu dati izsekotajiem (tikai precīza pilnā vārda sakritība)."""
    q = ",".join("?" * len(names))
    # Tas pats filtrs kā _fetch_politicians — profila lapa eksistē tikai šiem.
    rows = db.execute(
        f"""SELECT id, name FROM tracked_politicians
            WHERE name IN ({q})
              AND relationship_type NOT IN ('inactive', 'commentator')""",
        names,
    ).fetchall()
    cutoff = trailing_days_cutoff(POSITIONS_WINDOW_DAYS)
    people: dict[str, dict[str, Any]] = {}
    for r in rows:
        pid = r["id"]
        # Pozīcijas 90 dienās: COALESCE(stated_at, created_at) — tā pati datuma
        # izvēle kā profila pozīciju sarakstam (politicians.py). Abas kolonnas
        # glabā LV laiku, tāpēc 'localtime' NEDRĪKST likt.
        pos90 = db.execute(
            """SELECT COUNT(*) FROM claims
               WHERE opponent_id = ? AND claim_type = 'position'
                 AND substr(COALESCE(stated_at, created_at), 1, 10) >= ?""",
            (pid, cutoff),
        ).fetchone()[0]
        # Pretrunas: tas pats predikāts kā profila «Pretrunas» cilnei
        # (COALESCE(confirmed,1)=1), lai kartītes skaitlis sakrīt ar saiti.
        # 2026-10-08 NULL nav nevienā rindā — tātad ekvivalents confirmed=1.
        ctr = db.execute(
            """SELECT COUNT(*) FROM contradictions
               WHERE opponent_id = ? AND COALESCE(confirmed, 1) = 1""",
            (pid,),
        ).fetchone()[0]
        # Convocation follows the Titania URL, not the vote date.
        voted = db.execute(
            f"""SELECT 1 FROM saeima_individual_votes siv
               JOIN saeima_votes sv ON sv.id = siv.vote_id
               WHERE siv.politician_id = ? AND sv.url LIKE ?
                 AND {not_attendance_sql("siv.vote")} LIMIT 1""",
            # Lēca = IEPRIEKŠĒJĀ Saeima (pieredze); pašreizējā balso gandrīz visi.
            (pid, base_url(SAEIMA_CONVOCATION - 1) + "%"),
        ).fetchone() is not None
        latest = db.execute(
            """SELECT stance, topic, source_url, COALESCE(stated_at, created_at) AS d
               FROM claims
               WHERE opponent_id = ? AND claim_type = 'position'
               ORDER BY COALESCE(stated_at, created_at) DESC, id DESC LIMIT 1""",
            (pid,),
        ).fetchone()
        people[r["name"]] = {
            "pid": pid,
            "pos90": pos90,
            "ctr": ctr,
            "voted14": voted,
            "latest": (
                {
                    "stance": latest["stance"],
                    "topic": latest["topic"],
                    "source_url": latest["source_url"],
                    "date": lv_date(latest["d"]),
                }
                if latest
                else None
            ),
        }
    return people


def _current_government(db: sqlite3.Connection) -> dict[str, Any] | None:
    """Jaunākais uzticības balsojums no ``coalition_periods`` — ja tas ir ŠĪ sasaukuma.

    Nav tabulas/rindas, nav balsojuma vai tas ir iepriekšējā Saeimā (jaunā valdība
    vēl nav apstiprināta) → None, un abas valdības lēcas lapā neparādās.
    """
    try:
        row = db.execute(
            """SELECT source_vote_id FROM coalition_periods
               ORDER BY valid_from_date DESC, valid_from_time DESC LIMIT 1"""
        ).fetchone()
    except sqlite3.OperationalError:
        return None
    if not row or row[0] is None:
        return None
    vote = db.execute(
        "SELECT id, motif, vote_date, url FROM saeima_votes WHERE id = ?", (row[0],)
    ).fetchone()
    # Convocation follows the Titania URL, not the vote date (kā lēcai «Balsoja 14.»).
    if not vote or not (vote["url"] or "").startswith(base_url(SAEIMA_CONVOCATION)):
        return None
    ballots: dict[int, str] = {}
    rows_total = 0
    for r in db.execute(
        "SELECT politician_id, vote FROM saeima_individual_votes WHERE vote_id = ?",
        (vote["id"],),
    ):
        rows_total += 1
        if r["politician_id"] is None:
            continue
        if r["vote"] not in _CAST:
            raise ValueError(f"saeima: uzticības balsojumā {vote['id']} nezināma balss {r['vote']!r}")
        if ballots.get(r["politician_id"], r["vote"]) != r["vote"]:
            raise ValueError(f"saeima: politiķim {r['politician_id']} balsojumā {vote['id']} divas atšķirīgas balsis")
        ballots[r["politician_id"]] = r["vote"]
    return {
        "vote_id": vote["id"],
        "motif": vote["motif"] or "",
        "date": lv_date(vote["vote_date"]),
        "date_short": _short_date(str(vote["vote_date"])[:10]),
        "url": vote["url"],
        "ballots": ballots,
        "rows_total": rows_total,
    }


def _cabinet_rows(db: sqlite3.Connection) -> list[dict[str, Any]]:
    """Valdības bloks: viena rinda katram amatam ar ministru, saite uz tā rindu valdiba.html.

    Tie paši dati, ko valdiba.html (``fetch_cabinet``), lai abas lapas nekad nerunā
    pretī; ministrija bez ministra šeit izlaista (to paskaidro valdiba.html).
    Lapa vēl nepublicēta → tukšs saraksts, bloka nav (nekādu saišu uz 404).
    """
    if not VALDIBA_PUBLISHED:
        return []
    cabinet, others = fetch_cabinet(db)
    return [
        {"post": row["post"], "anchor": row["anchor"], "name": m["name"], "party_short": m["party_short"]}
        for row in cabinet + others
        for m in row["ministers"]
    ]


def _join_lv(items: list[str]) -> str:
    """['AS', 'NA', 'X'] → 'AS, NA un X'."""
    return " un ".join([", ".join(items[:-1]), items[-1]]) if len(items) > 1 else "".join(items)


def _build_context(
    db: sqlite3.Connection,
    elected_path: Path,
    results_path: Path,
    amati_path: Path | None = None,
) -> dict[str, Any]:
    elected, results = _load_composition(elected_path, results_path)
    offices = _load_offices(amati_path or AMATI_PATH, elected)
    # Sēdvietas = SĒDOŠIE (ievēlētie ± mandāti), ne CVK saraksts.
    sitting = offices["sitting"]
    parties = {r["id"]: dict(r) for r in db.execute("SELECT id, name, short_name, color FROM parties")}
    by_nr = {x["list_nr"]: x for x in results["lists"]}

    seat_counts: dict[int, int] = {}
    for e in sitting:
        seat_counts[e["list_nr"]] = seat_counts.get(e["list_nr"], 0) + 1
    # Vietu skaits no SASTĀVA (ne rezultātu faila — tie var atšķirties, kamēr
    # viens ir provizorisks); vienādam skaitam — pēc balsīm.
    order = sorted(seat_counts, key=lambda nr: (-seat_counts[nr], -by_nr[nr]["votes"]))

    people = _fetch_people(db, [e["name"] for e in sitting])
    photo_dir = ASSETS_DIR / "photos"
    gov = _current_government(db)
    coalition_map = get_coalition_map(db)

    lists: list[dict[str, Any]] = []
    for nr in order:
        x = by_nr[nr]
        party = parties.get(x.get("party_id"))
        name = party["name"] if party else x["cvk_name"]
        lists.append({
            "gov": _GOV_STATUS.get(coalition_map.get(name, ""), "nav"),
            "nr": nr,
            "name": name,
            "short": (party["short_name"] if party else None) or x["cvk_name"],
            "color": (party.get("color") if party else None) or "var(--text-muted)",
            "seats": seat_counts[nr],
            "seats_text": _seats_text(seat_counts[nr]),
            "members": [],
        })
    list_by_nr = {lst["nr"]: lst for lst in lists}

    # Amati pa vārdiem: teksts čipam un aria-label (Prezidijs pirmais) + gredzens
    # (Prezidijs un frakciju priekšsēdētāji). Frakcijas amatam priekšā saraksta
    # īsais nosaukums; amata teksts verbatim, tikai pirmais burts mazais.
    office_texts: dict[str, list[str]] = {}
    # Rindai īsāks teksts: grupa jau nosauc frakciju, tāpēc bez prefiksa.
    row_texts: dict[str, list[str]] = {}
    ringed: set[str] = set()
    for m in offices["presidium"]["members"]:
        office_texts.setdefault(m["name"], []).append(m["office"])
        row_texts.setdefault(m["name"], []).append(m["office"])
        ringed.add(m["name"])
    for f in offices["factions"]["items"]:
        lst = list_by_nr[f["list_nr"]]
        lst["leadership"] = []
        for ld in f["leaders"]:
            title = ld["title"][0].lower() + ld["title"][1:]
            office_texts.setdefault(ld["name"], []).append(f"{lst['short']} frakcijas {title}")
            row_texts.setdefault(ld["name"], []).append(title)
            lst["leadership"].append({"name": ld["name"], "slug": _slugify(ld["name"]), "title": title})
            if ld["role"] == "chair":
                ringed.add(ld["name"])
                # Aizvērtas grupas galvenei: verbatim amats + vārds (nav jāloka).
                lst["chair_label"] = f"{ld['title']} {ld['name']}"

    for e in sitting:
        p = people.get(e["name"])
        slug = _slugify(e["name"])
        lst = list_by_nr[e["list_nr"]]
        member = {
            "list": lst,
            "name": e["name"],
            "slug": slug,
            # Aizstājējam CVK apgabala nav; rinda pasaka, kāpēc viņš sēž.
            "region": "ministra vietā" if e.get("substitute") else (e.get("region") or ""),
            "substitute": bool(e.get("substitute")),
            "tracked": p is not None,
            "voted14": bool(p and p["voted14"]),
            "pos90": p["pos90"] if p else None,
            "ctr": p["ctr"] if p else None,
            "latest": p["latest"] if p else None,
            "has_photo": p is not None and (photo_dir / f"{slug}.jpg").exists(),
            "office": " · ".join(office_texts.get(e["name"], [])),
            "office_row": " · ".join(row_texts.get(e["name"], [])),
            "ring": e["name"] in ringed,
        }
        member["pos_bucket"] = _pos_bucket(member["pos90"])
        member["ctr_bucket"] = _ctr_bucket(member["ctr"])
        member["pos_text"] = (
            "nav datu" if member["pos90"] is None
            else "nav pozīciju" if member["pos90"] == 0
            else f"{_lv_number(member['pos90'])} {_lv_plural(member['pos90'], 'pozīcija', 'pozīcijas')}"
        )
        member["ctr_text"] = (
            "nav datu" if member["ctr"] is None
            else "nav pretrunu" if member["ctr"] == 0
            else f"{member['ctr']} {_lv_plural(member['ctr'], 'pretruna', 'pretrunas')}"
        )
        member["v14_text"] = "balsoja" if member["voted14"] else "nebalsoja"
        member["gov"] = lst["gov"]
        member["gov_text"] = _GOV_TEXT[lst["gov"]]
        # Balss TIKAI caur precīzā vārda politician_id; nav rindas → «nav», ne «pret».
        ballot = gov["ballots"].get(p["pid"]) if (gov and p) else None
        member["uzt"] = _CAST[ballot] if ballot else "nav"
        member["uzt_text"] = _CAST_TEXT[member["uzt"]]
        lst["members"].append(member)

    coords = _arc_positions(SEATS_TOTAL)
    seats: list[dict[str, Any]] = []
    for lst in lists:
        for m in lst["members"]:
            x, y = coords[len(seats)]
            seats.append({**m, "x": x, "y": y})

    tracked_n = sum(1 for s in seats if s["tracked"])
    voted_n = sum(1 for s in seats if s["voted14"])
    pos_total = sum(s["pos90"] or 0 for s in seats)
    ctr_people = sum(1 for s in seats if s["ctr"])

    def _count(key: str, val: str) -> int:
        return sum(1 for s in seats if s[key] == val)

    by_name = {s["name"]: s for s in seats}
    presidium = [{**by_name[m["name"]], "office": m["office"]} for m in offices["presidium"]["members"]]
    leaders = [ld for f in offices["factions"]["items"] for ld in f["leaders"]]
    committees = [
        {
            "name": c["name"],
            "url": c.get("url") or "",
            "anchor": "kom-" + _slugify(c["name"]),
            "n": len(c["members"]),
            "members": [
                {**by_name[m["name"]], "title": m["title"], "role": _COMMITTEE_ROLE[m["title"]]}
                for m in c["members"]
            ],
        }
        for c in offices["committees"]["items"]
    ]
    for c in committees:
        c["chair"] = next(m for m in c["members"] if m["role"] == "chair")

    gov_ctx = None
    if gov:
        gov_ctx = {
            "date": gov["date"],
            "date_short": gov["date_short"],
            "url": gov["url"],
            "motif": gov["motif"],
            "coalition_text": _join_lv([lst["short"] for lst in lists if lst["gov"] == "koalicija"]),
            "counts": {b: _count("gov", b) for b in ("koalicija", "opozicija", "nav")},
            "uzt_counts": {b: _count("uzt", b) for b in ("par", "pret", "atturas", "nebalsoja", "nav")},
        }
        gov_ctx["known_n"] = len(seats) - gov_ctx["counts"]["nav"]
        gov_ctx["rows_n"] = len(seats) - gov_ctx["uzt_counts"]["nav"]
        # Silent success: balsojuma rindas, kas netika nevienai sēdvietai (NULL
        # politician_id vai politiķis nav starp 100), — skaitā render izdrukā.
        gov_ctx["unlinked_n"] = gov["rows_total"] - gov_ctx["rows_n"]

    updated = str(results.get("cvk_updated_at") or "")
    return {
        "gov": gov_ctx,
        "seats": seats,
        "lists": lists,
        "dot_r": round(_DOT_R * _SCALE, 2),
        "hit_r": round(_HIT_R * _SCALE, 2),
        "provisional": bool(results.get("provisional", True)),
        "updated_short": f"{updated[8:10]}.{updated[5:7]}." if len(updated) >= 10 else "",
        "source_url": results.get("source_url") or "",
        "total": len(seats),
        "tracked_n": tracked_n,
        "untracked_n": len(seats) - tracked_n,
        "voted_n": voted_n,
        "vote_convocation": SAEIMA_CONVOCATION - 1,
        "pos_total": pos_total,
        "pos_total_text": _lv_number(pos_total),
        "ctr_people": ctr_people,
        "window_days": POSITIONS_WINDOW_DAYS,
        "pos_counts": {b: _count("pos_bucket", b) for b in ("0", "1", "5", "20", "nav")},
        "ctr_counts": {b: _count("ctr_bucket", b) for b in ("0", "1", "2", "nav")},
        "ring_r": round(_RING_R * _SCALE, 2),
        "presidium": presidium,
        "presidium_source_url": offices["presidium"].get("source_url") or "",
        "factions_source_url": offices["factions"].get("source_url") or "",
        "offices_checked": _short_date(offices.get("checked")),
        "committees": committees,
        "committees_source_url": offices["committees"].get("source_url") or "",
        "committees_checked": _short_date(offices["committees"].get("checked")),
        "mandates_n": len((offices.get("mandates") or {}).get("substitutes") or []),
        "cabinet": _cabinet_rows(db),
        "faction_chairs_n": sum(1 for ld in leaders if ld["role"] == "chair"),
        "faction_deputies_n": sum(1 for ld in leaders if ld["role"] == "deputy"),
    }


def render_saeima(
    env: Environment,
    db: sqlite3.Connection,
    atmina_dir: Path,
    elected_path: Path | None = None,
    results_path: Path | None = None,
    amati_path: Path | None = None,
) -> dict[str, int]:
    """saeima.html. Atgriež skaitītājus; nepilns sastāvs vai nesaskanīgi amati → ValueError."""
    ctx = _build_context(
        db, elected_path or ELECTED_PATH, results_path or RESULTS_PATH, amati_path or AMATI_PATH
    )
    _render_page(env, "saeima.html.j2", atmina_dir / "saeima.html", ctx)
    summary = {
        "sēdvietas": ctx["total"],
        "izsekoti": ctx["tracked_n"],
        "bez_profila": ctx["untracked_n"],
        "prezidijs": len(ctx["presidium"]),
        "frakciju_priekšsēdētāji": ctx["faction_chairs_n"],
        "vietnieki": ctx["faction_deputies_n"],
    }
    if ctx["gov"]:
        g = ctx["gov"]
        summary.update({
            "koalīcija": g["counts"]["koalicija"],
            "opozīcija": g["counts"]["opozicija"],
            "uzticība_rindas": g["rows_n"],
            "uzticība_nesasaistītas": g["unlinked_n"],
        })
    else:
        summary["valdības_lēcas"] = 0
    print("  saeima: " + " ".join(f"{k}={v}" for k, v in summary.items()))
    return summary
