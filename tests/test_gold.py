"""T82: the gold set. Golden is a regression test (it froze the Amazon blanks as expected); gold is a person's verdict
on a sample, checked against what the code produces, so a frozen error cannot pass twice."""
import json
import os
import shutil
import tempfile
import threading
import unittest
from pathlib import Path
from unittest import mock

import duckdb

from ledger import gold
from ledger.config import PROVEN


def _db(ticker="AMZN", years=("FY2022", "FY2023", "FY2024", "FY2025", "FY2026"), untagged=12, tagged=8):
    """A small database with the columns the draw reads: 3 fields x 5 years of values, and facts tagged and untagged."""
    con = duckdb.connect(":memory:")
    con.execute("create table documents (ticker varchar, accession varchar, url varchar)")
    con.execute("create table extractions (extraction_id varchar, accession varchar, ticker varchar, table_id varchar, row_label varchar, column_label varchar, cell_text varchar)")
    con.execute("create table note_extractions as select * from extractions where false")
    con.execute('create table "values" (ticker varchar, field varchar, period varchar, value bigint, label varchar, extraction_ids varchar)')
    con.execute("create table facts (ticker varchar, field varchar, dimension varchar, period varchar, value bigint, label varchar, reference bigint, extraction_ids varchar)")
    con.execute("create table reference_values (ticker varchar, field varchar, period varchar, value bigint)")
    con.execute("insert into documents values (?, 'acc-1', 'https://www.sec.gov/x.htm')", [ticker])
    for i, (f, y) in enumerate((f, y) for f in ("revenue", "capex", "opex") for y in years):
        eid = f"acc-1|{f}|{y}"
        con.execute("insert into extractions values (?, 'acc-1', ?, 't0001', ?, ?, ?)", [eid, ticker, f"Total {f}", y, f"{1000 + i:,}"])
        con.execute('insert into "values" values (?, ?, ?, ?, \'agree\', ?)', [ticker, f, y, (1000 + i) * 1_000_000, eid])
        con.execute("insert into reference_values values (?, ?, ?, ?)", [ticker, f, y, (1000 + i) * 1_000_000])
    for i in range(untagged + tagged):
        f, y = ("ppe_category", "segment_revenue")[i % 2], years[i % len(years)]
        dim, eid = f"dim{i}", f"acc-1|{f}|dim{i}|{y}"
        con.execute("insert into note_extractions values (?, 'acc-1', ?, 't0009', ?, ?, ?)", [eid, ticker, dim, y, str(i)])
        con.execute("insert into facts values (?, ?, ?, ?, ?, ?, ?, ?)", [ticker, f, dim, y, i * 1_000_000, "no_reference" if i < untagged else "agree", None if i < untagged else i * 1_000_000, eid])
    return con


class Draw(unittest.TestCase):
    def setUp(self):
        self.dir = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.dir, True)

    def test_ten_values_ten_facts_stratified_untagged_oversampled(self):
        con = _db()
        r = gold.draw(con, "v1.9.0", ["AMZN"], root=self.dir, evidence={})
        self.assertEqual((r["AMZN"]["values"], r["AMZN"]["facts"]), (10, 10))
        items = gold.load("AMZN", self.dir)["items"]
        vals = [i for i in items if i["kind"] == "value"]
        by_field = sorted(sum(i["field"] == f for i in vals) for f in ("revenue", "capex", "opex"))
        self.assertEqual(by_field, [3, 3, 4])  # spread across fields
        self.assertEqual(max(sum(i["period"] == y for i in vals) for y in {i["period"] for i in vals}), 2)  # and years
        self.assertGreaterEqual(sum(i["untagged"] for i in items), 6)  # 60% of the facts, though they are 60% of the pool here too
        it = vals[0]
        for k in ("ticker", "field", "dimension", "period", "value", "cites", "verdict", "note", "by", "at"):
            self.assertIn(k, it)
        c = it["cites"][0]
        self.assertEqual((c["accession"], c["table"]), ("acc-1", "t0001"))
        self.assertTrue(c["url"].startswith("https://www.sec.gov/x.htm#:~:text="))
        self.assertIsNone(it["verdict"])

    def test_untagged_are_oversampled_against_their_share(self):
        con = _db(untagged=4, tagged=30)  # 12% of the facts have no XBRL twin
        gold.draw(con, "v1.9.0", ["AMZN"], root=self.dir, evidence={})
        self.assertEqual(sum(i["untagged"] for i in gold.load("AMZN", self.dir)["items"]), 4)  # every one of them

    def test_the_seed_carries_the_release_version(self):
        con = _db()
        a = [i["id"] for i in gold.sample(gold.candidates(con, "AMZN", {}), "v1.9.0", "AMZN")]
        self.assertEqual(a, [i["id"] for i in gold.sample(gold.candidates(con, "AMZN", {}), "v1.9.0", "AMZN")])  # reproducible
        self.assertNotEqual(a, [i["id"] for i in gold.sample(gold.candidates(con, "AMZN", {}), "v1.10.0", "AMZN")])  # moves

    def test_a_redraw_never_overwrites_a_verdict(self):
        con = _db()
        gold.draw(con, "v1.9.0", ["AMZN"], root=self.dir, evidence={})
        first = gold.load("AMZN", self.dir)["items"][0]
        gold.record("AMZN", first["id"], "right", "", "Kenny Geiler", root=self.dir)
        con.execute('update "values" set value = 1 where field = ? and period = ?', [first["field"], first["period"]])
        r = gold.draw(con, "v1.10.0", ["AMZN"], root=self.dir, evidence={})
        self.assertEqual(r["AMZN"]["kept"], 1)
        kept = next(i for i in gold.load("AMZN", self.dir)["items"] if i["id"] == first["id"])
        self.assertEqual((kept["verdict"], kept["value"], kept["by"]), ("right", first["value"], "Kenny Geiler"))  # the claim as verified, not the live value


