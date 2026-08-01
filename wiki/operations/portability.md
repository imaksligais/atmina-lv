# Portabilitāte — ja tu NEESI Claude Code

Šī lapa ir svešam aģentu harness (cits CLI aģents, cits modelis, cloud runner),
kas grib izpildīt atmina rutīnas. Repo ir apzināti pašaprakstošs — noteikumi
dzīvo šeit, ne kādā privātā atmiņā — bet daļa izpildes semantikas ir Claude
Code specifiska. Šeit tās tulkojums.

## Kur dzīvo procedūras

| Kas | Kur | Kā lasīt, ja neesi Claude Code |
|---|---|---|
| Operating manual | `CLAUDE.md` (repo sakne) | Lasi pirmo un pilnībā — kontrakti #1–#13, slazdi **T1–T15** un eskalācijas noteikumi ir saistoši jebkuram izpildītājam. Diapazonu nepārraksti no galvas — pārskaiti `CLAUDE.md` § Known Traps. |
| ~~`AGENTS.md`~~ | **dzēsts 2026-08-01** | Repo saknē vairs NAV `AGENTS.md`. Tas bija novecojis (8 pretrunas ar `CLAUDE.md`) un aktīvi kaitīgs — sk. § Ne-darīt BACKLOG-ā. Ja tavs harness meklē `AGENTS.md` un neatrod, lasi `CLAUDE.md` un šo failu; cita „aģentu" faila šeit nav. |
| Skills (`/dienas-rutina`, `/deep-check`, `/social-thread`, `/seed-entity`, `/saeima-ingest`, `/audit-integrity`) | `.claude/commands/*.md` | Tās ir **izpildāmas soli-pa-solim procedūras ar iekodētiem guardrail**, ne fona dokumentācija. Atver attiecīgo failu un izpildi to secīgi pats. NEREKONSTRUĒ procedūru no CLAUDE.md kopsavilkuma — guardrail (T8 ūnija, publish-pauze, copy-bloki) dzīvo tieši šajos failos. |
| Aģentu prompti (`@claim-extractor`, `@contradiction-hunter`, `@devils-advocate`, …) | `.claude/agents/*.md` | Claude Code tos palaiž kā paralēlus sub-aģentus. Bez sub-aģentu mehānisma: atver failu, **pieņem tā lomu un izpildi to pašu darbu inline, secīgi pa politiķiem**. Frontmatter rindas (`name:`, `description:`, `model:`) ignorē — tās ir Claude Code maršrutēšana. |
| Workflow skripti | `.claude/workflows/*.js` | Claude Code orķestrācijas DSL. Neizpildi tos citā harness — lasi kā plānu (stadiju secība + promptu teksti) un izpildi stadijas manuāli. |
| Runbooki, komandas, kvalitātes latiņas | `wiki/operations/` | Parasts markdown, harness-neitrāls. Sāc ar `operacijas.md`, `commands.md`, `quality-bars.md`. |

## Kas ir iekodēts kodā (tevi pasargās) un kas nav (jāievēro pašam)

**Kodā:** `store_claim` idempotence un topic normalizācija, `save_analysis`
atomicitāte un `failures` saraksts, diakritiku validators (`src/quality.py`),
Pydantic modeļi (`src/models.py`), `check.sh` vārti.

**Daļēji kodā:** publish-pauze. Kopš 2026-08-09 `scripts/deploy.sh` preflight
izsauc `check_output.py --publish-gate-only` un iziet ar 1, ja `output/atmina/blog/`
ir pārskata lapa bez `approved=1` attēla vai ar orfānu (T15) — tas ir CIETS vārts,
ne konvencija, un to apiet tikai ar apzinātu `--no-output-check`. Konvencijā paliek
pati **atļauja**: kas drīkst iziet un kad, joprojām ir operatora lēmums, un vieni
vārti to neaizstāj.

**Tikai konvencijā (kods tevi NEapturēs):** `empty_doc_ids` obligātums (T5),
verbatim citāti, `failures` saraksta lasīšana (T3), rollback pārī ar katru roku
mutāciju, koalīcijas loģika tikai no `parties.coalition_status`.

## Cietie brīdinājumi svešam modelim

1. **Latviešu valodas vārti ir izpildītāja modeļa spēju jautājums, ne
   dokumentācijas.** Standing decision: ekstrakcija un visi LV teksti iet uz
   Opus, jo pat spēcīgs mazāks modelis (Sonnet, 2026-06-11 izmēģinājums) LV
   gramatikā kļūdījās ~30–40% stance lauku. Ja tavs modelis nav pierādījis LV
   gramatiku + stilistiku, NEDARI ekstrakciju/pārskatu pa taisno — dari
   ēnu-izmēģinājumu (sk. zemāk).
2. **Pirmais brauciens = dry-run.** Izpildi rutīnu bez `store_*` izsaukumiem un
   bez publicēšanas; salīdzini izvadi ar `quality-bars.md` un ar tās pašas
   dienas references izvadi. Tikai pēc operatora apstiprinājuma raksti DB.
3. **Publicēšana vienmēr paliek pie operatora** — pārskats, social, deploy.
   Viens apstiprinājums nav standing apstiprinājums (CLAUDE.md eskalācija #7).
4. **Meta-noteikums no CLAUDE.md darbojas arī tev:** ja divi noteikumi konfliktē
   un nevari izšķirt — apstājies un ziņo, nevis raksti.

## Kā zināt, ka viss vajadzīgais ir repo

Privātajā operatora atmiņā (Claude-specifiskā) NAV nekā izpildei kritiska —
standing rule prasa visus saistošos lēmumus turēt CLAUDE.md / wiki / aģentu
promptos. Ja izpildes laikā šķiet, ka trūkst noteikuma, kura dēļ jāminas —
tas ir signāls apstāties un jautāt operatoram, ne improvizēt.
