"""`/audit-integrity` pārbaužu reģistrs — viens read-only skripts visām pārbaudēm.

Līdz 2026-09-30 15 no 20 pārbaudēm dzīvoja tikai kā SQL/Python teksts
`.claude/commands/audit-integrity.md`, un aģents tās katru reizi pārrakstīja no
jauna: vaicājums varēja atšķirties starp skrējieniem, un vārtiem nebija testu,
kas pierāda, ka tie var nokrist (CLAUDE.md «A gate that cannot fail is not
evidence»). Plāns: `docs/plans/2026-09-30-audit-integrity-skripts.md`.
Bāzes līnijas un incidentu vēsture: `.claude/references/audit-integrity/bazes-linijas.md`.

PĀRNESE, NE UZLABOJUMS. Katras pārbaudes semantika ir prompta vaicājums (vai,
kur promptā bija tikai proza, tās burtisks lasījums — pieņemtie lēmumi
atzīmēti pie funkcijas ar «PROZAS LASĪJUMS»). Četri esošie skripti netiek
pārrakstīti — reģistrs tos importē: 9b `audit_minister_vote_coverage`, 13
`audit_vector_staleness`, 15 `src.quoted_speaker.find_inversions` (tas pats,
ko sauc `audit_junction_role_inversion.py`), 18 `audit_topic_canonical`.
12. pārbaude ir tas pats mērījums kā 15. — abas norāda uz vienu funkciju.

PĀRBAUŽU NUMURI NEMAINĀS — uz tiem atsaucas `src/matcher.py`, `src/quality.py`,
`src/saeima/votes.py`, skriptu docstringi, testi un CHANGELOG.

IZEJAS KODS (tas pats kontrakts kā `scripts/audit_*.py`):
  0 tīrs · 1 atradumi · 2 salauzts saucējs (checked=0) vai metode nepārbaudīta.
Izejas kodu nosaka TIKAI vārtu pārbaudes (`gate=True`). Informatīvās (1, 1b,
6, 8, 12, 15) drukā tabulu un saucēju, bet kodu neietekmē — arī pie checked=0.
Vārtu pārbaudei `flagged` ir neapstrādātais skaits (sakrīt ar prompta
vaicājumu); kodu nosaka `new` = flagged mīnus dokumentēti pieņemtie id
(`ACCEPTED_*` konstantes zemāk). Pieņemto sarakstu maina tikai operators.

TIKAI LASĪŠANA: savienojums `file:…?mode=ro`. Divi izņēmumi, abi mantoti no
koda, ko reģistrs importē, un abi izpilda tikai SELECT: 13. pārbaudes skripts
atver savu savienojumu (`audit_vector_staleness._connect`), un 1b matcher
ielādē formas caur `get_db()`. `db.log_action('integrity_audit', …)` ir aģenta
solis promptā, ne šī skripta.

Lietošana (no repo saknes, VIENMĒR .venv interpretators, PYTHONUTF8=1):
  .venv/Scripts/python.exe scripts/audit_integrity.py                  # viss
  .venv/Scripts/python.exe scripts/audit_integrity.py --only 2,7,11
  .venv/Scripts/python.exe scripts/audit_integrity.py --scope orphans --json
"""

from __future__ import annotations

import argparse
import collections
import json
import logging
import re
import sqlite3
import sys
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable

_REPO = Path(__file__).resolve().parent.parent
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

from src.db import (  # noqa: E402
    PRODUCTION_DB_PATH,
    REVIEW_AGE_EXPR,
    _REVIEW_STATUS_EXPR,
    REVIEW_QUEUE_AGE_DAYS,
    lv_cutoff,
    now_lv,
)
from src.lv_text import fold_lower  # noqa: E402

# --- Dokumentēti pieņemtie karogi (maina tikai operators) ------------------

# 2. pārbaude (bāzlīnija 2026-08-25 `111 | 1 | 1`, abi `1` ir dokumentēti
# izņēmumi — BACKLOG § Ne-darīt): id 27 Bordāns — x_handle apzināti NULL,
# `inactive`, profila lapa netiek renderēta; id 62 Svirskis — divi X konti
# apzināti (operatora lēmums 2026-07-16, apstiprināts 2026-09-07).
ACCEPTED_2: frozenset[int] = frozenset({27, 62})
# 3. pārbaude: pretruna #27 atsaukta 2026-09-30 (confirmed=-1), tās vecā
# pozīcija #6991 dzēsta ar operatora lēmumu — `claim_old_id` NULL ir
# dokumentētas atsaukšanas pēda, ne bārenis (commit 65eb6b76).
ACCEPTED_3: frozenset[int] = frozenset({27})
# 9. pārbaude: īstas partijas maiņas, `party` ir pareizs — «leave them alone,
# they will flag again every run» (BACKLOG § Ne-darīt: Ābrama 77, Kiršteins 96,
# Ceļapīters 145). + Drelinga 87, J. Kļaviņa 100, Pleškāne 119: ST → LPV jau
# piemērots (fix_party_role_cvk_review_2026-09-25, pleskane 2026-08-13), balso ar
# faction=NULL — operatora lēmums 2026-09-30.
ACCEPTED_9: frozenset[int] = frozenset({77, 87, 96, 100, 119, 145})
# 17. pārbaude: 11 zināmie/pieņemtie claim id (bāzlīnija 2026-08-05).
ACCEPTED_17: frozenset[int] = frozenset({
    7481, 18095, 18096, 18377, 20450, 20538, 20802,
    548162, 548267, 548268, 555829,
})

# --- Sliekšņi (prompta triāžas noteikumi) -----------------------------------

