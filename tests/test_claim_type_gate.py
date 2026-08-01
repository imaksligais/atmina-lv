"""Datu kontrakts #4 bija apgalvots, bet neizpildīts.

`CLAUDE.md`: „**every render + brief query gates on `claim_type='position'`**, so
non-`position` types are invisible to those surfaces by construction". Tieši uz
šo pamatojas 4a apakšpunkts — ka programmu solījumi *par brīvu* nenonāk politiķu
lapās. Līdz 2026-08-01 to nepārbaudīja nekas.

Šī klase nedegradējas pakāpeniski. `saeima_vote` pārsniedz `position` attiecībā
**101:1** (512 918 pret 5 078), tāpēc aizmirsts predikāts rezultātu neapgriež
par mazliet — tas to apgriež pilnībā. Mērīts pirms labojuma: 112 no 180 aktīvo
politiķu „pēdējā aktivitāte" nebija pozīcija, un `wiki/index.md` partiju tabulā
Stabilitātei! rādīja 56 794 „pozīcijas" īsto 16 vietā.

Vārti tur `src/render/**`, `src/briefs.py`, `src/wiki.py`, `src/routine.py` —
tieši to virsmu kopu, ko kontrakts nosauc. `src/db.py`, `src/analyze.py` un
meklēšanas ceļi ar nolūku paliek ārpus: tiem visu tipu lasījums IR pareizais.

Vietas, kur visu tipu lasījums ir pareizs arī šeit, dzīvo `ALLOWED` sarakstā ar
pamatojumu katrai. Sarakstam pašam ir vārti (`test_allowlist_has_no_dead_rows`):
novecojis izņēmums ir tieši tas, kā šāds tests klusi pārstāj sargāt.
"""

from __future__ import annotations

import ast
import re
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SRC = REPO / "src"

TARGET_FILES = sorted(
    set(SRC.glob("render/**/*.py"))
    | {SRC / "briefs.py", SRC / "wiki.py", SRC / "routine.py"}
)

_SQL_COMMENT = re.compile(r"--[^\n]*")
_FROM_CLAIMS = re.compile(r"\b(?:FROM|JOIN)\s+claims\b", re.I)

# (fails, raksturīgs SQL fragments, kāpēc visu tipu lasījums šeit ir pareizs)
ALLOWED: list[tuple[str, str, str]] = [
    (
        "src/briefs.py",
        "FROM contradictions c",
        "pretruna JOIN uz claims pēc PRIMĀRĀS ATSLĒGAS (claim_old_id/claim_new_id) — "
        "kuri claims, to nosaka pati pretruna; tipa filtrs te atņemtu rindas, ko "
        "pretruna jau ir izvēlējusies",
    ),
    (
        "src/render/politicians.py",
        "FROM contradictions ct",
        "tas pats, kas augšā — pretrunu JOIN pēc PK, ne pēc tipa",
    ),
    (
        "src/routine.py",
        "SELECT MAX(created_at) as ts FROM claims",
        "kad DB pēdējoreiz kaut kas notika — jebkurš claim ir aktivitāte, "
        "un šo skaitli nekas nenosauc par pozīciju",
    ),
    (
        "src/wiki.py",
        "SELECT DISTINCT topic FROM claims",
        "tēmu universs wiki lapām, ne pozīciju skaitīšana. Mērīts 2026-08-01: "
        "32 tēmas visos tipos un 32 tikai pozīcijās — filtrs neko nemainītu",
    ),
    (
        "src/wiki.py",
        "SELECT COUNT(DISTINCT topic) FROM claims",
        "tas pats tēmu universs, skaitītāja formā (32 = 32)",
    ),
    (
        "src/wiki.py",
        "LEFT JOIN claims c ON c.document_id = d.id",
        "pārskatīti web doki, kas NEDEVA nevienu claim — dokuments, kas deva "
        "komentāru, claim ir devis, tāpēc šeit jāskaita visi tipi",
    ),
    (
        "src/render/news.py",
        "SELECT DISTINCT document_id, topic FROM claims",
        "dokumenta tēmu tagi, ne pozīciju attiecinājums uz politiķi. Mērīts "
        "2026-08-01: filtrs mainītu 5 no 3663 zinu dokumentiem, un visos piecos "
        "tagi TIKTU ZAUDĒTI (None), nevis izlaboti",
    ),
    (
        "src/render/news.py",
        "SELECT DISTINCT document_id FROM claims",
        "vai šim dokumentam vispār ir claims — visu tipu jautājums pēc definīcijas",
    ),
    (
        "src/render/x.py",
        "SELECT c.source_url, c.topic",
        "tvīta tēmas tags pēc URL. Mērīts 2026-08-01: filtrs mainītu 6 no 32 394 "
        "X postiem, un visos sešos tags pazustu — komentāra claim tēma tvītu "
        "apraksta tikpat pareizi kā pozīcijas claim",
    ),
    (
        "src/render/x.py",
        "JOIN documents d ON d.source_url = c.source_url",
        "trending tēmas pār X dokumentiem — jau ierobežotas ar d.platform, tāpēc "
        "balsojumu claims (saeima.lv URL) tur netrāpa pēc konstrukcijas",
    ),
]


