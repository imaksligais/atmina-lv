"""«Kur ceļi krustojas» — kopīgās vietas (Saites v2, 2. posms).

Vieta = Saeimas komisija/delegācija (14. Saeima, titania) vai organizācija
no amatpersonu deklarācijām (VID), kurā vismaz DIVI izsekoti politiķi ir
bijuši vienlaikus: komisijā periodi pārklājas ≥ ``MIN_OVERLAP_DAYS``,
organizācijā abiem ir kopīgs deklarācijas gads. Tikai fakts ar avotu —
nekad «strādāja kopā» (plāns docs/plans/2026-11-22-saites-v2-posms2-plans.md).

``build_places(db)`` aprēķina visu vienreiz renderā; to lieto gan
``vietas/<slug>.html`` + Saites lapas saraksts, gan profila «Saites» cilne,
tāpēc profils nevar saitēt uz vietu, kuras lapa nav uzbūvēta.
"""

from __future__ import annotations

import hashlib
import logging
import sqlite3
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Any, Optional

from src.lv_text import slugify
from src.profile_kind import CURRENT_TERM_START
from src.saeima.convocation import SAEIMA_CONVOCATION
from src.render.vad import declaration_label

logger = logging.getLogger(__name__)

MIN_OVERLAP_DAYS = 30
SLUG_MAX = 60

# titania `level` → (vietas veids, etiķete lasītājam). Frakcijas (2),
# «Deputāts» (10) un Prezidijs (4) nav vietas, kur «ceļi krustojas».
COMMISSION_LEVELS: dict[str, tuple[str, str]] = {
    "3": ("komisija", "Saeimas komisija"),
    "5": ("komisija", "Saeimas apakškomisija"),
    "11": ("komisija", "Parlamentārās izmeklēšanas komisija"),
    "6": ("delegacija", "Saeimas delegācija"),
}
CONVOCATION = 14

# Organizācijas rāda TIKAI no šī pārbaudītā saraksta (reģ. nr. → nosaukums
# pārbaudei). Jauna organizācija pēc VID ielādes netiek publicēta klusām:
# renders to izlaiž un saskaita (`unreviewed_orgs`). Partijas, partiju
# apvienības un pašvaldību apvienības šeit apzināti nav. Pārbaudīts
# 2026-11-22 pret produkcijas DB.
#
# Apzināti NAV (2026-11-22 kandidāti ar kopīgu gadu): partijas un to
# apvienības (Vienotība, NA, ZZS, LZP, LZS, Progresīvie, LPV, Stabilitātei!,
# Saskaņa, JL, TP, LPP/LC, Reformu partija, KPV LV, Par!, Attīstībai/Par!,
# GKR, GKML, Brīvie demokrāti, Suverēnā vara, Reģionu alianse, LRA,
# Liepājas partija, Latvijai un Ventspilij, Kopā Latvijai, Katram un katrai,
# Jaunlatvieši, Latvijas Krievu savienība, Latvijas Restarts, SCP, PCTVL,
# Pilsoniskā savienība, TSP, LSDSP, LPP, TB/LNNK, Visu Latvijai!, Saskaņas
# Centrs, Apvienotais saraksts), partijām piesaistītas politiskas biedrības
# (Nacionālais bloks, «Stabilitātei- Jā!»), pašvaldību apvienības (LPS,
# Lielo pilsētu asociācija, RACA, Rīgas Metropole) un ministrija (KEM).
ORG_ALLOWLIST: dict[str, str] = {
    "40003101808": "Baltijas Starptautiskā akadēmija",
    "40003246194": "Ziemeļkurzemes reģionālā slimnīca",
    "40008037590": "Draudzības un sadarbības fonds",
    "40003113794": "Latvijas Vēstnesis",
    "40008028757": "Eiropas Kustība Latvijā",
    "40003457109": "Paula Stradiņa klīniskā universitātes slimnīca",
    "42403013918": "ALAAS",
    "40003135880": "Biznesa augstskola Turība",
    "40003080436": "Fonds atvērtai sabiedrībai DOTS",
    "40003016840": "CATA",
    "40008106426": "Darīsim paši!",
    "40003619950": "Rīgas satiksme",
    "40003457128": "Bērnu klīniskā universitātes slimnīca",
    "40003215461": "Rēzeknes namsaimnieks",
    "40003090010": "RISEBA",
    "42403015020": "Ludzas apsaimniekotājs",
    "40103208907": "Latvijas Nacionālā opera un balets",
    "40003275348": "Rehabilitācijas centrs «Rāzna»",
    "50008022421": "Latvijas Olimpiskā komiteja",
    "58503007191": "LATRAPS",
    "40008005063": "Latgaliešu kultūras biedrība",
    "40003949089": "WAVE MEDIA",
    "40003044261": "Žurnāls Santa",
    "40003837074": "RSU Ambulance",
    "50008021661": "Baltā māja",
    "40008004918": "Latvijas Darba devēju konfederācija",
    "40008188047": "Latvijas Komandu sporta spēļu asociācija",
    "40008279219": "Zero Waste Latvija",
    "40008297021": "Latvijas Futbola arodbiedrība",
    "41703007095": "Jelgavas poliklīnika",
    "40008022932": "Latvijas Sporta federāciju padome",
    "40203364600": "ZAB ABSOLVO",
    "40008329825": "Sievietes drošībai",
    "50008319551": "Vēstures entuziastu klubs",
}

