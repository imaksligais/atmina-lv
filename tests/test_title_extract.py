"""Tests for src.title_extract — title extraction from HTML.

Covers signal priority cascade, site-suffix stripping, entity decoding,
length capping, and graceful handling of missing/empty input.
"""
from src.title_extract import extract_title


def test_og_title_wins_over_html_title():
    html = '''<html><head>
        <meta property="og:title" content="Saeimas budžeta debates">
        <title>Saeimas budžeta debates - LSM.lv</title>
    </head></html>'''
    assert extract_title(html) == "Saeimas budžeta debates"


def test_twitter_title_when_no_og():
    html = '''<html><head>
        <meta name="twitter:title" content="Premjere par vēlēšanām">
        <title>Premjere par vēlēšanām | Delfi</title>
    </head></html>'''
    assert extract_title(html) == "Premjere par vēlēšanām"


def test_jsonld_headline_when_no_meta():
    html = '''<html><head>
        <script type="application/ld+json">
        {"@type":"NewsArticle","headline":"Felss par budžetu"}
        </script>
        <title>Felss par budžetu - NRA</title>
    </head></html>'''
    assert extract_title(html) == "Felss par budžetu"


def test_html_title_with_lsm_suffix_stripped():
    html = '<html><head><title>Saeima atbalsta likumprojektu - LSM.lv</title></head></html>'
    assert extract_title(html) == "Saeima atbalsta likumprojektu"


def test_html_title_with_la_suffix_stripped():
    html = '<html><head><title>Kapsētu likums stājas spēkā - Latvijas Avīze</title></head></html>'
    assert extract_title(html) == "Kapsētu likums stājas spēkā"


def test_h1_fallback_when_no_title_tag():
    html = '<html><body><h1>Vēlēšanu IT problēmas</h1><p>...</p></body></html>'
    assert extract_title(html) == "Vēlēšanu IT problēmas"


def test_html_entities_decoded():
    html = '<html><head><title>Siliņa: &quot;Tas ir nepieņemami&quot;</title></head></html>'
    assert extract_title(html) == 'Siliņa: "Tas ir nepieņemami"'


def test_returns_none_for_empty_or_garbage():
    assert extract_title("") is None
    assert extract_title("<html></html>") is None
    assert extract_title(None) is None


def test_length_capped_at_250():
    long = "x" * 400
    html = f'<html><head><title>{long}</title></head></html>'
    out = extract_title(html)
    assert out is not None
    assert len(out) <= 250


def test_strips_whitespace_and_collapses():
    html = '<html><head><title>  Daudz   atstarpju\n\n\nun rindu  </title></head></html>'
    assert extract_title(html) == "Daudz atstarpju un rindu"


def test_og_title_with_reversed_attribute_order():
    """Real-world Yoast SEO and Drupal Metatag sometimes emit content first."""
    html = '<html><head><meta content="Real og title" property="og:title"><title>Wrong - LSM.lv</title></head></html>'
    assert extract_title(html) == "Real og title"


def test_twitter_title_with_reversed_attribute_order():
    html = '<html><head><meta content="Real twitter title" name="twitter:title"><title>Wrong - Delfi</title></head></html>'
    assert extract_title(html) == "Real twitter title"


def test_whitespace_og_title_falls_through_to_next_signal():
    """og:title with whitespace-only content must not kill the cascade."""
    html = '<html><head><meta property="og:title" content="   "><title>Real - LSM.lv</title></head></html>'
    assert extract_title(html) == "Real"


def test_empty_og_title_falls_through_to_next_signal():
    html = '<html><head><meta property="og:title" content=""><title>Real - LSM.lv</title></head></html>'
    assert extract_title(html) == "Real"


def test_single_quoted_attributes():
    html = "<html><head><meta property='og:title' content='Single quoted og'></head></html>"
    assert extract_title(html) == "Single quoted og"


def test_title_tag_with_attributes():
    html = '<html><head><title id="main">Real title - LSM.lv</title></head></html>'
    assert extract_title(html) == "Real title"


def test_suffix_in_middle_not_stripped():
    """Suffix-strip must be anchored at end -- mid-string occurrence stays."""
    html = '<html><head><title>Stāsts par LSM.lv darbu</title></head></html>'
    assert extract_title(html) == "Stāsts par LSM.lv darbu"
