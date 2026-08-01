"""Tests for src/quality.py — text validation guardrails."""

import pytest

from src.quality import restore_text_from_source, validate_lv_diacritics


class TestValidateLvDiacritics:
    """Diacritic guardrail for Latvian text fields."""

    def test_latvian_with_diacritics_passes(self):
        text = (
            "Siliņa paziņo koalīcijas turpināšanu pēc krīzes sarunām. "
            "Gatava upurēt koalīciju airBaltic atbalsta dēļ."
        )
        ok, reason = validate_lv_diacritics(text)
        assert ok is True, reason

    def test_latvian_without_diacritics_fails(self):
        text = (
            "Silina pazino koalicijas turpinasanu pec krizes sarunam. "
            "Gatava upuret koaliciju airBaltic atbalsta del."
        )
        ok, reason = validate_lv_diacritics(text)
        assert ok is False
        assert "diacritic" in reason.lower() or "stripped" in reason.lower()

    def test_short_text_passes_without_check(self):
        # Short text can't be reliably classified
        text = "Spruds par ANO."
        ok, _ = validate_lv_diacritics(text)
        assert ok is True

    def test_empty_text_passes(self):
        assert validate_lv_diacritics("")[0] is True
        assert validate_lv_diacritics(None)[0] is True

    def test_russian_text_skipped(self):
        # Cyrillic-heavy text should not trigger LV validation
        text = (
            "Президент России выступил на конференции в Москве "
            "и обсудил вопросы безопасности с европейскими лидерами."
        )
        ok, reason = validate_lv_diacritics(text)
        assert ok is True
        assert "cyrillic" in reason.lower() or "non-latvian" in reason.lower()

    def test_english_text_skipped(self):
        # English text without LV stopwords should not be validated
        text = (
            "The president announced new policies regarding national "
            "security and international cooperation with allies."
        )
        ok, reason = validate_lv_diacritics(text)
        assert ok is True
        assert "latvian" in reason.lower() or "marker" in reason.lower()

    def test_topic_field_short_passes(self):
        # Topic field is typically short — shouldn't be flagged
        ok, _ = validate_lv_diacritics("Koalicija")
        assert ok is True

    def test_partial_diacritics_above_threshold_passes(self):
        # Latvian text with a few diacritics still passes (~3% is fine)
        text = (
            "Speciālists analizē airBaltic ienemumu sadalu un eksporta "
            "potencialu, kā arī obligaciju turetaju interesi par 30M aizdevumu."
        )
        # This has SOME diacritics ("Speciālists", "kā") — should pass
        ok, _ = validate_lv_diacritics(text)
        assert ok is True

    def test_uppercase_diacritics_counted(self):
        # ĀĒĪŪŅĻĶĢŠŽČ should count as diacritics
        text = (
            "ĀRĒJĀS politikas jautājumi un Šveices ekonomika ir svarīgi "
            "valstij, jo no tā ir atkarīga arī mūsu eksporta nākotne."
        )
        ok, _ = validate_lv_diacritics(text)
        assert ok is True

    def test_real_world_failure_case(self):
        # Actual broken claim from DB (claim #7521)
        text = "Daudz tiek runats par airBaltic izmaksu sadalu, bet ne tik daudz par ienemumu sadalu."
        ok, _ = validate_lv_diacritics(text)
        assert ok is False

    # ------------------------------------------------------------------
    # Regression fixtures: the eleven stances that reached the LIVE site
    # fully de-diacritised (created 2026-04-09..04-16 during T4 context
    # drift, corrected 2026-08-02). Every one of them PASSED this gate
    # before the fix, which is why they shipped.
    #
    # Mechanism worth remembering: fasttext does not confidently recognise
    # stripped Latvian — it returned lv 0.13-0.32 for five of these and
    # fr/lt/pl/sl/ur 0.13-0.19 for the rest. That unconfident verdict then
    # let the "not enough Latvian markers" escape fire, because a short
    # noun-dense stance scores 0-1 LV markers. The text never reached the
    # ratio check, the only test that can see stripping.
    # ------------------------------------------------------------------

    STRIPPED_LIVE_STANCES = [
        "Brinina ka IT iepirkumu kartela dalibnieki bijusi iesaistiti velesanu IT sistemu izstrade",
        "Kritize Finansu ministriju par izvairishanos uzniemties atbildibu Rail Baltica finansejuma jautajuma",
        "Iesniedz priekslikumus taksometru nozares reformai: vienota licencesanas sistema, viena licence visai Latvijai, platformu komisijas maksas griesti 15%",
        "SM tiks reorganizeta, jo nespej nodrosinat strategisku procesu vadibu - premjere parnem airBaltic procesa vadibu",
        "Degvielas cenu merkis 1.80-1.90 EUR/l - akcizes samazinajums nenesIs rezultatu, EM iesniedz papildu priekslikumus",
        "Publicee Citskovska atkla jumus - VK vaditajs atteica apmaksat Silinas rekinu, tika atlaists no darba",
        "Kritize Kulturas ministrijas (Progresivie) izsludinato konkursu uz JRT direktora vietu - apdraud teatra stabilitati",
        "Atsedz Rigas Siltuma valdes locekles 7 dienu komandejumu uz Spaniju - konference bija 3 dienas",
        "Atbalsta grozijumus Valsts parvaldes iekartas likuma - vienkarsot publisku kapitalsabiedribu dibinasanu",
        "Dubultpilsoni nedrikst but Saeimas deputati - NA un AS atbalsts ir patriotisma maska",
        "airBaltic aizdevuma balsojumam jabut sodien, SM ministra politiska atbildiba, SM reorganizacija",
    ]

    @pytest.mark.parametrize("text", STRIPPED_LIVE_STANCES)
    def test_stripped_live_stances_are_rejected(self, text):
        ok, reason = validate_lv_diacritics(text)
        assert ok is False, f"stripped stance slipped through: {reason}"

    def test_diacritic_light_but_correct_latvian_still_passes(self):
        """A real claim (#1563) with ONE diacritic in 84 letters = 1.19%.

        Correct Latvian; the words simply do not take diacritics. An earlier
        version of the 2026-08-02 fix rejected this. At a write boundary a
        rejection is a refused row, so a false positive here is not cosmetic —
        it blocks a legitimate claim.
        """
        text = ("Panācis Satversmes tiesas spriedumu — krievu valoda "
                "sabiedriskajos medijos neatbilst Satversmei")
        ok, reason = validate_lv_diacritics(text)
        assert ok is True, reason

    def test_unconfident_fasttext_does_not_excuse_zero_diacritics(self):
        """The core of the 2026-08-02 fix, stated as behaviour.

        fasttext being UNSURE is not evidence of NOT-Latvian. Escaping the
        ratio check now needs a positive non-LV signal, never the mere absence
        of Latvian markers.
        """
        text = ("Atsedz Rigas Siltuma valdes locekles 7 dienu komandejumu uz "
                "Spaniju - konference bija 3 dienas")
        assert validate_lv_diacritics(text)[0] is False

    def test_genuine_english_still_skipped(self):
        """Regression guard in the opposite direction — the EN escape must
        survive the tightening, or Braže/Rinkēvičs English posts start failing.
        """
        for text in (
            "Latvia stands with Ukraine and will continue supporting its defence "
            "against Russian aggression for as long as it takes.",
            "Glad to meet colleagues today and discuss the next steps for our "
            "joint infrastructure programme.",
        ):
            ok, reason = validate_lv_diacritics(text)
            assert ok is True, f"English wrongly rejected: {reason}"