# Pārbaudīti un apzināti NErādīti (sk. komentāru virs ORG_ALLOWLIST).
# Brīdinājums renderā skaita tikai organizācijas, kas nav NEVIENĀ sarakstā.
ORG_EXCLUDED: frozenset[str] = frozenset({
    # Otrā lasītāja pārbaude 2026-11-22: pašvaldību aģentūra (biedri — trīs
    # pašvaldības) un politiskas biedrības (kandidātu izvirzīšana, sadarbība
    # ar partiju; «Tīģeris un pūķis» deklarācijās arī «SUVERĒNĀ VARA»,
    # «TAUTAS VARA»).
    "40008134754",  # Zemgales reģionālā enerģētikas aģentūra
    "40008159512",  # Meierovica biedrība par progresīvām pārmaiņām
    "40008120241",  # Brīvības un solidaritātes fonds
    "50008299471",  # Biedrība «Tīģeris un pūķis» / «SUVERĒNĀ VARA»
    "40008020804",  # Latvijas Pašvaldību savienība
    "40008044840",  # "LATVIJAS ZEMNIEKU SAVIENĪBA"
    "40008044893",  # Latvijas Zaļā partija
    "40008044982",  # Tautas saskaņas partija
    "40008045009",  # "Latvijai un Ventspilij"
    "40008045174",  # Apvienība "Tēvzemei un Brīvībai"/LNNK
    "40008045263",  # Tautas partija
    "40008045329",  # Politisko organizāciju apvienība "Par cilvēka tiesībām vieno
    "40008046127",  # Latvijas Sociāldemokrātiskā strādnieku partija
    "40008062649",  # "Latvijas Lielo pilsētu asociācija"
    "40008065236",  # Jaunais laiks
    "40008068618",  # Latvijas Pirmā partija
    "40008068957",  # Zaļo un Zemnieku savienība
    "40008082611",  # Partija "Visu Latvijai!"
    "40008087553",  # Politiskā partija "Reģionu alianse"
    "40008087572",  # "LIEPĀJAS PARTIJA"
    "40008087873",  # "SUVERĒNĀ VARA"
    "40008093085",  # Politisko partiju apvienība "Saskaņas Centrs"
    "40008120059",  # "Latvijas Krievu savienība"
    "40008120631",  # Partija "LPP/LC"
    "40008127894",  # "Pilsoniskā savienība"
    "40008132630",  # SABIEDRĪBA CITAI POLITIKAI
    "40008153670",  # "Saskaņa" sociāldemokrātiskā partija
    "40008158358",  # Jaunā VIENOTĪBA
    "40008162620",  # Nacionālais bloks
    "40008181602",  # "Reformu partija"
    "40008185924",  # Partija "VIENOTĪBA"
    "40008191935",  # "BRĪVIE DEMOKRĀTI"
    "40008193917",  # Partija "Gods kalpot Rīgai"
    "40008220045",  # Nacionālā apvienība "Visu Latvijai!"-"Tēvzemei un Brīvībai/L
    "40008237304",  # "Reģionālo attīstības centru apvienība"
    "40008244240",  # Rīgas un Pierīgas pašvaldību apvienība "RĪGAS METROPOLE"
    "40008253188",  # Politiskā partija "KPV LV"
    "40008262104",  # "PROGRESĪVIE"
    "40008268164",  # "Kustība "Par!""
    "40008275931",  # Attīstībai/Par!
    "40008302093",  # "Stabilitātei- Jā!"
    "40008303741",  # Politiskā partija "Latvijas Reģionu Apvienība"
    "40008304516",  # Politiskā partija "Stabilitātei!"
    "40008305013",  # Politiskā partija "KATRAM UN KATRAI"
    "40008310156",  # LATVIJA PIRMAJĀ VIETĀ
    "40008317099",  # "Latvijas Restarts"
    "40008322687",  # APVIENĪBA JAUNLATVIEŠI
    "40008326301",  # Politiskā partija "KOPĀ LATVIJAI"
    "40900039891",  # Klimata un enerģētikas ministrija
    "50008221771",  # "APVIENOTAIS SARAKSTS - Latvijas Zaļā partija, Latvijas Reģi
    "50008251121",  # "Gods kalpot mūsu Latvijai"
})

