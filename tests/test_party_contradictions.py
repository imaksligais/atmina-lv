"""Partiju pretrunu šaurās versijas vārti (plāns 2026-08-06).

Sedz: T14 procedurālo veto (references ķēde 2025-04-10), frakcijas nostājas
blīvuma slieksni ar Nebalsoja izslēgšanu, ex-ST NULL-frakcijas gadījumu un
``contradictions.party_id`` migrācijas idempotenci.
"""

import math
import os
import struct
import tempfile

import pytest

from src.db import get_db, init_db
from src.party_contradictions import (
    COSINE_WEIGHT,
    LEXICAL_WEIGHT,
    MAJORITY_THRESHOLD,
    cosine,
    faction_stance,
    is_procedural,
    ensure_vec,
    lexical_overlap,
    load_claim_vector,
    rank_candidates,
    score_pair,
)
from src.saeima import init_saeima_tables


class TestT14ProceduralVeto:
    @pytest.mark.parametrize("motif", [
        "Par lēmuma projekta \"Par aizliegumu...\" iekļaušanu sēdes darba kārtībā",
        "Par iekļaušanu nākamās sēdes darba kārtībā",
        "Par likumprojekta nodošanu Tautsaimniecības komisijai",
        "Grozījumi likumā — nodošana komisijām",
        "Par likumprojekta atzīšanu par steidzamu",
        "Par priekšlikumu Nr.1. Grozījumi (1467/Lp14), 2.lasījums",
    ])
    def test_procedural_vetoed(self, motif):
        assert is_procedural(motif)

    @pytest.mark.parametrize("motif", [
        "Grozījumi Trauksmes celšanas likumā (1051/Lp14), 2.lasījums",
        "Grozījumi Imigrācijas likumā (1200/Lp14), 3.lasījums",
        None,
        "",
    ])
    def test_substantive_passes(self, motif):
        assert not is_procedural(motif)


@pytest.fixture
def tmp_db():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    init_db(path)
    init_saeima_tables(path)
    db = get_db(path)
    db.execute(
        "INSERT INTO saeima_votes (id, vote_date, vote_time, motif, url) "
        "VALUES (1, '2026-07-01', '10:00', 'Grozījumi testam', 'https://x/1')"
    )
    yield db
    db.close()
    try:
        os.unlink(path)
    except (PermissionError, FileNotFoundError):
        pass


def _seed_votes(db, faction, votes):
    for i, v in enumerate(votes):
        db.execute(
            "INSERT INTO saeima_individual_votes "
            "(vote_id, deputy_name, faction, vote) VALUES (1, ?, ?, ?)",
            (f"Deputāts {faction or 'X'} {i}", faction, v),
        )


class TestFactionStance:
    def test_clear_majority(self, tmp_db):
        _seed_votes(tmp_db, "JV", ["Par"] * 10 + ["Pret"] * 2)
        fs = faction_stance(tmp_db, 1, "JV")
        assert fs["stance"] == "Par"
        assert fs["cast"] == 12

    def test_split_faction_returns_none(self, tmp_db):
        # 6/11 = 55 % < 60 % slieksnis — šķelta frakcija, nostājas nav
        _seed_votes(tmp_db, "NA", ["Par"] * 6 + ["Pret"] * 5)
        assert 6 / 11 < MAJORITY_THRESHOLD
        assert faction_stance(tmp_db, 1, "NA") is None

    def test_nebalsoja_not_a_stance(self, tmp_db):
        # Nebalsoja neskaitās ne nostājā, ne saucējā
        _seed_votes(tmp_db, "ZZS", ["Par"] * 3 + ["Nebalsoja"] * 20)
        fs = faction_stance(tmp_db, 1, "ZZS")
        assert fs["stance"] == "Par"
        assert fs["cast"] == 3

    def test_atturas_is_a_stance(self, tmp_db):
        # Atturas ir substantīvs akts (CLAUDE.md Atturas noteikums)
        _seed_votes(tmp_db, "PRO", ["Atturas"] * 9 + ["Par"] * 1)
        assert faction_stance(tmp_db, 1, "PRO")["stance"] == "Atturas"

    def test_null_faction_ex_st_case(self, tmp_db):
        # ex-ST klase: deputāti balso, bet frakcijas avotā nav → nostāja
        # nav aprēķināma pēc konstrukcijas (izmeklēts 2026-08-06)
        _seed_votes(tmp_db, None, ["Par"] * 8)
        assert faction_stance(tmp_db, 1, "ST") is None


