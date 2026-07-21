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
| Neskaidrs konteksts vai vājš avots | 0.50–0.60 | Pievienot `"needs_review": true` |
| Nezināma tēma vai šaubīgs avots | < 0.50 | `NEEDS_REVIEW` statuss |

## Circuit breaker

Ja vienam politiķim ir vairāk par **33 dokumentiem dienā**, analizē tikai pirmās 33 (augstākais salience). Pārējos atzīmēt ar `save_analysis(claims=[], empty_doc_ids=[...])` (`empty_doc_ids` ir obligāts — bez tā neko neatzīmē) vai palaist rutīnu vēlreiz.

## Contradiction severity

| Tips | Apraksts |
|------|----------|
| `direct_contradiction` | Tieša pretruna — teica A, tagad saka ne-A |
| `reversal` | Apgrieziens — būtiska pozīcijas maiņa |
| `minor_shift` | Maza nobīde — nianse mainījusies, pamats tas pats |
