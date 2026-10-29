import unittest

from ledger.config import AI_SET, MVP_YEARS, STAGES, added, stage_tickers, tracked


class Config(unittest.TestCase):
    def test_window_is_5_consecutive_fiscal_years(self):
        self.assertEqual([int(y[2:]) for y in MVP_YEARS], list(range(2022, 2027)))

    def test_stages_grow_to_the_19_companies_plus_any_added(self):
        prev = set()
        for n in STAGES:
            self.assertTrue(prev <= set(stage_tickers(n)), f"stage {n} drops a company")
            prev = set(stage_tickers(n))
        self.assertEqual([len(stage_tickers(n)) for n in (1, 2)] + [len(AI_SET)], [1, 5, 19])
        self.assertEqual(len(stage_tickers(3)), 19 + len({c["ticker"] for c in added()} - {c["ticker"] for c in AI_SET}))
        self.assertEqual(stage_tickers(3), [c["ticker"] for c in tracked()])


if __name__ == "__main__":
    unittest.main()
