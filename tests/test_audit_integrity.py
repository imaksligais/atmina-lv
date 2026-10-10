"""`scripts/audit_integrity.py` — `/audit-integrity` pārbaužu reģistra testi.

KĀPĒC. Līdz 2026-09-30 pārbaudes dzīvoja tikai kā prompta teksts, un nekas
nepierādīja, ka tās var nokrist (CLAUDE.md «A gate that cannot fail is not
evidence»). Trīs no tām kādreiz ziņoja pārliecinošu «tīrs», būdamas strukturāli
nespējīgas nostrādāt: 2. (NULL-akls `LOWER(a)<>LOWER(b)`, 7 rindas mēnešiem),
7. (skenēja disku→DB, kopā bija viens fails), 11. (atslēgu, ne rindu
salīdzinājums — 14. to redz). Tāpēc katrai vārtu pārbaudei šeit ir trīs
gadījumi: tīra rinda → `flagged=0` un `checked>0`; iesēts defekts →
`flagged≥1`; tukša tabula → izejas kods 2 (salauzts saucējs, ne «tīrs»).

Hermētiski: DB tiek būvēta testā (minimālas kolonnas), ražošanas DB nekad
netiek aiztikta (tests/conftest.py § 4).
"""
from __future__ import annotations

import hashlib
import json
import sqlite3
from pathlib import Path

import pytest

import scripts.audit_integrity as ai
from src.db import _float_list_to_bytes, lv_cutoff, now_lv

SCHEMA = """
CREATE TABLE tracked_politicians (id INTEGER PRIMARY KEY, name TEXT, name_forms TEXT,
    relationship_type TEXT, party TEXT, role TEXT, x_handle TEXT, negative_patterns TEXT);
CREATE TABLE social_accounts (id INTEGER PRIMARY KEY, opponent_id INTEGER, platform TEXT, handle TEXT);
CREATE TABLE contradictions (id INTEGER PRIMARY KEY, opponent_id INTEGER, claim_old_id INTEGER,
    claim_new_id INTEGER, reviewed INTEGER DEFAULT 0, confirmed INTEGER DEFAULT 0, detected_at TEXT);
CREATE TABLE claims (id INTEGER PRIMARY KEY, opponent_id INTEGER, document_id INTEGER, topic TEXT,
    stance TEXT, quote TEXT, reasoning TEXT, source_url TEXT, stated_at TEXT, created_at TEXT,
    claim_type TEXT DEFAULT 'position', review_status TEXT, review_status_at TEXT);
CREATE TABLE documents (id INTEGER PRIMARY KEY, content TEXT, platform TEXT, source_url TEXT,
    scraped_at TEXT, word_count INTEGER, reviewed_at TEXT);
CREATE TABLE document_politicians (document_id INTEGER, politician_id INTEGER, role TEXT);
CREATE TABLE brief_images (id INTEGER PRIMARY KEY, note_id INTEGER, image_path TEXT, approved INTEGER);
CREATE TABLE context_notes (id INTEGER PRIMARY KEY, topic TEXT, note_type TEXT, created_at TEXT);
CREATE TABLE political_tensions (id INTEGER PRIMARY KEY, source_url TEXT, created_at TEXT);
CREATE TABLE analyses (id INTEGER PRIMARY KEY, created_at TEXT);
CREATE TABLE saeima_votes (id INTEGER PRIMARY KEY, vote_date TEXT, url TEXT);
CREATE TABLE saeima_individual_votes (id INTEGER PRIMARY KEY AUTOINCREMENT, vote_id INTEGER,
    politician_id INTEGER, faction TEXT, vote TEXT);
CREATE TABLE parties (id INTEGER PRIMARY KEY, name TEXT, short_name TEXT);
CREATE TABLE claim_vectors (claim_id INTEGER PRIMARY KEY, embedding BLOB);
"""


def _mkdb(tmp_path: Path, sql: str = "", params: list[tuple[str, tuple]] = ()) -> str:
    path = tmp_path / "audit.db"
    db = sqlite3.connect(path)
    db.executescript(SCHEMA + sql)
    for stmt, args in params:
        db.execute(stmt, args)
    db.commit()
    db.close()
    return str(path)


def _run(path: str, num: str, **ctx_kw) -> ai.CheckResult:
    db = ai.connect_ro(path)
    try:
        return ai.CHECKS[num](ai.Ctx(db=db, db_path=path, **ctx_kw))
    finally:
        db.close()


def _exit(path: str, only: str, tmp_path: Path) -> int:
    return ai.main(["--db", path, "--only", only, "--output-root", str(tmp_path / "out")])


def _old(days: int) -> str:
    return lv_cutoff(days)


# --- 2. x_handle ↔ social_accounts -------------------------------------------

_POL2 = "INSERT INTO tracked_politicians (id, name, relationship_type, x_handle) VALUES "


def test_check2_clean_row_has_denominator(tmp_path):
    path = _mkdb(tmp_path, _POL2 + "(5, 'A B', 'tracked', 'ab');"
                 "INSERT INTO social_accounts VALUES (1, 5, 'twitter', 'AB');")
    r = _run(path, "2")
    assert (r.checked, r.flagged) == (1, 0)


