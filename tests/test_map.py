"""docs/MAP.md names real places: every ledger/ path it mentions exists, and every package under ledger/ has a line."""
import re
import unittest

from ledger.core import store

MAP = store.ROOT / "docs" / "MAP.md"


class Map(unittest.TestCase):
    def test_every_path_exists_and_every_package_is_listed(self):
        text = MAP.read_text()
        paths = set(re.findall(r"`(ledger/[\w/.]+?)`", text))
        mods = set(re.findall(r"`((?:core|ingest|extract|checks|review|release|web)/[\w.]+\.py)`", text))
        self.assertTrue(paths and mods)
        for p in paths:
            self.assertTrue((store.ROOT / p.rstrip("/")).exists(), p)
        for m in mods:
            self.assertTrue((store.ROOT / "ledger" / m).exists(), m)
        for d in sorted((store.ROOT / "ledger").iterdir()):
            if d.is_dir() and (d / "__init__.py").exists() and d.name not in ("cli", "spikes"):
                self.assertIn(f"`ledger/{d.name}/`", text, d.name)


if __name__ == "__main__":
    unittest.main()
