import os
import unittest
from pathlib import Path

from ledger import golden
from ledger.config import PROVEN


class Golden(unittest.TestCase):
    """The pipeline proves itself on the proven set: run the code stages on the frozen fixtures, compare every table (docs/PROOF.md).
    About 30 seconds. Set LEDGER_SKIP_GOLDEN=1 to skip while iterating on something else."""

    @unittest.skipIf(os.environ.get("LEDGER_SKIP_GOLDEN") or not (golden.FIXTURES / "seed.json").exists(), "no fixtures or skipped")
    def test_code_stages_reproduce_the_expected_tables(self):
        r = golden.check()
        self.assertFalse(r.get("failed_step"), f"step failed: {r.get('failed_step')}\n" + "\n".join(l["err"][-600:] or l["out"][-600:] for l in r["log"] if l["exit"] not in (0, 2)))
        self.assertTrue(r["ok"], "differences: " + "; ".join(f"{k}: {v['n_only_in_run']} only in the run, {v['n_only_in_expected']} only in expected" for k, v in r["diffs"].items()))

    def test_fixtures_cover_the_proven_set(self):
        import json
        seed = json.loads((golden.FIXTURES / "seed.json").read_text())
        self.assertEqual(seed["tickers"], PROVEN)
        self.assertTrue(any((golden.FIXTURES / "data" / "notes" / "outputs").glob("*.json")))
        for name in (*golden.TABLES, *golden.LISTS):  # the stored tables and the computed taxonomy rows (T31)
            self.assertTrue((golden.EXPECTED / f"{name}.csv").exists(), name)


if __name__ == "__main__":
    unittest.main()
