# atmina.lv — politiskā atmiņa

**Ko viņi teica. Kā viņi balsoja.**

atmina ir Latvijas politiskās caurskatāmības platforma. Tā katru dienu lasa ziņu medijus, politiķu X/Twitter kontus un Saeimas balsojumu protokolus, izraksta no tiem politiķu **pozīcijas** — kurš, ko un kur ir teicis, ar saiti uz avotu — un meklē **pretrunas**: gan starp agrāk un tagad teikto, gan starp vārdiem un balsojumiem. Rezultāts ir publiska vietne [atmina.lv](https://atmina.lv).

> Vārds *atmiņa* šeit ir burtisks: platforma atceras, ko politiķis teica vakar, lai vēlētājam tas nebūtu jāatceras pašam.

---

## Ko vietne rāda

- **Pozīcijas** — politiķu izteikumi 32 tēmās; katram ir citāts, datums un saite uz avotu
- **Pretrunas** — pozīciju maiņas laika gaitā un nesakritības starp runāto un nobalsoto, katra ar abiem avotiem blakus
- **Saeimas balsojumi** — kā katrs deputāts balsojis katrā balsošanā, likumprojektu virzība pa lasījumiem
- **Partiju programmas** — 2026. gada vēlēšanu solījumi pa tēmām, lai vēlāk tos varētu salīdzināt ar padarīto
- **Nauda** — KNAB ziedojumu dati un amatpersonu deklarāciju kopsavilkumi
- **Dienas un nedēļas pārskati** — neitrāli faktu kopsavilkumi

Noskaņojuma ("sentimenta") analīzes nav — tā tika izmēģināta un izmesta kā neuzticama. atmina rāda, *kas pateikts* un *kā nobalsots*, nevis to, kā pret to justies.

## Principi

- **Katrai pozīcijai ir avots.** Izteikums bez pārbaudāmas avota saites datubāzē nemaz nenonāk — to nodrošina pati datu uzbūve, ne tikai labi nodomi.
- **Katru pretrunu pirms publicēšanas mēģina apgāzt.** Atsevišķā pārbaudes solī tiek meklēti pretargumenti: koalīcijas disciplīna, mainījies konteksts vai procedūras balsojums nav pretruna.
- **Citu cilvēku apgalvojumi par politiķi tiek attiecināti uz teicēju**, nevis pasniegti kā fakti.
- **Labojumi un atbildes tiesības.** Ja pamanāt kļūdu vai vēlaties atbildēt uz platformā atspoguļotu pozīciju, rakstiet uz **info@atmina.lv** vai izveidojiet GitHub *issue*.

## Kā tas strādā

```
  Ziņu mediji · X/Twitter · Saeima · KNAB · VID deklarācijas
                          │
                    ievākšana (RSS, twikit, Playwright)
                          │
                SQLite + vektoru meklēšana (sqlite-vec)
                          │
        Claude Code aģenti: pozīciju izguve →
        pretrunu meklēšana → pretargumentu pārbaude →
        kvalitātes pārbaude → pārskatu rakstīšana
                          │
              Jinja2 → statisks HTML → atmina.lv
```

Analīzes dzinējs ir [Claude Code](https://claude.com/claude-code) ar specializētiem aģentiem (`.claude/agents/`): `@claim-extractor` (pozīciju izguve), `@contradiction-hunter` (pretrunu meklēšana), `@devils-advocate` (pretargumentu pārbaude), `@quality-reviewer` (kvalitātes pārbaude), `@brief-writer` / `@weekly-brief-writer` (pārskati), `@saeima-tracker` (balsojumu ievākšana), `@graphics-designer` (attēli), `@mentions-monitor` (X pieminējumi). Publicēšanu apstiprina cilvēks; pati vietne ir statisks HTML un iztiek bez servera koda.

## Apjoms (2026. gada jūlijs)

| | |
|---|---|
| Politiķu profili | ~190 |
| Pozīcijas | 4000+ |
| Saeimas balsojumi | 6000+ (530 000+ individuālo balsu ierakstu) |
| Likumprojekti | ~350 (33 likumiem ir savas lapas) |
| Partiju programmu solījumi | 230+ (13 partijas) |
| Ievāktie dokumenti | 51 000+ |
| Darbībā | kopš 2026. gada aprīļa, atjaunojas katru dienu |

## Datu avoti

Visi avoti ir publiski; atmina neapkopo nepubliskus datus.

| Avots | Kas tiek ņemts |
|---|---|
| LSM, Delfi, TVNet, NRA, Diena, LA, Jauns.lv, rus.Delfi | Raksti (RSS un automātiska izguve) |
| X / Twitter | Politiķu pašu konti un pieminējumi |
| Saeima (titania.saeima.lv) | Balsojumi, likumprojekti, darba kārtības |
| KNAB | Ziedojumi, brīdinājumi |
| VID | Amatpersonu deklarācijas |
| Latvijas Vēstnesis | Izsludinātie likumi |
| CVK | Partiju vēlēšanu programmas |

## Izstrādātājiem

Tehnoloģijas: Python 3.11+, SQLite (WAL) + sqlite-vec, Pydantic v2, Jinja2, httpx + trafilatura, twikit, Playwright, Claude Code kā analīzes dzinējs.

```bash
git clone https://github.com/imaksligais/atmina-lv
cd atmina-lv
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
bash scripts/check.sh        # pārbaudes: ruff + pytest + renderēšanas tests
```

Piekļuves atslēgas glabājas operētājsistēmas atslēgu glabātavā (*keyring*; `python -m src.credentials set …`), nevis repozitorijā. Pilna uzstādīšanas instrukcija: [`wiki/operations/dev-setup.md`](wiki/operations/dev-setup.md); komandu saraksts: [`wiki/operations/commands.md`](wiki/operations/commands.md); datu kontrakti un invarianti: [`CLAUDE.md`](CLAUDE.md); shēmas lēmumu vēsture: [`wiki/CHANGELOG.md`](wiki/CHANGELOG.md).

Palīdzīgas rokas ir gaidītas — sk. [`CONTRIBUTING.md`](CONTRIBUTING.md). Par datu kļūdām ziņojiet ar GitHub *issue*, pievienojot avota saiti vai politiķa lapas adresi.

## Plāni un finansējums

Projekts ir viena izstrādātāja un Claude Code aģentu darbs, šobrīd pašfinansēts; iesniegts pieteikums NLnet **NGI0 Commons Fund** (2026-06). Tālākie nodomi: sociālo tīklu atbalsts vairākiem protokoliem (Bluesky, Mastodon), koda pārkārtošana, lai platformu varētu pārnest uz citu valstu parlamentiem, atvērto datu slānis (JSON eksports, API) un iespēja darbināt analīzi ar citiem valodu modeļiem. Līdzīgi projekti citur pasaulē: [Abgeordnetenwatch.de](https://www.abgeordnetenwatch.de) (Vācija) un [TheyVoteForYou](https://theyvoteforyou.org.au) (Austrālija).

## Licence

**AGPL-3.0-or-later** — stingrs *copyleft* ar tīkla klauzulu: ikvienam, kas darbina atvasinātu versiju kā tīkla pakalpojumu, ir pienākums publicēt tās pirmkodu. Caurskatāmības platformai arī pašai jābūt caurskatāmai. Pilns teksts: [`LICENSE`](LICENSE).

---

## In English

atmina is a Latvian political-transparency platform. It ingests news media, politicians' X/Twitter feeds, and Saeima (parliament) voting records daily; extracts source-cited **positions** per politician using a Claude Code agent pipeline; detects **contradictions** between past and present statements and between rhetoric and votes; and publishes a static site at [atmina.lv](https://atmina.lv). No sentiment analysis — only what was said and how they voted, with a source link on every claim. AGPL-3.0. Contact: info@atmina.lv.

*Veidots ar [Claude Code](https://claude.ai/code).*