KIND_ORDER = ("komisija", "delegacija", "organizacija")


@dataclass
class Member:
    pid: int
    name: str
    slug: str
    party: str
    role: str                      # cilvēkam lasāms amats(-i)
    when: str                      # cilvēkam lasāms laiks
    source_url: str
    intervals: list[tuple[date, date]] = field(default_factory=list)
    years: set[int] = field(default_factory=set)


@dataclass
class Place:
    slug: str
    kind: str                      # komisija | delegacija | organizacija
    kind_label: str
    name: str                      # lasītājam: komisijai pilns, organizācijai īsais (ORG_ALLOWLIST)
    reg_nr: str
    members: list[Member]
    legal_name: str = ""           # organizācijai: nosaukums deklarācijā (biežākais)
    together: dict[int, list[tuple[Member, str]]] = field(default_factory=dict)


# ── tīrā loģika ──────────────────────────────────────────────────────


def merge_intervals(spans: list[tuple[date, date]], gap_days: int = 1) -> list[tuple[date, date]]:
    """Apvieno periodus, kas pārklājas vai saskaras (titania amata maiņa
    ir jauna rinda: «Deputāte 23.11–23.11» + «Priekšsēdētāja 23.11–…»)."""
    out: list[tuple[date, date]] = []
    for a, b in sorted(spans):
        if out and (a - out[-1][1]).days <= gap_days:
            out[-1] = (out[-1][0], max(out[-1][1], b))
        else:
            out.append((a, b))
    return out


def overlap_days(x: list[tuple[date, date]], y: list[tuple[date, date]]) -> int:
    """Kopīgo dienu skaits (ieskaitot abas robežas) starp diviem periodu sarakstiem."""
    total = 0
    for a1, b1 in x:
        for a2, b2 in y:
            lo, hi = max(a1, a2), min(b1, b2)
            if lo <= hi:
                total += (hi - lo).days + 1
    return total


def year_ranges(years: set[int]) -> str:
    """{2019, 2021, 2022, 2023} → «2019, 2021–2023»."""
    ys = sorted(years)
    parts: list[str] = []
    i = 0
    while i < len(ys):
        j = i
        while j + 1 < len(ys) and ys[j + 1] == ys[j] + 1:
            j += 1
        parts.append(str(ys[i]) if i == j else f"{ys[i]}–{ys[j]}")
        i = j + 1
    return ", ".join(parts)


# Latviešu alfabēta secība: «ā» uzreiz pēc «a» (Python «ā» liek aiz «z»).
_LV_ALPHA = "aābcčdeēfgģhiījkķlļmnņopqrsštuūvwxyzž"


