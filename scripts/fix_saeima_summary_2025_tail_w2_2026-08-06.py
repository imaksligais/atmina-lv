"""2025. gada balsojumu `summary` astes aizvēršana (50 rindas).

Konteksts: BACKLOG § parity — 2025. gada saeima_votes rindas ar document_nr,
bet bez kopsavilkuma. Šīm rindām NAV māsas ieraksta ar to pašu document_nr, no
kura kopsavilkumu pārmantot, tāpēc saturs iegūts no avota — titania
saeimalivs_lmp.nsf lēmumprojektu tekstiem (.edoc konteinera .docx, tiešs .docx
vai teksta PDF; piecos gadījumos attēlu-PDF nolasīts vizuāli).

Diskiplīna:
  * raksta TIKAI saeima_votes.summary; bill_id / current_stage netiek aiztikti
    (Pipeline Invariant 12);
  * neviens kopsavilkums nesatur CITA balsojuma iznākuma frāzi — procesuālajiem
    balsojumiem aprakstīts, PAR KO balso, bez lasījuma iznākuma teikuma;
  * kopsavilkums neatkārto motif virsrakstu.

Paired rollback: data/rollback_saeima_summary_2025_tail_w2_2026-08-06.sql
Apply date: 2026-08-06
"""

from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

DB = Path(__file__).resolve().parent.parent / "data" / "atmina.db"

# --- 617/Lm14: Augstākās izglītības padomes sastāvs, balsojums pa kandidātam ---
_AIP = (
    "Augstākās izglītības padomes sastāvu Saeima apstiprina pa vienam kandidātam; "
    "šis balsojums attiecas uz {org} deleģēto pārstāvi. Sastāvu izvirzīja "
    "Izglītības, kultūras un zinātnes komisija; padome darbu sāk 2025. gada 21. janvārī."
)

_617 = {
    6927: "Latvijas Zinātņu akadēmijas",
    6928: "Latvijas Universitāšu asociācijas",
    6929: "Latvijas Mākslas augstskolu asociācijas",
    6930: "Latvijas Izglītības vadītāju asociācijas",
    6931: "Latvijas Tirdzniecības un rūpniecības kameras",
    6932: "Latvijas Koledžu asociācijas",
    6933: "Rektoru padomes",
    6934: "Latvijas Augstskolu profesoru asociācijas",
    6935: "Latvijas Darba devēju konfederācijas",
    6936: "Latvijas Izglītības un zinātnes darbinieku arodbiedrības",
    6937: "Latvijas Studentu apvienības",
    6938: "Privāto augstskolu asociācijas",
}

