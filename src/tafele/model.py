"""Izpētes tāfeles dati: ielāde un validācija.

Tāfele ir rakstu skats, ne avots: katrai saitei jābūt avotam, rakstam ar
enkuru un godīgam pierādījuma līmenim. Kļūdas tiek savāktas un paziņotas
visas kopā — viena kļūda nedrīkst noslēpt nākamo.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re
from typing import Any

import yaml

GRID = (1200, 820)
PUBLIC_PERSONS = frozenset({"linde", "hoppstaedter", "kanans", "divja", "kalvins", "rivza"})
ENTITY_TYPES = frozenset({"person", "company", "branch", "group", "institution", "law", "aggregate"})
LINK_KINDS = frozenset({"amats", "ipasums", "pilsoniba", "zoar", "adrese", "cits"})
ZONE_KINDS = frozenset({"registered", "portal", "branch", "institution", "foreign", "other"})
PERSON_COLORS = frozenset({"vis", "lin", "hop", "neu"})


class BoardError(Exception):
    """Tāfeles datu kļūda (struktūra vai saturs)."""


@dataclass(frozen=True)
class Source:
    label: str
    url: str


@dataclass(frozen=True)
class Fact:
    text: str
    source: Source
    article: str


@dataclass(frozen=True)
class Zone:
    id: str
    name: str
    kind: str
    note: str
    box: tuple[int, int, int, int]


@dataclass(frozen=True)
class Entity:
    id: str
    type: str
    name: str
    pos: tuple[int, int]
    summary: str
    zone: str | None = None
    color: str | None = None
    label: str | None = None
    facts: tuple[Fact, ...] = ()
    not_claimed: str | None = None
    unknown: str | None = None


@dataclass(frozen=True)
class Link:
    id: str
    from_id: str
    to_id: str
    verb: str
    period: str
    tier: int
    kind: str
    source: Source
    article: str
    quote: str | None = None
    caveat: str | None = None


@dataclass(frozen=True)
class Guide:
    article: str
    label: str
    links: tuple[str, ...]


@dataclass(frozen=True)
class Board:
    slug: str
    title: str
    data_date: str
    draft: bool
    articles: dict[str, str]
    zones: tuple[Zone, ...]
    entities: tuple[Entity, ...]
    links: tuple[Link, ...]
    guides: tuple[Guide, ...]

    def entity(self, eid: str) -> Entity | None:
        return next((e for e in self.entities if e.id == eid), None)


def _src(raw: Any, where: str) -> Source:
    if not isinstance(raw, dict):
        raise BoardError(f"{where}: trūkst avota (source)")
    return Source(label=_text(raw.get("label", "")), url=_text(raw.get("url", "")))


def _text(value: Any) -> str:
    if not isinstance(value, str):
        raise ValueError("sagaidīta virkne")
    return value


def _id(value: Any) -> str:
    value = _text(value)
    if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", value):
        raise ValueError(f"nederīgs identifikators: {value!r}")
    return value


def _optional_text(value: Any) -> str | None:
    return None if value is None else _text(value)


def _coords(value: Any, size: int) -> tuple[int, ...]:
    if not isinstance(value, list) or len(value) != size or any(type(v) is not int for v in value):
        raise ValueError(f"koordinātām jābūt {size} veselu skaitļu sarakstam")
    return tuple(value)


def _tier(value: Any) -> int:
    if type(value) is not int:
        raise ValueError("tier jābūt veselam skaitlim")
    return value


def load_board(path: Path) -> Board:
    try:
        raw = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:  # pragma: no cover — YAML sintakse
        raise BoardError(f"{path.name}: YAML neparsējas: {exc}") from exc
    if not isinstance(raw, dict):
        raise BoardError(f"{path.name}: sagaidīts YAML objekts")
    try:
        if type(raw.get("draft", True)) is not bool:
            raise ValueError("draft jābūt true vai false")
        for field in ("zones", "entities", "links", "guides"):
            if not isinstance(raw.get(field, []), list) or any(
                not isinstance(row, dict) for row in raw.get(field, [])
            ):
                raise ValueError(f"{field}: sagaidīts objektu saraksts")
        zones = tuple(Zone(id=_id(z["id"]), name=_text(z["name"]), kind=_text(z["kind"]), note=_text(z.get("note", "")),
                           box=_coords(z["box"], 4)) for z in raw.get("zones", []))
        entities = tuple(
            Entity(id=_id(e["id"]), type=_text(e["type"]), name=_text(e["name"]), pos=_coords(e["pos"], 2),
                   summary=_text(e.get("summary", "")), zone=_optional_text(e.get("zone")), color=_optional_text(e.get("color")),
                   label=_optional_text(e.get("label")),
                   facts=tuple(Fact(text=_text(f["text"]), source=_src(f.get("source"), e["id"]),
                                    article=_text(f.get("article", ""))) for f in e.get("facts", [])),
                   not_claimed=_optional_text(e.get("not_claimed")), unknown=_optional_text(e.get("unknown")))
            for e in raw.get("entities", []))
        links = tuple(
            Link(id=_id(l["id"]), from_id=_id(l["from"]), to_id=_id(l["to"]), verb=_text(l["verb"]),
                 period=str(l.get("period", "")), tier=_tier(l["tier"]), kind=_text(l["kind"]),
                 source=_src(l.get("source"), l["id"]), article=_text(l.get("article", "")),
                 quote=_optional_text(l.get("quote")), caveat=_optional_text(l.get("caveat")))
            for l in raw.get("links", []))
        guides = tuple(Guide(article=_text(g["article"]), label=_text(g["label"]), links=tuple(_id(v) for v in g.get("links", [])))
                       for g in raw.get("guides", []))
        articles = raw.get("articles", {})
        if not isinstance(articles, dict):
            raise ValueError("articles: sagaidīts objekts")
        return Board(slug=_id(raw["slug"]), title=_text(raw["title"]), data_date=str(raw["data_date"]),
                     draft=raw.get("draft", True), articles={_id(k): _text(v) for k, v in articles.items()},
                     zones=zones, entities=entities, links=links, guides=guides)
    except (KeyError, TypeError, ValueError) as exc:
        raise BoardError(f"{path.name}: nederīga datu struktūra: {exc}") from exc


def _article_state(articles_dir: Path, slug: str) -> str | None:
    """'published' | 'draft' | None (nav faila)."""
    # src.render.__init__ ielādē orķestratoru, kas importē šo datu modeli.
    # Kopīgo parsētāju importējam lietošanas brīdī, lai neveidotos cikls.
    from src.render._common.filters import _parse_frontmatter

    md = articles_dir / f"{slug}.md"
    if not md.exists():
        return None
    text = md.read_text(encoding="utf-8-sig")
    fm, _ = _parse_frontmatter(text)
    if not isinstance(fm, dict) or (text.startswith("---") and not fm):
        raise BoardError(f"{slug}: nederīgs frontmatter")
    return "draft" if fm.get("draft") else "published"


def validate_board(board: Board, articles_dir: Path, require_published: bool, *,
                   extra_persons: frozenset[str] = frozenset()) -> None:
    err: list[str] = []
    ids = [e.id for e in board.entities]
    known = set(ids)
    zone_ids = {z.id for z in board.zones}
    for dup in {i for i in ids if ids.count(i) > 1}:
        err.append(f"{dup}: dublēts kartītes id")
    allowed = PUBLIC_PERSONS | extra_persons
    w, h = GRID

    def check_article(owner: str, ref: str) -> None:
        slug, _, anchor = ref.partition("#")
        if not anchor:
            err.append(f"{owner}: raksta saitei trūkst enkura (#…): {ref!r}")
        if slug not in board.articles:
            err.append(f"{owner}: raksts {slug!r} nav sarakstā articles")
            return
        try:
            state = _article_state(articles_dir, slug)
        except BoardError as exc:
            err.append(f"{owner}: {exc}")
            return
        if state is None:
            err.append(f"{owner}: raksta fails {slug}.md neeksistē")
        elif require_published and state == "draft":
            err.append(f"{owner}: raksts {slug} vēl ir melnraksts")

    for e in board.entities:
        if e.type not in ENTITY_TYPES:
            err.append(f"{e.id}: nezināms veids {e.type!r}")
        if e.type == "person":
            if e.id not in allowed:
                err.append(f"{e.id}: persona nav publisko personu sarakstā")
            if e.color not in PERSON_COLORS:
                err.append(f"{e.id}: personas krāsai jābūt vienai no {sorted(PERSON_COLORS)}")
        x, y = e.pos
        if not (0 <= x <= w and 0 <= y <= h):
            err.append(f"{e.id}: pozīcija {e.pos} ārpus režģa {GRID}")
        if e.zone and e.zone not in zone_ids:
            err.append(f"{e.id}: nezināma zona {e.zone!r}")
        for i, f in enumerate(e.facts):
            if not f.source.url.startswith(("https://", "http://")):
                err.append(f"{e.id} fakts {i}: trūkst avota URL")
            check_article(f"{e.id} fakts {i}", f.article)

    for z in board.zones:
        if z.kind not in ZONE_KINDS:
            err.append(f"{z.id}: nezināms zonas veids {z.kind!r}")
        x, y, zw, zh = z.box
        if not (0 <= x < w and 0 <= y < h and zw > 0 and zh > 0 and x + zw <= w and y + zh <= h):
            err.append(f"{z.id}: zona ārpus režģa {GRID}")

    link_ids = [l.id for l in board.links]
    for dup in {i for i in link_ids if link_ids.count(i) > 1}:
        err.append(f"{dup}: dublēts saites id")
    for l in board.links:
        for end in (l.from_id, l.to_id):
            if end not in known:
                err.append(f"{l.id}: nezināma kartīte {end!r}")
        if l.tier not in (1, 2, 3):
            err.append(f"{l.id}: līmenim jābūt 1, 2 vai 3")
        if l.tier >= 2 and not (l.caveat or "").strip():
            err.append(f"{l.id}: {l.tier}. līmeņa saitei vajag atrunu pie diega (caveat)")
        if l.kind not in LINK_KINDS:
            err.append(f"{l.id}: nezināms saites veids {l.kind!r}")
        if not l.source.url.startswith(("https://", "http://")):
            err.append(f"{l.id}: trūkst avota URL")
        if not l.verb.strip():
            err.append(f"{l.id}: trūkst teikuma (verb)")
        check_article(l.id, l.article)

    lset = set(link_ids)
    for g in board.guides:
        if g.article not in board.articles:
            err.append(f"ceļvedis {g.label!r}: nezināms raksts {g.article!r}")
        for lid in g.links:
            if lid not in lset:
                err.append(f"ceļvedis {g.label!r}: nezināma saite {lid}")

    if err:
        raise BoardError("\n".join(sorted(err)))
