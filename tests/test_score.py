"""The per-agent score (T49): counts with denominators from the live tables through status.state (via proof.company),
the twin only where the rows have one, the faults only where a run measured them."""
import json
import os
import unittest
from unittest import mock

from ledger import score, store


def _doc(acc, ticker, period):
    return {"accession": acc, "ticker": ticker, "cik": 1, "form": "10-K", "period": period, "filed": period, "url": "u", "sha256": "0" * 64, "bytes": 1,
            "parser_version": "p", "table_count": 20, "income_tables": "t1", "cash_flow_tables": "t2", "tables_path": "t"}


class Synthetic(unittest.TestCase):
    def setUp(self):
        self.con = store.init(":memory:")
        store.write(self.con, "documents", [_doc("0000789019-25-000001", "MSFT", "2025-06-30")], replace=True)
        v = lambda field, period, label: {"ticker": "MSFT", "field": field, "period": period, "period_end": "2025-06-30", "value": 1, "source": "agent", "method": "reported", "label": label, "basis": "as_reported", "first_reported": None, "extraction_ids": "", "input_hash": ""}
        store.write(self.con, "values", [v("capex", "FY2024", "agree"), v("capex", "FY2025", "agree"), v("opex", "FY2025", "definition_gap"), v("revenue", "FY2025", "not_reported"), v("revenue", "FY2024", "unresolved")], replace=True)
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
        self.assertEqual(sc["twin"], {"agree": 2, "of": 4})  # not_reported has no twin; the three others XBRL tags
        self.assertEqual(sc["stage"], "values")

    def test_the_values_stage_findings_are_not_the_readers_outputs(self):
        store.write(self.con, "exceptions", [{"exception_id": "e1", "rule_id": "jump", "severity": "warn", "ticker": "MSFT", "field": "capex", "period": "FY2025", "subject": "s", "message": "a jump", "input_hash": "h"}], replace=True)
        self.assertEqual(score.score(self.con, "reader", ["MSFT"])["outputs"], 5)

    def test_notes_reader_twin_leaves_out_no_reference(self):
        sc = score.score(self.con, "notes_reader", ["MSFT"])
        self.assertEqual(sc["outputs"], 3)
        self.assertEqual(sc["checked"], 1)
        self.assertEqual(sc["explained"], 1)  # no_reference: the label explains it
        self.assertEqual(sc["open"], 1)
        self.assertEqual(sc["twin"], {"agree": 1, "of": 2})

    def test_quote_readers_have_no_twin_and_no_fault_test(self):
        sc = score.score(self.con, "ai_reader", ["MSFT"])
        self.assertEqual((sc["outputs"], sc["checked"], sc["explained"]), (2, 1, 1))  # a verified quote; a program statement carries its guard
        self.assertIsNone(sc["twin"])
        self.assertIsNone(sc["faults"])
        self.assertIn("not measured", sc["note"])
        self.assertIn("aispend", sc["note"])
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
        score._REPORTS["nowhere"] = [{"fault": "sign_flip", "extraction_id": "0000789019-25-000001|capex|2024-07-01|2025-06-30", "outcome": "rule", "caught_by": ["sign"]},
                                     {"fault": "wrong_scale", "extraction_id": "0000789019-25-000001|capex|2024-07-01|2025-06-30", "outcome": "no_effect", "caught_by": []},
                                     {"fault": "wrong_row", "extraction_id": "0000789019-25-000001|capex|2024-07-01|2025-06-30", "outcome": "escaped", "caught_by": []},
                                     {"fault": "wrong_row", "extraction_id": "0000000000-25-000001|capex|2024-07-01|2025-06-30", "outcome": "rule", "caught_by": ["sign"]}]  # another company
        fl, note = score.faults(self.con, "reader", ["MSFT", "NVDA"])
        self.assertEqual(fl, {"caught": 1, "planted": 3, "no_effect": 1, "escaped": 1})
        self.assertIn("nowhere (2026-10-30)", note)
        self.assertIn("no run covered NVDA", note)

    def test_by_agent_carries_the_score(self):
        from ledger import cost
        r = cost.by_agent(self.con, "reader", ["MSFT"])
        self.assertEqual(r["score"]["outputs"], 5)
        self.assertIsNone(cost.by_agent(self.con, "attributor", ["MSFT"])["score"])


@unittest.skipUnless((store.DEFAULT_DB).exists(), "no working database")
class RealDatabase(unittest.TestCase):
    def test_every_live_reader_counts_sum_to_the_denominator_on_the_six(self):
        import duckdb
        from ledger.config import PROVEN
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
                    self.assertIn("not measured", sc["note"], aid)
        finally:
            con.close()


if __name__ == "__main__":
    unittest.main()
