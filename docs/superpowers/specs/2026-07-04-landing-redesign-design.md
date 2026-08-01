# Sākumlapas pievilcības pārveide (A + vēlēšanu akcents) — dizaina spec

**Datums:** 2026-07-04 · **Statuss:** apstiprināts sarunā (operators izvēlējās "A + B akcents")
**Konteksts:** 2026-07-04 pilnais UI audits (1.–3. fāze DONE) atklāja, ka sākumlapai trūkst emocionālo āķu: nav seju, vizuālais paraksts (sepia ilustrācijas) aprakts trešajā ekrānā, Chart.js noklusētais zilais lauž vintage identitāti, "Šonedēļ 0 balsojumi" izskatās miris, vēlēšanu countdown (91d) ir tikai čips stūrī.

## Mērķis

Sākumlapa 5 sekundēs pasaka, kas šī ir par lapu, un izskatās dzīva un vizuāli savdabīga — izmantojot TIKAI esošos resursus (politiķu foto `assets/photos/<slug>.jpg`, sepia ilustrācijas, `PARTY_COLORS`/`TOPIC_COLORS`, `days_until_election`). Nekādu jaunu datu pipeline.

## Prasības pa sekcijām

1. **Hero asināšana.** Virsraksts, meklētājs, 3 sparkline kartes paliek. Karuseļa kartē: avatārs 42→56px, citātu duelis "Iepriekš → Pašlaik" vizuāli dominē (lielāks pretstatījuma marķieris, mazāk meta-teksta). Jauns countdown bloks hero zonā: "Līdz 15. Saeimas vēlēšanām — {{ days_until_election }} dienas" + saite "Partiju programmas →" uz `partijas.html`.
2. **Sekciju secība:** Hero → Jaunākie pārskati → Jaunākās pretrunas → Līderu josla (ex-Rangi) → Jaunākās analīzes → Tendences → Pēdējie balsojumi.
3. **Rangi → Līderu josla ar sejām.** 4 kolonnas paliek; katras #1 = mini-kartīte ar foto (40–48px), vārdu, vērtību; pārējie kā kompaktas rindas ar 20px avatāriem (foto ja ir, citādi iniciāļu aplītis ar partijas krāsu — tas pats paterns kā hero `hero-feature-avatar`).
4. **Pretrunu kartes:** kopsavilkums `-webkit-line-clamp: 4`; citātu pāris = galvenais vizuālais elements; foto lielāks. Bez datu izmaiņām.
5. **Tendenču grafiki zīmola paletē:** topicsChart stabiņi no `TOPIC_COLORS`, politiciansChart no katra politiķa `party_color`; krāsas padod no `dashboard.py` konteksta caur `safe_json`, nevis hardkodē JS.
6. **Šonedēļ bez mirušām nullēm:** ja `votes_7d == 0` → skaitītāja vietā fakts "Saeima brīvlaikā · pēdējie balsojumi {pēdējā balsojuma datums}"; tas pats princips `contradictions_7d == 0` ("pēdējā pretruna {datums}").

## Ierobežojumi (nedrīkst aiztikt)

- Vintage-print identitāte, gaišā/tumšā tēmu mehānika (`--party-color` konvencija ar `color-mix` gaišajai).
- `base.html.j2` chrome / `_CHROME_SPECS`; curated lapas.
- Nekādu jaunu JS bibliotēku; Chart.js paliek ar `defer`.
- Char-baselines pārsvētī centralizēti pēc izmaiņām (REGEN=1), `bash scripts/check.sh` zaļš, deploy tikai `--no-delete`.

## Skartie faili

`templates/index.html.j2` (sekciju secība, hero, līderu josla, clamp, chart krāsu dati), `src/render/dashboard.py` (has_photo rangiem, brīvlaika fakts, chart krāsu saraksti), `src/render/rankings.py` (has_photo lauks, ja ērtāk tur), `assets/style.css` (countdown bloks, līderu josla, clamp, avatāru izmēri), testi (hermētiski helperiem).

## Verifikācija

check.sh + baselines; Playwright vizuālā pārbaude 1440px+375px ABĀS tēmās; live pārbaude pēc deploy (foto 200, chart krāsas ≠ #3b82f6 zilā, countdown redzams).
