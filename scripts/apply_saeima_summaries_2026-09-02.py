"""2026-07-23 (43) + 2026-08-20 (17) balsojumu `summary` aizpilde no @saeima-tracker
melnrakstiem + `saeima_vote` claim stance pārģenerēšana.

Konteksts: abas sesijas nokrita uz pilnīguma vārtiem (a) — bill-tipa balsojumi
bez kopsavilkuma, claim stance = ģeneriskais «Balsoja PAR: <motif>». Melnrakstus
rakstīja četri Opus `@saeima-tracker` aģenti (lasīšanas režīmā) failos
`data/saeima_summaries_drafts_2026-09-02/summaries_*.json`; šis skripts ir vienīgais rakstītājs.

Disciplīna:
  * raksta TIKAI `saeima_votes.summary` (tikai tur, kur šobrīd NULL) un
    `claims.stance` tā paša balsojuma `saeima_vote` claim rindām;
    `bill_id` / `current_stage` netiek aiztikti (inv #12);
  * NEpārembedo — `saeima_vote` claims nes vektoru kopš 2026-08-21 verdikta
    (CLAUDE.md § Escalation 8);
  * stance forma = `src/saeima/votes.py::generate_claims_from_votes`
    (prefikss + kopsavilkums ar mazo sākumburtu, izņemot akronīmu);
  * vārti pirms rakstīšanas: id tiešām NULL; teksts nesākas ar motif;
    nesatur cita balsojuma iznākuma frāzi; diakritiku validācija.

Paired rollback: data/rollback_saeima_summaries_0723_0820_2026-09-02.sql
Apply date: 2026-09-02
"""

from __future__ import annotations

import argparse
import glob
import json
import re
import sqlite3
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))
from src.quality import validate_lv_diacritics  # noqa: E402

DB = REPO / "data" / "atmina.db"
DRAFT_GLOB = str(REPO / "data" / "saeima_summaries_drafts_2026-09-02" / "summaries_*.json")
ROLLBACK = REPO / "data" / "rollback_saeima_summaries_0723_0820_2026-09-02.sql"

PREFIX = {
    "Par": "Atbalsta",
    "Pret": "Iebilst pret",
    "Atturas": "Atturējās balsojumā par",
    "Nebalsoja": "Nebalsoja par",
}
OUTCOME_PHRASES = re.compile(
    r"(galīgajā lasījumā (vienbalsīgi )?pieņemt|lasījumā pieņemt|vienbalsīgi pieņemt|"
    r"Saeima pieņēma|tika pieņemt|noraidīja ar|pieņemts ar \d)",
    re.IGNORECASE,
)
SENTINEL = "Kopsavilkums nav pieejams"


def _lower_first(s: str) -> str:
    if s[:2].isupper():
        return s
    return s[0].lower() + s[1:] if s else ""


def _sql_str(s: str) -> str:
    return "'" + s.replace("'", "''") + "'"


def load_drafts() -> dict[int, str]:
    out: dict[int, str] = {}
    for f in sorted(glob.glob(DRAFT_GLOB)):
        d = json.loads(Path(f).read_text(encoding="utf-8"))
        for k, v in d.items():
            if k.startswith("_"):
                continue
            vid = int(k)
            if vid in out:
                raise SystemExit(f"STOP: vote {vid} appears in two draft files")
            out[vid] = v.strip()
    return out


def gate(db: sqlite3.Connection, drafts: dict[int, str]) -> list[str]:
    problems: list[str] = []
    for vid, text in drafts.items():
        row = db.execute(
            "SELECT motif, summary FROM saeima_votes WHERE id = ?", (vid,)
        ).fetchone()
        if row is None:
            problems.append(f"{vid}: nav tādas rindas")
            continue
        motif, existing = row
        if existing is not None:
            problems.append(f"{vid}: summary jau nav NULL")
        if not text:
            problems.append(f"{vid}: tukšs melnraksts")
            continue
        if text.startswith(SENTINEL):
            continue
        if text[:40].lower() == motif[:40].lower():
            problems.append(f"{vid}: atkārto motif")
        if OUTCOME_PHRASES.search(text):
            problems.append(f"{vid}: satur lasījuma iznākuma frāzi: {text[:90]}")
        ok, why = validate_lv_diacritics(text)
        if not ok:
            problems.append(f"{vid}: diakritikas {why}")
        if len(text) > 700:
            problems.append(f"{vid}: pārāk garš ({len(text)})")
    return problems


