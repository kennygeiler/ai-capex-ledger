import unittest

from ledger.evaluation import comparable


class Comparability(unittest.TestCase):
    def test_narrower_reference_below_ours_inside_the_window_is_consistent(self):
        e = {"measure": "share", "value": 0.60, "scope": "narrower"}
        self.assertEqual(comparable(e, 0.68)[0], "consistent")
        self.assertEqual(comparable(e, 0.80)[0], "disagree")   # 20 points over: outside the window
        self.assertEqual(comparable(e, 0.50)[0], "disagree")   # a wider measure below a narrower one: wrong direction

    def test_wider_reference_above_ours_is_consistent(self):
        e = {"measure": "share", "value": 0.70, "scope": "wider"}
        self.assertEqual(comparable(e, 0.62)[0], "consistent")
        self.assertEqual(comparable(e, 0.75)[0], "disagree")

    def test_not_comparable_and_same(self):
        self.assertEqual(comparable({"measure": "share", "value": 0.9, "scope": "not_comparable", "scope_note": "a planning floor"}, 0.56), ("not_comparable", "a planning floor"))
        self.assertEqual(comparable({"measure": "amount", "value": 100.0}, 130.0)[0], "disagree")

    def test_amount_window(self):
        e = {"measure": "amount", "value": 100.0, "scope": "narrower"}
        self.assertEqual(comparable(e, 140.0)[0], "consistent")
        self.assertEqual(comparable(e, 160.0)[0], "disagree")


if __name__ == "__main__":
    unittest.main()
