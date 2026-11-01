"""The test run as a report file (T30): `ledger test` runs the unittest suite and writes reports/tests.json, which the
Release page's "Test run" line reads (checklist.py).

Shape: {"ok": bool, "count": int, "failures": ["test id: first line of the error", ...], "skipped": int,
        "golden": true | false | null (ran and passed | ran and failed | skipped, --fast or no fixtures),
        "at": ISO UTC, "git": short sha of HEAD or null (no git, as on the hosted copy), "dirty": bool | null}.
The checklist compares `git` with its own HEAD: a run on another commit or a dirty tree is stale and informs, never signs."""
import json
import subprocess
import traceback
import unittest
from datetime import datetime, timezone

from . import store

REPORT = store.ROOT / "reports" / "tests.json"
GOLDEN_TEST = "tests.test_golden.Golden.test_code_stages_reproduce_the_expected_tables"


class Result(unittest.TextTestResult):
    """TextTestResult that also keeps every test id it started and one line per failure or error."""

    def __init__(self, *a, **kw):
        super().__init__(*a, **kw)
        self.started = []
        self.lines = []

    def startTest(self, test):
        self.started.append(test.id())
        super().startTest(test)

    def _line(self, test, err):
        first = (traceback.format_exception_only(err[0], err[1]) or [""])[0].strip().splitlines() or [""]
        self.lines.append(f"{test.id()}: {first[0]}")

    def addFailure(self, test, err):
        self._line(test, err)
        super().addFailure(test, err)

    def addError(self, test, err):
        self._line(test, err)
        super().addError(test, err)


def git_state(root=None) -> tuple:
    """(short sha of HEAD, dirty) from the working tree at `root`; (None, None) without git or a repository. The report
    file itself never counts as dirty: writing it is what the run does; untracked files do not count either."""
    root = root or store.ROOT
    try:
        sha = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=root, capture_output=True, text=True, timeout=10)
        if sha.returncode:
            return None, None
        st = subprocess.run(["git", "status", "--porcelain", "--untracked-files=no"], cwd=root, capture_output=True, text=True, timeout=10)
    except (OSError, subprocess.SubprocessError):
        return None, None
    changed = [l for l in st.stdout.splitlines() if l.strip() and not l[3:].strip().endswith("reports/tests.json")]
    return sha.stdout.strip() or None, bool(changed) if st.returncode == 0 else None


def changed_since(sha: str, root=None) -> list | None:
    """Paths that differ between commit `sha` and HEAD, or None without git or when `sha` is unknown here. The checklist
    uses it to forgive a run whose only successor commits recorded the run (reports/tests.json) and nothing else."""
    try:
        r = subprocess.run(["git", "diff", "--name-only", sha, "HEAD"], cwd=root or store.ROOT, capture_output=True, text=True, timeout=10)
    except (OSError, subprocess.SubprocessError):
        return None
    return [l.strip() for l in r.stdout.splitlines() if l.strip()] if r.returncode == 0 else None


def report(result, seconds: float | None = None, git=None) -> dict:
    """The report for one run. `result` is a unittest result (Result, or any TestResult with testsRun, failures, errors,
    skipped); the golden flag is read from whether GOLDEN_TEST started, was skipped, or failed."""
    skipped_ids = {t.id() for t, _ in result.skipped}
    failed_ids = {t.id() for t, _ in (*result.failures, *result.errors)}
    started = set(getattr(result, "started", ())) or (failed_ids | skipped_ids)
    lines = getattr(result, "lines", None)
    if lines is None:
        lines = [f"{t.id()}: {(e or '').strip().splitlines()[-1] if (e or '').strip() else ''}" for t, e in (*result.failures, *result.errors)]
    if GOLDEN_TEST in skipped_ids or GOLDEN_TEST not in started:
        golden = None
    else:
        golden = GOLDEN_TEST not in failed_ids
    sha, dirty = git if git is not None else git_state()
    rep = {"ok": result.wasSuccessful(), "count": result.testsRun, "failures": lines, "skipped": len(result.skipped), "golden": golden,
           "at": datetime.now(timezone.utc).isoformat(timespec="seconds"), "git": sha, "dirty": dirty}
    if seconds is not None:
        rep["seconds"] = round(seconds, 1)
    return rep


def write(rep: dict, path=None) -> None:
    path = path or REPORT
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(rep, indent=1) + "\n")
