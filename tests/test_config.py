import unittest

from ledger.config import DEV_SPLIT, HOLDOUT, MVP_QUARTERS, MVP_TICKERS


class Split(unittest.TestCase):
    def test_dev_and_holdout_partition_the_mvp(self):
        self.assertEqual(len(MVP_TICKERS), 19)
        self.assertFalse(set(DEV_SPLIT) & set(HOLDOUT))
        self.assertEqual(set(DEV_SPLIT) | set(HOLDOUT), set(MVP_TICKERS))

    def test_window_is_8_consecutive_quarters(self):
        self.assertEqual(len(MVP_QUARTERS), 8)
        self.assertEqual(MVP_QUARTERS, sorted(MVP_QUARTERS))



class Stages(unittest.TestCase):
    def test_stages_grow_and_keep_dev_and_holdout_apart(self):
        from ledger.config import STAGES
        prev = set()
        for n in sorted(STAGES):
            s = STAGES[n]
            self.assertTrue(prev <= set(s["tickers"]), f"stage {n} drops a company")
            self.assertFalse(set(s["dev"]) & set(s["holdout"]))
            self.assertEqual(set(s["dev"]) | set(s["holdout"]), set(s["tickers"]))
            prev = set(s["tickers"])
        self.assertEqual([len(STAGES[n]["tickers"]) for n in (1, 2, 3)], [1, 5, 19])


if __name__ == "__main__":
    unittest.main()
