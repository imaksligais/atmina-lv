"""Saeimas summary vārti ir piesaistīti SĒDES datumam, ne glabāšanas brīdim.

Nosauktā kļūme: saeima-tracker Step 5 vecā forma filtrēja
`date(created_at) = date('now', '+3 hours')`. Sēde, kas ielādēta pāri
pusnaktij, sadalījās divās "dienās" — pēc pusnakts saglabātie balsojumi bez
summary pazuda no vārtiem, un tie ziņoja tīru rezultātu. Otrā kļūme:
`LIKE '%/Lp14)%'` pēc 2026-10-03 vēlēšanām (15. Saeima, `/Lp15`) neredzētu
nevienu likumprojektu un saucējs kļūtu 0.
"""
import pytest


@pytest.fixture()
def db(tmp_path):
    from src.db import get_db, init_db
    from src.saeima.schema import init_saeima_bills, init_saeima_tables

    db_path = str(tmp_path / "t.db")
    init_db(db_path)
    init_saeima_tables(db_path)
    init_saeima_bills(db_path)
    conn = get_db(db_path)
    rows = [
        # Sēde 2026-09-24: viens balsojums saglabāts pirms pusnakts ar summary,
        # otrs PĒC pusnakts bez summary — tieši tas, ko vecā forma pazaudēja.
        (1, "Grozījumi likumā (1001/Lp14)", "2026-09-24", "10:00:00", "u1",
         "Kopsavilkums.", "2026-09-24 23:50:00"),
        (2, "Jauns likums (12/Lp15)", "2026-09-24", "11:00:00", "u2",
         None, "2026-09-25 00:10:00"),
        # Lēmuma projekts (/Lm) — sargā `L[pm]` daļu paternā.
        (5, "Lēmuma projekts (340/Lm15)", "2026-09-24", "11:02:00", "u5",
         None, "2026-09-25 00:10:30"),
        # Procedurāls balsojums bez likumprojekta numura — nav saucējā.
        (3, "Par darba kārtības grozījumu", "2026-09-24", "11:05:00", "u3",
         None, "2026-09-25 00:11:00"),
        # Citas sēdes likumprojekts, glabāts tajā pašā kalendāra dienā kā #2 —
        # nedrīkst ieskaitīties 2026-09-24 sēdē.
        (4, "Grozījumi likumā (77/Lm14)", "2026-09-25", "09:00:00", "u4",
         None, "2026-09-25 00:20:00"),
    ]
    for r in rows:
        conn.execute(
            "INSERT INTO saeima_votes (id, motif, vote_date, vote_time, url, summary,"
            " created_at) VALUES (?,?,?,?,?,?,?)", r)
    conn.commit()
    yield conn
    conn.close()


def test_gate_sees_votes_stored_after_midnight(db):
    from src.saeima.votes import bill_votes_missing_summary
    checked, missing = bill_votes_missing_summary(db, "2026-09-24")
    assert checked == 3
    assert missing == [(2, "Jauns likums (12/Lp15)"), (5, "Lēmuma projekts (340/Lm15)")]


def test_empty_day_has_zero_denominator(db):
    from src.saeima.votes import bill_votes_missing_summary
    assert bill_votes_missing_summary(db, "2026-09-23") == (0, [])


def test_prompts_do_not_hand_roll_the_summary_gate():
    """Promptu summary vārti iet caur bill_votes_missing_summary(), nevis pašu SQL.

    `/saeima-ingest` vārti (a) līdz 2026-09-25 bija `summary IS NULL AND motif
    LIKE '%/Lp14)%'` — bez saucēja un piesaistīti 14. sasaukumam: pēc 15. Saeimas
    sanākšanas tie atrastu 0 rindu un ziņotu tīru rezultātu.
    """
    from pathlib import Path
    root = Path(__file__).resolve().parent.parent
    prompts = [*root.glob(".claude/agents/*.md"), *root.glob(".claude/commands/*.md")]
    assert len(prompts) >= 10
    hits = [f"{p.name}:{i}"
            for p in prompts
            for i, line in enumerate(p.read_text(encoding="utf-8").splitlines(), 1)
            if "summary IS NULL" in line or "Lp14)%" in line or "Lm14)%" in line]
    assert not hits, "pašrakstīti summary vārti promptos:\n" + "\n".join(hits)
    users = [p.name for p in prompts
             if "bill_votes_missing_summary" in p.read_text(encoding="utf-8")]
    assert {"saeima-tracker.md", "saeima-ingest.md"} <= set(users)
    petition_users = [p.name for p in prompts
                      if "petition_votes_polarity" in p.read_text(encoding="utf-8")]
    assert {"saeima-tracker.md", "saeima-ingest.md"} <= set(petition_users)
