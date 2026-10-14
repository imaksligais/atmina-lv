# claim-extractor — `stated_at` un dublikāti

Lasi pirms katras glabāšanas. Kodols: `.claude/agents/claim-extractor.md`.

## ±5 dienu dublikātu pārbaude (pastāvīgs solis)

Pirms glabāšanas izsauc `get_existing_claims(pid, stated_around=<raksta datums>)` (logs pēc `stated_at` ±5 d) un salīdzini pēc SATURA. Ja tas pats izteikums šim pid jau ir glabāts no cita avota (aģentūras pārstāsts, tas pats tvīts citā medijā, tā pati diena citā URL), dublikātu **neglabā** un piemin atskaitē. `store_claim()` idempotence to nenoķer, jo `source_url` atšķiras. Glabā pirmavotu (paša tvītu vai pilnāko tekstu), ne pārstāstu.

Drošības tīkls pēc glabāšanas: `failures` ieraksts `possible_duplicate` (`claim_id`, `similar_claim_id`, `distance`). Claim jau ir glabāts. Izlasi abus un atskaitē nosauc: dublikāts (dzēšanu ierosini operatoram ar rollback) vai atšķirīga nostāja (atstāj abus).

## `stated_at`

1. **Notikuma Latvijas kalendārā diena.** Tvītu `published_at` ir UTC: pēc 21:00 UTC vasarā (22:00 ziemā) LV datums jau ir nākamā diena. `2026-08-23T21:44 UTC` → `stated_at='2026-08-24'`.
2. **Ja izteikuma īstā diena ir ārpus 7 dienu loga, `stated_at` = publiskošanas diena**, bet īsto datumu pasaki `stance` tekstā («30. jūlijā datētā vēstulē …»). Iemesls: dienas pārskats ņem tikai claims, kuru `stated_at` nav vecāks par 7 dienām (`src/briefs.py::_BRIEF_DAY_CLAIM_SQL`). Tas attiecas uz vēstulēm, atbildēm uz deputātu jautājumiem, arhīva runām. Ja īstā diena ir logā — raksti to.
3. **Kulberga dienasgrāmata («Diena Nr. N premjera krēslā»):** datums no iekavām («(PIEKTDIENA 18.Sept)»), ja tas ir 7 dienu logā; citādi publicēšanas diena + datums stance tekstā. Numuru datuma aprēķinam neizmanto (numuri atkārtojas un iet ne pēc kārtas). Ja datuma iekavās nav — publicēšanas diena, un stance sāc ar «Dienasgrāmatas ierakstā Nr. N …».

Vēsturiskās rindas šie noteikumi NEbīda.
