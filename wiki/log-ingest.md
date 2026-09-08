# Ingest Log

_Hronoloģisks žurnāls — katrs dokuments, kad apstrādāts, no kura avota._

Žurnāls rotē reizi mēnesī. Raksti dzīvo `wiki/log-ingest/<YYYY-MM>.md` failos; `append_ingest_entry()` un `append_ingest_batch_summary()` (src/ingest_log.py) automātiski raksta aktīvā mēneša failā.

## Mēneši

- [[log-ingest/2026-04|2026. gada aprīlis]]
- [[log-ingest/2026-05|2026. gada maijs]]
- [[log-ingest/2026-06|2026. gada jūnijs]]
- [[log-ingest/2026-07|2026. gada jūlijs]]
- [[log-ingest/2026-08|2026. gada augusts]]
- [[log-ingest/2026-09|2026. gada septembris]]

> **Šo sarakstu tagad uztur kods** (`_ensure_index_entry()`, `src/ingest_log.py`, 2026-08-27) — `_resolve_log_file()` to izsauc katrā ingest, tāpēc jauns mēnesis rindu pieliek pats, un jau aizdreifējis indekss nākamajā ingest panāk sevi. Nepievieno rindas ar roku.
>
> Kāpēc vārts eksistē: līdz tam saraksts bija rakstīts ar roku, kamēr faili rotēja automātiski, un tas divreiz aizdreifēja klusi — trīs mēnešus (05–07) tas rādīja tikai aprīli (trīs no četriem žurnāla failiem no šejienes nebija sasniedzami), un 2026-08-27 atkal bija par vienu mēnesi atpalicis. Iepriekšējā redakcija šeit lūdza cilvēkam atcerēties pievienot rindu — t.i. vārts, kas paļaujas uz atmiņu. Testi: `tests/test_ingest_log_index.py` (7, mutācijas-pārbaudīti — izņemot izsaukumu, divi kļūst sarkani; fixtūra ir `tmp_path`, tāpēc tie nostrādā arī tad, kad `wiki/log-ingest/` uz diska nav).
>
> **Mēneša faili ir lokāli, nav git-izsekoti** (`.gitignore`, 2026-08-01) — tie ir append-only operatora diagnostika, ~110 KB mēnesī, ko lasa tikai interaktīvi. Publiskajā repo šīs saites tāpēc neved nekur; jēgpilnā ielādes vēsture dzīvo [[CHANGELOG]]. Pati mape un lasīšanas ceļš strādā normāli — `read_ingest_log()` lasa no diska.

## Lasīšana

```python
from src.ingest_log import read_ingest_log
# Jaunākie 10 ieraksti pāri visiem mēneša failiem (newest first):
print("\n".join(read_ingest_log(last_n=10)))
```

`read_ingest_log()` noklusēti lasa no `wiki/log-ingest/` direktorijas, iet caur mēneša failiem no jaunākā uz vecāko, un apkopo ierakstus līdz `last_n` ir sasniegts.

## Vēsturiski

Pirms 2026-04-21 visi ingest ieraksti dzīvoja šajā failā kā append-only log (297 rindas). Migrācijas laikā saturs tika pārdalīts mēneša failos — tagad šis fails ir indekss. Rotācijas iemesls: audit log faili aug monotoni un bez rotācijas kļūst grūti navigējami.
