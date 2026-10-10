# Handoff 2026-10-03 — vēlēšanu dienas rutīna (PUBLICĒTA)

> **Statuss:** pārskats #674 publicēts pēc operatora atļaujas («A un publicēt»): attēls #358 apstiprināts, #359 noraidīts; `approve_publish 2026-10-03`; deploy `ffca6bbe`, `verify_host` 9/9, attēlu URL 4/4 = 200, `blog/2026-10-03.html` 200. Tajā pašā deploy no `blog/2026-10-02.html` izņemta #729774 rinda (live: 0 trāpījumu).

## Kas izdarīts

- **#729774 (Krištopans, RT) dzēsts** + rinda izņemta no #672 (`scripts/_fix_withdraw_kristopans_rt_2026_10_03.py`, rollback komitēts pirms apply).
- **Divas ielādes** (vakara + ~23:00; pirmo nakts mēģinājumu apturēja atmiņas trūkums, atkārtots pēc operatora «vari ielādēt»). Plāni 133/133 + 41/41 pāri; atgūšana 12 + 13 web pāri. **59 pozīcijas** par dienu (+10 no Saeimas 24.09 stenogrammām, `stated_at=2026-09-24`, operatora lēmums «pēc vēlēšanām»). Pretrunas 0 (divi `contradiction_hunt` ieraksti ar `rejected_candidates`).
- **Spriedzes** #426 (Liepnieks → Kulbergs), #427 (Daugavietis → Stepaņenko); 6 priekšlikumi noraidīti. **Tendence** #673 (koalīcijas robežas vēlēšanu naktī).
- **Operatora tēma — vēlēšanu sistēma / CVK skaitļi:** pārskata sadaļa «Vēlēšanu norise un CVK dati» (19 avoti; aktivitātes skaitļu atšķirības starp medijiem, CVK precizēšanas skaidrojums, ~3 h skaitīšanas aizkave ETVR pārbaudes dēļ, CVK sēdes lēmums). Vienīgā sekotā politiķa pozīcija par CVK: Liepnieks #729827. Ielādēti `ingest_url` 123718 (LSM), 123719 (Diena).
- **Labojumi:** #729831 exit poll formulējums (`data/{fix,rollback}_kucinskis_exitpoll_2026-10-03.sql`); QR 15 valodas/faktu labojumi + #729834, #729849, spriedze #426 (`data/rollback_qr_2026-10-03.sql`, komitēts PĒC apply — QR aģentam git aizliegts). Re-embed izdarīts.

## Atvērts nākamajai sesijai

- **Oficiālie CVK rezultāti** — pārskats balstās uz vēlētāju aptauju; 10-04 rutīnā rezultāti + reakcijas. Sociālais pavediens par vēlēšanu rezultātiem (handoff 10-02 lēmums) — tikai pēc oficiālajiem datiem.
- **Vārdabrālis (T1/T13):** «Latvija pirmajā vietā» sarakstā ir CITS Viktors Valainis (doc 123460 piesaistīts pid 25). Matcher pilnu vārdu neatšķir — operatora lēmums par disambiguāciju; pārbaudīt 10-03 Valaiņa saites.
- **Vēstneša stenogrammas 122684/122685:** `reviewed_at` joprojām NULL. Neatzīmēju, jo tas pārklātu arī subjekta (122684: pid 67 Briškens) slotu, kas nav izvilkts. Vēstnesis nav ekstrakcijas rindā — ietekme zema; lēmums operatoram.
- **9 pozīcijas par Rinkēviča pārvēlēšanu** (#729808–#729816, `stated_at=2026-10-02`) nav nevienā pārskatā (10-02 jau publicēts). Var izmantot nedēļas pārskatā.
- **TypeSafe:** 10-03 Kozlovskis kļūdains veto (ģenitīvs) → `backlog/dati-db.md`; `enforce` joprojām NĒ.
- **KNAB/klusuma periods:** vairāki politiķi vēlēšanu dienā tvītoja aicinājumus balsot (piem., Velps); pārskatā tikai KNAB skaitļi, bez vārdiem — apzināti.
