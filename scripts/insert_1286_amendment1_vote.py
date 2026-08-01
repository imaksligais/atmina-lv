"""One-shot manual insert of 14.05.2026 priekšlikums Nr.1 vote on 1286/Lp14.

Source: operator's screenshot (priekšlikuma balsojuma rezultāti from Saeima LIVE
system, not publicly indexed). Provenance: PDF priekšlikumu tabula at
https://titania.saeima.lv/livs14/saeimalivs14.nsf/0/6A761C6C00612794C2258DF6004A0E09/$file/1286_2.pdf

The kopējais 2.lasījuma balsojums at 16:00 is captured separately as vote 196.
This row captures the priekšlikums Nr.1 (Butāns/Vitenbergs valodas amendment)
that Saeima rejected before the bāzes likuma vote.

Idempotent on (vote_date, vote_time, bill_id) — re-run safe.
"""
import sqlite3
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src.matcher import match_politician

DEPUTIES = [
    # PAR (23)
    ('Raimonds Bergmanis', 'AS', 'Par'),
    ('Augusts Brigmanis', 'ZZS', 'Par'),
    ('Artūrs Butāns', 'NA', 'Par'),
    ('Jānis Dombrava', 'NA', 'Par'),
    ('Raivis Dzintars', 'NA', 'Par'),
    ('Ilze Indriksone', 'NA', 'Par'),
    ('Aleksandrs Kiršteins', None, 'Par'),
    ('Jurģis Klotiņš', 'NA', 'Par'),
    ('Līga Kļaviņa', 'ZZS', 'Par'),
    ('Māris Kučinskis', 'AS', 'Par'),
    ('Andris Kulbergs', 'AS', 'Par'),
    ('Lauris Lizbovskis', 'AS', 'Par'),
    ('Ingmārs Līdaka', 'AS', 'Par'),
    ('Uģis Mitrevics', 'NA', 'Par'),
    ('Ināra Mūrniece', 'NA', 'Par'),
    ('Nauris Puntulis', 'NA', 'Par'),
    ('Edgars Putra', 'AS', 'Par'),
    ('Harijs Rokpelnis', 'ZZS', 'Par'),
    ('Andrejs Svilāns', 'AS', 'Par'),
    ('Edvīns Šnore', 'NA', 'Par'),
    ('Edmunds Teirumnieks', 'NA', 'Par'),
    ('Jānis Vitenbergs', 'NA', 'Par'),
    ('Didzis Zemmers', 'ZZS', 'Par'),
    # PRET (22)
    ('Maija Armaņeva', 'LPV', 'Pret'),
    ('Edmunds Cepurītis', 'PRO', 'Pret'),
    ('Svetlana Čulkova', None, 'Pret'),
    ('Jekaterina Drelinga', None, 'Pret'),
    ('Liene Gātere', 'PRO', 'Pret'),
    ('Ilja Ivanovs', None, 'Pret'),
    ('Mārcis Jencītis', 'LPV', 'Pret'),
    ('Igors Judins', None, 'Pret'),
    ('Jefimijs Klementjevs', None, 'Pret'),
    ('Jeļena Kļaviņa', None, 'Pret'),
    ('Dmitrijs Kovaļenko', None, 'Pret'),
    ('Kristaps Krištopans', 'LPV', 'Pret'),
    ('Gunārs Kūtris', 'ZZS', 'Pret'),
    ('Linda Liepiņa', 'LPV', 'Pret'),
    ('Natalja Marčenko-Jodko', None, 'Pret'),
    ('Ramona Petraviča', 'LPV', 'Pret'),
    ('Viktorija Pleškāne', None, 'Pret'),
    ('Amils Saļimovs', None, 'Pret'),
    ('Vilis Sruoģis', None, 'Pret'),
    ('Ričards Šlesers', 'LPV', 'Pret'),
    ('Andris Šuvajevs', 'PRO', 'Pret'),
    ('Edmunds Zivtiņš', 'LPV', 'Pret'),
    # ATTURAS (37)
    ('Skaidrīte Ābrama', None, 'Atturas'),
    ('Česlavs Batņa', 'AS', 'Atturas'),
    ('Inga Bērziņa', 'JV', 'Atturas'),
    ('Andris Bērziņš', 'ZZS', 'Atturas'),
    ('Anita Brakovska', 'ZZS', 'Atturas'),
    ('Kaspars Briškens', 'PRO', 'Atturas'),
    ('Oļegs Burovs', None, 'Atturas'),
    ('Ingrīda Circene', 'JV', 'Atturas'),
    ('Anda Čakša', 'JV', 'Atturas'),
    ('Mārtiņš Daģis', 'JV', 'Atturas'),
    ('Gundars Daudze', 'ZZS', 'Atturas'),
    ('Dāvis Mārtiņš Daugavietis', 'JV', 'Atturas'),
    ('Jānis Dinevičs', 'ZZS', 'Atturas'),
    ('Mārtiņš Felss', 'JV', 'Atturas'),
    ('Alīna Gendele', 'JV', 'Atturas'),
    ('Ligita Gintere', 'ZZS', 'Atturas'),
    ('Juris Jakovins', 'ZZS', 'Atturas'),
    ('Andrejs Judins', 'JV', 'Atturas'),
    ('Zanda Kalniņa-Lukaševica', 'JV', 'Atturas'),
    ('Inese Kalniņa', 'JV', 'Atturas'),
    ('Atis Labucis', 'JV', 'Atturas'),
    ('Ainars Latkovskis', 'JV', 'Atturas'),
    ('Gatis Liepiņš', 'JV', 'Atturas'),
    ('Valdis Maslovskis', 'ZZS', 'Atturas'),
    ('Daiga Mieriņa', 'ZZS', 'Atturas'),
    ('Antoņina Ņenaševa', 'PRO', 'Atturas'),
    ('Jānis Patmalnieks', 'JV', 'Atturas'),
    ('Igors Rajevs', None, 'Atturas'),
    ('Leila Rasima', 'PRO', 'Atturas'),
    ('Uģis Rotbergs', 'JV', 'Atturas'),
    ('Jana Simanovska', 'PRO', 'Atturas'),
    ('Jānis Skrastiņš', 'JV', 'Atturas'),
    ('Zane Skujiņa-Rubene', 'JV', 'Atturas'),
    ('Jānis Vucāns', 'ZZS', 'Atturas'),
    ('Agita Zariņa-Stūre', 'JV', 'Atturas'),
    ('Jānis Zariņš', 'JV', 'Atturas'),
    ('Viesturs Zariņš', 'JV', 'Atturas'),
    # NEBALSO (8)
    ('Uldis Augulis', 'ZZS', 'Nebalsoja'),
    ('Andrejs Ceļapīters', None, 'Nebalsoja'),
    ('Līga Kozlovska', 'ZZS', 'Nebalsoja'),
    ('Agnese Krasta', 'JV', 'Nebalsoja'),
    ('Līga Rasnača', 'PRO', 'Nebalsoja'),
    ('Andris Sprūds', 'PRO', 'Nebalsoja'),
    ('Edgars Tavars', 'AS', 'Nebalsoja'),
    ('Juris Viļums', 'AS', 'Nebalsoja'),
]

