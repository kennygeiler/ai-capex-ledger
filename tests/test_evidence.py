"""The rendered-10-K re-read confirms a real cited cell and notices one moved to another column or row."""
import shutil
import tempfile
import unittest
from pathlib import Path

from ledger.evidence import read, same

FIX = Path(__file__).parent / "fixtures" / "filings" / "ORCL_10-K_2026-05-31.html"
REV = {"extraction_id": "rev", "table_id": "t0000", "row_label": "Total revenues", "column_label": "Year Ended May 31, | 2026", "cell_text": "67,357"}
CHROME = Path("/Applications/Google Chrome.app").exists() or shutil.which("google-chrome")


class Same(unittest.TestCase):
    def test_ignores_dollar_signs_and_spaces_not_parentheses(self):
        self.assertTrue(same("$ (98,338)", "(98,338)"))
        self.assertFalse(same("98,338", "(98,338)"))


@unittest.skipUnless(CHROME, "needs Chrome")
class Reread(unittest.TestCase):
    def test_confirms_the_cell_and_notices_a_moved_citation(self):
        cites = [REV, {**REV, "extraction_id": "col", "column_label": "Year Ended May 31, | 2025"},
                 {**REV, "extraction_id": "row", "row_label": "Operating income"}]
        with tempfile.TemporaryDirectory() as d:
            r = read(FIX, cites, {"rev"}, Path(d))
            self.assertTrue((Path(d) / r["rev"]["img"]).exists())
        self.assertEqual([r[k]["match"] for k in ("rev", "col", "row")], [True, False, False])


if __name__ == "__main__":
    unittest.main()


class RunTogether(unittest.TestCase):
    def test_a_cell_that_runs_several_values_together_confirms_none_of_them(self):
        """The cited text must be the whole cell (review of the evidence viewer): a run-together cell is a reason, not a match."""
        from ledger.evidence import runs_together, same
        self.assertFalse(same("(2,292)(2,367)(2,828)", "(2,367)"))
        self.assertTrue(runs_together("(2,292)(2,367)(2,828)", "(2,367)"))
        self.assertFalse(runs_together("(2,292)(2,367)(2,828)", "(2,36)"))
        self.assertTrue(same("$ 28,496", "28,496"))
        self.assertTrue(runs_together("(437)2,1902,089", "2,089"))
        self.assertTrue(runs_together("(437)2,1902,089", "2,190"))
        self.assertFalse(runs_together("(437)2,1902,089", "1,902"))
