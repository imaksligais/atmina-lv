# Spec: "Uzmanības centrā" rotācijas kompozīts (landing)

**Datums:** 2026-07-07 · **Statuss:** DONE + DEPLOYED 2026-07-07 (master `52b5a7f`, live-verificēts; izkārtojuma v2 pēc operatora atsauksmes — hot banneris pilnā platumā, B/C sloti pusplatumā zem tā)
**Problēma:** landing pretrunu sekcija ("Jaunākās pretrunas") barojas tikai no pretrunām — 23 confirmed kopā, tikai 3 pēdējās 30 dienās (raža ~1/2700) → sekcija pēc konstrukcijas stāv uz vietas.
**Risinājums:** tās vietā viena "Uzmanības centrā" sekcija ar trim slotiem un svaiguma-fallback ķēdi, kas nekad nav tukša, jo A slots (Karstā tēma) vienmēr eksistē.

## Verificētie dati (2026-07-07, dzīvā DB)

| Klase | Svaigums 7–14d | Loma |
|---|---|---|
| Pozīcijas pa tēmām | top tēma 18 poz. / 14 politiķi 7d; visas top-6 ≥8 | A slots — vienmēr |
| Verbatim citāti (sal≥0.5, len>40) | 113 nedēļā | dienas citāts — vienmēr |
| Pretrunas confirmed=1 | 3 mēnesī | B slots, kad svaigas |
| Spriedzes | 8 14 dienās | B/C slots, kad svaigas |
| Saeimas balsojumi | 0 14 dienās (vasara) | NAV šajā sekcijā |

## Uzbūve

**Čaula.** Aizstāj "Jaunākās pretrunas" sekciju tās pašā vietā (pozīcija №3 aiz Pārskatiem) `templates/index.html.j2`. Virsraksts "Uzmanības centrā". Grid `2fr 1fr 1fr`; 375px — vertikāls stack; tukši B/C sloti kolapsē un A izplešas.

**A slots — Karstā tēma (vienmēr).**
- Skors: `poz_skaits + 4·MAX(salience)` pa `claim_type='position'` pozīcijām pēdējās 7 dienās; izšķirtne → vairāk atšķirīgu politiķu. Audience-konti (`journalist/organization/neutral/inactive`) izslēgti (tas pats filtrs kā brief statistikai).
- Saturs: tēmas nosaukums; čipi "N pozīcijas · M politiķi · šonedēļ" (`lv_plural`); 2–3 citātu kartes — augstākā salience, viens citāts uz politiķi, **`quote` verbatim** (CLAUDE.md vārtu izņēmums), avatārs esošajā idiomā (`assets/photos/{slug}.jpg` + iniciāļu fallback + `--pc`), avota saite + datums; koalīcija/opozīcija sadalījuma josla pār VISĀM tēmas 7d pozīcijām (`get_coalition_map`, bezpartejiskie ar NULL statusu → neitrāli, joslā neskaitās); CTA → `temas/{slug}.html`.

**B slots — svaigā pretruna → spriedze → dienas citāts.**
- Jaunākā `confirmed=1` pretruna, ja `detected_at` < 14d — no orchestratora jau padotā `contradictions` saraksta (BEZ jauna vaicājuma), esošais kartes stils saīsināts.
- Citādi jaunākā spriedze <14d; citādi dienas citāts.

**C slots — spriedžu duelis → dienas citāts → kolapss.**
- Jaunākā spriedze <14d, kas nav B slotā: divas puses (avatāri), `tension_type` marķējums, `description`, abu avotu saites (`source_url`, `target_url`), CTA → `spriedzes.html`.
- Citādi dienas citāts (ja nav jau izmantots); citādi slots kolapsē.

**Dienas citāts** = dienas (fallback: 7d) augstākās salience pozīcija ar `quote` >40 zīmēm; liela tipogrāfija, attiecinājums, avota saite. Verbatim, bez labojumiem.

## Datu slānis

`src/render/dashboard.py` — trīs jauni tīri helperi, katrs atgriež `dict | None`:
- `_hot_topic(db)` — skors, čipi, citātu kartes, koalīcijas sadalījums;
- `_fresh_tension(db)` — jaunākā spriedze <14d ar abu pušu vārdiem/slug/foto;
- `_quote_of_day(db)` — augstākās salience svaigais citāts.

Pretrunu svaiguma filtrs — templotē no esošajiem datiem. Visi vaicājumi iet pa esošajiem indeksiem (`idx_claims_stated_at`, `idx_claims_opponent_topic`) — NAV `_heavy_fetch_plan` izmaiņu. Slot-izvēles loģika (fallback ķēde) — Python pusē (`render_dashboard` konteksta saliktnē), templote tikai rāda, kas padots.

## Ierobežojumi (verificēti)

- **Auto-apdeite:** dienas rutīnas šaurais renders jau ietver `dashboard` (pārskati + hero josla to prasa) → kompozīts pārrēķinās katrā renderā bez jauniem mehānismiem. Svaiguma logi izvērtējas render brīdī — SSR semantika, tāda pati kā visai lapai.
- **Bloat:** index.html 62 KB → ~+3–5 KB neto (pretrunu kartes saraujas 3→1); nulle jauna JS; ~120–150 rindas CSS esošajās idiomās; jaunie attēli tikai jau eksistējoši avatāri (lazy, 56px). Perf ne-darīt saraksts neaiztikts.
- **AA kontrasts** abās tēmās: datu krāsas caur `--party-color`/`--pc` custom prop (gaišajā color-mix patumšina) — esošā konvencija.
- **Ārpus tvēruma:** balsojumu slots (sesiju atkarīgs), solījumu bloks (standing lēmums gaidīt visas programmas), iniciāļu helpera dedupe (tikai ja B slots to dabiski prasa), analizes.html (dala domēnu, netiek aiztikts).

## Testi un izvešana

- Hermētiski testi helperiem (fixture DB): salience-svērtā izvēle uzvar pret tīru skaitu; audience izslēgti; citāts verbatim; fallback ķēdes 4 stāvokļi (pretruna+spriedze / tikai spriedze / tikai citāts / viss tukšs→A izplešas); koalīcijas josla skaita visas pozīcijas, ne tikai rādītās.
- Renders + Playwright 1440/375, gaišā UN tumšā tēma; nav horizontālā scroll; `section-head-title` skaits pirms/pēc.
- Char-baseline REGEN centralizēti beigās; narrow renders `--only=dashboard`; deploy `--no-delete` tikai pēc operatora apstiprinājuma.
