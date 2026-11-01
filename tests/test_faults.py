"""ledger/faults.py (T67): the nine kinds on a real parsed filing and synthetic extractions; the XBRL-off rule set;
the report shape with `written` and by_kind; score.faults reads by_kind and xbrl_off; every sum matches its parts."""
import json
import shutil
from datetime import datetime, timezone
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from ledger import score, store
from ledger.cli.faults import report, report_path
from ledger.faults import FAULTS, OMIT, SYSTEMATIC_OF, XBRL_RULE, omission, rows_of, rule_set, systematic, tally, trials, wrong_table
from ledger.rules import load

try:  # `unittest discover -s tests` loads the modules top-level; `python -m unittest tests.test_faults` as a package
    from test_rules import ACC, REV, ext, parsed
    from test_score import _doc
except ImportError:
    from .test_rules import ACC, REV, ext, parsed
    from .test_score import _doc

DOC = parsed()
INCOME, CASH = DOC["statements"]["income"][0], DOC["statements"]["cash_flow"][0]


def _cell(table, label, col):
    row = next(r for r in table["rows"] if r["label"] == label)
    return next(c for c in row["cells"] if c["col"] == col)


class Kinds(unittest.TestCase):
    def test_nine_kinds_in_order_with_a_docstring_each(self):
        self.assertEqual(list(FAULTS), ["wrong_column", "stale_column", "wrong_row", "wrong_scale", "sign_flip", "misread_digits", "omission", "wrong_table", "systematic"])
        for k in ("omission", "wrong_table", "systematic"):
            self.assertIn("catch", FAULTS[k].__doc__)

    def test_omission_drops_the_extraction(self):
        self.assertIs(omission(REV, DOC), OMIT)
        ts = [(k, xs, d) for k, xs, d in trials([REV], {ACC: DOC}) if k == "omission"]
        self.assertEqual(len(ts), 1)
        self.assertEqual(ts[0][1], [])
        self.assertEqual(ts[0][2], {"extraction_id": REV["extraction_id"]})

    def test_wrong_table_cites_the_other_statement_and_the_cell_exists(self):
        bad = wrong_table(REV, DOC)  # an income line pointed at the cash-flow table
        self.assertEqual(bad["table_id"], CASH["id"])
        self.assertNotEqual(bad["table_id"], REV["table_id"])
        self.assertEqual(bad["column_label"], REV["column_label"])  # the same column label exists in the other table
        cell = _cell(CASH, bad["row_label"], CASH["columns"].index(bad["column_label"]))
        self.assertEqual(cell["text"], bad["cell_text"])
        self.assertEqual(bad["value"], round(cell["value"] * CASH["scale"]))
        # and the other way: a cash-flow line lands on the income statement
        capex = ext("capex", "2025-06-01", "2026-05-31", -1, "(1)", CASH["rows"][5]["label"], CASH["columns"][0], table=CASH["id"])
        back = wrong_table(capex, DOC)
        self.assertEqual(back["table_id"], INCOME["id"])
        self.assertLessEqual(back["value"], 0)  # capex keeps its sign convention

    def test_wrong_table_is_none_without_the_other_statement(self):
        doc = {"statements": {"income": [INCOME], "cash_flow": []}}
        self.assertIsNone(wrong_table(REV, doc))

    def test_systematic_moves_every_year_of_a_field_the_same_way(self):
        xs = [{**REV, "extraction_id": f"{ACC}|revenue|{y - 1}-06-01|{y}-05-31", "period_start": f"{y - 1}-06-01", "period_end": f"{y}-05-31",
               "column_label": col, "cell_text": _cell(INCOME, REV["row_label"], i)["text"], "value": round(_cell(INCOME, REV["row_label"], i)["value"] * INCOME["scale"])}
              for i, (y, col) in enumerate(zip((2026, 2025, 2024), INCOME["columns"]))]
        out = list(systematic(xs, {ACC: DOC}))
        variants = {d["variant"] for _, d in out}
        self.assertEqual(variants, {"wrong_row", "wrong_scale"})  # wrong_column: every column spans a year, so no move
        for ys, d in out:
            self.assertEqual(d["n"], 3)
            self.assertEqual(d["field"], "revenue")
            self.assertEqual(d["extraction_id"], xs[0]["extraction_id"])
            self.assertEqual(len(ys), 3)
            if d["variant"] == "wrong_scale":
                self.assertEqual([y["value"] for y in ys], [x["value"] * 1000 for x in xs])
            else:
                self.assertEqual(len({y["row_label"] for y in ys}), 1)  # the same wrong line in every year
                self.assertNotEqual(ys[0]["row_label"], REV["row_label"])
        self.assertEqual(list(systematic([REV], {ACC: DOC})), [])  # one year is a one-cell fault, not a systematic one

    def test_trials_name_an_extraction_id_on_every_row(self):
        for name, xs, detail in trials([REV], {ACC: DOC}):
            self.assertIn(name, FAULTS)
            self.assertTrue(detail["extraction_id"])
            self.assertIsInstance(xs, list)