def test_check2_null_x_handle_with_live_account_is_flagged(tmp_path):
    """Klase, kas 2026-08-23 sēdēja nereportēta: `x_handle IS NULL` un dzīvs
    `social_accounts` konts. Kails `LOWER(a)<>LOWER(b)` to nekad neredz
    (NULL salīdzinājums ir NULL) — profila lapā trūkst X saites."""
    path = _mkdb(tmp_path, _POL2 + "(5, 'A B', 'tracked', NULL);"
                 "INSERT INTO social_accounts VALUES (1, 5, 'twitter', 'AB');")
    r = _run(path, "2")
    assert (r.checked, r.flagged) == (1, 1)
    assert r.extra["NULL klase"] == 1
    assert r.status() == 1


def test_check2_value_mismatch_is_flagged(tmp_path):
    """Svirska klase (id 62): abi lauki aizpildīti, bet norāda uz dažādiem kontiem."""
    path = _mkdb(tmp_path, _POL2 + "(5, 'A B', 'tracked', 'ESvirskis');"
                 "INSERT INTO social_accounts VALUES (1, 5, 'twitter', 'realNepareizais');")
    assert _run(path, "2").extra["vērtību nesakritība"] == 1


def test_check2_accepted_id_27_does_not_fail_the_run(tmp_path):
    """Bordāns (id 27, inactive) ir apzināti NULL — pieņemts, `new=0`, exit 0."""
    path = _mkdb(tmp_path, _POL2 + "(27, 'Jānis Bordāns', 'inactive', NULL);"
                 "INSERT INTO social_accounts VALUES (1, 27, 'twitter', 'JBordans');")
    r = _run(path, "2")
    assert (r.flagged, r.new, r.status()) == (1, 0, 0)


def test_check2_empty_join_is_broken_not_clean(tmp_path):
    """`0 | 0 | 0` nozīmē, ka salūza JOIN, ne ka dati ir tīri."""
    path = _mkdb(tmp_path)
    assert _exit(path, "2", tmp_path) == 2


# --- 3. Bāreņi ----------------------------------------------------------------

def test_check3_resolving_refs_are_clean_and_dangling_is_flagged(tmp_path):
    """Pretruna, kuras `claim_old_id` norāda uz dzēstu claim, publicētā lapā
    rāda caurumu; pieņemtā #27 (atsaukta, vecā pozīcija dzēsta) nekrīt."""
    base = ("INSERT INTO claims (id) VALUES (1), (2);"
            "INSERT INTO contradictions (id, claim_old_id, claim_new_id) VALUES (10, 1, 2);")
    r = _run(_mkdb(tmp_path, base), "3")
    assert (r.checked, r.flagged) == (1, 0)
    (tmp_path / "audit.db").unlink()
    r = _run(_mkdb(tmp_path, base + "INSERT INTO contradictions (id, claim_old_id, claim_new_id) "
                   "VALUES (11, 999, 2), (27, NULL, 2);"), "3")
    assert (r.checked, r.flagged, r.new) == (3, 2, 1)
    assert r.accepted == [27]


def test_check3_empty_is_broken(tmp_path):
    assert _exit(_mkdb(tmp_path), "3", tmp_path) == 2


# --- 4. Novecojušas rindas ----------------------------------------------------

def test_check4_fresh_queue_is_clean(tmp_path):
    path = _mkdb(tmp_path, params=[
        ("INSERT INTO contradictions (id, reviewed, confirmed, detected_at) VALUES (1, 0, 0, ?)",
         (now_lv(),)),
        ("INSERT INTO claims (id, reasoning, review_status, created_at) VALUES "
         "(1, 'NEEDS_REVIEW: x', 'needs_review', ?)", (now_lv(),)),
    ])
    r = _run(path, "4")
    assert (r.checked, r.flagged) == (2, 0)


def test_check4_aged_from_marker_not_claim(tmp_path):
    """2026-08-22: retro-marķēšana ielika vecus claims rindā, un `created_at`
    vārti uzreiz ziņoja «pārkāpumu». Vecums skaitās no `review_status_at`."""
    path = _mkdb(tmp_path, params=[
        ("INSERT INTO claims (id, reasoning, review_status, created_at, review_status_at) "
         "VALUES (1, 'NEEDS_REVIEW: x', 'needs_review', ?, ?)", (_old(60), now_lv())),
        ("INSERT INTO claims (id, reasoning, review_status, created_at, review_status_at) "
         "VALUES (2, 'NEEDS_REVIEW: y', 'needs_review', ?, ?)", (_old(60), _old(20))),
    ])
    r = _run(path, "4")
    assert r.flagged == 1
    assert [x["id"] for x in r.rows] == [2]


