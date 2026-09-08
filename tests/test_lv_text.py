"""Pin tests for `src/lv_text.py` — the single Latvian transliteration home.

Written BEFORE the six duplicate tables were collapsed (plāna punkts 4.3,
audits §3.1–3.2). Every expected value below was captured from the
implementations as they stood at HEAD `83546921`, so a regression in the
merged helper fails here rather than silently in a slug, a topic name or a
speaker attribution.

Two of the six tables were divergent. The historical tables are inlined as
literals so the merge can be proven, not asserted:

* ``_HIST_TOPIC_MAP`` — lowercase-only (13 zīmes). Behaviour-identical,
  because both call sites lowercased first.
* ``_HIST_QUOTED_SPEAKER`` — missing ``ō``/``ŗ`` (22 zīmes). The ONLY
  intentional behaviour change in 4.3, gated by the real-corpus parity test
  below (0 divergences over 922 DB name/name_forms rows, measured
  2026-09-05).
"""

from pathlib import Path

from src.lv_text import LV_TRANS, fold_lower, slugify, strip_diacritics

# ── Historical tables, verbatim from the pre-4.3 tree ────────────────

_HIST_FULL = str.maketrans(  # wiki.py:29, render/_common.py:160,
    "āčēģīķļņōŗšūžĀČĒĢĪĶĻŅŌŖŠŪŽ",  # quality.py:22, knab/analyze.py:17
    "acegiklnorsuzACEGIKLNORSUZ",
)
_HIST_TOPIC_MAP = str.maketrans("āčēģīķļņōŗšūž", "acegiklnorsuz")  # topic_map.py:387
_HIST_QUOTED_SPEAKER = str.maketrans(  # quoted_speaker.py:24
    "āčēģīķļņšūžĀČĒĢĪĶĻŅŠŪŽ",
    "acegiklnsuzACEGIKLNSUZ",
)

_LOWER_DIACRITICS = "āčēģīķļņōŗšūž"
_UPPER_DIACRITICS = "ĀČĒĢĪĶĻŅŌŖŠŪŽ"

# 45 real names from `SELECT name FROM tracked_politicians WHERE
# relationship_type != 'inactive'` (2026-09-05, read-only), every one
# carrying at least one diacritic. 128 of 196 active rows qualify; this is
# the diacritic-bearing head of that list.
_REAL_NAMES = [
    "Edgars Rinkēvičs", "Evika Siliņa", "Ainārs Šlesers", "Jānis Dombrava",
    "Edvīns Šnore", "Kristaps Krištopans", "Andris Šuvajevs", "Jānis Hermanis",
    "Edmunds Jurēvics", "Baiba Braže", "Andris Sprūds", "Daiga Mieriņa",
    "Arvils Ašeradens", "Roberts Zīle", "Mārtiņš Staķis", "Atis Švinka",
    "Reinis Pozņaks", "Jāzeps Baško", "Ēriks Pucens", "Ārands Ruģēns",
    "Ansis Pūpols", "Maija Armaņeva", "Ričards Šlesers", "Jānis Sārts",
    "Kas Notiek Latvijā", "Ēriks Stendzenieks", "Jurģis Liepnieks",
    "Guntars Vītols", "Elīna Treija", "Anda Čakša", "Kaspars Briškens",
    "Edvards Smiltēns", "Ināra Mūrniece", "Oļegs Burovs", "Juris Viļums",
    "Edmunds Cepurītis", "Skaidrīte Ābrama", "Ingrīda Circene",
    "Česlavs Batņa", "Mārtiņš Daģis", "Artūrs Butāns", "Svetlana Čulkova",
    "Dāvis Mārtiņš Daugavietis", "Jānis Dinevičs", "Mārtiņš Felss",
]


class TestTableCoverage:
    """The merged table must be the widest of the six, not the narrowest."""

    def test_table_is_byte_identical_to_the_four_matching_copies(self):
        assert LV_TRANS == _HIST_FULL

    def test_covers_both_cases_of_every_latvian_diacritic(self):
        assert strip_diacritics(_LOWER_DIACRITICS) == "acegiklnorsuz"
        assert strip_diacritics(_UPPER_DIACRITICS) == "ACEGIKLNORSUZ"

    def test_covers_the_historical_letters_o_macron_and_r_cedilla(self):
        # The exact pair `quoted_speaker._FOLD` was missing.
        assert strip_diacritics("ōŗŌŖ") == "orOR"

    def test_denominator_is_26_characters(self):
        assert len(LV_TRANS) == 26


class TestStripDiacriticsPreservesCase:
    def test_case_survives(self):
        assert strip_diacritics("Āris Šķērslis") == "Aris Skerslis"

    def test_non_latvian_characters_pass_through(self):
        assert strip_diacritics("Test (something) 42 — ok") == "Test (something) 42 — ok"

    def test_cyrillic_untouched(self):
        assert strip_diacritics("Ушаков") == "Ушаков"

    def test_empty(self):
        assert strip_diacritics("") == ""


class TestFoldLower:
    """Pins `quoted_speaker._fold` (translate → lower) exactly."""

    def test_pinned_outputs(self):
        assert fold_lower(_LOWER_DIACRITICS) == "acegiklnorsuz"
        assert fold_lower(_UPPER_DIACRITICS) == "acegiklnorsuz"
        assert fold_lower("Āris Šķērslis") == "aris skerslis"
        assert fold_lower("Evika Siliņa") == "evika silina"
        assert fold_lower("Jānis Bērziņš") == "janis berzins"
        assert fold_lower("Koalīcija un partijas") == "koalicija un partijas"
        assert fold_lower("Test (something)") == "test (something)"
        assert fold_lower("") == ""


