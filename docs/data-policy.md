# Data Policy / Datu politika

**Last reviewed:** 2026-05-15
**Maintainer contact:** info@atmina.lv
**Jurisdiction:** Latvia (EU GDPR + Fizisko personu datu apstrādes likums)

---

## Abstract (English)

atmina collects, structures, and re-publishes **public statements and public records** about Latvian politicians: media interviews, social-media posts, parliamentary votes, campaign-finance declarations, asset declarations, and promulgated laws. The platform processes personal data of public officials in the exercise of their public duties.

Legal basis: GDPR Art. 6(1)(e) (public interest) and the journalistic-purpose exemption in GDPR Art. 85 as transposed into Latvian law (Fizisko personu datu apstrādes likums § 32).

This policy describes what we collect, how to request corrections, and how to invoke the right of reply.

---

## 1. Mērķis (Purpose)

atmina ir Latvijas politiskās caurskatāmības platforma. Mēs apkopojam **publiski izteiktas** politiķu pozīcijas, balsojumus un publiskus reģistru datus, lai vēlētāji varētu izsekot retorikas un rīcības atbilstībai laikā.

Mēs **neglabājam un nepublicējam**:
- privātu saraksti vai personīgo dzīves datus;
- avotus, kas nav publiski pieejami;
- nepilngadīgo personu datus;
- politiķu ģimenes locekļu datus (izņemot, ja tie paši ir publiski politiķi vai amatpersonas);
- subjektīvus vērtējumus, sentimentu vai izteikumu interpretāciju.

## 2. Datu apjoms (Scope of collected data)

| Datu tips | Avots | Glabāšana |
|---|---|---|
| Mediju raksti ar politiķa pozīciju | LSM, Delfi, NRA, TVNet, Diena, LETA, LA, Jauns.lv | Saites + ekstrahēts saturs (trafilatura), `source_url` katram apgalvojumam |
| X/Twitter ieraksti | Politiķa publiski X profili | URL + teksts |
| Saeimas balsojumi | titania.saeima.lv | Pilns vēsturisks balsojumu reģistrs |
| Likumprojekti un to posmi | Saeima + LR Vēstnesis | Posmu hronoloģija (`append_bill_stage`) |
| KNAB priekšvēlēšanu finansu deklarācijas | knab.gov.lv | Ziedojumi, brīdinājumi |
| VID amatpersonu deklarācijas (VAD) | vid.gov.lv | Pamatdarbība, papildienākumi, īpašumi (publiski reģistri) |
| Latvijas Vēstnesis | vestnesis.lv | Promulgētie tiesību akti |

Visi avoti ir **publiski pieejami**. atmina neveic non-publisku reģistru skrēpošanu, nepieprasa parakstītu piekļuvi un neuzglabā nekādus datus, kas nav pirmtiesīgi publicēti pašu politiķu vai kompetento iestāžu.

## 3. Juridiskais pamatojums (Legal basis)

- **GDPR 6. panta 1. punkta e) apakšpunkts** — apstrāde sabiedrības interesēs (politiskās līdzdalības caurskatāmība).
- **GDPR 85. pants** — žurnālistikas un akadēmisko mērķu izņēmums.
- **Fizisko personu datu apstrādes likums 32. pants** (LV) — žurnālistikas, akadēmisku, mākslinieciskās izpausmes vai literāras izteikšanās mērķim.

Publiski ievēlēti vai amatā ieceltie politiķi atbilstoši Eiropas Cilvēktiesību tiesas judikatūrai (*Lingens pret Austriju*, 1986; *Oberschlick pret Austriju*, 1991) ir uzskatāmi par publiskām personām attiecībā uz savu politisko darbību, un viņu privātās dzīves aizsardzības standarts šajā kontekstā ir samazināts.

## 4. Datu kontrolieris (Data controller)

| Lauks | Vērtība |
|---|---|
| Datu kontrolieris | atmina projekta uzturētājs (fiziska persona) |
| Kontaktinformācija | info@atmina.lv |
| Atrašanās vieta | Latvija |
| Pārstāvis ES | n/a (datu kontrolieris pats atrodas ES) |
| Datu aizsardzības inspektors (DPO) | Nav iecelts (apjoms zem GDPR 37. panta sliekšņa) |

Sūdzības iespējams iesniegt arī **Datu valsts inspekcijai** (dvi.gov.lv).

## 5. Politiķa tiesības (Data subject rights)

Jebkura persona, kuras dati atmina apstrādā, var īstenot šādas tiesības:

| Tiesība | GDPR pants | atmina process |
|---|---|---|
| Piekļuves tiesības | 15 | E-pasts, atbilde 30 dienu laikā |
| Labošanas tiesības | 16 | Sk. **§6 Right of reply** zemāk |
| Dzēšanas tiesības | 17 | Sk. **§7 Takedown** zemāk |
| Apstrādes ierobežošana | 18 | Pieejams strīda gadījumā |
| Iebildumu tiesības | 21 | Aplūko individuāli; žurnālistikas izņēmums var ierobežot |
| Pārnesamība | 20 | Nav piemērojama (publiski dati, ne lietotāja konts) |

## 6. Atbildes tiesības (Right of reply)

Politiķi un publiskās amatpersonas var pieprasīt papildināt savu profilu ar formālu atbildi uz konkrētu apgalvojumu vai pretrunu.

**Process:**

1. Sūti e-pastu uz **info@atmina.lv** ar tēmu `[atmina-reply] <politiķa slug>`.
2. Norādi konkrēto URL atmina.lv (piemēram, `https://atmina.lv/politiki/<slug>.html#claim-12345`).
3. Pievieno atbildes tekstu (līdz 500 vārdi) un datumu.
4. Atbilde tiek pievienota profila lapā ar skaidru norādi, ka tā ir politiķa oficiāla atbilde, ne atmina redakcijas viedoklis.

