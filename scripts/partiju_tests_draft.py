"""Partiju tests — T1 melnraksta eksports (tikai LASA DB).

Katram kandidāt-apgalvojumam izdrukā visu 14 startējošo sarakstu
`program_promise` pozīcijas attiecīgajās tēmās, ar atslēgvārdu iezīmi
(PIEMIN / KLUSĒ?) — palīgrīks kodētājam, NE gala dati. Kodējums
(par / pret / klusē) ir cilvēka lēmums pret avota tekstu.

Lietošana:
    .venv/Scripts/python.exe scripts/partiju_tests_draft.py [--out content/partiju-tests/kodejums_draft.md]

Saucējs (cik šūnu apskatīts) tiek drukāts stderr — 0 = salauzts rīks, ne tīrs rezultāts.
"""

from __future__ import annotations

import argparse
import re
import sqlite3
import sys
from pathlib import Path

DB = "file:data/atmina.db?mode=ro"
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from scripts.partiju_tests_validate import STARTING  # noqa: E402

# (id, tēmas, apgalvojuma melnraksts, "piekrītu" nozīme, atslēgvārdu regex)
CANDIDATES = [
    ("k01", ["Aizsardzība un drošība", "Budžets un finanses"],
     "Aizsardzībai jāatvēl vismaz 5 % no IKP arī tad, ja tāpēc jāsamazina citi izdevumi.",
     "par = 5 % vai vairāk; pret = samazināt / pārdalīt aizsardzības budžetu",
     r"5\s?%|IKP|aizsardzības (budžet|finansējum)"),
    ("k02", ["Ukraina un Krievija", "Ārpolitika"],
     "Latvijai jāturpina atbalstīt Ukrainu, kamēr karš nav beidzies.",
     "par = atbalsts Ukrainai; pret = neitralitāte / neiesaistīties",
     r"Ukrain|neitralit"),
    ("k03", ["Ukraina un Krievija", "Ārpolitika", "Aizsardzība un drošība"],
     "Ekonomiskie sakari ar Krieviju un Baltkrieviju jāatjauno, tiklīdz tas ir iespējams.",
     "par = atjaunot sadarbību / pārskatīt sankcijas; pret = pārtraukt / saglabāt sankcijas",
     r"Krievij|Baltkriev|sankcij"),
    ("k04", ["Aizsardzība un drošība"],
     "Obligātais valsts aizsardzības dienests jāsaglabā.",
     "par = saglabāt / paplašināt VAD; pret = atcelt obligāto iesaukšanu",
     r"aizsardzības dienest|VAD\b|iesauk|Zemessardz"),
    ("k05", ["Budžets un finanses", "Sociālā politika"],
     "Cilvēkiem ar lielākiem ienākumiem nodokļos jāatdod lielāka ienākumu daļa nekā cilvēkiem ar mazākiem.",
     "par = progresīvie nodokļi / kapitāla nodokļi; pret = vienāda likme / mazināt IIN visiem",
     r"progres[īi]v|ienākuma nodok|IIN|neapliekam|vienot[aā]s? likm"),
    ("k06", ["Budžets un finanses"],
     "Pievienotās vērtības nodoklis pārtikai vai citām pamatprecēm jāsamazina.",
     "par = samazināt PVN; pret = PVN nemainīt / celt",
     r"PVN|pievienotās vērtības"),
    ("k07", ["Veselības aprūpe"],
     "Ja valsts nespēj nodrošināt ārstēšanu laikā, valstij tā jāapmaksā privātā iestādē.",
     "par = nauda seko pacientam / privāto integrācija; pret = tikai valsts sistēma",
     r"rind|gaidīšan|privāt"),
    ("k08", ["Izglītība", "Budžets un finanses"],
     "Skolotāju algas jāceļ ātrāk nekā citās valsts sektora nozarēs.",
     "par = pedagogu atalgojuma celšana; pret = nav",
     r"pedagog|skolotāj"),
    ("k09", ["Izglītība"],
     "Augstskolu skaits jāsamazina, apvienojot tās.",
     "par = konsolidēt / apvienot augstskolas; pret = saglabāt reģionālās augstskolas",
     r"augstskol|augstāk[āa]s? izglīt|universitā"),
    ("k10", ["Imigrācija"],
     "Darbaspēka imigrācija no trešajām valstīm jāierobežo arī tad, ja uzņēmumiem trūkst darbinieku.",
     "par = ierobežot / kontrolēt; pret = atvieglot darbaspēka ievešanu",
     r"imigr|migr|viesstrādniek|trešaj"),
    ("k11", ["Valodu politika", "Izglītība"],
     "Skolās jāmāca tikai latviešu valodā, bez izņēmumiem mazākumtautību valodām.",
     "par = tikai latviski / stiprināt; pret = izglītība dzimtajā valodā / krievu valoda kā izvēle",
     r"latviešu valod|valsts valod|dzimtaj|krievu valod|mazākumtaut"),
    ("k12", ["Valodu politika", "Imigrācija"],
     "Nepilsoņiem pilsonība jāpiešķir atvieglotā kārtībā.",
     "par = atvieglota naturalizācija; pret = repatriācija / statusa izbeigšana bez pilsonības",
     r"nepilso|naturaliz|pilsonīb"),
    ("k13", ["Valsts pārvalde", "Budžets un finanses"],
     "Ministriju skaits jāsamazina, tās apvienojot.",
     "par = apvienot / likvidēt ministrijas; pret = nav",
     r"birokrāt|ierēdņ|pārvald.*(samazin|kompakt|štat)|štat"),
    ("k14", ["Pašvaldības", "Budžets un finanses"],
     "Lielāka nodokļu daļa jāatstāj pašvaldībām, mazāk jāpārdala caur valsts budžetu.",
     "par = lielāka pašvaldību/reģionu daļa; pret = centralizēt",
     r"pašvaldīb.*(nodok|finans|ieņēmum|budžet)|reģion.*(nodok|finans|budžet)|pārdal"),
    ("k15", ["Rail Baltica", "Transports"],
     "Rail Baltica jāpabeidz pilnā apjomā arī tad, ja izmaksas turpina augt.",
     "par = pabeigt pilnā apjomā; pret = apturēt / samazināt apjomu / auditēt pirms turpināt",
     r"Rail Baltica|RB\b"),
    ("k16", ["Lauksaimniecība"],
     "Latvijas lauksaimnieku tiešmaksājumi jāpielīdzina ES vidējam līmenim.",
     "par = izlīdzināt tiešmaksājumus; pret = nav",
     r"tiešmaksājum|tiešo maksājum|tiešie maksājum"),
    ("k17", ["Sociālā politika", "Tieslietas"],
     "Satversmē ģimene jādefinē kā vīrieša un sievietes savienība.",
     "par = ģimenes definīcija / Stambulas konvencijas denonsēšana; pret = laulību vienlīdzība / visu ģimeņu aizsardzība",
     r"Stambul|ģimenes defin|laulīb|vīrietis un sieviete|bioloģisk|dzimum"),
    ("k18", ["Klimats", "Vide", "Degviela un enerģētika"],
     "Latvijai jāsasniedz klimatneitralitāte ES noteiktajā termiņā, pat ja tas sadārdzina enerģiju.",
     "par = klimatneitralitāte / zaļais kurss; pret = pārskatīt / atteikties no zaļā kursa",
     r"klimat|zaļ[āa] kurs|zaļo kurs|Zaļ[āa] kurs|Green Deal"),
    ("k19", ["Degviela un enerģētika"],
     "Jaunas vēja elektrostacijas jābūvē arī tad, ja vietējie iedzīvotāji iebilst.",
     "par = vēja parku attīstība; pret = ierobežot / vietējais veto",
     r"vēja|atjaunojam|AER\b|saules"),
    ("k20", ["Pensijas", "Sociālā politika"],
     "Pensiju 2. līmenim jābūt brīvprātīgam, ar tiesībām uzkrājumu izņemt.",
     "par = brīvprātīgs / izņemt / pārcelt uz 1. līmeni; pret = saglabāt obligātu",
     r"2\.\s?(pensiju )?līme[nņ]|pensiju 2|otr[āa] līme[nņ]|fondēt"),
    ("k21", ["Sabiedriskie mediji", "Kultūra"],
     "Sabiedriskajam medijam jāpārtrauc raidīt krievu valodā.",
     "par = tikai latviski; pret = saglabāt RU saturu",
     r"sabiedrisk.*medij|LSM|LTV|Latvijas Radio|medij"),
    ("k22", ["Valsts kapitālsabiedrības", "airBaltic"],
     "airBaltic jāpārdod privātiem investoriem.",
     "par = pārdot / privatizēt; pret = saglabāt valsts kontroli",
     r"airBaltic|privatiz|kapitālsabiedrīb"),
    ("k23", ["Vēlēšanas", "Koalīcija un partijas", "Valsts pārvalde"],
     "Valsts prezidents tautai jāievēl tiešās vēlēšanās.",
     "par = tiešas prezidenta vēlēšanas; pret = nav",
     r"prezident|tautas nobals|referend|Saeimas deputātu skait"),
    ("k24", ["Korupcija un KNAB", "Tieslietas"],
     "Par korupciju notiesātām personām uz mūžu jāaizliedz ieņemt valsts amatus.",
     "par = mūža aizliegums / stingrāki sodi; pret = nav",
     r"korupc|KNAB|amatpersonu atbildīb"),
]
CANDIDATES.append(("k25", ["Budžets un finanses", "Pašvaldības"],
     "Nekustamā īpašuma nodoklis vienīgajam mājoklim jāatceļ.",
     "par = atcelt NĪN vienīgajam mājoklim; pret = saglabāt / stiprināt NĪN",
     r"nekustamā īpašuma nodok|NĪN"))