class TestRestoreTextFromSource:
    """Restore diacritics in stripped text by matching against the source
    document that has the original diacritics intact.
    """

    def test_exact_substring_restored(self):
        source = "Es jau gara acīm redzu atbildes uz šo tvītu par nabadzīgiem pensionāriem."
        stripped = "gara acim redzu atbildes uz so tvitu par nabadzigiem"
        restored = restore_text_from_source(stripped, source)
        assert restored == "gara acīm redzu atbildes uz šo tvītu par nabadzīgiem"

    def test_full_quote_restored(self):
        source = (
            "Daudz tiek runāts par airBaltic izmaksu sadaļu, bet ne tik daudz "
            "publiskajā telpā mēs dzirdam par ieņēmumu sadaļu."
        )
        stripped = "Daudz tiek runats par airBaltic izmaksu sadalu, bet ne tik daudz par ienemumu sadalu."
        # The exact stripped quote isn't in source — paraphrased. Should fail.
        restored = restore_text_from_source(stripped, source)
        assert restored is None

    def test_case_insensitive_match(self):
        source = "Vai ZZS izmanto airBaltic savu šauro politisko mērķu sasniegšanai?"
        stripped = "vai zzs izmanto airbaltic savu sauro politisko merku sasniegsanai"
        restored = restore_text_from_source(stripped, source)
        # Should find it case-insensitively, return source casing
        assert restored is not None
        assert "šauro" in restored
        assert "mērķu" in restored

    def test_quote_not_in_source_returns_none(self):
        source = "Pilnīgi cits saturs šeit, nekādu pārklāšanos."
        stripped = "kaut kas cits"
        assert restore_text_from_source(stripped, source) is None

    def test_empty_inputs_return_none(self):
        assert restore_text_from_source("", "") is None
        assert restore_text_from_source("", "source") is None
        assert restore_text_from_source("text", "") is None

    def test_too_short_quote_skipped(self):
        # Very short stripped fragments could match anywhere — refuse
        source = "Es jau gara acīm redzu atbildes uz šo tvītu."
        stripped = "es"
        assert restore_text_from_source(stripped, source) is None

    def test_real_world_x_tweet(self):
        # Real source from doc #16920 (Mežals tweet)
        source = (
            "🟥 Kā MĒS 53 minūtes grillējām Saeimas deputātus!\n"
            "Dubultpilsoņi nedrīkst būt Saeimas deputāti un ieņemt augstus valsts amatus!"
        )
        # Stripped version stored as claim quote (claim #7520)
        stripped = "Dubultpilsoni nedrikst but Saeimas deputati un ienemt augstus valsts amatus!"
        restored = restore_text_from_source(stripped, source)
        assert restored == "Dubultpilsoņi nedrīkst būt Saeimas deputāti un ieņemt augstus valsts amatus!"

    def test_restored_text_passes_diacritic_validation(self):
        # Sanity: anything we restore should pass validation
        source = (
            "Premjerministre Evika Siliņa paziņoja par koalīcijas turpināšanu "
            "pēc krīzes sarunām ar partneriem un ZZS frakciju."
        )
        stripped = "paziņoja par koalicijas turpinasanu pec krizes sarunam ar partneriem un ZZS"
        restored = restore_text_from_source(stripped, source)
        assert restored is not None
        ok, _ = validate_lv_diacritics(restored)
        assert ok is True


