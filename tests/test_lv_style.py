"""Tests for src.lv_style — LV-stilistikas linteris brief-writer aģentam."""

from src.lv_style import lint_lv_style


def _rules(issues):
    return sorted({i["rule"] for i in issues})


def _matches(issues, rule):
    return [i["match"] for i in issues if i["rule"] == rule]


def test_clean_text_returns_empty():
    text = "Šodien Sprūds (PRO) atbalsta 5 % IKP līniju."
    assert lint_lv_style(text) == []


def test_no_space_before_percent_caught():
    text = "Tērē 5% no IKP aizsardzībai."
    issues = lint_lv_style(text)
    assert "no-space-before-percent" in _rules(issues)
    assert "5%" in _matches(issues, "no-space-before-percent")


def test_decimal_percent_caught():
    text = "Atbalsta 4,5% PVN samazinājumu."
    issues = lint_lv_style(text)
    assert "no-space-before-percent" in _rules(issues)
    assert "4,5%" in _matches(issues, "no-space-before-percent")


def test_anglicism_aksi_caught():
    text = "Latvija virza Rumānijas ekonomisko aksi."
    issues = lint_lv_style(text)
    assert "anglicism" in _rules(issues)
    assert "aksi" in _matches(issues, "anglicism")


def test_anglicism_starta_caught():
    text = "Parakstu vākšanas startā nereaģē."
    issues = lint_lv_style(text)
    assert "anglicism" in _rules(issues)


def test_anglicism_ataka_caught():
    text = "Politiska ataka uz koalīciju."
    issues = lint_lv_style(text)
    assert "anglicism" in _rules(issues)
    assert "ataka" in _matches(issues, "anglicism")


def test_anglicism_polemika_caught():
    text = "Asa polemika par budžetu."
    issues = lint_lv_style(text)
    assert "anglicism" in _rules(issues)
    assert "polemika" in _matches(issues, "anglicism")


def test_table_rows_protected():
    """Markdown tabulu rindas (kas satur claim citātus no extractor) netiek skenētas."""
    text = """
| Politiķis | Pozīcija |
|---|---|
| X | Atbalsta 5% no IKP — startā tērē mazāk |
"""
    assert lint_lv_style(text) == []


def test_context_box_protected():
    """<div class="context-box"> bloki (DB context notes) netiek skenēti."""
    text = """
<div class="context-box">
Saeima 2020. gadā lēma par 5% no IKP. Šis ir startā plāns.
</div>
"""
    assert lint_lv_style(text) == []


def test_html_comment_protected():
    """<!-- DIENAS STATS --> u.c. komentāri netiek skenēti."""
    text = "<!-- 5% pozīcijas -->"
    assert lint_lv_style(text) == []


def test_adjacent_surname_repetition_in_paragraph():
    """Ja DB ir tracked politiķis ar uzvārdu, divreiz blakus paragrāfā = flag."""
    # Šis tests pieņem, ka DB ir vismaz viens politiķis ar uzvārdu garākam par 5
    # simboliem. Mēs vienkārši pārbaudām, ka linter neuzkaras uz reālā DB
    # saraksta, un ka rule kategorija eksistē linterī.
    from src.lv_style import _load_tracked_surnames
    surnames = _load_tracked_surnames()
    if not surnames:
        # Ja DB tukša/nepieejama — skip ar test-level pārliecību
        return
    name = next(iter(surnames))
    text = f"{name} atbalsta priekšlikumu, {name} kritizē komisiju."
    issues = lint_lv_style(text)
    assert "adjacent-surname-repetition" in _rules(issues)
    assert name in _matches(issues, "adjacent-surname-repetition")


def test_multiple_issues_aggregated():
    text = "Aksi un 5% IKP — startā tērē mazāk."
    issues = lint_lv_style(text)
    rules = _rules(issues)
    assert "anglicism" in rules
    assert "no-space-before-percent" in rules


def test_anglicism_melisana_caught():
    """'melīšana' nav LV — pareizais ir 'melošana'."""
    text = "Opozīcija pārmet valdībai melīšanu par budžetu."
    issues = lint_lv_style(text)
    assert "anglicism" in _rules(issues)
    assert "melīšanu" in _matches(issues, "anglicism")


def test_anglicism_konsenss_caught():
    """'konsenss' = anglicisms → 'vienprātība'."""
    text = "Panāca konsensu par reformu."
    issues = lint_lv_style(text)
    assert "anglicism" in _rules(issues)
    assert "konsensu" in _matches(issues, "anglicism")


def test_ol_trap_line_starting_with_number_caught():
    """Rindkopa, kas sākas ar 'N. ' (cipars+punkts+atstarpe), ir markdown
    sakārtota-saraksta slazds — pārlūks apēd ciparu un rāda '1.'."""
    text = "4. jūnijā Saeima lēma par budžeta grozījumiem."
    issues = lint_lv_style(text)
    assert "ol-trap" in _rules(issues)


def test_ol_trap_number_mid_sentence_not_flagged():
    """Datums teikuma vidū (ne rindas sākumā) NAV slazds."""
    text = "Sēde notika 4. jūnijā, kad lēma par budžetu."
    issues = lint_lv_style(text)
    assert "ol-trap" not in _rules(issues)
