"""Decisions re-apply only on unchanged inputs; gates refuse; same inputs, same hash; the diff names changes."""
import unittest

from ledger.release import build, content_hash, failing, gates, table, to_check, version_key
from ledger.review import apply, open_items

EXC = {"exception_id": "sign|NVDA|capex|FY2026", "rule_id": "sign", "severity": "block", "ticker": "NVDA", "field": "capex", "period": "FY2026", "input_hash": "h1", "message": "m"}
VAL = {"ticker": "NVDA", "field": "capex", "period": "FY2026", "period_end": "2026-01-25", "value": -5, "source": "agent", "label": "agree", "basis": "as_reported", "first_reported": -5, "extraction_ids": ""}
DEC = {"exception_id": EXC["exception_id"], "kind": "override", "value": 5, "input_hash": "h1", "decision_id": "d1"}


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
        g = gates([], [], {"values": []}, tickers=["NVDA"], unconfirmed=[{"key": "finding_unconfirmed|TSLA|opex FY2024"}])
        self.assertEqual(g["G6"], {"NVDA": [], "TSLA": ["finding_unconfirmed|TSLA|opex FY2024"]})
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


if __name__ == "__main__":
    unittest.main()


class SplitIds(unittest.TestCase):
    def test_commas_inside_labels(self):
        from ledger.release import split_ids
        j = "0001692819-26-000006|revenue|2023-01-01|2023-12-31,0001692819-26-000006|cost_of_revenue_part|2023-01-01|2023-12-31|Fuel, purchased power costs, and delivery fees,0001692819-26-000006|operating_income|2023-01-01|2023-12-31"
        self.assertEqual(len(split_ids(j)), 3)
        self.assertTrue(split_ids(j)[1].endswith("delivery fees"))