SHORT_FORM_MAX = 4               # 1. pārbaude: ≤4 zīmju formas (T1)
VETO_JOURNAL_DAYS = 14           # 1b
CONTRADICTION_REVIEW_DAYS = 14   # 4: reviewed=0
SURVIVOR_UNCONFIRMED_DAYS = 30   # 4: confirmed=0 AND reviewed=0
STALE_PARTY_DAYS = 30            # 5
STALE_PARTY_TOPIC = "Koalīcija un partijas"
STALE_PARTY_PATTERNS = ("izstāj", "pamet", "pāriet", "jaunu partiju")
SAME_DAY_DUP_DAYS = 30           # 6
STUB_WORDS = 80                  # 8
STUB_DAYS = 30                   # 8
FACTION_COVERAGE_MIN = 0.20      # 9: <20 % → izvadīt laika līniju
FACTION_WINDOW_DAYS = 7          # 9: triāžas logs (tikai attēlošanai)
INVERSION_DAYS = 90              # 12/15

SCOPES: dict[str, tuple[str, ...]] = {
    "matcher": ("1", "1b", "2", "12", "15"),
    "stale": ("4", "5", "8", "9", "9b", "13", "17"),
    "orphans": ("3", "6", "10", "11", "14", "18"),
    "briefs": ("7", "16"),
}


@dataclass
class Ctx:
    db: sqlite3.Connection
    db_path: str
    output_root: Path = _REPO / "output" / "atmina"
    data_dir: Path = _REPO / "data"
    now_utc: datetime | None = None
    embed_fn: Callable[[str], Any] | None = None
    cache: dict = field(default_factory=dict)

    def utc_now_str(self) -> str:
        now = self.now_utc or datetime.now(timezone.utc)
        return now.strftime("%Y-%m-%d %H:%M:%S")


@dataclass
class CheckResult:
    num: str
    name: str
    checked: int
    flagged: int
    expected: str
    gate: bool = True
    accepted: list[int] = field(default_factory=list)   # karogotās rindas ar pieņemtu id
    rows: list[dict] = field(default_factory=list)
    extra: dict = field(default_factory=dict)
    broken: str = ""                                     # metode nepārbaudīta

    @property
    def new(self) -> int:
        return self.flagged - len(self.accepted)

    def status(self) -> int:
        if not self.gate:
            return 0
        if self.broken or self.checked == 0:
            return 2
        return 1 if self.new > 0 else 0


def connect_ro(db_path: str) -> sqlite3.Connection:
    db = sqlite3.connect(f"file:{Path(db_path).as_posix()}?mode=ro", uri=True)
    db.row_factory = sqlite3.Row
    return db


def _one(db: sqlite3.Connection, sql: str, params: tuple = ()) -> int:
    return db.execute(sql, params).fetchone()[0] or 0


# --- 1. Matcher sadursmju risks (T1) — informatīva --------------------------

def check_1(ctx: Ctx) -> CheckResult:
    """PROZAS LASĪJUMS: «ģenerētās formas» = tieši tās, ko matcher ģenerē
    (`_latvian_surname_inflections(name.split()[-1])`, izņemot institucionālos
    un @-vārdus), plus prompta «katrai uzvārda formai» — katrai glabātajai
    viena vārda formai. Paraugs = pēdējo 14 dienu dokumenti, `_occurrences`
    (vārda robežas semantika kopš B2)."""
    from src.matcher import _latvian_surname_inflections, _occurrences

    pols = ctx.db.execute(
        "SELECT id, name, name_forms, relationship_type FROM tracked_politicians "
        "WHERE relationship_type != 'inactive' ORDER BY id"
    ).fetchall()
    cutoff = lv_cutoff(VETO_JOURNAL_DAYS)
    rows: list[dict] = []
    flagged_pids: set[int] = set()
    for p in pols:
        try:
            stored = json.loads(p["name_forms"]) if p["name_forms"] else []
        except (TypeError, ValueError):
            stored = []
        parts = (p["name"] or "").split()
        institutional = p["relationship_type"] in ("journalist", "organization")
        seeds = {f for f in stored if f and " " not in f and not f.startswith("@")}
        if len(parts) >= 2 and not parts[-1].startswith("@") and not institutional:
            seeds.add(parts[-1])
        generated: set[str] = set()
        if not institutional:
            for s in seeds:
                generated.update(_latvian_surname_inflections(s))
        short = [(f, "glabāta") for f in stored if f and len(f) <= SHORT_FORM_MAX]
        short += [(f, "ģenerēta") for f in sorted(generated - set(stored))
                  if len(f) <= SHORT_FORM_MAX]
        for form, origin in short:
            flagged_pids.add(p["id"])
            docs = ctx.db.execute(
                "SELECT id, content FROM documents WHERE scraped_at >= ? "
                "AND content IS NOT NULL AND instr(content, ?) > 0",
                (cutoff, form),
            ).fetchall()
            hits = [(d["id"], d["content"], _occurrences(d["content"], form)) for d in docs]
            hits = [h for h in hits if h[2]]
            sample = ""
            if hits:
                doc_id, content, idx = hits[0]
                i = idx[0]
                sample = f"doc {doc_id}: {content[max(0, i - 40):i + len(form) + 40]!r}"
            rows.append({
                "id": p["id"], "name": p["name"], "form": form, "origin": origin,
                "klase": "vārda robeža (namesake)" if " " not in form else "frāze (substring)",
                "docs_14d": len(hits), "piemērs": sample,
            })
    return CheckResult(
        "1", "matcher ≤4 zīmju formas (T1)", len(pols), len(flagged_pids),
        "izpēte; negative_patterns tikai priekšlikumi", gate=False, rows=rows,
    )


# --- 1b. B2-veto žurnāls — informatīva --------------------------------------

