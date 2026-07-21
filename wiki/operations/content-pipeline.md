# Satura pipeline (atmina.lv)

## Direktorija struktūra

`content/` direktorija satur publicētos rakstus un analīzes Markdown ar YAML frontmatter:
- `content/ideology.md` — publiski publicētā platformas ideoloģija
- `content/analizes/` — datu analīzes raksti (piem. `deklaracijas-2026.md`)

## Frontmatter prasības

Visiem satura failiem nepieciešami lauki:
- `title` — raksta nosaukums
- `date` — datums (YYYY-MM-DD)
- `description` — īss apraksts

Analīžu rakstiem papildus:
- `tags` — tēmu saraksts
- `url` — publikācijas ceļš

## Ģenerēšana

Statiskā vietne tiek ģenerēta uz `output/` direktoriju:

```bash
python -c "from src.generate import generate_public_site; generate_public_site()"
```

Templates atrodas `templates/` direktorijā. Stils: `assets/style.css`.
