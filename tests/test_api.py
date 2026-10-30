"""The read API: filters, grouping, CSV; saved views; plans versus reality on a small in-memory store."""
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import duckdb

from ledger import api, plans, store, views


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
    store.write(con, "attribution", [
        {"ticker": "META", "field": "capex", "period": "FY2024", "kind": "actual", "method": "ppe_category", "ai_amount": 20_000_000_000, "ai_share": 0.51, "confidence": 0.5,
         "basis": "b", "inputs": "fact:x", "model": "hyperscaler@v2", "model_sha256": "abc", "prompt_version": "attribution@v1", "run_id": "r", "input_hash": "h"},
        {"ticker": "NVDA", "field": "revenue", "period": "FY2025", "kind": "actual", "method": "segment", "ai_amount": 115_000_000_000, "ai_share": 0.88, "confidence": 0.8,
         "basis": "b", "inputs": "fact:y", "model": "chip_seller@v1", "model_sha256": "abc", "prompt_version": "attribution@v2", "run_id": "r", "input_hash": "h2"}], replace=True)
    return con


class Plans(unittest.TestCase):
    def test_newest_guidance_before_year_end_is_the_plan(self):
        con = _store()
        p = plans.plans(con)
        self.assertEqual(len(p), 1)
        self.assertEqual(p[0]["plan_low"], 37_000_000_000)  # the July update, not April's; the January actual is after year end
        self.assertEqual(p[0]["actual"], 39_230_000_000)
        self.assertEqual(p[0]["gap"], 39_230_000_000 - 38_500_000_000)
        self.assertTrue(p[0]["inside_range"])


class Api(unittest.TestCase):
    def test_filters_and_layer(self):
        con = _store()
        rows = api.query(con, "attribution", {"field": "revenue"})
        self.assertEqual([r["ticker"] for r in rows], ["NVDA"])
        self.assertEqual(rows[0]["layer"], "chip_seller")
        self.assertEqual(api.query(con, "attribution", {"layer": "hyperscaler,chip_seller"}).__len__(), 2)
        self.assertEqual(api.query(con, "attribution", {"ticker": "meta"})[0]["ticker"], "META")

    def test_group(self):
        con = _store()
        g = api.query(con, "attribution", {"group": "layer"})
        self.assertEqual({r["layer"]: r["amount"] for r in g}, {"chip_seller": 115_000_000_000, "hyperscaler": 20_000_000_000})
        with self.assertRaises(ValueError):
            api.query(con, "attribution", {"group": "basis"})

    def test_csv(self):
        con = _store()
        out = api.to_csv(api.query(con, "attribution", {"field": "revenue"}))
        self.assertTrue(out.startswith("ticker,field,period,kind,method,ai_amount"))
        self.assertIn("NVDA,revenue,FY2025", out)

    def test_projects_empty_until_the_table_exists(self):
        self.assertEqual(api.query(_store(), "projects", {}), [])

    def test_companies_and_theses_need_no_db(self):
        self.assertEqual(len(api.fetch(None, "companies")), 100)
        self.assertTrue(any(t["layer"] == "power" for t in api.fetch(None, "theses")))


class Views(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.patch = mock.patch.object(views, "FILE", Path(self.tmp.name) / "views.json")
        self.patch.start()

    def tearDown(self):
        self.patch.stop()
        self.tmp.cleanup()

    def test_save_replace_delete(self):
        v = views.save({"name": "AI capex by layer", "measure": "attribution", "filters": {"field": "capex"}, "group": "layer", "show": "bars"}, "Kenny")
        self.assertEqual(v["id"], "ai-capex-by-layer")
        views.save({**v, "show": "grid"}, "Kenny")
        d = views.load()
        self.assertEqual(len(d["views"]), 1)
        self.assertEqual(d["views"][0]["show"], "grid")
        self.assertEqual(len(d["history"]), 1)
        views.delete(v["id"], "Kenny")
        self.assertEqual(views.load()["views"], [])
        with self.assertRaises(KeyError):
            views.get(v["id"])

    def test_validation(self):
        with self.assertRaises(ValueError):
            views.save({"name": "x", "measure": "nope"}, "Kenny")
        with self.assertRaises(ValueError):
            views.save({"name": "x", "measure": "values", "group": "basis"}, "Kenny")
        with self.assertRaises(ValueError):
            views.save({"name": "x", "measure": "values"}, "")

    def test_view_data(self):
        views.save({"id": "rev", "name": "Revenue", "measure": "attribution", "filters": {"field": "revenue"}, "group": None, "show": "grid"}, "Kenny")
        out = api.view_data(_store(), "rev")
        self.assertEqual([r["ticker"] for r in out["rows"]], ["NVDA"])


class Coverage(unittest.TestCase):
    def test_counts(self):
        cov = api.coverage(_store())
        row = next(r for r in cov["rows"] if r["layer"] == "chip_seller" and r["field"] == "revenue")
        self.assertEqual(row["amount"], 1)
        self.assertEqual(row["no_row"], row["companies"] - 1)


class Cost(unittest.TestCase):
    def test_report(self):
        from ledger import cost
        con = _store()
        store.write(con, "documents", [], replace=True)
        store.write(con, "runs", [
            {"run_id": "r1", "step": "attribution", "subject": "META", "started_at": "2026-10-30T00:00:00", "seconds": 20.0, "outcome": "ok",
             "versions": json.dumps({"prompt": "attribution@v1", "model": "hyperscaler@v2", "llm": "claude-opus-5-5"}), "detail": json.dumps({"rows": 3, "model": "claude-opus-5-5", "input_tokens": 1_000_000, "output_tokens": 50_000, "attempts": 1})},
            {"run_id": "r1", "step": "attribution", "subject": "NVDA", "started_at": "2026-10-30T00:00:00", "seconds": 5.0, "outcome": "failed",
             "versions": json.dumps({"prompt": "attribution@v1"}), "detail": json.dumps({"error": "x"})}], replace=True)
        rep = cost.report(con)
        self.assertEqual(rep["total"]["usd"], 5.0)  # 1M in at $4 + 50k out at $20
        self.assertEqual(rep["steps"]["attribution"]["failed"], 1)
        self.assertEqual(rep["companies"][0]["ticker"], "META")
        self.assertIn("$5.00", cost.render(rep))


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