def test_check4_matches_open_review_queue(tmp_path):
    """Vārtu forma dzīvo `src.db.open_review_queue()`; reģistrs to atkārto uz ro
    savienojuma. Ja abas kādreiz atšķirsies, audits un @quality-reviewer
    ziņos dažādas rindas — šis tests to aizliedz."""
    from src.db import REVIEW_QUEUE_AGE_DAYS, open_review_queue

    path = _mkdb(tmp_path, params=[
        ("INSERT INTO claims (id, reasoning, review_status, created_at) VALUES "
         "(?, 'NEEDS_REVIEW', 'needs_review', ?)", (i, _old(d)))
        for i, d in enumerate((1, 13, 15, 40), start=1)
    ])
    canonical = sorted(r["id"] for r in open_review_queue(path) if r["age_days"] > REVIEW_QUEUE_AGE_DAYS)
    r = _run(path, "4")
    assert sorted(x["id"] for x in r.rows) == canonical == [3, 4]


def test_check4_unreviewed_contradiction_and_trigger_desync(tmp_path):
    """reviewed=0 >14 d ir rindas parāds; `reviewed=1 confirmed=0` ir dokumentēts
    noraidījums (#40 Judins) un NEDRĪKST karoties. Sanity rinda ≠ 0 = trigeri
    vairs nedarbojas."""
    path = _mkdb(tmp_path, params=[
        ("INSERT INTO contradictions (id, reviewed, confirmed, detected_at) VALUES (1, 0, 0, ?)", (_old(20),)),
        ("INSERT INTO contradictions (id, reviewed, confirmed, detected_at) VALUES (40, 1, 0, ?)", (_old(60),)),
        ("INSERT INTO claims (id, reasoning, review_status, created_at) VALUES "
         "(1, 'NEEDS_REVIEW: x', 'reviewed', ?)", (now_lv(),)),
    ])
    r = _run(path, "4")
    assert r.extra["trigeru sanity"] == 1
    assert {x["id"] for x in r.rows if x["id"]} == {1}
    assert r.flagged == 2


def test_check4_sanity_sees_null_status_beside_marker(tmp_path):
    """Trigeri pārstāj rakstīt kolonnu → `review_status` paliek NULL pie
    `NEEDS_REVIEW` marķiera. Agrākā forma `(status='needs_review') != (reasoning
    LIKE …)` NULL gadījumā atgrieza NULL un šo rindu neskaitīja — tieši tā
    trigeru atteice, ko sanity rinda pastāv, lai noķertu."""
    path = _mkdb(tmp_path, params=[
        ("INSERT INTO claims (id, reasoning, review_status, created_at) VALUES "
         "(1, 'NEEDS_REVIEW: x', NULL, ?)", (now_lv(),)),
        ("INSERT INTO claims (id, reasoning, review_status, created_at) VALUES "
         "(2, 'parasts pamatojums', NULL, ?)", (now_lv(),)),
    ])
    assert _run(path, "4").extra["trigeru sanity"] == 1


def test_check4_sanity_follows_trigger_glob_not_like(tmp_path):
    """Trigeris lieto reģistrjutīgu `GLOB` (CLAUDE.md: prozas «needs_review»
    neatzīmē rindu). `LIKE` ir reģistrnejutīgs un šādu rindu kļūdaini sauktu par
    trigeru desinhronizāciju."""
    path = _mkdb(tmp_path, params=[
        ("INSERT INTO claims (id, reasoning, review_status, created_at) VALUES "
         "(1, 'aģents minēja needs_review prozā', NULL, ?)", (now_lv(),)),
    ])
    assert _run(path, "4").extra["trigeru sanity"] == 0


def test_check4_buckets_use_lv_clock(tmp_path):
    """Kolonnas ir LV laikā; `julianday('now')` ir UTC. Rinda, kas marķēta tieši
    pirms 7 d un 2 h (LV), pēc UTC pulksteņa ir tikai ~6 d 23 h veca un krīt
    nepareizajā grozā (T17)."""
    from datetime import datetime, timedelta

    stamp = (datetime.strptime(now_lv(), "%Y-%m-%d %H:%M:%S")
             - timedelta(days=7, hours=2)).strftime("%Y-%m-%d %H:%M:%S")
    path = _mkdb(tmp_path, params=[
        ("INSERT INTO claims (id, reasoning, review_status, created_at, review_status_at) VALUES "
         "(1, 'NEEDS_REVIEW: x', 'needs_review', ?, ?)", (stamp, stamp)),
    ])
    assert _run(path, "4").extra["sadalījums"] == {"8-14d": 1}


def test_check4_empty_is_broken(tmp_path):
    assert _exit(_mkdb(tmp_path), "4", tmp_path) == 2


# --- 5. Partijas maiņas valoda ------------------------------------------------

def _claim5(stance: str, when: str) -> tuple[str, tuple]:
    return ("INSERT INTO claims (opponent_id, topic, stance, reasoning, stated_at) VALUES "
            "(1, 'Koalīcija un partijas', ?, '', ?)", (stance, when))


