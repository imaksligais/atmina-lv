# Nodošana: 2026-09-07 vakara rutīna (5.–10. solis)

**Stāvoklis 15:45 LV:** pēcpusdienas rutīna izpildīta līdz 4. solim un apzināti apturēta — operatora lēmums: dienas pārskats tikai pēc OTRĀ (vakara) ingest. Repo HEAD `a1efda2f` (+ šis fails), CHANGELOG «2026-09-07 (13)». **Nekas šodien nav deployots** — kokā stāv tēmas→profila `#pozicijas` labojums.

## Kas jau izdarīts (nedublē)

| Solis | Stāvoklis | Pierādījums |
|---|---|---|
| 1 Ingest (rīta) | 5/5, 594 doki (twitter 264, x_mention 210, web 92, vestnesis 28) | `logs` #… `morning_ingest` 2026-09-07 15:1x |
| 2 Ekstrakcija | 126/126 doki, **42 pozīcijas #709108–#709149** (34 fan-out + 8 junction-atgūšana), `failures=[]` | `SELECT COUNT(*) FROM claims WHERE claim_type='position' AND DATE(created_at)='2026-09-07'` = 42 |
| 3 Pretrunas | 42/42 pārbaudītas, 0 atrastas; `contradiction_hunt` logs ar 5 `rejected_candidates` | `print_routine()` 3. solis ✓ |
| 4 Devils-advocate | nav ko pārskatīt | — |
| Nedēļas § 4/§ 5 | pilnais tests 2549 zaļi; NEEDS_REVIEW 55→0 (rīts) + 5 jaunas rindas šodien | CHANGELOG (12), (13) |

## Vakarā — secība

1. **Otrs ingest fonā** (`scripts/morning_ingest.py`, ~15 min; Bash timeout par īsu). NELAID `check.sh` paralēli — ražošanas-DB sargs testos noķer fona ingest kā «testi rakstīja DB» (šodien 15:0x tā notika).
2. **Ekstrakcija tikai jaunajiem dokiem** (`reviewed_at IS NULL AND DATE(scraped_at)='2026-09-07'`) — tā pati partiju shēma (≤12 doki/aģents, `.claude/agents/claim-extractor.md`), kopīgais prompts bija scratchpad — atkārto tā būtību: ±5 d dublikāti, `empty_doc_ids` tikai izlasītajiem, `failures` lasīt, relay/žurnālisti bez paša pozīcijām. Pēc tam `find_inversions(db, days=1)` (bez platformas filtra) → atgūšanas aģents.
3. **Pretrunas** jaunajām + otra `log_action('contradiction_hunt')` rinda ar `rejected_candidates`.
4. **5. Spriedzes** — 29 politiķiem jaunas pozīcijas; kandidāti no dienas: artilērijas iepirkums (Sprūds #709108 ↔ Siliņa #709143 ↔ Melnis #709144 ↔ NBS #709134), valdības 100 dienas (Kulbergs #709112 ↔ Butāns #709146 / Jurēvics #709147 / Valainis #709148 / Tavars #709149), Vanšu tilts (Valainis #709126 ↔ Pūpols/Rīgas dome), Ijabs #709142 pret iznīcinātājiem kā pretdronu risinājumu.
5. **6. Tendences** — B forma (≤120 vārdi), append-only, `routine_day_window` 05:00.
6. **7. Pārskats** `@brief-writer` → korektūra → `@quality-reviewer` (`ROUTINE_DAY='2026-09-07'`, arī pēc pusnakts) → **8.** `@graphics-designer` → operatora attēla apstiprinājums.
7. **Renders**: `--only=blog,dashboard,static,temas,politiki` (temas+politiki OBLIGĀTI — `#pozicijas` labojums) → variantu vārts (a) ar `DAY='2026-09-07'` → `approve_publish.py 2026-09-07` → `deploy.sh --dry-run --no-delete` → deploy ar operatora atļauju → live vārts (b) `curl -I` 4 varianti + `https://atmina.lv/temas/<slug>.html` saites beidzas ar `#pozicijas`.
8. **9. Wiki sync**, commit ar CHANGELOG «2026-09-07 (rutīna)».

## Operatora lēmumi, kas radušies šodien (BACKLOG § Atliktais 53–57 + šie)

- **Čakša #709111 pret JV programmu #532676** — ministra pozīcija vs partijas solījums (obligātā vidējā izglītība). Jauna klase, konvencijas nav; `rejected_candidates` panelī. Glabāt kā pretrunu vai ne — tavs lēmums.
- **Siliņa #709143 (Archer)** — retorika-vs-rīcība; embeddings neredz (T9). Ja gribi: `@contradiction-hunter` strukturālā pase vienam pid.
- **MK rīkojumi Vēstnesī** — 5 Kulberga doki (103441–103445) atzīmēti tukši pēc precedenta #14500 (līdzparakstītājs ministrs); Braže/Indriksone/Abu Meri tur `mentioned` → viņu slotos vairs neparādīsies. Konvencija nekur nav pierakstīta — 2 177 `vestnesis` doki, 225 reviewed.
- **Kleinbergs 103448** — Rīgas domes saistošie noteikumi ar priekšsēdētāja parakstu → tukšs (koleģiāls akts). Tā pati klase.
- **Tēmu nesakritība vienā sižetā:** Vanšu tilts #689778 `Pilsētvide` vs #709126 `Transports`; Pūpola zaļā kursa kritika #709130 `ES politika` vs #548105/#532325 `Klimats`. Labojums = UPDATE + re-embed + rollback.
- **needs_review 5:** #709110 Hermanis (tēma Vēlēšanas/Imigrācija), #709112 Kulbergs (bez citāta), #709116 Siliņa (personiska atbilde = pozīcija?), #709127 Valainis (eksports → Budžets vai Ārpolitika), #709128 Pūpols (t.co saite bez satura).
- Seeding kandidāti: Gints Kaminskis (LPS, doc 102911), @spunde, @liana_langa. Kolīzijas kandidāts: doc 102960 → Valsts kontrole (garāmejošs pieminējums).
- Velpa imigrācijas pozīciju blīvums (6 claims 7 dienās) — vai atkārtotas kampaņas ziņas turpmāk `empty_doc_ids`.

## Slazdi, kas šodien parādījās

- `weekly_cross_check(0.80)` = 56 871 pāri — nelaid to kā rindu (BACKLOG 53).
- 13. pārbaude tagad izslēdz `saeima_vote` (`saeima_vote_izslēgti=N`); gaidāmais `stale=0`.
- `find_inversions(db, days=N)` prasa `db` pirmajā argumentā un atgriež `{"checked", "inversions"}` — ne sarakstu.
- Pašretvīts (`RT @savs_handle`) first_party kontā ir tīra paša pozīcija (Pūpols #709129) — aģenta prompta RT-noteikums šo apakšgadījumu nesedz; vērts ierakstīt promptā.
- Sociālie melnraksti nedēļas pārskatam (`docs/tweet_bank/2026-09-07-*`, `docs/social/2026-09-07-*`) joprojām nepublicēti; Reddit melnraksts pārkāpj biežuma noteikumu (BACKLOG 56).
