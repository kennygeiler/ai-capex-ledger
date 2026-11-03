"""The per-agent score (T49): counts with denominators from the live tables through status.state (via proof.company),
the twin only where the rows have one, the faults only where a run measured them."""
import json
import os
import shutil
import subprocess
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest import mock

from ledger.checks import score
from ledger.core import store


def _doc(acc, ticker, period):
    return {"accession": acc, "ticker": ticker, "cik": 1, "form": "10-K", "period": period, "filed": period, "url": "u", "sha256": "0" * 64, "bytes": 1,
            "parser_version": "p", "table_count": 20, "income_tables": "t1", "cash_flow_tables": "t2", "tables_path": "t"}


class Synthetic(unittest.TestCase):
    def setUp(self):
        self.con = store.init(":memory:")
        store.write(self.con, "documents", [_doc("0000789019-25-000001", "MSFT", "2025-06-30")], replace=True)
        v = lambda field, period, label: {"ticker": "MSFT", "field": field, "period": period, "period_end": "2025-06-30", "value": 1, "source": "agent", "method": "reported", "label": label, "basis": "as_reported", "first_reported": None, "extraction_ids": "", "input_hash": ""}
        store.write(self.con, "values", [v("capex", "FY2024", "agree"), v("capex", "FY2025", "agree"), v("opex", "FY2025", "definition_gap"), v("revenue", "FY2025", "not_reported"), v("revenue", "FY2024", "unresolved")], replace=True)
        # XBRL looked up for MSFT (T80's marker, T81: not_reported explains only then): every cell but revenue FY2025, the not_reported one
        r = lambda field, period: {"ticker": "MSFT", "field": field, "period": period, "value": 1, "method": "reported", "concept": "us-gaap:X", "period_start": "2024-07-01",
                                   "period_end": "2025-06-30", "accession": "0000789019-25-000001", "restated": False, "original_value": None}
        store.write(self.con, "reference_values", [r("capex", "FY2024"), r("capex", "FY2025"), r("opex", "FY2025"), r("revenue", "FY2024")], replace=True)
        f = lambda field, dim, period, label: {"ticker": "MSFT", "field": field, "dimension": dim, "period": period, "period_end": "2025-06-30", "value": 1, "first_reported": 1, "basis": "as_reported", "label": label, "reference": 1, "accession": "0000789019-25-000001", "extraction_ids": "", "input_hash": ""}
        store.write(self.con, "facts", [f("segment_capex", "Cloud", "FY2025", "agree"), f("segment_capex", "Cloud", "FY2024", "no_reference"), f("ppe_category", "Land", "FY2025", "unresolved")], replace=True)
        s = lambda sid, kind, quote: {"statement_id": sid, "text_id": "x", "source": "mdna", "accession": "0000789019-25-000001", "ticker": "MSFT", "field": "capex", "period": "FY2026", "kind": kind, "scope": "total", "class": "explicit_amount",
                                      "amount_low": 1000000000, "amount_high": 1000000000, "share": None, "quote": quote, "passage": quote, "confidence": 0.9, "notes": "", "prompt_version": "aispend@v4", "run_id": "r"}
        store.write(self.con, "ai_statements", [s("s1", "outlook", "We expect capital expenditures of $1 billion in fiscal 2026."), s("s2", "outlook", "The joint venture, once completed, will cost $1 billion through 2030.")], replace=True)
        # no resolutions on file for the synthetic rows; decisions/ stays as it is
        self.patch = mock.patch.object(score, "_REPORTS", {})
        self.patch.start()

    def tearDown(self):
        self.patch.stop()
        self.con.close()

    def test_reader_counts_sum_to_the_denominator_and_the_twin_is_the_rows_xbrl_tags(self):
        sc = score.score(self.con, "reader", ["MSFT"])
        self.assertEqual(sc["outputs"], 5)
        self.assertEqual(sc["checked"] + sc["explained"] + sc["open"] + sc["blocked"], sc["outputs"])
        self.assertEqual((sc["checked"], sc["explained"], sc["open"], sc["blocked"]), (2, 2, 1, 0))  # agree x2; definition_gap and not_reported explained; unresolved open
        self.assertEqual(sc["twin"], {"agree": 2, "of": 4, "interval": [0.15, 0.85]})  # not_reported has no twin; the three others XBRL tags
        self.assertEqual(sc["stage"], "values")

    def test_the_twin_interval_is_wilson_on_the_counts_and_none_without_a_denominator(self):
        from ledger.core import stats
        sc = score.score(self.con, "reader", ["MSFT"])
        low, high = stats.wilson(sc["twin"]["agree"], sc["twin"]["of"])
        self.assertEqual(sc["twin"]["interval"], [round(low, 4), round(high, 4)])
        self.assertIn("Wilson 95%", sc["note"])
        self.assertIn("(not no_reference / not_reported rows)", sc["note"])
        self.assertIn("(not no_reference rows)", score.score(self.con, "notes_reader", ["MSFT"])["note"])
        self.assertEqual(score.with_interval({"agree": 0, "of": 0}), {"agree": 0, "of": 0, "interval": None})
        self.assertEqual(score.with_interval({"agree": 70, "of": 71})["interval"], [0.9244, 0.9975])
        # a company with no values rows: of is 0, the interval is None, never a made-up share
        store.write(self.con, "documents", [_doc("0000000000-25-000001", "NVDA", "2025-01-26")], replace=False)
        self.assertEqual(score.score(self.con, "reader", ["NVDA"])["twin"], {"agree": 0, "of": 0, "interval": None})

    def test_the_values_stage_findings_are_not_the_readers_outputs(self):
        store.write(self.con, "exceptions", [{"exception_id": "e1", "rule_id": "jump", "severity": "warn", "ticker": "MSFT", "field": "capex", "period": "FY2025", "subject": "s", "message": "a jump", "input_hash": "h"}], replace=True)
        self.assertEqual(score.score(self.con, "reader", ["MSFT"])["outputs"], 5)

    def test_notes_reader_twin_leaves_out_no_reference(self):
        sc = score.score(self.con, "notes_reader", ["MSFT"])
        self.assertEqual(sc["outputs"], 3)
        self.assertEqual(sc["checked"], 1)
        self.assertEqual(sc["explained"], 1)  # no_reference: the label explains it
        self.assertEqual(sc["open"], 1)
        self.assertEqual(sc["twin"], {"agree": 1, "of": 2, "interval": [0.0945, 0.9055]})

    def test_quote_readers_have_no_twin_and_no_fault_test(self):
        sc = score.score(self.con, "ai_reader", ["MSFT"])
        self.assertEqual((sc["outputs"], sc["checked"], sc["explained"]), (2, 1, 1))  # a verified quote; a program statement carries its guard
        self.assertIsNone(sc["twin"])
        self.assertIsNone(sc["faults"])
        self.assertIn("not measured", sc["faults_note"])
        self.assertIn("aispend", sc["faults_note"])
        sc = score.score(self.con, "projects_reader", ["MSFT"])
        self.assertEqual(sc["outputs"], 0)
        self.assertIsNone(sc["twin"])
        self.assertIsNone(sc["faults"])

    def test_faults_need_a_run_whose_report_covers_the_company(self):
        fl, note = score.faults(self.con, "reader", ["MSFT"])
        self.assertIsNone(fl)
        self.assertIn("no `ledger faults` run", note)
        store.write(self.con, "runs", [{"run_id": "f1", "step": "faults", "subject": "nowhere", "started_at": "2026-10-30T00:00:00+00:00", "seconds": 1.0, "outcome": "ok", "versions": "{}", "detail": "{}"}], replace=True)
        fl, note = score.faults(self.con, "reader", ["MSFT"])
        self.assertIsNone(fl)  # the report does not exist
        self.assertIn("no `ledger faults` run covered", note)
        self.reports = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.reports)
        self.rp = mock.patch.object(score, "REPORTS", self.reports)
        self.rp.start()
        self.addCleanup(self.rp.stop)
        (self.reports / "nowhere-faults.json").write_text(json.dumps([{"fault": "sign_flip", "extraction_id": "0000789019-25-000001|capex|2024-07-01|2025-06-30", "outcome": "rule", "caught_by": ["sign"]},
                                     {"fault": "wrong_scale", "extraction_id": "0000789019-25-000001|capex|2024-07-01|2025-06-30", "outcome": "no_effect", "caught_by": []},
                                     {"fault": "wrong_row", "extraction_id": "0000789019-25-000001|capex|2024-07-01|2025-06-30", "outcome": "escaped", "caught_by": []},
                                     {"fault": "wrong_row", "extraction_id": "0000000000-25-000001|capex|2024-07-01|2025-06-30", "outcome": "rule", "caught_by": ["sign"]}]))  # another company
        fl, note = score.faults(self.con, "reader", ["MSFT", "NVDA"])
        self.assertEqual({k: fl[k] for k in ("caught", "planted", "no_effect", "escaped")}, {"caught": 1, "planted": 3, "no_effect": 1, "escaped": 1})
        self.assertEqual(fl["by_kind"]["wrong_row"]["escaped"], 1)  # T67: per kind, for this company only
        self.assertIsNone(fl["xbrl_off"])  # no XBRL-off report beside this one
        self.assertIn("reports/nowhere-faults.json: run 2026-10-30, file written", note)
        self.assertIn("report newer than its run", note)  # the file was written now, the run says 2026-10-30
        self.assertIn("no run covered NVDA", note)
        # the file's own time is compared with the run's: a file no newer than its run is not called newer
        old = datetime(2026, 10, 29, tzinfo=timezone.utc).timestamp()
        os.utime(self.reports / "nowhere-faults.json", (old, old))
        fl, note = score.faults(self.con, "reader", ["MSFT"])
        self.assertNotIn("report newer", note)
        self.assertIn("file written 2026-10-29", note)

    def test_a_rewritten_report_is_read_again(self):
        reports = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, reports)
        with mock.patch.object(score, "REPORTS", reports):
            f = reports / "r-faults.json"
            f.write_text(json.dumps([{"fault": "sign_flip", "extraction_id": "a|capex|x|y", "outcome": "rule", "caught_by": ["sign"]}]))
            self.assertEqual(len(score._report("r")[0]), 1)
            f.write_text(json.dumps([{"fault": "sign_flip", "extraction_id": "a|capex|x|y", "outcome": "escaped", "caught_by": []}, {"fault": "wrong_row", "extraction_id": "a|capex|x|y", "outcome": "rule", "caught_by": ["sign"]}]))
            rows, written = score._report("r")  # ledger faults overwrote the file: size differs, so the cache misses
            self.assertEqual(len(rows), 2)
            self.assertTrue(written.startswith("20"))
            self.assertEqual(score._report("missing"), (None, None))

    def test_faults_note_is_its_own_field_and_the_note_states_the_exclusions(self):
        sc = score.score(self.con, "reader", ["MSFT"])
        self.assertIn("faults_note", sc)
        self.assertIn("no `ledger faults` run", sc["faults_note"])
        self.assertNotIn("faults:", sc["note"])
        self.assertIn("5 value rows", sc["note"])
        self.assertIn("1 not_reported", sc["note"])
        self.assertEqual(sc["excluded"], {"warn_findings": 0})
        self.assertEqual(sc["stage_rows"], 5)
        sc = score.score(self.con, "notes_reader", ["MSFT"])
        self.assertIn("Mapping stage", sc["note"])
        self.assertIn("faults.py", sc["faults_note"])

    def test_by_agent_carries_the_score(self):
        from ledger.extract import cost
        r = cost.by_agent(self.con, "reader", ["MSFT"])
        self.assertEqual(r["score"]["outputs"], 5)
        self.assertIsNone(cost.by_agent(self.con, "attributor", ["MSFT"])["score"])


