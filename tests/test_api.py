"""The read API: filters, grouping, CSV; saved views; plans versus reality on a small in-memory store."""
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import duckdb

from ledger.web import api, views
from ledger.core import store


def _store():
    con = store.init(":memory:")
    store.write(con, "values", [
        {"ticker": "META", "field": "capex", "period": "FY2024", "period_end": "2024-12-31", "value": 39_230_000_000, "basis": "as_reported", "label": "agree",
         "first_reported": None, "source": "agent", "method": "reported", "extraction_ids": "x", "input_hash": "h"}], replace=True)
    store.write(con, "texts", [
        {"text_id": "t1", "ticker": "META", "kind": "earnings_release", "accession": None, "url": "u1", "date": "2024-07-31", "period_end": "2024-06-30", "fiscal_year": 2024, "path": "p", "sha256": "0" * 64, "chars": 10},
        {"text_id": "t0", "ticker": "META", "kind": "earnings_release", "accession": None, "url": "u0", "date": "2024-04-24", "period_end": "2024-03-31", "fiscal_year": 2024, "path": "p", "sha256": "0" * 64, "chars": 10},
        {"text_id": "t2", "ticker": "META", "kind": "earnings_release", "accession": None, "url": "u2", "date": "2025-01-29", "period_end": "2024-12-31", "fiscal_year": 2024, "path": "p", "sha256": "0" * 64, "chars": 10}], replace=True)
    store.write(con, "ai_statements", [
        {"statement_id": "s0", "text_id": "t0", "source": "earnings_release", "accession": None, "ticker": "META", "field": "capex", "period": "FY2024", "kind": "outlook", "scope": "total", "class": "explicit_amount",
         "amount_low": 35_000_000_000, "amount_high": 40_000_000_000, "share": None, "quote": "35-40", "passage": "p1", "confidence": 0.9, "notes": None, "prompt_version": "aispend@v3", "run_id": "r"},
        {"statement_id": "s1", "text_id": "t1", "source": "earnings_release", "accession": None, "ticker": "META", "field": "capex", "period": "FY2024", "kind": "outlook", "scope": "total", "class": "explicit_amount",
         "amount_low": 37_000_000_000, "amount_high": 40_000_000_000, "share": None, "quote": "37-40", "passage": "p1", "confidence": 0.9, "notes": None, "prompt_version": "aispend@v3", "run_id": "r"},
        {"statement_id": "s2", "text_id": "t2", "source": "earnings_release", "accession": None, "ticker": "META", "field": "capex", "period": "FY2024", "kind": "actual", "scope": "total", "class": "explicit_amount",
         "amount_low": 39_230_000_000, "amount_high": 39_230_000_000, "share": None, "quote": "39.23", "passage": "p1", "confidence": 0.9, "notes": None, "prompt_version": "aispend@v3", "run_id": "r"}], replace=True)
    return con


class Api(unittest.TestCase):
    def test_projects_empty_until_the_table_exists(self):
        self.assertEqual(api.query(_store(), "projects", {}), [])

    def test_companies_need_no_db(self):
        self.assertEqual(len(api.fetch(None, "companies")), 100)


