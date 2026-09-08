"""Tests for src/saeima.py claim generation.

Phase B of the claim_type split migration: every claim that
generate_claims_from_votes persists must carry claim_type='saeima_vote'.
The actual HTML parsing / network fetching is covered elsewhere; this file
focuses on the writer call path.
"""

import os
import tempfile
import pytest

from src.db import get_db, init_db
from src.saeima import (
    IndividualVote,
    SAEIMA_BASE_URL,
    VoteResult,
    _motif_to_topic,
    _resolve_vote_url,
    generate_claims_from_votes,
    init_saeima_tables,
    parse_vote_snapshot,
    store_vote,
)


def _safe_unlink(path):
    try:
        os.unlink(path)
    except PermissionError:
        pass


@pytest.fixture
def saeima_db():
    """Fresh DB with one tracked politician ready to receive a vote claim."""
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    init_db(path)
    init_saeima_tables(path)

    db = get_db(path)
    db.execute(
        "INSERT INTO tracked_politicians (id, name, party) VALUES (1, 'Test Deputāts', 'JV')"
    )
    db.commit()
    db.close()
    yield path
    _safe_unlink(path)


class TestGenerateClaimsFromVotesClaimType:
    def test_saeima_vote_claim_is_tagged(self, saeima_db, monkeypatch):
        """When generate_claims_from_votes persists a claim for a tracked
        politician's vote, the resulting row must have claim_type='saeima_vote'.
        Without this tag, Phase C readers would treat the row as a first-
        person position and it would pollute headline metrics, topic
        distributions, and contradiction candidates — the exact regression
        the claim_type split exists to prevent.
        """
        # Route the module's DB_PATH default to our fixture DB so the
        # internal get_db() calls inside generate_claims_from_votes land on
        # the temp DB rather than production.
        import src.saeima as saeima_mod
        import src.db as db_mod

        monkeypatch.setattr(db_mod, "DB_PATH", saeima_db)
        monkeypatch.setattr(saeima_mod, "DB_PATH", saeima_db)

        vote = VoteResult(
            motif="Par likumprojekta pieņemšanu otrajā lasījumā",
            date="2026-04-10",
            time="10:30",
            total_par=50,
            total_pret=30,
            total_atturas=5,
            total_nebalso=15,
            result="Pieņemts",
            url="/voting/12345",
            individual_votes=[
                IndividualVote(
                    deputy_name="Test Deputāts",
                    faction="JV",
                    # "Par", nevis "par" — parsētājs vienmēr dod lielo burtu
                    # (539 909 biļeteni DB, visi Par/Pret/Atturas/Nebalsoja).
                    # Kopš 2026-07-25 neatpazīta biļetena vērtība claim vairs
                    # netaisa vispār, tā vietā, lai ražotu "par: <motīvs>" no
                    # `vote_lv` atkāpšanās zara — sk.
                    # _BALLOT_VALUES_THAT_ARE_POSITIONS.
                    vote="Par",
                    politician_id=1,
                ),
            ],
        )

        claim_ids = generate_claims_from_votes(vote, vote_db_id=0, db_path=saeima_db)
        assert len(claim_ids) == 1, f"expected 1 claim, got {len(claim_ids)}"

        db = get_db(saeima_db)
        row = db.execute(
            "SELECT claim_type, topic, stance FROM claims WHERE id = ?",
            (claim_ids[0],),
        ).fetchone()
        db.close()

        assert row is not None, "claim not found after generate_claims_from_votes"
        assert row["claim_type"] == "saeima_vote", (
            f"saeima-tracker wrote claim with claim_type={row['claim_type']!r}, "
            f"expected 'saeima_vote'. Every vote row MUST be tagged so Phase C "
            f"readers can filter votes out of position-only views."
        )


class TestRegistrationEventsGenerateNoClaims:
    """Klātbūtnes reģistrācija nav pozīcija — tā ir apmeklējuma atzīme.

    Bez vārtiem katrs reģistrācijas notikums ražoja claim uz katru sekoto
    deputātu ar stance no neapstrādātās biļetena vērtības ("Re&#291;istr&#275;jies:
    Deputātu klātbūtnes reģistrācija"). 2026-07-25 auditā tādu bija 30 376 jeb
    5,5% no visiem claims. Sk. src/saeima/votes.py _REGISTRATION_MOTIF_PREFIX.
    """

    def _vote(self, motif):
        return VoteResult(
            motif=motif,
            date="2026-04-10",
            time="10:30",
            total_par=0,
            total_pret=0,
            total_atturas=0,
            total_nebalso=0,
            result="Noraidīts",
            url=f"/voting/{abs(hash(motif)) % 100000}",
            individual_votes=[
                IndividualVote(
                    deputy_name="Test Deputāts",
                    faction="JV",
                    vote="Reģistrējies",
                    politician_id=1,
                ),
            ],
        )

    def test_registration_event_yields_no_claims(self, saeima_db, monkeypatch):
        import src.saeima as saeima_mod
        import src.db as db_mod

        monkeypatch.setattr(db_mod, "DB_PATH", saeima_db)
        monkeypatch.setattr(saeima_mod, "DB_PATH", saeima_db)

        vote = self._vote("Deputātu klātbūtnes reģistrācija")
        claim_ids = generate_claims_from_votes(vote, vote_db_id=0, db_path=saeima_db)
        assert claim_ids == [], (
            f"registration event produced {len(claim_ids)} claim(s); attendance "
            f"is not a position and must never become one"
        )

    def test_quorum_check_ballot_yields_no_claims(self, saeima_db, monkeypatch):
        """Klātbūtnes stāvokļi parādās arī ĪSTU balsojumu vidū, ne tikai
        reģistrācijas notikumos — "Kvoruma pārbaude" atstāja 100 tādus claims
        pēc 2026-07-25 tīrīšanas. Tāpēc vārti ir pēc biļetena vērtības, ne tikai
        pēc motīva prefiksa.
        """
        import src.saeima as saeima_mod
        import src.db as db_mod

        monkeypatch.setattr(db_mod, "DB_PATH", saeima_db)
        monkeypatch.setattr(saeima_mod, "DB_PATH", saeima_db)

        vote = self._vote("Kvoruma pārbaude")
        claim_ids = generate_claims_from_votes(vote, vote_db_id=0, db_path=saeima_db)
        assert claim_ids == [], (
            f"quorum check produced {len(claim_ids)} claim(s); "
            f"Reģistrējies is an attendance state, not a position"
        )

    def test_real_bill_naming_registracija_still_yields_claims(
        self, saeima_db, monkeypatch
    ):
        """The guard is a PREFIX match, not '%reģistrācij%' — a substring filter
        would silently swallow real bills such as the Civilstāvokļa aktu
        reģistrācijas likums. Same reasoning as src/render/votes.py:173.
        """
        import src.saeima as saeima_mod
        import src.db as db_mod

        monkeypatch.setattr(db_mod, "DB_PATH", saeima_db)
        monkeypatch.setattr(saeima_mod, "DB_PATH", saeima_db)

        vote = self._vote(
            "Grozījumi Civilstāvokļa aktu reģistrācijas likumā (9998/Lp14), 1.lasījums"
        )
        vote.individual_votes[0].vote = "Par"
        claim_ids = generate_claims_from_votes(vote, vote_db_id=0, db_path=saeima_db)
        assert len(claim_ids) == 1, (
            f"a real bill whose title contains 'reģistrācijas' produced "
            f"{len(claim_ids)} claims; the guard must match the motif PREFIX only"
        )