class TestMigration:
    def test_contradictions_party_id_exists_and_idempotent(self, tmp_db):
        cols = {r[1] for r in tmp_db.execute(
            "PRAGMA table_info(contradictions)").fetchall()}
        assert "party_id" in cols
        # atkārtots init_db tam pašam ceļam — nedrīkst krist (savienojumu
        # aizver vispirms: trigeru DROP prasa ekskluzīvu piekļuvi)
        path = tmp_db.execute("PRAGMA database_list").fetchone()[2]
        tmp_db.close()
        init_db(path)
        db2 = get_db(path)
        cols2 = {r[1] for r in db2.execute(
            "PRAGMA table_info(contradictions)").fetchall()}
        assert "party_id" in cols2
        db2.close()


# ---------------------------------------------------------------- ranžēšana

def _unit(*vals: float) -> list[float]:
    """384-dim vienības vektors no pirmajām komponentēm (pārējās 0)."""
    vec = list(vals) + [0.0] * (384 - len(vals))
    norm = math.sqrt(sum(v * v for v in vec)) or 1.0
    return [v / norm for v in vec]


def _insert_claim(db, claim_id, opponent_id, topic, stance, source_url,
                  claim_type, party_id=None, vector=None):
    db.execute(
        "INSERT INTO claims (id, opponent_id, topic, stance, source_url, "
        "claim_type, party_id) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (claim_id, opponent_id, topic, stance, source_url, claim_type, party_id),
    )
    if vector is not None:
        ensure_vec(db)
        db.execute(
            "INSERT INTO claim_vectors (claim_id, embedding) VALUES (?, ?)",
            (claim_id, struct.pack("384f", *vector)),
        )


class TestCosine:
    def test_identical_vectors(self):
        v = _unit(1.0, 2.0, 3.0)
        assert cosine(v, v) == pytest.approx(1.0)

    def test_orthogonal(self):
        assert cosine(_unit(1.0, 0.0), _unit(0.0, 1.0)) == pytest.approx(0.0)

    def test_length_mismatch_is_an_error_not_a_zero(self):
        # Klusa 0.0 tuvība saplūstu ar "nav vektora" — labāk kritums.
        with pytest.raises(ValueError):
            cosine([1.0, 0.0], [1.0, 0.0, 0.0])


class TestLexicalOverlap:
    def test_shared_subject_scores_high(self):
        a = "Programmā paredzēts atteikties no obligātā valsts aizsardzības dienesta."
        b = "Grozījumi Valsts aizsardzības dienesta likumā (1467/Lp14), 3.lasījums"
        assert lexical_overlap(a, b) > 0.4

    def test_unrelated_texts_score_zero(self):
        assert lexical_overlap(
            "Programmā solīta neitralitātes atjaunošana.",
            "Grozījumi Ceļu satiksmes likumā, 2.lasījums",
        ) == pytest.approx(0.0)

    def test_short_stems_do_not_merge_different_words(self):
        # 2026-08-18 palaidiens: 5 zīmju stumbrs sapludināja "Civildienesta"
        # (solījums par valsts pārvaldi) ar "Civilprocesa" (motīvs) → 1.000
        # leksiskais un FP top-30 augšā.
        assert lexical_overlap(
            "Reformēs Civildienesta likumu un samazinās birokrātiju.",
            "Grozījumi Civilprocesa likumā (1233/Lp14), 1.lasījums",
        ) == pytest.approx(0.0)

    def test_single_shared_word_does_not_saturate(self):
        # Viens sakritis vārds īsā motīvā nedrīkst dot pilnu 1.0.
        assert lexical_overlap(
            "Programmā solīta izglītības sistēmas reforma.",
            "Grozījumi Izglītības likumā",
        ) < 0.5

    def test_vote_boilerplate_does_not_create_overlap(self):
        # "Grozījumi ... likumā ... lasījums" ir katrā otrā motīvā — ja tas
        # skaitītos, rangs mērītu veidlapu, ne saturu.
        assert lexical_overlap(
            "Grozījumi likumā, 2.lasījums",
            "Grozījumi likumā, 3.lasījums",
        ) == pytest.approx(0.0)


