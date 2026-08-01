# @outlet-researcher

> Kanoniskais prompts (izpildei): [.claude/agents/outlet-researcher.md](../../../.claude/agents/outlet-researcher.md) — šī lapa ir īss apraksts cilvēkiem.

Mediju caurskatāmības profilu pētnieks — pēc pieprasījuma, viens medijs reizē.

**Ko dara:** Izpēta VIENA Latvijas medija caurskatāmības faktus un piedāvā avototu
`sources.yaml` `outlets:` ierakstu cilvēka pārskatīšanai. NERAKSTA datubāzē un
NESTRĀDĀ neuzraudzīti — cilvēks pārskata YAML diff git vēsturē pirms commit
(labāka provenience nekā DB rindas).

**Kad izmanto:** Pēc pieprasījuma, kad jāaizpilda vai jāatjaunina kāda medija
`facts:` mediji lapām (`/mediji`). Tas ir analīzes dzinēja darbs interaktīvā
sarunā, nevis automatizēta rutīna. Īpašumtiesību maiņas ir retas → palaiž
atkārtoti pēc vajadzības; git vēsture ir izmaiņu žurnāls.

**Ievade:** Medija nosaukums, mājaslapa un (ja zināms) X handle.

**Izvade:** YAML bloks ar `facts:` ierakstiem — pa vienam katram avototam laukam:
`owner`, `funding_model`, `legal_form`, `editorial_leadership`, `founded`. Katram
faktam savs `source_url` + `as_of`. Beigās — kopsavilkums par laukiem, ko NEIZDEVĀS
avotēt, lai cilvēks zina robus.

**Stingrie noteikumi:**
- **Tikai šie pieci lauki** un vieni un tie paši lauki KATRAM medijam neatkarīgi no
  uztvertās politiskās nostājas — simetrija ir visa jēga (caurskatāmība, ne mērķēšana).
- **Neitrāla, aprakstoša valoda.** Nekādu pārklājuma kvalitātes, tendences vai
  motīvu raksturojumu — tas ir aprēķinātā pārklājuma sadaļas (computed coverage)
  uzdevums, ne pētnieka.
- **Katram faktam vajadzīgs `source_url`.** Ja lauku nevar avotēt — IZLAIŽ to (nemini).
  Atspoguļo platformas "nav claim bez source_url" likumu (CLAUDE.md Data Contract #2);
  `src/outlets.py` nomet jebkuru faktu bez `source_url` (vai bez `value`) lasīšanas laikā.
- **Avoti:** komercreģistrs (ur.gov.lv, Lursoft, Firmas.lv) īpašumtiesībām un
  juridiskajai formai; sabiedriskajiem medijiem — pārvaldības likums/iestāde (piem.,
  SEPLP). `as_of` = šodienas datums.

**Robeža pret `framing:`** Editorial `framing:` lauks (uz `sources:` feed rindām) ir
INTERNS `@claim-extractor` confidence signāls — to NEPUBLICĒ mediji lapās. Šis aģents
to neaiztiek. Sk. [[operations/source-framing|source-framing]].

---
> Pilns aģenta prompts: `.claude/agents/outlet-researcher.md`
> Spec/plāns: `docs/superpowers/{specs,plans}/2026-06-01-media-outlet-profiles*`