def main(apply: bool, regen_dates: list[str], rollback: Path = ROLLBACK, no_drafts: bool = False) -> int:
    drafts = {} if no_drafts else load_drafts()
    print(f"melnraksti: {len(drafts)} balsojumi")
    db = sqlite3.connect(DB)
    db.row_factory = sqlite3.Row
    problems = gate(db, drafts)
    if problems:
        print("VĀRTI NEIZIETI:")
        for p in problems:
            print("  ", p)
        return 1
    print("vārti: OK (visi id NULL, bez motif atkārtojuma, bez iznākuma frāzēm, diakritika OK)")

    # Rollback + plan
    rb = [
        "-- Rollback for scripts/apply_saeima_summaries_2026-09-02.py (apply 2026-09-02)",
        "-- Reverses: saeima_votes.summary aizpilde (07-23: 43, 08-20: 17) + claims.stance regen",
        "BEGIN;",
    ]
    stance_plan: list[tuple[str, int, str]] = []  # (new_stance, claim_id, old_stance)
    # Otrs avots: tās pašas sesijas balsojumi, kam summary JAU IR, bet claim
    # stance palika ģeneriskais «Balsoja PAR: <motif>» (summary ierakstīts pēc
    # claim ģenerēšanas). 08-20: 54 balsojumi / 4616 claims; 07-23: 20 / 1508.
    regen: dict[int, str] = {}
    if regen_dates:
        for r in db.execute(
            "SELECT id, summary FROM saeima_votes WHERE vote_date IN ({}) "
            "AND summary IS NOT NULL AND summary != motif AND summary NOT LIKE ?".format(
                ",".join("?" * len(regen_dates))
            ),
            (*regen_dates, SENTINEL + "%"),
        ):
            regen[r["id"]] = r["summary"]
    for vid, text in drafts.items():
        rb.append(f"UPDATE saeima_votes SET summary = NULL WHERE id = {vid};")
    for vid, text in {**regen, **drafts}.items():
        if text.startswith(SENTINEL):
            continue  # sentinel → stance stays motif-based (votes.py behaviour)
        v = db.execute("SELECT url FROM saeima_votes WHERE id = ?", (vid,)).fetchone()
        pid_to_vote = {
            r["politician_id"]: r["vote"]
            for r in db.execute(
                "SELECT politician_id, vote FROM saeima_individual_votes "
                "WHERE vote_id = ? AND politician_id IS NOT NULL",
                (vid,),
            )
        }
        low = _lower_first(text)
        for c in db.execute(
            "SELECT id, opponent_id, stance FROM claims "
            "WHERE source_url = ? AND claim_type = 'saeima_vote'",
            (v["url"],),
        ):
            dv = pid_to_vote.get(c["opponent_id"])
            if not dv:
                continue
            new = f"{PREFIX.get(dv, dv)}: {low}"
            if new != c["stance"]:
                stance_plan.append((new, c["id"], c["stance"]))
                rb.append(
                    f"UPDATE claims SET stance = {_sql_str(c['stance'])} WHERE id = {c['id']};"
                )
    rb.append("COMMIT;")
    print(f"plāns: {len(drafts)} summary + {len(stance_plan)} stance (t.sk. {len(regen)} balsojumi ar esošu summary)")

    if not apply:
        print("(sausā palaide — pievieno --apply)")
        return 0

    if rollback.exists():
        raise SystemExit(f"STOP: rollback fails jau eksistē — {rollback}; dod --rollback-out ar unikālu vārdu")
    rollback.write_text("\n".join(rb) + "\n", encoding="utf-8")
    print(f"rollback: {rollback}")
    try:
        n_s = 0
        for vid, text in drafts.items():
            n_s += db.execute(
                "UPDATE saeima_votes SET summary = ? WHERE id = ? AND summary IS NULL",
                (text, vid),
            ).rowcount
        n_c = 0
        for new, cid, _old in stance_plan:
            n_c += db.execute(
                "UPDATE claims SET stance = ? WHERE id = ?", (new, cid)
            ).rowcount
        if n_s != len(drafts) or n_c != len(stance_plan):
            raise RuntimeError(f"skaits nesakrīt: summary {n_s}/{len(drafts)}, stance {n_c}/{len(stance_plan)}")
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
    print(f"IERAKSTĪTS: summary {n_s}, stance {n_c}")
    return 0


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--regen-sessions", default="", help="komatatdalīti vote_date, kuru esošos claim stance pārģenerēt no summary")
    ap.add_argument("--rollback-out", default=str(ROLLBACK), help="pāra rollback ceļš (unikāls katram palaidienam)")
    ap.add_argument("--no-drafts", action="store_true", help="tikai --regen-sessions, melnrakstus nelasa (jau ierakstītiem)")
    a = ap.parse_args()
    raise SystemExit(main(a.apply, [d for d in a.regen_sessions.split(",") if d], Path(a.rollback_out), a.no_drafts))
