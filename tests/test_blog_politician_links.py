"""Politiķu saites ar lodziņu dienas pārskatos (`blog/<datums>.html`).

Kļūmes, ko šis tests ķer: (1) dienas pārskatā vārds paliek bez saites, jo
renderis to dienu nesasaista ar cilvēkiem; (2) saiti saņem cilvēks, kuram tajā
dienā nav nedz pozīcijas, nedz publiskas pretrunas (tikai pieminēts — T1 klases
risks); (3) nedēļas pārskats vai `blog.html` iegūst saites, kaut tās nav
apstiprinātas; (4) grupētais vaicājums aizslīd prom no skeleta dienas predikāta.

Īstais orķestrators, pagaidu DB; dzīvā DB netiek aiztikta.
"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

import pytest

from src.briefs import _BRIEF_DAY_CLAIM_SQL, DAILY_BRIEF_TOPIC_PREFIX, _brief_day_params
from src.db import get_db, init_db
from src.saeima.schema import init_saeima_bills, init_saeima_tables

DAY = "2031-10-24"
EARLIER = "2031-10-21"
WEEK = "2031-10-20"

SPOKE = "Anna Bērziņa"           # pozīcija šajā dienā, vārds rindkopā
IN_TABLE = "Kārlis Ozols"        # pozīcija šajā dienā, vārds tikai tabulas šūnā
LATE = "Laura Kalniņa"           # teikts agrāk, ielādēts šajā dienā (skeleta otrais zars)
CONTRA = "Pēteris Vītols"        # tikai publiska pretruna šajā dienā
OTHER_DAY = "Inese Kalna"        # pozīcija citā dienā — šeit tikai pieminēta
WITHDRAWN = "Rita Zariņa"        # atsaukta pretruna (confirmed=-1)
CANDIDATE = "Ilze Krūma"         # pretrunas kandidāts (confirmed=0)
IN_REVIEW = "Līga Sproģe"        # pozīcija šajā dienā, bet needs_review

BRIEF = f"""# Dienas pārskats — {DAY}

## Galvenais

{SPOKE} runāja. {SPOKE} atkārtoja. {LATE} piebilda, {CONTRA} iebilda.
{OTHER_DAY}, {WITHDRAWN}, {CANDIDATE} un {IN_REVIEW} arī tika pieminēti.

## Aktīvākie politiķi

