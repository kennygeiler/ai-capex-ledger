"""A definition replaces a question: a revenue definition turns an XBRL gap into definition_gap, and named cost lines
keep cost_lines_summed quiet. Every entry must say who decided and why."""
import tempfile
import unittest
from pathlib import Path

from ledger.definitions import cost_lines, load, revenue_gap_explained
from ledger.reconcile import values_for
from ledger.rules import Context, run, load as load_rules
from tests.test_reconcile import DOCS, x
from tests.test_rules import ext

DEFS = {"XOM": {"revenue": {"line": "Sales", "why": "tag is wider", "by": "Kenny Geiler"},
                "cost_lines": {"lines": ["Crude oil and product purchases", "Production and manufacturing expenses"], "why": "no total", "by": "Kenny Geiler"}}}


class Definitions(unittest.TestCase):
    def test_a_revenue_definition_explains_the_xbrl_gap(self):
        xs = [x("revenue", "2025-05-31", 100_000_000, "a", "2025-07-01")]
        self.assertEqual(values_for("XOM", xs, {("revenue", "FY2025"): 104_000_000}, "0531", DOCS)[0]["label"], "unresolved")
        self.assertEqual(values_for("XOM", xs, {("revenue", "FY2025"): 104_000_000}, "0531", DOCS, DEFS)[0]["label"], "definition_gap")
        self.assertEqual(values_for("AMD", xs, {("revenue", "FY2025"): 104_000_000}, "0531", DOCS, DEFS)[0]["label"], "unresolved")

    def test_named_cost_lines_keep_the_rule_quiet(self):
        part = ("cost_of_revenue_part", "2025-01-01", "2025-12-31")
        xs = [ext(*part, 5_000_000_000, "5,000", "Crude oil and product purchases", "2025"), ext(*part, 2_000_000_000, "2,000", "Production and manufacturing expenses", "2025")]
        rules = [r for r in load_rules() if r["id"] == "cost_lines_summed"]
        xs = [{**e, "ticker": "XOM"} for e in xs]
        self.assertEqual(len(run(Context([], xs), rules)), 1)
        self.assertEqual(run(Context([], xs, definitions=DEFS), rules), [])
        extra = xs + [{**xs[0], "row_label": "Selling, general and administrative", "extraction_id": "z"}]
        self.assertEqual(len(run(Context([], extra, definitions=DEFS), rules)), 1)  # a line the definition doesn't name still asks

    def test_an_entry_needs_who_and_why(self):
        p = Path(tempfile.mkdtemp()) / "companies.yaml"
        p.write_text("XOM:\n  revenue:\n    line: Sales\n")
        with self.assertRaises(ValueError):
            load(p)
        p.write_text("XOM:\n  cost_lines:\n    lines: [A, B]\n    why: w\n    by: K\n")
        self.assertEqual(cost_lines(load(p), "XOM"), {"A", "B"})
        self.assertFalse(revenue_gap_explained(load(p), "XOM"))


if __name__ == "__main__":
    unittest.main()


class OpexDefinition(unittest.TestCase):
    def test_loads_and_explains(self):
        from ledger.definitions import load, opex_gap_explained
        defs = load()
        self.assertTrue(opex_gap_explained(defs, "IRM"))
        self.assertFalse(opex_gap_explained(defs, "MSFT"))