class TestGenerateClaimsAcronymGuard:
    """Summary-based stances lowercase the summary's first char for natural
    flow ("Atbalsta: grozījumus…"). A summary opening with an acronym must
    keep its case — 2026-06-11 session produced 340 "lPV deputātu…" stances
    that had to be hand-fixed.
    """

    def _generate(self, saeima_db, monkeypatch, summary):
        import src.saeima as saeima_mod
        import src.db as db_mod

        monkeypatch.setattr(db_mod, "DB_PATH", saeima_db)
        monkeypatch.setattr(saeima_mod, "DB_PATH", saeima_db)

        vote = VoteResult(
            motif="Grozījumi Testa likumā (9999/Lp14), 1.lasījums",
            date="2026-06-11",
            time="10:30",
            total_par=50,
            total_pret=30,
            total_atturas=5,
            total_nebalso=15,
            result="Pieņemts",
            url="/voting/acronym-test",
            individual_votes=[
                IndividualVote(
                    deputy_name="Test Deputāts",
                    faction="JV",
                    vote="Par",
                    politician_id=1,
                ),
            ],
        )
        vote_db_id = store_vote(vote, agenda_item_id=None, db_path=saeima_db,
                                summary=summary)
        claim_ids = generate_claims_from_votes(vote, vote_db_id, db_path=saeima_db)
        assert len(claim_ids) == 1
        db = get_db(saeima_db)
        stance = db.execute(
            "SELECT stance FROM claims WHERE id = ?", (claim_ids[0],)
        ).fetchone()["stance"]
        db.close()
        return stance

    def test_acronym_summary_keeps_case(self, saeima_db, monkeypatch):
        stance = self._generate(
            saeima_db, monkeypatch,
            "LPV deputātu priekšlikums likvidēt Klimata un enerģētikas ministriju",
        )
        assert stance.startswith("Atbalsta: LPV deputātu"), stance

    def test_regular_summary_still_lowercased(self, saeima_db, monkeypatch):
        stance = self._generate(
            saeima_db, monkeypatch,
            "Priekšlikums pārcelt mācību gada sākumu uz 1. oktobri",
        )
        assert stance.startswith("Atbalsta: priekšlikums pārcelt"), stance


class TestResolveVoteUrl:
    """Absolute-URL callers used to get silently double-prefixed, producing
    broken links in 3000+ stored claims. The helper must accept both shapes.
    """

    def test_absolute_url_passthrough(self):
        absolute = f"{SAEIMA_BASE_URL}/Voting?ReadForm&parentID=abc123"
        assert _resolve_vote_url(absolute) == absolute

    def test_http_absolute_url_passthrough(self):
        absolute = "http://example.com/vote"
        assert _resolve_vote_url(absolute) == absolute

    def test_relative_url_gets_prefixed(self):
        relative = "./0/ABCDEF1234?OpenDocument"
        assert _resolve_vote_url(relative) == f"{SAEIMA_BASE_URL}/0/ABCDEF1234?OpenDocument"

    def test_bare_relative_without_dotslash(self):
        relative = "0/ABCDEF1234?OpenDocument"
        assert _resolve_vote_url(relative) == f"{SAEIMA_BASE_URL}/0/ABCDEF1234?OpenDocument"

    def test_empty_returns_none(self):
        assert _resolve_vote_url("") is None
        assert _resolve_vote_url(None) is None


class TestStoreVoteResolvesUrl:
    """store_vote() must persist absolute Saeima URLs. The Playwright snapshot
    plūsma yields relative anchors like './0/HEX?OpenDocument'; if those are
    written raw, the public site renders <a href="#"> for the "Balsojuma
    tabula" link (the safe_url filter rejects non-http(s) values). 2026-04-23
    session shipped 34 such broken rows before this guard was added.
    """

    def test_relative_url_stored_as_absolute(self, saeima_db):
        relative = "./0/ABCDEF1234?OpenDocument"
        vote = VoteResult(
            motif="Test motīvs",
            date="2026-04-27",
            time="11:00",
            total_par=1, total_pret=0, total_atturas=0, total_nebalso=0,
            result="Pieņemts",
            url=relative,
            individual_votes=[],
        )
        vote_id = store_vote(vote, db_path=saeima_db)

        db = get_db(saeima_db)
        stored = db.execute(
            "SELECT url FROM saeima_votes WHERE id = ?", (vote_id,)
        ).fetchone()["url"]
        db.close()

        expected = f"{SAEIMA_BASE_URL}/0/ABCDEF1234?OpenDocument"
        assert stored == expected, (
            f"store_vote persisted url={stored!r}; expected absolute "
            f"{expected!r}. Without resolution the templates render "
            f"href=\"#\" via safe_url filter."
        )

    def test_absolute_url_passes_through(self, saeima_db):
        absolute = f"{SAEIMA_BASE_URL}/0/FEDCBA?OpenDocument"
        vote = VoteResult(
            motif="Test motīvs 2",
            date="2026-04-27",
            time="11:01",
            total_par=1, total_pret=0, total_atturas=0, total_nebalso=0,
            result="Pieņemts",
            url=absolute,
            individual_votes=[],
        )
        vote_id = store_vote(vote, db_path=saeima_db)

        db = get_db(saeima_db)
        stored = db.execute(
            "SELECT url FROM saeima_votes WHERE id = ?", (vote_id,)
        ).fetchone()["url"]
        db.close()

        assert stored == absolute, "absolute URL must round-trip unchanged"

    def test_no_double_prefix_regression(self):
        """Regression guard: an absolute URL must not end up with two base
        URLs concatenated (the bug that corrupted 3000+ rows on 2026-04-16).
        """
        absolute = f"{SAEIMA_BASE_URL}/Voting?parentID=xyz"
        result = _resolve_vote_url(absolute)
        assert result.count(SAEIMA_BASE_URL) == 1, (
            f"URL double-prefix regression: {result!r}"
        )


