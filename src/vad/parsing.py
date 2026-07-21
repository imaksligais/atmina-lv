"""Parse VID amatpersonu deklarāciju HTML uz strukturētu Pydantic modeli.

Spec: docs/superpowers/specs/2026-05-02-vad-deklaracijas-design.md § 5

Algoritms:
1. Atver HTML ar BeautifulSoup
2. Header tabula = pirmā <table> pirms pirmās numurētās <h2>
3. Katra numurētā <h2> regex `^\\s*(\\d+)\\.\\s+` ieskicē sekciju
4. Iterē DOM siblings līdz nākamai <h2>
5. Sekcijas saturs = visas <table> tās ietvaros (sec 6 ir 2 tabulas)
6. Narratīvās sekcijas (4b, 11, 11b, 13) = <h2> + nākamie <p>
"""

from __future__ import annotations

import re
from typing import Optional

from bs4 import BeautifulSoup, Tag
from pydantic import BaseModel, Field

ALLOWED_CURRENCIES = {"EUR", "USD", "RUB", "GBP", "JPY", "CHF", "SEK", "NOK", "DKK"}

_H2_NUMBERED = re.compile(r"^\s*(\d+)\.\s+")
_DATE_RE = re.compile(r"(\d{2})\.(\d{2})\.(\d{4})")
_REG_NUMBER_RE = re.compile(r"\b[49]\d{10}\b")  # Latvijas reģ.nr.: 11 cipari, sākas ar 4 vai 9


class VadHeader(BaseModel):
    declaration_type: str
    declaration_kind: str  # normalized: annual|start|end|post_year_1|post_year_2|interim
    declaration_year: Optional[int]
    full_name: str
    institution: str
    position_title: str
    submitted_at: Optional[str]
    published_at: Optional[str]


class VadPositionRow(BaseModel):
    position_title: str
    entity_name: str
    entity_reg_number: Optional[str] = None
    entity_address: Optional[str] = None
    is_individual: bool = False


class VadRealEstateRow(BaseModel):
    property_type: str
    location: str
    ownership_status: str


class VadCompanyRow(BaseModel):
    company_name: str
    reg_number: Optional[str] = None
    address: Optional[str] = None
    capital_kind: str
    units: Optional[float] = None
    total_value: Optional[float] = None
    currency: Optional[str] = None


class VadVehicleRow(BaseModel):
    vehicle_type: str
    brand: str
    year_made: Optional[int] = None
    year_registered: Optional[int] = None
    ownership_status: str


class VadSavingsRow(BaseModel):
    savings_kind: str  # "cash" | "bank"
    amount: float
    currency: str
    amount_in_words: Optional[str] = None
    holder_name: Optional[str] = None
    holder_reg_number: Optional[str] = None
    holder_address: Optional[str] = None


class VadIncomeRow(BaseModel):
    source: str
    source_reg_number: Optional[str] = None
    is_individual: bool = False
    income_type: str
    amount: float
    currency: str


class VadTransactionRow(BaseModel):
    transaction_description: str
    amount: Optional[float] = None
    currency: Optional[str] = None


class VadDebtRow(BaseModel):
    creditor_name: str
    creditor_reg_number: Optional[str] = None
    creditor_address: Optional[str] = None
    amount: float
    currency: str
    amount_in_words: Optional[str] = None


class VadLoanGivenRow(BaseModel):
    amount: float
    currency: str
    amount_in_words: Optional[str] = None


class VadFamilyRow(BaseModel):
    full_name: str
    relation: str


class ParsedDeclaration(BaseModel):
    header: VadHeader
    positions: list[VadPositionRow] = Field(default_factory=list)
    real_estate: list[VadRealEstateRow] = Field(default_factory=list)
    companies: list[VadCompanyRow] = Field(default_factory=list)
    financial_instruments_text: Optional[str] = None
    vehicles: list[VadVehicleRow] = Field(default_factory=list)
    savings: list[VadSavingsRow] = Field(default_factory=list)
    income: list[VadIncomeRow] = Field(default_factory=list)
    transactions: list[VadTransactionRow] = Field(default_factory=list)
    debts: list[VadDebtRow] = Field(default_factory=list)
    loans_given: list[VadLoanGivenRow] = Field(default_factory=list)
    other_benefits_text: Optional[str] = None
    trust_agreement_text: Optional[str] = None
    has_private_pension: Optional[bool] = None
    has_life_insurance: Optional[bool] = None
    other_info: Optional[str] = None
    family: list[VadFamilyRow] = Field(default_factory=list)


