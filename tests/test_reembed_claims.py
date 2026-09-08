"""Vārti `scripts/reembed_claims.py` CLI ceļam.

`--ids-from` eksistē tāpēc, ka pozicionālie argumenti nesedz bulk gadījumu:
4 087 id ir ~28 tūkst. rakstzīmju komandrindā, kas uz Windows atduras pret
~32 tūkst. limitu. Rollback fails, kas prasa vektoru pārrēķinu, glabā savu id
sarakstu blakus kā `.ids` failu, un `data/rollback_dup_saeima_vote_claims_*.sql`
galvene uz šo karogu TIEŠI atsaucas — tāpēc, ja karogs pazūd, dokumentētā
atkopšanās procedūra kļūst nepalaižama, un to noķer šie testi.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parent.parent / "scripts" / "reembed_claims.py"
_spec = importlib.util.spec_from_file_location("reembed_claims", SCRIPT)
reembed_claims = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(reembed_claims)


class TestReadIdsFile:
    def test_reads_one_id_per_line(self, tmp_path):
        p = tmp_path / "x.ids"
        p.write_text("101\n202\n303\n", encoding="utf-8")
        assert reembed_claims.read_ids_file(str(p)) == [101, 202, 303]

    def test_skips_blank_lines_and_comments(self, tmp_path):
        p = tmp_path / "x.ids"
        p.write_text("# komentārs\n101\n\n  \n202\n# vēl viens\n", encoding="utf-8")
        assert reembed_claims.read_ids_file(str(p)) == [101, 202]

    def test_tolerates_surrounding_whitespace(self, tmp_path):
        p = tmp_path / "x.ids"
        p.write_text("  101  \n\t202\n", encoding="utf-8")
        assert reembed_claims.read_ids_file(str(p)) == [101, 202]

    def test_bulk_sized_file_round_trips(self, tmp_path):
        """4 087 rindas — tieši tas apjoms, kura dēļ karogs eksistē."""
        ids = list(range(1000, 1000 + 4087))
        p = tmp_path / "bulk.ids"
        p.write_text("\n".join(map(str, ids)) + "\n", encoding="utf-8")
        assert reembed_claims.read_ids_file(str(p)) == ids

    def test_rejects_non_numeric_loudly(self, tmp_path):
        p = tmp_path / "x.ids"
        p.write_text("101\nnav-skaitlis\n", encoding="utf-8")
        with pytest.raises(ValueError):
            reembed_claims.read_ids_file(str(p))


class TestMainArgWiring:
    """`main()` nedrīkst klusi neko nedarīt, un abi ievadi jāsavieno."""

    def test_no_ids_at_all_is_an_error_not_a_silent_noop(self, monkeypatch, capsys):
        monkeypatch.setattr("sys.argv", ["reembed_claims.py"])
        called = []
        monkeypatch.setattr(reembed_claims, "reembed",
                            lambda *a, **k: called.append(a))
        with pytest.raises(SystemExit):
            reembed_claims.main()
        assert not called, "bez id skriptam jākrīt, ne jāpalaiž tukšs pārrēķins"

    def test_ids_from_reaches_reembed(self, tmp_path, monkeypatch):
        p = tmp_path / "x.ids"
        p.write_text("501\n502\n", encoding="utf-8")
        monkeypatch.setattr("sys.argv",
                            ["reembed_claims.py", "--ids-from", str(p)])
        seen = {}
        monkeypatch.setattr(reembed_claims, "reembed",
                            lambda ids, dry_run=False: seen.update(ids=ids, dry=dry_run))
        reembed_claims.main()
        assert seen["ids"] == [501, 502]

    def test_positional_and_file_combine(self, tmp_path, monkeypatch):
        p = tmp_path / "x.ids"
        p.write_text("777\n", encoding="utf-8")
        monkeypatch.setattr("sys.argv",
                            ["reembed_claims.py", "42", "--ids-from", str(p)])
        seen = {}
        monkeypatch.setattr(reembed_claims, "reembed",
                            lambda ids, dry_run=False: seen.update(ids=ids))
        reembed_claims.main()
        assert seen["ids"] == [42, 777]

    def test_dry_run_flag_is_forwarded(self, tmp_path, monkeypatch):
        monkeypatch.setattr("sys.argv",
                            ["reembed_claims.py", "--dry-run", "9"])
        seen = {}
        monkeypatch.setattr(reembed_claims, "reembed",
                            lambda ids, dry_run=False: seen.update(dry=dry_run))
        reembed_claims.main()
        assert seen["dry"] is True
