"""One-off script: apply meaningful summaries for 14 votes from 2026-05-07 and 2026-05-14 sessions.

Step 3.5 (@saeima-tracker prompt) was skipped during these dispatches; the 15 votes had
NULL saeima_votes.summary fields. This script also assigns bill_id=22 (1019/Lp14)
to vote 183 (President's veto otrreizēja caurlūkošana).

Idempotent: SQL UPDATE overwrites whatever is there.
"""
import sys
sys.path.insert(0, '.')

from src.db import get_db

db = get_db('data/atmina.db')

# vote_id -> (bill_id_for_assignment_or_None_meaning_no_change, summary_text)
summaries = {
    # --- 07.05.2026 — LPV opozīcijas sociālā pakete, visi noraidīti pirmajā lasījumā nodošanas balsojumā ---

    179: (None, "LPV (Krištopans, Drelinga, Kļaviņa, Pleškāne, Zivtiņš) ierosinātais speciālā likuma projekts pedagogiem ar vismaz 35 gadu izdienas stāžu piešķir izdienas pensiju no 60 gadu vecuma 90 % apmērā no vidējās mēneša algas, motivējot ar pedagogu trūkumu (~300 vakanču Rīgā un Pierīgā). Saeima nodošanu komisijām noraidīja (29/18/24) — koalīcija norādīja, ka 2025. gada beigās jau pieņemta izdienas pensiju sistēmas reforma, kas šādu izņēmumu neparedz."),

    189: (None, "LPV (Armaņeva, Drelinga, Pleškāne, Stobova, Zivtiņš) opozīcijas grozījumi likumam «Par valsts pensijām» — daļa no LPV pensiju paketes, kas paralēli notiekošajai parakstu vākšanai par pensiju 2. līmeņa daļas ātrāku izņemšanu paplašina vecuma pensiju saņēmēju tiesības. Saeima nodošanu komisijām noraidīja (36/21/24) — koalīcija un Finanšu ministrija norāda uz fiskālās ilgtspējas riskiem."),

    180: (None, "LPV (Krištopans, Armaņeva, Liepiņa, Petraviča, Zivtiņš) opozīcijas grozījumi likumam «Par iedzīvotāju ienākuma nodokli» turpina virkni nodokļu atvieglojumu priekšlikumu ģimenēm (līdzīgi pavasarī jau noraidītajam priekšlikumam atbrīvot no IIN vecākus ar trīs vai vairāk bērniem). Saeima nodošanu komisijām noraidīja (37/9/33) — koalīcijas vairums atturējās."),

    191: (None, "LPV (Krištopans, Drelinga, Kļaviņa, Pleškāne, Stobova) opozīcijas grozījumi Valsts sociālo pabalstu likumā — daļa no LPV sociālā atbalsta paketes ģimenēm un pensionāriem. Saeima nodošanu komisijām noraidīja (36/13/33) — līdzīgi pārējiem 07.05. dienā nodošanai pieteiktajiem LPV likumprojektiem koalīcijas vairums atturējās."),

    # --- 14.05.2026 — Pieprasījumi ministriem (P14) ---

    194: (None, "AS frakcijas (E.Smiltēns, E.Tavars u.c., 10 deputāti) pieprasījums Ministru prezidentei E.Siliņai sniegt skaidrojumu par publisko informāciju saistībā ar Amsterdamas lidostas VIP zāles izmantošanu. Pēc Ministru prezidentes ASV vizītes laikā (2024. martā) izmantotā VIP servisa izmaksas — 4 184 EUR — un kopumā četru gadu laikā par Siliņas VIP tēriņiem lidostās samaksāti ~35 550 EUR. Saeima pieprasījumu atbalstīja (41/28/1) — premjerei būs jāsniedz skaidrojums deputātiem."),

    188: (None, "LPV (Pleškāne, Zivtiņš, Armaņeva, Liepiņa, Krištopans u.c., 10 deputāti) pieprasījums viedās administrācijas un reģionālās attīstības ministram R.Čudaram (JV) par otra domes priekšsēdētāja ievēlēšanu Rēzeknes valstspilsētas domē — saistībā ar februārī notikušo iepriekšējā mēra A.Bartaševiča (Kopā Latvijai) atstādināšanu pēc pielaides valsts noslēpumam atteikuma un 10.04.2026 ievēlēto jauno mēru J.Tutinu (Kopā Latvijai). Saeima pieprasījumu noraidīja (10/47/9)."),

    178: (None, "NA frakcijas (J.Vitenbergs, A.Butāns, U.Mitrevics u.c., 10 deputāti) pieprasījums izglītības un zinātnes ministrei D.Melbārdei (NA — pašas frakcijas ministrei) par MK rīkojuma projektu Nr. 26-TA-109 — IZM plāno pārdot Latvijas Sporta muzeja ēku Vecrīgā, Alksnāja ielā 9, lai segtu IZM budžeta iztrūkumu, paredzot muzeja pārcelšanu uz Spēļu spēļu zāli un saglabājot esošās telpas vēl 3 gadus. NA iebilst pret nekonsultēto lēmumu un ēkas pārdošanas vajadzību. Saeima pieprasījumu noraidīja (30/41/1)."),

    190: (None, "LPV (Armaņeva, Liepiņa, Petraviča, Zivtiņš, Stobova u.c., 10 deputāti) pieprasījums Ministru prezidentei E.Siliņai par iespējamu interešu konflikta un dāvinājumu pieņemšanas ierobežojumu pārkāpumiem, JV politiķiem 2026. gada aprīlī piedaloties Konrāda Adenauera fonda pilnībā apmaksātā seminārā Komo ezera krastā Itālijā. Brauciens nokļuvis arī KNAB redzeslokā jautājumā par to, vai ārvalstu fonda apmaksāts ceļojums uzskatāms par aizliegtu partijas finansēšanu. Saeima pieprasījumu atbalstīja (46/25/0)."),

    # --- 14.05.2026 — Lēmumprojekts (Lm14) ---

    185: (None, "Budžeta un finanšu (nodokļu) komisijas (referents E.Jurēvics, JV) lēmumprojekts apstiprināt deputāti Andu Čakšu (JV, ex-IZM ministre) par Saeimas pārstāvi Ziemeļu Investīciju bankas Kontroles komitejā ar 2026. gada 1. jūniju — atbilstoši līgumam starp Ziemeļvalstīm, Baltijas valstīm un Latviju par NIB pārvaldību. Pieņemts ar plašu vairākumu (85/4/0)."),

    # --- 14.05.2026 — Likumprojekti (Lp14) ---

    181: (None, "JV deputātu (E.Jurēvics, G.Liepiņš, I.Vergina, Z.Kalniņa-Lukaševica, A.Zariņa-Stūre) ierosinātais grozījumu projekts Administratīvo sodu likumam par pārkāpumiem pārvaldes, sabiedriskās kārtības un valsts valodas lietošanas jomā vienoti palielina naudas sodus ~40 % apmērā (no 7→10, 28→39, 140→196 naudas soda vienībām) par sabiedriskās kārtības traucēšanu, viltus speciālo dienestu izsaukumiem, valsts valodas nelietošanu uzrakstos, etiķetēs, līgumos, filmu tulkojumos, kā arī Saeimas slēgto sēžu ziņu izpaušanu. 2. lasījumā pieņemts (67/20/8) — koalīcija atbalstīja, opozīcija dalījās."),

    187: (None, "Tautsaimniecības, agrārās, vides un reģionālās politikas komisijas (referents K.Briškens, PRO) izstrādātais grozījumu projekts Preču un pakalpojumu piekļūstamības likumā transponē ES Direktīvu 2019/882, pievienojot trūkstošās definīcijas (pakalpojums; saskaņotais standarts; tehniskā specifikācija; dzelzceļa pasažieru pārvadājumu pakalpojums) — reaģējot uz Eiropas Komisijas 30.01.2026. argumentēto atzinumu pārkāpuma procedūras lietā Nr. INFR(2022)0313. 1. lasījumā vienprātīgi pieņemts (97/0/0)."),

    186: (None, "Tautsaimniecības, agrārās, vides un reģionālās politikas komisijas (referents K.Briškens, PRO) izstrādātais grozījumu projekts Preču un pakalpojumu piekļūstamības likumā transponē ES Direktīvu 2019/882, pievienojot trūkstošās definīcijas (pakalpojums; saskaņotais standarts; tehniskā specifikācija; dzelzceļa pasažieru pārvadājumu pakalpojums) — reaģējot uz Eiropas Komisijas 30.01.2026. argumentēto atzinumu pārkāpuma procedūras lietā Nr. INFR(2022)0313. 2. lasījumā (steidzams) vienprātīgi pieņemts (94/0/0)."),

    184: (None, "Valsts pārvaldes un pašvaldības komisijas (referents O.Burovs) izstrādātais grozījumu projekts Mākslīgā intelekta centra likumā ļauj Centram pārņemt sekretariāta funkciju (juridiskais atbalsts, iepirkumi, lietvedība, IKT, infodrošība) savā paspārnē — līdz šim šo nodrošināja Valsts digitālā aģentūra (VDAA), neļaujot Centram patstāvīgi plānot resursus. Centra struktūra: padome + valde/direktors. Spēkā no 2026. gada 1. jūnija. 1. lasījumā pieņemts (88/4/0)."),

    177: (None, "Valsts pārvaldes un pašvaldības komisijas (referents O.Burovs) izstrādātais grozījumu projekts Mākslīgā intelekta centra likumā ļauj Centram pārņemt sekretariāta funkciju (juridiskais atbalsts, iepirkumi, lietvedība, IKT, infodrošība) savā paspārnē — līdz šim šo nodrošināja Valsts digitālā aģentūra (VDAA), neļaujot Centram patstāvīgi plānot resursus. Centra struktūra: padome + valde/direktors. Spēkā no 2026. gada 1. jūnija. 2. lasījumā (steidzams) pieņemts (90/4/0)."),

    # --- 14.05.2026 — Vote 183: Otrreizēja caurlūkošana 1019/Lp14 (assign bill_id=22) ---

    183: (22, "Likumprojekta «Grozījumi Kriminālprocesā un administratīvo pārkāpumu lietvedībā nodarītā kaitējuma atlīdzināšanas likumā» (1019/Lp14) otrreizēja caurlūkošana pēc Valsts prezidenta lūguma — sākotnējais TM iniciētais likumprojekts (3. lasījumā pieņemts 15.01.2026) modernizē 2018. gada likumu par kriminālprocesā/administratīvajā procesā nodarītā kaitējuma atlīdzināšanu: paplašina atbildību no šaurās «iestāde, prokuratūra vai tiesa» uz «publisko tiesību juridisko personu», atceļ mantiskā zaudējuma apmēra ierobežojumus, ļauj individuāli izvērtēt juridiskās palīdzības izdevumus, transponē ES Direktīvas 2016/800 prasības par bērnu procesuālajām garantijām un papildina ar Finanšu izlūkošanas dienesta atbildību. Saeima knapi atbalstīja otrreizēju izskatīšanu (47/44/1)."),
}

