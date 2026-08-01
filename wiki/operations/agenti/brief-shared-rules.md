# Brief shared rules (daily + weekly)

Koplietotie žurnālistikas noteikumi `brief-writer` un `weekly-brief-writer`
aģentiem. Katrs aģents pievieno savu struktūras kontraktu; šie noteikumi ir
kopīgi.

## Mutācija
- Vienīgā atļautā DB rakstīšana ir `store_context_note()`. NEKAD DELETE/DROP/
  destruktīvs UPDATE uz `claims`, `contradictions`, `analyses`, `documents`,
  `document_politicians`, `tracked_politicians`, `saeima_*`.

## Avoti
- Katram pieminētam apgalvojumam jābūt `source_url`. Formāts: `[domēns.lv](pilns_url)`.
  Ja nav URL — `—`, nefabricē.

## Per-speaker atribūcija (OBLIGĀTI)
- Teikumā formā "X un Y [darbība] Z" katram nosauktajam runātājam DB jābūt
  vismaz vienam `claims` ierakstam par tieši TO substanci. Bucket-grupēšana un
  co-occurrence NAV pierādījums (2026-05-21 incidents: Lapsa par VK).

## NO DB iekšējiem ID/enum publiskā tekstā
- NEKAD `Pretruna #24`, `(minor_shift)`, `(6↔123)`. Lieto aprakstošas atsauces.

## LV-stilistika
- Pirms saglabāt palaid `lint_lv_style(content)` un izlabo visu. `5 %` (ar
  atstarpi), `eiro`, NE `ataka/polemika/aksi/startā`. Saglabā diakritiku.
- **Neizgudro vārdus / nelieto kalkus.** Lints (`src/lv_style.py` ANGLICISMS)
  noķer tikai slēgto sarakstu; PĀRI tam verificē pret standarta LV — kalkus
  lints NEvar noķert. Pazīstamie labojumi:

  | Nepareizi (kalks/izgudrots) | Pareizi (standarta LV) |
  |---|---|
  | ataka | uzbrukums *(lint)* |
  | polemika | diskusija / domstarpības *(lint)* |
  | melīšana | melošana *(lint)* |
  | konsenss | vienprātība / vienota nostāja *(lint)* |
  | smiltsstunda | smilšu pulkstenis *(kalks, NE lint)* |

  Vāciski kalkēti salikteņi (smiltsstunda, viesnīcgalds, lapsuvis) → aizvieto ar
  aprakstošu native frāzi. Arī `metaphor_hint` laukos: aprakstošas LV frāzes, ne
  kalki ("smiltsstunda" → "smilšu pulkstenis").

## Datumi un īpašvārdi
- Nedēļas dienu pie datuma raksti TIKAI pēc pārbaudes (`python -c "import
  datetime; print(datetime.date(2026,7,4).strftime('%A'))"`) — nepārbaudīta
  diena ir izdomāta diena (2026-07-05 weekly incidents: "ceturtdien,
  4. jūlijā" — patiesībā sestdiena).
- Personvārda pamatformu pirms locīšanas verificē pret avotu dokumentiem —
  divi līdzīgi vārdi lokās atšķirīgi (2026-07-05 incidents: "Elvja Strazdiņa"
  ← avotos dominē "Elviss", tātad ģen. "Elvisa").

## Neitralitāte
- Bez ieteikumiem, partijas perspektīvas, subjektīviem īpašības vārdiem.
  Proporcionāli substancei, ne mākslīgam balansam.