Mēs **nepublicējam** atbildes, kas:
- satur trešo personu personīgi identificējamus datus;
- pārkāpj LR likumus (goda aizskaršana, naida runa);
- neatsaucas uz konkrētu apgalvojumu vai pretrunu atmina vietnē.

Atbildes parasti tiek publicētas 7 darba dienu laikā.

## 7. Labošana, dzēšana, takedown (Correction & takedown)

### 7.1 Faktiskās kļūdas

Ja atmina ir nepareizi attiecināts apgalvojums, kļūdaini citēts mediju raksts vai nepareizi sakārtots balsojums:

1. E-pasts uz **info@atmina.lv** ar tēmu `[atmina-correction] <politiķa slug>`.
2. Norādi konkrēto URL un faktisko kļūdu (ar pierādījumu — oriģinālā avota saiti).
3. Labojums tiek izpildīts 3 darba dienu laikā, ar publisku CHANGELOG ierakstu un, ja nepieciešams, redakcijas paskaidrojumu.

### 7.2 Pilnīga dzēšana

Pilnīga datu dzēšana parasti **netiek piešķirta** politiķiem attiecībā uz viņu publisko darbību (žurnālistikas izņēmums, GDPR 85. pants). Tomēr tiek dzēsti:

- **automātiski**: ja avots tiek noņemts no oriģinālā mediju portāla un nav arhivēts atklātos arhīvos;
- **pēc pieprasījuma**: amata zaudēšanas + 5 gadu pēc darbības pārtraukšanas, ja persona vairs nav publiska amatpersona;
- **pēc pieprasījuma**: nelikumīga datu apstrāde (piem., kļūdaina personas datu sajaukšana — homonīmu vai diakritisko zīmju trūkuma dēļ).

### 7.3 Right to be forgotten

Persons, kas vairs nav publiskā politiskā amatā un nav kandidē 5 gadu laikā, var pieprasīt sava profila arhivēšanu (publiskā URL atvienošanu, datu saglabāšanu auditācijai). Apstrāde 30 dienu laikā.

## 8. Avotu disciplīna (Source citation)

Katram apgalvojumam (`claim`) atmina datu bāzē ir obligāta `source_url`. Bez tā apgalvojums tiek atmests DB slānī bez kļūdas — tas ir tehnisks invariants, ne politika ([CLAUDE.md §2](../CLAUDE.md)).

Pretrunas (`contradictions`) tiek saglabātas tikai pēc divkārša aģentu procesa:
1. `@contradiction-hunter` ekstraktē kandidātus.
2. `@devils-advocate` adversariāli verificē un atfiltrē procedurālus / koalīcijas-disciplīnas false-pozitīvus.

## 9. Kā mēs novēršam kļūdas (Error mitigation)

- **Source-URL invariants** — apgalvojumi bez avota tiek atmesti.
- **`@quality-reviewer`** — pēdējais aģents pirms publicēšanas; pārbauda datu integritāti, neitralitāti, valodu.
- **Append-only context notes** — vēsturisko pozīciju nedrīkst pārrakstīt; jaunas piezīmes pievieno atsevišķās rindās.
- **Sentiment analysis ir noņemts** — atmina nepublicē emocionālus / subjektīvus vērtējumus.
- **Politiķu identifikācija** — vārds + uzvārds + partija (`name_forms` + `negative_patterns`); homonīmu gadījumi tiek manuāli risināti.

## 10. Atklātība par mūsu kļūdām

Labojumi tiek dokumentēti publiski:
- `wiki/CHANGELOG.md` — strukturāli un schema lēmumi.
- Git commit vēsture — katrs labojums ar `fix(profiles):` vai `fix(claims):` prefiksu.
- Daily / weekly brief sekcijā — ja kļūda skāra publicētu pārskatu.

## 11. Trešo personu datu apstrāde

atmina neizmanto:
- analītikas pakalpojumus (Google Analytics, Plausible, utt.);
- reklāmas tīklus;
- lietotāju kontu sistēmas;
- cookies (izņemot serveru tehniskos cookies, ja tādi būtu).

atmina.lv ir **statisks HTML** — nav backend, kas glabātu apmeklētāju datus.

Aģentu inference notiek caur **Anthropic API** (Claude). Anthropic ir mūsu apakšapstrādātājs (sub-processor). Anthropic atrašanās vieta: ASV. Sk. Anthropic privacy policy: https://www.anthropic.com/legal/privacy. **M5** milestone plāno LLM provider abstrakciju, kas atļaus self-hosted modeļu izmantošanu un samazinās šo atkarību.

## 12. Šī politika

| Lauks | Vērtība |
|---|---|
| Versija | 1.0 (melnraksts pirms public flip) |
| Spēkā stāšanās | Pēc atmina repo publicēšanas |
| Iepriekšējās versijas | Git vēstures `docs/data-policy.md` |
| Pārmaiņu paziņojumi | Atjauninājumi tiek pievienoti `wiki/CHANGELOG.md` |

Politikas autoritatīvā versija ir **angļu valodā** šī faila §1 abstract. Latviešu sadaļas ir tulkojums priekš sabiedrības pieejamības; konflikta gadījumā piemēro angļu versiju kopā ar latviešu likumdošanu.

---

*Šī politika tiek pārskatīta vismaz reizi 12 mēnešos vai būtisku izmaiņu gadījumā atmina darbībā.*
