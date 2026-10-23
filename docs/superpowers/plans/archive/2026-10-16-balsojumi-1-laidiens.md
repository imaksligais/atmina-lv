# Balsojumi cilne — 1. laidiens (attēlojums, ne dati)

**Operators 2026-10-16:** «sāc ar balsojumi cilni kā ieteikts, bet pārliecinies, ka nezaudējam datus — tie tikai attēloti labāk».
Analīze: `.scratch/balsojumi_redesign/kritika.md`, `astra.md` (nav repo).

## Nepārkāpjamais noteikums
Katrs fakts, ko kartīte rāda šodien, paliek sasniedzams: motīvs, dokumenta nr., stadija, steidzams, ķēdes saite, datums + laiks (ar sekundēm), iznākums, Par/Pret/Atturas skaitļi, visas frakciju čipas ar skaitļiem un `title`, kopsavilkums + priekšlikuma piezīme, 3 saites, VISI izsekotie politiķi (vārds, frakcija, balss). Mainās tikai izkārtojums un TAS, KAD saraksts tiek uzbūvēts. Datu fails (`balsojumi-matrica*.json`), Python renderētājs un matricas/likumprojektu cilnes netiek aiztiktas.

## Izmaiņas
1. **Slinkais politiķu saraksts.** `archiveBuildCard` vairs neiekļauj `<table>`; `<details class="vote-tracked" data-vi="i">` ar to pašu `<summary>` «Izsekotie politiķi (N)». Tabulu uzbūvē pirmajā atvēršanā (deleģēts `toggle` klausītājs ar capture, `assets/*.js`, bez inline JS) no TĀS PAŠAS `trackedForVote(i)` funkcijas — rindas, secība un etiķetes identiskas. Eksportē `window.balsojumiTrackedHtml(i)`.
2. **Izvēlētā deputāta balss kartītē.** Ja `filters.deputies` nav tukšs, katrai izvēlētajai personai kartītē (tūlīt pēc iznākuma/skaitļu rindas) rinda: vārds (saite uz profilu), frakcija, balss nozīmīte ar `VOTE_LABEL` (Par/Pret/Atturas/Nebalsoja). Ja personai šajā balsojumā nav ieraksta (`.`): «nav individuālā ieraksta» — NEKAD «nepiedalījās». Atturas paliek atsevišķa, dzeltena etiķete.
3. **Mobilā kartīte (≤600 px).** `.vote-header` kolonnā: datums atsevišķā rindā virs motīva, motīvs pilnā platumā. Pilns laiks paliek.
4. **Iznākuma mala.** Zaļa tikai `Pieņemts`, sarkana tikai `Noraidīts`, pārējie (`Likums`, `Paziņojums`, `Nod. kom.`, tukšs) — neitrāla (`--text-muted`/`--border`). Saskaņā ar esošo `test_unknown_result_never_renders_a_red_badge`.
5. **Mobilais pirmais ekrāns.** ≤600 px: meklētājs pirmais un pilnā platumā (16 px fonts, ≥44 px augsts); 4 izvēlnes 2×2 režģī; leģenda kompaktāka, Atturas teikums paliek redzams. `#votes-archive-info` → `role="status" aria-live="polite"`. Hero tipogrāfija netiek mainīta.

## Testi (projekta noteikums: vispirms, maz, katram skaidrs darbs)
Paplašina `tests/test_balsojumi_readability.py` node harnesu:
- **Datu saglabāšana:** kartītes HTML + `balsojumiTrackedHtml(i)` kopā satur katra izsekotā politiķa vārdu, frakciju un balss etiķeti (fixture: 2 politiķi), un kartītes HTML vairs nesatur `<table` (pirms izmaiņas: krīt).
- **Izvēlētā balss:** `filters.deputies=["Cilda Cīrule"]` → kartītē «Cilda Cīrule» ar «Par»; balsojumā 0/1 (kur `.`) un divu personu izvēlē — «nav individuālā ieraksta», nevis «nepiedalījās».
- Mutācijas pierādījums katram.
Pārbaude pēc renderēšanas (orķestrators, Playwright): dzīvās lapas pirmo 200 kartīšu teksts (ar atvērtām detaļām) ⊆ lokālā build teksts — datu paritāte; ekrānuzņēmumi 390 px un 1280 px, abās tēmās.

## Ārpus tvēruma
Meklēšanas diakritika, URL stāvoklis, vēsturiskā frakcija, matrica, likumprojekti, hero — nākamie laidieni. Deploy — tikai ar operatora atļauju.