class TestMotifToTopic:
    """Motif keyword map gaps surfaced on 2026-04-16: four bills whose topics
    fell through to the raw motif string, producing non-canonical topic
    values and mis-grouped claims.
    """

    def test_ministru_kabineta_iekarta_maps_to_valsts_parvalde(self):
        motif = "Grozījumi Ministru kabineta iekārtas likumā (1294/Lp14), nodošana komisijām"
        assert _motif_to_topic(motif) == "Valsts pārvalde"

    def test_knab_maps_to_tieslietas(self):
        motif = "Grozījumi Korupcijas novēršanas un apkarošanas biroja likumā (1298/Lp14), nodošana komisijām"
        assert _motif_to_topic(motif) == "Tieslietas"

    def test_latvijas_banka_maps_to_budzets_un_finanses(self):
        motif = "Grozījumi Latvijas Bankas likumā (1300/Lp14), nodošana komisijām"
        assert _motif_to_topic(motif) == "Budžets un finanses"

    def test_air_baltic_with_space_maps_to_airbaltic(self):
        """The existing 'airBaltic' keyword (no space) did not match
        Saeima's 'Air Baltic Corporation' phrasing. Both forms must route
        to the airBaltic topic group.
        """
        motif = 'Par Saeimas piekrišanu valsts īstermiņa aizdevuma izsniegšanai AS "Air Baltic Corporation" (953/Lm14)'
        assert _motif_to_topic(motif) == "airBaltic"

    def test_airbaltic_nospace_still_works(self):
        motif = "airBaltic finansējuma palielināšana"
        assert _motif_to_topic(motif) == "airBaltic"

    # 2026-07-28 — bare _stem("elektr") mis-routed every "Elektronisk*" bill
    # to Degviela un enerģētika (105 votes / 9171 claims backfilled via
    # data/fix_topic_elektr_2026-07-28.sql). Specific guards precede the
    # Energy block; energy itself narrowed to explicit stems.

    def test_elektronisko_plassazinas_maps_to_sabiedriskie_mediji(self):
        motif = "Grozījumi Elektronisko plašsaziņas līdzekļu likumā (1200/Lp14), 2.lasījums"
        assert _motif_to_topic(motif) == "Sabiedriskie mediji"

    def test_sabiedrisko_eplp_parvaldibas_maps_to_sabiedriskie_mediji(self):
        motif = ("Grozījumi Sabiedrisko elektronisko plašsaziņas līdzekļu "
                 "un to pārvaldības likumā (1071/Lp14), 3.lasījums")
        assert _motif_to_topic(motif) == "Sabiedriskie mediji"

    def test_elektronisko_sakaru_maps_to_digitala_politika(self):
        motif = "Grozījumi Elektronisko sakaru likumā (1145/Lp14), 1.lasījums"
        assert _motif_to_topic(motif) == "Digitālā politika"

    def test_elektroniskas_naudas_maps_to_budzets(self):
        motif = ("Grozījumi Maksājumu pakalpojumu un elektroniskās naudas "
                 "likumā (1102/Lp14), 2.lasījums")
        assert _motif_to_topic(motif) == "Budžets un finanses"

    def test_tabakas_e_smekesanas_maps_to_veseliba(self):
        motif = ("Grozījumi Tabakas izstrādājumu, augu smēķēšanas produktu, "
                 "elektronisko smēķēšanas ierīču un to šķidrumu aprites "
                 "likumā (1030/Lp14), 3.lasījums")
        assert _motif_to_topic(motif) == "Veselības aprūpe"

    def test_elektroenergijas_tirgus_stays_energy(self):
        motif = "Grozījumi Elektroenerģijas tirgus likumā (1174/Lp14), 2.lasījums"
        assert _motif_to_topic(motif) == "Degviela un enerģētika"

    def test_elektribas_tikla_tarifi_stays_energy(self):
        motif = ("Par uzdevumu Ministru kabinetam nekavējoties risināt "
                 "elektrības tīkla tarifu pieauguma mazināšanu")
        assert _motif_to_topic(motif) == "Degviela un enerģētika"

    # 2026-04-26 audit: gaps surfaced during 23.04. Saeima session scrape.
    # Three motif categories fell through to the topic_map passthrough and
    # leaked the raw motif text into the topic column.

    def test_naftas_produkti_is_energy(self):
        """Fuel-price legislation is energy policy, not state administration."""
        motif = "Grozījumi Naftas produktu cenu pieauguma ierobežošanas likumā (1313/Lp14), nodošana komisijām"
        assert _motif_to_topic(motif) == "Degviela un enerģētika"

    def test_maksatnespejas_likums_is_tieslietas(self):
        """Insolvency law is justice domain (procedural)."""
        motif = "Grozījumi Maksātnespējas likumā (1260/Lp14), 1.lasījums"
        assert _motif_to_topic(motif) == "Tieslietas"

    # 2026-06-11 session load: the generic `aizsardzīb` fallback classified
    # animal-welfare votes as defence (24 votes / 2103 claims backfilled
    # 2026-06-12, see data/fix_dzivnieku_aizsardzibas_topic_2026-06-12.sql).

    def test_dzivnieku_aizsardzibas_likums_is_lauksaimnieciba(self):
        """Animal-welfare law is agriculture policy, not defence."""
        motif = "Grozījumi Dzīvnieku aizsardzības likumā (1323/Lp14), 1.lasījums"
        assert _motif_to_topic(motif) == "Lauksaimniecība"

    def test_dzivnieku_aizsardzibas_amendment_is_lauksaimnieciba(self):
        """Amendment-vote motifs carry the same bill title and must follow it."""
        motif = "Par priekšlikumu Nr.21. Grozījumi Dzīvnieku aizsardzības likumā (148/Lp14), 3.lasījums"
        assert _motif_to_topic(motif) == "Lauksaimniecība"

    def test_generic_aizsardziba_still_defence(self):
        """The guard must not weaken the defence fallback for actual defence bills."""
        motif = "Grozījumi Nacionālās drošības likumā (1310/Lp14), 1.lasījums"
        assert _motif_to_topic(motif) == "Aizsardzība un drošība"

    def test_unmapped_motif_falls_back_to_valsts_parvalde(self):
        """When neither the keyword map nor topic_map.normalize_topic
        recognizes a motif, return the safe default 'Valsts pārvalde'
        — never pass the raw motif text through to the topic column.
        """
        motif = "Par 10 485 Latvijas pilsoņu kolektīvā iesnieguma \"Goda ģimenes\" statuss vecākiem uz mūžu - pateicība par ieguldījumu Latvijas tautas ataudzē turpmāko virzību (952/Lm14)"
        assert _motif_to_topic(motif) == "Valsts pārvalde"

    # 2026-06-12 coverage revīzija: 543 votes fell through the generic
    # `pārvald`/`aizsardzīb`/`nodokl` fallbacks to "Valsts pārvalde" and were
    # backfilled to their canonical topic (data/fix_motif_topic_coverage_2026-06-12.sql).
    # Each test below pins a stem family that MUST beat a generic rule.

    def test_nekustama_ipasuma_nodoklis_is_pasvaldibas(self):
        """Municipal property tax is local-government revenue, not Budžets.
        Must beat the generic `nodokl`→Budžets rule (which sits lower).
        """
        motif = "Grozījumi likumā “Par nekustamā īpašuma nodokli” (1280/Lp14), nodošana komisijām"
        assert _motif_to_topic(motif) == "Pašvaldības"

    def test_akcizes_nodoklis_is_budzets(self):
        """Excise tax is a state budget matter."""
        motif = "Grozījumi likumā “Par akcīzes nodokli” (913/Lp14), 1.lasījums"
        assert _motif_to_topic(motif) == "Budžets un finanses"

    def test_ienakuma_nodoklis_is_budzets(self):
        """Income tax is a state budget matter."""
        motif = "Grozījumi likumā “Par iedzīvotāju ienākuma nodokli” (862/Lp14), 1.lasījums"
        assert _motif_to_topic(motif) == "Budžets un finanses"

    def test_ieslodzijuma_vietas_is_tieslietas(self):
        """Prison administration is a justice matter. Must beat the generic
        `pārvald`→Valsts pārvalde rule ("Ieslodzījuma vietu pārvaldes likums").
        """
        motif = "Grozījumi Ieslodzījuma vietu pārvaldes likumā (1052/Lp14), 2.lasījums"
        assert _motif_to_topic(motif) == "Tieslietas"

    def test_kapitalsabiedribu_parvaldiba_is_valsts_kapitalsabiedribas(self):
        """State capital-share governance routes to the enterprises topic.
        Must beat the generic `pārvald`→Valsts pārvalde rule
        ("kapitāla daļu un kapitālsabiedrību pārvaldības likums").
        """
        motif = "Grozījumi Publiskas personas kapitāla daļu un kapitālsabiedrību pārvaldības likumā (1105/Lp14)"
        assert _motif_to_topic(motif) == "Valsts kapitālsabiedrības"

    def test_administrativo_teritoriju_is_pasvaldibas(self):
        """Administrative-territory bills are a municipalities matter."""
        motif = "Grozījumi Administratīvo teritoriju un apdzīvoto vietu likumā (572/Lp14), nodošana komisijām"
        assert _motif_to_topic(motif) == "Pašvaldības"

    def test_zemessardze_is_aizsardziba(self):
        """National Guard law is defence."""
        motif = "Grozījumi Latvijas Republikas Zemessardzes likumā (552/Lp14), 1.lasījums"
        assert _motif_to_topic(motif) == "Aizsardzība un drošība"

    def test_energoresursu_is_energetika(self):
        """Energy-resource pricing law is energy policy — the existing
        `enerģēt` stem misses 'Energoresursu' (no 'ēt' root).
        """
        motif = "Grozījumi Energoresursu cenu ārkārtēja pieauguma samazinājuma pasākumu likumā (99/Lp14)"
        assert _motif_to_topic(motif) == "Degviela un enerģētika"

    def test_covid_is_veselibas_aprupe(self):
        """Covid-19 law is health policy. Must beat the generic `pārvald`
        rule, which the bill title contains ("izplatības seku pārvarēšanas").
        """
        motif = "Grozījums Covid-19 infekcijas izplatības seku pārvarēšanas likumā (519/Lp14), 2.lasījums"
        assert _motif_to_topic(motif) == "Veselības aprūpe"

    def test_autortiesibu_is_kultura(self):
        """Copyright law is culture domain."""
        motif = "Grozījumi Autortiesību likumā (726/Lp14), 1.lasījums"
        assert _motif_to_topic(motif) == "Kultūra"

    def test_konfiskacija_is_tieslietas(self):
        """Criminal-asset confiscation law is justice domain."""
        motif = "Grozījumi Noziedzīgi iegūtas mantas konfiskācijas izpildes likumā (1000/Lp14), 1.lasījums"
        assert _motif_to_topic(motif) == "Tieslietas"

    def test_maternitates_is_sociala_politika(self):
        """Maternity-insurance law is social policy."""
        motif = "Grozījums likumā “Par maternitātes un slimības apdrošināšanu” (1102/Lp14), 1.lasījums"
        assert _motif_to_topic(motif) == "Sociālā politika"

    def test_zemes_privatizacija_is_pasvaldibas(self):
        """Rural land-privatisation law is a municipalities / land matter."""
        motif = "Grozījumi likumā “Par zemes privatizāciju lauku apvidos” (1281/Lp14), 1.lasījums"
        assert _motif_to_topic(motif) == "Pašvaldības"


