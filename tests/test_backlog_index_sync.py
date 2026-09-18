"""`BACKLOG.md` indekss nedrīkst atpalikt no `backlog/*.md` tēmu failiem.

Kāpēc šis tests eksistē. Ieraksta pievienošana tēmas failam un indeksa
atjaunināšana ir DIVI soļi, un otrais tiek izlaists sistemātiski — trīs reizes
trijās dienās, katru reizi cita sesija:

  * 2026-08-23 audits izlaboja «64 pret 66» (trūka divi ieraksti).
  * 2026-08-24 sesija atrada to pašu no jauna (`agenti-pipeline` 12 pret 16,
    `matcher` 12 pret 13) un CHANGELOG-ā to nosauca par klasi, ne gadījumu.
  * 2026-08-25 sesija, pievienojot trīs jaunus ierakstus, ieviesa trīs jaunus
    driftus tajā pašā piegājienā — ieskaitot ierakstu PAR to, ka soļi tiek
    izlaisti.

`BACKLOG.md` preambula sauc indeksu par pirmo, ko lasa katra sesija, un tieši
nesinhrons indekss padara ierakstu neredzamu tam, kas seko norādei «lasi
indeksu pirmo». Skaitītājs ir lēts; klase nav.

**Paplašināts 2026-09-05 — skaitītājs viens pats bija vārti, kas nevar nokrist
šai klasei.** 2026-09-05 struktūras audits atrada divus statusa driftus, kurus
šis fails ar zaļu skrējienu nespēja ieraudzīt, jo tas skaitīja tikai `### `
rindas: «Render self-join» indeksā stāvēja `[DEFERRED]`, kamēr tēmas failā tas
bija `[SLĒGTS 2026-08-20 — kodols]` (t.i. jau padarīts darbs izskatījās
neaizsākts), un kandidātu panelim indekss bija nometis datumu no
`[IZPILDĪTS 2026-09-04]`. Skaits abos gadījumos sakrita perfekti. Tāpēc tagad
salīdzinām arī **statusa tagu pa ierakstam**, un indeksa rinda pēc konvencijas
ir tēmas faila `### ` virsraksts verbatim.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
INDEX = ROOT / "BACKLOG.md"
TOPIC_DIR = ROOT / "backlog"

# "**[`backlog/matcher.md`](backlog/matcher.md)** — 14 ieraksti:"
_INDEX_LINE = re.compile(
    r"\*\*\[`backlog/(?P<name>[a-z0-9-]+)\.md`\]\(backlog/(?P=name)\.md\)\*\*\s*—\s*"
    r"(?P<count>\d+)\s+ieraksti:"
)


def _index_counts() -> dict[str, int]:
    text = INDEX.read_text(encoding="utf-8")
    return {m.group("name"): int(m.group("count")) for m in _INDEX_LINE.finditer(text)}


def _entry_count(path: Path) -> int:
    """Ieraksts = `### ` virsraksts rindas sākumā (tā pati forma, ko lieto grep -c)."""
    return sum(1 for line in path.read_text(encoding="utf-8").splitlines()
               if line.startswith("### "))


# "- **[FIX]** Kaut kas" — indeksa ieraksta rinda zem faila virsraksta.
_INDEX_ENTRY = re.compile(r"^-\s+\*\*\[(?P<tag>[^\]]+)\]\*\*")
# "### [FIX] Kaut kas" — tēmas faila ieraksta virsraksts.
_TOPIC_HEADING = re.compile(r"^###\s+\[(?P<tag>[^\]]+)\]")


def _index_tags() -> dict[str, list[str]]:
    """Statusa tagi indeksā, faila → tagu saraksts ieraksta secībā."""
    tags: dict[str, list[str]] = {}
    current: str | None = None
    for line in INDEX.read_text(encoding="utf-8").splitlines():
        header = _INDEX_LINE.search(line)
        if header:
            current = header.group("name")
            tags[current] = []
            continue
        if current is None:
            continue
        entry = _INDEX_ENTRY.match(line)
        if entry:
            tags[current].append(entry.group("tag"))
        elif line.startswith("## "):
            current = None
    return tags


def _topic_tags(path: Path) -> list[str]:
    """Statusa tagi tēmas failā, `### ` virsrakstu secībā."""
    out: list[str] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.startswith("### "):
            continue
        m = _TOPIC_HEADING.match(line)
        assert m, f"`{path.name}`: `### ` virsraksts bez statusa taga: {line!r}"
        out.append(m.group("tag"))
    return out


def test_index_lists_every_topic_file():
    """Saucējs, ne tikai atradums: katram failam jābūt indeksā un otrādi."""
    on_disk = {p.stem for p in TOPIC_DIR.glob("*.md")}
    in_index = set(_index_counts())
    assert on_disk, "backlog/ ir tukšs — salūzis tests, ne tīrs rezultāts"
    assert on_disk == in_index, (
        f"indekss un backlog/ nesakrīt.\n"
        f"  tikai diskā: {sorted(on_disk - in_index)}\n"
        f"  tikai indeksā: {sorted(in_index - on_disk)}"
    )


@pytest.mark.parametrize("name", sorted(p.stem for p in TOPIC_DIR.glob("*.md")))
def test_index_count_matches_topic_file(name: str):
    counts = _index_counts()
    assert name in counts, f"`backlog/{name}.md` nav pieteikts BACKLOG.md indeksā"
    actual = _entry_count(TOPIC_DIR / f"{name}.md")
    assert counts[name] == actual, (
        f"`backlog/{name}.md`: indekss saka {counts[name]}, failā ir {actual} `### ` ierakstu. "
        f"Pievienojot vai izgriežot ierakstu, atjauno ARĪ BACKLOG.md indeksa rindu un skaitli."
    )


@pytest.mark.parametrize("name", sorted(p.stem for p in TOPIC_DIR.glob("*.md")))
def test_index_status_tags_match_topic_file(name: str):
    """Skaits vien nepietiek — arī STATUSA TAGS jāsakrīt, ieraksts pa ierakstam.

    Saucējs izvadā ir apzināts: ja indeksa blokā ir 0 aizzīmju, tas nav tīrs
    rezultāts, bet salauzts parseris (`_INDEX_ENTRY` forma nomainījusies).
    """
    topic = _topic_tags(TOPIC_DIR / f"{name}.md")
    index = _index_tags().get(name)
    assert index is not None, f"`backlog/{name}.md` nav pieteikts BACKLOG.md indeksā"
    assert topic, f"`backlog/{name}.md` nesatur nevienu `### ` ierakstu — salūzis tests, ne tīrs rezultāts"
    assert index, (
        f"`backlog/{name}.md` indeksa blokā 0 aizzīmju rindu, kaut failā ir {len(topic)} "
        f"ierakstu — vārti, kas nevar nokrist. Pārbaudi indeksa rindu formu "
        f"(`- **[TAGS]** virsraksts`)."
    )
    assert index == topic, (
        f"`backlog/{name}.md`: statusa tagi indeksā un failā atšķiras "
        f"(saucējs: {len(topic)} ieraksti failā, {len(index)} indeksā).\n"
        f"  indeksā: {index}\n"
        f"  failā:   {topic}\n"
        f"Indeksa rinda pēc konvencijas ir `### ` virsraksts VERBATIM — ja maini "
        f"statusu tēmas failā, maini to arī indeksā."
    )
