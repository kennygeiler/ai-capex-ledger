"""Decisions re-apply only on unchanged inputs; gates refuse; same inputs, same hash; the diff names changes."""
import unittest

from ledger.release.release import build, content_hash, failing, gates, table, to_check, version_key
from ledger.review.review import apply, open_items

EXC = {"exception_id": "sign|NVDA|capex|FY2026", "rule_id": "sign", "severity": "block", "ticker": "NVDA", "field": "capex", "period": "FY2026", "input_hash": "h1", "message": "m"}
VAL = {"ticker": "NVDA", "field": "capex", "period": "FY2026", "period_end": "2026-01-25", "value": -5, "source": "agent", "label": "agree", "basis": "as_reported", "first_reported": -5, "extraction_ids": ""}
DEC = {"exception_id": EXC["exception_id"], "kind": "override", "value": 5, "input_hash": "h1", "decision_id": "d1",
       "reviewer": "Kenny Geiler"}  # F14: a block closes only on a person's decision (tests.test_trust.DecisionAuthors holds a run's)


class Decisions(unittest.TestCase):
    def test_a_decision_closes_its_exception_until_the_input_changes(self):
        self.assertEqual(open_items([EXC], [DEC]), [])
        self.assertEqual(open_items([{**EXC, "input_hash": "h2"}], [DEC]), [{**EXC, "input_hash": "h2"}])

    def test_the_latest_decision_wins(self):
        later = {**DEC, "kind": "reject", "value": None, "decision_id": "d2"}
        self.assertEqual(apply([VAL], [EXC], [DEC, later])[0]["source"], "missing")
        self.assertEqual(apply([VAL], [EXC], [DEC])[0]["value"], 5)


class Versions(unittest.TestCase):
    def test_versions_sort_by_number_not_by_string(self):
        names = ["v1.10.0", "v1.9.0", "v0.2.0", "v1.1.0"]
        self.assertEqual(sorted(names, key=version_key), ["v0.2.0", "v1.1.0", "v1.9.0", "v1.10.0"])
        self.assertNotEqual(sorted(names), sorted(names, key=version_key))


class Gates(unittest.TestCase):
    """T4: one column per company in scope; a release is refused on any failing row."""
    T = ["NVDA"]

    def test_refuses_without_hand_check_or_with_an_open_blocker(self):
        g = gates([VAL], [EXC], None, tickers=self.T)
        self.assertEqual(g["G5"], {"NVDA": ["no hand-check file"]})
        self.assertEqual(g["G4"], {"NVDA": [EXC["exception_id"]]})
        self.assertEqual(failing(g), {"NVDA": {"G4": [EXC["exception_id"]], "G5": ["no hand-check file"]}})

    def test_passes_when_everything_is_decided_and_checked(self):
        hc = {"values": [{"ticker": "NVDA", "field": "capex", "period": "FY2026", "value": -5, "verified": True}]}
        self.assertEqual(failing(gates([VAL], [], hc, tickers=self.T)), {})
        self.assertTrue(gates([{**VAL, "value": 6}], [], hc, tickers=self.T)["G5"]["NVDA"])  # a check of an older value doesn't count

    def test_every_company_in_scope_gets_a_row_and_fails_on_its_own(self):
        vals = [VAL, {**VAL, "ticker": "MSFT", "label": "unresolved"}]
        g = gates(vals, [EXC], None, tickers=["NVDA", "MSFT"])
        self.assertEqual(set(g["G4"]), {"NVDA", "MSFT"})
        self.assertEqual(g["G4"], {"NVDA": [EXC["exception_id"]], "MSFT": []})
        self.assertEqual(g["G5"]["MSFT"], ["no hand-check file"])
        self.assertEqual(failing(gates(vals, [EXC], None, tickers=["MSFT"]))["MSFT"], {"G5": ["no hand-check file"]})  # NVDA's blocker is not MSFT's
        t = table(g)
        self.assertIn("MSFT", t.splitlines()[2]) if t.splitlines()[2].startswith("MSFT") else self.assertIn("MSFT", t)
        self.assertEqual([l.endswith("FAILS") for l in t.splitlines()[1:]], [True, True])

    def test_an_unconfirmed_decision_fails_g6_under_its_company_even_outside_the_scope(self):
        g = gates([], [], {"values": []}, tickers=["NVDA"], unconfirmed=[{"key": "finding_unconfirmed|TSLA|opex|FY2024||jump|"}])
        self.assertEqual(g["G6"], {"NVDA": [], "TSLA": ["finding_unconfirmed|TSLA|opex|FY2024||jump|"]})
        self.assertEqual(list(failing(g)), ["TSLA"])

    def test_only_values_xbrl_cant_vouch_for_and_a_sample_need_a_person(self):
        vals = [{**VAL, "period": f"FY{2000 + i}", "value": i + 1} for i in range(30)] + [{**VAL, "period": "FY2099", "value": 7, "label": "unresolved"}]
        c = to_check(vals)
        self.assertEqual((len(c), c[("NVDA", "capex", "FY2099")]), (11, "xbrl_differs"))
        self.assertEqual(c, to_check(vals))  # the same sample every run
        hc = {"values": [{"ticker": t, "field": f, "period": p, "value": next(v["value"] for v in vals if v["period"] == p), "verified": True} for t, f, p in c]}
        self.assertEqual(gates(vals, [], hc, tickers=self.T)["G5"], {"NVDA": []})

    def test_a_machine_confirmed_cell_needs_no_person(self):
        v = {**VAL, "label": "unresolved", "extraction_ids": "a,b"}
        self.assertEqual(gates([v], [], None, tickers=self.T)["G5"], {"NVDA": ["no hand-check file"]})
        self.assertEqual(gates([v], [], None, {"a"}, tickers=self.T)["G5"], {"NVDA": ["no hand-check file"]})  # every cell of the value must be confirmed
        self.assertEqual(gates([v], [], None, {"a", "b"}, tickers=self.T)["G5"], {"NVDA": []})