def test_check5_exit_language_mid_sentence_is_flagged(tmp_path):
    """T6: pozīcija saka «izstājas no partijas», bet `party` paliek vecs. Valoda
    ir teikuma VIDŪ — prefiksa `LIKE 'izstāj%'` to neredzētu nekad."""
    pol = "INSERT INTO tracked_politicians (id, name, party) VALUES (1, 'A B', 'JV');"
    r = _run(_mkdb(tmp_path, pol, [_claim5("Paziņo, ka nekavējoties izstājas no partijas", now_lv()),
                                   _claim5("Atbalsta koalīcijas līgumu", now_lv())]), "5")
    assert (r.checked, r.flagged) == (2, 1)


def test_check5_clean_and_old_rows_outside_window(tmp_path):
    pol = "INSERT INTO tracked_politicians (id, name, party) VALUES (1, 'A B', 'JV');"
    r = _run(_mkdb(tmp_path, pol, [_claim5("Atbalsta koalīciju", now_lv()),
                                   _claim5("izstājas", _old(40))]), "5")
    assert (r.checked, r.flagged) == (1, 0)


def test_check5_empty_is_broken(tmp_path):
    assert _exit(_mkdb(tmp_path), "5", tmp_path) == 2


# --- 7. Attēlu varianti -------------------------------------------------------

def _images(root: Path, stem: str, variants=("hero", "card", "thumb", "og")) -> None:
    from src.image_variants import variant_filename

    d = root / "images" / "briefs"
    d.mkdir(parents=True, exist_ok=True)
    for v in variants:
        (d / variant_filename(f"{stem}.png", v)).write_bytes(b"x")


def test_check7_all_variants_present_is_clean(tmp_path):
    root = tmp_path / "out"
    _images(root, "ok")
    path = _mkdb(tmp_path, "INSERT INTO brief_images VALUES (1, 1, 'atmina/images/briefs/ok.png', 1);")
    r = _run(path, "7", output_root=root)
    assert (r.checked, r.flagged) == (1, 0)


def test_check7_approved_row_without_variants_is_flagged(tmp_path):
    """2026-08-02: #93/#96 bija `approved=1`, bet hero/og 404 dzīvajā lapā, kamēr
    vecā disks→DB skenēšana ziņoja «tīrs» (kopā bija viens PNG ar savu
    `-hero.webp`). Virziens DB→disks redz rindu, kurai uz diska nav nekā."""
    root = tmp_path / "out"
    _images(root, "decoy", variants=("hero",))
    (root / "images" / "briefs" / "decoy.png").write_bytes(b"x")
    _images(root, "ok")
    path = _mkdb(tmp_path, "INSERT INTO brief_images VALUES (1, 1, 'atmina/images/briefs/ok.png', 1);"
                 "INSERT INTO brief_images VALUES (93, 5, 'atmina/images/briefs/dead.png', 1);"
                 "INSERT INTO brief_images VALUES (94, 6, 'atmina/images/briefs/retired.png', 2);")
    r = _run(path, "7", output_root=root)
    assert (r.checked, r.flagged) == (2, 1)
    assert r.rows[0]["id"] == 93
    assert r.extra["approved sadalījums"] == {1: 2, 2: 1}


def test_check7_empty_is_broken(tmp_path):
    assert _exit(_mkdb(tmp_path), "7", tmp_path) == 2


# --- 9. Partija ↔ frakcija ----------------------------------------------------

def _faction_db(tmp_path, pid: int, party: str, labels: list[str]) -> str:
    sql = ("INSERT INTO parties VALUES (1, 'Jaunā Vienotība', 'JV'), (2, 'Stabilitātei!', 'ST');"
           f"INSERT INTO tracked_politicians (id, name, party, relationship_type) "
           f"VALUES ({pid}, 'X Y', '{party}', 'tracked');")
    params = []
    for i, lab in enumerate(labels, start=1):
        params.append(("INSERT INTO saeima_votes VALUES (?, '2026-04-01', ?)", (i, f"u{i}")))
        params.append(("INSERT INTO saeima_individual_votes (vote_id, politician_id, faction, vote) "
                       "VALUES (?, ?, ?, 'Par')", (i, pid, lab)))
    return _mkdb(tmp_path, sql, params)


def test_check9_party_matching_faction_is_clean(tmp_path):
    r = _run(_faction_db(tmp_path, 1, "Jaunā Vienotība", ["JV"] * 9 + ["ST"]), "9")
    assert (r.checked, r.flagged) == (1, 0)


def test_check9_party_wrong_from_seeding_is_flagged(tmp_path):
    """Šmita klase (2026-07-26): `party='Stabilitātei!'` pret 1 668 AS balsīm —
    nepareizs no sēšanas dienas, tāpēc 5. pārbaudes valoda to nekad neredz."""
    r = _run(_faction_db(tmp_path, 150, "Stabilitātei!", ["JV"] * 9 + ["ST"]), "9")
    assert (r.checked, r.flagged, r.new) == (1, 1, 1)


def test_check9_accepted_genuine_switch_does_not_fail(tmp_path):
    """Ceļapīters (145) tiešām pārgāja — karosies katrā skrējienā, `party` pareizs."""
    r = _run(_faction_db(tmp_path, 145, "Jaunā Vienotība", ["ST"] * 9 + ["JV"]), "9")
    assert (r.flagged, r.new, r.status()) == (1, 0, 0)


