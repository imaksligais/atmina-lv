"""One-shot grammar/stylistic fixes for 5 saeima_votes summaries + bill 88
after grammar review of 2026-05-16 backfill session.

Applies these corrections (alongside corresponding claim stance regen):

- vote 195: factual fix — "(2. lasījums)" → "3. lasījums" (motif says 3.lasījums)
- vote 196: drop "deputātu" before "21 priekšlikums" (21 takes nom.sg.), replace
            anglicism "amendment" with "priekšlikums"
- vote 197: replace anglicism "amendment" with "grozījums", fix "iebaks" →
            "iekļauts" (proper LV form)
- vote 178: "nekonsultēto lēmumu" → "neapspriesto lēmumu" (more natural LV),
            "pašas frakcijas ministrei" → "savas frakcijas ministrei"
- vote 188: rephrase "pēc pielaides valsts noslēpumam atteikuma" → "pēc atteikuma
            izsniegt pielaidi valsts noslēpumam" (clearer)
- bill 88:  "izskatīti 21 priekšlikumi" → "izskatīts 21 priekšlikums" (21 = nom.sg.)

After updating saeima_votes.summary + saeima_bills.summary, regenerates the
'<prefix>: <summary>' claim.stance for all saeima_vote claims linked to these
votes via source_url (mirrors generate_claims_from_votes lines 462-473).

Idempotent — safe to re-run; only writes when content changes.
"""
import sqlite3

FIXES = {
    195: (
        'Grozījumi Operatīvās darbības likumā 3. lasījumā vienprātīgi pieņemti (93/0/0). '
        'Precizē operatīvās darbības subjektu pilnvaras un šīs darbības uzraudzības kārtību.'
    ),
    196: (
        'Grozījumu Ceļu satiksmes likumā 2. lasījums (steidzams) — vienprātīgi pieņemts (83/0/0). '
        'Aktualizē militārās tehnikas, militārā transportlīdzekļa un militārā transportlīdzekļa '
        'piekabes definīcijas; izskatīts 21 priekšlikums. Priekšlikums Nr.1 (Butāna/Vitenberga '
        'priekšlikums par autovadītāju apmācību tikai latviešu un ES/EEZ valodās) — balsots '
        'atsevišķi pirms tam un noraidīts (sk. balsojumu 14:54).'
    ),
    197: (
        'Priekšlikums Nr.1 Grozījumiem Ceļu satiksmes likumā (1286/Lp14) — deputātu A.Butāna '
        'un J.Vitenberga (NA) ierosinājums: transportlīdzekļu vadītāju apmācība un eksāmeni '
        'notiek valsts valodā; CSDD drīkst piedāvāt arī ES vai EEZ dalībvalstu oficiālajās '
        'valodās. Praktiski izslēgtu krievu valodu (kas nav ES/EEZ valoda). Komisija '
        '(vad. K.Briškens, PRO) neatbalstīja; Saeima noraidīja (par 23, pret 22, atturas 37). '
        'Valodas politikas grozījums, iekļauts militārās tehnikas grozījumu likumprojektā.'
    ),
    178: (
        'NA frakcijas (J.Vitenbergs, A.Butāns, U.Mitrevics u.c., 10 deputāti) pieprasījums '
        'izglītības un zinātnes ministrei D.Melbārdei (NA — savas frakcijas ministrei) par '
        'MK rīkojuma projektu Nr. 26-TA-109 — IZM plāno pārdot Latvijas Sporta muzeja ēku '
        'Vecrīgā, Alksnāja ielā 9, lai segtu IZM budžeta iztrūkumu, paredzot muzeja '
        'pārcelšanu uz komandu sporta spēļu zāli un saglabājot esošās telpas vēl 3 gadus. '
        'NA iebilst pret neapspriesto lēmumu un ēkas pārdošanas vajadzību. Saeima '
        'pieprasījumu noraidīja (30/41/1).'
    ),
    188: (
        'LPV (Pleškāne, Zivtiņš, Armaņeva, Liepiņa, Krištopans u.c., 10 deputāti) '
        'pieprasījums viedās administrācijas un reģionālās attīstības ministram R.Čudaram '
        '(JV) par otra domes priekšsēdētāja ievēlēšanu Rēzeknes valstspilsētas domē — '
        'saistībā ar februārī notikušo iepriekšējā mēra A.Bartaševiča (Kopā Latvijai) '
        'atstādināšanu pēc atteikuma izsniegt pielaidi valsts noslēpumam un 10.04.2026 '
        'ievēlēto jauno mēru J.Tutinu (Kopā Latvijai). Saeima pieprasījumu noraidīja '
        '(10/47/9).'
    ),
}

BILL_88_FIX = (
    'Grozījumi Ceļu satiksmes likumā: aktualizē militārās tehnikas un militārā '
    'transportlīdzekļa definīcijas (1. lasījums 16.04, 2. lasījums steidzams 14.05). '
    '2.lasījumā izskatīts 21 priekšlikums; priekšlikums Nr.1 (Butāns/Vitenbergs NA — '
    'autovadītāju apmācība valsts valodā + ES/EEZ valodās) noraidīts pirms bāzes likuma '
    'vienprātīgas pieņemšanas (83-0-0).'
)

PREFIX = {
    'Par': 'Atbalsta',
    'Pret': 'Iebilst pret',
    'Atturas': 'Atturējās balsojumā par',
    'Nebalsoja': 'Nebalsoja par',
}


def main():
    db = sqlite3.connect('data/atmina.db')
    db.row_factory = sqlite3.Row
    try:
        for vote_id, new_summary in FIXES.items():
            db.execute(
                "UPDATE saeima_votes SET summary = ? WHERE id = ?",
                (new_summary, vote_id),
            )
            print(f"vote {vote_id}: summary fixed ({len(new_summary)} chars)")
        db.execute("UPDATE saeima_bills SET summary = ? WHERE id = 88", (BILL_88_FIX,))
        print(f"bill 88: summary fixed ({len(BILL_88_FIX)} chars)")

        total_updated = 0
        for vote_id in FIXES:
            v = db.execute(
                "SELECT url, summary FROM saeima_votes WHERE id = ?", (vote_id,)
            ).fetchone()
            summary_lower = v['summary'][0].lower() + v['summary'][1:]
            iv_rows = db.execute(
                "SELECT politician_id, vote FROM saeima_individual_votes "
                "WHERE vote_id = ? AND politician_id IS NOT NULL",
                (vote_id,),
            ).fetchall()
            pid_to_vote = {iv['politician_id']: iv['vote'] for iv in iv_rows}
            claims = db.execute(
                "SELECT id, opponent_id, stance FROM claims "
                "WHERE source_url = ? AND claim_type = 'saeima_vote'",
                (v['url'],),
            ).fetchall()
            updated_here = 0
            for c in claims:
                deputy_vote = pid_to_vote.get(c['opponent_id'])
                if not deputy_vote:
                    continue
                new_stance = f"{PREFIX.get(deputy_vote, deputy_vote)}: {summary_lower}"
                if new_stance != c['stance']:
                    db.execute(
                        "UPDATE claims SET stance = ? WHERE id = ?",
                        (new_stance, c['id']),
                    )
                    updated_here += 1
            total_updated += updated_here
            print(f"  vote {vote_id}: {updated_here} claim stances regenerated")
        db.commit()
        print(f"\nTotal claim stances re-updated: {total_updated}")
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == '__main__':
    main()
