# HANDOFF 2026-09-21 — nedēļas analīze 2026-09-14…20 publicēta; izpildītājs: Devin CLI (SWE-2)

> Publisks fails — operatīvās piezīmes, nekā identificējoša.
> Konteksts: pārskats rakstīts/verificēts/publicēts vienā sesijā; operators deva «ģenerē un deploy».

## 1. Stāvoklis

| solis | stāvoklis |
|---|---|
| Pārskats DB | `context_notes` **id=625**, `weekly_brief`, topic `nedēļas analīze 2026-09-14 līdz 2026-09-20` |
| Publicēšanas atļauja | `publish_approvals` ieraksts `nedela-2026-09-14` (2026-09-21 08:20) |
| Attēls | `brief_images` id **338** `approved=1` (sepia full-bleed); 336 un 337 `approved=2` (operatora noraidījumi) |
| Deploy | versija `c1a73abb-5d88-4efe-a01f-5487d94b6ec3`; dzīvs: `https://atmina.lv/blog/nedela-2026-09-14.html` 200 |
| Darba fails | `data/_weekly_draft_2026-09-14.md` (identisks #625 saturam; var dzēst) |

## 2. QA atradums — IZPILDĪTS 2026-09-21 (operatora «salabo»; deploy `1569452c`, rollback `data/rollback_note_625_frakcijas_2026-09-21.sql`; arī 88. rindkopa: darba kārtības balsojums + NA 8/9 nebalsoja). Sociālie melnraksti: `docs/tweet_bank/2026-09-21-nedelas-parskats-social.md`, `docs/social/2026-09-21-*` — gaida atļauju.

Sākotnējais atradums:

`@quality-reviewer` palaists **pēc** publicēšanas (operatora «palaid») — verdicts **PASS ar vienu [JALABO]**:

- **Rindkopa 87** (bloku komentārs, vote_id=8204): teksts «pret balsoja ZZS un LPV (27)» — faktiski Pret=27 ir **ZZS 9 + LPV 5 + AS 4 + ārpusfrakciju 9**. Izlaistā detaļa ir tēzes kodols: **AS sašķēlās** (4 pret / 3 atturas / 4 nebalsoja / 0 par) — premjera partija neatbalstīja NA graudu aizliegumu. `saeima_votes.summary` forma: «pret — ZZS, LPV un daļa AS».
- Sekundāri (nav bloķējoši): rindkopa 88 — NA frakcija pie divu-māšu likuma 8/9 `Nebalsoja` (DB summary to min, teksts nē); «vienbalsīgi» piektdienas valdības lēmumam koroborē doc 109387 (X ieraksts), ne citētā pmo.ee saite.
- Labojuma ceļš: `store_context_note` UPSERT uz #625 (weekly_brief ir izņēmums append-only likumam) + `--only=dashboard,blog,static` + deploy. **Operators vēl nav teicis «labo».**

## 3. Attēlu vēsture

- 336 — `weekly` stils AR virsrakstu (noklusējums `weekly_brief` tipam).
- 337 — `editorial --no-text`; operators noraidīja: «puse kā editorial lapa, image tikai sānā» — stils atstāj labo kadra daļu tukšu.
- 338 — `sepia` (teksta-brīvs pēc stila definīcijas), full-bleed kā dienas pārskatiem — operators apstiprināja.
- Mācība: nedēļas attēlam, kas jāizskatās kā dienas, `--style sepia` pārsniej `weekly` noklusējumu.

## 4. Budžets

`src/graphics/config.py`: `MONTHLY_BUDGET_USD` 5.00 → **20.00** (operatora lēmums 2026-09-21 — septembris bija izsmelts: 136 ģenerācijas / $5.265). Viena ģenerācija = $0.039.

## 5. Vides slazds (deploy no šī harnessa)

Šajā sesijā `bash` rezolvējās uz `/c/Windows/system32/bash` (WSL launcher), ne MSYS — deploy zem WSL: `.env.deploy` avoti nonāk WSL env, bet `npx` ir Windows process → `CLOUDFLARE_API_TOKEN` cauri neaizgāja (nav WSLENV), un Windows `FIND.EXE` salauza failu skaitīšanu. Darba risinājums:

```
PATH=/usr/bin:/bin:$PATH /usr/bin/bash scripts/deploy.sh --no-delete
```

Operatora parastajā terminālī (Git Bash) tas netraucē. Ja pārtrūkst vēlreiz — tas ir tas pats cēlonis.

## 6. Ko šī sesija nedarīja / nav vārtu

- `@quality-reviewer` pirms publicēšanas netika palaists (orķestra īsceļš — operators apstiprināja deploy tieši; QA palaists pēc fakta). Runbook prasa QR PASS **pirms** deploy — nākamajam nedēļas pārskatam tas ir vārti, ne opcija.
- Sociālie pavedieni: nav rakstīti, nav publicēti (atsevišķa atļauja nepieciešama).
- `render_baseline_*.json` fikstūras nav regenētas — pārskata renders mainīja `index.html` hash likumīgi; ja tests klauvē, `REGEN=1 pytest tests/test_render_chars.py`.