def check_1b(ctx: Ctx) -> CheckResult:
    """Prompta Python bloks gandrīz burtiski. `match_politicians` ielādē formas
    caur `get_db()` ar noklusēto ceļu, tāpēc uz izsaukuma laiku `src.db.DB_PATH`
    tiek pārslēgts uz `ctx.db_path` un pēc tam atjaunots (tikai SELECT)."""
    import src.db as _db
    from src.matcher import _clear_politician_cache, match_politicians

    logging.getLogger("src.matcher").setLevel(logging.ERROR)
    docs = ctx.db.execute(
        "SELECT id, content FROM documents WHERE scraped_at >= ? AND content IS NOT NULL",
        (lv_cutoff(VETO_JOURNAL_DAYS),),
    ).fetchall()
    names = {r["id"]: r["name"] for r in ctx.db.execute("SELECT id, name FROM tracked_politicians")}
    old_path = _db.DB_PATH
    _db.DB_PATH = ctx.db_path
    _clear_politician_cache()
    by_pair: dict = collections.defaultdict(list)
    try:
        for d in docs:
            log: list[dict] = []
            match_politicians(d["content"], veto_log=log)
            for e in log:
                by_pair[(e["pid"], e["preceding"])].append((d["id"], e["snippet"]))
    finally:
        _db.DB_PATH = old_path
        _clear_politician_cache()
    rows = [
        {"id": pid, "name": names.get(pid, pid), "preceding": prec, "docs": len(hits),
         "piemērs": f"{hits[0][0]}: {hits[0][1][:90]!r}"}
        for (pid, prec), hits in sorted(by_pair.items(), key=lambda kv: -len(kv[1]))
    ]
    return CheckResult(
        "1b", "B2-veto žurnāls (14 d)", len(docs), len(by_pair),
        "izpēte; lasīt abos virzienos", gate=False, rows=rows,
    )


# --- 2. x_handle ↔ social_accounts ------------------------------------------

def check_2(ctx: Ctx) -> CheckResult:
    """Prompta SQL (a)/(b)/(c). NULL zars ir obligāts: kails
    `LOWER(a) <> LOWER(b)` ir SQL-NULL-akls (7 rindas nereportētas mēnešiem)."""
    db = ctx.db
    denom = _one(db, """
        SELECT COUNT(*) AS saucejs FROM social_accounts sa
          JOIN tracked_politicians tp ON tp.id = sa.opponent_id
         WHERE sa.platform = 'twitter'""")
    null_rows = db.execute("""
        SELECT tp.id, tp.name, tp.relationship_type, sa.handle FROM social_accounts sa
          JOIN tracked_politicians tp ON tp.id = sa.opponent_id
         WHERE sa.platform = 'twitter' AND tp.x_handle IS NULL AND sa.handle IS NOT NULL
         ORDER BY tp.id""").fetchall()
    value_rows = db.execute("""
        SELECT tp.id, tp.name, tp.x_handle, sa.handle FROM social_accounts sa
          JOIN tracked_politicians tp ON tp.id = sa.opponent_id
         WHERE sa.platform = 'twitter' AND tp.x_handle IS NOT NULL
           AND LOWER(tp.x_handle) <> LOWER(sa.handle)
         ORDER BY tp.id""").fetchall()
    rows = [{"klase": "NULL", **dict(r)} for r in null_rows]
    rows += [{"klase": "vērtība", **dict(r)} for r in value_rows]
    return CheckResult(
        "2", "x_handle ↔ social_accounts", denom, len(rows), "0 ārpus pieņemtajiem",
        accepted=[r["id"] for r in rows if r["id"] in ACCEPTED_2], rows=rows,
        extra={"saucējs": denom, "NULL klase": len(null_rows), "vērtību nesakritība": len(value_rows)},
    )


# --- 3. Bāreņi ---------------------------------------------------------------

def check_3(ctx: Ctx) -> CheckResult:
    """PROZAS LASĪJUMS: «neatrisinās» = NULL vai norāda uz neesošu claim.
    `position` claims uz `inactive` politiķiem — tikai skaits (audit trail)."""
    db = ctx.db
    checked = _one(db, "SELECT COUNT(*) FROM contradictions")
    bad = db.execute("""
        SELECT c.id, c.claim_old_id, c.claim_new_id, c.confirmed FROM contradictions c
         WHERE c.claim_old_id IS NULL OR c.claim_new_id IS NULL
            OR NOT EXISTS (SELECT 1 FROM claims x WHERE x.id = c.claim_old_id)
            OR NOT EXISTS (SELECT 1 FROM claims x WHERE x.id = c.claim_new_id)
         ORDER BY c.id""").fetchall()
    inactive = _one(db, """
        SELECT COUNT(*) FROM claims c JOIN tracked_politicians tp ON tp.id = c.opponent_id
         WHERE c.claim_type = 'position' AND tp.relationship_type = 'inactive'""")
    rows = [dict(r) for r in bad]
    return CheckResult(
        "3", "pretrunu bāreņu atsauces", checked, len(rows), "0 ārpus pieņemtajiem",
        accepted=[r["id"] for r in rows if r["id"] in ACCEPTED_3], rows=rows,
        extra={"position uz inactive (info)": inactive},
    )


# --- 4. Novecojušas pārskatīšanas rindas ------------------------------------

_REVIEW_BUCKETS_SQL = """
SELECT CASE WHEN julianday(:now) - julianday(COALESCE(review_status_at, created_at)) > 30 THEN '>30d'
            WHEN julianday(:now) - julianday(COALESCE(review_status_at, created_at)) > 14 THEN '15-30d'
            WHEN julianday(:now) - julianday(COALESCE(review_status_at, created_at)) > 7  THEN '8-14d'
            ELSE '<=7d' END AS vecums,
       COUNT(*)
FROM claims WHERE review_status = 'needs_review'
GROUP BY 1 ORDER BY 2 DESC"""


