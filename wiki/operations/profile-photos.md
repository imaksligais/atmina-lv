# Profila bildes (auto-fetch + manuāla plūsma)

atmina.lv politiķu profila avatāru pievienošana, JPEG-konversija un publicēšana.

**Fails:** `assets/photos/<_slugify(name)>.jpg` — **īsts JPEG** (sākas ar `FF D8 FF`), kvadrāts, ≤512 px. Profilu kopa = `tracked_politicians WHERE relationship_type NOT IN ('inactive','commentator')` (render `_fetch_politicians`). Trūkstošos atrod, pārbaudot katra slug `.jpg` eksistenci:

```bash
PYTHONUTF8=1 .venv/Scripts/python.exe -c "import os,sqlite3; from scripts.fetch_profile_photos import _slugify; ex=set(os.listdir('assets/photos')); print([n for (n,) in sqlite3.connect('data/atmina.db').execute(\"SELECT name FROM tracked_politicians WHERE relationship_type NOT IN ('inactive','commentator')\") if _slugify(n)+'.jpg' not in ex])"
```

## Ne-acīmredzamie soļi

1. **Templati lieto failu-URL, NE data-URI.** `politician`/`personas`/`partija`/`pretrunas` `.j2` atsaucas uz `assets/photos/<slug>.jpg`. Jaunai bildei **jāpārrender `politiki`** (visas profila lapas ar `has_photo=True`) — faila iekopēšana vien NEPALĪDZ. Avatāri rādās arī `personas` + `partijas` (+ `pretrunas` kartiņās).
2. **og-card attēli prasa īstu JPEG.** `_common._photo_data_uri()` cieti iekodē `data:image/jpeg`, tāpēc PNG/WebP ar `.jpg` nosaukumu salauž kartīti. Konvertē ar `scripts.fetch_profile_photos._to_jpeg_bytes()` (caurspīdīgums → balts fons). Sargs: `tests/test_profile_photos_jpeg.py` pārbauda visus `assets/photos/*.jpg`.
3. **Auto-fetch X avatārus:**
   ```bash
   .venv/Scripts/python.exe -m scripts.fetch_profile_photos [--dry-run] [--names "Vārds Uzvārds"]
   ```
   Prasa X handle (`x_handle` / `social_accounts`); kopš 2026-10-06 skripts pats pārkodē uz JPEG. Handle-less profili (institūcijas, daži politiķi) = manuāla augšupielāde.
4. **Manuālās bildes (operators ieliek mapē):** faila nosaukums → slug ar `_slugify`; nesakritības (piem. `anita_bike` → Anete Biķe) sasaista ar roku. Apgriež kvadrātā (horizontāli centrā, vertikāli tuvāk augšai), ≤512 px, `_to_jpeg_bytes`. Pirms commit **apskati kontaktlapu** — tālu uzņemtiem portretiem seja apaļajā rāmī ir par mazu, tos apgriež tuvāk ar roku.
5. **Asset-kopēšana NAV `_want`-gated** — `src/render/_orchestrator.py` (~rindas 242–253) `assets/photos/` kopē uz output arī narrow render laikā. Tāpēc šajā mapē neliec iekšējus failus — tie aiziet publiski.

## Publicēšana

```bash
.venv/Scripts/python.exe -m src.render --only=politiki,personas,partijas,pretrunas
bash scripts/deploy.sh
```

Deploy augšupielādē VISU `output/atmina/` koku ([deploy.md](deploy.md)); šaurais renders strādā, jo pārējās lapas paliek kokā no iepriekšējiem renderiem. Pēc deploy Cloudflare jaunos failus var rādīt kā 404 vēl ~1–2 min — pārbaudi vēlreiz, nevis deployo atkārtoti.

**Piemēri:** 2026-05-30 — 17 auto-fetch + 2 manuāli → 0 trūkst no 176. 2026-10-05 — 15. Saeimas kohorta: 59 manuāli + 1 X (Latvijas Banka) → 0 trūkst no 252.
