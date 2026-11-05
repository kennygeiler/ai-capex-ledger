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

from ledger.review import gold
from ledger.core import store
from urllib.parse import quote
from ledger.core.config import PROVEN


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


    def test_a_verdict_recorded_while_the_draw_runs_survives(self):
        con = _db()
        gold.draw(con, "v1.9.0", ["AMZN"], root=self.dir, evidence={})
        iid = gold.load("AMZN", self.dir)["items"][0]["id"]
        real = gold.candidates

        def slow(*a, **kw):  # the draw is building its sample; a person presses Right meanwhile
            gold.record("AMZN", iid, "right", "", "Kenny Geiler", root=self.dir)
            return real(*a, **kw)
        with mock.patch.object(gold, "candidates", side_effect=slow):
            gold.draw(con, "v1.10.0", ["AMZN"], root=self.dir, evidence={})
        it = next(i for i in gold.load("AMZN", self.dir)["items"] if i["id"] == iid)
        self.assertEqual((it["verdict"], it["by"]), ("right", "Kenny Geiler"))

    def test_rows_with_no_value_are_not_drawn(self):
        con = _db()
        con.execute('update "values" set value = null where field = \'capex\'')
        con.execute("update facts set value = null where field = 'ppe_category'")
        gold.draw(con, "v1.9.0", ["AMZN"], root=self.dir, evidence={})
        items = gold.load("AMZN", self.dir)["items"]
        self.assertTrue(all(i["value"] is not None for i in items))
        self.assertFalse(any(i["field"] in ("capex", "ppe_category") for i in items))

    def test_kept_verdicts_keep_their_draw_and_the_header_says_the_file_mixes(self):
        con = _db()
        gold.draw(con, "v1.9.0", ["AMZN"], root=self.dir, evidence={})
        first = gold.load("AMZN", self.dir)["items"][0]
        gold.record("AMZN", first["id"], "right", "", "Kenny Geiler", root=self.dir)
        con.execute('delete from "values" where field = ? and period = ?', [first["field"], first["period"]])  # the redraw cannot pick it again
        gold.draw(con, "v1.10.0", ["AMZN"], root=self.dir, evidence={})
        doc = gold.load("AMZN", self.dir)
        kept = next(i for i in doc["items"] if i["id"] == first["id"])
        self.assertEqual((kept["release"], kept["seed"], kept["drawn_at"]), (first["release"], first["seed"], first["drawn_at"]))
        self.assertEqual(kept["release"], "v1.9.0")
        self.assertEqual((doc["release"], doc["draws"]), ("v1.10.0", ["v1.9.0", "v1.10.0"]))
        self.assertIn("mixes draws", doc["note"])
        self.assertIn("11 values", doc["note"])


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
        self.assertTrue(gold.compare(g, [self.row(value=5, label="not_extracted")], [], res_index={})["ok"])  # open: does not ship as checked
        self.assertTrue(gold.compare(g, [self.row(value=None, label="not_extracted")], [], res_index={})["ok"])  # a blank ships nothing

    def test_wrong_changed_since_the_verdict_fails_re_verify(self):
        c = gold.compare(self.doc([self.item("wrong", value=5, note="the filing shows 6")]), [self.row(value=6)], [], res_index={})
        self.assertFalse(c["ok"])
        self.assertIn("changed since verdict, re-verify", c["failures"][0])

    def test_wrong_with_the_row_gone_fails_re_verify(self):
        c = gold.compare(self.doc([self.item("wrong", value=5, note="x")]), [], [], res_index={})
        self.assertIn("row gone, re-verify", c["failures"][0])

    def test_wrong_fact_whose_dimension_was_renamed_is_row_gone(self):
        it = {"id": gold.item_id("fact", "AMZN", "segment_revenue", "AWS", "FY2024"), "ticker": "AMZN", "field": "segment_revenue", "dimension": "AWS", "period": "FY2024", "value": 7, "verdict": "wrong", "note": "x"}
        f = {"ticker": "AMZN", "field": "segment_revenue", "dimension": "Amazon Web Services", "period": "FY2024", "value": 7, "label": "no_reference"}
        c = gold.compare(self.doc([it]), [], [f], res_index={})
        self.assertFalse(c["ok"])
        self.assertIn("row gone, re-verify", c["failures"][0])

    def test_right_fails_on_a_null_gold_value_and_a_missing_row(self):
        self.assertIn("holds no value", gold.compare(self.doc([self.item("right", value=None)]), [self.row(value=None, label="not_reported")], [], res_index={})["failures"][0])
        self.assertIn("row gone", gold.compare(self.doc([self.item("right")]), [], [], res_index={})["failures"][0])

    def test_right_is_value_only(self):
        """An open row whose value is unchanged passes gold: open for another reason is the Open line's job (EVALS.md)."""
        self.assertTrue(gold.compare(self.doc([self.item("right")]), [self.row(label="unresolved")], [], res_index={})["ok"])

    def test_unverified_is_counted_never_a_pass(self):
        c = gold.compare(self.doc([self.item(None), self.item("cant_say", note="?")]), [self.row(value=1)], [])
        self.assertEqual((c["unverified"], c["cant_say"], c["checked"]), (1, 1, 0))
        self.assertEqual(c["state"], "unverified")
        line = gold.summary_line(c)
        self.assertIn("unverified 1 of 2", line)
        self.assertNotIn("pass,", line)
        self.assertEqual(gold.compare({}, [], [])["state"], "unverified")  # nothing checked is never a pass

    def test_facts_match_by_dimension(self):
        it = {"id": gold.item_id("fact", "AMZN", "segment_revenue", "AWS", "FY2024"), "ticker": "AMZN", "field": "segment_revenue", "dimension": "AWS", "period": "FY2024", "value": 7, "verdict": "right"}
        f = {"ticker": "AMZN", "field": "segment_revenue", "dimension": "AWS", "period": "FY2024", "value": 7, "label": "no_reference"}
        self.assertTrue(gold.compare(self.doc([it]), [], [f])["ok"])
        self.assertFalse(gold.compare(self.doc([it]), [], [{**f, "dimension": "North America"}])["ok"])


    def test_golden_check_runs_gold_against_the_tables_it_produced(self):
        """golden.gold_check is what `ledger golden --check` calls on its temporary database: a planted change fails it."""
        from ledger.checks import golden
        con = _db()
        it = {"id": gold.item_id("value", "AMZN", "revenue", "", "FY2022"), "ticker": "AMZN", "field": "revenue", "dimension": "", "period": "FY2022",
              "value": 1000 * 1_000_000, "verdict": "right", "by": "Kenny Geiler"}
        self.assertTrue(golden.gold_check(con, self.doc([it]))["ok"])
        con.execute('update "values" set value = value + 1000000 where field = \'revenue\' and period = \'FY2022\'')
        c = golden.gold_check(con, self.doc([it]))
        self.assertFalse(c["ok"])
        self.assertIn("value|AMZN|revenue||FY2022", c["failures"][0])


