# @contradiction-hunter

> Kanoniskais prompts (izpildei): [.claude/agents/contradiction-hunter.md](../../../.claude/agents/contradiction-hunter.md) — šī lapa ir īss apraksts cilvēkiem.

Krusteniskais analītiķis — salīdzina publiskos izteikumus ar Saeimas balsojumiem un seko pozīciju izmaiņām laika gaitā.

**Ko dara:** Atrod pretrunas starp politiķu retoriku un balsojumiem. Filtrē false positives no koalīcijas disciplīnas, procedurāliem balsojumiem un atšķirīgām apakštēmām. Izvada strukturētus kandidātus @devils-advocate pārskatīšanai.

**Kad izmanto:** Nedēļas rutīnā vai pēc jaunas Saeimas sesijas apstrādes. Max 5 politiķi sesijā.

**Ievade:** (1) Politiķi ar gan `position`, gan `vote` claims — retorika↔balsojums. (2) Politiķi ar 5+ position claims — pozīciju maiņa laika gaitā.

**Izvade:** Kandidātu saraksts ar pilnu kontekstu — frakcijas balsojums, false positive pārbaude, žurnālista tests, ieteiktā severity/salience.

**Princips:** "Vai politiķis to varētu izskaidrot 30 sekundēs?" Ja jā — droši vien nav pretruna. Ja skaidrojumam vajag spin — ir kandidāts.

**Divi detektēšanas režīmi:**
- **Retorika↔balsojums** — publisks izteikums vs. Saeimas balsojums (frakcijas disciplīnas pārbaude obligāta)
- **Pozīcija↔pozīcija** — izteikumu maiņa laika gaitā (laika starpības un konteksta maiņas analīze)

**8 false positive filtri:**
1. Koalīcijas disciplīna (visa frakcija balsoja tāpat)
2. Taktiska bloķēšana (partija virzīja savu versiju)
3. Atšķirīga apakštēma (plašs topics sakrīt, bet konkrēts jautājums atšķiras)
4. Procedurāls balsojums (turpmāko virzību, nodošana komisijām)
5. Konsekventa duālā pozīcija (abas pozīcijas loģiski saderīgas)
6. Leģitīma evolūcija (konteksts mainījies 3+ mēnešos)
7. Lomas maiņa (no opozīcijas uz valdību vai otrādi)
8. Auditorijas freimings (tā pati pozīcija citādi formulēta citai auditorijai)

---
> Pilns aģenta prompts: `.claude/agents/contradiction-hunter.md`
