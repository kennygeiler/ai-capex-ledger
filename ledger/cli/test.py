"""python -m ledger test [--fast] [--verbose]

Runs the unittest suite (tests/) and writes reports/tests.json for the Release page's "Test run" line (T30,
ledger/testreport.py). --fast sets LEDGER_SKIP_GOLDEN=1, so the golden test is skipped and the report says golden null.
Exit 0 only when every test passed."""
import argparse
import os
import sys
import time
import unittest

from .. import store
from ..testreport import REPORT, Result, report, write


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="python -m ledger test")
    ap.add_argument("--fast", action="store_true", help="skip the golden test (LEDGER_SKIP_GOLDEN=1); the report says golden null")
    ap.add_argument("--verbose", "-v", action="store_true")
    a = ap.parse_args(argv)
    if a.fast:
        os.environ["LEDGER_SKIP_GOLDEN"] = "1"
    suite = unittest.defaultTestLoader.discover(str(store.ROOT / "tests"), top_level_dir=str(store.ROOT))
    t0 = time.monotonic()
    result = unittest.TextTestRunner(stream=sys.stderr, verbosity=2 if a.verbose else 1, resultclass=Result).run(suite)
    rep = report(result, seconds=time.monotonic() - t0)
    write(rep)
    golden = {True: "golden ok", False: "golden FAILED", None: "golden skipped"}[rep["golden"]]
    print(f"{rep['count']} tests, {len(rep['failures'])} failing, {rep['skipped']} skipped, {golden}, {rep['seconds']} s, "
          f"{rep['git'] or 'no git'}{' dirty' if rep['dirty'] else ''} -> {REPORT.relative_to(store.ROOT)}")
    return 0 if rep["ok"] else 1