def test_check9_party_never_seen_as_label_is_skipped_and_empty_is_broken(tmp_path):
    """Alianses un ne-Saeimas partijas klusē pēc konstrukcijas — tās nav
    saucējā, un saucējs 0 ir salauzti vārti."""
    path = _faction_db(tmp_path, 1, "Latvijas Zaļā partija", ["JV"] * 3)
    r = _run(path, "9")
    assert r.checked == 0
    assert _exit(path, "9", tmp_path) == 2


# --- 10. Provenance -----------------------------------------------------------

def test_check10_clean_and_tension_citing_unknown_url(tmp_path):
    """`political_tensions` #175 (2026-07-30): raw INSERT ar tvīta ID, kas nav
    nevienā dokumentā, nonāca publicētā pārskatā. A zars to redz."""
    base = ("INSERT INTO documents (id, source_url) VALUES (1, 'u1');"
            "INSERT INTO political_tensions VALUES (1, 'u1', '2026-01-01 10:00:00');"
            "INSERT INTO claims (id, document_id, source_url, claim_type) VALUES (1, 1, 'u1', 'position');")
    r = _run(_mkdb(tmp_path, base), "10")
    assert r.checked > 0 and r.flagged == 0
    (tmp_path / "audit.db").unlink()
    r = _run(_mkdb(tmp_path, base + "INSERT INTO political_tensions VALUES (175, 'x.com/s/999', "
                   "'2026-01-01 10:00:00');"), "10")
    assert r.flagged == 1 and r.rows[0]["klase"] == "A"


def test_check10_claim_url_mismatch_vote_url_and_lv_stamp_in_utc_column(tmp_path):
    """B: claim cita citu URL nekā savs dokuments; C: balsojuma claim bez
    `saeima_votes.url`; D: LV laiks UTC kolonnā (tās pašas sesijas slazds)."""
    from datetime import datetime, timezone

    now = datetime(2026, 9, 30, 12, 0, 0, tzinfo=timezone.utc)
    path = _mkdb(tmp_path, "INSERT INTO documents (id, source_url) VALUES (1, 'u1');"
                 "INSERT INTO claims (id, document_id, source_url, claim_type) VALUES (1, 1, 'OTHER', 'position');"
                 "INSERT INTO claims (id, source_url, claim_type) VALUES (2, 'vote-x', 'saeima_vote');"
                 "INSERT INTO analyses VALUES (1, '2026-09-30 14:30:00');")
    r = _run(path, "10", now_utc=now)
    assert sorted(x["klase"] for x in r.rows) == ["B", "C", "D"]


def test_check10_empty_is_broken(tmp_path):
    assert _exit(_mkdb(tmp_path), "10", tmp_path) == 2


# --- 11. Trijnieku delta ------------------------------------------------------

def test_check11_clean_and_duplicate_triple(tmp_path):
    """2026-08-02: divas `UPDATE claims SET topic` migrācijas SAPLUDINĀJA 4 087
    trijniekus, ko `store_claim()` nekad nepieņemtu."""
    ins = "INSERT INTO claims (opponent_id, source_url, topic, claim_type) VALUES (1, 'v1', 'T', 'saeima_vote');"
    r = _run(_mkdb(tmp_path, ins), "11")
    assert (r.checked, r.flagged) == (1, 0)
    (tmp_path / "audit.db").unlink()
    r = _run(_mkdb(tmp_path, ins * 2), "11")
    assert (r.checked, r.flagged) == (2, 1)


def test_check11_null_source_url_is_not_a_duplicate(tmp_path):
    """`||` ar NULL dod NULL, `COUNT(DISTINCT)` to izlaiž, un katra rinda ar NULL
    `source_url` agrāk parādījās kā delta — dublikāts, kura nav."""
    ins = ("INSERT INTO claims (opponent_id, source_url, topic, claim_type) VALUES "
           "(1, NULL, 'T', 'saeima_vote'), (1, 'v1', 'T', 'saeima_vote');")
    r = _run(_mkdb(tmp_path, ins), "11")
    assert (r.checked, r.flagged) == (2, 0)


def test_check11_empty_is_broken(tmp_path):
    assert _exit(_mkdb(tmp_path), "11", tmp_path) == 2


# --- 14. Claims pa balsojumiem ------------------------------------------------

def _vote_db(tmp_path, n_claims: int, ballots=("Par", "Pret")) -> str:
    params = [("INSERT INTO saeima_votes VALUES (1, '2026-03-26', 'v1')", ())]
    for i, b in enumerate(ballots, start=1):
        params.append(("INSERT INTO saeima_individual_votes (vote_id, politician_id, vote) "
                       "VALUES (1, ?, ?)", (i, b)))
    params.append(("INSERT INTO saeima_individual_votes (vote_id, politician_id, vote) "
                   "VALUES (1, 99, 'Reģistrējies')", ()))
    for i in range(n_claims):
        params.append(("INSERT INTO claims (opponent_id, source_url, topic, claim_type) "
                       "VALUES (?, 'v1', ?, 'saeima_vote')", (i, f"T{i}")))
    return _mkdb(tmp_path, params=params)


