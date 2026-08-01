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


def test_table_cells_scanned_by_mechanical_rules():
    """Kopš 2026-08-09 mehāniskie noteikumi skenē arī tabulu šūnas.

    Tas ir vārtu jēgas tests: `stance` teksts pārskatā dzīvo TABULĀ, un tie ir
    mūsu vārdi, ne citāts. Kamēr tabulas bija aizsargātas, linteris redzēja
    37 % pārskata un „0 problēmu" nozīmēja „neskatījos" (BACKLOG § Dati/DB).
    """
    text = """
| Politiķis | Pozīcija |
|---|---|
| X | Atbalsta 5% no IKP — startā tērē mazāk |
"""
    issues = lint_lv_style(text)
    assert "5%" in _matches(issues, "no-space-before-percent")
    assert "startā" in _matches(issues, "anglicism")


def test_table_cells_not_scanned_by_prose_rules():
    """Prozas noteikumi tabulās NEDRĪKST nostrādāt — tur tie dod viltus
    pozitīvus (2026-08-07 melnraksts: handle sakrita ar uzvārdu)."""
    name = "Ašeradens"
    text = f"""
| Politiķis | Pozīcija |
|---|---|
| {name} | {name} atbalsta, {name} kritizē |
"""
    issues = lint_lv_style(text, surnames={name})
    assert "adjacent-surname-repetition" not in _rules(issues)


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
    """Viens uzvārds divreiz blakus paragrāfā = flag.

    Uzvārdu kopa padota FIKSĒTI, nevis ņemta no dzīvās DB. Iepriekšējā versija
    sākās ar `if not surnames: return`, un kails `return` ir PASS, ne skip —
    tāpēc CI-ā (kur `data/atmina.db` ir gitignorēta) tests gadiem izpildīja
    nulle apgalvojumu par likumu, kuru tam bija jāsargā.
    """
    name = "Ašeradens"
    text = f"{name} atbalsta priekšlikumu, {name} kritizē komisiju."
    issues = lint_lv_style(text, surnames={name})
    assert "adjacent-surname-repetition" in _rules(issues)
    assert name in _matches(issues, "adjacent-surname-repetition")


def test_surname_rule_fires_without_db():
    """4. likumam jāstrādā arī tad, kad DB nav — tas ir CI noklusējums.

    Bez `surnames=` argumenta šis ir tieši tas klusais izlaidiens, kuru
    2026-08-09 vārtu audits atrada: tā pati ievade dod flagu ar DB un „tīrs"
    bez tās.
    """
    import src.db as dbmod
    original = dbmod.DB_PATH
    dbmod.DB_PATH = "E:/atmina/data/__nav_tadas_db__.db"
    try:
        from src.lv_style import _load_tracked_surnames_report
        loaded, reason = _load_tracked_surnames_report()
        assert loaded == set()
        assert reason, "tukšai uzvārdu kopai VIENMĒR jānāk ar iemeslu"
        text = "Ašeradens atbalsta priekšlikumu, Ašeradens kritizē komisiju."
        # Bez padotās kopas likums izlaižas — tas ir dokumentētais stāvoklis.
        assert lint_lv_style(text) == []
        # Ar padoto kopu tas skrien arī bez DB.
        assert "adjacent-surname-repetition" in _rules(
            lint_lv_style(text, surnames={"Ašeradens"})
        )
    finally:
        dbmod.DB_PATH = original


def test_report_names_skipped_rules_when_surnames_empty():
    """Saucējam jārāda, ka likums NEskrēja.

    `coverage_pct` mēra rakstzīmes, tāpēc tukšas uzvārdu kopas gadījumā tas
    joprojām ir 100 % — un tieši tāpēc vien tas nekad nav pietiekams
    pierādījums.
    """
    from src.lv_style import lint_lv_style_report
    rep = lint_lv_style_report("Vienkāršs teikums bez problēmām.", surnames=set())
    assert rep["rules_total"] == 4
    assert rep["rules_run"] == 3
    assert rep["surnames_loaded"] == 0
    assert [s["rule"] for s in rep["rules_skipped"]] == ["adjacent-surname-repetition"]
    assert rep["rules_skipped"][0]["reason"]
    # Teksta ass klusē par šo robu — tas ir šī testa jēgas kodols.
    assert rep["coverage_pct"] == 100.0


