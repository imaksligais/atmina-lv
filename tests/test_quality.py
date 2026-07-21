"""Tests for src/quality.py — text validation guardrails."""

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
