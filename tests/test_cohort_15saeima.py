from scripts.cohort_15saeima import ascii_fold, build_cohort, is_female, make_role


def test_ascii_fold_strips_latvian_diacritics():
    assert ascii_fold("Ļubova Švecova") == "Lubova Svecova"
    assert ascii_fold("Pēteris Dimants") == "Peteris Dimants"


def test_is_female_by_first_name_ending():
    assert is_female("Līga") and is_female("Nellija") and is_female("Inna")
    assert not is_female("Jānis") and not is_female("Andris")


def test_role_gender_and_no_premature_deputy_title():
    assert make_role("AS", "Vidzeme", False) == "15. Saeimā ievēlēts — AS, Vidzeme"
    assert make_role("PRO", "Rīga", True) == "15. Saeimā ievēlēta — PRO, Rīga"
    assert "deputāt" not in make_role("NA", "Latgale", False)


def test_build_skips_tracked_and_maps_party_by_list_number():
    calc = {"elected": [
        {"name": "Krista Burāne", "region": "Rīga", "pos": 6, "score": 1, "list_nr": 14, "rank": 6},
        {"name": "Andris Kulbergs", "region": "Rīga", "pos": 1, "score": 1, "list_nr": 7, "rank": 1},
    ]}
    rows = build_cohort(calc, tracked_names={"Andris Kulbergs"})
    assert [r["name"] for r in rows] == ["Krista Burāne"]
    r = rows[0]
    assert r["party"] == "Progresīvie" and r["female"] is True
    assert r["name_forms"] == ["Krista Burāne", "Burāne", "Krista Burane", "Burane"]


def test_homonym_is_documented_not_guarded():
    # homonym_of ir dokumentācija operatoram; formas tās pašas kā visiem,
    # jo matcher kailo uzvārdu pievieno pats (Global Constraints).
    calc = {"elected": [{"name": "Eduards Zivtiņš", "region": "Vidzeme", "pos": 20,
                         "score": 1, "list_nr": 8, "rank": 2}]}
    r = build_cohort(calc, tracked_names=set())[0]
    assert r["homonym_of"] == 153
    assert r["name_forms"] == ["Eduards Zivtiņš", "Zivtiņš", "Eduards Zivtins", "Zivtins"]


# --- Task 2: sadursmju priekšskatījums + SQL izvade -------------------------
from scripts.cohort_15saeima import emit_sql, existing_name_collisions, preview_rows  # noqa: E402


def test_preview_reports_denominator_and_shared_form():
    rows = [{"name": "Nellija Kleinberga", "surname": "Kleinberga", "name_forms":
             ["Nellija Kleinberga"], "homonym_of": 5}]
    existing = {5: ["Kleinbergs", "Kleinberga", "Kleinbergam"]}
    docs = ["Kleinberga paziņoja", "Nellija Kleinberga sacīja", "cits teksts"]
    out = preview_rows(rows, existing, docs)
    k = [r for r in out if r["form"] == "Kleinberga"][0]
    assert k["shared_with"] == [5] and k["hits"] == 2
    assert all("docs_scanned" in r and r["docs_scanned"] == 3 for r in out)


def test_preview_flags_short_forms():
    rows = [{"name": "Anete Biķe", "surname": "Biķe", "name_forms": ["Anete Biķe", "Biķe"],
             "homonym_of": None}]
    out = preview_rows(rows, {}, [])
    assert {r["form"] for r in out if r["short"]} >= {"Biķe", "Biķi"}


def test_emit_sql_is_idempotent_and_rollback_deletes_by_name():
    rows = [{"name": "Krista Burāne", "name_forms": ["Krista Burāne", "Burāne"],
             "party": "Progresīvie", "role": "15. Saeimā ievēlēta — PRO, Rīga",
             "x_handle": "kburane"}]
    fwd, rb = emit_sql(rows)
    assert "WHERE NOT EXISTS (SELECT 1 FROM tracked_politicians WHERE name = 'Krista Burāne')" in fwd
    assert "INSERT INTO social_accounts" in fwd and "'first_party'" in fwd
    assert "DELETE FROM tracked_politicians WHERE name = 'Krista Burāne'" in rb
    assert rb.index("DELETE FROM social_accounts") < rb.index("DELETE FROM tracked_politicians")


def test_name_guard_catches_diacritic_and_spacing_variants():
    # Rollback dzēš pēc name: ja kohortas vārds jau ir DB (arī ASCII vai ar
    # dubultatstarpi), WHERE NOT EXISTS to izlaistu un rollback izdzēstu
    # SVEŠU rindu. Sargs salīdzina salocītus vārdus, ne precīzas virknes.
    rows = [{"name": "Dana Šlesere"}, {"name": "Nellija Kleinberga"}, {"name": "Krista Burāne"}]
    existing = ["Dana Slesere", "Nellija  Kleinberga", "Ainārs Šlesers"]
    hits = existing_name_collisions(rows, existing)
    assert sorted(h[0] for h in hits) == ["Dana Šlesere", "Nellija Kleinberga"]
    assert existing_name_collisions([{"name": "Krista Burāne"}], existing) == []


