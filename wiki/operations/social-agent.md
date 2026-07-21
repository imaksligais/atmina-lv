# Social Agent — X/Twitter postu aģents

_Atjaunots: 2026-04-19 21:10_

Manuāli triggerējams CLI aģents, kas no atmina.lv datiem izvelk top-3 tvītu kandidātus (pretrunas / nedēļas stats / analīžu highlights), ģenerē tekstu + attēlu, sūta draftus uz Telegrāmu operatora apstiprinājumam, un publicē apstiprinātos tvītus uz `@atminaLV` caur twikit.

**Nav automātisks.** Nav webhook. Nav iekšējā dashboarda. Ir flow eksperiments — vēlāk taps separāta aģentu pārvaldības sistēma.

## @atminaLV konta balss

**Profila bio (no 2026-04-19):**

> Atceries to, ko viņi cer, ka aizmirsīsi. Pozīcijas, balsojumi, pretrunas — ar datumiem un avotiem. atmina.lv

**Pirmais thread (2026-04-19, 5 tvīti):** `docs/tweet_bank/2026-04-19-intro-thread.{md,html,pdf}` + gatavi PNGs `docs/tweet_bank/2026-04-19-intro/tweet_{1..5}_*.png`.

**Tonis:** Fakti ar datumiem, bez retoriskiem jautājumiem. Pretrunu draftu formāts (kopš 2026-04-21):

```
{Vārds Uzvārds} — {kategorija} · {tēma}

{DATUMS-1}: {agrākais paziņojums vai balsojums}
{DATUMS-2}: {vēlākais paziņojums vai balsojums}

atmina.lv/pretrunas/{id}.html
```

Kategorijas (no `src.generate.CATEGORY_LV` analoga): `pozīcijas maiņa` (position+position), `vārdi vs. darbi` (position+saeima_vote), `balsojuma maiņa` (vote+vote). Paraphrases neliek pēdiņās; verbātīmas citātu rindas — ar. Latvieši — "premjere" (nevis "premjēre"). Stats grafiki izslēdz žurnālistus / influencerus / neitrālus kontus (`relationship_type`).

**Vizuāls (pretrunas):** `src/social_agent/visuals.py::render_pretruna_og_card` kopē pregenerēto OG karti no `output/atmina/assets/og/pretruna-{id}.png` — vienota dizaina patiesība ar lapu (severity chip, party color, chronological labels). `quote_card.html.j2` paliek kā fallback, ja lapa nav pārģenerēta. Brand palete — `#0d1014` BG + `#eab308` ambera accent (iepriekš bijusi magenta `#ff3b7f`, nomesta 2026-04-21).

## Pakotne

`src/social_agent/` — 8 moduļi:

| Fails | Atbildība |
|---|---|
| `candidates.py` | DB queries + interest_score + top-N atlase ar per-pillar cap |
| `drafters.py` | Pillar-specific ≤280 char teksta šabloni |
| `visuals.py` | 3 rendereri: `render_chart` (matplotlib), `render_quote_card` (Playwright HTML→PNG), `render_illustration` (nanobanana) |
| `storage.py` | `social_drafts` tabulas CRUD + status pārejas |
| `publisher.py` | twikit wrapper — `publish_draft(text, image_path) -> tweet_id` |
| `telegram.py` | Tiešs Bot API caur httpx (sendPhoto/sendMessage) + reply parser |
| `cli.py` | `brainstorm` / `approve` / `skip` / `revise` / `resend` |
| `__main__.py` | `python -m src.social_agent ...` entry point |

## DB tabula `social_drafts`

Statusi: `pending → posted / rejected / revising / failed`. `approved` tabulā vairs netiek uzrakstīts (status pāriet tieši uz `posted` pēc sekmīgas publikācijas).

Kolonnas: `id, pillar, text, image_path, source_data_json, score, status, telegram_msg_id, telegram_chat_id, revision_count, parent_draft_id, created_at, posted_at, tweet_id, error_message`.

## 3 content pillars