def check_4(ctx: Ctx) -> CheckResult:
    """Pretrunas: reviewed=0 >14 d; confirmed=0 AND reviewed=0 >30 d
    (`detected_at` ir LV → `lv_cutoff`). Claims: vārtu forma ir
    `src.db.open_review_queue()` — tā pati `REVIEW_AGE_EXPR` + `now_lv()` +
    `age_days > REVIEW_QUEUE_AGE_DAYS`, šeit uz ro savienojuma (tests sargā, ka
    abas sakrīt). Vecuma sadalījums mēra pret `now_lv()` — kolonnas ir LV laikā,
    un `julianday('now')` (UTC) tās novecināja par 3 h (T17; labots 2026-09-30).
    Sanity rinda jābūt 0: tā salīdzina kolonnu ar trigeru PAŠU izteiksmi
    (`_REVIEW_STATUS_EXPR`, `IS NOT`), tāpēc redz arī NULL kolonnu pie marķiera —
    agrākā `(a) != (b)` forma NULL gadījumā atgrieza NULL un klusēja."""
    db = ctx.db
    n_contr = _one(db, "SELECT COUNT(*) FROM contradictions")
    stale_rev = db.execute(
        "SELECT id, detected_at FROM contradictions WHERE reviewed = 0 AND detected_at < ? ORDER BY id",
        (lv_cutoff(CONTRADICTION_REVIEW_DAYS),)).fetchall()
    stale_conf = db.execute(
        "SELECT id, detected_at FROM contradictions WHERE confirmed = 0 AND reviewed = 0 "
        "AND detected_at < ? ORDER BY id",
        (lv_cutoff(SURVIVOR_UNCONFIRMED_DAYS),)).fetchall()
    queue = db.execute(
        f"""SELECT c.id, CAST(julianday(?) - julianday({REVIEW_AGE_EXPR}) AS INT) AS age_days
            FROM claims c WHERE c.review_status = 'needs_review'
            ORDER BY {REVIEW_AGE_EXPR}""",
        (now_lv(),)).fetchall()
    aging = [r for r in queue if r["age_days"] > REVIEW_QUEUE_AGE_DAYS]
    sanity = _one(db, f"SELECT COUNT(*) FROM claims WHERE review_status IS NOT ({_REVIEW_STATUS_EXPR})")
    buckets = {r[0]: r[1] for r in db.execute(_REVIEW_BUCKETS_SQL, {"now": now_lv()}).fetchall()}
    reviewed = _one(db, "SELECT COUNT(*) FROM claims WHERE review_status = 'reviewed'")
    contr_ids = sorted({r["id"] for r in stale_rev} | {r["id"] for r in stale_conf})
    rows = [{"klase": f"pretruna reviewed=0 >{CONTRADICTION_REVIEW_DAYS}d", "id": r["id"],
             "detected_at": r["detected_at"]} for r in stale_rev]
    rows += [{"klase": f"pretruna confirmed=0 reviewed=0 >{SURVIVOR_UNCONFIRMED_DAYS}d",
              "id": r["id"], "detected_at": r["detected_at"]} for r in stale_conf]
    rows += [{"klase": f"needs_review >{REVIEW_QUEUE_AGE_DAYS}d", "id": r["id"],
              "age_days": r["age_days"]} for r in aging]
    if sanity:
        rows.append({"klase": "trigeru sanity ≠ 0", "id": None, "n": sanity})
    return CheckResult(
        "4", "novecojušas pārskatīšanas rindas", n_contr + len(queue),
        len(contr_ids) + len(aging) + (sanity > 0), "0", rows=rows,
        extra={"pretrunas": n_contr, f"reviewed=0 >{CONTRADICTION_REVIEW_DAYS}d": len(stale_rev),
               f"confirmed=0∧reviewed=0 >{SURVIVOR_UNCONFIRMED_DAYS}d": len(stale_conf),
               "needs_review": len(queue), f">{REVIEW_QUEUE_AGE_DAYS}d": len(aging),
               "reviewed": reviewed, "sadalījums": buckets, "trigeru sanity": sanity},
    )


# --- 5. Novecojusi partijas valoda (T6) -------------------------------------

def check_5(ctx: Ctx) -> CheckResult:
    """PROZAS LASĪJUMS: «stance/reasoning SATUR» → `LIKE '%…%'` (prefiksa forma
    `'izstāj%'` pret stance teikumu praktiski nekad nenostrādā). Nosacījums
    «party nemainīts kopš pirms stated_at» nav izpildāms — partijas vēstures
    kolonnas nav; tāpēc katra rinda ir kandidāts manuālai pārbaudei."""
    cond = " OR ".join(f"c.{col} LIKE '%{p}%'" for col in ("stance", "reasoning")
                       for p in STALE_PARTY_PATTERNS)
    cutoff = lv_cutoff(STALE_PARTY_DAYS)
    checked = _one(ctx.db, "SELECT COUNT(*) FROM claims c WHERE c.topic = ? AND c.stated_at >= ?",
                   (STALE_PARTY_TOPIC, cutoff))
    rows = ctx.db.execute(
        f"""SELECT c.id, tp.id AS pid, tp.name, tp.party, c.stated_at, substr(c.stance, 1, 120) AS stance
            FROM claims c JOIN tracked_politicians tp ON tp.id = c.opponent_id
            WHERE c.topic = ? AND c.stated_at >= ? AND ({cond}) ORDER BY c.id""",
        (STALE_PARTY_TOPIC, cutoff)).fetchall()
    return CheckResult("5", "partijas maiņas valoda (T6)", checked, len(rows), "0",
                       rows=[dict(r) for r in rows])


# --- 6. Tās pašas dienas dublikāti — informatīva ----------------------------

