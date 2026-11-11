"""Render saeima.html — 15. Saeimas pusloks (sēdvietu karte ar četrām lēcām).

Spec: docs/superpowers/specs/2026-10-08-saeimas-pusloks-design.md.

Sastāvs = ievēlēto saraksta fails (CVK oficiālais, apstiprināts 2026-10-16); saraksta
nosaukums un krāsa = CVK rezultātu fails + ``parties``. Sasaiste ar profilu —
TIKAI precīzs pilnais ``tracked_politicians.name`` (T1: nekādu apakšvirkņu) un
tikai tiem, kam profila lapa tiešām tiek renderēta (tas pats WHERE kā
``_fetch_politicians``), lai sēdvieta nekad nevestu uz 404.

Visas lēcu vērtības aprēķina šeit; lapa bez JS rāda «Saraksta» lēcu un strādā.
``assets/slv1.js`` tikai pārslēdz ``data-lens`` un atver kartīti.

Amati (Prezidijs, frakciju vadība, komisiju statuss) — no kurētā
``data/saeima15_amati.yaml`` (spec: 2026-11-11-saeimas-lapa-amati-design.md),
NE no ``tracked_politicians.role`` (brīvs teksts, T6). Neatbilstība → KRĪT.
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
from src.render._common.cvk import read_elected, read_election_results
from src.saeima.convocation import SAEIMA_CONVOCATION, base_url
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

SEATS_TOTAL = 100
POSITIONS_WINDOW_DAYS = 90

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


def _load_offices(path: Path, elected: list[dict[str, Any]]) -> dict[str, Any]:
    """Amatu YAML → pārbaudīts dict. Jebkura neatbilstība sastāvam → ValueError."""
    doc = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    list_of = {e["name"]: e["list_nr"] for e in elected}

    def _fail(msg: str) -> NoReturn:
        raise ValueError(f"saeima: {path.name}: {msg}")

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

    committees = doc.get("committees") or {}
    # Komisiju sastāva/vadības attēlojums vēl nav uzbūvēts — cits statuss = jāpapildina kods.
    if committees.get("status") != "not_elected":
        _fail(f"komisiju statuss {committees.get('status')!r} nav atbalstīts")
    if not committees.get("names"):
        _fail("nav komisiju nosaukumu")
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


def _build_context(
    db: sqlite3.Connection,
    elected_path: Path,
    results_path: Path,
    amati_path: Path | None = None,
) -> dict[str, Any]:
    elected, results = _load_composition(elected_path, results_path)
    offices = _load_offices(amati_path or AMATI_PATH, elected)
    parties = {r["id"]: dict(r) for r in db.execute("SELECT id, name, short_name, color FROM parties")}
    by_nr = {x["list_nr"]: x for x in results["lists"]}

    seat_counts: dict[int, int] = {}
    for e in elected:
        seat_counts[e["list_nr"]] = seat_counts.get(e["list_nr"], 0) + 1
    # Vietu skaits no SASTĀVA (ne rezultātu faila — tie var atšķirties, kamēr
    # viens ir provizorisks); vienādam skaitam — pēc balsīm.
    order = sorted(seat_counts, key=lambda nr: (-seat_counts[nr], -by_nr[nr]["votes"]))

    people = _fetch_people(db, [e["name"] for e in elected])
    photo_dir = ASSETS_DIR / "photos"

    lists: list[dict[str, Any]] = []
    for nr in order:
        x = by_nr[nr]
        party = parties.get(x.get("party_id"))
        lists.append({
            "nr": nr,
            "name": party["name"] if party else x["cvk_name"],
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

    for e in elected:
        p = people.get(e["name"])
        slug = _slugify(e["name"])
        lst = list_by_nr[e["list_nr"]]
        member = {
            "list": lst,
            "name": e["name"],
            "slug": slug,
            "region": e.get("region") or "",
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
    committees = offices["committees"]

    updated = str(results.get("cvk_updated_at") or "")
    return {
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
        "committees": {"n": len(committees["names"]), "source_url": committees.get("source_url") or ""},
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
    print("  saeima: " + " ".join(f"{k}={v}" for k, v in summary.items()))
    return summary