**1. Pretrunas** — no `contradictions` tabulas, dedup pret `posted` draftiem (`source_data_json->>'contradiction_id'`). Vizuāls: quote card.

**2. Nedēļas stats** — top 10 politiķu aktivitāte pēdējās 7 dienās no `claims` (filtrs `claim_type='position'`). Viens kandidāts uz ISO nedēļu. Vizuāls: matplotlib bar chart.

**3. Analīžu highlights** — attacks no `oppo_briefs.strongest_attacks` (JSON) + `political_tensions`. Dedup pret `posted`. Vizuāls: nanobanana ilustrācija vai quote card.

## Interest score

```
score = 0.3 * salience
      + 0.3 * severity_norm     (critical=1.0, major=0.7, minor=0.4, none=0.0, unknown=0.6)
      + 0.2 * freshness          (1 - age_hours/168, clamped)
      + 0.2 * novelty            (1 - Jaccard(topic, posted_last_7d))
```

Top 3 pēc score, hard cap 2 vienas pīlāra draftus.

## Darbplūsma

```
1. python -m src.social_agent brainstorm
     │ (candidates → score → select top 3)
     │ (render text + visual per pillar)
     │ (save social_drafts row, status='pending')
     ▼
2. Telegram (bot) sūta 3 postus ar bildēm un katra pēdiņā:
   "Draft #42 · pretrunas ... Approve: `ok 42` · Skip: `skip 42` · Revise: `42 <instrukcija>`"
     │
     ▼
3. Operators atbild Telegrāmā:
     ok 42              → python -m src.social_agent approve 42
     skip 42            → python -m src.social_agent skip 42
     42 pārraksti īsāk  → python -m src.social_agent revise 42 pārraksti īsāk
     │
     ▼
4. approve: publicē ar twikit → status='posted', saglabā tweet_id. Ja publikācija krīt, status='failed' ar error_message.
   skip: status='rejected'
   revise: llm_rewrite(old_text, instruction) → jauns child draft, parent status='revising', bērns 'pending' → atkal uz Telegrāmu.
```

## Pirmreizējais setup

```bash
python -m src.credentials set telegram_bot_token         # Bot API tokens
python -m src.credentials set telegram_operator_chat_id  # Piem. 619646282
python -m src.credentials set x_atmina_cookies_path      # ceļš uz atminaLV cookies

# Saglabā @atminaLV X/Twitter cookies:
# data/x_cookies_atmina.json (auth_token + ct0 no browser DevTools)

# Playwright browser (ja vēl nav instalēts):
python -m playwright install chromium

# DB tabula tiek radīta automātiski nākamajā init_db() izsaukumā:
python -c "from src.db import init_db; init_db()"
```

## Komandas

```bash
python -m src.social_agent brainstorm                        # atlasa + sūta top 3 draftus
python -m src.social_agent approve <id>                      # publicē uz X
python -m src.social_agent skip <id>                         # noraidīt draftu
python -m src.social_agent revise <id> <instrukcija...>      # pārģenerē ar LLM instrukciju
python -m src.social_agent resend <id>                       # atkārtoti sūta uz Telegrāmu
```

## Smoke test

`scripts/social_agent_smoke.md` — soli-pa-solim manuāls end-to-end tests. Obligāti pirmajā palaišanā pret burner X kontu, pirms pārslēgties uz `@atminaLV`.

## Tweet bankas

Atsevišķas manuāli sastādītas draftu kolekcijas dzīvo `docs/tweet_bank/YYYY-MM-DD-<tēma>.{md,html,pdf}`. `scripts/render_tweet_bank.py` ģenerē PDF/HTML no draftu metadatiem un PNG bildēm. Noder, kad gribi manuāli ievākt interesantas idejas un pievienot tās arhīvam, nelaižot caur `brainstorm` pipeline.

## Manuālais dienas-pārskata pavediens (lead + numurēti reply)

Atsevišķi no `brainstorm` pipeline. Kad operators publicē @atminaLV dienas-pārskata **tvītu pavedienu** (recepte apstiprināta 2026-05-30):