# --- Task 2 labojumi: X kontu sargs + run_emit_sql STOP ceļš ------------------
import sqlite3  # noqa: E402
from pathlib import Path  # noqa: E402

from scripts.cohort_15saeima import handle_collisions, run_emit_sql  # noqa: E402

_SCHEMA = Path(__file__).resolve().parent.parent / "src" / "schema.sql"


def _schema_db(path) -> sqlite3.Connection:
    # Pagaidu DB no src/schema.sql (NEKAD produkcija) + runtime migrāciju
    # kolonnas, ko emit_sql INSERT lieto (src/db_migrations.py).
    db = sqlite3.connect(path)
    db.executescript(_SCHEMA.read_text(encoding="utf-8"))
    db.execute("ALTER TABLE tracked_politicians ADD COLUMN x_handle TEXT")
    db.execute("ALTER TABLE social_accounts ADD COLUMN feed_type TEXT DEFAULT 'first_party'")
    return db


def _row(name, handle):
    return {"name": name, "name_forms": [name], "party": "P", "role": "r", "x_handle": handle}


def test_handle_guard_is_case_insensitive_across_both_tables_and_cohort():
    rows = [_row("Krista Burāne", "kburane"), _row("Anete Biķe", "AneteBike"),
            _row("Cits Deputāts", "@aneteBIKE"), _row("Bez Konta", None)]
    existing = [("social_accounts.handle", 7, "KBurane"),
                ("tracked_politicians.x_handle", 9, "@ANETEBIKE"),
                ("social_accounts.handle", 8, "kaut_kas_cits")]
    hits = handle_collisions(rows, existing)
    assert len(hits) == 3
    assert any("Cits Deputāts" in h and "kohortā jau 'Anete Biķe'" in h for h in hits)
    assert any("pid=7" in h and "Krista Burāne" in h for h in hits)
    assert any("pid=9" in h and "Anete Biķe" in h for h in hits)
    assert handle_collisions([_row("Krista Burāne", "kburane")],
                             [("social_accounts.handle", 8, "kaut_kas_cits")]) == []


def test_emit_sql_does_not_duplicate_case_variant_handle():
    # Pat ja sargs tiktu apiets, SQL NOT EXISTS salīdzina bez reģistra.
    db = _schema_db(":memory:")
    db.execute("INSERT INTO social_accounts (opponent_id, platform, handle) "
               "VALUES (999, 'twitter', 'KBurane')")
    fwd, _ = emit_sql([_row("Krista Burāne", "kburane")])
    db.executescript(fwd)
    assert db.execute("SELECT COUNT(*) FROM social_accounts "
                      "WHERE lower(handle) = 'kburane'").fetchone()[0] == 1


def test_run_emit_sql_stops_on_folded_name_collision(tmp_path, capsys):
    db_path = tmp_path / "guard.db"
    db = _schema_db(db_path)
    db.execute("INSERT INTO tracked_politicians (name) VALUES ('Dana  Slesere')")
    db.commit()
    db.close()
    out_dir = tmp_path / "out"
    rc = run_emit_sql(db_path, [_row("Dana Šlesere", None)], out_dir, "2026-10-05")
    assert rc == 1 and not out_dir.exists()
    assert "Dana Šlesere" in capsys.readouterr().err


def test_run_emit_sql_stops_on_handle_collision(tmp_path, capsys):
    db_path = tmp_path / "guard.db"
    db = _schema_db(db_path)
    db.execute("INSERT INTO social_accounts (opponent_id, platform, handle) "
               "VALUES (1, 'twitter', 'KBurane')")
    db.commit()
    db.close()
    out_dir = tmp_path / "out"
    rc = run_emit_sql(db_path, [_row("Krista Burāne", "kburane")], out_dir, "2026-10-05")
    assert rc == 1 and not out_dir.exists()
    assert "KBurane" in capsys.readouterr().err
    # Bez sadursmes tas pats ceļš raksta abus failus ar rollback galveni.
    rc = run_emit_sql(db_path, [_row("Krista Burāne", "kburane2")], out_dir, "2026-10-05")
    rb = (out_dir / "rollback_seed_15saeima_2026-10-05.sql").read_text(encoding="utf-8")
    assert rc == 0 and "document_politicians" in rb and "+1 tieši" in rb