class TestParseVoteSnapshotMotif:
    """Regex parsing of the motif line in a Playwright accessibility
    snapshot. Pre-2026-04-26 the regex stopped at the first internal
    quote, truncating motifs that contained escaped \" sequences (e.g.
    citizen-petition titles).
    """

    def test_simple_motif_extracted(self):
        snapshot = '          - generic [ref=e16]: "Balsošanas motīvs: Grozījumi Imigrācijas likumā (1180/Lp14), 3.lasījums"\n'
        result = parse_vote_snapshot(snapshot)
        assert result.motif == "Grozījumi Imigrācijas likumā (1180/Lp14), 3.lasījums"

    def test_motif_with_escaped_quotes_not_truncated(self):
        snapshot = '          - generic [ref=e16]: "Balsošanas motīvs: Par 10 485 Latvijas pilsoņu kolektīvā iesnieguma \\"Goda ģimenes\\" statuss vecākiem uz mūžu turpmāko virzību (952/Lm14)"\n'
        result = parse_vote_snapshot(snapshot)
        assert "Goda ģimenes" in result.motif
        assert "(952/Lm14)" in result.motif
        # Ensure quotes were unescaped
        assert '\\"' not in result.motif

    def test_motif_with_curly_quotes_unaffected(self):
        """Smart quotes inside motif should pass through (no escape needed)."""
        snapshot = '          - generic [ref=e16]: "Balsošanas motīvs: Grozījumi likumā “Par zemes dzīlēm” (1271/Lp14), 2.lasījums, steidzams"\n'
        result = parse_vote_snapshot(snapshot)
        assert "Par zemes dzīlēm" in result.motif
        assert "(1271/Lp14)" in result.motif


