# KNAB politiskā finansējuma dati

KNAB scraper ielādē ziedojumus un deklarācijas no info.knab.gov.lv.

## Komandas

```bash
# Pilna atjaunināšana (pirmā reize ~30 min, inkrementāli ~5 min)
python -c "from src.knab import fetch_all; fetch_all()"

# Vaicājumu palīgi
python -c "from src.knab import get_party_summary; import json; print(json.dumps(get_party_summary(), indent=2, ensure_ascii=False))"
python -c "from src.knab import get_top_donors; import json; print(json.dumps(get_top_donors(10), indent=2, ensure_ascii=False))"
python -c "from src.knab import get_alerts; import json; print(json.dumps(get_alerts(severity='critical'), indent=2, ensure_ascii=False))"

# Tikai cross-reference pārbaudes (bez ielādes)
python -c "from src.knab_analyze import run_all_checks; run_all_checks()"
```

## Tabulas

| Tabula | Apraksts |
|--------|----------|
| `knab_donors` | Unikālas personas (saistītas ar tracked_politicians pēc vārda) |
| `knab_donations` | Visi individuālie ziedojumi (~73K ieraksti) |
| `knab_declarations` | Gada pārskati izsekotajām partijām |
| `knab_alerts` | Konstatētas anomālijas |

## Anomāliju tipi

| Tips | Apraksts |
|------|----------|
| `multi_party_donor` | Persona ziedo 2+ partijām |
| `family_cluster` | Viens uzvārds, viena partija, vairāki ziedotāji |
| `limit_violation` | Gada limits partijā pārsniegts |
| `declaration_mismatch` | KNAB ziedojumu summa vs deklarētie ienākumi >10% atšķirība |