def parse_declaration_html(html: str) -> ParsedDeclaration:
    """Parse a modern VID amatpersonu deklarācijas detail HTML page."""
    soup = BeautifulSoup(html, "html.parser")
    header = _parse_header(soup)
    sections = _split_sections(soup)
    return ParsedDeclaration(
        header=header,
        positions=_parse_positions(sections.get(2)),
        real_estate=_parse_real_estate(sections.get(3)),
        companies=_parse_companies(sections.get(4)),
        financial_instruments_text=_parse_financial_instruments(soup),
        vehicles=_parse_vehicles(sections.get(5)),
        savings=_parse_savings(sections.get(6)),
        income=_parse_income(sections.get(7)),
        transactions=_parse_transactions(sections.get(8)),
        debts=_parse_debts(sections.get(9)),
        loans_given=_parse_loans_given(sections.get(10)),
        other_benefits_text=_parse_other_benefits(soup),
        trust_agreement_text=_parse_trust_agreement(soup),
        has_private_pension=_parse_pension_flag(sections.get(12), 0),
        has_life_insurance=_parse_pension_flag(sections.get(12), 1),
        other_info=_parse_other_info(sections.get(13)),
        family=_parse_family(sections.get(14)),
    )


def _norm_date(text: str) -> Optional[str]:
    m = _DATE_RE.search(text or "")
    if not m:
        return None
    dd, mm, yyyy = m.groups()
    return f"{yyyy}-{mm}-{dd}"


def _norm_year(text: str) -> Optional[int]:
    m = re.search(r"par\s+(\d{4})\.\s*gadu", text or "")
    return int(m.group(1)) if m else None


def _norm_kind(declaration_type: str) -> str:
    t = declaration_type.lower()
    if "kārtējā gada" in t or "ikgadējā" in t:
        return "annual"
    if "darba sākuma" in t:
        return "start"
    if "beidzot pildīt" in t:
        return "end"
    if "par pirmo gadu" in t:
        return "post_year_1"
    if "par otro gadu" in t:
        return "post_year_2"
    return "interim"


def _norm_currency(text: str) -> Optional[str]:
    text = (text or "").strip().upper()
    if text in ALLOWED_CURRENCIES:
        return text
    return text or None


def _norm_amount(text: str) -> Optional[float]:
    text = (text or "").strip().replace(" ", "").replace(",", ".")
    try:
        return float(text)
    except (ValueError, TypeError):
        return None


def _clean_cell(text: str) -> str:
    """Normalize whitespace including non-breaking spaces."""
    return " ".join(text.replace("\xa0", " ").split())


def _parse_header(soup: BeautifulSoup) -> VadHeader:
    table = soup.find("table")
    if table is None:
        raise ValueError("nav header table")
    fields: dict[str, str] = {}
    for row in table.find_all("tr"):
        cells = [_clean_cell(c.get_text(" ", strip=True)) for c in row.find_all(["td", "th"])]
        if len(cells) >= 2:
            fields[cells[0].rstrip(":").strip()] = cells[1]
    decl_type = fields.get("Deklarācijas veids", "")
    full_name = fields.get("Vārds, uzvārds", "")
    institution = fields.get(
        "Darbavieta vai valsts amatpersonu saraksta iesniedzējas institūcija", ""
    )
    position_title = fields.get("Valsts amatpersonas amats", "")
    if not decl_type or not full_name:
        raise ValueError(f"nepilnīgs header: {fields!r}")
    return VadHeader(
        declaration_type=decl_type,
        declaration_kind=_norm_kind(decl_type),
        declaration_year=_norm_year(decl_type),
        full_name=full_name,
        institution=institution,
        position_title=position_title,
        submitted_at=_norm_date(fields.get("Iesniegta VID", "")),
        published_at=_norm_date(fields.get("Publicēta", "")),
    )


def _split_sections(soup: BeautifulSoup) -> dict[int, list[Tag]]:
    out: dict[int, list[Tag]] = {}
    h2s = soup.find_all("h2")
    for h2 in h2s:
        text = h2.get_text(" ", strip=True)
        m = _H2_NUMBERED.match(text)
        if not m:
            continue
        n = int(m.group(1))
        siblings: list[Tag] = []
        for sib in h2.find_next_siblings():
            if sib.name == "h2" and _H2_NUMBERED.match(sib.get_text(" ", strip=True)):
                break
            if isinstance(sib, Tag):
                siblings.append(sib)
        out[n] = siblings
    return out


def _table_rows(siblings: Optional[list[Tag]]) -> list[list[str]]:
    if not siblings:
        return []
    rows = []
    for sib in siblings:
        tables_in_sib = [sib] if sib.name == "table" else sib.find_all("table")
        for table in tables_in_sib:
            tbodies = table.find_all("tbody")
            if len(tbodies) >= 2:
                data_tbody = tbodies[1]
            elif tbodies:
                data_tbody = tbodies[0]
            else:
                data_tbody = table
            for tr in data_tbody.find_all("tr"):
                cells = [td.get_text(" ", strip=True) for td in tr.find_all(["td", "th"])]
                if cells:
                    rows.append(cells)
    return rows


