"""Saeimas sasaukums — vienīgā vieta, kur dzīvo sasaukuma numurs.

Titania katram sasaukumam tur atsevišķu bāzi (`LIVS13`, `LIVS14`, …), un
dokumentu numuri nes sasaukuma sufiksu (`1315/Lp14`, `1/Lp15`). Pārslēgšana uz
nākamo sasaukumu ir `SAEIMA_CONVOCATION` maiņa + pārbaude pēc
`docs/plans/2026-09-27-15-saeima-sasaukums.md` § Pārslēgšanas diena.
Numuru paterni jau tagad ir neatkarīgi no sasaukuma, jo pārejas laikā vienā
sēdē var parādīties abu sasaukumu numuri.

Modulis bez projekta iekšējām atkarībām: tas importē tikai standarta
bibliotēku, tāpēc to drīkst importēt gan `src.saeima`, gan `src.render`.
"""
from __future__ import annotations

import re

SAEIMA_CONVOCATION = 14

# Dokumenta numura sufikss jebkuram sasaukumam: Lp14, Lm15, P15 …
# Tieši divi cipari, un aiz tiem nav cipara (`/P140` nav paziņojums).
BILL_SUFFIX = r"(?:Lp|Lm|P)\d{2}(?!\d)"

_BILL_TYPE_RE = re.compile(r"(Lp|Lm|P)(\d{2})")
_BILL_NR_TAIL_RE = re.compile(rf"/({BILL_SUFFIX})$")
_KIND_LABELS = {"Lp": "Likumprojekts", "Lm": "Lēmuma projekts", "P": "Paziņojums"}
_KIND_ORDER = {"Lp": 0, "Lm": 1, "P": 2}


def base_url(convocation: int = SAEIMA_CONVOCATION) -> str:
    """Sasaukuma darba kārtību datubāzes adrese, piem. `…/LIVS14/SaeimaLIVS2_DK.nsf`."""
    return f"https://titania.saeima.lv/LIVS{convocation}/SaeimaLIVS2_DK.nsf"


def is_valid_bill_type(bill_type: str | None) -> bool:
    """`Lp`/`Lm`/`P` + divciparu sasaukums (`Lp14`, `P15`)."""
    return bool(bill_type) and _BILL_TYPE_RE.fullmatch(bill_type) is not None


def bill_type_from_nr(doc_nr: str | None) -> str | None:
    """`'1/Lp15'` → `'Lp15'`; neatpazīstams numurs → `None`."""
    m = _BILL_NR_TAIL_RE.search(doc_nr or "")
    return m.group(1) if m else None


def bill_kind(bill_type: str | None) -> tuple[str, int] | None:
    """`'Lp15'` → `('Likumprojekts', 15)`; neatpazīstams tips → `None`."""
    m = _BILL_TYPE_RE.fullmatch(bill_type or "")
    if not m:
        return None
    return _KIND_LABELS[m.group(1)], int(m.group(2))


def bill_type_sort_key(bill_type: str) -> tuple[int, int, str]:
    """Jaunākais sasaukums pirmais, tad Lp → Lm → P; nezināmie beigās."""
    m = _BILL_TYPE_RE.fullmatch(bill_type or "")
    if not m:
        return (1, 0, bill_type or "")
    return (-int(m.group(2)), _KIND_ORDER[m.group(1)], "")
