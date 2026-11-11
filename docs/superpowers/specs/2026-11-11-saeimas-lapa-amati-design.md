# Saeimas lapa ar amatiem — dizains (2026-11-11)

**Pamats:** `docs/HANDOFF-2026-11-11.md` § Nākamais darbs (operators 11.11.: Saeimas lapa ar amatiem, ne tikai 100 sēdvietām). Turpina [`2026-10-08-saeimas-pusloks-design.md`](2026-10-08-saeimas-pusloks-design.md). Lēmumi pieņemti kopā ar advisor; publicēšana un partiju krāsu DB maiņa — tikai ar operatora «jā».

## Mērķis

Lasītājs `saeima.html` uzreiz redz, KAS vada Saeimu (Prezidijs) un katru frakciju, un pie katra deputāta — viņa amatu. Veiksme: telefonā Prezidija locekli vai frakcijas vadītāju atrod bez ritināšanas cauri 100 kartītēm, un katram amatam ir avots un datums.

## Fakti (mērīti 2026-11-11)

- saeima.lv (statisks HTML, saglabāts ar SHA-256: `docs/audits/2026-11-11-saeima-amati/`):
  - **Prezidijs** (5, visi no 03.11.2026.): Edvards Smiltēns — Saeimas priekšsēdētājs (AS); Ināra Mūrniece — priekšsēdētāja biedre (NA); Raimonds Vējonis — priekšsēdētāja biedrs (AS); Ramona Petraviča — Saeimas sekretāre (LPV); Antoņina Ņenaševa — Saeimas sekretāres biedre (PRO).
  - **Frakcijas** (6, 100 deputāti, nepiederošo 0, visi no 03.11.2026.): AS 41 — Kučinskis, vietnieki Bergmanis, Melnalksnis; LPV 17 — Šlesers, v. Zivtiņš; SV/AJ 15 — Stepaņenko, v. Brēmanis; NA 10 — Butāns, v. Mitrevics; PRO 10 — Šuvajevs, v. Lāce; JV 7 — Lībiņa-Egnere, v. Bērziņa.
  - Frakciju sastāvs vārds pret vārdu = CVK saraksts (`cvk_sv2026_ievēlētie.yaml`): 6/6 frakcijas, 0 atšķirību.
  - **Komisijas:** 16 nosaukumi, nevienai nav ne vadības, ne sastāva (vēl nav ievēlētas).
- `tracked_politicians.role` šos amatus jau nes (`data/fix_roles_prezidijs_frakcijas_2026-11-03.sql`), bet tas ir brīvs teksts un denormalizēts (T6); Ņenaševai tur «sekretāra biedre», saeima.lv — «sekretāres biedre».
- § Ne-darīt (37): saeima.lv amatu parseri NEBŪVĒT, `saeima_deputy_positions` rakstīt tikai no titania DepWeb (joprojām 401).

## Lēmumi

