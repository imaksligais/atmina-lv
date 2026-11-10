# HANDOFF 2026-11-10 (vakars): dienas rutīna

Papildina `docs/HANDOFF-2026-11-10.md`. Rutīnas diena 10.11. palaista vakarā (vienīgā ielāde dienā).

## Izdarīts
- **Ielāde:** 5/5, +790 dokumentu. Pirmā ielāde ar jauno X kodu iztur pārbaudi: `ctx_reply` 174, `ctx_quote` 166, pašu `@`-tvītu 5073 → 5199, jaunu `/status/<id>` dublikātu grupu 0 (mans vaicājums: 61 → 61; TSV bāzē 45 — atšķirības cēlonis nav noskaidrots). `replies_before_floor` = 2142 (handoff lēsa ~205).
- **Ekstrakcija:** 38 aģenti, 6 kārtas, plāns 255 pāri → atkārtots plāns 0. Pozīcijas 753466–753576 (111; 753496 dzēsta → 110). Atgūšana: 12/12 web pāri (+5 pozīcijas).
- **2c:** 30 atzīmētas → 23 izvērtētas, 753496 dzēsta (Delfi neoficiālā informācija, tas pats publiski 753564; dokuments 155260 paliek), 753575 `stated_at` → 08.11. Rollback `data/rollback_needs_review_rutina_2026-11-10.sql`.
- **2d:** stance-checker 110/110 (B 4, C 3, U 1). Piemēroti 8 labojumi + 3 pēc quality-reviewer. Pārbaudītājs NOĶĒRA zināmo 753516 defektu, bet NENOĶĒRA 753546 («norāda» Leščinska pārmetumam).
- **Pretrunas:** balsotāji 25/25, pozīcijas 110/110; #67 Kulbergs (2030. g. budžets bez deficīta) `minor_shift`, `confirmed=0` (11.11. operators noraidīja, dzēsta). Jaunā puse balstās LSM rakstā, ko daļa politiķu apstrīd kā izkropļotu. 45 noraidītie kandidāti panelī.
- **Saeima:** 10.11. nesēdēja; manifests pārģenerēts; 03.11. paritāte: trūkst 0.
- **Spriedzes:** 9 pieņemtas, 7 noraidītas. **Piezīmes:** 814–817. **Pārskats:** note 818, quality-reviewer labojumi piemēroti; `check.sh` 4182 passed.

## Publicēts un izlemts
- **Pārskats publicēts 10.11. 23:50** ar operatora «jā» (versija 694bfdc5, attēls #448). Live: attēli 4/4 HTTP 200, `verify_host` 9/9. Deploy aizveda arī KNAB etiķeti un OG `?v=`.
- **Operatora lēmumi 11.11.** (rollback `data/rollback_operator_2026-11-11.sql`):
  - pretruna #67 dzēsta (nekad nav publicēta): bez tieša citāta neinteresanta;
  - 753500, 753516, 753541, 753542 izvērtētas un paliek;
  - 753529, 753478 dzēstas (nav konteksta); dokumenti paliek;
  - 4 Vēstneša pāri (155938, 155939) atzīmēti kā izvērtēti: stenogrammā tikai pieminēti;
  - **nākamais deploy** noņems 753529 un 753478 no profilu lapām (līdz tam tās vēl ir live).
- 155938 ir 29.10. stenogramma — 4. darba «0. solis» (kāpēc nav 29.10. stenogrammas) ir atbildēts: tā ir DB.
- DB kopijas: svaiga ārējā kopija 11.11., pēc tam abi `.db` izdzēsti (pārējā `.scratch/xctx-trial/` paliek).

## Ievērības vērti, bet neatvērti
- Hunter: Kulbergs maijā (#20528) «veselībā netaupīs» ↔ slimnīcu tīkla reforma plānā — pozīcijas par reformu vēl nav.
- Skujiņa-Rubene 795/Lm14 (prēmiju atcelšana, darba kārtības balsojums) — devils-advocate: robežgadījums.
- Žurnālistu relay sloti (pid 57, 242) nonāk ekstrakcijas plānā; satīras doks 155458 piesaistīts pid 242.
- Vītols (pid 64) `role` var būt novecojis (avotos «finanšu ministra padomnieks») — T6 pārbaude. Kulberga `role` «Ministru prezidents» ir pareizs: 9.09. rīkojumu viņš paraksta kā Ministru prezidents (vienlaikus nākamās valdības veidotājs).
- Plāna 7. solis (atpakaļaizpilde 153 dokiem) tagad ir atbloķēts.
