# 3. līmeņa meklējums — protokols izpildītājam (viens saraksts uz aģentu)

Konteksts: Partiju tests (`docs/plans/2026-09-17-partiju-tests-handoff.md`, `docs/plans/2026-09-14-partiju-tests-v1-godigums.md` § 3.1). Tavs uzdevums: vienam sarakstam katrai `klusē` šūnai (fails `_brief_<SN>.txt` blakus) atrast saraksta LĪDERA 2026. gada publisku izteikumu, kas apgalvojumu adresē bez interpretācijas.

## Noteikumi (obligāti)
1. Vide: Windows, bash; `.venv/Scripts/python.exe` (repo sakne); ceļi pēdiņās. DB TIKAI lasīšanai: `sqlite3.connect('file:data/atmina.db?mode=ro', uri=True)`. Neko nerakstīt DB, `kodejums.json`, git. Neko neingestēt.
2. Avoti prioritātē: (a) DB `documents` ar `document_politicians.politician_id = <lideris_id>` (`role='subject'` vispirms, tad `mentioned`), `COALESCE(published_at, scraped_at) >= '2026-01-01'` — lasi `content`, `source_url`, `published_at`, `platform`; (b) partijas oficiālā mājaslapa (ziņas, intervijas, `majaslapa` no brīfa) caur WebFetch; (c) WebSearch pēc `"<vārds>" <tēmas atslēgvārdi> 2026` — tikai mediju raksti ar konkrētu citātu, kas piedēvēts līderim.
3. Der TIKAI: runātājs = līderis pats (ne partija, ne cits deputāts), datums 2026. gadā, konkrēts URL, verbatim citāts (nesaīsināts, oriģinālvalodā; ne pārstāsts). Bez citāta ieteikuma NAV — raksti „nav atrasts”.
4. Nostāja `par`/`pret` tikai tad, ja citāts to nolasa tieši pēc brīfa `piekrit_nozime`. Ja izteikums ir PRETRUNĀ CVK programmas tekstam (brīfa piezīme saka, ko CVK saka) → ieteikums `klusē` + piezīme ar abiem faktiem. Izteikums nekad nepārraksta programmu.
5. Katram jautājumam vienu labāko kandidātu + līdz 2 rezerves. Ziņo saucēju: cik DB dokumentus izlasīji, cik tīmekļa lapas atvēri.
6. Pagaidu skripti TIKAI savā apakšmapē `scratchpad/<SN>/` — kopīgi nosaukumi (`q.py`) paralēlajiem aģentiem sadūrās 2026-09-17.
7. Latviešu valoda tavos vārdos (piezīmes, kāpēc) — gramatika + stils pārbaudīts; citāts verbatim, arī ar kļūdām.

## Izvade
Raksti TIKAI failu `content/partiju-tests/l3/<SN>.md` (SN = saraksta kods). Formāts:

```
# <SN> — 3. līmenis, <līdera vārds> (id N), meklēts 2026-09-17

Saucējs: DB dokumenti izlasīti N (subject A, mentioned B); tīmekļa lapas M; WebSearch vaicājumi K.

## q01
- ieteikums: par | pret | klusē | nav atrasts
- līmenis: izteikums
- runatajs: <vārds> (id N)
- datums: YYYY-MM-DD
- url: <konkrēts URL>
- document_id: <ja no DB, citādi "nav DB — ingest kandidāts">
- citats: "<verbatim>"
- kāpēc: <1–2 teikumi: kā citāts nolasa apgalvojumu; vai saskan ar CVK piezīmi>
- rezerves: <līdz 2, tāds pats formāts saīsināti, vai "nav">
```

Beigās sadaļa `## Kopsavilkums`: tabula `jautājums / ieteikums / avota tips / document_id vai "ingest"`, un saraksts ar URL, kas nav DB (ingest kandidāti operatoram).
