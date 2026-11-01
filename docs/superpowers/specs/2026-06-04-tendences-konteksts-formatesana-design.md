# Tendences → Konteksts: formatēšana + datu higiēna

**Datums:** 2026-06-04
**Tvērums:** Analīzes lapas (`analizes.html`) Tendences subtaba "Konteksts" sadaļa.
**Mērķis:** Novērst divas defektu klases — (1) JSON grāmatvedības atkritumu noplūdi publiskajā UI un (2) "palagu" + kailo markdown/claim-ID artefaktu nelasāmo formatējumu.

## Problēmas diagnoze

Tendences subtaba "Konteksts" sadaļa (`templates/analizes.html.j2:183-195`) renderē `context_notes`
kartiņas caur `_fetch_context_notes` (`src/render/blog.py:107`). Divas saknes:

1. **JSON atkritumu ieraksti.** 4 vienreizēji attēlu-ģenerēšanas skripti
   (`scripts/generate_synthesis_image.py`, `scripts/gen_kulberga_tweet_image.py`,
   `scripts/gen_kulberga_valdiba_image.py`, `scripts/gen_saeima_2026_04_30_image.py`)
   raksta audit-rindu tabulā `context_notes` ar `note_type='context'` un `content` = JSON
   (`{"kind": "synthesis_featured_image", ...}` / `{"kind": "tweet_image", ...}`). Tās eksistē
   **tikai** lai `brief_images.note_id` ārējā atslēga atrisinātos (skat. komentāru
   `generate_synthesis_image.py:90`). DB satur 9 šādas rindas. `_fetch_context_notes` tās
   ielādē un dump'o kā kartiņas → strukturēti dati noplūst publiskajā HTML.
   `src/briefs.py:183` jau filtrē tās ārā (`startswith("{")`), bet analīzes renderītājs nē.

2. **Nelasāms formatējums.** Īstās piezīmes:
   - Renderētas kā `{{ note.content }}` (escaped plain-text) → markdown netiek apstrādāts;
     `**Tendence (...)**` rāda kailus zvaigznīšus, līniju-sākuma `#` paliek redzami.
   - Pilnas ar kailiem claim-ID: `claim #208`, `(#6757)`, `#1113`, `(#14411)`, `(#20534)`.
     Pārkāpj māju citēšanas stilu (kaili `#NNNNN` neved nekur; skat.
     `feedback_synthesis_citation_style` atmiņu).

## Lēmumi (no brainstorm)

- **Tvērums:** Konteksts fix + datu higiēna (saknes labojums, ne tikai reader-filtrs).
- **Truncate:** Nē. Rādīt pilnu tekstu; tikai sakārtot tipogrāfiju. Kartiņas paliek dažāda augstuma.
- **Polling:** Rādīt tikai `note_type='context'`. `'polling'` (1 rinda) izņemts — svešs šai sadaļai.
- **Topic chip:** Neitrāls (border + muted fons), bez per-topic krāsas — turas tipogrāfijas-tīrīšanas tvērumā un izvairās no cross-modulu krāsu-kartes importa.

## Dizains

### ① Datu higiēna — jauns `note_type='asset'`

`context_notes.note_type` ir brīva `TEXT` kolonna bez CHECK-ierobežojuma
(`schema.sql:196` + indekss `idx_context_notes_type` rindā 254) → jauns tips neprasa
shēmas migrāciju.

- **Writer (4 skripti):** mainīt audit-rindas `note_type` no netiešā `'context'` uz `'asset'`.
  Katrs skripts veido rindu ar `json.dumps({"kind": ...})` saturu; pievienot/labot
  `note_type='asset'` ierakstā.
- **Backfill (vienreizējs SQL):**
  ```sql
  UPDATE context_notes
     SET note_type = 'asset'
   WHERE note_type = 'context' AND TRIM(content) LIKE '{%';
  ```
  Skar 9 rindas. `brief_images.note_id` FK **netiek skarts** — `id` paliek nemainīgs.
  Rollback fails: `data/rollback_asset_note_type.sql` (saglabā skarto id sarakstu pirms UPDATE).
