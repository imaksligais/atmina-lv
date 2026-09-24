---
name: seed-entity
description: Onboard a new tracked politician, party, organization, or CVK-list carrier — name_forms with diacritic+ASCII variants, generated-inflection collision preview, independently verified party, x_handle↔social_accounts consistency, INSERTs + paired rollback for operator approval. Encodes the diacritic-pair, joint-list, and ≤4-char guardrails.
argument-hint: "<name> [politician|party|org|carrier] [party] [role] [x_handle]"
---

# Seed entity — jaunas entītijas pievienošana

Onboard the entity in `$ARGUMENTS`. Pattern reference: `wiki/operations/seeding.md`. Quality bar: `wiki/operations/quality-bars.md § Seedēšana`.

## Why this shape

Every recurring matcher trap is a *pre-seed* decision. The matcher is substring-based and does NOT fold diacritics (CLAUDE.md Schema invariants) — missing an ASCII variant means the politician never links from X/RSS. `scripts/audit_matcher_name_forms.py` catches missing ASCII variants but NOT a wrong stem (Šnore was seeded as `Šņore`, 2026-05-16) — stems are eyeball-verified. Inflections are generated at match time by `src/matcher.py::_latvian_surname_inflections`, and generated forms ≤4 chars are substring bombs (T1: `Kolu`→"Kolumbija", twice). News joint-list wording mislabels party (Tutins seeded as LPV from "LPV/Kopā Latvijai", 2026-04-26). `tracked_politicians.x_handle` (render) and `social_accounts.handle` (fetch) silently diverge (Ašeradens). `parties.short_name` is `NOT NULL UNIQUE` — a party INSERT without it fails.

## Procedure

1. **Duplicate/typo check.** Query `tracked_politicians` for name + `name_forms` overlap (and `parties.name`/`short_name` for party seeds). A near-match = STOP and ask — it may be the same person misspelled.
2. **Build `name_forms`.** Base LV name, ASCII-stripped variant(s), established short forms. Do NOT enumerate inflections — the matcher generates them. Verify stems by eye against how LV press actually writes the name.
3. **Collision preview.** Run `_latvian_surname_inflections` over each surname form and list every stored OR generated form ≤4 chars. For each, grep recent `documents` for substring hits to see what it would collide with. Each flag = operator decision (accept / add `negative_patterns` / drop the form). Never auto-add `negative_patterns`.
4. **Verify party independently** (Wikipedia LV / ir.lv / official party site — never joint-list news wording). Bezpartejisks → `party=NULL`. Interest groups → `relationship_type='organization'`, `party=NULL` (seeding.md § Institucionālā balss). Common-noun surname → consider the journalist/Seržants guard.
5. **Party / carrier seeds.** `parties` row requires `name` + `short_name` + `coalition_status` (operator confirms the value; non-Saeima lists follow the operator's call — `get_coalition_map` treats unknown as "other" → UI "Bez Saeimas frakcijas"). CVK-list case: seed the party row AND the carrier politician together; program ingest then follows CLAUDE.md Data Contract #4a (`scripts/ingest_url.py --url <CVK url> --politician-id <carrier>`, one consolidated promise per topic).
6. **X account.** Set BOTH `tracked_politicians.x_handle` and a `social_accounts` row (`platform='twitter'`, `feed_type='first_party'` for own accounts / `'relay'` for aggregators, `active=1`) with the SAME handle; confirm live that the account belongs to the person.
7. **Emit SQL + rollback.** INSERTs plus paired `data/rollback_seed_<slug>_<date>.sql` (header: forward change + apply date). AskUserQuestion approval BEFORE executing; execute in one transaction; commit both files together.
8. **Post-seed.** Run `scripts/audit_matcher_name_forms.py`; then `link_politicians_to_documents(rescan_all=True)` if historic documents should link to the new entity (manual, not via morning_ingest).
9. **Cohort audit before anything publishes (CLAUDE.md T13).** A rescan over the historic corpus is a *bulk per-person ingest*, and that is where homonym contamination arrives at scale — one bad form silently attaches dozens of documents about a different person, and each one then looks like evidence. So: after the rescan, read a sample of the NEW junction rows per seeded entity (not just the counts), confirm the matched text is really about this person, and keep `vad_disambig` / `negative_patterns` whitelists as the fix path — operator-approved, never auto-added. Seeding a whole cohort (a CVK list, a new faction) means auditing **every** member this way before the first render, not the ones that look risky. The 2026-07-31 Valsts kontrole rescan is the reference: 336 links, exactly 2 wrong, and both were only findable by reading rows.

## Guardrails

- Operator approves the final `party` value and EVERY ≤4-char form — no auto-commit, no auto-`negative_patterns`.
- Both diacritic and ASCII variant sets present, or the seed is INCOMPLETE.
- Coalition lives on `parties.coalition_status`, never per-politician fields (inv #10).
- LV grammar + stylistics gate on every stored string (`role`, descriptions).
- Paired rollback committed alongside the seed (CLAUDE.md Schema invariants).
