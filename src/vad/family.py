"""Politiķa deklarētā ģimene — TIKAI iekšējai lietošanai.

Ģimenes locekļu vārdus publiski nerādām (docs/data-policy.md § 1, operatora
lēmums 2026-11-27). Tos lieto divi lasītāji:

* `scripts/audit_vad_family_clusters.py` — vārdabrāļu atšķiršana pēc ģimenes;
* `src/render` — lai radinieka vārdu paslēptu arī tur, kur tas parādās citās
  deklarācijas sadaļās (dāvinājuma maksātājs, amata otra puse, kreditors).

Ģimene nāk no `vad_family` (jaunā forma) vai, ja deklarācijai to rindu nav, no
`raw_html` (vecā forma 2002–2013, ģimene §12 — `vad_family` to neraksta).
"""

from __future__ import annotations

import re
import sqlite3
import unicodedata
from collections import defaultdict
from typing import Iterable, Optional

from src.vad.parsing import parse_declaration_html


# VID vietturis nezināmam radiniekam — nav vārds.
_PLACEHOLDER_TOKENS = {"nezinams", "nezinama", "nav", "noradits"}
_WORD_RE = re.compile(r"[^\W\d_]+")


def name_tokens(text: Optional[str]) -> list[str]:
    """Vārdi salīdzināšanai: bez reģistra un bez garumzīmēm/mīkstinājumiem
    («Bērziņš» = «BERZINS»; SQLite UPPER LV burtus nelocī)."""
    folded = unicodedata.normalize("NFKD", (text or "").casefold())
    folded = "".join(c for c in folded if not unicodedata.combining(c))
    return _WORD_RE.findall(folded)


def name_variants(full_name: Optional[str]) -> list[frozenset[str]]:
    """Viena radinieka vārda kopas: «Anna Ozola/Bērziņa» → {anna, ozola} un
    {anna, berzina}. Mazāk par 2 vārdiem vai vietturis → nekas."""
    parts = (full_name or "").split()
    alts = parts[-1].split("/") if parts and "/" in parts[-1] else [None]
    out = []
    for alt in alts:
        words = parts[:-1] + [alt] if alt is not None else parts
        toks = frozenset(name_tokens(" ".join(words)))
        if len(toks) >= 2 and not toks <= _PLACEHOLDER_TOKENS:
            out.append(toks)
    return out


def contains_name(text: Optional[str], names: Iterable[frozenset[str]]) -> bool:
    """Vai laukā ir kāds no vārdiem — visi vārda vārdi laukā, jebkurā secībā,
    arī ar papildu tekstu («ANNA OZOLA, ,», «Ozola Anna (māte)»)."""
    toks = set(name_tokens(text))
    return any(n <= toks for n in names)


def declaration_families(
    db: sqlite3.Connection, opponent_ids: Iterable[int]
) -> dict[int, list[tuple[str, str]]]:
    """decl_id → [(radniecība, vārds)] visām šo politiķu deklarācijām."""
    pids = list(opponent_ids)
    if not pids:
        return {}
    marks = ",".join("?" * len(pids))
    out: dict[int, list[tuple[str, str]]] = defaultdict(list)
    for decl_id, relation, full_name in db.execute(
        f"SELECT f.declaration_id, f.relation, f.full_name FROM vad_family f "
        f"JOIN vad_declarations d ON d.id = f.declaration_id WHERE d.opponent_id IN ({marks})",
        pids,
    ):
        out[decl_id].append((relation, full_name))
    for decl_id, raw_html in db.execute(
        f"SELECT id, raw_html FROM vad_declarations WHERE opponent_id IN ({marks}) "
        f"AND raw_html IS NOT NULL AND id NOT IN (SELECT declaration_id FROM vad_family)",
        pids,
    ):
        fams = [(f.relation, f.full_name) for f in parse_declaration_html(raw_html).family]
        if fams:
            out[decl_id] = fams
    return dict(out)


def private_family_names(
    db: sqlite3.Connection, opponent_ids: Iterable[int]
) -> dict[int, set[frozenset[str]]]:
    """pid → radinieku vārdu kopas (`name_variants`), kas jāpaslēpj publiski.

    Visu politiķa deklarāciju apvienojums (pirmslaulību un laulības uzvārds
    abi). Izņēmuma nav — arī radinieku, kas pats ir politiķis, šeit slēpj
    (vārda sakritība nepierāda, ka tā ir tā pati persona). Izlaiž tikai paša
    politiķa vārdu (ja radiniekam tas pats vārds, nekas jauns netiek atklāts)."""
    pids = list(opponent_ids)
    if not pids:
        return {}
    marks = ",".join("?" * len(pids))
    own = {pid: frozenset(name_tokens(n)) for pid, n in db.execute(
        f"SELECT id, name FROM tracked_politicians WHERE id IN ({marks})", pids)}
    owner = dict(db.execute(
        f"SELECT id, opponent_id FROM vad_declarations WHERE opponent_id IN ({marks})", pids))
    out: dict[int, set[frozenset[str]]] = defaultdict(set)
    for decl_id, fams in declaration_families(db, pids).items():
        pid = owner[decl_id]
        for _relation, name in fams:
            for variant in name_variants(name):
                if variant != own.get(pid):
                    out[pid].add(variant)
    return dict(out)