def norm(s: str) -> str:
    return re.sub(r"\s+", " ", s or "").strip()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="content/partiju-tests/kodejums_draft.md")
    args = ap.parse_args()

    c = sqlite3.connect(DB, uri=True)
    rows = c.execute(
        """SELECT p.short_name, c.topic, c.id, c.stance, c.quote, c.source_url
           FROM claims c JOIN parties p ON p.id = c.party_id
           WHERE c.claim_type = 'program_promise'"""
    ).fetchall()
    by_party: dict[str, list] = {}
    for sn, topic, cid, stance, quote, url in rows:
        by_party.setdefault(sn, []).append((topic, cid, norm(stance), norm(quote), url))
    missing = [p for p in STARTING if p not in by_party]
    if missing:
        print(f"KĻŪDA: nav program_promise rindu sarakstiem {missing}", file=sys.stderr)
        return 1

    out = ["# Partiju tests — kodējuma melnraksts (T1, automātisks, tikai lasīts no DB)\n",
           "Katrai šūnai: **PIEMIN** = atslēgvārds trāpa pozīcijas tekstā (kandidāts par/pret), "
           "**TĒMA** = partijai ir pozīcija tēmā, bet atslēgvārds netrāpa (visticamāk klusē), "
           "**KLUSĒ?** = tēmā pozīcijas nav. Kodējums ir cilvēka lēmums pret avota tekstu.\n"]
    cells = 0
    summary = []
    for cid, topics, statement, meaning, pat in CANDIDATES:
        rx = re.compile(pat, re.I)
        out.append(f"\n## {cid} — {statement}\n\nTēmas: {', '.join(topics)}  \nKodēšanas atgādne: {meaning}\n")
        hits = 0
        for party in STARTING:
            cells += 1
            in_topic = [r for r in by_party[party] if r[0] in topics]
            hit = [r for r in in_topic if rx.search(r[2]) or rx.search(r[3])]
            # atslēgvārds var trāpīt arī citā tēmā — rādām kā papildu norādi
            elsewhere = [r for r in by_party[party] if r[0] not in topics and (rx.search(r[2]) or rx.search(r[3]))]
            if hit:
                mark = "PIEMIN"
                hits += 1
            elif elsewhere:
                mark = "PIEMIN (citā tēmā)"
                hits += 1
            elif in_topic:
                mark = "TĒMA"
            else:
                mark = "KLUSĒ?"
            out.append(f"\n### {party} — {mark}\n")
            for topic, claim_id, stance, quote, url in (hit or elsewhere or in_topic):
                out.append(f"- claim_id {claim_id} · {topic} · [CVK]({url})  \n  **Pozīcija:** {stance}")
                if quote:
                    out.append(f"  \n  **Citāts:** „{quote}”")
        summary.append((cid, hits, statement))
        out.append(f"\n_Piemin: {hits} no 14._\n")

    out.insert(2, "\n## Kopsavilkums (partiju skaits, kas apgalvojumu piemin — augšējā robeža)\n\n| id | piemin | apgalvojums |\n|---|---|---|\n"
               + "\n".join(f"| {c} | {h} | {s} |" for c, h, s in summary) + "\n")
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text("\n".join(out), encoding="utf-8")
    print(f"Apskatītas {cells} šūnas ({len(CANDIDATES)} apgalvojumi × {len(STARTING)} saraksti); "
          f"rakstīts {args.out}", file=sys.stderr)
    for c_, h, s in summary:
        print(f"  {c_} {h:2d}  {s}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
