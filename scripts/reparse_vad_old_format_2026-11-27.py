"""Vienreizēja migrācija 2026-11-27: pārparsē vad_declarations.raw_html ar
parsētāju, kas lasa arī veco VID formu (2002–2013): iestāde «Darbavieta:»,
brīvteksts §11 (jaunajā formā §13), ģimene §12 (jaunajā §14).

Raksta TIKAI `institution` un `other_info`. Ģimenes rindas (`vad_family`) NEraksta:
profila VAD panelis tās rāda publiski, un datu politika § 1 ģimenes datus
nepublicē — tas ir operatora lēmums (handoff). `audit_vad_family_clusters.py`
vecās deklarācijas ģimeni nolasa no `raw_html`.

Vārti: jaunās formas deklarācijām nekas nedrīkst mainīties (ne lauki, ne ģimene,
ne pensijas karogi) — ja mainās, skripts apstājas pirms rakstīšanas.

Pāra rollback: data/rollback_vad_old_format_reparse_2026-11-27.sql (rakstīts
ar --write-rollback, commitē PIRMS --apply). Bez karogiem tikai DRY-RUN.

Lietojums:
    .venv/Scripts/python.exe scripts/reparse_vad_old_format_2026-11-27.py
    .venv/Scripts/python.exe scripts/reparse_vad_old_format_2026-11-27.py --write-rollback
    .venv/Scripts/python.exe scripts/reparse_vad_old_format_2026-11-27.py --apply
"""

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from src.db import get_db  # noqa: E402
from src.vad.parsing import parse_declaration_html  # noqa: E402

ROLLBACK_PATH = REPO_ROOT / "data" / "rollback_vad_old_format_reparse_2026-11-27.sql"


def _sql(v):
    return "NULL" if v is None else "'" + v.replace("'", "''") + "'"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--write-rollback", action="store_true", help="tikai uzraksta rollback failu")
    ap.add_argument("--apply", action="store_true", help="raksta DB (rollback jau commitēts)")
    ap.add_argument("--db", help="DB ceļš (noklusējums: produkcijas DB)")
    args = ap.parse_args()

    db = get_db(args.db) if args.db else get_db()
    decls = db.execute(
        "SELECT id, institution, other_info, has_private_pension, has_life_insurance, raw_html "
        "FROM vad_declarations ORDER BY id"
    ).fetchall()
    fam_db: dict[int, list[tuple[str, str]]] = {}
    for r in db.execute("SELECT declaration_id, full_name, relation FROM vad_family ORDER BY id"):
        fam_db.setdefault(r["declaration_id"], []).append((r["full_name"], r["relation"]))

    updates: list[tuple[int, dict, dict]] = []  # (id, new, old)
    modern_drift: list[str] = []
    n_old = n_old_family = n_old_family_rows = n_quote = 0
    for d in decls:
        parsed = parse_declaration_html(d["raw_html"] or "")
        # Forma pēc avota, ne pēc DB lauka — pēc apply `institution` vairs nav tukšs.
        is_old = parsed.header.is_old_form
        new = {"institution": parsed.header.institution, "other_info": parsed.other_info}
        old = {"institution": d["institution"], "other_info": d["other_info"]}
        changed = {k: v for k, v in new.items() if v != old[k]}
        if not is_old:
            fam_new = [(f.full_name, f.relation) for f in parsed.family]
            flags_new = (parsed.has_private_pension, parsed.has_life_insurance)
            flags_old = tuple(None if v is None else bool(v)
                              for v in (d["has_private_pension"], d["has_life_insurance"]))
            # Vienīgā atļautā izmaiņa: VID «'…'» pēdiņas ap iestādi noņemtas.
            quote_only = set(changed) == {"institution"} and (
                (old["institution"] or "").strip("'").strip() == new["institution"])
            if (changed and not quote_only) or fam_new != fam_db.get(d["id"], []) \
                    or flags_new != flags_old:
                modern_drift.append(f"decl {d['id']}: {sorted(changed)} ģimene/karogi")
            elif changed:
                n_quote += 1
                updates.append((d["id"], changed, {k: old[k] for k in changed}))
            continue
        n_old += 1
        if d["id"] in fam_db or (d["institution"] or "") not in ("", parsed.header.institution):
            modern_drift.append(f"decl {d['id']}: vecā forma, bet vad_family rindas vai cita iestāde")
        if parsed.family:
            n_old_family += 1
            n_old_family_rows += len(parsed.family)
        if not parsed.header.institution:
            modern_drift.append(f"decl {d['id']}: vecā forma, iestāde joprojām tukša")
        if changed:
            updates.append((d["id"], changed, {k: old[k] for k in changed}))

    n_inst = sum("institution" in u[1] for u in updates)
    n_oi = sum("other_info" in u[1] for u in updates)
    print(f"[scan] {len(decls)} deklarāciju; vecā forma (raw_html galvenē «Darbavieta:») {n_old}")
    print(f"[diff] institution mainīsies: {n_inst} (t. sk. jaunās formas pēdiņas: {n_quote}); other_info: {n_oi}")
    print(f"[info] vecajām ar ģimeni raw_html: {n_old_family} dekl., {n_old_family_rows} rindas "
          f"(NErakstām — sk. docstring)")
    print(f"[gate] jaunās formas izmaiņas / anomālijas: {len(modern_drift)}")
    for m in modern_drift[:20]:
        print("   ", m)
    if modern_drift:
        print("[STOP] vārti nokrita — nekas nav rakstīts.")
        return 1
    lines = [
        "-- Rollback priekš: scripts/reparse_vad_old_format_2026-11-27.py --apply (2026-11-27)",
        "-- Uz priekšu: vad_declarations.institution + other_info vecajām (2002–2013) deklarācijām",
        "-- un VID «'…'» pēdiņas ap iestādi 9 jaunās formas deklarācijām.",
        "BEGIN;",
    ]
    for did, _new, old in updates:
        sets = ", ".join(f"{k}={_sql(v)}" for k, v in old.items())
        lines.append(f"UPDATE vad_declarations SET {sets} WHERE id={did};")
    rollback = "\n".join(lines + ["COMMIT;"]) + "\n"

    if args.write_rollback:
        ROLLBACK_PATH.write_text(rollback, encoding="utf-8")
        print(f"[rollback] {ROLLBACK_PATH.name}: {len(updates)} UPDATE — commitē PIRMS --apply")
        return 0
    if not args.apply:
        print("\n[dry-run] nekas nav rakstīts. --write-rollback, commit, tad --apply.")
        return 0
    if not ROLLBACK_PATH.exists() or ROLLBACK_PATH.read_text(encoding="utf-8") != rollback:
        print("[STOP] rollback fails nav vai neatbilst šim skrējienam — vispirms --write-rollback + commit.")
        return 1

    try:
        with db:
            for did, new, old in updates:
                # Tikai ja rinda nav mainījusies kopš skenēšanas — citādi rollback
                # atjaunotu novecojušu vērtību; viss tiek atcelts.
                sets = ", ".join(f"{k}=?" for k in new)
                where = " AND ".join(f"{k} IS ?" for k in old)
                cur = db.execute(f"UPDATE vad_declarations SET {sets} WHERE id=? AND {where}",
                                 (*new.values(), did, *old.values()))
                if cur.rowcount != 1:
                    raise RuntimeError(f"decl {did} mainījusies kopš skenēšanas")
        print(f"[done] {len(updates)} deklarācijas atjaunotas")
        return 0
    except Exception as e:
        print(f"[fail] transakcija atcelta: {type(e).__name__}: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
