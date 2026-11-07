"""Skaitļu kolonnas markdown tabulās atpazīst automātiski (operators 2026-10-24).

Kļūme, ko ķer: balsojumu un naudas kolonnas stāvēja pa kreisi («63 : 10 : 1»
nav zem «0 : 27 : 51»), jo markdown autors neraksta `---:`. Kolonna ir skaitļu,
ja VISAS tās netukšās šūnas ir skaitļi; viena teksta šūna = kolonna paliek tāda.
"""
from bs4 import BeautifulSoup

from src.render._common.filters import _label_table_cells


def _table(head, rows):
    th = "".join(f"<th>{h}</th>" for h in head)
    body = "".join("<tr>" + "".join(f"<td>{c}</td>" for c in r) + "</tr>" for r in rows)
    return f"<table>\n<thead>\n<tr>{th}</tr>\n</thead>\n<tbody>{body}</tbody>\n</table>"


def _num_cols(html):
    soup = BeautifulSoup(_label_table_cells(html), "html.parser")
    heads = soup.select("thead th")
    return [h.get_text() for h in heads if "num" in (h.get("class") or [])], soup


def test_vote_money_percent_and_dash_columns_are_numeric():
    html = _table(
        ["Dokuments", "Par : pret : atturas", "Summa", "Daļa", "Izmaiņa"],
        [
            ["1590/Lp14", "63 : 10 : 1", "188 229 €", "12,5 %", "−1 234"],
            ["1591/Lp14", "0 : 27 : 51", "—", "100 %", "+3"],
        ],
    )
    cols, soup = _num_cols(html)
    assert cols == ["Par : pret : atturas", "Summa", "Daļa", "Izmaiņa"]
    assert all("num" in td["class"] for td in soup.select("tbody td:nth-of-type(2)"))


def test_one_text_cell_keeps_column_as_text_and_all_dash_is_not_numeric():
    html = _table(
        ["Gads", "Piezīme", "Tukšs"],
        [["2024", "teksts", "—"], ["nav zināms", "12", "—"]],
    )
    cols, _ = _num_cols(html)
    assert cols == []
