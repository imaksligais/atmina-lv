"""Test family-cluster audit: detect 2+ disjoint family clusters per pid."""

from scripts.audit_vad_family_clusters import (
    family_signature,
    cluster_disjoint_families,
)


def test_signature_uses_whole_declared_family():
    """Vecāki un brāļi/māsas desmitgadēm nemainās — tie sasaista deklarācijas
    pirms un pēc laulības. Tikai laulātais+bērni 2026-11-27 deva 21 viltus
    karogu un palaida garām 1 no 5 zināmajiem vārdabrāļiem."""
    before_marriage = family_signature([("Māte", "INESE OZOLA"), ("Brālis", "JĀNIS OZOLS")])
    after_marriage = family_signature([("Laulātais", "ANNA OZOLA"), ("Māte", "INESE OZOLA")])
    clusters = cluster_disjoint_families([(1, before_marriage), (2, after_marriage)])
    assert [c["decl_ids"] for c in clusters] == [[1, 2]]


def test_signature_normalizes_whitespace_and_case():
    fams_a = [("Laulātais", "  Anna  Ozola ")]
    fams_b = [("Laulātais", "ANNA OZOLA")]
    assert family_signature(fams_a) == family_signature(fams_b)


def test_cluster_disjoint_two_unrelated_clusters():
    """Divas deklarācijas ar pilnīgi atšķirīgām ģimenēm = 2 klasteri."""
    decls_with_fams = [
        (1, frozenset({("Laulātais", "ANNA OZOLA")})),
        (2, frozenset({("Laulātais", "MARTA BĒRZIŅA")})),
    ]
    clusters = cluster_disjoint_families(decls_with_fams)
    assert len(clusters) == 2


def test_cluster_disjoint_subset_merges():
    """Ja viena deklarācija ir apakškopa otrai (piem. parsing izlaida bērnu),
    abas pieder vienam klasterim."""
    decls_with_fams = [
        (1, frozenset({("Laulātais", "ANNA OZOLA"), ("Meita", "LAURA OZOLA")})),
        (2, frozenset({("Laulātais", "ANNA OZOLA")})),
    ]
    clusters = cluster_disjoint_families(decls_with_fams)
    assert len(clusters) == 1
    assert {1, 2} == set(clusters[0]["decl_ids"])


def test_cluster_disjoint_overlap_merges():
    """Pārklāšanās vismaz 1 ģimenes loceklim = vienots klasters
    (pievienoti bērni laika gaitā)."""
    decls_with_fams = [
        (1, frozenset({("Laulātais", "ANNA OZOLA")})),
        (2, frozenset({("Laulātais", "ANNA OZOLA"), ("Dēls", "MĀRTIŅŠ OZOLS")})),
        (3, frozenset({("Dēls", "MĀRTIŅŠ OZOLS"), ("Meita", "LAURA OZOLA")})),
    ]
    clusters = cluster_disjoint_families(decls_with_fams)
    assert len(clusters) == 1


def test_empty_family_decls_form_own_cluster_or_skip():
    """Deklarācijas bez ģimenes datiem (vecas dekl < 2010) tiek izlaistas no
    klasterizācijas — nevar pierādīt piederību ne tā, ne tā."""
    decls_with_fams = [
        (1, frozenset()),
        (2, frozenset({("Laulātais", "ANNA OZOLA")})),
    ]
    clusters = cluster_disjoint_families(decls_with_fams)
    assert len(clusters) == 1  # tukšā tiek izlaista
    assert clusters[0]["decl_ids"] == [2]


def test_relation_label_variants_match_same_person():
    """Vecā forma raksta «Sieva»/«Vīrs», jaunā «Laulātais»; to pašu brāli viena
    deklarācija sauc «Brālis», cita «Pusbrālis» — bez kartējuma viens cilvēks
    izskatās pēc diviem."""
    assert family_signature([("Sieva", "ANNA OZOLA")]) == family_signature(
        [("Laulātais", "ANNA OZOLA")])
    assert family_signature([("Vīrs", "JĀNIS OZOLS")]) == family_signature(
        [("Laulātais", "JĀNIS OZOLS")])
    assert family_signature([("pusbrālis", "JĀNIS OZOLS")]) == family_signature(
        [("Brālis", "JĀNIS OZOLS")])


def test_audit_reads_old_format_family_from_raw_html(tmp_path):
    """Vecās formas ģimene `vad_family` netiek rakstīta — audits to lasa no
    `raw_html`. Bez tā divas vecās deklarācijas ar svešām ģimenēm izskatās
    «tīras» (vārti, kas nevar nokrist; 2026-11-27)."""
    import sqlite3
    from pathlib import Path

    from scripts.audit_vad_family_clusters import audit_pid
    from src.vad.schema import init_vad_tables

    html = (Path(__file__).parent / "fixtures" / "vad" / "old-format-2003.html").read_text(
        encoding="utf-8")
    other = (html.replace("TESTA BRĀLIS", "CITS BRĀLIS").replace("TESTA SIEVA", "CITA SIEVA")
             .replace("TESTA MĀTE", "CITA MĀTE"))
    path = str(tmp_path / "t.db")
    db = sqlite3.connect(path)
    db.execute("CREATE TABLE tracked_politicians (id INTEGER PRIMARY KEY, name TEXT)")
    db.execute("INSERT INTO tracked_politicians VALUES (1, 'Testa Persona')")
    db.commit()
    init_vad_tables(path)
    for uuid, raw in (("a", html), ("b", other)):
        db.execute("INSERT INTO vad_declarations(opponent_id, vad_uuid, declaration_type, "
                   "declaration_kind, institution, position_title, source_url, raw_html) "
                   "VALUES (1, ?, 'Kārtējā gada deklarācija - par 2003. gadu', 'annual', "
                   "'TESTA IESTĀDE', 'Docents', 'https://example.test', ?)", (uuid, raw))
    db.commit()
    db.row_factory = sqlite3.Row
    result = audit_pid(db, 1)
    db.close()
    assert result["n_clusters"] == 2
