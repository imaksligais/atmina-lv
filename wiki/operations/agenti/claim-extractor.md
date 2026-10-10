# @claim-extractor

> Kanoniskais prompts (izpildei): [.claude/agents/claim-extractor.md](../../../.claude/agents/claim-extractor.md) — šī lapa ir īss apraksts cilvēkiem. Atsauces faili, ko aģents lasa pēc vajadzības: [.claude/references/claim-extractor/](../../../.claude/references/claim-extractor/).

Neitrāla politisko pozīciju ekstrakcija no dokumentiem.

**Ko dara:** lasa dokumentus (ziņas, tvītus) un izvelk konkrētas politiķu pozīcijas. «Nevaru noteikt» ir derīgs rezultāts.

**Kad izmanto:** dienas rutīnas solī pēc dokumentu ielādes; dispečēšana pēc `scripts/plan_extraction.py` (viens pid = viens aģents kārtā, mazas rindas pako līdz 8 dokiem).

**Ievade:** `get_politician_documents(pid)`; `get_existing_claims(pid, stated_around=…)` dublikātu pārbaudei.

**Izvade:** `save_analysis()` ar claims sarakstu → DB `claims` tabula; pēc tam obligāta pretrunu pārbaude (`search_similar_claims`, CLAUDE.md inv #7).

## Pārbūve 2026-09-30 (prompts v4)

Prompts no 597 rindām saīsināts līdz ~100 rindu kodolam. Iemesls: stance pret avotu mērījumā (1 696 pozīcijas) 16 % pozīciju kopš maija bija plašākas par avotu, lai gan noteikumi pret to promptā jau bija — garā tekstā tie nedarbojās lēmuma brīdī.

- **Kodols:** pozīcijas definīcija (tā pati, ko lieto vērtētāji — `docs/audits/2026-09-30-stance-izlase/RUBRIKA.md`), «katrs dokuments ir atsevišķs lēmums», 7 jautājumi, izvades forma, confidence un NEEDS_REVIEW (§ 4), cietie noteikumi.
- **Atsauces faili:** `sloti.md` (žurnālisti, organizācijas, biroja balss, simulācija), `datumi-dublikati.md` (`stated_at`, ±5 d dublikāti), `glabasana.md` (`save_analysis` mehānika, `failures`, vide, pretrunu solis), `temas.md` (robežas un precedenti).
- **Koda vārti `support`:** katrai `position` pozīcijai obligāti 1–3 burtiski fragmenti no ŠĪ dokumenta teksta. `save_analysis` (`src/support.py`) pozīciju neglabā, ja fragmenta nav vai tas nav avotā, un ziņo `failures` (`missing_support` / `support_not_in_source`). Doks, kuram visas pozīcijas atteiktas, netiek atzīmēts kā izskatīts. Tests: `tests/test_support_gate.py` (mutācija pārbaudīta).
- **Eval pirms ieviešanas:** `docs/eval/claim-extractor-prompt-v4-2026-09-30.md`.
- Vecā prompta vēsture (incidenti, claim ID): `git show f4dd442b:.claude/agents/claim-extractor.md`.

## Galvenie noteikumi

- `sentiment` vienmēr 0.0.
- Tēmas — 33 grupas no `src/topic_map.py`; tēmu izvēlas izteikuma pamatojums, ne instruments.
- Claims bez `source_url` tiek nomesti un ziņoti `failures` (`missing_source_url`) — tas nav kluss zudums, bet viegli nepamanāms.
- Max 12 doki vienā pasē; atlikušos apstrādā svaigs aģents (kvalitātes robeža, ne STOP).
- **Neizlasītus dokumentus NEDRĪKST atzīmēt ar `empty_doc_ids`** — tas uzliek `reviewed_at`, un dokuments pazūd no rindas bez pēdas (T5 + T11).
- `claim_type` = `'position'` (noklusējums). `'saeima_vote'` rezervēts `@saeima-tracker`; `'commentary'` ceļš slēgts kopš 2026-04-25.
- `quote` — burtisks pirmās personas teksts vai `null`; `quote=null` → confidence ≤ 0.65 (0.65 tikai skaidram atstāstam); jebkura šaubu pazīme → ≤ 0.6 + `NEEDS_REVIEW:`.
- Žurnālistu un mediju plūsmas (`journalist`/`organization` + `relay`) ir atklāšanas kanāli: slota pasei noklusējums `empty_doc_ids`; text-scan piesaista politiķus, ko tās citē. Pārbaudi pret DB, ne pret tabulu: `SELECT tp.relationship_type, sa.feed_type, COUNT(*) FROM social_accounts sa JOIN tracked_politicians tp ON tp.id=sa.opponent_id GROUP BY 1,2`.

**Shēmas slazds:** tvītiem `documents.title` VIENMĒR ir NULL, un `text` kolonnas nav — saturs ir `content`.

**Indirect-reference vārti (`save_analysis`):** ja `reasoning` satur frāzes kā «nav paša pozīcij», «bare retweet», «tikai pieminē», `save_analysis` automātiski pieliek `NEEDS_REVIEW:` marķieri (claim netiek nomests).

**Novērojumi, ne defekti:**
- `platform` nav autorības pierādījums: doc 88328 ir `platform='x_mention'`, bet tas ir Kulberga paša tvīts. Autorību pārbauda pret `source_url` + `social_accounts`.
- Kandidātu saraksta raksti nes daudz junction rindu bez pozīcijām (doc 93539) — tas nav matcher defekts; programmu saturs iet `program_promise` ceļā.

---
> Pilns aģenta prompts: `.claude/agents/claim-extractor.md`