class RuleSet(unittest.TestCase):
    def test_xbrl_off_removes_only_xbrl_reconcile(self):
        rules = load()
        on, off = rule_set(rules), rule_set(rules, xbrl=False)
        self.assertEqual([r["id"] for r in on], [r["id"] for r in rules])
        self.assertEqual({r["id"] for r in on} - {r["id"] for r in off}, {XBRL_RULE})
        self.assertEqual(len(off), len(on) - 1)


ROWS = [{"fault": "sign_flip", "extraction_id": "a|capex|x|y", "outcome": "rule", "caught_by": ["sign"]},
        {"fault": "sign_flip", "extraction_id": "a|capex|x|z", "outcome": "no_effect", "caught_by": []},
        {"fault": "omission", "extraction_id": "a|capex|x|y", "outcome": "escaped", "caught_by": []},
        {"fault": "omission", "extraction_id": "a|capex|x|z", "outcome": "xbrl_only", "caught_by": []},
        {"fault": "systematic", "extraction_id": "a|capex|x|y", "variant": "wrong_row", "field": "capex", "n": 3, "outcome": "rule", "caught_by": ["jump"]}]


class Report(unittest.TestCase):
    def test_tally_sums_match(self):
        t = tally(ROWS)
        self.assertEqual({k: t[k] for k in ("planted", "caught", "rule", "xbrl_only", "no_effect", "escaped")}, {"planted": 5, "caught": 3, "rule": 2, "xbrl_only": 1, "no_effect": 1, "escaped": 1})
        self.assertEqual(list(t["by_kind"]), ["sign_flip", "omission", "systematic"])
        self.assertEqual(t["by_kind"]["omission"], {"planted": 2, "caught": 1, "rule": 0, "xbrl_only": 1, "no_effect": 0, "escaped": 1})
        for c in [t, *t["by_kind"].values()]:
            self.assertEqual(c["planted"], c["caught"] + c["no_effect"] + c["escaped"])
            self.assertEqual(c["caught"], c["rule"] + c["xbrl_only"])
        self.assertEqual(sum(c["planted"] for c in t["by_kind"].values()), t["planted"])
        self.assertEqual(tally([]), {"planted": 0, "caught": 0, "rule": 0, "xbrl_only": 0, "no_effect": 0, "escaped": 0, "by_kind": {}})

    def test_report_shape_and_paths(self):
        rules = load()
        rep = report("x", False, rule_set(rules, xbrl=False), ROWS)
        self.assertTrue(rep["written"].startswith("20") and "T" in rep["written"])
        self.assertFalse(rep["xbrl"])
        self.assertNotIn(XBRL_RULE, rep["rules"])
        self.assertEqual(rep["kinds"], list(FAULTS))
        self.assertEqual(rep["rows"], ROWS)
        self.assertEqual(rep["planted"], 5)
        self.assertIn("by_kind", rep)
        self.assertIn(XBRL_RULE, report("x", True, rules, ROWS)["rules"])
        self.assertEqual(report_path("stage3").name, "stage3-faults.json")
        self.assertEqual(report_path("stage3", xbrl=False).name, "stage3-faults-xbrl-off.json")
        self.assertEqual(rows_of(rep), ROWS)
        self.assertEqual(rows_of(ROWS), ROWS)  # the pre-T67 shape, a bare list
        self.assertEqual(rows_of(None), [])