class Vacuous(unittest.TestCase):
    """A gold set that is not there, or does not read, never passes; golden.json is still written on every path."""
    def setUp(self):
        self.dir = Path(tempfile.mkdtemp()) / "gold"
        self.addCleanup(shutil.rmtree, self.dir.parent, True)

    def check(self):
        from ledger.checks import golden
        with mock.patch.object(gold, "GOLD", self.dir):
            return golden.gold_check(_db())

    def test_no_folder_fails(self):
        c = self.check()
        self.assertFalse(c["ok"])
        self.assertIn("no gold/ folder", c["failures"][0])

    def test_a_proven_company_without_a_file_or_items_fails_naming_it(self):
        gold.draw(_db(), "v1.9.0", ["AMZN"], root=self.dir, evidence={})
        (self.dir / "MSFT.json").write_text(json.dumps({"items": []}))
        c = self.check()
        self.assertFalse(c["ok"])
        self.assertTrue(any("gold/NVDA.json: missing" in f for f in c["failures"]))
        self.assertTrue(any("gold/MSFT.json: no items" in f for f in c["failures"]))

    def test_a_corrupt_or_malformed_file_fails_naming_the_file_and_the_rest_still_load(self):
        for t in PROVEN:
            gold.draw(_db(t), "v1.9.0", [t], root=self.dir, evidence={})
        (self.dir / "AMD.json").write_text("{not json")
        doc = json.loads((self.dir / "GOOGL.json").read_text())
        doc["items"][0]["verdict"] = "Right"
        (self.dir / "GOOGL.json").write_text(json.dumps(doc))
        doc = json.loads((self.dir / "MSFT.json").read_text())
        del doc["items"][0]["value"]
        (self.dir / "MSFT.json").write_text(json.dumps(doc))
        c = self.check()
        self.assertFalse(c["ok"])
        joined = " ".join(c["failures"])
        for want in ("gold/AMD.json: does not read", "gold/GOOGL.json", "'Right'", "gold/MSFT.json", "lacks value"):
            self.assertIn(want, joined)
        self.assertEqual(c["items"], 60)  # AMZN, APLD, NVDA still loaded

    def test_a_check_that_raises_is_a_named_failure_not_a_traceback(self):
        from ledger.checks import golden
        with mock.patch.object(gold, "compare_db", side_effect=RuntimeError("boom")):
            c = golden.gold_check(_db())
        self.assertFalse(c["ok"])
        self.assertIn("boom", c["failures"][0])