def test_report_all_rules_run_when_surnames_present():
    from src.lv_style import lint_lv_style_report
    rep = lint_lv_style_report("Vienkāršs teikums.", surnames={"Ašeradens"})
    assert rep["rules_run"] == rep["rules_total"] == 4
    assert rep["rules_skipped"] == []
    assert rep["surnames_loaded"] == 1


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


def test_report_returns_denominator():
    """`lint_lv_style_report` nosauc, cik daudz teksta tiešām skenēts —
    citādi tukšs saraksts lasās kā „viss tīrs", nevis „neskatījos"."""
    from src.lv_style import lint_lv_style_report
    text = """Naratīva rindkopa par budžetu.

| Politiķis | Pozīcija |
|---|---|
| X | Atbalsta 5 % no IKP |

<div class="context-box">
Konteksta piezīme no context_notes.
</div>
"""
    rep = lint_lv_style_report(text)
    # Mehāniskie noteikumi redz naratīvu + tabulu, bet ne context-box.
    assert rep["scanned_chars"] > rep["prose_scanned_chars"]
    assert rep["scanned_chars"] < rep["total_chars"]
    assert 0 < rep["coverage_pct"] < 100
    assert rep["issues"] == []


def test_report_issues_match_lint_output():
    """Saucēja funkcija nedrīkst atšķirties no pamata lintera atradumiem."""
    from src.lv_style import lint_lv_style_report
    text = "Tērē 5% no IKP aizsardzībai."
    assert lint_lv_style_report(text)["issues"] == lint_lv_style(text)


def test_single_line_context_box_does_not_swallow_rest_of_document():
    """Vienrindas `<div class="context-box">…</div>` drīkst apēst TIKAI sevi.

    Līdz labojumam `_strip_protected_regions` ieslēdza `in_context_box`, kad
    rindā bija atverošais tags, un `continue` nekad nepārbaudīja, vai tajā pašā
    rindā ir arī `</div>`. Karogs palika ieslēgts līdz NĀKAMAJAM `</div>`, tāpēc
    viss teksts pēc boksa klusi izkrita no skenējuma — `coverage_pct` 7,4 % ar
    „0 problēmu" (BACKLOG § Jaunie 2026-08-17 rutīnas karogi).
    """
    text = """<div class="context-box">Konteksta piezīme: 5% no IKP startā.</div>

Naratīvs pēc boksa: Tērē 7% no IKP, un tas ir politiska ataka.
"""
    issues = lint_lv_style(text)
    # Teksts PĒC boksa tiek skenēts.
    assert "7%" in _matches(issues, "no-space-before-percent")
    assert "ataka" in _matches(issues, "anglicism")
    # Paša boksa saturs joprojām ir aizsargāts.
    assert "5%" not in _matches(issues, "no-space-before-percent")
    assert "startā" not in _matches(issues, "anglicism")


def test_single_line_context_box_coverage_stays_high():
    """Vienrindas bokss nedrīkst nogāzt `coverage_pct` līdz ~7 %.

    Skenējamā daļa šeit ir lielākā daļa dokumenta; ja karogs paliek karājoties,
    saucējs nokrīt uz boksa rindas garumu vien.
    """
    from src.lv_style import lint_lv_style_report
    box = '<div class="context-box">Īsa piezīme.</div>'
    body = "\n".join(f"Naratīva rindkopa numur {i} par budžetu un Saeimas sēdi." for i in range(20))
    rep = lint_lv_style_report(f"{box}\n\n{body}\n", surnames={"Ašeradens"})
    assert rep["coverage_pct"] > 90, rep
    assert rep["scanned_chars"] < rep["total_chars"]  # bokss tomēr izgriezts


def test_multiline_context_box_still_protected_after_fix():
    """Daudzrindu bokss paliek aizsargāts, un teksts pēc tā — skenēts."""
    text = """<div class="context-box">
Konteksta piezīme: 5% no IKP startā.
</div>

Naratīvs: Tērē 7% no IKP.
"""
    issues = lint_lv_style(text)
    assert "7%" in _matches(issues, "no-space-before-percent")
    assert "5%" not in _matches(issues, "no-space-before-percent")
    assert "startā" not in _matches(issues, "anglicism")


def test_lint_returns_plain_list_contract_unchanged():
    """Prompti (`brief-writer`, `weekly-brief-writer`) pārbauda `== []`.
    Atgriešanas forma nedrīkst kļūt par dict/tuple."""
    assert lint_lv_style("Tīrs teksts bez problēmām.") == []
    assert isinstance(lint_lv_style("Tērē 5% no IKP."), list)