def _parse_positions(siblings) -> list[VadPositionRow]:
    out = []
    for cells in _table_rows(siblings):
        if len(cells) < 3:
            continue
        position_title, entity_name, third = cells[0], cells[1], cells[2]
        reg = None
        addr = None
        m = _REG_NUMBER_RE.search(third)
        if m:
            reg = m.group(0)
            addr = (third[:m.start()] + third[m.end():]).strip(", ").strip() or None
        else:
            addr = third or None
        out.append(VadPositionRow(
            position_title=position_title, entity_name=entity_name,
            entity_reg_number=reg, entity_address=addr,
            is_individual=(reg is None and "," not in (entity_name or "")),
        ))
    return out


def _parse_real_estate(siblings) -> list[VadRealEstateRow]:
    out = []
    for cells in _table_rows(siblings):
        if len(cells) < 3:
            continue
        out.append(VadRealEstateRow(
            property_type=cells[0], location=cells[1], ownership_status=cells[2],
        ))
    return out


def _parse_companies(siblings) -> list[VadCompanyRow]:
    out = []
    for cells in _table_rows(siblings):
        if len(cells) < 6:
            continue
        company_name, ra, capital_kind, units, total, cur = cells[:6]
        reg = None
        addr = None
        m = _REG_NUMBER_RE.search(ra)
        if m:
            reg = m.group(0)
            addr = (ra[:m.start()] + ra[m.end():]).strip(", ").strip() or None
        else:
            addr = ra or None
        out.append(VadCompanyRow(
            company_name=company_name, reg_number=reg, address=addr,
            capital_kind=capital_kind,
            units=_norm_amount(units), total_value=_norm_amount(total),
            currency=_norm_currency(cur),
        ))
    return out


def _parse_vehicles(siblings) -> list[VadVehicleRow]:
    out = []
    for cells in _table_rows(siblings):
        if len(cells) < 5:
            continue
        ym = cells[2].strip() or None
        yr = cells[3].strip() or None
        out.append(VadVehicleRow(
            vehicle_type=cells[0], brand=cells[1],
            year_made=int(ym) if ym and ym.isdigit() else None,
            year_registered=int(yr) if yr and yr.isdigit() else None,
            ownership_status=cells[4],
        ))
    return out


def _parse_savings(siblings) -> list[VadSavingsRow]:
    out = []
    if not siblings:
        return out
    tables = []
    for sib in siblings:
        if sib.name == "table":
            tables.append(sib)
        else:
            tables.extend(sib.find_all("table"))
    for table in tables:
        header_cells = []
        thead_or_first = table.find("thead") or table.find("tbody")
        if thead_or_first:
            first_tr = thead_or_first.find("tr")
            if first_tr:
                header_cells = [c.get_text(" ", strip=True).lower() for c in first_tr.find_all(["th", "td"])]
        is_bank = any("bezskaidr" in h or "turētāj" in h for h in header_cells)
        kind = "bank" if is_bank else "cash"
        tbodies = table.find_all("tbody")
        data_tbody = tbodies[1] if len(tbodies) >= 2 else (tbodies[0] if tbodies else table)
        for tr in data_tbody.find_all("tr"):
            cells = [c.get_text(" ", strip=True) for c in tr.find_all(["td", "th"])]
            if not cells:
                continue
            if kind == "cash" and len(cells) >= 3:
                amt = _norm_amount(cells[0])
                cur = _norm_currency(cells[1])
                if amt is None or cur is None:
                    continue
                out.append(VadSavingsRow(
                    savings_kind="cash", amount=amt, currency=cur,
                    amount_in_words=cells[2] or None,
                ))
            elif kind == "bank" and len(cells) >= 4:
                amt = _norm_amount(cells[0])
                cur = _norm_currency(cells[1])
                if amt is None or cur is None:
                    continue
                holder_addr = cells[3] if len(cells) >= 4 else None
                holder_reg = None
                m = _REG_NUMBER_RE.search(holder_addr or "")
                if m:
                    holder_reg = m.group(0)
                    holder_addr = (holder_addr[:m.start()] + holder_addr[m.end():]).strip(", ").strip() or None
                out.append(VadSavingsRow(
                    savings_kind="bank", amount=amt, currency=cur,
                    holder_name=cells[2] or None,
                    holder_reg_number=holder_reg, holder_address=holder_addr,
                ))
    return out


