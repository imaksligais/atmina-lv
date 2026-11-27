"""`word_truncate` (Jinja filtrs `word_trunc`) — kļūme, ko tas novērš: teksts
nogriezts vārda vidū («saka, ka em…») vai ar komatu pirms daudzpunktes («,…»)."""

from src.render._common.text import word_truncate


def test_cuts_at_word_boundary_and_drops_trailing_comma():
    text = "Kulbergs saka, ka emisijas jāsamazina, bet budžetā naudas nav"
    out = word_truncate(text, 20)  # 20. zīme krīt vārdā «emisijas»
    assert out == "Kulbergs saka, ka…", out


def test_short_text_unchanged_and_single_ellipsis():
    assert word_truncate("Īss teksts", 50) == "Īss teksts"
    assert word_truncate("viens divi trīs četri", 12).count("…") == 1