class Views(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.patch = mock.patch.object(views, "FILE", Path(self.tmp.name) / "views.json")
        self.patch.start()

    def tearDown(self):
        self.patch.stop()
        self.tmp.cleanup()

    def test_validation(self):
        with self.assertRaises(ValueError):
            views.save({"name": "x", "measure": "nope"}, "Kenny Geiler")
        with self.assertRaises(ValueError):
            views.save({"name": "x", "measure": "values", "group": "basis"}, "Kenny Geiler")
        with self.assertRaises(ValueError):
            views.save({"name": "x", "measure": "values"}, "")



class ReleaseRows(unittest.TestCase):
    def test_signed_release_lists_are_typed(self):
        rows = api.release_rows("v1.4.0", "values")
        self.assertTrue(rows and isinstance(rows[0]["value"], (int, float)))
        self.assertEqual(rows[0]["release"], "v1.4.0")
        with self.assertRaises(KeyError):
            api.release_rows("v1.4.0", "projects")  # v1.4.0 predates the list


class CsvLineEndings(unittest.TestCase):
    def test_to_csv_uses_lf(self):
        out = api.to_csv([{"a": 1, "b": "x"}, {"a": 2, "b": None}])
        self.assertNotIn("\r", out)
        self.assertEqual(out, "a,b\n1,x\n2,\n")


class StatusAndFlag(unittest.TestCase):
    def test_every_row_says_whether_its_company_is_proven(self):
        rows = api.fetch(None, "companies")
        from ledger.core.config import PROVEN
        self.assertEqual({r["ticker"] for r in rows if r["proven"]}, set(PROVEN))

    def test_values_rows_carry_status_and_flag(self):
        import duckdb
        from ledger.review import resolutions
        con = duckdb.connect()
        con.execute('create table "values" (ticker text, field text, period text, period_end text, value double, label text, basis text, first_reported double, source text, extraction_ids text)')
        con.execute("insert into \"values\" values ('T','opex','FY2022','2022-12-31',74.5e6,'unresolved','as_reported',74.5e6,'agent','x'), ('MSFT','capex','FY2025','2025-06-30',64551e6,'agree','as_reported',64551e6,'agent','y')")
        con.execute("create table extractions (extraction_id text, accession text, table_id text, row_label text, column_label text, cell_text text)")  # T64: the values list joins its cited cells
        con.execute("insert into extractions values ('y','0000789019-25-000059','t0070','Additions to property and equipment','2025','(64,551)')")
        con.execute("create table documents (accession text, filed text)")
        con.execute("insert into documents values ('0000789019-25-000059','2025-07-30')")
        old = resolutions.LOG
        import tempfile, pathlib, json
        resolutions.LOG = pathlib.Path(tempfile.mkdtemp()) / "resolutions.jsonl"
        resolutions.LOG.write_text(json.dumps({"key": "finding_unconfirmed|T|opex|FY2022||jump|", "hash": "h", "state": "fix", "reason": "unit", "by": "k", "at": "2026-10-30"}) + "\n")
        try:
            rows = {(r["ticker"], r["period"]): r for r in api.fetch(con, "values")}
        finally:
            resolutions.LOG = old
        self.assertEqual((rows[("T", "FY2022")]["flag"], rows[("T", "FY2022")]["status"]), ("differs_from_xbrl", "fix_pending"))
        self.assertEqual((rows[("MSFT", "FY2025")]["flag"], rows[("MSFT", "FY2025")]["status"]), ("", ""))
        self.assertIn("status", api.to_csv(list(rows.values())).splitlines()[0])
        m = rows[("MSFT", "FY2025")]  # T64: the cited cells spelled out, the filing and its date beside the value
        self.assertEqual((m["accession"], m["filed"], m["first_reported"]), ("0000789019-25-000059", "2025-07-30", 64551e6))
        self.assertEqual(m["citations"], "0000789019-25-000059 t0070 'Additions to property and equipment' / '2025' = (64,551)")
        self.assertEqual((rows[("T", "FY2022")]["accession"], rows[("T", "FY2022")]["citations"]), (None, ""))  # a cited cell the table no longer has: nothing invented


class UnknownCompany(unittest.TestCase):
    """F-BF6: #proof/ZZZZ read "Proven" and "Ready for release" for a ticker nobody follows. The trail API answers 404
    "Unknown company" for it; a followed ticker still gets its trail."""

    def setUp(self):
        import os
        import threading
        from http.server import ThreadingHTTPServer
        from ledger.core import store
        from ledger.web import app
        if not store.DEFAULT_DB.exists() or os.environ.get("LEDGER_SKIP_DB"):
            self.skipTest("no database")
        srv = ThreadingHTTPServer(("127.0.0.1", 0), app.Handler)
        threading.Thread(target=srv.serve_forever, daemon=True).start()
        self.addCleanup(srv.shutdown)
        self.base = f"http://127.0.0.1:{srv.server_address[1]}"

    def get(self, path):
        import json
        from urllib import error, request
        try:
            with request.urlopen(self.base + path) as r:
                return r.status, json.loads(r.read())
        except error.HTTPError as e:
            return e.code, json.loads(e.read())

    def test_a_made_up_ticker_is_404_unknown_company(self):
        code, body = self.get("/api/v1/proof/ZZZZ")
        self.assertEqual((code, body["error"]), (404, "Unknown company"))
        self.assertNotIn("proven", body)

    def test_a_followed_ticker_still_has_its_trail(self):
        code, body = self.get("/api/v1/proof/apld")
        self.assertEqual(code, 200)
        self.assertEqual(body["ticker"], "APLD")


class YearRange(unittest.TestCase):
    """F-BF7: ?from= and ?to= filter a list by period or fiscal_year, inclusive, server side, so an export holds the rows
    the chart holds; a row with no year is kept, as the chart keeps it."""

    ROWS = [{"ticker": "A", "fiscal_year": "FY2022"}, {"ticker": "A", "fiscal_year": "FY2023"}, {"ticker": "A", "period": "FY2026"}, {"ticker": "A"}]

    def test_from_and_to_are_inclusive(self):
        got = api.apply(list(self.ROWS), {"from": "FY2023", "to": "fy2025"})
        self.assertEqual(got, [self.ROWS[1], self.ROWS[3]])

    def test_the_csv_export_of_the_real_taxonomy_equals_the_filtered_rows(self):
        import os
        if not store.DEFAULT_DB.exists() or os.environ.get("LEDGER_SKIP_DB"):
            self.skipTest("no database")
        con = duckdb.connect(str(store.DEFAULT_DB), read_only=True)
        try:
            q = {"measure": "spent", "category": "capex", "from": "FY2023", "to": "FY2024"}
            rows = api.query(con, "taxonomy", q)
            every = api.query(con, "taxonomy", {})
        finally:
            con.close()
        self.assertTrue(rows)
        self.assertLess(len(rows), len(every))
        self.assertTrue(all(r["measure"] == "spent" and r["category"] == "capex" and "FY2023" <= r["fiscal_year"] <= "FY2024" for r in rows))


class CompanyStates(unittest.TestCase):
    """F-BF15: a followed ticker with no filing read is "No filings yet", never Proven; a ticker nobody follows is "Unknown
    company" (404). Both words come from states.COMPANY. A busy database on the trail is a 503, never an unknown company."""

    def setUp(self):
        import os
        if not store.DEFAULT_DB.exists() or os.environ.get("LEDGER_SKIP_DB"):
            self.skipTest("no database")
        import threading
        from http.server import ThreadingHTTPServer
        from ledger.web import app
        srv = ThreadingHTTPServer(("127.0.0.1", 0), app.Handler)
        threading.Thread(target=srv.serve_forever, daemon=True).start()
        self.addCleanup(srv.shutdown)
        self.base = f"http://127.0.0.1:{srv.server_address[1]}"

    def get(self, path):
        from urllib import error, request
        try:
            with request.urlopen(self.base + path) as r:
                return r.status, json.loads(r.read())
        except error.HTTPError as e:
            return e.code, json.loads(e.read())

    def test_the_state_function(self):
        from ledger.core import states
        self.assertEqual((states.company(True, 3), states.company(False, 3), states.company(True, 0), states.company(False, 0)), ("filed", "filed", "unfiled", "unknown"))
        self.assertEqual((states.word("company", "unfiled"), states.word("company", "unknown")), ("No filings yet", "Unknown company"))

    def test_a_followed_ticker_with_no_filings_is_never_proven(self):
        from ledger.core import config
        fake = config.tracked() + [{"ticker": "ZZTR", "name": "Tracked Unfiled"}]
        with mock.patch("ledger.web.app.tracked", return_value=fake), mock.patch("ledger.checks.proof.tracked", return_value=fake):
            code, body = self.get("/api/v1/proof/ZZTR")
        self.assertEqual(code, 200)
        self.assertEqual((body["filing_state"], body["proven"]), ("unfiled", False))

    def test_a_ticker_nobody_follows_is_unknown(self):
        from ledger.core import states
        code, body = self.get("/api/v1/proof/ZZZZ")
        self.assertEqual((code, body["error"], body["state"]), (404, states.word("company", "unknown"), "unknown"))

    def test_a_filed_company_keeps_its_trail(self):
        code, body = self.get("/api/v1/proof/APLD")
        self.assertEqual((code, body["filing_state"]), (200, "filed"))

    def test_a_busy_database_is_503_not_unknown(self):
        from ledger.web import app
        with mock.patch.object(app, "_con", side_effect=app.Busy("database busy")):
            code, body = self.get("/api/v1/proof/ZZZZ")
        self.assertEqual(code, 503)

    def test_the_trail_page_reads_the_words_from_states(self):
        js = (store.ROOT / "ledger" / "web" / "pages" / "trail.js").read_text()
        self.assertIn("stateWord('company', c.filing_state)", js)
        self.assertNotIn("'No filings yet'", js)


class GoldenView(unittest.TestCase):
    """F-BF16: /api/v1/golden names what each field covers: tables_ok the tables only, regression_at that run's date, no
    top-level ok or at; the hand check is live, and a failed live read says so (gold_live false, the error)."""

    def test_fields_and_a_failing_live_read(self):
        from ledger.web import app
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / "reports").mkdir()
            (root / "reports" / "golden.json").write_text(json.dumps({"ok": False, "tables_ok": True, "at": "2026-11-05T10:00:00+00:00", "gold": {"state": "unverified", "unverified": 1, "items": 120}}))
            with mock.patch.object(app.store, "ROOT", root), mock.patch("ledger.review.gold.compare_db", side_effect=RuntimeError("gold/ unreadable")):
                g = app.golden_view()
        self.assertNotIn("ok", g)
        self.assertNotIn("at", g)
        self.assertEqual((g["tables_ok"], g["regression_at"]), (True, "2026-11-05T10:00:00+00:00"))
        self.assertEqual((g["gold_live"], g["gold"]["state"]), (False, "unverified"))
        self.assertIn("gold/ unreadable", g["gold_error"])

    def test_no_report_is_not_compared(self):
        from ledger.web import app
        with tempfile.TemporaryDirectory() as d, mock.patch.object(app.store, "ROOT", Path(d)), mock.patch.object(app, "live_hand_check", return_value={}):
            g = app.golden_view()
        self.assertEqual((g["tables_ok"], g["regression_at"]), (None, None))

    def test_proof_puts_the_snapshot_date_on_the_regression_part_only(self):
        js = (store.ROOT / "ledger" / "web" / "pages" / "proof.js").read_text()
        self.assertNotIn("g.ok", js)
        self.assertNotIn("g.at)", js)
        # the one regression line (the header's; the card that repeated it went with flow #11) ends at its date, the hand check is its own link
        self.assertIn("${tablesOk(g) ? 'Tables unchanged' : 'Tables changed'} · ${day(g.regression_at)}`);  // the one regression line", js)
        self.assertNotIn("'Regression test'", js)
        self.assertIn("' · Not live'", js)


