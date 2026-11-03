"""ledger/core/stats.py (T53): the Wilson 95% interval on a share, with known values; None where there is no denominator."""
import unittest

from ledger.core import stats


class Wilson(unittest.TestCase):
    def test_seventy_of_seventy_one(self):
        low, high = stats.wilson(70, 71)
        self.assertAlmostEqual(low, 0.9244, places=4)
        self.assertAlmostEqual(high, 0.9975, places=4)
        self.assertLess(high, 1.0)  # a 1 of 71 miss keeps the top end under 100%

    def test_no_denominator_is_none(self):
        self.assertIsNone(stats.wilson(0, 0))
        self.assertIsNone(stats.share(0, 0))

    def test_all_agree_on_a_small_n_stays_wide(self):
        low, high = stats.wilson(3, 3)
        self.assertAlmostEqual(low, 0.4385, places=4)
        self.assertEqual(high, 1.0)
        low, high = stats.wilson(0, 5)
        self.assertEqual(low, 0.0)
        self.assertAlmostEqual(high, 0.4345, places=4)

    def test_textbook_value(self):
        # 80 of 100 at 95%: 0.711–0.867 (Newcombe 1998, table of Wilson limits), the EVALS "about ±8 points" line
        low, high = stats.wilson(80, 100)
        self.assertAlmostEqual(low, 0.7112, places=3)
        self.assertAlmostEqual(high, 0.8666, places=3)

    def test_half_is_symmetric_and_the_bounds_hold(self):
        low, high = stats.wilson(2, 4)
        self.assertAlmostEqual(low + high, 1.0, places=9)
        with self.assertRaises(ValueError):
            stats.wilson(5, 4)

    def test_share(self):
        self.assertAlmostEqual(stats.share(70, 71), 70 / 71)


if __name__ == "__main__":
    unittest.main()
