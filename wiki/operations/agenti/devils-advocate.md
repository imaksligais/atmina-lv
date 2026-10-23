# @devils-advocate

> Kanoniskais prompts (izpildei): [.claude/agents/devils-advocate.md](../../../.claude/agents/devils-advocate.md) — šī lapa ir īss apraksts cilvēkiem.

Adversariālais verifikators — skeptisks, rigorōzs.

**Ko dara:** Pārskata jaunās pretrunas un claims pirms publikācijas. Uzbrūk vājiem pierādījumiem. Piešķir robustness score: Strong / Medium / Weak / False.

**Kad izmanto:** Dienas rutīnas solī PĒC claim extraction. Obligāts pirms publikācijas.

**Ievade:** Šodienas pretrunas un jaunie claims no DB.

**Izvade:** Robustness novērtējums katrai pretrunai. False pretrunas jādzēš vai jāpazemina.

**Princips:** "Pierādi to." Ja pierādījumi ir vāji, pienākums to pateikt — pat ja sistēma ir pārliecināta.

---
> Pilns aģenta prompts: `.claude/agents/devils-advocate.md`