def test_english_tweet_with_to_preposition_passes():
    """Regression for 2026-04-23: English tweet quoting LV export figures
    was rejected because LV_STOPWORDS includes 'to' (firing on 'exports to
    Russia' → lv_score=2) while EN_MARKERS missed common tokens like 'at',
    'more', 'already'. Should now pass via fasttext detection or expanded
    EN_MARKERS.
    """
    from src.quality import validate_lv_diacritics
    text = (
        "Latvian exports to Russia remain at 70.5 million euros. "
        "Six times more than Estonia already does at this level."
    )
    ok, reason = validate_lv_diacritics(text)
    assert ok, f"English tweet should not be rejected, got: {reason}"


def test_stripped_latvian_still_rejected_despite_fasttext_drift():
    """Guardrail preservation: stripped Latvian must STILL be rejected.
    fasttext misclassifies stripped LV as fr/sr/hr at low confidence, so
    the early-exit (which fires only on conf >= 0.70) doesn't trigger.
    Falls through to the token matcher, which catches it via LV_STOPWORDS
    and the low-diacritic ratio.
    """
    from src.quality import validate_lv_diacritics
    # Real-world stripped LV: 'Daudz tiek runats par partija koalicija budzets
    # un tie netiek risinati tomer valsts parvalde turpinas ka ierasts.'
    text = (
        "Daudz tiek runats par partija koalicija un budzets bet tie netiek "
        "risinati tomer valsts parvalde turpinas ka ierasts — tas nav labi."
    )
    ok, reason = validate_lv_diacritics(text)
    assert not ok, f"Stripped Latvian should be rejected, got ok=True with reason: {reason}"
    assert "stripped" in reason.lower() or "diacritic" in reason.lower()


def test_russian_text_passes():
    """Cyrillic/Russian text must pass (already handled by Cyrillic-heavy
    early-return at src/quality.py:88-90). Fasttext would also say 'ru' with
    high confidence. Two independent signals converge on 'accept'.
    """
    from src.quality import validate_lv_diacritics
    text = (
        "Президент и премьер-министр обсудили вопросы безопасности "
        "на встрече в Риге в четверг, а также экспорт в Россию."
    )
    ok, reason = validate_lv_diacritics(text)
    assert ok, f"Russian text should pass, got: {reason}"


