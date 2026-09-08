"""Profila Pārskata tēmas čips atver Pozīcijas AR uzliktu tēmas filtru (T4).

Adreses forma: ``politiki/<slug>.html?tema=<URL-kodēta tēma>#pozicijas``.
Šeit pārbaudāms tas, ko dod Python/Jinja puse — pats čips nes kanonisko
tēmu abās formās (kodēto ``href``, nekodēto ``data-topic``), tēma sakrīt ar
kādu no ``#topic-filter`` pogām, un "Kopēt saiti" ir marķēta kopēt
pašreizējo skatu. JS uzvedība (filtra uzlikšana, ?tema= sinhronizācija)
pārbaudīta pārlūkā; šeit — tikai avota līguma punkti, kas saista JS ar
templotes atribūtiem (parametra nosaukums, čipa handleris).

Renderēšanas fikstūras paterns aizgūts no ``tests/test_render_own_pubs.py``.
"""
from datetime import date, timedelta
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

from src.db import get_db, init_db
from src.render._common import _safe_json_filter, _safe_url_filter
from src.render.politicians import render_politicians
from src.saeima.schema import init_saeima_tables

TOPIC = "Aizsardzība un drošība"
TOPIC_ENC = "Aizsardz%C4%ABba%20un%20dro%C5%A1%C4%ABba"
OTHER_TOPIC = "airBaltic"


def _env() -> Environment:
    env = Environment(loader=FileSystemLoader("templates"), autoescape=True)
    env.filters["safe_url"] = _safe_url_filter
    env.filters["safe_json"] = _safe_json_filter
    env.filters["lv_date"] = (
        lambda s: f"{s[8:10]}.{s[5:7]}.{s[:4]}"
        if s and len(s) >= 10 and "-" in s else s or ""
    )
    env.filters["autolink_bills"] = lambda s, *a, **k: s
    env.filters["lv_plural"] = lambda n, *a, **k: ""
    env.globals["assets_version"] = "test"
    return env


def _seed(db_path):
    """Politiķis ar 3 svaigām TOPIC pozīcijām (dominant-topic slieksnis) +
    vienu citas tēmas pozīciju (lai filtra joslā ir vairāk par vienu pogu)."""
    init_db(db_path)
    init_saeima_tables(db_path)
    db = get_db(db_path)
    db.execute("INSERT INTO tracked_politicians (id,name,party,relationship_type) "
               "VALUES (1,'A Kalns','JV','tracked')")
    rows = [(TOPIC, 3), (TOPIC, 4), (TOPIC, 5), (OTHER_TOPIC, 6)]
    for i, (topic, offset) in enumerate(rows, start=1):
        stated = (date.today() - timedelta(days=offset)).isoformat()
        db.execute(
            "INSERT INTO documents (id,content,content_hash,platform,source_domain,"
            "source_url,scraped_at,published_at) VALUES (?,?,?,'web','delfi.lv',?,?,?)",
            (i, f"Teksts {i}", f"h{i}", f"https://delfi.lv/{i}", stated, stated),
        )
        db.execute(
            "INSERT INTO claims (id,opponent_id,document_id,topic,stance,confidence,"
            "source_url,stated_at,claim_type) VALUES (?,?,?,?,?,0.9,?,?,'position')",
            (i, 1, i, topic, f"Pozīcija {i}", f"https://delfi.lv/{i}", stated),
        )
    db.commit()
    return db


def _render(tmp_path) -> str:
    db = _seed(str(tmp_path / "t.db"))
    out = tmp_path / "site" / "atmina"
    out.mkdir(parents=True)
    render_politicians(_env(), db, out, [{
        "id": 1, "name": "A Kalns", "slug": "a-kalns",
        "profile_kind": "politician", "role_label": "deputāts",
        "party": "JV", "x_handle": None,
    }], pid_to_syntheses={})
    return (out / "politiki" / "a-kalns.html").read_text(encoding="utf-8")


# ── čips: kanoniskā tēma + ?tema= adrese ────────────────────────────


def test_topic_chip_links_to_encoded_tema_param(tmp_path):
    """Čipa href = <slug>.html?tema=<URL-kodēta tēma>#pozicijas."""
    html = _render(tmp_path)
    assert f'href="a-kalns.html?tema={TOPIC_ENC}#pozicijas"' in html
    # Diakritika kodēta, nevis ielikta adresē neapstrādāta.
    assert f"?tema={TOPIC}#" not in html


def test_topic_chip_carries_canonical_topic_attribute(tmp_path):
    """data-topic nes NEkodēto kanonisko vērtību — tieši to, ko ppv1.js
    salīdzina ar filtra pogas data-filter."""
    html = _render(tmp_path)
    assert (f'class="parskats-topic-chip" data-tab-link="pozicijas" '
            f'data-topic="{TOPIC}"') in html


def test_chip_topic_matches_an_existing_filter_button(tmp_path):
    """Čipa tēmai jāsakrīt ar reālu #topic-filter pogu, citādi deep-link
    klusi nokrīt uz "Visas tēmas"."""
    html = _render(tmp_path)
    assert f'data-filter="{TOPIC}"' in html
    assert f'data-filter="{OTHER_TOPIC}"' in html
    assert 'data-filter="all"' in html