- **`src/models.py:45`:** `note_type` Literal → pievienot `"asset"`.
- **Blakusefekts (vēlams):** `routine.py:_check_tendences` (`routine.py:375`) skaita
  `note_type='context'` → pēc backfill tendences-skaits kļūst pareizs (vairs neskaita JSON rindas).
  Nav koda izmaiņas; tikai uzvedības korekcija.

### ② Reader filtrs (aizsargs)

`_fetch_context_notes` (`src/render/blog.py:107`):

```python
rows = db.execute("""
    SELECT * FROM context_notes
    WHERE note_type = 'context'
      AND TRIM(content) NOT LIKE '{%'
    ORDER BY created_at DESC LIMIT 20
""").fetchall()
```

- `'polling'` izņemts no `IN (...)` (lēmums: tikai `context`).
- `NOT LIKE '{%'` ir defense-in-depth, ja kāds nākotnes skripts paslīd cauri bez `note_type='asset'`.

### ③ Satura tīrīšana — `_clean_context_note(content: str) -> str`

Jauns helper. Atrašanās vieta: `src/render/_common.py` (koplietots; sub-page boundary atļauj
visiem render-moduļiem importēt no `_common`). Atgriež sanitizētu HTML.

Soļi:
1. **Strip kailos claim-ID:** regex `re.sub(r"\s*\(?(?:claim\s+)?#\d{3,6}\)?", "", content)`.
   Optional `claim\s+` prefikss notver `claim #208` pilnībā (neatstāj kailo vārdu "claim");
   `(?:...)?` arī sedz `#6757`, `(#6757)`, `(#14411)` bez prefiksa. Pēc strip — `re.sub(r"\s{2,}", " ", ...)`
   sakļauj dubultos tukšumus, kas rodas, izņemot ID vidū teikuma.
2. **Render markdown:** caur `markdown.Markdown(extensions=["tables", "fenced_code"])`
   (identiski `_common.py:240` sintēzēm) → tad `_sanitize_html()` (`_common.py:127`).

Šis pārvērš `**Tendence (...)**` par `<strong>`, noņem kailos ID, un dod tīru HTML.

### ④ Kartiņu izkārtojums — `templates/analizes.html.j2:188-192`

- `_fetch_context_notes` katrai piezīmei pievieno `content_html` (no `_clean_context_note`).
  Alternatīvi tīrīšana notiek renderītājā pirms template — turēt loģiku Python pusē, template
  tikai `{{ note.content_html | safe }}`.
- Template:
  ```html
  <div class="card">
    <div class="ctx-meta">
      {% if note.topic %}<span class="ctx-chip">{{ note.topic }}</span>{% endif %}
      <span class="ctx-date">{{ note.created_at[:10] if note.created_at else '' }}</span>
    </div>
    <div class="ctx-body">{{ note.content_html | safe }}</div>
  </div>
  ```
- CSS (neitrāls chip + lasāms body): `.ctx-chip` = mazs pill (border `var(--border)`,
  fons `var(--surface-2)` vai līdzvērtīgs, `font-size:0.72rem`, padding, radius); `.ctx-date`
  = `var(--text-muted)`; `.ctx-body` = `font-size:0.9rem; line-height:1.55` ar `<strong>`/`<p>`
  atstarpēm. Pievienot `base.html.j2`/koplietotā CSS, saskaņā ar esošajiem `--` mainīgajiem.

### ⑤ Vizuālā kvalitāte + responsīvs (galvenais akcepta kritērijs)

Lietotāja prasība: **skaisti gan desktop, gan mobile, intuitīvi, bez gļukiem.**

Esošā bāze (verificēta):
- `.grid-3` = `repeat(auto-fill, minmax(320px, 1fr))` (style.css:1015) → dabiski sašaurinās;
  `≤768px` skaidrs `grid-template-columns: 1fr` (style.css:2052). Mobile-collapse jau strādā.

