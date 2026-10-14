"""`scripts/audit_topic_canonical.py` — /audit-integrity 18. pārbaudes tests.

KĀPĒC ŠĪ PĀRBAUDE PASTĀV (verdikts 24, 2026-09-06)
`src/tools.py::store_claim` normalizē `topic`, `src/db.py::store_claim` ne —
un `topic` ir daļa no idempotences atslēgas `(opponent_id, source_url, topic)`.
Operatora lēmums bija NEMAINĪT `db.store_claim` (atslēgas maiņa bez sausā
palaidiena ir tā pati klase, kas 2026-08-02 saražoja 4 087 dublikātus), bet
uzlikt vārtu: ne-kanonisko `position` tēmu skaits pret `src/topic_map.py`
33 kanoniskajām grupām. Bāzlīnija 2026-09-07: `flagged=0`, 33 no 33.

VĀRTS, KAS NEVAR KRIST, NAV PIERĀDĪJUMS. Tāpēc `checked=0` ir kļūda (izejas
kods 2), ne "tīrs rezultāts" — tieši tāpat kā 7. pārbaude gadu skenēja vienu
failu un ziņoja "tīrs".
"""
from __future__ import annotations

import os
import sqlite3
import tempfile

import pytest

from scripts.audit_topic_canonical import audit_topics, run_audit

CANON = {"Aizsardzība un drošība", "Tieslietas", "Izglītība"}


def _mkdb(rows):
    """rows: list of (topic, claim_type)."""
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    db = sqlite3.connect(path)
    db.execute(
        "CREATE TABLE claims (id INTEGER PRIMARY KEY AUTOINCREMENT, "
        "topic TEXT, claim_type TEXT)"
    )
    for topic, ctype in rows:
        db.execute("INSERT INTO claims (topic, claim_type) VALUES (?, ?)", (topic, ctype))
    db.commit()
    db.close()
    return path


@pytest.fixture
def cleanup():
    paths: list[str] = []
    yield paths
    for p in paths:
        try:
            os.unlink(p)
        except (PermissionError, FileNotFoundError):
            pass


def _audit(path, canonical=CANON):
    db = sqlite3.connect(path)
    db.row_factory = sqlite3.Row
    try:
        return audit_topics(db, canonical)
    finally:
        db.close()


def test_all_canonical_reports_zero_with_a_denominator(cleanup):
    path = _mkdb([("Tieslietas", "position"), ("Izglītība", "position")])
    cleanup.append(path)
    res = _audit(path)
    assert res["checked"] == 2
    assert res["distinct"] == 2
    assert res["canonical"] == 3
    assert res["flagged"] == 0
    assert res["rows"] == []


def test_non_canonical_topic_is_flagged_with_count_and_sample(cleanup):
    path = _mkdb(
        [
            ("Tieslietas", "position"),
            ("Drošības politika", "position"),
            ("Drošības politika", "position"),
        ]
    )
    cleanup.append(path)
    res = _audit(path)
    assert res["checked"] == 3
    assert res["flagged"] == 1
    topic, count, sample_id = res["rows"][0]
    assert topic == "Drošības politika"
    assert count == 2
    assert sample_id == 2  # mazākais id ar šo tēmu — lasāms ieejas punkts triāžai


def test_non_position_claim_types_are_out_of_scope(cleanup):
    """`saeima_vote` tēmas nāk no `_motif_to_topic()` un apzināti evolucionē;
    programmas solījumi renderējas tikai partijas lapā. Vārts ir par
    `position` — to pašu klasi, ko `claim_type='position'` vārti visur citur."""
    path = _mkdb(
        [
            ("Tieslietas", "position"),
            ("Kaut kāda balsojuma tēma", "saeima_vote"),
            ("Programmas tēma", "program_promise"),
        ]
    )
    cleanup.append(path)
    res = _audit(path)
    assert res["checked"] == 1
    assert res["flagged"] == 0


def test_empty_denominator_is_a_broken_gate_not_a_clean_run(cleanup):
    path = _mkdb([("Kaut kas", "saeima_vote")])
    cleanup.append(path)
    res = _audit(path)
    assert res["checked"] == 0
    assert run_audit(path, canonical=CANON) == 2


def test_exit_codes(cleanup):
    clean = _mkdb([("Tieslietas", "position")])
    dirty = _mkdb([("Tieslietas", "position"), ("Nekanoniska", "position")])
    cleanup.extend([clean, dirty])
    assert run_audit(clean, canonical=CANON) == 0
    assert run_audit(dirty, canonical=CANON) == 1


def test_default_canonical_set_is_the_topic_map_33():
    from src.topic_map import get_all_group_names

    from scripts.audit_topic_canonical import canonical_topics

    assert canonical_topics() == set(get_all_group_names())
    assert len(canonical_topics()) == 33