def test_check14_one_claim_per_cast_ballot_is_clean(tmp_path):
    """Datu kontrakts #4b: `Reģistrējies` nav balss un nav claim."""
    r = _run(_vote_db(tmp_path, 2), "14")
    assert (r.checked, r.flagged) == (1, 0)


def test_check14_vote_loaded_twice_is_flagged_at_ratio_2(tmp_path):
    """2026-05-27: P3 pārlāde uzrakstīja otru pilnu claim kopu 46 balsojumiem ar
    ATŠĶIRĪGĀM tēmām — 11. pārbaude to neredzēja trīs mēnešus, šī redz tajā
    pašā dienā (attiecība tieši 2.0)."""
    r = _run(_vote_db(tmp_path, 4), "14")
    assert (r.checked, r.flagged) == (1, 1)
    assert r.rows[0]["ratio"] == 2.0
    assert r.extra["dubultoti (2.0)"] == 1


def test_check14_partial_write_is_flagged_below_1(tmp_path):
    """`store_vote()` commit pirms claim ģenerēšanas: nepareizs interpretators
    (2026-07-25, 20 rindas) atstāj balsojumu bez claims."""
    r = _run(_vote_db(tmp_path, 1), "14")
    assert r.extra["missing (<1.0)"] == 1


def test_check14_empty_is_broken(tmp_path):
    assert _exit(_mkdb(tmp_path), "14", tmp_path) == 2


# --- 16. daily_brief topic ----------------------------------------------------

def test_check16_canonical_clean_and_fifth_form_flagged(tmp_path):
    """Četras formas (`dienas pārskats`, bez diakritikas, kails `daily`) lika
    `LIKE 'dienas analīze %'` redzēt 70 no 119 rindām — klusi."""
    ok = "INSERT INTO context_notes (topic, note_type) VALUES ('dienas analīze 2026-09-29', 'daily_brief');"
    r = _run(_mkdb(tmp_path, ok), "16")
    assert (r.checked, r.flagged) == (1, 0)
    (tmp_path / "audit.db").unlink()
    r = _run(_mkdb(tmp_path, ok + "INSERT INTO context_notes (topic, note_type) VALUES ('daily', 'daily_brief');"), "16")
    assert (r.checked, r.flagged) == (2, 1)


def test_check16_empty_is_broken(tmp_path):
    assert _exit(_mkdb(tmp_path), "16", tmp_path) == 2


# --- 17. Pārskrāpēšanā zudis citāts -------------------------------------------

def _quote_db(tmp_path, cid: int, quote: str, content: str) -> str:
    return _mkdb(tmp_path, params=[
        ("INSERT INTO documents (id, content, platform, scraped_at) VALUES (1, ?, 'web', '2026-09-02 10:00:00')",
         (content,)),
        ("INSERT INTO claims (id, document_id, quote, created_at) VALUES (?, 1, ?, '2026-09-01 10:00:00')",
         (cid, quote)),
    ])


def test_check17_quote_survives_folding_and_typographic_quotes(tmp_path):
    """Diakritikas, tipogrāfisko pēdiņu un atstarpju atšķirības nav zudums."""
    r = _run(_quote_db(tmp_path, 1, "Mēs  „atbalstām” to", "Viņš teica: mes \"atbalstam\" to."), "17")
    assert (r.checked, r.flagged) == (1, 0)


def test_check17_rescrape_that_ate_the_quote_is_flagged(tmp_path):
    """URL-first dedup pārraksta `content` vietā; `check_quote_against_source()`
    šo klasi apzināti palaiž («cannot verify»), tāpēc neviens cits to neredz."""
    r = _run(_quote_db(tmp_path, 900001, "Mēs atbalstām to", "Pavisam cits raksts."), "17")
    assert (r.checked, r.flagged, r.new) == (1, 1, 1)


def test_check17_accepted_id_does_not_fail(tmp_path):
    r = _run(_quote_db(tmp_path, 7481, "Koalīcijas partneri vienojušies", "Cits teksts."), "17")
    assert (r.flagged, r.new, r.status()) == (1, 0, 0)


def test_check17_empty_is_broken(tmp_path):
    assert _exit(_mkdb(tmp_path), "17", tmp_path) == 2


# --- 9b, 13, 18 — adapteri uz esošajiem skriptiem ------------------------------

def test_check9b_adapter_reports_the_blind_zone(tmp_path):
    """pid=224 Melnis: ministrs bez neviena frakcijas etiķetēta balsojuma — 9.
    pārbaude par viņu klusēja divus mēnešus."""
    path = _mkdb(tmp_path, "INSERT INTO tracked_politicians (id, name, party, role, relationship_type) "
                 "VALUES (224, 'R M', 'ZZS', 'Zemkopības ministrs', 'tracked');")
    r = _run(path, "9b")
    assert (r.checked, r.flagged, r.status()) == (1, 1, 1)


