"""Operatora lēmumi 2026-10-14 (vienreizējs): pretruna #57 publicēta ar
Kulberga paskaidrojumu; 5 kļūdainas Kalēja (pid 226) saites dzēstas;
Gendeles (pid 91) role labots. Rollback: data/rollback_operator_recs_2026-10-14.sql."""
import sys
sys.path.insert(0, ".")
from src.db import get_db

ADD = (" Pēc viņa teiktā, iepriekš nebija informācijas par to, cik varētu "
       "izmaksāt starptautiskās tiesvedības, ko šāds lēmums var izraisīt.")
KALEJS_DOCS = (57275, 64602, 65797, 3469, 132783)

c = get_db()
s, conf = c.execute("SELECT summary, confirmed FROM contradictions WHERE id=57").fetchone()
assert conf == 0 and ADD not in s
c.execute("UPDATE contradictions SET summary=?, confirmed=1 WHERE id=57", (s + ADD,))
n = c.execute(f"DELETE FROM document_politicians WHERE politician_id=226 AND document_id IN "
              f"({','.join(map(str, KALEJS_DOCS))})").rowcount
assert n == 5, n
c.execute("UPDATE tracked_politicians SET role='Saeimas deputāte (14. Saeima)' WHERE id=91")
c.commit()
print("ok: #57 confirmed, junction deleted", n)
