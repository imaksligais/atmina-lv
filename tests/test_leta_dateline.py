"""parse_leta_dateline: LETA datelines carry day + month but no year.

Failure it guards: a wrong year or a foreign/quoted date stored as
documents.published_at for leta.lv articles (2 577 NULL rows, 2026-10-14).
Forms below are taken verbatim from the corpus where marked.
"""
from datetime import date

import pytest

from src.ingest import leta_published_at, parse_leta_dateline

T = "Virsraksts\n"


@pytest.mark.parametrize("text, scraped, expected", [
    # Corpus forms — every month spelling seen 2026-03…10
    (T + "Rīga, 24. marts, LETA. Teksts", "2026-03-25 10:00:00", date(2026, 3, 24)),
    (T + "Rīga, 26. apr., LETA. Teksts", "2026-04-26 10:00:00", date(2026, 4, 26)),
    (T + "Rīga, 17. maijs, LETA. Teksts", "2026-05-18 12:37:13", date(2026, 5, 17)),
    (T + "Rīga, 2. jūn., LETA. Teksts", "2026-06-02 15:31:20", date(2026, 6, 2)),
    (T + "Rīga, 2. jūn.., LETA. Teksts", "2026-06-02 15:31:20", date(2026, 6, 2)),
    (T + "Rīga, 6. jūl., LETA. Teksts", "2026-07-06 22:49:36", date(2026, 7, 6)),
    (T + "Kijiva, 3. aug., LETA--UNIAN. Teksts", "2026-08-04 00:18:15", date(2026, 8, 3)),
    (T + "Rīga, 14. sept., LETA. Teksts", "2026-09-14 21:54:35", date(2026, 9, 14)),
    (T + "Kārdifa (Lielbritānija), 7. okt., LETA. Teksts", "2026-10-08 09:00:00", date(2026, 10, 7)),
    (T + "Luksemburga, 21. apr., LETA--AFP. Teksts", "2026-04-21 15:00:00", date(2026, 4, 21)),
    (T + "Kijiva, 1. aug., LETA--AFP/BBC/DPA/INTERFAX-UKRAINA/UKRAINSKA. T", "2026-08-01 20:00:00", date(2026, 8, 1)),
    # Corpus malformations: doc 73852 (no comma, multi-word agency), doc 87080 (",.")
    (T + "Kijiva, 25. jūl. LETA--UKRAINSKA PRAVDA. Ukraina", "2026-07-26 22:04:40", date(2026, 7, 25)),
    (T + "Rīga, 14. aug.,. LETA. Agrā piektdienas rītā", "2026-08-14 18:53:32", date(2026, 8, 14)),
    # Dateline on line 0 (no title) and after a two-line title
    ("Rīga, 3. okt., LETA. Teksts", "2026-10-03 19:46:55", date(2026, 10, 3)),
    ("Virsraksta 1. rinda\nVirsraksta 2. rinda\nRīga, 3. okt., LETA. T", "2026-10-03 19:00:00", date(2026, 10, 3)),
    # Months not yet in the corpus: abbreviated, full, ASCII
    (T + "Rīga, 15. janv., LETA. T", "2026-01-15 10:00:00", date(2026, 1, 15)),
    (T + "Rīga, 15. febr., LETA. T", "2026-02-15 10:00:00", date(2026, 2, 15)),
    (T + "Rīga, 15. nov., LETA. T", "2026-11-15 10:00:00", date(2026, 11, 15)),
    (T + "Rīga, 15. dec., LETA. T", "2026-12-15 10:00:00", date(2026, 12, 15)),
    (T + "Riga, 15. jun., LETA. T", "2026-06-15 10:00:00", date(2026, 6, 15)),
    (T + "Rīga, 15. septembris, LETA. T", "2026-09-15 10:00:00", date(2026, 9, 15)),
    # Year rollover: scraped in January, dateline in December
    (T + "Rīga, 31. dec., LETA. T", "2027-01-02 08:00:00", date(2026, 12, 31)),
    # Window edge: 7 days accepted, 8 rejected
    (T + "Rīga, 7. okt., LETA. T", "2026-10-14 10:00:00", date(2026, 10, 7)),
    (T + "Rīga, 6. okt., LETA. T", "2026-10-14 10:00:00", None),
    # A month later than scraped_at in the same year → last year → far outside window
    (T + "Rīga, 20. okt., LETA. T", "2026-10-14 10:00:00", None),
    # No dateline / not LETA / unknown month / impossible day
    (T + "Rīga, 24. marts, Delfi. Teksts", "2026-03-25 10:00:00", None),
    (T + "Bez datuma rindas teksts.", "2026-03-25 10:00:00", None),
    (T + "Rīga, 24. smarts, LETA. T", "2026-03-25 10:00:00", None),
    (T + "Rīga, 31. apr., LETA. T", "2026-05-01 10:00:00", None),
    ("", "2026-03-25 10:00:00", None),
])
def test_parse_leta_dateline(text, scraped, expected):
    assert parse_leta_dateline(text, scraped) == expected


def test_leta_published_at_format_and_domain_gate():
    text = T + "Rīga, 24. marts, LETA. Teksts"
    url = "https://www.leta.lv/home/important/F56547E5-264A-4BBC-B9F7-552C1AD21C4A"
    assert leta_published_at(url, text, "2026-03-25 10:00:00") == "2026-03-24T00:00:00"
    # Same text from another outlet is not trusted as a LETA dateline.
    assert leta_published_at("https://www.delfi.lv/x", text, "2026-03-25 10:00:00") is None
