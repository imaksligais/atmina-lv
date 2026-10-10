# HANDOFF 2026-10-08…09 — stāvoklis pēc 10-09

## Izdarīts 10-08…09 (detaļas — `wiki/CHANGELOG.md` 2026-10-08 (6)…2026-10-09 (10))
- **Saeima:** kolektīvo iesniegumu polaritāte + vārti; īpašvārdu reģistrs; «Likums» → `pieņemts` (72 likumprojekti), 33 tiesneši + 38 lēmumi, procedūra atdalīta, (e1) atteikta iekļaušana = «noraidīts».
- **Profili:** citāts Pozīciju cilnē, «Atturas» piezīme, Pozīciju tabula telefonā = kartītes, Pārskatā «Balso kopā ar savu frakciju» (122 lapas), Saeimā cilnē teikums, kāpēc balsojumi beidzas (25 profili, `data/bio/saeima_mandats.yaml`).
- **A11y:** filtru pogām `aria-pressed`, matricas josla bez `!important`, neesoša `?tema=` saite → noklusējums (CHANGELOG 2026-10-09 (10)).
- **Citas lapas:** Personas — 4 metriku kolonnas; `analizes.html` telefonā; dienas pārskata pretrunu šūna = izvilkums + saite; mobilās CSS sīkās lietas.
- Visi deployoti, `verify_host` 9/9 katrā; pēdējais `1bda5668`.

## Nākamais
1. **15. Saeimas pārslēgšana (~03.11.):** `docs/plans/2026-09-27-15-saeima-sasaukums.md` § Pārslēgšanas diena — tur arī frakcijas bloks (8. p.) un mandāta teikumi (9. p.); Personas rail grupēšana pēc koalīcijas (atlikta līdz tam).
- **Neiesākt:** savs fonts/identitāte (operators 10-08: «vēlāk»); laika ass, dalīšanās kartiņas, tēmu direktorijas 2. kārta (verdikti 45/46).

## Gaida operatoru
- **Par/Pret/Atturas josla Pārskatā** — izskaidrota, ieteikums nedarīt (atspoguļo koalīciju/opozīciju, ne cilvēku); skaidrs lēmums nav dots.
- `aria-label="Galvenā izvēlne"` — prasa frozen-regex maiņas svētību; `[NESKAIDRS]` pretrunas datuma rinda (`backlog/vietne-ui.md`) — nosaukt defektu vai izsvītrot.
- Autora uzvārda grep publiskajā klonā (operatora solis).
- **Morozs/Plaude** — seedēt tikai pēc CVK oficiālā ievēlēto saraksta.

## Gaida operatoru (pārcelts 2026-10-09)

_Atvērtie punkti no 7 handoffiem, kas 2026-10-09 pārvietoti uz `docs/arhivs/handoffs/` un nav pierakstīti nekur citur. Pārbaudīts pret git vēsturi, CHANGELOG, backlogu un DB (tikai lasot). Iekavās — avota handoffs; «pārcelts jau 10-05» nozīmē, ka punkts joprojām ir atvērts kopš iepriekšējās arhivēšanas. Kur pārējie punkti — `docs/arhivs/handoffs/README.md` § 2026-10-09._