class Check(unittest.TestCase):
    def doc(self, items):
        return {"AMZN": {"items": items}}

    def item(self, verdict, value=716924000000, **kw):
        return {"id": gold.item_id("value", "AMZN", "revenue", "", "FY2025"), "ticker": "AMZN", "field": "revenue", "dimension": "", "period": "FY2025",
                "value": value, "verdict": verdict, "by": "Kenny Geiler", **kw}

    def row(self, value=716924000000, label="agree"):
        return {"ticker": "AMZN", "field": "revenue", "period": "FY2025", "value": value, "label": label}

    def test_right_still_equal_passes(self):
        c = gold.compare(self.doc([self.item("right")]), [self.row()], [])
        self.assertTrue(c["ok"])
        self.assertEqual((c["checked"], c["right"], c["unverified"]), (1, 1, 0))

    def test_a_planted_change_to_a_right_value_fails_naming_the_item(self):
        c = gold.compare(self.doc([self.item("right")]), [self.row(value=716924000001)], [])
        self.assertFalse(c["ok"])
        self.assertIn("value|AMZN|revenue||FY2025", c["failures"][0])

    def test_the_frozen_amazon_blank_fails(self):
        """The Amazon revenue blank (before T65): golden froze it as expected; a gold item Kenny marked right at the
        XBRL value fails against a values table where the cell is blank and labelled not_reported, or has no row."""
        g = self.doc([self.item("right", value=716924000000)])
        ref = [{"ticker": "AMZN", "field": "revenue", "period": "FY2025", "value": 716924000000}]
        blank = gold.compare(g, [self.row(value=None, label="not_reported")], [], ref, res_index={})
        self.assertFalse(blank["ok"])
        self.assertIn("a blank (not_reported)", blank["failures"][0])
        self.assertFalse(gold.compare(g, [], [], ref, res_index={})["ok"])  # and with no row at all

    def test_wrong_must_differ_or_be_open(self):
        g = self.doc([self.item("wrong", value=5, note="the filing shows 6")])
        shipped = gold.compare(g, [self.row(value=5, label="agree")], [], res_index={})
        self.assertFalse(shipped["ok"])
        self.assertIn("still ships", shipped["failures"][0])
        self.assertTrue(gold.compare(g, [self.row(value=6)], [], res_index={})["ok"])  # fixed
        self.assertTrue(gold.compare(g, [self.row(value=5, label="not_extracted")], [], res_index={})["ok"])  # open: does not ship as checked

    def test_unverified_is_counted_never_a_pass(self):
        c = gold.compare(self.doc([self.item(None), self.item("cant_say", note="?")]), [self.row(value=1)], [])
        self.assertEqual((c["unverified"], c["cant_say"], c["checked"]), (1, 1, 0))
        self.assertIn("unverified: 1 of 2", gold.summary_line(c))

    def test_facts_match_by_dimension(self):
        it = {"id": gold.item_id("fact", "AMZN", "segment_revenue", "AWS", "FY2024"), "ticker": "AMZN", "field": "segment_revenue", "dimension": "AWS", "period": "FY2024", "value": 7, "verdict": "right"}
        f = {"ticker": "AMZN", "field": "segment_revenue", "dimension": "AWS", "period": "FY2024", "value": 7, "label": "no_reference"}
        self.assertTrue(gold.compare(self.doc([it]), [], [f])["ok"])
        self.assertFalse(gold.compare(self.doc([it]), [], [{**f, "dimension": "North America"}])["ok"])


    def test_golden_check_runs_gold_against_the_tables_it_produced(self):
        """golden.gold_check is what `ledger golden --check` calls on its temporary database: a planted change fails it."""
        from ledger import golden
        con = _db()
        it = {"id": gold.item_id("value", "AMZN", "revenue", "", "FY2022"), "ticker": "AMZN", "field": "revenue", "dimension": "", "period": "FY2022",
              "value": 1000 * 1_000_000, "verdict": "right", "by": "Kenny Geiler"}
        self.assertTrue(golden.gold_check(con, self.doc([it]))["ok"])
        con.execute('update "values" set value = value + 1000000 where field = \'revenue\' and period = \'FY2022\'')
        c = golden.gold_check(con, self.doc([it]))
        self.assertFalse(c["ok"])
        self.assertIn("value|AMZN|revenue||FY2022", c["failures"][0])


