# Sākumlapa: josla „Jaunākais” — dizains (2026-09-20)

## Problēma

Sākumlapas augša reti mainās, svaigākais saturs stāv apakšā. Mērījums 2026-09-20 (`output/atmina/index.html`):
karuseļa pirmā kartīte — pretruna 2026-06-11 → 2026-07-16 (jūlijs), jo `hero_feed` bez svaigas (≤ 14 d)
apstiprinātas pretrunas ņem vecāko kā „enkuru”; „Jaunākās analīzes” (VID izmeklēšana 19.09) — 7. sadaļa no 8.

## Lēmumi (operators 2026-09-20)

1. Pirmais mainīgais elements = josla ar jaunāko dienas/nedēļas pārskatu un jaunāko analīzi/sintēzi.
2. Vieta: iekš `section.hero-v2`, starp sākumpunktu nav (`.hero-entry`) un karuseli (`.hero-feature`).
3. Nosaukums „Jaunākais” (ne „Šodien”): no rīta tur ir vakardienas pārskats; datums kartītē ir patiesība.

## Uzvedība

- **Josla** `.latest-strip`: kicker „Jaunākais”, līdz 2 kartītes.
  - Kreisā: jaunākais pārskats no `blog_posts[0]` (jau kārtoti pēc subjekta datuma dilstoši) — attēls (`card` variants),
    tips (`type_label`, nedēļas pārskatam `is-weekly`), datums, virsraksts (`headline`, ja nav — `title`).
  - Labā: `analysis_items[0]` — jaunākais no analyses ∪ syntheses pēc datuma (esošā `_analysis_feed_items` kārtošana).
    Attēls (dark/light), kicker (Tematiskā analīze / Sintēze), datums, virsraksts, apraksts.
  - Zīme „Jauns” uz kartītes, ja vecums ≤ 7 d (`_ANALYSIS_NEW_DAYS`, viens un tas pats abām kartītēm).
  - Ja pārskata nav — tikai analīzes kartīte (pilnā platumā). Ja nav nekā — joslas nav.
- **Dublēšanās:** „Jaunākie pārskati” rāda `blog_posts[1:4]`; „Jaunākās analīzes” kļūst „Vairāk analīžu” ar
  `analysis_items[1:3]`; ja pēc atņemšanas sadaļa tukša — to nerenderē. `fresh_highlight` josla pazūd (CSS `.fresh-strip` paliek
  neizmantota — dzēšam arī to).
- **Karuselis:** `hero_feed` bez svaigām pretrunām rāda 0 pretrunu (nevis 1 vecu enkuru); pozīcijas aizpilda līdz 6.
  Tests `test_hero_feed_stale_contradictions_keep_one_anchor` apgriežas uz „…show_none”.

## Tehniski

- `src/render/dashboard.py`: `_analysis_feed_items` → atgriež pilnu kārtoto sarakstu (ne duo); jauna tīra funkcija
  `latest_strip(blog_posts, analysis_items, today_iso) -> dict | None` ar `brief`, `analysis`, katrai `is_new`;
  `render_dashboard` padod `latest`, `recent_briefs = blog_posts[1:4]`, `more_analyses = items[1:3]`.
- `templates/index.html.j2`: jauns bloks, sadaļu korekcijas, `fresh_highlight` izņemts.
- `assets/style.css`: `.latest-strip`, `.latest-card` (pēc `.brief-featured-card` parauga), ≤ 640 px vienā kolonnā.
- Nav JS, CSP neskarts. `REGEN=1 pytest tests/test_render_chars.py` pēc izmaiņām (index.html hash).

## Vārti

- Vienību testi `latest_strip` (abi · tikai analīze · tukšs · `is_new` robeža) un `hero_feed` bez enkura.
- Šablona tests: renderētajā `index.html` ir `.latest-strip` ar pārskata slugu, un tas pats slugs NAV `.brief-featured-grid`.
- `bash scripts/check.sh` zaļš; Playwright 375 px `scrollWidth == innerWidth`; ekrānuzņēmums operatoram.
- Deploy tikai ar operatora atļauju (dota 2026-09-20 kopā ar Partiju testa B3).
