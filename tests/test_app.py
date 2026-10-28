"""The app's one review action accepts only current warnings, with a reason and a name."""
import unittest

from ledger import app, store


@unittest.skipUnless(store.DEFAULT_DB.exists(), "needs a built ledger database")
class AcceptWarnings(unittest.TestCase):
    def test_needs_a_reason_and_a_name(self):
        with self.assertRaises(ValueError):
            app.accept_warnings(["x"], " ", "Kenny Geiler")
        with self.assertRaises(ValueError):
            app.accept_warnings(["x"], "expected", "")

    def test_refuses_anything_but_a_current_warning(self):
        con = app._con()
        block = con.execute("select exception_id from exceptions where severity = 'block' limit 1").fetchone()
        con.close()
        for ids in (["no-such-exception"], [block[0]] if block else ["no-such-exception"]):
            with self.assertRaises(ValueError):
                app.accept_warnings(ids, "expected", "Kenny Geiler")


if __name__ == "__main__":
    unittest.main()
