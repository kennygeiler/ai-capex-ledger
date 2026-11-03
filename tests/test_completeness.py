"""T81: completeness against the answer key. Every (company, field, year) XBRL holds a value for ships a value, is an
open item, or a person decided it; anything else is a silent blank, counted by the Release checklist's required line
"Answer-key values missing from the dataset". The coverage rule fires on the same cells, from the same first year and
the same fields. On the six the line reads 0; planting a deleted row turns it red."""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from datetime import date
from pathlib import Path

from ledger.core import config, store
from ledger.checks import golden, proof, rules
from tests.test_status import fixture_root

ACC = "0000000000-25-000001"
REF = [("X", "revenue", "FY2024", 100), ("X", "capex", "FY2024", 20), ("X", "opex", "FY2024", 30),
       ("X", "revenue", "FY2025", 110), ("X", "capex", "FY2025", 22), ("X", "opex", "FY2025", 33),
       ("X", "cost_of_revenue", "FY2025", 50),  # not a released field: never counted
       ("X", "revenue", "FY2019", 90)]  # not a released year: never counted


def _value(f, p, value, label, **kw):
    return {"ticker": "X", "field": f, "period": p, "period_end": f"{p[2:]}-12-31", "value": value, "source": "agent" if value is not None else "missing",
            "method": "computed" if f == "opex" else "reported", "label": label, "basis": "as_reported", "first_reported": value,
            "extraction_ids": "", "input_hash": "h-" + f + p, **kw}


def _ref(t, f, p, v):
    return {"ticker": t, "field": f, "period": p, "value": v, "method": "reported", "concept": "us-gaap:X", "period_start": f"{p[2:]}-01-01",
            "period_end": f"{p[2:]}-12-31", "accession": ACC, "restated": False, "original_value": None}


def _exc(f, p, rule="coverage"):
    return {"exception_id": f"{rule}|X|{f}|{p}|None", "rule_id": rule, "severity": "warn", "ticker": "X", "field": f, "period": p, "subject": None,
            "message": f"no {f} value for {p}", "input_hash": "ih"}


def _decision(e, kind, who, value=None):
    return {"decision_id": "d1", "exception_id": e["exception_id"], "kind": kind, "value": value, "reason": "checked the filing", "reviewer": who, "input_hash": "ih"}


