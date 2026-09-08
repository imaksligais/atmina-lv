"""Dienas pārskata attēlu variantu pašdziedināšanās tests.

Spec: pirms brief attēlu kopēšanas deploy kokā renderis nodrošina, ka katram
`<slug>.png` blakus ir `-hero.webp`, `-card.webp`, `-thumb.webp` un `-og.jpg`.

Kāpēc šis tests eksistē: `_copy_brief_images` APZINĀTI izlaiž neapstrādātos PNG
masterus (tie nav references nevienā lapā, 75 MB bāreņu). Tāpēc pārskatam, kuram
varianti nekad nav ģenerēti, deploy kokā nenonāk NEKAS — kamēr lapa joprojām
atsaucas uz `<slug>-hero.webp` un `<slug>-og.jpg`. Rezultāts dzīvajā vietnē ir
404 hero un 404 `og:image`, un tieši tas ir aizgājis divreiz (2026-08-02 audits
atrada divus publicētus pārskatus; 2026-08-08 tas atkārtojās un tika noķerts
pirms deploy tikai ar roku veiktā failu pārbaudē).

`analizes` un `synthesis` attēlu mapes jau sen sauc `_ensure_image_variants`;
`briefs` — vienīgā virsma, kur trūkstošs attēls ir tūlīt redzams lasītājam —
to nedarīja.
"""
from src.render._orchestrator import _copy_brief_images, _ensure_image_variants
from src.image_variants import VARIANTS


def _png(path):
    """Uzraksta minimālu, bet īstu PNG (make_variants to atver ar Pillow)."""
    from PIL import Image
    Image.new("RGB", (1376, 768), (200, 190, 170)).save(path)


def test_variants_are_generated_for_a_bare_png(tmp_path):
    src = tmp_path / "briefs"
    src.mkdir()
    _png(src / "2026-08-08-dienas-parskats-abc123.png")

    n = _ensure_image_variants(src)

    assert n == 1
    names = sorted(p.name for p in src.iterdir())
    for suffix in ("-hero.webp", "-card.webp", "-thumb.webp", "-og.jpg"):
        assert f"2026-08-08-dienas-parskats-abc123{suffix}" in names, (
            f"trūkst {suffix} — lapa uz to atsaucas, tāpēc dzīvajā tas būtu 404"
        )
    assert len(VARIANTS) == 4


def test_bare_png_alone_reaches_deploy_tree_as_nothing(tmp_path):
    """Regresijas sargs: BEZ variantu ģenerēšanas deploy koks paliek TUKŠS.

    Šis ir defekta mehānisms — nevis kļūda kopēšanā, bet klusa nulle."""
    src = tmp_path / "briefs"
    src.mkdir()
    dest = tmp_path / "dest"
    dest.mkdir()
    _png(src / "2026-08-08-dienas-parskats-abc123.png")

    assert _copy_brief_images(src, dest) == 0
    assert list(dest.iterdir()) == []


def test_ensure_then_copy_delivers_all_four_variants(tmp_path):
    """Pareizā secība: vispirms pašdziedināšanās, tad kopēšana."""
    src = tmp_path / "briefs"
    src.mkdir()
    dest = tmp_path / "dest"
    dest.mkdir()
    _png(src / "2026-08-08-dienas-parskats-abc123.png")

    _ensure_image_variants(src)
    n = _copy_brief_images(src, dest)

    names = sorted(p.name for p in dest.iterdir())
    assert n == 4
    assert names == [
        "2026-08-08-dienas-parskats-abc123-card.webp",
        "2026-08-08-dienas-parskats-abc123-hero.webp",
        "2026-08-08-dienas-parskats-abc123-og.jpg",
        "2026-08-08-dienas-parskats-abc123-thumb.webp",
    ]
    assert "2026-08-08-dienas-parskats-abc123.png" not in names


def test_rejected_images_are_skipped(tmp_path):
    """Noraidītajiem attēliem variantus NEģenerē.

    `deploy.sh` ir additīvs (`--no-delete`), tāpēc reizi augšuplādēts variants
    paliek serverī mūžīgi. Noraidītie attēli ir kalibrācijas pēdas — nepareiza
    metafora, atsaukts virsraksts, bojāta tipogrāfija — un tiem uz servera nav
    ko darīt pat tad, ja neviena lapa uz tiem nesaista."""
    src = tmp_path / "briefs"
    src.mkdir()
    _png(src / "labais.png")
    _png(src / "noraidits.png")

    n = _ensure_image_variants(src, skip_stems={"noraidits"})

    assert n == 1
    names = sorted(p.name for p in src.iterdir())
    assert "labais-hero.webp" in names
    assert not any(x.startswith("noraidits-") for x in names), (
        f"noraidītajam attēlam uzģenerēti varianti: {names}"
    )


def test_variant_files_are_not_reprocessed(tmp_path):
    """Varianti paši nedrīkst kļūt par avotu jauniem variantiem."""
    src = tmp_path / "briefs"
    src.mkdir()
    _png(src / "brief-1.png")
    _ensure_image_variants(src)
    # Otrā palaide: avotu skaits paliek 1, nevis aug ar variantiem.
    assert _ensure_image_variants(src) == 1