def check_6(ctx: Ctx) -> CheckResult:
    """PROZAS LASĪJUMS: `position`, 30 d pēc `stated_at`, grupa = tas pats
    `(opponent_id, topic, DATE(stated_at))` ar ≥2 dažādiem `source_url`.
    Stance-līdzības filtra NAV (nekad nav bijis definēts) — `flagged` ir augšējā
    robeža (BACKLOG § Atliktais 57), tāpēc pārbaude ir informatīva."""
    cutoff = lv_cutoff(SAME_DAY_DUP_DAYS)
    checked = _one(ctx.db, "SELECT COUNT(*) FROM claims WHERE claim_type = 'position' AND stated_at >= ?",
                   (cutoff,))
    groups = ctx.db.execute("""
        SELECT opponent_id, topic, DATE(stated_at) AS diena,
               COUNT(DISTINCT source_url) AS urls, GROUP_CONCAT(id) AS ids
        FROM claims WHERE claim_type = 'position' AND stated_at >= ?
        GROUP BY opponent_id, topic, DATE(stated_at)
        HAVING COUNT(DISTINCT source_url) > 1
        ORDER BY diena DESC, opponent_id""", (cutoff,)).fetchall()
    return CheckResult("6", "tās pašas dienas dublikātu grupas (30 d)", checked, len(groups),
                       "augšējā robeža; triāža pēc stance", gate=False,
                       rows=[dict(r) for r in groups])


# --- 7. Pārskatu attēlu varianti (DB→disks) ---------------------------------

def check_7(ctx: Ctx) -> CheckResult:
    """Prompta Python bloks: katrai `approved=1` rindai visi četri
    `VARIANTS` zem `output/atmina/`. Virziens DB→disks — disks→DB skenēja
    vienu failu un bija «tīrs» mūžīgi."""
    from src.image_variants import VARIANTS, variant_filename

    total = 0
    rows: list[dict] = []
    for r in ctx.db.execute(
        "SELECT id, note_id, image_path FROM brief_images WHERE approved=1 ORDER BY id"
    ):
        total += 1
        rel = Path(r["image_path"].removeprefix("atmina/"))
        missing = [v for v in VARIANTS
                   if not (ctx.output_root / rel.with_name(variant_filename(rel.name, v))).exists()]
        if missing:
            rows.append({"id": r["id"], "note_id": r["note_id"], "path": str(rel), "trūkst": missing})
    buckets = {b[0]: b[1] for b in ctx.db.execute(
        "SELECT approved, COUNT(*) FROM brief_images GROUP BY approved").fetchall()}
    return CheckResult("7", "pārskatu attēlu varianti (DB→disks)", total, len(rows), "0",
                       rows=rows, extra={"approved sadalījums": buckets})


# --- 8. Nogriezti stubi — informatīva ---------------------------------------

def check_8(ctx: Ctx) -> CheckResult:
    """PROZAS LASĪJUMS: nepārskatīti dokumenti ar `word_count < 80`, logs 30 d
    pēc `scraped_at` (vienīgais ierakstītais skrējiens, `logs` 2026-07-07:
    `8_truncated_stubs_30d`). Prompts platformu nefiltrē, tāpēc tvīti dominē
    skaitu — platformu sadalījums ir `extra`. Re-ingest kandidāti, ne vārti."""
    cutoff = lv_cutoff(STUB_DAYS)
    by_pl = ctx.db.execute(
        "SELECT platform, COUNT(*) AS n, SUM(word_count < ?) AS stubs FROM documents "
        "WHERE reviewed_at IS NULL AND scraped_at >= ? GROUP BY platform ORDER BY platform",
        (STUB_WORDS, cutoff)).fetchall()
    checked = sum(r["n"] for r in by_pl)
    flagged = sum(r["stubs"] or 0 for r in by_pl)
    sample = ctx.db.execute(
        "SELECT id, platform, word_count, source_url FROM documents "
        "WHERE reviewed_at IS NULL AND scraped_at >= ? AND word_count < ? "
        "AND platform = 'web' ORDER BY id DESC LIMIT 20", (cutoff, STUB_WORDS)).fetchall()
    return CheckResult("8", "nogriezti stubi (<80 vārdi, 30 d)", checked, flagged,
                       "re-ingest kandidāti", gate=False, rows=[dict(r) for r in sample],
                       extra={"pa platformām": {r["platform"]: r["stubs"] or 0 for r in by_pl}})


# --- 9. Partija ↔ Saeimas frakcija (T6) -------------------------------------

_FACTION_SQL = """
SELECT tp.id, tp.name, tp.party, iv.faction, COUNT(*) n,
       MIN(v.vote_date) first, MAX(v.vote_date) last
FROM tracked_politicians tp
JOIN saeima_individual_votes iv ON iv.politician_id = tp.id
JOIN saeima_votes v ON v.id = iv.vote_id
WHERE tp.relationship_type != 'inactive' AND iv.faction IS NOT NULL
GROUP BY tp.id, iv.faction ORDER BY tp.id, first"""


def check_9(ctx: Ctx) -> CheckResult:
    """Prompta SQL; tad Python: partijas `short_name` (pēc `parties.name` vai
    `short_name`) segums <20 % no frakcijas etiķetētajiem balsojumiem → karogs.
    Izlaiž partijas, kuru `short_name` nekad neparādās kā etiķete (alianses,
    ne-Saeimas partijas) — tās klusē pēc konstrukcijas. Triāžas logs (7 d līdz
    pēdējam etiķetētajam balsojumam) ir tikai attēlošanai."""
    db = ctx.db
    timeline = db.execute(_FACTION_SQL).fetchall()
    labels = {r["faction"] for r in timeline}
    short_of: dict[str, str] = {}
    for p in db.execute("SELECT name, short_name FROM parties").fetchall():
        if p["short_name"]:
            short_of[p["name"]] = p["short_name"]
            short_of[p["short_name"]] = p["short_name"]
    by_pid: dict[int, list] = collections.defaultdict(list)
    for r in timeline:
        by_pid[r["id"]].append(r)
    checked = 0
    rows: list[dict] = []
    for pid, tl in by_pid.items():
        short = short_of.get(tl[0]["party"] or "")
        if not short or short not in labels:
            continue
        checked += 1
        total = sum(r["n"] for r in tl)
        own = sum(r["n"] for r in tl if r["faction"] == short)
        if own / total >= FACTION_COVERAGE_MIN:
            continue
        last = max(r["last"] for r in tl)
        start = (datetime.strptime(last[:10], "%Y-%m-%d")
                 - timedelta(days=FACTION_WINDOW_DAYS - 1)).strftime("%Y-%m-%d")
        window_votes = _one(db, "SELECT COUNT(*) FROM saeima_votes WHERE vote_date BETWEEN ? AND ?",
                            (start, last))
        in_window = {r[0]: r[1] for r in db.execute(
            "SELECT iv.faction, COUNT(*) FROM saeima_individual_votes iv "
            "JOIN saeima_votes v ON v.id = iv.vote_id WHERE iv.politician_id = ? "
            "AND v.vote_date BETWEEN ? AND ? GROUP BY iv.faction", (pid, start, last)).fetchall()}
        rows.append({
            "id": pid, "name": tl[0]["name"], "party": tl[0]["party"], "short": short,
            "segums": f"{own}/{total}",
            "laika līnija": [(r["faction"], r["n"], r["first"], r["last"]) for r in tl],
            "logs": f"{start}…{last[:10]} ({window_votes} balsojumi): "
                    + ", ".join(f"{k or '∅'} {v}/{window_votes}" for k, v in in_window.items()),
        })
    return CheckResult(
        "9", "partija ↔ frakcijas ieraksts (<20 %)", checked, len(rows), "0 ārpus pieņemtajiem",
        accepted=[r["id"] for r in rows if r["id"] in ACCEPTED_9], rows=rows,
        extra={"etiķetes": sorted(labels)},
    )


