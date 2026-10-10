# Nedēļas rutīna

Izpilda reizi nedēļā (parasti piektdien vai pirmdien).

## 1. Pretrunu medības — `/deep-check`

Nedēļas pretrunu pāreja ir `/deep-check` nedēļas aktīvākajiem politiķiem (@contradiction-hunter → @devils-advocate; izdzīvojušie `confirmed=0` operatora pārskatam). Iepriekšējais `src/cross_check.py` pilnais pāru saraksts izņemts 2026-10-01 (operatora verdikts D5): pie 0,80 tas deva 56 871 pāri, ko neviens nevarēja izskatīt.

## 2. Nedēļas pārskats

```python
from src.briefs import generate_weekly_brief
skeleton = generate_weekly_brief(week_start="YYYY-MM-DD")  # markeri + deterministiski dati + movers SVG
```

Skeletu bagātina `@weekly-brief-writer` aģents (**NE** `@brief-writer` — tas ir daily).
Struktūra: Nedēļas stāsts → Nedēļā skaitļos → Kas kustējās (grafiks) → Nedēļas
galvenās tēmas → Pretrunas → Skats uz priekšu → Vizuālais brief. Stat josla un
movers grafiks ir deterministiski (no DB, ne no AI). Saglabā ar:

```python
from src.tools import store_context_note
store_context_note(topic="nedēļas analīze START līdz END", note_type="weekly_brief",
    content=md, source="atmina analīze")
```

> **Formāts** — pilnais SAGLABĀ/PAPILDINI apraksts dzīvo `.claude/agents/weekly-brief-writer.md`; koplietotie noteikumi `wiki/operations/agenti/brief-shared-rules.md`.