class TestFactionLabelNormalization:
    """Titania's own cell format drifted for Stabilitātei! — `ST!` through
    2025-12, `ST` in 2026-03..04. Storing both verbatim split one faction's
    50k-ballot history across two labels, so any faction-grouping query
    silently lost one side (found by /audit-integrity check 9, 2026-08-04).
    The parser must normalize to `ST` — the `parties.short_name` form that
    coalition logic and check 9 key on — so the pending 2025 backfill cannot
    reintroduce the split."""

    @staticmethod
    def _snapshot_with_deputy(faction_cell):
        return (
            '          - generic [ref=e16]: "Balsošanas motīvs: Testa balsojums (1/Lp14)"\n'
            '          - cell "1." [ref=e20]\n'
            '          - cell "Testa Deputāts" [ref=e21]\n'
            f'          - cell "{faction_cell}" [ref=e22]\n'
            '          - cell "Par" [ref=e23]\n'
        )

    def test_st_bang_is_normalized_to_short_name_form(self):
        result = parse_vote_snapshot(self._snapshot_with_deputy("ST!"))
        assert len(result.individual_votes) == 1
        assert result.individual_votes[0].faction == "ST"

    def test_st_plain_passes_through(self):
        result = parse_vote_snapshot(self._snapshot_with_deputy("ST"))
        assert len(result.individual_votes) == 1
        assert result.individual_votes[0].faction == "ST"


class TestParseVoteSnapshotResult:
    """Vote outcome detection — 2026-04-26 audit caught two votes (id 99
    airBaltic loan, id 113 Degvielas tirgotāju komisija) that were
    misclassified as 'Noraidīts' because the parser fell through to a
    51-of-100 absolute-majority fallback. The Latvian rule is absolute
    majority of KLĀTESOŠO deputātu — Lm-type vote snapshots that lack the
    explicit label must be calculated against present-deputy count, not
    the full 100-seat chamber.
    """

    def _snapshot_with_totals(self, par, pret, atturas, nebalso, motif="Test motif"):
        # Minimal snapshot that triggers the fallback (no 'Noraidīts'/'Pieņemts' label).
        # totals regex expects: "par N, pret N, atturas N". nebalso isn't read
        # from snapshot text; we set it on the VoteResult fixture directly via
        # the fallback computation override below.
        return (
            f'          - generic [ref=e16]: "Balsošanas motīvs: {motif}"\n'
            f'        - generic: "par {par}, pret {pret}, atturas {atturas}, nebalso {nebalso}"\n'
        )

    def test_airbaltic_49_par_88_present_passes(self):
        """49 par > (88 // 2) = 44 → Pieņemts. Vote 99 regression."""
        snapshot = self._snapshot_with_totals(49, 23, 1, 15)
        result = parse_vote_snapshot(snapshot)
        assert result.total_par == 49
        assert result.result == "Pieņemts"

    def test_46_par_85_present_passes(self):
        """Lm-type procedural vote: 46 > (85 // 2) = 42 → Pieņemts. Vote 113 regression."""
        snapshot = self._snapshot_with_totals(46, 15, 22, 2)
        result = parse_vote_snapshot(snapshot)
        assert result.result == "Pieņemts"

    def test_par_below_present_majority_fails(self):
        """34 par, 82 present → threshold 41, 34 < 41 → Noraidīts."""
        snapshot = self._snapshot_with_totals(34, 33, 3, 12)
        result = parse_vote_snapshot(snapshot)
        assert result.result == "Noraidīts"

    def test_explicit_noraidits_label_wins(self):
        """When snapshot text contains 'Noraidīts', the label is authoritative."""
        snapshot = self._snapshot_with_totals(60, 5, 0, 0) + "Noraidīts\n"
        result = parse_vote_snapshot(snapshot)
        assert result.result == "Noraidīts"

    def test_no_ballot_cast_leaves_result_empty(self):
        """Attendance registration is not a motion — do not fabricate a result.

        Before 2026-08-17 the fallback fell through to `0 > 0 == False` and
        wrote 'Noraidīts'; that put a rejection the source never states on 540
        procedural rows (attendance registration, quorum check, office ballot).
        """
        snapshot = self._snapshot_with_totals(
            0, 0, 0, 88, motif="Deputātu klātbūtnes reģistrācija"
        )
        result = parse_vote_snapshot(snapshot)
        assert not result.result, f"fabricated result: {result.result!r}"

    def test_explicit_pienemts_label_wins(self):
        """When snapshot text contains 'Pieņemts', the label is authoritative."""
        snapshot = self._snapshot_with_totals(10, 50, 0, 0) + "Pieņemts\n"
        result = parse_vote_snapshot(snapshot)
        assert result.result == "Pieņemts"


class TestResultProvenance:
    """`saeima_votes.result_source` — is a stored outcome a SOURCE QUOTE or OUR
    ARITHMETIC?

    Until 2026-08-18 `result` was a mixed-provenance field: part agenda label
    (live tracker), part compute-from-totals fallback (backfill), with no
    column separating the two — so no `result` value could be cited as the
    source's own word (BACKLOG § Saeima, PALIEK ATVĒRTS 2).

    Domain: 'agenda_label' | 'computed' | NULL (unknown / no assertion).
    """

    def test_column_exists_after_init(self, saeima_db):
        db = get_db(saeima_db)
        cols = {r[1] for r in db.execute("PRAGMA table_info(saeima_votes)").fetchall()}
        db.close()
        assert "result_source" in cols

    def test_domain_is_enforced(self, saeima_db):
        import sqlite3

        db = get_db(saeima_db)
        with pytest.raises(sqlite3.IntegrityError):
            db.execute(
                "INSERT INTO saeima_votes (motif, result, result_source) "
                "VALUES ('x', 'Pieņemts', 'guessed')"
            )
        # The three legal values must all pass.
        for value in ("agenda_label", "computed", None):
            db.execute(
                "INSERT INTO saeima_votes (motif, result, result_source) "
                "VALUES ('x', 'Pieņemts', ?)",
                (value,),
            )
        db.commit()
        db.close()

    def _vote(self, **kw):
        base = dict(
            motif="Test motīvs",
            date="2026-08-18",
            time="11:00",
            total_par=50, total_pret=10, total_atturas=0, total_nebalso=0,
            url="./0/PROVENANCE1?OpenDocument",
            individual_votes=[],
        )
        base.update(kw)
        return VoteResult(**base)

    def _stored(self, db_path, vote_id):
        db = get_db(db_path)
        row = db.execute(
            "SELECT result, result_source FROM saeima_votes WHERE id = ?",
            (vote_id,),
        ).fetchone()
        db.close()
        return row["result"], row["result_source"]

    def test_agenda_label_kwarg_wins_and_is_recorded(self, saeima_db):
        """The agenda item's own label is the authority — verbatim, provenance
        'agenda_label', overriding whatever the totals would compute."""
        vote = self._vote(result="Pieņemts", result_source="computed")
        vote_id = store_vote(vote, db_path=saeima_db, agenda_result="Nod. kom.")
        assert self._stored(saeima_db, vote_id) == ("Nod. kom.", "agenda_label")

    def test_computed_result_is_marked_computed(self, saeima_db):
        vote = self._vote(result="Pieņemts", result_source="computed")
        vote_id = store_vote(vote, db_path=saeima_db)
        assert self._stored(saeima_db, vote_id) == ("Pieņemts", "computed")

    def test_no_result_stores_null_provenance(self, saeima_db):
        vote = self._vote(
            result=None, result_source=None,
            total_par=0, total_pret=0, total_atturas=0, total_nebalso=88,
        )
        vote_id = store_vote(vote, db_path=saeima_db)
        assert self._stored(saeima_db, vote_id) == (None, None)

    def test_parser_marks_fallback_as_computed(self):
        snapshot = (
            '          - generic [ref=e16]: "Balsošanas motīvs: Test"\n'
            '        - generic: "par 49, pret 23, atturas 1, nebalso 15"\n'
        )
        parsed = parse_vote_snapshot(snapshot)
        assert parsed.result == "Pieņemts"
        assert parsed.result_source == "computed"

    def test_parser_marks_source_label_as_agenda_label(self):
        snapshot = (
            '          - generic [ref=e16]: "Balsošanas motīvs: Test"\n'
            '        - generic: "par 10, pret 50, atturas 0, nebalso 0"\n'
            "Pieņemts\n"
        )
        parsed = parse_vote_snapshot(snapshot)
        assert parsed.result == "Pieņemts"
        assert parsed.result_source == "agenda_label"

    def test_parser_leaves_provenance_null_when_no_result(self):
        snapshot = (
            '          - generic [ref=e16]: "Balsošanas motīvs: '
            'Deputātu klātbūtnes reģistrācija"\n'
            '        - generic: "par 0, pret 0, atturas 0, nebalso 88"\n'
        )
        parsed = parse_vote_snapshot(snapshot)
        assert parsed.result is None
        assert parsed.result_source is None


