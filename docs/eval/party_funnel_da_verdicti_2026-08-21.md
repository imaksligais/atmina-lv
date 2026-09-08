# DA top-30 verdikti — partiju pretrunu piltuve (2026-08-21)

Inline `@devils-advocate` izskats (bez subaģentiem, pa partiju klasteriem) 30 pāriem no
[`party_funnel_2026-08-18.md`](party_funnel_2026-08-18.md). Binārais vārts: KILL vai KEEP
(`scripts/partiju_pretrunas.py` procedūras 3. solis).

**Iznākums: 30 × KILL, 0 × KEEP.** Nekas nav glabāts DB — 0 `store_contradiction` izsaukumu,
DB read-only. Tas ir normāls iznākums (~1 publikējams uz ~2700 jēlpāriem; šeit 1807 ekrānēti
→ 0), nevis izvairīšanās — katram KILL ir konkrēts pamats zemāk.

Obligāto pārbaužu statuss (HANDOFF 2026-08-21): T14 ķēdes vilktas pret DB visiem 30 pāriem
(`.scratch/da_top30_verify.py`, read-only); frakcijas sadalījums katrā `vote_id`
pārbaudīts pret `saeima_individual_votes` (sakrīt ar funnel izvadi; funnel rāda tikai
Pret/Atturas, DB papildus rāda `Nebalsoja`); virziena spriedums un Atturas semantika
katram pārim; laika plaisa (2026 programmas, `stated_at` 2026-07 vs balsojumi 2022–2026)
novērtēta — nevienam pārim tā nebija izšķiroša, jo visi krita uz agrākiem pamatiem.

## KILL tipi (sadale)

| Iemesls | Pāri |
|---|---|
| **Virziena saskaņa** — Pret balsojums faktiski SASKAŅOTS ar solījumu | 1, 2, 7, 9, 16, 26 |
| **T14 inversija/jaukta ķēde** — citētais viens balsojums apgriež ierakstu | 11, 14, 19, 25 |
| **Atturas semantika** — atturēšanās nav citējama kā pozīcija (T14/atturas noteikums) | 13, 17, 20, 23, 28 |
| **Procedurāls/whip konteksts** — pieprasījumi, budžeta standoff, tehniski grozījumi | 3, 10, 12, 15, 18, 21, 24, 27, 30 |
| **Tēmas līmenis bez satura konflikta** | 4, 5, 6, 8, 22, 29 |

## Pāru verdikti

### ST klasters

