from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from src.db import get_db

changes = {
    704273: (
        'Žuravļeva paša tvīts (ne RT): izsaka nostāju pret indiešu imigrāciju Latvijā un viņu tradīciju ieviešanu, paužot bažas, ka latviskā vide sarūk. Pozīcija par imigrāciju un kultūras integrāciju; kvalifikatori ("jau", "daudz par daudz", "latviskā Latvijā paliek mazāk") saglabāti.',
        'Žuravļeva paša ieraksts, nevis pārpublicēts cita autora teksts: izsaka nostāju pret indiešu imigrāciju Latvijā un viņu tradīciju ieviešanu, paužot bažas, ka latviskā vide sarūk. Pozīcija par imigrāciju un kultūras integrāciju; kvalifikatori ("jau", "daudz par daudz", "latviskā Latvijā paliek mazāk") saglabāti.',
    ),
    704274: (
        'NEEDS_REVIEW: Latvijas Bankas ekonomiste Ludmila Fadejeva LSM rakstā par nabadzību Latvijā kā vienu no ienākumu nevienlīdzības risinājumiem min mērķētāku atbalsta politiku, lai atbalstu saņemtu patiešām tie, kuriem ir mazāk iespēju. Teikums par mērķētāku atbalstu ir žurnālista atstāsts uzreiz pēc viņas citāta, tāpēc citāts nav verbatīms un pārliecība pazemināta. Raksta statistika un pārējo intervēto stāsti nav iestādes nostāja.',
        'NEEDS_REVIEW: Latvijas Bankas ekonomiste Ludmila Fadejeva LSM rakstā par nabadzību Latvijā kā vienu no ienākumu nevienlīdzības risinājumiem min mērķētāku atbalsta politiku, lai atbalstu saņemtu patiešām tie, kuriem ir mazāk iespēju. Teikums par mērķētāku atbalstu ir žurnālista atstāsts uzreiz pēc viņas citāta, tāpēc burtisks citāts nav saglabāts un pārliecība pazemināta. Raksta statistika un pārējo intervēto stāsti nav iestādes nostāja.',
    ),
    704275: (
        'Delfi TV raidījuma «Kāpēc» video raksta apraksts (1014 zīmes, virs stuba sliekšņa): NBS komandieris ģenerālleitnants Pudāns runā amata lomā iestādes vārdā par sava dienesta darbu pie dronu novirzīšanas risinājumiem — iestādes balss ar vērtējumu (2026-08-09 klases tests izpildīts). Saglabāti kvalifikatori: «vēl jāvērtē, vai un kā vadību zaudējušu dronu būtu iespējams ietekmēt» un «tālākas nākotnes jautājums»; apņemšanās elements ir darbs pie risinājumiem un pārliecība par spēju iegūšanu, ne konkrēts instruments ar termiņu. Tēma pēc instrumenta: pretdronu spējas — bez vārda «drons» izteikums sabrūk.',
        'Delfi TV raidījuma «Kāpēc» rakstā NBS komandieris ģenerālleitnants Kaspars Pudāns amata lomā runā par dienesta darbu pie dronu novirzīšanas risinājumiem. Saglabāti būtiskie ierobežojumi: vēl jāvērtē, vai un kā būtu iespējams ietekmēt vadību zaudējušu dronu, un vajadzīgās spējas raksturotas kā tālākas nākotnes jautājums. Konkrētais darbs attiecas uz mērķētu dronu novirzīšanas risinājumiem, nevis jau ieviestu spēju ar noteiktu termiņu.',
    ),
}
with get_db() as db:
    for claim_id, (old, new) in changes.items():
        row = db.execute("SELECT reasoning FROM claims WHERE id = ?", (claim_id,)).fetchone()
        if row is None or row["reasoning"] != old:
            raise SystemExit(f"Unexpected pre-image for {claim_id}")
        db.execute("UPDATE claims SET reasoning = ? WHERE id = ?", (new, claim_id))
    db.commit()
print("updated=3")