class Build(unittest.TestCase):
    def test_same_inputs_same_hash_and_diff_names_changes(self):
        a = build("v0.1.0", [VAL], [], [EXC], None)
        self.assertEqual(content_hash(a), content_hash(build("v0.1.0", [VAL], [], [EXC], None)))
        self.assertIn("First release.", a["DIFF.md"])
        b = build("v0.1.1", [{**VAL, "value": 5}], [], [EXC], [{"ticker": "NVDA", "field": "capex", "period": "FY2026", "value": "-5"}])
        self.assertIn("-5 → 5", b["DIFF.md"])


class Headlines(unittest.TestCase):
    """T64 / DC6: a row without a value is never counted as a value added; QUALITY.md says what was checked and by what."""

    def test_a_blank_row_is_counted_on_its_own_line_not_as_a_value_added(self):
        blank = {**VAL, "field": "opex", "value": None, "first_reported": None, "source": "missing", "label": "not_reported"}
        b = build("v0.1.1", [VAL, blank], [], [], [{"ticker": "NVDA", "field": "revenue", "period": "FY2026", "value": "1"}])
        self.assertIn("Added: 1 values for NVDA.", b["DIFF.md"])
        self.assertIn("1 rows without a value, not in values.csv (not_reported: 1).", b["DIFF.md"])
        self.assertTrue(b["QUALITY.md"].splitlines()[2].startswith("1 values in values.csv"))
        self.assertIn("1 rows without a value, not in values.csv (not_reported: 1)", b["QUALITY.md"])
        self.assertIn("## Columns of values.csv", b["README.md"])
        self.assertIn("| `check_label` |", b["README.md"])

    def test_rows_diff_counts_added_and_removed_rows_without_a_value_on_their_own(self):
        from ledger.release.release import rows_diff, rows_diff_md
        t = "ticker,field,period,value\n"
        d = rows_diff({"values.csv": t + "A,capex,FY1,5\nA,opex,FY1,\n"}, {"values.csv": t + "B,capex,FY1,\n"})["values"]
        self.assertEqual((d["added"], d["removed"], d["without_value"]), (2, 1, {"added": 1, "removed": 1}))
        self.assertIn("rows without a value: 1 of the added, 1 of the removed", rows_diff_md({"values": d}))

    def test_the_check_line_names_code_and_the_hand_check_file_or_its_absence(self):
        from ledger.release.release import GATES, check_line
        self.assertNotIn("by a person where it can't", GATES["G5"])
        line = check_line([VAL], frozenset())
        self.assertIn("By machine: the re-read of the rendered 10-K confirmed 0 of 0 cited cells", line)
        self.assertIn("independent reading", line)
        self.assertNotIn("two independent sources", line)
        self.assertIn("By a person: no hand-check for this release", line)
        hc = {"values": [{"ticker": "NVDA", "field": "capex", "period": "FY2026", "value": -5, "verified": True}, {"ticker": "NVDA", "field": "capex", "period": "FY2025", "value": 1, "verified": True}]}
        self.assertIn("By a person: 1 values verified on the filing in golden/stage1-handcheck.json", check_line([VAL], frozenset(), hc, "golden/stage1-handcheck.json"))
        self.assertIn("By a person: 0 values verified", check_line([VAL], frozenset(), {"values": [{**hc["values"][0], "value": 7}]}, "f"))  # a hand-check at another value does not count


class SplitIds(unittest.TestCase):
    def test_commas_inside_labels(self):
        from ledger.release.release import split_ids
        j = "0001692819-26-000006|revenue|2023-01-01|2023-12-31,0001692819-26-000006|cost_of_revenue_part|2023-01-01|2023-12-31|Fuel, purchased power costs, and delivery fees,0001692819-26-000006|operating_income|2023-01-01|2023-12-31"
        self.assertEqual(len(split_ids(j)), 3)
        self.assertTrue(split_ids(j)[1].endswith("delivery fees"))


