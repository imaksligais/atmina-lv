"""Rutīna 2026-11-07: atribūcija «jo Latvija nav starp izņēmumiem» → «pēc … teiktā» (803). --write-rollback | --apply"""
import subprocess
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.stdout.reconfigure(encoding="utf-8")
from src.db import get_db  # noqa: E402
RB = Path("data/rollback_quality4_2026-11-07.sql")
BRIEF = [("kritizē partneri JV, jo Latvija nav starp izņēmumiem", "kritizē partneri JV, jo, pēc viņa teiktā, Latvija nav starp izņēmumiem"),
         ("(JV), jo Latvija nav starp izņēmumiem", "(JV), jo, pēc kritiķu teiktā, Latvija nav starp izņēmumiem")]
db = get_db()
c, topic, source = db.execute("SELECT content, topic, source FROM context_notes WHERE id=803").fetchone()
if "--write-rollback" in sys.argv:
    RB.write_text("-- Rollback: rutīna 2026-11-07, 803 atribūcija (scripts/_fix_quality4_2026-11-07.py). Apply date: 2026-11-07.\n"
                  "UPDATE context_notes SET content='" + c.replace("'", "''") + "' WHERE id=803;\n", encoding="utf-8")
    print("rakstīts", RB)
elif "--apply" in sys.argv:
    if subprocess.run(["git", "ls-files", "--error-unmatch", str(RB)], capture_output=True).returncode or subprocess.run(["git", "diff", "--quiet", "HEAD", "--", str(RB)]).returncode:
        sys.exit("STOP: rollback nav commitēts")
    from src.tools import store_context_note
    for o, n in BRIEF:
        assert c.count(o) == 1, o
        c = c.replace(o, n)
    print(store_context_note(topic=topic, note_type="daily_brief", content=c, source=source))
