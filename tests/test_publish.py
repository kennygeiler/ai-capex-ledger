"""The publish gate: only a signed release whose files match the signed hash goes to production; column typing."""
import json
import unittest
from unittest import mock

from ledger import publish


class Gate(unittest.TestCase):
    def test_unsigned_release_refused(self):
        with self.assertRaises(publish.NotPublishable) as cm:
            publish.check("v1.2.0")
        self.assertIn("not signed", str(cm.exception))

    def test_unknown_release_refused(self):
        with self.assertRaises(publish.NotPublishable):
            publish.check("v0.0.0")

    def test_signed_release_passes(self):
        rel = publish.check("v1.4.0")
        self.assertEqual(rel["manifest"]["hash"], rel["signoff"]["hash"])

    def test_hash_mismatch_refused(self):
        with mock.patch.object(publish, "content_hash", lambda files: "0" * 64):
            with self.assertRaises(publish.NotPublishable) as cm:
                publish.check("v1.4.0")
            self.assertIn("no longer match", str(cm.exception))


class Columns(unittest.TestCase):
    def test_types(self):
        cols = dict(publish.columns(["ticker", "value", "period_end", "basis", "ai_share"]))
        self.assertEqual(cols, {"ticker": "text", "value": "numeric", "period_end": "date", "basis": "text", "ai_share": "numeric"})

    def test_ddl_quotes_and_release_column(self):
        self.assertEqual(publish.ddl("ledger_values", ["ticker", "value"]),
                         'CREATE TABLE IF NOT EXISTS ledger_values (release text NOT NULL, "ticker" text, "value" numeric)')


if __name__ == "__main__":
    unittest.main()


class Ordinal(unittest.TestCase):
    def test_version_order(self):
        self.assertLess(publish.ordinal("v1.3.0"), publish.ordinal("v1.4.0"))
        self.assertLess(publish.ordinal("v1.10.0"), publish.ordinal("v2.0.0"))