# bill_id -> summary (one row per bill).
# For bills with two votes (161 — 186+187, 163 — 184+177) take the 2.lasījums final reading summary.
bill_summaries = {
    158: summaries[179][1],
    159: summaries[189][1],
    160: summaries[180][1],
    162: summaries[191][1],
    168: summaries[194][1],
    169: summaries[188][1],
    170: summaries[178][1],
    171: summaries[190][1],
    166: summaries[185][1],
    172: summaries[181][1],
    161: summaries[186][1],  # 2.lasījums steidzams — galīgais pieņemts
    163: summaries[177][1],  # 2.lasījums steidzams — galīgais pieņemts
    # bill 22 (1019/Lp14) has a previously-stored summary about priekšlikumu termiņa pagarināšanu (procedural).
    # We do NOT overwrite that — vote 183 summary captures the otrreizēja caurlūkošana context.
}

with db:
    for vote_id, (assign_bill_id, summary) in summaries.items():
        db.execute("UPDATE saeima_votes SET summary = ? WHERE id = ?", (summary, vote_id))
        if assign_bill_id is not None:
            db.execute("UPDATE saeima_votes SET bill_id = ? WHERE id = ?", (assign_bill_id, vote_id))
            print(f"vote {vote_id}: assigned bill_id={assign_bill_id}")

    for bid, summ in bill_summaries.items():
        db.execute("UPDATE saeima_bills SET summary = ? WHERE id = ?", (summ, bid))

print("OK — committed all summaries")

# Verify
rows = db.execute("""
SELECT v.id AS vote_id, v.bill_id, v.summary IS NOT NULL AS has_v,
       b.summary IS NOT NULL AS has_b, b.document_nr
FROM saeima_votes v LEFT JOIN saeima_bills b ON v.bill_id = b.id
WHERE v.id IN (185,194,188,178,190,181,187,186,184,177,179,189,180,191,183)
ORDER BY v.id
""").fetchall()
for r in rows:
    print(f"vote {r['vote_id']:3}  bill_id={r['bill_id']!s:5}  doc={r['document_nr']!s:14}  has_vote_summary={r['has_v']}  has_bill_summary={r['has_b']}")