class MissingFromDataset(unittest.TestCase):
    """proof.missing_from_dataset on a small database: what counts as a silent blank and what does not."""

    def setUp(self):
        d = Path(tempfile.mkdtemp(prefix="ledger-t81-"))
        self.addCleanup(shutil.rmtree, d, True)
        self.con = store.init(d / "ledger.duckdb")
        self.addCleanup(self.con.close)
        store.write(self.con, "reference_values", [_ref(*r) for r in REF])
        self.complete = [_value("revenue", "FY2024", 100, "agree"), _value("capex", "FY2024", 20, "agree"), _value("opex", "FY2024", 30, "agree"),
                         _value("revenue", "FY2025", 110, "agree"), _value("capex", "FY2025", 22, "agree"), _value("opex", "FY2025", 33, "agree")]

    def entries(self, values, idx=None, ds=None, excs=(), tickers=("X",)):
        self.con.execute('delete from "values"')
        self.con.execute("delete from exceptions")
        store.write(self.con, "values", values)
        if excs:
            store.write(self.con, "exceptions", list(excs))
        return proof.missing_from_dataset(self.con, list(tickers), ds or [], idx=idx or {})

    def missing(self, values, **kw):
        return [(m["field"], m["period"]) for m in self.entries(values, **kw)]

    def swap(self, f, p, row):
        return [row if (v["field"], v["period"]) == (f, p) else v for v in self.complete]

    def without(self, f, p):
        return [v for v in self.complete if (v["field"], v["period"]) != (f, p)]

    def test_complete_reads_zero(self):
        self.assertEqual(self.missing(self.complete), [])

    def test_a_deleted_value_row_counts(self):
        self.assertEqual(self.missing(self.without("capex", "FY2025")), [("capex", "FY2025")])

    def test_a_blank_with_a_checked_label_counts(self):
        self.assertEqual(self.missing(self.swap("opex", "FY2025", _value("opex", "FY2025", None, "agree"))), [("opex", "FY2025")])

    def test_not_reported_over_an_xbrl_value_is_open_not_silent(self):
        # since T81 status.of_value opens it (XBRL holds a value), so the Open line counts it and this line does not
        self.assertEqual(self.missing(self.swap("revenue", "FY2024", _value("revenue", "FY2024", None, "not_reported"))), [])

    def test_not_extracted_is_open_not_silent(self):
        self.assertEqual(self.missing(self.swap("revenue", "FY2025", _value("revenue", "FY2025", None, "not_extracted"))), [])

    def test_no_answer_key_loaded_is_never_a_pass(self):
        got = self.entries(self.complete, tickers=("X", "Y"))  # Y has no reference rows
        self.assertEqual([(m["ticker"], m["why"]) for m in got], [("Y", "no XBRL answer loaded")])
        self.con.execute("drop table reference_values")
        got = self.entries(self.complete, tickers=("X", "Y"))
        self.assertEqual([(m["ticker"], m["why"]) for m in got], [("X", "no XBRL answer loaded"), ("Y", "no XBRL answer loaded")])

    def test_an_open_finding_on_a_missing_row_is_counted_on_open_not_here(self):
        rows = self.without("capex", "FY2025")
        self.assertEqual(self.missing(rows, excs=[_exc("capex", "FY2025")]), [])  # undecided: review.open_items has it
        self.assertEqual(self.missing(rows, excs=[_exc("capex", "FY2024")]), [("capex", "FY2025")])  # a finding on another year does not cover it

    def test_a_persons_decision_on_the_finding_clears_it_a_runs_does_not(self):
        rows, e = self.without("capex", "FY2025"), _exc("capex", "FY2025")
        self.assertEqual(self.missing(rows, excs=[e], ds=[_decision(e, "accept", "Kenny Geiler")]), [])
        got = self.entries(rows, excs=[e], ds=[_decision(e, "accept", "Claude")])
        self.assertEqual([(m["field"], m["period"]) for m in got], [("capex", "FY2025")])
        self.assertEqual(self.missing(rows, excs=[e], ds=[{**_decision(e, "accept", "Kenny Geiler"), "author_kind": "agent"}]), [("capex", "FY2025")])  # person_wrote prefers author_kind (T69)

    def test_a_persons_resolution_accounts_for_it_a_runs_does_not(self):
        key = ("values", "X", "revenue", "", "FY2024", "")
        person = {key: {"id": "r1", "state": "explain", "status": "explained", "by": "Kenny Geiler", "at": "", "reason": "the filer withdrew the tag"}}
        run = {key: {"id": "r2", "state": "explain", "status": "explained", "by": "Replication run (Claude)", "at": "", "reason": "fine"}}
        fix = {key: {"id": "r3", "state": "fix", "status": "open", "by": "Replication run (Claude)", "at": "", "reason": "re-read it"}}
        nr = self.swap("revenue", "FY2024", _value("revenue", "FY2024", None, "not_reported"))
        self.assertEqual(self.missing(nr, idx=person), [])
        self.assertEqual(self.missing(nr, idx=run), [("revenue", "FY2024")])  # a run's explain over an XBRL value is silent
        self.assertEqual(self.missing(nr, idx=fix), [])  # a fix is open: the Open line counts it

    def test_a_reject_decision_by_a_person_accounts_for_it(self):
        e = _exc("capex", "FY2025", "xbrl_reconcile")
        self.assertEqual(self.missing(self.complete, ds=[_decision(e, "reject", "Kenny Geiler")], excs=[e]), [])
        self.assertEqual(self.missing(self.complete, ds=[_decision(e, "reject", "Claude")], excs=[e]), [("capex", "FY2025")])

    def test_an_override_fills_it(self):
        e = _exc("capex", "FY2025")
        self.assertEqual(self.missing(self.without("capex", "FY2025") + [_value("capex", "FY2025", None, "agree")], ds=[_decision(e, "override", "Kenny Geiler", 22)], excs=[e]), [])

    def test_no_xbrl_value_never_counts(self):
        self.con.execute("delete from reference_values where field = 'capex'")
        self.assertEqual(self.missing([v for v in self.complete if v["field"] != "capex"]), [])

    def test_a_year_before_the_first_10k_row_is_not_counted(self):
        rows = [v for v in self.complete if v["period"] == "FY2025"]  # the company's 10-Ks start at FY2025; XBRL also holds FY2024
        self.assertEqual(self.missing(rows), [])
        ctx = rules.Context(values=rows, extractions=[], reference={(t, f, p): _ref(t, f, p, v) for t, f, p, v in REF}, years=["FY2024", "FY2025"],
                            tickers=["X"], today=date(2026, 11, 1))
        self.assertEqual([x.period for x in rules.CHECKS["coverage"](ctx, {"filing_days": 90})], [])  # coverage skips it too
        self.assertEqual(rules.first_periods(rows), {"X": "FY2025"})

    def test_the_coverage_rule_reads_the_release_fields_and_fires_on_every_cell_the_line_counts(self):
        rows = self.without("capex", "FY2025")
        rows = [_value("revenue", "FY2024", None, "not_reported") if (v["field"], v["period"]) == ("revenue", "FY2024") else v for v in rows]
        rows = [_value("opex", "FY2024", None, "agree") if (v["field"], v["period"]) == ("opex", "FY2024") else v for v in rows]
        line = set(self.missing(rows))
        ctx = rules.Context(values=rows, extractions=[], reference={(t, f, p): _ref(t, f, p, v) for t, f, p, v in REF}, years=["FY2024", "FY2025"],
                            tickers=["X"], today=date(2026, 11, 1))
        params = next(r for r in rules.load() if r["id"] == "coverage")["params"]
        self.assertNotIn("fields", params)  # one list: config.RELEASE_FIELDS
        cov = {(x.field, x.period) for x in rules.CHECKS["coverage"](ctx, params)}
        self.assertEqual(line, {("capex", "FY2025"), ("opex", "FY2024")})
        self.assertLessEqual(line, cov)
        self.assertIn(("revenue", "FY2024"), cov)  # not_reported over XBRL: coverage fires, the value row is open, the line leaves it to Open
        self.assertEqual({f for f, _ in cov} | {f for f, _ in line}, set(config.RELEASE_FIELDS))
        # a not_reported with no XBRL value stays a stated reason for coverage, and the line never counts it
        ctx.reference.pop(("X", "revenue", "FY2024"))
        self.assertNotIn(("revenue", "FY2024"), {(x.field, x.period) for x in rules.CHECKS["coverage"](ctx, params)})


