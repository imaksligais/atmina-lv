"""Retrofetch Vitenbergs 2020-2022 publiska komunikācija — EM Kariņa I valdībā.

Mērķis: ielikt DB vēsturisko substrātu klimata/atjaunojamās enerģijas pretrunu hunt
pret 2026-05-25 retoriku (claim #20850: "klimata jautājumi, iespējams, jāiepauzē"
kā Klimata un enerģētikas ministra kandidāts).

Pattern follows Sprūds/Indriksone/Šuvajevs retrofetches (skipl 2026-05-11/12) —
hardcoded URL list, httpx+trafilatura fetch, insert_document, link junction.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import httpx  # noqa: E402
import trafilatura  # noqa: E402

from src.db import insert_document  # noqa: E402
from src.matcher import link_politicians_to_documents  # noqa: E402
from src.ingest import _extract_published_at  # noqa: E402
from src.title_extract import extract_title  # noqa: E402

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/131.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "lv,en;q=0.5",
}

# Hardcoded candidate URLs from WebSearch (2026-05-26) — EM tenūra 2020-11 → 2022-05.
# Focus: enerģētika, OIK, vēja parki, Eiropas Zaļais kurss, COVID-ekonomikas balanss.
CANDIDATES = [
    # TVNet — Vitenbergs as subject (URL contains his name OR he is primary speaker)
    "https://www.tvnet.lv/7419688/vitenbergs-jauna-gada-pirmaja-darbdiena-sasaucis-valsts-energetiskas-krizes-centra-sedi",
    "https://www.tvnet.lv/7440942/vitenbergs-valdibai-jalemj-par-ierobezojumu-atcelsanu-lai-uznemeji-spetu-planoti-stradat",
    "https://www.tvnet.lv/7166350/nakamnedel-piedavas-jaunu-ierobezojumu-modeli-kas-laus-stradat-visiem-tirgotajiem",
    "https://www.tvnet.lv/6939895/ekonomikas-ministra-amata-apstiprinats-janis-vitenbergs",
    "https://www.tvnet.lv/7526597/karins-pauz-ka-vitenbergs-parak-paklavas-uznemeju-lobija-interesem",
    "https://www.tvnet.lv/7245911/kpv-lv-deputati-plano-velreiz-spriest-vai-vitenbergs-drikstetu-saglabat-ekonomikas-ministra-amatu",
    "https://www.tvnet.lv/4572679/oik-atlaides-energoietilpigajiem-razotajiem-paredzets-kompenset-no-latvenergo-dividendem",
    "https://www.tvnet.lv/6835245/tiks-veidota-nacionala-energetikas-un-klimata-padome",
    # LSM — "Vitenbergs:" headlines + topic articles
    "https://www.lsm.lv/raksts/zinas/ekonomika/vitenbergs-nepieciesams-atrast-balansu-starp-veselibas-un-ekonomikas-nozarem.a375904/",
    "https://www.lsm.lv/raksts/zinas/ekonomika/veja-parku-attistisanai-plano-veidotlatvenergo-un-latvijas-valsts-mezu-kopuznemumu.a444777/",
    "https://www.lsm.lv/raksts/zinas/ekonomika/em-par-oik-reviziju-tas-bus-vertigs-dokuments-energetikas-politikas-pilnveidei.a388027/",
    "https://www.lsm.lv/raksts/zinas/ekonomika/eiropas-zalais-kurss-bus-liels-izaicinajums-gan-latvijas-uznemejiem-gan-politikiem.a426052/",
    "https://www.lsm.lv/raksts/zinas/ekonomika/latvija-darbojas-tikai-divi-veja-parki-to-attistisanu-kave-nesakartota-likumdosana-un-iedzivotaju-iebildumi.a436148/",
    "https://www.lsm.lv/raksts/zinas/ekonomika/kadel-latvija-kutri-izmanto-saules-un-veja-energiju.a404318/",
    "https://www.lsm.lv/raksts/zinas/ekonomika/valdiba-apsver-iespeju-samazinat-pvn-likmi-elektroenergijai.a433301/",
    "https://www.lsm.lv/raksts/zinas/ekonomika/eiropas-zalais-kurss-var-veicinat-elektribas-cenu-kapumu.a421523/",
    "https://www.lsm.lv/raksts/zinas/ekonomika/latvija-un-igaunija-plano-piesaistit-es-finansejumu-veja-parka-vietas-izpetei-rigas-lici.a369150/",
    "https://www.lsm.lv/raksts/zinas/ekonomika/sak-veja-parka-targale-buvniecibu-ventspils-novada.a398548/",
    "https://www.lsm.lv/raksts/zinas/ekonomika/latvijas-un-igaunijas-kopprojekta-veja-parku-jura-varetu-veidot-kurzemes-piekraste.a438282/",
    "https://www.lsm.lv/raksts/zinas/latvija/kpv-lv-valde-atsauc-ekonomikas-ministru-vitenbergu-no-amata-pec-vina-pievienosanas-na.a401530/",
    "https://www.lsm.lv/raksts/zinas/latvija/premjers-nevaru-piekrist-ka-vitenbergs-ir-vajs-ekonomikas-ministrs.a457098/",
    "https://www.lsm.lv/raksts/zinas/ekonomika/vitenbergs-atteicies-klut-par-ekonomikas-ministrijas-parlamentaro-sekretaru.a459183/",
    "https://www.lsm.lv/raksts/zinas/latvija/pavluts-koalicija-pastav-uzskats-ka-vitenbergs-ir-salidzinosi-vajs-ministrs.a457073/",
]


def fetch_one(client: httpx.Client, url: str) -> dict | None:
    try:
        resp = client.get(url)
        resp.raise_for_status()
    except Exception as e:
        print(f"  ERR fetch  {url[:80]}: {e}")
        return None

    text = trafilatura.extract(
        resp.text, include_comments=False, include_tables=False, deduplicate=True
    )
    if not text or len(text) < 150:
        print(f"  SKIP thin  {url[:80]}: {len(text or '')} chars")
        return None

    if "Vitenberg" not in text:
        print(f"  SKIP nm     {url[:80]}: no Vitenberg mention")
        return None

    title = extract_title(resp.text)
    pub_at = _extract_published_at(resp.text)
    return {
        "url": url,
        "title": title,
        "published_at": pub_at,
        "text": text[:50000],
    }


def main() -> None:
    print(f"Vitenbergs 2020-2022 retrofetch — {len(CANDIDATES)} candidates")
    print()

    fetched: list[dict] = []
    with httpx.Client(timeout=20.0, follow_redirects=True, headers=HEADERS) as client:
        for url in CANDIDATES:
            item = fetch_one(client, url)
            if item:
                fetched.append(item)
                print(f"  OK   {len(item['text']):>5}  pub={item['published_at'] or '?'}  {item['title'][:60] if item['title'] else url[-50:]}")

    print()
    print(f"Fetched {len(fetched)}/{len(CANDIDATES)}. Inserting docs + linking...")
    print()

    stored_ids: list[int] = []
    for item in fetched:
        doc_id = insert_document(
            content=item["text"],
            source_id=None,
            platform="web",
            language="lv",
            source_url=item["url"],
            published_at=item["published_at"],
            title=item["title"],
        )
        if doc_id is None:
            print(f"  DUPE  {item['url'][:80]} — content already in DB")
        else:
            stored_ids.append(doc_id)
            print(f"  doc#{doc_id:>6}  pub={item['published_at'] or '?'}  {item['url'][-60:]}")

    print()
    print(f"Stored {len(stored_ids)} new docs.")
    print()

    # Rescan all recently-added documents and link politicians.
    print("Running link_politicians_to_documents(rescan_all=True, days=1)...")
    linked = link_politicians_to_documents(days=1, rescan_all=True)
    vit_docs = [d for d, pids in linked.items() if 139 in pids]
    print(f"  Total docs linked this scan: {len(linked)}")
    print(f"  Vitenbergs (pid=139) linked to: {len(vit_docs)} docs")
    if vit_docs:
        print(f"  doc_ids: {sorted(vit_docs)}")


if __name__ == "__main__":
    main()
