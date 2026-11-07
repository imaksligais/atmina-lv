"""Register political tensions extracted from 2026-04-25 claims.

Each tension links source_pid (the speaker doing the action) to target_pid
(the named politician). All source URLs verified to exist in documents table.

Reasoning per tension is in the description field.
"""
from src.db import store_tension


TENSIONS = [
    # Kurmitis_ (175) -> Smiltēns (69, AS) — personal mockery
    dict(
        source_pid=175, target_pid=69, topic="Koalīcija un partijas",
        tension_type="uzbrukums",
        description=(
            "@Kurmitis_ apsmej Edvardu Smiltēnu (AS) — "
            "raksturo kā partijas 'lielāko bļāvēju' un sarkastiski piesaista to "
            "ASV konservatīvo politiķu vīriešu tualetes skandāliem. Personiska "
            "ņirgāšanās bez konkrētas politikas pretrunas."
        ),
        source_url="https://x.com/Kurmitis_/status/2047667490344341824",
    ),
    # Kurmitis_ (175) -> Zivtiņš (153, LPV) — substantive corruption insinuation
    dict(
        source_pid=175, target_pid=153, topic="Tieslietas",
        tension_type="uzbrukums",
        description=(
            "@Kurmitis_ apgalvo, ka Edmunds Zivtiņš (LPV) divreiz bijis Rīgas "
            "Satiksmes valdes loceklis kopumā ~10 gadus tieši tajā periodā, "
            "kad uzņēmumā notika korupcijas skandāli un fiktīvās nodarbinātības "
            "izmeklēšana. Substanciāla, bet bez tiešas apsūdzības formulējuma."
        ),
        source_url="https://x.com/Kurmitis_/status/2047206075724648531",
    ),
    # Heinrih5 (171) -> Melnis (157, ZZS) — LTV media bias + EV/CO2 policy critique
    dict(
        source_pid=171, target_pid=157, topic="Sabiedriskie mediji",
        tension_type="uzbrukums",
        description=(
            "@Heinrih5 apsūdz LTV Ziņas (žurnāliste @DagnijaNeimane) reklāmas "
            "sižetu veidošanā par klimata un enerģētikas ministru Kasparu "
            "Melni (ZZS), nevis objektīvā žurnālistikā par CO2 nodokļa sociālo "
            "nevienlīdzību (40k EV pircēji + 4k atbalsts vs. 3k auto pircēji + "
            "augstāks degvielas CO2 nodoklis)."
        ),
        source_url="https://x.com/Heinrih5/status/2047195174057422973",
    ),
    # Heinrih5 (171) -> Siliņa (2, JV) — 100M responsibility attack
    dict(
        source_pid=171, target_pid=2, topic="Budžets un finanses",
        tension_type="uzbrukums",
        description=(
            "@Heinrih5 retoriski jautā, vai par 'simtu miljonu izšķērdēšanu' "
            "atbildēs premjere Evika Siliņa (JV) vai aizsardzības ministrs Andris "
            "Sprūds (PRO) — implicē, ka abi ir atbildīgi un valsts ir kļuvusi "
            "izsķērdīga. Nenosauc konkrētus 100 milj. izlietošanas kanālus."
        ),
        source_url="https://x.com/Heinrih5/status/2046998325568655589",
    ),
    # Heinrih5 (171) -> Sprūds (16, PRO) — same 100M tweet, second target
    dict(
        source_pid=171, target_pid=16, topic="Budžets un finanses",
        tension_type="uzbrukums",
        description=(
            "@Heinrih5 retoriski jautā, vai par 'simtu miljonu izšķērdēšanu' "
            "atbildēs aizsardzības ministrs Andris Sprūds (PRO) vai premjere "
            "Evika Siliņa (JV). Tā paša tvīta otrais mērķis."
        ),
        source_url="https://x.com/Heinrih5/status/2046998325568655589",
    ),
    # Heinrih5 (171) -> Staķis (22, PRO) — interest conflict insinuation
    dict(
        source_pid=171, target_pid=22, topic="Valsts pārvalde",
        tension_type="uzbrukums",
        description=(
            "@Heinrih5 implicē interešu konfliktu iepirkumu procedūrās, "
            "norādot, ka Mārtiņš Staķis (PRO) ir Viestura Kleinberga (PRO) "
            "padomnieks. Sarkastiski raksturo iepirkumu vērtēšanu kā "
            "'raķešu zinātni' ar iepriekš noteiktu uzvarētāju."
        ),
        source_url="https://x.com/Heinrih5/status/2046985713393025443",
    ),
    # Heinrih5 (171) -> Švinka (26, PRO) — endorsement (atbalsts, not uzbrukums)
    dict(
        source_pid=171, target_pid=26, topic="Koalīcija un partijas",
        tension_type="atbalsts",
        description=(
            "@Heinrih5 atklāti atbalsta Ati Švinku (PRO) kā Progresīvo "
            "premjera kandidātu — uzslavē par tiešām atbildēm žurnālistiem "
            "un raksturo kā 'līderi, kuru Latvija sen pelnījusi'. Skaidrs "
            "atbalsta paziņojums, nevis uzbrukums."
        ),
        source_url="https://x.com/Heinrih5/status/2046914666694168667",
    ),
    # Kurmitis_ (175) -> Šlesers (3, LPV) — KNAB call to investigate flight tickets
    dict(
        source_pid=175, target_pid=3, topic="Tieslietas",
        tension_type="uzbrukums",
        description=(
            "@Kurmitis_ aicina KNAB un J. Straumi pārbaudīt Aināra Šlesera (LPV) "
            "lidojumu biļešu apmaksu — sarkastiski jautā, vai Šlesera divi "
            "'personāži' biļetes pirka paši, ar 'onkuli Orbānu' vai Ķīnas "
            "vēstniecības palīdzību. Konkrēta KNAB izmeklēšanas prasība."
        ),
        source_url="https://x.com/Kurmitis_/status/2044112079498379365",
    ),
]


def main() -> None:
    print(f"Registering {len(TENSIONS)} tensions...\n")
    for i, t in enumerate(TENSIONS, 1):
        try:
            tid = store_tension(**t)
            print(f"[{i}/{len(TENSIONS)}] OK tension_id={tid} "
                  f"{t['source_pid']}->{t['target_pid']} [{t['tension_type']}] {t['topic']}")
        except Exception as e:
            print(f"[{i}/{len(TENSIONS)}] FAIL {t['source_pid']}->{t['target_pid']}: "
                  f"{type(e).__name__}: {e}")


if __name__ == "__main__":
    main()
