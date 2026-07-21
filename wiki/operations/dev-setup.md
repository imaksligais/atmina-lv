# Dev setup

Vienreizējais setup atminā strādājošam darba galdam. Pēc instalācijas — pārejam uz [operacijas.md](operacijas.md) dienas plūsmai.

## Tech stack

- **Python 3.11+** — Windows: `.venv/Scripts/activate`
- **SQLite (WAL mode) + sqlite-vec** — 384-dim embeddings ar `intfloat/multilingual-e5-small`
- **Pydantic v2** — visi `src/models.py` modeļi strikti, `list[dict]` (nevis `list[str]`)
- **Jinja2** — templates atrodas `templates/`
- **httpx + trafilatura + BeautifulSoup4** — ingest pipeline (RSS, web scraper)
- **twikit** — cookie-based X/Twitter klients; **vajag lokālus patches** pēc katras pārinstalācijas (sk. [twikit-notes.md](twikit-notes.md))
- **simplemma** — latviešu lemmatizācija
- **fasttext** — valodas detekcija ingest laikā

## Pirmreizējās instalācijas soļi

```powershell
git clone <repo> atmina
cd atmina
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python scripts/patch_twikit.py             # twikit X-API patches
python -m pytest tests/                    # smoke
```

## Twitter/X autentifikācija

`data/x_cookies.json` (gitignored) — kritiskie lauki: `auth_token` un `ct0`. Kad cookies expire, ekstraktē no DevTools → Application → Cookies (`x.com`/`twitter.com`).

Pool pieņem līdz 6 cookie slotus (`1.json`...`6.json`) ar round-robin caur `XClientPool` (multi-account plāns slēgts 2026-04-30).

## Datu bāzes ceļš

`data/atmina.db` (galvenā SQLite). Pārvaldība — `src/db.py::get_db()`. **Migrācijas:** `src/db.py::init_db()` ir idempotents — palaiž `init_db()` pēc `git pull`, ja pielikušās jaunas tabulas/kolonnas.

## Kritiski rakstītāji

- **Komandas** — sk. [commands.md](commands.md)
- **Twikit patches** — [twikit-notes.md](twikit-notes.md)
- **Routine** — [daily-routine.md](daily-routine.md)
- **Aģenti** — [agenti/](agenti/)

## Vides gotchas (Windows)

- **nanobanana / gemini SDK + salūzis `.venv`:** ja Microsoft Store Python stub vai salūzis venv lauž `google-genai` importu attēlu ģenerēšanā, palaid ar bāzes Python 3.12 + `PYTHONPATH=.venv/Lib/site-packages` (ABI-saderīgs 3.12) un `PYTHONIOENCODING=utf-8`. Gemini key: `data/gemini_key.json`. CLI: `python -m src.graphics.cli {brief,thread}`.
- **Git worktree:** lieto PowerShell + `Set-Location` + `& "…/Git/bin/bash.exe"`, NE Bash-CWD-ķēdi (`cd …` nepersists starp Bash izsaukumiem). Sub-agentiem: controller `cd .worktrees/<branch>` PIRMS dispatch + prompts mandatē `git rev-parse` verifikāciju (CWD mantojas no controllera, ne prompta).
- **Commit ziņas ar LV/em-dash:** raksti ziņu failā un `git commit -F .git-commit-msg.tmp` — PowerShell heredoc lauž parsing uz diakritikām/em-dash.
- **Konsoles Unicode:** Python skriptiem, kas printē LV tekstu, `PYTHONIOENCODING=utf-8` (citādi cp1252 `UnicodeEncodeError`).

## Operatīvās piezīmes

- **Dokumentu deduplikācija** — ingest laikā automātiska (`content_hash` exact + `simhash` near-dupe). Same-day brief overwrite ir atļauts; `context_notes` (note_type='context') ir append-only.
- **Routine status** — `python -c "from src.routine import print_routine; print_routine()"` parāda 10 soļu statusu un cookie slot skaitu.
- **Deploy gates** — `scripts/check.sh` jāiziet pirms `scripts/deploy.sh`.
