# Satura pipeline (atmina.lv)

## Direktorija struktūra

`content/` direktorija satur publicētos rakstus un analīzes Markdown ar YAML frontmatter:
- `content/ideology.md` — publiski publicētā platformas ideoloģija
- `content/analizes/` — datu analīzes raksti (piem. `deklaracijas-2026.md`)

## Frontmatter prasības

Visiem satura failiem nepieciešami lauki:
- `title` — raksta nosaukums
- `date` — datums (YYYY-MM-DD)
- `description` — īss apraksts

Analīžu rakstiem papildus:
- `tags` — tēmu saraksts
- `url` — publikācijas ceļš

## Ģenerēšana

Statiskā vietne tiek ģenerēta uz `output/` direktoriju:

```bash
.venv/Scripts/python.exe -c "from src.render import generate_public_site; generate_public_site()"
```

Templates atrodas `templates/` direktorijā. Stils: `assets/style.css`.

## Zināmās ievākšanas robežas (novērojumi, ne darbi)

Rīcība sākas tikai tad, ja biežums aug; neatver no jauna bez jauna fakta.

- **pietiek.com** — aiz Cloudflare JS izaicinājuma krīt visas automātiskās metodes (httpx, curl, crawl4ai headless un headed); `trafilatura` uz raksta HTML strādā, RSS `https://pietiek.com/rss/`. NEpievieno `sources.yaml`, kamēr nav CF risinājuma.
- **pmo.ee paywall stubi** — pieņemti; ja kāds nes claim, truncated-stub vārti to marķē NEEDS_REVIEW. 2026-09-25: 2 430 doki, 391 ar `word_count<90`.
- **Tvīti, kuru saturs ir video pielikumā** (doc 79162) un **quote-tweet/atbilžu saturs** (doc 81547) — tvīta `content` nes tikai autora tekstu, tāpēc pozīcija pielikumā vai citētajā tvītā nav ekstraktējama. Ja klase kļūst bieža — ievākšanas paplašinājums vai apzināta pieņemšana.
- **`is_paywall` nav uzticams** — neviens ingest ceļš kolonnu neraksta (visas 351 rindas ar `1` ir no 2026-03-25…04-06; Delfi paywall doc 76622 ir `0`). Truncated-source spriedumiem vajag teksta/garuma pazīmi.