class Rate(unittest.TestCase):
    def test_error_rate_has_n_and_a_wilson_interval(self):
        items = [{"verdict": "right"}] * 70 + [{"verdict": "wrong"}] + [{"verdict": "cant_say"}] * 2 + [{"verdict": None}] * 3
        r = gold.error_rate(items)
        self.assertEqual((r["wrong"], r["n"], r["cant_say"], r["unverified"]), (1, 71, 2, 3))
        self.assertEqual(r["interval"], [0.0025, 0.0756])  # 1 of 71: 0.25%–7.56%, the mirror of T53's 70 of 71
        self.assertIsNone(gold.error_rate([{"verdict": None}])["interval"])


class Verdict(unittest.TestCase):
    def setUp(self):
        self.dir = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.dir, True)
        gold.draw(_db(), "v1.9.0", ["AMZN"], root=self.dir, evidence={})
        self.iid = gold.load("AMZN", self.dir)["items"][0]["id"]

    def test_record_refuses_a_non_person_a_bad_verdict_and_a_wrong_without_a_note(self):
        before = (self.dir / "AMZN.json").read_text()
        for by in ("Claude", "Kenny", "", "Kenny Geiler agent"):
            with self.assertRaises(ValueError):
                gold.record("AMZN", self.iid, "right", "", by, root=self.dir)
        with self.assertRaises(ValueError):
            gold.record("AMZN", self.iid, "maybe", "", "Kenny Geiler", root=self.dir)
        with self.assertRaises(ValueError):
            gold.record("AMZN", self.iid, "wrong", " ", "Kenny Geiler", root=self.dir)
        with self.assertRaises(KeyError):
            gold.record("AMZN", "value|AMZN|nope||FY1999", "right", "", "Kenny Geiler", root=self.dir)
        with self.assertRaises(KeyError):
            gold.record("../AMZN", self.iid, "right", "", "Kenny Geiler", root=self.dir)
        self.assertEqual((self.dir / "AMZN.json").read_text(), before)
        it = gold.record("AMZN", self.iid, "wrong", "the filing shows 1,001", "Kenny Geiler", root=self.dir)
        self.assertEqual((it["verdict"], it["by"]), ("wrong", "Kenny Geiler"))
        self.assertEqual(next(i for i in gold.load("AMZN", self.dir)["items"] if i["id"] == self.iid)["note"], "the filing shows 1,001")
        self.assertEqual([p.name for p in self.dir.iterdir() if p.suffix == ".tmp"], [])  # nothing half-written left behind

    def test_the_route_refuses_a_non_person_and_writes_a_person(self):
        from http.server import ThreadingHTTPServer
        from urllib import error, request
        from ledger import app
        with mock.patch.object(gold, "GOLD", self.dir):
            srv = ThreadingHTTPServer(("127.0.0.1", 0), app.Handler)
            threading.Thread(target=srv.serve_forever, daemon=True).start()
            self.addCleanup(srv.shutdown)

            def post(body, ctype="application/json"):
                req = request.Request(f"http://127.0.0.1:{srv.server_address[1]}/api/gold/verdict", data=json.dumps(body).encode(), headers={"Content-Type": ctype}, method="POST")
                try:
                    with request.urlopen(req) as r:
                        return r.status, json.loads(r.read())
                except error.HTTPError as e:
                    return e.code, json.loads(e.read())
            body = {"ticker": "AMZN", "id": self.iid, "verdict": "right", "note": "", "by": "Claude"}
            code, out = post(body)
            self.assertEqual(code, 400)
            self.assertIn("config.PEOPLE", out["error"])
            self.assertEqual(post({**body, "by": "Kenny Geiler"}, ctype="text/plain")[0], 403)  # the guard every write has
            self.assertIsNone(gold.load("AMZN", self.dir)["items"][0]["verdict"])
            code, out = post({**body, "by": "Kenny Geiler"})
            self.assertEqual((code, out["verdict"], out["by"]), (200, "right", "Kenny Geiler"))


class Files(unittest.TestCase):
    def test_gold_covers_the_six(self):
        docs = gold.load_all()
        self.assertEqual(sorted(docs), sorted(PROVEN))
        for t, d in docs.items():
            drawn = [i for i in d["items"]]
            self.assertGreaterEqual(sum(i["kind"] == "value" for i in drawn), 10, t)
            self.assertGreaterEqual(sum(i["kind"] == "fact" for i in drawn), 10, t)
            self.assertTrue(any(i["untagged"] for i in drawn), t)
            self.assertTrue(d["seed"].endswith(f"|{d['release']}|{t}"), t)
            for i in drawn:
                self.assertTrue(i["verdict"] is None or (i["verdict"] in gold.VERDICTS and i["by"] and i["at"]), i["id"])


if __name__ == "__main__":
    unittest.main()