class TestScorePair:
    def test_topic_match_raises_rank(self):
        matched = score_pair(cos=0.8, lex=0.5, topic_match=True)
        unmatched = score_pair(cos=0.8, lex=0.5, topic_match=False)
        assert matched > unmatched
        assert unmatched == 0.0

    def test_weights_sum_to_one_and_cosine_dominates(self):
        assert COSINE_WEIGHT + LEXICAL_WEIGHT == pytest.approx(1.0)
        assert COSINE_WEIGHT > LEXICAL_WEIGHT
        assert score_pair(cos=1.0, lex=1.0, topic_match=True) == pytest.approx(1.0)

    def test_higher_cosine_ranks_higher(self):
        assert score_pair(0.9, 0.2, True) > score_pair(0.4, 0.2, True)


@pytest.fixture
def rank_db(tmp_db):
    """Divi solījumi + divi balsojuma claims ar zināmiem vektoriem."""
    tmp_db.execute(
        "INSERT INTO saeima_votes (id, vote_date, vote_time, motif, url) VALUES "
        "(2, '2026-07-02', '11:00', 'Par likumprojekta nodošanu komisijai', "
        "'https://x/2')"
    )
    tmp_db.execute("INSERT INTO tracked_politicians (id, name) VALUES (1, 'A')")
    tmp_db.execute("INSERT INTO parties (id, name, short_name) VALUES (1, 'Partija', 'PP')")
    tmp_db.execute(
        "INSERT INTO saeima_individual_votes (vote_id, deputy_name, faction, "
        "vote, politician_id) VALUES (1, 'A', 'PP', 'Pret', 1)"
    )
    # solījums #100 un tuvs balsojuma claim #200 (cos ~1.0)
    _insert_claim(tmp_db, 100, 1, "Aizsardzība un drošība",
                  "Programmā paredzēts atteikties no obligātā dienesta.",
                  "https://prog/1", "program_promise", party_id=1,
                  vector=_unit(1.0, 0.0, 0.0))
    _insert_claim(tmp_db, 200, 1, "Aizsardzība un drošība",
                  "Iebilst pret: Grozījumi Valsts aizsardzības dienesta likumā",
                  "https://x/1", "saeima_vote", vector=_unit(0.99, 0.14, 0.0))
    # solījums #101 bez vektora
    _insert_claim(tmp_db, 101, 1, "Izglītība", "Programmā solīts kaut kas cits.",
                  "https://prog/1", "program_promise", party_id=1, vector=None)
    _insert_claim(tmp_db, 201, 1, "Izglītība", "Iebilst pret: Grozījumi Izglītības likumā",
                  "https://x/1", "saeima_vote", vector=_unit(0.0, 1.0, 0.0))
    return tmp_db


def _cand(**kw):
    base = {
        "party": "Partija", "faction": "PP", "promise_id": 100,
        "promise_topic": "Aizsardzība un drošība",
        "promise_stance": "Programmā paredzēts atteikties no obligātā dienesta.",
        "vote_id": 1, "vote_url": "https://x/1", "vote_date": "2026-07-01",
        "motif": "Grozījumi Valsts aizsardzības dienesta likumā (1467/Lp14), 3.lasījums",
        "document_nr": "1467/Lp14", "faction_stance": "Pret",
        "faction_counts": {"Pret": 8}, "chain_len": 1,
    }
    base.update(kw)
    return base


