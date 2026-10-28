"""The filing's own reason for changing past years is found for the reviewer."""
import unittest

from ledger.ingest.notes import restatement_note


class Notes(unittest.TestCase):
    def test_finds_the_sentence(self):
        page = "<p>Revenue grew.</p><p>As a result of this transaction, certain prior-period amounts have been <b>recast</b> to conform. Other text.</p>"
        self.assertEqual(restatement_note(page), "As a result of this transaction, certain prior-period amounts have been recast to conform.")

    def test_none_when_absent(self):
        self.assertIsNone(restatement_note("<p>Nothing changed. Budget and forecast information.</p>"))  # not "recast" inside "forecast"


if __name__ == "__main__":
    unittest.main()