**Vārti pirms deploy: `@quality-reviewer` PASS (obligāts, tāpat kā dienas rutīnā).** Nedēļas pārskatam ir tie paši vārti, kas aprakstīti [daily-routine.md „Pirms 10. soļa"](daily-routine.md#pirms-10-soļa-quality-reviewer-obligāts) — QR pārbauda datu integritāti, operators pieņem publicēšanas lēmumu, un abi notiek **pirms** `deploy.sh`. 2026-09-21 šis solis tika izlaists (QR palaists pēc publicēšanas) un atrada reālu kļūdu jau dzīvā lapā: bloku komentārs rakstīja „pret balsoja ZZS un LPV (27)", kaut Pret=27 bija ZZS 9 + LPV 5 + AS 4 + ārpusfrakciju 9 — premjera partija bija sašķēlusies, un tieši tas bija tēzes kodols. Labošana prasīja `store_context_note` UPSERT, pārrenderēšanu un otru deploy (`1569452c`).

Nedēļas pārskatam papildus dienas pārbaudēm: frakciju sadalījums katram citētajam `vote_id` jāņem no `weekly_vote_breakdown(week_start="YYYY-MM-DD")` (`src/briefs.py`), ne no pārstāstījuma (CLAUDE.md T6 „party ≠ faction"); `saeima_votes.summary` satur balsojuma satura aprakstu, ne skaitļus. Izvade grupē balsojumus pa `document_nr`, tāpēc ķēdi izlasi pilnībā (T14); `ārpusfrakciju` ir atsevišķa grupa, un rinda `⚠ NESAKRĪT` nozīmē, ka individuālās balsis nesakrīt ar kopsummām — tādu balsojumu necitē. `@quality-reviewer` salīdzina katru prozā minēto frakciju skaitli ar šo izvadi.

## 3. Saeimas sesijas

Palaid `@saeima-tracker` lai ielādētu jaunas sesijas no titania.saeima.lv.

Pēc tam Saeimas aktivitāte (amati, debašu runātāji, deputātu jautājumi; ~15 min, palaid fonā): `.venv/Scripts/python.exe -m scripts.ingest_saeima_activity --what all`. Exit 1 = STOP vai avota kļūme — izlasi `failure:` rindas; `unmatched:` (neizsekoti runātāji, piem. parlamentārie sekretāri) nav kļūda. Plāns un robi: `docs/plans/2026-10-06-saeimas-aktivitate.md`.

## 4. Sanity audits

- **Saeima vote-result audit** — palaid `.venv/Scripts/python.exe scripts/audit_saeima_vote_results.py` (exit 0 = clean). Ja exit 1, palaid ar `--verbose` lai redzētu konkrētus vote_id un izmeklē, vai `78d87fb` style fallback bug ir atgriezies vai jauns parser drift. **Gaidāmā vērtība ir 0** (datu labojums izpildīts 2026-08-17, sk. `backlog/saeima.md`; 2026-09-07 mērījums: `rows=8012 asserted=7442 unknown=570 aliased=30 mismatches=0`, exit 0). Jebkurš nenulles `mismatches` ir jauns parsera dreifs, ne vecais 562 atlikums — līdz 2026-09-07 šeit stāvēja novecojusi instrukcija «salīdzini ar 562».
- **Pilnais testu skrējiens** — `CHECK_PYTEST_MARKERS="" bash scripts/check.sh`. Dienas `check.sh` kopš 2026-08-01 izlaiž `slow` marķieri, jo tie divi testi iet uz **dzīvo KNAB vietni** — trešās puses nepieejamība nedrīkst apturēt mūsu publicēšanu. Reizi nedēļā tie tomēr jāpalaiž: tie ir vienīgā pārbaude, ka KNAB skrāpis vēl atbilst avota formātam (T12 klase — formāta maiņa, ne noņemšana).

## 5. NEEDS_REVIEW triāža (pievienots 2026-07-16, operatora lēmums)

Bez kadences NR rinda aug ~4/dienā (07-04 triāža 126→0; 12 dienās atkal 49). Reizi nedēļā:

```sql
-- Filtrē pēc KOLONNAS (kopš 2026-08-03), nevis pēc teksta. `review_status` ir
-- atvasināta no `reasoning` ar trigeriem, tāpēc tā redz visu rindu neatkarīgi
-- no marķiera formas un novietojuma. Enkurotais `LIKE 'NEEDS_REVIEW%'` savulaik
-- atgrieza 20 no 119 rindām un izskatījās pēc īsas rindas.
SELECT id, opponent_id, topic,
       substr(reasoning, instr(reasoning, 'NEEDS_REVIEW'), 200) AS marker
FROM claims WHERE review_status = 'needs_review' ORDER BY id;

-- Rindas vecums — jaunais lēmuma pamats (tukša rinda nekad nav bijusi patiesa).
-- Vecumu mēra no MARĶIERA, ne no claim: `COALESCE(review_status_at, created_at)`
-- (kopš 2026-09-07). `created_at` ir cits fakts — kad tapa PATS claim; ar to
-- katra retro-marķēšanas kārta uzreiz ražoja «pārkāpumu» par darbu, kas notika
-- iepriekšējā dienā (2026-08-22: 19 no 19 pārkāpuma rindām). Rindām, kas
-- rakstītas pirms 2026-09-07, zīmoga nav, un tās joprojām skaitās no
-- `created_at` — neviena rinda ar šo maiņu nekļūst jaunāka.
SELECT CASE WHEN julianday('now') - julianday(COALESCE(review_status_at, created_at)) > 14 THEN '>14d'
            WHEN julianday('now') - julianday(COALESCE(review_status_at, created_at)) > 7  THEN '8-14d'
            ELSE '<=7d' END AS vecums, COUNT(*)
FROM claims WHERE review_status = 'needs_review' GROUP BY 1;
```

Katram: apstiprināt topiku VAI pārkartēt (topic maiņai OBLIGĀTI pārrēķina `claim_vectors` embedding: `embed_text(topic || ': ' || stance)`, DELETE+INSERT ar `sqlite_vec.load`; **attiecas uz position/commentary/program_promise — `saeima_vote` rindām kopš 2026-08-21 vektora nav un pār-embedēšana to izveidotu no jauna, kas ir verdikta pārkāpums**). Marker aizstāj ar `Izvērtēts YYYY-MM-DD:` (audit trail paliek reasoning laukā, publiskās virsmas reasoning nerāda). VIENMĒR pārī rollback `data/rollback_needs_review_triage_YYYY-MM-DD.sql` ar oriģinālo topic+reasoning PIRMS piemērošanas. Paraugs: 2026-07-16 skrējiens (49→0, rollback failā redzama pilnā forma). Pēc topic remapiem — narrow render `--only=temas,pozicijas,politiki,dashboard` + deploy `--no-delete`.