class Cli(unittest.TestCase):
    """`ledger golden --check`: equal tables and a gold failure exit 1; equal tables and only unverified items exit 0, and
    both lines print, so the tables' "equal" never reads as a gold pass."""
    def run_cli(self, g_):
        import contextlib
        import io
        from ledger.cli import golden as cli
        root = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, root, True)
        r = {"ok": g_["state"] == "pass", "exit_ok": not g_["failures"], "diffs": {}, "log": [], "gold": g_}  # as golden.check builds it
        buf = io.StringIO()
        with mock.patch.object(cli, "check", return_value=r), mock.patch.object(cli.store, "ROOT", root), contextlib.redirect_stdout(buf):
            code = cli.main(["--check"])
        return code, buf.getvalue(), json.loads((root / "reports" / "golden.json").read_text())

    def test_gold_failure_with_equal_tables_exits_1(self):
        g_ = gold.compare({"AMZN": {"items": [Check().item("right")]}}, [Check().row(value=1)], [])
        code, out, rep = self.run_cli(g_)
        self.assertEqual(code, 1)
        self.assertIn("every table equals", out)
        self.assertIn("gold: FAIL", out)
        self.assertEqual((rep["tables_ok"], rep["ok"], rep["gold"]["state"]), (True, False, "fail"))

    def test_unverified_only_exits_0_and_says_unverified(self):
        g_ = gold.compare({"AMZN": {"items": [Check().item(None)]}}, [Check().row()], [])
        code, out, rep = self.run_cli(g_)
        self.assertEqual(code, 0)
        self.assertIn("gold: unverified 1 of 1", out)
        self.assertEqual(rep["gold"]["state"], "unverified")
        # exit 0 is the tables' check only: the report never calls unverified ok, and the Release line is red on it
        self.assertEqual((rep["ok"], rep["gold"]["ok"], rep["gold"]["holds"]), (False, False, True))
        from ledger.release.checklist import hand_check_line, regression_line
        self.assertEqual(regression_line({**rep, "git": "abc1234", "dirty": False}, head="abc1234")["state"], "pass")  # the tables' line says only that the tables are unchanged (on this commit, F20)
        with mock.patch.object(gold, "compare_db", return_value=g_):  # the hand check is its own line, red on unchecked
            line = hand_check_line(None, {"AMZN": {"items": [Check().item(None)]}}, [])
        self.assertIn("0 of 1 with a verdict", line["note"])
        self.assertEqual((line["state"], line["required"], line["ok"]), ("fail", True, False))

    def test_zero_verdicts_is_never_ok(self):
        """The vacuous pass: 0 of N verdicts, nothing failing, used to read ok=true and turn the Release golden line green."""
        g_ = gold.compare({"AMZN": {"items": [Check().item(None), Check().item(None)]}}, [Check().row()], [])
        self.assertEqual((g_["ok"], g_["holds"], g_["state"], g_["checked"]), (False, True, "unverified", 0))
        from ledger.release.checklist import hand_check_line, regression_line
        with mock.patch.object(gold, "compare_db", return_value=g_):
            self.assertEqual(hand_check_line(None, {}, [])["state"], "fail")
        with mock.patch.object(gold, "compare_db", return_value={**g_, "state": "pass", "unverified": 0}):
            self.assertEqual(hand_check_line(None, {}, [])["state"], "pass")
        self.assertEqual(regression_line({"ok": True, "tables_ok": False})["state"], "fail")
        self.assertEqual(regression_line(None)["state"], "fail")
        self.assertEqual(regression_line({"ok": True, "at": "x"})["state"], "fail")  # a report from before gold: no gold state, never green


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
        with self.assertRaises(ValueError):
            gold.record("AMZN", self.iid, "cant_say", "", "Kenny Geiler", root=self.dir)
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
        from ledger.web import app
        with mock.patch.object(gold, "GOLD", self.dir):
            srv = ThreadingHTTPServer(("127.0.0.1", 0), app.Handler)
            threading.Thread(target=srv.serve_forever, daemon=True).start()
            self.addCleanup(srv.shutdown)

            base = f"http://127.0.0.1:{srv.server_address[1]}"

            def post(body, ctype="application/json", origin=None):
                req = request.Request(f"{base}/api/gold/verdict", data=json.dumps(body).encode(), headers={"Content-Type": ctype, **({"Origin": origin} if origin else {})}, method="POST")
                try:
                    with request.urlopen(req) as r:
                        return r.status, json.loads(r.read())
                except error.HTTPError as e:
                    return e.code, json.loads(e.read())
            body = {"ticker": "AMZN", "id": self.iid, "verdict": "right", "note": "", "by": "Claude"}
            code, out = post(body)
            self.assertEqual(code, 400)
            self.assertIn("config.PEOPLE", out["error"])
            self.assertEqual(post({**body, "by": "Kenny Geiler"}, ctype="text/plain")[0], 403)  # the guards every write has
            self.assertEqual(post({**body, "by": "Kenny Geiler"}, origin="https://evil.example")[0], 403)
            with mock.patch.object(app, "_con", side_effect=app.Busy("busy")):  # the summary counts live groups; a busy database still answers, as drawn
                with request.urlopen(f"{base}/api/v1/gold") as r:
                    d = json.loads(r.read())
                    self.assertEqual((d["companies"][0]["ticker"], d["groups_live"]), ("AMZN", False))
            try:
                request.urlopen(f"{base}/api/v1/gold?t=BOGUS")
                self.fail("?t=BOGUS answered 200")
            except error.HTTPError as e:
                self.assertEqual(e.code, 400)
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


