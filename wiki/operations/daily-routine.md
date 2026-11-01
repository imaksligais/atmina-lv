# Dienas rutīna

Šī lapa ir tikai norāde. Rutīnas soļi te vairs netiek uzturēti, jo divas kopijas dreifēja (2026-08-01 un 2026-10-11 auditi atrada pretrunas ar kanonisko procedūru).

- **Procedūra:** `/dienas-rutina` prasme — [`.claude/commands/dienas-rutina.md`](../../.claude/commands/dienas-rutina.md). Soļi, laika noteikumi, publicēšanas vārti, renders un deploy dzīvo tur.
- **Stāvoklis:** `.venv/Scripts/python.exe -c "from src.routine import print_routine; print_routine()"` (soļu definīcija — `src/routine.py`).
- **Kvalitātes vārti pirms publicēšanas:** [`.claude/agents/quality-reviewer.md`](../../.claude/agents/quality-reviewer.md); pass/fail kritēriji — [quality-bars.md](quality-bars.md).
- **Komandas un atsevišķas plūsmas** (manuāla URL ielāde, Vēstnesis, REGEN): [commands.md](commands.md), [operacijas.md](operacijas.md).

Iepriekšējā garā versija: `git log -- wiki/operations/daily-routine.md`.
