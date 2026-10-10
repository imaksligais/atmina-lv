# Handoff 2026-09-30 (rīts) — citātu triāža + 29.09. sociālie posti

**Stāvoklis:** 29.09. pārskata X pavediens, FB un Reddit posti publicēti (operators). Citātu triāža pabeigta, commit `1c4f3f48`; vietnē kopš 11:04 (pilns renders + deploy `9ea0286e`, verify_host 9/9).

## Vakara rutīnai (2026-09-30)
- **10. solis — `politiki` jau renderēti un deployoti 11:04 (9ea0286e); vakarā parastais tvērums**; bija: (vai pilns renders): laboti 297 `claims.quote` (257 → burtisks avota teksts, 40 → NULL) ~250 profilos; `--only=` bez `politiki` tos neatjauno (commands.md § `personas` ≠ `politiki`). Citāti parādās arī `dashboard`/`focus` blokos.
- Ielāde šodien vēl nav palaista (09:26 stāvoklis).
- #725092 Valainis (Re:Baltica, Zemgales slimnīcas, `stated_at` 09-28) ieies šodienas pārskatā; LDDK 2 % kvota — dublikāts #724749, neglabāts.
- Rutīnas 3. solis rāda ✗, jo #725092 pretrunu pārbaudei (aģents: 0 kandidātu, 294 pozīcijas) nav `contradiction_hunt` loga rindas — vakara medības to nosegs.

## Gaida operatoru
- **5 claims ar nepamatotu stance — ATSAUKTI 2026-09-30 (deploy 9ea0286e, pilns renders ar politiki)**; bija: #275 Braže (prezidenta atļauja nēsāt apbalvojumu ≠ viņas pozīcija), #7514 Briškens (raidījuma anotācija, pats nerunā), #6978 Dombrava (stance apgalvo pretējo tvītam), #6929 Pūpols, #6951 A. Hermanis (stance izdomāta no migrācijas tvīta). Ieteikums: atsaukt ar rollback, pārattiecināt vēlāk.
- **Vēl 9 atsaukti + 21 stance LV labojums (deploy `7d6578d7`, verify_host 9/9).**
- **17 B_REWRITE izpildīti 09-30 pēcpusdienā (DB, NAV deployots):** 15 stance šaurāk + re-embed, 3 atsaukti (#1568, #7426, #17778), #689653 `NEEDS_REVIEW` (operatoram jānoskatās Lapsas video); pārsaistīti #14346, #7489, #18375. Rollback `data/rollback_stance_b_rewrite_2026-09-30.sql`. **Vakara rutīnas renderam jāietver `politiki`**, lai tie nonāk vietnē; deploy — ar operatora «jā».
- 17 citi OPERATOR — 14 «citāts no cita dokumenta» (pārsaistīt vai NULL), 3 citi; 65 stance karogi (14 tikai gramatika/garumzīmes, 51 stance plašāka par avotu — nākamā sesija, katrai obligāts re-embed). Saraksti: `docs/audits/2026-09-30-citatu-triaza.md`.
- 8 sociālo melnrakstu faili (`docs/tweet_bank|social/2026-09-29*`, `2026-09-30*`) nav komitēti.

## Nākamā sesija — stance pret avotu, pārējais korpuss (operators 09-30: «pārbaudīt vēl»)

**1.–2. solis IZPILDĪTS 09-30:** izlase 300 → A+B april 47 % (~580), bez citāta 12 % (~100), vēlāki 16 % (~860). Atskaite `docs/audits/2026-09-30-stance-izlase/README.md`. Gaida: operatora apjoma lēmums (3. solis) + rubrikas 4. punkts; izlases 101 priekšlikums vēl jāverificē un jāpiemēro.

Šodien stance pārbaudīti tikai 383 claims ar citāta problēmām; defekti koncentrējās aprīļa partijās. Korpuss (09-30): 7 826 `position`, no tiem 1 552 izveidoti līdz 2026-05-01, 870 bez citāta.
1. Vispirms 17 B_REWRITE (`docs/audits/2026-09-30-citatu-triaza/stance_grades.json`) + 3 saišu pārsaistīšana.
2. **Mērījums pirms apjoma (T18):** nejauša izlase ~300 claims (150 aprīlis, 75 bez citāta, 75 maijs–septembris), tās pašas A/B/C/D pakāpes kā `stance_grades.json`. ~5 Opus palīgi pa ~60 — tas ir fan-out, vajag operatora «jā» ar šo skaitu.
3. Pēc defektu īpatsvara pa slāņiem izlemj: pilna aprīļa + bez-citāta pārbaude (~40 palīgu) vai tikai augstā riska slānis. A → atsaukt ar rollback, C → LV labojums + re-embed, B → šaurāka stance ar LV vārtiem.

## 09-30 pēcpusdiena — izpildīts (DB, NAV deployots)
- Izlase 300: 7 atsaukti + 94 laboti; aprīļa pilnā pārbaude 1 096: 34 atsaukti + 582 laboti (visiem re-embed). Kopā ar rītu: ~700 profilu stance mainīti → **vakara renderā OBLIGĀTI `politiki`** (vai pilns renders); deploy tikai ar operatora «jā». `check.sh` zaļš.
- 4 HOLD operatoram + blakusatradumi: `docs/audits/2026-09-30-stance-izlase/README.md` § Piemērots.
- `claim-extractor` kontrolsarakstam pievienots 7. jautājums (viss stance šajā dokumentā; laiks/modalitāte; cēlonis/sekas).

## Nākamais — claim-extractor pārbūve (operators 09-30: «ļoti garš, jāizdomā kaut kas»)
Prompts 597 rindas / ~16k tokenu; puse apjoma = žurnālistu slots (11,8 KB), Critical Rules ar incidentu vēsturi (10,5 KB), save_analysis mehānika (9,3 KB); 49 claim ID atsauces. Noteikumi, ko pārkāpj (vilcinājumu nomešana, jautājums → apgalvojums), promptā JAU ir — tie nedarbojas lēmuma brīdī.
Priekšlikums (gaida operatora «jā»): (1) kodols ≤150 rindas — pozīcijas definīcija no `RUBRIKA.md`, 7 jautājumi, izvades forma, NEEDS_REVIEW, LV vārti; (2) žurnālistu slots, tēmas, save mehānika, incidentu arhīvs → atsauces faili, lasa tikai pēc vajadzības; (3) koda vārti: katrai pozīcijai obligāts burtisks `support` fragments, `save_analysis` pārbauda `support in doc_text`; (4) viens dokuments = viens lēmums (pakošana līdz 8 dokiem vienā aģentā ienes faktus no blakus dokiem). Pirms ieviešanas: eval uz ~40 šodien verificētiem dokiem — vecais prompts pret jauno, bez rakstīšanas DB; ieviest tikai, ja labāk.
