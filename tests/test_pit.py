"""Point in time (T55, ledger/pit.py): an as-of query never returns a figure filed after the date asked (no lookahead); on
today's date it says what `values` says; APLD's FY2025 revenue flips on the second 10-K's filing date; a bad date is 400
through the real Handler; and on a synthetic pair of filings a date between them answers the first."""
import json
import os
import threading
import unittest
from datetime import date
from http.server import ThreadingHTTPServer
from unittest import mock
from urllib import error, request

import duckdb

from ledger import api, pit, store
from ledger.config import PROVEN

DOC = {"cik": 1, "form": "10-K", "url": "u", "sha256": "0" * 64, "bytes": 1, "parser_version": "p", "table_count": 1, "tables_path": "t", "income_tables": None, "cash_flow_tables": None}
CELL = {"unit_stated": "millions", "unit_source": "table", "scale": 1_000_000, "table_id": "t1", "row_label": "Revenue", "column_label": "2024", "cell_text": "1", "confidence": 1.0,
        "notes": None, "prompt_version": "s@v1", "run_id": "r"}


def _synthetic():
    """Two 10-Ks for FY2024 of X: the first (filed 2025-02-01) says revenue 100m, the second (filed 2026-02-01) restates it to 120m;
    opex's three cells only in the second."""
    con = store.init(":memory:")
    store.write(con, "documents", [{**DOC, "accession": "0000000001-25-000001", "ticker": "X", "period": "2024-12-31", "filed": "2025-02-01"},
                                   {**DOC, "accession": "0000000001-26-000001", "ticker": "X", "period": "2024-12-31", "filed": "2026-02-01"}])
    cells = [("0000000001-25-000001", "revenue", 100_000_000), ("0000000001-26-000001", "revenue", 120_000_000),
             ("0000000001-26-000001", "cost_of_revenue", 50_000_000), ("0000000001-26-000001", "operating_income", 30_000_000)]
    store.write(con, "extractions", [{**CELL, "extraction_id": f"{a}|{f}|2024-01-01|2024-12-31", "accession": a, "ticker": "X", "field": f, "period_start": "2024-01-01", "period_end": "2024-12-31", "value": v}
                                     for a, f, v in cells])
    store.write(con, "values", [{"ticker": "X", "field": "revenue", "period": "FY2024", "period_end": "2024-12-31", "value": 120_000_000, "basis": "restated", "label": "agree",
                                 "first_reported": 100_000_000, "source": "agent", "method": "reported", "extraction_ids": "0000000001-26-000001|revenue|2024-01-01|2024-12-31", "input_hash": "h"}])
    return con


class Synthetic(unittest.TestCase):
    def test_a_date_between_two_filings_answers_the_first(self):
        con = _synthetic()
        self.assertEqual(pit.as_of(con, "2025-01-31"), [])  # nothing filed yet: absent, not null
        first = pit.as_of(con, "2025-06-30")
        self.assertEqual([(r["field"], r["value"], r["accession"], r["restated_later"]) for r in first], [("revenue", 100_000_000, "0000000001-25-000001", True)])
        second = pit.as_of(con, "2026-02-01")
        self.assertEqual({(r["field"], r["value"]) for r in second}, {("revenue", 120_000_000), ("opex", 40_000_000)})  # opex only once its three cells exist
        self.assertFalse(any(r["restated_later"] for r in second))

    def test_values_as_of_keeps_basis_and_first_reported_and_the_taxonomy_drops_rows_filed_after(self):
        con = _synthetic()
        with mock.patch.object(api, "SCOPE", ["X"]):
            rows = api.query(con, "values", {"as_of": "2025-06-30"})
        self.assertEqual([(r["value"], r["basis"], r["first_reported"], r["filed"], r["as_of"]) for r in rows], [(100_000_000, "restated", 100_000_000, "2025-02-01", "2025-06-30")])
        self.assertNotIn("check_label", rows[0])
        tax = [{"ticker": "X", "fiscal_year": "FY2024", "measure": "spent", "category": "capex", "accession": "a", "check": "agree", "check_method": "xbrl", "filed": "2026-02-01"},
               {"ticker": "X", "fiscal_year": "FY2024", "measure": "committed", "category": "purchase_obligations", "filed": "2026-02-01"},
               {"ticker": "X", "fiscal_year": "FY2024", "measure": "committed", "category": "finance_lease_liability", "filed": "2025-02-01"},
               {"ticker": "X", "fiscal_year": "FY2024", "measure": "company_stated_ai", "category": "ai_capex", "filed": None}]
        kept = pit.taxonomy_as_of(con, tax, "2025-06-30", ["X"])
        self.assertEqual([r["category"] for r in kept], ["finance_lease_liability"])  # no capex cell by then; the later note and the undated row are gone

    def test_bad_dates_and_other_lists_are_value_errors(self):
        con = _synthetic()
        for bad in ("2025-13-01", "yesterday", "2025"):
            with self.assertRaises(ValueError):
                api.query(con, "values", {"as_of": bad})
        with self.assertRaises(ValueError):
            api.query(con, "facts", {"as_of": "2025-06-30"})