def test_copy_button_marked_to_copy_current_view(tmp_path):
    """"Kopēt saiti" saglabā kanonisko adresi, bet ir marķēta pārnest arī
    pašreizējo cilni un tēmas filtru (chrome-v1.js [data-copy-state])."""
    html = _render(tmp_path)
    assert 'data-copy-url="https://atmina.lv/politiki/a-kalns.html"' in html
    assert 'data-copy-state="1"' in html


# ── JS↔templote līgums (avota pārbaudes, kā bmv1 testos) ─────────────


def test_ppv1_reads_and_syncs_the_same_tema_param():
    js = Path("assets/ppv1.js").read_text(encoding="utf-8")
    assert '.get("tema")' in js                 # ielādē lasa
    assert 'searchParams.set("tema", topic)' in js   # filtra maiņa raksta
    assert 'searchParams.delete("tema")' in js       # "Visas tēmas" noņem


def test_ppv1_chip_click_applies_topic_filter():
    js = Path("assets/ppv1.js").read_text(encoding="utf-8")
    assert "if (link.dataset.topic) setTopic(link.dataset.topic, true);" in js


def test_ppv1_never_interpolates_a_topic_into_a_selector():
    """Nevalidēta URL/čipa vērtība nedrīkst nonākt CSS selektorā —
    pogu meklē, pārstaigājot sarakstu (topicButton)."""
    js = Path("assets/ppv1.js").read_text(encoding="utf-8")
    assert "data-filter=" not in js
    assert "function topicButton(topic)" in js


def test_copy_handler_falls_back_to_canonical_url():
    js = Path("assets/chrome-v1.js").read_text(encoding="utf-8")
    assert "btn.hasAttribute('data-copy-state')" in js
    # try/catch → ja URL/location nav pieejams, paliek data-copy-url vērtība.
    assert "catch (err) { /* fallback: kanoniskā adrese */ }" in js


# ── Tēmu filtra josla: skaitlis, secība pēc biežuma, sakļaušana ──────────
# (2026-09-07: 33 tēmu čipu mākonis ar sarkanu aktīvo pildījumu izskatījās
# neglīts; tagad — «Saites» cilnes filtra valoda: punkts tēmas krāsā +
# skaits, biežākās pirmās, aiz 12. tēmas sakļautas aiz «Vēl N tēmas».)


def test_topic_filter_buttons_carry_counts_and_are_sorted_by_count(tmp_path):
    html = _render(tmp_path)
    all_btn = html.index('data-filter="all"')
    topic_btn = html.index(f'data-filter="{TOPIC}"')
    other_btn = html.index(f'data-filter="{OTHER_TOPIC}"')
    assert all_btn < topic_btn < other_btn, "biežākā tēma (3 poz.) pirms retākās (1 poz.)"
    # Skaits redzams pogā, ne tikai nosaukums.
    seg = html[topic_btn:topic_btn + 400]
    assert '<span class="filter-count">3</span>' in seg
    seg_all = html[all_btn:all_btn + 400]
    assert '<span class="filter-count">4</span>' in seg_all


def test_topic_filter_collapses_beyond_twelve_topics(tmp_path):
    db = _seed(str(tmp_path / "t.db"))
    stated = date.today().isoformat()
    for i in range(10, 30):
        db.execute(
            "INSERT INTO documents (id,content,content_hash,platform,source_domain,"
            "source_url,scraped_at,published_at) VALUES (?,?,?,'web','delfi.lv',?,?,?)",
            (i, f"T {i}", f"h{i}", f"https://delfi.lv/{i}", stated, stated),
        )
        db.execute(
            "INSERT INTO claims (id,opponent_id,document_id,topic,stance,confidence,"
            "source_url,stated_at,claim_type) VALUES (?,?,?,?,?,0.9,?,?,'position')",
            (i, 1, i, f"Tēma {i}", f"Pozīcija {i}", f"https://delfi.lv/{i}", stated),
        )
    db.commit()
    out = tmp_path / "site" / "atmina"
    out.mkdir(parents=True)
    render_politicians(_env(), db, out, [{
        "id": 1, "name": "A Kalns", "slug": "a-kalns",
        "profile_kind": "politician", "role_label": "deputāts",
        "party": "JV", "x_handle": None,
    }], pid_to_syntheses={})
    html = (out / "politiki" / "a-kalns.html").read_text(encoding="utf-8")
    # 22 tēmas: 12 redzamas, 10 sakļautas ar `hidden` + data-topic-more marķieri.
    assert html.count('class="filter-btn topic-filter-btn topic-filter-more" hidden') == 10
    assert 'data-topic-more-toggle' in html
    assert "Vēl 10 tēmas" in html


def test_topic_filter_is_flat_when_twelve_or_fewer(tmp_path):
    html = _render(tmp_path)
    assert "topic-filter-more" not in html
    assert "data-topic-more-toggle" not in html


def test_ppv1_expands_collapsed_topic_on_deeplink():
    js = Path("assets/ppv1.js").read_text(encoding="utf-8")
    assert "data-topic-more-toggle" in js
    # setTopic atklāj sakļautu pogu, lai ?tema= uz reto tēmu nepaliek neredzams.
    assert "revealTopicButtons" in js