# Manual overrides for screenshot vs DB spelling mismatches
MANUAL_OVERRIDES = {
    'Edvīns Šnore': 7,
    'Ilja Ivanovs': 92,
    'Natalja Marčenko-Jodko': 111,
}

SOURCE_URL = (
    'https://titania.saeima.lv/saeimalivs14.nsf/0/'
    '6A761C6C00612794C2258DF6004A0E09?OpenDocument'
)
PDF_URL = (
    'https://titania.saeima.lv/livs14/saeimalivs14.nsf/0/'
    '6A761C6C00612794C2258DF6004A0E09/$file/1286_2.pdf'
)

MOTIF = (
    'Par priekšlikumu Nr.1 (deputāti A.Butāns, J.Vitenbergs) — '
    'Grozījumi Ceļu satiksmes likumā (1286/Lp14), 2.lasījums, steidzams. '
    'Priekšlikums papildināt likuma 4. pantu ar (5)³ daļu: transportlīdzekļu '
    'vadītāju apmācība un eksāmeni notiek valsts valodā; CSDD tiesības '
    'nodrošināt arī ES vai EEZ dalībvalstu oficiālajās valodās. '
    'Komisijas atzinums: Neatbalstīts.'
)

RESULT = 'Noraidīts'


def main():
    assert sum(1 for _, _, v in DEPUTIES if v == 'Par') == 23
    assert sum(1 for _, _, v in DEPUTIES if v == 'Pret') == 22
    assert sum(1 for _, _, v in DEPUTIES if v == 'Atturas') == 37
    assert sum(1 for _, _, v in DEPUTIES if v == 'Nebalsoja') == 8

    db = sqlite3.connect('data/atmina.db')
    db.row_factory = sqlite3.Row
    try:
        existing = db.execute(
            "SELECT id FROM saeima_votes WHERE vote_date=? AND vote_time=? AND bill_id=?",
            ('2026-05-14', '14:54:02', 88),
        ).fetchone()
        if existing:
            print(f"ALREADY EXISTS: vote_id={existing['id']}; nothing to do.")
            return

        cur = db.execute(
            """INSERT INTO saeima_votes
            (motif, vote_date, vote_time, total_par, total_pret, total_atturas, total_nebalso,
             result, url, document_nr, document_url, topic, bill_id, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now', '+3 hours'))""",
            (
                MOTIF, '2026-05-14', '14:54:02',
                23, 22, 37, 8,
                RESULT, SOURCE_URL, '1286/Lp14', PDF_URL, 'Valodu politika', 88,
            ),
        )
        vote_id = cur.lastrowid
        print(f"Inserted saeima_votes id={vote_id}")

        matched = 0
        unmatched_log = []
        for name, faction, vote in DEPUTIES:
            pid = MANUAL_OVERRIDES.get(name) or match_politician(name)
            if pid:
                matched += 1
            else:
                unmatched_log.append(name)
            db.execute(
                """INSERT INTO saeima_individual_votes
                (vote_id, deputy_name, faction, vote, politician_id, created_at)
                VALUES (?, ?, ?, ?, ?, datetime('now', '+3 hours'))""",
                (vote_id, name, faction, vote, pid),
            )
        db.commit()
        print(f"Inserted 90 individual votes; matched={matched}; unmatched={len(unmatched_log)}")
        for n in unmatched_log:
            print('  unmatched:', n)
        print(f"\nNext: run generate_claims_from_votes(vote_id={vote_id})")
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == '__main__':
    main()
