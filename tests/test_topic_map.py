"""Tests for src/topic_map.py — topic normalization and grouping."""

from src.topic_map import (
    TOPIC_GROUPS,
    normalize_topic,
    get_group_topics,
    get_all_group_names,
)


class TestNormalizeTopic:
    """Tests for normalize_topic()."""

    def test_direct_match_returns_group(self):
        assert normalize_topic("NATO") == "Aizsardzība un drošība"

    def test_already_group_name_returns_as_is(self):
        assert normalize_topic("Aizsardzība un drošība") == "Aizsardzība un drošība"

    def test_unknown_topic_passthrough(self):
        assert normalize_topic("šis neeksistē") == "šis neeksistē"

    def test_saeima_keyword_match_vide(self):
        assert normalize_topic("Par atkritumu apsaimniekošanu") == "Vide"

    def test_saeima_keyword_match_izglitiba(self):
        assert normalize_topic("Grozījumi Izglītības likumā") == "Izglītība"

    def test_saeima_keyword_match_budzets(self):
        assert normalize_topic("Par nodokļu reformu") == "Budžets un finanses"

    def test_saeima_keyword_match_transports(self):
        assert normalize_topic("Ceļu satiksmes likums") == "Transports"

    def test_saeima_procedural_motion(self):
        assert normalize_topic("Likumprojekta izskatīšana 2. lasījumā") == "Valsts pārvalde"

    def test_saeima_procedural_balsojums(self):
        assert normalize_topic("Balsojums par priekšlikumu") == "Valsts pārvalde"

    def test_airbaltic_variants(self):
        assert normalize_topic("AirBaltic") == "airBaltic"
        assert normalize_topic("airBaltic finansējums") == "airBaltic"

    def test_rail_baltic_typo_coerces_to_rail_baltica(self):
        """'Rail Baltic' (missing trailing 'a') is a non-canonical typo an
        extractor emitted 2026-06-01; the diacritic-strip fallback can't catch
        it (different letters, not diacritics), so it needs an explicit alias.
        It must coerce to canonical 'Rail Baltica'."""
        assert normalize_topic("Rail Baltic") == "Rail Baltica"

    def test_ekonomika_alias_coerces_to_budzets(self):
        """'Ekonomika un finanses' is a non-canonical label earlier writers
        produced. normalize_topic must coerce it to the canonical
        'Budžets un finanses' so position matrices stay consistent.
        """
        assert normalize_topic("Ekonomika un finanses") == "Budžets un finanses"

    def test_immigration_variants(self):
        assert normalize_topic("imigrācija") == "Imigrācija"
        assert normalize_topic("darbaspēka imigrācija") == "Imigrācija"
        assert normalize_topic("ES migrācijas pakts") == "Imigrācija"

    def test_all_raw_topics_normalize_to_their_group(self):
        """Every raw topic in TOPIC_GROUPS must normalize to its group."""
        for group, topics in TOPIC_GROUPS.items():
            for topic in topics:
                result = normalize_topic(topic)
                assert result == group, f"'{topic}' normalized to '{result}', expected '{group}'"


class TestStrippedDiacriticsFallback:
    """When the @claim-extractor agent context-drifts and produces a topic
    without diacritics, normalize_topic must still resolve it to the
    canonical group via diacritic-stripped subtopic matching.
    Real-world cases observed in the 2026-04-16 spike.
    """

    def test_koalicija_resolves_to_koalicija_un_partijas(self):
        # 5 claims in DB had topic "Koalicija" (stripped from "Koalīcija")
        assert normalize_topic("Koalicija") == "Koalīcija un partijas"

    def test_parvaldiba_resolves_to_valsts_parvalde(self):
        # 2 claims had "Parvaldiba" (stripped from "Pārvaldība")
        assert normalize_topic("Parvaldiba") == "Valsts pārvalde"

    def test_arlietas_resolves_to_arpolitika(self):
        # 1 claim had "Arlietas" (stripped from "Ārlietas")
        assert normalize_topic("Arlietas") == "Ārpolitika"

    def test_pilsoniba_resolves_to_sociala_politika(self):
        # 1 claim had "Pilsoniba" (stripped from "Pilsonība")
        assert normalize_topic("Pilsoniba") == "Sociālā politika"

    def test_kultura_resolves_to_kultura_group(self):
        # 1 claim had "Kultura" (stripped from "Kūltūra"). Treated as a
        # first-class topic group since cultural policy / theatre / film
        # are recurring political subjects.
        assert normalize_topic("Kultura") == "Kultūra"

    def test_subtopic_strip_match_is_case_insensitive(self):
        # Case insensitive matching for stripped form
        assert normalize_topic("KOALICIJA") == "Koalīcija un partijas"
        assert normalize_topic("koalicija") == "Koalīcija un partijas"


class TestGetGroupTopics:
    def test_returns_topics_for_known_group(self):
        topics = get_group_topics("Droni")
        assert "dronu incidents" in topics
        assert len(topics) >= 3

    def test_returns_empty_for_unknown_group(self):
        assert get_group_topics("Nav tāds") == []


class TestGetAllGroupNames:
    def test_returns_sorted_list(self):
        names = get_all_group_names()
        assert names == sorted(names)
        assert len(names) == len(TOPIC_GROUPS)

    def test_contains_expected_groups(self):
        names = get_all_group_names()
        assert "Aizsardzība un drošība" in names
        assert "Vēlēšanas" in names
        assert "Imigrācija" in names


class TestTopicGroupIntegrity:
    def test_no_empty_groups(self):
        for group, topics in TOPIC_GROUPS.items():
            assert len(topics) > 0, f"Group '{group}' has no topics"

    def test_no_duplicate_raw_topics(self):
        """If duplicates existed, module import would raise ValueError."""
        seen = set()
        for topics in TOPIC_GROUPS.values():
            for topic in topics:
                assert topic not in seen, f"Duplicate raw topic: '{topic}'"
                seen.add(topic)
