import unittest

import duckdb

from ledger import views, workbench


def _flow(queue):
    return {"scope": "all", "names": {"GOOGL": "Alphabet", "IRM": "Iron Mountain"}, "release": {"last": "v1.5.0"}, "changed": {"last_run": "2026-10-30T00:00:00"}, "queue": queue, "noise": 2,
            "insight": {"evaluation": {"rows": [{"ticker": "GOOGL", "field": "capex", "period": "FY2025", "measure": "share", "relation": "eq", "reference": 0.6, "outcome": "disagree", "source": {"kind": "company_statement"}}]}}}


def _con():
    con = duckdb.connect()
    con.execute("create table facts (ticker text, field text, dimension text, period text, value double, label text, reference text, period_end text)")
    con.execute("insert into facts values ('GOOGL','ppe_category','Technical infrastructure','FY2025',141852e6,'unresolved','139596000000','2025-12-31'), ('GOOGL','ppe_category','Technical infrastructure','FY2024',112504e6,'agree','112504000000','2024-12-31')")
    con.execute("create table documents (accession text, ticker text, cik integer, filed text)")
    con.execute('create table "values" (ticker text, field text, period text, value double, label text)')
    con.execute("insert into \"values\" values ('GOOGL','capex','FY2025',91447e6,'agree'), ('GOOGL','capex','FY2024',52535e6,'agree')")
    con.execute("create table attribution (ticker text, field text, period text, kind text, method text, ai_amount double, ai_share double, basis text, inputs text, confidence double)")
    con.execute("insert into attribution values ('GOOGL','capex','FY2025','actual','ppe_category',29348e6,0.5586,'growth in technical infrastructure','fact:GOOGL|ppe_category|Technical infrastructure|FY2025,fact:GOOGL|ppe_category|Technical infrastructure|FY2024',0.5)")
    return con


class Workbench(unittest.TestCase):
    def test_reference_disagrees_row_has_both_numbers_and_inputs(self):
        q = {"kind": "reference_disagrees", "state": "disagrees", "ticker": "GOOGL", "where": "AI capex FY2025", "impact": "x", "dollars": 17935e6, "new": True, "action": "method", "key": "k1", "hash": "h1", "resolution": None,
             "detail": {"field": "capex", "period": "FY2025", "measure": "share", "relation": "ge", "reference": 0.9, "ours": 0.5586, "method": "ppe_category", "basis": "what it measures", "source": {"quote": "at least 90%", "url": "https://x", "kind": "company_statement", "date": "2024-01-30"}}}
        out = workbench.items(_con(), _flow([q]))
        r = out["rows"][0]
        self.assertEqual((r["measure"], r["ours"], r["reference"], r["relation"]), ("share", 0.5586, 0.9, "ge"))
        self.assertAlmostEqual(r["delta"], -0.3414)
        self.assertEqual(r["field"], "ai_capex")
        self.assertEqual(r["evidence"]["quote"], "at least 90%")
        self.assertEqual([i["value"] for i in r["evidence"]["inputs"]], [141852e6, 112504e6])
        self.assertEqual(r["evidence"]["inputs"][0]["check"], "unresolved")
        self.assertEqual(out["open"], 1)
        self.assertEqual(out["causes"][0]["cause"], "reference_disagrees")
        years = {y["period"]: y for y in r["series"]}
        self.assertEqual(years["FY2025"]["total"], 91447e6)
        self.assertEqual(years["FY2025"]["amount"], 29348e6)
        self.assertEqual(years["FY2024"]["amount"], None)  # no attribution row that year, still a year on the chart
        self.assertEqual(years["FY2025"]["refs"][0]["reference"], 0.6)

    def test_fact_differs_row_carries_cell_and_delta(self):
        q = {"kind": "fact_differs", "state": "disagrees", "ticker": "GOOGL", "where": "ppe_category Technical infrastructure FY2025", "impact": "x", "dollars": 0, "new": False, "action": "definition", "key": "k2", "hash": "h2",
             "resolution": {"state": "accept", "by": "Kenny", "at": "2026-10-30", "reason": "ok"},
             "detail": {"field": "ppe_category", "dimension": "Technical infrastructure", "period": "FY2025", "value": 141852e6, "reference": 139596e6, "cite": {"extraction_id": "nope", "table_id": "t0130", "row_label": "Technical infrastructure(1)", "column_label": "As of | 2025", "cell_text": "141,852", "accession": "a"}, "url": "https://sec", "used_by": [], "release_value": "141852000000"}}
        out = workbench.items(_con(), _flow([q]))
        r = out["rows"][0]
        self.assertEqual(r["evidence"]["cell"]["cell_text"], "141,852")
        self.assertIsNone(r["evidence"]["png"])
        self.assertEqual(r["delta"], 2256e6)
        self.assertAlmostEqual(r["delta_pct"], 2256 / 139596)
        self.assertEqual(out["open"], 0)  # accepted: not open
        self.assertEqual([(y["period"], y["reference"]) for y in r["series"]], [("FY2024", 112504e6), ("FY2025", 139596e6)])

    def test_finding_rows_get_numbers_only_when_numeric(self):
        qs = [{"kind": "finding_unconfirmed", "state": "look", "ticker": "IRM", "where": "opex FY2024", "impact": "x", "action": "open", "key": "k3", "hash": "h3", "resolution": None,
               "detail": {"field": "opex", "period": "FY2024", "kind": "restated", "before": 10e6, "after": 12e6, "size": 0.2, "message": "m"}},
              {"kind": "finding_unconfirmed", "state": "look", "ticker": "IRM", "where": "cost_of_revenue", "impact": "x", "action": "open", "key": "k4", "hash": "h4", "resolution": None,
               "detail": {"field": "cost_of_revenue", "period": None, "kind": "row_switch", "before": None, "after": None, "size": 0, "message": "renamed"}}]
        rows = workbench.items(_con(), _flow(qs))["rows"]
        self.assertEqual((rows[0]["ours"], rows[0]["reference"], rows[0]["measure"]), (12e6, 10e6, "usd"))
        self.assertIn("Restated", rows[0]["cause_label"])
        self.assertIsNone(rows[1]["measure"])
        self.assertIn("renamed", rows[1]["cause_label"].lower())


class ChartViews(unittest.TestCase):
    def setUp(self):
        self._file = views.FILE
        import tempfile, pathlib
        views.FILE = pathlib.Path(tempfile.mkdtemp()) / "views.json"

    def tearDown(self):
        views.FILE = self._file

    def test_chart_view_saves_its_spec(self):
        v = views.save({"name": "AI capex by layer", "measure": "attribution", "filters": {"field": "capex"}, "group": None, "show": "chart", "chart": {"x": "period", "series": "layer", "type": "stacked"}}, "Kenny")
        self.assertEqual(v["chart"], {"x": "period", "series": "layer", "type": "stacked", "value": ""})
        g = views.save({"name": "Grid", "measure": "values", "filters": {}, "group": None, "show": "grid", "chart": {"x": "period", "series": "", "type": "bars"}}, "Kenny")
        self.assertNotIn("chart", g)

    def test_chart_view_rejects_a_bad_axis(self):
        with self.assertRaises(ValueError):
            views.save({"name": "Bad", "measure": "attribution", "filters": {}, "group": None, "show": "chart", "chart": {"x": "colour", "series": "", "type": "bars"}}, "Kenny")
        with self.assertRaises(ValueError):
            views.save({"name": "Bad", "measure": "attribution", "filters": {}, "group": None, "show": "chart"}, "Kenny")


if __name__ == "__main__":
    unittest.main()
