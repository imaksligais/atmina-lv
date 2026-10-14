# airBaltic sintēzes 2. daļa — pierādījumu bāze

_Darba dokuments, 2026-09-06. Read-only lasījums no `data/atmina.db` + tīmekļa pirmavoti. Nekas nav publicēts._
_Korpuss: `claims` `topic='airBaltic' AND claim_type='position' AND stated_at>='2026-04-22'` = **139 rindas** (mērīts 2026-09-06); `saeima_votes` `document_nr IN ('953/Lm14','1495/Lp14')` = **8 balsojumi**; nevienā citā balsojumā kopš 04-01 motīvā nav Air Baltic._
_Laika zonas: `claims.stated_at` un `context_notes.created_at` = LV; `political_tensions.created_at` = UTC._
_**NEPĀRBAUDĪTS** = publiskajā ierakstā neatradu apstiprinājumu; tas nav noliegums._

---

## 1. Pirmās daļas audits

| # | Apgalvojums 1. daļā | Statuss | Pierādījums |
|---|---|---|---|
| 1 | «Saeimas balsojums 16.04. — iziet ar 23 PRET» | **piepildījās** | `saeima_votes` id **99**, 2026-04-16 15:53:40, 49/23/1/15, `Pieņemts`. PRET summa 1+4+7+11=23. |
| 2 | «ZZS frakcija sašķēlās **pa pusēm**: Rokpelnis PAR, Augulis PRET» | **nepiepildījās (faktu kļūda)** | Balsojumā 99 ZZS frakcijā **14 deputāti: 13 PAR, 1 PRET** (Augulis). Rokpelnis bija viens no 13. Sk. § 1.1. |
| 3 | «Augulis un Rokpelnis — vienīgie ZZS deputāti, kuru balsojumi tiek fiksēti» | **nepiepildījās** | Visi 14 ZZS frakcijas deputāti ir `saeima_individual_votes` rindās; +Ceļapīters (ZZS partija, bez frakcijas etiķetes). |
| 4 | «NA + AS + Stabilitātei vienoti **nebalsoja**» | **nepiepildījās (daļēji)** | NA 9 Nebalsoja ✔; AS **4 Pret + 4 Nebalsoja + 1 Atturas** ✘; ST 9 PRET + 2 Nebalsoja ✘. Vienota bija tikai NA. |
| 5 | 1. daļas frakciju tabula (JV 6 vārdi, PRO 4 vārdi u.c.) | **nepiepildījās** | JV 25 PAR, PRO 8 PAR. Tabula uzskaitīja apakškopu, nevis frakciju. LPV 7 PRET tabulā nav vispār. |
| 6 | Valaiņa pretruna #24 (07.04. ↔ 14.04.) | **piepildījās** | `contradictions` id 24, `minor_shift`, `confirmed=1`, `reviewed=1`, claims 6628↔7414, `detected_at` 2026-04-18. Nepārklasificēt. |
| 7 | «Valaiņa prasība pēc Satiksmes ministrijas ir ierakstīta; nākamajā koalīcijas sarunu posmā tā būs konkrēta pozīcija» | **nepiepildījās** | Kulberga valdībā (apstiprināta **2026-05-28**) satiksmes ministrs ir **Rihards Kozlovskis (JV)**; Valainis saglabāja ekonomikas ministra amatu ([tvnet](https://www.tvnet.lv/8480022/latvija-jauna-valdiba-saeima-izsaka-uzticibu-kulberga-valdibai)). |
| 8 | Kulbergs 21.04.: «tālāk par Jāņiem neizvilks» | **nepiepildījās** | Sk. § 1.2. Uzņēmums darbojas; 29.05. sākta valsts aizdevuma atmaksa; līdz 24.07. atmaksāti 12,9 M. |
| 9 | «Nākamā cikla balsojums notiks pirms 31.08.» | **piepildījās** | 2026-08-20 ārkārtas sēdē seši balsojumi par 1495/Lp14; likums pieņemts (id 8071, 54/21/1/7). |
| 10 | «Švinka uzņēmās politisko atbildību… ja augustā atmaksa neizdodas, to vērtēs pret šo apgalvojumu» | **nav nosakāms kā solījuma pārbaude** | Atmaksa 31.08. **neizdevās** — 18 M pamatsummas atlikums atlikts līdz 30.12.2026. (MK 25.08.). Bet Švinka amatā nebija kopš 28.05.; publiskā ierakstā nav neviena izteikuma, kur viņš šo saistītu ar 16.04. apgalvojumu. |

Papildus: 1. daļas «Siliņas Liepājas jautājums» paliek **nav nosakāms** — korpusā kopš 04-22 nav neviena claim par Liepājas spiedienu; nav jaunu publisku dokumentu.

### 1.1. ZZS 16. aprīlī — abi balsojumi blakus (T6 / T14)

Balsojums **6660** (14:14:13, par iekļaušanu darba kārtībā, 54/13/1/20) un **99** (15:53:40, pēc būtības, 49/23/1/15). Abi `document_nr='953/Lm14'`, `topic='airBaltic'`.

| Frakcija | 6660 (14:14) | 99 (15:53) |
|---|---|---|
| JV | 25 Par | 25 Par |
| PRO | 8 Par | 8 Par |
| ZZS | 12 Par, 2 Nebalsoja | **13 Par, 1 Pret** |
| AS | 11 Nebalsoja | 4 Pret, 4 Nebalsoja, 1 Atturas |
| NA | 6 Par, 3 Nebalsoja | 9 Nebalsoja |
| LPV | 6 Pret | 7 Pret |
| bez frakcijas etiķetes | 3 Par, 7 Pret, 1 Atturas, 4 Nebalsoja | 3 Par, 11 Pret, 2 Nebalsoja |

ZZS frakcijas deputāti balsojumā **99** poimenīgi: **PAR** — A. Bērziņš, Brakovska, Brigmanis, Mieriņa, Zemmers, Daudze, **Rokpelnis**, Jakovins, Dinevičs, Gintere, L. Kozlovska, L. Kļaviņa, Maslovskis (13). **PRET** — **Augulis** (1).
Balsojumā **6660** Augulis un L. Kozlovska nebalsoja, pārējie 12 PAR.

**T6 brīdinājums (frakcijas etiķete).** Kopš 2026-04-16 Titania Stabilitātei rindām frakcijas šūnu atstāj tukšu — `faction IS NULL`. Balsojumā 99 no 16 bezetiķetes rindām 10 ir Stabilitātei! deputāti (Ivanovs, Klementjevs, Kovaļenko, Marčenko-Jodko, Sruoģis, Čulkova, Drelinga, J. Kļaviņa, I. Judins, Saļimovs), 2 — LPV ārpus frakcijas (Kiršteins, Pleškāne), pārējie bezpartejiskie/ārpusfrakciju (Rajevs, Vergina, Burovs, Šmits, Ceļapīters). **Jebkurš teikums «frakcija X balsoja…» jābalsta `faction` sadalījumā TAJĀ `vote_id`, un ST gadījumā etiķete tur nav.**

### 1.2. «Tālāk par Jāņiem neizvilks» (21.04.) — kas notika līdz jūnija beigām

| Datums | Fakts | Avots |
|---|---|---|
| 2026-05-29 | airBaltic veic **pirmo 6,4 M eiro** valsts aizdevuma atmaksu; aizdevums izsniegts pa daļām | [sam.gov.lv](https://www.sam.gov.lv/lv/jaunums/airbaltic-sak-atmaksat-valsts-aizdevumu) |
| 2026-06-01/02 | Satiksmes ministrs Kozlovskis: vasarā valsts finansējums «varētu būt nepieciešams» | claims **#521099**, **#521141** |
| 2026-06-15 | Kulbergs (jau premjers): turpmākiem ieguldījumiem jānāk no privātā sektora; plāni tiks izvērtēti līdz jūlija beigām | claim **#532067** |
| ~2026-07-24 | Atmaksāti **12,9 M** (pamatsumma + līgumiskie procenti); gala termiņš joprojām 31.08.2026. | [nra.lv 526259](https://nra.lv/ekonomika/latvija/526259-airbaltic-sak-valsts-aizdevuma-atmaksu.htm) |

Secinājums: **prognoze nepiepildījās** — uzņēmums Jāņus pārdzīvoja un pat sāka atmaksu. Kulberga otrā daļa (380 M obligāciju slogs paliek neatrisināts; 30 M nepietiek) **piepildījās** — sk. § 2.

---

## 2. Hronoloģija 2026-04-22 – 2026-09-06

Stadijas: *piedāvāts / pilnvarots / noslēgts / izmaksāts*.

| Datums | Notikums | Stadija | Pirmavots | DB |
|---|---|---|---|---|
| 2026-04-16 | Saeima piekrīt 30 M īstermiņa aizdevumam, atmaksa līdz 31.08., bez nodrošinājuma | pilnvarots | [titania, vote 99](https://titania.saeima.lv/LIVS14/SaeimaLIVS2_DK.nsf/Voting?ReadForm&parentID=4e7fc213-d6f8-4532-8e4e-b5667fa18a97) | votes 6660, 99 |
| 2026-04-22 | Švinka: likme «divciparu», atmaksa pa daļām no maija beigām/jūnija | — | delfi.lv | claim #11313 |
| 2026-05-28 | **Saeima apstiprina Kulberga valdību** (66:25). Koalīcija AS+NA+JV+ZZS. Satiksmes ministrs — Kozlovskis (JV), ekonomikas — Valainis (ZZS) | — | [tvnet](https://www.tvnet.lv/8480022/latvija-jauna-valdiba-saeima-izsaka-uzticibu-kulberga-valdibai) | — |
| 2026-05-29 | Pirmā atmaksa 6,4 M; aizdevums izsniegts **pa daļām** | izmaksāts (daļēji) | [sam.gov.lv](https://www.sam.gov.lv/lv/jaunums/airbaltic-sak-atmaksat-valsts-aizdevumu) | — |
| 2026-07-20 | Kulbergs: sarunas ar **trim** investoriem; valsts daļa jāminimizē. Kozlovskis: 31.08. termiņš **nav grozāms** | piedāvāts | lsm.lv a655585; diena.lv | #548468, **#548462** |
| 2026-07-24 | Kulbergs vēršas Ģenerālprokuratūrā par agrāko lēmumu likumību | — | lsm.lv a656250 | #553975; tension 163; note #366 |
| ~2026-07-24 | Atmaksāti 12,9 M no 30 M | izmaksāts | [nra.lv 526259](https://nra.lv/ekonomika/latvija/526259-airbaltic-sak-valsts-aizdevuma-atmaksu.htm) | — |
| 2026-07-28 | Jaunais biznesa plāns: Rīga kā bāze, valsts **25 % + 1 akcija**; MK vēl nelemj | piedāvāts | lsm.lv a656672 | **#555721**, #555751, #555752 |
| 2026-07-30 | MK pilnvaro Valsts kasi pārstāvēt Latviju obligacionāru sapulcē; MK atbalsta biznesa plāna īstenošanu | pilnvarots | lsm.lv a656929; delfi | #555840–#555842 |
| 2026-08-03 | Obligacionāru sapulce atlikta kvoruma trūkuma dēļ | — | lsm.lv a657318 | #615947 |
| 2026-08-11 | Publisks flotes pagrieziens: no ~54 uz ~36 A220 līdz 2026. g. beigām; jauns finansējums «simtiem miljonu» | piedāvāts | lsm.lv a658405, a659559 | — |
| 2026-08-14 | **MK ārkārtas sēde**: lūgs Saeimai deleģējumu valsts dalībai pagaidu finansējumā **līdz 30 M** («no nulles līdz 30»); plāno pagarināt aizdevuma atmaksu līdz 31.12. | piedāvāts | lsm.lv a658885; leta; [sam.gov.lv](https://www.sam.gov.lv/lv/jaunums/valdiba-atbalsta-pasakumus-airbaltic-finansu-stabilitates-nodrosinasanai) | **#689615–#689619**, #689621, #689627; **note #460** |
| 2026-08-17 | **Obligacionāru sapulce apstiprina procentu maksājumu kapitalizāciju** (14.08. un 14.11. maksājumi pieskaitāmi pamatsummai) | noslēgts | [sam.gov.lv](https://www.sam.gov.lv/lv/jaunums/airbaltic-obligaciju-turetaji-apstiprina-ierosinatos-grozijumus-obligaciju-noteikumos) | **note #468**; #689745, #689751–#689754 |
| 2026-08-19 | Saeimas Budžeta komisija konceptuāli atbalsta; ZZS iebilst pret 30 M sadaļu | — | diena.lv; pmo.ee/8530531 | #690468, #690470, #690473, #690480, #690483, #703966, #703967, #703970 |
| **2026-08-20** | **Saeima ārkārtas sēdē pieņem «Air Baltic Corporation AS» finanšu stabilizācijas pasākumu likumu (1495/Lp14)** — seši balsojumi, sk. § 2.1 | pilnvarots | titania (6 URL) | votes 7957, 7902, 7944, 8069, 8070, 8071; **note #474** |
| 2026-08-25 | MK atbalsta atlikušās **18 M** pamatsummas + procentu un soda naudas maksājuma atlikšanu **līdz 2026-12-30**; atliktajai summai 2 % gadā soda nauda | noslēgts (MK līmenī) | [sam.gov.lv](https://www.sam.gov.lv/lv/jaunums/valdiba-atbalsta-airbaltic-valsts-aizdevuma-maksajuma-termina-pagarinasanu-stiprinot-uznemuma-finansu-stabilitati); lsm.lv a660301 | — |
| **2026-09-03** | **airBaltic paziņo (Nasdaq Riga) par vienošanos ar daļu obligacionāru un trešo pušu finansētājiem par starpfinansējumu līdz 257 M ar 25 % gadā**, dzēšana 26.02.2027.; 180 M pieejami drīz pēc obligacionāru piekrišanas, vēl 77 M pēc papildu nosacījumiem | **piedāvāts** (nav noslēgts) | airBaltic preses relīze «airBaltic agrees terms for up to €257 million of interim financing» ([company.airbaltic.com newsroom](https://company.airbaltic.com/en/newsroom)); [db.lv](https://db.lv/zinas/airbaltic-vienojusies-par-starpfinansejuma-nosacijumiem-lidz-257-miljoniem-eiro-ar-25-likmi); [diena.lv](https://diena.lv/raksts/latvija/zinas-71/airbaltic-vienojusies-par-starpfinansejuma-nosacijumiem-lidz-257-miljoniem-eiro-ar-25-likmi) | #709018 (09-03) |
| 2026-09-04 | Politiskā reakcija: Valainis norobežojas (MK nav skatīts, atbildība premjeram; ZZS redz Lufthansa virzienu); Liepnieks, Krištopans, Velps kritizē 25 % | — | x.com | **#709060**, #709046, #709040, #709041, #709055; tensions 262, 263; **note #533** |
| 2026-09-05 | ZZS paziņo, ka 07.09. koalīcijas sanāksmē prasīs premjera skaidrojumu par 25 % likmi | — | [pmo.ee/8540463](https://pmo.ee/8540463) | #709071; tension 266; **note #540** |
| **2026-09-11** | Obligacionāru sapulce par starpfinansējumu (nākotnē) | — | db.lv, diena.lv | note #540 |

### 2.1. 1495/Lp14 ķēde 2026-08-20 (T14 — ķēdi citē veselu vai necitē)

| Vote id | Laiks | Solis | Par/Pret/Att/Neb | Rezultāts | **ZZS frakcija** |
|---|---|---|---|---|---|
| 7957 | 09:03:46 | nodošana komisijām | 64/7/0/10 | Nod. kom. | 11 **Par** |
| 7902 | 09:06:34 | steidzamība | 68/4/0/15 | Pieņemts | 14 **Par** |
| 7944 | 12:24:21 | 1. lasījums | 58/22/1/7 | Pieņemts | 12 **Pret**, 2 Par |
| 8069 | 17:40:07 | priekšlikums Nr. 2 | 18/50/1/14 | **Noraidīts** | 11 **Par**, 1 Atturas |
| 8070 | 17:44:37 | priekšlikums Nr. 3 | 60/4/9/12 | Pieņemts | 11 **Par**, 1 Atturas |
| 8071 | 17:46:09 | 2. las., steidzams (galīgais) | 54/21/1/7 | **Pieņemts** | 11 **Pret**, 1 Atturas |

Galīgā balsojuma (8071) frakciju sadalījums — **T6/T14 autoritāte**: AS 11 Par · JV 21 Par · NA 12 Par · PRO 7 Par · **ZZS 11 Pret + 1 Atturas** · LPV 6 Nebalsoja · bez etiķetes 3 Par, 10 Pret, 1 Nebalsoja (bezetiķetes PRET vidū Stabilitātei deputāti Ivanovs, Klementjevs, Kovaļenko, Marčenko-Jodko, Sruoģis, Čulkova, Saļimovs, I. Judins + Burovs, Ceļapīters).

- Konteksta piezīme **#474** «ZZS balsoja pret» — **apstiprinās galīgajam balsojumam (8071) un 1. lasījumam (7944)**, bet NE ķēdei kopumā: rītā ZZS balsoja PAR nodošanu komisijām un PAR steidzamību, un PAR abiem priekšlikumiem. Priekšlikums Nr. 2 (noraidīts 18/50) ir vienīgais, kur ZZS bija gandrīz vienīgā PAR — tas saskan ar Rokpeļņa iebildumu pret 30 M sadaļu (#690470).
- `saeima_votes.topic` visiem sešiem = `Budžets un finanses`, ne `airBaltic` → filtrs pēc tēmas tos nesatver; meklēt pēc `document_nr`.
- Blakus atradums: `quality-bars.md` Ierāmējuma vārtu piezīme runā par «visiem trīs 1495/Lp14 balsojumiem» — DB ir seši.

---

## 3. Finansējuma instrumentu tabula

| Instruments | Summa | Likme | Termiņš | Aizņēmējs | Devējs | Valsts daļa | Stadija | Avots |
|---|---|---|---|---|---|---|---|---|
| 2024. g. obligācijas | 380 M (nominālā emisija) | **14,50 %** | 2029 | AS «Air Baltic Corporation» | tirgus obligacionāri | valstij pieder obligācijas **50 M** (≈13 % emisijas, #689618) | izmaksāts | [sam.gov.lv 17.08.](https://www.sam.gov.lv/lv/jaunums/airbaltic-obligaciju-turetaji-apstiprina-ierosinatos-grozijumus-obligaciju-noteikumos) |
| Valsts īstermiņa aizdevums (pavasaris 2026) | **30 M**, izsniegts pa daļām, bez nodrošinājuma | «divciparu» — precīza likme **NEPĀRBAUDĪTS** | sākotnēji 31.08.2026. | airBaltic | Latvijas valsts (Valsts kase) | 100 % | izmaksāts; 12,9 M atmaksāti līdz 24.07.; **18 M atlikts līdz 30.12.2026.** ar 2 % gadā soda naudu | titania vote 99; [sam.gov.lv 25.08.](https://www.sam.gov.lv/lv/jaunums/valdiba-atbalsta-airbaltic-valsts-aizdevuma-maksajuma-termina-pagarinasanu-stiprinot-uznemuma-finansu-stabilitati) |
| Procentu kapitalizācija (14.08. + 14.11. maksājumi) | ~27 M pieskaitīti pamatsummai | — | 2029 | airBaltic | esošie obligacionāri | proporcionāli 50 M turējumam | **noslēgts 17.08.2026.** | sam.gov.lv 17.08.; note #468 |
| Valsts iespējamā dalība pagaidu finansējumā | **līdz 30 M** («no nulles līdz 30») | «uz identiskiem nosacījumiem ar privātajiem» | — | airBaltic | Latvijas valsts | — | **pilnvarots** ar 1495/Lp14 20.08.; MK lems atsevišķi | lsm.lv a658885; note #460; vote 8071 |
| Starpfinansējums — **super senior** obligācijas | **līdz 257 M** (180 M uzreiz + 77 M pēc nosacījumiem) | **25 % gadā** | **26.02.2027.** | airBaltic | **Polus Capital Management** (Londona) + **Klirmark Capital 4** (Izraēla); esošie obligacionāri, t. sk. valsts, var piedalīties proporcionāli | valsts dalība **iespējama, nav pienākums** | **piedāvāts** — vajadzīga obligacionāru un akcionāru piekrišana; sapulce **11.09.2026.** | airBaltic paziņojums Nasdaq Riga 03.09.; db.lv; diena.lv |
| Ilgtermiņa rekapitalizācija (plāns) | 225 M jauns aizņēmums + 100 M jauns pašu kapitāls; daļa 2029. g. obligāciju → kapitāldaļās, atlikums aizstāts ar ≤125 M jaunu parādu | — | — | airBaltic | — | **NEPĀRBAUDĪTS** | **piedāvāts** | db.lv 03.09.; jauns.lv 723372 |

---

## 4. Personu līnijas

Amats norādīts **notikuma brīdī** (valdības maiņa 2026-05-28), ne pēc `tracked_politicians.role`.

### Andris Kulbergs (AS)
| Datums | Amats | Ko teica/darīja | Claim / avots |
|---|---|---|---|
| 2026-06-15 | premjers | Turpmākiem ieguldījumiem jānāk no privātā sektora | #532067 |
| 2026-07-04 | premjers | Saņēmis rakstisku investīciju piedāvājumu; sarunas ar trim investoriem | #547860 |
| 2026-07-20 | premjers | Valsts daļa jāminimizē; valstij nav jānodarbojas ar aviobiznesu | #548468 |
| 2026-07-24 | premjers | Iesniegums Ģenerālprokuratūrā | #553975 |
| 2026-07-31 | premjers | 380 M obligāciju darījums bija «liela kļūda» | #555857; note #395 |
| 2026-08-13 | premjers | **Pieci** laba plāna nosacījumi | #689577 |
| 2026-08-14 | premjers | **Četri** nosacījumi (bez «valsts saglabā būtisku līdzdalību») | #689621 |
| 2026-08-16 | premjers | Maksātnespēja = «sliktākais variants», bet variants | #689710 |
| **2026-08-20** | premjers | Saeimas ārkārtas sēdē aicina atbalstīt likumu; «mandāts sarunām, ne jauna nauda» | #690497, #703858, #703970 |
| **2026-08-21** | premjers | 14,5 % darījums bija kļūda; «mūsu valdība to neatkārtos» | #703860, #703865, #703866; note #479; tension 225 |
| 2026-08-26 | premjers | FM jādod uzdevums aktīvi meklēt stratēģisko investoru | #704122 |

**Datumu vārti (quality-bars § Ierāmējums).** Aicinājums Saeimā notika **20.08.** — visi seši 1495/Lp14 balsojumi ir `vote_date='2026-08-20'`. 14,5 % vērtējums — **21.08.** Tie **nav viena diena**. Uzmanību: claim **#703862** (`stated_at` 2026-08-21, `topic='Budžets un finanses'`) ir tā paša 20.08. uzstāšanās atstāsts ar raksta datumu; saturiski to sedz #690497/#703858. Nelietot #703862 kā 21. augusta notikumu.

### Viktors Valainis (ZZS, ekonomikas ministrs visā periodā — saglabāja amatu arī Kulberga valdībā)
| Datums | Ko teica | Claim |
|---|---|---|
| 2026-08-07 | Katrs iedzīvotājs jau iemaksājis 250 EUR; katrs nākamais ieguldījums jāvērtē | #689336 |
| 2026-08-17 | Nevar apgalvot, ka ZZS frakcija gatava balsot par visu piedāvāto | #689754 |
| 2026-08-18 | «ZZS ir valdībā, un tieši tāpēc mūsu pienākums ir neklusēt» | #689777 |
| **2026-09-04** | 257 M aizņēmums **MK nav skatīts un atbalstīts**; atbildība ar likumu premjeram; ZZS redz Lufthansa virzienu | **#709060**; tension 262; note #533 |

### Atis Švinka (PRO; satiksmes ministrs līdz 28.05., pēc tam Saeimas deputāts opozīcijā)
| Datums | Amats | Ko teica | Claim |
|---|---|---|---|
| 2026-04-22 | ministrs | Likme «divciparu»; atmaksa no maija beigām/jūnija | #11313 |
| 2026-04-25 | ministrs | Vasarā nav plānota masveida reisu atcelšana | #11389 |
| 2026-05-19 | ministrs | Rosina Baltijas trīs valstu solidāru atbalsta modeli | #20589 |
| 2026-07-01 | deputāts | Valsts kapitāls 25 %+1 pieļaujams tikai pēc privāto investoru piesaistes | #532498 |
| 2026-08-18 | deputāts | Pirms jauna finansējuma sabiedrībai jāzina valdības stratēģija | #689791 |
| 2026-08-20 | deputāts | «Divarpus mēnešus nekas nav darīts»; airBaltic ≈1,5 % IKP eksportam | #703944, #703955 |
| 2026-08-21 | deputāts | Apgalvo, ka Valainis aiz slēgtām durvīm piedāvājis 600 M — «liekulība» | #703963; tension 234 |

### Rihards Kozlovskis (JV; iekšlietu ministrs → **satiksmes ministrs no 28.05.2026.**)
| Datums | Ko teica | Claim |
|---|---|---|
| 2026-06-01/02 | Vasarā valsts finansējums varētu būt nepieciešams | #521099, #521141 |
| **2026-07-20** | **«30 M atmaksas termiņš (31.08.) nav grozāms, jo to apstiprinājusi Saeima»** | **#548462** |
| 2026-07-28 | Atbalsta biznesa plānu: Rīga kā bāze + valsts 25 % + 1 akcija | #555721 |
| 2026-07-30 | Bez stratēģiskā investora plāns nav veiksmīgs; papildu valsts finansējums nav paredzēts | #555840–#555842 |
| **2026-08-14** | **Valdība plāno pagarināt atmaksas termiņu līdz 31.12.; lūgs Saeimai deleģējumu līdz 30 M** | **#689615, #689616, #689618, #689619** |
| 2026-08-20 | «Glābšana? Es teiktu — piedalīšanās biznesa plānā» | #690502, #703943 |
| 2026-09-03 | Valdība dara visu, lai bāzes vieta saglabātos Rīgā | #706183 |

**#548462 ↔ #689616 — `contradictions` rindas NAV.** `SELECT * FROM contradictions WHERE claim_old_id IN (…) OR claim_new_id IN (…)` pār visiem 19 galvenajiem claim ID atgriež **0 rindu**. Vienīgā airBaltic pretruna DB ir **#24 (Valainis, aprīlis)**. Tātad nedrīkst rakstīt «Kozlovskis mainīja nostāju» / «pretruna» / «apvērsums». Faktiskais mehānisms, kas abas pozīcijas savieno: 20.07. termiņu bija noteikusi Saeima, un tikai **jauns Saeimas lēmums 20.08.** (1495/Lp14) to varēja mainīt — ko arī izdarīja. Formulējums, kas paliek pierādījumu robežās: «to, ko jūlijā sauca par negrozāmu, augustā grozīja tā pati institūcija, kas bija noteikusi».

### Evika Siliņa (JV; premjere līdz 28.05., pēc tam demisionējusi / deputāte)
| Datums | Amats | Ko teica | Claim |
|---|---|---|---|
| 2026-08-17 | eks-premjere | Iepriekšējā valdība jau bija uzdevusi sagatavot biznesa plānu; svarīgi saglabāt valsts ietekmi | #689752, #689753 |
| 2026-08-20 | eks-premjere | Atbalsta valsts iesaisti, bet «valsts nevar būt vienīgais finansētājs» | #690518; note #474 |
Pret viņu vērsti: tension **222** (Kļaviņš, 14 % likme, «lombarda») un **225** (Kulbergs, 14,5 % kļūda).

---

## 5. Pretrunas un spriedzes

**`contradictions` ar `topic='airBaltic'` — viena rinda:**

| id | Persona | claims | Smagums | confirmed | reviewed | detected_at |
|---|---|---|---|---|---|---|
| **24** | Valainis | 6628 → 7414 | `minor_shift` | **1** | 1 | 2026-04-18 |

Citu airBaltic pretrunu DB **nav**, arī `confirmed=0` nav. Visas «pozīcijas maiņas» 2. daļā jāformulē kā hronoloģija, ne kā pretruna.

**`political_tensions` kopš 2026-04-22, kas piemin airBaltic** (13 rindas; `created_at` = UTC):

| id | created_at (UTC) | Tēma | Tips | No → Kam | Viena rinda |
|---|---|---|---|---|---|
| 85 | 04-26 12:12 | Pilsētvide | uzbrukums | Kulbergs → Kotello | airBaltic minēts tikai kā piemērs PRO «infrastruktūras bremzēšanai» |
| 86 | 04-29 06:53 | airBaltic | uzbrukums | Rokpelnis → Švinka | ZZS prasa Švinkas personīgo atbildību, citādi jāatkāpjas |
| 116 | 06-13 20:31 | airBaltic | uzbrukums | Šlesers → Briškens | Vaino PRO par bankrotu un Rail Baltica |
| 133 | 07-10 04:09 | airBaltic | uzbrukums | Šlesers → Ašeradens | Personificēta atbildības prasība pirms vēlēšanām |
| 145 | 07-16 23:59 | airBaltic | spriedze | Šlesers → Kozlovskis | Prasa rīcības plānu |
| 146 | 07-17 19:28 | Koalīcija | spriedze | Šuvajevs → Kulbergs | Lielie jautājumi (t. sk. airBaltic) paliek malā |
| 160 | 07-23 20:41 | airBaltic | spriedze | Šlesers → Kozlovskis | Aicina atlaist satiksmes ministru |
| 163 | 07-24 18:09 | Tieslietas | spriedze | Kulbergs → Siliņa | ST + Ģenerālprokuratūra vienā dienā |
| 222 | 08-20 21:29 | airBaltic | uzbrukums | Kļaviņš → Siliņa | 14 % likme, personisks apvainojums |
| 225 | 08-21 22:32 | airBaltic | spriedze | Kulbergs → Siliņa | 14,5 % darījums = kļūda |
| 230 | 08-23 19:13 | airBaltic | spriedze | Krauze → Kozlovskis | Koalīcijas ZZS deputāts pret ministru tajās pašās debatēs |
| 234 | 08-23 19:13 | airBaltic | uzbrukums | Švinka → Valainis | «600 M aiz slēgtām durvīm»; Valaiņa atbilde avotā nav |
| **262** | **09-04 20:45** | airBaltic | spriedze | **Valainis → Kulbergs** | Koalīcijas ministrs norobežojas no 257 M |
| 263 | 09-04 20:45 | airBaltic | spriedze | Liepnieks → Kulbergs | Prasa skaidrojumu par 25 % |
| 266 | 09-05 18:17 | airBaltic | spriedze | Velps → Kulbergs | 25 % = «ātro kredītu peļņa» |

Spriedzes **nav** pretrunas — tās ir fiksēti publiski uzbrukumi, ne apgalvojums par kāda nekonsekvenci.

---

## 6. Atvērtie jautājumi (publiskais ieraksts neatbild)

1. **Valsts aizdevuma likme.** Švinka 04-22 teica «divciparu skaitlis»; precīzs procents nekur publiski nav nosaukts. MK 25.08. lēmums min tikai 2 % soda naudu par atlikto summu.
2. **Vai valsts izmantos līdz 30 M pilnvarojumu.** MK lems atsevišķi; 06.09. lēmuma nav.
3. **Vai valsts 30 M ir 257 M ietvaros vai papildus.** Sk. § 7.1 — avoti to skaidri nenošķir.
4. **Kāds ir 2029. g. obligāciju atlikums pēc 17.08. kapitalizācijas.** Emitenta apstiprināts skaitlis nav atrasts.
5. **Kas notiks ar valsts 88,37 % daļu**, ja 50 M obligācijas + 18 M aizdevums tiks kapitalizēti un pievienosies jauns privātais kapitāls. Nav publicēta neviena pro forma īpašnieku struktūra.
6. **Švinkas «600 M aiz slēgtām durvīm»** (#703963) — Valaiņa atbilde publiskajā ierakstā nav fiksēta; apgalvojums paliek vienpusējs.
7. **Siliņas Liepājas jautājums** (1. daļa) — kopš 04-22 nekas jauns.
8. **Vai Ģenerālprokuratūras izvērtējums (24.07.) noslēdzies** — iznākums nav publicēts.

---

## 7. Tirgus komentētāja scenārijs — pārbaude

Avots, kas ierosināja šos jautājumus, ir anonīms X pavediens ar paša atrunu «guesstimate». **Tas nav citējams kā avots nevienam faktam.** Zemāk katrs apgalvojums pārbaudīts pret pirmavotiem.

### 7.1. Septembra darījuma struktūra

| Apgalvojums | Statuss | Pierādījums |
|---|---|---|
| Kopsumma 257 M | **CONFIRMED** | airBaltic paziņojums Nasdaq Riga 2026-09-03; [db.lv](https://db.lv/zinas/airbaltic-vienojusies-par-starpfinansejuma-nosacijumiem-lidz-257-miljoniem-eiro-ar-25-likmi) |
| Sadalījums «konsorcijs 150 M + valsts 30 M + vēlāk 77 M» | **REFUTED** | Publiskotais sadalījums ir **180 M + 77 M**, ne 150+30+77. Valsts nav atsevišķa daļa struktūrā. |
| Vai valsts 30 M ir 257 M **iekšpusē** | **NEPĀRBAUDĪTS** | Likums (20.08.) dod deleģējumu «valsts iespējamai dalībai airBaltic **starpfinansējuma obligāciju iegādē** līdz 30 M, piedaloties vienlaikus ar privātajiem investoriem un uz identiskiem nosacījumiem» → tas norāda uz dalību **tajā pašā emisijā** (proporcionāli ~13 % turējumam ≈ 33 M). Neviens avots to tomēr nesaka ar vārdiem «no kuriem» / «papildus». Nerakstīt ne vienu, ne otru. |
| Aizdevēji «Polus Capital» un «Klirmark Capital» | **CONFIRMED, ar precizējumu** | **Polus Capital Management** — Londonā bāzēta ieguldījumu pārvaldes sabiedrība; **Klirmark Capital 4** — Izraēlā reģistrēta ieguldījumu sabiedrība. LV avoti tos nosauc: [db.lv](https://db.lv/zinas/airbaltic-vienojusies-par-starpfinansejuma-nosacijumiem-lidz-257-miljoniem-eiro-ar-25-likmi), [diena.lv](https://diena.lv/raksts/latvija/zinas-71/airbaltic-vienojusies-par-starpfinansejuma-nosacijumiem-lidz-257-miljoniem-eiro-ar-25-likmi). Polus apņemas iegādāties vismaz pusi; Polus + Klirmark parakstās par to daļu, ko citi obligacionāri neizmanto. |
| Struktūra ir **super senior** (augstāka prioritāte par 2024. g. obligācijām) | **CONFIRMED** | «super senior bonds» — db.lv, diena.lv, airBaltic relīzes virsraksts. |
| «25 %» — kupons, PIK vai all-in | **NEPĀRBAUDĪTS** | Visi avoti raksta tikai «25 % gadā» / «procentu likme 25 %». Naudas kupona vai PIK dalījums nekur nav publicēts. Rakstīt «25 % gadā», nevis «kupons» vai «ienesīgums». |
| Termiņš | **CONFIRMED** | Dzēšana **2027-02-26**. |
| Nosacījumi | **CONFIRMED** | Obligacionāru piekrišana (sapulce 11.09.) **un** akcionāru piekrišana; 180 M pēc obligacionāru piekrišanas, 77 M pēc papildu nosacījumu izpildes. Padomes priekšsēdētājs **Andrejs Martinovs**: 25 % ir «labākais, ko airBaltic patlaban var saņemt». Vadītājs — **Erno Hildén**. Kovenanti publiski nav zināmi — **NEPĀRBAUDĪTS**. |

### 7.2. 2024. gada obligācijas

| Apgalvojums | Statuss | Pierādījums |
|---|---|---|
| Emisija 380 M, kupons 14,50 %, dzēšana 2029 | **CONFIRMED** | [sam.gov.lv 17.08.2026.](https://www.sam.gov.lv/lv/jaunums/airbaltic-obligaciju-turetaji-apstiprina-ierosinatos-grozijumus-obligaciju-noteikumos) |
| Pamatsumma šodien 395 M | **NEPĀRBAUDĪTS** | 17.08.2026. obligacionāri apstiprināja **14.08. un 14.11. maksājumu kapitalizāciju** (~27 M pieskaitāmi pamatsummai), tātad pamatsumma aug. Bet emitenta publicētu atlikumu ar datumu neatradu. 1. daļas «~380 M» apzīmē **emisijas nominālu**, ne pašreizējo atlikumu — tā arī jāformulē. |
| Valstij pieder obligācijas 50 M (≈13 %) | **CONFIRMED** | #689618 (Kozlovskis, 14.08.); db.lv 03.09. |

### 7.3. Bilance

| Apgalvojums | Statuss | Pierādījums |
|---|---|---|
| Pašu kapitāls −250 M | **NEPĀRBAUDĪTS** | Publiski pieejamie skaitļi: koncerna pašu kapitāls **−165,3 M 2024. g. beigās** un **−183,6 M 2025. g. beigās**. −250 M nav apstiprināts nevienā emitenta pārskatā, ko atradu. |
| Nauda, kopējie aizņēmumi, nomas saistības | **NEPĀRBAUDĪTS** | H1 2026 pārskata pozīcijas neatradu fetchojamā formā. |
| 2026. g. rezultāti | **daļēji** | 1. ceturksnī neto zaudējumi **70,1 M** (pret 29,3 M gadu iepriekš), ieņēmumi rekordaugsti **149,1 M**. H1 2026 ieņēmumi ~349,6 M, 2 454 900 pasažieru. Šie skaitļi nāk no otršķirīgiem pārstāstiem — pirms publicēšanas jāaizvieto ar emitenta pārskatu. |

### 7.4. Flote un plāns

| Apgalvojums | Statuss | Pierādījums |
|---|---|---|
| Flotes samazinājums −18 lidmašīnas | **CONFIRMED (pēc būtības)** | No ~54 uz ~36 A220-300 līdz 2026. g. beigām; ~40 līdz 2031. g. → −18. [lsm.lv 11.08.](https://www.lsm.lv/raksts/zinas/ekonomika/11.08.2026-airbaltic-maina-kursu-mazaka-flote-un-jauns-finansejums-simtiem-miljonu-apmera.a658405/), [lsm.lv 19.08.](https://www.lsm.lv/raksts/zinas/ekonomika/19.08.2026-pec-flotes-samazinasanas-airbaltic-kopeja-lidojumu-kapacitate-bus-par-10-mazaka.a659559/) |
| ACMI izbeigšana | **REFUTED** | Plāns paredz **ciešāku** komerciālu sadarbību ar ACMI partneriem, ne izbeigšanu (turpat). Švinka 07-01 prasīja tikai «ekonomiski pamatotus ACMI līgumus» (#532498). |
| Ieņēmumu prognoze ~600 M, EBITDAR ~110 M | **NEPĀRBAUDĪTS** | Publiskotā biznesa plāna daļā šie skaitļi neparādās. Publiskoti citi: ~225 M likviditātei tuvākajā laikā; mērķis ~45 M regulāra gada finanšu ieguvuma. |
| Kapacitāte pēc flotes samazināšanas | **CONFIRMED** | −10 % kopējā lidojumu kapacitāte (lsm.lv 19.08.); 2027. g. vasarā mazāk maršrutu (lsm.lv 02.09., a661481). |

### 7.5. Īpašumtiesības un kontrole

| Apgalvojums | Statuss | Pierādījums |
|---|---|---|
| Valsts daļa | **CONFIRMED** | **88,37 %** valstij, **10 %** Lufthansa, **1,62 %** «Aircraft Leasing 1», 0,01 % citi. |
| «Aircraft Leasing 1 / **Lauris Ekbergs**» | **REFUTED** | «Aircraft Leasing 1» saistīta ar **dāņu uzņēmēju Larsu Tūhesenu (Lars Thuesen)**. Vārds «Lauris Ekbergs» nav atrodams nevienā airBaltic akcionāru aprakstā. |
| ES 51 % īpašumtiesību un kontroles prasība | **CONFIRMED pēc būtības, panta teksts NEPĀRBAUDĪTS** | Regulas (EK) Nr. 1008/2008 **4. panta f) apakšpunkts**: ES gaisa pārvadātāja licences saņemšanai vairāk nekā 50 % uzņēmuma jāpieder dalībvalstīm un/vai dalībvalstu valstspiederīgajiem, un tiem uzņēmums **faktiski jākontrolē** (divpakāpju tests — īpašumtiesību daļa + faktiskā kontrole). EUR-Lex pilno tekstu neizdevās ievilkt (lapa neatgriež panta tekstu); pirms publicēšanas panta formulējums jācitē no [EUR-Lex ELI](https://eur-lex.europa.eu/eli/reg/2008/1008/oj/eng), nevis no šī apraksta. |
| Scenārijs «Polus & Klirmark 60–75 %, obligacionāri 15–30 %, valsts 10 %» | **NEPĀRBAUDĪTS — nepublicēt** | Neviens emitenta, MK vai ministrijas dokuments nesatur pēcrestrukturizācijas īpašnieku sadalījumu. Publiskots ir tikai virziens: daļa 2029. g. obligāciju → kapitāldaļās; valsts 50 M obligācijas + >17–18 M aizdevums plānoti kapitalizēt pamatkapitālā. |
| DB claim par kontroli/īpašniekiem kopš 08-25 | **1 rinda** | **#709040** (Krištopans, LPV, 2026-09-04): valsts «de facto zaudē lielāko daļu kontroles», pieļauj, ka valsts nepiedalīsies jaunajā emisijā un tās īpatsvars kļūs niecīgs. Tas ir **politiķa prognoze**, ne dokuments. Pretī: **#690468** (Vīksna, AS, 08-19) — kapitalizācija «nav norakstīšana», bet formas maiņa. |

---

## Vārti nākamajam solim

- Katram skaitlim tekstā jābūt vai nu claim/vote/tension/note ID ar datumu, vai URL no šī dokumenta.
- Neviena «mainīja nostāju» / «pretruna» konstrukcija ārpus #24.
- 257 M darījums ir **piedāvāts**, ne noslēgts — obligacionāru sapulce 11.09.2026. Jebkurš teikums pagātnes formā («aizņēmās», «saņēma») ir nepatiess uz 06.09.
- Balsojumu ķēdes citē veselas (T14) vai necitē vispār.