class Score(unittest.TestCase):
    """score.faults on a database with one MSFT filing: the T67 report shape, by_kind, and the XBRL-off report beside it."""

    def setUp(self):
        self.con = store.init(":memory:")
        store.write(self.con, "documents", [_doc("0000789019-25-000001", "MSFT", "2025-06-30")])
        started = datetime.now(timezone.utc).isoformat(timespec="seconds")  # the run that writes the report, ending after the write
        store.write(self.con, "runs", [{"run_id": "f1", "step": "faults", "subject": "six", "started_at": started, "seconds": 60.0, "outcome": "ok", "versions": "{}", "detail": "{}"}])
        self.reports = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.reports)
        p = mock.patch.object(score, "REPORTS", self.reports)
        p.start()
        self.addCleanup(p.stop)
        mine = [{**r, "extraction_id": "0000789019-25-000001" + r["extraction_id"][1:]} for r in ROWS]
        other = [{"fault": "sign_flip", "extraction_id": "0000000000-25-000001|capex|x|y", "outcome": "escaped", "caught_by": []}]
        (self.reports / "six-faults.json").write_text(json.dumps(report("six", True, load(), mine + other)))
        self.off = [{**r, "outcome": "escaped" if r["outcome"] == "xbrl_only" else r["outcome"]} for r in mine]
        (self.reports / "six-faults-xbrl-off.json").write_text(json.dumps(report("six", False, rule_set(load(), xbrl=False), self.off)))

    def test_by_kind_and_xbrl_off_for_the_company_only(self):
        started = self.con.execute("select started_at from runs").fetchone()[0]
        fl, note = score.faults(self.con, "reader", ["MSFT"])
        self.assertEqual({k: fl[k] for k in ("caught", "planted", "no_effect", "escaped", "xbrl_only")}, {"caught": 3, "planted": 5, "no_effect": 1, "escaped": 1, "xbrl_only": 1})
        self.assertEqual(fl["by_kind"]["omission"]["escaped"], 1)
        self.assertEqual(sum(c["planted"] for c in fl["by_kind"].values()), fl["planted"])
        self.assertEqual({k: fl["xbrl_off"][k] for k in ("caught", "planted", "escaped")}, {"caught": 2, "planted": 5, "escaped": 2})
        self.assertEqual(fl["xbrl_off"]["xbrl_only"], 0)
        self.assertEqual(fl["xbrl_off"]["by_kind"]["omission"], {"planted": 2, "caught": 0, "rule": 0, "xbrl_only": 0, "no_effect": 0, "escaped": 2})
        self.assertIn("XBRL off: the same trials with xbrl_reconcile removed", note)
        self.assertIn(f"file written {started[:10]}", note)  # the report's own written field
        self.assertNotIn("report newer", note)  # written before the run ended

    def test_without_the_xbrl_off_report(self):
        (self.reports / "six-faults-xbrl-off.json").unlink()
        fl, note = score.faults(self.con, "reader", ["MSFT"])
        self.assertIsNone(fl["xbrl_off"])
        self.assertIn("no XBRL-off report", note)

    def test_a_report_written_before_its_run_reads_newer(self):
        rep = json.loads((self.reports / "six-faults.json").read_text())
        rep["written"] = "2026-10-01T00:00:00+00:00"
        (self.reports / "six-faults.json").write_text(json.dumps(rep))
        _, note = score.faults(self.con, "reader", ["MSFT"])
        self.assertIn("file written 2026-10-01", note)
        self.assertNotIn("report newer", note)
        rep["written"] = "2099-12-01T00:00:00+00:00"  # rewritten after the run ended
        (self.reports / "six-faults.json").write_text(json.dumps(rep))
        _, note = score.faults(self.con, "reader", ["MSFT"])
        self.assertIn("report newer than its run", note)


    def test_a_stale_xbrl_off_report_is_not_shown(self):
        rep = json.loads((self.reports / "six-faults-xbrl-off.json").read_text())
        rep["written"] = "2020-01-01T00:00:00+00:00"  # older than the normal run: a different run's numbers
        (self.reports / "six-faults-xbrl-off.json").write_text(json.dumps(rep))
        fl, note = score.faults(self.con, "reader", ["MSFT"])
        self.assertIsNone(fl["xbrl_off"])
        self.assertIn("older than the normal run for MSFT", note)

    def test_an_xbrl_off_report_over_fewer_companies_is_not_shown(self):
        store.write(self.con, "documents", [_doc("0001045810-25-000001", "NVDA", "2025-01-26")])
        rep = json.loads((self.reports / "six-faults.json").read_text())
        rep["rows"] = rep["rows"] + [{"fault": "sign_flip", "extraction_id": "0001045810-25-000001|capex|x|y", "outcome": "rule", "caught_by": ["sign"]}]
        (self.reports / "six-faults.json").write_text(json.dumps(rep))
        fl, note = score.faults(self.con, "reader", ["MSFT", "NVDA"])
        self.assertIsNone(fl["xbrl_off"])  # the off file covers MSFT only: never a smaller denominator beside the headline
        self.assertIn("XBRL off not shown", note)