# --- pārējie: viens satura kopsavilkums uz dokumentu, visiem tā balsojumiem ---
_BY_DOC: dict[str, tuple[list[int], str]] = {
    "633/Lm14": (
        [6985, 6986],
        "Patstāvīgais priekšlikums prasa valdībai atcelt 2024. gada 26. novembra "
        "Ministru kabineta noteikumus Nr. 745, kas paredz izveidot izglītības "
        "kvalitātes monitoringa sistēmas platformu par 21,3 miljoniem eiro ES "
        "kohēzijas naudas, un šo finansējumu novirzīt mācību līdzekļiem, pedagogu "
        "slodzei un atbalsta personālam.",
    ),
    "637/Lm14": (
        [7000, 7001, 7002],
        "Lēmuma projekts uzdod Ministru prezidentei pilnībā aizliegt sabiedriskos "
        "pasažieru pārvadājumus uz Krieviju un Baltkrieviju, kā arī no tām, tostarp "
        "to organizēšanas tranzītu, un vienoties par tādu pašu aizliegumu ar pārējām "
        "Baltijas valstīm. Pamatojums — Valsts drošības dienesta konstatētie vervēšanas un "
        "izlūkošanas riski un ziņas par sankcijām pakļautu preču pārvešanu autobusos.",
    ),
    "715/Lm14": (
        [7116, 7117, 7118],
        "Lēmuma projekts uzdod izglītības ministrei ar grozījumiem Ministru kabineta "
        "noteikumos panākt, ka no 2025. gada 1. septembra Latvijas izglītības "
        "iestādēs krievu valodā vairs nenotiek informācijas apmaiņa, mācību process, "
        "skolēnu konkursi un svinīgie priekšnesumi. Iesniedzēji atsaucas uz sūdzībām "
        "par bilingvālām stundām un Pēdējā zvana priekšnesumiem Liepājā un Daugavpilī.",
    ),
    "718/Lm14": (
        [7125, 7126],
        "Lēmuma projekts uzdod Ministru prezidentei nodrošināt, ka no 2025. gada "
        "1. jūlija valsts naftas produktu drošības rezervju un dabasgāzes iegādē par "
        "prioritāru tiek noteikta sadarbība ar ASV un citām NATO dalībvalstīm. "
        "Pamatojums — pāreja uz rezervju fizisku iegādi un uzglabāšanu Latvijā un "
        "vēlme piegādes ķēdes sasaistīt ar aizsardzības partneriem.",
    ),
    "719/Lm14": (
        [7127],
        "Lēmuma projekts aicina Ministru kabinetu nekavējoties samazināt valsts "
        "pārvaldē strādājošo skaitu par 30 %, novēršot iestāžu funkciju pārklāšanos, "
        "izvērtēt Sabiedrības integrācijas fonda un citu valsts veidotu institūciju "
        "lietderību, apvienot valsts nekustamā īpašuma pārvaldīšanas iestādes un šo "
        "samazinājumu iestrādāt 2026. gada budžeta projektā.",
    ),
    "721/Lm14": (
        [7148, 7149],
        "Lēmuma projekts aicina Saeimu pieņemt regulējumu, kas apturētu vēja "
        "elektrostaciju un vēja parku projektēšanu un būvniecību visā Latvijā, un "
        "uzdot Tautsaimniecības, agrārās, vides un reģionālās politikas komisijai "
        "jautājumu izvērtēt atkārtoti. Iesniedzēji atsaucas uz 10 652 pilsoņu "
        "parakstīto kolektīvo iesniegumu «Par Latviju bez vēja parkiem».",
    ),
    "724/Lm14": (
        [7183, 7184],
        "Lēmuma projekts uzdod ārlietu ministrei līdz 2025. gada 1. jūlijam sagatavot "
        "priekšlikumu iekļaut Latvijas nacionālo sankciju sarakstā SIA «Latprodukti» "
        "— veikalu tīkla «Mere» operatoru Latvijā — un tās piecus īpašniekus, "
        "Krievijas pilsoņus. Pamatojums: «Mere» ir Krievijas tīkla «Svetofor» zīmols "
        "Eiropā, un 2025. gada aprīlī Polija noteica sankcijas tā īpašniekiem.",
    ),
    "725/Lm14": (
        [7171, 7173],
        "Deklarācijas projekts pasludina, ka padomju okupācijas režīma īstenotās "
        "rusifikācijas sekas ir jānovērš, nosakot ierobežojumus krievu valodas "
        "lietojumam sabiedriskajā dzīvē — sarunvalodā, plašsaziņas līdzekļos, "
        "izglītībā, sportā un interešu nodarbībās —, lai latviešu valoda atgūtu "
        "kopējās saziņas un demokrātiskās līdzdalības valodas lomu.",
    ),
    "727/Lm14": (
        [7172, 7185, 7186],
        "Deklarācijas projekts aicina pārtraukt sabiedrības šķelšanu, aizsargāt "
        "mazākumtautību pastāvēšanu Latvijā, aizliegt diskrimināciju pēc piederības "
        "nacionālai minoritātei un atturēties no politikas, kas mazākumtautības "
        "asimilētu pret to gribu. Projekts balstīts uz Vispārējo konvenciju par "
        "nacionālo minoritāšu aizsardzību un Satversmes 114. pantu.",
    ),
    "728/Lm14": (
        [7177],
        "Deklarācijas projekts nosoda 13. Saeimas un Krišjāņa Kariņa valdības "
        "Covid-19 ierobežojumus, lūdz iedzīvotājiem piedošanu un apņemas kompensēt to "
        "radītos finansiālos zaudējumus un morālās ciešanas. Ministru kabinetam līdz "
        "2025. gada 1. septembrim būtu jāiesniedz tiesību aktu projekti par "
        "kompensācijām, izmaksājot tās līdz 2026. gada 24. janvārim.",
    ),
    "755/Lm14": (
        [7222],
        "Lēmuma projekts uzdod finanšu ministram līdz 2025. gada 31. jūlijam "
        "sagatavot grozījumus nodokļu likumos un Ministru kabineta noteikumos "
        "Nr. 178, lai novērstu faktisko dubulto aplikšanu ar nodokli dividendēm, ko Latvijas "
        "sabiedrības izmaksā fiziskām personām — ES, EEZ, OECD un NATO valstu nodokļu "
        "rezidentiem. Ierosinājums seko Amerikas Tirdzniecības palātas Latvijā "
        "2025. gada februāra vēstulei valdībai.",
    ),
    "795/Lm14": (
        [7247],
        "Lēmuma projekts uzdod Ministru kabinetam līdz 2026. gada budžeta "
        "sastādīšanai iesniegt papildu izdevumu samazinājumu publiskajā pārvaldē: "
        "samazināt iepirkumus par 7–8 % un ierēdņu skaitu vismaz par 10 %, likvidēt "
        "brīvās vakances, atcelt prēmijas par ikgadējo darba izpildes novērtējumu un "
        "naudas balvas, kā arī veikt funkciju auditu un likvidēt iestādes ar "
        "pārklājošām funkcijām.",
    ),
    "796/Lm14": (
        [7248, 7249],
        "Lēmuma projekts uzdod Ministru prezidentei līdz 2025. gada 1. oktobrim "
        "pārskatīt valsts budžeta izstrādes procesu, lai deputāti tiktu iesaistīti jau "
        "sagatavošanas stadijā: diskusijas par fiskālajiem mērķiem pirms projekta "
        "iesniegšanas Saeimā, tiešsaistes piekļuve budžeta datiem un skaidrāka Valsts "
        "kases informācija par ilgtermiņa saistībām un valsts parāda dinamiku.",
    ),
    "798/Lm14": (
        [7277],
        "Lēmuma projekts uzdod Ministru kabinetam papildu izdevumu samazinājumu "
        "2026. gada budžetā rast, nepiešķirot finansējumu četriem Latvijas Zinātnes "
        "padomes apstiprinātiem projektiem par 300 000 eiro katrs: autovadīšanas "
        "novērtēšanas, viena dzimuma partnerību, antidženderisma diskursa un dzelzs "
        "laikmeta bioarheoloģijas pētījumiem.",
    ),
    "810/Lm14": (
        [7276],
        "Lēmuma projekts uzdod Ministru prezidentei nekavējoties pieņemt Ministru "
        "kabineta lēmumu par pilnīgu Latvijas robežas slēgšanu ar Krieviju un "
        "Baltkrieviju militāro mācību «Zapad» laikā no 12. līdz 16. septembrim, bet "
        "Aizsardzības ministrijai — veikt papildu drošības pasākumus. Pamatojums: "
        "kaujas dronu ielidošana Polijā un Polijas lēmums mācību laikā slēgt robežu "
        "ar Baltkrieviju.",
    ),
    "817/Lm14": (
        [7285],
        "Lēmuma projekts prasa atlikt četru «zaļā kursa» likumprojektu izskatīšanu "
        "Saeimā — Klimata likuma, Transporta enerģijas likuma, grozījumu likumā «Par "
        "piesārņojumu» un Ekonomiskās ilgtspējas likuma — un nepieņemt regulējumu, kas "
        "būtiski palielina budžeta izdevumus vai slogu privātpersonām. Pamatojums: "
        "Nacionālā enerģētikas un klimata plāna izpildei nepieciešams 13,1 miljards "
        "eiro, bet iezīmēti tikai 3,8 miljardi, kamēr vienīgā budžeta prioritāte ir "
        "valsts drošība.",
    ),
    "826/Lm14": (
        [7347],
        "Lēmuma projekts uzdod Ministru prezidentei ar Ministru kabineta lēmumu slēgt "
        "Latvijas gaisa telpu gar robežu ar Krieviju un Baltkrieviju uz nenoteiktu "
        "laiku. Pamatojums: septembrī noteiktie pagaidu gaisa telpas ierobežojumi, "
        "dronu incidenti Ziemeļeiropas lidostās un Krievijas iznīcinātāju ielidošana "
        "Igaunijas gaisa telpā.",
    ),
    "828/Lm14": (
        [7352, 7353],
        "Lēmuma projekts nosaka, ka vēja elektrostacijām ar jaudu virs 2 MW attālumam "
        "līdz dzīvojamām un publiskām ēkām jābūt vismaz 2 km, un aicina Ministru "
        "kabinetu līdz 2025. gada 31. decembrim pārskatīt Ministru kabineta "
        "noteikumus Nr. 240, kuros pašlaik noteikti 800 m. Pamatojums — trokšņa, "
        "infraskaņas, vibrāciju un ēnu mirgošanas ietekme uz iedzīvotāju veselību.",
    ),
    "844/Lm14": (
        [7496, 7497],
        "Lēmuma projekts nosaka vadlīniju, ka vēja elektrostacijām ar jaudu virs 2 MW "
        "attālumam līdz dzīvojamām un publiskām ēkām jābūt vismaz 2 km, un aicina "
        "Ministru kabinetu nekavējoties pārskatīt Ministru kabineta noteikumus "
        "Nr. 240, kuros pašlaik noteikti 800 m. Izpildes parlamentāro kontroli "
        "paredzēts uzdot Tautsaimniecības, agrārās, vides un reģionālās politikas "
        "komisijai.",
    ),
    "845/Lm14": (
        [7392, 7498, 7499],
        "Lēmuma projekts uzdod Ministru prezidentei nodrošināt lēmumus un likumu "
        "izpildi, lai valsts un pašvaldību iestādēs darba vides, pakalpojumu "
        "sniegšanas un saziņas valoda ar iedzīvotājiem būtu valsts valoda. Iesniedzēji "
        "norāda, ka vairākās iestādēs joprojām tiek lietota krievu valoda, kas ir "
        "pretrunā ar Satversmes 4. pantu un Valsts valodas likumu.",
    ),
    "878/Lm14": (
        [7864, 7865],
        "Lēmuma projekts aicina Ministru kabinetu apturēt jaunu vēja enerģijas staciju "
        "projektu akceptēšanu, līdz ir pieņemts regulējums par trokšņa, mirguļošanas "
        "un zemfrekvences skaņas ietekmes novērtējumu, par staciju demontāžu un "
        "rekultivāciju, kā arī par drošības zonām, un līdz ir izstrādātas vadlīnijas "
        "avāriju un ugunsgrēku risku novēršanai. Divu mēnešu laikā valdībai būtu "
        "jāinformē Saeima par izstrādes gaitu.",
    ),
}


