# Ingest Log

_Hronoloģisks žurnāls — katrs dokuments, kad apstrādāts, no kura avota._

Žurnāls rotē reizi mēnesī. Raksti dzīvo `wiki/log-ingest/<YYYY-MM>.md` failos; `append_ingest_entry()` un `append_ingest_batch_summary()` (src/ingest_log.py) automātiski raksta aktīvā mēneša failā.

## Mēneši

- [[log-ingest/2026-04|2026. gada aprīlis]]

## Lasīšana

```python
from src.ingest_log import read_ingest_log
# Jaunākie 10 ieraksti pāri visiem mēneša failiem (newest first):
print("\n".join(read_ingest_log(last_n=10)))
```

`read_ingest_log()` noklusēti lasa no `wiki/log-ingest/` direktorijas, iet caur mēneša failiem no jaunākā uz vecāko, un apkopo ierakstus līdz `last_n` ir sasniegts.

## Vēsturiski

Pirms 2026-04-21 visi ingest ieraksti dzīvoja šajā failā kā append-only log (297 rindas). Migrācijas laikā saturs tika pārdalīts mēneša failos — tagad šis fails ir indekss. Rotācijas iemesls: audit log faili aug monotoni un bez rotācijas kļūst grūti navigējami.