PLANT = r'''
import json, sys, duckdb
from datetime import date
from ledger.checks import proof, rules; from ledger.core import store
from ledger.core.config import MVP_YEARS, PROVEN
from ledger.checks.reconcile import values_for
from ledger.review.review import decisions
plant = sys.argv[1]
con = duckdb.connect(str(store.DEFAULT_DB))
q = lambda sql, *p: [dict(zip([c[0] for c in cur.description], r)) for cur in [con.execute(sql, list(p))] for r in cur.fetchall()]
pick = "select v.ticker, v.field, v.period from \"values\" v join reference_values r using (ticker, field, period) where v.value is not null and v.ticker = 'MSFT' and v.field = 'capex' order by 3 desc limit 1"
if plant == "deleted_row":  # the value was never written: no row at all for a cell XBRL holds
    t, f, p = con.execute(pick).fetchone()
    con.execute("delete from \"values\" where ticker = ? and field = ? and period = ?", [t, f, p])
if plant == "not_reported":  # the Amazon case before T65: a blank labelled not_reported over an XBRL value
    t, f, p = con.execute(pick).fetchone()
    con.execute("update \"values\" set label = 'not_reported', value = null where ticker = ? and field = ? and period = ?", [t, f, p])
if plant == "deleted_extraction":  # the reader returns nothing for the cell; reconcile labels it as it would (MSFT's year ends 30 June)
    t, f, p = con.execute(pick).fetchone()
    end = con.execute("select period_end from \"values\" where ticker = ? and field = ? and period = ?", [t, f, p]).fetchone()[0]
    con.execute("delete from extractions where ticker = ? and field = ? and period_end = ?", [t, f, end])
    xs = q("select e.*, d.form, d.filed from extractions e join documents d using (accession) where e.ticker = 'MSFT'")
    ref = {(r["field"], r["period"]): r["value"] for r in q("select field, period, value from reference_values where ticker = 'MSFT'")}
    docs = {r["accession"]: (r["sha256"], r["parser_version"]) for r in q("select accession, sha256, parser_version from documents")}
    vals = values_for("MSFT", xs, ref, "0630", docs)
    con.execute("delete from \"values\" where ticker = 'MSFT'")
    store.write(con, "values", vals)
    print(json.dumps({"label": next(v["label"] for v in vals if (v["field"], v["period"]) == (f, p))}))
if plant == "no_reference":  # MSFT's answer key never loaded
    con.execute("delete from reference_values where ticker = 'MSFT'")
miss = proof.missing_from_dataset(con, PROVEN, decisions())
values = q("select * from \"values\" where ticker in (select unnest(?))", PROVEN)
ref = {(r["ticker"], r["field"], r["period"]): r for r in q("select * from reference_values where ticker in (select unnest(?))", PROVEN)}
params = next(r for r in rules.load() if r["id"] == "coverage")["params"]
cov = rules.CHECKS["coverage"](rules.Context(values=values, extractions=[], reference=ref, years=list(MVP_YEARS), tickers=list(PROVEN), today=date(2026, 11, 1)), params)
print(json.dumps({"missing": [[m["ticker"], m["field"], m["period"], m["why"]] for m in miss], "coverage": [[x.ticker, x.field, x.period] for x in cov],
                  "open": proof.board(con)["open"]}))
'''


