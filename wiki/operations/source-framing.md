# Avotu framing apzināšanās

Katram avotam `sources.yaml` ir `framing:` lauks kas raksturo medija redakcionālo perspektīvu. Kad `@claim-extractor` apstrādā dokumentu, viņam jāapzinās no kura avota tas nāk. Tas pats notikums LSM un Neatkarīgā var tikt atspoguļots ar atšķirīgu akcentu.

**Aģenta uzdevums:** izvilkt politiķa faktisko pozīciju, nevis avota interpretāciju.

## Avotu profili

| Avots | Framing | Piezīmes |
|-------|---------|----------|
| **LETA** | Faktoloģisks | Visfaktoloģiskākais, minimāla interpretācija |
| **LSM** | Institucionāli neitrāls | Tendēts uz valdības pozīcijas atspoguļošanu |
| **Neatkarīgā** | Konservatīvi nacionāla | Vairāk opozīcijas perspektīvas |
| **Delfi** | Engagement optimizēts | Sensacionālāki virsraksti |
| **TVNet** | Keyword-filtered | Tikai politiskais saturs (konfigurēts sources.yaml) |
| **Latvijas Avīze** | Konservatīvi-centriska | Lauku/nacionālās identitātes fokuss, deklarāciju un caurskatāmības tēmas |
| **Jauns.lv** | Tabloid-uzsvars, augsta personu blīvuma | Sensacionālāki virsraksti, ātrs ziņu cikls; bieži pirmie ar deputātu finanšu/Saeimas algu stāstiem un reģionālajiem skandāliem; pārklāj politiku/sabiedrību/Riga municipal |

## Kā lietot

Lasot dokumentu no konkrēta avota:
1. Pārbaudīt avota `framing:` lauku `sources.yaml`
2. Izvilkt **politiķa pozīciju**, nevis žurnālista interpretāciju
3. Ja citāts ir tieši no politiķa — augstāka confidence
4. Ja ir tikai avota pārstāsts — zemāka confidence, pievienot reasoning

## Saistība ar publiskajiem mediju profiliem (`/mediji`)

Šis `framing:` lauks ir **INTERNS** — tikai `@claim-extractor` confidence signāls;
to **nepublicē**. Atsevišķi, publiskie, **avototie** caurskatāmības fakti (īpašnieks,
finansējums, juridiskā forma, redakcijas vadība, dibināšana) dzīvo `sources.yaml`
`outlets:` blokā un renderējas `/mediji` lapās (`src/outlets.py` + `src/render/mediji.py`);
tos aizpilda [[operations/agenti/outlet-researcher|@outlet-researcher]]. Princips:
caurskatāmība, ne mērķēšana — faktiem ir avoti, `framing:` paliek aizkulisēs.

> **Autoritatīvais saraksts:** augšējā tabula ir ilustratīva (daļa avotu); pilnais
> avotu + `framing:` saraksts ir `sources.yaml` (tur dzīvo arī `outlet:` tagi, kas grupē
> feed rindas mediju entītijās).
