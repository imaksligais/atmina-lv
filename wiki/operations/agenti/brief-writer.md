# @brief-writer

> Kanoniskais prompts (izpildei): [.claude/agents/brief-writer.md](../../../.claude/agents/brief-writer.md) — šī lapa ir īss apraksts cilvēkiem.

Neitrāls dienas/nedēļas pārskatu ģenerētājs.

**Ko dara:** Raksta faktisku politisko pārskatu no DB datiem — kopsavilkums, aktīvākie politiķi, galvenās tēmas, koalīcija vs opozīcija. Tonis kā Reuters ziņu aģentūra.

**Kad izmanto:** Dienas rutīnas solī pēc pozīciju analīzes un pretrunu pārbaudes.

**Ievade:** `generate_daily_brief()` skelets + tiešie SQL vaicājumi.

**Izvade:** Markdown pārskats → `store_context_note(note_type="daily_brief")` → parādās blogā un sākumlapā.

**Obligātas sekcijas:** Galvenais, Aktīvākie politiķi, Galvenās tēmas (ar context box), Koalīcija vs Opozīcija.

**Nav:** rekomendācijas, partiju perspektīva, uzbrukuma leņķi, subjektīvi īpašības vārdi.

---
> Pilns aģenta prompts: `.claude/agents/brief-writer.md`