class InjectXbrlOff(unittest.TestCase):
    """inject(): a fault only the XBRL comparison sees reads xbrl_only with every rule, escaped with XBRL off."""

    def test_xbrl_only_becomes_escaped_without_the_rule(self):
        from ledger import faults as F
        from ledger.rules import Context
        rules = load()
        xbrl_hit = {"exception_id": "x1", "input_hash": "h", "rule_id": XBRL_RULE, "severity": "block"}
        def fake_run(ctx, rs):  # the XBRL rule fires on the corrupted set only, and only when it is in the rule set
            on = any(r["id"] == XBRL_RULE for r in rs)
            return [xbrl_hit] if on and ctx.extractions and ctx.extractions[0].get("value") == -1 else []
        base = [{"field": "revenue", "period": "FY2025", "value": 1}]
        bad = [{"field": "revenue", "period": "FY2025", "value": -1}]
        ctx = Context(values=[], extractions=[{"value": 1}], parsed={})
        with mock.patch.object(F, "run", fake_run), \
             mock.patch.object(F, "trials", lambda xs, parsed: iter([("sign_flip", [{"value": -1}], {"extraction_id": "a|b"})])), \
             mock.patch.object(F, "values_for", lambda t, xs, *a: bad if xs and xs[0]["value"] == -1 else base):
            on = F.inject("MSFT", [{"value": 1}], {}, None, {}, ctx, rules)
            off = F.inject("MSFT", [{"value": 1}], {}, None, {}, ctx, rule_set(rules, xbrl=False))
        self.assertEqual([r["outcome"] for r in on], ["xbrl_only"])
        self.assertEqual([r["outcome"] for r in off], ["escaped"])

    def test_trials_leave_the_input_list_unchanged(self):
        xs = [REV]
        before = json.dumps(xs, sort_keys=True, default=str)
        list(trials(xs, {ACC: DOC}))
        self.assertEqual(json.dumps(xs, sort_keys=True, default=str), before)


class SystematicOf(unittest.TestCase):
    def test_the_variants_are_one_cell_kinds(self):
        for v in SYSTEMATIC_OF:
            self.assertIn(v, FAULTS)
            self.assertFalse(getattr(FAULTS[v], "company_wide", False))
        self.assertTrue(systematic.company_wide)
