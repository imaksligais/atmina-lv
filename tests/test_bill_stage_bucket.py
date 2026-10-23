"""Tīrā loģika: likumprojekta grupa joslā «kur tagad» un grozāmā likuma
nosaukums no virsraksta. Kļūmes: steidzams likums (pieņemts 2. lasījumā)
krita «pieņemti 2. lasījumā»; lēmumi/paziņojumi iejaucās likumprojektu joslā;
locījums «Krimināllikumā» parādījās kā likuma nosaukums; kartītēs bija
iekšējie stadiju kodi («tiesneša_amats», «Lm14 cits»); steidzama likuma
kartīte rādīja «2. lasījums · pieņemts» (izklausās pēc «pieņemts 2. lasījumā»),
kamēr josla to sauc «Kļuvuši par likumu»."""

import pytest

from src.render.bills import _stage_bucket, _stage_label, amended_law_name, card_status


@pytest.mark.parametrize("bt,stage,status,want", [
    ("Lp14", "3.lasījums", "pieņemts", "pienemts"),
    ("Lp14", "2.lasījums", "pieņemts", "pienemts"),   # steidzams / ratifikācija
    ("Lp14", "iesniegts", "noraidīts", "noraidits"),
    ("Lp14", "1.lasījums", "noraidīts", "noraidits"),
    ("Lp14", "iesniegts", "procesā", "iesniegts"),
    ("Lp14", "1.lasījums", "procesā", "pec1"),
    ("Lp14", "2.lasījums", "procesā", "pec2"),
    ("Lp14", "3.lasījums", "procesā", "pec2"),
    ("Lp14", None, "procesā", "nav"),
    ("Lp14", "procesuāls", "procesā", "nav"),
    ("Lp15", "jauna_stadija", "procesā", "nav"),
    ("Lm14", "tiesneša_amats", "pieņemts", ""),
    ("P14", "paziņojuma_balsojums", "noraidīts", ""),
    ("Lp14", "atsaukts", "atsaukts", "atsaukts"),   # 1525/Lp14, 2026-10-20
])
def test_stage_bucket(bt, stage, status, want):
    assert _stage_bucket(bt, stage, status) == want


@pytest.mark.parametrize("title,want", [
    ("Grozījumi Krimināllikumā", "Krimināllikums"),
    ("Grozījums Krimināllikumā", "Krimināllikums"),
    ("Grozījumi Ceļu satiksmes likumā", "Ceļu satiksmes likums"),
    ("Grozījumi likumā “Par iedzīvotāju ienākuma nodokli”", "«Par iedzīvotāju ienākuma nodokli»"),
    ("Grozījumi Militārā poligona “Sēlija” izveides likumā", "Militārā poligona “Sēlija” izveides likums"),
    ("Grozījumi Saeimas kārtības rullī", None),
    ("Grozījums Latvijas Republikas Satversmē", None),
    ("Valsts sporta fonda likums", None),
    ("Grozījumi Administratīvo sodu likumā par pārkāpumiem pārvaldes jomā", None),
])
def test_amended_law_name(title, want):
    assert amended_law_name(title) == want


@pytest.mark.parametrize("stage,want", [
    ("tiesneša_amats", "lēmums par tiesneša amatu"),
    ("Lm14 cits", "lēmums"),
    ("Lm15 cits", "lēmums"),
    ("nezināms", None),
    (None, None),
    ("jauna_stadija", "jauna_stadija"),
    ("2.lasījums", "2. lasījums"),
])
def test_stage_label(stage, want):
    assert _stage_label(stage) == want


@pytest.mark.parametrize("bt,stage,status,want", [
    ("Lp14", "2.lasījums", "pieņemts", "kļuvis par likumu"),   # steidzams
    ("Lp14", "3.lasījums", "pieņemts", "kļuvis par likumu"),
    ("Lp14", "2.lasījums", "procesā", "2. lasījums · procesā"),
    ("Lp14", "1.lasījums", "noraidīts", "1. lasījums · noraidīts"),
    ("Lm14", "tiesneša_amats", "pieņemts", "lēmums par tiesneša amatu · pieņemts"),
    ("Lp14", "nezināms", "procesā", "procesā"),
    ("Lp14", "2.lasījums", None, "2. lasījums"),
    ("P14", "atsaukts", "atsaukts", "atsaukts"),     # ne «atsaukts · atsaukts»
])
def test_card_status(bt, stage, status, want):
    assert card_status(bt, stage, status) == want