class RowsDiff(unittest.TestCase):
    """T8: DIFF.md lists rows added, removed and changed per list by the row's key, and a changed `check` names the column."""
    OLD = "ticker,fiscal_year,measure,category,reported_name,value,check\nMSFT,FY2024,spent,capex,Additions,10,agree\nMSFT,FY2024,planned,guidance,Capex,,verbatim\nMSFT,FY2024,planned,guidance,Capex,5,verbatim\nAMD,FY2024,spent,capex,Additions,3,agree\n"
    NEW = "ticker,fiscal_year,measure,category,reported_name,value,check,mapped\nMSFT,FY2024,spent,capex,Additions,10,explained,True\nMSFT,FY2024,planned,guidance,Capex,5,verbatim,True\nNVDA,FY2025,spent,capex,Additions,7,agree,True\n"

    def test_added_removed_changed_by_key_and_a_changed_check_is_named(self):
        from ledger.release.release import rows_diff, rows_diff_md
        d = rows_diff({"taxonomy.csv": self.NEW, "values.csv": "ticker,field,period,value\n"}, {"taxonomy.csv": self.OLD})
        t = d["taxonomy"]
        self.assertEqual((t["added"], t["removed"], t["changed"], t["rows"]), (1, 2, 1, 3))  # NVDA added; AMD and one of the two MSFT guidance rows removed; MSFT capex check changed
        self.assertEqual(t["examples"]["changed"], [{"key": ["MSFT", "FY2024", "spent", "capex", "Additions"], "columns": {"check": ("agree", "explained")}}])
        self.assertEqual(t["columns_added"], ["mapped"])
        self.assertNotIn("values", d)  # the previous release has no values.csv to compare
        md = rows_diff_md(d)
        self.assertIn("| taxonomy.csv | 3 | 1 | 2 | 1 |", md)
        self.assertIn("MSFT FY2024 spent capex Additions: check: agree → explained", md)
        self.assertIn("columns added: `mapped`", md)
        self.assertEqual(rows_diff({"taxonomy.csv": self.NEW}, None), {})
        self.assertEqual(rows_diff_md({}), "")

    def test_a_repeated_key_with_one_changed_and_one_removed(self):
        from ledger.release.release import rows_diff
        t = "ticker,fiscal_year,measure,category,reported_name,value,source,quote\n"
        old = t + "A,FY1,planned,guidance,Capex,1,s1,one\nA,FY1,planned,guidance,Capex,2,s2,two\nA,FY1,planned,guidance,Capex,3,s3,three\n"
        new = t + "A,FY1,planned,guidance,Capex,1,s1,one\nA,FY1,planned,guidance,Capex,9,s2,two\n"
        d = rows_diff({"taxonomy.csv": new}, {"taxonomy.csv": old})["taxonomy"]
        self.assertEqual((d["added"], d["removed"], d["changed"]), (0, 1, 1))
        self.assertEqual(d["examples"]["changed"][0]["columns"], {"value": ("2", "9")})  # s2 moved; s3 left

    def test_a_repeated_key_pairs_the_closest_rows(self):
        from ledger.release.release import rows_diff
        t = "ticker,fiscal_year,measure,category,reported_name,value,source\n"
        d = rows_diff({"taxonomy.csv": t + "A,FY1,planned,guidance,Capex,1,s1\nA,FY1,planned,guidance,Capex,2,s2\n"}, {"taxonomy.csv": t + "A,FY1,planned,guidance,Capex,2,s2\nA,FY1,planned,guidance,Capex,1,s1\n"})
        self.assertEqual((d["taxonomy"]["added"], d["taxonomy"]["removed"], d["taxonomy"]["changed"]), (0, 0, 0))


if __name__ == "__main__":
    unittest.main()


class OneThreshold(unittest.TestCase):
    def test_zero_never_widens_the_tolerance(self):
        from ledger.core import config
        self.assertEqual(config.rounding_unit(0), 1)
        self.assertTrue(config.restated(0, 400_000, config.rounding_unit(0)))

    def test_every_site_moves_with_the_one_constant(self):
        from unittest import mock
        from ledger.core import config
        with mock.patch.object(config, "RESTATEMENT_TOLERANCE", 10):
            self.assertFalse(config.restated(100, 104, 1))
        self.assertTrue(config.restated(100, 104, 1))


class StatusColumnDoc(unittest.TestCase):
    """F27: the packet README said the status column holds empty, confirmed, overridden or rejected; it holds the words
    resolutions.by_row writes."""

    def test_the_readme_names_the_status_values_the_rows_carry(self):
        from ledger.release.release import column_doc
        from ledger.review.resolutions import STATUS
        for name in ("values", "facts"):
            allowed, meaning = column_doc(name, "status")
            for w in STATUS.values():
                self.assertIn(f"`{w}`", allowed, name)
                self.assertIn(f"`{w}`", meaning, name)
            for gone in ("confirmed", "overridden", "rejected"):
                self.assertNotIn(gone, allowed + meaning, name)