- **Lead tvīts (1/)** — operators raksta pats (parasti par dienas galveno notikumu/personām). Claude raksta **numurētus reply (2/N … N/N)**, katrs sedz vienu dienas brief beatu (balsojuma anatomija, aizsardzība, droni, korupcija/iepirkumi, topošie ministri, "Diena bloku skatā"). Saturs no reālā dienas brief.
- **Katrs reply:** īsa kategorijas virsrindiņa + 1 rūpīgs teikums. Saturatvītos **NEKĀDU saišu** (atmina.lv linkus noņēma 2026-05-30). Bloku kopsavilkuma tvīts = koalīcija/opozīcija/ārpus Saeimas/neitrāli ar pozīciju skaitu.
- **Noslēdzošais saites-tvīts** (2026-06-06): pēc bloku kopsavilkuma atsevišķs pēdējais tvīts ar **kailu pārskata URL** (`https://atmina.lv/blog/<datums>.html`) un **BEZ pievienota attēla** — OG-kartīte automātiski uzrāda dienas plakātu (`og:image`). Teksts: "Pilnu <D. mēnesis> pārskatu … lasi mūsu mājaslapā:" + URL jaunā rindā. Vienīgais tvīts ar saiti.
- **Vadošais tvīts BEZ statistikas rindas** (2026-06-08): lead beigās NELIEC kailo skaitļu rindu — skaitļi ir troksnis āķī.
- **Tagi:** katru nosaukto politiķi ar @handle no DB (`social_accounts.handle`, query pa uzvārdu). Forma: `Vārds Uzvārds (@handle, Partija)`. **Nekad nesāc tvītu ar @handle** — X renderē kā reply → slēpj no non-followers; sāc ar kategoriju/tēmu. Verificē handle no DB, nemini no galvas.
- **Attēli:** katram reply 1 sepia "aged archival editorial illustration" (muted sepia + slate-blue, cross-hatching, aged paper, 16:9, **bez teksta/cipariem**), metaforu vadīts. Nanobanana caur `python -m src.graphics.cli thread` (kanoniskā SEPIA_STYLE).
- **Stils:** datumi "D. mēnesis" lokatīvā (NE ISO; ISO tikai URL ceļā); saite = kails URL (nekad markdown/iekavās — X nerenderē markdown); "Dienas pārskats" reģistrs (NE anglicisms "Dienas brief"); bez ataka/polemika/melīšana/konsenss; LV gramatika+stilistika obligāti.
- **Pakotne:** `docs/tweet_bank/<datums>-dienas-parskats-social.md` (teksti + handles + attēlu prompti).

> **NB — @atminaLV ir X-verified:** 280 zīmju limits NAV saistošs; drafti var būt garāki (pillar-šabloni ≤280 augšā ir vadlīnija, ne griesti). Nepiemini char count draftos.

## Ierobežojumi (MVP)

- Nav auto-posting — viss iet caur operatora apstiprinājumu
- Nav publicēto tvītu atspoguļojuma atmina.lv (x.html vai kur citur)
- Nav operatora dashboarda — draftu stāvoklis redzams tikai DB
- Tikai X/Twitter — nav BlueSky/Mastodon/LinkedIn
- `llm_rewrite` ir heuristiskais stub — īstena LLM call (Claude API) nāks nākamajā iterācijā
- Telegrama reply handling ir _session-bound_ — plugin piegādā reply kā `<channel>` bloku šajā Claude Code sesijā, un Claude (vai operators no terminaļa) izsauc CLI. Nav background daemon.

## Nākotne

- Auto-posting zemriska pīlāriem (stats, highlights bez tiešiem citātiem)
- Apstiprināto tvītu parādīšana atmina.lv `x.html` (feed vai arhīvs)
- Iekšējais dashboard tab draftu queue + engagement metrics
- LLM-based `revise` (Claude API call)
- A/B variantu ģenerācija ("iedod 3 dažādus framing vienai pretrunai")
- Multi-platform fan-out