| Jautājums | Lēmums | Kāpēc |
|---|---|---|
| Datu avots | Viens kurēts `data/saeima15_amati.yaml`: Prezidijs, frakciju vadība (priekšsēdētājs + vietnieki), 16 komisiju nosaukumi ar statusu «vēl nav ievēlētas», katram blokam `source_url` + `checked` datums. Rakstīts ar roku no saglabātajām lapām. | Ne-darīt 37: nav parsera repo, nav DB rakstu. Tas pats modelis kā CVK YAML. |
| `role` kolonna | Lapa to NElasa. | Brīvs teksts, var novecot (T6); YAML ir viens avots ar datumu. |
| Validācija | Ielādētājs KRĪT, ja: vārds nav ievēlēto sarakstā; kādam sarakstam ar vietām nav frakcijas ieraksta; frakcijas vadītājs nav no tās frakcijas saraksta; Prezidijā ≠ 5; amats nav no atļautā saraksta; viens vārds divreiz vienā lomā. | «Silent success» — klusa tukša sadaļa ir sliktāka par kritienu. |
| Prezidijs | Jauns bloks **zem puslokā, virs «Deputāti pa sarakstiem»**: piecas kompaktas kartītes (foto, vārds, amats, frakcijas krāsas punkts), katra ved uz `#dep-<slug>` (esošais `slv1.js` `hashchange` jau atver grupu un rindu — jauns JS nav vajadzīgs). Izkārtojums: viens `grid` ar `repeat(auto-fit, minmax(…, 1fr))` — telefonā 2 kolonnas, platā ekrānā 5 rindā; bez horizontālas ritināšanas. Foto ir visiem 5 (`assets/photos`). | Prezidijs ir vienīgais jaunais saturs, kas pelna savu bloku. |
| Frakciju vadība | NAV jauns bloks: saraksta grupas ķermeņa pirmajā rindā (ne `<summary>` — saite tur pārslēgtu grupu), («Apvienotais saraksts · 41 vieta») rinda «Frakcijas vadība: Kučinskis · vietnieki Bergmanis, Melnalksnis» ar enkuriem. | Telefonā lapa jau ~8 000 px; otrs bloks dublētu sarakstu. |
| Amata zīme | Deputāta rindā un kartītē īss čips; teksts katram cilvēkam glabāts YAML **verbatim** no saeima.lv («Saeimas sekretāres biedre», «Priekšsēdētājas vietnieks» — dzimte atkarīga no abiem cilvēkiem, tāpēc NEatvasina). Frakcijas amatam čipā priekšā frakcijas īsais nosaukums («AS frakcijas priekšsēdētājs»). Amats arī sēdvietas `aria-label`. | Amats redzams tur, kur cilvēks jau meklē. |
| Kārtība sarakstā | Deputātu secību grupā NEMAINA. | Sēdvietu koordinātas piešķir pēc `members` secības — pārkārtošana pārbīdītu pusloku. |
| Puslokā | Bez 5. lēcas (pie 390 px četras pogas jau aizņem visu platumu). Amatpersonu sēdvietām (5 + 6 = 11) — plāns kontūras gredzens visās lēcās; gredzena skaidrojums ir VIENA rinda ārpus četrām lēcu leģendām (redzama visās lēcās): «Gredzens — Prezidijs vai frakcijas priekšsēdētājs». | Redzams bez jaunas vadīklas; krāsa joprojām nozīmē lēcu. |
| Komisijas | Viena datēta statusa rinda Prezidija blokā vai tā apakšā: «16 komisiju sastāvs un vadība vēl nav ievēlēti · saeima.lv, 11.11.» ar saiti. Pilnu bloku būvē, kad ir dati. | Nebūvē UI tukšiem datiem. |
| Stils | `good-css`: loģiskās īpašības, `oklch`/esošie tokeni, `:focus-visible`, hover tikai `(hover:hover) and (pointer:fine)`, bez jauniem breakpoint-kāpņu; esošās `slv-*` klases paplašina, ne dublē. Gaišā un tumšā tēma. | Operatora prasība (atmiņa: UI darbā vienmēr good-css). |
| JS | Nav jauna JS; ja kartītei vajag amatu — tā ir iepriekš renderētajā `<div>`. | CSP; lapa strādā bez JS. |

## Arhitektūra

- `data/saeima15_amati.yaml` — jauns. Forma (ilustratīvi):
  ```yaml
  convocation: 15
  checked: 2026-11-11
  presidium:
    source_url: https://www.saeima.lv/lv/sasaukumi/15-saeima/prezidijs/
    members:
      - {name: Edvards Smiltēns, office: Saeimas priekšsēdētājs, since: 2026-11-03}
  factions:
    source_url: https://www.saeima.lv/lv/sasaukumi/15-saeima/frakcijas/
    items:
      - list_nr: 7
        since: 2026-11-03
        leaders:
          - {name: Māris Kučinskis, title: Priekšsēdētājs}
          - {name: Raimonds Bergmanis, title: Priekšsēdētāja vietnieks}
  committees:
    source_url: https://www.saeima.lv/lv/sasaukumi/15-saeima/komisijas/
    status: not_elected
    names: [...]
  ```