def _parse_income(siblings) -> list[VadIncomeRow]:
    out = []
    seen: set[tuple] = set()
    for cells in _table_rows(siblings):
        if len(cells) < 4:
            continue
        source, income_type, amount_str, cur = cells[:4]
        amount = _norm_amount(amount_str)
        currency = _norm_currency(cur)
        if amount is None or currency is None:
            continue
        m = _REG_NUMBER_RE.search(source)
        reg = m.group(0) if m else None
        # Deduplicate: same (source, reg_number, income_type, amount, currency) within a declaration.
        # VAD HTML sometimes contains duplicate <tr> rows for the same income entry.
        dedup_key = (source, reg, income_type, amount, currency)
        if dedup_key in seen:
            continue
        seen.add(dedup_key)
        # Individual if no reg number and source contains only names (ends with trailing comma/spaces)
        is_individual = reg is None and bool(re.search(r",\s*,?\s*$", source))
        out.append(VadIncomeRow(
            source=source, source_reg_number=reg, is_individual=is_individual,
            income_type=income_type, amount=amount, currency=currency,
        ))
    return out


def _parse_transactions(siblings) -> list[VadTransactionRow]:
    out = []
    for cells in _table_rows(siblings):
        if not cells:
            continue
        desc = cells[0]
        amt = _norm_amount(cells[1]) if len(cells) > 1 else None
        cur = _norm_currency(cells[2]) if len(cells) > 2 else None
        out.append(VadTransactionRow(
            transaction_description=desc, amount=amt, currency=cur,
        ))
    return out


def _parse_debts(siblings) -> list[VadDebtRow]:
    out = []
    for cells in _table_rows(siblings):
        if len(cells) < 4:
            continue
        creditor = cells[0]
        ra = cells[1] if len(cells) > 1 else ""
        amt = _norm_amount(cells[2] if len(cells) > 2 else "")
        cur = _norm_currency(cells[3] if len(cells) > 3 else "")
        words = cells[4] if len(cells) > 4 else None
        if amt is None or cur is None:
            continue
        reg = None
        addr = None
        m = _REG_NUMBER_RE.search(ra)
        if m:
            reg = m.group(0)
            addr = (ra[:m.start()] + ra[m.end():]).strip(", ").strip() or None
        else:
            addr = ra or None
        out.append(VadDebtRow(
            creditor_name=creditor, creditor_reg_number=reg, creditor_address=addr,
            amount=amt, currency=cur, amount_in_words=words,
        ))
    return out


def _parse_loans_given(siblings) -> list[VadLoanGivenRow]:
    out = []
    for cells in _table_rows(siblings):
        if len(cells) < 3:
            continue
        amt = _norm_amount(cells[0])
        cur = _norm_currency(cells[1])
        if amt is None or cur is None:
            continue
        out.append(VadLoanGivenRow(
            amount=amt, currency=cur, amount_in_words=cells[2] or None,
        ))
    return out


def _parse_pension_flag(siblings, idx: int) -> Optional[bool]:
    rows = _table_rows(siblings)
    if not rows or len(rows[0]) <= idx:
        return None
    val = (rows[0][idx] or "").strip().lower()
    if val == "ir":
        return True
    if val == "nav":
        return False
    return None


def _parse_family(siblings) -> list[VadFamilyRow]:
    out = []
    for cells in _table_rows(siblings):
        if len(cells) < 2:
            continue
        out.append(VadFamilyRow(full_name=cells[0], relation=cells[1]))
    return out


def _narrative_after_h2(soup: BeautifulSoup, h2_match: str) -> Optional[str]:
    for h2 in soup.find_all("h2"):
        if h2_match.lower() in h2.get_text(" ", strip=True).lower():
            paragraphs = []
            for sib in h2.find_next_siblings():
                if sib.name == "h2":
                    break
                if sib.name in ("p", "div"):
                    text = sib.get_text(" ", strip=True)
                    if text:
                        paragraphs.append(text)
            return "\n\n".join(paragraphs) if paragraphs else None
    return None


def _parse_financial_instruments(soup):
    return _narrative_after_h2(soup, "finanšu instrumenti")


def _parse_other_benefits(soup):
    return _narrative_after_h2(soup, "noziedzīgi iegūtu līdzekļu")


def _parse_trust_agreement(soup):
    return _narrative_after_h2(soup, "trasta līgums")


def _parse_other_info(siblings):
    if not siblings:
        return None
    paragraphs = []
    for sib in siblings:
        if sib.name in ("p", "div"):
            text = sib.get_text(" ", strip=True)
            if text:
                paragraphs.append(text)
    return "\n\n".join(paragraphs) if paragraphs else None
