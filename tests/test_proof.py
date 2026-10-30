import unittest

from ledger.proof import amendment_without_statements


class Amendments(unittest.TestCase):
    def test_a_part_three_amendment_is_explained(self):
        self.assertTrue(amendment_without_statements({"form": "10-K/A", "table_count": 3, "income_tables": "", "cash_flow_tables": ""}))
        self.assertFalse(amendment_without_statements({"form": "10-K", "table_count": 3, "income_tables": "", "cash_flow_tables": ""}))
        self.assertFalse(amendment_without_statements({"form": "10-K/A", "table_count": 80, "income_tables": "", "cash_flow_tables": ""}))  # a full restated 10-K/A: locate or open
        self.assertFalse(amendment_without_statements({"form": "10-K/A", "table_count": 3, "income_tables": "t1", "cash_flow_tables": "t2"}))
        self.assertTrue(amendment_without_statements({"form": "10-K/A", "table_count": 3, "income_tables": "t0005,t0006", "cash_flow_tables": None}))  # AMD: a compensation table taken for an income statement


if __name__ == "__main__":
    unittest.main()
