"""Pārbauda visus gadus uz NĪ ārpus Latvijas vai ar tukšu atrašanās lauku.

Mērķis — apstiprināt vai noliegt analīzes apgalvojumu '0 deklarētu īpašumu
ārvalstīs'. Iet cauri visam vad_real_estate datu kopumam (2002-2025), grupē
location pēc šablona Latvija/cita/tukšs un ziņo skaitļus + politiķu sarakstu.
"""
import sqlite3
import sys

DB_PATH = "data/atmina.db"


def main():
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row

    print("=== NĪ atrašanās lauka klasifikācija ===\n")

    # Tukšs lauks
    n_null = con.execute("""
        SELECT COUNT(*) FROM vad_real_estate vre
        JOIN vad_declarations vd ON vd.id = vre.declaration_id
        JOIN tracked_politicians tp ON tp.id = vd.opponent_id
        WHERE tp.relationship_type != 'inactive'
          AND (vre.location IS NULL OR vre.location = '')
    """).fetchone()[0]
    print(f"Tukšs vai NULL location: {n_null} ieraksti")

    # Sākas ar 'Latvija,'
    n_lv = con.execute("""
        SELECT COUNT(*) FROM vad_real_estate vre
        JOIN vad_declarations vd ON vd.id = vre.declaration_id
        JOIN tracked_politicians tp ON tp.id = vd.opponent_id
        WHERE tp.relationship_type != 'inactive'
          AND vre.location LIKE 'Latvija,%'
    """).fetchone()[0]
    print(f"Sākas ar 'Latvija,': {n_lv} ieraksti")

    # Visi citi
    n_other = con.execute("""
        SELECT COUNT(*) FROM vad_real_estate vre
        JOIN vad_declarations vd ON vd.id = vre.declaration_id
        JOIN tracked_politicians tp ON tp.id = vd.opponent_id
        WHERE tp.relationship_type != 'inactive'
          AND vre.location IS NOT NULL
          AND vre.location != ''
          AND vre.location NOT LIKE 'Latvija,%'
    """).fetchone()[0]
    print(f"Citi (potenciālas ārvalstis vai citā formātā): {n_other} ieraksti")

    print()
    print("=== Citi (NOT 'Latvija,...' un ne tukši) ===\n")
    rows = list(con.execute("""
        SELECT vre.location, vre.property_type, vd.declaration_year,
               GROUP_CONCAT(DISTINCT tp.name) AS politiķi,
               COUNT(*) AS n
        FROM vad_real_estate vre
        JOIN vad_declarations vd ON vd.id = vre.declaration_id
        JOIN tracked_politicians tp ON tp.id = vd.opponent_id
        WHERE tp.relationship_type != 'inactive'
          AND vre.location IS NOT NULL
          AND vre.location != ''
          AND vre.location NOT LIKE 'Latvija,%'
        GROUP BY vre.location, vre.property_type
        ORDER BY n DESC
    """))
    if not rows:
        print("Nav atrastas — visi NĪ ar definētu location ir Latvijā.\n")
    else:
        print(f"Atrasts: {len(rows)} unikāli (location, tipa) kombinācijas:\n")
        for r in rows:
            print(f"  [{r['n']}× {r['property_type']!s:<20}] '{r['location']!s}'")
            print(f"    politiķi: {r['politiķi']}")
        print()

    print("=== Tukšu / NULL location ieraksti pa politiķim (ja ir) ===\n")
    rows = list(con.execute("""
        SELECT tp.name, vd.declaration_year, COUNT(*) AS n
        FROM vad_real_estate vre
        JOIN vad_declarations vd ON vd.id = vre.declaration_id
        JOIN tracked_politicians tp ON tp.id = vd.opponent_id
        WHERE tp.relationship_type != 'inactive'
          AND (vre.location IS NULL OR vre.location = '')
        GROUP BY tp.id, vd.declaration_year
        ORDER BY tp.name, vd.declaration_year
    """))
    if not rows:
        print("Nav atrastas — visiem NĪ ierakstiem ir definēta atrašanās.\n")
    else:
        print(f"Atrasti: {len(rows)} grupas (politiķis, gads):\n")
        for r in rows:
            print(f"  {r['name']:<30} y={r['declaration_year']!s:<6}  {r['n']} ieraksti bez atrašanās")
        print()

    print("=== Apstiprinājums ===\n")
    foreign_count = n_other + n_null
    if foreign_count == 0:
        print("✓ Apgalvojums '0 deklarētu īpašumu ārvalstīs' apstiprinās: visi NĪ Latvijā.")
        return 0
    else:
        print(f"✗ Apgalvojums NEapstiprinās: {n_other} ieraksti citās valstīs/formātos + {n_null} tukši.")
        print("  § 6 jāatjaunina ar reāliem skaitļiem.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
