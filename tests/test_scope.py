"""The scope (T2, config.SCOPE): what every list, page and packet shows unless a ticker is asked for by name."""
import unittest
from unittest import mock

from ledger import api, config
from ledger.config import PROVEN, SCOPE


class Scope(unittest.TestCase):
    def test_scope_is_the_proven_set_until_widened(self):
        self.assertEqual(SCOPE, PROVEN)
        self.assertTrue(set(PROVEN) <= set(SCOPE))
        self.assertTrue(set(SCOPE) <= {c["ticker"] for c in config.tracked()})

    def test_a_list_with_no_ticker_filter_is_the_scope(self):
        rows = api.query(None, "companies", {})
        self.assertEqual(sorted(r["ticker"] for r in rows), sorted(SCOPE))
        self.assertEqual(len(api.fetch(None, "companies")), 100)  # the database keeps every company

    def test_a_ticker_outside_the_scope_still_answers(self):
        out = [c["ticker"] for c in config.tracked() if c["ticker"] not in SCOPE][0]
        rows = api.query(None, "companies", {"ticker": out})
        self.assertEqual([r["ticker"] for r in rows], [out])
        self.assertEqual(api.query(None, "companies", {"ticker": f"{out},{SCOPE[0]}"}).__len__(), 2)

    def test_a_signed_release_read_through_the_api_is_scoped_too(self):
        rows = api.query(None, "values", {"release": "v1.7.0"})
        self.assertTrue(rows)
        self.assertEqual({r["ticker"] for r in rows} - set(SCOPE), set())
        self.assertTrue({r["ticker"] for r in api.query(None, "values", {"release": "v1.7.0", "ticker": "MU"})} == {"MU"})

    def test_the_board_and_the_queue_read_the_scope(self):
        import inspect
        from ledger import app, proof
        self.assertIn("for t in SCOPE", inspect.getsource(proof.board))
        self.assertIn("sorted(SCOPE)", inspect.getsource(app._flow))


if __name__ == "__main__":
    unittest.main()