class YearRangeValidation(unittest.TestCase):
    """F-BF17: from and to are FY plus four digits, and from is not after to; anything else is a 400."""

    def test_bad_values_are_refused(self):
        for q in ({"from": "2024"}, {"to": "fy24"}, {"from": "FY2024x"}, {"from": "FY2025", "to": "FY2023"}):
            with self.assertRaises(ValueError, msg=q):
                api.apply([{"ticker": "A", "fiscal_year": "FY2024"}], q)
        self.assertEqual(len(api.apply([{"ticker": "A", "fiscal_year": "FY2024"}], {"from": " fy2024 ", "to": "FY2024"})), 1)

    def test_the_route_answers_400(self):
        import threading
        from http.server import ThreadingHTTPServer
        from urllib import error, request
        from ledger.web import app
        srv = ThreadingHTTPServer(("127.0.0.1", 0), app.Handler)
        threading.Thread(target=srv.serve_forever, daemon=True).start()
        self.addCleanup(srv.shutdown)
        with mock.patch.object(app, "_con", return_value=mock.MagicMock()), mock.patch.object(api, "fetch", return_value=[]):
            with self.assertRaises(error.HTTPError) as e:
                request.urlopen(f"http://127.0.0.1:{srv.server_address[1]}/api/v1/taxonomy?from=FY2026&to=FY2022")
        self.assertEqual(e.exception.code, 400)


class ViewWriters(unittest.TestCase):
    """F-BF18: a saved view is saved or deleted only by a name on config.PEOPLE, as every other write."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        p = mock.patch.object(views, "FILE", Path(self.tmp.name) / "views.json")
        p.start()
        self.addCleanup(p.stop)

    def test_save_and_delete_refuse_a_name_off_the_list(self):
        v = {"name": "Capex", "measure": "values", "filters": {}, "group": None, "show": "grid"}
        for by in ("Mallory", "claude", " "):
            with self.assertRaises(ValueError):
                views.save(v, by)
        saved = views.save(v, "Kenny Geiler")
        with self.assertRaises(ValueError) as e:
            views.delete(saved["id"], "Mallory")
        self.assertIn("config.PEOPLE", str(e.exception))
        self.assertEqual([x["id"] for x in views.load()["views"]], [saved["id"]])
        views.delete(saved["id"], "Kenny Geiler")
        self.assertEqual(views.load()["views"], [])
