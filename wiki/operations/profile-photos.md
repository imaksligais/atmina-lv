# Profila bildes (auto-fetch + manuāla plūsma)

atmina.lv politiķu profila avatāru pievienošana, JPEG-konversija un publicēšana.

**Fails:** `assets/photos/<_slugify(name)>.jpg`. Profilu kopa = `tracked_politicians WHERE relationship_type NOT IN ('inactive','commentator')` (render `_fetch_politicians`). Trūkstošos atrod, pārbaudot katra slug `.jpg` eksistenci (paraugs `.tmp/find_missing_photos.py`; manuālais `_trukst.md` tracking fails mēdz novecot).

## Ne-acīmredzamie soļi

1. **Templati lieto failu-URL, NE data-URI.** `politician`/`personas`/`partija`/`pretrunas` `.j2` atsaucas uz `assets/photos/<slug>.jpg`. Jaunai bildei **jāpārrender `politiki`** (visas profila lapas ar `has_photo=True`) — faila iekopēšana vien NEPALĪDZ. Avatāri rādās arī `personas` + `partijas` (+ `pretrunas` kartiņās).
2. **og-card attēli prasa īstu JPEG.** `_common._photo_data_uri()` cieti iekodē `data:image/jpeg`, tāpēc avota PNG **jākonvertē uz īstu JPEG** (Pillow venv'ā; paraugs `.tmp/png_to_avatar.py`, cap 512 px, drop alpha).
3. **Auto-fetch X avatārus:**
   ```bash
   PYTHONPATH=.venv/Lib/site-packages py -3.12 -m scripts.fetch_profile_photos [--dry-run]
   ```
   Prasa X handle (`x_handle` / `social_accounts`). Handle-less profili (institūcijas, daži politiķi) = manuāla augšupielāde.
4. **Asset-kopēšana NAV `_want`-gated** — orchestratorā (~rindas 214–224) `assets/photos/` kopēšana uz output notiek arī narrow render laikā.

## Publicēšana

```bash
py -3.12 -m src.render --only=politiki,personas,partijas
bash scripts/deploy.sh --no-delete
```

Aditīvs deploy (sk. [Komandas](commands.md) — `--only` scope + `--no-delete`).

**Piemērs (2026-05-30):** 17 auto-fetch + 2 manuāli (Bartaševičs / Tutins) → 0 trūkst no 176.