def check_9b(ctx: Ctx) -> CheckResult:
    """`scripts/audit_minister_vote_coverage.py` — tās pašas funkcijas izsaukums."""
    from scripts.audit_minister_vote_coverage import audit_minister_coverage

    res = audit_minister_coverage(ctx.db)
    return CheckResult("9b", "ministri bez balsojumu seguma (aklā zona)", res["checked"],
                       res["flagged"], "katra rinda = manuāla partijas pārbaude",
                       rows=[dict(r) for r in res["rows"]])


# --- 10. Provenance, kas neatrisinās + ar roku rakstītu rindu paraksti ------

def check_10(ctx: Ctx) -> CheckResult:
    """Prompta A/B/C/D SQL burtiski; saucēji — katra vaicājuma kandidātu kopa.
    D saista UTC «tagad» (`ctx.now_utc`) — tas ir tās pašas sesijas slazds
    (ķer tikai pēdējo ~3 h rakstus), ne vēsturisks audits."""
    db = ctx.db
    now = ctx.utc_now_str()
    a = db.execute("""
        SELECT t.id, substr(t.created_at,1,19) AS created_at, t.source_url
        FROM political_tensions t
        WHERE COALESCE(t.source_url,'') <> ''
          AND NOT EXISTS (SELECT 1 FROM documents d WHERE d.source_url = t.source_url)
        ORDER BY t.id DESC""").fetchall()
    b = db.execute("""
        SELECT c.id, c.claim_type, c.document_id, c.source_url, d.source_url AS doc_url
        FROM claims c JOIN documents d ON d.id = c.document_id
        WHERE c.document_id IS NOT NULL
          AND COALESCE(c.source_url,'') <> COALESCE(d.source_url,'')""").fetchall()
    c = db.execute("""
        SELECT c.id, c.source_url FROM claims c
        WHERE c.claim_type = 'saeima_vote' AND COALESCE(c.source_url,'') <> ''
          AND NOT EXISTS (SELECT 1 FROM saeima_votes v WHERE v.url = c.source_url)""").fetchall()
    d = db.execute("""
        SELECT id, created_at FROM political_tensions WHERE created_at > ?
        UNION ALL SELECT id, created_at FROM analyses WHERE created_at > ?""", (now, now)).fetchall()
    den = {
        "A": _one(db, "SELECT COUNT(*) FROM political_tensions WHERE COALESCE(source_url,'') <> ''"),
        "B": _one(db, "SELECT COUNT(*) FROM claims c JOIN documents d ON d.id = c.document_id "
                      "WHERE c.document_id IS NOT NULL"),
        "C": _one(db, "SELECT COUNT(*) FROM claims WHERE claim_type = 'saeima_vote' "
                      "AND COALESCE(source_url,'') <> ''"),
        "D": _one(db, "SELECT (SELECT COUNT(*) FROM political_tensions) + (SELECT COUNT(*) FROM analyses)"),
    }
    found = {"A": a, "B": b, "C": c, "D": d}
    rows = [{"klase": k, **dict(r)} for k, rs in found.items() for r in rs]
    return CheckResult(
        "10", "provenance neatrisinās / roku rakstītas rindas", sum(den.values()), len(rows), "0",
        rows=rows, extra={k: f"{den[k]}/{len(found[k])}" for k in den},
    )


# --- 11. Datu kontrakts #4b globāli ------------------------------------------

def check_11(ctx: Ctx) -> CheckResult:
    """Aklā zona: salīdzina atslēgas, ne rindas — 14. to redz. Atslēga ir
    NULL-droša (`COALESCE`): `||` ar NULL dod NULL, `COUNT(DISTINCT)` to izlaiž,
    un katra rinda ar NULL `source_url`/`topic` agrāk uzpūta deltu (labots 2026-09-30)."""
    key = "COALESCE(opponent_id, '') || '|' || COALESCE(source_url, '') || '|' || COALESCE(topic, '')"
    r = ctx.db.execute(f"""
        SELECT COUNT(*) AS total,
               COUNT(DISTINCT {key}) AS distinct_triples,
               COUNT(*) - COUNT(DISTINCT {key}) AS delta
        FROM claims WHERE claim_type = 'saeima_vote'""").fetchone()
    return CheckResult("11", "saeima_vote trijnieku delta (#4b)", r["total"], r["delta"], "0",
                       extra={"distinct_triples": r["distinct_triples"]})


# --- 12 / 15. Junction lomu inversija — informatīva --------------------------