- `src/render/saeima.py` — `AMATI_PATH` konstante (testi pārsien uz fixture kā `ELECTED_PATH`/`RESULTS_PATH`, arī `tests/conftest.py`), `_load_offices()` ar validāciju, `member["office"]`, `lst["leadership"]`, `ctx["presidium"]`, `ctx["committees"]`. Ielādētājs — `src/render/_common/cvk.py` blakus vai saeima.py iekšā (viens lietotājs → saeima.py).
- `templates/saeima.html.j2` — Prezidija bloks, grupas galvenes rinda, čips rindā/kartītē, gredzena klase sēdvietai.
- CSS — esošajā Saeimas lapas stila failā (kur dzīvo `slv-*`).
- Render izdrukā: `sēdvietas=100 izsekoti=N bez_profila=M prezidijs=5 frakciju_priekšsēdētāji=6 vietnieki=7` (gredzens = 11).

## Testi (CLAUDE.md 7. princips)

- **Ieviests (advisor 11.11.):** amatpersonām rindā amats novada vietā, vienā rindā (`text-overflow: ellipsis`; frakcijas amats bez prefiksa, pilns teksts kartītē un `aria-label`) — rindas vienā augstumā; aizvērtas grupas `<summary>` nes priekšsēdētāju kā tekstu («Priekšsēdētājs Ainārs Šlesers»), atvērtā grupā to aizstāj pilnā vadības rinda.
- **Ieviests:** Prezidijs telefonā (konteiners < 36rem) — kompaktas rindas vienā kolonnā, platā — 5 kartītes rindā.
- **Pārraksta esošo** `test_saeima_page_end_to_end` (nav jauna testa blakus): fixture YAML ar amatiem → lapā (a) Prezidija bloks ar 5 saitēm uz `#dep-*`, (b) frakcijas vadītājs grupas galvenē, (c) amata čips pie viena deputāta, (d) gredzena klase tieši amatpersonu sēdvietām. Pirms ieviešanas parāda, ka tests krīt.
- `test_saeima_incomplete_composition_fails` paplašina ar vienu gadījumu: amatu YAML vārds, kura nav ievēlēto sarakstā → `ValueError`.
- `test_render_chars` bāzlīnija — REGEN tikai šai lapai.
- Pilns `bash scripts/check.sh` vienreiz beigās.

## Vizuālā pārbaude

Renderē uz atsevišķu `--output` mapi; ekrānuzņēmumi 390 px un 1280 px, gaišā un tumšā tēma, pa vienam pārlūkam; salīdzināšanas HTML «Pirms»/«Pēc» (pirms — `.scratch/saeima-amati/pirms-*.png`), atvērts pārlūkā.

## 2. fāze — partiju krāsas (atsevišķi)

Pēc 1. fāzes ekrānuzņēmumiem: katras Saeimas partijas krāsa pret oficiālo logo (avots + datums katrai), kontrasts gaišajā un tumšajā tēmā, problēmu pāri SV-AJ #741D77 ↔ PRO #a855f7 un NA #22c55e ↔ ZZS #84cc16. Priekšlikums + pirms/pēc paraugs operatoram; DB raksts `parties.color` tikai pēc «jā», ar pāra rollback, tad `clear_party_color_cache()` un pilns renders.

## Ārpus šī darba

Komisiju sastāvs (kad ievēlēts — tas pats YAML), ministri ārpus Saeimas, `saeima_deputy_positions` (titania). Deploy — tikai ar operatora atļauju.

**Publicēšanas ceļš:** `saeima.html` nav apstiprinājuma vārtu, tāpēc darbs notiek zarā `saeima-amati` (galvenajā checkout, bez worktree), renderē tikai uz atsevišķu `--output`; merge masterā — pēc operatora «jā» uz ekrānuzņēmumiem.

## Risks handoffam

Kad apstiprinās jauno valdību, ministri var nolikt mandātus un ienāks aizstājēji — sēžošais sastāvs atšķirsies no CVK saraksta, un ielādētājs (pamatoti) apturēs renderu, līdz abi faili atjaunoti.
