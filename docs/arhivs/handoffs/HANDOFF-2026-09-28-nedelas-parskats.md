# Handoff 2026-09-28 — nedēļas pārskats 21.–27.09. publicēts

**Stāvoklis:** pārskats #653 + attēls #349 live (deploy `0a82b572`, `verify_host` 9/9, varianti 4/4 → 200, `/pretrunas/53.html` 200). Iepriekšējais handoff: `docs/HANDOFF-2026-09-27-15-saeima.md` (atvērtie punkti tur paliek spēkā).

## Izdarīts
- Nedēļas skelets: `weekly_vote_breakdown()`, īsa pretrunu šūna, pagājušās nedēļas «Skats uz priekšu» (`4bbf92ff`, CHANGELOG 2026-09-27 (2)).
- QR divas kārtas; labojumi + rollback `data/rollback_weekly_653_2026-09-28.sql`.
- T6 amati (Jurēvics, Vīksna, A. Bērziņš, Batņa) + doc 95002 Rinkēvičs → `mentioned` (`8a57f192`, rollback).
- Vietnes sīkumi (`2b27bd1e`): priekšskatījuma saites, «aktīvi politiķi» 171 → 149, atskaite pārlūkā, «Jauns» kontrasts, «None» noplūdes + vārti.

## Otrais deploy (`efcab01d`, 9/9)
- Operatora lēmumi izpildīti: amati Siliņa/Ašeradens/Lībiņa-Egnere (→ deputāta profils), Viļums, Liepiņa (`f717ba9b`); viena pretrunu vārdnīca, «/ 7d» = 7 dienas, atskaite → partijas.html, «ārpusfrakciju» balsojumu lapā (`a110178b`, CHANGELOG 2026-09-28 (2)).
- Backlogā: amatu pārskatīšana pēc 15. Saeimas (`backlog/dati-db.md`), dienas pretrunu šūna (`backlog/vietne-ui.md`).

## Gaida operatoru
- `focus.py` («Karstā tēma», top pozīcijas) joprojām 8 dienu logs; `contradictions.py:189`, `news.py:172` lieto `date.today()`, ne LV laiku.
- Pretrunas #29 saglabātajā kopsavilkumā «Apvērsuma tendence» (3 lapas) — pārrakstīt vai atstāt.
- Balsojumu kartītes čips nedalītai frakcijai rāda kopskaitu zem vairākuma etiķetes (19 atturas + 1 nebalsoja → «20 atturas»).
- Nākamais nedēļas pārskats (28.09.–04.10.) aptver vēlēšanu dienu: 3.10. sociālos postus nepublicē; rezultāti tikai pēc CVK.
- Pārskatā #653 `## Kas kustējās` trūkst iemesla teikuma (izgriezts QR vārdu limita dēļ) — nav precedents; nākamnedēļ saglabā.

## 2026-09-28 pēcpusdiena
- Sociālie melnraksti nedēļai (X, FB, Reddit) — `0c60b2ef`, nepostēti. Partiju testu operators pagaidām nevirza.
- Saeimas posmu klasifikators + 5 rindas (CHANGELOG 2026-09-28 (3)); #770 → `backlog/saeima.md`. Ceturtdien 01.10. sēde + atbildes uz jautājumiem (kalendārs pārbaudīts) — pirmā dzīvā pārbaude jaunajam klasifikatoram.
- 09-27 handoff datu sīkumi pārbaudīti, **neko nemainīju**: #724919 Braže — avots airēšanas dienu nenosauc (published 25.09. 21:16 UTC = 26.09. LV), `stated_at` paliek; #718013 Kučinskis — burtiskais citāts doc 114519 sedz tikai blakus elementu (nodokļi), ne pozīcijas kodolu; #718005 Abu Meri — burtisks citāts ir CITĀ dokumentā (nra.lv 117622), `quote` pozīcijai ar pmo.ee avotu to likt nedrīkst; ja vajag, jauna pozīcija no 117622 (0 pozīciju tur šobrīd); #718085/#718086 Smiltēns — divi atsevišķi tvīti, otrs pievieno memorandu — ne dublikāts; #615866/#718100 Baško — divi izteikumi ar 7 nedēļu starpību (likuma atcelšana vs valsts finansējums) — ne dublikāts.

