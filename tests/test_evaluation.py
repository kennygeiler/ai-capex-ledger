"""The reference set scores the attribution: a stated figure within tolerance agrees, a floor or ceiling is a bound, and a
company-year we have no number for is a coverage miss, not an error."""
import unittest

from ledger.evaluation import score

ATTR = [{"ticker": "GOOGL", "field": "capex", "period": "FY2025", "kind": "actual", "method": "ppe_category", "ai_amount": 54_000_000_000, "ai_share": 0.58, "confidence": 0.6},
        {"ticker": "MSFT", "field": "capex", "period": "FY2025", "kind": "actual", "method": "ppe_category", "ai_amount": 39_000_000_000, "ai_share": 0.61, "confidence": 0.6},
        {"ticker": "TSLA", "field": "capex", "period": "FY2024", "kind": "actual", "method": "qualitative", "ai_amount": None, "ai_share": None, "confidence": 0.5}]
SRC = {"kind": "company_statement", "url": "https://example.com", "quote": "q"}
GOLD = [{"ticker": "GOOGL", "period": "FY2025", "field": "capex", "measure": "share", "relation": "eq", "value": 0.60, "basis": "b", "source": SRC, "by": "K"},
        {"ticker": "MSFT", "period": "FY2025", "field": "capex", "measure": "share", "relation": "le", "value": 0.50, "basis": "b", "source": SRC, "by": "K"},
        {"ticker": "TSLA", "period": "FY2024", "field": "capex", "measure": "amount", "relation": "ge", "value": 5_000_000_000, "basis": "b", "source": SRC, "by": "K"}]


class Evaluation(unittest.TestCase):
    def test_outcomes_and_bands(self):
        ev = score(GOLD, ATTR, {})
        self.assertEqual([r["outcome"] for r in ev["rows"]], ["agree", "disagree", "no_estimate"])
        self.assertEqual((ev["with_estimate"], ev["agree"], ev["disagree"], ev["no_estimate"]), (2, 1, 1, 1))
        b = ev["bands"]["ppe_category"]
        self.assertEqual((b["n"], b["agree"], b["n_eq"]), (2, 1, 1))
        self.assertAlmostEqual(b["median_abs_error"], abs(0.58 - 0.60) / 0.60)


if __name__ == "__main__":
    unittest.main()