1. **KILL** (VAD 605/Lp14 2.las., #2294). Grozījumi **paplašina** iesaukšanas tiesības — Pret
   paplašinājumam ir saskanīgi ar solījumu atcelt obligāto dienestu. Turklāt ķēde jaukta:
   1.lasījumā (#2035) ST balsoja Par 8 (67/0 vienprātīgi), Pret tikai vēlāk.
2. **KILL** (VAD likums 67/Lp14 2.las., #3340). ST visa 31 balsojuma ķēdē konsekventi pret
   dienesta IEVIEŠANU — tas IR solījuma izpilde, ne pretruna.
9. **KILL** (Starptautiskā enerģētikas programma 686/Lp14, #2307). Pret starptautiskai
   enerģētikas vienošanai saskan ar «pārskatīt starptautiskās vienošanās» solījumu.
16. **KILL** (476/Lm14, #1598). Pret sadarbības pārtraukšanai ar RU/BY = saskanīgi ar
    solījumu atjaunot ekonomisko sadarbību. Funnel ķēra leksisku sakritību («sadarbība ar
    Krieviju»), virziens ir tas pats.
22. **KILL** (Bērnu tiesību 522/Lp14, #2057). Saturs: NA iniciatīva, komisijas alternatīva
    attiecinātu «bērna» jēdzienu uz VAD dienesta personām; noraidīts 1/34/43. Nav virziena
    konflikta ar dzimstības/atbalsta solījumu — tēmas līmeņa sakritība tikai.

### AS klasters

3. **KILL** (PVN 404/Lp14 1.las., #4908). 2023-11 koalīcijas budžeta standoff whip-balsojumi;
    solījums generisks («stabilizēs nodokļu politiku»); ķēdē AS Par vairākiem priekšlikumiem.
    Interpretācijas pārbaude neiziet: saprātīgs cilvēks var turēt abas pozīcijas.
8. **KILL** (VSÅ 418/Lp14, #4725). Saturs: reģistrētu partnerību partneru sociālās
    apdrošināšanas tiesības. Nav sakritības ar ģimenes-atbalsta solījumu — tēmas līmenis.
11. **KILL** (VSÅ 401/Lp14, #4890). T14 inversija: 2.lasījumā (#5192, 88/0) AS **Par 10**.
     Tikai 1.lasījuma Pret apgriež ierakstu.
12. **KILL** (Bērnu tiesību 408/Lp14, #4882). Saturs: inspekcijas pārdēvēšana/pakļaušana;
     2.lasījumā AS Par. Administratīva reorganizācija nekonfliktē ar ģimenes solījumu.
13. **KILL** (522/Lp14, #2057). Atturas semantika: AS Atturas 7 (+Nebalsoja 5); komisijas
     alternatīvredakcijas procedūra; atturēšanās nav pozīcija.
14. **KILL** (VSÅ 29/Lp14, #5578). T14: noraida SĀKOTNĒJO variantu, jo Sociālo un darba lietu
     komisija izstrādājusi alternatīvu likumprojektu (35/Lp14) — tīri procedurāls noraidījums.
15. **KILL** (VPI 337/Lp14, #1478). Tehniski atsauču grozījumi (v. «Par pašvaldībām» →
     Pašvaldību likums); noraidīti 1/81 gandrīz vienbalsīgi. Nav pozīciju nesējs.
26. **KILL** (MUN 397/Lp14 1.las., #4884). Grozījumi nosaka VIENOTU 25% MUN likmi — AS Pret
     likmes pacelšanai ir saskanīgi ar UIN režīma saglabāšanas / zemas mikronodokļa likmes
     solījumu. Virziena saskaņa.

### NA + JV klasters

4. **KILL** (budžets 2025, 757/Lp14 1.las., #2467). Opozīcijas frakcijas Pret veselam
     budžetam nav pierādījums pret generisku «prognozējama nodokļu politika» solījumu;
     ķēde 213 balsojumi, NA Par saviem ~40 priekšlikumiem.
5. **KILL** (budžets 2024, 430/Lp14, #4912). Tas pats — ķēde 253 balsojumi.
6. **KILL** (budžets 2026, 1130/Lp14, #1112). Tas pats.
30. **KILL** (337/Lp14, #1478). Tas pats balsojums kā pāris 15 — tehnisks, 1/81.
17. **KILL** (493/Lp14, #1461). Saturs: aizliegts RU/BY lauksaimniecības produkcijas imports.
     JV Atturas 14 blokā — koalīcijas mēroga atturēšanās (arī ZZS) ir koalīcijas procedūras
     fakts, ne partijas pozīcija (T14). Ar ES tiešmaksājumu solījumu saturs nekonfliktē.
23. **KILL** (Prof.izgl. 943/Lp14, #696). Pašas JV deputātu grupas iniciatīva, frakcija
     atturējās blokā (20) un motīvs krita 1/32/46. Atturēšanos aizliegts citēt kā pozīciju;
     viens balsojums bez ķēdes — vārts neiziet.
27. **KILL** (104/P14, #1180). Deputātu pieprasījums par budžeta datu pieejamību; valdošās
     partijas Pret neobligātam pieprasījumam nav pretrunā ar fiskālās atbildības solījumu
     (parads <55% IKP utm.). Tēmas līmenis («budžets»).

### ZZS + LPV klasters

10. **KILL** (49/P14, #2273). Neobligāts deputātu pieprasījums par izglītības finansējumu;
     koalīcijas ZZS to noraida — standarta valdības pozīcijas aizstāvība, ne programmas
     pretruna.
18. **KILL** (68/P14, #389). Pieprasījums par valdības zāļu reformas nepilnībām; ZZS Pret =
     koalīcijas aizstāvība. Reformas turpināšanas solījums netiek apgriezts.
20. **KILL** (493/Lp14, #1461). ZZS Atturas 11+Pret 3 (nodošanā Par 14) — jaukta ķēde +
     atturas semantika; saturs (RU/BY importu aizliegums) nekonfliktē ar tiešmaksājumu
     solījumu.
24. **KILL** (62/P14, #3109). Neobligāts lēmumprojekts par kultūras mantojuma pārvaldību;
     koalīcijas Pret; nav pretrunas ar kultūras nozares solījumu.
7. **KILL** (RB 1471/Lp14 1.las., #6121). Steidzamais RB turpinājuma grozījums (koalīcijas
    atbalstīts 58/27); LPV Pret = saskanīgi ar «apturēt Rail Baltica» solījumu. Virziena
    saskaņa.
19. **KILL** (750/Lp14, #2498). T14 inversija: 1.lasījumā Pret 6, bet visos 2.lasījuma
     priekšlikumos Par un galīgajā 86/0 **Par 7**. LPV beigās atbalstīja ģimenes pabalsta
     palielinājumu — citēt tikai 1.lasījumu nozīmē apgriezt ierakstu.
29. **KILL** (493/Lp14, #1461). LPV Pret 6 RU/BY importu aizliegumam — žurnālistiski
     interesanti, BET LPV solījums runā par tiešmaksājumiem/zaļo kursu, ne tirdzniecību ar
     RU/BY. Nav virziena konflikta ar GLABĀTO solījumu (tēmas līmenis).

### PRO klasters

21. **KILL** (49/P14, #2273). Tas pats pieprasījums kā pāris 10 — procedurāls.
25. **KILL** (29/Lp14, #5578). Tas pats T14 alternatīvredakcijas gadījums kā pāris 14.
28. **KILL** (Bērnu tiesību 248/Lp14, #3941). PRO atturējās blokā visos 3 ķēdes balsojumos
     (steidzama/1.las./2.las.). Atturēšanās nav citējama kā pozīcija; kopsavilkums nespecifisks
     par saturu; ar ģimeņu atbalsta solījumu nav demonstrējama virziena pretruna.

## Evasion check (obligāts)

«Vai ir pāri, kurus interpretēju labvēlīgi?» — **Jā, divi**, abus fiksēju otram skatam:

- **#28 (PRO Atturas uz bērnu tiesību grozījumiem 248/Lp14):** skeptisks žurnālists jautātu,
  kāpēc PRO, kas sola «laulību vienlīdzību un visu ģimeņu aizsardzību», trīsreiz blokā
  atturējās pret Cilvēktiesību komisijas grozījumiem. Vārts tomēr KILL: atturas-noteikums
  aizliedz vienu atturēšanos lasīt kā politisko pozīciju, un satura kopsavilkums DB nepiedāvā
  virziena pierādījumu. Ja 248/Lp14 saturs kādreiz tiks izlasīts no titania LP un izrādīs
  tiešu saiti ar PRO ģimeņu-vienlīdzības solījumu — kandidāts pārskatīšanai.
- **#29 (LPV Pret RU/BY lauksaimniecības importa aizliegumam):** stāsts ir reāls, bet tas ir
  ārpus saglabātā solījuma teksta — partiju-pretrunu funnel var spriest tikai pret glabāto
  claim. Atsevišķs potenciāls temats (ne šī cikla objekts).

## Sekas

- `store_contradiction` izsaukumu: 0. DB nemainīta (sesija read-only).
- Piltuve šim top-30 ciklam slēgta; jauns rangs būtu jauns DA cikls (BACKLOG § Partiju
  pretrunas).