def lv_sort_key(text: str) -> tuple[int, ...]:
    """Kārtošanas atslēga pēc latviešu alfabēta; cipari un zīmes pirms burtiem."""
    out = []
    for ch in text.casefold():
        i = _LV_ALPHA.find(ch)
        out.append(1000 + i if i >= 0 else ord(ch) if ch.isalnum() or ch == " " else 0)
    return tuple(out)


def place_slug(name: str, suffix: str) -> str:
    base = slugify(name)[:SLUG_MAX].rstrip("-") or "vieta"
    return f"{base}-{suffix}"


def _commission_end(d_to: Optional[str], loaded: str) -> date:
    """Amata beigas. titania iepriekšējā sasaukuma amatus bieži neaizver
    (2026-11-04: 589 rindas ar NULL): tie beidzās līdz ar sasaukumu, t.i.
    jaunās Saeimas pirmajā sēdē — tas pats noteikums kā profila Saeimā cilnē.
    Pašreizējam sasaukumam NULL = ielādes brīdī vēl amatā."""
    if d_to:
        return date.fromisoformat(d_to)
    if CONVOCATION < SAEIMA_CONVOCATION:
        return date.fromisoformat(CURRENT_TERM_START)
    return date.fromisoformat(loaded)


def _lv_d(d: date) -> str:
    return d.strftime("%d.%m.%Y")


def _member_role(positions: list[str]) -> str:
    """titania amati hronoloģiski → «priekšsēdētāja, locekle». Vispārīgo
    «Deputāts/Deputāte» komisijas kontekstā rāda kā «loceklis/locekle»."""
    seen: list[str] = []
    for p in positions:
        p = " ".join((p or "").split())
        if p == "Deputāts":
            p = "loceklis"
        elif p == "Deputāte":
            p = "locekle"
        p = p[:1].lower() + p[1:]
        if p and p not in seen:
            seen.append(p)
    # Vadošos amatus pirms vispārīgā locekļa.
    seen.sort(key=lambda r: r in ("loceklis", "locekle"))
    out = ", ".join(seen)
    return out[:1].upper() + out[1:]


def _shown_positions(rs: list[tuple]) -> list[str]:
    """Amati, ko rādīt: «Deputāts/Deputāte» rindu izmet, ja to pilnībā ietver
    vadošā amata rinda (titania amata maiņas artefakts) — tas pats noteikums
    kā profila Saeimā cilnē (``politicians._group_deputy_positions``).
    ``rs`` = (position, date_from, date_to, …); date_to NULL = turpinās."""
    from src.render.politicians import _PLAIN_MEMBER, _interval_contains

    def row(r: tuple) -> dict[str, Any]:
        return {"position": (r[0] or "").strip(), "date_from": r[1], "date_to": r[2]}
    items = [row(r) for r in rs]
    leads = [r for r in items if r["position"] not in _PLAIN_MEMBER]
    return [
        r["position"] for r in items
        if r["position"] not in _PLAIN_MEMBER
        or not any(_interval_contains(lead, r) for lead in leads)
    ]


def _pairs(members: list[Member], kind: str) -> dict[int, list[tuple[Member, str]]]:
    """pid → [(otrs, kopīgā laika teksts)] tikai pāriem, kas tiešām bija vienlaikus."""
    out: dict[int, list[tuple[Member, str]]] = {}
    for i, a in enumerate(members):
        for b in members[i + 1:]:
            if kind == "organizacija":
                shared = a.years & b.years
                if not shared:
                    continue
                label = f"abi {year_ranges(shared)}. g. deklarācijās"
            else:
                if overlap_days(a.intervals, b.intervals) < MIN_OVERLAP_DAYS:
                    continue
                label = ""
            out.setdefault(a.pid, []).append((b, label))
            out.setdefault(b.pid, []).append((a, label))
    return out


# ── dati ─────────────────────────────────────────────────────────────


def _politicians(db: sqlite3.Connection) -> dict[int, dict[str, Any]]:
    rows = db.execute(
        "SELECT id, name, COALESCE(party, '') FROM tracked_politicians "
        "WHERE COALESCE(relationship_type, '') != 'inactive'"
    ).fetchall()
    return {r[0]: {"name": r[1], "slug": slugify(r[1]), "party": r[2]} for r in rows}