- **Junction lomas (DB 10-09 nemainītas):** doc 120049 (`subject` Rinkēvičs, runā Kulbergs), 120019 (Stepaņenko tikai pieminēta), 120172 (Stendzenieks bez vārda tekstā), 120749 («Krustpunktā»), 120708/120684/120676 (Abu Meri nerunā), 121897 (Rinkēvičs `mentioned`); Ričards Šlesers (pid 56) `subject` 124194 un 124250, kur runā Ainārs; Abu Meri `mentioned` 125775/125808/125829, kaut raksts ir par viņu; Pujāts (pid 246) `mentioned` 4 dokos, kur runā pats; Rinkēvičs 126730. Klase — `backlog/matcher.md` § «`subject`» lomai (10-05 seed, pārcelts jau 10-05; 10-05 rutīna; 10-06 rutīna).
- **Vārdabrālis:** doc 123460 piesaistīts pid 25 kā `subject`, bet tajā ir cits Viktors Valainis (10-05 seed, pārcelts jau 10-05).
- **Iespējams dublikāts:** #725139 ↔ #717891 (Augulis, PVN degvielai) (10-05 seed, pārcelts jau 10-05).
- **Pozīcijas pēc izvēles:** Kulberga 2022. gada citāts doc 118396; Valaiņa «ZZS vērsies Satversmes tiesā» (doc 120027); Rinkēviča JEF detaļa #725099; Zeltīta #725159 avots ir Velpa RT; Šlesera LSM citāts doc 123761 (#729876 to nesatur); Kulbergs doc 85876 («Iekārtas iepirkām…», pozīcijas nav) (10-05 seed, pārcelts jau 10-05; 10-04; 10-05 seed).
- **Redakcionālais noteikums nav ratificēts:** bijušā PRO deputāta uzvārds izņemts no mūsu tekstiem (apsūdzība nav celta), bet noteikums nav ierakstīts nevienā promptā — ratificēt vai atsaukt (10-05 seed, pārcelts jau 10-05).
- **Saeima:** 10-01 sēdes paritāte nav auditēta (57 balsojumi; pēc manifesta pārģenerēšanas `audit_saeima_agenda_parity.py --dates 2026-10-01`); Siliņa / 1380/Lp14 — vai JV atmeta savu 3 % priekšlikumu (#655815); sv#1739 (217/Lp14 Nr. 16) — vai tas ir DUS alkohola aizliegums, kas skar Bērziņa #532031; `Lm` dokumentu iznākums «Paziņojums» arī pieņemtam balsojumam (8305, 1108/Lm14, 57:17:1; vēl 18 `Lm` rindas ar «Paziņojums» nav lasītas) (10-05 seed, pārcelts jau 10-05).
- **Atgūšana:** 80 politiķi, kurus 09-23 pazemināja uz `mentioned`, un Latkovskis doc 115440 (`extracted_at` NULL) (10-05 seed, pārcelts jau 10-05).
- **Datums:** doc 114881 (leta.lv) bez `published_at` (10-05 seed, pārcelts jau 10-05).
- **Koda sīkumi:** `print_routine()` bez argumenta ņem `today_lv()`, ne rutīnas dienu; `src/briefs.py` nedēļas loga kortežs divreiz un kopīgs pretrunu SQL; promptu vārts neķer `strftime`/`substr` datuma salīdzinājumu; audita 3. vārti pārgadu gadījumā; balsojumu kartītes čips nedalītai frakcijai; `src/quality.py` garumzīmju vārti (#11270); Ņenaševas RT netiek glabāti, bet kursors virzās (10-05 seed, pārcelts jau 10-05).
- **Nedēļas pārskats 28.09.–04.10.** nav uzrakstīts (pēdējais `weekly_brief` ir #653); 9 Rinkēviča pozīcijas #729808–#729816 nav nevienā pārskatā — rakstīt vai izlaist (10-05 seed, pārcelts jau 10-05).
- **Smiltēns #729887** — iespējams `minor_shift` (panelis «Pretrunu kandidāti»), pretruna nav glabāta (10-04; 10-05 seed).
- **Čulkova** par Rosļikova neatgriešanos pret #704157 — iespējams pāris, pozīcija nav izvilkta (10-05 rutīna).
- **T6 partijas:** Urbanovičs (pid 232) — vai izstājas no «Saskaņas» vai tikai no vadības (`party` nemainīts); Štāls (pid 173) — JKP apsver likvidāciju vai zīmola maiņu; «Stabilitātei!» (`parties.id`=9) ir `opposition`, kaut frakcijas vairs nav — pārbaudīt (10-04; 10-05 rutīna; 10-06 rutīna).
- **«Šleseri»** (Danas akuzatīvs = ģimenes daudzskaitlis, 3 doki) — formas lēmums nav pieņemts (10-05 seed).
- **15. Saeimas 30 jaunie deputāti** bez neviena `subject` doka — vajag vēsturisko meklēšanu (`/historic-backfill`, operatora laiks) (10-05 seed).
- **Dimants (pid 260)** — vājākā VAD sasaiste, Jev pārbaude pēc izvēles (10-05 seed).
- **Skeleta sīkumi** `src/briefs.py`: SV-AJ/SV/AJ apzīmējums, tēmu secība, pmo.ee/tvnet.lv (10-05 rutīna).
- **Vai skeletam jāfiltrē `review_status`?** Pagaidām NEEDS_REVIEW pozīcijas no pārskata izņem ar roku (10-06 rutīna).
- **52 dzēsto pozīciju tvīti** (10-06 triāža) joprojām ir cilnē «X ieraksti» un `x.html` — dzēst dokumentus vai atstāt (10-06 rutīna).
- **#689653 Lapsa** — joprojām `needs_review`, jāpārbauda video (10-06 rutīna).
- **CSS:** `--xv1-*` mainīgie nav definēti `.pnv1-section` (`assets/style.css`) (10-05 seed).
- **X pavedieni 10-06** (`docs/tweet_bank/2026-10-06-dienas-parskats-social.md`, `docs/tweet_bank/2026-10-06-saeimas-aktivitate-social.md`) — failos «NEPOSTĒTS»; publicēt vai atzīmēt kā novecojušus (10-06 Saeimas aktivitāte).
- **T21 CLAUDE.md** (kolektīvo iesniegumu polaritāte) — tikai ar operatora «jā»; nav ierakstīts (10-07 nākamā sesija).
- **Kļaviņa foto CF kešs** — ja live vēl rāda Jodu, Purge Custom URL panelī (10-07 nākamā sesija).