class TestRankCandidates:
    def test_denominators_are_reported(self, rank_db):
        res = rank_candidates(rank_db, [_cand()], top_n=30)
        st = res["stats"]
        assert st["pairs_in"] == 1
        assert st["ranked"] == 1
        assert st["skipped_missing_vector"] == 0
        assert len(res["ranked"]) == 1
        assert res["ranked"][0]["cosine"] > 0.95
        assert res["ranked"][0]["vote_claim_id"] == 200

    def test_missing_vector_is_skipped_with_a_count_not_zero_similarity(self, rank_db):
        res = rank_candidates(rank_db, [_cand(
            promise_id=101, promise_topic="Izglītība",
            promise_stance="Programmā solīts kaut kas cits.",
            motif="Grozījumi Izglītības likumā",
        )], top_n=30)
        assert res["ranked"] == []
        assert res["stats"]["skipped_missing_vector"] == 1
        assert res["stats"]["ranked"] == 0

    def test_procedural_motif_never_enters_the_ranking(self, rank_db):
        # T14 veto jau nostrādā ekrānā; šeit tas ir otrais slānis, lai
        # ranžētājs nekad neatgrieztu procedurālu pāri, ja to padod tieši.
        res = rank_candidates(rank_db, [_cand(
            vote_id=2, vote_url="https://x/2",
            motif="Par likumprojekta nodošanu komisijai",
        )], top_n=30)
        assert res["ranked"] == []
        assert res["stats"]["vetoed_procedural"] == 1

    def test_topic_mismatch_pair_is_dropped(self, rank_db):
        # Balsojuma claims tēmā "Aizsardzība un drošība" nav pie promise_topic
        # "Izglītība" tajā pašā URL → nav reprezentatīvā claim.
        res = rank_candidates(rank_db, [_cand(
            promise_topic="Nodokļi", promise_id=100,
        )], top_n=30)
        assert res["ranked"] == []
        assert res["stats"]["no_vote_claim"] == 1

    def test_top_n_truncates_but_denominator_keeps_the_full_count(self, rank_db):
        cands = [_cand(), _cand(vote_date="2026-07-03")]
        res = rank_candidates(rank_db, cands, top_n=1)
        assert res["stats"]["pairs_in"] == 2
        assert res["stats"]["ranked"] == 2
        assert len(res["ranked"]) == 1

    def test_same_promise_and_document_nr_collapse_to_one_da_pair(self, rank_db):
        # T14: viena document_nr ķēde jālasa kopā → viens DA spriedums par
        # (solījums, dokuments), nevis pa vienam ķēdes balsojumam.
        cands = [
            _cand(vote_id=1, vote_date="2026-07-01"),
            _cand(vote_id=1, vote_date="2026-07-05",
                  motif="Grozījumi Valsts aizsardzības dienesta likumā "
                        "(1467/Lp14), 2.lasījums"),
        ]
        res = rank_candidates(rank_db, cands, top_n=30)
        assert len(res["ranked"]) == 1
        assert res["stats"]["collapsed_chain_dupes"] == 1
        assert res["stats"]["ranked"] == 2  # saucējs paliek pilns

    def test_collapse_can_be_disabled(self, rank_db):
        cands = [_cand(vote_date="2026-07-01"), _cand(vote_date="2026-07-05")]
        res = rank_candidates(rank_db, cands, top_n=30, collapse_chains=False)
        assert len(res["ranked"]) == 2
        assert res["stats"]["collapsed_chain_dupes"] == 0

    def test_ranking_writes_nothing(self, rank_db):
        before = rank_db.execute("SELECT COUNT(*) FROM contradictions").fetchone()[0]
        rank_candidates(rank_db, [_cand()], top_n=30)
        after = rank_db.execute("SELECT COUNT(*) FROM contradictions").fetchone()[0]
        assert before == after == 0


class TestLoadClaimVector:
    def test_returns_none_when_absent(self, rank_db):
        assert load_claim_vector(rank_db, 101) is None

    def test_returns_384_floats(self, rank_db):
        vec = load_claim_vector(rank_db, 100)
        assert vec is not None and len(vec) == 384