def test_check9b_minister_with_labelled_ballots_is_clean(tmp_path):
    path = _mkdb(tmp_path, "INSERT INTO tracked_politicians (id, name, party, role, relationship_type) "
                 "VALUES (1, 'A B', 'JV', 'Tieslietu ministrs', 'tracked');"
                 "INSERT INTO saeima_individual_votes (vote_id, politician_id, faction, vote) VALUES (1, 1, 'JV', 'Par');")
    r = _run(path, "9b")
    assert (r.checked, r.flagged, r.status()) == (1, 0, 0)


def test_check9b_empty_is_broken(tmp_path):
    assert _exit(_mkdb(tmp_path), "9b", tmp_path) == 2


def test_check18_adapter_clean_and_noncanonical(tmp_path):
    from src.topic_map import get_all_group_names

    canon = get_all_group_names()[0]
    ins = f"INSERT INTO claims (topic, claim_type) VALUES ('{canon}', 'position');"
    r = _run(_mkdb(tmp_path, ins), "18")
    assert (r.checked, r.flagged) == (1, 0)
    (tmp_path / "audit.db").unlink()
    r = _run(_mkdb(tmp_path, ins + "INSERT INTO claims (topic, claim_type) VALUES ('Drošības politika', 'position');"), "18")
    assert (r.checked, r.flagged) == (2, 1)


def test_check18_empty_is_broken(tmp_path):
    assert _exit(_mkdb(tmp_path), "18", tmp_path) == 2


def _fake_embed(text: str) -> list[float]:
    return [float(b) for b in hashlib.sha256(text.encode("utf-8")).digest()[:8]]


def _vector_db(tmp_path, embedded_as: str) -> tuple[str, Path]:
    data = tmp_path / "data"
    data.mkdir()
    (data / "fix_x.sql").write_text("UPDATE claims SET stance = 'jauns' WHERE id = 1;", encoding="utf-8")
    (data / "reembed_elektr_vectors_2026-08-03.ids").write_text("2\n", encoding="utf-8")
    path = _mkdb(tmp_path, params=[
        ("INSERT INTO claims (id, topic, stance) VALUES (1, 'T', 'jauns'), (2, 'T', 'ctrl')", ()),
        ("INSERT INTO claim_vectors VALUES (1, ?)", (_float_list_to_bytes(_fake_embed(embedded_as)),)),
        ("INSERT INTO claim_vectors VALUES (2, ?)", (_float_list_to_bytes(_fake_embed("T: ctrl")),)),
    ])
    return path, data


def test_check13_adapter_fresh_vector_is_clean(tmp_path):
    path, data = _vector_db(tmp_path, "T: jauns")
    r = _run(path, "13", data_dir=data, embed_fn=_fake_embed)
    assert (r.checked, r.flagged, r.status()) == (1, 0, 0)


def test_check13_adapter_stale_vector_is_flagged(tmp_path):
    """Kails `UPDATE claims SET stance` bez re-embed (eskalācija 8) — nekas neceļ,
    `search_similar_claims` ranžē pēc vecā teksta."""
    path, data = _vector_db(tmp_path, "T: vecs")
    r = _run(path, "13", data_dir=data, embed_fn=_fake_embed)
    assert (r.checked, r.flagged, r.status()) == (1, 1, 1)


def test_check13_adapter_no_candidates_is_broken_not_clean(tmp_path):
    """Nav neviena `data/fix_*.sql` kandidāta → checked=0. Skripts pats tad
    atgrieztu 0; reģistrā saucējs 0 ir salauzti vārti (exit 2)."""
    path, data = _vector_db(tmp_path, "T: jauns")
    (data / "fix_x.sql").unlink()
    r = _run(path, "13", data_dir=data, embed_fn=_fake_embed)
    assert (r.checked, r.broken, r.status()) == (0, "", 2)


def test_check2_accepted_multiplicity_counts_rows_not_ids(tmp_path):
    """Pieņemts id ar divām karogotām rindām (Svirskis: divi X konti) nedrīkst
    radīt `new=1` — pieņemšana skaitās pa rindām, tāpat kā `flagged`."""
    path = _mkdb(tmp_path, _POL2 + "(62, 'E S', 'tracked', 'ESvirskis');"
                 "INSERT INTO social_accounts VALUES (1, 62, 'twitter', 'a'), (2, 62, 'twitter', 'b');")
    r = _run(path, "2")
    assert (r.flagged, r.new, r.status()) == (2, 0, 0)


def test_check13_adapter_failing_control_is_method_broken(tmp_path):
    """Salauzts salīdzinājums ziņo VISU kā stale; krītoša kontrole → exit 2."""
    path, data = _vector_db(tmp_path, "T: jauns")
    r = _run(path, "13", data_dir=data, embed_fn=lambda t: _fake_embed("salauzts " + t))
    assert r.broken and r.status() == 2


# --- Informatīvās pārbaudes nekad neietekmē izejas kodu -------------------------