class LiveHandCheck(unittest.TestCase):
    """F-BF2: Release's Hand check line and Proof's header read the verdicts in gold/*.json live, through gold.compare_db,
    so a verdict given on Proof counts with no `ledger golden --check` run; the Regression test line keeps reading the
    report, with its date."""

    def setUp(self):
        if not store.DEFAULT_DB.exists() or os.environ.get("LEDGER_SKIP_DB"):
            self.skipTest("no database")
        self.root = Path(tempfile.mkdtemp(prefix="gold-"))
        self.addCleanup(shutil.rmtree, self.root, True)
        for f in gold.GOLD.glob("*.json"):
            shutil.copy(f, self.root / f.name)
        p = mock.patch.object(gold, "GOLD", self.root)
        p.start()
        self.addCleanup(p.stop)
        docs, _ = gold.load_checked()
        self.open_ = [(t, it) for t, d in sorted(docs.items()) for it in d["items"] if not gold.has_verdict(it)]
        if not self.open_:  # every real item has a verdict: clear one in the copy, so there is something to give
            t = sorted(docs)[0]
            d = json.loads((self.root / f"{t}.json").read_text())
            d["items"][0].update({"verdict": None, "note": "", "by": None, "at": None})
            (self.root / f"{t}.json").write_text(json.dumps(d))
            self.open_ = [(t, d["items"][0])]

    def line(self):
        from ledger.release.checklist import hand_check_line
        con = duckdb.connect(str(store.DEFAULT_DB), read_only=True)
        try:
            return hand_check_line(con)
        finally:
            con.close()

    def test_a_verdict_written_to_a_gold_file_changes_the_line_with_no_cli_run(self):
        t, it = self.open_[0]
        before = self.line()
        self.assertEqual((before["label"], before["state"]), ("Hand check", "fail"))
        self.assertEqual(before["link"], f"proof?gold={self.open_[0][0]}")  # Fix in: the first unchecked item's company
        self.assertIn({"company": t, "item": gold.what(it), "link": f"proof?gold={t}&item={quote(it['id'], safe='')}"}, before["detail"])
        n = int(before["note"].split(" of ")[0])
        gold.record(t, it["id"], "right", "", "Kenny Geiler")
        after = self.line()
        self.assertTrue(after["note"].startswith(f"{n + 1} of "), after["note"])
        self.assertNotIn(it["id"], json.dumps(after["detail"]).replace("%7C", "|"))

    def test_proofs_header_reads_the_same_live_verdicts(self):
        from ledger.web import app
        t, it = self.open_[0]
        n = app.live_hand_check(None)["gold"]["unverified"]
        gold.record(t, it["id"], "right", "", "Kenny Geiler")
        live = app.live_hand_check({"state": "unverified", "unverified": n})
        self.assertEqual((live["gold_live"], live["gold"]["unverified"], live["gold_at_check"]["unverified"]), (True, n - 1, n))