Jaunās prasības (lai variable-height kartiņas neradītu gļukus):
- **`align-items: start`** uz Konteksta grid (scoped, piem. `.ctx-grid`) — bez tā CSS-grid
  rindas izstiepj zemākās kartiņas līdz augstākās augstumam → tukši "caurumi". Tas ir
  galvenais ne-truncate izkārtojuma gļuks, ko jānovērš.
- **Chip:** eleganta editoriāla pill (atbilst atmina restrained estētikai — Georgia serif,
  cream/slate). Monohroms `var(--surface-2)`/`var(--border)`, neliels `letter-spacing`,
  `font-size:0.72rem`. (Per-topic krāsa = vēlama nākotne; monohroms tur tvērumu un izskatās tīri.)
- **Body tipogrāfija:** `line-height:1.55`, `<strong>` redzams bez kliedzošuma, `<p>` ar
  atstarpēm; saraksti/atstarpes no markdown nedrīkst lauzt kartiņas padding.
- **Mobile (≤768 / ≤480):** chip+datums rinda `flex-wrap`; kartiņas padding samazināts;
  fontu izmēri lasāmi; nav horizontālā scroll/overflow (garš URL/vārds wrap ar `overflow-wrap`).
- **Bez gļukiem:** nav `{"kind"` noplūdes, nav kailo `#`, nav izstieptu tukšu kartiņu,
  nav teksta overflow ārpus kartiņas, vienmērīgs gap abos skatos.

**Verifikācija (obligāta):** Playwright snapshot Konteksta sadaļai **divos viewport** —
desktop (~1280px) un mobile (~390px). Vizuāli apstiprināt: 3→1 kolonnas, izlīdzinātas
kartiņas, lasāma tipogrāfija, nav overflow. Skat. testēšanas sadaļu.

## Vienības / robežas

| Vienība | Ko dara | Atkarības |
|---|---|---|
| `_clean_context_note` (`_common.py`) | claim-ID strip + markdown→sanitized HTML | `re`, `markdown`, `_sanitize_html` |
| `_fetch_context_notes` (`blog.py`) | filtrē `context` + ne-JSON, pievieno `content_html` | `_clean_context_note` |
| 4 `scripts/gen_*` | raksta audit-rindas ar `note_type='asset'` | — |
| backfill SQL | pārvieto esošās 9 JSON rindas uz `asset` | — |

## Testēšana

- **Unit:** `_clean_context_note` — (a) strip `#208`/`(#6757)`/`claim #1113`; (b) `**x**`→`<strong>`;
  (c) JSON saturs nedrīkst sasniegt šo funkciju (filtrēts agrāk); (d) tukšs/None drošs.
- **Unit:** `_fetch_context_notes` ar seeded DB (1 context, 1 asset/JSON, 1 polling) →
  atgriež tikai context rindu ar `content_html`.
- **Smoke:** `generate_public_site --only=dashboard` + Playwright pārbaude, ka Konteksts sadaļā
  nav `{"kind"` un nav kailo `#NNNNN`.
- **Vizuāls (divos viewport):** Playwright snapshot desktop (~1280px) + mobile (~390px):
  3→1 kolonnas, `align-items:start` (nav izstieptu tukšu kartiņu), nav horizontālā overflow,
  chip+datums wrap mobilajā. Šis ir galvenais akcepta kritērijs.
- **Regresija:** `briefs.py` JSON-filtrs paliek (defense-in-depth); esošie brief testi zaļi.
- `bash scripts/check.sh` zaļš (ruff + pytest + smoke).

## Ārpus tvēruma

- Diagrammu (tēmas/politiķi/laika līnija) vizuālā pārstrāde.
- Per-topic krāsainie chip (atstāts kā vēlama nākotnes uzlabošana).
- `brief_images.note_id` FK strukturālā pārkārtošana (audit-rindas joprojām dzīvo `context_notes`).
