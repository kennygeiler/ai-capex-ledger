"""T81: completeness against the answer key. Every (company, field, year) XBRL holds a value for ships a value or is an
open item; anything else is a silent blank, counted by the Release checklist's required line "Answer-key values missing
from the dataset". The coverage rule fires on the same cells. On the six the line reads 0; planting a deleted row or a
not_reported over an XBRL value turns it red."""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from datetime import date
from pathlib import Path

from ledger import golden, proof, rules, store
from tests.test_status import fixture_root

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
            "period_end": f"{p[2:]}-12-31", "accession": "0000000000-25-000001", "restated": False, "original_value": None}


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

    def missing(self, values, idx=None, ds=None, excs=()):
        self.con.execute('delete from "values"')
        self.con.execute("delete from exceptions")
        store.write(self.con, "values", values)
        if excs:
            store.write(self.con, "exceptions", list(excs))
        return [(m["field"], m["period"]) for m in proof.missing_from_dataset(self.con, ["X"], idx=idx or {}, ds=ds or [])]

    def swap(self, f, p, row):
        return [row if (v["field"], v["period"]) == (f, p) else v for v in self.complete]

    def test_complete_reads_zero(self):
        self.assertEqual(self.missing(self.complete), [])

    def test_a_deleted_value_row_counts(self):
        self.assertEqual(self.missing([v for v in self.complete if (v["field"], v["period"]) != ("capex", "FY2025")]), [("capex", "FY2025")])

    def test_not_reported_over_an_xbrl_value_counts(self):
        self.assertEqual(self.missing(self.swap("revenue", "FY2024", _value("revenue", "FY2024", None, "not_reported"))), [("revenue", "FY2024")])

    def test_a_blank_with_a_checked_label_counts(self):
        self.assertEqual(self.missing(self.swap("opex", "FY2025", _value("opex", "FY2025", None, "agree"))), [("opex", "FY2025")])

    def test_not_extracted_is_open_not_silent(self):
        self.assertEqual(self.missing(self.swap("revenue", "FY2025", _value("revenue", "FY2025", None, "not_extracted"))), [])

    def test_a_persons_resolution_accounts_for_it_a_runs_does_not(self):
        rows = self.swap("revenue", "FY2024", _value("revenue", "FY2024", None, "not_reported"))
        key = ("values", "X", "revenue", "", "FY2024", "")
        person = {key: {"id": "r1", "state": "explain", "status": "explained", "by": "Kenny Geiler", "at": "", "reason": "the filer withdrew the tag"}}
        run = {key: {"id": "r2", "state": "explain", "status": "explained", "by": "Replication run (Claude)", "at": "", "reason": "fine"}}
        fix = {key: {"id": "r3", "state": "fix", "status": "open", "by": "Replication run (Claude)", "at": "", "reason": "re-read it"}}
        self.assertEqual(self.missing(rows, idx=person), [])
        self.assertEqual(self.missing(rows, idx=run), [("revenue", "FY2024")])
        self.assertEqual(self.missing(rows, idx=fix), [])  # a fix is open: the Open line counts it

    def test_a_reject_decision_by_a_person_accounts_for_it(self):
        e = {"exception_id": "xbrl_reconcile|X|capex|FY2025|None", "rule_id": "xbrl_reconcile", "severity": "warn", "ticker": "X", "field": "capex",
             "period": "FY2025", "subject": None, "message": "m", "input_hash": "ih"}
        d = lambda who: [{"decision_id": "d1", "exception_id": e["exception_id"], "kind": "reject", "value": None, "reason": "r", "reviewer": who, "input_hash": "ih"}]
        self.assertEqual(self.missing(self.complete, ds=d("Kenny Geiler"), excs=[e]), [])
        self.assertEqual(self.missing(self.complete, ds=d("Claude"), excs=[e]), [("capex", "FY2025")])

    def test_an_override_fills_it(self):
        e = {"exception_id": "coverage|X|capex|FY2025|None", "rule_id": "coverage", "severity": "warn", "ticker": "X", "field": "capex",
             "period": "FY2025", "subject": None, "message": "m", "input_hash": "ih"}
        ds = [{"decision_id": "d1", "exception_id": e["exception_id"], "kind": "override", "value": 22, "reason": "r", "reviewer": "Kenny Geiler", "input_hash": "ih"}]
        self.assertEqual(self.missing(self.swap("capex", "FY2025", _value("capex", "FY2025", None, "not_reported")), ds=ds, excs=[e]), [])

    def test_no_xbrl_value_never_counts(self):
        self.con.execute("delete from reference_values where field = 'capex'")
        self.assertEqual(self.missing([v for v in self.complete if v["field"] != "capex"]), [])

    def test_the_coverage_rule_fires_on_every_cell_the_line_counts(self):
        rows = [v for v in self.complete if (v["field"], v["period"]) != ("capex", "FY2025")]
        rows = [_value("revenue", "FY2024", None, "not_reported") if (v["field"], v["period"]) == ("revenue", "FY2024") else v for v in rows]
        line = set(self.missing(rows))
        ctx = rules.Context(values=rows, extractions=[], reference={(t, f, p): _ref(t, f, p, v) for t, f, p, v in REF}, years=["FY2024", "FY2025"],
                            tickers=["X"], today=date(2026, 11, 1))
        cov = {(x.field, x.period) for x in rules.CHECKS["coverage"](ctx, {"fields": ["revenue", "capex", "opex"], "filing_days": 90})}
        self.assertEqual(line, {("capex", "FY2025"), ("revenue", "FY2024")})
        self.assertLessEqual(line, cov)
        # a not_reported with no XBRL value stays a stated reason for coverage, and the line never counts it
        ctx.reference.pop(("X", "revenue", "FY2024"))
        self.assertNotIn(("revenue", "FY2024"), {(x.field, x.period) for x in rules.CHECKS["coverage"](ctx, {"fields": ["revenue"], "filing_days": 90})})


