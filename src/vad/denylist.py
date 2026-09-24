"""VAD deklarāciju deny-list — aizsardzība pret homonīmu atkārtotu ievākšanu.

Spec konteksts: data/NVO/izpete_2026-08-12/vad_homonimu_adjudikacija.md;
purge rollback: data/rollback_vad_homonimu_purge_2026-08-12.sql.

Fons (BACKLOG backlog/vad.md): pid=146 (Andris Bērziņš) vad_disambig hinti
principiāli nešķir divus Saeimas deputātus ar vienu vārdu — abu amata teksts ir
„Saeimas deputāts / Latvijas Republikas Saeima". Nākotnes VAD sweep var atkal
ievilkt LPP/LC Bērziņa deklarācijas. Deny-list bloķē zināmās svešās rindas pirms
disambig/dedup soļiem.

Divas kājas (vad_uuid rotē per-session — operacijas.md § VAD, F14):
  - STABILĀ kāja ``match`` {kind, year}: dzīva pāri sesijām. Lietota tikai tur,
    kur gads ir rekonstruējams no search-rindas etiķetes (annual/2009, /2010) un
    apstiprināti nekrīt ar paša politiķa likumīgām rindām.
  - UUID kāja (``match`` nav): vienreizēja; VID var rotēt uuid un kāja klusi
    zaudē spēku — tāpēc katrs uuid-trāpījums log'o loud, un pēc sweep manuālā
    pārbaude paliek pastāvīgs tīkls (backlog/vad.md).

Formāts (data/vad_denylist.json): atslēgas ar "_" priekšpēdēju ir komentāri.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path

log = logging.getLogger(__name__)

DEFAULT_DENYLIST_PATH = Path(__file__).resolve().parents[2] / "data" / "vad_denylist.json"


@dataclass(frozen=True)
class DenyEntry:
    pid: int
    vad_uuid: str
    match_kind: str | None  # None → tikai uuid kāja
    match_year: int | None
    reason: str


@dataclass(frozen=True)
class VadDenylist:
    entries: tuple[DenyEntry, ...] = field(default_factory=tuple)

    def by_pid(self, pid: int) -> tuple[DenyEntry, ...]:
        return tuple(e for e in self.entries if e.pid == pid)

    def __bool__(self) -> bool:
        return bool(self.entries)


def load_denylist(path: Path | None = None) -> VadDenylist:
    """Ielādē deny-list no JSON. Trūkstošs fails → tukšs saraksts (nav kļūda)."""
    p = path or DEFAULT_DENYLIST_PATH
    if not p.exists():
        return VadDenylist()
    raw = json.loads(p.read_text(encoding="utf-8"))
    items = raw.get("entries", []) if isinstance(raw, dict) else []
    entries = []
    for item in items:
        match = item.get("match")
        entries.append(DenyEntry(
            pid=int(item["pid"]),
            vad_uuid=str(item["vad_uuid"]),
            match_kind=str(match["kind"]) if match else None,
            match_year=int(match["year"]) if match and match.get("year") is not None else None,
            reason=str(item.get("reason", "")),
        ))
    n_uuid_only = sum(1 for e in entries if e.match_kind is None)
    log.info(
        "vad-denylist ielādēts: %s=%d ieraksti (%d stabili, %d uuid-only)",
        p.name, len(entries), len(entries) - n_uuid_only, n_uuid_only,
    )
    return VadDenylist(entries=tuple(entries))


def deny_hit(
    pid: int,
    vad_uuid: str,
    kind: str,
    year: int | None,
    denylist: VadDenylist | None,
) -> str | None:
    """Atgriež trāpījuma iemeslu vai None.

    Kārtība: uuid kāja vispirms (precīza pat ja match lauki nesakrīt), tad
    stabilā (kind, year) kāja. year salīdzināms kā reģistrēts — None == None.
    """
    if not denylist:
        return None
    for e in denylist.by_pid(pid):
        if e.vad_uuid and e.vad_uuid == vad_uuid:
            leg = "uuid"
            if e.match_kind is not None:
                leg = "uuid+kind-year"
            return f"[{leg}] {e.reason}"
        if (
            e.match_kind is not None
            and e.match_kind == kind
            and e.match_year == year
        ):
            return f"[kind-year] {e.reason}"
    return None