class Handler(unittest.TestCase):
    def test_a_bad_date_is_400_through_the_handler(self):
        from ledger import app
        srv = ThreadingHTTPServer(("127.0.0.1", 0), app.Handler)
        threading.Thread(target=srv.serve_forever, daemon=True).start()
        self.addCleanup(srv.shutdown)
        with mock.patch("ledger.app._con", return_value=mock.MagicMock()):
            try:
                request.urlopen(f"http://127.0.0.1:{srv.server_address[1]}/api/v1/values?as_of=2025-02-30")
                self.fail("expected 400")
            except error.HTTPError as e:
                self.assertEqual(e.code, 400)
                self.assertIn("as_of", json.loads(e.read())["error"])


@unittest.skipUnless(store.DEFAULT_DB.exists() and not os.environ.get("LEDGER_SKIP_DB"), "no data/ledger.duckdb")
class RealDatabase(unittest.TestCase):
    """On the six: no lookahead at any filing date, today equals `values`, and APLD FY2025 revenue flips on 2026-07-29."""

    @classmethod
    def setUpClass(cls):
        cls.con = duckdb.connect(str(store.DEFAULT_DB), read_only=True)
        cls.six = list(PROVEN)

    @classmethod
    def tearDownClass(cls):
        cls.con.close()

    def test_no_lookahead_at_every_filing_date(self):
        days = [r[0] for r in self.con.execute("select distinct filed from documents where ticker in (select unnest(?)) order by 1", [self.six]).fetchall()]
        self.assertGreater(len(days), 10)
        seen = 0
        for d in days:
            for r in pit.as_of(self.con, d, self.six):
                self.assertLessEqual(r["filed"], d, r)
                seen += 1
        self.assertGreater(seen, 0)

    def test_today_equals_values(self):
        today = date.today().isoformat()
        live = {(v[0], v[1], v[2]): v[3] for v in self.con.execute('select ticker, field, period, value from "values" where value is not null and ticker in (select unnest(?))', [self.six]).fetchall()}
        got = {(r["ticker"], r["field"], r["period"]): r["value"] for r in pit.as_of(self.con, today, self.six)}
        self.assertEqual(got, live)

    def test_apld_fy2025_revenue_flips_on_the_second_10k(self):
        pick = lambda d: next(r for r in pit.as_of(self.con, d, ["APLD"]) if r["field"] == "revenue" and r["period"] == "FY2025")
        before, after = pick("2026-07-28"), pick("2026-07-29")
        self.assertEqual((before["value"], before["accession"], before["restated_later"]), (144_193_000, "0001144879-25-000021", True))
        self.assertEqual((after["value"], after["accession"], after["restated_later"]), (228_569_000, "0001144879-26-000048", False))
        self.assertFalse([r for r in pit.as_of(self.con, "2025-07-29", ["APLD"]) if r["period"] == "FY2025"])  # the day before the first 10-K: absent
        tax = api.query(self.con, "taxonomy", {"as_of": "2026-07-28", "ticker": "APLD", "measure": "spent", "category": "capex"})
        self.assertTrue(tax and all(r["filed"] <= "2026-07-28" and r["as_of"] == "2026-07-28" for r in tax))


if __name__ == "__main__":
    unittest.main()