def _commission_places(db: sqlite3.Connection, pols: dict[int, dict[str, Any]]) -> list[Place]:
    levels = tuple(COMMISSION_LEVELS)
    rows = db.execute(
        f"SELECT politician_id, level, body, position, date_from, date_to, source_url, "
        f"       DATE(created_at, 'localtime') "
        f"FROM saeima_deputy_positions WHERE convocation = ? "
        f"AND level IN ({','.join('?' * len(levels))}) AND politician_id IS NOT NULL "
        f"ORDER BY date_from, id",
        (CONVOCATION, *levels),
    ).fetchall()
    grouped: dict[tuple[str, str], dict[int, list[tuple]]] = {}
    for pid, level, body, pos, d_from, d_to, url, loaded in rows:
        if pid not in pols or not d_from:
            continue
        grouped.setdefault((body, level), {}).setdefault(pid, []).append(
            (pos, d_from, d_to, url, loaded)
        )
    places: list[Place] = []
    for (body, level), per_pid in grouped.items():
        kind, kind_label = COMMISSION_LEVELS[level]
        members: list[Member] = []
        for pid, rs in per_pid.items():
            spans = []
            for _pos, d_from, d_to, _url, loaded in rs:
                start = date.fromisoformat(d_from)
                spans.append((start, _commission_end(d_to, loaded)))
            merged = merge_intervals(spans)
            when = "; ".join(f"{_lv_d(a)}–{_lv_d(b)}" for a, b in merged)
            p = pols[pid]
            members.append(Member(
                pid=pid, name=p["name"], slug=p["slug"], party=p["party"],
                role=_member_role(_shown_positions(rs)), when=when,
                source_url=rs[-1][3] or "", intervals=merged,
            ))
        if len({m.pid for m in members}) < 2:
            continue
        together = _pairs(members, kind)
        if not together:
            continue
        suffix = hashlib.sha1(f"{level}|{body}".encode()).hexdigest()[:6]
        members.sort(key=lambda m: m.intervals[0][0])
        places.append(Place(
            slug=place_slug(body, suffix), kind=kind, kind_label=kind_label,
            name=body, reg_nr="", members=members, together=together,
        ))
    return places


def _org_candidates(db: sqlite3.Connection, pols: dict[int, dict[str, Any]]) -> dict[str, dict[str, Any]]:
    rows = db.execute(
        "SELECT p.entity_reg_number, p.entity_name, p.position_title, d.opponent_id, "
        "       d.declaration_type, d.submitted_at, d.declaration_year, d.source_url "
        "FROM vad_positions p JOIN vad_declarations d ON d.id = p.declaration_id "
        "WHERE p.is_individual = 0 AND p.entity_reg_number IS NOT NULL "
        "AND p.entity_reg_number != '' AND p.entity_reg_number NOT LIKE '9%' "
        "ORDER BY d.submitted_at, d.id, p.id"
    ).fetchall()
    orgs: dict[str, dict[str, Any]] = {}
    for reg, ename, title, pid, dtype, submitted, dyear, url in rows:
        if pid not in pols:
            continue
        year: Optional[int] = dyear
        if year is None:
            label_year = declaration_label(dtype, submitted)[1][:4]
            year = int(label_year) if label_year.isdigit() else None
        if year is None:
            continue
        o = orgs.setdefault(reg, {"names": {}, "members": {}})
        o["names"][ename] = o["names"].get(ename, 0) + 1
        m = o["members"].setdefault(
            pid, {"titles": [], "decl": None, "years": set(), "url": ""})
        # Amati no JAUNĀKĀS deklarācijas (visi tās amati šajā organizācijā),
        # burtiski — senākās deklarācijās tas pats amats rakstīts citādi.
        if m["decl"] != (submitted, url):
            m["decl"], m["titles"] = (submitted, url), []
        t = " ".join((title or "").split())
        if t and t.casefold() not in {x.casefold() for x in m["titles"]}:
            m["titles"].append(t)
        m["years"].add(year)
        m["url"] = url or m["url"]          # jaunākā deklarācija (ORDER BY submitted_at)
    return orgs


