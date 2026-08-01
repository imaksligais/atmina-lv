# Nedēļas rutīna

Izpilda reizi nedēļā (parasti piektdien vai pirmdien).

## 1. Pilns pretrunu cross-check

Pārskata VISUS claims pārus pa politiķiem un tēmām. Rezultātus pārbauda cilvēks:

```python
from src.cross_check import weekly_cross_check, print_cross_check_report
results = weekly_cross_check(similarity_threshold=0.80)
print_cross_check_report(results)
```

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

## 3. Saeimas sesijas

Palaid `@saeima-tracker` lai ielādētu jaunas sesijas no titania.saeima.lv.

## 4. Sanity audits

- **Saeima vote-result audit** — palaid `.venv/Scripts/python.exe scripts/audit_saeima_vote_results.py` (exit 0 = clean). Ja exit 1, palaid ar `--verbose` lai redzētu konkrētus vote_id un izmeklē, vai `78d87fb` style fallback bug ir atgriezies vai jauns parser drift. **Šobrīd vārti ir sarkani ar zināmu iemeslu:** `mismatches=562` (540 procedurālas rindas ar fabricētu `Noraidīts` + 22 reāli balsojumi ar nepareizu `result`), visas no backfill fallback — cēlonis kodā izlabots 2026-08-17, datu labojums vēl neizdarīts, sk. `BACKLOG.md` § Saeima. Nedēļas skrējienā salīdzini **skaitli** ar 562: pieaugums = jauns dreifs, ne vecais atlikums.
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

-- Rindas vecums — jaunais lēmuma pamats (tukša rinda nekad nav bijusi patiesa):
SELECT CASE WHEN julianday('now') - julianday(created_at) > 14 THEN '>14d'
            WHEN julianday('now') - julianday(created_at) > 7  THEN '8-14d'
            ELSE '<=7d' END AS vecums, COUNT(*)
FROM claims WHERE review_status = 'needs_review' GROUP BY 1;
```

Katram: apstiprināt topiku VAI pārkartēt (topic maiņai OBLIGĀTI pārrēķina `claim_vectors` embedding: `embed_text(topic || ': ' || stance)`, DELETE+INSERT ar `sqlite_vec.load`; **attiecas uz position/commentary/program_promise — `saeima_vote` rindām kopš 2026-08-21 vektora nav un pār-embedēšana to izveidotu no jauna, kas ir verdikta pārkāpums**). Marker aizstāj ar `Izvērtēts YYYY-MM-DD:` (audit trail paliek reasoning laukā, publiskās virsmas reasoning nerāda). VIENMĒR pārī rollback `data/rollback_needs_review_triage_YYYY-MM-DD.sql` ar oriģinālo topic+reasoning PIRMS piemērošanas. Paraugs: 2026-07-16 skrējiens (49→0, rollback failā redzama pilnā forma). Pēc topic remapiem — narrow render `--only=temas,pozicijas,politiki,dashboard` + deploy `--no-delete`.