def test_genuine_latvian_with_diacritics_passes():
    """Baseline: real Latvian text with proper diacritics must pass.
    No regression from the fasttext early-exit or EN_MARKERS expansion.
    """
    from src.quality import validate_lv_diacritics
    text = (
        "Šodien parlamentā notiek debates par budžeta grozījumiem. "
        "Ministru kabineta sēdē pieņemti lēmumi par ārpolitikas prioritātēm "
        "un sadarbību ar kaimiņvalstīm aizsardzības jomā."
    )
    ok, reason = validate_lv_diacritics(text)
    assert ok, f"Genuine Latvian should pass, got: {reason}"


def test_fasttext_unavailable_is_logged_not_silent(monkeypatch, caplog):
    """When fasttext cannot run, this gate degrades OPEN — so it must say so.

    With ``ft_lang is None`` the "not enough Latvian markers" escape fires
    regardless of diacritics, so fully de-diacritised text walks through — the
    exact input class the gate exists to catch (T4 context drift). Until
    2026-08-15 the ``except`` swallowed the failure with a bare ``pass``, so the
    degradation left no trace at all. The repair for the underlying outage is a
    reliable model load (BACKLOG § fasttext lid-modeļa pārejoša nepieejamība);
    this test only locks in that the outage is VISIBLE.
    """
    import src.ingest
    import src.quality

    def _boom(_text):
        raise RuntimeError("lid.176 unavailable")

    monkeypatch.setattr(src.ingest, "_detect_language", _boom)
    monkeypatch.setattr(src.quality, "_FT_UNAVAILABLE_WARNED", False)

    stripped = (
        "Atsedz Rigas Siltuma valdes locekles 7 dienu komandejumu uz "
        "Spaniju - konference bija 3 dienas"
    )
    caplog.set_level("WARNING", logger="src.quality")
    validate_lv_diacritics(stripped)

    warnings = [r for r in caplog.records if "fasttext lang-ID unavailable" in r.getMessage()]
    assert len(warnings) == 1, f"expected exactly one degradation warning, got {len(warnings)}"
    assert "DEGRADED" in warnings[0].getMessage()

    # Warn ONCE per process: this runs inside bulk extraction loops, and a
    # per-string warning would bury the signal it is meant to raise.
    validate_lv_diacritics(stripped)
    again = [r for r in caplog.records if "fasttext lang-ID unavailable" in r.getMessage()]
    assert len(again) == 1, "warning must be one-shot, not per-call"


def test_ft_model_path_is_repo_relative_not_cwd_dependent(monkeypatch, tmp_path):
    """Candidate #3 fix: the vendored lid.176 model must be located by repo
    position, not process CWD. A CWD-relative path silently falls back to a
    network fetch when the routine runs from a foreign directory, and a failed
    fetch degrades the diacritic gate open (stripped Latvian walks through)."""
    import os as _os

    from src.ingest import _ft_model_path

    monkeypatch.chdir(str(tmp_path))
    path = _ft_model_path()
    assert _os.path.isabs(path)
    assert _os.path.isfile(path), f"vendored model not found at {path}"
    assert _os.path.getsize(path) > 100_000, "vendored model looks truncated"


def test_ft_model_download_retries_and_is_atomic(monkeypatch, tmp_path):
    """The fallback download must retry transient failures and write atomically
    — a partial file poisons the cache and wedges the gate as permanently
    unavailable, which is worse than a one-off fetch failure."""
    import os as _os
    import time
    import urllib.request

    from src.ingest import _FT_MODEL_URL, _download_ft_model

    calls = {"n": 0}

    def _fake_urlretrieve(url, dest):
        assert url == _FT_MODEL_URL
        calls["n"] += 1
        if calls["n"] < 3:
            raise OSError("transient network failure")
        with open(dest, "wb") as fh:
            fh.write(b"FAKE MODEL BYTES")

    monkeypatch.setattr(urllib.request, "urlretrieve", _fake_urlretrieve)
    monkeypatch.setattr(time, "sleep", lambda *a, **k: None)

    model_path = str(tmp_path / "lid.176.ftz")
    _download_ft_model(model_path)

    assert calls["n"] == 3
    with open(model_path, "rb") as fh:
        assert fh.read() == b"FAKE MODEL BYTES"
    assert not _os.path.exists(model_path + ".part")
