"""Latviešu teksta pamathelperi — VIENA transliterācijas tabula visam repo.

Kāpēc šis modulis eksistē (audits `docs/audits/2026-09-05-struktura-src.md`
§3.1–3.2, plāna punkts 4.3): diakritikas nolaišanas tabula bija iekopēta
**sešās** vietās — četras baitu-identiskas (`wiki.py`, `render/_common.py`,
`quality.py`, `knab_analyze.py`) un divas KLUSI ATŠĶIRĪGAS:

* ``topic_map._STRIP_DIACRITICS`` — tikai mazie burti (13 zīmes). Nekad
  neatšķīrās praksē, jo abi tā izsaukumi ievadu jau bija nolaiduši ar
  ``.lower()``; apvienošana ar pilno tabulu ir bez-uzvedības maiņas.
* ``quoted_speaker._FOLD`` — trūka ``ō`` un ``ŗ`` (22 zīmes). Šī ir
  **defekta klase**, ne apzināts lēmums: divas kaimiņu-moduļu tabulas, kas
  loka atšķirīgi, ražo neatkārtojamu atribūcijas kļūdu. Mērījums pirms
  apvienošanas: 0 atšķirību pār 922 reālām rindām (225 `tracked_politicians`
  vārdi + 697 `name_forms` ieraksti) un 0 pār 33 `claims.topic` vērtībām —
  ``ō``/``ŗ`` mūsdienu latviešu ortogrāfijā nav lietoti, tāpēc DB tos nesatur.
  Tāpēc te ir VIENA tabula, ne variants. Vārti: `tests/test_lv_text.py`
  (vēsturiskās tabulas iekodētas kā literāļi un salīdzinātas pret jauno).

**Šis modulis NAV matčera locīšanas ceļš.** CLAUDE.md shēmas invariants
"matčeris ir substring-balstīts un NElokas diakritiku" attiecas uz
`src/matcher.py`, kas šo moduli neimportē. Te ir tikai slug-veidošana
(URL), fuzzy salīdzināšana (KNAB donoru vārdi, tēmu kanonizācija, citāta
verifikācija) un `quoted_speaker` nominatīva atslēga.

Publiskie nosaukumi: ``LV_TRANS``, ``strip_diacritics``, ``fold_lower``,
``slugify``. Vecie privātie nosaukumi (``_LV_TRANS``, ``_STRIP_DIACRITICS``,
``_FOLD``, ``_slugify``, ``_fold``) paliek importējami no saviem vecajiem
moduļiem kā aliasi, tāpēc ārējie importi (`src/tools.py`, `src/render/*`,
testi) nesalūst.

Blakusefekts: ``_slugify`` pārcelšana šurp likvidē repo vienīgo importu
ciklu ``src.wiki ↔ src.wiki_lint`` — `wiki_lint` vairs neatliek importu uz
funkcijas iekšu, lai cikls neaizvērtos.
"""

from __future__ import annotations

# Vienīgā latviešu diakritikas → ASCII tabula repo. Abi reģistri, ieskaitot
# ``ō``/``ŗ`` (vēsturiskās zīmes; sastopamas vecos tekstos un citātos).
LV_TRANS = str.maketrans(
    "āčēģīķļņōŗšūžĀČĒĢĪĶĻŅŌŖŠŪŽ",
    "acegiklnorsuzACEGIKLNORSUZ",
)


def strip_diacritics(text: str) -> str:
    """Nolaiž latviešu diakritiku, SAGLABĀJOT reģistru (``Š`` → ``S``)."""
    return text.translate(LV_TRANS)


def fold_lower(text: str) -> str:
    """Nolaiž diakritiku UN pārvērš mazajos burtos — salīdzināšanas atslēga.

    Lieto tur, kur avots var būt ar vai bez garumzīmēm (X, RSS, skrāpēts
    HTML) un reģistrs nav nozīmīgs: KNAB donoru vārdi, tēmu kanonizācija,
    `quoted_speaker` nominatīva atslēga.
    """
    return text.translate(LV_TRANS).lower()


def slugify(name: str) -> str:
    """Transliterē latviešu zīmes un pārvērš URL-drošā slugā.

    Mazie burti, atstarpes → defises, pārējais ne-alfanumeriskais nomests.
    Atstarpju kolapss NENOTIEK apzināti — ``"Jānis  Bērziņš"`` dod
    ``"janis--berzins"``; slugi ir jau publicēti un renderēti šajā formā.
    """
    transliterated = name.translate(LV_TRANS)
    slug = transliterated.lower().replace(" ", "-")
    return "".join(c for c in slug if c.isalnum() or c == "-")