PLANT = r'''
import json, sys, duckdb
from datetime import date
from ledger import proof, resolutions, rules, store
from ledger.config import MVP_YEARS, PROVEN
from ledger.reconcile import values_for
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
miss = proof.missing_from_dataset(con, PROVEN)
values = q("select * from \"values\" where ticker in (select unnest(?))", PROVEN)
ref = {(r["ticker"], r["field"], r["period"]): r for r in q("select * from reference_values where ticker in (select unnest(?))", PROVEN)}
cov = rules.CHECKS["coverage"](rules.Context(values=values, extractions=[], reference=ref, years=list(MVP_YEARS), tickers=list(PROVEN), today=date(2026, 11, 1)),
                               {"fields": ["revenue", "capex", "opex"], "filing_days": 90})
print(json.dumps({"missing": [[m["ticker"], m["field"], m["period"]] for m in miss], "coverage": [[x.ticker, x.field, x.period] for x in cov],
                  "open": proof.board(con)["open"]}))
'''


@unittest.skipIf(not (golden.FIXTURES / "seed.json").exists(), "no fixtures")
class TheSixAreComplete(unittest.TestCase):
    """On the frozen tables of the six: the line reads 0, and the coverage rule agrees cell for cell."""

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
        self.assertEqual(len(r["missing"]), 1, r["missing"])
        self.assertEqual(r["missing"][0][:2], ["MSFT", "capex"])
        self.assertIn(r["missing"][0], r["coverage"])

    def test_not_reported_over_an_xbrl_value_turns_it_red(self):
        r = self.run_plant("not_reported")
        self.assertEqual(len(r["missing"]), 1, r["missing"])
        self.assertEqual(r["missing"][0][:2], ["MSFT", "capex"])
        self.assertIn(r["missing"][0], r["coverage"])

    def test_a_deleted_extraction_is_open_not_silent(self):
        base = self.run_plant("none")["open"]
        r = self.run_plant("deleted_extraction")
        self.assertEqual(r["label"], "not_extracted")  # reconcile asks XBRL (T65): the blank is open
        self.assertEqual(r["missing"], [])  # counted once, on the Open line, not here
        self.assertEqual(r["open"], base + 1)
        self.assertEqual(len([c for c in r["coverage"] if c[1] == "capex"]), 1)


if __name__ == "__main__":
    unittest.main()