| Politiķis | Pozīcijas |
|---|---|
| {IN_TABLE} | 1 |
"""
WEEKLY = f"# Nedēļas analīze — {WEEK} līdz 2031-10-26\n\n## Īsumā\n\n{SPOKE} runāja.\n"


def _pid(db, name: str) -> int:
    return db.execute(
        "INSERT INTO tracked_politicians (name, party, relationship_type) "
        "VALUES (?, 'Partija', 'coalition')",
        (name,),
    ).lastrowid


def _claim(db, pid: int, stated: str, created: str, reasoning: str = "") -> None:
    db.execute(
        "INSERT INTO claims (opponent_id, topic, stance, quote, source_url, claim_type, "
        "stated_at, created_at, reasoning) VALUES (?, 'Ekonomika', 's', 'q', ?, 'position', ?, ?, ?)",
        (pid, f"https://e.lv/{pid}/{stated}/{created}", f"{stated} 10:00:00",
         f"{created} 12:00:00", reasoning),
    )


def _contradiction(db, pid: int, detected: str, confirmed: int) -> None:
    db.execute(
        "INSERT INTO contradictions (opponent_id, topic, summary, confirmed, detected_at) "
        "VALUES (?, 'Ekonomika', 'p', ?, ?)",
        (pid, confirmed, detected),
    )


@pytest.fixture
def db_path():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    init_db(path)
    init_saeima_tables(path)
    init_saeima_bills(path)
    db = get_db(path)
    ids = {n: _pid(db, n) for n in (
        SPOKE, IN_TABLE, LATE, CONTRA, OTHER_DAY, WITHDRAWN, CANDIDATE, IN_REVIEW)}
    _claim(db, ids[SPOKE], DAY, DAY)
    # Nedēļas pārskata datumā arī ir pozīcija: tikai `is_weekly` tur saites prom.
    _claim(db, ids[SPOKE], WEEK, WEEK)
    _claim(db, ids[IN_TABLE], DAY, DAY)
    _claim(db, ids[LATE], EARLIER, DAY)
    _claim(db, ids[OTHER_DAY], EARLIER, EARLIER)
    _claim(db, ids[IN_REVIEW], DAY, DAY, reasoning="NEEDS_REVIEW: tests")
    # 00:30 nākamajā kalendāra dienā joprojām ir šīs dienas rutīna.
    _contradiction(db, ids[CONTRA], "2031-10-25 00:30:00", 1)
    _contradiction(db, ids[WITHDRAWN], f"{DAY} 15:00:00", -1)
    _contradiction(db, ids[CANDIDATE], f"{DAY} 15:00:00", 0)
    db.execute(
        "INSERT INTO context_notes (topic, note_type, content, created_at) "
        "VALUES (?, 'daily_brief', ?, ?)",
        (f"{DAILY_BRIEF_TOPIC_PREFIX}{DAY}", BRIEF, f"{DAY} 21:00:00"),
    )
    db.execute(
        "INSERT INTO context_notes (topic, note_type, content, created_at) "
        "VALUES (?, 'weekly_brief', ?, ?)",
        (f"nedēļas pārskats {WEEK}", WEEKLY, "2031-10-26 21:00:00"),
    )
    db.commit()
    db.close()
    yield path
    try:
        os.remove(path)
    except OSError:
        pass


def _render(db_path: str, out: Path) -> Path:
    import src.render._orchestrator as orch

    with pytest.MonkeyPatch.context() as mp:
        for name in ("_download_chart_js", "_download_annotation_plugin", "_download_d3"):
            mp.setattr(orch, name, lambda *a, **k: None)
        orch.generate_public_site(
            db_path=db_path, output_dir=str(out), only={"blog"}, include_drafts=True,
        )
    return out / "atmina"


def test_daily_brief_links_that_days_politicians_only(db_path, tmp_path, capfd):
    site = _render(db_path, tmp_path)
    page = (site / "blog" / f"{DAY}.html").read_text(encoding="utf-8")

    # Pirmā pilnā vārda pieminēšana → profils; otrā paliek teksts.
    assert page.count('class="pol-link"') == 4
    assert '<a class="pol-link" href="../politiki/anna-berzina.html"' in page
    assert f"</a> runāja. {SPOKE} atkārtoja." in page
    # Tabulas šūna, skeleta otrais zars un tikai-pretrunas cilvēks.
    assert '<td data-label="Politiķis"><a class="pol-link" href="../politiki/karlis-ozols.html"' in page
    assert '<a class="pol-link" href="../politiki/laura-kalnina.html"' in page
    assert '<a class="pol-link" href="../politiki/peteris-vitols.html"' in page
    # Cits datums, atsaukta pretruna, kandidāts, needs_review — bez saites.
    for name in (OTHER_DAY, WITHDRAWN, CANDIDATE, IN_REVIEW):
        assert name in page
        assert f">{name}</a>" not in page

    assert 'id="pol-pop"' in page
    assert "assets/polpop.js" in page

    # Nedēļas pārskats un rādītājs nemainās (saucējs: vārds tur ir).
    weekly = (site / "blog" / f"nedela-{WEEK}.html").read_text(encoding="utf-8")
    assert SPOKE in weekly
    for other in (weekly, (site / "blog.html").read_text(encoding="utf-8")):
        assert "pol-link" not in other
        assert "pol-pop" not in other
        assert "polpop.js" not in other

    # Saucējs stderr: viena kopsavilkuma rinda, ne pa rindai katrai lapai.
    lines = [
        ln for ln in capfd.readouterr().err.splitlines()
        if ln.startswith("[blog] politiķu saites")
    ]
    assert len(lines) == 1
    assert "4 / 4 / 4 (listed / resolved / linked)" in lines[0]


def test_grouped_day_query_matches_skeleton_predicate(db_path):
    """Grupētais vaicājums = skeleta `_BRIEF_DAY_CLAIM_SQL` katrai dienai.

    Kļūme: predikāts mainās vienā vietā, otra paliek — saites klusi aizslīd no
    tā, ko pārskats aptver. Rinda «jau pārskatā» (pārskats rakstīts PĒC pozīcijas
    ielādes) un rinda ārpus 7 dienu loga ir zari, ko viegli pazaudēt.
    """
    from src.briefs import brief_day_politician_ids

    db = get_db(db_path)
    briefed = _pid(db, "Jau Pārskatā")
    too_old = _pid(db, "Par Vecu")
    _claim(db, briefed, "2031-10-22", DAY)
    db.execute(
        "INSERT INTO context_notes (topic, note_type, content, created_at) "
        "VALUES (?, 'daily_brief', 'x', '2031-10-24 23:00:00')",
        (f"{DAILY_BRIEF_TOPIC_PREFIX}2031-10-22",),
    )
    _claim(db, too_old, "2031-10-01", DAY)
    db.commit()

    contra_only = {r[0] for r in db.execute("SELECT opponent_id FROM contradictions")}
    grouped = brief_day_politician_ids(db)
    seen = 0
    for day in ("2031-10-01", EARLIER, "2031-10-22", DAY):
        expected = {r[0] for r in db.execute(
            f"SELECT c.opponent_id FROM claims c WHERE {_BRIEF_DAY_CLAIM_SQL} "
            "AND c.claim_type = 'position'",
            _brief_day_params(day),
        )}
        assert grouped.get(day, set()) - contra_only == expected, day
        seen += len(expected)
    assert seen >= 5  # vārti nav tukši: katrs zars tiešām devis rindas
    db.close()