def build() -> dict[int, str]:
    out: dict[int, str] = {vid: _AIP.format(org=org) for vid, org in _617.items()}
    for _doc, (ids, text) in _BY_DOC.items():
        for vid in ids:
            assert vid not in out, f"dublēts vote id {vid}"
            out[vid] = text
    return out


def main(apply: bool) -> int:
    plan = build()
    print(f"plānoti {len(plan)} kopsavilkumi")

    db = sqlite3.connect(DB)
    db.row_factory = sqlite3.Row
    target = {
        r["id"]
        for r in db.execute(
            "SELECT id FROM saeima_votes WHERE vote_date LIKE '2025%' "
            "AND (summary IS NULL OR summary='') "
            "AND document_nr IS NOT NULL AND document_nr != ''"
        )
    }
    print(f"DB rinda: {len(target)} rindas bez kopsavilkuma")

    missing = target - plan.keys()
    extra = plan.keys() - target
    if missing:
        print(f"STOP: {len(missing)} DB rindas bez plānota kopsavilkuma: {sorted(missing)}")
        db.close()
        return 1
    if extra:
        print(f"STOP: {len(extra)} plānoti id nav rindā: {sorted(extra)}")
        db.close()
        return 1

    if not apply:
        for vid in sorted(plan):
            print(f"  {vid}: {plan[vid][:70]}...")
        print("\n(dry-run — nekas netika rakstīts; palaid ar --apply)")
        db.close()
        return 0

    written = 0
    with db:
        for vid, text in plan.items():
            cur = db.execute(
                "UPDATE saeima_votes SET summary = ? WHERE id = ? AND summary IS NULL",
                (text, vid),
            )
            written += cur.rowcount
    print(f"ierakstīti {written} kopsavilkumi (gaidīti {len(plan)})")
    db.close()
    return 0 if written == len(plan) else 1


if __name__ == "__main__":
    sys.exit(main(apply="--apply" in sys.argv))