def _sql_literals() -> list[tuple[Path, int, str]]:
    """Katrs SQL literālis mērķa failos, ar SQL komentāriem nogrieztiem.

    `ast.walk` atdod gan `JoinedStr`, gan tā iekšējos `Constant` mezglus, tāpēc
    f-string vaicājums bez šīs filtrācijas atnāktu DIVREIZ: vienreiz vesels un
    vienreiz kā fragments līdz pirmajai `{...}` vietai. Fragments, protams,
    nesatur predikātu, kas stāv aiz tās — un tieši tā šis tests pats saražotu
    9 nepatiesus atradumus `briefs.py` (pārbaudīts 2026-08-01).
    """
    out: list[tuple[Path, int, str]] = []
    for path in TARGET_FILES:
        if not path.exists():
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        nested: set[int] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.JoinedStr):
                nested.update(id(c) for c in ast.walk(node) if c is not node)
        for node in ast.walk(tree):
            if id(node) in nested:
                continue
            if isinstance(node, ast.Constant) and isinstance(node.value, str):
                raw = node.value
            elif isinstance(node, ast.JoinedStr):
                # vietturis tur tokenus šķirtus, lai `{tabula}claims` nelasītos
                # kā `claims`
                raw = "".join(
                    v.value if isinstance(v, ast.Constant) and isinstance(v.value, str)
                    else " <expr> "
                    for v in node.values
                )
            else:
                continue
            if raw:
                out.append((path, node.lineno, _SQL_COMMENT.sub("", raw)))
    return out


def _claims_queries() -> list[tuple[Path, int, str]]:
    return [(p, n, s) for p, n, s in _sql_literals() if _FROM_CLAIMS.search(s)]


def _allowlist_match(path: Path, sql: str) -> tuple[str, str, str] | None:
    rel = path.relative_to(REPO).as_posix()
    for entry in ALLOWED:
        if entry[0] == rel and entry[1] in sql:
            return entry
    return None


def test_claims_queries_gate_on_claim_type():
    """Katrs `FROM claims` render/brief virsmā filtrē pēc `claim_type`."""
    offenders = []
    for path, lineno, sql in _claims_queries():
        if "claim_type" in sql:
            continue
        if _allowlist_match(path, sql):
            continue
        one_line = " ".join(sql.split())
        offenders.append(
            f"{path.relative_to(REPO).as_posix()}:{lineno}\n      {one_line[:200]}"
        )
    assert not offenders, (
        f"{len(offenders)} `FROM claims` vaicājumi bez claim_type predikāta "
        "(Datu kontrakts #4):\n    " + "\n    ".join(offenders)
        + "\n  saeima_vote:position ir 101:1, tāpēc trūkstošs predikāts rezultātu "
        "APGRIEŽ, ne pasliktina. Vai nu pievieno filtru, vai ieraksti vietu ALLOWED "
        "sarakstā ar pamatojumu, KĀPĒC visu tipu lasījums tur ir pareizs."
    )


def test_allowlist_has_no_dead_rows():
    """Novecojis izņēmums ir tieši tas, kā šādi vārti klusi pārstāj sargāt."""
    queries = _claims_queries()
    dead = []
    for entry in ALLOWED:
        rel, fragment, _reason = entry
        if not any(
            p.relative_to(REPO).as_posix() == rel and fragment in sql
            for p, _n, sql in queries
        ):
            dead.append(f"{rel} — fragments neatbilst nevienam vaicājumam: {fragment!r}")
    assert not dead, (
        "ALLOWED rindas, kas vairs neko nesedz:\n  " + "\n  ".join(dead)
        + "\nIzņem tās — citādi saraksts aug, un vārti sedz mazāk, nekā izskatās."
    )


def test_allowlist_entries_carry_a_reason():
    missing = [e[0] + " / " + e[1] for e in ALLOWED if not e[2].strip()]
    assert not missing, (
        "ALLOWED rindas bez pamatojuma:\n  " + "\n  ".join(missing)
        + "\nBez pamatojuma nākamā sesija nevar zināt, vai izņēmums vēl ir patiess."
    )


def test_gate_actually_scans_something():
    """Tukša mērķu kopa padarītu visus augšējos testus par tukšu zaļo gaismu."""
    queries = _claims_queries()
    assert len(TARGET_FILES) >= 8, f"mērķa failu par maz: {len(TARGET_FILES)}"
    assert len(queries) >= 50, (
        f"atrasti tikai {len(queries)} `FROM claims` vaicājumi — pārbaudi, vai "
        "literāļu izvilcējs nav salūzis"
    )
