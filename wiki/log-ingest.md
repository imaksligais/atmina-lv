# Ingest Log

_Hronoloģisks žurnāls — katrs dokuments, kad apstrādāts, no kura avota._

Žurnāls rotē reizi mēnesī. Raksti dzīvo `wiki/log-ingest/<YYYY-MM>.md` failos; `append_ingest_entry()` un `append_ingest_batch_summary()` (src/ingest_log.py) automātiski raksta aktīvā mēneša failā.

## Mēneši

- [[log-ingest/2026-04|2026. gada aprīlis]]
- [[log-ingest/2026-05|2026. gada maijs]]
- [[log-ingest/2026-06|2026. gada jūnijs]]
- [[log-ingest/2026-07|2026. gada jūlijs]]

> Šis saraksts ir **rakstīts ar roku**, kamēr paši faili rotē automātiski — tāpēc tas aizdreifē klusi. Trīs mēnešus (05–07) tas rādīja tikai aprīli, tātad trīs no četriem žurnāla failiem no šejienes nebija sasniedzami. Kad `append_ingest_entry()` atver jaunu mēnesi, pievieno rindu arī šeit.
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