def _org_places(
    db: sqlite3.Connection, pols: dict[int, dict[str, Any]], unreviewed: list[tuple[str, str]],
) -> list[Place]:
    places: list[Place] = []
    for reg, o in _org_candidates(db, pols).items():
        name = max(o["names"].items(), key=lambda kv: (kv[1], kv[0]))[0]
        members = []
        for pid, m in o["members"].items():
            p = pols[pid]
            members.append(Member(
                pid=pid, name=p["name"], slug=p["slug"], party=p["party"],
                role=", ".join(m["titles"]), when=year_ranges(m["years"]),
                source_url=m["url"], years=m["years"],
            ))
        if len(members) < 2:
            continue
        together = _pairs(members, "organizacija")
        if not together:
            continue
        if reg not in ORG_ALLOWLIST:
            if reg not in ORG_EXCLUDED:
                unreviewed.append((reg, name))
            continue
        members.sort(key=lambda m: (min(m.years), m.name))
        places.append(Place(
            slug=place_slug(ORG_ALLOWLIST[reg], reg), kind="organizacija",
            kind_label="Organizācija (amatpersonu deklarācijas)",
            name=ORG_ALLOWLIST[reg], legal_name=name, reg_nr=reg,
            members=members, together=together,
        ))
    return places


def build_places(db: sqlite3.Connection) -> dict[str, Any]:
    """Visas vietas + indekss pa politiķiem.

    Atgriež ``{"places": [...], "by_pid": {pid: [(Place, Member, [(otrs, teksts)])]},
    "unreviewed_orgs": [(reg, nosaukums)]}``.
    """
    pols = _politicians(db)
    unreviewed: list[tuple[str, str]] = []
    places: list[Place] = []
    loaded = ""
    # Vecās testu/legacy DB bez titania vai VID tabulām → vienkārši bez šī avota
    # (tāpat kā likumprojektu bloks profilā).
    try:
        places += _commission_places(db, pols)
        loaded = db.execute(
            "SELECT MAX(DATE(created_at, 'localtime')) FROM saeima_deputy_positions"
            " WHERE convocation = ?", (CONVOCATION,),
        ).fetchone()[0] or ""
    except sqlite3.OperationalError as exc:
        logger.info("[vietas] bez komisijām: %s", exc)
    try:
        places += _org_places(db, pols, unreviewed)
    except sqlite3.OperationalError as exc:
        logger.info("[vietas] bez organizācijām: %s", exc)
    places.sort(key=lambda p: (KIND_ORDER.index(p.kind), lv_sort_key(p.name)))
    by_pid: dict[int, list[tuple[Place, Member, list[tuple[Member, str]]]]] = {}
    for pl in places:
        for m in pl.members:
            by_pid.setdefault(m.pid, []).append((pl, m, pl.together.get(m.pid, [])))
    if unreviewed:
        logger.warning(
            "[vietas] %d organizācijas ar kopīgiem politiķiem nav pārbaudītas "
            "(ORG_ALLOWLIST) — izlaistas: %s",
            len(unreviewed), ", ".join(f"{r} {n[:30]}" for r, n in unreviewed[:10]),
        )
    return {"places": places, "by_pid": by_pid, "unreviewed_orgs": unreviewed, "loaded": loaded}


def render_places(
    env: Any, places_data: dict[str, Any], atmina_dir: Path, prune: bool = True,
) -> int:
    """Raksta ``vietas/<slug>.html``.

    ``prune`` dzēš vecās lapas. Orķestris to dara tikai, ja šajā renderā
    pārbūvē ARĪ Saites lapu un profilus: šaurs renders (`--only=saites`)
    citādi dzēstu lapu, uz kuru vēl saitē nepārbūvētie profili."""
    out_dir = atmina_dir / "vietas"
    out_dir.mkdir(parents=True, exist_ok=True)
    if prune:
        for old in out_dir.glob("*.html"):
            old.unlink()
    from src.render._common.assets import _render_page
    for pl in places_data["places"]:
        _render_page(env, "vieta.html.j2", out_dir / f"{pl.slug}.html", {
            "place": pl, "loaded": places_data["loaded"],
            "active_page": "saites", "assets_prefix": "../",
        })
    return len(places_data["places"])
