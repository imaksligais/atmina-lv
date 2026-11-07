"""Tests for scripts.eval_matcher_collisions — declared regression gates are enforced."""

from scripts.eval_matcher_collisions import (
    REGRESSION_FP_LINKS_MAX,
    REGRESSION_GOLD_HIT_MIN,
    regression_gates_failed,
)


def _run(fp_links=0, gold_hit=1300):
    return {"fp_links": list(range(fp_links)), "gold_hit": gold_hit}


def test_gates_pass_at_declared_thresholds():
    assert regression_gates_failed(_run(fp_links=3, gold_hit=1260)) is False


def test_gates_pass_inside_thresholds():
    assert regression_gates_failed(_run(fp_links=0, gold_hit=2000)) is False


def test_gate_fails_on_too_many_fp_links():
    assert regression_gates_failed(_run(fp_links=4, gold_hit=1260)) is True


def test_gate_fails_on_low_gold_hit():
    assert regression_gates_failed(_run(fp_links=0, gold_hit=1259)) is True


def test_thresholds_match_docstring_contract():
    """The enforced constants must equal the gates documented in the module docstring."""
    assert REGRESSION_FP_LINKS_MAX == 3
    assert REGRESSION_GOLD_HIT_MIN == 1260


def test_cli_db_controls_forms_and_real_matcher(tmp_path, monkeypatch):
    import sys
    import pytest
    import src.db as dbmod
    import src.matcher as matcher
    import scripts.eval_matcher_collisions as evaluator
    path = tmp_path / "copy.db"
    dbmod.init_db(str(path))
    db = dbmod.get_db(str(path))
    db.execute("INSERT INTO tracked_politicians (id,name,name_forms,negative_patterns) "
               "VALUES (991,'Juris Testavards', ?, ?)",
               ('["Juris Testavards","Testavards"]', '["blocked-marker"]'))
    db.commit()
    db.close()
    original_path = dbmod.DB_PATH
    class Checked(Exception):
        pass
    def inspect(path_arg, quick):
        forms = matcher._load_politician_forms()
        assert [r[0] for r in forms] == [991]
        assert forms[0][3] == ["blocked-marker"]
        assert matcher.match_politicians("Juris Testavards sacīja.")
        assert not matcher.match_politicians("Juris Testavards blocked-marker")
        raise Checked
    monkeypatch.setattr(evaluator, "load_datasets", inspect)
    monkeypatch.setattr(sys, "argv", ["eval", "--db", str(path)])
    with pytest.raises(Checked):
        evaluator.main()
    assert dbmod.DB_PATH == original_path
    assert matcher._politician_forms_cache is None
