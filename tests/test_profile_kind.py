"""Unit tests for ``src.profile_kind.derive_profile_kind``.

Twelve parametrized cases cover all 10 ``ProfileKind`` values plus the
chunk-split + bijuš-prefix filter (the regex bug fix from the design
review — without it, the active deputy in case 6 would mis-classify as
``minister`` because of her former ministerial chunk).
"""

import pytest

from src.profile_kind import derive_profile_kind


@pytest.mark.parametrize(
    "rel,role,votes,expected",
    [
        ("inactive", "Saeimas deputāts", 50, "inactive"),
        ("journalist", "Žurnālists", 0, "journalist"),
        ("organization", "Darba devēju interešu organizācija", 0, "organization"),
        ("neutral", "Politiskais analītiķis", 0, "analyst"),
        ("tracked", "Ministru prezidente", 0, "minister"),
        # Chunk-split bug fix: the "bijusī ... ministre" chunk must be
        # filtered BEFORE substring match, otherwise rule 5 fires first
        # and the active deputy classifies as minister.
        ("tracked", "Saeimas deputāte, bijusī Izglītības un zinātnes ministre", 50, "deputy"),
        ("tracked", "EP deputāts", 0, "mep"),
        # EP leadership role (Roberts Zīle real DB row): substring "ep deputāt"
        # would miss this — ``\bep\b`` word-anchor catches the whole family.
        ("tracked", "EP viceprezidents", 0, "mep"),
        ("tracked", "Rīgas mērs", 0, "regional"),
        ("tracked", "Saeimas deputāts", 70, "deputy"),
        ("tracked", "Bijušais Saeimas priekšsēdētājs", 0, "former"),
        # Real DB row: would mis-classify as `regional` if the bijuš filter
        # only catches ``bijus[aīi]\b`` — ``bijuša`` doesn't word-boundary
        # before the ``i`` in ``bijušais``, leaving the chunk in active_role
        # so rule 7's ``mērs`` substring fires. Broadened ``^biju[sš]``
        # catches it.
        ("tracked", "Bijušais Rēzeknes mērs", 0, "former"),
        ("tracked", "Valdes priekšsēdētājs", 0, "politician"),
        ("tracked", None, 0, "politician"),
    ],
)
def test_derive_profile_kind(rel, role, votes, expected):
    assert derive_profile_kind(rel, role, votes) == expected