class TestExtractAgendaResultLabels:
    """The outcome label lives ONLY on the agenda page, in the 9th argument of
    `drawDKP_*(...)`, keyed to the agenda ITEM — the vote page's red span is
    empty. `addVotesLink(DKP_HEX, VOTE_HEX)` is the bridge from item to vote.
    Fixture below is trimmed from the live 2026-07-23 agenda.
    """

    AGENDA = (
        'drawDKP_Pr("1","","Groz%C4%ABjums","1471/Lp14","1",'
        '"0D2D0F288010446BC2258E3D003FA686","Komisija","",'
        '"par 48, pret 16, atturas 0 &nbsp; <b>Likums</b>","3","x","","5156B","6");\n'
        'drawDKP_Pr("1","","Groz%C4%ABjumi","1458/Lp14","2",'
        '"2E5BE29F3A69B72DC2258E3D003FA687","Komisija","",'
        '"par 63, pret 7, atturas 1 &nbsp; <b>Pie&#326;emts</b>","2","","1","5140","6");\n'
        'drawDKP_UT("","","Deput%C4%81tu%20kl%C4%81tb%C5%ABtnes%20re%C4%A3istr%C4%81cija",'
        '"","","9157DCD3236F50C9C2258E3D003FA69A","","",'
        '"re&#291;istr&#275;ju&#353;ies 85 &nbsp;","","","","","6");\n'
        'addVotesLink("0D2D0F288010446BC2258E3D003FA686",'
        '"20FFD0CEDD18C261C2258E3D003FA68D","0","0","0");\n'
        'addVotesLink("2E5BE29F3A69B72DC2258E3D003FA687",'
        '"6304FAE90F25C519C2258E3D003FA68F","0","0","0");\n'
        'addVotesLink("9157DCD3236F50C9C2258E3D003FA69A",'
        '"B6CD380F2A82391DC2258E3D003FA69C","0","0","0");\n'
    )

    def test_labels_keyed_by_vote_url(self):
        from src.saeima import extract_agenda_result_labels

        labels = extract_agenda_result_labels(self.AGENDA)
        base = SAEIMA_BASE_URL
        assert labels == {
            f"{base}/0/20FFD0CEDD18C261C2258E3D003FA68D?OpenDocument": "Likums",
            f"{base}/0/6304FAE90F25C519C2258E3D003FA68F?OpenDocument": "Pieņemts",
        }

    def test_item_without_label_is_absent_not_guessed(self):
        """Attendance registration carries no <b> label — the map must omit it
        rather than invent an outcome (the 540-row fabrication class)."""
        from src.saeima import extract_agenda_result_labels

        labels = extract_agenda_result_labels(self.AGENDA)
        registration = (
            f"{SAEIMA_BASE_URL}/0/B6CD380F2A82391DC2258E3D003FA69C?OpenDocument"
        )
        assert registration not in labels

    def test_empty_agenda_yields_empty_map(self):
        from src.saeima import extract_agenda_result_labels

        assert extract_agenda_result_labels("<html></html>") == {}


class TestResultSourceSeedMigration:
    """The 2026-08-18 seed: provenance is asserted ONLY for the 5 rows whose
    agenda label was read in a rendered browser during the 08-17/18 sanitation.
    Everything else stays NULL — we do not guess provenance.
    """

    FIX = "data/fix_result_source_seed_2026-08-18.sql"
    ROLLBACK = "data/rollback_result_source_seed_2026-08-18.sql"

    def _read(self, rel):
        import pathlib

        import pytest

        path = pathlib.Path(__file__).resolve().parent.parent / rel
        if not path.exists():
            # Publiskajā spogulī data/*.sql ir izslēgti pēc sync receptes —
            # tur šie testi skipojas (test_no_deploy_credentials precedents).
            # Privātajā kokā faili IR tracked, tāpēc skips tur nenotiek un
            # īsta faila pazušana joprojām būtu redzama commit diffā.
            pytest.skip(f"{rel} nav kokā (publiskais spogulis bez data/*.sql)")
        return path.read_text(encoding="utf-8")

    def test_seed_touches_exactly_the_five_verified_ids(self):
        import re

        sql = self._read(self.FIX)
        ids = set(re.findall(r"\b(6459|905|956|1435|6192)\b", sql))
        assert ids == {"6459", "905", "956", "1435", "6192"}
        assert sql.count("UPDATE saeima_votes") == 2, (
            "expect exactly two UPDATEs: 'Pieņemts' row + the four 'Nod. kom.' rows"
        )
        assert "agenda_label" in sql
        assert "computed" not in sql

    def test_rollback_exists_and_reverts_to_null(self):
        sql = self._read(self.ROLLBACK)
        assert "result_source = NULL" in sql
        assert "UPDATE saeima_votes" in sql