@unittest.skipUnless(shutil.which("node"), "no node")
class Page(unittest.TestCase):
    """rules.js scoreBlock, run in node with the page's helpers stubbed to plain text: every count with its denominator,
    blocked and escaped always written, zero included; the faults line is the API's faults_note when nothing was measured."""

    def render(self, sc):
        from ledger.core import states
        js = (store.ROOT / "ledger" / "web" / "pages" / "rules.js").read_text()
        harness = states.js() + """
const h = (tag, attrs = {}, ...kids) => kids.flat(Infinity).filter((k) => k !== '' && k != null).join(' ');
const int = (n) => (n == null || n === '' ? '—' : Number(n).toLocaleString('en-US'));
const STAGE_LABEL_UI = {values: 'Values', facts: 'Facts', statements: 'Statements', planned: 'Planned'};
""" + js + "\nprocess.stdout.write(scoreBlock(JSON.parse(process.argv[process.argv.length - 1])));"
        return subprocess.run(["node", "-e", harness, "--", json.dumps(sc)], capture_output=True, text=True, check=True).stdout

    def test_zero_blocked_and_zero_escaped_are_written(self):
        sc = {"outputs": 81, "checked": 70, "explained": 11, "open": 0, "blocked": 0, "twin": {"agree": 70, "of": 71, "interval": [0.9244, 0.9975]},
              "faults": {"caught": 1275, "planted": 1283, "no_effect": 8, "escaped": 0}, "faults_note": "reports/stage3-faults.json: run 2026-10-30", "stage": "values", "companies": 6, "note": "n"}
        out = self.render(sc)
        self.assertIn("Checked 70 · Unverified 11 · To review 0 · Blocks release 0 (of 81)", out)
        self.assertIn("Matches SEC XBRL 70 of 71 · 98.6% (95% CI 92.4–99.8%)", out)
        # one display path: the page computes the interval from agree / of; the API's interval is informational, so a
        # missing or a wrong one changes nothing on the page
        del sc["twin"]["interval"]
        self.assertIn("Matches SEC XBRL 70 of 71 · 98.6% (95% CI 92.4–99.8%)", self.render(sc))
        sc["twin"]["interval"] = [0.1, 0.2]
        self.assertIn("Matches SEC XBRL 70 of 71 · 98.6% (95% CI 92.4–99.8%)", self.render(sc))
        sc["twin"] = {"agree": 0, "of": 0, "interval": None}
        self.assertIn("Matches SEC XBRL 0 of 0", self.render(sc))
        self.assertNotIn("95% CI", self.render(sc))  # no share, no interval
        self.assertIn("Caught 1,275 of 1,283 · Missed 0 · No effect 8", out)
        self.assertNotIn("reports/stage3-faults.json", out)  # file names stay in the API, off the page

    def test_not_measured_is_said_when_nothing_was_planted(self):
        sc = {"outputs": 3, "checked": 1, "explained": 1, "open": 0, "blocked": 1, "twin": None, "faults": None, "faults_note": "not measured: no fault test exists for the notes step's outputs", "stage": "facts", "companies": 1, "note": "n"}
        out = self.render(sc)
        self.assertIn("Blocks release 1 (of 3)", out)
        self.assertIn("No SEC XBRL counterpart", out)
        self.assertIn("Not measured", out)  # nothing planted: said, never a zero
        self.assertNotIn("Caught", out)


@unittest.skipUnless((store.DEFAULT_DB).exists(), "no working database")
class RealDatabase(unittest.TestCase):
    def test_every_live_reader_counts_sum_to_the_denominator_on_the_six(self):
        import duckdb
        from ledger.core.config import PROVEN
        con = duckdb.connect(str(store.DEFAULT_DB), read_only=True)
        try:
            for aid in score.AGENT_STAGE:
                sc = score.score(con, aid, PROVEN)
                self.assertEqual(sc["checked"] + sc["explained"] + sc["open"] + sc["blocked"], sc["outputs"], aid)
                self.assertGreater(sc["outputs"], 0, aid)
                if sc["twin"] is not None:
                    self.assertLessEqual(sc["twin"]["agree"], sc["twin"]["of"], aid)
                    self.assertLessEqual(sc["twin"]["of"], sc["outputs"], aid)
                if sc["faults"] is not None:
                    f = sc["faults"]
                    self.assertEqual(f["caught"] + f["no_effect"] + f["escaped"], f["planted"], aid)
                else:
                    self.assertIn("not measured", sc["faults_note"], aid)
        finally:
            con.close()


if __name__ == "__main__":
    unittest.main()
