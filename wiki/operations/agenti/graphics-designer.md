# @graphics-designer

> Kanoniskais prompts (izpildei): [.claude/agents/graphics-designer.md](../../../.claude/agents/graphics-designer.md) — šī lapa ir īss apraksts cilvēkiem.

Dienas/nedēļas pārskatu featured-image ģenerators ar cilvēka apstiprinājumu.

**Ko dara:** Nolasa `visual_brief_json` no `context_notes` rindas, izvēlas metaforu no `src/graphics/visual_map.py` kandidātiem, salikta nanobanana promptu, ģenerē 16:9 PNG, saglabā kā `approved=0` `brief_images` tabulā. Neaprobo automātiski — operators izlemj.

**Kad izmanto:** Dienas rutīnas 8. solis (pēc `@brief-writer`, pirms `@quality-reviewer`), ja brief satur `## Vizuālais brief` bloku ar aizpildītu tēmu, tēzi un metaforas hint.

**Ievade:** viens parametrs — `note_id` (int), kas atbilst `daily_brief`/`weekly_brief` rindai ar `visual_brief_json` aizpildītu.

**Izvade:**
- `status: pending_approval` + `image_id` + `image_path` — PNG uz diska (`output/images/briefs/`), rinda DB ar `approved=0`
- `status: already_approved` — ja apstiprināts attēls jau eksistē (idempotence)
- `status: failed` — budžets pārsniegts, safety block, vai API kļūda; auditēšanas rinda tiek saglabāta

**Cilvēka-apstiprināšanas plūsma:** operators saņem PNG un atbild `OK` / `noraidi` / `pārģenerē` / `pārģenerē ar <modifikators>`. Funkcijas `approve_image()`, `reject_image()` `src/graphics/storage.py`.

**Nav:** automātiska apstiprināšana, brief satura pārrakstīšana, statistikas izgudrošana, PNG manipulācijas pēc ģenerēšanas.

**Ierobežojumi:**
- Budžeta pārbaude pirms katra API izsaukuma (`budget_check()` — mēneša limits)
- Diakritikas saglabāšana `visual_brief["headline"]` (STRICT TEXT RULE)
- Katra pārģenerēšana = jauna DB rinda (nekad UPDATE/DELETE esošās)
- Modifikatori pievienojami prompta beigās pirms `generate_image()`

---
> Pilns aģenta prompts: `.claude/agents/graphics-designer.md`
> Infrastruktūra: `src/graphics/` (visual_map, prompt, nanobanana, storage, config)