class TestMotifToTopicFalsePositiveGuards:
    """Regression guards for the 2026-04-17 matcher rewrite.

    The old substring matcher used `"ES " in motif.lower()`, which
    matched any Latvian genitive ending in `-es ` (aprites, dzīles,
    apstrādes, ...). The stem `"aizsardzīb"` similarly over-covered
    justice- and environment-related phrases. 8 votes on 2026-04-16
    were mis-tagged as a result. Every case below is pinned here so
    a future refactor cannot silently reintroduce the regression.
    """

    # --- "ES " no longer swallows genitive suffixes ---

    def test_ieroču_aprites_is_defence_not_eu(self):
        motif = "Grozījumi Ieroču aprites likumā (1307/Lp14), nodošana komisijām"
        assert _motif_to_topic(motif) == "Aizsardzība un drošība"

    def test_zemes_dzilem_is_vide_not_eu(self):
        motif = "Grozījumi likumā \u201cPar zemes dzīlēm\u201d (1271/Lp14), 2.lasījums, steidzams"
        assert _motif_to_topic(motif) == "Vide"

    def test_ietekmes_uz_vidi_is_vide_not_eu(self):
        motif = "Grozījumi likumā \u201cPar ietekmes uz vidi novērtējumu\u201d (1276/Lp14), 2.lasījums, steidzams"
        assert _motif_to_topic(motif) == "Vide"

    def test_robežsardzes_is_defence_not_eu(self):
        motif = "Grozījumi Valsts robežsardzes likumā (1197/Lp14), 3.lasījums"
        assert _motif_to_topic(motif) == "Aizsardzība un drošība"

    def test_biometrijas_datu_apstrades_is_tieslietas_not_eu(self):
        motif = "Grozījumi Biometrijas datu apstrādes sistēmas likumā (1203/Lp14), 3.lasījums"
        assert _motif_to_topic(motif) == "Tieslietas"

    def test_real_es_still_matches(self):
        """Genuine ES-policy motifs must still route to 'ES politika' —
        the word-boundary fix narrows the pattern, it doesn't disable it.
        """
        assert _motif_to_topic("Par ES direktīvas ieviešanu") == "ES politika"
        assert _motif_to_topic("Grozījumi Eiropas Parlamenta vēlēšanu likumā") == "Vēlēšanas"  # "vēlēšan" wins

    # --- "aizsardzīb" no longer swallows justice / environment phrases ---

    def test_tiesibu_aizsardzibas_iestadei_is_tieslietas(self):
        motif = "Par iespējamu politisko spiedienu un patiesībai neatbilstošas informācijas sniegšanu tiesību aizsardzības iestādei"
        assert _motif_to_topic(motif) == "Tieslietas"

    def test_vides_aizsardzibas_is_vide(self):
        motif = "Grozījumi Vides aizsardzības likumā (1269/Lp14), 2.lasījums, steidzams"
        assert _motif_to_topic(motif) == "Vide"

    def test_sugu_un_biotopu_aizsardzibas_is_vide(self):
        motif = "Grozījumi Sugu un biotopu aizsardzības likumā (1277/Lp14), 2.lasījums, steidzams"
        assert _motif_to_topic(motif) == "Vide"

    def test_whistleblower_law_is_tieslietas_not_defence(self):
        motif = "Sabiedrības interesēs iesaistīto personu aizsardzības likums (1186/Lp14), 3.lasījums"
        assert _motif_to_topic(motif) == "Tieslietas"

    # --- "drošīb" no longer swallows public-health and road-safety phrases ---

    def test_epidemiologiskas_drosibas_is_sociala_not_defence(self):
        motif = "Grozījumi Epidemioloģiskās drošības likumā (1139/Lp14), 3.lasījums"
        assert _motif_to_topic(motif) == "Sociālā politika"

    def test_celu_satiksmes_drosiba_is_transports(self):
        """Road safety is transport, not national defence."""
        motif = "Grozījumi Ceļu satiksmes drošības likumā"
        assert _motif_to_topic(motif) == "Transports"

    # --- Ambiguous bill titles are still routed correctly ---

    def test_kimisko_vielu_is_vide(self):
        motif = "Grozījumi Ķīmisko vielu likumā (1273/Lp14), 2.lasījums, steidzams"
        assert _motif_to_topic(motif) == "Vide"

    def test_udens_apsaimniekosanas_is_vide(self):
        motif = "Grozījumi Ūdens apsaimniekošanas likumā (1275/Lp14), 2.lasījums, steidzams"
        assert _motif_to_topic(motif) == "Vide"

    def test_radiacijas_drosiba_stays_defence(self):
        """Radiation safety IS national security, not environment."""
        motif = "Grozījumi likumā \u201cPar radiācijas drošību un kodoldrošību\u201d"
        assert _motif_to_topic(motif) == "Aizsardzība un drošība"

    def test_nato_is_exact_word_match(self):
        """Full-word match: `NATO` must match the abbreviation, not a
        future Latvian word that happens to contain those letters.
        """
        assert _motif_to_topic("Par NATO dalībvalsts atbalstu") == "Aizsardzība un drošība"

    # --- Stems still work across Latvian inflections ---

    def test_parvald_stem_still_matches_inflections(self):
        assert _motif_to_topic("Grozījumi Valsts pārvaldes iekārtas likumā") == "Valsts pārvalde"
        assert _motif_to_topic("Pārvaldība un reforma") == "Valsts pārvalde"

    # --- "Bērnu tiesību aizsardzīb" must NOT fall through to 'tiesību aizsardzīb' ---

    def test_bernu_tiesibu_aizsardzib_is_social_not_justice(self):
        """Child-protection law is a social-policy framework (child welfare,
        family policy). The 'tiesību aizsardzīb' rule (law-enforcement
        bodies) must not claim it. 2026-04-01 regression.
        """
        motif = "Grozījums Bērnu tiesību aizsardzības likumā (1257/Lp14), 1.lasījums"
        assert _motif_to_topic(motif) == "Sociālā politika"

    # --- Cultural institutions must not fall through to "nacionāl" → defence ---

    def test_concert_hall_is_kultura_not_defence(self):
        """`topic_map._SAEIMA_KEYWORD_MAP` catches 'nacionāl' as defence,
        so 'Nacionālās koncertzāles' bills used to end up under 'Aizsardzība
        un drošība'. Culture-specific rules must win first.
        """
        motif = "Nacionālās koncertzāles \u201cRīgas filharmonija\u201d likums (1217/Lp14), 3.lasījums"
        assert _motif_to_topic(motif) == "Kultūra"

    def test_library_law_is_kultura(self):
        motif = "Grozījumi Bibliotēku likumā (1284/Lp14), 1.lasījums"
        assert _motif_to_topic(motif) == "Kultūra"

    def test_museum_law_is_kultura(self):
        assert _motif_to_topic("Grozījumi Muzeju likumā") == "Kultūra"


