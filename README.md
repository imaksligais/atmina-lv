# atmina.lv — politiskā atmiņa

[![CI](https://github.com/imaksligais/atmina-lv/actions/workflows/ci.yml/badge.svg)](https://github.com/imaksligais/atmina-lv/actions/workflows/ci.yml)
[![Licence: AGPL-3.0](https://img.shields.io/badge/licence-AGPL--3.0-blue.svg)](LICENSE)
[![Vietne](https://img.shields.io/badge/vietne-atmina.lv-2e7d32.svg)](https://atmina.lv)

**Ko viņi teica. Kā viņi balsoja.**

atmina atceras, ko Latvijas politiķi ir teikuši un kā viņi ir balsojuši, lai vēlētājam tas nebūtu jāatceras pašam. Katram izteikumam ir saite uz avotu. Viss ir publiski lasāms vietnē **[atmina.lv](https://atmina.lv)**.

---

## Kas tas ir

Katru dienu atmina izlasa ziņu medijus, politiķu X/Twitter kontus un Saeimas balsojumus. No tiem tā izraksta politiķu **pozīcijas**: kurš, ko, kad un kur teica. Tad tā meklē **pretrunas**: vai politiķis tagad saka ko citu nekā agrāk un vai viņa vārdi atbilst viņa balsojumiem.

Noskaņojumu atmina nevērtē. Tā rāda tikai to, kas pateikts un kā nobalsots, ar avotu blakus.

## Ko var atrast vietnē

| Sadaļa | Kas tur ir |
|---|---|
| **Profili** | Katra politiķa pozīcijas, balsojumi, pretrunas un X ieraksti vienā lapā |
| **Pozīcijas** | Izteikumi 35 tēmās — citāts, datums, avota saite |
| **Pretrunas** | Mainīts viedoklis vai vārdi pret balsojumu, abi avoti blakus |
| **Saeima un balsojumi** | Kā katrs deputāts balsoja; likumprojektu ceļš pa lasījumiem |
| **Partijas** | Partiju sastāvs un 2026. gada vēlēšanu programmu solījumi |
| **Spriedzes** | Ko politiķi publiski saka viens par otru — kritika un atbalsts |
| **Saites** | Politiķu savstarpējo saikņu karte — kurš par kuru ko teicis |
| **Finanses** | Partiju finanses un ziedojumi pēc KNAB datiem |
| **Analīzes un atradumi** | Padziļināti pētījumi, piemēram, par valsts naudu nevalstiskajām organizācijām un amatpersonu deklarācijām |
| **Mediji** | Kam pieder Latvijas mediji un kā tie tiek finansēti |
| **Pārskati** | Dienas un nedēļas pārskati — tikai fakti, bez vērtējuma |

## Principi

- **Bez avota nav pozīcijas.** Izteikumu bez avota saites atmina nesaglabā.
- **Katru pretrunu vispirms mēģina apgāzt.** Atsevišķā pārbaudē meklē pretargumentus: vai šķietamo pretrunu neizskaidro partijas disciplīna, apstākļu maiņa vai balsojums par procedūras jautājumu.
- **Citu teikto attiecina uz teicēju.** Ja kāds apgalvo kaut ko par politiķi, tas paliek šī cilvēka teiktais, nevis fakts.
- **Cilvēks apstiprina, pirms kaut kas tiek publicēts.** Pārskati un analīzes nonāk vietnē tikai pēc pārlasīšanas un skaidras atļaujas.
- **Labojumi un atbildes tiesības.** Pamanījāt kļūdu? Rakstiet uz **redakcija@atmina.lv** vai iesniedziet kļūdas ziņojumu GitHub.

## Kā tas strādā

```
  Ziņu mediji · X/Twitter · Saeima · KNAB · VID · Latvijas Vēstnesis
                              │
                  ievākšana (RSS, twikit, Playwright)
                              │
                  SQLite + vektoru meklēšana (sqlite-vec)
                              │
        Claude Code aģenti: pozīciju izguve → pretrunu meklēšana
        → pretargumentu pārbaude → kvalitātes pārbaude → pārskati
                              │
               cilvēka apstiprinājums → statisks HTML → atmina.lv
```

Analīzi veic [Claude Code](https://claude.com/claude-code) aģenti. Katram ir savs uzdevums; to apraksti ir mapē [`.claude/agents/`](.claude/agents/):

- `@claim-extractor` — izraksta pozīcijas no rakstiem un ierakstiem
- `@stance-checker` — neatkarīgi pārbauda, vai pozīcija atbilst avotam
- `@contradiction-hunter` — meklē pretrunas, arī starp vārdiem un balsojumiem
- `@devils-advocate` — mēģina katru pretrunu apgāzt pirms publicēšanas
- `@quality-reviewer` — pēdējā pārbaude pirms publicēšanas
- `@brief-writer`, `@weekly-brief-writer` — dienas un nedēļas pārskati
- `@saeima-tracker` — apkopo Saeimas sēžu darba kārtības un balsojumu rezultātus
- `@graphics-designer` — pārskatu attēli
- `@mentions-monitor` — politiķu pieminējumi X tīklā
- `@outlet-researcher` — mediju īpašnieku un finansējuma fakti
- `@video-extractor` — pozīcijas no video transkriptiem (vēl nav lietots ikdienā)

Vietne ir statisks HTML bez servera koda. Sīkdatņu nav: apmeklējumu skaitu mēra ar [Umami](https://umami.is), kas darbojas bez sīkdatnēm.

## Datu avoti

Visi avoti ir publiski. Nepubliskus datus atmina nevāc.

| Avots | Ko ņemam |
|---|---|
| LSM, Delfi, TVNet, LETA, Neatkarīgā, Diena, Latvijas Avīze, Jauns.lv | Ziņu raksti (RSS un automātiska izguve) |
| X / Twitter | Politiķu pašu ieraksti un pieminējumi |
| Saeima (titania.saeima.lv) | Balsojumi, likumprojekti, sēžu darba kārtības |
| Latvijas Vēstnesis | Izsludinātie likumi un tiesību akti |
| KNAB | Partiju ziedojumi |
| VID | Amatpersonu deklarācijas |
| CVK | Kandidātu saraksti un partiju programmas |

Aktuālie skaitļi (cik politiķu, pozīciju, balsojumu un dokumentu) mainās katru dienu. Tie ir šeit: [`wiki/index.md`](wiki/index.md) un vietnes lapā [Statistika](https://atmina.lv/statistika.html).

## Atbalsts un plāni

Vietnes saturs ir bez maksas visiem un tāds arī paliks. Ja gribat palīdzēt segt izmaksas: **[atbalsts.atmina.lv](https://atbalsts.atmina.lv)**. Atbalstītāji neietekmē, par kādām tēmām vai politiķiem atmina raksta.

Projekts ir iesniedzis pieteikumu arī NLnet **NGI0 Commons Fund** (2026. gada jūnijā).

**Tālākie plāni:** atvērto datu eksports (JSON, API), atbalsts Bluesky un Mastodon, iespēja darbināt analīzi ar citiem valodu modeļiem un pielāgot platformu citu valstu parlamentiem. Līdzīgi projekti citur: [Abgeordnetenwatch.de](https://www.abgeordnetenwatch.de) (Vācija) un [TheyVoteForYou](https://theyvoteforyou.org.au) (Austrālija).

## Izstrādātājiem

<details>
<summary><b>Uzstādīšana un testi</b></summary>

Tehnoloģijas: Python 3.11+, SQLite (WAL) + sqlite-vec, Pydantic v2, Jinja2, httpx + trafilatura, twikit, Playwright. Analīzes dzinējs ir Claude Code.

```bash
git clone https://github.com/imaksligais/atmina-lv
cd atmina-lv
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python scripts/patch_twikit.py
python -m playwright install chromium

python -m ruff check src scripts tests
python -m pytest tests -q -m "not integration and not slow"
```

Pēdējās divas komandas palaiž arī CI. Tās jāiztur katram *pull request*.

`bash scripts/check.sh` svaigā klonā **nestrādās**, un tas ir gaidīts. Tas ģenerē vietnes lapas no operatora datubāzes `data/atmina.db`, ko repozitorijs neizplata. Šis skripts ir uzturētāja pēdējā pārbaude pirms publicēšanas, nevis prasība līdzstrādniekam.

Piekļuves atslēgas glabājas operētājsistēmas atslēgu glabātavā (*keyring*), nevis repozitorijā.

Kur lasīt tālāk:

- uzstādīšana — [`wiki/operations/dev-setup.md`](wiki/operations/dev-setup.md)
- komandas — [`wiki/operations/commands.md`](wiki/operations/commands.md)
- datu noteikumi un zināmās kļūdu klases — [`CLAUDE.md`](CLAUDE.md)
- lēmumu vēsture — [`wiki/CHANGELOG.md`](wiki/CHANGELOG.md)
- kā palīdzēt — [`CONTRIBUTING.md`](CONTRIBUTING.md)

</details>

Palīdzīgas rokas ir gaidītas. Ja atrodat kļūdu datos, iesniedziet kļūdas ziņojumu GitHub un pievienojiet avota saiti vai politiķa lapas adresi.

## Licence

**AGPL-3.0-or-later.** Kas darbina pārveidotu versiju kā tīkla pakalpojumu, tam jāpublicē arī tās pirmkods. Caurskatāmības platformai pašai jābūt caurskatāmai. Pilns teksts: [`LICENSE`](LICENSE).

---

## In English

**atmina** is a Latvian political-transparency platform. Every day it reads news media, politicians' X/Twitter feeds and Saeima (parliament) voting records. A pipeline of Claude Code agents extracts source-cited **positions** for each politician and looks for **contradictions** — between what was said before and now, and between rhetoric and votes. Each contradiction is challenged by a separate adversarial step before publication, and a human approves every brief and analysis before it goes live.

The result is a static site at [atmina.lv](https://atmina.lv): politician profiles, Saeima votes, party programmes, donations and declarations, investigative analyses and daily/weekly briefs. No sentiment analysis — only what was said and how they voted, with a source link on every claim.

Licensed AGPL-3.0-or-later. Contributions are welcome; see [`CONTRIBUTING.md`](CONTRIBUTING.md). Contact: redakcija@atmina.lv · Support: [atbalsts.atmina.lv](https://atbalsts.atmina.lv)
