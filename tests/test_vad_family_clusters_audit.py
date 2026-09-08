"""Test family-cluster audit: detect 2+ disjoint immediate-family clusters per pid."""

from scripts.audit_vad_family_clusters import (
    immediate_family_signature,
    cluster_disjoint_families,
)


def test_immediate_family_signature_excludes_extended_family():
    """Tikai laulātais + bērni veido klasteru atslēgu — māsa/brālis/vecāki var
    mainīties mantojuma vai parsēšanas variabilitātes dēļ."""
    fams = [
        ("Laulātais", "ANNA OZOLA"),
        ("Meita", "LAURA OZOLA"),
        ("Māte", "INESE OZOLA"),
        ("Brālis", "JĀNIS OZOLS"),
    ]
    sig = immediate_family_signature(fams)
    assert sig == frozenset({("Laulātais", "ANNA OZOLA"), ("Meita", "LAURA OZOLA")})


def test_signature_normalizes_whitespace_and_case():
    fams_a = [("Laulātais", "  Anna  Ozola ")]
    fams_b = [("Laulātais", "ANNA OZOLA")]
    assert immediate_family_signature(fams_a) == immediate_family_signature(fams_b)


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
