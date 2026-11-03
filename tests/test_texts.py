"""A listed PDF link names its quarter; that quarter lands on the company's own calendar."""
import unittest

from ledger.ingest.texts import _quarter


class Quarter(unittest.TestCase):
    def test_quarter_and_year_from_link_names(self):
        self.assertEqual(_quarter("META-Q3-2026-Earnings-Call-Transcript.pdf"), (2026, 3))
        self.assertEqual(_quarter("Q2FY27-CFO-Commentary.pdf"), (2027, 2))
        self.assertEqual(_quarter("Transcript of Second Quarter 2027, PDF file"), (2027, 2))
        self.assertEqual(_quarter("NVDA-Q1-2027-Earnings-Call-20-May-2026-5_00-PM-ET.pdf"), (2027, 1))
        self.assertIsNone(_quarter("annual-report.pdf"))


if __name__ == "__main__":
    unittest.main()
