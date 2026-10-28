"""The app's review action accepts only warnings and cost-line confirmations, with a reason and a name.
Decisions go to a temporary log here, never to decisions/decisions.jsonl."""
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from ledger import app, review, store


@unittest.skipUnless(store.DEFAULT_DB.exists(), "needs a built ledger database")
class Decide(unittest.TestCase):
    def setUp(self):
        self.log = Path(tempfile.mkdtemp()) / "decisions.jsonl"
        self.patch = mock.patch.object(review, "LOG", self.log)
        self.patch.start()

    def tearDown(self):
        self.patch.stop()

    def _ids(self, where):
        con = app._con()
        try:
            return [r[0] for r in con.execute(f"select exception_id from exceptions where {where} limit 1").fetchall()]
        finally:
            con.close()

    def test_needs_a_reason_and_a_name(self):
        with self.assertRaises(ValueError):
            app.decide_items(["x"], " ", "Kenny Geiler")
        with self.assertRaises(ValueError):
            app.decide_items(["x"], "expected", "")

    def test_refuses_unknown_items_and_other_blocks(self):
        with self.assertRaises(ValueError):
            app.decide_items(["no-such-exception"], "expected", "Kenny Geiler")
        other = self._ids("severity = 'block' and rule_id <> 'cost_lines_summed'")
        if other:
            with self.assertRaises(ValueError):
                app.decide_items(other, "expected", "Kenny Geiler")

    def test_writes_only_to_the_log_it_is_given(self):
        ids = self._ids("severity = 'warn'")
        if ids:
            app.decide_items(ids, "test", "Test")
            self.assertEqual(len(self.log.read_text().splitlines()), 1)


if __name__ == "__main__":
    unittest.main()
