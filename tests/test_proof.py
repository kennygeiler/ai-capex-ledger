import unittest

from ledger.core import status
from ledger.checks.proof import _item, amendment_without_statements, keys_of


class Amendments(unittest.TestCase):
    def test_a_part_three_amendment_is_explained(self):
        self.assertTrue(amendment_without_statements({"form": "10-K/A", "table_count": 3, "income_tables": "", "cash_flow_tables": ""}))
        self.assertFalse(amendment_without_statements({"form": "10-K", "table_count": 3, "income_tables": "", "cash_flow_tables": ""}))
        self.assertFalse(amendment_without_statements({"form": "10-K/A", "table_count": 80, "income_tables": "", "cash_flow_tables": ""}))  # a full restated 10-K/A: locate or open
        self.assertFalse(amendment_without_statements({"form": "10-K/A", "table_count": 3, "income_tables": "t1", "cash_flow_tables": "t2"}))
        self.assertTrue(amendment_without_statements({"form": "10-K/A", "table_count": 3, "income_tables": "t0005,t0006", "cash_flow_tables": None}))  # AMD: a compensation table taken for an income statement


if __name__ == "__main__":
    unittest.main()


class Keys(unittest.TestCase):
    def test_rows_by_key_grade_sum_to_the_denominator(self):
        """T56: every item counts once, under its strongest key or under none; the grades sum to rows."""
        items = [_item("capex FY2025", status.state({"check": "xbrl"})), _item("capex FY2024", status.state({"check": "esef:ifrs-full:Revenue"})),
                 _item("revenue FY2025", status.state({"check": "source:0001"})), _item("q", status.state({"check": "rule:quarters_tie"})),
                 _item("plan", status.state({"check": "actual:FY2025"})), _item("quote", status.state({"check": "quote"})),
                 _item("gap", status.state({"definition": "revenue"})), _item("open", status.state({}))]
        k = keys_of(items)
        self.assertEqual(k, {"twin": 2, "second_source": 1, "tie": 1, "later_truth": 1, "second_reading": 0, "none": 3, "rows": 8})
        self.assertEqual(sum(k[g] for g in (*status.KEY_GRADE, "none")), k["rows"])
        self.assertEqual(keys_of([]), {"twin": 0, "second_source": 0, "tie": 0, "later_truth": 0, "second_reading": 0, "none": 0, "rows": 0})
        self.assertEqual(items[0]["key"], "twin")
        self.assertEqual(items[0]["keys"], ["twin"])
        self.assertIsNone(items[-1]["key"])
