# Analīzes rubrikas

## Salience skala

| Diapazons | Līmenis | Piemēri |
|-----------|---------|---------|
| 0.9–1.0 | Core pillar | NATO, ES, nodokļi — partijas pamattēmas |
| 0.7–0.8 | Major policy | Nozīmīga politikas pozīcija |
| 0.5–0.6 | Standard | Regulāra tēma, vidēja nozīme |
| 0.3–0.4 | Minor | Maza tēma, epizodiska pieminēšana |
| 0.1–0.2 | Trivial | Komentārs, apsveikums, retweet |

## Confidence kalibrācija

| Situācija | Confidence | Papildu darbība |
|-----------|------------|-----------------|
| Tiešs citāts no politiķa, uzticams avots | 0.85–0.95 | — |
| Avota pārstāsts, ticams konteksts | 0.70–0.80 | — |
| Neskaidrs konteksts vai vājš avots | 0.50–0.60 | `reasoning` PREFIKSĀ `NEEDS_REVIEW: ` |
| Nezināma tēma vai šaubīgs avots | < 0.50 | `reasoning` PREFIKSĀ `NEEDS_REVIEW: ` + iemesls tajā pašā rindā |

> **Karogs dzīvo `reasoning` TEKSTĀ, un tikai prefiksā.** `needs_review` kolonnas vai parametra **nav** — pārbaudīts kodā 2026-08-02: `src/` nav neviena. Liekā atslēga claim vārdnīcā tiek **klusi atmesta**, tāpēc šādi „atzīmēts" claim nonāk DB izskatoties pilnīgi pārliecināts. (Līdz 2026-08-02 šī tabula prasīja tieši to — `"needs_review": true`.) Prefikss, ne beigas: no 113 atvērtajiem karogiem 97 bija tekstā beigās, un kanoniskais `LIKE 'NEEDS_REVIEW%'` tos neredz — sk. BACKLOG § `NEEDS_REVIEW` karogam ir DIVAS atrisināšanas konvencijas.

## Circuit breaker

Ja vienam politiķim ir vairāk par **12 dokumentiem dienā**, analizē pirmos 12 (augstākais salience; limits samazināts no 33 uz 12 2026-04-22 pēc batch-drift diagnostikas — sk. `.claude/agents/claim-extractor.md`). Atlikušie iet **OTRAJĀ SWEEP** — atsevišķs skrējiens ar tīru kontekstu, parasti paralēls sub-aģents. 12 ir kvalitātes limits, **nav** STOP un **nav** iemesls dokumentus izmest.

> **NEKAD neatzīmē neizlasītus dokumentus ar `empty_doc_ids`.** `empty_doc_ids` iet caur `src/analyze.py` uz `reviewed_doc_ids` un uzliek `reviewed_at`, tāpēc dokuments pazūd no `get_pending_politicians()` **uz visiem laikiem**, bez jebkādas pēdas, ka to neviens nav atvēris — neierobežots kluss satura zudums (T5 + T11). `empty_doc_ids` drīkst likt TIKAI dokumentam, kuru tiešām izlasīji un kurā tiešām nav pozīcijas. (Līdz 2026-08-02 šī sadaļa prasīja tieši pretējo.)
>
> Blakus, jo tas pats maldina: **`reviewed_at` ir per-DOKUMENTS, ne per-politiķis.** Dokuments, kas pārskatīts viena politiķa slotā, izskatās pabeigts arī tad, ja cita politiķa pozīcija tajā nav aiztikta — tieši tā 2026-08-01 gandrīz pazuda Jurēvica pozīcija doc 78085 (sk. BACKLOG § Junction lomas apgrieztas).

## Contradiction severity

| Tips | Apraksts |
|------|----------|
| `direct_contradiction` | Tieša pretruna — teica A, tagad saka ne-A |
| `reversal` | Apgrieziens — būtiska pozīcijas maiņa |
| `minor_shift` | Maza nobīde — nianse mainījusies, pamats tas pats |