class TestSlugify:
    """Pins `wiki._slugify` / `render/_common._slugify` (identical) exactly."""

    def test_pinned_outputs(self):
        assert slugify("Evika Siliņa") == "evika-silina"
        assert slugify("Āris Šķērslis") == "aris-skerslis"
        assert slugify("Jānis Bērziņš") == "janis-berzins"
        assert slugify(_LOWER_DIACRITICS) == "acegiklnorsuz"
        assert slugify(_UPPER_DIACRITICS) == "acegiklnorsuz"
        assert slugify("Test (something)") == "test-something"
        assert slugify("Koalīcija un partijas") == "koalicija-un-partijas"
        assert slugify("") == ""

    def test_double_space_is_NOT_collapsed(self):
        # Published slugs depend on this; collapsing would 404 them.
        assert slugify("Jānis  Bērziņš") == "janis--berzins"

    def test_real_names_slug_to_ascii_only(self):
        for name in _REAL_NAMES:
            slug = slugify(name)
            assert slug.isascii(), name
            assert all(c.isalnum() or c == "-" for c in slug), name


class TestDivergentTablesWereSafeToMerge:
    """The measurement that authorised collapsing the two odd tables."""

    def test_topic_map_table_is_equivalent_on_lowercased_input(self):
        # Both `topic_map` call sites do `.lower()` before `.translate()`,
        # so the lowercase-only table and the full table cannot differ.
        probes = [
            *_REAL_NAMES,
            _LOWER_DIACRITICS,
            _UPPER_DIACRITICS,
            "Koalīcija un partijas",
            "Aizsardzība un drošība",
            "NVO un pilsoniskā sabiedrība",
            "ŌŗĪstais Ŗīgas Ōzols",
        ]
        for probe in probes:
            low = probe.lower()
            assert low.translate(_HIST_TOPIC_MAP) == low.translate(LV_TRANS), probe

    def test_quoted_speaker_table_agrees_on_every_real_name(self):
        # 0 divergences over the full 922-row corpus (225 names + 697
        # name_forms) on 2026-09-05; this is the diacritic-bearing sample.
        for name in _REAL_NAMES:
            old = name.translate(_HIST_QUOTED_SPEAKER).lower()
            assert old == fold_lower(name), name

    def test_quoted_speaker_table_diverged_ONLY_on_o_macron_and_r_cedilla(self):
        # The one intentional change: the old table left `ō`/`ŗ` unfolded.
        old = "ŌŗĪstais Ŗīgas Ōzols".translate(_HIST_QUOTED_SPEAKER).lower()
        assert old == "ōŗistais ŗigas ōzols"
        assert fold_lower("ŌŗĪstais Ŗīgas Ōzols") == "oristais rigas ozols"


class TestOldPrivateNamesStayImportable:
    """Nothing outside `src/lv_text.py` had to change its import."""

    def test_wiki(self):
        from src.wiki import _LV_TRANS, _slugify
        assert _LV_TRANS == LV_TRANS
        assert _slugify("Evika Siliņa") == "evika-silina"

    def test_render_common(self):
        # `src/render/_common/constants.py` re-exports `_LV_TRANS` from here.
        from src.render._common import _LV_TRANS, _slugify
        assert _LV_TRANS == LV_TRANS
        assert _slugify("Evika Siliņa") == "evika-silina"

    def test_quality(self):
        from src.quality import _STRIP_DIACRITICS
        assert _STRIP_DIACRITICS == LV_TRANS

    def test_knab_analyze(self):
        from src.knab.analyze import _LV_TRANS, _normalize_name
        assert _LV_TRANS == LV_TRANS
        assert _normalize_name("  Jānis   Bērziņš ") == "janis berzins"

    def test_topic_map(self):
        from src.topic_map import _STRIP_DIACRITICS
        assert _STRIP_DIACRITICS == LV_TRANS

    def test_quoted_speaker(self):
        from src.quoted_speaker import _FOLD, _fold
        assert _FOLD == LV_TRANS
        assert _fold("Šķērslis") == "skerslis"


class TestNoImportCycle:
    """`src.wiki ↔ src.wiki_lint` was the repo's only import cycle.

    It must be checked in a CLEAN interpreter, not by popping `sys.modules`
    in-process: re-importing `src.wiki` mid-session hands later tests a second
    module object and breaks `wiki_sync` monkeypatching in `tests/test_wiki.py`
    (observed 2026-09-05 while writing this file — 3 false failures).
    """

    def test_importing_wiki_lint_first_needs_no_deferred_import(self):
        import subprocess
        import sys

        proc = subprocess.run(
            [sys.executable, "-c",
             "import src.wiki_lint, src.wiki; "
             "assert src.wiki_lint.lint_wiki_with_db and src.wiki.wiki_sync; "
             "print('ok')"],
            cwd=str(Path(__file__).resolve().parents[1]),
            capture_output=True, text=True,
        )
        assert proc.returncode == 0, proc.stderr
        assert "ok" in proc.stdout

    def test_wiki_lint_has_no_deferred_wiki_import(self):
        src = Path(__file__).resolve().parents[1] / "src" / "wiki_lint.py"
        text = src.read_text(encoding="utf-8")
        # Only the explanatory comment may name the old cycle.
        code = "\n".join(ln for ln in text.splitlines() if not ln.lstrip().startswith("#"))
        assert "from src.wiki import" not in code

    def test_slugify_lives_in_the_leaf_module(self):
        import src.render._common as common
        import src.wiki as wiki

        assert wiki._slugify is slugify
        assert common._slugify is slugify