def _inversions(ctx: Ctx) -> dict:
    if "inversions" not in ctx.cache:
        from src.quoted_speaker import find_inversions

        ctx.cache["inversions"] = find_inversions(ctx.db, days=INVERSION_DAYS)
    return ctx.cache["inversions"]


def _inversion_result(num: str, name: str, ctx: Ctx) -> CheckResult:
    res = _inversions(ctx)
    inv = res["inversions"]
    by_pl = collections.Counter(i.get("platform") or "?" for i in inv)
    rows = [{"id": i["document_id"], "platform": i.get("platform"),
             "runā (mentioned)": ", ".join(i["speaker_names"]),
             "subject": ", ".join(i["subject_names"])} for i in inv]
    return CheckResult(num, name, res["checked"], len(inv), "kandidāti; lasīt likmi, ne skaitu",
                       gate=False, rows=rows, extra={"pa platformām": dict(by_pl)})


def check_12(ctx: Ctx) -> CheckResult:
    """Tas pats mērījums kā 15. (viena funkcija, lai nav divu mērījumu)."""
    return _inversion_result("12", "mentioned runātājs ārpus rindas (=15)", ctx)


def check_15(ctx: Ctx) -> CheckResult:
    return _inversion_result("15", "junction lomu inversija (90 d)", ctx)


# --- 13. claim_vectors novecošana -------------------------------------------

def check_13(ctx: Ctx) -> CheckResult:
    """`scripts/audit_vector_staleness.run_audit` ar skripta noklusējumiem
    (kandidāti no `data/fix_*.sql`, izlase 300, kontrole 25 no
    `reembed_elektr_vectors_2026-08-03.ids`). `method_ok=False` → 2."""
    from scripts.audit_vector_staleness import extract_fix_file_ids, run_audit

    ids = extract_fix_file_ids(ctx.data_dir)
    cpath = ctx.data_dir / "reembed_elektr_vectors_2026-08-03.ids"
    control = [int(x) for x in cpath.read_text().split()][:25] if cpath.exists() else []
    rep = run_audit(ctx.db_path, ids, sample=300, control_ids=control, embed_fn=ctx.embed_fn)
    return CheckResult(
        "13", "claim_vectors novecošana", rep["checked"], rep["stale"], "0",
        rows=[{"id": i} for i in rep["stale_ids"]],
        broken="" if rep["method_ok"] else rep["note"],
        extra={"match": rep["match"], "missing": rep["missing"],
               "saeima_vote_izslēgti": rep["vote_excluded"],
               "kontrole": f"{rep['control']['match']}/{rep['control']['checked']}"},
    )


# --- 14. saeima_vote claims pa balsojumiem pret nodotajām balsīm ------------

_BALLOT_CTE = """
WITH b AS (
    SELECT vote_id, COUNT(*) AS ballots
    FROM saeima_individual_votes
    WHERE vote IN ('Par','Pret','Atturas','Nebalsoja')
    GROUP BY vote_id
), c AS (
    SELECT source_url, COUNT(*) AS claims
    FROM claims WHERE claim_type = 'saeima_vote'
    GROUP BY source_url
)"""


def check_14(ctx: Ctx) -> CheckResult:
    """Prompta SQL burtiski (vispirms agregē abas puses — `claims.source_url`
    nav indeksa). Saucējs = balsojumi ar ≥1 nodotu balsi. Lasīt attiecību:
    2.0 = ielādēts divreiz; <1.0 = daļējs raksts (`store_vote()` commit pirms
    claims); 0 = ģenerēšana nav notikusi."""
    db = ctx.db
    checked = _one(db, _BALLOT_CTE + " SELECT COUNT(*) FROM saeima_votes v JOIN b ON b.vote_id = v.id")
    rows = db.execute(_BALLOT_CTE + """
        SELECT v.id, v.vote_date, b.ballots, COALESCE(c.claims, 0) AS claims,
               ROUND(COALESCE(c.claims, 0) * 1.0 / b.ballots, 2) AS ratio
        FROM saeima_votes v
        JOIN b ON b.vote_id = v.id
        LEFT JOIN c ON c.source_url = v.url
        WHERE COALESCE(c.claims, 0) != b.ballots
        ORDER BY ratio DESC, v.vote_date""").fetchall()
    return CheckResult(
        "14", "saeima_vote claims pa balsojumiem", checked, len(rows), "0",
        rows=[dict(r) for r in rows],
        extra={"missing (<1.0)": sum(1 for r in rows if r["ratio"] < 1.0),
               "dubultoti (2.0)": sum(1 for r in rows if r["ratio"] == 2.0)},
    )


# --- 16. Ne-kanonisks daily_brief topic -------------------------------------

def check_16(ctx: Ctx) -> CheckResult:
    """Prompta SQL burtiski. Labojot prefiksu neraksta ar roku:
    `src.briefs.daily_brief_topic(date)` + `brief_subject_date()`."""
    r = ctx.db.execute("""
        SELECT COUNT(*) AS checked,
               SUM(topic NOT LIKE 'dienas analīze %') AS flagged
          FROM context_notes WHERE note_type = 'daily_brief'""").fetchone()
    rows = ctx.db.execute("""
        SELECT id, topic, created_at FROM context_notes
         WHERE note_type = 'daily_brief' AND topic NOT LIKE 'dienas analīze %'
         ORDER BY id""").fetchall()
    return CheckResult("16", "daily_brief topic prefikss", r["checked"], r["flagged"] or 0, "0",
                       rows=[dict(x) for x in rows])


# --- 17. Pārskrāpēti web doki, kas vairs nesatur citātu ---------------------

_QUOTE_MARKS = str.maketrans({"„": '"', "“": '"', "”": '"', "«": '"', "»": '"', "″": '"',
                              "‘": "'", "’": "'", "‚": "'", "′": "'"})
_WS = re.compile(r"\s+")


