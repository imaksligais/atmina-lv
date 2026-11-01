# Koalīcija balsojuma dienā (balsojumu lapa, 3. laidiens)

**Problēma (T6 klase).** Balsojuma kartīte grupē frakcijas zem «Koalīcija»/«Opozīcija» pēc ŠODIENAS `parties.coalition_status`. Siliņas laika balsojumā (2023-09-15…2026-05-27) PRO stāv «Opozīcijā», AS «Koalīcijā» — otrādi nekā bija. Kad 15. Saeima sanāks (novembris) un statusi mainīsies (BACKLOG 204), pārkrāsosies VISAS 14. Saeimas kartītes. 2026-10-16 (2) makets apzināti atstāja «šodienas statusu, kā agrāk»; handoff 2026-10-16 to ieliek nākamajā laidienā — šis plāns to izpilda.

**Patiesība.** Trīs DB balsojumi «Uzticības izteikšana Ministru kabinetam» (visi Pieņemts). Frakcija = koalīcijā, ja tās vairākums balsoja Par:

| id | datums laiks | koalīcija (frakciju etiķetes) |
|---|---|---|
| 5623 | 2022-12-14 16:42:42 | AS, JV, NA |
| 4411 | 2023-09-15 17:10:11 | JV, PRO, ZZS |
| 5754 | 2026-05-28 17:20:31 | AS, JV, NA, ZZS |

Pārbaude ar neuzticības balsojumiem (2023-06-15, 2025-05-29 … 2026-09-03): starplaikos neviena koalīcijas frakcija nav mainījusi pusi. 101 balsojums ir pirms 5623 (13. Saeimas valdība, uzticības balsojums nav DB) — tiem koalīciju NEMINAM.

## Dizains
1. **Tabula `coalition_periods`** (`id`, `valid_from_date TEXT`, `valid_from_time TEXT`, `factions TEXT` — komatatdalītas kanoniskās `siv.faction` etiķetes, `source_vote_id INTEGER`, `note TEXT`). Shēma `src/schema.sql` + `src/db_migrations.py` (paraugs `_apply_dp_suppressions`), `tests/test_schema.py`.
2. **Sēklas skripts `scripts/seed_coalition_periods.py`**: atvasina rindas no uzticības balsojumiem (frakcijas vairākums Par); `--dry-run` (noklusējums) izdrukā, `--apply` ieraksta idempotenti. Rollback `data/rollback_coalition_periods_2026-10-16.sql` commitots PIRMS `--apply`. Tabula ir patiesība; skripts — kā to aizpilda un vēlāk pārbauda. Ierobežojums (ierakstīt docstring): partijas iziešana no koalīcijas termiņa vidū nenāk ar kabineta uzticības balsojumu — to pievieno ar roku rindu + rollback.
3. **`src/coalition.py`**: `coalition_periods(db)` un `coalition_at(periods, date, time) -> frozenset | None`. Robeža: balsojums pieder jaunajam periodam, ja `(vote_date, vote_time) >= (valid_from_date, valid_from_time)`. Pirms pirmā perioda → `None`. Docstring «Temporal semantics» atjaunināt.
4. **Serveris** `src/render/votes.py::_enrich_faction_breakdown`: statusu ņem no balsojuma perioda — frakcija periodā → `coalition`; cita reāla frakcija → `opposition`; bez-frakcijas bucket → `other`; ja periods `None` → visām `other` (kārtība pēc lieluma).
5. **JSON** `src/render/votes_matrix.py::_build_matrix_compact`: augšlīmenī `coalitions: [[etiķetes], …]`, katram balsojumam `co` = indekss vai `null`. `DATA.factions[].cs` paliek (matricas cilne — pēdējā frakcija, apzināti nemainīts).
6. **Klients** `assets/bmv1.js` ~1403: grupēšana pēc `DATA.coalitions[v.co]`, nevis `csMap()`. `co === null` → viena grupa «Frakcijas» bez Koalīcija/Opozīcija dalījuma.
7. **Audits** `/audit-integrity` (vai tā skriptā): jaunākā perioda kopa == frakcijas, kuru partijām `coalition_status='coalition'`; citādi brīdinājums (noķer BACKLOG 204 maiņu, ja jaunās valdības periods nav iesēts).

## Testi (pirms koda, jākrīt šodien)
- `tests/test_render_votes_matrix_json.py`: fiksturā 2 periodi; Siliņas laika balsojumam PRO=koalīcija, AS=opozīcija; balsojumam pēc 2026-05-28 otrādi; balsojumam pirms pirmā perioda `co is null`. Robeža: tās pašas dienas balsojums pirms uzticības laika → vecais periods.
- Pārlūka tests (tas pats harness kā `tests/test_balsojumi_url_filters.py`): Siliņas laika kartītē «PRO» rinda ir zem «Koalīcija».
- Mutācija: atgriez `csMap()` → pārlūka tests krīt.

## Ārpus tvēruma
`src/briefs.py`, `personas.py`, `parties.py`, `politicians.py`, `focus.py` — tur «šodien» ir pareizi. Matricas cilnes «pēdējā frakcija» grupēšana — dizaina izvēle, nav maldinājums.

## Pabeigšana (orķestrators)
Diff pārskats; `CHECK_PYTEST_WORKERS=3 bash scripts/check.sh`; `--apply` uz produkcijas DB tikai pēc rollback commit; renders `--only=balsojumi,static`; paritāte pret dzīvo lapu (saites, kopskaitļi, kartīšu skaits, tikai sagaidītās grupu maiņas); deploy; `verify_host`; CHANGELOG ieraksts (≤5 rindas) ar pamatojumu «pirms 15. Saeimas sanākšanas».
