# @quality-reviewer

> Kanoniskais prompts (izpildei): [.claude/agents/quality-reviewer.md](../../../.claude/agents/quality-reviewer.md) — šī lapa ir īss apraksts cilvēkiem.

Galīgais kvalitātes vārtnieks pirms publikācijas.

**Ko dara:** Pārbauda datu integritāti, avotu saites, pilnību un neitralitāti. Seko kontrolsarakstiem, ne intuīcijai.

**Kad izmanto:** Pirms jebkuras publikācijas — dienas pārskats, nedēļas pārskats, analīzes.

**Pārbauda:**
- Vai visi skaitļi sakrīt ar DB?
- Vai visām pozīcijām ir source_url?
- Vai pretrunas ir korektas (nav viltus)?
- Vai tonis ir neitrāls (nav editoriālisma)?
- Vai formāts atbilst prasībām?

**Diena = rutīnas diena (kopš 2026-09-25).** `ROUTINE_DAY` pēc noklusējuma ir `src.briefs.current_routine_day()` (līdz 05:00 — vakardiena), un dienas vaicājumi lieto `routine_day_window()`, tāpēc pēc pusnakts ierakstītās rindas vairs neizkrīt. Iepriekšējas dienas pārbaudei iestati `ROUTINE_DAY = "YYYY-MM-DD"` ar roku.

---
> Pilns aģenta prompts: `.claude/agents/quality-reviewer.md`
