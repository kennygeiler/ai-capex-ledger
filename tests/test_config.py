import unittest

from ledger.config import AI_SET, MVP_TICKERS, MVP_YEARS, STAGES, added


class Config(unittest.TestCase):
    def test_window_is_5_consecutive_fiscal_years(self):
        self.assertEqual([int(y[2:]) for y in MVP_YEARS], list(range(2022, 2027)))

    def test_stages_grow_to_the_19_companies_plus_any_added(self):
        prev = set()
        for n in sorted(STAGES):
            self.assertTrue(prev <= set(STAGES[n]["tickers"]), f"stage {n} drops a company")
            prev = set(STAGES[n]["tickers"])
        self.assertEqual([len(STAGES[n]["tickers"]) for n in (1, 2)] + [len(AI_SET)], [1, 5, 19])
        self.assertEqual(len(STAGES[3]["tickers"]), 19 + len({c["ticker"] for c in added()} - {c["ticker"] for c in AI_SET}))
        self.assertEqual(set(STAGES[3]["tickers"]), set(MVP_TICKERS))


if __name__ == "__main__":
    unittest.main()