class TestStep35Discipline:
    """2026-05-16 regress: 21 saeima_votes rows landed with summary IS NULL
    because @saeima-tracker dispatches skipped Step 3.5 (read bill text +
    write summary). Resulting claim stances were generic "Balsoja PAR:
    <motif>" instead of "Atbalsta: <substance>". The trīslīmeņu fix
    (CHANGELOG 2026-05-16) makes summary writable at store_vote time AND
    surfaces missing summaries via a warning log.
    """

    def test_store_vote_persists_summary_inline(self, saeima_db):
        """store_vote() accepts summary/document_url/document_nr keyword args
        and writes them in the same INSERT — eliminating the NULL→UPDATE
        pattern that historically allowed Step 3.5 to be silently skipped.
        """
        vote = VoteResult(
            motif="Grozījumi Testa likumā (9999/Lp14), 2.lasījums",
            date="2026-05-16", time="10:00",
            total_par=85, total_pret=0, total_atturas=0, total_nebalso=15,
            result="Pieņemts",
            url="https://example.com/vote",
            individual_votes=[],
        )
        vote_id = store_vote(
            vote,
            db_path=saeima_db,
            summary="Paplašina X lauka regulējumu, transponē ES Direktīvu Y.",
            document_url="https://titania.saeima.lv/livs14/.../doc",
            document_nr="9999/Lp14",
        )
        db = get_db(saeima_db)
        row = db.execute(
            "SELECT summary, document_url, document_nr FROM saeima_votes WHERE id = ?",
            (vote_id,),
        ).fetchone()
        db.close()
        assert row["summary"] == "Paplašina X lauka regulējumu, transponē ES Direktīvu Y."
        assert row["document_nr"] == "9999/Lp14"
        assert row["document_url"].endswith("/doc")

    def test_store_vote_summary_optional(self, saeima_db):
        """Backward-compat: store_vote() without summary kwarg still works;
        summary column stays NULL (procedural votes, legacy callers).
        """
        vote = VoteResult(
            motif="Procedūras balsojums bez likumprojekta",
            date="2026-05-16", time="10:01",
            total_par=50, total_pret=40, total_atturas=10, total_nebalso=0,
            result="Pieņemts",
            url="https://example.com/proc",
            individual_votes=[],
        )
        vote_id = store_vote(vote, db_path=saeima_db)
        db = get_db(saeima_db)
        row = db.execute(
            "SELECT summary FROM saeima_votes WHERE id = ?", (vote_id,)
        ).fetchone()
        db.close()
        assert row["summary"] is None

    def test_generate_claims_warns_on_billlike_motif_without_summary(self, saeima_db, monkeypatch):
        """Layer-1 detection: bill-like motif (matches \\(N/L[pm]14\\)) without
        summary writes a saeima_summary_missing warning to logs. This is the
        signal that Step 3.5 was skipped — the post-routine verification gate
        and operator review surface it before regressing 1500+ claim stances
        again.
        """
        # DB_PATH is late-bound in src.db (resolved at call time by get_db),
        # so patching the single src.db.DB_PATH global is sufficient; the old
        # src.saeima.votes.DB_PATH re-export no longer exists.
        monkeypatch.setattr("src.db.DB_PATH", saeima_db)
        vote = VoteResult(
            motif="Grozījumi Lielā likumā (8888/Lp14), 2.lasījums, steidzams",
            date="2026-05-16", time="11:00",
            total_par=83, total_pret=0, total_atturas=0, total_nebalso=17,
            result="Pieņemts",
            url="https://example.com/missing-summary",
            individual_votes=[IndividualVote(
                deputy_name="Test Deputāts", faction="JV", vote="Par", politician_id=1
            )],
        )
        vote_id = store_vote(vote, db_path=saeima_db)  # no summary
        generate_claims_from_votes(vote, vote_id, db_path=saeima_db)

        db = get_db(saeima_db)
        warn_rows = db.execute(
            "SELECT details FROM logs WHERE action = 'saeima_summary_missing' AND status = 'warning'"
        ).fetchall()
        db.close()
        assert len(warn_rows) == 1, "exactly one warning expected per bill-like vote without summary"

    def test_generate_claims_no_warning_when_summary_present(self, saeima_db, monkeypatch):
        """Inverse: writing summary inline at store_vote() time means
        generate_claims_from_votes finds it and produces no warning row.
        """
        # DB_PATH is late-bound in src.db (resolved at call time by get_db),
        # so patching the single src.db.DB_PATH global is sufficient; the old
        # src.saeima.votes.DB_PATH re-export no longer exists.
        monkeypatch.setattr("src.db.DB_PATH", saeima_db)
        vote = VoteResult(
            motif="Grozījumi Cilvēktiesību likumā (7777/Lp14), 1.lasījums",
            date="2026-05-16", time="11:01",
            total_par=80, total_pret=5, total_atturas=0, total_nebalso=15,
            result="Pieņemts",
            url="https://example.com/with-summary",
            individual_votes=[IndividualVote(
                deputy_name="Test Deputāts", faction="JV", vote="Par", politician_id=1
            )],
        )
        vote_id = store_vote(
            vote, db_path=saeima_db,
            summary="Stiprina cilvēktiesību aizsardzību publiskajā pārvaldē.",
        )
        generate_claims_from_votes(vote, vote_id, db_path=saeima_db)

        db = get_db(saeima_db)
        warn_rows = db.execute(
            "SELECT details FROM logs WHERE action = 'saeima_summary_missing'"
        ).fetchall()
        db.close()
        assert warn_rows == [], "no warning expected when summary is set inline"

    def test_generate_claims_no_warning_on_procedural_motif(self, saeima_db, monkeypatch):
        """Procedural votes without a bill reference (no (N/Lp14) / (N/Lm14)
        in motif) are exempt from the discipline — image-only PDFs, no-conf
        motions, presidential appointments etc. legitimately have no bill
        text to summarize.
        """
        # DB_PATH is late-bound in src.db (resolved at call time by get_db),
        # so patching the single src.db.DB_PATH global is sufficient; the old
        # src.saeima.votes.DB_PATH re-export no longer exists.
        monkeypatch.setattr("src.db.DB_PATH", saeima_db)
        vote = VoteResult(
            motif="Par neuzticības izteikšanu Ministru prezidentam",
            date="2026-05-16", time="11:02",
            total_par=42, total_pret=50, total_atturas=0, total_nebalso=8,
            result="Noraidīts",
            url="https://example.com/procedural",
            individual_votes=[IndividualVote(
                deputy_name="Test Deputāts", faction="JV", vote="Pret", politician_id=1
            )],
        )
        vote_id = store_vote(vote, db_path=saeima_db)  # no summary
        generate_claims_from_votes(vote, vote_id, db_path=saeima_db)

        db = get_db(saeima_db)
        warn_rows = db.execute(
            "SELECT details FROM logs WHERE action = 'saeima_summary_missing'"
        ).fetchall()
        db.close()
        assert warn_rows == [], "no warning expected for procedural (non-bill) motif"