def test_informational_checks_never_change_exit_code(tmp_path):
    """1 / 6 / 8 ir izpētes vai augšējās robežas saraksti (BACKLOG § Atliktais 57:
    6. pārbaudes 101 grupa bez līdzības filtra). Ja tās karotu exit kodu, audits
    būtu «1» mūžīgi — vārti, kas nevar iziet, ir tikpat bezjēdzīgi kā tie, kas
    nevar krist."""
    path = _mkdb(tmp_path, params=[
        ("INSERT INTO tracked_politicians (id, name, name_forms, relationship_type) "
         "VALUES (1, 'Jānis Kols', '[\"Jānis Kols\", \"Kols\"]', 'tracked')", ()),
        ("INSERT INTO claims (opponent_id, topic, source_url, stated_at) VALUES (1, 'T', 'a', ?), (1, 'T', 'b', ?)",
         (now_lv(), now_lv())),
        ("INSERT INTO documents (id, content, platform, scraped_at, word_count) VALUES (1, 'Kols teica', 'web', ?, 5)",
         (now_lv(),)),
    ])
    results = {n: _run(path, n) for n in ("1", "6", "8")}
    assert results["1"].flagged == 1
    assert any(x["form"] == "Kols" and x["docs_14d"] == 1 for x in results["1"].rows)
    assert results["6"].flagged == 1
    assert results["8"].flagged == 1
    assert all(not r.gate and r.status() == 0 for r in results.values())
    assert _exit(path, "1,6,8", tmp_path) == 0
    (tmp_path / "audit.db").unlink()
    assert _exit(_mkdb(tmp_path), "1,6,8", tmp_path) == 0


def test_checks_12_and_15_are_one_measurement(tmp_path):
    """12. un 15. ir viena klase; divas implementācijas nozīmētu divus dažādus
    mērījumus. Dokuments, kur `mentioned` runā un `subject` ne → viena inversija."""
    path = _mkdb(tmp_path, params=[
        ("INSERT INTO tracked_politicians (id, name, name_forms, relationship_type) VALUES "
         "(1, 'Jānis Bērziņš', '[]', 'tracked'), (2, 'Anna Kalniņa', '[]', 'tracked')", ()),
        ("INSERT INTO documents (id, content, platform, source_url, scraped_at) VALUES "
         "(1, 'Jānis Bērziņš ' || printf('%.200c', '.') || ' Anna Kalniņa teica, ka tas ir labi.', 'web', 'u', ?)", (now_lv(),)),
        ("INSERT INTO document_politicians VALUES (1, 1, 'subject'), (1, 2, 'mentioned')", ()),
    ])
    db = ai.connect_ro(path)
    try:
        ctx = ai.Ctx(db=db, db_path=path)
        r12, r15 = ai.check_12(ctx), ai.check_15(ctx)
    finally:
        db.close()
    assert (r12.checked, r12.flagged) == (r15.checked, r15.flagged) == (1, 1)
    assert r12.rows == r15.rows
    assert not r12.gate and not r15.gate


# --- CLI / reģistrs -----------------------------------------------------------

def test_every_check_number_is_registered_and_scoped():
    """Numuri ir enkuri (`src/matcher.py`, `src/quality.py`, `src/saeima/votes.py`,
    CHANGELOG) — tos nemaina; katra pārbaude pieder kādai `--scope` grupai."""
    expected = ["1", "1b", *map(str, range(2, 10)), "9b", *map(str, range(10, 19))]
    assert sorted(ai.CHECKS) == sorted(expected)
    scoped = [n for nums in ai.SCOPES.values() for n in nums]
    assert sorted(scoped) == sorted(expected)
    assert ai.select_checks("2,9b") == ["2", "9b"]
    with pytest.raises(SystemExit):
        ai.select_checks("99")


def test_output_line_always_carries_the_denominator(tmp_path, capsys):
    """Zaļš bez saucēja nav pierādījums — katrā rindā `checked=` un `flagged=`."""
    path = _mkdb(tmp_path, "INSERT INTO context_notes (topic, note_type) VALUES ('dienas analīze 2026-09-29', 'daily_brief');")
    assert _exit(path, "16,11", tmp_path) == 2  # 11: tukša tabula
    out = capsys.readouterr().out
    lines = [ln for ln in out.splitlines() if ln[:2] in ("16", "11")]
    assert len(lines) == 2 and all("checked=" in ln and "flagged=" in ln for ln in lines)
    assert "SALAUZTI VĀRTI" in out


def test_json_output_is_parseable(tmp_path, capsys):
    path = _mkdb(tmp_path, "INSERT INTO context_notes (topic, note_type) VALUES ('daily', 'daily_brief');")
    code = ai.main(["--db", path, "--only", "16", "--json"])
    payload = json.loads(capsys.readouterr().out)
    assert code == payload["exit"] == 1
    assert payload["checks"][0]["num"] == "16" and payload["checks"][0]["flagged"] == 1


def test_script_never_writes_the_database(tmp_path):
    """Savienojums ir `mode=ro`: jebkurš raksts krīt skaļi, ne klusi izdodas."""
    db = ai.connect_ro(_mkdb(tmp_path))
    try:
        with pytest.raises(sqlite3.OperationalError):
            db.execute("INSERT INTO analyses VALUES (1, 'x')")
    finally:
        db.close()