class TheSixAreComplete(unittest.TestCase):
    """On the frozen tables of the six: the line reads 0, and the coverage rule agrees cell for cell. The fixtures must
    exist: a line over nothing would pass."""

    def setUp(self):
        self.assertTrue((golden.FIXTURES / "seed.json").exists(), "the golden fixtures are missing: the completeness line would pass vacuously")

    def run_plant(self, plant: str) -> dict:
        root = fixture_root()
        try:
            out = subprocess.run([sys.executable, "-c", PLANT, plant], cwd=store.ROOT, env={**os.environ, "LEDGER_ROOT": str(root)}, capture_output=True, text=True)
            self.assertEqual(out.returncode, 0, out.stderr[-2000:])
            return {k: v for l in out.stdout.strip().splitlines() if l.startswith("{") for k, v in json.loads(l).items()}
        finally:
            shutil.rmtree(root, ignore_errors=True)

    def test_the_six_read_zero_and_coverage_agrees(self):
        r = self.run_plant("none")
        self.assertEqual(r["missing"], [])
        self.assertEqual([c for c in r["coverage"] if c[2]], [])  # the coverage rule finds no missing cell on the six either

    def test_a_deleted_value_turns_it_red(self):
        r = self.run_plant("deleted_row")
        self.assertEqual([m[:2] + [m[3]] for m in r["missing"]], [["MSFT", "capex", "no row in values"]], r["missing"])
        self.assertIn(r["missing"][0][:3], r["coverage"])

    def test_not_reported_over_an_xbrl_value_is_open_and_coverage_fires(self):
        base = self.run_plant("none")["open"]
        r = self.run_plant("not_reported")
        self.assertEqual(r["missing"], [])  # one verdict: the value row is open (status.of_value), counted on Open
        self.assertEqual(r["open"], base + 1)
        self.assertEqual(len([c for c in r["coverage"] if c[:2] == ["MSFT", "capex"]]), 1)

    def test_a_deleted_extraction_is_open_not_silent(self):
        base = self.run_plant("none")["open"]
        r = self.run_plant("deleted_extraction")
        self.assertEqual(r["label"], "not_extracted")  # reconcile asks XBRL (T65): the blank is open
        self.assertEqual(r["missing"], [])  # counted once, on the Open line, not here
        self.assertEqual(r["open"], base + 1)
        self.assertEqual(len([c for c in r["coverage"] if c[1] == "capex"]), 1)

    def test_no_answer_key_loaded_turns_it_red(self):
        r = self.run_plant("no_reference")
        self.assertEqual([[m[0], m[3]] for m in r["missing"]], [["MSFT", "no XBRL answer loaded"]])


if __name__ == "__main__":
    unittest.main()