def norm_quote_text(text: str) -> str:
    """Prompta `norm`: diakritiku salocīšana + tipogrāfisko pēdiņu normalizācija
    + lower + `\\s+` sabrukums."""
    return _WS.sub(" ", fold_lower((text or "").translate(_QUOTE_MARKS))).strip()


def check_17(ctx: Ctx) -> CheckResult:
    """Prompta metode: SQL sašaurina (web doki, pārskrāpēti PĒC claim izveides —
    abas kolonnas LV laikā), Python dara salocīto ietveršanas testu. Karogs
    ārpus `ACCEPTED_17` = svaigs pārskrāpējums apēda vēl vienu citātu."""
    cands = ctx.db.execute("""
        SELECT c.id, c.quote, d.content FROM claims c
          JOIN documents d ON d.id = c.document_id
         WHERE c.quote IS NOT NULL AND c.quote != ''
           AND d.platform = 'web' AND d.scraped_at > c.created_at
         ORDER BY c.id""").fetchall()
    rows = [{"id": r["id"], "quote": r["quote"][:90]} for r in cands
            if norm_quote_text(r["quote"]) not in norm_quote_text(r["content"] or "")]
    return CheckResult(
        "17", "pārskrāpēšanā zudis citāts", len(cands), len(rows), "0 ārpus pieņemtajiem",
        accepted=[r["id"] for r in rows if r["id"] in ACCEPTED_17], rows=rows,
    )


# --- 18. Ne-kanoniskas position tēmas ---------------------------------------

def check_18(ctx: Ctx) -> CheckResult:
    """`scripts/audit_topic_canonical.audit_topics` — tās pašas funkcijas izsaukums."""
    from scripts.audit_topic_canonical import audit_topics, canonical_topics

    res = audit_topics(ctx.db, canonical_topics())
    return CheckResult(
        "18", "ne-kanoniskas position tēmas", res["checked"], res["flagged"], "0",
        rows=[{"topic": t, "n": n, "id": i} for t, n, i in res["rows"]],
        extra={"distinct": f"{res['distinct']}/{res['canonical']}"},
    )


CHECKS: dict[str, Callable[[Ctx], CheckResult]] = {
    "1": check_1, "1b": check_1b, "2": check_2, "3": check_3, "4": check_4,
    "5": check_5, "6": check_6, "7": check_7, "8": check_8, "9": check_9,
    "9b": check_9b, "10": check_10, "11": check_11, "12": check_12, "13": check_13,
    "14": check_14, "15": check_15, "16": check_16, "17": check_17, "18": check_18,
}


def select_checks(only: str | None = None, scope: str = "all") -> list[str]:
    if only:
        wanted = [x.strip() for x in only.split(",") if x.strip()]
        unknown = [x for x in wanted if x not in CHECKS]
        if unknown:
            raise SystemExit(f"nezināmas pārbaudes: {unknown}; derīgās: {list(CHECKS)}")
        return wanted
    if scope == "all":
        return list(CHECKS)
    return list(SCOPES[scope])


def run_checks(ctx: Ctx, nums: list[str]) -> list[CheckResult]:
    return [CHECKS[n](ctx) for n in nums]


def exit_code(results: list[CheckResult]) -> int:
    return max((r.status() for r in results), default=0)


def _fmt_example(r: dict) -> str:
    for sub in ("form", "preceding", "klase"):
        if r.get("id") is not None and r.get(sub) is not None:
            return f"{r['id']}:{r[sub]}"
    key = next((k for k in ("id", "ids", "topic") if r.get(k) is not None), None)
    return str(r[key]) if key else "?"


def format_line(r: CheckResult, max_examples: int = 8) -> str:
    tag = "" if r.gate else " [info]"
    line = f"{r.num} · {r.name}{tag} · checked={r.checked} flagged={r.flagged} (sagaidāms {r.expected})"
    if r.accepted:
        line += f" · pieņemti {r.accepted}, jauni {r.new}"
    if r.extra:
        line += " · " + "; ".join(f"{k}={v}" for k, v in r.extra.items())
    if r.rows:
        ex = [_fmt_example(x) for x in r.rows[:max_examples]]
        more = f" …+{len(r.rows) - max_examples}" if len(r.rows) > max_examples else ""
        line += f"\n    piem.: {', '.join(ex)}{more}"
    if r.gate and r.checked == 0:
        line += "\n    SALAUZTI VĀRTI: checked=0 — saucējs tukšs, rezultāts nav pierādījums."
    if r.broken:
        line += f"\n    METODE NEPĀRBAUDĪTA: {r.broken}"
    return line


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--db", default=str(_REPO / PRODUCTION_DB_PATH))
    ap.add_argument("--output-root", default=str(_REPO / "output" / "atmina"))
    ap.add_argument("--only", help="komatiem atdalīti numuri, piem. 2,7,9b")
    ap.add_argument("--scope", default="all", choices=["all", *SCOPES])
    ap.add_argument("--json", action="store_true", help="mašīnlasāma izvade")
    ap.add_argument("--rows", action="store_true", help="drukāt visas rindas (ne tikai piemērus)")
    args = ap.parse_args(argv)

    nums = select_checks(args.only, args.scope)
    db = connect_ro(args.db)
    try:
        ctx = Ctx(db=db, db_path=args.db, output_root=Path(args.output_root))
        results = run_checks(ctx, nums)
    finally:
        db.close()
    code = exit_code(results)
    if args.json:
        payload = [{**asdict(r), "new": r.new, "status": r.status()} for r in results]
        print(json.dumps({"exit": code, "checks": payload}, ensure_ascii=False, default=str, indent=1))
        return code
    for r in results:
        print(format_line(r))
        if args.rows:
            for row in r.rows:
                print(f"      {row}")
    print(f"\nexit={code} (0 tīrs · 1 atradumi · 2 salauzts saucējs / metode nepārbaudīta)")
    return code


if __name__ == "__main__":
    raise SystemExit(main())
